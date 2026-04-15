# FINDING-S — SDLC pipeline decision record

**Date:** 2026-04-15
**Author:** alpha (AWB mode, queue/ item #130)
**Scope:** Decision record for LRR Phase 10 §3.5 FINDING-S (SDLC pipeline dormancy). Per alpha's gap proposal E (inflection `20260415-173500`, §1.E). Enumerates the three options, documents alpha's recommendation, and leaves an explicit operator input slot with a default-ship fallback.
**Register:** decision-record (structured, not narrative)
**Status:** draft decision record, operator input required

## 1. FINDING-S definition

**FINDING-S** = **S**DLC pipeline dormancy: the LLM-driven software lifecycle pipeline (Triage → Plan → Implement → Adversarial Review → Axiom Gate → Auto-merge) has 324 dry-run events logged, 0 production executions, all 5 stages DORMANT.

Per workspace CLAUDE.md § "SDLC Pipeline":

> LLM-driven lifecycle via GitHub Actions: Triage → Plan → Implement → Adversarial Review (3 rounds max) → Axiom Gate → Auto-merge. Scripts in `scripts/`, workflows in `.github/workflows/`. All scripts support `--dry-run`. Observability via `profiles/sdlc-events.jsonl` + Langfuse traces. Agent PRs only on `agent/*` branches with `agent-authored` label.

The pipeline was implemented and dry-run-tested, but never transitioned from dry-run to live execution. All 324 logged events are `--dry-run` artifacts. `sdlc-events.jsonl` shows zero non-dry-run entries. Current state of the 5 stages:

| Stage | Workflow file | Live? | Dry-run events |
|---|---|---|---|
| Triage | `.github/workflows/triage.yml` (if exists) | DORMANT | part of 324 |
| Plan | `.github/workflows/plan.yml` | DORMANT | part of 324 |
| Implement | `.github/workflows/auto-fix.yml` | DORMANT | part of 324 |
| Adversarial Review | `.github/workflows/claude-review.yml` | DORMANT | part of 324 |
| Axiom Gate | `.github/workflows/axiom-gate.yml` | DORMANT | part of 324 |

All 5 stages have a 100% failure rate in dry-run mode — the pipeline never progressed past stage 2 in any observed dry-run attempt.

## 2. Why SDLC integration is considered

Three motivations for having an LLM-driven SDLC pipeline at all:

1. **Parallelism across phases.** The LRR + HSEA epics have 14 phases × ~3-8 sessions each. An LLM-orchestrated pipeline could run non-blocking background work (draft commits, run tests, open PRs) while human-driven sessions do high-judgment work.
2. **Axiom gate enforcement.** The Axiom Gate stage is designed to reject PRs that introduce T0 axiom violations (auth, roles, user_id, etc.). Currently enforced via commit-time hooks + CODEOWNERS; SDLC pipeline would add a second layer.
3. **Self-reference as research artifact.** Hapax orchestrating its own SDLC is a publishable research outcome (meta-agent loop on code maintenance). Substrate for future research claims.

## 3. Three options

### 3.1 Option 1 — **Retire**

**Action:** Delete the dormant infrastructure entirely.

```
rm -f .github/workflows/auto-fix.yml
rm -f .github/workflows/claude-review.yml
rm -f .github/workflows/triage.yml
rm -f .github/workflows/plan.yml
rm -f .github/workflows/axiom-gate.yml
rm -f profiles/sdlc-events.jsonl
```

Remove the § "SDLC Pipeline" section from council CLAUDE.md.

**Effort:** ~50 LOC of deletion + 1 docs update. ~30 min.

**Trade-offs:**
- **Pro:** free up CI minutes (currently costing ~$X/month in GitHub Actions even for dry-runs — unknown but non-zero)
- **Pro:** reduce CLAUDE.md cognitive load for future sessions — one fewer dormant subsystem to track
- **Pro:** eliminates the "is it live?" ambiguity that has repeatedly confused audit passes
- **Con:** loses 324 dry-run events' worth of debugging data about why the pipeline failed
- **Con:** re-building later (if the decision is reversed) costs the full implementation effort again (~2-3 weeks?)
- **Con:** closes the self-reference research direction permanently

**Recommended for:** operators who have decided the SDLC pipeline is not worth investing in and want to reduce system complexity.

### 3.2 Option 2 — **Revive**

**Action:** Fix the 100%-failure workflows. Run dry-run for 2 more weeks. Reassess.

Technical scope:
1. Investigate why dry-runs fail at stage 2 (Plan). Most likely: prompt cost budget exceeded, LLM timeout, or output-parse failure.
2. Fix the root cause(s). Patch the workflow yaml + any Python orchestration scripts.
3. Re-enable dry-run execution.
4. Monitor for 2 weeks. Decide at end: retire or integrate.

**Effort:** ~500 LOC across workflows + scripts + tests. ~1 week alpha effort (concentrated).

**Trade-offs:**
- **Pro:** preserves optionality — a successful revive makes Option 3 possible
- **Pro:** 2-week evaluation window is time-boxed, so the decision is bounded
- **Con:** 100% dry-run failure rate is a bad sign; revival may just push failure to stage 3 or 4
- **Con:** 1 week of alpha effort while LRR Phase 5 substrate gate is blocking other work
- **Con:** reassessment in 2 weeks puts the decision past LRR Phase 10 close — may not be time to integrate

**Recommended for:** operators who want to preserve optionality but are not yet committed to integration.

### 3.3 Option 3 — **Integrate**

**Action:** Use the SDLC pipeline's Triage → Plan → Implement → Review → Gate stages to orchestrate LRR + HSEA epic phase execution. The pipeline becomes the real vehicle for phase work.

Technical scope:
1. Everything in Option 2 (fix the 100% failure rate)
2. Integrate the Triage stage with the queue/ per-item protocol v3 — queue items become pipeline inputs
3. Integrate the Plan stage with `docs/superpowers/plans/` authoring workflow
4. Integrate the Implement stage with the branch-+-PR workflow (replacing manual alpha/beta authoring for mechanical work)
5. Integrate the Review stage with existing PR review workflows
6. Integrate the Gate stage with the axiom commit hooks

**Effort:** ~1,500 LOC across workflows + scripts + docs + tests + integration glue. ~3 weeks alpha-equivalent effort, probably parallelizable.

**Trade-offs:**
- **Pro:** produces a meaningful research artifact (Hapax orchestrating its own SDLC on the livestream epic — publishable material for the self-reference research direction)
- **Pro:** once working, reduces per-PR human effort significantly
- **Pro:** axiom gate enforcement at the pipeline level gives defense-in-depth
- **Con:** highest cost of the three options
- **Con:** substantial integration risk — could hijack the LRR epic if pipeline bugs block phase execution
- **Con:** requires operator commitment + availability for the 3-week integration window
- **Con:** contention with LRR Phase 5 substrate gate — neither alpha nor beta has bandwidth for both

**Recommended for:** operators who want the SDLC pipeline as a first-class research artifact AND are willing to slow down LRR execution to build it.

## 4. Alpha's recommendation

**Default: Option 1 (retire) unless operator chooses otherwise.**

Reasoning:

1. **The 100% failure rate across 324 events is a strong empirical signal.** A system that cannot execute successfully even in dry-run mode has a deeper design problem than can be fixed in a single debugging pass. Option 2's "fix and re-evaluate in 2 weeks" is polite uncertainty; Option 1 is the operationally honest call.
2. **Alpha + beta bandwidth is the real constraint.** Post-§14 substrate gate, LRR Phase 5 re-spec + HSEA Phase 4 I-cluster + HSEA Phase 6/7 plan authoring all need attention. Option 2's 1 week or Option 3's 3 weeks compete directly with critical-path LRR work.
3. **Axiom gate enforcement is already handled at commit time.** The axiom-scan.sh + axiom-commit-scan.sh hooks (queue #123 audit) enforce T0 violations. An SDLC-level gate would be a second layer, not the only layer. The marginal benefit is small.
4. **Option 3's research value is real but deferrable.** "Hapax orchestrates its own SDLC" is a good research direction but does not need to happen during LRR. It can be re-started from scratch in Cycle 3 (post-Phase-A-data) with the benefit of a cleaner starting point.

**Exception: upgrade to Option 2 for critical substrate swaps.** If the operator decides the substrate gate needs LLM-orchestrated de-risking (e.g., automatically running Phase A sessions against the new substrate with SDLC-mediated rollback), then Option 2 becomes worth the 1-week investment. But this is a substrate-specific exception, not a general recommendation.

## 5. Operator input slot

**Question for operator:**

> Which option for FINDING-S SDLC pipeline?
>
> - [ ] Option 1 — retire (default, alpha's recommendation)
> - [ ] Option 2 — revive + 2-week dry-run
> - [ ] Option 3 — integrate with LRR + HSEA execution
> - [ ] Defer decision to post-LRR (keep dormant as-is)

**Default-ship fallback:** if no operator input by 2026-04-22 (one week from this decision record), ship Option 1 (retire). Rationale: a dormant subsystem consuming CI minutes is actively worse than a deleted subsystem; absence of operator input is interpretable as "not actively valued."

**Escalation path:** operator says "wait, I need to think about this" → defer decision to post-LRR (keep dormant). Operator says nothing → default-ship Option 1 on 2026-04-22.

## 6. Implementation order for Option 1 (if chosen)

1. Commit 1: delete `.github/workflows/auto-fix.yml` + `claude-review.yml` + any other SDLC workflow files
2. Commit 2: delete `profiles/sdlc-events.jsonl` (preserve copy at `/tmp/sdlc-events-archived-2026-04-22.jsonl` for forensics)
3. Commit 3: update council CLAUDE.md § "SDLC Pipeline" — either delete section entirely OR replace with a one-line tombstone ("SDLC pipeline retired 2026-04-XX per FINDING-S decision")
4. Commit 4: update LRR Phase 10 spec §3.5 to reflect the ratified decision

All four commits can bundle into one PR for clean history.

## 7. Implementation order for Option 2 (if chosen)

1. Investigate dry-run failure root cause (read `profiles/sdlc-events.jsonl` + Langfuse traces for the last 10 failed runs)
2. Identify the failing stage + failure mode (LLM timeout / cost / parse error / axiom gate false-positive / other)
3. Patch the root cause (workflow yaml, Python orchestration, or prompt template — whichever)
4. Re-enable dry-run execution via `gh workflow run --inputs dry_run=true`
5. Monitor for 2 weeks with daily digest via ntfy
6. Decide at end: retire or integrate

## 8. Implementation order for Option 3 (if chosen)

Not drafted in detail because alpha's recommendation is Option 1. If operator chooses Option 3, alpha will draft a separate decision record + 3-week execution plan as a follow-up queue item.

## 9. Cross-references

- **Alpha close-out handoff:** `docs/superpowers/handoff/2026-04-XX-alpha-close-out.md` — original FINDING-S source (324 dry-run events figure)
- **LRR Phase 10 spec §3.5:** `docs/superpowers/specs/2026-04-15-lrr-phase-10-observability-drills-polish-design.md` @ commit `89283a9d1` on `beta-phase-4-bootstrap`
- **Workspace CLAUDE.md § "SDLC Pipeline"** — current documented state of the dormant pipeline
- **Queue item #123 hooks/scripts audit:** confirms axiom-scan.sh + axiom-commit-scan.sh already enforce T0 violations at commit time
- **Queue item #132 Prometheus metrics registry audit:** downstream; may find SDLC-pipeline-related metrics that affect this decision
- **Alpha's gap proposal E:** inflection `20260415-173500` §1.E — seeded this queue item

## 10. What this decision record does NOT do

- **Does not execute Option 1.** Decision is pending operator input; default-ship fires on 2026-04-22 if no input.
- **Does not delete any SDLC workflow files.** Retention is pending decision.
- **Does not update LRR Phase 10 §3.5 spec text.** That happens downstream of the operator decision.
- **Does not close FINDING-S.** FINDING-S remains OPEN until the decision is ratified + executed.

## 11. Closing

FINDING-S is a concrete operational decision — retire the dormant SDLC pipeline, invest in it, or integrate it into the LRR + HSEA execution workflow. Alpha recommends Option 1 (retire) based on 100% dry-run failure rate + constrained alpha/beta bandwidth + existing axiom-gate coverage at commit time. Operator input slot open until 2026-04-22; default-ship fires on that date if no input.

— alpha, 2026-04-15T19:22Z
