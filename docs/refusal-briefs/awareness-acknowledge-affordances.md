# Refusal Brief: Acknowledge / Mark-read / Triage Affordances on Awareness Surfaces

**Slug:** `awareness-acknowledge-affordances`
**Axiom tag:** `no_HITL`
**Refusal classification:** Anti-pattern #1 (operator-awareness drop §10)
**Status:** REFUSED — no module, no endpoint, no UI implementing these
semantics is to be built.
**Date:** 2026-04-26
**Related cc-task:** `awareness-refused-acknowledge-mark-read-affordances`

## What was refused

Any UI surface, endpoint, or daemon affording the operator a way to:

- `Acknowledge` a refusal event or awareness signal
- `Mark as read` a queue entry
- `Dismiss` a notification
- `Triage` an alert (high/medium/low, snooze, defer)
- Any synonym thereof: `clear`, `archive` (as user-action), `resolve`,
  `accept`, `note as seen`

The refusal scope covers both the `awareness-state` cluster (the
13-category state spine + REST/SSE endpoints + Tauri sidebar + Wear OS
tile + omg.lol fanout) and the `refusal-brief` cluster (the canonical
refusal log + its consumer surfaces).

## Why this is refused

### Constitutional grounds

**`feedback_full_automation_or_no_engagement` (operator directive
2026-04-25T16:55Z):** Hapax surfaces are full-auto or they don't
exist. Every `Acknowledge` button is operator labor — a HITL
checkpoint masquerading as a status indicator. The operator's
explicit policy is: **refuse all surfaces not fully Hapax-automated**,
and that refusal is itself a constitutive thesis
(infrastructure-as-argument).

The single_user axiom is also relevant: ack-state is intrinsically
per-user state. Hapax models no users; introducing acknowledgement
state would force a user-modelling concession the constitution
rejects.

### Human-factors grounds — Endsley & Sarter automation surprise canon

The HFE literature on automation surprise has a stable finding: any
operator-required clearance creates a **partial-attention bug** with
exactly two modes, both pathological.

> "Operators frequently fail to monitor automation, and when they do
> monitor, they fail to detect changes in automation state." —
> Sarter, N. B., & Woods, D. D. (1995). *How in the world did we
> ever get into that mode? Mode error and awareness in supervisory
> control.* Human Factors, 37(1), 5–19.

> "Situation awareness errors most often involve failures in
> perception of relevant cues in the environment, including failure
> to monitor automation state changes." — Endsley, M. R. (1995).
> *Toward a theory of situation awareness in dynamic systems.*
> Human Factors, 37(1), 32–64.

Translated to the awareness surfaces:

- **Mode A — operator believes the queue is bounded by their
  attention.** They glance at the dashboard, see N unacked items, and
  feel responsible for the backlog. The system, meanwhile, treats the
  queue as informational and assumes the operator is *not* triaging.
- **Mode B — system believes operator is triaging.** Cadence
  decisions (alert escalation, frequency damping) bake in an
  ack-rate prior. When the operator stops acking (because they
  realised it was busywork), alert quality silently degrades.

Neither mode produces accurate situation awareness. Both are
strictly worse than "no ack affordance exists, the system runs the
queue end-to-end, the operator reads the dashboard if they choose."

### Refusal-as-data continuity

The refusal-brief log itself (`agents/refusal_brief/`) is built on
the premise that refusals are constitutive data, not operator
attention items. Adding `acknowledge` semantics to a refusal log
inverts that premise: it would say "this refusal is provisional
until the operator stamps it." The whole substrate's stance is the
opposite — the refusal is the operator's stance.

## What is built instead

The awareness epic ships consumer-only, read-only surfaces:

- `## Awareness` + `## Refused` sections in the daily-note
  ([#1491](https://github.com/ryanklee/hapax-council/pull/1491)) —
  operator reads, never edits
- `/api/awareness` REST + `/api/awareness/stream` SSE
  ([#1493](https://github.com/ryanklee/hapax-council/pull/1493),
  [#1504](https://github.com/ryanklee/hapax-council/pull/1504)) —
  GET-only, `TestReadOnlyContract` enforces the no-mutation invariant
  at the route-table level
- omg.lol public-safe fanout
  ([#1508](https://github.com/ryanklee/hapax-council/pull/1508)) —
  daemon-side filter, no read-receipt
- Weekly review aggregator
  ([#1511](https://github.com/ryanklee/hapax-council/pull/1511)) —
  count + raw list, no per-week verdict, no recommended-action prose

Each surface explicitly does NOT carry ack/dismiss/triage controls.
The `## Refused` daily-note section, the `/api/refusals` endpoint,
and the omg.lol render all enumerate raw entries; none expose
mark-as-read state.

## CI-enforcement

A future CI guard MAY land that scans any new `awareness-class` or
`refusal-brief` consumer file for the regex
`mark.read|acknowledge|dismiss|triage` (case-insensitive) and fails
the build on a hit. This brief stands as the policy whether or not
that guard is yet wired.

## Cross-references

- `awareness-state-stream-canonical` cc-task: state-spine substrate
- `awareness-refusal-brief-writer` cc-task: refusal-log substrate
- `awareness-refused-tile-tap-action` cc-task: refuses on-tap expand
  for action (sibling refusal under the same axiom)
- `awareness-refused-operator-curated-filters` cc-task: refuses
  user-curated dashboard filters (sibling)
- `awareness-refused-scheduled-summary-cadence` cc-task: refuses
  cadence implying response (sibling)

## Bibliographic note

Endsley + Sarter are the canonical citation here, but the same
finding is reflected across the wider automation-surprise literature
— Bainbridge (1983), Parasuraman & Riley (1997), Lee & See (2004).
The refusal does not turn on any single citation; it turns on the
unified finding that operator-clearance steps in otherwise-automated
loops are mode-confusion generators.
