# Refusal Brief: GitHub Discussions on Hapax Repos

**Slug:** `leverage-REFUSED-github-discussions-enabled`
**Axiom tag:** `single_user`, `feedback_full_automation_or_no_engagement`
**Refusal classification:** Multi-user Q&A surface — not daemon-tractable
**Status:** REFUSED — Discussions disabled on all first-party repos
**Date:** 2026-04-26
**Related cc-task:** `leverage-REFUSED-github-discussions-enabled`
**Related work:** `repo-pres-issues-redirect-walls` (broader repo-presentation refusal-shape)

## What was refused

GitHub Discussions tab on any first-party Hapax repository:

- `ryanklee/hapax-council`
- `ryanklee/hapax-officium`
- `ryanklee/hapax-constitution`
- `ryanklee/hapax-mcp`
- `ryanklee/hapax-watch`
- `ryanklee/hapax-phone`
- `ryanklee/hapax-assets` (when bootstrapped)

Discussions tab is **disabled** in repository Settings; this brief
documents why and provides the lift-condition probe.

## Why this is refused

### Single-operator axiom (constitutional)

GitHub Discussions creates a per-thread Q&A surface where
non-operator parties post questions expecting per-question replies.
The single-operator axiom precludes operator-mediated Q&A — each
question is unique, no daemon can compose a meaningful response, and
operator-physical reply-attention is not a renewable resource.

### Full-automation envelope

Per `feedback_full_automation_or_no_engagement` (operator
constitutional directive 2026-04-25T16:55Z): the operator refuses
research / engagement surfaces not fully Hapax-automated. A
"Discussions tab + bot reply" pattern would either be:
- Unhelpful (bot can't answer novel questions correctly)
- Misleading (bot pretends to know what it doesn't)
- Engagement-bait (operator gets dragged back into the surface)

All three violate the constitutional posture.

## Issues stay enabled — structural distinction

Issues remain enabled on first-party repos because Issues are
structurally different from Discussions:

- **Issues**: bug tracker / feature request queue. Each entry has a
  defined disposition (fix / wontfix / duplicate / closed-as-stale).
  Daemon-tractable triage workflows exist (see
  `repo-pres-issues-redirect-walls` for the redirect-wall + issue
  template work).
- **Discussions**: open-ended Q&A. Each thread expects free-form
  per-thread engagement. No defined disposition; no triage workflow
  that doesn't reduce to "operator reads + replies."

The Issues redirect-walls cc-task (`repo-pres-issues-redirect-walls`)
is the FULL_AUTO disposition for the Issues surface;
github-discussions has no equivalent and is therefore refused.

## Daemon-tractable boundary

Hapax's authorized engagement surfaces are:
- **Refusal Brief log** — refusal-as-data substrate; non-engagement
  is itself the artefact
- **Bridgy POSSE → Mastodon + Bluesky** — public-feed broadcast
  (no per-user state)
- **Citation graph** — DataCite RelatedIdentifier edges; engagement
  through cited works, not threaded conversation
- **Issues (with redirect walls)** — per `repo-pres-issues-redirect-walls`,
  bug-tracker only; no contribution-surface drift

GitHub Discussions does not fit any of these patterns.

## Phase 1 (this PR): Refusal-brief documentation only

Phase 2 (separate cc-task `repo-pres-issues-redirect-walls`) ships:
- `gh api repos/.../`-style PATCH to disable Discussions across all 7 repos
- CI drift-check that fails build if Discussions is re-enabled
- README explicit "Discussions disabled by constitutional policy" line

Phase 1 establishes the constitutional record so the Phase 2 enforcer
has a documented rationale.

## Lift conditions

This is a constitutional refusal grounded in the single-operator
axiom + full-automation directive. Lift requires either:
- Single-operator axiom retirement (not currently planned)
- Full-automation envelope removal (probe path:
  `~/.claude/projects/-home-hapax-projects/memory/MEMORY.md`; lift
  keyword: absence of `feedback_full_automation_or_no_engagement`)

## Cross-references

- cc-task vault note: `leverage-REFUSED-github-discussions-enabled.md`
- Phase 2 enforcer: `repo-pres-issues-redirect-walls.md`
- Issues structural distinction: same Phase 2 cc-task documents the
  Issues redirect-wall + issue-template work
- Source research: drop-leverage strategy
  (`docs/research/2026-04-25-leverage-strategy.md`)
- Drop 3 §3: refusal-shaped UI affordances (Sponsorships off,
  Discussions off, Wiki repurposed)
