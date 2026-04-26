# Architecture: leverage-attrib-arxiv-velocity-preprint

**Authored:** 2026-04-26 by alpha
**cc-task:** `leverage-attrib-arxiv-velocity-preprint` (WSJF 8.0)
**Related refusal:** `docs/refusal-briefs/leverage-arxiv-institutional-shortcut.md` (the institutional-email shortcut closed by arXiv Jan 2026; this is the daemon-tractable replacement path)

## Goal

Daemon-tractable arXiv preprint flow for the operator's velocity findings, gated only on endorser-courtship (the only path arXiv accepts post-Jan 2026 for first-time submitters in CS-AI/cs.HC and similar categories the operator has presence in). Honors `feedback_full_automation_or_no_engagement`: every step is daemon-side; operator's role is the consent gate at the end.

## Existing infrastructure (audit)

| Component | Path | Status |
|---|---|---|
| Cold-contact candidate registry | `agents/cold_contact/candidate_registry.py` | Shipped — Pydantic CandidateEntry + 14-vector AUDIENCE_VECTORS controlled vocab. **No email/telephone fields by design** (direct outreach REFUSED) |
| ORCID validator | `agents/cold_contact/orcid_validator.py` | Shipped — validates entries against ORCID public API |
| Citation-graph touch policy | `agents/cold_contact/graph_touch_policy.py` | Shipped — ≤5 candidates/deposit, ≤3/year/candidate cap, JSONL touch log |
| Zenodo RelatedIdentifier graph | `agents/publication_bus/related_identifier.py` | Shipped — DataCite RelatedIdentifier dataclass + 6 RelationType + 7 IdentifierType |
| ORCID verifier (operator-side) | `agents/publication_bus/orcid_verifier.py` | Shipped — daily verification of operator ORCID against minted concept-DOIs |
| DataCite citation-graph snapshot | `agents/attribution/datacite_graphql_snapshot.py` | Shipped — nightly snapshot around DOI/SWHID/ORCID nodes |
| Zenodo community submitter | `agents/publication_bus/community_submitter.py` | Phase 1 shipped (submit-only client + community taxonomy); Phase 2 daemon path pending |

## Missing components (this cc-task delivers)

| Component | Path | Effort | Order |
|---|---|---|---|
| **Endorser discovery** | `agents/cold_contact/endorser_discovery.py` (new) | 4-6h | 1 |
| Endorsement-request artifact composer | `agents/publication_bus/arxiv_endorser_request.py` (new) | 2-3h | 2 |
| Velocity-findings preprint manuscript | `docs/preprints/2026-04-velocity-findings.md` (new) | 8-12h authoring | 3 (operator-gateable) |
| Daemon: endorser-discovery → graph-touch-policy → publish-bus | `agents/cold_contact/endorser_courtship_daemon.py` (new) | 4-6h | 4 |
| Acceptance smoke: integration test against Zenodo sandbox | `tests/integration/test_arxiv_endorser_flow.py` (new) | 2-3h | 5 |
| systemd unit + drop-in for daemon | `systemd/units/hapax-arxiv-endorser-courtship.{service,timer}` (new) | 30 min | 6 (post-daemon) |

**Total daemon scope:** ~13-19h across 5 PRs (excluding manuscript authoring).

## Endorser-discovery design

**Input:** operator's audience-vector classification (already in `candidate_registry.AUDIENCE_VECTORS`). For velocity findings, target category is `cs.HC` + `cs.AI` (HCI + AI/ML), with `cs.SE` (software engineering) overlap.

**Discovery sources:**
1. **DataCite Commons GraphQL** — query for arxiv DOIs in target category, last 90 days. Already-shipped client at `agents/publication_bus/datacite_mirror.py`.
2. **ORCID public API** — for each unique author DOI, resolve ORCID iD and last activity timestamp. Already-shipped helpers at `agents/publication_bus/orcid_verifier.py`.
3. **arXiv API** — confirm contributor status in target category. Read-only, unauthenticated. New helper: `_arxiv_check_contributor()` in `endorser_discovery.py`.

**Filter:** active contributors (≥1 paper last 12 months in target category) AND not already in `~/hapax-state/cold-contact/touches.jsonl` within `graph_touch_policy.MIN_REVISIT_YEARS`.

**Output:** ranked candidate list (by recent-activity + topic-overlap) written to `~/hapax-state/cold-contact/arxiv-endorser-candidates.json`. Capped at 20 candidates per cycle (downstream `graph_touch_policy` enforces ≤5/deposit + ≤3/year caps).

## Endorsement-request artifact

The endorser is contacted **only via citation-graph signal**, never by direct email (consistent with existing `cold_contact` family-wide stance). The artifact is a **publicly-deposited Zenodo record** with `RelatedIdentifier` edges pointing AT the endorser's existing arxiv works (`References` relation type) — the citation-graph touch is the courtship.

`ArxivEndorserRequest` (subclass of `PublisherKit.PublisherBase`):
- ClassVar metadata: `slug = "leverage-arxiv-velocity-endorser"`, `tier = CONDITIONAL_ENGAGE` (operator initiates; daemon assembles)
- `_emit()` writes:
  - One Zenodo deposit per endorser candidate, with `Related identifier (References)` to the endorser's most-recent paper DOI
  - Title: "Velocity-finding cross-reference (potential arXiv endorser: <ORCID>)"
  - Description: short acknowledgement of the cross-referenced work + brief context (1 paragraph, <500 chars)
  - Composes via `RefusalFooterInjector` so the standard non-engagement clause is included
- Logs to `~/hapax-state/cold-contact/touches.jsonl` so `graph_touch_policy` can enforce caps

**The endorsement REQUEST itself** (when the operator chooses to formally request endorsement) goes through the standard arXiv endorsement form, operator-mediated. The daemon's role ends at the citation-graph relationship signal; operator decides which endorser to formally ask.

## Constitutional posture

- `feedback_full_automation_or_no_engagement`: every step daemon-tractable; operator gates only at the end (formal endorsement request)
- `interpersonal_transparency`: candidate registry has no email/telephone fields; cross-reference artifacts are public
- `single_user`: operator is the only formal-action actor
- Refusal-as-data on missing arXiv account / ORCID: graceful no-op + ntfy

## Sequencing for shipping

Current PR: this architecture doc (deliverable 0).

Next PRs (alpha-routable, ~19h total):
1. `feat(cold-contact): endorser_discovery.py + tests`
2. `feat(publication-bus): arxiv_endorser_request publisher`
3. `feat(cold-contact): courtship daemon + systemd unit + timer`
4. `test(integration): arxiv-endorser-flow against Zenodo sandbox`

Manuscript authoring (deliverable 3) is operator-mediated drafting — daemon doesn't write the velocity-findings paper itself, but it can compose first-draft scaffolding from the existing `docs/research/2026-04-25-velocity-comparison.md` + sprint measure data + Bayesian validation results. Filing as separate cc-task `velocity-findings-manuscript-draft`.

## Cross-references

- Velocity comparison source data: `docs/research/2026-04-25-velocity-comparison.md`
- Refusal of institutional-email shortcut: `docs/refusal-briefs/leverage-arxiv-institutional-shortcut.md`
- V5 publication bus surface registry: `agents/publication_bus/surface_registry.py`
- Cold-contact graph touch policy: `agents/cold_contact/graph_touch_policy.py`

— alpha
