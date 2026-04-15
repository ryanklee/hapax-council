# HSEA pre-staging branch-only vs main reconciliation audit

**Date:** 2026-04-15
**Author:** alpha (AWB mode, queue/ item #112)
**Scope:** After PR #855 shipped HSEA Phase 6 + 7 spec extractions, audit remaining HSEA phases to identify any branch-only docs that should be cherry-picked to main. Output: reconciliation proposals for any drift.
**Register:** scientific, neutral
**Depends on:** queue #108 (HSEA epic coverage audit, shipped in PR #867)

## 1. Headline

**All 13 HSEA phase specs are on main. Plans are incomplete: 11 of 13 on main, 2 missing entirely.**

- **Specs on main:** 13/13 (Phases 0–12) ✓
- **Plans on main:** 11/13 (Phases 0–5, 8–12)
- **Plans missing:** Phase 6 + Phase 7 — not on main, not on any remote branch, not in git history, not on disk anywhere

**No branch-only HSEA docs exist.** No cherry-pick proposals required. The missing Phase 6 + Phase 7 plans are **unauthored work**, not drift between branches and main.

## 2. Inventory method

```bash
# Specs on main
ls docs/superpowers/specs/*hsea-phase*-design.md

# Plans on main
ls docs/superpowers/plans/*hsea-phase*-plan.md

# All remote branches (searched for HSEA references)
git branch -r | grep -Ei 'hsea|phase-(6|7)'

# Git history for Phase 6/7 plan files across all refs
git log --all --oneline -- 'docs/superpowers/plans/2026-04-15-hsea-phase-6-*-plan.md' \
                           'docs/superpowers/plans/2026-04-15-hsea-phase-7-*-plan.md'

# Disk search
find / -name '*hsea-phase-6*plan*' -o -name '*hsea-phase-7*plan*' 2>/dev/null
```

All searches returned empty for Phase 6/7 plan files. The specs exist (PR #855 aa4576e79), but the plans were never authored.

## 3. HSEA Phase inventory (13 phases)

| Phase | Spec on main | Plan on main | Notes |
|---|---|---|---|
| 0 — Foundation primitives | ✓ `2026-04-15-hsea-phase-0-foundation-primitives-design.md` | ✓ `2026-04-15-hsea-phase-0-foundation-primitives-plan.md` | Delta authored, landed pre-#855 |
| 1 — Visibility surfaces | ✓ `2026-04-15-hsea-phase-1-visibility-surfaces-design.md` | ✓ `2026-04-15-hsea-phase-1-visibility-surfaces-plan.md` | Delta authored |
| 2 — Core director activities | ✓ `2026-04-15-hsea-phase-2-core-director-activities-design.md` | ✓ `2026-04-15-hsea-phase-2-core-director-activities-plan.md` | Delta authored |
| 3 — Research program orchestration | ✓ `2026-04-15-hsea-phase-3-research-program-orchestration-design.md` | ✓ `2026-04-15-hsea-phase-3-research-program-orchestration-plan.md` | Delta authored |
| 4 — Code drafting cluster | ✓ `2026-04-15-hsea-phase-4-code-drafting-cluster-design.md` | ✓ `2026-04-15-hsea-phase-4-code-drafting-cluster-plan.md` | Delta authored |
| 5 — M-series triad | ✓ `2026-04-15-hsea-phase-5-m-series-triad-design.md` | ✓ `2026-04-15-hsea-phase-5-m-series-triad-plan.md` | Delta authored |
| **6 — Content quality + clip mining** | ✓ `2026-04-15-hsea-phase-6-content-quality-clip-mining-design.md` | **✗ MISSING** | Beta PR #855 extracted spec only |
| **7 — Self-monitoring + catastrophic tail** | ✓ `2026-04-15-hsea-phase-7-self-monitoring-catastrophic-tail-design.md` | **✗ MISSING** | Beta PR #855 extracted spec only |
| 8 — Platform value curation | ✓ `2026-04-15-hsea-phase-8-platform-value-curation-design.md` | ✓ `2026-04-15-hsea-phase-8-platform-value-curation-plan.md` | Delta authored |
| 9 — Revenue preparation | ✓ `2026-04-15-hsea-phase-9-revenue-preparation-design.md` | ✓ `2026-04-15-hsea-phase-9-revenue-preparation-plan.md` | Delta authored |
| 10 — Reflexive stack | ✓ `2026-04-15-hsea-phase-10-reflexive-stack-design.md` | ✓ `2026-04-15-hsea-phase-10-reflexive-stack-plan.md` | Delta authored |
| 11 — Multi-agent spawner | ✓ `2026-04-15-hsea-phase-11-multi-agent-spawner-design.md` | ✓ `2026-04-15-hsea-phase-11-multi-agent-spawner-plan.md` | Delta authored |
| 12 — Long-tail handoff | ✓ `2026-04-15-hsea-phase-12-long-tail-handoff-design.md` | ✓ `2026-04-15-hsea-phase-12-long-tail-handoff-plan.md` | Delta authored |

**Totals:** 13/13 specs + 11/13 plans on main. Missing: 2 plans (Phase 6, Phase 7).

## 4. PR #855 analysis

PR #855 (commit `aa4576e79`, merged 2026-04-15T08:38Z, author: beta) shipped exactly two files:

- `docs/superpowers/specs/2026-04-15-hsea-phase-6-content-quality-clip-mining-design.md`
- `docs/superpowers/specs/2026-04-15-hsea-phase-7-self-monitoring-catastrophic-tail-design.md`

The commit message describes 10 Cluster B deliverables for Phase 6 + Cluster D deliverables for Phase 7, all captured in spec form. **No plan files shipped.**

This matches delta's 9-section pre-staging pattern for the specs but not for plans. Delta's earlier HSEA extractions (Phases 0–5, 8–12) paired spec + plan in the same PR; PR #855 only delivered half.

## 5. Remote branch search

```
$ git branch -r | grep -Ei 'hsea|phase-(6|7)'
(empty)
```

**No HSEA-tagged branches on origin.** All HSEA pre-staging work has either been merged to main (Phases 0–5, 8–12 full pairs + Phase 6/7 specs) or has been cleaned up post-merge. No dangling branches with Phase 6/7 plan drafts.

Local branches checked: `beta-phase-4-bootstrap` (no Phase 6/7 plan files), `docs/drop-62-phase-11-hedge-fix-126` (deleted post-merge). Reflog scanned: no references to Phase 6/7 plan authoring events.

## 6. Git history search

```
$ git log --all --oneline -- 'docs/superpowers/plans/2026-04-15-hsea-phase-6-*' \
                              'docs/superpowers/plans/2026-04-15-hsea-phase-7-*'
(empty)
```

**Phase 6 + Phase 7 plan files have zero git history across all refs.** They were never authored in any commit on any branch.

## 7. Disk search

`find /` for `*hsea-phase-6*plan*` and `*hsea-phase-7*plan*` returned empty results across the entire filesystem. Not in `/tmp/`, not in `~/.cache/`, not in any worktree, not in any stash, not in any inflection or research drop.

The plans genuinely do not exist.

## 8. Classification: unauthored work, not drift

**This is not a reconciliation problem.** Reconciliation implies two divergent states that need to be merged or synced. Here there is only one state (main) and a gap (no plans authored for Phase 6/7). The correct remediation is a **fresh plan authoring pass**, not a cherry-pick.

The queue item #112 description assumed some phase pre-stagings might still be on branches. The audit finding is: **zero branch-only HSEA docs exist**. PR #855 is the only case where a spec was extracted without its paired plan, and the plan simply was not written.

## 9. Remediation proposals

### 9.1 Primary proposal — author Phase 6 + Phase 7 plans (queue items)

Create two new queue items:

```yaml
id: "137"  # or next available
title: "HSEA Phase 6 plan authoring"
description: |
  Author docs/superpowers/plans/2026-04-15-hsea-phase-6-content-quality-clip-mining-plan.md
  following delta's 9-section plan template. Input: existing spec at
  docs/superpowers/specs/2026-04-15-hsea-phase-6-content-quality-clip-mining-design.md.
  Phase 6 covers 10 Cluster B deliverables (clipability scorer, exemplar curation,
  anti-pattern detection, etc.). Mirror the plan structure of Phases 4, 5, 8.
priority: normal
size_estimate: "~200 lines plan, ~25 min"
```

```yaml
id: "138"  # or next available
title: "HSEA Phase 7 plan authoring"
description: |
  Author docs/superpowers/plans/2026-04-15-hsea-phase-7-self-monitoring-catastrophic-tail-plan.md
  following delta's 9-section plan template. Input: existing spec at
  docs/superpowers/specs/2026-04-15-hsea-phase-7-self-monitoring-catastrophic-tail-design.md.
  Phase 7 covers Cluster D deliverables (FSM recovery narration, alert triage,
  catastrophic tail monitoring). Mirror the plan structure of Phases 4, 5, 8.
priority: normal
size_estimate: "~200 lines plan, ~25 min"
```

### 9.2 Alternative — accept partial extraction + document rationale

If Phase 6 + Phase 7 plan authoring is intentionally deferred (e.g., because those clusters are lower priority per drop #62 fold-in table row #14 UP-12 parallelism basket), amend the HSEA epic spec `docs/superpowers/specs/2026-04-14-hsea-epic-design.md` to state: "Phase 6 + Phase 7 plans are intentionally deferred pending Phase 0–5 execution; specs are sufficient for pre-staging."

Alpha recommends the primary proposal (author the plans) over the alternative. The partial extraction was likely an oversight during the rapid-pace #855 ship, not an intentional design decision.

### 9.3 No cherry-pick proposals

**Zero branch-only HSEA docs to cherry-pick.** All work is either on main or unauthored.

## 10. Cross-references

- **Queue item #108:** `docs/research/2026-04-15-hsea-epic-coverage-audit.md` (shipped in PR #867) — confirmed all 13 specs on main
- **Queue item #112:** this doc (shipped in PR #TBD) — reconciliation check; zero branch drift
- **PR #855:** `aa4576e79` — beta's Phase 6 + 7 spec extraction (spec-only, no plans)
- **HSEA epic spec:** `docs/superpowers/specs/2026-04-14-hsea-epic-design.md`
- **Delta's 9-section pattern:** documented in `docs/research/2026-04-15-delta-extraction-pattern-meta-analysis.md` (shipped 2026-04-15)

## 11. Closing

No branch-only HSEA work exists. The only HSEA phase gap on main is the two missing plans (Phase 6 + Phase 7), which are unauthored rather than drifted. Recommended remediation: author the two missing plans as fresh queue items.

Branch-only commit per queue item #112 acceptance criteria.

— alpha, 2026-04-15T18:12Z
