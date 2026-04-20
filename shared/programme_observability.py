"""Programme-layer Prometheus observability — Phase 9 of the
programme-layer plan (D-28).

Mirror of `shared/director_observability.py` at the programme scale.
Defines 7 metric families covering programme lifecycle (start/end/active/
durations) + the two architectural invariants (candidate-set
preservation + soft-prior-not-hardening).

This module ships the surface now; emit-call wiring lands as
ProgrammeManager (Phase 7) + downstream consumers (Phases 5/6/8) come
online. Pattern matches director_observability: emit functions are
graceful no-ops when prometheus_client is unavailable, so tests + dev
environments can import without a metrics dependency.

Two invariant metrics carry SEMANTIC contracts the rest of the system
must honor:

- ``hapax_programme_candidate_set_reduction_total`` MUST always be 0
  in production. Increments only on a Phase-4 ``_apply_programme_bias``
  bug — see ``shared/affordance_pipeline.py``. Already wired in D-28.
- ``hapax_programme_soft_prior_overridden_total`` MUST be > 0 per
  stream. Soft-prior-not-hardening detector: a programme that never
  gets overridden is acting as a hard gate, which violates the
  ``project_programmes_enable_grounding`` axiom.

References:
- Plan §Phase 9 (`docs/superpowers/plans/2026-04-20-programme-layer-plan.md`)
- Project memory: project_programmes_enable_grounding
- Sister observability surface: shared/director_observability.py
"""

from __future__ import annotations

import logging
from typing import Any, Literal

log = logging.getLogger(__name__)

# Programme-end reasons. Aligned with plan §Phase 9 line 914-915.
EndReason = Literal["planned", "operator", "emergent", "aborted"]

_METRICS_AVAILABLE = False

try:
    from prometheus_client import Counter, Gauge

    _programme_start_total = Counter(
        "hapax_programme_start_total",
        "Programmes started, labelled by role + show.",
        ("role", "show_id"),
    )
    _programme_end_total = Counter(
        "hapax_programme_end_total",
        ("Programmes ended, labelled by role + show + reason (planned|operator|emergent|aborted)."),
        ("role", "show_id", "reason"),
    )
    _programme_active = Gauge(
        "hapax_programme_active",
        "1 iff the labelled programme is the active one (one-hot per role).",
        ("programme_id", "role"),
    )
    _programme_duration_planned = Gauge(
        "hapax_programme_duration_planned_seconds",
        "Planned duration of the labelled programme, in seconds.",
        ("programme_id",),
    )
    _programme_duration_actual = Gauge(
        "hapax_programme_duration_actual_seconds",
        "Actual elapsed duration of the labelled programme, in seconds.",
        ("programme_id",),
    )
    _programme_soft_prior_overridden_total = Counter(
        "hapax_programme_soft_prior_overridden_total",
        (
            "INVARIANT: must be > 0 per stream. Counts cases where a "
            "candidate's composed score overcame programme bias and was "
            "still recruited despite negative bias. Zero rate = soft prior "
            "is acting as hard gate (violates project_programmes_enable_"
            "grounding)."
        ),
        ("programme_id", "reason"),
    )
    # Set-reduction sentinel: defined in shared/governance/demonet_metrics.py
    # so the affordance pipeline's _apply_programme_bias path can increment
    # without a circular import. Imported here for symmetry — same name.

    _METRICS_AVAILABLE = True
except Exception:  # pragma: no cover — prometheus_client missing at install
    log.info("prometheus_client unavailable — programme observability metrics are no-ops")


def emit_programme_start(programme: Any) -> None:
    """Increment start counter + activate gauge for a Programme.

    Programme is structurally typed: needs ``role``, ``programme_id``,
    ``parent_show_id``, ``planned_duration_s``. No exception propagates
    out — the lifecycle path must not break on a metrics failure.
    """
    if not _METRICS_AVAILABLE:
        return
    try:
        role = str(getattr(programme, "role", "unknown"))
        show_id = str(getattr(programme, "parent_show_id", "unknown"))
        programme_id = str(getattr(programme, "programme_id", "unknown"))
        planned = float(getattr(programme, "planned_duration_s", 0.0))
        _programme_start_total.labels(role=role, show_id=show_id).inc()
        _programme_active.labels(programme_id=programme_id, role=role).set(1)
        _programme_duration_planned.labels(programme_id=programme_id).set(planned)
    except Exception:
        log.warning("emit_programme_start failed", exc_info=True)


def emit_programme_end(programme: Any, *, reason: EndReason = "planned") -> None:
    """Increment end counter + deactivate gauge + record actual duration."""
    if not _METRICS_AVAILABLE:
        return
    try:
        role = str(getattr(programme, "role", "unknown"))
        show_id = str(getattr(programme, "parent_show_id", "unknown"))
        programme_id = str(getattr(programme, "programme_id", "unknown"))
        elapsed = getattr(programme, "elapsed_s", None)
        actual = float(elapsed) if elapsed is not None else 0.0
        _programme_end_total.labels(role=role, show_id=show_id, reason=reason).inc()
        _programme_active.labels(programme_id=programme_id, role=role).set(0)
        _programme_duration_actual.labels(programme_id=programme_id).set(actual)
    except Exception:
        log.warning("emit_programme_end failed", exc_info=True)


def emit_soft_prior_override(programme_id: str, reason: str = "high_pressure") -> None:
    """Increment the soft-prior-override counter.

    Called from the affordance pipeline when a candidate scored high
    enough to recruit DESPITE programme bias attempting to attenuate it
    (the spec §5.1 "0.95 cosine × 0.5 bias = 0.475 above threshold"
    case). This is the soft-prior-not-hardening detector — must fire at
    least once per stream per active programme.
    """
    if not _METRICS_AVAILABLE:
        return
    try:
        _programme_soft_prior_overridden_total.labels(
            programme_id=programme_id, reason=reason
        ).inc()
    except Exception:
        log.warning("emit_soft_prior_override failed", exc_info=True)


__all__ = [
    "EndReason",
    "emit_programme_end",
    "emit_programme_start",
    "emit_soft_prior_override",
]
