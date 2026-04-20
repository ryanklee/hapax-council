"""MonetizationRiskGate — zero-red-flag content invariant (task #165).

Gates candidate capabilities against YouTube monetization risk BEFORE the
affordance pipeline scores them. Sits adjacent to the consent gate in
``shared.affordance_pipeline.AffordancePipeline.select``.

Risk levels (matched on ``OperationalProperties.monetization_risk``):

- **high**: unconditionally blocked on every surface
- **medium**: blocked unless the active ``Programme`` opts the capability
  in via ``Programme.constraints.monetization_opt_ins``
- **low** / **none**: pass through the filter unchanged

The filter is pure (no side effects, no network, no state) in its
Ring-1-only mode. Optional Ring 2 integration (Phase 3) calls an
LLM classifier on the rendered payload and merges the verdict — Ring 2
can ESCALATE the risk but never DE-ESCALATE it (catalog is authoritative
on the floor; Ring 2 catches rendered-payload specifics the catalog
cannot foresee).

References:
    - docs/research/2026-04-19-demonetization-safety-design.md §1, §4
    - docs/superpowers/plans/2026-04-20-demonetization-safety-plan.md §2, §3
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal, Protocol

from shared.affordance import MonetizationRisk

# Re-exports for Phase-1 call sites.
__all__ = [
    "MonetizationRisk",
    "MonetizationRiskGate",
    "RiskAssessment",
    "SurfaceKind",
]


class SurfaceKind(StrEnum):
    """Where the rendered output would land if emitted.

    Phase 1 records the surface kind on each filter decision for later
    auditing; Phase 6 wires it into the egress JSONL. Phase 3 uses it to
    pick the classifier prompt.
    """

    TTS = "tts"
    CAPTIONS = "captions"
    CHRONICLE = "chronicle"
    OVERLAY = "overlay"
    WARD = "ward"
    NOTIFICATION = "notification"
    LOG = "log"


@dataclass(frozen=True)
class RiskAssessment:
    """Immutable result of a classification or catalog-lookup decision.

    Used by both the pre-flight capability filter (Ring 1) and the
    pre-render classifier (Ring 2, Phase 3) so both rings emit the same
    shape for downstream audit + quiet-frame logic.
    """

    allowed: bool
    risk: MonetizationRisk
    reason: str
    surface: SurfaceKind | None = None


class _CandidateLike(Protocol):
    """Structural type for AffordancePipeline SelectionCandidates.

    Accepts any object exposing ``capability_name`` and ``payload`` — keeps
    the gate independent of affordance_pipeline's import graph.
    """

    capability_name: str
    payload: dict[str, Any]


class _ProgrammeLike(Protocol):
    """Structural type for the Programme that opts-in medium capabilities.

    Phase 1 only reads ``monetization_opt_ins``. The concrete Programme
    model from ``shared.programme`` does not yet have this field (it
    lands in plan Phase 5 — intentionally so); for now the gate treats
    missing programmes and missing opt-ins identically.
    """

    @property
    def monetization_opt_ins(self) -> set[str]: ...


# Risk ordering used by the Ring 1 ↔ Ring 2 escalation merge. Ring 2 can
# raise the effective risk to the strictest of the two verdicts; it
# cannot drop below the catalog-declared floor.
_RISK_ORDER: dict[str, int] = {"none": 0, "low": 1, "medium": 2, "high": 3}


def _max_risk(a: str, b: str) -> str:
    """Return the stricter of two risk strings."""
    return a if _RISK_ORDER.get(a, 0) >= _RISK_ORDER.get(b, 0) else b


class MonetizationRiskGate:
    """Pure filter — blocks high-risk always, gates medium-risk on programme.

    No I/O, no caching, no logging in the hot path. A separate audit hook
    (Phase 6) will subscribe to the filter's return value without touching
    the filter itself.

    Ring 2 pre-render classification (Phase 3) is opt-in — callers that
    have a rendered payload and want a second-pass verdict pass
    ``ring2_classifier`` + ``surface`` + ``rendered_payload`` to
    ``assess()``. Call sites without those stay on Ring 1 (catalog-only)
    behavior — zero cost, zero behavior change.
    """

    def assess(
        self,
        candidate: _CandidateLike,
        programme: _ProgrammeLike | None = None,
        *,
        ring2_classifier: Any = None,
        surface: SurfaceKind | None = None,
        rendered_payload: Any = None,
    ) -> RiskAssessment:
        """Return a RiskAssessment without mutating state.

        Called from the pipeline's filter step and also available as a
        standalone helper for ad-hoc audits (plan Phases 6, 10).

        Ring 2 integration (optional): when ``ring2_classifier`` and
        ``surface`` are both provided and the surface is a broadcast
        surface, the classifier is invoked on the rendered payload and
        its verdict is merged with the catalog's ring-1 annotation via
        ``max_risk`` (stricter wins). Classifier failures go through
        ``classify_with_fallback`` which applies the fail-closed policy.
        """
        ring1_risk: MonetizationRisk = candidate.payload.get("monetization_risk", "none")
        ring1_reason = candidate.payload.get("risk_reason") or ""
        name = candidate.capability_name

        # Short-circuit: ring-1 high is authoritative — no Ring 2 call,
        # no Programme opt-in path. Saves the GPU round-trip on the
        # capabilities catalog already declares unsafe.
        if ring1_risk == "high":
            return RiskAssessment(
                allowed=False,
                risk=ring1_risk,
                reason=f"{name}: high-risk capability blocked unconditionally ({ring1_reason})".strip(
                    " ()"
                ),
                surface=surface,
            )

        # Ring 2 pass — only when caller opted in + surface is broadcast.
        effective_risk: str = ring1_risk
        ring2_reason = ""
        ring2_used = False
        if ring2_classifier is not None and surface is not None:
            # Deferred imports keep this module dependency-light for
            # callers that never use Ring 2.
            from shared.governance.classifier_degradation import classify_with_fallback
            from shared.governance.ring2_prompts import is_broadcast_surface

            if is_broadcast_surface(surface):
                decision = classify_with_fallback(
                    ring2_classifier,
                    capability_name=name,
                    rendered_payload=rendered_payload,
                    surface=surface,
                )
                ring2_used = True
                ring2_reason = decision.assessment.reason
                # Ring 2 can escalate the risk but never de-escalate —
                # catalog is the floor.
                effective_risk = _max_risk(ring1_risk, decision.assessment.risk)
                # If the fail-closed wrapper fired and blocked, surface
                # that immediately; don't continue through opt-in logic.
                if not decision.assessment.allowed and decision.used_fallback:
                    return RiskAssessment(
                        allowed=False,
                        risk=effective_risk,  # type: ignore[arg-type]
                        reason=f"{name}: ring2 degraded → {ring2_reason}",
                        surface=surface,
                    )

        # Effective-risk-high path: Ring 2 escalated to high.
        if effective_risk == "high":
            return RiskAssessment(
                allowed=False,
                risk=effective_risk,  # type: ignore[arg-type]
                reason=f"{name}: ring2 escalated to high ({ring2_reason})",
                surface=surface,
            )
        if effective_risk == "medium":
            opted_in = False
            if programme is not None:
                opt_ins = getattr(programme, "monetization_opt_ins", None)
                if opt_ins is not None and name in opt_ins:
                    opted_in = True
            if not opted_in:
                detail = (
                    f" (ring2: {ring2_reason})"
                    if ring2_used and ring2_reason and effective_risk != ring1_risk
                    else ""
                )
                return RiskAssessment(
                    allowed=False,
                    risk=effective_risk,  # type: ignore[arg-type]
                    reason=f"{name}: medium-risk capability requires programme opt-in{detail}",
                    surface=surface,
                )
            return RiskAssessment(
                allowed=True,
                risk=effective_risk,  # type: ignore[arg-type]
                reason=f"{name}: medium-risk capability opted in by active programme",
                surface=surface,
            )
        return RiskAssessment(
            allowed=True,
            risk=effective_risk,  # type: ignore[arg-type]
            reason=f"{name}: {effective_risk}-risk capability — passed",
            surface=surface,
        )

    def candidate_filter(
        self,
        candidates: list[_CandidateLike],
        programme: _ProgrammeLike | None = None,
    ) -> list[_CandidateLike]:
        """Return only the candidates that pass the monetization gate.

        Batch helper — Ring 2 is deliberately not wired here because
        the rendered payload differs per candidate. Call ``assess()``
        directly with Ring 2 kwargs when classification is needed.
        """
        return [c for c in candidates if self.assess(c, programme).allowed]


# Phase 1 ships a module-level singleton — the gate is stateless, so a
# single instance costs nothing and prevents accidental drift if callers
# were to construct multiple gates with divergent futures.
GATE = MonetizationRiskGate()


def candidate_filter(
    candidates: list[_CandidateLike],
    programme: _ProgrammeLike | None = None,
) -> list[_CandidateLike]:
    """Module-level convenience for the shared singleton."""
    return GATE.candidate_filter(candidates, programme)


def assess(
    candidate: _CandidateLike,
    programme: _ProgrammeLike | None = None,
) -> RiskAssessment:
    """Module-level convenience for the shared singleton."""
    return GATE.assess(candidate, programme)


# Deliberately unused import — kept only so ``Literal`` remains available
# for Phase 3 RiskAssessment refinements when the classifier lands.
_ = Literal
