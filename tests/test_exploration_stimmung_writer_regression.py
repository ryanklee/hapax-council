"""Regression tests for the exploration stimmung writer stall.

REGRESSION-2 (2026-04-18 alpha smoketest):
`/dev/shm/hapax-exploration/stimmung.json` had not been written for ~22h
because the VLA's StimmungCollector was constructed with
`enable_exploration=False` on the mistaken assumption that a primary
writer existed elsewhere. No other daemon instantiated StimmungCollector,
so the writer was permanently dark.

These tests pin the contract that:

1. VLA instantiates its StimmungCollector and TemporalBandFormatter with
   exploration ENABLED - this guarantees the canonical component=stimmung
   and component=temporal_bands writers are live.
2. A stimmung writer that ticks produces a valid
   `hapax-exploration/stimmung.json` file.
3. The new health_monitor `check_exploration_writers` correctly detects
   stale and dead writers and recommends restarting the owning service.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

from agents.health_monitor.checks.exploration import (
    COMPONENT_OWNERS,
    DEAD_THRESHOLD_S,
    STALE_THRESHOLD_S,
    check_exploration_writers,
    emit_degraded_signal,
)
from agents.health_monitor.models import Status

if TYPE_CHECKING:
    import pytest


class TestVlaCanonicalWriter:
    """Guard: VLA must own the stimmung + temporal_bands exploration writers."""

    def test_vla_stimmung_collector_has_exploration_enabled(self) -> None:
        """If VLA silences exploration, nobody writes stimmung.json."""
        from agents.visual_layer_aggregator.aggregator import VisualLayerAggregator

        agg = VisualLayerAggregator()
        assert agg._stimmung_collector._exploration is not None, (
            "VLA's StimmungCollector must have enable_exploration=True. "
            "Flipping this to False revives the REGRESSION-2 stall: no other "
            "daemon instantiates StimmungCollector, so the canonical writer "
            "goes dark."
        )
        assert agg._stimmung_collector._exploration.component == "stimmung"

    def test_vla_temporal_formatter_has_exploration_enabled(self) -> None:
        from agents.visual_layer_aggregator.aggregator import VisualLayerAggregator

        agg = VisualLayerAggregator()
        assert agg._temporal_formatter._exploration is not None
        assert agg._temporal_formatter._exploration.component == "temporal_bands"


class TestStimmungWriterEndToEnd:
    """A stimmung tick with exploration enabled must land on disk."""

    def test_snapshot_writes_exploration_stimmung(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The writer is called by ExplorationTrackerBundle. Redirect by
        # monkeypatching the name it imports.
        from shared import exploration_tracker, exploration_writer
        from shared.stimmung import StimmungCollector

        def redirected(sig, shm_root=None):
            return exploration_writer.publish_exploration_signal(sig, shm_root=tmp_path)

        monkeypatch.setattr(exploration_tracker, "publish_exploration_signal", redirected)

        collector = StimmungCollector(enable_exploration=True)
        collector.update_health(healthy=10, total=10)
        collector.update_gpu(used_mb=1000, total_mb=10000)
        collector.update_engine(events_processed=100, actions_executed=100, errors=0, uptime_s=60)
        collector.update_perception(freshness_s=1.0, confidence=1.0)

        snap = collector.snapshot()
        assert snap is not None

        written = tmp_path / "hapax-exploration" / "stimmung.json"
        assert written.exists(), "StimmungCollector.snapshot() must publish stimmung.json"
        data = json.loads(written.read_text())
        assert data["component"] == "stimmung"
        assert "boredom_index" in data

    def test_snapshot_is_silent_when_exploration_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Control test: documents the failure mode that caused REGRESSION-2."""
        from shared import exploration_tracker
        from shared.stimmung import StimmungCollector

        called: list = []

        def capture(sig, shm_root=None):
            called.append(sig)

        monkeypatch.setattr(exploration_tracker, "publish_exploration_signal", capture)

        collector = StimmungCollector(enable_exploration=False)
        collector.update_health(healthy=10, total=10)
        collector.snapshot()

        assert not called, (
            "With enable_exploration=False, publish_exploration_signal must "
            "NOT be invoked. This is the REGRESSION-2 configuration."
        )


class TestHealthMonitorExplorationCheck:
    """The health-monitor check must detect > 120s staleness per component."""

    @staticmethod
    def _write_signal(shm_root: Path, component: str, mtime: float) -> Path:
        """Write a valid ExplorationSignal JSON and backdate it."""
        from shared.exploration import ExplorationSignal
        from shared.exploration_writer import publish_exploration_signal

        sig = ExplorationSignal(
            component=component,
            timestamp=mtime,
            mean_habituation=0.1,
            max_novelty_edge=None,
            max_novelty_score=0.0,
            error_improvement_rate=0.0,
            chronic_error=0.0,
            mean_trace_interest=0.5,
            stagnation_duration=0.0,
            local_coherence=0.5,
            dwell_time_in_coherence=0.0,
            boredom_index=0.0,
            curiosity_index=0.5,
        )
        publish_exploration_signal(sig, shm_root=shm_root)
        path = shm_root / "hapax-exploration" / f"{component}.json"
        os.utime(path, (mtime, mtime))
        return path

    def test_fresh_writer_is_healthy(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from agents.health_monitor.checks import exploration as exp_mod

        monkeypatch.setattr(exp_mod, "EXPLORATION_DIR", tmp_path / "hapax-exploration")
        now = time.time()
        for component in COMPONENT_OWNERS:
            self._write_signal(tmp_path, component, now)

        results = asyncio.run(check_exploration_writers())
        for r in results:
            assert r.status == Status.HEALTHY, (
                f"Expected HEALTHY for {r.name}, got {r.status}: {r.message}"
            )

    def test_stale_writer_emits_degraded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from agents.health_monitor.checks import exploration as exp_mod

        monkeypatch.setattr(exp_mod, "EXPLORATION_DIR", tmp_path / "hapax-exploration")
        now = time.time()
        for component in COMPONENT_OWNERS:
            mtime = now - (STALE_THRESHOLD_S + 10) if component == "stimmung" else now
            self._write_signal(tmp_path, component, mtime)

        results = asyncio.run(check_exploration_writers())
        by_name = {r.name: r for r in results}
        assert by_name["exploration_stimmung"].status == Status.DEGRADED
        assert "stalled" in by_name["exploration_stimmung"].message.lower()
        assert "visual-layer-aggregator" in (by_name["exploration_stimmung"].remediation or "")

    def test_dead_writer_emits_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from agents.health_monitor.checks import exploration as exp_mod

        monkeypatch.setattr(exp_mod, "EXPLORATION_DIR", tmp_path / "hapax-exploration")
        now = time.time()
        for component in COMPONENT_OWNERS:
            mtime = now - (DEAD_THRESHOLD_S + 60) if component == "stimmung" else now
            self._write_signal(tmp_path, component, mtime)

        results = asyncio.run(check_exploration_writers())
        by_name = {r.name: r for r in results}
        assert by_name["exploration_stimmung"].status == Status.FAILED
        assert "dead" in by_name["exploration_stimmung"].message.lower()

    def test_missing_file_emits_degraded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from agents.health_monitor.checks import exploration as exp_mod

        monkeypatch.setattr(exp_mod, "EXPLORATION_DIR", tmp_path / "hapax-exploration")
        (tmp_path / "hapax-exploration").mkdir()
        for component in COMPONENT_OWNERS:
            if component == "stimmung":
                continue
            self._write_signal(tmp_path, component, time.time())

        results = asyncio.run(check_exploration_writers())
        by_name = {r.name: r for r in results}
        assert by_name["exploration_stimmung"].status == Status.DEGRADED
        assert "absent" in by_name["exploration_stimmung"].message.lower()

    def test_missing_directory_emits_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from agents.health_monitor.checks import exploration as exp_mod

        monkeypatch.setattr(exp_mod, "EXPLORATION_DIR", tmp_path / "never-made")
        results = asyncio.run(check_exploration_writers())
        assert len(results) == 1
        assert results[0].name == "exploration_dir"
        assert results[0].status == Status.FAILED


class TestDegradedSignalEmitter:
    """emit_degraded_signal must publish a valid stale-marker signal."""

    def test_publishes_fully_unhealthy_signal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from agents.health_monitor.checks import exploration as exp_mod
        from shared import exploration_writer

        def redirected(sig, shm_root=None):
            exploration_writer.publish_exploration_signal(sig, shm_root=tmp_path)

        monkeypatch.setattr(exp_mod, "publish_exploration_signal", redirected)

        assert emit_degraded_signal("stimmung", reason="writer_stall") is True
        path = tmp_path / "hapax-exploration" / "stimmung.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["component"] == "stimmung"
        assert data["chronic_error"] == 1.0
        assert data["max_novelty_edge"] == "writer_stall"
