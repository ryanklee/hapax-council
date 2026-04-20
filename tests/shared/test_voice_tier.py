"""Tests for shared.voice_tier — 7-tier voice transformation primitive."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from shared.voice_tier import (
    TIER_CATALOG,
    TIER_NAMES,
    TierProfile,
    VoiceTier,
    apply_tier,
    profile_for,
    tier_from_name,
)


class TestTierEnum:
    def test_seven_tiers(self) -> None:
        assert len(list(VoiceTier)) == 7

    def test_ordinal(self) -> None:
        assert VoiceTier.UNADORNED < VoiceTier.RADIO < VoiceTier.BROADCAST_GHOST
        assert VoiceTier.BROADCAST_GHOST < VoiceTier.MEMORY < VoiceTier.UNDERWATER
        assert VoiceTier.UNDERWATER < VoiceTier.GRANULAR_WASH < VoiceTier.OBLITERATED

    def test_distance(self) -> None:
        assert abs(VoiceTier.RADIO - VoiceTier.UNADORNED) == 1
        assert abs(VoiceTier.OBLITERATED - VoiceTier.UNADORNED) == 6


class TestCatalogShape:
    def test_catalog_covers_all_tiers(self) -> None:
        assert set(TIER_CATALOG.keys()) == set(VoiceTier)

    def test_tier_names_covers_all(self) -> None:
        assert set(TIER_NAMES.keys()) == set(VoiceTier)

    def test_profile_shape(self) -> None:
        for profile in TIER_CATALOG.values():
            assert isinstance(profile, TierProfile)
            assert profile.tier in VoiceTier
            assert 0.0 <= profile.intelligibility_floor <= 1.0
            assert set(profile.dimension_vector.keys()) == {
                "intensity",
                "tension",
                "diffusion",
                "degradation",
                "depth",
                "pitch_displacement",
                "temporal_distortion",
                "spectral_color",
                "coherence",
            }
            for v in profile.dimension_vector.values():
                assert 0.0 <= v <= 1.0


class TestIntelligibilityMonotonic:
    def test_floor_decreases_with_tier(self) -> None:
        """Moving up the tier ladder never increases intelligibility.

        T0 = 1.0, T6 = 0.0; intermediate steps must be monotonically
        non-increasing. This is the load-bearing invariant for the
        budget system — a consumer that assumed "higher tier = lower
        intelligibility" must never be contradicted.
        """
        tiers_ordered = sorted(TIER_CATALOG.values(), key=lambda p: p.tier.value)
        floors = [p.intelligibility_floor for p in tiers_ordered]
        assert floors == sorted(floors, reverse=True)

    def test_unadorned_is_full_intelligibility(self) -> None:
        assert TIER_CATALOG[VoiceTier.UNADORNED].intelligibility_floor == 1.0

    def test_obliterated_is_zero_intelligibility(self) -> None:
        assert TIER_CATALOG[VoiceTier.OBLITERATED].intelligibility_floor == 0.0


class TestMutexAndDurationCap:
    def test_granular_tiers_claim_engine_mutex(self) -> None:
        for tier in (VoiceTier.GRANULAR_WASH, VoiceTier.OBLITERATED):
            assert "evil_pet_granular_engine" in TIER_CATALOG[tier].mutex_groups

    def test_non_granular_tiers_have_no_mutex(self) -> None:
        for tier in (
            VoiceTier.UNADORNED,
            VoiceTier.RADIO,
            VoiceTier.BROADCAST_GHOST,
            VoiceTier.MEMORY,
            VoiceTier.UNDERWATER,
        ):
            assert TIER_CATALOG[tier].mutex_groups == frozenset()

    def test_obliterated_has_duration_cap(self) -> None:
        assert TIER_CATALOG[VoiceTier.OBLITERATED].max_duration_s == 15.0

    def test_non_obliterated_no_duration_cap(self) -> None:
        for tier in VoiceTier:
            if tier != VoiceTier.OBLITERATED:
                assert TIER_CATALOG[tier].max_duration_s is None


class TestProfileFor:
    def test_returns_catalog_entry(self) -> None:
        assert profile_for(VoiceTier.MEMORY) is TIER_CATALOG[VoiceTier.MEMORY]

    def test_raises_on_unknown(self) -> None:
        with pytest.raises(KeyError):
            profile_for(9999)  # type: ignore[arg-type]


class TestApplyTier:
    def test_applies_all_nine_dims(self) -> None:
        chain = MagicMock()
        apply_tier(VoiceTier.MEMORY, chain)
        assert chain.activate_dimension.call_count == 9
        # All keys should be prefixed vocal_chain.* at the call site.
        names = [call.args[0] for call in chain.activate_dimension.call_args_list]
        for name in names:
            assert name.startswith("vocal_chain.")

    def test_emits_cc_overrides_when_midi_provided(self) -> None:
        chain = MagicMock()
        midi = MagicMock()
        apply_tier(VoiceTier.GRANULAR_WASH, chain, midi_output=midi)
        # T5 has 2 CC overrides for granular engine engagement
        assert midi.send_cc.call_count == 2

    def test_skips_cc_overrides_without_midi(self) -> None:
        chain = MagicMock()
        apply_tier(VoiceTier.OBLITERATED, chain, midi_output=None)
        # 9 dim activations, 0 CC writes (no midi)
        assert chain.activate_dimension.call_count == 9

    def test_unadorned_zeros_all_dims(self) -> None:
        chain = MagicMock()
        apply_tier(VoiceTier.UNADORNED, chain)
        for call in chain.activate_dimension.call_args_list:
            # Third positional or 'level' kwarg
            level = call.kwargs.get("level", call.args[2] if len(call.args) > 2 else None)
            assert level == 0.0


class TestTierFromName:
    def test_canonical_names(self) -> None:
        assert tier_from_name("unadorned") == VoiceTier.UNADORNED
        assert tier_from_name("radio") == VoiceTier.RADIO
        assert tier_from_name("broadcast-ghost") == VoiceTier.BROADCAST_GHOST
        assert tier_from_name("memory") == VoiceTier.MEMORY
        assert tier_from_name("underwater") == VoiceTier.UNDERWATER
        assert tier_from_name("granular-wash") == VoiceTier.GRANULAR_WASH
        assert tier_from_name("obliterated") == VoiceTier.OBLITERATED

    def test_tN_aliases(self) -> None:
        assert tier_from_name("t0") == VoiceTier.UNADORNED
        assert tier_from_name("T6") == VoiceTier.OBLITERATED
        assert tier_from_name("t3") == VoiceTier.MEMORY

    def test_underscore_variant(self) -> None:
        assert tier_from_name("broadcast_ghost") == VoiceTier.BROADCAST_GHOST
        assert tier_from_name("granular_wash") == VoiceTier.GRANULAR_WASH

    def test_case_insensitive(self) -> None:
        assert tier_from_name("MEMORY") == VoiceTier.MEMORY
        assert tier_from_name("Radio") == VoiceTier.RADIO

    def test_aliases(self) -> None:
        assert tier_from_name("clear") == VoiceTier.UNADORNED
        assert tier_from_name("max") == VoiceTier.OBLITERATED
        assert tier_from_name("full") == VoiceTier.OBLITERATED
        assert tier_from_name("granular") == VoiceTier.GRANULAR_WASH

    def test_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown voice tier"):
            tier_from_name("loud")
