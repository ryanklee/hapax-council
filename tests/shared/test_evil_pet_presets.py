"""Tests for shared.evil_pet_presets — CC-burst preset pack (#194)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from shared.evil_pet_presets import (
    PRESETS,
    EvilPetPreset,
    get_preset,
    list_presets,
    recall_preset,
)
from shared.voice_tier import VoiceTier


class TestPresetCoverage:
    def test_has_preset_per_tier(self) -> None:
        names = list_presets()
        for tier in VoiceTier:
            expected = f"hapax-{tier.name.lower().replace('_', '-')}"
            assert expected in names, f"missing preset: {expected}"

    def test_has_mode_d(self) -> None:
        assert "hapax-mode-d" in list_presets()

    def test_has_bypass(self) -> None:
        assert "hapax-bypass" in list_presets()

    def test_thirteen_presets_total(self) -> None:
        # 7 tiers + Mode D + bypass + 4 routing-aware (Phase 2) = 13.
        assert len(PRESETS) == 13


class TestPresetShape:
    def test_each_has_name_and_description(self) -> None:
        for preset in PRESETS.values():
            assert preset.name
            assert preset.description

    def test_each_has_nonempty_ccs(self) -> None:
        for preset in PRESETS.values():
            assert preset.ccs, f"preset {preset.name!r} has empty ccs"

    def test_cc_values_in_midi_range(self) -> None:
        for preset in PRESETS.values():
            for cc, value in preset.ccs.items():
                assert 0 <= cc <= 127, f"{preset.name}: CC {cc} out of range"
                assert 0 <= value <= 127, f"{preset.name}: value {value} out of range"

    def test_bypass_grains_off(self) -> None:
        """Bypass preset must set CC 11 (grains volume) to 0."""
        bypass = get_preset("hapax-bypass")
        assert bypass.ccs[11] == 0

    def test_mode_d_grains_on(self) -> None:
        """Mode D preset must engage grains (CC 11 high)."""
        mode_d = get_preset("hapax-mode-d")
        assert mode_d.ccs[11] >= 100  # 94%+ per Smitelli 2020 floor

    def test_mode_d_shimmer_on(self) -> None:
        mode_d = get_preset("hapax-mode-d")
        assert mode_d.ccs[94] > 0

    def test_mode_d_full_wet_mix(self) -> None:
        mode_d = get_preset("hapax-mode-d")
        assert mode_d.ccs[40] == 127


class TestTierPresets:
    def test_t0_inherits_base_scene(self) -> None:
        """UNADORNED overrides nothing — pure base scene."""
        preset = get_preset("hapax-unadorned")
        assert preset.ccs[11] == 0  # grains off (base scene default)
        assert preset.ccs[7] == 127  # volume max

    def test_t5_engages_granular_engine(self) -> None:
        preset = get_preset("hapax-granular-wash")
        # T5 cc_override sets CC 11 = 90 + CC 40 = 110.
        assert preset.ccs[11] == 90
        assert preset.ccs[40] == 110

    def test_t6_full_granular(self) -> None:
        preset = get_preset("hapax-obliterated")
        assert preset.ccs[11] == 120
        assert preset.ccs[40] == 127
        assert preset.ccs[94] == 60  # shimmer on


class TestGetPreset:
    def test_returns_named(self) -> None:
        preset = get_preset("hapax-bypass")
        assert preset.name == "hapax-bypass"

    def test_raises_on_unknown(self) -> None:
        with pytest.raises(KeyError):
            get_preset("hapax-nonexistent")


class TestRecallPreset:
    def test_emits_all_ccs(self) -> None:
        midi = MagicMock()
        n = recall_preset("hapax-bypass", midi, delay_s=0.0)
        preset = get_preset("hapax-bypass")
        assert n == len(preset.ccs)
        assert midi.send_cc.call_count == len(preset.ccs)

    def test_emits_on_default_channel(self) -> None:
        midi = MagicMock()
        recall_preset("hapax-bypass", midi, delay_s=0.0)
        for call in midi.send_cc.call_args_list:
            assert call.kwargs["channel"] == 0  # EVIL_PET_MIDI_CHANNEL

    def test_custom_channel(self) -> None:
        midi = MagicMock()
        recall_preset("hapax-bypass", midi, channel=3, delay_s=0.0)
        for call in midi.send_cc.call_args_list:
            assert call.kwargs["channel"] == 3

    def test_tolerates_send_cc_failure(self) -> None:
        """A single bad send_cc doesn't abort the whole recall."""
        midi = MagicMock()
        midi.send_cc.side_effect = [RuntimeError("boom")] + [None] * 20
        # Use a small preset so MagicMock side_effect list covers it.
        preset = get_preset("hapax-bypass")
        # Shrink the preset's ccs list for this test by wrapping.
        n = recall_preset("hapax-bypass", midi, delay_s=0.0)
        # One failed, rest succeeded.
        assert n == len(preset.ccs) - 1

    def test_raises_on_unknown_preset(self) -> None:
        with pytest.raises(KeyError):
            recall_preset("hapax-nonexistent", MagicMock(), delay_s=0.0)

    def test_verify_port_default_off_preserves_fire_and_log(self) -> None:
        """Default verify_port=False must NOT add the pre-burst ping."""
        midi = MagicMock()
        recall_preset("hapax-bypass", midi, delay_s=0.0)
        ccs = get_preset("hapax-bypass").ccs
        assert midi.send_cc.call_count == len(ccs)

    def test_verify_port_pings_before_burst(self) -> None:
        """D-24 §10.4: verify_port=True pings CC 0 / value 0 before burst."""
        midi = MagicMock()
        recall_preset("hapax-bypass", midi, delay_s=0.0, verify_port=True)
        first_call = midi.send_cc.call_args_list[0]
        assert first_call.kwargs.get("cc") == 0
        assert first_call.kwargs.get("value") == 0

    def test_verify_port_raises_on_ping_failure(self) -> None:
        """When verify_port=True and the port is dead, raise loudly instead
        of silently logging send_cc failures for every CC in the burst."""
        midi = MagicMock()
        midi.send_cc.side_effect = RuntimeError("port closed")
        with pytest.raises(RuntimeError, match="pre-burst port verify failed"):
            recall_preset("hapax-bypass", midi, delay_s=0.0, verify_port=True)
        # Burst was NOT attempted — only the ping fired.
        assert midi.send_cc.call_count == 1


class TestPresetObjectShape:
    def test_dataclass_frozen(self) -> None:
        """EvilPetPreset is immutable so shared-dict mutations are safe."""
        preset = EvilPetPreset(name="test", description="t", ccs={11: 0})
        with pytest.raises(Exception):
            preset.name = "other"  # type: ignore[misc]


# ── evilpet-s4-routing Phase 2: 4 routing-aware presets ──────────────


class TestRoutingAwarePresets:
    """Spec §7: hapax-sampler-wet, -bed-music, -drone-loop, -s4-companion."""

    NEW_PRESETS = (
        "hapax-sampler-wet",
        "hapax-bed-music",
        "hapax-drone-loop",
        "hapax-s4-companion",
    )

    def test_all_four_registered(self) -> None:
        names = set(list_presets())
        for name in self.NEW_PRESETS:
            assert name in names, f"missing routing-aware preset: {name}"

    def test_each_has_substantive_ccs(self) -> None:
        """Each new preset must carry a substantive CC map (at least
        the BASE_SCENE 16 entries plus its own overrides)."""
        for name in self.NEW_PRESETS:
            preset = get_preset(name)
            assert len(preset.ccs) >= 16, (
                f"{name} has only {len(preset.ccs)} CCs; expected ≥16 (BASE_SCENE + overrides)"
            )

    def test_each_has_descriptive_doc(self) -> None:
        for name in self.NEW_PRESETS:
            preset = get_preset(name)
            assert len(preset.description) > 30, (
                f"{name} description is too short ({len(preset.description)} chars)"
            )

    def test_sampler_wet_ccs(self) -> None:
        """hapax-sampler-wet: dense grains + sustained reverb tail."""
        preset = get_preset("hapax-sampler-wet")
        assert preset.ccs[11] == 100  # Grains volume
        assert preset.ccs[40] == 120  # Mix
        assert preset.ccs[91] == 60  # Reverb amount
        assert preset.ccs[93] == 70  # Reverb tail

    def test_bed_music_ccs(self) -> None:
        """hapax-bed-music: light grains, bright filter, balanced mix."""
        preset = get_preset("hapax-bed-music")
        assert preset.ccs[11] == 30
        assert preset.ccs[40] == 85
        assert preset.ccs[70] == 80  # Filter freq slightly bright

    def test_drone_loop_ccs(self) -> None:
        """hapax-drone-loop: full-wet, long tail, primary granular."""
        preset = get_preset("hapax-drone-loop")
        assert preset.ccs[11] == 110
        assert preset.ccs[40] == 127  # 100% wet
        assert preset.ccs[93] == 90

    def test_s4_companion_ccs(self) -> None:
        """hapax-s4-companion: secondary granular — must NOT dominate S-4."""
        preset = get_preset("hapax-s4-companion")
        assert preset.ccs[11] == 70
        assert preset.ccs[40] == 100
        # Spec §7 governance: must stay below sampler-wet (100) so the
        # S-4's Mosaic engine remains the primary granular voice.
        assert preset.ccs[11] < get_preset("hapax-sampler-wet").ccs[11], (
            "s4-companion grains volume must stay below sampler-wet to preserve S-4 primacy"
        )

    def test_all_new_presets_in_midi_range(self) -> None:
        """Belt-and-braces: every CC in every new preset must be 0..127."""
        for name in self.NEW_PRESETS:
            preset = get_preset(name)
            for cc, value in preset.ccs.items():
                assert 0 <= cc <= 127, f"{name}: CC {cc} out of range"
                assert 0 <= value <= 127, f"{name}: CC {cc} value {value} out of range"

    def test_recall_emits_all_four_new_presets(self) -> None:
        """Plan Task 2.6: recall_preset() must work for all 4 new presets
        without raising. Each must emit exactly its preset.ccs count."""
        for name in self.NEW_PRESETS:
            midi = MagicMock()
            n = recall_preset(name, midi, delay_s=0.0)
            preset = get_preset(name)
            assert n == len(preset.ccs), (
                f"{name} emitted {n} CCs but preset declares {len(preset.ccs)}"
            )
            assert midi.send_cc.call_count == len(preset.ccs)


# ── evilpet-s4-routing Phase 4: preset-recall observability ───────────


class TestRecallObservability:
    """recall_preset() emits Prometheus counters per preset name."""

    def _read_counter(self, name: str, **labels: str) -> float:
        from prometheus_client import REGISTRY

        v = REGISTRY.get_sample_value(name, labels=labels) or 0.0
        return float(v)

    def test_metric_module_constants_exist(self) -> None:
        """Counter handles must be importable for dashboards / scripts."""
        from shared.evil_pet_presets import (
            _METRICS_AVAILABLE,
            _preset_recall_ccs_total,
            _preset_recalls_total,
        )

        assert _METRICS_AVAILABLE is True
        assert _preset_recalls_total is not None
        assert _preset_recall_ccs_total is not None

    def test_recall_increments_recall_counter(self) -> None:
        """Each recall_preset call bumps hapax_evilpet_preset_recalls_total
        by 1, labelled with the preset name."""
        before = self._read_counter(
            "hapax_evilpet_preset_recalls_total",
            preset_name="hapax-bypass",
        )
        recall_preset("hapax-bypass", MagicMock(), delay_s=0.0)
        after = self._read_counter(
            "hapax_evilpet_preset_recalls_total",
            preset_name="hapax-bypass",
        )
        assert after - before == 1.0

    def test_recall_increments_cc_counter_by_ccs_emitted(self) -> None:
        """The CC counter advances by the number of CCs successfully sent
        — ties Prometheus telemetry to actual MIDI traffic."""
        preset = get_preset("hapax-sampler-wet")
        before = self._read_counter(
            "hapax_evilpet_preset_recall_ccs_total",
            preset_name="hapax-sampler-wet",
        )
        n = recall_preset("hapax-sampler-wet", MagicMock(), delay_s=0.0)
        after = self._read_counter(
            "hapax_evilpet_preset_recall_ccs_total",
            preset_name="hapax-sampler-wet",
        )
        assert n == len(preset.ccs)
        assert after - before == float(n)

    def test_recall_counter_label_per_preset(self) -> None:
        """Two different presets bump counters with separate labels."""
        before_a = self._read_counter(
            "hapax_evilpet_preset_recalls_total",
            preset_name="hapax-drone-loop",
        )
        before_b = self._read_counter(
            "hapax_evilpet_preset_recalls_total",
            preset_name="hapax-bed-music",
        )
        recall_preset("hapax-drone-loop", MagicMock(), delay_s=0.0)
        recall_preset("hapax-bed-music", MagicMock(), delay_s=0.0)
        after_a = self._read_counter(
            "hapax_evilpet_preset_recalls_total",
            preset_name="hapax-drone-loop",
        )
        after_b = self._read_counter(
            "hapax_evilpet_preset_recalls_total",
            preset_name="hapax-bed-music",
        )
        assert after_a - before_a == 1.0
        assert after_b - before_b == 1.0
