# Refusal Brief: Webhook Receivers Without Sender Authentication

**Slug:** `mail-monitor-refused-unverified-webhook`
**Axiom tag:** `single_user`, `feedback_full_automation_or_no_engagement`, security substrate
**Refusal classification:** Trivially-exploitable injection vector
**Status:** REFUSED — no webhook endpoint accepts mail events without JWT/HMAC sender verification.
**Date:** 2026-04-26
**Related cc-task:** `mail-monitor-refused-unverified-webhook`
**Sibling refusal-briefs (mail-monitor refusal library complete):**
  - `mail-monitor-aggregation-digest.md`
  - `mail-monitor-auto-reply.md`
  - `mail-monitor-inbox-panel.md`
  - `mail-monitor-out-of-label-read.md`
  - `mail-monitor-sentiment-analysis.md`
  - `mail-monitor-spam-classifier-overreach.md`

## What was refused

- HTTP webhook endpoints in `agents/mail_monitor/` without sender
  authentication
- Webhook receivers that accept arbitrary POSTs without:
  - **Pub/Sub push:** JWT validation against Google's published keys
    (verifying `iss=accounts.google.com` and `aud` matching the
    webhook URL)
  - **Mailhook (omg.lol):** HMAC validation against the operator's
    omg.lol webhook secret
- Signed-payload-omitted endpoints (`/webhook/gmail`,
  `/api/awareness/inbound/omg-lol`)
- "Test mode" endpoints that bypass verification for development

## Why this is refused

### Trivially exploitable injection vector

Without sender authentication, webhook endpoints accept arbitrary
inputs from the network. Any party that learns the webhook URL can
inject:

- Fake mail events that trigger spurious category dispatch
- Synthetic SUPPRESS events to inflate the suppression list
- Forged operational alerts that mutate awareness state
- Forged refusal-feedback events that pollute the refusal-as-data
  substrate

These are not theoretical — webhook URLs leak via DNS reconnaissance,
typosquatting domains, accidental commit-history exposure. The
verification layer is the sole boundary between "operator-trusted
event" and "internet-supplied event."

### Single-operator axiom: trust boundary at the daemon

Per `single_user` axiom: Hapax is one operator. The daemon's trust
model assumes events originate from operator-authorized sources
(Pub/Sub from operator's Google Cloud project, omg.lol Mailhook from
operator's account). Without verification, that trust assumption is
unsupported — the daemon would be acting on inputs it has no basis
to trust.

### Refusal-as-data integrity

Forged SUPPRESS events would corrupt the refusal-as-data substrate.
Per `interpersonal_transparency` axiom + the substrate principle:
each refusal event is a discrete first-class data point. Allowing
network-supplied forgeries would inject false refusals,
constitutionally violating the substrate's integrity.

### Mandatory verification mechanisms

Per `mail-monitor-006-webhook-receivers` (offered cc-task; alpha's
lane), the verification layer is one of the load-bearing
acceptance criteria:

- **Gmail Pub/Sub push** must validate JWT against
  `https://www.googleapis.com/oauth2/v3/certs`, check `iss`
  (=`accounts.google.com`), check `aud` (=webhook URL)
- **omg.lol Mailhook** must validate HMAC-SHA256 of payload against
  operator's pre-shared secret
- 5xx response on verification failure (no body leak)
- Verification failures land in `refusal-brief.append()` as
  immediate (non-aggregated) refusal events

## Daemon-tractable boundary

Authorized webhook receivers must satisfy ALL of:

1. **Sender authentication** (JWT or HMAC) — verified before any
   payload parsing
2. **Path-based routing** — `/webhook/gmail` accepts only
   Pub/Sub-shaped JWTs; `/api/awareness/inbound/omg-lol` accepts
   only Mailhook-HMAC payloads
3. **Refusal-event logging** — verification failures append to
   `/dev/shm/hapax-refusals/log.jsonl` immediately

Endpoints that don't satisfy all three are constitutional
violations.

## CI guard (deferred to mail-monitor-006 implementation)

This refusal-brief defers the CI guard to the implementation of
`mail-monitor-006-webhook-receivers` (alpha's lane). The guard
shape — static check that every `@app.post("/webhook/...")`
handler has a verification dependency — should be implemented
alongside the receivers, not as a standalone test against absent
implementation.

This brief establishes the constitutional posture so that when
the receivers ship, the verification layer is non-negotiable from
day one.

## Refused implementation

- NO `@app.post("/webhook/gmail")` without JWT validation
- NO `@app.post("/api/awareness/inbound/omg-lol")` without HMAC
  validation
- NO `if DEBUG: skip_verification()` branches
- NO test-only endpoints that bypass verification for staging
- NO 200-response on verification failure (must be 401/403)

## Lift conditions

This refusal cannot lift while Hapax is internet-exposed. Lift
would require:
- Hapax operating exclusively on a private network with no
  webhook endpoints reachable from the internet
- Or constitutional retirement of the security substrate
  principle (not currently planned)

## Cross-references

- cc-task vault note: `mail-monitor-refused-unverified-webhook.md`
- Implementation cc-task: `mail-monitor-006-webhook-receivers.md`
  (alpha's lane; offered, has design-spec dep)
- Sibling refusals: see header (mail-monitor refusal library now
  complete with this 7th brief)
- Source research: `docs/research/2026-04-25-mail-monitoring.md`
  §Anti-patterns + §Verification mechanism
- Constitutional anchors: `single_user` axiom, security substrate
