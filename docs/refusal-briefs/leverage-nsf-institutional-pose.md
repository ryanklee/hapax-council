# Refusal Brief: Posing as NSF Institutional Applicant

**Slug:** `leverage-REFUSED-pose-nsf-institutional-applicant`
**Axiom tag:** `single_user`, `feedback_full_automation_or_no_engagement`, `management_governance`
**Refusal classification:** Eligibility-falsification refusal — multiple grant programs require institutional PI status; pose would be falsification.
**Status:** REFUSED — no NSF application as institutional PI; no institutional-affiliation pose anywhere.
**Date:** 2026-04-26
**Related cc-task:** `leverage-REFUSED-pose-nsf-institutional-applicant`
**Sibling refusals:**
  - `leverage-REFUSED-nih-grants` (categorically ineligible per AI-developed-app ban)
  - `leverage-REFUSED-sloan-pi-fellowship` (operator-physical PI fellowship)

## What was refused

- NSF grant applications listing operator as institutional PI
- ERC, national-academy, or any institutional-PI-required program
  applications
- Any "consortium pose" where Hapax claims affiliation with an
  institution operator does not actually have
- Eligibility filter bypass / misrepresentation in any application
  flow

## Why this is refused

### Eligibility-falsification grounds

NSF, ERC, NIH (separately refused), national-academy programs, and
many institutional-PI grant programs require **verifiable
institutional affiliation**. Hapax operates outside institutional
affiliation: the operator is a single individual, the council
runs on personal infrastructure, no university / lab / nonprofit
backs the work.

Applying as institutional PI without that affiliation is
**falsification**:
- Misrepresentation to the funding agency (criminal-law exposure
  in some jurisdictions)
- Violation of program ToS / certification clauses signed by the
  applicant
- Violation of `management_governance` axiom: "LLMs prepare,
  humans deliver" — but humans cannot deliver a fake institutional
  posture

### Constitutional grounds

Per `feedback_full_automation_or_no_engagement` (operator
constitutional directive 2026-04-25T16:55Z): the operator refuses
funding paths that require operator-physical relationship
management. Institutional-PI status implies:

- Operator-physical institutional credentialing
- Operator-physical PI training / certifications
- Multi-year reporting to the institutional-research-office
- Subaward / consortium-management overhead

Even if Hapax were affiliated with an institution, the
institutional-PI posture would be operator-physical at every step.

### Single-operator axiom

The single-operator axiom precludes maintaining a fake
multi-tenant / institutional-collaboration posture. Hapax is
constitutionally one operator; pretending otherwise to satisfy
program eligibility is incompatible.

## Daemon-tractable boundary (the funded-research path)

Same as the other institutional-grant refusals:

1. **Lightning / Nostr Zaps** — anonymous, no institutional
   credentialing
2. **Liberapay sub-threshold recurring** — no KYC, no institutional
   posture
3. **PyPI methodology distribution** — `hapax-axioms`,
   `hapax-refusals`, `hapax-velocity-meter`, `hapax-swarm`
4. **Citation-graph attribution via DataCite Commons** — academic-
   credit accrues through Zenodo deposits + RelatedIdentifier graph
   without institutional applicant posture

These cover the "doing the research" + "distributing the methodology"
+ "accruing academic credit" angles. Institutional-grant funding is
structurally incompatible.

## Eligibility filter

`hapax-state/grants/eligibility-filter.yaml` (operator-curated)
enforces this refusal at the data layer: programs requiring
institutional-PI status are excluded from any grant-discovery
daemon's candidate-list output.

The filter is operator-curated rather than auto-derived because
program-eligibility language is heterogeneous; manual curation
prevents both false-positive ineligibles ("missed an eligible
program") and false-negative eligibles ("would-have-passed
verification but cannot be validated programmatically").

## Refused implementation

- NO `agents/grant_writer/nsf.py` as institutional applicant
- NO `agents/grant_writer/erc.py` as institutional PI
- NO institutional-affiliation field populated on any application
- NO falsified DUNS / SAM.gov / UEI registration
- License-request auto-reply does NOT mention institutional-grant
  channels

## Lift conditions

This is a constitutional + legal refusal. Lift requires either:

- Operator obtaining genuine institutional affiliation (not
  currently in scope; would itself be an operator-physical
  multi-year process)
- All major institutional-grant programs revising eligibility to
  permit non-institutional applicants (extremely unlikely)

The `refused-lifecycle-conditional-watcher` daemon (when shipped)
will check the eligibility-filter operator-curation per its
cadence policy.

## Cross-references

- cc-task vault note: `leverage-REFUSED-pose-nsf-institutional-applicant.md`
- Sibling refusal: `leverage-REFUSED-nih-grants` (AI-developed-app ban)
- Sibling refusal: `leverage-REFUSED-sloan-pi-fellowship` (PI
  fellowship operator-physical)
- Eligibility filter: `hapax-state/grants/eligibility-filter.yaml`
- Replacement money paths: `leverage-money-lightning-nostr-zaps`,
  `leverage-money-liberapay-recurring`
- Methodology distribution: `leverage-workflow-hapax-axioms-pypi`
- Source research: `docs/research/2026-04-25-leverage-strategy.md`
