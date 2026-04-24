"""YouTube telemetry impingement emitter (ytb-005).

3-min tick polls Analytics, computes deviation against a 24h
rolling-median baseline, classifies salience, and appends a
``CompositionalImpingement``-shaped JSON record to
``/dev/shm/hapax-dmn/impingements.jsonl``.

## Cadence

180 s tick → 480 ticks/day. Analytics API soft-cap is 500 req/day,
so we stay under by design. The cc-task's hypothetical 60s cadence
(1440/day) was over the soft-cap.

## Failure mode

Analytics read failure → emit a ``stale`` impingement (zero salience)
so the bus heartbeat is unbroken and the QM2 sampler can distinguish
"no tick fired" from "tick fired but had no data". Loop never raises.

## Metrics

- ``hapax_broadcast_yt_analytics_polls_total{result}`` — Counter
  labelled ``ok`` / ``error``.
- ``hapax_broadcast_yt_telemetry_impingements_emitted_total{kind}``
  — Counter labelled ``ambient`` / ``spike`` / ``drop`` / ``stale``.
"""

from __future__ import annotations

import json
import logging
import os
import signal as _signal
import threading
import time as _time
from pathlib import Path

from prometheus_client import REGISTRY, CollectorRegistry, Counter, start_http_server

from agents.youtube_telemetry.baseline import RollingMedianBaseline
from agents.youtube_telemetry.client import AnalyticsClient, channel_id_from_env
from agents.youtube_telemetry.salience import classify, stale_verdict

log = logging.getLogger(__name__)

DEFAULT_BUS_PATH = Path("/dev/shm/hapax-dmn/impingements.jsonl")
DEFAULT_TICK_S: float = float(os.environ.get("HAPAX_YT_TELEMETRY_TICK_S", "180"))
METRICS_PORT: int = int(os.environ.get("HAPAX_YT_TELEMETRY_METRICS_PORT", "9498"))
SOURCE_TAG = "youtube_telemetry"


class TelemetryEmitter:
    """3-min-tick emitter for YouTube viewer-telemetry impingements."""

    def __init__(
        self,
        *,
        client: AnalyticsClient,
        bus_path: Path = DEFAULT_BUS_PATH,
        baseline: RollingMedianBaseline | None = None,
        registry: CollectorRegistry = REGISTRY,
        tick_s: float = DEFAULT_TICK_S,
    ) -> None:
        self._client = client
        self._bus_path = bus_path
        # `baseline or RollingMedianBaseline()` would be wrong here — an
        # empty baseline (`__len__ == 0`) is falsy in bool context.
        self._baseline = baseline if baseline is not None else RollingMedianBaseline()
        self._tick_s = max(1.0, tick_s)
        self._stop_evt = threading.Event()

        self.poll_total = Counter(
            "hapax_broadcast_yt_analytics_polls_total",
            "Analytics API poll attempts.",
            ["result"],
            registry=registry,
        )
        self.impingements_total = Counter(
            "hapax_broadcast_yt_telemetry_impingements_emitted_total",
            "Telemetry impingements emitted on the bus.",
            ["kind"],
            registry=registry,
        )

    # ── Public API ────────────────────────────────────────────────────

    def tick_once(self, *, now: float | None = None) -> None:
        """Pull one realtime sample and emit one bus record."""
        now = _time.time() if now is None else now
        try:
            reading = self._client.read_realtime(now=now)
        except Exception:  # noqa: BLE001
            log.warning("analytics tick failed; emitting stale heartbeat", exc_info=True)
            self.poll_total.labels(result="error").inc()
            self._emit_stale(now)
            return

        self.poll_total.labels(result="ok").inc()
        deviation = self._baseline.deviation(reading.concurrent_viewers)
        verdict = classify(deviation)
        self._baseline.record(reading.concurrent_viewers)
        self._emit(
            verdict_kind=verdict.kind,
            salience=verdict.salience,
            ccu=reading.concurrent_viewers,
            engagement=reading.engagement_score,
            deviation=deviation,
            sampled_at=reading.sampled_at,
        )

    def run_forever(self) -> None:
        for sig in (_signal.SIGTERM, _signal.SIGINT):
            try:
                _signal.signal(sig, lambda *_: self._stop_evt.set())
            except ValueError:
                pass

        log.info(
            "youtube telemetry emitter starting, port=%d tick=%.1fs channel=%s",
            METRICS_PORT,
            self._tick_s,
            self._client.channel_id,
        )
        while not self._stop_evt.is_set():
            try:
                self.tick_once()
            except Exception:  # noqa: BLE001
                log.exception("tick failed; continuing on next cadence")
            self._stop_evt.wait(self._tick_s)

    def stop(self) -> None:
        self._stop_evt.set()

    # ── Bus emit ──────────────────────────────────────────────────────

    def _emit_stale(self, now: float) -> None:
        verdict = stale_verdict()
        self._emit(
            verdict_kind=verdict.kind,
            salience=verdict.salience,
            ccu=0.0,
            engagement=None,
            deviation=None,
            sampled_at=now,
        )

    def _emit(
        self,
        *,
        verdict_kind: str,
        salience: float,
        ccu: float,
        engagement: float | None,
        deviation: float | None,
        sampled_at: float,
    ) -> None:
        record = {
            "ts": sampled_at,
            "source": SOURCE_TAG,
            "intent_family": "youtube.telemetry",
            "narrative": self._narrative(verdict_kind, ccu, deviation),
            "salience": salience,
            "kind": verdict_kind,
            "grounding_provenance": ["youtube.analytics.realtime.concurrent_viewers"],
            "concurrent_viewers": ccu,
            "engagement_score": engagement,
            "deviation_ratio": deviation,
            "channel_id": self._client.channel_id,
        }
        try:
            self._bus_path.parent.mkdir(parents=True, exist_ok=True)
            with self._bus_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, default=str) + "\n")
        except OSError:
            log.warning("impingement bus write failed for kind=%s", verdict_kind, exc_info=True)
            return
        self.impingements_total.labels(kind=verdict_kind).inc()

    def _narrative(self, kind: str, ccu: float, deviation: float | None) -> str:
        if kind == "stale":
            return "youtube analytics: read failed; reporting stale heartbeat"
        if kind == "ambient":
            if deviation is None:
                return f"youtube analytics: viewer count {ccu:.0f}; baseline cold-start"
            return f"youtube analytics: viewer count {ccu:.0f} ({deviation:.2f}x baseline)"
        if kind == "spike":
            return f"youtube analytics: viewer count {ccu:.0f} ({deviation:.2f}x baseline) — spike"
        return f"youtube analytics: viewer count {ccu:.0f} ({deviation:.2f}x baseline) — drop"


def main() -> None:
    """Daemon entry — `python -m agents.youtube_telemetry`."""
    logging.basicConfig(
        level=os.environ.get("HAPAX_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    channel_id = channel_id_from_env()
    client = AnalyticsClient(channel_id=channel_id)
    start_http_server(METRICS_PORT, addr="127.0.0.1")
    emitter = TelemetryEmitter(client=client)
    emitter.run_forever()


if __name__ == "__main__":
    main()
