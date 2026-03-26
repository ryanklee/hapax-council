"""Tests for UniformModulator."""

from __future__ import annotations

from agents.effect_graph.modulator import UniformModulator
from agents.effect_graph.types import ModulationBinding


class TestBindingManagement:
    def test_add_binding_appears_in_bindings(self) -> None:
        mod = UniformModulator()
        b = ModulationBinding(node="n1", param="alpha", source="energy")
        mod.add_binding(b)
        assert mod.bindings == [b]

    def test_add_binding_replaces_same_node_param(self) -> None:
        mod = UniformModulator()
        b1 = ModulationBinding(node="n1", param="alpha", source="energy", scale=1.0)
        b2 = ModulationBinding(node="n1", param="alpha", source="valence", scale=2.0)
        mod.add_binding(b1)
        mod.add_binding(b2)
        assert len(mod.bindings) == 1
        assert mod.bindings[0].source == "valence"

    def test_remove_binding(self) -> None:
        mod = UniformModulator()
        mod.add_binding(ModulationBinding(node="n1", param="alpha", source="energy"))
        mod.remove_binding("n1", "alpha")
        assert mod.bindings == []

    def test_remove_nonexistent_is_noop(self) -> None:
        mod = UniformModulator()
        mod.remove_binding("n1", "alpha")  # should not raise

    def test_replace_all(self) -> None:
        mod = UniformModulator()
        mod.add_binding(ModulationBinding(node="n1", param="alpha", source="energy"))
        new = [
            ModulationBinding(node="n2", param="beta", source="valence"),
            ModulationBinding(node="n3", param="gamma", source="arousal"),
        ]
        mod.replace_all(new)
        assert len(mod.bindings) == 2
        sources = {b.source for b in mod.bindings}
        assert sources == {"valence", "arousal"}


class TestTick:
    def test_basic_tick(self) -> None:
        mod = UniformModulator()
        mod.add_binding(ModulationBinding(node="n1", param="alpha", source="energy", smoothing=0.0))
        result = mod.tick({"energy": 0.5})
        assert result == {("n1", "alpha"): 0.5}

    def test_scale_and_offset(self) -> None:
        mod = UniformModulator()
        mod.add_binding(
            ModulationBinding(
                node="n1", param="alpha", source="energy", scale=2.0, offset=0.1, smoothing=0.0
            )
        )
        result = mod.tick({"energy": 0.5})
        assert result[("n1", "alpha")] == 2.0 * 0.5 + 0.1

    def test_smoothing_pulls_toward_target(self) -> None:
        mod = UniformModulator()
        mod.add_binding(ModulationBinding(node="n1", param="alpha", source="energy", smoothing=0.8))
        # First tick: no previous, uses target directly.
        r1 = mod.tick({"energy": 1.0})
        assert r1[("n1", "alpha")] == 1.0
        # Second tick with new value: should be smoothed between 1.0 and 0.0.
        r2 = mod.tick({"energy": 0.0})
        expected = 0.8 * 1.0 + 0.2 * 0.0
        assert abs(r2[("n1", "alpha")] - expected) < 1e-9

    def test_missing_signal_produces_no_update(self) -> None:
        mod = UniformModulator()
        mod.add_binding(ModulationBinding(node="n1", param="alpha", source="energy", smoothing=0.0))
        result = mod.tick({"valence": 0.5})  # "energy" not present
        assert ("n1", "alpha") not in result

    def test_replace_all_clears_smoothed_state(self) -> None:
        mod = UniformModulator()
        b = ModulationBinding(node="n1", param="alpha", source="energy", smoothing=0.8)
        mod.add_binding(b)
        mod.tick({"energy": 1.0})
        # Replace all — smoothed state should be cleared.
        mod.replace_all([b])
        r = mod.tick({"energy": 0.0})
        # No previous smoothed value, so target directly.
        assert r[("n1", "alpha")] == 0.0
