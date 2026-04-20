"""ClassifierDegradedController — hysteresis state machine on Ring 2 health.

Phase 4 §Classifier unavailable → fail-closed template-only. Layered on
top of the per-call ``classify_with_fallback`` from
``classifier_degradation.py``:

- **Per-call fail-closed** (Phase 4, shipped): each individual Ring 2
  call that raises ``ClassifierUnavailable`` produces a synthetic
  medium-risk block-verdict. The failing capability is withheld; other
  capabilities are unaffected.
- **Controller-level degrade** (this module): when the classifier
  fails ``DEGRADE_THRESHOLD`` times in a row, the controller
  transitions to ``degrade`` state. In ``degrade``, callers that
  consult ``is_degraded()`` withhold ALL broadcast-surface LLM-
  generated emissions until ``RESTORE_THRESHOLD`` consecutive
  successes occur.

The distinction: per-call blocks the specific risky content; the
controller blocks the whole category of risky content while the
classifier is flaky.

State transitions:

    nominal ── 3 consecutive failures ──▶ degrade
    degrade ── 5 consecutive successes ──▶ nominal

Pattern mirrors ``llm_health.py`` / ``soak.py`` hysteresis state
machines — explicit counters + thresholds rather than time-based
windows, so behaviour is deterministic under test.

Observability:

- ``on_transition`` callback fires on any state change with
  ``(old_state, new_state, reason)``. Production wires this to
  ``shared.notify.send_notification`` for ``degrade``/``restore`` ntfy.
- ``snapshot()`` returns the current counters + state for Grafana
  scraping.

Thread-safe via a single ``threading.Lock`` — production call-sites
hit this from multiple CPAL / compositor threads.

Reference:
    - docs/superpowers/plans/2026-04-20-demonetization-safety-plan.md §Phase 4
    - shared/governance/classifier_degradation.py — the per-call
      fail-closed path this controller observes
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from threading import Lock
from typing import Final

log = logging.getLogger(__name__)


# Failure/success thresholds (plan §Phase 4 spec: 3-fail degrade,
# 5-success restore). Tunable via operator config; conservative
# defaults mean one random 502 from TabbyAPI does not trigger degrade
# and one recovery blip doesn't restore prematurely.
DEGRADE_THRESHOLD: Final[int] = 3
RESTORE_THRESHOLD: Final[int] = 5


class ClassifierHealthState(StrEnum):
    NOMINAL = "nominal"
    DEGRADE = "degrade"


@dataclass
class ClassifierHealthSnapshot:
    """Immutable read-only view of the controller's current state."""

    state: ClassifierHealthState
    consecutive_failures: int
    consecutive_successes: int
    total_failures: int
    total_successes: int


TransitionCallback = Callable[[ClassifierHealthState, ClassifierHealthState, str], None]


@dataclass
class ClassifierDegradedController:
    """Hysteresis controller wrapping per-call classifier outcomes.

    Call ``record_success()`` after every successful Ring 2 verdict
    (including fail-closed per-call blocks — those are "the classifier
    returned cleanly even if the verdict was block"). Call
    ``record_failure(reason)`` after every ``ClassifierUnavailable``
    raise that the per-call wrapper caught.

    Read ``is_degraded()`` at production call-sites to decide whether
    to withhold all broadcast emissions.
    """

    degrade_threshold: int = DEGRADE_THRESHOLD
    restore_threshold: int = RESTORE_THRESHOLD
    on_transition: TransitionCallback | None = None

    # Internal state — do not touch directly; use the public methods.
    _state: ClassifierHealthState = ClassifierHealthState.NOMINAL
    _consecutive_failures: int = 0
    _consecutive_successes: int = 0
    _total_failures: int = 0
    _total_successes: int = 0
    _lock: Lock = field(default_factory=Lock)

    # --- public API --------------------------------------------------

    def record_failure(self, reason: str = "") -> None:
        """Record a classifier failure. Fires transition callback if state changes."""
        with self._lock:
            self._consecutive_successes = 0
            self._consecutive_failures += 1
            self._total_failures += 1
            if (
                self._state == ClassifierHealthState.NOMINAL
                and self._consecutive_failures >= self.degrade_threshold
            ):
                self._transition(
                    ClassifierHealthState.DEGRADE,
                    reason=f"{self._consecutive_failures} consecutive failures: {reason}",
                )

    def record_success(self) -> None:
        """Record a successful classifier verdict. May restore from degrade."""
        with self._lock:
            self._consecutive_failures = 0
            self._consecutive_successes += 1
            self._total_successes += 1
            if (
                self._state == ClassifierHealthState.DEGRADE
                and self._consecutive_successes >= self.restore_threshold
            ):
                self._transition(
                    ClassifierHealthState.NOMINAL,
                    reason=f"{self._consecutive_successes} consecutive successes",
                )

    def is_degraded(self) -> bool:
        """Read current degrade state — callers check before broadcast emissions."""
        with self._lock:
            return self._state == ClassifierHealthState.DEGRADE

    def snapshot(self) -> ClassifierHealthSnapshot:
        """Return a snapshot of current counters for metrics scraping."""
        with self._lock:
            return ClassifierHealthSnapshot(
                state=self._state,
                consecutive_failures=self._consecutive_failures,
                consecutive_successes=self._consecutive_successes,
                total_failures=self._total_failures,
                total_successes=self._total_successes,
            )

    def reset(self) -> None:
        """Reset all counters + return to nominal. Primarily for tests."""
        with self._lock:
            prior = self._state
            self._state = ClassifierHealthState.NOMINAL
            self._consecutive_failures = 0
            self._consecutive_successes = 0
            self._total_failures = 0
            self._total_successes = 0
            if prior != ClassifierHealthState.NOMINAL:
                self._fire_callback(prior, ClassifierHealthState.NOMINAL, "reset")

    # --- internals ---------------------------------------------------

    def _transition(self, new_state: ClassifierHealthState, *, reason: str) -> None:
        """Assume _lock is held; flip state + fire callback."""
        old_state = self._state
        if old_state == new_state:
            return
        self._state = new_state
        # Reset the OPPOSITE counter on entry to a new state so we don't
        # immediately flip back — the counter for the new state's exit
        # condition starts at 0.
        if new_state == ClassifierHealthState.DEGRADE:
            self._consecutive_successes = 0
        else:
            self._consecutive_failures = 0
        log.warning(
            "ClassifierDegradedController: %s → %s (%s)",
            old_state.value,
            new_state.value,
            reason,
        )
        self._fire_callback(old_state, new_state, reason)

    def _fire_callback(
        self,
        old_state: ClassifierHealthState,
        new_state: ClassifierHealthState,
        reason: str,
    ) -> None:
        """Invoke on_transition if set, isolating failures from the state machine."""
        if self.on_transition is None:
            return
        try:
            self.on_transition(old_state, new_state, reason)
        except Exception:
            log.exception("ClassifierDegradedController: on_transition callback raised")


# Module-level singleton. Production services share state across
# threads via this instance. Tests construct their own controllers.
CONTROLLER = ClassifierDegradedController()


__all__ = [
    "CONTROLLER",
    "ClassifierDegradedController",
    "ClassifierHealthSnapshot",
    "ClassifierHealthState",
    "DEGRADE_THRESHOLD",
    "RESTORE_THRESHOLD",
    "TransitionCallback",
]
