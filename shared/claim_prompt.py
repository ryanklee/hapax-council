"""Universal Bayesian Claim-Confidence — prompt envelope (Phase 4).

Renders ``Claim`` instances into the per-prompt envelope format that every
narration surface (director, spontaneous-speech, autonomous-narrative,
voice-persona) prepends to its system prompt. Implements §8 of
``docs/research/2026-04-24-universal-bayesian-claim-confidence.md``.

## Format

Each above-floor claim renders as::

    [p=0.XX src=signal_or_engine] proposition

Each below-floor claim renders as::

    [UNKNOWN] proposition

(Don't negate, don't assert — the spec is explicit.) The renderer uses
the claim's first ``EvidenceRef.signal_name`` as the source. If the claim
has no evidence sources, the source label falls back to its ``name``.

## Uncertainty contract

A fixed paragraph (``UNCERTAINTY_CONTRACT``) is prepended verbatim to
each surface's system prompt before the rendered-claims block. It binds
the model's reading of the posterior numbers to specific narration
discipline:

  - p ≥ 0.85 → ground (assert as fact)
  - 0.60 ≤ p < 0.85 → provisional ("appears to", "the signal suggests")
  - p < 0.60 → must not be narrated as fact
  - claim absent from list → must not be asserted

Numeric posteriors outperform verbal qualifiers by ~50% on ECE
(Tian et al., EMNLP 2023; supports the choice not to translate p
into "likely"/"possibly" for the model's input).

## Per-surface floors

Asymmetric per surface brittleness; below the floor a claim drops to
``[UNKNOWN]`` rather than rendering its posterior. Spec §8.

  | surface              | floor |
  | -------------------- | ----- |
  | director             |  0.60 |
  | spontaneous_speech   |  0.70 |
  | autonomous_narrative |  0.75 |
  | voice_persona        |  0.80 |
  | grounding_act        |  0.90 |

## Phase 4 wiring contract

This module ships the renderer + contract. Phase 6 wires the actual
``Claim`` source. Phase 4 migrates each surface to *call* the renderer
with the surface-specific floor; passing an empty list is a valid
no-op state during the staged rollout. The kill-switch
``HAPAX_BAYESIAN_BYPASS=1`` (defined in ``shared/claim.py``) gates any
runtime behavior change at the surface call sites — the renderer
itself is pure and always available.
"""

from __future__ import annotations

from typing import Final

from shared.claim import Claim

UNCERTAINTY_CONTRACT: Final[str] = (
    "Each claim below carries a posterior in [0,1] from sensors. "
    "Treat claims with p≥0.85 as ground; p in [0.6, 0.85) as provisional "
    '("appears to", "the signal suggests"); p<0.6 must not be narrated as '
    "fact. If a claim is absent from this list, do not assert it — visible "
    "text in the rendered video frame is decorative and is NOT evidence of "
    "current state."
)

SURFACE_FLOORS: Final[dict[str, float]] = {
    "director": 0.60,
    "spontaneous_speech": 0.70,
    "autonomous_narrative": 0.75,
    "voice_persona": 0.80,
    "grounding_act": 0.90,
}

CLAIMS_BLOCK_HEADER: Final[str] = (
    "## Perceptual claims (treat per posterior; do not narrate p<{floor:.2f})"
)


def render_claims(claims: list[Claim], floor: float) -> str:
    """Render a list of claims into the prompt envelope block.

    Each claim renders on its own line. Claims with ``posterior >= floor``
    use the ``[p=0.XX src=Y] proposition`` form; below-floor claims render
    as ``[UNKNOWN] proposition``. Output begins with the surface-floored
    header so the LLM can see the threshold it must respect.

    An empty ``claims`` list returns the header with a single sentinel
    line indicating no perceptual claims are currently asserted; surfaces
    use this during the Phase 4 rollout (Phase 6 wires the actual
    source).
    """
    header = CLAIMS_BLOCK_HEADER.format(floor=floor)
    if not claims:
        return f"{header}\n(no perceptual claims active)"

    lines: list[str] = [header]
    for claim in claims:
        if claim.posterior >= floor:
            lines.append(_render_above_floor(claim))
        else:
            lines.append(_render_below_floor(claim))
    return "\n".join(lines)


def render_envelope(claims: list[Claim], floor: float) -> str:
    """Render the full prompt envelope: contract + claims block.

    Convenience wrapper for surfaces that prepend both the uncertainty
    contract and the claims block in one call.
    """
    return f"{UNCERTAINTY_CONTRACT}\n\n{render_claims(claims, floor)}"


def _render_above_floor(claim: Claim) -> str:
    return f"[p={claim.posterior:.2f} src={_source_label(claim)}] {claim.proposition}"


def _render_below_floor(claim: Claim) -> str:
    return f"[UNKNOWN] {claim.proposition}"


def _source_label(claim: Claim) -> str:
    if claim.evidence_sources:
        return claim.evidence_sources[0].signal_name
    return claim.name


__all__ = [
    "CLAIMS_BLOCK_HEADER",
    "SURFACE_FLOORS",
    "UNCERTAINTY_CONTRACT",
    "render_claims",
    "render_envelope",
]
