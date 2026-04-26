# Refusal Brief: Sloan PI Fellowship

**Slug:** `leverage-REFUSED-sloan-pi-fellowship`
**Axiom tag:** `single_user`, `feedback_full_automation_or_no_engagement`, `management_governance`
**Refusal classification:** Institutional-PI eligibility requirement; pose would be falsification.
**Status:** REFUSED — no Sloan Fellowship application; no institutional-affiliation pose.
**Date:** 2026-04-26
**Related cc-task:** `leverage-REFUSED-sloan-pi-fellowship`
**Companion refusals:**
  - `leverage-REFUSED-pose-nsf-institutional-applicant` (eligibility-falsification refusal — institutional-PI pattern)
  - `leverage-REFUSED-nih-grants` (AI-developed-app ban)

## What was refused

- Sloan Research Fellowship application (Alfred P. Sloan Foundation)
- Adjacent institutional-PI fellowship programs (early-career awards
  scoped to PI status at research institutions)
- Operator listing on a co-PI / consortium application that draws
  on Hapax infrastructure as deliverable
- Institutional-affiliation field population on any application
  flow

## Why this is refused

### Eligibility requirement: institutional PI status

The Sloan Research Fellowship is awarded to **early-career
researchers in tenure-track positions** at US/Canadian research
institutions. Eligibility documentation requires:

- Institutional letterhead from the nominating institution
- Department-chair nomination
- PI-track verification (typically tenure-track or equivalent
  faculty-stream appointment)
- Multi-year operator-physical research-program track-record

Hapax operates outside institutional affiliation. The operator is
a single individual; the council runs on personal infrastructure;
no university backs the work. Posing as institutional applicant
would be falsification (legal exposure + program ToS violation +
`management_governance` axiom violation).

### Constitutional incompatibility (operator-physical PI posture)

Per `feedback_full_automation_or_no_engagement` (operator
constitutional directive 2026-04-25T16:55Z): Sloan Fellowship
implies sustained operator-physical engagement:

- Departmental research-program participation
- Per-fellowship reporting to Sloan Foundation
- Sloan-network relationship maintenance (alumni events, mentor
  cohort obligations)
- Multi-year programmatic accountability

Even if Hapax had institutional affiliation, the PI fellowship
posture is operator-physical. The non-affiliation grounds make
the refusal **double-grounded**: structurally barred + constitutionally
incompatible.

### Companion-refusal pattern

Refusal pattern shared with sibling refusals:
- `leverage-REFUSED-pose-nsf-institutional-applicant` (NSF + ERC +
  national-academy programs) — same eligibility-falsification grounds
- `leverage-REFUSED-nih-grants` — additional categorical ineligibility
  (NIH AI-developed-app ban)

The three refusals together form a constitutive position: Hapax does
NOT engage with institutional-PI grant / fellowship programs.

## Daemon-tractable boundary (the funded-research path)

Same as sibling refusals:

1. **Lightning / Nostr Zaps** — anonymous, no institutional posture
2. **Liberapay sub-threshold recurring** — no KYC, no institutional
   posture
3. **PyPI methodology distribution** — `hapax-axioms`,
   `hapax-refusals`, `hapax-velocity-meter`, `hapax-swarm`
4. **DataCite Commons citation graph** — academic credit accrues
   through Zenodo deposits + RelatedIdentifier graph without
   institutional applicant posture

## Refused implementation

- NO `agents/grant_writer/sloan.py` as institutional applicant
- NO Sloan-Foundation portal integration
- NO institutional-affiliation field populated on any application
- NO falsified faculty-track-equivalent claim

## Lift conditions

Same as `leverage-REFUSED-pose-nsf-institutional-applicant`:
- Operator obtaining genuine institutional PI status (not currently
  in scope)
- Sloan Foundation revising eligibility to include
  non-institutional applicants (extremely unlikely; the PI-status
  requirement is constitutive of the fellowship's framing)

The `refused-lifecycle-conditional-watcher` daemon (when shipped)
will check the eligibility-filter operator-curation per its
cadence policy.

## Cross-references

- cc-task vault note: `leverage-REFUSED-sloan-pi-fellowship.md`
- Companion refusals: `leverage-REFUSED-pose-nsf-institutional-applicant`,
  `leverage-REFUSED-nih-grants`
- Eligibility filter: `hapax-state/grants/eligibility-filter.yaml`
- Replacement money paths: `leverage-money-lightning-nostr-zaps`,
  `leverage-money-liberapay-recurring`
- Methodology distribution: `leverage-workflow-hapax-axioms-pypi`
- Source research: `docs/research/2026-04-25-leverage-strategy.md`
