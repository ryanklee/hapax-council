# HSEA Phase 3 — Research Program Orchestration (Cluster C) — Design Spec

**Date:** 2026-04-15
**Author:** delta (pre-staging extraction; HSEA execution remains alpha/beta workstream)
**Status:** DRAFT pre-staging — awaiting operator sign-off + LRR UP-6 close before Phase 3 open
**Epic reference:** `docs/superpowers/specs/2026-04-14-hsea-epic-design.md` §5 Phase 3 (brief) + `docs/research/2026-04-14-hapax-self-executes-tactics-as-content.md` drop #58 §3 Cluster C (detailed)
**Plan reference:** `docs/superpowers/plans/2026-04-15-hsea-phase-3-research-program-orchestration-plan.md`
**Branch target:** `feat/hsea-phase-3-research-program-orchestration`
**Cross-epic authority:** drop #62 §5 UP-11 (HSEA Phase 3 + LRR Phase 8/9 co-ship) + §3 ownership table rows 2/5/6
**Unified phase mapping:** **UP-11 Content programming + objectives + closed loop** (drop #62 §5 line 146): LRR Phases 8 + 9 own infra; HSEA Phase 3 owns C-cluster narration on top. Depends on UP-3 + UP-10. ~2,500 LOC HSEA Phase 3 portion of UP-11 total.

---

## 1. Phase goal

Automate the LRR research program flow end-to-end with Hapax as the **preparer at every stage** — narrating voice grounding sessions, auditing attribution integrity, drafting PRs from other sessions' worktree commits, verifying the PyMC 5 BEST port live on stream, running triple-session ritualized cadence timers, amending OSF pre-registrations, reacting to the 8B pivot as a spectator event, composing research drops from milestones, and shipping publishable result drops with hard verification gates.

**What this phase is:** 11 C-cluster sub-drafters (C2-C12) that orchestrate the LRR research program pipeline. Each drafter composes `ComposeDropActivity` from HSEA Phase 2 deliverable 3.6 (per drop #62 Q3 rescoping — narration-only, not code-drafting). Together they form the "Hapax prepares; operator delivers" loop that converts LRR research events into stream content + governance-queue items.

**What this phase is NOT:** does not ship LRR Phase 8 (content programming via objectives; that's LRR scope within UP-11), does not ship LRR Phase 9 (closed-loop feedback; also LRR within UP-11), does not ship the persona spec (LRR Phase 7 / UP-9), does not ship `compose_drop` or `synthesize` activity primitives (HSEA Phase 2). Phase 3 is the C-cluster narration LAYER on top of those primitives.

**Drop #58 framing:** drop #58 §3 Cluster C establishes that Hapax-as-preparer is the tactical answer to drop #57 T2.x research-stream-support family. Every C-cluster deliverable is a discrete touch point where Hapax transforms a research event (session start, attribution audit tick, PR merge, quant swap, result drop) into narrated content + governance-queue items.

---

## 2. Dependencies + preconditions

**Cross-epic (from drop #62 §5 line 146):**

1. **LRR UP-0 + UP-1 closed.** Standard chain.
2. **LRR UP-3 (Phase 2 archive instrument) closed.** C11 "publishable result composer" reads archived segments for the Phase A results drop.
3. **HSEA UP-2 (Phase 0) closed.** Every C-cluster deliverable uses governance queue + spawn budget + promote scripts.
4. **HSEA UP-4 (Phase 1 visibility surfaces) closed.** C3 attribution audit narration daemon writes to the research state broadcaster's data source; C6 triple-session ritualized cadence surfaces via the governance queue overlay.
5. **HSEA UP-10 (Phase 2 core director activities) closed.** C-cluster drafters ALL compose `ComposeDropActivity` from HSEA Phase 2 deliverable 3.6 as narration-only spectator drafters. Without Phase 2, C-cluster has no narrator base class.
6. **LRR UP-9 (Phase 7 persona) closed.** Transitively via HSEA Phase 2.
7. **LRR Phase 4 (UP-6 Phase A completion + OSF pre-registration) closed for C6, C7, C11.** C6 requires condition_id plumbing, C7 amends the OSF pre-reg, C11 ships once Phase A has actual results.

**Intra-epic:** HSEA Phase 0, 1, 2 all closed.

**Infrastructure:**

1. `ComposeDropActivity` public API from HSEA Phase 2 deliverable 3.6 — the narrator base.
2. LRR research registry + condition_id taxonomy (LRR Phase 1 deliverables).
3. OSF project (created at LRR Phase 1 item 6; filed at LRR Phase 4).
4. PyMC 5 BEST implementation (LRR Phase 1 item 7).
5. Research integrity heartbeat file `~/hapax-state/research-integrity/heartbeat.json` (LRR Phase 1 adjacent).
6. `scripts/research-registry.py` CLI (LRR Phase 1).
7. `agents/hapax_daimonion/voice_session/` (existing voice grounding infrastructure).
8. Beta worktree reading capability for C4 (read-only; C4 does NOT write to beta's worktree).

---

## 3. Deliverables (11 items: C2–C12)

Each deliverable is a narrator drafter that subclasses or composes `ComposeDropActivity` from HSEA Phase 2 deliverable 3.6. Per drop #62 §10 Q3 ratification, NONE of these ship code directly — they produce research drops and governance-queue entries that the operator reviews and approves.

### 3.1 C2 — Voice grounding session spectator event

**Scope:**
- `/voice-session` director activity that watches for voice grounding session start (via a `/dev/shm/hapax-voice/session-active.flag` file written by the voice pipeline)
- On session start: composes a governance queue entry "voice grounding session started at <timestamp>, condition_id=X" + narrates the start on stream
- On session end: composes a session summary drop with: duration, utterance count, stance transitions, condition_id, any notable events
- Narration-only: no code changes, no voice pipeline modifications
- **Target files:** `agents/hapax_daimonion/cluster_c/voice_session_spectator.py` (~150 LOC)
- **Size:** ~200 LOC with tests

### 3.2 C3 — Attribution audit narration daemon

**Scope:**
- New systemd user timer `hapax-attribution-audit-narrator.timer` (every 10 minutes)
- Reads `~/hapax-state/research-integrity/heartbeat.json`; compares `attribution_tier` to previous tick's value
- On tier change (direct → derived, or direct → orphaned): composes a research drop summarizing what changed + why it matters
- Writes to governance queue for operator review
- **Target files:** `agents/hapax_daimonion/cluster_c/attribution_audit_narrator.py` (~180 LOC) + systemd unit files
- **Size:** ~250 LOC with tests

### 3.3 C4 — Phase 4 PR drafting (LRR Phase 4 beta worktree reader)

**Scope:**
- Reads the `beta-phase-4-bootstrap` branch (or whatever branch LRR Phase 4 ships on) via `git log` + `git diff` subprocess calls
- Detects new commits since the last scan
- For each new commit: drafts a PR body paragraph describing the change (title, rationale, test coverage)
- Composes the per-commit paragraphs into a full PR body draft for LRR Phase 4
- Writes the drafted PR body to `/dev/shm/hapax-compositor/draft-buffer/lrr-phase-4-pr.partial.md`
- Governance queue entry: "LRR Phase 4 PR draft updated, N new commits processed"
- **Does NOT open the PR** — operator reviews the draft + opens the PR via `promote-pr.sh`
- **Target files:** `agents/hapax_daimonion/cluster_c/phase_4_pr_drafter.py` (~250 LOC)
- **Size:** ~350 LOC with tests

### 3.4 C5 — PyMC 5 BEST verification live narrator

**Scope:**
- Depends on LRR Phase 1 PyMC 5 BEST port merged
- Watches for new test runs of `stats.py::best_two_group()` — triggered via inotify on `tests/test_stats_best.py` test output OR a dedicated `~/hapax-state/best-runs/` directory
- On a new BEST run: reads the posterior summary (`diff_mu`, `effect_size`, HDI bounds); composes a 2-3 paragraph narration of "what the model found"
- Narration template: persona-compatible language explaining the statistical result for stream audience
- Composes a governance queue entry for operator review
- **Target files:** `agents/hapax_daimonion/cluster_c/best_verification_narrator.py` (~200 LOC)
- **Size:** ~280 LOC with tests

### 3.5 C6 — Triple-session ritualized cadence

**Scope:**
- Three systemd user timers: morning-session, midday-session, evening-session
- Each timer fires at a fixed time (operator-configurable via `config/ritualized-cadence.yaml`)
- On timer fire: unlocks a director loop activity lock that makes `/voice-session` or similar activities more likely to be selected
- Writes a governance queue entry "ritualized session window open: <name>"
- At the end of the session window: writes a closure entry
- **Requires LRR Phase 4 condition_id plumbing** (per epic spec "C6 requires LRR Phase 4 (condition_id plumbing) merged")
- **Target files:**
  - `agents/hapax_daimonion/cluster_c/ritualized_cadence.py` (~150 LOC)
  - `systemd/user/hapax-ritualized-*.timer` (3 new files)
  - `config/ritualized-cadence.yaml` (operator-editable times)
- **Size:** ~200 LOC + 3 systemd units

### 3.6 C7 — OSF pre-registration amendment drafter

**Scope:**
- Watches for condition changes (via research-marker.json mtime) that would require an OSF pre-reg amendment
- Drafts the amendment text in OSF-compatible format
- Writes to `/dev/shm/hapax-compositor/draft-buffer/osf-amendment-<cond>.partial.md`
- Governance queue entry: "OSF amendment drafted for condition change X → Y; operator review required before submission"
- Operator manually submits the amendment to OSF via their browser (NO auto-submission — constitutional constraint)
- **Target files:** `agents/hapax_daimonion/cluster_c/osf_amendment_drafter.py` (~200 LOC)
- **Size:** ~280 LOC with tests

### 3.7 C8 — 8B pivot scheduled spectator event

**Scope:**
- Watches for the 8B pivot event (condition transition from Qwen3.5-9B to Hermes 3 8B)
- Specifically: when research-marker flips to `cond-phase-a-prime-hermes-8b-002` (or whatever the 5a condition is)
- Composes a specific narration drop: "the 8B pivot has landed; here's what changed, why, what we expect to see in the data"
- References drop #56 v3 + drop #62 §4 option c + drop #62 §13 5b reframing for context
- One-time event; the drafter retires after the first fire
- **Target files:** `agents/hapax_daimonion/cluster_c/pivot_spectator.py` (~150 LOC)
- **Size:** ~200 LOC with tests

### 3.8 C9 — Confound decomposition teach-in

**Scope:**
- Periodic (weekly) narration drop that walks through one confound from the current experimental design
- Candidate confounds: parameter count (8B vs 9B), training objective (SFT vs DPO), system-prompt compliance, context window
- Each teach-in explains: what the confound is, how it could bias the result, what we're doing to isolate it, what we CAN'T isolate with current hardware
- Pedagogical tone; stream content for researchers + general audience
- **Target files:** `agents/hapax_daimonion/cluster_c/confound_teach_in.py` (~200 LOC)
- **Size:** ~280 LOC

### 3.9 C10 — Research drop auto-generation from milestones

**Scope:**
- Milestone events: condition open/close, OSF pre-reg filing, substrate swap, Phase X completion
- For each milestone: compose a research drop summarizing what the milestone means
- Template per milestone type; data from research registry + lrr-state.yaml + hsea-state.yaml
- Writes to governance queue for operator review
- **Target files:** `agents/hapax_daimonion/cluster_c/milestone_drop_generator.py` (~300 LOC)
- **Size:** ~400 LOC with tests

### 3.10 C11 — Publishable result composer (Phase A results drop)

**Scope:**
- Runs when Phase A collection window closes + BEST analysis has run
- Composes a publishable research drop with:
  - Claim statement (from `claim_id` in condition.yaml)
  - Methods summary (drawn from Phase 4 OSF amendment)
  - Data summary (n=N, condition A count, condition A' count, etc.)
  - BEST posterior + HDI + effect size
  - Interpretation paragraph
  - Limitations paragraph (confounds + axiom-latency constraints)
- **5 hard verification gates** before the drop can be promoted:
  1. Attribution audit green (heartbeat.json attribution_tier = "direct")
  2. OSF pre-registration was filed BEFORE data collection started
  3. Frozen-files enforced for all of Phase A (no DEVIATIONs bypassed)
  4. Sample size met the pre-registered target
  5. Analysis code (stats.py BEST) matches the pre-registered version (sha256)
- If any gate fails: drop is blocked; narrator writes a "gate-fail" governance entry instead
- **Target files:** `agents/hapax_daimonion/cluster_c/publishable_result_composer.py` (~400 LOC)
- **Size:** ~550 LOC with tests

### 3.11 C12 — Research integrity heartbeat (per-second refresh)

**Scope:**
- Extends the existing `~/hapax-state/research-integrity/heartbeat.json` writer (if one exists; create if not)
- Heartbeat schema: `{written_at, attribution_tier, active_condition_id, deviation_count, frozen_file_hashes_match, last_reaction_ts}`
- Refresh rate: every 1 second (systemd timer or a persistent daemon)
- HSEA Phase 1 deliverable 1.2 research state broadcaster reads this file
- **Target files:**
  - `agents/hapax_daimonion/cluster_c/heartbeat_writer.py` (~150 LOC)
  - `systemd/user/hapax-research-integrity-heartbeat.service` (persistent daemon)
- **Size:** ~200 LOC with tests

---

## 4. Phase-specific decisions since epic authored

1. **All C-cluster drafters are narration-only per drop #62 §10 Q3 ratification (2026-04-15T05:35Z).** Phase 3 does NOT ship code-drafting agents; it ships narrators that compose research drops and governance-queue entries. The distinction matters: narrators compose `ComposeDropActivity` from HSEA Phase 2 deliverable 3.6; they do not invoke `promote-patch.sh`.

2. **C4 reads beta worktree but does NOT write to it.** The beta-phase-4-bootstrap branch is beta's worktree (or alpha's depending on which session is on it at phase open time). C4 uses subprocess `git log` + `git diff` on the branch without checking it out. Write authority stays with the owning session.

3. **C6 triple-session cadence requires LRR Phase 4 condition_id plumbing.** Drop #62 §3 row 5 confirms condition_id is LRR Phase 1 scope; LRR Phase 4 is where the cadence gating goes live (per the "C6 requires LRR Phase 4" note in the epic spec).

4. **C11 5 hard gates are load-bearing for publication integrity.** If any gate fails, the drop is BLOCKED from promotion — not just warned about. This is stricter than normal governance queue review because a publishable result is a scientific commitment.

5. **C12 heartbeat writer MAY already exist.** Phase 3 opener investigates at open time: if a heartbeat writer exists, C12 extends it; if not, C12 creates it fresh. Same interface either way.

6. **All drop #62 §10 open questions closed.**

---

## 5. Exit criteria

Phase 3 closes when:

1. All 11 C-cluster drafters registered as director loop activities (via HSEA Phase 2 deliverable 3.1 taxonomy extension — NOT expanding beyond 13 ACTIVITY_CAPABILITIES; each C-drafter composes existing `compose_drop`)
2. C2 voice session spectator fires on a real voice session start
3. C3 attribution audit narrator timer running; catches at least one simulated tier change
4. C4 PR drafter reads beta worktree, drafts PR body without errors
5. C5 BEST verification narrator fires on a real test run
6. C6 ritualized cadence timers enabled + first session window opens/closes successfully
7. C7 OSF amendment drafter fires on a condition transition
8. C8 pivot spectator ready to fire (one-shot; can't be verified until actual 8B pivot occurs — ship as conditional)
9. C9 confound teach-in weekly timer running
10. C10 milestone drop generator fires on at least one milestone event
11. C11 publishable result composer passes all 5 hard gates on a test fixture + blocks on gate failure
12. C12 heartbeat writer emits per-second + HSEA Phase 1 1.2 broadcaster consumes without errors
13. `hsea-state.yaml::phase_statuses[3].status == closed`
14. Handoff doc written

---

## 6. Risks + mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| HSEA Phase 2 (UP-10) not ready when Phase 3 opens | Phase 3 cannot compose ComposeDropActivity | Phase 3 onboarding verifies UP-10 closed; block if not |
| C4 reading beta worktree races with beta's writes | Partial read, stale diff | Read via `git log <branch>` (commit-level, not working-tree); no race with uncommitted changes |
| C7 OSF amendment text format divergence from OSF requirements | Operator has to reformat manually | Phase 3 opener tests against OSF's amendment submission format; may require iteration |
| C11 hard gates fail on real Phase A results | Drop blocked indefinitely | Gate failures surface via governance queue entry; operator investigates + corrects underlying issue |
| C6 ritualized timers conflict with operator's schedule | Timers fire during sleep/focus | Timers are operator-configurable via `config/ritualized-cadence.yaml`; operator adjusts |
| C12 heartbeat daemon consumes CPU at 1Hz refresh | System load increase | Heartbeat writer is trivial (~10 LOC of state read + JSON write); negligible load |
| C-cluster drafters collide on governance queue | Queue fills with C-cluster noise | Spawn budget caps per-C-drafter touch point (each C-drafter has its own budget entry); operator tunes |

---

## 7. Open questions

All drop #62 §10 resolved. Phase-3-specific:

1. **Spawn budget allocations per C-drafter.** Default: ~$0.05/day per drafter (adjustable by operator).
2. **C6 ritualized cadence default times.** Default: 09:00 / 13:00 / 20:00 local time. Operator adjusts.
3. **C9 confound teach-in schedule.** Weekly at a fixed day/time vs event-driven. Default: weekly Sunday 10:00.
4. **C11 5-gate definitions may need tightening** once real Phase A results arrive. Gate criteria are the spec; the exact thresholds (e.g., "sample size met target" — by what margin?) can be tuned.

---

## 8. Companion plan doc

`docs/superpowers/plans/2026-04-15-hsea-phase-3-research-program-orchestration-plan.md`.

Execution order:
1. C12 heartbeat writer (foundational; HSEA Phase 1 1.2 consumer)
2. C2 voice session spectator (simplest drafter)
3. C3 attribution audit narrator (extends C12)
4. C10 milestone drop generator (parallel track, covers multiple events)
5. C8 pivot spectator (one-shot, simple)
6. C4 PR drafter (beta worktree reader, moderate complexity)
7. C5 BEST verification narrator (depends on LRR Phase 1 BEST)
8. C6 ritualized cadence (depends on LRR Phase 4)
9. C7 OSF amendment drafter
10. C9 confound teach-in (weekly cadence; low urgency)
11. C11 publishable result composer (shipped LAST; depends on Phase A results)

---

## 9. End

Pre-staging spec for HSEA Phase 3 Research Program Orchestration (Cluster C). Extracts from HSEA epic spec §5 Phase 3 + drop #58 §3 Cluster C framing. All 11 deliverables are narration-only per drop #62 Q3 ratification; compose `ComposeDropActivity` from HSEA Phase 2 deliverable 3.6.

Pre-staging authored by delta as coordinator-plus-extractor. Eighth extraction in delta's pre-staging queue this session. Companion plan to follow.

— delta, 2026-04-15
