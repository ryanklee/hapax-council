# Refusal Brief: Mail-Monitor Auto-Reply (General Case)

**Slug:** `mail-monitor-refused-auto-reply`
**Axiom tag:** `feedback_full_automation_or_no_engagement`, `feedback_hapax_authors_programmes`
**Refusal classification:** Anti-pattern #3 (mail-monitoring research §Anti-patterns) — manufactured correspondence
**Status:** REFUSED — no daemon-side auto-reply to inbound mail in any of the 6 categories.
**Date:** 2026-04-26
**Related cc-task:** `mail-monitor-refused-auto-reply`
**CI guard:** `tests/test_forbidden_mail_monitor_send_imports.py`
**Sibling refusal-brief:** `mail-monitor-aggregation-digest.md`

## What was refused

- Auto-reply to inbound refusal-feedback (Category E)
- Auto-reply to inbound cold-contact replies (Category C)
- Auto-reply to inbound LICENSE-REQUEST mail (Category A) — quote
  drafting is daemon-side; the *outbound mail* is REFUSED at the
  mail-monitor layer
- Auto-reply to operational mail (Category D)
- Auto-reply to inbound webhook-bounced mail
- Any vacation-style / out-of-office auto-reply from operator's
  Gmail
- `agents/mail_monitor/auto_reply/` package
- SMTP / `smtplib` / `aiosmtplib` / `sendgrid` / `mailgun` /
  `sendinblue` imports anywhere under `agents/mail_monitor/`

## Why this is refused

### Hapax-authors strictly applies to publication artefacts

`feedback_hapax_authors_programmes` mandates that programme
authorship is fully Hapax-generated. By extension and explicit per
this anti-pattern: Hapax authors **publication artefacts**, not
correspondence. Auto-replying to a refusal-feedback message would
create an implicit dialogue — the daemon performing reception and
acknowledgement that operator has not authorised.

### Anti-anthropomorphization

Mail correspondents are not Hapax's interlocutors; they're senders
in a routing graph. Auto-reply makes the daemon perform
conversational subjectivity. That contradicts the
anti-anthropomorphization posture: structural input (mail event)
should produce structural output (vault filing, chronicle entry,
refusal-brief log row), not conversational output.

### Refusal-as-data preservation

A SUPPRESS reply is data. An auto-reply ("thanks for the SUPPRESS,
we have noted you on the suppression list") performs **reception**,
which the operator has not authorized. The reception performance is
operator-physical attention by proxy; the daemon is implicitly
saying "operator is monitoring this." That implicit claim is
constitutionally false.

### Permitted exception: outbound-correlated DOI-retry

**One narrow exception** survives this refusal: the
`mail-monitor-009-verify-processor` may, when it extracts a DOI
from inbound mail and that DOI fails to resolve via
`https://doi.org/` within 24h, call the originating service's
`/actions/publish` endpoint directly (e.g., Zenodo deposit-action
API).

This is **not a reply to the inbound mail**:
- It's a retry of the original publication action
- It uses the publication-API directly, not SMTP
- It targets the publishing service, not the mail correspondent
- It's mail-API-free (no smtplib import required)

The CI guard remains compatible: `smtplib` and equivalents stay
forbidden in `agents/mail_monitor/`. Deposit-action API calls go
through the publication-bus modules, which already have their own
HTTP shapes (bare-`requests`).

## Daemon-tractable boundary

Authorized mail-monitor outputs:
- Vault filing (per category disposition)
- Chronicle event entries (no body content; sender domain + ORCID
  + message-id only)
- Refusal-brief log appends (for SUPPRESS / refusal-feedback
  categories)
- `awareness.mail.suppress_count_1h` state field updates
- Mark-read + remove-INBOX actions on the original message

None of these is outbound correspondence.

## CI guard

`tests/test_forbidden_mail_monitor_send_imports.py` scans
`agents/mail_monitor/` for any import of `smtplib`, `aiosmtplib`,
`sendgrid`, `mailgun`, `sendinblue`. CI fails on any match.

The guard is path-scoped to `agents/mail_monitor/` only — other
surfaces (publication-bus, etc.) are not subject to this guard
since their constraints differ.

## Refused implementation

- NO `agents/mail_monitor/auto_reply.py`
- NO `agents/mail_monitor/processors/auto_reply_*.py`
- NO Gmail API `users.messages.send()` call from any mail_monitor
  module (the Gmail API permits send via the same OAuth scope, but
  daemon must not exercise that capability)
- NO out-of-office vacation auto-responder

## Lift conditions

This is a constitutional refusal grounded in three directives. Lift
requires retirement of any of:

- `feedback_full_automation_or_no_engagement`
- `feedback_hapax_authors_programmes`
- Anti-anthropomorphization principle (constitutional)

The `refused-lifecycle-constitutional-watcher` daemon (when shipped)
will check the probe per its cadence policy.

## Cross-references

- cc-task vault note: `mail-monitor-refused-auto-reply.md`
- CI guard: `tests/test_forbidden_mail_monitor_send_imports.py`
- Sibling refusal: `mail-monitor-aggregation-digest.md`
- Permitted exception spec:
  `mail-monitor-009-verify-processor.md` (DOI-retry via API)
- Authorized outbound paths: `agents/publication_bus/*` (deposit-
  action APIs, never SMTP)
- Source research: `docs/research/2026-04-25-mail-monitoring.md`
  §Anti-patterns #3
