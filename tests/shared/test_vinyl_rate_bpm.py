"""Tests for the vinyl-rate BPM compensation helpers (task #142, PR B).

Pins the rate-compensated BPM math for the 45-on-33 preset (0.741×),
standard 33⅓ (1.0×), standard 45 (1.0×), and edge cases (zero rate,
negative rate, missing file, garbage file). ``compensate_bpm`` is the
numeric primitive and ``normalized_bpm_signal`` is the SHM-backed
helper tempo-reactive consumers import.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from shared import vinyl_rate
from shared.vinyl_rate import (
    compensate_bpm,
    normalized_bpm_signal,
)

# ── compensate_bpm: explicit rate arg ───────────────────────────────────────


class TestCompensateBpmExplicitRate:
    def test_45_on_33_raw_120_normalizes_to_162(self):
        """45 RPM disc on 33⅓ preset: rate 0.741, raw 120 → nominal ≈162."""
        nominal = compensate_bpm(120.0, rate=0.741)
        assert nominal == pytest.approx(161.94, abs=0.1)

    def test_33_at_unit_rate_is_identity(self):
        """33⅓ preset at standard rate: raw 120 → nominal 120."""
        assert compensate_bpm(120.0, rate=1.0) == pytest.approx(120.0)

    def test_45_at_unit_rate_is_identity(self):
        """45 preset at standard rate: raw 120 → nominal 120."""
        assert compensate_bpm(120.0, rate=1.0) == pytest.approx(120.0)

    def test_zero_rate_returns_observed_unchanged(self):
        """Guard: a zero rate cannot divide; pass the observed value through."""
        assert compensate_bpm(120.0, rate=0.0) == 120.0

    def test_negative_rate_returns_observed_unchanged(self):
        """Guard: a negative rate is nonsensical; pass the observed value through."""
        assert compensate_bpm(120.0, rate=-0.5) == 120.0


# ── normalized_bpm_signal: SHM-backed helper ────────────────────────────────


class TestNormalizedBpmSignal:
    def test_missing_file_returns_none(self, tmp_path: Path):
        """No BPM file present → no signal (consumer falls through)."""
        with patch.object(vinyl_rate, "_BPM_FILE", tmp_path / "missing.txt"):
            assert normalized_bpm_signal() is None

    def test_empty_file_returns_none(self, tmp_path: Path):
        bpm_file = tmp_path / "current-bpm.txt"
        bpm_file.write_text("")
        with patch.object(vinyl_rate, "_BPM_FILE", bpm_file):
            assert normalized_bpm_signal() is None

    def test_garbage_content_returns_none(self, tmp_path: Path):
        bpm_file = tmp_path / "current-bpm.txt"
        bpm_file.write_text("not-a-number")
        with patch.object(vinyl_rate, "_BPM_FILE", bpm_file):
            assert normalized_bpm_signal() is None

    def test_zero_bpm_returns_none(self, tmp_path: Path):
        """Zero raw BPM means no beat grid available — treat as no signal."""
        bpm_file = tmp_path / "current-bpm.txt"
        bpm_file.write_text("0.0")
        with patch.object(vinyl_rate, "_BPM_FILE", bpm_file):
            assert normalized_bpm_signal() is None

    def test_negative_bpm_returns_none(self, tmp_path: Path):
        bpm_file = tmp_path / "current-bpm.txt"
        bpm_file.write_text("-1.0")
        with patch.object(vinyl_rate, "_BPM_FILE", bpm_file):
            assert normalized_bpm_signal() is None

    def test_45_on_33_compensates(self, tmp_path: Path):
        """Full path: raw 120 BPM + rate 0.741 → nominal ≈162."""
        bpm_file = tmp_path / "current-bpm.txt"
        rate_file = tmp_path / "vinyl-playback-rate.txt"
        bpm_file.write_text("120")
        rate_file.write_text("0.741")
        with (
            patch.object(vinyl_rate, "_BPM_FILE", bpm_file),
            patch.object(vinyl_rate, "_RATE_FILE", rate_file),
            patch.object(vinyl_rate, "_LEGACY_BOOL_FILE", tmp_path / "legacy-absent.txt"),
        ):
            nominal = normalized_bpm_signal()
        assert nominal is not None
        assert nominal == pytest.approx(161.94, abs=0.1)

    def test_unit_rate_is_identity(self, tmp_path: Path):
        bpm_file = tmp_path / "current-bpm.txt"
        rate_file = tmp_path / "vinyl-playback-rate.txt"
        bpm_file.write_text("120")
        rate_file.write_text("1.0")
        with (
            patch.object(vinyl_rate, "_BPM_FILE", bpm_file),
            patch.object(vinyl_rate, "_RATE_FILE", rate_file),
            patch.object(vinyl_rate, "_LEGACY_BOOL_FILE", tmp_path / "legacy-absent.txt"),
        ):
            nominal = normalized_bpm_signal()
        assert nominal == pytest.approx(120.0)

    def test_whitespace_is_stripped(self, tmp_path: Path):
        bpm_file = tmp_path / "current-bpm.txt"
        rate_file = tmp_path / "vinyl-playback-rate.txt"
        bpm_file.write_text("  120.0\n")
        rate_file.write_text("1.0\n")
        with (
            patch.object(vinyl_rate, "_BPM_FILE", bpm_file),
            patch.object(vinyl_rate, "_RATE_FILE", rate_file),
            patch.object(vinyl_rate, "_LEGACY_BOOL_FILE", tmp_path / "legacy-absent.txt"),
        ):
            nominal = normalized_bpm_signal()
        assert nominal == pytest.approx(120.0)
