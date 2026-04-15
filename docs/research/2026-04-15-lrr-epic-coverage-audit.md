# LRR epic coverage audit

**Date:** 2026-04-15
**Author:** alpha (refill 8 item #103)
**Scope:** per-phase audit of LRR epic spec/plan/implementation coverage on `origin/main`. Maps: spec present, plan present, execution work shipped, gaps, deferrals, critical path.
**Authoritative surface:** `origin/main` as of commit `7d77fd5bb`. Branch-only artifacts (`beta-phase-4-bootstrap` etc.) are NOT counted as "on main" even if they exist in git.
**Status:** research drop; ground-truth snapshot for coordinator refill planning.

---

## 1. Coverage matrix

| Phase | Spec on main | Plan on main | Implementation PRs | Status | Branch-only artifacts |
|---|---|---|---|---|---|
| **0** Verification + FINDING-Q spike | ✓ `2026-04-14-lrr-phase-0-verification-design.md` + `-finding-q-spike-notes.md` | ✓ `2026-04-14-lrr-phase-0-verification-plan.md` | PR #794, prior sweep | **CLOSED** | — |
| **1** Research registry | ✓ `2026-04-14` + `2026-04-15-lrr-phase-1-research-registry-design.md` | ✓ `2026-04-14` + `2026-04-15-lrr-phase-1-research-registry-plan.md` | PRs #840-#844 (schema + marker + probe + Qdrant notes) | **CLOSED** (10 items shipped) | — |
| **2** Archive + research instrument | ✓ `2026-04-14` + `2026-04-15-lrr-phase-2-archive-research-instrument-design.md` + retention doc | ✓ `2026-04-14` + `2026-04-15-lrr-phase-2-archive-research-instrument-plan.md` | PRs #849, #850, #851, #853, #854, #856, #857, #859, #860, #864 (item #97 runbook in-flight) | **SUBSTANTIVELY CLOSED** (9 items shipped, item #58 operator-deferred) | — |
| **3** Hardware validation | ✓ `2026-04-14` + `2026-04-15-lrr-phase-3-hardware-validation-design.md` | ✓ `2026-04-14` + `2026-04-15-lrr-phase-3-hardware-validation-plan.md` | PR #848 (PSU stress + fps measurement), prior sweep | **IN-PROGRESS** | — |
| **4** Phase A completion + OSF pre-reg | ✓ `2026-04-15-lrr-phase-4-phase-a-completion-osf-design.md` | ✓ `2026-04-15-lrr-phase-4-phase-a-completion-osf-plan.md` | PRs #845, #846, #847, #852 | **IN-PROGRESS** | — |
| **5** Substrate swap (Hermes 8B parallel) | **MISSING** | **MISSING** | — | **REOPENED post-§14** — substrate TBD per drop #62 §14 Hermes abandonment; beta substrate research v1+v2+errata on branch only | Beta's substrate research drops at commits `bb2fb27ca` + `d33b5860c` + `f2a5b2348` live on `beta-phase-4-bootstrap`; no spec/plan authored yet because substrate is undecided |
| **6** Governance finalization + stream-mode axis | **MISSING** | **MISSING** | — | **PRE-STAGED ON BETA BRANCH** — epsilon authored 869-line spec + 483-line plan at `c945b78f2` on `beta-phase-4-bootstrap`; not cherry-picked to main | 2 files at `docs/superpowers/{specs,plans}/2026-04-15-lrr-phase-6-governance-finalization-{design,plan}.md` on branch only. Has known §0.5 reconciliation drift (D1 Q5 joint PR + D2 70B reactivation guard) flagged in beta's cohabitation drop `cda23c206` |
| **7** Persona spec | ✓ `2026-04-15-lrr-phase-7-persona-spec-design.md` | ✓ `2026-04-15-lrr-phase-7-persona-spec-plan.md` | — | **PENDING SUBSTRATE** — persona authoring blocked on LRR Phase 5 substrate ratification | — |
| **8** Content programming via objectives | ✓ `2026-04-15-lrr-phase-8-content-programming-via-objectives-design.md` | ✓ `2026-04-15-lrr-phase-8-content-programming-via-objectives-plan.md` | — | **NOT STARTED** | — |
| **9** Closed-loop feedback | ✓ `2026-04-14` + `2026-04-15-lrr-phase-9-closed-loop-feedback-design.md` | ✓ `2026-04-14` + `2026-04-15-lrr-phase-9-closed-loop-feedback-plan.md` | — | **NOT STARTED** | — |
| **10** Observability + drills + polish | **MISSING** | **MISSING** | PR #801 (6 commits, pre-session Prometheus/drills work), plus partial hapax-ai exporter (1/6 Pis) | **IN-PROGRESS via branch-only spec** | Beta's extraction at commit `89283a9d1` on `beta-phase-4-bootstrap` holds the authoritative spec + plan; not cherry-picked to main |
| **11** (naming TBD) | **NOT SPEC'D** | **NOT SPEC'D** | — | **NOT DEFINED** — possibly placeholder for LRR epic closure / retrospective phase | — |

## 2. Critical gaps

### 2.1 LRR Phase 5 — substrate TBD (~blocking Phase 7 + indirectly Phases 8-11)

Drop #62 §14 (Hermes abandonment) reopened the substrate question. Beta's substrate research v1/v2/errata (commits `bb2fb27ca`, `d33b5860c`, `f2a5b2348` on `beta-phase-4-bootstrap`) enumerates 5 scenarios:

1. Keep Qwen3.5-9B + fix (lowest disruption) — MEDIUM-HIGH confidence
2. Parallel-deploy OLMo 3-7B (research-aligned) — HIGH confidence
3. Empirical bake-off — HIGH confidence
4. Immediate Llama 3.1 8B swap — LOW-MEDIUM confidence
5. Mistral Small 3.1 24B at 5.0bpw (no-RL principle) — MEDIUM confidence

**Blocker:** operator has not yet selected a scenario. Phase 5 authoring is blocked until a scenario is ratified; each scenario would produce a different spec.

**Unblocks when:** operator ratifies (a) keep vs swap direction, (b) RIFTS dataset download authorization, (c) OLMo 3-7B weight download authorization. Beta's v2 synthesis doc enumerates the full operator decision surface.

### 2.2 LRR Phase 6 — pre-staged on branch, not on main

Epsilon's pre-staging (869-line spec + 483-line plan) lives only on `beta-phase-4-bootstrap`. A Phase 6 opener session would normally find it by cross-referencing drop #62; a casual main-reader would not.

**Known drift:** §0.5 reconciliation block pending per beta's `cda23c206` research drop (Q5 joint PR framing + 70B reactivation guard rule). Should be applied before the joint `hapax-constitution` PR opens.

**Unblocks when:** Phase 5 closes (substrate decided) + Phase 6 opener applies the §0.5 block. Non-urgent because Phase 6 depends on Phase 5.

### 2.3 LRR Phase 10 — spec/plan on branch, partial implementation on main

PR #801 shipped 6 commits of Phase 10 observability work pre-session. Epsilon's hapax-ai provisioning added 1/6 Prometheus exporters (`hapax-ai:9100`). Beta's extraction at `89283a9d1` authored the full spec + plan but only on `beta-phase-4-bootstrap`.

**Gap:** no on-main spec means a future execution session has to read the branch-only spec OR re-derive from epic text.

**Unblocks when:** either (a) beta-phase-4-bootstrap merges (PR #819), or (b) a cherry-pick PR ships the Phase 10 spec/plan to main independently.

### 2.4 LRR Phase 11 — not yet defined

No spec, no plan, no naming yet. Possibly reserved for LRR epic closure / retrospective / handoff phase. Delta should clarify Phase 11 existence + scope in a refill or closure inflection.

## 3. Execution status summary

- **Phases with full execution underway or complete:** 0, 1, 2, 3, 4 (5 of 11)
- **Phases with spec+plan on main but zero execution:** 7, 8, 9 (3 of 11)
- **Phases blocked on substrate decision:** 5, 7 (2 of 11)
- **Phases with spec+plan only on branch:** 6, 10 (2 of 11)
- **Phases not defined:** 11 (1 of 11)

## 4. Critical path analysis

```
LRR epic completion critical path (simplified):

  operator substrate decision
       ↓
  LRR Phase 5 spec + plan authoring
       ↓
  LRR Phase 5 execution
       ↓
  LRR Phase 7 persona execution (blocked on Phase 5)
       ↓
  LRR Phase 6 joint constitutional PR (bundles HSEA Phase 0 0.5 precedent)
       ↓
  LRR Phases 8 + 9 execution (parallel-able)
       ↓
  LRR Phase 10 polish + observability execution
       ↓
  LRR Phase 11 (?) — epic closure / retrospective
```

The operator substrate decision is the single blocking gate for the second half of the LRR epic. Everything past Phase 4 either depends on Phase 5 directly (Phase 7 persona) or is parallelizable but pointless until substrate is chosen (Phases 8-10 narrate against whichever LLM is running, so they need to know what's running).

## 5. Recommendations

### 5.1 Immediate

1. **Surface the substrate decision** as a Tier 1 operator-morning-read item. Beta's v2 synthesis already does this; this audit reinforces that Phase 5-11 execution is blocked until the decision lands.
2. **Cherry-pick the branch-only Phase 6 + Phase 10 spec/plan docs to main** once `beta-phase-4-bootstrap` (PR #819) merges. Until then, the gap is tolerable because Phase 6 + Phase 10 opening depends on upstream work anyway.
3. **Clarify Phase 11 existence + scope** — delta refill 9+ should either define Phase 11 or confirm the LRR epic closes at Phase 10.

### 5.2 Non-urgent

1. **Phase 7 persona authoring** can begin in parallel with Phase 5 even though execution is blocked — the persona spec is substrate-agnostic in structure and only needs the substrate identity to be filled in at execution time.
2. **Phase 8 + Phase 9 preparation work** (reading drop #58 Cluster B + drop #62 §10 Q3 narration-only ratification) can happen during the substrate-decision wait window.
3. **§0.5 reconciliation block for epsilon's Phase 6 spec** (D1 + D2 drift items) can be applied whenever that spec is cherry-picked, not blocking anything upstream.

### 5.3 Coordinator / refill hygiene

Delta's refill 8 item #102 asked for LRR Phase 4 plan authoring. That plan already exists at `docs/superpowers/plans/2026-04-15-lrr-phase-4-phase-a-completion-osf-plan.md` on main. **Already-shipped finding**: item #102 should be marked resolved without new authoring. This is similar to refill 5 item #56 (segment sidecar writer was already at different paths than the spec suggested). Going forward, refill authoring should do a `ls docs/superpowers/{specs,plans}/` sweep before asking for doc creation.

## 6. Non-drift observations

- LRR Phase 0 `FINDING-Q` spike notes are correctly preserved as a separate doc (not folded into the main Phase 0 spec). Phase 0 is canonically closed.
- LRR Phase 1 has BOTH `2026-04-14` and `2026-04-15` spec/plan pairs on main — the `-04-15` versions are amendments-in-place per delta's extraction pattern (9-section template + cross-epic authority pointer). The `-04-14` versions are historical audit trail.
- LRR Phase 2 item #58 (audio archive) is correctly deferred to operator activation via PR #864 runbook. Not a gap.

## 7. References

- Drop #62 `docs/research/2026-04-14-cross-epic-fold-in-lrr-hsea.md` (ratification + addenda trail)
- Beta substrate research v1/v2/errata on `beta-phase-4-bootstrap` (commits `bb2fb27ca`, `d33b5860c`, `f2a5b2348`)
- Epsilon LRR Phase 6 pre-staging on `beta-phase-4-bootstrap` (commit `c945b78f2`)
- Beta LRR Phase 10 extraction on `beta-phase-4-bootstrap` (commit `89283a9d1`)
- Beta LRR Phase 6 cohabitation drift drop (commit `cda23c206`)
- Delta overnight synthesis (commit `b5dcdbf2b`)
- Alpha's 16:55Z refill 4 terminal closure inflection
- Delta refill 8 inflection (`20260415-171100-delta-alpha-refill-8-items-101-105.md`)

— alpha, 2026-04-15T17:20Z
