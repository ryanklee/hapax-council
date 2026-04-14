# LIVESTREAM RESEARCH READY — Epic Execution Plan

> **For agentic workers:** This is a multi-phase epic spanning weeks. Each phase produces one or more PRs. The `superpowers:subagent-driven-development` or `superpowers:executing-plans` skills apply at the per-phase level, NOT at the epic level — open one phase at a time, write its design spec + plan, execute it, merge it, then move to the next.

**Goal:** Arrive at the end-state triad — Hapax running on Hermes 3 70B SFT-only, serving a 24/7 Legomena Live research medium, with Hapax as the continual content programmer and research-objective-pursuer.

**Epic design:** `docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md` (authoritative; this plan is the execution companion)

**Predecessor research map:** `~/.cache/hapax/relay/context/2026-04-13-livestream-as-research-medium-research-map.md` (scope reference, not authoritative — the epic design doc supersedes it)

**Duration estimate:** 22-30 sessions across 4-6 weeks, time-gated by Phase 4 voice session cadence

**Session roles:** alpha drives execution end-to-end. Beta is available for parallel work if needed, but most phases are serialized by branch discipline and by research-validity constraints that require a single author per condition transition.

---

## 1. Execution model

This epic is too large for one session. It is structured to be picked up incrementally by future alpha sessions (and possibly beta sessions for parallelizable sub-items). Each session picks up **exactly one phase** at a time — no phase skipping, no inter-phase parallelism without explicit spontaneous-worktree coordination.

**Invariants across all phases:**

- **One active phase at a time.** `~/.cache/hapax/relay/lrr-state.yaml` (created at Phase 0 open) holds the `current_phase` field. Sessions picking up LRR work check this file first.
- **Phase N opens only after Phase N-1 is closed** (exit criteria met, PR merged, handoff written). Exceptions: Phase 4 is time-gated and runs in parallel with Phase 3 prep work.
- **Each phase is its own branch + PR.** Branch name: `feat/lrr-phase-N-<slug>`. No multi-phase branches.
- **Every phase writes a handoff doc** at `docs/superpowers/handoff/YYYY-MM-DD-lrr-phase-N-complete.md` on close.
- **Frozen files are enforced** (Phase 1 forward). Pre-commit hook blocks any change to the current condition's `frozen_files` manifest.
- **Research-registry state follows the code.** Condition changes happen at the moment of substrate change, not before. The registry is append-only.

---

## 2. Phase pickup procedure

Every session that picks up an LRR phase follows this sequence:

```
STEP 1: Onboard (standard alpha/beta relay session start)
  - Read ~/.cache/hapax/relay/onboarding-{role}.md
  - Read ~/.cache/hapax/relay/PROTOCOL.md
  - Read peer status (alpha.yaml / beta.yaml)
  - Check for new inflections

STEP 2: LRR state check
  - Read ~/.cache/hapax/relay/lrr-state.yaml
  - Note current_phase, last_completed_phase, known_blockers
  - If current_phase has an open PR: either continue that work OR wait
  - If no current_phase: next available phase per dependency graph

STEP 3: Read the epic design
  - docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md
  - Skip to the phase you're opening; read the whole section
  - Read the prior phase's handoff doc for context

STEP 4: Write the per-phase spec + plan
  - docs/superpowers/specs/YYYY-MM-DD-lrr-phase-N-<slug>-design.md
    - Extract the scope from the epic design's Phase N section
    - Add any phase-specific decisions made since the epic was authored
    - Include exit criteria from the epic (verbatim or updated)
  - docs/superpowers/plans/YYYY-MM-DD-lrr-phase-N-<slug>-plan.md
    - TDD/checkbox task breakdown
    - Use `superpowers:writing-plans` skill
    - Reference the spec; do not duplicate
  - Commit both under the same PR as the implementation (see Step 6)

STEP 5: Execute the phase
  - Follow the per-phase plan
  - Update ~/.cache/hapax/relay/lrr-state.yaml as milestones are hit
  - Run verification commands for each exit criterion
  - Do NOT claim phase complete until every exit criterion verifies

STEP 6: Close the phase
  - Write the handoff doc at docs/superpowers/handoff/YYYY-MM-DD-lrr-phase-N-complete.md
  - Update ~/.cache/hapax/relay/lrr-state.yaml (move current_phase forward)
  - Update docs/research/lrr-progress.md with completion checkmark
  - Open the PR with the spec + plan + implementation + handoff
  - Merge when CI green + operator review (if required per phase)
  - Move to Step 1 for the next phase OR retire the session
```

---

## 3. LRR state file

**Location:** `~/.cache/hapax/relay/lrr-state.yaml`

**Created:** at Phase 0 open

**Schema:**

```yaml
epic_id: livestream-research-ready
epic_design_doc: docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md
epic_plan_doc: docs/superpowers/plans/2026-04-14-livestream-research-ready-epic-plan.md

current_phase: 0  # or null if epic paused
current_phase_owner: alpha  # which role holds the active phase
current_phase_branch: feat/lrr-phase-0-verification
current_phase_pr: null  # set when PR opens
current_phase_opened_at: 2026-04-14T10:00:00Z

last_completed_phase: null
last_completed_at: null
last_completed_handoff: null

completed_phases: []

known_blockers: []
  # Example entry:
  # - phase: 4
  #   blocker: sprint-0-g3
  #   description: G3 sprint gate blocks Condition A baseline collection
  #   discovered_at: 2026-04-15T00:00:00Z
  #   resolved_at: null
  #   resolution: null

current_condition: cond-phase-a-baseline-qwen-001  # from research-registry
previous_condition: null

notes: |
  Epic picked up by alpha on 2026-04-14. Phase 0 in progress.
```

**Rules:**

- Written by sessions that execute phases; read by all sessions.
- Single-writer at a time (the session that holds `current_phase_owner`).
- Any session picking up LRR work reads this file in Step 2 of the pickup procedure.
- Never edit manually — use `scripts/lrr-state.py` (to be created in Phase 0).

---

## 4. Coordination between planning and execution sessions

This epic was planned in a long conversational session between the operator and alpha on 2026-04-13 and 2026-04-14. That planning session:

1. Ran 5 parallel investigations into the scope
2. Wrote the predecessor research map (`~/.cache/hapax/relay/context/2026-04-13-livestream-as-research-medium-research-map.md`)
3. Captured operator decisions (DF-1 posture problem, D-1 substrate-first, D-2 Option B, end-state triad)
4. Did a synthesis pass against Garage Door Open + livestream-performance-map
5. Wrote this epic design doc + two audit passes + three rounds of patching
6. Landed the epic design in git via this PR

**Future execution sessions inherit the epic** via:

- **Git:** the epic design spec + this plan doc are on main
- **Relay:** `lrr-state.yaml` holds the current execution state; `alpha.yaml` / `beta.yaml` hold session-level status
- **Handoff docs:** per-phase handoffs at `docs/superpowers/handoff/YYYY-MM-DD-lrr-phase-N-complete.md`
- **Research registry:** `~/hapax-state/research-registry/` (starting Phase 1) holds condition state
- **Context artifacts:** `~/.cache/hapax/relay/context/` for any working material that doesn't land in git

**The planning session does not return.** Future alpha sessions may reference the predecessor research map for scope context, but the epic design doc is the authoritative source.

---

## 5. Per-phase kickoff checklist

Use this at the start of every phase:

- [ ] Relay onboarding complete (Step 1 of pickup)
- [ ] `lrr-state.yaml` current_phase matches the phase I'm opening
- [ ] Prior phase's handoff doc read
- [ ] Epic design doc Phase N section read in full
- [ ] No unresolved `known_blockers` for this phase
- [ ] Branch discipline check: no unmerged branches blocking `git checkout -b`
- [ ] Spontaneous worktree created: `git worktree add ~/projects/hapax-council--lrr-phase-N -b feat/lrr-phase-N-<slug>`
- [ ] Per-phase spec drafted in `docs/superpowers/specs/`
- [ ] Per-phase plan drafted in `docs/superpowers/plans/` (TDD checkboxes)
- [ ] Phase 4 specifically: operator sign-off on OSF pre-reg filing if applicable
- [ ] Phase 5 specifically: operator present for the substrate swap (high-risk op)
- [ ] Phase 7 specifically: operator sign-off on persona YAML before commit
- [ ] Phase 10 specifically: FINDING-S decision recorded before closing

---

## 6. Per-phase close checklist

- [ ] Every exit criterion from the epic design Phase N section verified by running a command or test
- [ ] Verification outputs captured in the handoff doc
- [ ] Phase PR merged to main
- [ ] Spontaneous worktree removed: `git worktree remove ~/projects/hapax-council--lrr-phase-N`
- [ ] `lrr-state.yaml` updated: current_phase → N+1, last_completed_phase → N, completed_phases appended
- [ ] Handoff doc at `docs/superpowers/handoff/YYYY-MM-DD-lrr-phase-N-complete.md` committed
- [ ] Relay status updated: `alpha.yaml` (or `beta.yaml`) notes the merged PR and the next phase
- [ ] Any new known_blockers for downstream phases logged in `lrr-state.yaml`
- [ ] If the phase opened a condition change: research-registry state verified
- [ ] `RESEARCH-STATE.md` updated if the phase touched voice grounding research
- [ ] Convergence log updated if parallel peer session exists

---

## 7. Handoff doc template

```markdown
# LRR Phase N Completion Handoff — YYYY-MM-DD

**Phase:** N — <phase name>
**Owner:** alpha (or beta)
**Session:** <session identifier>
**Merged PR:** #<number>
**Branch (deleted on merge):** feat/lrr-phase-N-<slug>

## What shipped

[Bullet list of specific deliverables — files added, services modified, metrics added, decisions made]

## Exit criteria verification

For each exit criterion from the epic design Phase N section:

- [x] Criterion text — verification command output or evidence

## Deviations from the plan

[Anything that differed from the original phase spec. Include rationale.]

## Known issues surfaced

[New bugs, new gaps, new blockers that were discovered during execution but not resolved in this phase.]

## Next phase prerequisites

[What the next phase needs that wasn't included in the epic design.]

## Condition registry state (if changed)

- Before: cond-<...>
- After: cond-<...>
- DEVIATION filed: DEVIATION-NNN (if applicable)

## Relay state updates

- lrr-state.yaml updated: [field changes]
- alpha.yaml updated: [field changes]

## Time to completion

- Opened at: <ts>
- Closed at: <ts>
- Wall clock: <hours>
- Sessions spent: <N>

## Pickup-ready note for the next session

[One or two paragraphs the next session can read cold to understand what state the epic is in.]
```

---

## 8. Parallelism rules

Most phases are serialized by:

1. **Branch discipline** (`no-stale-branches.sh` blocks new branches when unmerged branches exist)
2. **Research validity** (condition changes are single-author, single-session events)
3. **Execution dependency** (Phase 5 requires Phase 4 to be complete; Phase 8 requires Phase 7; etc.)

**Allowed parallelism:**

- **Phase 3 and Phase 4 can overlap.** Phase 3 is hardware prep (engineering work). Phase 4 is data collection (operator time). Phase 4 runs on the CURRENT substrate (Qwen) while Phase 3 prepares the NEXT substrate (Hermes). This is the only explicit parallelism in the epic.
- **Phase 10 sub-items can overlap** — some are cross-repo fixes (`llm-stack/`), some are per-condition observability wiring, some are drills. A single session can work multiple Phase 10 items in sequence without branching between them.
- **Beta participation:** if beta is active, beta can work on peer-research work (e.g., livestream-performance-map follow-ups, new claims outside LRR scope). Beta should NOT pick up LRR phases unless alpha is retired and beta is taking over.

**Forbidden parallelism:**

- Two sessions working different LRR phases simultaneously (branch discipline + condition registry integrity)
- Any phase skipping
- Any condition change outside Phase 5 (the only authorized condition transition in the epic)

---

## 9. Bootstrap for the next alpha session

A fresh alpha session picking up this epic for the first time (not the planning session) should:

1. **Standard relay onboarding** (read `onboarding-alpha.md`, `PROTOCOL.md`, peer status, inflections)
2. **Read `lrr-state.yaml`.** If it doesn't exist: you are the first execution session. Create it with `current_phase: 0`.
3. **Read this plan doc in full.** Start at §1.
4. **Read the epic design doc** (`docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md`). At minimum: §0 Headline, §3 Guiding Principles, §4 Phase Summary, Phase 0 section.
5. **Read the predecessor research map** at `~/.cache/hapax/relay/context/2026-04-13-livestream-as-research-medium-research-map.md` for scope context. Not authoritative — just background.
6. **Verify the world is in the state the epic assumes.** The epic design §2 has a "Pre-epic verification findings (2026-04-14)" section. Re-run those verifications if > 1 week has passed since the epic was authored. Things may have drifted.
7. **Open Phase 0.** Follow §2 Phase pickup procedure steps 3-6. Write the Phase 0 per-phase spec + plan. Execute. Close. Handoff. Move on.

---

## 10. Phase-by-phase quick reference

Concise pointers. Full content is in the epic design doc.

| Phase | Slug | Spec file (per-phase) | Key verification |
|---|---|---|---|
| 0 | `verification` | `specs/YYYY-MM-DD-lrr-phase-0-verification-design.md` | chat-monitor active, token ledger multi-component, /data inodes ≤85%, FINDING-Q 2-4 shipped, Sierpinski baseline, RTMP path confirmed, huggingface-cli, voice transcript path, Kokoro baseline |
| 1 | `research-registry` | `specs/YYYY-MM-DD-lrr-phase-1-research-registry-design.md` | registry dir + YAML, research-marker SHM, condition_id in JSONL+Qdrant+Langfuse, frozen-file pre-commit, stats.py BEST, backfill verified, Qdrant schema drift closed |
| 2 | `archive-research-instrument` | `specs/YYYY-MM-DD-lrr-phase-2-archive-research-instrument-design.md` | archival re-enabled, segment sidecars, research marker frames, archive-search CLI, vault integration, layout-declared video_out |
| 3 | `hardware-validation` | `specs/YYYY-MM-DD-lrr-phase-3-hardware-validation-design.md` | Option γ partition live, driver/CUDA verified, PSU stress passed, thermals pass, Hermes 3 quant downloaded, config draft, rollback documented, cable hygiene, brio-operator re-measure |
| 4 | `phase-a-completion` | `specs/YYYY-MM-DD-lrr-phase-4-phase-a-completion-design.md` | G3 resolved or documented, ≥10 Condition A sessions, OSF pre-reg filed, data checksums, Qdrant snapshot, Condition A collection_halt_at marked |
| 5 | `hermes-3-substrate-swap` | `specs/YYYY-MM-DD-lrr-phase-5-hermes-3-substrate-swap-design.md` | Hermes 3 70B EXL3 active, directive compliance ≥3/5, condition transition atomic, DEVIATION-037 filed, consent-latency drill passes, speech-continuity test passes, CAPABLE routing preserved |
| 6 | `governance-finalization` | `specs/YYYY-MM-DD-lrr-phase-6-governance-finalization-design.md` | `it-irreversible-broadcast` merged, `hapax-stream-mode` CLI, redaction test matrix, ConsentGatedWriter, stimmung auto-private, presence-detect closed loop, revocation drill, su-privacy-001 + corporate_boundary amendments, fortress enum retired, ConsentRegistry validation |
| 7 | `persona-spec` | `specs/YYYY-MM-DD-lrr-phase-7-persona-spec-design.md` | `axioms/persona/hapax-livestream.yaml` committed with operator sign-off, persona_renderer compiles <500 tokens, injection verified, register shift measurable |
| 8 | `content-programming-via-objectives` | `specs/YYYY-MM-DD-lrr-phase-8-content-programming-via-objectives-design.md` | objectives authored, hapax-objectives CLI, director loop objective-advancement scoring, overlay tiles, hero mode, Stream Deck, YouTube description auto-update, attention bids, environmental perception, overlay content formalization |
| 9 | `closed-loop-feedback` | `specs/YYYY-MM-DD-lrr-phase-9-closed-loop-feedback-design.md` | chat signals → stimmung → activity scoring, research-aware chat reactor, daimonion code-narration with SHM publishers, async chat queue, scientific captions, stimmung-vs-stream correlation, operator-voice-over-YouTube ducking |
| 10 | `observability-drills-polish` | `specs/YYYY-MM-DD-lrr-phase-10-observability-drills-polish-design.md` | per-condition Prometheus slicing, stimmung dashboards, 6 drills + 2-hour stability, FINDING-S decision, T3 prompt caching, PERCEPTION_INTERVAL tuned, consent + surface audit trails, cross-repo scrape fixes, C2/C3 exporters, weekly correlation report, pre/post stimmung delta |

---

## 11. When this epic completes

At Phase 10 close:

- `lrr-state.yaml` sets `current_phase: null` and `completed_phases: [0,1,2,3,4,5,6,7,8,9,10]`
- Final handoff doc: `docs/superpowers/handoff/YYYY-MM-DD-lrr-epic-retirement.md`
- Relay status updated across alpha + beta
- Research registry has ≥2 conditions (Condition A baseline + Condition A' Hermes)
- All exit criteria from the epic design §11 satisfied
- Voice grounding `RESEARCH-STATE.md` updated with epic completion
- Epic design + plan docs remain as historical record; future work is a new epic

**"Research is complete"** is not the right frame. The research is never complete — it is stationary / adaptive per I-1. The epic completes; the research continues. New epics branch off future conditions. The livestream is the ongoing substrate.

---

End of execution plan. Open Phase 0.
