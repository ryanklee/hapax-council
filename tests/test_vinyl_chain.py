"""Tests for VinylChainCapability — Mode D granular wash (DMCA-defeat)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from agents.hapax_daimonion.vinyl_chain import (
    DIMENSIONS,
    MODE_D_SCENE,
    VINYL_CHAIN_AFFORDANCES,
    VINYL_CHAIN_RECORDS,
    VinylChainCapability,
)
from shared.impingement import Impingement, ImpingementType


def _impingement() -> Impingement:
    return Impingement(
        timestamp=time.time(),
        source="vinyl_deck",
        type=ImpingementType.STATISTICAL_DEVIATION,
        strength=0.7,
        content={"metric": "vinyl_modulation"},
    )


class TestDimensionsShape:
    def test_nine_dimensions(self) -> None:
        assert len(DIMENSIONS) == 9

    def test_all_prefixed(self) -> None:
        for name in DIMENSIONS:
            assert name.startswith("vinyl_source."), name

    def test_expected_nine_dims_present(self) -> None:
        expected = {
            "vinyl_source.position_drift",
            "vinyl_source.spray",
            "vinyl_source.grain_size",
            "vinyl_source.density",
            "vinyl_source.pitch_displacement",
            "vinyl_source.harmonic_richness",
            "vinyl_source.spectral_skew",
            "vinyl_source.stereo_width",
            "vinyl_source.decay_tail",
        }
        assert set(DIMENSIONS.keys()) == expected

    def test_each_dim_has_at_least_one_cc_mapping(self) -> None:
        """Permits TBD CCs in the research doc — dim drops to 0 mappings
        only if ALL its CCs are marked None. We assert non-zero so no
        dim is ever a complete no-op."""
        for name, dim in DIMENSIONS.items():
            assert len(dim.cc_mappings) >= 1, f"{name} has zero mappings"


class TestGovernanceRisk:
    def test_all_records_medium_risk(self) -> None:
        for r in VINYL_CHAIN_RECORDS:
            assert r.operational.monetization_risk == "medium"
            assert r.operational.risk_reason
            assert "programme opt-in" in r.operational.risk_reason.lower()

    def test_affordance_signature_includes_mode_d(self) -> None:
        assert "mode_d_granular_wash" in VINYL_CHAIN_AFFORDANCES


class TestModeDScene:
    def test_mode_d_scene_includes_grains_on(self) -> None:
        cc_values = {cc: val for cc, val, _ in MODE_D_SCENE}
        assert cc_values[11] >= 100, "Grains volume must be engaged in Mode D"
        assert cc_values[40] >= 120, "Mix must be near fully wet in Mode D"
        assert cc_values[94] > 0, "Shimmer must be engaged in Mode D (voice forbids)"

    def test_mode_d_scene_inverts_voice_base(self) -> None:
        """The load-bearing governance distinction — voice sets grains=0,
        mix=50; Mode D inverts both."""
        from agents.hapax_daimonion.vocal_chain import DIMENSIONS as VOICE_DIMS  # noqa

        mode_d_grains = {cc: val for cc, val, _ in MODE_D_SCENE}[11]
        # Voice base sets CC 11 = 0 (scripts/evil-pet-configure-base.py BASE_SCENE)
        # Voice base sets CC 40 = 95 (Mix 75% wet per recent operator tuning)
        # We only assert the Mode D direction here.
        assert mode_d_grains >= 100


class TestModeDLifecycle:
    def test_init_mode_d_inactive(self) -> None:
        cap = VinylChainCapability(midi_output=MagicMock())
        assert cap.mode_d_active is False

    def test_activate_mode_d_writes_scene(self) -> None:
        midi = MagicMock()
        cap = VinylChainCapability(midi_output=midi)
        cap.activate_mode_d()
        assert cap.mode_d_active is True
        # 14 CCs in the scene; each sent once
        assert midi.send_cc.call_count == len(MODE_D_SCENE)

    def test_dimension_activation_noop_without_mode_d(self) -> None:
        """Safety: dimension writes ignored until Mode D is explicitly on,
        so an accidental impingement can't wash vinyl through the
        granular engine."""
        midi = MagicMock()
        cap = VinylChainCapability(midi_output=midi)
        cap.activate_dimension("vinyl_source.spray", _impingement(), 0.8)
        assert cap.get_dimension_level("vinyl_source.spray") == 0.0
        midi.send_cc.assert_not_called()

    def test_dimension_activation_works_after_mode_d(self) -> None:
        midi = MagicMock()
        cap = VinylChainCapability(midi_output=midi)
        cap.activate_mode_d()
        midi.reset_mock()
        cap.activate_dimension("vinyl_source.spray", _impingement(), 0.8)
        assert cap.get_dimension_level("vinyl_source.spray") == pytest.approx(0.8)
        assert midi.send_cc.call_count >= 1

    def test_deactivate_mode_d_resets_state(self) -> None:
        midi = MagicMock()
        cap = VinylChainCapability(midi_output=midi)
        cap.activate_mode_d()
        cap.activate_dimension("vinyl_source.spray", _impingement(), 0.8)
        cap.deactivate_mode_d()
        assert cap.mode_d_active is False
        assert cap.activation_level == 0.0
        assert cap.get_dimension_level("vinyl_source.spray") == 0.0

    def test_decay_noop_when_mode_d_off(self) -> None:
        midi = MagicMock()
        cap = VinylChainCapability(midi_output=midi)
        cap.decay(elapsed_s=5.0)
        midi.send_cc.assert_not_called()


class TestCCMapInvariants:
    def test_no_within_device_cc_collision_across_dimensions(self) -> None:
        """Same invariant as vocal_chain: one CC per (device, dim).
        Cross-chain collisions with vocal_chain are acceptable because
        Mode D and voice can never be active simultaneously on Evil Pet
        — Mode D takes the device via activate_mode_d()."""
        ownership: dict[tuple[str, int], str] = {}
        for dim in DIMENSIONS.values():
            for m in dim.cc_mappings:
                key = (m.device, m.cc)
                assert key not in ownership or ownership[key] == dim.name, (
                    f"within-device CC collision: {dim.name} vs {ownership[key]} "
                    f"on {m.device} CC{m.cc}"
                )
                ownership[key] = dim.name
