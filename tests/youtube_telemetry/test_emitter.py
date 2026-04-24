"""Tests for ``agents.youtube_telemetry.emitter``.

Unit-level tests pin the bus-record schema, the metric-counter
behaviour, the spike/drop classification round-trip, and the
graceful-degradation path. Integration test verifies an emitted
record is readable as JSON from the bus file.
"""

from __future__ import annotations

import json
from unittest import mock

import pytest
from prometheus_client import CollectorRegistry

from agents.youtube_telemetry.baseline import RollingMedianBaseline
from agents.youtube_telemetry.client import AnalyticsClient, RealtimeReading, channel_id_from_env
from agents.youtube_telemetry.emitter import TelemetryEmitter


def _make_emitter(
    *,
    bus_path,
    reading: RealtimeReading | None = None,
    raises: Exception | None = None,
    baseline: RollingMedianBaseline | None = None,
) -> tuple[TelemetryEmitter, mock.Mock]:
    client = mock.Mock(spec=AnalyticsClient)
    client.channel_id = "UC-test-channel"
    if raises is not None:
        client.read_realtime.side_effect = raises
    elif reading is not None:
        client.read_realtime.return_value = reading
    emitter = TelemetryEmitter(
        client=client,
        bus_path=bus_path,
        baseline=baseline,
        registry=CollectorRegistry(),
    )
    return emitter, client


def _read_bus(bus_path) -> list[dict]:
    if not bus_path.exists():
        return []
    return [json.loads(line) for line in bus_path.read_text().splitlines() if line.strip()]


# ── Bus emit — schema + cold-start ───────────────────────────────────


class TestEmit:
    def test_cold_start_emits_ambient(self, tmp_path):
        bus = tmp_path / "impingements.jsonl"
        reading = RealtimeReading(concurrent_viewers=12.0, engagement_score=None, sampled_at=1.0)
        emitter, _ = _make_emitter(bus_path=bus, reading=reading)
        emitter.tick_once(now=1.0)
        records = _read_bus(bus)
        assert len(records) == 1
        record = records[0]
        assert record["intent_family"] == "youtube.telemetry"
        assert record["source"] == "youtube_telemetry"
        assert record["kind"] == "ambient"
        assert record["salience"] == pytest.approx(0.2)
        assert record["concurrent_viewers"] == pytest.approx(12.0)
        assert record["deviation_ratio"] is None  # baseline cold
        assert record["channel_id"] == "UC-test-channel"
        assert record["grounding_provenance"] == ["youtube.analytics.realtime.concurrent_viewers"]

    def test_spike_classification(self, tmp_path):
        bus = tmp_path / "impingements.jsonl"
        baseline = RollingMedianBaseline(min_samples=1)
        baseline.extend([10.0, 10.0, 10.0])
        reading = RealtimeReading(concurrent_viewers=25.0, engagement_score=None, sampled_at=1.0)
        emitter, _ = _make_emitter(bus_path=bus, reading=reading, baseline=baseline)
        emitter.tick_once(now=1.0)
        record = _read_bus(bus)[0]
        assert record["kind"] == "spike"
        assert record["salience"] == pytest.approx(0.7)
        assert record["deviation_ratio"] == pytest.approx(2.5)

    def test_drop_classification(self, tmp_path):
        bus = tmp_path / "impingements.jsonl"
        baseline = RollingMedianBaseline(min_samples=1)
        baseline.extend([20.0, 20.0, 20.0])
        reading = RealtimeReading(concurrent_viewers=5.0, engagement_score=None, sampled_at=1.0)
        emitter, _ = _make_emitter(bus_path=bus, reading=reading, baseline=baseline)
        emitter.tick_once(now=1.0)
        record = _read_bus(bus)[0]
        assert record["kind"] == "drop"
        assert record["salience"] == pytest.approx(0.5)

    def test_baseline_warms_after_each_tick(self, tmp_path):
        bus = tmp_path / "impingements.jsonl"
        baseline = RollingMedianBaseline(min_samples=2)
        reading = RealtimeReading(concurrent_viewers=10.0, engagement_score=None, sampled_at=1.0)
        emitter, client = _make_emitter(bus_path=bus, reading=reading, baseline=baseline)
        emitter.tick_once(now=1.0)
        emitter.tick_once(now=2.0)
        emitter.tick_once(now=3.0)
        records = _read_bus(bus)
        # 3rd tick saw a warm baseline so deviation is set.
        assert records[2]["deviation_ratio"] == pytest.approx(1.0)

    def test_engagement_passed_through_when_present(self, tmp_path):
        bus = tmp_path / "impingements.jsonl"
        reading = RealtimeReading(concurrent_viewers=10.0, engagement_score=42.5, sampled_at=1.0)
        emitter, _ = _make_emitter(bus_path=bus, reading=reading)
        emitter.tick_once(now=1.0)
        record = _read_bus(bus)[0]
        assert record["engagement_score"] == pytest.approx(42.5)


# ── Failure mode ─────────────────────────────────────────────────────


class TestFailure:
    def test_read_failure_emits_stale(self, tmp_path):
        bus = tmp_path / "impingements.jsonl"
        emitter, _ = _make_emitter(bus_path=bus, raises=RuntimeError("API down"))
        emitter.tick_once(now=1.0)
        record = _read_bus(bus)[0]
        assert record["kind"] == "stale"
        assert record["salience"] == 0.0
        assert record["deviation_ratio"] is None

    def test_read_failure_increments_error_counter(self, tmp_path):
        bus = tmp_path / "impingements.jsonl"
        emitter, _ = _make_emitter(bus_path=bus, raises=RuntimeError("API down"))
        emitter.tick_once(now=1.0)
        # Confirm the error counter ticked (sample 1 means 1 error
        # since process start).
        samples = list(emitter.poll_total.collect())
        assert any(
            sample.value == 1.0
            for metric in samples
            for sample in metric.samples
            if sample.labels.get("result") == "error"
        )

    def test_kind_counter_records_classification(self, tmp_path):
        bus = tmp_path / "impingements.jsonl"
        baseline = RollingMedianBaseline(min_samples=1)
        baseline.extend([10.0, 10.0])
        reading = RealtimeReading(concurrent_viewers=25.0, engagement_score=None, sampled_at=1.0)
        emitter, _ = _make_emitter(bus_path=bus, reading=reading, baseline=baseline)
        emitter.tick_once(now=1.0)
        samples = list(emitter.impingements_total.collect())
        spike_total = next(
            sample.value
            for metric in samples
            for sample in metric.samples
            if sample.labels.get("kind") == "spike"
        )
        assert spike_total == 1.0


# ── Bus-write integration ────────────────────────────────────────────


class TestBusIntegration:
    def test_record_is_valid_json_per_line(self, tmp_path):
        bus = tmp_path / "impingements.jsonl"
        reading = RealtimeReading(concurrent_viewers=10.0, engagement_score=None, sampled_at=1.0)
        emitter, _ = _make_emitter(bus_path=bus, reading=reading)
        emitter.tick_once(now=1.0)
        emitter.tick_once(now=2.0)
        lines = bus.read_text().strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            json.loads(line)  # raises on malformed

    def test_bus_path_parent_created(self, tmp_path):
        bus = tmp_path / "subdir" / "deeper" / "impingements.jsonl"
        reading = RealtimeReading(concurrent_viewers=10.0, engagement_score=None, sampled_at=1.0)
        emitter, _ = _make_emitter(bus_path=bus, reading=reading)
        emitter.tick_once(now=1.0)
        assert bus.exists()


class TestChannelIdFromEnv:
    def test_reads_env(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_CHANNEL_ID", "UC-real")
        assert channel_id_from_env() == "UC-real"

    def test_strips_whitespace(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_CHANNEL_ID", "  UC-real  ")
        assert channel_id_from_env() == "UC-real"

    def test_raises_when_missing(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_CHANNEL_ID", raising=False)
        with pytest.raises(RuntimeError, match="YOUTUBE_CHANNEL_ID"):
            channel_id_from_env()
