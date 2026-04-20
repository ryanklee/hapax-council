"""Tests for agents.hapax_daimonion.voice_path — tier → path selection."""

from __future__ import annotations

from pathlib import Path

from agents.hapax_daimonion.voice_path import (
    PathConfig,
    VoicePath,
    all_paths,
    describe_path,
    load_paths,
    requires_granular_engine,
    select_voice_path,
)
from shared.voice_tier import VoiceTier


class TestLoadPaths:
    def test_default_config_parses(self) -> None:
        paths = load_paths()
        assert set(paths.keys()) == set(VoicePath)

    def test_dry_path_has_no_dsp(self) -> None:
        paths = load_paths()
        dry = paths[VoicePath.DRY]
        assert dry.via_evil_pet is False
        assert dry.via_s4 is False

    def test_evil_pet_path_engages_engine(self) -> None:
        paths = load_paths()
        ep = paths[VoicePath.EVIL_PET]
        assert ep.via_evil_pet is True
        assert ep.via_s4 is False

    def test_radio_path_s4_direct(self) -> None:
        paths = load_paths()
        radio = paths[VoicePath.RADIO]
        assert radio.via_evil_pet is False
        assert radio.via_s4 is True

    def test_both_path_parallel(self) -> None:
        paths = load_paths()
        both = paths[VoicePath.BOTH]
        assert both.via_evil_pet is True
        assert both.via_s4 is True


class TestSelectVoicePath:
    def test_unadorned_is_dry(self) -> None:
        assert select_voice_path(VoiceTier.UNADORNED) == VoicePath.DRY

    def test_radio_tier_picks_s4_direct(self) -> None:
        assert select_voice_path(VoiceTier.RADIO) == VoicePath.RADIO

    def test_broadcast_ghost_through_evil_pet(self) -> None:
        assert select_voice_path(VoiceTier.BROADCAST_GHOST) == VoicePath.EVIL_PET

    def test_memory_through_evil_pet(self) -> None:
        assert select_voice_path(VoiceTier.MEMORY) == VoicePath.EVIL_PET

    def test_underwater_through_evil_pet(self) -> None:
        assert select_voice_path(VoiceTier.UNDERWATER) == VoicePath.EVIL_PET

    def test_granular_wash_through_evil_pet(self) -> None:
        """T5 needs the granular engine — Evil Pet path."""
        assert select_voice_path(VoiceTier.GRANULAR_WASH) == VoicePath.EVIL_PET

    def test_obliterated_through_evil_pet(self) -> None:
        assert select_voice_path(VoiceTier.OBLITERATED) == VoicePath.EVIL_PET


class TestCustomConfig:
    def test_override_with_injected_paths(self, tmp_path: Path) -> None:
        """Callers can pass a prebuilt paths dict for test isolation."""
        custom: dict[VoicePath, PathConfig] = {
            VoicePath.DRY: PathConfig(
                path=VoicePath.DRY,
                description="test",
                sink="test-sink",
                via_evil_pet=False,
                via_s4=False,
                default_for_tiers=frozenset({"memory"}),  # remap
            ),
            VoicePath.EVIL_PET: PathConfig(
                path=VoicePath.EVIL_PET,
                description="",
                sink="",
                via_evil_pet=True,
                via_s4=False,
                default_for_tiers=frozenset(),
            ),
            VoicePath.RADIO: PathConfig(
                path=VoicePath.RADIO,
                description="",
                sink="",
                via_evil_pet=False,
                via_s4=True,
                default_for_tiers=frozenset(),
            ),
            VoicePath.BOTH: PathConfig(
                path=VoicePath.BOTH,
                description="",
                sink="",
                via_evil_pet=True,
                via_s4=True,
                default_for_tiers=frozenset(),
            ),
        }
        # With custom map where only 'memory' is claimed by DRY, memory
        # should pick DRY instead of EVIL_PET.
        assert select_voice_path(VoiceTier.MEMORY, paths=custom) == VoicePath.DRY

    def test_unknown_tier_claim_falls_back_to_dry(self, tmp_path: Path) -> None:
        """Unclaimed tier → DRY (safest intelligibility choice)."""
        custom: dict[VoicePath, PathConfig] = {
            vp: PathConfig(
                path=vp,
                description="",
                sink="",
                via_evil_pet=False,
                via_s4=False,
                default_for_tiers=frozenset(),
            )
            for vp in VoicePath
        }
        # No path claims any tier.
        assert select_voice_path(VoiceTier.MEMORY, paths=custom) == VoicePath.DRY


class TestRequiresGranularEngine:
    def test_dry_false(self) -> None:
        assert requires_granular_engine(VoicePath.DRY) is False

    def test_radio_false(self) -> None:
        assert requires_granular_engine(VoicePath.RADIO) is False

    def test_evil_pet_true(self) -> None:
        assert requires_granular_engine(VoicePath.EVIL_PET) is True

    def test_both_true(self) -> None:
        """BOTH routes audio through Evil Pet + S-4 in parallel."""
        assert requires_granular_engine(VoicePath.BOTH) is True


class TestDescribe:
    def test_describe_dry(self) -> None:
        desc = describe_path(VoicePath.DRY)
        assert "ryzen" in desc.lower() or "analog" in desc.lower()

    def test_all_paths_enumerated(self) -> None:
        paths = all_paths()
        assert set(paths) == set(VoicePath)
