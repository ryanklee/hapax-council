# HSEA Phase 12 — Long-tail Integration + Handoff — Design Spec

**Date:** 2026-04-15
**Author:** delta (pre-staging extraction)
**Status:** DRAFT pre-staging — ships at epic close, UP-13 terminal
**Epic reference:** `docs/superpowers/specs/2026-04-14-hsea-epic-design.md` §5 Phase 12
**Plan reference:** `docs/superpowers/plans/2026-04-15-hsea-phase-12-long-tail-handoff-plan.md`
**Branch target:** `feat/hsea-phase-12-long-tail-handoff`
**Cross-epic authority:** drop #62 §5 UP-13 (epic close)
**Unified phase mapping:** UP-13 terminal — ~1,000 LOC + substantial handoff documentation

---

## 1. Phase goal

Complete the **remaining touch points** from the de-duplicated ~65-item touch-point inventory that did not fit into Clusters B/C/D/E/F/G/H/I/M. Ship the **session handoff doc drafter** (second-order gap from drop #59). Ship the **CI watch + merge queue triager** (second-order gap from drop #59). Ship the **documentation drift sweeper** (CLAUDE.md + README + spec doc drift detection). Ship the **final epic close handoff** that summarizes the entire HSEA epic's outcomes, open items, and recommended next-epic directions.

**Phase 12 is the epic's terminal phase.** After Phase 12 closes, the HSEA epic is complete + all open items are either resolved or explicitly deferred with rationale.

---

## 2. Dependencies + preconditions

1. **All prior HSEA phases closed** (Phases 0-11)
2. **LRR UP-13 closed** (LRR Phase 10 observability + drills + polish)
3. **Shared index `research-stream-state.yaml` has both epics at `unified_sequence[UP-13].status: open`**
4. **Operator review bandwidth for the final handoff** — Phase 12 produces a long-form close-out that operator reads through before epic is declared "done"

---

## 3. Deliverables

### 3.1 Long-tail touch points inventory

**Scope:** From the de-duplicated ~65-item touch-point inventory (drop #58 + drop #57 tactics), list everything that did NOT land in any Cluster B/C/D/E/F/G/H/I/M phase. These are the "long-tail" items — low individual value but collectively worth shipping for coverage.

**Examples of candidate long-tail touch points** (opener verifies against the actual inventory at phase open):
- Minor Cairo overlays not already shipped in Phase 1 or Phase 8
- Configuration + documentation edits
- Small observability additions
- Test coverage improvements on existing modules
- Deferred items from earlier phases that didn't block close but should ship for completeness

**Target files:** whichever files the long-tail items touch; Phase 12 doesn't have a fixed file list
**Size:** ~300 LOC spread across the long-tail items

### 3.2 Session handoff doc drafter (second-order gap from drop #59)

**Scope:** A director activity + drafter that produces a `docs/superpowers/handoff/YYYY-MM-DD-<session>-handoff.md` file when a session retires. The drafter reads the session's recent commits, open PRs, uncommitted changes, TodoWrite state, outstanding items from closure inflections, then composes a handoff markdown.

**Why this is a gap:** drop #59 audit found that sessions were writing handoff docs inconsistently. Some sessions (alpha at 2026-04-13T19:35Z) retired with thorough handoffs; others ran out of context without one. Automating the handoff via a drafter ensures consistency.

**Target files:**
- `agents/hapax_daimonion/phase_12/session_handoff_drafter.py` (~300 LOC)
- `docs/superpowers/handoff/templates/session-handoff-template.md` (~100 lines template)
- Tests (~200 LOC)

**Size:** ~600 LOC

### 3.3 CI watch + merge queue triager (second-order gap from drop #59)

**Scope:** An agent that watches the PR merge queue + CI state + flags stalled PRs (no merge activity in >24h) + triages by suggesting which PR to merge first. Reads `gh pr list` + CI state from `/dev/shm/hapax-ci-state.json` (LRR Phase 9 item 9).

**Why this is a gap:** drop #59 found that alpha's earlier session had a sprawling open-PR state (12+ PRs at session retirement). Automated triage could have surfaced the sprawl earlier.

**Target files:**
- `agents/hapax_daimonion/phase_12/merge_queue_triager.py` (~250 LOC)
- Systemd timer (hourly)
- Tests (~180 LOC)

**Size:** ~470 LOC

### 3.4 Documentation drift sweeper

**Scope:** Combined with HSEA Phase 8 E6 doc freshness auto-check but broader — sweeps CLAUDE.md files + README files + spec docs for:
- References to deleted files
- References to renamed functions/classes
- Stale commit SHAs
- Stale PR URLs
- Outdated architecture diagrams

Output: a governance queue entry per drift event; operator approves fixes + the sweeper auto-applies approved fixes.

**Target files:**
- `agents/hapax_daimonion/phase_12/doc_drift_sweeper.py` (~350 LOC)
- Systemd timer (weekly)
- Tests (~250 LOC)

**Size:** ~650 LOC

### 3.5 Final epic close handoff

**Scope:** Long-form (~5000 word) closing document at `docs/superpowers/handoff/YYYY-MM-DD-hsea-phase-12-complete.md` (and also `docs/superpowers/handoff/YYYY-MM-DD-hsea-epic-complete.md`). Contents:

- **Total LOC shipped** across all 13 HSEA phases
- **Touch points deployed** (count + list) vs touch points deferred + rationale
- **Open items inherited from drops #57/#58/#59/#60/#61/#62** — fully resolved or flagged for next epic
- **Recommended next-epic directions** — what Hapax's next research epic should focus on, based on HSEA findings
- **Constitutional state** — all axiom precedents landed + new implications
- **Observability state** — per-condition Prometheus slicing, Langfuse state, governance queue volume metrics
- **Research program state** — conditions opened/closed, claims settled, OSF pre-regs filed
- **Substrate state** — current production LLM, post-Hermes landscape resolution
- **Session coordination outcomes** — protocol v1 + v1.5 evaluation, what worked + what didn't

**Target file:** `docs/superpowers/handoff/YYYY-MM-DD-hsea-phase-12-complete.md` (committed at phase close)
**Size:** ~5000 lines markdown (prose-heavy, not code)

---

## 4. Phase-specific decisions

1. **Long-tail inventory is opener-defined** — Phase 12 opener reads the drop #58/#57 inventory + subtracts everything already shipped, lists the residual, picks what to ship
2. **Session handoff drafter is session-agnostic** — works for alpha, beta, delta, epsilon, any future session
3. **Merge queue triager is advisory** — never auto-merges PRs, never auto-closes
4. **Doc drift sweeper is operator-gated** — auto-detects drift, operator approves fixes, sweeper applies
5. **Final epic close is operator-reviewed** — long-form document, operator reads + edits before the close commit lands

---

## 5. Exit criteria

- **`~/.cache/hapax/relay/hsea-state.yaml::overall_health == green`**
- **All 110 touch points either shipped or explicitly deferred with rationale** (from the de-duplicated ~65 base + ~45 stretch items noted across phases)
- **Final handoff doc written** + operator-approved + committed
- **Session handoff drafter operational** — test retirement produces a valid handoff doc
- **CI watch + merge queue triager running** — at least one hourly tick + one triage recommendation surfaced
- **Doc drift sweeper running** — weekly sweep + at least one drift event surfaced
- **All HSEA phase_statuses[0..12] == closed**
- **`research-stream-state.yaml::unified_sequence[UP-13].status == closed`**

---

## 6. Risks + mitigations

| Risk | Mitigation |
|---|---|
| Long-tail inventory too large to ship in reasonable time | Explicit deferral with rationale is acceptable; not everything must ship |
| Final epic close handoff is too long to review | Operator can skim + sign off in sections |
| Session handoff drafter produces generic output | Template-driven with session-specific sections; operator can edit |
| Merge queue triager surfaces noise | Tunable sensitivity; start conservative |
| Doc drift sweeper false-positives on intentional archaisms | Allowlist mechanism in the sweeper |

---

## 7. Open questions

1. How many long-tail items are worth shipping vs deferring? Opener-decided based on bandwidth
2. Final handoff doc length — 5000 words target but operator can request condensed
3. Merge queue triager run cadence (hourly default)
4. Doc drift sweeper cadence (weekly default)

---

## 8. Plan

`docs/superpowers/plans/2026-04-15-hsea-phase-12-long-tail-handoff-plan.md`. Execution order: 3.2 session handoff drafter (useful independently of phase close) → 3.3 merge queue triager → 3.4 doc drift sweeper → 3.1 long-tail sweep → 3.5 final epic close handoff (LAST, operator-reviewed).

---

## 9. End

Pre-staging spec for HSEA Phase 12 Long-tail Integration + Handoff. Terminal phase of the HSEA epic. Completes remaining touch points + ships second-order automation (session handoff, merge queue triage, doc drift sweep) + produces the final epic close handoff.

Seventeenth complete extraction in delta's pre-staging queue this session.

— delta, 2026-04-15
