# Delta + Alpha Coordination Protocol

**Date:** 2026-04-19
**Author:** delta
**Status:** Design proposal, pre-live
**Context:** Operator directive (2026-04-19): two Claude sessions (`delta` and `alpha`) must stay "never idle" and move through ~10 named pre-live workstreams "quickly seamlessly and safely" before livestream go-live.
**Evolves:**
- `~/.cache/hapax/relay/PROTOCOL.md` (v1 trio spec)
- `docs/superpowers/plans/2026-04-18-trio-delivery-pipeline.md` (delta=ship / beta=audit / alpha=smoketest)
- `~/.cache/hapax/relay/queue-state-{alpha,beta,epsilon}.yaml` (v2 refill-batch state machine)

This document does **not** replace the existing infrastructure. It tightens the delta ↔ alpha edge for the pre-live sprint while leaving beta/epsilon coordination unchanged.

---

## §1. Survey of existing multi-agent coordination art

Five traditions translate to two-agent engineering pairs. Cite-sized highlights, then the principles that actually port.

**Pair programming (Beck, "Extreme Programming Explained", 1999).** Two engineers at one terminal: driver types, navigator watches for strategy drift. Throughput parity with solo work, defect-rate reduction 15–50% across case studies (Williams & Kessler 2003, Cockburn & Williams 2000). The non-obvious cost is **synchronous cognitive load** — both engineers must hold the same mental model. For async AI agents this trades cleanly: the shared artifact is the relay queue, not a shared terminal. Navigator discipline maps onto audit-before-merge.

**Pivotal Labs pair-ownership (2005–2012).** Pivotal pairs rotated daily; nobody owned a module. Result: every engineer had passable context on every module, bus factor ~= team size. Downside: pairs rediscovered each module's gotchas daily. For delta+alpha this argues *against* strict directory ownership and *for* weak ownership with a "pinged peer" convention — "I'm about to touch `shared/config.py`, speak now."

**Sprint cells (Scrum-of-Scrums, Sutherland, "Scrum: The Art of Doing Twice the Work in Half the Time", 2014).** A cell owns a vertical slice end-to-end (UI + API + data). Cells coordinate at an explicit sync, not continuously. Translating to two agents: each "cell" is a *workstream-family* (audio chain, director, compositor, observability). Within a family one agent owns all PRs; across families the two agents sync via the relay and never race.

**Conway's Law partitioning (Conway 1968; MacCormack et al. 2012).** System architecture mirrors the communication topology of the authoring teams. Corollary for agents: the partition you *pick* becomes the architectural seam. If delta owns `shared/` and alpha owns `agents/studio_compositor/`, the shared/agents interface will harden. If you partition by *feature family*, the feature-family seams harden instead. Pre-live, the livestream is the product — feature-family partition is the right bias.

**Feature-slice ownership (GitHub Flow / Shopify trunk-based development).** Each change is a short-lived branch → PR → squash-merge → deploy-on-green. Two parallel agents can use this safely iff: (a) branches are short (<4 h), (b) trunk stays deployable, (c) post-merge verification is automatic. All three already hold in this repo: branches are short by `work-resolution-gate.sh`, trunk runs `rebuild-services.timer`, alpha smoketests post-deploy per the 2026-04-18 plan. Feature-slice ownership is therefore the *existing default* — the question is how to partition slices between two agents without collision.

**AI-specific multi-agent coordination (recent).** LangGraph's `Command` primitive (2024) models explicit routing between agents as graph edges, not dynamic negotiation. AutoGen (Wu et al. 2023) found that deterministic turn-taking beats dynamic turn-taking on task-completion when agents are close peers — negotiation overhead dominates. CrewAI's "delegation with back-channel" pattern: one agent delegates, the other responds asynchronously, both persist state to a shared kv store. This is the closest fit to our file-based relay.

**Principles that port:**

1. **Partition the seam, not the work.** Decide what file-boundary the two agents will treat as a contract, harden that, and let each own everything on their side.
2. **Turn-taking beats negotiation.** When a task *can* be claimed by either agent, deterministic rules ("odd-numbered queue IDs to alpha, even to delta") are faster than bidding.
3. **The queue is the navigator.** In pair-programming terms, the queue file plays the navigator role — it holds the plan, flags drift, and survives across sessions.
4. **Short-lived branches, deployable trunk, automated post-deploy verification.** Already in place.
5. **Weak ownership + pre-edit declaration.** Avoid hard directory walls; use a file-level claim lock (already defined in `PROTOCOL.md` §9).
6. **Peer review is a pipeline stage, not an interrupt.** Beta owns audits, alpha owns smoketests — delta+alpha pair coordinates *upstream* of that pipeline, not around it.

References: Beck 1999; Cockburn & Williams 2000; Williams & Kessler 2003; Conway 1968; MacCormack, Baldwin & Rusnak 2012; Sutherland 2014; Wu et al. "AutoGen" 2023; LangGraph docs v0.2 (2024); CrewAI docs (2024).

---

## §2. Work-partitioning scheme

### 2.1 Options and trade-offs

**Option A — By directory/component.**
Alpha owns `agents/studio_compositor/**`, `agents/hapax_daimonion/**`, `agents/hapax_imagination/**`. Delta owns `shared/**`, `logos/**`, `docs/**`, `config/**`.
*Pros:* Deterministic, zero collision on file-edit, easy to explain, matches existing worktree separation.
*Cons:* Many of the 11 pre-live workstreams span both — voice-mod MIDI touches `agents/hapax_daimonion/` *and* `shared/midi_*.py` *and* `config/pipewire/`. Either one agent crosses the wall (breaking the contract) or two agents coordinate per-task (re-invents the queue). Also: `docs/` traffic is ~40% of delta's keystrokes by recent history — a directory wall starves alpha of cross-system context.

**Option B — By workstream / feature family.**
Alpha owns: audio chain (1), voice-mod MIDI (2), HARDM Phase 2 (3), director layer (4), token-meter (9). Delta owns: preset variety (5), de-monetization safety (6), observability Wave B (7), audit C/D/E (8), InsightFace (10), orphan wards + findings chrome + chat-keywords (11).
*Pros:* Each workstream has cohesive expertise concentration, PRs stay in one family, spec+impl+tests travel together, no cross-agent negotiation per task.
*Cons:* Families have coarse-grained size imbalance — HARDM Phase 2 alone is larger than three preset-variety phases combined. Requires size-normalization at planning time.

**Option C — By task weight / complexity.**
Alpha does multi-PR epics and multi-file structural work; delta does single-commit tactical fixes and research dispatch.
*Pros:* Maps to observed strengths (alpha has shipped the audit-closeout bundle, camera 24/7 epic; delta has shipped 103+ research drops and single-commit corrections).
*Cons:* Doesn't partition the *substrate* — both still touch the same files. Race risk concentrates on files that both care about (`shared/config.py`, `agents/effect_graph/*`, anything in the active PR's diff). This is the status-quo failure mode.

### 2.2 Recommendation — **Hybrid: workstream ownership with a shared-substrate escape hatch**

Primary partition is **by workstream family (Option B)**, because pre-live work is already organized that way and family ownership minimizes cross-agent cognitive load. Each family has a **primary owner** and a **secondary reviewer**. Delta and alpha each own ~half the families by estimated LOC, not family count.

Within each family, the owner authors specs, writes implementation PRs, owns CI-to-merge, and is the named reviewer for the peer's adjacent PRs.

**Shared-substrate escape hatch:** when a workstream *must* touch a file owned by a different family (e.g., voice-mod MIDI needs a new capability in `shared/midi_bus.py`), the owner writes a **substrate-claim note** to `~/.cache/hapax/relay/locks/<session>-<path-slug>.lock` *before* editing, per the existing §9 rule. The peer honors the lock or opens a merge-window discussion via relay.

**Proposed assignment:**

| # | Workstream | Owner | Reviewer | Rationale |
|---|-----|-------|----------|-----------|
| 1 | Audio chain (voice-mod MIDI, notif leak, L6, ducking) | alpha | delta | Alpha owns hapax_daimonion; audio chain is its output stage |
| 2 | Voice-mod MIDI dim refinement (Phase 2) | alpha | delta | Continuation of #1 |
| 3 | HARDM Phase 2 (per-cell rewrite + Hypothesis anti-face) | alpha | delta | Heavy algebraic work; alpha has been in this code |
| 4 | Director / content-programming layer | delta | alpha | Delta has drop #62 and spec authoring patterns; director sits atop director_loop and spans shared/ + docs/ |
| 5 | Preset-variety Phases 3–9 | delta | alpha | Delta has shipped 103+ research drops; preset variety is scoring-algorithm tuning with high research cadence |
| 6 | De-monetization safety multi-phase (4-layer) | alpha | delta | Touches studio_compositor + face_obscure_integration; alpha territory |
| 7 | Observability Wave B (emergent-misbehavior detectors) | delta | alpha | Detectors read jsonl files + write metrics; sits in shared/ + agents/health_monitor |
| 8 | Audit Wave C/D/E (MixQuality, replay harness, programmes, §19 ritual) | delta | alpha | Audit is delta's canonical output; replay harness is tooling |
| 9 | Token-meter Phase 2 (aesthetic refinement) | alpha | delta | Cairo rendering; alpha owns compositor |
| 10 | InsightFace face-matcher (#162/163) | alpha | delta | face_obscure + detection pipeline |
| 11 | Orphan wards (#178) + FINDING-W chrome (#179) + chat-keywords (#180) | delta | alpha | Cairo sources + chat reactor; sits between families, delta takes it by capacity |

Net split by estimated PR count: alpha ~7 workstreams (audio-heavy, compositor-heavy), delta ~4 workstreams (research-heavy, detector-heavy). Net split by estimated LOC: ~55% alpha / ~45% delta, which matches the asymmetry the operator already observes (alpha writes more code, delta writes more docs).

**Why this over pure-B:** HARDM Phase 2 and Audit Wave C/D/E are both plausible delta work; assigning them opposite ways gives alpha the implementation-heavy epic and delta the research-heavy epic, matching demonstrated strengths.

---

## §3. Relay protocol redesign

### 3.1 Per-agent outbox queue directory layout

Existing queue is a single flat directory (`~/.cache/hapax/relay/queue/*.yaml`). The v2 state machine is per-session (`queue-state-alpha.yaml`, `queue-state-epsilon.yaml`) but items are commingled.

Replace with per-agent outbox directories, preserving the flat queue for cross-session items:

```
~/.cache/hapax/relay/queue/
├── alpha/
│   ├── offered/        # items ready for alpha to pull
│   ├── in-flight/      # alpha has claimed, symlink to offered file
│   └── done/           # alpha has shipped, moved here on PR merge
├── delta/
│   ├── offered/
│   ├── in-flight/
│   └── done/
├── shared/             # unassigned items, either agent may claim
│   └── offered/
├── archive/            # unchanged
└── done/               # legacy flat done dir, kept for backward compat
```

**Atomicity of pickup:** agent picks up an item by `mv queue/alpha/offered/<id>.yaml queue/alpha/in-flight/<id>.yaml` — POSIX rename is atomic within the same filesystem. If two processes race, only one `mv` succeeds; the other gets `ENOENT`. No flock needed for pickup.

**Shipping:** on PR merge, `mv queue/alpha/in-flight/<id>.yaml queue/alpha/done/<id>.yaml` and write shipped-fields in the same transaction.

### 3.2 Polling cadence contract

| Event | Cadence |
|---|---|
| Active work in progress | No polling. Agent stays focused on current PR. |
| Between PRs (agent idle-adjacent) | Poll every 30 s for 5 min, then every 60 s for 10 min, then every 270 s (existing ScheduleWakeup default) |
| Cold start / session resume | Read once, pick highest-priority offered item |
| Peer finished a PR (observed via git log) | Immediate re-poll (peer may have unblocked a dependency) |

Cadence is enforced by the ScheduleWakeup primitive and by agent discipline, not by a daemon. 270 s is the existing watch interval; the 30 s / 60 s burst after a completion catches cascades.

### 3.3 Next-task pre-stocking

Every queue item has a `next_on_completion: <id>` field. When alpha ships item N, the queue state mutator auto-promotes `next_on_completion` from `queue/alpha/shared/` into `queue/alpha/offered/`. No delta intervention needed.

Pre-stocking rule for delta (populator):
- Write items in dependency-ordered chains of 3–5.
- Head of chain lands in `queue/alpha/offered/`.
- Tail of chain lands in `queue/alpha/shared/` with `blocked_on: <previous-id>`.
- Advance the chain on every completion observed.

This keeps the *visible* offered queue shallow (one or two items) — reducing alpha's pickup complexity — while pre-stocking several turns ahead.

### 3.4 Deadlock detection

Both agents can't block on each other if each owns their own lane. But cross-family work can create a cycle: alpha needs delta's `shared/midi_bus.py` PR merged; delta needs alpha's `agents/hapax_daimonion/midi_emitter.py` PR merged.

Detection mechanism: `scripts/relay-deadlock-check.py` (new). Runs every 270 s alongside the watch cycle. Walks `queue/*/in-flight/*.yaml`, builds the `blocked_on` graph, flags cycles via Tarjan. Emits an inflection at `~/.cache/hapax/relay/inflections/<ts>-auto-deadlock-detected.md` addressed `for: both`.

Resolution: the agent named first alphabetically (alpha) merges its PR partial, opens a follow-up issue for the blocked portion, and writes an unblock note to the other's queue.

### 3.5 Idempotent DONE marker

The completer writes `done: {pr: N, commit: SHA, at: <iso-ts>, by: <session>}` to the item YAML as a *single atomic replace* (write to `.tmp`, `mv`). Re-running the marker write is idempotent (same file).

Peer observes DONE by polling `queue/<peer>/done/*.yaml` — no ambiguity about who completed what.

### 3.6 Protocol tests

New test file `tests/relay/test_queue_protocol.py`:

| Test | Invariant |
|---|---|
| `test_pickup_is_atomic` | Two processes calling `mv` simultaneously; exactly one succeeds |
| `test_done_marker_idempotent` | Writing DONE twice leaves the file byte-identical |
| `test_next_on_completion_advances_chain` | After DONE on N, N+1 appears in offered/ |
| `test_deadlock_detector_finds_simple_cycle` | 2-node cycle detected |
| `test_deadlock_detector_finds_3_cycle` | 3-node cycle detected |
| `test_substrate_lock_prevents_concurrent_edit` | Alpha acquires lock, delta's acquire returns False |
| `test_substrate_lock_expires` | Stale lock (>10min old) auto-released on next acquire |
| `test_queue_state_yaml_schema` | Pydantic validation of every queue item |
| `test_shared_pool_claim_atomic` | Two agents racing on `shared/offered/X.yaml`, only one wins |
| `test_cold_start_resume_picks_highest_priority` | `urgent > normal > low` strictly enforced |

Tests are pure-Python, use `tmp_path` fixture, no network or external deps. Target: 100% protocol path coverage.

---

## §4. Conflict-avoidance protocol

### 4.1 Pre-edit declaration (substrate lock)

File: `~/.cache/hapax/relay/locks/<session>-<path-slug>.lock`. Content:

```yaml
session: alpha
path: shared/midi_bus.py
held_since: 2026-04-19T20:30:00Z
expires_at: 2026-04-19T20:40:00Z   # 10 min default
rationale: "voice-mod MIDI phase 2 — adding channel-strip dimension"
pr: null   # fill when PR opened
```

Acquire: write lock file atomically (`O_CREAT | O_EXCL`) — `FileExistsError` means peer holds it.
Check: peer reads lock file before editing the declared path.
Release: delete lock file on PR open (not commit — operator may iterate on uncommitted edits).
Expiration: 10 min. Rationale: a 10-min claim is long enough for coherent edits, short enough to unblock a stuck peer.

This mechanism already exists in `PROTOCOL.md` §9; the addition here is the **TTL + auto-expire** and a helper CLI:

```
hapax-lock acquire shared/midi_bus.py "voice-mod phase 2"  # exit 0 on success, 1 if held
hapax-lock release shared/midi_bus.py                       # exit 0
hapax-lock list                                             # JSON of all active locks
```

### 4.2 Rebase discipline

Pre-push rule: always `git fetch origin main && git rebase origin/main` before `git push`. No exceptions.

Pre-commit rule: the existing `rebase-needed` hook detects when your branch base ≠ `origin/main` *and* main has moved ≥3 commits since your branch point. Warns, does not block.

Force-push rule: blocked on shared branches (`main`, `alpha/*`, `delta/*`) by existing `no-stale-branches.sh`. Permitted on personal feature branches after rebase. **Never** permitted on a PR branch another agent has reviewed — that loses review history.

### 4.3 Per-agent branch namespace

- Alpha creates: `alpha/<slug>` (feature) or `alpha/<epic>-phase-N` (epic phase)
- Delta creates: `delta/<slug>` or `delta/<epic>-phase-N`
- Shared coordination branches: `coord/<slug>` (rare; both agents must rebase before touching)

Hooks enforce: `no-stale-branches.sh` rejects branch creation outside these namespaces when unmerged branches exist in the peer's namespace. This is a *soft* check — the intent is to surface coordination, not block it.

### 4.4 CI-gate before merge

No branch merges to main without green CI. Enforced by GitHub branch protection; not by agent discipline.

Existing: SDLC pipeline (triage → plan → adversarial → axiom gate), ruff, pyright, unit tests.

Added for pre-live: **smoketest-on-main deployment gate**. After merge, `rebuild-services.timer` deploys within 5 min. Alpha's smoketest per the 2026-04-18 plan must pass. If smoketest fails within 10 min of merge, the author opens a revert PR *immediately*.

### 4.5 Merge-forward protocol

When both agents have open PRs against main and both go green at the same time:

1. **Alphabetic priority.** Alpha merges first (a < d).
2. **Delta rebases.** Delta's `git pull origin main --rebase` handles the rebase. If the rebase conflicts, delta marks its PR `needs-manual-merge` in queue-state and waits for alpha's smoketest to land.
3. **No force-push to shared branches.** If rebase produces a non-linear history, open a new PR rather than force-pushing.

---

## §5. Idleness prevention

### 5.1 When-idle decision tree

An agent enters the "idle" state when:
- Current PR is merged and green-on-deploy, AND
- Queue `offered/` directory is empty.

```
idle?
├── queue/<me>/offered/ has items?
│   └── yes → pick highest-priority, start work
├── queue/shared/offered/ has items I can claim?
│   └── yes → atomic claim via mv, start work
├── peer has an open PR awaiting review?
│   └── yes → review it (beta normally does this; if beta unavailable, delta/alpha pair-reviews)
├── recent research drop has un-actioned findings?
│   └── yes → propose queue items addressing findings, place in queue/shared/offered/
├── audit health checks overdue?
│   └── yes → run claude-md-rot, axiom-sweep, consent-trace, or storage-audit
├── my own queue-state YAML has stale entries?
│   └── yes → prune (mv stale → archive/)
├── docs directory has broken cross-refs?
│   └── yes → propose queue items to fix
├── self-dispatch: what have I been too busy to research?
│   └── yes → dispatch a research-agent via Agent tool
└── otherwise → ScheduleWakeup(270s), emit "idle-no-work" inflection
```

The tree is ordered by value-density: action on offered items yields the most, self-dispatched research the least. The final "no-work" inflection is a signal to the operator that the pre-live backlog is exhausted.

### 5.2 Specific idle fallbacks

**Auto-pull from shared pool.** `queue/shared/offered/` holds items either agent can claim. Delta populates this with items that don't belong to a single owner — cross-cutting refactors, docs cleanups, audit follow-ups. When an agent finishes everything in `queue/<me>/offered/`, it claims from shared.

**Self-dispatch research.** Rule of thumb: if the agent has <5 min of predicted work left and no queued items, dispatch a research agent on an under-investigated topic from the agent's own open-questions list. Research drops land in `docs/research/` and generate new queue items when they surface actionable findings.

**Peer-review peer's open PRs.** If beta is busy or unavailable for an audit, the other primary agent can run a light review (not a substitute for beta's audit). Reviews are commented on the PR, not merged into the workflow.

**Audits / health.** Rotate through `claude-md-rot`, `axiom-sweep`, `storage-audit`, `branch-audit`, `consent-trace`, `relay-deadlock-check`. Each audit should be runnable in ≤3 min and produce a ntfy-worthy summary.

**Documentation cleanup.** Cross-reference checker over `docs/research/**`; dead-link pruner; ADR backlog walker.

**Memory pruning.** Walk `~/.claude/projects/-home-hapax-projects/memory/` for stale entries, archive older than 60 days with zero references.

---

## §6. Safety rails

1. **No commits to main without CI green.** Enforced by branch protection. Pre-live, disable admin-merge for non-emergency work. Emergency = "livestream is down" and only with operator verbal approval.

2. **Destructive ops (reset --hard, checkout ., branch -f, worktree remove) are pre-blocked on feature branches with unmerged commits** — existing `no-stale-branches.sh`. Add: pre-block `git push --force` on any branch that has commits authored by the peer. Rationale: peer authorship means peer has reviewed, force-push rewrites that review.

3. **Force-push is permitted only on personal feature branches pre-review and only with `--force-with-lease`.** `--force-with-lease` detects the case where upstream moved (peer pushed a review fix); abort and ask.

4. **Rollback procedure.** If a merge lands bad work:
   - Alpha's smoketest catches it within 10 min → author opens revert PR (`revert-<original-sha>`).
   - Revert PR gets expedited review (both agents + no beta audit required for straight reverts).
   - Revert merges; smoketest reruns; if green, normal work resumes.
   - Delta writes a post-mortem research drop at `docs/research/<date>-incident-<slug>.md` documenting root cause + preventive queue items.

5. **Work-resolution gate** (`work-resolution-gate.sh`) prevents an agent from starting new work while open PRs exist in their namespace. This is the existing hook; respect it — do not `HAPAX_SKIP_WORK_GATE=1` without operator approval.

6. **Operator is never a blocker.** 10-min decision defaults (existing §7 rule) apply to both agents. Default actions must be reversible without operator intervention.

7. **Pre-live freeze for high-blast-radius files.** A short list of "do not touch without announcing" files: `shared/config.py`, `axioms/registry.yaml`, `shared/impingement_consumer.py`, `systemd/user/*.service`, `config/pipewire/*`. Any edit writes a substrate-lock and a brief rationale to the inflection log.

---

## §7. Measurement

### 7.1 Metrics

| Metric | Measurement | Target | Owner |
|---|---|---|---|
| **Time-to-first-commit per queue drop** | Wallclock from `offered/` mtime to first commit on the branch | p50 < 3 min, p95 < 10 min | delta+alpha |
| **Idle-time percentage** | Fraction of wallclock where agent is in idle state per §5.1 | < 10% per agent during pre-live | both |
| **Merge conflicts per day** | Count of `git rebase` with `CONFLICT` in output | = 0 (pre-live) | both |
| **Rework / revert rate** | Reverted PRs / total merged PRs | < 5% | both |
| **Tasks shipped per hour** | PRs merged per wallclock hour, both agents combined | ≥ 1 | both |
| **Queue buffer depth** | `ls queue/<agent>/offered/ | wc -l` at any moment | ≥ 2 per agent | delta (populator) |
| **Cross-family bleed** | PRs touching a file outside the owner's family | ≤ 1 per day | both |
| **Substrate lock contention** | Count of `hapax-lock acquire` returns 1 (peer held) | ≤ 3 per day | both |
| **Deadlock detections** | Inflections emitted by the deadlock detector | = 0 | both |
| **CI green rate on first push** | PRs with green CI on initial push / all PRs opened | ≥ 80% | both |

### 7.2 Collection

- Metrics are derived from (a) git log, (b) queue directory state at each watch tick, (c) relay inflection count, (d) GitHub API via `gh pr list --json`.
- Collector: `scripts/relay-metrics-emit.py` (new) runs every 270 s alongside the watch cycle, writes a single JSON line to `~/.cache/hapax/relay/metrics/YYYY-MM-DD.jsonl`.
- Downstream: Prometheus text exporter at `127.0.0.1:9485/metrics` reads the latest JSONL. Grafana dashboard `relay-coordination` (new) consumes it.

### 7.3 Dashboard (Grafana)

Panels:
1. Time-to-first-commit histogram (per-agent series, p50/p95 bands).
2. Idle-time percentage stacked bar (per-agent, per-hour).
3. Queue buffer depth line (per-agent, with target band 2–15 shaded).
4. Merge conflicts + deadlock detections count (big-number panels, alert if >0).
5. Cross-family bleed counter (daily heatmap).
6. CI green-on-first rate gauge (weekly rolling).

Alert rules:
- `idle_time_pct > 15%` for 10 min → ntfy warning.
- `queue_buffer_depth < 1` for 5 min → ntfy critical to delta.
- `deadlock_detections > 0` → ntfy critical to both.
- `merge_conflicts_today > 0` → ntfy warning to both.

Retention: 14 days on Prometheus, indefinite in JSONL.

---

## §8. Implementation steps

Ordered, concrete, shippable in one sitting.

### Step 1 — Create new queue directory structure (1 PR, delta)

```bash
mkdir -p ~/.cache/hapax/relay/queue/{alpha,delta}/{offered,in-flight,done}
mkdir -p ~/.cache/hapax/relay/queue/shared/offered
mkdir -p ~/.cache/hapax/relay/metrics
```

Migrate existing flat queue items:
```bash
# For each queue/*.yaml in root of queue/, inspect `assigned_to:` field
uv run python scripts/relay-migrate-queue.py --dry-run
uv run python scripts/relay-migrate-queue.py --apply
```

The migration script is small (~80 LOC) and lives at `scripts/relay-migrate-queue.py`. Preserves the flat queue for backward compat; moves each item into `queue/<assignee>/offered/`.

Deliverables:
- `scripts/relay-migrate-queue.py`
- `tests/relay/test_migrate_queue.py`
- Updated `~/.cache/hapax/relay/PROTOCOL.md` §Directory Layout

### Step 2 — Write protocol tests (1 PR, delta)

`tests/relay/test_queue_protocol.py` per §3.6. 10 tests. Must be hermetic (tmp_path fixture, no network).

```bash
uv run pytest tests/relay/ -v
```

Deliverables:
- `tests/relay/test_queue_protocol.py`
- `tests/relay/conftest.py` (if needed for shared fixtures — per workspace convention, keep self-contained first)

### Step 3 — Implement the polling-loop script (1 PR, alpha)

`scripts/relay-agent-loop.sh`: the idle-time decision tree from §5.1. Intended to be invoked manually by each agent between PRs; not a daemon.

```bash
# Usage
scripts/relay-agent-loop.sh --as alpha --max-iterations 5
```

Also the substrate-lock CLI:

```bash
# hapax-lock in ~/.local/bin/
hapax-lock acquire <path> <rationale>
hapax-lock release <path>
hapax-lock list
```

Deliverables:
- `scripts/relay-agent-loop.sh`
- `~/.local/bin/hapax-lock` (symlink to `scripts/hapax-lock.py`)
- `tests/scripts/test_hapax_lock.py`

### Step 4 — Implement metrics collector + Grafana dashboard (1 PR, delta)

```
scripts/relay-metrics-emit.py          # JSONL writer, invoked every 270 s
scripts/relay-metrics-exporter.py      # Prometheus text exporter on :9485
config/grafana/dashboards/relay-coordination.json
```

Wire into `systemd/user/hapax-relay-metrics.timer` (5 min cadence). Grafana provisioning picks up the dashboard JSON automatically (existing pattern).

Deliverables:
- three scripts above
- systemd timer unit + service unit
- Grafana dashboard JSON
- `tests/scripts/test_relay_metrics_emit.py`

### Step 5 — Populate the pre-live backlog per §2.2 (1 PR, delta)

Walk the 11 workstreams. Write 3–5 queue items per workstream with full acceptance criteria. Place in `queue/<owner>/offered/` (first item) and `queue/<owner>/shared/` with `blocked_on` (tail).

Item template:

```yaml
id: alpha-301
title: "Audio chain: voice-mod MIDI channel-strip dim"
owner: alpha
reviewer: delta
workstream: "audio-chain"
status: offered
priority: normal
depends_on: []
next_on_completion: alpha-302

description: |
  Implement the channel-strip dimension in the voice-mod MIDI bridge.
  Reference: docs/superpowers/specs/2026-04-XX-voice-mod-phase-2.md §3.1
target_files:
  - agents/hapax_daimonion/voice_mod_midi.py
  - shared/midi_bus.py  # SUBSTRATE — acquire lock before editing
  - tests/hapax_daimonion/test_voice_mod_midi_phase2.py
acceptance: |
  - channel-strip dimension emits CC on the configured channel
  - Hypothesis property test covers ±{0.0, 0.5, 1.0} boundaries
  - manual test: open Evil Pet, observe MIDI in
size_estimate: ~200 LOC + 8 tests
created_at: 2026-04-19T20:45:00Z
created_by: delta
```

Ship ~40 queue items across the 11 workstreams.

Deliverables:
- queue items under `~/.cache/hapax/relay/queue/{alpha,delta}/offered/` and `...shared/`
- `queue-state-alpha.yaml` and new `queue-state-delta.yaml` updated

### Step 6 — Dry-run (both agents, 2 hours)

Run the new protocol for 2 hours with instrumentation on. Specifically:

- Alpha picks an item from `queue/alpha/offered/`, ships a PR, merges, verifies via `queue/alpha/done/` move.
- Delta picks an item from `queue/delta/offered/`, ships a PR, merges.
- Deliberately induce a substrate conflict: delta starts editing `shared/config.py`, alpha tries to edit the same file. Verify `hapax-lock` blocks alpha.
- Deliberately induce a dependency chain: alpha ships 301, verify 302 auto-promotes into `queue/alpha/offered/`.
- Run `scripts/relay-deadlock-check.py`: should emit zero inflections.
- Read the Grafana dashboard; verify all 6 panels render.

Log observations to `~/.cache/hapax/relay/inflections/<ts>-delta-alpha-protocol-dry-run.md`.

### Step 7 — Ratify (operator)

Operator reviews the dry-run inflection, approves protocol, or requests changes. Default action if operator doesn't respond in 24 h: protocol is adopted (this is a reversible change — we can revert the directory migration with `scripts/relay-migrate-queue.py --revert`).

Deliverables:
- `~/.cache/hapax/relay/PROTOCOL.md` version bumped to v2.1
- Announcement inflection addressed `for: both`

### Step 8 — Steady-state operation

Protocol is live. Both agents follow the decision tree in §5.1 between PRs. Metrics visible on Grafana. Delta continues queue population; alpha continues primary implementation work on its owned workstreams.

Re-evaluate after 1 week of steady-state: check metrics against targets in §7.1. If any metric is off by >2x, write a remediation inflection.

---

## §9. Non-goals

- **Replacing beta/epsilon coordination.** Beta still audits, epsilon still owns Pi fleet. Their existing protocols stand unchanged.
- **Daemonizing the coordination.** The relay stays file-based; agents remain the actors. No long-running process owns the protocol.
- **Semantic work distribution.** No LLM tries to decide who should own what — the partition in §2.2 is static for the pre-live sprint.
- **Post-live carry-over.** This protocol is scoped to pre-live. After go-live, retune based on observed stream-operation workload.

---

## §10. Rollback

If the new protocol causes more friction than the current flat queue:

1. `scripts/relay-migrate-queue.py --revert` moves all `queue/<agent>/offered/*.yaml` back to `queue/*.yaml`.
2. Delete `queue/{alpha,delta,shared}/` subdirs.
3. Revert the `PROTOCOL.md` doc change.
4. Write a post-mortem at `docs/research/<date>-delta-alpha-protocol-retrospective.md`.
5. Fall back to the v2 per-session queue-state YAML as the authoritative pull mechanism.

Rollback is a ~2-min operation, single commit.

---

## §11. Open questions

1. **Should `queue/shared/offered/` have a claim-race policy beyond atomic mv?** Currently first-mv-wins. Could be priority-weighted (alpha gets preference on even minutes, delta on odd) if bias is observed.
2. **Is 270 s the right long-poll cadence?** Inherited from inflection polling. The 30 s / 60 s / 270 s back-off after a completion may need tuning.
3. **Who writes `queue-state-delta.yaml`?** Delta currently does not maintain its own status file (per onboarding-delta.md). Adopting this protocol requires delta to write one. Low cost, but a norm-change.
4. **Does alpha need a dedicated delta-facing worktree?** Current alpha worktree is `~/projects/hapax-council/` (primary). No change proposed, but if substrate-lock contention is high (>3/day), consider a throwaway worktree for cross-family work.
5. **How does this interact with the 2026-04-18 trio-delivery plan?** Delta+alpha pair here is upstream of that pipeline; beta/alpha audit-smoketest roles stay downstream. The plan should be updated to reference this protocol at its §3 (Relay Files) section. Minor doc sync.

---

*End of design.*
