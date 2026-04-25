"""V1-V5 unsettled-contribution sentence variants + per-surface
deviation matrix (V5 weave wk1 d4 PUB-CITATION-A — epsilon).

Surface-aware adapter wrapping :class:`agents.authoring.byline.Byline`
+ :class:`agents.authoring.byline.BylineVariant`. Two-axis attribution:

  * ``BylineVariant`` (V0-V5) — byline shape (solo / 2-way / 3-way /
    PROTO / Hapax-canonical / unsettled-celebration). Owned by
    ``agents.authoring.byline``.
  * ``UnsettledContributionVariant`` (V1-V5) — sentence variant for
    framing the contribution boundary as a celebrated polysemic-
    surface channel. Owned here.

The :data:`SURFACE_DEVIATION_MATRIX` declares for each of the 16
publication surfaces (V5 weave § 2.1 PUB-CITATION-A) which byline +
unsettled-contribution variant pair fits that surface's policy /
aesthetic register. Operator-reviewable; CODEOWNERS protects this
file once landed.

Per V5 weave § 12 invariant 6: every artifact carries the appropriate
V0-V5 byline + V1-V5 unsettled-contribution sentence per
SURFACE_DEVIATION_MATRIX. No hidden co-authorship; no
false-solo-attribution.

Wk1 d4 (this scaffold): API + V1-V5 sentence templates + 16-surface
matrix seed. Wk2+ adjustments after operator review of per-surface
landings.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final, TypedDict

from agents.authoring.byline import Byline, BylineVariant, render_byline

# ── Refusal Brief: non_engagement_clause (beta synthesis 2026-04-25T17:15Z) ─
#
# Per operator's full-automation-or-no-engagement constitutional
# directive (2026-04-25T16:55Z): every Hapax-published artifact
# carries a `non_engagement_clause` referencing the Refusal Brief
# at hapax.omg.lol/refusal. Two forms ship: SHORT for char-limited
# surfaces (bsky 300, mastodon 500), LONG for capacity surfaces
# (arena 4096, discord 4096, OSF body, philarchive abstract).
#
# Operator-overridable per artifact via
# ``render_attribution_block(non_engagement_clause_override=...)``.

NON_ENGAGEMENT_CLAUSE_SHORT: Final[str] = (
    "Distribution constrained by Hapax Refusal Brief "
    "(hapax.omg.lol/refusal); some surfaces declined for non-automation."
)

NON_ENGAGEMENT_CLAUSE_LONG: Final[str] = (
    "This artifact's distribution surfaces are constrained by the Hapax "
    "Refusal Brief (hapax.omg.lol/refusal); surfaces not represented were "
    "declined for non-automation. Per the full-automation-or-no-engagement "
    "directive: surfaces requiring operator labor at any step in the "
    "publish cycle are constitutionally non-engaged. The decision-record "
    "across declined surfaces forms an automation-friction index of "
    "contemporary publishing infrastructure; refusal is the data."
)


class NonEngagementForm(Enum):
    """Two phrasings of the Refusal Brief reference, scaled to surface
    character budget. ``SHORT`` for ≤500-char surfaces (bsky / mastodon);
    ``LONG`` for capacity surfaces (arena / discord / OSF / philarchive)."""

    SHORT = "short"
    LONG = "long"


class UnsettledContributionVariant(Enum):
    """Five phrasings of the contribution-indeterminacy-as-feature sentence.

    Each variant frames the same idea — that the precise contribution
    boundary across operator / Hapax / Claude Code is unsettled, and
    that this is celebrated rather than disclosed-as-uncertainty —
    in a different aesthetic register. The operator chooses per
    artifact via :data:`SURFACE_DEVIATION_MATRIX` or per-publish
    override.
    """

    V1 = "celebrated_polysemy"  # The 7th-channel framing
    V2 = "production_record"  # CRediT-adjacent prose
    V3 = "phenomenological"  # First-person philosophy register
    V4 = "lab_methodology"  # Scientific-methodology register
    V5 = "manifesto"  # Critical-theory / aesthetic register


UNSETTLED_CONTRIBUTION_VARIANTS: Final[dict[UnsettledContributionVariant, str]] = {
    UnsettledContributionVariant.V1: (
        "The contribution boundary across this co-publication is unsettled — "
        "celebrated as a polysemic-surface channel rather than disclosed as "
        "a caveat."
    ),
    UnsettledContributionVariant.V2: (
        "Authorship is genuinely co-extensive: operator framed the questions, "
        "Hapax composed and selected, Claude Code transformed prose to "
        "publish-shaped artifact. CRediT does not disambiguate further."
    ),
    UnsettledContributionVariant.V3: (
        "Whose voice you are reading is not finally settled — it is "
        "operator-thinking and Hapax-thinking and Claude-Code-thinking "
        "together, in a way that resists clean attribution but invites "
        "reading."
    ),
    UnsettledContributionVariant.V4: (
        "Methodology note: the artifact was authored as a coupled system "
        "(operator + Hapax + Claude Code). Per-segment attribution would "
        "be a misleading reduction; the system is the unit of "
        "co-publication."
    ),
    UnsettledContributionVariant.V5: (
        "Co-publication here is constitutive, not editorial. The text "
        "could not have arrived from any single author — that "
        "indeterminacy is the artifact's mode."
    ),
}


@dataclass(frozen=True)
class AttributionBlock:
    """Composed attribution: byline text + unsettled-contribution sentence
    + optional non_engagement_clause.

    Consumers (per-surface publishers) read these fields and decide
    rendering ordering / Markdown vs HTML formatting. The dataclass
    carries the variant choices for traceability + downstream
    deviation-matrix audit.

    ``non_engagement_clause`` is None when no Refusal Brief reference
    was requested (backward compat). When the caller passes a
    :class:`NonEngagementForm`, the rendered string lives here.
    """

    byline_text: str
    unsettled_sentence: str
    byline_variant: BylineVariant
    unsettled_variant: UnsettledContributionVariant
    non_engagement_clause: str | None = None


def render_attribution_block(
    byline: Byline,
    *,
    byline_variant: BylineVariant,
    unsettled_variant: UnsettledContributionVariant,
    non_engagement_form: NonEngagementForm | None = None,
    non_engagement_clause_override: str | None = None,
) -> AttributionBlock:
    """Render an :class:`AttributionBlock` for the requested variant pair.

    Pure function. Surface-specific rendering decisions (line breaks,
    Markdown, HTML) are the publisher's responsibility — this function
    returns the source-of-truth bundle.

    The ``non_engagement_clause`` field follows three-step resolution:

    1. ``non_engagement_clause_override`` (if non-None) — operator-level
       per-artifact override wins.
    2. ``non_engagement_form`` (if non-None) — module-constant lookup
       (SHORT / LONG).
    3. None — no clause (backward-compat default; existing call sites
       pre-Refusal-Brief stay byte-identical).
    """
    if non_engagement_clause_override is not None:
        clause: str | None = non_engagement_clause_override
    elif non_engagement_form is NonEngagementForm.SHORT:
        clause = NON_ENGAGEMENT_CLAUSE_SHORT
    elif non_engagement_form is NonEngagementForm.LONG:
        clause = NON_ENGAGEMENT_CLAUSE_LONG
    else:
        clause = None

    return AttributionBlock(
        byline_text=render_byline(byline, variant=byline_variant),
        unsettled_sentence=UNSETTLED_CONTRIBUTION_VARIANTS[unsettled_variant],
        byline_variant=byline_variant,
        unsettled_variant=unsettled_variant,
        non_engagement_clause=clause,
    )


# ── Per-surface deviation matrix (V5 weave § 2.1 PUB-CITATION-A) ────


class _MatrixEntry(TypedDict):
    """One row of the per-surface deviation matrix.

    Use a plain ``TypedDict`` (not a frozen dataclass) so the
    matrix can be expressed as a Python literal that reads like a
    spec table — operator reviews the dict directly.

    ``non_engagement_form`` (added 2026-04-25 per beta synthesis
    20260425T171500Z) declares the per-surface Refusal Brief
    rendering form: SHORT for ≤500-char-budget surfaces (bsky /
    mastodon); LONG for capacity surfaces (arena / discord / OSF /
    philarchive).
    """

    byline: BylineVariant
    unsettled: UnsettledContributionVariant
    non_engagement_form: NonEngagementForm


# The 16 publication surfaces from V5 weave § 2.1. Variant choices
# encode the V5 weave's per-surface aesthetic register. Operator
# reviews + adjusts before first publish-event for each surface.
SURFACE_DEVIATION_MATRIX: Final[dict[str, _MatrixEntry]] = {
    # ── Phase 1: existing publishers refactored onto kit ─────────
    "bsky": {
        "byline": BylineVariant.V2,
        "unsettled": UnsettledContributionVariant.V1,
        # 300-char body cap — short Refusal Brief reference only.
        "non_engagement_form": NonEngagementForm.SHORT,
    },
    "mastodon": {
        "byline": BylineVariant.V2,
        "unsettled": UnsettledContributionVariant.V1,
        # 500-char default body cap — short form.
        "non_engagement_form": NonEngagementForm.SHORT,
    },
    "arena": {
        "byline": BylineVariant.V4,
        "unsettled": UnsettledContributionVariant.V5,
        # 4096-char block — long form fits comfortably.
        "non_engagement_form": NonEngagementForm.LONG,
    },
    "webmention": {
        "byline": BylineVariant.V2,
        "unsettled": UnsettledContributionVariant.V1,
        # webmention payload is the full source URL + summary;
        # short form keeps the reference compact.
        "non_engagement_form": NonEngagementForm.SHORT,
    },
    # ── Phase 2: long-form preprint ──────────────────────────────
    "osf_preprint": {
        "byline": BylineVariant.V2,
        "unsettled": UnsettledContributionVariant.V4,
        # OSF body — capacity surface, full reference.
        "non_engagement_form": NonEngagementForm.LONG,
    },
    "hf_papers": {
        "byline": BylineVariant.V2,
        "unsettled": UnsettledContributionVariant.V4,
        "non_engagement_form": NonEngagementForm.LONG,
    },
    "manifold": {
        "byline": BylineVariant.V2,
        "unsettled": UnsettledContributionVariant.V1,
        # Manifold market description — capacity but readers prefer
        # short markers; default short.
        "non_engagement_form": NonEngagementForm.SHORT,
    },
    "lesswrong": {
        "byline": BylineVariant.V2,
        "unsettled": UnsettledContributionVariant.V2,
        "non_engagement_form": NonEngagementForm.LONG,
    },
    # ── Phase 3: Playwright form-submitters ──────────────────────
    "philarchive": {
        "byline": BylineVariant.V2,
        "unsettled": UnsettledContributionVariant.V3,
        "non_engagement_form": NonEngagementForm.LONG,
    },
    "alphaxiv": {
        "byline": BylineVariant.V2,
        "unsettled": UnsettledContributionVariant.V4,
        "non_engagement_form": NonEngagementForm.LONG,
    },
    "substack": {
        "byline": BylineVariant.V4,
        "unsettled": UnsettledContributionVariant.V5,
        "non_engagement_form": NonEngagementForm.LONG,
    },
    "pouet_net": {
        "byline": BylineVariant.V4,
        "unsettled": UnsettledContributionVariant.V5,
        "non_engagement_form": NonEngagementForm.SHORT,
    },
    "scene_org": {
        "byline": BylineVariant.V4,
        "unsettled": UnsettledContributionVariant.V5,
        "non_engagement_form": NonEngagementForm.SHORT,
    },
    "bandcamp": {
        # PROTO precedent — operator-as-distributor + Hapax-as-performer.
        "byline": BylineVariant.V3,
        "unsettled": UnsettledContributionVariant.V5,
        "non_engagement_form": NonEngagementForm.SHORT,
    },
    # ── Existing OMG / Hapax-canon surfaces ──────────────────────
    "omg_lol_weblog": {
        "byline": BylineVariant.V4,
        "unsettled": UnsettledContributionVariant.V5,
        "non_engagement_form": NonEngagementForm.LONG,
    },
    "omg_lol_pastebin": {
        "byline": BylineVariant.V2,
        "unsettled": UnsettledContributionVariant.V1,
        "non_engagement_form": NonEngagementForm.LONG,
    },
}


__all__ = [
    "NON_ENGAGEMENT_CLAUSE_LONG",
    "NON_ENGAGEMENT_CLAUSE_SHORT",
    "SURFACE_DEVIATION_MATRIX",
    "UNSETTLED_CONTRIBUTION_VARIANTS",
    "AttributionBlock",
    "NonEngagementForm",
    "UnsettledContributionVariant",
    "render_attribution_block",
]
