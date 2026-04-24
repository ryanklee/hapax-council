"""Impingement bus sampler — boredom vs curiosity rate Prometheus metrics.

The impingement bus at ``/dev/shm/hapax-dmn/impingements.jsonl`` is the
main signal surface for the affordance pipeline + director loop + CPAL.
Impingement *type* distribution is a strong proxy for content-state
quality:

- High **boredom** rate         → Hapax is stuck, no novelty
- High **curiosity** rate       → world providing rich stimulus
- High **pattern_match** rate   → content coherent
- High **salience_integration** → content building

This sampler tails the bus, increments a per-type counter, and derives a
single ``hapax_impingement_novelty_score`` gauge so dashboards and SS1
gating can read "is content stuck or flowing" from one number.

## Metrics on `:9496/metrics`

- ``hapax_impingement_rate_total{type}`` Counter — per-``ImpingementType``
  cumulative count. Divide by elapsed time in PromQL for rate.
- ``hapax_impingement_novelty_score`` Gauge — derived ratio
  ``(curiosity + pattern_match) / (boredom + 0.1)`` over the last
  5-minute window. Higher = more novel content; lower = stuck. The
  ``+ 0.1`` denominator floor prevents division spikes on quiet
  windows.
- ``hapax_impingement_sampler_tick_duration_seconds`` Histogram —
  sampler's own tick latency.

## Cost

Sampler uses ``ImpingementConsumer(cursor_path=…)`` so a restart picks
up where it left off rather than backfilling the entire bus or
skipping the unread tail. Tick reads only new lines since last cursor
— typically zero-to-tens per 5 s. Cheap.

## Failure mode

If the impingement file is missing or unreadable, the tick logs once
(throttled) and reports stale gauges. The sampler never raises out of
its tick loop — Prometheus scrape sees the last known values until
events resume.

Spec: ytb-QM2; depends on impingement bus + ``ImpingementConsumer`` (shipped).
"""

from __future__ import annotations

import logging
import os
import signal as _signal
import threading
import time
from collections import deque
from pathlib import Path

from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    start_http_server,
)

from shared.impingement import Impingement, ImpingementType
from shared.impingement_consumer import ImpingementConsumer

log = logging.getLogger(__name__)

# Default Prometheus scrape port. 9495 was taken by hapax-chronicle-quality-
# exporter (ytb-QM1, sibling); next free is 9496.
METRICS_PORT: int = int(os.environ.get("HAPAX_IMPINGEMENT_SAMPLER_METRICS_PORT", "9496"))

# Tick cadence. Faster than chronicle exporter (5s) because impingements
# arrive throughout a 5-minute novelty window and we want the gauge to
# track recent state, not 30-s-stale state.
DEFAULT_TICK_S: float = float(os.environ.get("HAPAX_IMPINGEMENT_SAMPLER_TICK_S", "5"))

# Novelty score window. Long enough to smooth out single-event noise,
# short enough that "stuck" detection within a livestream slot is
# actionable.
NOVELTY_WINDOW_S: float = float(os.environ.get("HAPAX_IMPINGEMENT_NOVELTY_WINDOW_S", "300"))

# Default impingement bus path. Override for tests.
DEFAULT_BUS_PATH: Path = Path("/dev/shm/hapax-dmn/impingements.jsonl")

# Cursor path — restart-safe like daimonion's two consumers.
DEFAULT_CURSOR_PATH: Path = (
    Path.home() / ".cache" / "hapax" / "impingement-cursor-quality-sampler.txt"
)

# Denominator floor for the novelty score — prevents the ratio from
# spiking on quiet windows where boredom transiently rounds to zero.
NOVELTY_DENOMINATOR_FLOOR: float = 0.1

# Numerator types: coherence + novelty signals.
NOVELTY_NUMERATOR_TYPES: frozenset[ImpingementType] = frozenset(
    {ImpingementType.CURIOSITY, ImpingementType.PATTERN_MATCH}
)

# Denominator type: stuckness signal.
NOVELTY_DENOMINATOR_TYPE: ImpingementType = ImpingementType.BOREDOM


class ImpingementSampler:
    """Tail-based sampler. One instance per process; thread-safe stop.

    Tests construct with ``registry=CollectorRegistry()`` to keep
    Prometheus state isolated across runs.
    """

    def __init__(
        self,
        *,
        bus_path: Path = DEFAULT_BUS_PATH,
        cursor_path: Path | None = DEFAULT_CURSOR_PATH,
        registry: CollectorRegistry = REGISTRY,
        tick_s: float = DEFAULT_TICK_S,
        novelty_window_s: float = NOVELTY_WINDOW_S,
    ) -> None:
        self._bus_path = bus_path
        self._tick_s = max(0.5, tick_s)
        self._novelty_window_s = max(10.0, novelty_window_s)
        self._stop_evt = threading.Event()
        self._unreadable_warned = False

        # Restart-safe consumer. Tests pass cursor_path=None for
        # in-memory cursoring without leaking files into the cache dir.
        self._consumer = ImpingementConsumer(bus_path, cursor_path=cursor_path)

        # Rolling deque of (ts, type) pairs over the novelty window.
        # Updated each tick; old entries pruned by ts.
        self._window: deque[tuple[float, ImpingementType]] = deque()

        # Counter is unlabeled-cardinality-bounded by ImpingementType
        # (7 values total — see shared/impingement.py).
        self.rate_total = Counter(
            "hapax_impingement_rate_total",
            "Cumulative impingement count per type. Divide by time for rate.",
            ["type"],
            registry=registry,
        )
        self.novelty_score = Gauge(
            "hapax_impingement_novelty_score",
            "(curiosity+pattern_match) / (boredom+0.1) over a 5min window. "
            "High = novel; low = stuck.",
            registry=registry,
        )
        self.tick_duration = Histogram(
            "hapax_impingement_sampler_tick_duration_seconds",
            "Sampler tick latency. >1s means parser is the slow link.",
            registry=registry,
        )

        # Pre-zero counters for every known type so dashboards see a
        # row per type from t=0 (otherwise prometheus_client doesn't
        # emit a label series until first .inc()).
        for t in ImpingementType:
            self.rate_total.labels(type=t.value)

    # ── Public API ────────────────────────────────────────────────────

    def tick_once(self, *, now: float | None = None) -> None:
        """Drain new impingements, increment counters, recompute novelty."""
        now = time.time() if now is None else now
        with self.tick_duration.time():
            try:
                new_events = self._consumer.read_new()
            except Exception:  # noqa: BLE001
                if not self._unreadable_warned:
                    log.warning(
                        "impingement bus unreadable at %s; reporting stale gauges",
                        self._bus_path,
                        exc_info=True,
                    )
                    self._unreadable_warned = True
                return

            self._unreadable_warned = False
            for imp in new_events:
                self._observe(imp, now=now)
            self._prune_window(now=now)
            self._recompute_novelty()

    def run_forever(self) -> None:
        """Blocking daemon loop. SIGTERM/SIGINT trigger clean exit."""
        for sig in (_signal.SIGTERM, _signal.SIGINT):
            try:
                _signal.signal(sig, lambda *_: self._stop_evt.set())
            except ValueError:
                # Not on the main thread — tests use this path.
                pass

        log.info(
            "impingement sampler starting, port=%d tick=%.1fs window=%.0fs",
            METRICS_PORT,
            self._tick_s,
            self._novelty_window_s,
        )
        while not self._stop_evt.is_set():
            try:
                self.tick_once()
            except Exception:  # noqa: BLE001
                log.exception("tick failed; continuing on next cadence")
            self._stop_evt.wait(self._tick_s)

    def stop(self) -> None:
        self._stop_evt.set()

    # ── Internals ─────────────────────────────────────────────────────

    def _observe(self, imp: Impingement, *, now: float) -> None:
        """Record one impingement: increment counter + push into window."""
        try:
            type_ = ImpingementType(imp.type)
        except (ValueError, AttributeError):
            # Unknown type from a downstream extension or a malformed
            # event — log and skip rather than mint a new label that
            # would unbound cardinality.
            log.debug("unknown impingement type from event %s", imp)
            return
        self.rate_total.labels(type=type_.value).inc()
        # Use the event's own timestamp for window membership, not now —
        # the bus may have buffered events while the sampler was down.
        ts = float(imp.timestamp) if imp.timestamp else now
        self._window.append((ts, type_))

    def _prune_window(self, *, now: float) -> None:
        """Drop entries older than the novelty window."""
        cutoff = now - self._novelty_window_s
        while self._window and self._window[0][0] < cutoff:
            self._window.popleft()

    def _recompute_novelty(self) -> None:
        """Update the novelty gauge from current window contents."""
        numerator = 0
        denominator = 0
        for _ts, type_ in self._window:
            if type_ in NOVELTY_NUMERATOR_TYPES:
                numerator += 1
            elif type_ == NOVELTY_DENOMINATOR_TYPE:
                denominator += 1
        score = numerator / (denominator + NOVELTY_DENOMINATOR_FLOOR)
        self.novelty_score.set(score)


def main() -> None:
    """Daemon entry — `python -m agents.quality_observability.impingement_sampler`."""
    logging.basicConfig(
        level=os.environ.get("HAPAX_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    start_http_server(METRICS_PORT, addr="127.0.0.1")
    sampler = ImpingementSampler()
    sampler.run_forever()


if __name__ == "__main__":
    main()
