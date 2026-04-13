"""Preset inputs schema + resolution tests — Phase 7 / parent I26+I27.

EffectGraph (the preset container) gains an optional ``inputs`` field.
Each ``PresetInput`` binds a SourceRegistry source pad to a named layer
slot. The compiler's ``resolve_preset_inputs`` helper dereferences the
pads against a live registry at preset-load time and raises
``PresetLoadError`` on any unknown pad — no silent fallthrough.
"""

from __future__ import annotations

import pytest

from agents.effect_graph.compiler import PresetLoadError, resolve_preset_inputs
from agents.effect_graph.types import EffectGraph, NodeInstance, PresetInput
from agents.studio_compositor.source_registry import SourceRegistry


def _minimal_graph(name: str = "t", inputs: list[PresetInput] | None = None) -> EffectGraph:
    return EffectGraph(
        name=name,
        nodes={"n": NodeInstance(type="noise")},
        edges=[],
        inputs=inputs,
    )


class _StubBackend:
    def get_current_surface(self) -> None:  # type: ignore[override]
        return None


# ── PresetInput schema ──────────────────────────────────────────────


def test_preset_input_accepts_pad_and_layer() -> None:
    entry = PresetInput(pad="reverie", **{"as": "layer0"})
    assert entry.pad == "reverie"
    assert entry.as_ == "layer0"


def test_preset_input_accepts_snake_case_attribute() -> None:
    entry = PresetInput(pad="reverie", as_="layer0")
    assert entry.as_ == "layer0"


def test_preset_input_rejects_empty_pad() -> None:
    with pytest.raises(ValueError):
        PresetInput(pad="", **{"as": "layer0"})


def test_preset_input_rejects_empty_as() -> None:
    with pytest.raises(ValueError):
        PresetInput(pad="reverie", **{"as": ""})


def test_preset_input_rejects_extra_fields() -> None:
    with pytest.raises(ValueError):
        PresetInput(pad="reverie", **{"as": "layer0", "nope": "x"})


def test_effect_graph_inputs_field_is_optional() -> None:
    graph = _minimal_graph()
    assert graph.inputs is None


def test_effect_graph_accepts_inputs_list() -> None:
    graph = _minimal_graph(
        inputs=[
            PresetInput(pad="reverie", **{"as": "layer0"}),
            PresetInput(pad="cam-vinyl", **{"as": "layer1"}),
        ],
    )
    assert graph.inputs is not None
    assert len(graph.inputs) == 2
    assert graph.inputs[0].pad == "reverie"
    assert graph.inputs[1].as_ == "layer1"


# ── resolve_preset_inputs ────────────────────────────────────────────


def test_resolve_returns_empty_dict_when_inputs_absent() -> None:
    registry = SourceRegistry()
    registry.register("reverie", _StubBackend())
    graph = _minimal_graph()
    assert resolve_preset_inputs(graph, registry) == {}


def test_resolve_returns_empty_dict_when_inputs_empty() -> None:
    registry = SourceRegistry()
    registry.register("reverie", _StubBackend())
    graph = _minimal_graph(inputs=[])
    assert resolve_preset_inputs(graph, registry) == {}


def test_resolve_maps_pads_to_backend_handles() -> None:
    registry = SourceRegistry()
    reverie_backend = _StubBackend()
    cam_backend = _StubBackend()
    registry.register("reverie", reverie_backend)
    registry.register("cam-vinyl", cam_backend)
    graph = _minimal_graph(
        inputs=[
            PresetInput(pad="reverie", **{"as": "layer0"}),
            PresetInput(pad="cam-vinyl", **{"as": "layer1"}),
        ],
    )
    resolved = resolve_preset_inputs(graph, registry)
    assert set(resolved.keys()) == {"layer0", "layer1"}
    assert resolved["layer0"] is reverie_backend
    assert resolved["layer1"] is cam_backend


def test_resolve_fails_loudly_on_unknown_pad() -> None:
    registry = SourceRegistry()
    registry.register("reverie", _StubBackend())
    graph = _minimal_graph(
        name="bad-preset",
        inputs=[PresetInput(pad="nonexistent", **{"as": "layer0"})],
    )
    with pytest.raises(PresetLoadError) as excinfo:
        resolve_preset_inputs(graph, registry)
    msg = str(excinfo.value)
    assert "bad-preset" in msg
    assert "nonexistent" in msg
    assert "reverie" in msg  # known pad list is included for debugging


def test_resolve_fails_loudly_on_second_unknown_after_known() -> None:
    """One known pad early in the list doesn't absolve a later unknown."""
    registry = SourceRegistry()
    registry.register("reverie", _StubBackend())
    graph = _minimal_graph(
        name="half-bad",
        inputs=[
            PresetInput(pad="reverie", **{"as": "layer0"}),
            PresetInput(pad="ghost", **{"as": "layer1"}),
        ],
    )
    with pytest.raises(PresetLoadError) as excinfo:
        resolve_preset_inputs(graph, registry)
    assert "ghost" in str(excinfo.value)


# ── Compositor preset-load path wiring ──────────────────────────────


def test_try_graph_preset_rejects_preset_with_unknown_input_pad(tmp_path, caplog) -> None:
    """Post-epic audit Phase 1 finding #2 regression pin.

    ``resolve_preset_inputs`` existed in the compiler module after
    Phase 7 of the completion epic but no caller invoked it from the
    preset-load path. A preset that referenced an unknown source pad
    was silently loaded into the graph runtime. This test pins that
    ``try_graph_preset`` now (a) calls ``resolve_preset_inputs``,
    (b) refuses to load on ``PresetLoadError``, and (c) logs the
    rejection at ERROR so AC-7 ("fails loudly") is visible in ops
    logs.
    """
    import logging

    from agents.studio_compositor.effects import try_graph_preset
    from agents.studio_compositor.source_registry import SourceRegistry

    # Minimal preset JSON with an ``inputs`` entry pointing at an
    # unknown source pad. ``nodes``/``edges`` are kept minimal — the
    # test exercises the input-resolution gate, not the node graph.
    bad_preset = {
        "name": "bad-inputs-preset",
        "nodes": {"n": {"type": "noise"}},
        "edges": [],
        "inputs": [{"pad": "does-not-exist", "as": "layer0"}],
    }
    preset_dir = tmp_path / "presets"
    preset_dir.mkdir()
    preset_path = preset_dir / "bad_inputs_preset.json"
    preset_path.write_text(
        __import__("json").dumps(bad_preset),
    )

    # Fake compositor with the minimum surface `try_graph_preset`
    # inspects: a source_registry that knows *some* pad, a
    # _graph_runtime with a load_graph spy, and a class that lets us
    # monkey-patch the preset directory search via environment
    # indirection (we override the Path.home() lookup by pointing the
    # tmp_path-hosted preset into the second fallback directory).

    class _FakeRuntime:
        def __init__(self) -> None:
            self.loaded = False

        def load_graph(self, graph) -> None:  # noqa: ARG002
            self.loaded = True

    class _FakeCompositor:
        def __init__(self, registry: SourceRegistry) -> None:
            self.source_registry = registry
            self._graph_runtime = _FakeRuntime()

    registry = SourceRegistry()
    registry.register("reverie", _StubBackend())
    compositor = _FakeCompositor(registry)

    # ``try_graph_preset`` walks two directories in order:
    # ``~/.config/hapax/effect-presets`` and
    # ``<repo>/presets``. Monkey-patch the former via HOME so the
    # tmp preset wins the search without touching the real repo.
    import os

    monkey_home = tmp_path / "home"
    (monkey_home / ".config" / "hapax" / "effect-presets").mkdir(parents=True)
    for p in preset_dir.iterdir():
        (monkey_home / ".config" / "hapax" / "effect-presets" / p.name).write_text(p.read_text())
    old_home = os.environ.get("HOME")
    os.environ["HOME"] = str(monkey_home)
    caplog.set_level(logging.ERROR, logger="agents.studio_compositor.effects")
    try:
        result = try_graph_preset(compositor, "bad_inputs_preset")
    finally:
        if old_home is not None:
            os.environ["HOME"] = old_home
        else:
            os.environ.pop("HOME", None)

    assert result is False, "preset with unknown input pad must not load"
    assert compositor._graph_runtime.loaded is False, (
        "graph runtime must not receive a preset whose inputs failed to resolve"
    )
    # ERROR log mentions the rejected preset name.
    assert any(
        "bad_inputs_preset" in rec.message and rec.levelno >= logging.ERROR
        for rec in caplog.records
    ), "rejection must log at ERROR for AC-7 'fails loudly'"
