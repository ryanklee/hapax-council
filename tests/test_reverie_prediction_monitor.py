"""tests/test_reverie_prediction_monitor.py — P7 uniforms-freshness watchdog.

Minimal coverage for the new P7 prediction added in the delta PR-2
follow-up. Does not backfill tests for P1–P6; those predate this work.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import patch

from agents import reverie_prediction_monitor as monitor


def _patch_uniforms(path: Path):
    """Context helper that points UNIFORMS_FILE at tmp_path."""
    return patch.object(monitor, "UNIFORMS_FILE", path)


class TestP7UniformsFreshness:
    def test_fresh_file_reports_healthy(self, tmp_path: Path) -> None:
        path = tmp_path / "uniforms.json"
        path.write_text("{}", encoding="utf-8")
        with _patch_uniforms(path):
            result = monitor.p7_uniforms_freshness()
        assert result.name == "P7_uniforms_freshness"
        assert result.healthy is True
        assert result.alert is None
        assert result.actual < monitor._P7_WARN_AGE_S

    def test_warning_window_is_healthy_but_not_alerting(self, tmp_path: Path) -> None:
        path = tmp_path / "uniforms.json"
        path.write_text("{}", encoding="utf-8")
        warn_mtime = time.time() - (monitor._P7_WARN_AGE_S + 5)
        os.utime(path, (warn_mtime, warn_mtime))
        with _patch_uniforms(path):
            result = monitor.p7_uniforms_freshness()
        assert result.healthy is True
        assert result.alert is None
        assert result.actual >= monitor._P7_WARN_AGE_S
        assert result.actual < monitor._P7_CRIT_AGE_S

    def test_critical_age_reports_unhealthy_with_alert(self, tmp_path: Path) -> None:
        path = tmp_path / "uniforms.json"
        path.write_text("{}", encoding="utf-8")
        crit_mtime = time.time() - (monitor._P7_CRIT_AGE_S + 10)
        os.utime(path, (crit_mtime, crit_mtime))
        with _patch_uniforms(path):
            result = monitor.p7_uniforms_freshness()
        assert result.healthy is False
        assert result.alert is not None
        assert "critical" in result.alert
        assert result.actual >= monitor._P7_CRIT_AGE_S

    def test_missing_file_is_unhealthy(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.json"
        with _patch_uniforms(path):
            result = monitor.p7_uniforms_freshness()
        assert result.healthy is False
        assert result.alert is not None
        assert "missing" in result.alert
        assert result.actual == -1.0

    def test_explicit_now_override_lets_us_compute_age_deterministically(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "uniforms.json"
        path.write_text("{}", encoding="utf-8")
        mtime = 1_000_000.0
        os.utime(path, (mtime, mtime))
        with _patch_uniforms(path):
            result = monitor.p7_uniforms_freshness(now=1_000_000.0 + 45.0)
        assert result.healthy is True
        assert result.alert is None
        assert result.actual == 45.0

    def test_sample_includes_p7(self, tmp_path: Path) -> None:
        """p7 must land in sample() output alongside the other six."""
        path = tmp_path / "uniforms.json"
        path.write_text("{}", encoding="utf-8")
        predictions_shm = tmp_path / "predictions.json"
        predictions_jsonl = tmp_path / "predictions.jsonl"
        with (
            _patch_uniforms(path),
            patch.object(monitor, "PREDICTIONS_SHM", predictions_shm),
            patch.object(monitor, "PREDICTIONS_JSONL", predictions_jsonl),
            patch.object(monitor, "_query_chronicle", return_value=[]),
            patch.object(monitor, "_load_activation_state", return_value={}),
            patch.object(monitor, "_load_associations", return_value={}),
            patch.object(monitor, "_load_perception", return_value={}),
        ):
            result = monitor.sample()

        prediction_names = [p.name for p in result.predictions]
        assert "P7_uniforms_freshness" in prediction_names
        assert len(result.predictions) == 7
