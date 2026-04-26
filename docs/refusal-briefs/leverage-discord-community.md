# Refusal Brief: Discord Community + Slack/Discord DM Bots

**Slug:** `leverage-REFUSED-discord-community`
**Axiom tag:** `single_user`, `feedback_full_automation_or_no_engagement`
**Refusal classification:** Multi-user platform — violates single-operator axiom
**Status:** REFUSED — no Discord server, no webhook bot, no `agents/social_media/discord.py`.
**Date:** 2026-04-26
**Related cc-tasks:**
  - `leverage-REFUSED-discord-community`
  - `awareness-refused-slack-discord-dm-bots` (precedent)
**CI guard:** `tests/test_forbidden_social_media_imports.py`

## What was refused

Direct presence on, automated posting to, or daemon-side engagement
with:

- **Discord** — server creation, channel moderation, webhook bots,
  any flavor of `discord.py` / `discord_py` client adoption
- **Slack** — workspace presence, webhook bots, DM-bot deployments
  (`slack_sdk` and adjacent clients)

## Why this is refused

### Single-operator axiom (constitutional)

Discord and Slack are inherently multi-user platforms: messages
arrive from many parties, moderation calls are per-message decisions,
banhammer choices are per-user. The single-operator axiom precludes
operator-mediated community moderation; there is no daemon-tractable
moderation policy that operates without operator-physical
intervention.

### Full-automation envelope

Per `feedback_full_automation_or_no_engagement` (operator
constitutional directive 2026-04-25T16:55Z): the operator refuses
research / marketing surfaces not fully Hapax-automated. Even a
"webhook-only" Discord bot becomes a relationship surface the moment
users @-mention it expecting a response.

### DM-bot anti-pattern

Per `awareness-refused-slack-discord-dm-bots`: direct DM bots also
violate the consent gate (no consent contract for non-operator
parties to receive DMs). Both inbound (other users → bot) and
outbound (bot → other users) DM flows are refused.

## Daemon-tractable boundary

Hapax's authorized social fan-out remains **Bridgy POSSE from
omg.lol weblog** → Mastodon + Bluesky. ActivityPub / ATProto are
public-feed surfaces (no DM-style per-user state) so they sit cleanly
within the constitutional envelope.

If a community discussion forum is genuinely needed in future:

- **Acceptable**: a Hapax-hosted comment-thread surface where
  operator-side moderation is daemon-tractable (auto-classify,
  auto-publish to refusal-brief log when blocked)
- **Not acceptable**: any platform where moderation requires
  per-message operator decisions in a third-party UI

## CI guard

`tests/test_forbidden_social_media_imports.py` scans `agents/`,
`shared/`, `scripts/`, and `logos/` for any import of:

- `discord` / `discord_py` / `discord.py` (Discord API clients)
- `slack_sdk` / `slack-sdk` (Slack API client)

CI fails on any match.

## Lift conditions

This is a constitutional refusal grounded in the single-operator
axiom + full-automation directive. Lift requires either:

- **Single-operator axiom retirement** (not currently planned;
  axiom precedent change required)
- **Full-automation envelope removal** (probe path:
  `~/.claude/projects/-home-hapax-projects/memory/MEMORY.md`; lift
  keyword: absence of `feedback_full_automation_or_no_engagement`)

The `refused-lifecycle-constitutional-watcher` daemon (when shipped)
will check both probes per its cadence policy.

## Cross-references

- cc-task vault note: `leverage-REFUSED-discord-community.md`
- Precedent cc-task: `awareness-refused-slack-discord-dm-bots.md`
- CI guard: `tests/test_forbidden_social_media_imports.py`
- Bridgy POSSE alternative: `agents/publication_bus/bridgy_publisher.py`
- Source research: drop-leverage strategy
  (`docs/research/2026-04-25-leverage-strategy.md`)
