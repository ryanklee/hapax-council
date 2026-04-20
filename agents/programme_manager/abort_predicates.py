"""Abort predicates registry — Phase 10 / B3 Critical #3.

Five named abort predicates the planner can compose into
``ProgrammeSuccessCriteria.abort_predicates``. Each predicate maps a
programme + perceptual snapshot to a boolean: True means "this
programme should abort now."

Per the audit's Critical #3 finding, the abort_evaluator was shipping
with zero registered predicates, so live-stream programmes could
never abort even when their abort_predicates list named one. This
module ships the contract + a starter registry; production wires
real perception sources (IR presence, VLA pressure, consent registry,
vinyl platter state, STT transcript) into each via a small
adapter callable.

Each predicate's signature is ``(programme, snapshot) -> bool``,
matching the AbortPredicateFn type the evaluator expects. The
``snapshot`` argument is intentionally untyped — production passes a
dict assembled from /dev/shm reads; tests pass dicts with mocked
fields. Predicates that can't read their data source (file missing,
import failure) return False (fail-open: when in doubt, do not abort).

References:
- Plan: docs/superpowers/plans/2026-04-20-programme-layer-plan.md §Phase 10
- Audit: docs/superpowers/audits/2026-04-20-3h-work-audit-remediation.md (B3 / Critical #3)
- Sister module: agents/programme_manager/abort_evaluator.py (consumer)
- Predicate naming: plan §Phase 10 lines 1011-1018
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)


# Type alias matching abort_evaluator.PredicateFn — kept locally so
# this module has no dependency cycle with the evaluator module.
AbortPredicateFn = Callable[[Any, Any], bool]


# ── Threshold defaults ────────────────────────────────────────────────

# Match plan §Phase 10 line 1011-1014 ("for_10min", "above_0.8_for_3min").
# Exposed as constants so production wiring can override per-deployment.
DEFAULT_OPERATOR_AWAY_S: float = 600.0  # 10 min
DEFAULT_PRESSURE_THRESHOLD: float = 0.8
DEFAULT_PRESSURE_DURATION_S: float = 180.0  # 3 min
DEFAULT_CONSENT_GRACE_S: float = 0.0  # expired = strictly past now


# ── Predicate implementations ─────────────────────────────────────────


def operator_left_room_for_10min(programme: Any, snapshot: Any) -> bool:
    """True iff the IR presence gauge has read 0 for >= 10 min.

    Snapshot fields (production wiring populates these from
    /dev/shm/hapax-ir/presence.json + a per-process timer):
      - ``ir_present`` (bool): latest presence reading
      - ``ir_absent_since_s`` (float | None): how long the gauge has
        been zero; None means "currently present"

    Conservative posture: missing fields → False (don't abort on
    sensor uncertainty). The 10-minute threshold matches the plan's
    operator-walked-away-from-stream cadence.
    """
    if not isinstance(snapshot, dict):
        return False
    if snapshot.get("ir_present") is True:
        return False
    absent_for = snapshot.get("ir_absent_since_s")
    if not isinstance(absent_for, (int, float)):
        return False
    return float(absent_for) >= DEFAULT_OPERATOR_AWAY_S


def impingement_pressure_above_0_8_for_3min(programme: Any, snapshot: Any) -> bool:
    """True iff VLA pressure has been >= 0.8 for >= 3 min continuously.

    Snapshot fields:
      - ``vla_pressure`` (float): current VLA pressure 0..1
      - ``vla_pressure_above_threshold_since_s`` (float | None): how
        long pressure has been above ``DEFAULT_PRESSURE_THRESHOLD``;
        None means "currently below"

    Conservative: if either field missing or types mismatch → False.
    """
    if not isinstance(snapshot, dict):
        return False
    pressure = snapshot.get("vla_pressure")
    if not isinstance(pressure, (int, float)) or float(pressure) < DEFAULT_PRESSURE_THRESHOLD:
        return False
    duration = snapshot.get("vla_pressure_above_threshold_since_s")
    if not isinstance(duration, (int, float)):
        return False
    return float(duration) >= DEFAULT_PRESSURE_DURATION_S


def consent_contract_expired(programme: Any, snapshot: Any) -> bool:
    """True iff the active consent contract for the programme's role has expired.

    Snapshot fields:
      - ``consent_contracts`` (dict | None): map role → expiry epoch.
        None / missing → False (no contracts known, don't abort).

    Production wiring populates this from ``axioms/contracts/`` via
    ``shared/consent.ConsentRegistry``. Conservative: when the
    snapshot omits the role's entry, treat as still-valid (no abort).
    """
    if not isinstance(snapshot, dict):
        return False
    contracts = snapshot.get("consent_contracts")
    if not isinstance(contracts, dict):
        return False
    role = getattr(programme, "role", None)
    if role is None:
        return False
    expiry = contracts.get(str(role))
    if not isinstance(expiry, (int, float)):
        return False
    now = snapshot.get("now_epoch")
    if not isinstance(now, (int, float)):
        return False
    return float(now) > float(expiry) + DEFAULT_CONSENT_GRACE_S


def vinyl_side_a_finished(programme: Any, snapshot: Any) -> bool:
    """True iff the vinyl-platter ward reports tail-in (track ended).

    Snapshot fields:
      - ``vinyl_side`` (str | None): "A" or "B"
      - ``vinyl_tail_in`` (bool): True when the platter has finished
        playing the side currently spinning

    Only fires for Side A — Side B finishing is a different programme
    decision (full-record-done, not side-flip-due). Conservative when
    fields missing.
    """
    if not isinstance(snapshot, dict):
        return False
    if snapshot.get("vinyl_side") != "A":
        return False
    return bool(snapshot.get("vinyl_tail_in", False))


def operator_voice_contradicts_programme_intent(programme: Any, snapshot: Any) -> bool:
    """True iff recent operator STT contradicts the programme's narrative_beat.

    Snapshot fields:
      - ``recent_stt`` (str | None): aggregated transcript of last
        ~30 s of operator speech
      - ``contradiction_score`` (float | None): pre-computed grounded
        LLM score; production populates this via the ``coding`` tier
        per plan §Phase 10 (must be a grounded model — abort decisions
        are governance moves)

    Conservative: missing score → False. The contradiction threshold
    is fixed at >= 0.7 (high confidence the operator is rejecting the
    programme's frame). Programmes without a narrative_beat default
    to never-firing this predicate (no frame to contradict).
    """
    if not isinstance(snapshot, dict):
        return False
    narrative_beat = getattr(getattr(programme, "content", None), "narrative_beat", None)
    if not narrative_beat:
        return False
    score = snapshot.get("contradiction_score")
    if not isinstance(score, (int, float)):
        return False
    return float(score) >= 0.7


# ── Registry ──────────────────────────────────────────────────────────


# Authoritative map of predicate-name → implementation. Caller
# (production daimonion startup, ProgrammeManager construction) hands
# this dict to the AbortEvaluator's predicates= argument.
DEFAULT_ABORT_PREDICATES: dict[str, AbortPredicateFn] = {
    "operator_left_room_for_10min": operator_left_room_for_10min,
    "impingement_pressure_above_0.8_for_3min": impingement_pressure_above_0_8_for_3min,
    "consent_contract_expired": consent_contract_expired,
    "vinyl_side_a_finished": vinyl_side_a_finished,
    "operator_voice_contradicts_programme_intent": operator_voice_contradicts_programme_intent,
}


def get_default_abort_predicates() -> dict[str, AbortPredicateFn]:
    """Return a mutable copy of the default registry.

    Production callers can extend or override individual predicates
    before passing the dict to AbortEvaluator. Returning a copy
    prevents accidental mutation of the module-level registry.
    """
    return dict(DEFAULT_ABORT_PREDICATES)


__all__ = [
    "DEFAULT_ABORT_PREDICATES",
    "DEFAULT_CONSENT_GRACE_S",
    "DEFAULT_OPERATOR_AWAY_S",
    "DEFAULT_PRESSURE_DURATION_S",
    "DEFAULT_PRESSURE_THRESHOLD",
    "AbortPredicateFn",
    "consent_contract_expired",
    "get_default_abort_predicates",
    "impingement_pressure_above_0_8_for_3min",
    "operator_left_room_for_10min",
    "operator_voice_contradicts_programme_intent",
    "vinyl_side_a_finished",
]
