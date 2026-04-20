"""Abort predicate evaluator + 5s operator-veto window — Phase 10.

Per research §4.4 + §6 emergent-transition type. The evaluator owns
the abort/veto state machine; the ProgrammeManager calls it each tick
to learn whether the active programme should abort.

State machine:

    no-pending → evaluate() returns AbortDecision when a registered
                 predicate fires; transitions to pending-abort.
    pending-abort → wait until veto_deadline_at. If a
                    `programme.abort.veto` impingement arrives BEFORE
                    the deadline, return to no-pending. Otherwise
                    commit_abort() returns the committed decision.

Architectural notes:

- Predicates are REGISTERED — there is no hardcoded "at t+Xs, abort"
  branch anywhere. The grounding-expansion test asserts this at the
  source level.
- Unregistered predicate names default to "not firing" (matches
  ProgrammeManager.unknown_predicate_satisfies=False default). A
  programme's success.abort_predicates list can name a predicate the
  evaluator hasn't been wired with yet — that's an unwired abort, not
  a silent live one.
- The evaluator is stateful in a single way: it tracks one pending
  abort (FSM enforces single-abort-in-flight). After commit or veto
  the state clears.

References:
- Plan §Phase 10 (`docs/superpowers/plans/2026-04-20-programme-layer-plan.md`)
- Spec §4.4 + §6
- shared/programme.py — Programme, ProgrammeSuccessCriteria
- shared/impingement.py — Impingement (operator-veto signal)
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from shared.impingement import Impingement
from shared.programme import Programme

log = logging.getLogger(__name__)


# Operator-veto signal. The 5s window is fixed by spec §6 line 1023-1025;
# operator presses an "undo abort" affordance which emits an impingement
# with this intent family.
VETO_INTENT_FAMILY = "programme.abort.veto"
DEFAULT_VETO_WINDOW_S = 5.0


PredicateFn = Callable[[Programme, dict], bool]
PredicateRegistry = Mapping[str, PredicateFn]


@dataclass(frozen=True)
class AbortDecision:
    """A pending or committed abort decision."""

    predicate_name: str
    triggered_at: float
    rationale: str
    veto_deadline_at: float


class AbortEvaluator:
    """Predicate-driven abort + veto FSM."""

    def __init__(
        self,
        *,
        predicates: PredicateRegistry | None = None,
        veto_window_s: float = DEFAULT_VETO_WINDOW_S,
        now_fn: Callable[[], float] = time.time,
    ) -> None:
        self._predicates: dict[str, PredicateFn] = dict(predicates or {})
        self._veto_window_s = veto_window_s
        self._now_fn = now_fn
        self._pending_abort: AbortDecision | None = None

    # --- public API ------------------------------------------------

    @property
    def pending_abort(self) -> AbortDecision | None:
        """Currently in-flight abort, if any. Clears after commit/veto."""
        return self._pending_abort

    def evaluate(
        self,
        programme: Programme,
        perceptual_snapshot: dict | None = None,
    ) -> AbortDecision | None:
        """Walk the programme's abort predicates; return decision on first true.

        Returns ``None`` when no registered predicate fires OR when an
        abort is already pending (the FSM allows one in-flight abort
        at a time — concurrent firings would race the veto window).
        """
        if self._pending_abort is not None:
            return None
        snapshot = perceptual_snapshot or {}
        for name in programme.success.abort_predicates:
            fn = self._predicates.get(name)
            if fn is None:
                # Unregistered → not firing. The unwired-predicate posture
                # matches ProgrammeManager.unknown_predicate_satisfies=False.
                log.debug("abort predicate %r not registered; skipping", name)
                continue
            try:
                fired = bool(fn(programme, snapshot))
            except Exception:
                log.warning("abort predicate %r raised; treating as False", name, exc_info=True)
                continue
            if fired:
                now = self._now_fn()
                decision = AbortDecision(
                    predicate_name=name,
                    triggered_at=now,
                    rationale=f"predicate {name!r} fired against programme {programme.programme_id!r}",
                    veto_deadline_at=now + self._veto_window_s,
                )
                self._pending_abort = decision
                return decision
        return None

    def handle_veto_impingement(self, imp: Impingement) -> bool:
        """Cancel a pending abort if this impingement is the veto signal.

        Returns True if the veto was honoured (pending abort cleared);
        False otherwise (no pending abort, wrong family, or window
        expired).
        """
        if self._pending_abort is None:
            return False
        if (imp.intent_family or "") != VETO_INTENT_FAMILY:
            return False
        if self._now_fn() > self._pending_abort.veto_deadline_at:
            log.info(
                "veto arrived after deadline (%.2fs late); abort stays committed",
                self._now_fn() - self._pending_abort.veto_deadline_at,
            )
            return False
        log.info(
            "operator veto cancelled abort %r within %.2fs",
            self._pending_abort.predicate_name,
            self._now_fn() - self._pending_abort.triggered_at,
        )
        self._pending_abort = None
        return True

    def commit_abort(self) -> AbortDecision | None:
        """Resolve a pending abort if its veto window has expired.

        Returns the committed AbortDecision (and clears state) when the
        deadline has passed; returns ``None`` when there's no pending
        abort OR when we're still in the veto window.
        """
        if self._pending_abort is None:
            return None
        if self._now_fn() < self._pending_abort.veto_deadline_at:
            return None
        decision = self._pending_abort
        self._pending_abort = None
        return decision

    def register(self, name: str, fn: PredicateFn) -> None:
        """Add or replace a predicate at runtime.

        Production wiring constructs the evaluator with predicates pre-
        registered; tests + the operator's "wire a new predicate live"
        affordance use this entry point.
        """
        self._predicates[name] = fn

    def registered_names(self) -> tuple[str, ...]:
        """Stable snapshot of currently registered predicate names."""
        return tuple(sorted(self._predicates))


__all__ = [
    "DEFAULT_VETO_WINDOW_S",
    "VETO_INTENT_FAMILY",
    "AbortDecision",
    "AbortEvaluator",
    "PredicateFn",
    "PredicateRegistry",
]
