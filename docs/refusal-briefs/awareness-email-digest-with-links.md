# Refusal Brief: Email Digests with Embedded "see more" Links

**Slug:** `awareness-refused-email-digest-with-links`
**Axiom tag:** `feedback_full_automation_or_no_engagement`
**Refusal classification:** Anti-pattern #5 (drop-6 §10) — manufactured click-pressure
**Status:** REFUSED — no daemon sends email summaries from awareness paths.
**Date:** 2026-04-26
**Related cc-task:** `awareness-refused-email-digest-with-links`
**CI guard:** `tests/test_forbidden_awareness_email_imports.py` (path-scoped to awareness paths only)
**Sibling refusal-briefs:**
  - `awareness-acknowledge-affordances.md`
  - `awareness-additional-affordances.md`
  - `awareness-aggregation-api.md`
  - `awareness-public-marketing-dashboards.md`

## What was refused

- Email digests sent by awareness daemons containing `[see more →](url)`-style links
- Email "weekly summary" / "daily digest" mailers from awareness or
  refusal-brief paths
- Plain-text emails from awareness paths (even without links — the
  cadence problem applies regardless)
- `agents/operator_awareness/email_sender/` package
- `smtplib` / `aiosmtplib` / `sendgrid` / `mailgun` / SES imports in
  `agents/operator_awareness/` or `agents/refusal_brief/`

## Why this is refused

### Manufactured click-pressure

Email digests with embedded links manufacture click-pressure. The
operator clicks → web view loads → that web view becomes the in-loop
surface. Per `feedback_full_automation_or_no_engagement` (operator
constitutional directive 2026-04-25T16:55Z): click-to-expand is
action; action implies queue management; queue management implies
operator-physical attention.

The "see more" pattern is the classic engagement-bait shape used by
SaaS platforms to drive click-through metrics. Constitutional posture
forecloses it.

### Cadence wrong-either-way

Email is the wrong medium for awareness state:

- **Too async for ops state:** by the time the operator reads the
  email, the underlying ops state has changed. Email digests latency-
  shift the data, making it stale on arrival.
- **Too sync for ambient:** email arrives with a notification chime,
  operator's email client unreads, attention is interrupted. That's
  a notification pattern, not an ambient pattern.

Neither cadence (async vs sync) fits. The right cadences are:

- **Ambient pulse:** waybar widget, omg.lol statuslog, Logos panel
  (all consume from the awareness state stream)
- **Push notification:** ntfy (operator-installable, low-pressure,
  no embedded action links)

### Email is structurally wrong even without links

Even a "plain-text complete prose with NO links" email digest fails
the cadence test. The refusal is therefore structural — not just
about links, but about email-as-medium for awareness.

## Daemon-tractable boundary

Authorized awareness consumption surfaces:

1. **Waybar widget** (per `awareness-waybar-*` cc-tasks) — ambient
   pulse, low-attention
2. **Logos panel** (per `awareness-tauri-sse-bridge`) — interactive
   read-only, operator-initiated
3. **omg.lol statuslog** (per `awareness-omg-lol-public-safe-filter`)
   — public-safe ambient
4. **ntfy push** (per `awareness-refused-ntfy-action-buttons`'s
   non-action-button path) — push notification without embedded
   action surface

None of these have embedded action links or expanded-content URLs.
All are read-only / read-rendered ambient surfaces.

## CI guard (path-scoped)

`tests/test_forbidden_awareness_email_imports.py` enforces the
refusal at the data layer. Path-scoped to:

- `agents/operator_awareness/` (when shipped — currently the
  awareness substrate is offered, not built)
- `agents/refusal_brief/`

Forbidden libraries: `smtplib`, `aiosmtplib`, `sendgrid`, `mailgun`,
`sendinblue`.

The mail-monitor surface (`agents/mail_monitor/`) is permitted to
use email libraries (mail-RECV is structurally different from mail-
SEND-to-operator). The path-scope discriminates correctly.

## Refused implementation

- NO `agents/operator_awareness/email_sender/`
- NO `agents/refusal_brief/digest_emailer.py`
- NO scheduled job that emails awareness summaries
- NO transactional-email service integration in awareness paths

## Lift conditions

This is a constitutional refusal grounded in
`feedback_full_automation_or_no_engagement`. Lift requires retirement
of that constitutional directive.

The `refused-lifecycle-constitutional-watcher` daemon (when shipped)
will check the probe per its cadence policy.

## Cross-references

- cc-task vault note: `awareness-refused-email-digest-with-links.md`
- CI guard: `tests/test_forbidden_awareness_email_imports.py`
- Sibling refusals: see header
- Authorized surfaces: `awareness-waybar-*`, `awareness-tauri-sse-bridge`,
  `awareness-omg-lol-public-safe-filter`
- Source research: drop-6 §10 anti-pattern #5
