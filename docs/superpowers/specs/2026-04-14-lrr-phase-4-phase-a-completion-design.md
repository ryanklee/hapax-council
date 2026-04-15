# LRR Phase 4 — Phase A Completion + OSF Pre-Registration (design)

**Date:** 2026-04-14 CDT
**Author:** beta (pre-staged during LRR Phase 4 bootstrap; operator ratifies at phase open)
**Parent epic spec:** `docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md` §Phase 4
**DEVIATION authority for frozen-file edits:** `research/protocols/deviations/DEVIATION-038.md`
**Status:** DRAFT — spec and engineering bootstrap pre-staged on `beta-phase-4-bootstrap` branch; awaiting operator review before marked ready.

---

## 0. Context

Phase 4 locks the Condition A control arm of the LRR voice grounding experiment before Phase 5 swaps the substrate from Qwen3.5-9B to Hermes 3 70B. The livestream-only rule (operator directive 2026-04-14) means Phase 4 runs as two sequential blocks:

1. **Engineering bootstrap** (scope items 1–4) — small, engineering-gated, closable in 1–2 sessions. Pre-staged by beta on branch `beta-phase-4-bootstrap` as PR #819.
2. **Livestream-run-gated collection window** (scope items 5–8) — runs in parallel with Phase 5 preparation. Collection throughput is determined by stream hours × active-condition tag coverage, not by operator session cadence.

This spec expands the 8-item scope from the epic spec into operational detail, covers design decisions and trade-offs, specifies verification procedures, and captures open questions for operator review. The epic spec is authoritative for goal + dependency + gating model; this spec is authoritative for procedural detail.

---

## 1. Goal (recap)

Lock the Condition A control arm under the livestream-only rule. Ship the engineering that makes voice-pipeline grounding DVs attributable to a research condition. Retire the pre-LRR dedicated-session data via DEVIATION. File the OSF pre-registration. Reach the ready-to-swap state for Phase 5.

---

## 2. Prerequisites

| Prereq | Status as of 2026-04-14 22:30 CDT | Notes |
|---|---|---|
| Phase 1 research registry | ✅ merged | `~/hapax-state/research-registry/` with `cond-phase-a-baseline-qwen-001` present |
| Phase 1 research marker SHM | ✅ wired | Written by `scripts/research-registry.py` on init/open/close |
| Phase 1 frozen-file pre-commit hook | ✅ active | `check-frozen-files.py` enforces `condition.yaml::frozen_files` |
| Phase 2 HLS archive rotation | ✅ merged | Condition-tagged segments flow into `~/hapax-state/stream-archive/hls/` |
| Phase 3 runtime partition α→γ | ⏸ pending | PR #811 merged; runtime activation requires `install-units.sh` + service restart (operator-scheduled) |
| Hermes 3 70B EXL3 quant | ⏸ in flight | 3.0bpw done (`~/projects/tabbyAPI/models/Hermes-3-Llama-3.1-70B-EXL3-3.0bpw/`, 27 GB); 3.5bpw running at layer 0 as of beta pre-staging |
| Sprint 0 G3 gate | ⏸ BLOCKING | "Measure 7.2 Run Claim 5 correlation analysis" blocks further Bayesian progression — see §9 |

Phase 4's engineering bootstrap (items 1–4) is **unblocked by Phase 3 runtime activation**. The collection window (items 5–8) is **blocked by G3 + runtime partition**, not by Phase 5 quant completion.

---

## 3. Scope

### 3.1 Item 1 — `shared/research_marker.py` hoist + voice-pipeline condition_id plumbing

**Pre-staged on branch.** Shipped in commits `3d9be7da9` (module + tests) and `faad34e16` (condition_id plumbing through `conversation_pipeline.py` + `grounding_evaluator.py`).

**Design decision:** extend `hapax_score(...)` and `hapax_bool_score(...)` in `agents/_telemetry.py` to accept an optional `metadata: dict | None = None` kwarg rather than using the trace-level metadata alone. Rationale:

- **Score-level attribution is stronger than trace-level.** Langfuse's query API can filter scores directly by `metadata.condition_id` without needing a two-step trace-then-score lookup.
- **Forward-compatible.** The extension is non-breaking — all existing callers default to no metadata and work unchanged.
- **Fail-safe.** If Langfuse SDK version doesn't accept the kwarg, the existing try/except silently drops the score (same contract as any other Langfuse issue).

**Verification path (for review):**

1. Open an active research condition via `scripts/research-registry.py open phase-a-test-stream` (creates `cond-phase-a-test-stream-NNN`).
2. Start the livestream in research mode.
3. Operator speaks into the voice pipeline on stream.
4. Query Langfuse: `langfuse_client.get_scores(name="turn_pair_coherence", metadata_filter={"condition_id": "cond-phase-a-test-stream-NNN"})`.
5. Expect at least one score returned.
6. Close the test condition: `scripts/research-registry.py close cond-phase-a-test-stream-NNN`.

**Rollback:** the engineering bootstrap commits can be reverted atomically. The metadata kwargs are purely additive; reverting leaves `hapax_score(...)` callers unchanged.

### 3.2 Item 2 — `DEVIATION-038.md` filing

**Pre-staged on branch.** Shipped in commits `b0e6fbb1a` (initial DEVIATION) + `cd7add804` (explicit frozen-file coverage list).

DEVIATION-038 bundles two effects into one filing because they share a single root (livestream-only rule adoption):

1. Retire pre-LRR Cycle 2 Phase A dedicated-session data (~431 grounding-act pairs from 2026-03-21/24/25) from Condition A sample counts. Data preserved in Langfuse; excluded by filtering on `metadata.condition_id`.
2. Authorize the three frozen-file edits required by item 1 and item 3: `grounding_evaluator.py`, `conversation_pipeline.py`, `CYCLE-2-PREREGISTRATION.md`.

Impact on validity: **MINIMAL**. Score values are bit-identical post-change; the metadata kwarg is pure analytical attribution.

### 3.3 Item 3 — `CYCLE-2-PREREGISTRATION.md` amendment

**Pre-staged on branch.** Shipped in commit `327aced57`.

Three surgical pre-filing edits:

- **§2.3 Phase Definitions** — declare that grounding experiment observations in Phases A / B / A' are collected exclusively during livestream runs in research mode. DEVIATION-038 referenced for pre-LRR pilot exclusion.
- **§3.2 Setting** — clarify data collection context as "livestream runs in research mode." Also correct the LLM routing reference from "Claude Opus 4.6" to "TabbyAPI (Qwen3.5-9B EXL3 for Phase A baseline; Hermes 3 70B EXL3 for the Phase 5 substrate swap target)."
- **§4.1 Implementation** — extend the implementation file list to include `grounding_evaluator.py`, `shared/research_marker.py`, `agents/studio_compositor/director_loop.py`, and the SHM marker file.

**Experimental design untouched.** Claim, hypothesis, DVs, BEST analysis methodology, and ABA phase structure are not modified. Only data source and implementation sections are clarified.

**OSF filing is NOT authorized by DEVIATION-038** — that's scope item 4, pending operator sign-off.

### 3.4 Item 4 — OSF project creation + pre-registration filing

**Operator action. Not pre-stagable.**

Procedure:

1. Operator reviews the amended `CYCLE-2-PREREGISTRATION.md` (from item 3) for factual correctness.
2. Operator creates OSF project for `claim-shaikh-sft-vs-dpo`.
3. Operator uploads the amended pre-registration document.
4. Operator generates the OSF pre-registration URL.
5. `research-registry/cond-phase-a-baseline-qwen-001/condition.yaml` is updated with:
   ```yaml
   osf_project_id: "XXXX-YYYY"
   pre_registration:
     url: "https://osf.io/XXXX/"
     filed_at: "2026-MM-DDTHH:MM:SSZ"
     document_sha256: "<hash of the amended CYCLE-2-PREREGISTRATION.md>"
   ```
6. The updated `condition.yaml` is committed alongside DEVIATION-038 in a single commit so the paper trail is atomic.

**OSF filing is one-way.** Once filed, the claim is public. Operator sign-off required. If the operator later wants to revise, OSF supports post-registration amendments but the original filing remains visible.

**Cross-reference:** `research/protocols/osf-project-creation.md` (Phase 1 PR #2 committed the procedure; LRR Phase 4 executes it).

### 3.5 Item 5 — Livestream-run-gated control arm collection

**With items 1–4 shipped, this is the "just let the livestream run" phase.**

The livestream runs in research mode with `research-registry current` = `cond-phase-a-baseline-qwen-001`. Every director_loop reaction is automatically tagged (Phase 1 infrastructure). Every voice grounding DV is automatically tagged (item 1 infrastructure). Collection throughput = stream hours × coverage.

**Sample target (open question for operator — see §9):** hybrid of

- ≥**N stream director reactions** tagged with `cond-phase-a-baseline-qwen-001` in the `stream-reactions` Qdrant collection AND in `~/hapax-state/stream-archive/hls/*/reactor-log-YYYY-MM.jsonl`.
- ≥**M voice grounding DVs** in Langfuse with `metadata.condition_id=cond-phase-a-baseline-qwen-001` covering `turn_pair_coherence`, `context_anchor_success`, `activation_score`, `acceptance_type`, and `sentinel_retrieval`.

**Defensible starting floors (operator may override):**

| Unit | Floor | Rationale |
|---|---|---|
| N (stream reactions) | 500 | Roughly 5 hours of stream at the current director_loop cadence (~100 reactions/hour). Leaves room for 50%+ noise filtering if needed. |
| M (voice grounding DVs per DV name) | 50 | Matches Cycle 1 pilot minimum sample for BEST two-group comparison with 80% power at d=0.5. 50 per DV name × 5 DVs = 250 scores total. |

These are starting floors; the operator should review against the pre-registered statistical-power commitment at Phase 4 open and adjust up or down before collection starts. **Do not start collection with ambiguous targets** — the `collection_halt_at` marker needs a deterministic trigger.

### 3.6 Item 6 — Continuous mid-collection integrity checks

Run every **N=100 reactions** (adjustable):

| Check | Command | Expected result |
|---|---|---|
| `research-registry current` unchanged | `scripts/research-registry.py current` | `cond-phase-a-baseline-qwen-001` |
| No frozen-file diffs | `scripts/check-frozen-files.py` (against staged changes) | exit 0 |
| Qdrant reaction count monotonically growing | `qdrant query count stream-reactions filter condition_id=cond-phase-a-baseline-qwen-001` | strictly greater than previous check |
| Langfuse score count monotonically growing | `langfuse_client.get_scores(metadata_filter={"condition_id": ...})` count | strictly greater than previous check |
| Split between channels stable | compare stream-director obs count vs voice-grounding obs count | neither channel stalls for >30 min while the other advances |

**Automation target:** a script `scripts/check-phase-a-integrity.py` that runs the 5 checks and exits non-zero on any anomaly. Intended for a systemd timer (15-min cadence) during the active collection window. **Not pre-staged by beta** — alpha or a Phase 4 engineering session implements it.

**Anomaly response:**

- `research-registry current` drifted → operator halts collection, investigates the unexpected open/close, potentially opens a new condition and restarts the window.
- Frozen-file diff detected → commit is rejected by the pre-commit hook already; check-phase-a-integrity.py flags if a diff exists on disk even without a commit attempt.
- Channel stall (one channel growing, other stalled) → likely a wiring regression; operator investigates with journalctl + the relevant test suite.

### 3.7 Item 7 — Data integrity lock at completion

When both sample target floors are met, the collection is **sealed** via three exports:

1. **JSONL checksums:** `sha256sum` on every `reactor-log-YYYY-MM.jsonl` file that has entries tagged with `cond-phase-a-baseline-qwen-001`. Record in `research-registry/cond-phase-a-baseline-qwen-001/data-checksums.txt`.
2. **Qdrant snapshot:** export all `stream-reactions` Qdrant points with `condition_id=cond-phase-a-baseline-qwen-001` to a tar.gz archive at `~/hapax-state/research-registry/cond-phase-a-baseline-qwen-001/qdrant-snapshot.tgz`. Include a top-level `manifest.json` with snapshot timestamp, point count, and Qdrant schema version. sha256 of the tarball appended to `data-checksums.txt`.
3. **Langfuse score export:** query all scores with `metadata.condition_id=cond-phase-a-baseline-qwen-001` and dump to `~/hapax-state/research-registry/cond-phase-a-baseline-qwen-001/langfuse-scores.jsonl`. One JSON line per score. sha256 appended to `data-checksums.txt`.

**This third export is new vs the original Phase 4 spec.** Omitting it would leave the voice-grounding DV half of Condition A analytically unreachable after the Phase 5 swap — Condition A and Condition A' would be compared only on stream-director reaction metrics, not on the pre-registered voice grounding DVs. The whole point of the item 1 condition_id plumbing is to make this export possible.

**Automation target:** a script `scripts/lock-phase-a-condition.py` that performs all three exports + writes `data-checksums.txt` atomically. Not pre-staged by beta — alpha or a Phase 4 engineering session implements it. Outline:

```python
def lock_condition(condition_id: str) -> None:
    # 1. JSONL checksums
    jsonl_files = glob("~/hapax-state/stream-archive/hls/*/reactor-log-*.jsonl")
    checksums = {f: sha256_of(f) for f in jsonl_files if contains_condition(f, condition_id)}

    # 2. Qdrant export
    qdrant_path = f"~/hapax-state/research-registry/{condition_id}/qdrant-snapshot.tgz"
    export_qdrant_points("stream-reactions", filter_condition_id=condition_id, dest=qdrant_path)
    checksums[qdrant_path] = sha256_of(qdrant_path)

    # 3. Langfuse score export
    lf_path = f"~/hapax-state/research-registry/{condition_id}/langfuse-scores.jsonl"
    export_langfuse_scores(metadata_filter={"condition_id": condition_id}, dest=lf_path)
    checksums[lf_path] = sha256_of(lf_path)

    # Atomic write of checksum manifest
    atomic_write_json(checksums, f"~/hapax-state/research-registry/{condition_id}/data-checksums.txt")
```

### 3.8 Item 8 — `collection_halt_at` marker

When item 7's integrity lock completes, write the halt marker:

```bash
yq -i '.collection_halt_at = "'"$(date -Iseconds)"'"' \
  ~/hapax-state/research-registry/cond-phase-a-baseline-qwen-001/condition.yaml
```

Per the append-only research registry model (P-3 in the epic spec), **conditions never close** — they get a `collection_halt_at` marker instead. Condition A remains queryable, comparable, and referenceable indefinitely.

Following the halt marker, Phase 5 pre-swap checks can begin. The Phase 5 spec's pre-swap check 1 now reads: "Phase 4 complete (Condition A locked, checksums, Qdrant snapshot, **Langfuse score export per Phase 4 scope item 7**)."

---

## 4. Design decisions summary

| Decision | Value | Rationale |
|---|---|---|
| Metadata attribution granularity | Score-level (not trace-level) | Stronger post-hoc filtering; forward-compatible with Langfuse query API |
| `hapax_score` signature change | Optional `metadata` kwarg | Non-breaking; all existing callers work unchanged |
| Condition reader location | `shared/research_marker.py` (hoisted from `director_loop.py`) | Both livestream director and voice pipeline depend on single implementation |
| Cache TTL | 5 seconds (matches original) | Livestream reactions become condition-aware within 5 s of `research-registry open` |
| Failure mode | Silent `None` on any error | Matches director_loop's existing fail-safe semantic |
| Sample target unit | Hybrid (stream reactions + voice DVs) | Protects against channel-specific droughts |
| Pre-LRR data disposition | Retire via DEVIATION-038, preserve in Langfuse | Analytical exclusion, not deletion |
| Pre-reg filing | Operator action, post-review | One-way, requires sign-off |
| Collection integrity lock | Three exports (JSONL + Qdrant + Langfuse) | Voice grounding DV channel must be analytically reachable post-swap |

---

## 5. Exit criteria

From the epic spec Phase 4 section, expanded with specific verification paths:

- [ ] `shared/research_marker.py` exists; imported by `conversation_pipeline.py` + `grounding_evaluator.py`. **Verify:** `grep -l "shared.research_marker" agents/hapax_daimonion/` returns both files.
- [ ] Stream-mode voice utterance produces Langfuse scores with `metadata.condition_id=<active>`. **Verify:** live end-to-end test from §3.1.
- [ ] `research/protocols/deviations/DEVIATION-038.md` committed. **Verify:** file exists on main.
- [ ] `CYCLE-2-PREREGISTRATION.md` amended (§2.3, §3.2, §4.1). **Verify:** `grep -c "livestream-only rule" agents/hapax_daimonion/proofs/CYCLE-2-PREREGISTRATION.md` returns ≥1.
- [ ] OSF project created; pre-reg uploaded; URL + sha256 recorded in `condition.yaml`. **Verify:** `yq '.osf_project_id, .pre_registration' condition.yaml` returns non-null.
- [ ] Sample targets met. **Verify:** see §3.5 thresholds.
- [ ] No frozen-file diffs beyond DEVIATION-038. **Verify:** `scripts/check-frozen-files.py` exit 0 on clean worktree.
- [ ] Three exports captured (JSONL + Qdrant + Langfuse). **Verify:** `ls ~/hapax-state/research-registry/cond-phase-a-baseline-qwen-001/data-checksums.txt qdrant-snapshot.tgz langfuse-scores.jsonl` — all three files exist with sha256 in checksums file.
- [ ] `research-registry current` still `cond-phase-a-baseline-qwen-001` with `collection_halt_at` marked. **Verify:** `yq '.collection_halt_at' condition.yaml` non-null.
- [ ] `RESEARCH-STATE.md` updated: "Phase A Complete (livestream-only baseline under Qwen3.5-9B); Condition A locked pending Phase 5 swap." **Verify:** new dated entry at top of file.

---

## 6. Risks + mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Livestream hours insufficient for sample target within operator's desired calendar window | Medium | Medium | Co-specify realistic target at phase open; extend collection window if needed. Engineering bootstrap unblocked. |
| Frozen-file pre-commit hook blocks a legitimate non-DEVIATION change | Low | Low | DEVIATION-038 covers the three files needed for the bootstrap; any other frozen-file touch during collection is a real regression and should block correctly. |
| Langfuse SDK version rejects metadata kwarg on `span.score()` | Low | Medium | `hapax_score` catches the exception; score is silently dropped (same fail-safe as other Langfuse failures). Monitor for regression via test_research_marker + test_grounding_evaluator on first CI run. |
| Stream-director observations and voice grounding DVs diverge (one channel stalls) | Medium | Low | Integrity check item 6 catches this; mitigation is operator investigation (likely a wiring regression). Both channels have independent sample floors. |
| OSF filing reveals pre-reg text issue post-amendment, post-filing | Medium | Low | Operator sign-off required before filing. If post-filing issue surfaces, OSF supports amendments with original filing visible. |
| Pre-LRR dedicated-session data resurfaces in analysis by accident | Low | Low | Every Phase A query filters on `metadata.condition_id=cond-phase-a-baseline-qwen-001`; pre-LRR scores lack the field entirely. Cannot cross-contaminate. |
| Sprint 0 G3 gate blocks Phase 4 collection indefinitely | High | Medium | See §9 open questions; Option 1 resolves inside LRR (default), Option 2 defers G3 to a non-LRR session. |
| Beta's Phase 4 bootstrap commits conflict with alpha's in-flight compositor work | Low | Low | Beta works in `hapax-council--beta/` worktree on `beta-phase-4-bootstrap` branch; alpha's `fix/drops-42-43-*` branches are disjoint file-scope (compositor code vs voice pipeline). No overlap observed at pass-5 audit time. |

---

## 7. Rollback

**Engineering bootstrap (items 1–4):** atomic git revert. The bootstrap commits are all on `beta-phase-4-bootstrap` branch. If the PR is not yet merged, the branch can be discarded. If merged, a revert PR restores the pre-bootstrap state. The metadata kwargs are additive; reverting leaves all callers unchanged.

**DEVIATION-038:** not revert-able in the normal sense — a DEVIATION is a permanent research record. If the operator later wants to un-retire the pre-LRR pilot data, the correct path is a new DEVIATION that formally re-admits the data to a Phase A-prime sample (a separate claim/condition, not a re-write of DEVIATION-038).

**Pre-registration amendment:** reversible via a new amendment pre-filing. Post-filing reversals require OSF's amendment workflow with history visible.

**Collection window (items 5–8):** if the window is interrupted (e.g., compositor failure, unexpected frozen-file edit, sample target miscalibration), the operator closes the current condition (`research-registry close cond-phase-a-baseline-qwen-001`) and opens a new one (e.g., `cond-phase-a-baseline-qwen-002`). Data already collected under the original ID remains tagged to the original ID; analysis scripts filter by the specific condition they need.

**Collection window rollback is lossless** because the append-only research registry model guarantees that collected data is never deleted. The only "undo" available is to pivot to a new condition.

---

## 8. Test plan

**Pre-merge (this PR):**

- [x] `uv run pytest tests/test_research_marker.py` — 16/16 pass
- [x] `uv run pytest tests/hapax_daimonion/test_grounding_ledger.py tests/hapax_daimonion/test_grounding_bridge.py tests/test_telemetry.py` — 72/72 pass
- [x] `uv run ruff check` + `ruff format` on all touched files — clean
- [x] `uv run pyright` on all touched files — 0 errors
- [ ] CI: full test suite green (awaiting push)

**Post-merge (Phase 4 open):**

- [ ] Open a test research condition via `research-registry.py open phase-a-test-stream`
- [ ] Start the livestream in research mode
- [ ] Operator speaks into the voice pipeline on stream (5+ utterances)
- [ ] Verify Langfuse scores for the test condition: `get_scores(metadata_filter={"condition_id": "cond-phase-a-test-stream-NNN"})` returns ≥5 scores per DV name
- [ ] Verify stream-reactions Qdrant count for the test condition
- [ ] Close the test condition via `research-registry.py close cond-phase-a-test-stream-NNN`
- [ ] Verify the real condition (`cond-phase-a-baseline-qwen-001`) is still active after the test close

**Collection window monitoring:**

- [ ] `scripts/check-phase-a-integrity.py` runs every 15 min via systemd timer (once implemented)
- [ ] Prometheus alert on integrity check failure
- [ ] Operator dashboard shows running sample count per channel

---

## 9. Open questions for operator review

1. **Sample target calibration.** §3.5 proposes N=500 stream reactions + M=50 per DV. Adjust against the pre-registered power commitment in the amended `CYCLE-2-PREREGISTRATION.md` §6 Sample Size. Operator ratifies at phase open.

2. **Sprint 0 G3 gate resolution.** The epic spec offers two options:
   - **Option 1 (resolve inside LRR):** Phase 4 opens with a G3 resolution step, executes the pending Measure 7.2 Claim 5 correlation analysis, closes the gate, resumes Phase A.
   - **Option 2 (resolve outside LRR):** Phase 4 waits until G3 is resolved in a separate Bayesian-schedule session.
   - **Default recommendation: Option 1.** Operator chooses at phase open.

3. **OSF project naming.** `claim-shaikh-sft-vs-dpo` is the internal claim ID. Does the OSF project use the same ID, a longer human-readable name, or a title drawn from the pre-reg §1.1? Operator decides at filing time.

4. **Collection window termination.** If the operator runs the livestream for (say) 20 hours without hitting the sample target, should Phase 4 extend the window or reduce the target? This is a statistical power trade-off — don't decide reactively.

5. **`scripts/check-phase-a-integrity.py` + `scripts/lock-phase-a-condition.py` implementation.** Both outlined in §3.6 and §3.7; neither is pre-staged by beta. Alpha or a Phase 4 engineering session owns these.

6. **Phase 4 engineering bootstrap PR strategy.** Beta has pre-staged commits on `beta-phase-4-bootstrap` as draft PR #819. At Phase 4 open, does alpha review-and-merge directly, or bundle with a Phase 4 operational-tooling PR (items 6.7 above)? Operator call.

---

## 10. References

- **Parent epic spec:** `docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md` §Phase 4
- **LRR state document:** `agents/hapax_daimonion/proofs/RESEARCH-STATE.md` §2026-04-14 LRR Phase 4 re-spec entry (beta pre-staged this session)
- **DEVIATION authority:** `research/protocols/deviations/DEVIATION-038.md`
- **OSF project creation procedure:** `research/protocols/osf-project-creation.md` (Phase 1 PR #2)
- **Hermes 3 migration plan:** `docs/superpowers/plans/2026-04-10-hermes3-70b-migration.md` §8 (baseline completion recommendation)
- **Hermes 3 voice architecture:** `docs/superpowers/specs/2026-04-10-hermes3-70b-voice-architecture-design.md`
- **Beta audit trajectory (cumulative through pass 5):**
  - `~/.cache/hapax/relay/context/2026-04-14-beta-lrr-audit-pass-5.md`
  - `~/.cache/hapax/relay/context/2026-04-14-beta-lrr-phase-4-respec-livestream-only.md`
- **Beta → delta cross-session ack:** `~/.cache/hapax/relay/inflections/20260414-224500-beta-delta-ack-phase-4-bootstrap-progress.md`

— beta
