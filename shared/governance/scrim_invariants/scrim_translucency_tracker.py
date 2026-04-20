"""Scrim-translucency runtime tracker (OQ-02 bound 2, observe-only by default).

Wraps the pure-stateless oracle in
``shared.governance.scrim_invariants.scrim_translucency`` with rolling-window
state, hysteresis transitions modeled on
``agents.hapax_daimonion.presence_engine.PresenceEngine``, and an atomic
signal publisher modeled on
``agents.studio_compositor.budget_signal.publish_degraded_signal``.

Shape (per research §6 of
``docs/research/2026-04-20-oq02-scrim-translucency-metric.md``):

- Per-frame ``record(frame, thresholds, reference_density)`` calls
  :func:`shared.governance.scrim_invariants.scrim_translucency.evaluate` and
  appends the score to a fixed-size ``deque``.
- The tracker carries a NOMINAL/DEGRADED state machine. K consecutive
  failing scores trips DEGRADED; N consecutive passing scores after that
  recovers to NOMINAL (recovery hysteresis defeats single-frame blips
  during transient B2 events).
- :func:`publish_scrim_signal` writes the current state to
  ``/dev/shm/hapax-compositor/scrim_translucency.json`` atomically.
- A FreshnessGauge ("compositor_scrim_translucency") makes the silent-stop
  failure mode visible on Prometheus, falling back to a no-op gauge if
  prometheus_client is unavailable.

Enforcement gate (HAPAX_SCRIM_INVARIANT_B2_ENFORCE):

    Default ``0`` (observe-only) — the tracker computes the score, holds
    state, publishes the signal. ``enforcement_active()`` returns False;
    downstream consumers (camera-profile selector, scrim-density
    modulator) consult that flag before acting on the signal so the
    operator can run the metric live without any compositor behavior
    change.

    Set ``HAPAX_SCRIM_INVARIANT_B2_ENFORCE=1`` after a calibration epoch
    confirms the metric does not flag legitimate scrim density. The
    published JSON is unchanged across the gate; only the consumer-side
    interpretation flips.

The tracker is thread-safe for concurrent ``record()`` calls (a single
lock guards window + state). Publishing is also thread-safe via the lock
+ the underlying ``atomic_write_json``.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from agents.studio_compositor.atomic_io import atomic_write_json
from shared.governance.scrim_invariants.scrim_translucency import (
    DEFAULT_REFERENCE_EDGE_DENSITY,
    SCHEMA_VERSION,
    TranslucencyScore,
    TranslucencyThresholds,
    evaluate,
)

if TYPE_CHECKING:
    import numpy as np

log = logging.getLogger(__name__)

DEFAULT_SIGNAL_PATH: Final[Path] = Path("/dev/shm/hapax-compositor/scrim_translucency.json")
"""Canonical shared-memory path for the scrim-translucency signal."""

DEFAULT_WINDOW_SIZE: Final[int] = 120
"""Rolling window of scores; ~4s at 30fps, sized like ``BudgetTracker``."""

DEFAULT_FAILURE_K: Final[int] = 30
"""K consecutive failing frames trip DEGRADED — ~1s at 30fps. Per research §6.1."""

DEFAULT_RECOVERY_N: Final[int] = 10
"""N consecutive passing frames after DEGRADED recover to NOMINAL.

Recovery hysteresis modeled on the presence_engine PRESENT/UNCERTAIN/AWAY
transitions: a single mid-failure passing frame must NOT recover the
state, or the signal will chatter on borderline scenes.
"""

ENFORCE_ENV_VAR: Final[str] = "HAPAX_SCRIM_INVARIANT_B2_ENFORCE"
"""Env var gating consumer-side enforcement. ``1`` enables, anything else (default) is observe-only."""

STATE_NOMINAL: Final[str] = "NOMINAL"
STATE_DEGRADED: Final[str] = "DEGRADED"


def enforcement_active() -> bool:
    """Return True iff the B2 enforcement gate is enabled.

    The published signal payload includes ``enforcement_active`` so
    consumers can introspect the gate state without re-reading the env.
    """
    return os.environ.get(ENFORCE_ENV_VAR, "0") == "1"


# -- Optional FreshnessGauge wiring (mirrors budget_signal.py) -------------------

try:
    from shared.freshness_gauge import FreshnessGauge

    try:
        from agents.studio_compositor.metrics import (
            REGISTRY as _COMPOSITOR_METRICS_REGISTRY,
        )
    except ImportError:
        _COMPOSITOR_METRICS_REGISTRY = None  # type: ignore[assignment]

    _PUBLISH_SCRIM_FRESHNESS: FreshnessGauge | None = FreshnessGauge(
        name="compositor_scrim_translucency",
        expected_cadence_s=1.0,
        registry=_COMPOSITOR_METRICS_REGISTRY,
    )
except Exception:  # pragma: no cover — prometheus_client / gauge optional
    log.warning(
        "FreshnessGauge unavailable for publish_scrim_signal; continuing without metric",
        exc_info=True,
    )
    _PUBLISH_SCRIM_FRESHNESS = None


@dataclass(frozen=True)
class ScrimTranslucencySnapshot:
    """Frozen view of tracker state for serialization.

    Aggregates the most recent score plus the rolling-window summary that
    feeds the JSON signal. ``state`` is the post-hysteresis label
    (NOMINAL or DEGRADED). ``transition_count`` counts NOMINAL→DEGRADED
    flips since tracker construction (degraded entries; recovery does
    not increment).
    """

    schema_version: int
    timestamp_monotonic_ms: float
    wall_clock: float
    state: str
    consecutive_failures: int
    consecutive_passes: int
    over_threshold: bool
    transition_count: int
    enforcement_active: bool
    failure_k: int
    recovery_n: int
    window_size: int
    samples_in_window: int
    current: dict[str, float | bool | str | None] | None


class ScrimTranslucencyTracker:
    """Thread-safe rolling-window tracker for the bound-2 oracle.

    Mirrors :class:`agents.studio_compositor.budget.BudgetTracker`:
    a single tracker instance is shared across the compositor (or owned
    by the eventual livestream-perf governance loop), records every
    egress frame, and is queried by the publisher on a 1Hz cadence.

    Hysteresis state machine (per research §6.3, modeled on
    ``presence_engine``):

        NOMINAL  --[K consecutive failing frames]-->  DEGRADED
        DEGRADED --[N consecutive passing frames]-->  NOMINAL

    ``DEGRADED`` is the state consumers gate on; the publisher exposes
    it as ``over_threshold=true``. Per the observe-only contract,
    enforcement actions in the compositor / structural director must
    additionally check :func:`enforcement_active`.
    """

    def __init__(
        self,
        *,
        window_size: int = DEFAULT_WINDOW_SIZE,
        failure_k: int = DEFAULT_FAILURE_K,
        recovery_n: int = DEFAULT_RECOVERY_N,
    ) -> None:
        if window_size < 1:
            raise ValueError(f"window_size must be >= 1, got {window_size}")
        if failure_k < 1:
            raise ValueError(f"failure_k must be >= 1, got {failure_k}")
        if recovery_n < 1:
            raise ValueError(f"recovery_n must be >= 1, got {recovery_n}")
        self._window_size = window_size
        self._failure_k = failure_k
        self._recovery_n = recovery_n

        self._lock = threading.Lock()
        self._scores: deque[TranslucencyScore] = deque(maxlen=window_size)
        self._consecutive_failures = 0
        self._consecutive_passes = 0
        self._state = STATE_NOMINAL
        self._transition_count = 0
        self._last_score: TranslucencyScore | None = None

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(
        self,
        frame: np.ndarray,
        thresholds: TranslucencyThresholds,
        *,
        reference_edge_density: float = DEFAULT_REFERENCE_EDGE_DENSITY,
    ) -> TranslucencyScore:
        """Score ``frame`` and update the rolling window + hysteresis state.

        Returns the computed :class:`TranslucencyScore` for callers that
        want to inspect the per-frame result (e.g. logging the failing
        component on transitions).
        """
        score = evaluate(frame, thresholds, reference_edge_density=reference_edge_density)
        with self._lock:
            self._scores.append(score)
            self._last_score = score
            if score.passed:
                self._consecutive_passes += 1
                self._consecutive_failures = 0
                if self._state == STATE_DEGRADED and self._consecutive_passes >= self._recovery_n:
                    self._state = STATE_NOMINAL
                    log.info(
                        "scrim translucency: DEGRADED -> NOMINAL after %d passing frames",
                        self._consecutive_passes,
                    )
            else:
                self._consecutive_failures += 1
                self._consecutive_passes = 0
                if self._state == STATE_NOMINAL and self._consecutive_failures >= self._failure_k:
                    self._state = STATE_DEGRADED
                    self._transition_count += 1
                    log.warning(
                        "scrim translucency: NOMINAL -> DEGRADED after %d failing frames "
                        "(failing component=%s, aggregate=%.3f)",
                        self._consecutive_failures,
                        score.failing_component,
                        score.aggregate,
                    )
        return score

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def consecutive_failures(self) -> int:
        with self._lock:
            return self._consecutive_failures

    def consecutive_passes(self) -> int:
        with self._lock:
            return self._consecutive_passes

    def state(self) -> str:
        with self._lock:
            return self._state

    def over_threshold(self) -> bool:
        """True iff the tracker is in the DEGRADED post-hysteresis state."""
        with self._lock:
            return self._state == STATE_DEGRADED

    def transition_count(self) -> int:
        with self._lock:
            return self._transition_count

    def snapshot(self) -> ScrimTranslucencySnapshot:
        """Return a frozen, serialization-ready view of tracker state."""
        with self._lock:
            current: dict[str, float | bool | str | None] | None
            if self._last_score is None:
                current = None
            else:
                current = {
                    "edge_density_ratio": round(self._last_score.edge_density_ratio, 4),
                    "luminance_variance_score": round(self._last_score.luminance_variance_score, 4),
                    "entropy_floor_score": round(self._last_score.entropy_floor_score, 4),
                    "aggregate": round(self._last_score.aggregate, 4),
                    "passed": self._last_score.passed,
                    "failing_component": self._last_score.failing_component,
                }
            return ScrimTranslucencySnapshot(
                schema_version=SCHEMA_VERSION,
                timestamp_monotonic_ms=round(time.monotonic() * 1000.0, 3),
                wall_clock=round(time.time(), 3),
                state=self._state,
                consecutive_failures=self._consecutive_failures,
                consecutive_passes=self._consecutive_passes,
                over_threshold=self._state == STATE_DEGRADED,
                transition_count=self._transition_count,
                enforcement_active=enforcement_active(),
                failure_k=self._failure_k,
                recovery_n=self._recovery_n,
                window_size=self._window_size,
                samples_in_window=len(self._scores),
                current=current,
            )


def build_scrim_signal(tracker: ScrimTranslucencyTracker) -> dict[str, object]:
    """Construct the JSON-serializable scrim-translucency signal dict.

    Pure function over ``tracker.snapshot()``. Useful in tests and for
    callers that want to merge the signal into a larger document before
    publishing.
    """
    snap = tracker.snapshot()
    payload: dict[str, object] = {
        "schema_version": snap.schema_version,
        "timestamp_ms": snap.timestamp_monotonic_ms,
        "wall_clock": snap.wall_clock,
        "state": snap.state,
        "over_threshold": snap.over_threshold,
        "consecutive_failures": snap.consecutive_failures,
        "consecutive_passes": snap.consecutive_passes,
        "transition_count": snap.transition_count,
        "enforcement_active": snap.enforcement_active,
        "failure_k": snap.failure_k,
        "recovery_n": snap.recovery_n,
        "window_size": snap.window_size,
        "samples_in_window": snap.samples_in_window,
        "current": snap.current,
    }
    return payload


def publish_scrim_signal(
    tracker: ScrimTranslucencyTracker,
    path: Path | None = None,
) -> Path | None:
    """Atomically publish the tracker's scrim-translucency signal to disk.

    Mirrors :func:`agents.studio_compositor.budget_signal.publish_degraded_signal`:
    write to ``path.tmp`` then ``os.replace`` onto the final path so
    external readers (the compositor, the VLA-side subscriber, the
    structural director) never see a partial write.

    Failures are logged via the FreshnessGauge (when available) and
    swallowed — a publish failure must NOT crash the egress path.
    Returns the path on success, ``None`` on failure.
    """
    target = path or DEFAULT_SIGNAL_PATH
    payload = build_scrim_signal(tracker)
    try:
        atomic_write_json(payload, target)
    except Exception:
        if _PUBLISH_SCRIM_FRESHNESS is not None:
            try:
                _PUBLISH_SCRIM_FRESHNESS.mark_failed()
            except Exception:  # pragma: no cover — gauge itself failing must not propagate
                log.warning("FreshnessGauge.mark_failed failed", exc_info=True)
        log.warning("scrim translucency signal publish failed (target=%s)", target, exc_info=True)
        return None
    if _PUBLISH_SCRIM_FRESHNESS is not None:
        try:
            _PUBLISH_SCRIM_FRESHNESS.mark_published()
        except Exception:  # pragma: no cover
            log.warning("FreshnessGauge.mark_published failed", exc_info=True)
    log.debug(
        "scrim translucency signal published: state=%s consecutive_failures=%d",
        payload.get("state"),
        int(payload.get("consecutive_failures", 0)),  # type: ignore[arg-type]
    )
    return target
