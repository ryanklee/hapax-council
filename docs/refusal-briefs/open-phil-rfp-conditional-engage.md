# Refusal Brief: Open Philanthropy RFP via Playwright form-fill

**Slug:** `leverage-money-open-phil-rfp-CONDITIONAL`
**Axiom tag:** `single_user` + `executive_function` + `corporate_boundary`
**Refusal classification:** CONDITIONAL_ENGAGE → REFUSED (failed full-automation gate)
**Status:** REFUSED — Open Phil RFP submission is not fully daemon-tractable.
**Date:** 2026-04-26
**Source research:** `docs/research/2026-04-25-leverage-strategy.md` §money-open-phil

## What is refused

Submitting Open Philanthropy RFP applications via Playwright-driven form-fill. The cc-task is the operator's audit-correction CONDITIONAL classification: stay CONDITIONAL until verification clears; if verification fails, demote to REFUSED.

## Why this is refused

### Per the original task's verification gate

The cc-task's `verification_required` is verbatim:

> Demonstrable full-daemon Playwright form-fill pathway with no operator hand-off; if not demonstrable, demote to REFUSED.

The verification protocol enumerated five sub-pathways. Of those:

| Pathway | Daemon-tractable? | Failure mode |
|---|---|---|
| 1. JS-rendered form fields | **Yes** | Playwright handles reliably |
| 2. reCAPTCHA / Cloudflare challenge | **No** | Stealth plugins handle reCAPTCHA v2 inconsistently and reCAPTCHA v3 rarely; Cloudflare challenges escalate adversarially over time |
| 3. PDF upload via `setInputFiles` | **Yes** | Stable Playwright capability |
| 4. Identity verification (email confirmation) | **Partial** | mail-monitor handles inbound, but email-confirmation links increasingly include device-binding tokens that fail headless-Chromium fingerprints |
| 5. Free-form essay drafting | **Partial** | `agents/composer/` can draft, but Open Phil RFP essays explicitly request "what specifically YOU plan to do" — first-person operator narrative that is hard to ground without operator hand-off |

Two of five pathways fail outright (reCAPTCHA + Cloudflare); two more fail conditionally (device-binding + first-person essay). The constitutional posture per `feedback_full_automation_or_no_engagement` is REFUSE.

### Per `executive_function` (weight 95)

Adversarial bot-detection is a recurring-attention failure mode. Each time Cloudflare or reCAPTCHA upgrades, the Playwright config breaks until operator-physical intervention. The full-automation contract is "errors include next actions; routine work automated" — a Playwright bot-detection failure does not include a next action the operator can defer indefinitely; it blocks the submission. Under sustained operation, the daemon would either ship broken submissions (silently failed) or surface manual-completion requests, both of which violate the FULL_AUTO contract.

### Per `single_user` (weight 100) + `corporate_boundary` (weight 90)

Open Philanthropy RFPs request applicant identity verification (sometimes via state-issued ID, sometimes via institutional affiliation, sometimes via prior public scholarly record). The full-automation contract requires the daemon to act as the operator's principal — but the identity-binding step at Open Phil's end is operator-personal and crosses the corporate boundary if the operator is asked about employer affiliation or work-product overlap. Daemon-side decision-making about which boxes to tick is not safe.

### Per the research drop's own caveat

The leverage-strategy research drop §money-open-phil flags Open Phil specifically as "operationally fragile" and recommends starting with venues that explicitly publish bot-friendly submission paths (e.g., grant lotteries with auto-graded eligibility forms). Per drop-leverage, the operator's higher-confidence path is `leverage-vector-grant-lotteries-portfolio` (closed earlier in session via alpha lane).

## What remains engaged

- Lightning-receive monetization rail (via Lightning relay; `pub-bus-money-rails-payment-processors`)
- Liberapay recurring-donations rail (operator-physical bootstrap; daemon-side touch updates)
- Itch.io PWYW bundle (Phase 1 shipped this session; #1715 merged)
- Grant-lotteries portfolio (daemon-eligible auto-graded forms; alpha lane CLOSED)
- Co-publishing royalty share via Zenodo + Internet Archive citations

The non-Open-Phil monetization stack covers operator's full attention budget.

## Constitutional alternative

If Open Philanthropy publishes a daemon-tractable submission API (REST endpoint with Bearer auth, no human-verification), it can be re-evaluated under the same gate. The current Playwright path does NOT meet the bar.

The operator can override this REFUSE at any time by re-classifying the cc-task `automation_status: FULL_AUTO` with a daemon-tractable form path specified — the refusal is not permanent.

## Refusal-as-data

This brief lands in `~/hapax-state/publications/refusal-annex-leverage-money-open-phil-rfp-CONDITIONAL.md` via `RefusalAnnexPublisher` Phase 1 + the Phase 2 cross-linker. The Zenodo refusal-deposit (per `pub-bus-internet-archive-ias3` sibling refusal-DOI minting) carries `RelatedIdentifier` of relation `IsRequiredBy` pointing at the leverage-strategy research drop DOI — making this REFUSE participate in the citation graph as a structured node.

The refusal narrative — "philanthropic-RFP submission systems are not daemon-tractable under sustained operation" — is itself a research artefact, surfaced via Hapax authorship rather than concealed.
