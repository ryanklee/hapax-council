# HAPAX SELF-EXECUTING AGENT (HSEA) — Epic Execution Plan

> **For agentic workers:** This is a multi-phase epic spanning weeks. Each phase produces one or more PRs. The `superpowers:subagent-driven-development` or `superpowers:executing-plans` skills apply at the per-phase level, NOT at the epic level — open one phase at a time, write its design spec + plan, execute it, merge it, then move to the next.

**Goal:** Arrive at the end-state where Hapax visibly executes its own tactical roadmap (drop #57) as livestream content under constitutional governance, with the operator as approval gate for every consequential artifact.

**Epic design:** `docs/superpowers/specs/2026-04-14-hsea-epic-design.md` (authoritative; this plan is the execution companion)

**Precedent research:**
- `docs/research/2026-04-14-hapax-self-executes-tactics-as-content.md` (drop #58 thesis)
- `docs/research/2026-04-14-drop-58-audit-critical-evaluation.md` (drop #59 audit)
- `docs/research/2026-04-14-tactics-and-strategies-to-increase-success-probabilities.md` (drop #57 tactics)

**Duration estimate:** 22-35 sessions across 4-8 weeks

**Session roles:** alpha drives primary execution end-to-end. Beta is available for parallel work on Phases 5-9 (which have no mutual dependencies beyond 0/1/2). Delta is research-only — no code-writing per subagent git safety rules.

---

## 1. Execution model

This epic is too large for one session. It is structured for incremental pickup. Each session picks up **exactly one phase** at a time — no phase skipping, no inter-phase parallelism except where explicitly noted below.

**Invariants across all phases:**

- **One active phase at a time per session.** `~/.cache/hapax/relay/hsea-state.yaml::current_phase` holds the primary phase pointer. Sessions picking up HSEA work check this file first.
- **Phase N opens only after Phase N-1 is closed** (exit criteria met, PR merged, handoff written). Exceptions: Phases 5-9 parallelize across worktrees after Phase 2 closes.
- **Each phase is its own branch + PR.** Branch name: `feat/hsea-phase-N-<slug>`. Multi-PR phases use suffixed branches: `feat/hsea-phase-N-<slug>-<deliverable>`.
- **Every phase writes a handoff doc** at `docs/superpowers/handoff/YYYY-MM-DD-hsea-phase-N-complete.md` on close.
- **Frozen files are enforced.** Pre-commit hook blocks any change to the active research condition's `frozen_files` manifest. Cluster I (Phase 4) patches to frozen files require a DEVIATION document drafted inline.
- **Spawn budget is enforced.** Phase 0 ships the ledger; every subsequent phase routes LLM calls through `check_can_spawn()` before dispatching.
- **Governance queue is append-only** — never delete entries, only archive.
- **Drafting never auto-commits** — every consequential artifact routes through operator-invoked `promote-*.sh`.

---

## 2. Phase pickup procedure

Every session that picks up an HSEA phase follows this sequence:

```
STEP 1: Onboard (standard alpha/beta relay session start)
  - Read ~/.cache/hapax/relay/onboarding-{role}.md
  - Read ~/.cache/hapax/relay/PROTOCOL.md
  - Read peer status (alpha.yaml / beta.yaml)
  - Check for new inflections

STEP 2: HSEA state check
  - Read ~/.cache/hapax/relay/hsea-state.yaml
  - Note current_phase, last_completed_phase, known_blockers, overall_health
  - If current_phase has an open PR: either continue that work OR wait
  - If no current_phase: next available phase per dependency graph
  - If overall_health != green: triage blockers first

STEP 3: Check LRR state (cross-epic dependencies)
  - Read ~/.cache/hapax/relay/lrr-state.yaml
  - HSEA Phase 3 depends on LRR Phase 4 (condition_id plumbing)
  - HSEA Phase 4 I1 depends on LRR Phase 1 (PyMC 5 BEST port) if using that drafter

STEP 4: Read the epic design
  - docs/superpowers/specs/2026-04-14-hsea-epic-design.md
  - Skip to the phase you're opening; read the whole section
  - Read the prior phase's handoff doc for context

STEP 5: Write the per-phase spec + plan
  - docs/superpowers/specs/YYYY-MM-DD-hsea-phase-N-<slug>-design.md
    - Extract the scope from the epic design's Phase N section
    - Add any phase-specific decisions made since the epic was authored
    - Include exit criteria from the epic (verbatim or updated)
    - Consult the per-cluster design research (Phase 0 / Cluster H / Cluster I designs in agent outputs)
  - docs/superpowers/plans/YYYY-MM-DD-hsea-phase-N-<slug>-plan.md
    - TDD/checkbox task breakdown
    - Per-deliverable LOC estimate
    - Per-deliverable test coverage target
    - Dependencies + gates

STEP 6: Create branch + open phase
  - git checkout -b feat/hsea-phase-N-<slug>
  - Update hsea-state.yaml: set current_phase, opened_at, current_phase_owner, current_phase_branch
  - Commit the spec + plan as the phase's first commit
  - Begin TDD execution of deliverables

STEP 7: Execute
  - Follow the per-phase plan doc strictly
  - Write tests first where applicable
  - Respect frozen-files universally
  - Respect spawn budget (ledger is live after Phase 0)
  - Respect governance queue for any artifact that becomes operator-facing

STEP 8: Close phase
  - All deliverables merged to main (not just branch)
  - All tests passing
  - Exit criteria from the epic doc verified
  - Write handoff doc at docs/superpowers/handoff/YYYY-MM-DD-hsea-phase-N-complete.md
  - Update hsea-state.yaml: set phase_statuses[N].status to closed, update last_completed_phase, clear current_phase fields
  - Push convergence line to ~/.cache/hapax/relay/convergence.log
```

---

## 3. Phase dependency graph

```
Phase 0 (Foundation) ─┬─> Phase 1 (Visibility) ─┬─> Phase 2 (Core Activities) ─┬─> Phase 3 (Research Orch)
                      │                          │                              ├─> Phase 4 (Code Drafting) [also LRR Phase 1]
                      │                          │                              ├─> Phase 5 (Biometric Triad)
                      │                          │                              ├─> Phase 6 (Content Quality)
                      │                          │                              ├─> Phase 7 (Self-Monitoring)
                      │                          │                              ├─> Phase 8 (Platform Value)
                      │                          │                              └─> Phase 9 (Revenue)
                      │                          │                                            │
                      │                          │                                            │
                      └─> Phase 10 (Reflexive) ←──┴──────────(after 6 + 8)─────────────────────┘
                                  │
                                  v
                            Phase 11 (Spawner) [requires 3]
                                  │
                                  v
                            Phase 12 (Long-tail + Handoff)
```

**Parallelizable (after Phase 2 closes):** Phases 3, 4, 5, 6, 7, 8, 9 — no mutual dependencies. Can run across alpha + beta worktrees subject to branch discipline (one active branch per session).

**Sequential:** Phase 0 → Phase 1 → Phase 2 → {3-9 parallel} → Phase 10 (depends on 6 + 8) → Phase 11 (depends on 3) → Phase 12.

---

## 4. Per-phase execution briefs

### Phase 0 — Foundation Primitives

**Branch:** `feat/hsea-phase-0-foundation-primitives`
**Duration:** 3-4 sessions
**Parallelism:** Single session, sequential deliverables
**Critical path:** ship 0.6 first (state file), then 0.1 + 0.3 in parallel, then 0.2 (depends on 0.1), then 0.4 (depends on 0.2), then 0.5 (last, depends on 0.4)
**Spec doc:** `docs/superpowers/specs/2026-04-14-hsea-phase-0-foundation-primitives-design.md` (write at phase open, copying from epic design §5 Phase 0)
**Plan doc:** `docs/superpowers/plans/2026-04-14-hsea-phase-0-plan.md`
**Exit criteria:** all 6 deliverables merged, end-to-end smoke test passes, handoff written

### Phase 1 — Visibility Surfaces

**Branch:** `feat/hsea-phase-1-visibility-surfaces`
**Duration:** 2-3 sessions
**Ordering within phase:** 1.1 HUD → 1.2 Research state → 1.3 Glass-box prompt → 1.4 Orchestration strip → 1.5 Governance queue overlay
**Exit criteria:** all 5 Cairo sources rendering in production compositor; golden-image regression tests

### Phase 2 — Core Director Activities

**Branch:** `feat/hsea-phase-2-core-director-activities`
**Duration:** 3 sessions
**Ordering:** 2.8 taxonomy first, then individual activities in any order
**Critical:** 2.7 `ReflectiveMomentScorer` ships with calibration period (7 days metric capture before enabling the gate)
**Exit criteria:** director loop alternates between old + new activities; ReflectiveMomentScorer calibrated

### Phase 3 — Research Program Orchestration

**Branch:** `feat/hsea-phase-3-research-orchestration`
**Duration:** 4 sessions
**LRR coupling:** C5 waits for LRR Phase 1; C6 waits for LRR Phase 4; C11 waits for LRR Phase 4 complete + green integrity
**Exit criteria:** one voice grounding session orchestrated end-to-end via C2; attribution audit catches simulated fault; first auto-generated drop via C10

### Phase 4 — Code Drafting Cluster (NEW)

**Branch:** `feat/hsea-phase-4-code-drafting`
**Duration:** 5 sessions (largest phase)
**Ordering:** 4.1 base agent → 4.2 staging → 4.3 per-task drafters (I2, I3, I4a/b/c, I5, I6, I7 first; I1 waits for LRR Phase 1) → 4.4 promote/reject scripts → 4.5 director `patch` activity → 4.6 code_review integration
**Capable alias task:** add `capable → claude-opus-4-6` to `shared/config.py` + `agents/_config.py` as first action
**Frozen-files probe task:** add `--probe` mode to `scripts/check-frozen-files.py` as a separate PR before drafter deliverables can depend on it
**Opus rate limit:** hard cap ≤3/day enforced at drafter + budget ledger
**Exit criteria:** all 7 drafters produce valid CodePatch outputs; ≥2 patches complete draft→review→approve→promote cycle; capable alias + probe mode merged

### Phase 5 — Biometric + Studio + Archival Triad (NEW)

**Branch:** `feat/hsea-phase-5-biometric-studio-archival`
**Duration:** 4-5 sessions
**Critical constraint:** M1 biometric intervention MUST route through operator-private only — never on stream. Test case: simulate HRV drop, verify impingement is private.
**Ordering:** M5 Reverie write channel (foundational, enables M16 + M20) → M1 biometric intervention → M2 retrieval-augmented memory → M3 studio creative state → M4 drift detector → supporting M-series
**Exit criteria:** M1 triggers on simulated HRV drop; M2 retrieval works against real voice query; M3 runs full session without consent violation; M4 produces ≥1 drift detection; M5 wired to ≥3 event types

### Phase 6 — Content Quality + Clip Mining

**Branch:** `feat/hsea-phase-6-content-quality`
**Duration:** 3 sessions
**Exit criteria:** clipability scorer running; exemplar auto-curation weekly ceremony executes; anti-pattern detection flags real violations

### Phase 7 — Self-Monitoring + Catastrophic Tail

**Branch:** `feat/hsea-phase-7-self-monitoring`
**Duration:** 3-4 sessions
**Critical:** D3 recurring-pattern fix proposer depends on Phase 4's drafter infrastructure existing
**Exit criteria:** anomaly narration fires on real metric trip; one postmortem auto-drafted; DMCA pre-check blocks a fixture known-risky track

### Phase 8 — Platform Value Curation

**Branch:** `feat/hsea-phase-8-platform-value`
**Duration:** 3 sessions
**Exit criteria:** live RESEARCH.md regenerates on file changes; morning briefing ritual fires; weekly retrospective executes once

### Phase 9 — Revenue Preparation (NEW)

**Branch:** `feat/hsea-phase-9-revenue-preparation`
**Duration:** 3 sessions
**Critical constraint:** H3 consulting channel gate MUST NOT unlock Phase 2 artifacts until `~/hapax-state/revenue/consulting-gate.json::phase_1_acknowledged: true` is set by operator
**Ordering:** H1 sponsor copy + H2 NLnet grant + H5 music tracker in parallel → H3 consulting (gated) → H4 deadline tracker → H6 overlay → H7 reconciliation → H8 axiom gate extension
**Exit criteria:** sponsor copy with all constitutional constraints validated; NLnet draft with ≥3 provenance-backed milestones; consulting Phase 1 draft produced with Phase 2 locked; deadline tracker fetching real cycle data; revenue reconciliation accessible

### Phase 10 — Reflexive Stack

**Branch:** `feat/hsea-phase-10-reflexive-stack`
**Duration:** 2-3 sessions
**Critical:** F10 meta-reflexive override must ship with or before F2. Drop #59 audit identified F10-after-F2 ordering as an anti-pattern.
**Exit criteria:** F3 scorer calibration data shows ~1-in-20 frequency; F14 meta-meta-reflexivity rate-limited to ≤3/stream; all layers F2-F14 schema-validated

### Phase 11 — Multi-Agent Spawner

**Branch:** `feat/hsea-phase-11-spawner`
**Duration:** 4 sessions
**Budget critical:** G2 weekly self-analysis ritual is the largest recurring spawn; verify $0.80/week cap is enforced
**Exit criteria:** G1 affordance registered and recruited; G2 ritual produces structured output; G13 emergency analyst fires on simulated Tier-1 incident

### Phase 12 — Long-tail Integration + Handoff

**Branch:** `feat/hsea-phase-12-longtail-handoff`
**Duration:** 3-4 sessions
**Exit criteria:** `hsea-state.yaml::overall_health == green` for ≥7 days; all 140 touch points either shipped or deferred with rationale; epic handoff doc written; operator formally closes the epic

---

## 5. Handoff document convention

Every phase close writes a handoff doc with this structure:

```markdown
# HSEA Phase N — <slug> — handoff

**Date:** YYYY-MM-DD
**Owner:** <session-id>
**Phase status:** closed
**PR URLs:** [list]
**Branch:** feat/hsea-phase-N-<slug>

## What shipped

- Deliverable 1: <description>
- Deliverable 2: <description>
- ...

## Total LOC shipped

<count> across <n> files, <m> tests added

## Exit criteria verification

- [x] Criterion 1 verified by <evidence>
- [x] Criterion 2 verified by <evidence>
- ...

## Known deferrals

- <item>: deferred to <phase or follow-up> because <reason>

## Observations for next phase

- <observation>
- <observation>

## Open questions for operator

- <question>
- <question>

## Blockers encountered + resolutions

- Blocker: <description>
- Resolution: <description>
```

---

## 6. Branch discipline for parallel phases (5-9)

When Phases 5-9 run in parallel across alpha + beta worktrees:

- **Worktree allocation:** alpha primary worktree for one phase; beta worktree for a different phase; spontaneous worktrees not used (max 4 worktrees total per hook policy)
- **Branch names distinct:** `feat/hsea-phase-5-biometric-triad` vs `feat/hsea-phase-9-revenue-preparation`
- **No cross-phase imports during parallel work:** if Phase 5 needs something from Phase 9, wait until Phase 9 merges
- **`hsea-state.yaml` is shared state:** both sessions write to the same file; use atomic tmp+rename; prefer appending notes over overwriting fields
- **Rebase alpha after beta merges** per workspace CLAUDE.md convention

---

## 7. Resumption protocol for interrupted phases

If a phase is opened but not closed before a session ends (or a long pause):

1. `hsea-state.yaml::phase_statuses[N].status: open` remains
2. Next session picks up the same phase
3. Reads the per-phase plan doc for the checkbox state
4. Reads the per-phase spec doc for the scope
5. Checks the branch for committed work
6. Resumes from the first unchecked task in the plan

No phase abandonment. If a phase genuinely cannot ship, write an abandonment handoff explaining why + recommended alternative, and update `hsea-state.yaml::phase_statuses[N].status: deferred`.

---

## 8. Cross-epic coordination

**LRR + HSEA interplay:**
- HSEA Phase 3 C5 waits for LRR Phase 1 (PyMC 5 BEST port) — Cluster I's I1 drafter can ship LRR Phase 1 itself, closing the dependency
- HSEA Phase 3 C6 + C11 wait for LRR Phase 4 (condition_id plumbing) — LRR Phase 4 is in beta's worktree
- HSEA Phase 7 D3 recurring-fix proposer may produce fixes for LRR-instrumented code; those must respect LRR frozen-files

**Session coordination:**
- If LRR and HSEA have conflicting phase-opens (e.g., both want alpha's main worktree), LRR takes precedence (LRR is the research harness; HSEA is visibility layer)
- Beta can open HSEA phases while alpha is on LRR work
- Relay inflections at each phase close ensure both epics see each other's state

---

## 9. Epic close protocol

When all 13 phases are closed:

1. Run a final audit pass comparing actual file state to epic design §7 exit criteria
2. Verify <10% file-reference error rate (vs drop #58's ~55%)
3. Write the final epic close handoff at `docs/superpowers/handoff/YYYY-MM-DD-hsea-complete.md`
4. Archive `hsea-state.yaml` to `~/.cache/hapax/relay/archive/hsea-state-YYYY-MM-DD.yaml`
5. Update `docs/research/CURRENT-STATE.md` (if E1 live RESEARCH.md shipped) with HSEA-complete status
6. Optionally write a meta-drop (#??) summarizing total LOC, touch points deployed, posterior shifts observed in practice, operator sustainability outcomes

---

## 10. Failure modes + recovery

**Phase 0 primitives take too long:** ship Phase 0 in partial mode — 0.1 + 0.3 + 0.6 first, then 0.2 + 0.4 + 0.5 as follow-up. Phase 1 can start on the partial primitives.

**Compositor failure blocks all visibility:** treat as a pre-Phase-0 blocker. Restore compositor first (depends on FDL-1 deployed state). Do not open HSEA phases against a failed compositor.

**Operator review fatigue:** reduce daily drafter activity via budget ledger. Ship Phase 5 M1 biometric intervention earlier if operator is showing signs of fatigue. Pause new phase opens until stabilized.

**Cluster I patch breaks production:** rollback via `git revert`, draft a fix patch via the same drafter, iterate. `promote-patch.sh` should have a rollback helper generated per patch.

**Revenue tactic violates constraint silently:** H8 axiom gate extension should catch this at commit time. If violation is observed in already-shipped code, file an incident drop and patch via Cluster I.

**Research integrity drifts during HSEA:** Phase 3 C3 attribution audit narration catches this. If drift is real, pause HSEA and return to LRR to fix.

---

## 11. Resource budget

**Time:** 22-35 sessions across 4-8 weeks, time-gated by Phase 5 M1 biometric data capture + Phase 2 scorer calibration

**LLM spend:**
- Phase 0: ~$0 (no LLM calls, just infrastructure)
- Phases 1-12 total: estimated $60-250/month during active execution (per drop #59 corrected estimate)
- Weekly self-analysis ritual (G2): $3-10/month
- Code drafter (Opus-tier I1, I4 escalations): $15-30/month
- All other clusters: $40-200/month combined

**LOC:** ~29,000 total across all phases

**Operator approval rate:** ~5-15 inbox items/day at steady state; peak 20-30 during Phase 4 code-drafting weeks

---

## 12. End

This plan is the execution companion to the HSEA epic design. Each phase picks up from here, follows the pickup procedure in §2, writes its own per-phase spec + plan, executes, closes, and hands off to the next.

The epic is large but decomposable. Phase 0 alone is valuable — the primitives it ships improve observability and governance even if no subsequent phase opens. Phases 1-4 deliver the core value (visibility + activities + research orchestration + code drafting). Phases 5-12 compound on that base.

**First session action:** open Phase 0 per §4 Phase 0 brief above.

— delta
