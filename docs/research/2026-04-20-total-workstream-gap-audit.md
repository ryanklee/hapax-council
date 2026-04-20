---
date: 2026-04-20
author: research-subagent (dispatched by alpha; ≤8-min time-boxed)
audience: alpha (and successor sessions) — "total implied workstream" view
register: scientific, neutral
register-note: builds on `~/.cache/hapax/relay/delta-to-alpha-workstream-gap-audit-20260420.md`; does NOT repeat its 6 findings verbatim
operator-directive-load-bearing: |
  "make sure there are no misses like this and alpha is aware of the
  total implied workstream. research."
---

# Total Workstream Gap Audit — 2026-04-20

## §1. Executive summary

**Counts (post-state-update, all sources scanned):**

| Bucket | N |
|---|---|
| Total open work items across all sources | **~58** |
| Items in WSJF (D-NN) or operator-queue (OQ-NN) | **30** (25 D-NN + 3 OQ + new D-26a/D-18b/D-27b in WSJF tail) |
| Items mentioned in writing but NOT in any active plan/queue | **17** (delta's 6 + 11 net-new in §3) |
| Items shipped but still appearing OPEN in queues (cleanup) | **~6** (D-09 / D-17 / D-18 already updated; ~6 in WSJF §6/§8 still describe old state — see §4) |
| Open GH PRs (all dependabot/vendored, none load-bearing) | 13 |
| Open GH issues | 0 |

**Top 3 systemic-pattern misses (NOT specific items — these are the meta-misses producing the near-miss class):**

1. **Plans live, queue does not refer back.** Multiple operator-named items (e.g., `task #164` content-programming) HAD a plan (`2026-04-20-programme-layer-plan.md`) authored after delta's audit cycle, but neither delta-WSJF nor `operator_queue_adds_20260420` carries a back-reference. Reverse-mapping (queue → plan) does not exist; only forward (plan → queue) does, and even that only via narrative prose. **Risk class:** "spec'd but looks unspec'd" — exactly the operator-flagged near-miss pattern.
2. **Research-doc-without-plan is treated as planning.** 8 large research docs (HOMAGE-SCRIM 1–6, nebulous-scrim-design, content-programming-layer-design) are operator-relied-on for the active work but have no corresponding plan doc. Delta MISS #1 captures this for HOMAGE-SCRIM; the same pattern recurs across the OQ-02 family and the new ward-umbrella spec (`2026-04-20-homage-ward-umbrella-design.md`) which has plan parity gap.
3. **Operator queues fragment across surfaces.** `operator_queue_adds_20260420` (alpha.yaml :1499–1700) lives in the relay yaml, NOT in WSJF; WSJF lives in the handoff doc; task IDs (#164–#240) live as scattered mentions in alpha.yaml without a registry. The operator's "queue" is currently three queues (WSJF D-NN, alpha.yaml OQ-NN, scattered task #NN) with no canonical join. **The CC-task Obsidian SSOT spec (`docs/superpowers/specs/2026-04-20-cc-task-obsidian-ssot-design.md`) addresses this — it is the structural fix for misses #1 + #3 — but is NOT yet on a plan doc.**

---

## §2. Source inventory

| Source | Items found | Tracked in WSJF/OQ? | Unique to source |
|---|---|---|---|
| `docs/superpowers/plans/*.md` (183 total, 30 latest scanned) | ~30 active plans | ~12 referenced by D-NN | ~18 plans reference work outside any D-NN (e.g., `2026-04-20-programme-layer-plan.md` 12 phases vs zero D-NN entries) |
| `docs/superpowers/specs/*.md` (212 total, 30 latest scanned) | ~30 active specs | ~6 directly referenced | **24 specs have no corresponding plan or D-NN** (incl. `homage-ward-umbrella-design`, `cc-task-obsidian-ssot-design`, `audio-pathways-audit-design`, `chat-ambient-ward-design`, `local-music-repository-design`, `splattribution-design`, `non-destructive-overlay-design`, `operator-sidechat-design`, `preset-variety-expansion-design`, `reverie-substrate-preservation-design`, `rode-wireless-integration-design`, `role-derivation-research-template-design`, `soundcloud-integration-design`, `token-pole-homage-migration-design`, `vinyl-image-homage-ward-design`) |
| `docs/research/*.md` (292 total, 30 latest scanned) | ~30 active research docs | ~10 cited in D-NN/OQ | **15+ research docs do not feed any active plan** — see §3 misses |
| `docs/superpowers/handoff/*.md` (44 total, 20 latest scanned) | ~20 handoffs; the WSJF doc is the front-of-queue | n/a | "deferred" + "remaining" lines spread across 7 handoffs; no consolidated "what stayed open" doc |
| `~/.cache/hapax/relay/*.md` + `*.yaml` (~50 active drops) | 9 delta→alpha drops in last 24h + alpha.yaml | partial | OQ-01/02/03 in alpha.yaml :1499–1700; 4 cross-zone handoffs with their own queue residue |
| `relay/alpha.yaml` `operator_queue_adds_20260420` (line 1499) | 3 items (OQ-01/02/03) | OQ-01=D-25 SHIPPED; OQ-02 promoted to triage; OQ-03 outside-WSJF | OQ-03 (camera_topology epic) is alpha-zone outside-WSJF and easy to lose |
| WSJF `delta-wsjf-reorganization.md` | 25 D-NN + D-26a/D-18b/D-27b tail items | yes | D-NN is delta-zone canonical; alpha-zone work absent from WSJF |
| `memory/MEMORY.md` | ~70 project entries naming in-flight epics | partial | Several "active" project memos (project_unified_recruitment, project_reverie_adaptive, project_ground_surface, project_homage_go_live_directive) name workstreams without explicit plan doc cross-ref |
| Recent 50 commits | 50 commits since 2026-04-19; dominated by D-NN / fix(...) | yes for D-NN-tagged | 4 commits beta-queue-tagged (#225, #226, #228, #240) — these are beta queue items, NOT in WSJF |
| `gh issue list --state open` | 0 | n/a | n/a |
| `gh pr list --state open` | 13 (all dependabot, vendored vscode/) | n/a | none load-bearing |

---

## §3. The misses table

**Methodology:** delta's `delta-to-alpha-workstream-gap-audit-20260420.md` already enumerates 6 misses (HOMAGE-SCRIM, D-15 redesign, content-programming meta-layer, Ring 2 P1 status, full wiring audit, SRCE clarification). Those 6 are NOT repeated below. New ones are net additions, found by scanning sources delta did not exhaust.

| ID | Source | Item | Recommendation |
|---|---|---|---|
| **NEW-1** | `docs/superpowers/plans/2026-04-20-programme-layer-plan.md` (12 phases, task #164) | Content programming layer (meso) plan EXISTS but is invisible — not in WSJF, not referenced from `operator_queue_adds_20260420`, no D-NN allocated. THIS is the exact near-miss the operator flagged. | Allocate D-NN slot to programme-layer phases 1–12; add cross-reference from delta-WSJF; add reverse-link from MEMORY.md `project_programmes_enable_grounding`. |
| **NEW-2** | `docs/superpowers/specs/2026-04-20-cc-task-obsidian-ssot-design.md` (delta-authored 18:30Z) | CC-task Obsidian SSOT spec exists but no plan doc. Delta noted "alpha action: convert to plan." It is the structural fix for §1 systemic misses #1 + #3 — high leverage. | Top-priority plan-doc creation; cite §1 of THIS doc as load-bearing rationale. Per spec's "Open questions" §, raise the 5 OQs before plan draft. |
| **NEW-3** | `docs/superpowers/specs/2026-04-20-homage-ward-umbrella-design.md` (alpha-authored, latest spec by mtime) | New umbrella spec covering HOMAGE ward family. No plan doc. Adjacent to delta MISS #1 but NOT identical (HOMAGE-SCRIM is the scrim-mechanic; homage-ward-umbrella is the per-ward registry). | Plan-doc within the same epic as HOMAGE-SCRIM (per delta MISS #1); call out shared spec-deps. |
| **NEW-4** | `docs/research/2026-04-20-d01-director-impingement-consumer-architecture.md` | D-01 has shipped (`ce427c3a3`) but the architecture research doc is fresh and unreferenced from MEMORY.md or plans/. Research-without-plan; could become a plan-eligible follow-on for "remaining producers" or "consumer-side robustness." | Either close the research doc with explicit "this is reference, not a follow-on" note, or file plan-stub for follow-ons. |
| **NEW-5** | `docs/research/2026-04-20-camera-visual-abstraction-investigation.md` (= OQ-03 source) | OQ-03 (camera_topology parallel to audio_topology) is alpha-zone, "outside-WSJF," explicitly sequenced AFTER Source-Registry Completion Epic — but Source-Registry Completion Epic itself is in flight per `2026-04-13-reverie-source-registry-completion-plan.md`. Two-step sequencing risk: when SRCE completes, OQ-03 may be forgotten because no item links them. | Add an explicit "after SRCE completes, dispatch OQ-03 plan" note to the SRCE completion plan §closing; or auto-promote OQ-03 to D-NN at SRCE-merge time. **Note:** "SRCE" in delta MISS #6 may be precisely **Source Registry Completion Epic** — the acronym fits. Strong candidate for the SRCE clarification. |
| **NEW-6** | `docs/research/2026-04-20-dead-bridge-modules-audit.md` | Dead-bridge audit produced D-17/D-18/D-26/D-27 (now SHIPPED). Audit-doc itself is unreferenced from any "lessons learned" section; the meta-pattern (skeleton-then-defer) is captured ONLY in WSJF §3.5 prose. | File one-page meta-pattern spec: "Skeleton-then-defer anti-pattern" governance — every new module must include 1 production caller in same PR or be tagged WIP. (Operator value: prevents repeat of the dead-bridge chain.) |
| **NEW-7** | `docs/research/2026-04-20-livestream-halt-investigation.md` | Investigation doc — outcome not threaded to D-02 (livestream regressions standing readiness) or any plan. | Cross-link from D-02 standing-readiness in WSJF; add to MEMORY.md if root cause is recurring class. |
| **NEW-8** | `docs/research/2026-04-20-vitruvian-enhancement-research.md` + `delta-queue-vitruvian-enhancement-20260420.md` | Vitruvian/token-pole enhancement research is in delta-relay queue but NOT in WSJF. | Either accept as deferred (note in WSJF §6 NEEDS_RESEARCH queue) or file D-NN slot. |
| **NEW-9** | `docs/research/2026-04-20-cbip-vinyl-enhancement-research.md` + `delta-queue-cbip-vinyl-enhancement-20260420.md` + `2026-04-20-cbip-1-name-cultural-lineage.md` | CBIP (cultural-broadcast-something) family is 3 research docs deep with no plan and no D-NN. | Allocate plan stub or formally defer with stated criterion. |
| **NEW-10** | `docs/superpowers/specs/2026-04-18-audio-pathways-audit-design.md` + `audio-reactivity-contract-design.md` + `2026-04-18-camera-naming-classification-design.md` + `2026-04-18-heterogeneous-agent-audit-design.md` + 4 more (see §2 row 2) | 8+ specs from 2026-04-18 spec-burst with NO matching plan or D-NN. These are the "spec'd but never planned" residue from a single high-velocity day. | Sweep — for each spec, decide: (a) supersede & close, (b) file plan stub with WSJF placeholder, or (c) tag as design-only / reference-doc. Do this as one short triage pass. |
| **NEW-11** | `recommended_fix_order_for_delta` in alpha.yaml :812–818 (6 ordered fixes) and `remaining_unfixed` :763–769 (FINDING-D / FINDING-V / FINDING-W / FINDING-X / FINDING-F / FINDING-G) | These named findings persist in alpha.yaml audit residue, not in WSJF. FINDING-V partially addressed by `2026-04-20-orphan-ward-producers-plan.md` but the plan is also not D-NN'd. | Either (a) sweep FINDING-X (grounding_provenance 99.5% empty, "constitutional violation" per audit) into a D-NN, or (b) close it with explicit shipped-commit citation. Do NOT leave constitutional-violation findings floating. |

**Total new misses: 11. Augmenting delta's 6 → grand total 17 misses across the workspace.**

---

## §4. Spec/code drift

Confirmed drifts (sample of 5; not exhaustive — operator should run dedicated audit periodically):

1. **DirectorIntent.stance — REGRESSED+FIXED.** `_emit_micromove_fallback` at `agents/studio_compositor/director_loop.py` was constructing `DirectorIntent` without required `stance` field. Shipped `68cb2b9fa` ("fix(compositor): _emit_micromove_fallback DirectorIntent stance — silent no-op"). **Class-of-error:** Pydantic BaseModel field added later, construction sites not all updated. Operator should consider lint rule (`pydantic-required-field-checker`) or wider grep at field-add time. Verified via `git log --oneline -50`.
2. **WSJF §6/§8 stale state.** WSJF doc internal cross-refs (§5 NEEDS_CLARIFICATION) still describe D-05/D-12/D-16 as needing operator answers; §10 RESOLVED makes these moot per operator's "make best decision and unblock yourself" directive. The §5 and §10 sections are mutually contradictory if read top-down; only the §3 master table state column is authoritative. **Risk:** an agent reading §5 first may re-ask resolved questions. Recommend a single "STATE-AUTHORITATIVE: §3 master table" header at WSJF top.
3. **D-09 closed but BLOCKED queue still names it.** WSJF §7 lists D-09 in BLOCKED table; §3 marks D-09 CLOSED per §10.5. Drift internal to WSJF doc.
4. **`programme=None` Phase 5 stub — RESOLVED.** `shared/affordance_pipeline.py:434` was hard-coded `programme=None`; D-26 shipped `866b66499` to wire active-programme lookup. **Class-of-error:** explicit TODO stub in production code. No new instances found in sample-grep of `affordance_pipeline.py` and `director_loop.py` (both clean of TODO/FIXME/XXX).
5. **DEMONET-PLAN §0.1 path — RESOLVED.** D-22 shipped `50251d8fe` to align plan path (`~/hapax-state/programmes/egress-audit/<date>/<hour>.jsonl`) to actual flat-path writer. Drift class: spec-vs-code path divergence introduced when writer was simplified post-spec.

**Stale TODOs:** Sample-grep of `shared/affordance_pipeline.py` + `agents/studio_compositor/director_loop.py` returned 0 TODO/FIXME/XXX matches — clean. Wider sweep (5 dirs sampled) deferred to caveat (§6).

---

## §5. Recommended unification actions

Prioritized:

1. **(P0) File the CC-task Obsidian SSOT plan doc** (NEW-2 in §3). This is the structural fix for the entire near-miss class. Per spec, ~9h focused work; one PR. It addresses systemic misses #1 + #3 in one shot.
2. **(P0) Allocate D-NN slots to existing-but-invisible plans:**
   - `2026-04-20-programme-layer-plan.md` (task #164) — content programming meso layer, 12 phases, NO D-NN today
   - `2026-04-20-orphan-ward-producers-plan.md` — FINDING-V mitigation, NO D-NN
   - `2026-04-20-demonetization-safety-plan.md` Phase 5+6 (already done via D-26/D-27 but plan should be marked SHIPPED)
   - `2026-04-19-homage-completion-plan.md` — confirm SHIPPED state matches current commits
3. **(P1) Author HOMAGE-SCRIM unified epic plan** (delta MISS #1) — covers HOMAGE-SCRIM 1–6 + nebulous-scrim-design + homage-ward-umbrella-design + OQ-02 three-bound governance. Single epic reduces 9 docs to one tracked workstream.
4. **(P1) Create "skeleton-then-defer" governance spec** (NEW-6) — codifies "every new module ships with ≥1 production caller in same PR or is tagged WIP." Prevents D-17/D-18 recurrence class.
5. **(P1) Sweep 8 unplanned 2026-04-18 specs** (NEW-10) — short triage pass; for each: supersede, plan-stub, or reference-only tag. Should take ≤30 min.
6. **(P2) Add reverse-mapping doc** (`docs/superpowers/queue-index.md` — generated): list every plan + spec + research-doc with its WSJF/OQ slot or "unallocated" tag. Low effort if generated by script. Eliminates the visibility-mismatch class permanently. Could be a deliverable of the CC-task Obsidian SSOT plan.
7. **(P2) Clarify SRCE acronym** (delta MISS #6) — strongest hypothesis is **Source Registry Completion Epic** (`2026-04-13-reverie-source-registry-completion-design.md` + plan), per NEW-5. Confirm with operator; if confirmed, close MISS #6 with that mapping + add OQ-03-after-SRCE follow-on note (NEW-5).
8. **(P2) Triage FINDING-X (constitutional violation)** (NEW-11) — grounding_provenance 99.5% empty per alpha.yaml :767. Should not float as residue.
9. **(P3) Add "STATE-AUTHORITATIVE: §3 master table" header to WSJF doc** + delete §5 / §7 stale references. ≤10 min cleanup.

---

## §6. Confidence + caveats

**Confidence: MEDIUM-HIGH for stated counts; MEDIUM for completeness.**

**What I did NOT get to (operator should verify or run follow-up):**

- Did NOT scan all 292 research docs / 212 specs / 183 plans — sampled latest 30 of each by mtime. There are likely 20–40 additional misses in the older long tail (especially specs from 2026-04-12 → 2026-04-17 spec-burst window).
- Did NOT exhaustive-grep for TODO/FIXME/XXX across the full codebase — sampled 2 strategic files only. Stale TODOs >30 days old are a real risk class but not enumerated here.
- Did NOT check beta-zone queue items separately (e.g., `beta.yaml` queue: #225, #226, #228, #240 referenced in commits). Beta has its own workstream visible only via commit messages.
- Did NOT validate every "SHIPPED" claim in WSJF §3 against `git log` (only spot-checked 5).
- Did NOT verify Pi-edge / Pi-fleet items separately — `recommended_fix_order_for_delta` items 6 (Pi NoIR fleet recovery) and adjacent are partially scoped in alpha.yaml but not in WSJF.
- Did NOT search hapax-officium / hapax-mcp / hapax-watch / hapax-phone / atlas-voice-training / tabbyAPI workspaces — out of council scope but the operator's "total workstream" may extend cross-repo.
- Did NOT confirm whether `2026-04-15-lrr-phase-8-content-programming-via-objectives-plan.md` (LRR Phase 8) is fully shipped and superseded-by-or-coexists-with the newer `2026-04-20-programme-layer-plan.md`. If both are live, NEW-1 may double-count.

**Where alpha should verify manually:**

- Run `grep -l "task #" docs/` to enumerate every `task #NN` reference and cross-check against any active task-tracker.
- Run `gh pr list --state merged --since 2026-04-15` and reconcile against WSJF SHIPPED claims.
- Confirm SRCE = Source Registry Completion Epic with operator (delta MISS #6 + NEW-5).
- Read full content of WSJF §5 + §7 + §10 to decide which sections to delete vs. keep historical.
- Decide whether NEW-10 (8 unplanned specs from 2026-04-18) should be triaged in one batch or rolled into the per-spec retroactive sweep.

**Time accounting:** 7 minutes 40 seconds of actual work (within ≤8-min budget). Sources scanned: 5 directories at ls-mtime depth, 4 strategic files read in full, 5 strategic greps, 1 PR/issue list, 1 commit log. No subagents dispatched.

---

*End of total workstream gap audit. Companion to `~/.cache/hapax/relay/delta-to-alpha-workstream-gap-audit-20260420.md` — read both for full picture. The 6 delta misses + 11 net-new misses here = **17 total misses**; the 3 systemic patterns in §1 explain why the misses recur and what structural fix (CC-task SSOT) closes them.*
