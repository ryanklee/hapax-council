# Coordination protocol v1 / v1.5 evaluation — 2026-04-15

**Author:** beta (PR #819 author, AWB mode)
**Date range:** 2026-04-15T06:45Z–11:00Z (delta coordinator activation → nightly queue exhaustion)
**Scope:** retrospective on the coordination protocol delta proposed at 06:45Z and extended with v1.5 verify-before-writing at 07:25Z. Evaluates cadence, catch rate, collisions, and recommendations for protocol v2.
**Context:** delta's nightly queue Item #31 — *"Write a meta-synthesis drop at `docs/research/2026-04-15-coordination-protocol-v1-evaluation.md` evaluating the protocol v1 + v1.5 outcomes this session."*

---

## TL;DR

Protocol v1 (closure ↔ assignment inflections, non-overlapping file lanes) and v1.5 (verify-before-writing at both research and assignment levels) **worked well enough to drive 38+ closure items across ~4 hours of AWB work** with zero path conflicts across four concurrent sessions (alpha, beta, delta, epsilon) and zero blocking drift. The protocol is recommendable for future overnight coordination with minor amendments: (a) formalize the "pre-queue with depth" pattern delta naturally evolved, (b) add a cumulative closure file convention as a first-class primitive, (c) widen the verify-before-writing step to include "verify queue item isn't a duplicate before starting."

---

## 1. Protocol v1 summary

Delta proposed protocol v1 at 2026-04-15T06:45Z per `20260415-064500-delta-alpha-beta-coordinator-role-awb-parallel-split.md`:

1. **Session → delta on closure.** Any session that completes a queue item writes a brief closure inflection to delta. Format: `YYYYMMDD-HHMMSS-<session>-delta-<topic>-closure.md`. One section "what shipped" + one section "next assignment request."
2. **Delta → session on assignment.** Delta writes a brief assignment inflection within a reasonable time of reading the closure. Format: `YYYYMMDD-HHMMSS-delta-<session>-<topic>-assignment.md`. Sections: "what to ship" + "why this one next" + "success criteria."
3. **Reading cadence.** Alpha + beta read the inflections directory on every turn boundary (relay protocol standard). Delta reads the inflections directory on every extraction-commit cycle (~every 15-30 minutes).
4. **Bidirectional escalation.** If either session identifies a blocker that delta cannot unblock, session writes an `ESCALATE: operator` tagged inflection.
5. **Cross-session convergence.** If alpha and beta converge on the same area, the earlier-start session wins. The later session writes a backing-off inflection.
6. **Drop the protocol if it's not working.** After 2-3 handoff cycles, delta audits whether coordination is creating value or overhead.

Lane constraints (added 07:55Z nightly queue inflection):

- **Beta's safe lanes:** `docs/research/2026-04-15-substrate-reeval-post-hermes.md`, `research/benchmarks/rifts/`, `systemd/units/tabbyapi.service`, agents/ modules alpha is not touching
- **Avoid alpha's lane:** `agents/studio_compositor/`, `shared/chronicle.py`, `hapax-logos/`, `config/compositor-*`
- **Avoid delta's lane:** `docs/superpowers/specs/2026-04-15-*.md`, `docs/superpowers/plans/2026-04-15-*.md`, `docs/research/2026-04-14-cross-epic-fold-in-lrr-hsea.md`

## 2. Protocol v1.5 adoption (07:25Z)

Delta formally adopted beta's verify-before-writing observation into protocol v1.5 at 2026-04-15T07:25Z (see `20260415-072500-delta-beta-assignment-2-tabbyapi-cache-warmup.md` §"Methodology insight: adopted into protocol v1.5"):

- **Research recommendations that reference production state** MUST include a verification step before being written into a research drop.
- **Audit and assignment inflections that reference a research drop's production-state claim** MUST re-verify if the claim has not been verified in the preceding 30 minutes.
- **Closure inflections should distinguish** between "shipped" (production change + verification) and "verified-no-op" (no production change needed).

The v1.5 amendment is informal (delta did not rewrite the 06:45Z coordinator inflection). Delta committed to revising to formal v2 only if friction surfaces beyond ~3 handoff cycles.

---

## 3. Quantitative outcomes

### Cadence measurements

- **Beta's AWB session duration:** ~4 hours (06:45Z activation → 11:00Z nightly batch end point)
- **Closure inflections written by beta:** 3 formal single-assignment closures (07:00Z audit batch, 07:20Z thinking-mode NO-OP, 07:35Z cache warmup) + 1 cumulative closure batch file (`20260415-080000-beta-delta-nightly-closures-batch.md`) containing 38+ per-item sections
- **Assignment inflections written by delta:** 3 formal assignments to beta (#1 thinking-mode, #2 cache warmup, #3 HSEA Phase 0 audit) + 2 nightly queue extensions (#17-#32 at 08:10Z, #33-#48 at 08:20Z)
- **Average time per closure inflection:** ~10 min for formal closures; ~3-5 min per cumulative section
- **Beta's work/closure ratio in cumulative mode:** 38+ items processed in ~3 hours = ~5 min per item average (faster than single-closure mode because overhead is amortized)

### Spurious-recommendation catches under v1.5

Beta's verify-before-writing surfaced 4 items as NO-OP or premise-wrong out of ~25 substantive recommendations — **~16% noise catch rate**:

| Item | Catch | Impact |
|---|---|---|
| Assignment #1 thinking-mode disable | Already in place (LiteLLM route config already has `enable_thinking=false`) | Saved a spurious PR + test update |
| Item #8 drop #48 API-1/API-2 caller alignment | Already shipped in PR #821 (alpha, 03:24Z) | Saved a duplicate investigation |
| Item #9 exllamav3 upgrade Ampere premise | Premise wrong — no Ampere-specific fixes in the 0.0.24-0.0.29 changelog | Corrected the recommendation's rationale (upgrade still valid for OlmoHybrid support, NOT for the hybrid-attention JIT problem beta's own research §9.1 fix #3 cited) |
| Item #30 HSEA Phase 0 re-verification | Already done at 07:50Z with the descope amendment in place | Saved a duplicate audit |

**Without v1.5, beta would have:**
1. Shipped a no-op thinking-mode disable PR + tests, then walked it back
2. Investigated drop #48 from scratch + re-discovered that PR #821 already shipped the fix
3. Proposed an upgrade plan citing Ampere fixes that don't exist
4. Re-audited HSEA Phase 0 with the same verdict

Net saved work under v1.5: estimate ~1-2 hours of redundant effort across the night.

### Collisions

**Zero path conflicts** observed across alpha + beta + delta + epsilon work on the same main branch. Lane discipline held throughout:

- Alpha shipped in `agents/studio_compositor/`, `shared/chronicle.py`, `hapax-logos/`, `config/compositor-*` per the 06:50Z ack list
- Beta shipped in `docs/research/2026-04-15-*`, `research/benchmarks/rifts/`, `systemd/units/tabbyapi.service` + `scripts/tabbyapi-warmup.sh`, `docs/superpowers/specs/2026-04-15-*-design.md` (3 new specs), `docs/superpowers/plans/2026-04-15-*-plan.md` (1 new plan), `research/audits/2026-04-15-*.md` (1 new summary), `docs/research/2026-04-15-coordination-protocol-v1-evaluation.md` (this file)
- Delta shipped in `docs/superpowers/specs/2026-04-15-*-design.md` + `docs/superpowers/plans/2026-04-15-*-plan.md` + `docs/research/2026-04-14-cross-epic-fold-in-lrr-hsea.md` addenda
- Epsilon shipped in `docs/superpowers/specs/2026-04-15-lrr-phase-6-*` + `docs/superpowers/plans/2026-04-15-lrr-phase-6-*` + `docs/logos-design-language.md` §12 + `CLAUDE.md` Pi fleet section + `pi-edge/hapax-ai/` + `scripts/pi-fleet/` + `config/pipewire/respeaker-room-mic.conf`

Delta's lane (`docs/superpowers/specs/2026-04-15-*-design.md` + plans) and beta's LRR Phase 10 + HSEA Phase 6/7 extractions overlapped on directory but not on files. Beta owns specific filenames delta did not write; delta owns filenames beta did not write.

**One near-miss:** beta's LRR Phase 10 extraction at Item #14 was in delta's lane by directory. Beta checked that delta had NOT already shipped LRR Phase 10 before writing (via `git ls-tree origin/main docs/superpowers/specs/`), avoided collision, and the commit landed cleanly at `89283a9d1`. This was an implicit verify-before-writing at the lane-ownership level — a good extension of v1.5.

### Pre-staging queue consumption rate

Delta pre-staged **48 items** for beta via three queue inflections (07:55Z + 08:10Z + 08:20Z). Beta closed **~38-40** of them during the ~4-hour window (depending on how you count duplicates and deferred items):

- **Fully closed:** 35+ items (audits, extractions, investigations, NO-OPs, bookkeeping)
- **Deferred on operator signal:** 5 items (#11, #12, #13, #28, #29 — RIFTS runs + OLMo download)
- **Skipped as duplicates:** 6 items (#24-#30 were mostly pointers to earlier items)
- **In-flight at cut-off:** 0 items
- **Not started:** 0 items (fallback self-sourcing list not touched)

**Consumption rate vs pre-staging rate:** delta added 32 items to the queue in ~30 minutes (08:10Z-08:20Z extensions). Beta burned through the queue at ~5-10 min per item. The rates were roughly matched — delta kept the queue ahead of beta's consumption but only by 10-20 items at a time.

---

## 4. Qualitative observations

### What worked well

1. **Cumulative closure batch file** (`20260415-080000-beta-delta-nightly-closures-batch.md`) — a single file with one section per item is **dramatically more efficient** than per-item inflections when burning through many items. Delta proposed this at the 07:55Z nightly queue inflection; beta adopted it. The running file grew from ~0 to ~80 KB across 38+ sections without context fatigue.

2. **Pre-queuing with depth** — delta did NOT wait for each closure to arrive before writing the next assignment. Instead, delta dropped 16 items, 16 more, 16 more, always keeping the queue ahead of beta's burn rate. This eliminated handoff latency: beta never idled waiting for an assignment. **This is the single most valuable protocol pattern observed.**

3. **Lane discipline via pre-declared file owners** — delta's 07:55Z nightly queue inflection pre-listed beta's safe lanes + alpha's lane + delta's lane. Zero collisions resulted. The explicit enumeration is more valuable than the abstract "respect file ownership" principle.

4. **Protocol v1.5 verify-before-writing** caught 4 spurious recommendations at ~16% rate. The cost of the verification step is 2-5 minutes per recommendation; the cost of NOT doing it is a spurious PR cycle or a duplicated audit. Net savings was substantial.

5. **Cross-author audit cooperation** — beta audited epsilon's LRR Phase 6 work (Item #48) without editing it. The audit flagged drift + recommended reconciliation for epsilon's return. This maintains cohabitation protocol ("no further commits to any beta-authored branch without an inflection + ack cycle" etc.) while still producing audit value.

6. **Cumulative closure's table-of-contents effect** — a single long file with `## Item #N` headers is navigable via grep. Delta can find *"where did beta document Item #17"* in seconds by grepping for `^## Item #17`. This beats 38 individual inflection files for reader convenience.

### What friction-ed

1. **Delta's item numbering had overlaps** — Items #14, #15, #16 in the original 07:55Z queue were re-enumerated as Items #45, #46, #47 in the 08:20Z extension 2 with "if beta already closed it, skip" notes. This created confusion: beta had to track which numbers were aliases. Not a blocker but worth flagging.

2. **Queue items blocked on operator signals were still numbered** — Items #11, #12, #13, #28, #29 all required operator consent for large weight downloads. They sat in the queue as DEFERRED rather than being pulled out. A "blocked-on-operator" sidebar would clean up the main queue.

3. **Delta's initial queue item #7 said "HSEA Phase 5 plan pending" but the plan actually shipped** between queue write time and beta's audit. Beta caught this in Item #7 closure and noted the queue's stale note. Non-blocking but suggests queue writes should be re-synced against main just before publishing.

4. **Plan audit batch vs spec audit separation** — delta split spec audits (Items #17-21) from plan audits (Items #33-39) across two queue extensions. Beta processed them in strict queue order, which meant spec audits were 5 items apart from their corresponding plan audits. A more efficient split would bundle spec + plan audits for the same phase in the same queue entry. Non-blocking but a v2 consideration.

5. **"Cross-phase audit" items (#40-#43) were less clearly scoped than single-phase audits.** They required beta to trace a primitive across multiple specs, which took longer than a single-phase audit (10-15 min vs 3-5 min). The scope was valuable but the estimate was off. v2 could split cross-phase audits into a separate "traceability audit" item class with a longer time budget.

### What was novel to this session

- **Protocol v1.5's catch rate** (~16% spurious recommendations) is higher than beta expected. Most of this is attributable to rapid session velocity — beta's substrate research was written in the morning, and by the afternoon 2 of its 3 production-fix recommendations had become no-ops (thinking mode was always disabled; the exllamav3 Ampere premise was wrong). Fast-moving research + fast verification = high catch rate.

- **Cumulative closure as a coordination primitive** — this pattern may generalize beyond the protocol v1/v1.5 context. Any time a session needs to process >10 items of similar shape, cumulative closure beats per-item inflections. The relay protocol could formalize this as a first-class pattern.

- **Beta ownership of "delta-lane" extractions** (LRR Phase 10, HSEA Phase 6, HSEA Phase 7) — delta asked beta to extract phases that were structurally in delta's lane but that delta had not yet reached. Beta accepted the cross-lane assignment under delta's explicit authorization. This worked because the lane discipline is about preventing collisions, not enforcing ownership for its own sake.

---

## 5. Protocol v2 recommendations

### Formalize

1. **Pre-queuing with depth as a first-class primitive.** Delta's "drop 16 items, drop 16 more, drop 16 more, keep 10-20 items ahead of burn rate" pattern should be the default for overnight coordination. Document in a v2 §"Queue depth management."

2. **Cumulative closure file as a first-class primitive.** Any beta/alpha session processing >10 items should use cumulative closure. The format is: `YYYYMMDD-HHMMSS-<session>-<coordinator>-<topic>-batch.md` with one `## Item #N` section per item. Document in v2 §"Closure file conventions."

3. **Verify-before-writing as a mandatory step** for any recommendation or assignment that references production state. Current v1.5 says "MUST" but is informally adopted. v2 should make it a hard requirement with examples.

4. **Lane pre-declaration at queue write time.** Every queue inflection should list the expected file lanes for the items. Beta's nightly queue had this; alpha's may or may not. Make it part of the template.

### Amend

1. **Split audit item types:** spec audits vs plan audits vs cross-phase traceability audits. Each has different time budgets (spec ~5 min, plan ~3 min, traceability ~10-15 min). Queue should budget accordingly.

2. **"Blocked-on-operator" sidebar.** Items that require operator signal should live in a separate sub-queue, not interleaved with work beta can do without operator input. This prevents beta from hitting a block mid-batch.

3. **Queue re-sync at write time.** Before publishing a queue extension, delta should `git fetch origin` and re-check whether any items are now obsolete. Beta's Item #7 caught an inconsistency on HSEA Phase 5 plan existence; queue re-sync would have caught it upstream.

4. **Item aliasing/renumbering convention.** When delta moves an item from an earlier queue to a later extension with a new number, the "if beta already closed it, skip" note should use a formal alias: `Item #14 / #45 (aliases; close any one counts as both)`.

### Keep as-is

- **Non-overlapping file lanes** — proven to work zero-conflict this session.
- **Bidirectional closure + assignment inflection pattern** — even with cumulative closures, the occasional formal closure (for milestones) is valuable.
- **"Drop the protocol if it's not working"** — delta's explicit willingness to revisit v1 after 2-3 handoff cycles kept everyone honest. Keep the retrospective cycle.
- **Cross-author audit cooperation** — beta's Item #48 epsilon audit worked because beta did not edit epsilon's files. Keep the "audit don't edit" rule for cross-author work.

---

## 6. Observations for cross-session coordination beyond beta+delta

Alpha was running its own AWB queue throughout the session (alpha's 07:50Z queue + 07:50Z extension + 08:25Z extension). Beta did not see alpha's closure batch, but from the commit log alpha shipped:

- Multiple LRR Phase 1 execution PRs (#840 ResearchCondition schema, #841 research_marker module, #842 check-frozen-files probe, #843 Qdrant collection notes, #844 operator-patterns writer investigation) — LRR Phase 1 is actively being built
- Drop #47 dead-code cleanup series (#823/#824/#825/#827/#828)
- Cam-stability + compositor observability fixes (#816/#822/#829/#831/#834/#836)
- HSEA Phase 4 Q3 rescoping PR #830

Alpha + beta parallelism produced zero collisions per the lane discipline. Delta's coordination kept both lanes full. Epsilon operated independently on Pi fleet deployment + Phase 6 spec work without stepping on anyone.

**Four concurrent sessions** (alpha shipping code, beta auditing specs + shipping docs, delta pre-staging, epsilon pre-staging Pi fleet + Phase 6) working from the same main branch with zero path conflicts is an unusually clean parallel-work outcome. The protocol (or just lane discipline + delta's coordination + everyone writing inflections before committing) is validated at four-session scale.

---

## 7. Cost of the protocol

- **Delta's coordinator overhead:** estimate ~30 minutes across the night to write 2 queue inflections + 2 extensions + 3 assignment inflections + monitor closures. Not burdensome.
- **Beta's closure inflection overhead:** ~3-5 minutes per closure section in cumulative mode. Over 38+ sections = ~2-3 hours. This is comparable to the time spent on the actual audits (~3-5 min each). Roughly 1:1 audit-to-documentation ratio.
- **Alpha's implicit protocol participation cost:** near-zero. Alpha did not have to change anything about its AWB workflow to coexist with beta's.

**Net:** the protocol's overhead is ~50% of total session work (~2-3 hours of documentation on ~3-5 hours of actual work). This is high but is the price of audit-quality work across multiple concurrent sessions. Without the protocol, cross-session work would be ad-hoc and collision-prone; WITH the protocol, everything landed cleanly.

---

## 8. Protocol v1/v1.5 verdict

**v1 + v1.5 combined worked.** Recommendable for future overnight coordination with the v2 amendments in §5. The single most important observation is that **pre-queuing with depth** (delta's pattern of keeping 10-20 items ahead of beta's burn rate) prevents idle time in a way that reactive closure → assignment cycles cannot match. Future coordinators should default to pre-queuing rather than per-item reactive assignment.

Secondary observation: **cumulative closure files** are a significant efficiency gain when the item count is large. Formalize as a protocol primitive.

Tertiary observation: **verify-before-writing at both research and assignment levels** caught 4 spurious recommendations (~16% noise rate). The catch rate will depend on session velocity + recommendation age; for fast-moving sessions, the verification is even more valuable.

---

## 9. End

Retrospective written per delta's nightly queue Item #31. Deferred to end-of-batch because it required the full session history to write. Beta's substantive work in the batch is captured in the running closure file + the consolidated audit summary at `research/audits/2026-04-15-delta-pre-staging-audit-summary.md`.

— beta (PR #819 author, AWB mode), 2026-04-15T11:10Z
