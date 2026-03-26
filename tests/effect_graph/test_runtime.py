"""Tests for GraphRuntime — three mutation levels."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.effect_graph.compiler import GraphCompiler
from agents.effect_graph.modulator import UniformModulator
from agents.effect_graph.registry import ShaderRegistry
from agents.effect_graph.runtime import GraphRuntime
from agents.effect_graph.types import (
    EffectGraph,
    GraphPatch,
    LayerPalette,
    ModulationBinding,
    NodeInstance,
)

# ---------------------------------------------------------------------------
# Manifest helpers (same pattern as test_compiler.py)
# ---------------------------------------------------------------------------


def _write_manifest(directory: Path, manifest: dict, frag_source: str | None = None) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / f"{manifest['node_type']}.json"
    manifest_path.write_text(json.dumps(manifest))
    frag_name = manifest.get("glsl_fragment")
    if frag_name and frag_source is not None:
        (directory / frag_name).write_text(frag_source)


STUB_GLSL = "void main() {}"

MANIFESTS: list[tuple[dict, str | None]] = [
    (
        {
            "node_type": "colorgrade",
            "glsl_fragment": "colorgrade.frag",
            "inputs": {"in": "frame"},
            "outputs": {"out": "frame"},
            "params": {"saturation": {"type": "float", "default": 1.0, "min": 0.0, "max": 2.0}},
        },
        STUB_GLSL,
    ),
    (
        {
            "node_type": "trails",
            "glsl_fragment": "trails.frag",
            "inputs": {"in": "frame"},
            "outputs": {"out": "frame"},
            "params": {"decay": {"type": "float", "default": 0.9, "min": 0.0, "max": 1.0}},
            "temporal": True,
            "temporal_buffers": 2,
        },
        STUB_GLSL,
    ),
    (
        {
            "node_type": "bloom",
            "glsl_fragment": "bloom.frag",
            "inputs": {"in": "frame"},
            "outputs": {"out": "frame"},
            "params": {"threshold": {"type": "float", "default": 0.8, "min": 0.0, "max": 1.0}},
        },
        STUB_GLSL,
    ),
    (
        {
            "node_type": "scanlines",
            "glsl_fragment": "scanlines.frag",
            "inputs": {"in": "frame"},
            "outputs": {"out": "frame"},
            "params": {"intensity": {"type": "float", "default": 0.3, "min": 0.0, "max": 1.0}},
        },
        STUB_GLSL,
    ),
    (
        {
            "node_type": "vignette",
            "glsl_fragment": "vignette.frag",
            "inputs": {"in": "frame"},
            "outputs": {"out": "frame"},
            "params": {"radius": {"type": "float", "default": 0.7, "min": 0.0, "max": 1.0}},
        },
        STUB_GLSL,
    ),
    (
        {
            "node_type": "noise_overlay",
            "glsl_fragment": "noise_overlay.frag",
            "inputs": {"in": "frame"},
            "outputs": {"out": "frame"},
            "params": {"amount": {"type": "float", "default": 0.1, "min": 0.0, "max": 1.0}},
        },
        STUB_GLSL,
    ),
    (
        {
            "node_type": "output",
            "inputs": {"in": "frame"},
            "outputs": {},
            "params": {},
        },
        None,
    ),
]


@pytest.fixture()
def registry(tmp_path: Path) -> ShaderRegistry:
    """Minimal registry with all test node types."""
    for manifest, glsl in MANIFESTS:
        _write_manifest(tmp_path, manifest, glsl)
    return ShaderRegistry(tmp_path)


@pytest.fixture()
def runtime(registry: ShaderRegistry) -> GraphRuntime:
    compiler = GraphCompiler(registry)
    modulator = UniformModulator()
    return GraphRuntime(registry, compiler, modulator)


def _simple_graph() -> EffectGraph:
    return EffectGraph(
        name="simple",
        nodes={
            "cg": NodeInstance(type="colorgrade", params={"saturation": 1.2}),
            "out": NodeInstance(type="output"),
        },
        edges=[["@live", "cg"], ["cg", "out"]],
    )


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


class TestInitialState:
    def test_no_graph(self, runtime: GraphRuntime) -> None:
        assert runtime.current_graph is None

    def test_no_plan(self, runtime: GraphRuntime) -> None:
        assert runtime.current_plan is None


# ---------------------------------------------------------------------------
# load_graph
# ---------------------------------------------------------------------------


class TestLoadGraph:
    def test_sets_current_graph(self, runtime: GraphRuntime) -> None:
        graph = _simple_graph()
        runtime.load_graph(graph)
        assert runtime.current_graph is graph

    def test_sets_current_plan(self, runtime: GraphRuntime) -> None:
        graph = _simple_graph()
        runtime.load_graph(graph)
        plan = runtime.current_plan
        assert plan is not None
        assert plan.name == "simple"
        assert [s.node_id for s in plan.steps] == ["cg", "out"]

    def test_calls_on_plan_changed(self, runtime: GraphRuntime) -> None:
        calls: list[tuple] = []
        runtime._on_plan_changed = lambda old, new: calls.append((old, new))
        graph = _simple_graph()
        runtime.load_graph(graph)
        assert len(calls) == 1
        assert calls[0][0] is None  # old plan was None
        assert calls[0][1] is runtime.current_plan

    def test_modulations_loaded(self, runtime: GraphRuntime) -> None:
        graph = _simple_graph()
        graph.modulations = [
            ModulationBinding(node="cg", param="saturation", source="energy", scale=0.5),
        ]
        runtime.load_graph(graph)
        bindings = runtime.modulator.bindings
        assert len(bindings) == 1
        assert bindings[0].node == "cg"
        assert bindings[0].source == "energy"

    def test_layer_palettes_applied(self, runtime: GraphRuntime) -> None:
        graph = _simple_graph()
        graph.layer_palettes = {"live": LayerPalette(saturation=0.8, brightness=1.1)}
        runtime.load_graph(graph)
        palette = runtime.get_layer_palette("live")
        assert palette.saturation == 0.8
        assert palette.brightness == 1.1


# ---------------------------------------------------------------------------
# patch_node_params
# ---------------------------------------------------------------------------


class TestPatchNodeParams:
    def test_updates_params(self, runtime: GraphRuntime) -> None:
        runtime.load_graph(_simple_graph())
        runtime.patch_node_params("cg", {"saturation": 1.5})
        assert runtime.current_graph is not None
        assert runtime.current_graph.nodes["cg"].params["saturation"] == 1.5

    def test_calls_on_params_changed(self, runtime: GraphRuntime) -> None:
        calls: list[tuple] = []
        runtime._on_params_changed = lambda nid, p: calls.append((nid, p))
        runtime.load_graph(_simple_graph())
        runtime.patch_node_params("cg", {"saturation": 0.9})
        assert len(calls) == 1
        assert calls[0] == ("cg", {"saturation": 0.9})

    def test_no_graph_raises(self, runtime: GraphRuntime) -> None:
        with pytest.raises(RuntimeError, match="No graph loaded"):
            runtime.patch_node_params("cg", {"saturation": 1.0})

    def test_unknown_node_raises(self, runtime: GraphRuntime) -> None:
        runtime.load_graph(_simple_graph())
        with pytest.raises(KeyError, match="nonexistent"):
            runtime.patch_node_params("nonexistent", {"x": 1})


# ---------------------------------------------------------------------------
# apply_patch — topology mutation
# ---------------------------------------------------------------------------


class TestApplyPatch:
    def test_add_nodes_and_edges(self, runtime: GraphRuntime) -> None:
        runtime.load_graph(_simple_graph())
        patch = GraphPatch(
            add_nodes={"bl": NodeInstance(type="bloom", params={"threshold": 0.7})},
            remove_edges=[["cg", "out"]],
            add_edges=[["cg", "bl"], ["bl", "out"]],
        )
        runtime.apply_patch(patch)
        graph = runtime.current_graph
        assert graph is not None
        assert "bl" in graph.nodes
        plan = runtime.current_plan
        assert plan is not None
        ids = [s.node_id for s in plan.steps]
        assert ids.index("cg") < ids.index("bl") < ids.index("out")

    def test_remove_nodes(self, runtime: GraphRuntime) -> None:
        # Start with a three-node chain: cg -> sc -> out
        graph = EffectGraph(
            name="chain",
            nodes={
                "cg": NodeInstance(type="colorgrade"),
                "sc": NodeInstance(type="scanlines"),
                "out": NodeInstance(type="output"),
            },
            edges=[["@live", "cg"], ["cg", "sc"], ["sc", "out"]],
        )
        runtime.load_graph(graph)
        # Remove scanlines, reconnect
        patch = GraphPatch(
            remove_nodes=["sc"],
            add_edges=[["cg", "out"]],
        )
        runtime.apply_patch(patch)
        assert runtime.current_graph is not None
        assert "sc" not in runtime.current_graph.nodes
        assert runtime.current_plan is not None
        ids = [s.node_id for s in runtime.current_plan.steps]
        assert ids == ["cg", "out"]

    def test_no_graph_raises(self, runtime: GraphRuntime) -> None:
        with pytest.raises(RuntimeError, match="No graph loaded"):
            runtime.apply_patch(GraphPatch())

    def test_calls_on_plan_changed(self, runtime: GraphRuntime) -> None:
        calls: list[tuple] = []
        runtime.load_graph(_simple_graph())
        runtime._on_plan_changed = lambda old, new: calls.append((old, new))
        patch = GraphPatch(
            add_nodes={"bl": NodeInstance(type="bloom")},
            remove_edges=[["cg", "out"]],
            add_edges=[["cg", "bl"], ["bl", "out"]],
        )
        runtime.apply_patch(patch)
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# Layer palettes
# ---------------------------------------------------------------------------


class TestLayerPalettes:
    def test_default_palettes(self, runtime: GraphRuntime) -> None:
        for layer in ("live", "smooth", "hls"):
            palette = runtime.get_layer_palette(layer)
            assert palette.saturation == 1.0

    def test_set_and_get(self, runtime: GraphRuntime) -> None:
        custom = LayerPalette(saturation=0.5, contrast=1.3)
        runtime.set_layer_palette("live", custom)
        result = runtime.get_layer_palette("live")
        assert result.saturation == 0.5
        assert result.contrast == 1.3

    def test_unknown_layer_returns_default(self, runtime: GraphRuntime) -> None:
        palette = runtime.get_layer_palette("nonexistent")
        assert palette == LayerPalette()


# ---------------------------------------------------------------------------
# get_graph_state
# ---------------------------------------------------------------------------


class TestGetGraphState:
    def test_no_graph(self, runtime: GraphRuntime) -> None:
        state = runtime.get_graph_state()
        assert state["graph"] is None
        assert "layer_palettes" in state
        assert state["modulations"] == []

    def test_with_graph(self, runtime: GraphRuntime) -> None:
        graph = _simple_graph()
        graph.modulations = [
            ModulationBinding(node="cg", param="saturation", source="energy"),
        ]
        runtime.load_graph(graph)
        state = runtime.get_graph_state()
        assert state["graph"] is not None
        assert state["graph"]["name"] == "simple"
        assert len(state["modulations"]) == 1
        assert "live" in state["layer_palettes"]
