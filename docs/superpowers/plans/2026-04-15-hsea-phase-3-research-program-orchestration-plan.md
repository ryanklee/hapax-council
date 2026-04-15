# HSEA Phase 3 — Research Program Orchestration (Cluster C) — Plan

**Date:** 2026-04-15
**Author:** delta (pre-staging extraction; HSEA execution remains alpha/beta workstream)
**Status:** DRAFT pre-staging — awaiting operator sign-off + all upstream UPs closed before Phase 3 open
**Spec reference:** `docs/superpowers/specs/2026-04-15-hsea-phase-3-research-program-orchestration-design.md`
**Branch target:** `feat/hsea-phase-3-research-program-orchestration`
**Unified phase mapping:** UP-11 (HSEA Phase 3 portion, co-ships with LRR Phase 8/9)

---

## 0. Preconditions

- [ ] LRR UP-0/UP-1 closed
- [ ] LRR UP-3 (Phase 2 archive) closed
- [ ] LRR UP-9 (Phase 7 persona) closed
- [ ] HSEA UP-2 (Phase 0) closed
- [ ] HSEA UP-4 (Phase 1) closed
- [ ] HSEA UP-10 (Phase 2 activities) closed — `ComposeDropActivity` public API available
- [ ] LRR Phase 4 (UP-6) closed for C6 condition_id plumbing (partial preconditions OK if non-C6 deliverables ship first)
- [ ] Session claims phase: `hsea-state.yaml::phase_statuses[3].status: open`

---

## Execution order + per-deliverable skeleton

All C-cluster drafters follow the same TDD shape:
1. Create `tests/hapax_daimonion/cluster_c/test_<drafter>.py` with fixtures for the trigger event + expected governance queue entry + expected drop content
2. Create `agents/hapax_daimonion/cluster_c/<drafter>.py` composing `ComposeDropActivity` from HSEA Phase 2 3.6
3. Spawn budget entry for the drafter's touch point
4. systemd unit OR director activity registration (depending on whether it's timer-driven or event-driven)
5. Lint + format + pyright + commit
6. Update `hsea-state.yaml::phase_statuses[3].deliverables[<C-id>].status: completed`

### 1. C12 heartbeat writer (foundational)

- [ ] Tests: trigger-driven 1Hz write + schema validation + stale detection
- [ ] `agents/hapax_daimonion/cluster_c/heartbeat_writer.py` (~150 LOC)
- [ ] `systemd/user/hapax-research-integrity-heartbeat.service` (persistent daemon, not timer)
- [ ] Commit: `feat(hsea-phase-3): C12 research integrity heartbeat 1Hz writer`

### 2. C2 voice session spectator

- [ ] Tests: mock `/dev/shm/hapax-voice/session-active.flag`; assert governance entry + session drop
- [ ] `agents/hapax_daimonion/cluster_c/voice_session_spectator.py` (~150 LOC)
- [ ] Commit: `feat(hsea-phase-3): C2 voice grounding session spectator narrator`

### 3. C3 attribution audit narrator

- [ ] Tests: mock heartbeat.json tier transitions; assert narration drop on each transition
- [ ] `agents/hapax_daimonion/cluster_c/attribution_audit_narrator.py` (~180 LOC)
- [ ] `systemd/user/hapax-attribution-audit-narrator.timer` (every 10 min)
- [ ] Commit: `feat(hsea-phase-3): C3 attribution audit narration daemon`

### 4. C10 milestone drop generator

- [ ] Tests: seed multiple milestone events (condition open, pre-reg, Phase X close); assert one drop per milestone
- [ ] `agents/hapax_daimonion/cluster_c/milestone_drop_generator.py` (~300 LOC)
- [ ] Registered as director loop activity `milestone_drop` composing `ComposeDropActivity`
- [ ] Commit: `feat(hsea-phase-3): C10 milestone drop auto-generation`

### 5. C8 8B pivot spectator

- [ ] Tests: fixture condition transition to 5a condition_id; assert one-shot fire + self-retirement
- [ ] `agents/hapax_daimonion/cluster_c/pivot_spectator.py` (~150 LOC)
- [ ] Commit: `feat(hsea-phase-3): C8 8B pivot scheduled spectator event`

### 6. C4 Phase 4 PR drafter

- [ ] Tests: fixture beta worktree branch with 3 commits; assert PR body draft contains all 3 + rationale
- [ ] `agents/hapax_daimonion/cluster_c/phase_4_pr_drafter.py` (~250 LOC)
- [ ] Read-only git subprocess calls (no checkout, no write)
- [ ] Commit: `feat(hsea-phase-3): C4 Phase 4 PR drafting from beta worktree`

### 7. C5 PyMC 5 BEST verification narrator

- [ ] Tests: fixture BEST run output; assert narration drop with posterior + HDI + effect size
- [ ] `agents/hapax_daimonion/cluster_c/best_verification_narrator.py` (~200 LOC)
- [ ] Commit: `feat(hsea-phase-3): C5 PyMC 5 BEST live verification narrator`

### 8. C6 triple-session ritualized cadence

- [ ] Tests: timer fires → governance entry → activity unlock → session close → closure entry
- [ ] `agents/hapax_daimonion/cluster_c/ritualized_cadence.py` (~150 LOC)
- [ ] `systemd/user/hapax-ritualized-morning.timer`, `-midday.timer`, `-evening.timer` (3 files)
- [ ] `config/ritualized-cadence.yaml` (operator-editable schedule)
- [ ] Commit: `feat(hsea-phase-3): C6 triple-session ritualized cadence + timers`

### 9. C7 OSF pre-registration amendment drafter

- [ ] Tests: fixture condition change → draft amendment → governance entry (no auto-submit)
- [ ] `agents/hapax_daimonion/cluster_c/osf_amendment_drafter.py` (~200 LOC)
- [ ] Commit: `feat(hsea-phase-3): C7 OSF pre-registration amendment drafter`

### 10. C9 confound decomposition teach-in

- [ ] Tests: weekly timer fires → confound narration drop
- [ ] `agents/hapax_daimonion/cluster_c/confound_teach_in.py` (~200 LOC)
- [ ] `systemd/user/hapax-confound-teach-in.timer` (weekly Sunday 10:00 default)
- [ ] Commit: `feat(hsea-phase-3): C9 confound decomposition teach-in weekly narrator`

### 11. C11 publishable result composer (SHIP LAST)

- [ ] Tests: 5 hard gates — (1) attribution green, (2) OSF pre-reg filed before collection, (3) no frozen-file DEVIATIONs bypassed, (4) sample size met, (5) stats.py sha256 matches pre-reg
- [ ] `agents/hapax_daimonion/cluster_c/publishable_result_composer.py` (~400 LOC)
- [ ] Each gate is a separate function + separate test case
- [ ] Gate failure → governance queue entry "gate X failed: <reason>"; drop NOT written to draft-buffer
- [ ] Gates pass → full result drop composed + governance queue entry for operator review
- [ ] Commit: `feat(hsea-phase-3): C11 publishable result composer + 5 hard verification gates`

---

## Phase 3 close

### Smoke tests

- [ ] All 11 C-drafters register as director loop activities (or timer-driven units)
- [ ] C12 heartbeat consumed by HSEA Phase 1 1.2 broadcaster without errors
- [ ] C2 fires on a real voice session (if one occurs during phase)
- [ ] C3 catches a simulated tier transition
- [ ] C4 drafts a PR body from a beta worktree fixture
- [ ] C10 fires on at least one milestone
- [ ] C11 passes fixture gates + blocks on gate failure

### Handoff doc

- [ ] `docs/superpowers/handoff/2026-04-15-hsea-phase-3-complete.md`

### State close-out

- [ ] `hsea-state.yaml::phase_statuses[3].status: closed` + `closed_at` + `handoff_path`
- [ ] `deliverables[C2..C12].status: completed` (all 11)
- [ ] `last_completed_phase: 3`
- [ ] Request operator update to `unified_sequence[UP-11].status: closed` (co-shipped with LRR Phase 8/9)

### Inflection

- [ ] Write inflection announcing Phase 3 closure + HSEA Phase 4/5/6/... UP-12 parallel cluster basket openable

---

## Cross-epic coordination

- All 11 C-drafters compose `ComposeDropActivity` from HSEA Phase 2 3.6
- C4 reads beta worktree read-only (no writes)
- C6 requires LRR Phase 4 condition_id plumbing live
- C11 requires LRR Phase 4 complete + Phase A results + stats.py BEST run
- C12 heartbeat is HSEA Phase 1 1.2 research state broadcaster's data source

---

## End

Compact per-phase plan for HSEA Phase 3 Cluster C. Pre-staging. Eighth extraction in delta's pre-staging queue this session. Execution remains alpha/beta workstream.

— delta, 2026-04-15
