"""Tests for the Stream Deck vinyl rate preset handler (task #142, PR C)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.stream_deck.commands.vinyl import (
    VINYL_RATE_COMMAND,
    VinylRatePresetError,
    handle_vinyl_rate_preset,
    resolve_rate,
)

# ── resolve_rate: preset math ──────────────────────────────────────────────


class TestResolveRate:
    def test_45_on_33(self):
        assert resolve_rate("45-on-33") == pytest.approx(0.741)

    def test_33_is_unit(self):
        assert resolve_rate("33") == pytest.approx(1.0)

    def test_45_is_unit(self):
        assert resolve_rate("45") == pytest.approx(1.0)

    def test_custom_valid(self):
        assert resolve_rate("custom:0.9") == pytest.approx(0.9)

    def test_custom_at_lower_bound(self):
        assert resolve_rate("custom:0.25") == pytest.approx(0.25)

    def test_custom_at_upper_bound(self):
        assert resolve_rate("custom:2.0") == pytest.approx(2.0)

    def test_custom_strips_whitespace(self):
        assert resolve_rate("custom:  0.9  ") == pytest.approx(0.9)

    def test_custom_above_bound_rejected(self):
        with pytest.raises(VinylRatePresetError, match="outside bounds"):
            resolve_rate("custom:5.0")

    def test_custom_below_bound_rejected(self):
        with pytest.raises(VinylRatePresetError, match="outside bounds"):
            resolve_rate("custom:0.1")

    def test_custom_malformed_float_rejected(self):
        with pytest.raises(VinylRatePresetError, match="not a float"):
            resolve_rate("custom:not-a-number")

    def test_unknown_preset_rejected(self):
        with pytest.raises(VinylRatePresetError, match="unknown vinyl preset"):
            resolve_rate("78")

    def test_empty_preset_rejected(self):
        with pytest.raises(VinylRatePresetError, match="non-empty"):
            resolve_rate("")


# ── handle_vinyl_rate_preset: SHM write ────────────────────────────────────


class TestHandler:
    def test_handler_writes_45_on_33_rate(self, tmp_path: Path):
        target = tmp_path / "vinyl-playback-rate.txt"
        rate = handle_vinyl_rate_preset({"preset": "45-on-33"}, rate_file=target)
        assert rate == pytest.approx(0.741)
        assert target.read_text().strip() == "0.741000"

    def test_handler_writes_33_rate(self, tmp_path: Path):
        target = tmp_path / "vinyl-playback-rate.txt"
        rate = handle_vinyl_rate_preset({"preset": "33"}, rate_file=target)
        assert rate == pytest.approx(1.0)
        assert target.read_text().strip() == "1.000000"

    def test_handler_writes_45_rate(self, tmp_path: Path):
        target = tmp_path / "vinyl-playback-rate.txt"
        rate = handle_vinyl_rate_preset({"preset": "45"}, rate_file=target)
        assert rate == pytest.approx(1.0)
        assert target.read_text().strip() == "1.000000"

    def test_handler_writes_custom_rate(self, tmp_path: Path):
        target = tmp_path / "vinyl-playback-rate.txt"
        rate = handle_vinyl_rate_preset({"preset": "custom:0.9"}, rate_file=target)
        assert rate == pytest.approx(0.9)
        assert target.read_text().strip() == "0.900000"

    def test_handler_rejects_out_of_range_custom(self, tmp_path: Path):
        target = tmp_path / "vinyl-playback-rate.txt"
        with pytest.raises(VinylRatePresetError, match="outside bounds"):
            handle_vinyl_rate_preset({"preset": "custom:5.0"}, rate_file=target)
        assert not target.exists(), "rejection must leave the SHM rate untouched"

    def test_handler_rejects_malformed_custom(self, tmp_path: Path):
        target = tmp_path / "vinyl-playback-rate.txt"
        with pytest.raises(VinylRatePresetError, match="not a float"):
            handle_vinyl_rate_preset({"preset": "custom:NaN-like"}, rate_file=target)
        # float("NaN-like") raises, handler never writes.
        assert not target.exists()

    def test_handler_rejects_unknown_preset(self, tmp_path: Path):
        target = tmp_path / "vinyl-playback-rate.txt"
        with pytest.raises(VinylRatePresetError, match="unknown vinyl preset"):
            handle_vinyl_rate_preset({"preset": "78-rpm"}, rate_file=target)
        assert not target.exists()

    def test_handler_rejects_missing_preset_arg(self, tmp_path: Path):
        target = tmp_path / "vinyl-playback-rate.txt"
        with pytest.raises(VinylRatePresetError, match="requires 'preset'"):
            handle_vinyl_rate_preset({}, rate_file=target)
        assert not target.exists()

    def test_handler_rejects_non_string_preset(self, tmp_path: Path):
        target = tmp_path / "vinyl-playback-rate.txt"
        with pytest.raises(VinylRatePresetError, match="requires 'preset'"):
            handle_vinyl_rate_preset({"preset": 45}, rate_file=target)
        assert not target.exists()

    def test_rejection_preserves_prior_rate(self, tmp_path: Path):
        """A rejected preset must not stomp an already-written rate."""
        target = tmp_path / "vinyl-playback-rate.txt"
        handle_vinyl_rate_preset({"preset": "45-on-33"}, rate_file=target)
        prior = target.read_text()
        with pytest.raises(VinylRatePresetError):
            handle_vinyl_rate_preset({"preset": "custom:99"}, rate_file=target)
        assert target.read_text() == prior, "prior rate must be retained on rejection"

    def test_handler_overwrites_prior_rate(self, tmp_path: Path):
        """Two valid dispatches in sequence: the second rate wins."""
        target = tmp_path / "vinyl-playback-rate.txt"
        handle_vinyl_rate_preset({"preset": "45-on-33"}, rate_file=target)
        handle_vinyl_rate_preset({"preset": "33"}, rate_file=target)
        assert target.read_text().strip() == "1.000000"

    def test_handler_creates_parent_directory(self, tmp_path: Path):
        """If /dev/shm/hapax-compositor doesn't yet exist, create it."""
        target = tmp_path / "nested" / "subdir" / "vinyl-playback-rate.txt"
        handle_vinyl_rate_preset({"preset": "33"}, rate_file=target)
        assert target.exists()
        assert target.read_text().strip() == "1.000000"


# ── Command name invariant ─────────────────────────────────────────────────


def test_command_name_matches_manifest():
    """The #140 manifest + #141 KDEConnect grammar pin this exact string."""
    assert VINYL_RATE_COMMAND == "audio.vinyl.rate_preset"
