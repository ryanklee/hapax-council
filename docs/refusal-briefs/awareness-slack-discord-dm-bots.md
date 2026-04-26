# Refusal Brief: Slack / Discord / DM-Routed Bot Summaries

**Slug:** `awareness-refused-slack-discord-dm-bots`
**Axiom tag:** `feedback_full_automation_or_no_engagement`, `single_user`, `feedback_no_operator_approval_waits`
**Refusal classification:** Anti-pattern #4 (drop-6 §10) — DM medium implies bidirectionality
**Status:** REFUSED — no daemon posts to operator's Slack / Discord / Signal / Matrix / iMessage as awareness summary.
**Date:** 2026-04-26
**Related cc-task:** `awareness-refused-slack-discord-dm-bots`
**Sibling refusal-briefs:**
  - `awareness-acknowledge-affordances.md`
  - `awareness-additional-affordances.md`
  - `awareness-aggregation-api.md`
  - `awareness-public-marketing-dashboards.md`
  - `awareness-email-digest-with-links.md`
  - `awareness-ntfy-action-buttons.md`
  - `awareness-pending-review-inboxes.md`
**Companion refusal:**
  - `leverage-discord-community.md` (Discord community surface; this brief is the awareness-DM-bot subset)

## What was refused

- Slack DM bot posting awareness summaries
- Discord DM bot posting awareness summaries
- Signal-cli or signal-bot summary posting
- Matrix DM bot via matrix-nio
- iMessage / SMS-routed awareness summary delivery
- Any daemon-side write to operator's DM inbox on any chat platform

## Why this is refused

### DM medium encodes bidirectional reply expectation

Even when the bot doesn't read replies, the **medium itself**
implies bidirectionality. Slack and Discord DMs are constitutively
person-to-person conversations; injecting bot summaries into that
medium colonizes attention on a channel that defaults to
bidirectional.

When a non-operator party (the bot) appears in operator's DM
inbox, the social affordances of that inbox apply: read receipts,
reply expectations, message-thread context. The operator's
default mode in those surfaces is "reply if someone messages me"
— breaking that pattern requires per-message conscious effort.

### `feedback_no_operator_approval_waits`

Per the operator's memory: "Sessions NEVER wait on operator
approval." Reverting > stalling. A DM-summary bot creates an
implicit wait surface — the operator may feel obligated to "see
it" before the daemon's next decision lands. That obligation
violates the no-wait directive.

### Single-operator axiom

Operator's DM channels are operator-only inboxes — they're
single-tenant by design (operator + counterparty). Injecting a
bot is not a single-tenant pattern; it implicitly creates a
two-party-plus-bot conversation. The single-operator axiom
precludes that multi-tenancy.

### Constitutional fit per `feedback_full_automation_or_no_engagement`

Per the operator's 2026-04-25T16:55Z constitutional directive:
operator refuses research / engagement surfaces not fully Hapax-
automated. DM-summary bots structurally invite engagement
(replies, follow-ups, in-thread questions) — patterns the
constitutional posture forecloses.

## Daemon-tractable boundary

Authorized awareness-output channels:

- **ntfy** — pure broadcast, no reply-expectation by medium
  (sender is the URL, not a person; user can't reply to a URL)
- **omg.lol statuslog** — public weblog post, no reply-expectation
  (weblog posts default to non-conversational)
- **Waybar widget** — local UI, no remote messaging
- **Logos panel** — local UI, no remote messaging

These work because the **medium itself** doesn't carry reply
expectation. ntfy and weblog are broadcast surfaces; widgets are
local UI.

## Companion refusal: Discord community

`leverage-REFUSED-discord-community` (already shipped in #1563)
refuses Discord as a multi-user community platform. This brief is
narrower: it refuses **awareness-summary DM bots** specifically.
Both refusals share the multi-user-medium-bidirectionality grounds
but cover different surface scopes:

- `leverage-discord-community.md`: NO Discord server / NO
  community moderation / NO public-channel posting
- `awareness-slack-discord-dm-bots.md` (this brief): NO daemon-
  side DM injection into operator's chat-platform inboxes (Slack,
  Discord, Signal, Matrix, iMessage)

Together they preclude all chat-platform awareness surfaces.

## CI guard

The existing `tests/test_forbidden_social_media_imports.py` already
blocks `discord` / `slack_sdk` imports globally as part of the
multi-user-platform refusal (per `leverage-REFUSED-discord-community`).
That guard suffices for this refusal too — DM-bot adoption requires
importing those libraries, which is already blocked.

For Signal / Matrix / iMessage clients (not yet in the guard
because no current refusal targets them as community platforms),
the path-scoped guard pattern from
`tests/test_forbidden_awareness_email_imports.py` could be extended.
For now, the constitutional refusal-brief captures the position;
import guards extend when (if) operator considers adopting these
clients for non-awareness use.

## Refused implementation

- NO `agents/operator_awareness/dm_bot/`
- NO `agents/operator_awareness/slack_summary/`
- NO `agents/operator_awareness/discord_summary/`
- NO `agents/operator_awareness/signal_summary/`
- NO `agents/operator_awareness/matrix_summary/`
- NO daemon-side write to any chat-platform DM channel as awareness
  output

## Lift conditions

This is a constitutional refusal grounded in three directives. Lift
requires retirement of any of:

- `feedback_full_automation_or_no_engagement`
- `feedback_no_operator_approval_waits`
- Single-operator axiom (constitutional; not currently planned)

The `refused-lifecycle-constitutional-watcher` daemon (when shipped)
will check the probe per its cadence policy.

## Cross-references

- cc-task vault note: `awareness-refused-slack-discord-dm-bots.md`
- Companion refusal: `leverage-discord-community.md`
- CI guard: `tests/test_forbidden_social_media_imports.py` (covers
  discord + slack via existing leverage-REFUSED-discord-community
  scope)
- Sibling refusals: see header
- Authorized awareness-output channels: ntfy (without action buttons,
  per `awareness-ntfy-action-buttons.md`), omg.lol statuslog,
  waybar / Logos local UI
- Source research: drop-6 §10 anti-pattern #4
