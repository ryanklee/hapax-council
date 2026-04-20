# Delta WSJF Reorganization — 2026-04-20

**Author:** delta (post-VRAM-incident triage cycle)
**Date:** 2026-04-20
**Audience:** next delta session (entry point)
**Register:** Engineering prioritization decision; concise; cite-or-it-didn't-happen.
**Source documents (all citations resolve to these):**

- `docs/superpowers/handoff/2026-04-20-delta-pre-compaction-commitments.md` (PRE-COMPACT)
- `docs/research/2026-04-20-delta-queue-flow-organization.md` (FLOW)
- `docs/superpowers/research-to-plan-triage-2026-04-20.md` (TRIAGE)
- `docs/superpowers/handoff/2026-04-20-delta-queue-cleared-handoff.md` (CAPSTONE)
- `docs/superpowers/handoff/2026-04-20-delta-l6-retargets-operator-runbook.md` (L6-RUNBOOK)
- `docs/superpowers/plans/2026-04-20-demonetization-safety-plan.md` (DEMONET-PLAN)
- `~/.cache/hapax/relay/delta.yaml` (DELTA-YAML; refreshed 2026-04-20T15:13Z post-VRAM-fix)
- `~/.cache/hapax/relay/delta-to-alpha-research-triage-20260420.md` (TRIAGE-RELAY)
- `~/.cache/hapax/relay/delta-to-alpha-rag-ingest-livestream-optimization-20260420.md` (RAG-RESEARCH)
- `docs/research/2026-04-20-six-hour-audit.md` (AUDIT) — woven 2026-04-20 d33be1a6e+ pass; produced D-17 through D-24

---

## §1. TL;DR

**Top 5 by WSJF (highest score = ship first):**

| Rank | Item | WSJF | State |
|---|---|---|---|
| 1 | Cross-zone PR review pickup for #197/#198 (alpha consumer side) | **17.0** | READY |
| 2 | Investigate operator-reported livestream regressions (standing readiness) | **13.0** | READY |
| 3 | Audit doc/spec-drift bundle (3 fixes; AUDIT §4.2 + §6.2 + §11.2) | **11.0** | READY |
| 4 | Audio-topology Phase 5 verifier sweep against current live graph | **8.0** | READY |
| 5 | L6 retargets apply (5 configs) | **7.6** | BLOCKED-operator |

**Ship-readiness distribution (24 items):**

- **READY:** 12 (queue-runnable now without operator input — 4 original + 8 audit-derived)
- **NEEDS_CLARIFICATION:** 3 (one-question sharpening unblocks)
- **NEEDS_RESEARCH:** 2 (research dispatch required first)
- **BLOCKED:** 7 (operator decision/hardware/peer-agent)

**Headline:** delta exited the prior session with the queue genuinely cleared (CAPSTONE §1 lines 11–33 lists 35 ships; PRE-COMPACT §3 line 50 confirms working-tree clean on `main`). The VRAM emergency closed cleanly (`8816040eb` shipped per DELTA-YAML lines 20–28; rag-ingest now drip-only inotify, 370 MB RSS, zero GPU). The 2026-04-20 six-hour audit (commit `d33be1a6e`) surfaced 14 net-new actionable findings (HIGH ×2, MEDIUM ×6 clustered, LOW ×11 bundled). The 3 most-urgent audit findings (speech_lexicon WIP, rag-ingest handoff doc, and Ring 2 Phase 1 commit) were resolved out-of-band by alpha (`9fad053b5`, `f89012131`, `d6a4d4753`); the residue is woven below as D-17 through D-24. Remaining work is dominated by (a) wiring two truly-dead governance modules (`quiet_frame`, `music_policy`) into production callers, and (b) a fast spec/doc-drift cleanup bundle that ranks #3 by WSJF.

---

## §2. Methodology

### §2.1 WSJF rubric

`WSJF = (Business Value + Time Criticality + Risk Reduction) / Job Size`

Components scored on Fibonacci-like 1-3-5-8-13. Source: `feedback_systematic_plans` (workspace MEMORY index) + standard SAFe WSJF.

| Dim | 13 | 8 | 5 | 3 | 1 |
|---|---|---|---|---|---|
| **Business Value** | unblocks operator's most-named gate | improves broadcast quality / workflow significantly | improves delta-zone subsystem | optimization / observability | nice-to-have |
| **Time Criticality** | go-live blocker decaying daily | stream-affecting, decays days | quality compounding weeks | decoupled | research-only |
| **Risk Reduction** | unblocks ≥3 downstream / fixes recurring failure | unblocks 1-2 items | enables future capability | isolated improvement | none |
| **Job Size** | 1=≤30min, 3=~1hr, 5=2-4hr, 8=4-8hr, 13=multi-day |

### §2.2 Spec-readiness states

- **READY:** acceptance criteria + named files + test plan exist; agent could ship without asking
- **NEEDS_CLARIFICATION:** direction clear; one operator/peer question unblocks
- **NEEDS_RESEARCH:** no spec yet; needs research dispatch first
- **BLOCKED:** waiting on operator decision, hardware, or peer agent (not a delta-side problem)

### §2.3 Sources scanned

PRE-COMPACT §4–§9 (in-flight, queued, operator-gated, shipped-with-followup); FLOW §3.1–§4.4 (dependency graph + size estimates); TRIAGE §1 + §3 (delta-zone unqueued); CAPSTONE §3–§5 (#202 pickup spec); DELTA-YAML lines 51–66 (`operator_gated_items_prescope` + `next_delta_session_priorities`); TRIAGE-RELAY lines 27–45 (alpha-zone gap list, adjacent for cross-zone scoring).

### §2.4 Anchor: operator's go-live gates

Per directive: Gate 1 monetization (delta-owned via #202), Gate 2 vinyl Mode D (shipped per FLOW §3 line 84), Gate 3 DEGRADATION (alpha-owned, shipped per directive). Gate 1 → Time Criticality 13 for any item directly advancing it.

---

## §3. Master scored table

Every remaining delta-zone item, scored. Sequenced by WSJF descending within each readiness state.

| ID | Item | Source | BV | TC | RR | JS | WSJF | State | Deps |
|---|---|---|---|---|---|---|---|---|---|
| **D-01** | Cross-zone PR review pickup for #197/#198 (alpha consumer side) | PRE-COMPACT §4.4 line 91; DELTA-YAML line 63; CAPSTONE §1 row #197+#198 | 8 | 13 | 13 | 2 | **17.0** | READY | alpha opens PR |
| **D-02** | Investigate operator-reported livestream regressions (standing readiness) | DELTA-YAML line 64; PRE-COMPACT §4.5 lines 97–102 | 13 | 13 | 13 | 3 | **13.0** | READY | operator surfaces issue |
| **D-03** | Audio-topology Phase 5 verify-sweep against current live graph | PRE-COMPACT §9.3 lines 232–240; FLOW §3 lines 88–94 | 5 | 5 | 5 | 2 | **8.0** | READY | none |
| **D-04** | L6 retargets apply (5 configs) | L6-RUNBOOK §1–§2; PRE-COMPACT §5.2 + §7 line 191; DELTA-YAML line 54 | 8 | 8 | 5 | 3 | **7.6** | BLOCKED-operator | Rode WP on ch 1 + AUX 1 confirm |
| **D-05** | #202 Ring 2 classifier Phase 1 (real per-SurfaceKind prompts + 500-sample bench) | CAPSTONE §3 lines 58–145; PRE-COMPACT §4.2 lines 72–83; DELTA-YAML lines 45–50 | 13 | 13 | 8 | 8 | **5.4** | NEEDS_CLARIFICATION | 500-sample labels |
| **D-06** | LADSPA loudnorm operator-apply step | PRE-COMPACT §5.5 lines 136–138; DELTA-YAML line 58 | 5 | 5 | 3 | 3 | **4.3** | BLOCKED-operator | `cp` + pipewire restart |
| **D-07** | Vinyl-broadcast signal-chain software wiring | TRIAGE §1 row 10; FLOW §3.2 line 145; TRIAGE §3 row 36 | 5 | 5 | 3 | 5 | **2.6** | NEEDS_CLARIFICATION | which ch maps where |
| **D-08** | Audio-normalization-ducking-strategy plan stub | TRIAGE §1 row 8; FLOW §10.3 line 390 | 3 | 3 | 5 | 3 | **3.7** | NEEDS_RESEARCH | LADSPA topology survey |
| **D-09** | Music policy Path B runtime switch (operator chooses) | PRE-COMPACT §5.3 lines 128–130; DELTA-YAML line 56 | 3 | 3 | 1 | 1 | **7.0** | BLOCKED-operator | operator flips `policy.path=` |
| **D-10** | Evil Pet `.evl` SD card preset parser (Phase 1) | PRE-COMPACT §5.4 lines 132–134; DELTA-YAML line 57; FLOW §3 lines 109–113 | 3 | 3 | 3 | 5 | **1.8** | BLOCKED-operator | factory `.evl` file |
| **D-11** | Dual-FX Phase 6 (S-4 firmware activation) | PRE-COMPACT §9.4 lines 246–247; FLOW §6 line 240 | 5 | 3 | 3 | 5 | **2.2** | BLOCKED-operator | flash S-4 OS 2.1.4 |
| **D-12** | #202 Phase 2 (classifier-side opt-in negotiation) | PRE-COMPACT §5.1 lines 110–114; DEMONET-PLAN §3.1 | 8 | 8 | 5 | 5 | **4.2** | BLOCKED-peer | strict-serial-after Phase 1 |
| **D-13** | #202 Phase 3 (integrate verdict into `MonetizationRiskGate.assess()`) | PRE-COMPACT §5.1 line 113; DEMONET-PLAN §3.1 | 13 | 8 | 8 | 5 | **5.8** | BLOCKED-peer | strict-serial-after Phase 2 |
| **D-14** | #202 Phase 4 (classifier-degraded fail-closed integration tests) | PRE-COMPACT §5.1 line 114; CAPSTONE §3.what's-pre-wired item 1 | 8 | 5 | 5 | 3 | **6.0** | BLOCKED-peer | strict-serial-after Phase 3 |
| **D-15** | rag-ingest livestream-compatible redesign (followup to VRAM fix) | DELTA-YAML lines 30–38; RAG-RESEARCH (relay drop) | 8 | 5 | 8 | 8 | **2.6** | NEEDS_RESEARCH | alpha returns spec+plan |
| **D-16** | Ring 2 prompt design — per `SurfaceKind` (TTS / captions / overlay / ward) | CAPSTONE §3.scope bullets 1–5; DEMONET-PLAN research §6 ref | 8 | 8 | 5 | 5 | **4.2** | NEEDS_CLARIFICATION | per-surface false-positive tolerance |
| **D-17** | Wire `quiet_frame` into production caller (CLI `scripts/hapax-quiet-frame` + pre-monetization-window programmatic call) | AUDIT §7.1 (`shared/governance/quiet_frame.py` 0 callers); §11 remediation row 4 | 8 | 8 | 5 | 3 | **7.0** | READY | none |
| **D-18** | Wire `music_policy` into CPAL audio loop / compositor mute path | AUDIT §7.1 (`shared/governance/music_policy.py` 0 callers); §11 remediation rows 1–6 | 8 | 8 | 5 | 3 | **7.0** | READY | none |
| **D-19** | Concurrency hardening bundle: `_DEFAULT_WRITER` TOCTOU lazy-init + `MusicPolicy._path_b_window_opened_at` lock | AUDIT §8.1 (`monetization_egress_audit.py:201-205`); §8.2 (`music_policy.py:117-180`); §12.2 cross-cutting | 5 | 3 | 5 | 2 | **6.5** | READY | none |
| **D-20** | Crash-safety/atomic-write bundle: `ProgrammePlanStore` `.tmp` orphan cleanup + `quiet_frame` no-op `if/else` collapse + monotonic store-growth compact + `prune_old_archives` crash-safety | AUDIT §8.3 (`programme_store.py:189-196`); §10.1 (`quiet_frame.py:130-145`); §9.1 (`monetization_egress_audit.py` prune loop) | 5 | 3 | 5 | 3 | **4.3** | READY | none |
| **D-21** | Repo-vs-systemd state divergence: `scripts/hapax-systemd-reconcile.sh` to disable timers absent from `systemd/units/` (rag-ingest still `enabled` post-deletion) | AUDIT §8.4 (`systemctl --user list-unit-files \| grep rag-ingest` shows `linked enabled`) | 5 | 5 | 5 | 3 | **5.0** | READY | none |
| **D-22** | Spec/doc drift bundle (3 doc-only fixes): DEMONET-PLAN §0.1 path reconcile + DEMONET-PLAN §0.4 attribution update + workspace CLAUDE.md `Shared Infrastructure` rag-ingest GPU-isolated bullet | AUDIT §6.2 (path drift `programmes/egress-audit/<date>/<hour>.jsonl` vs flat); §4.2 + §5.2 (Path A unilateral resolution); §11.2 (CLAUDE.md doc-lag) | 5 | 3 | 3 | 1 | **11.0** | READY | none |
| **D-23** | Detector-exception fail-closed + egress-audit timer + Prometheus counters bundle: wrap `MusicPolicy.evaluate()` detector in try/except + ship daily rotate+prune timer for `monetization_egress_audit` + add `hapax_demonet_*` counters across 8 new modules + optional `audit_writer` param on `classify_with_fallback` | AUDIT §9.2 (detector exception unhandled); §7.2 (rotate/prune never fires); §11.1 (zero Prometheus across 8 modules); §11.5 (no audit hook in `classify_with_fallback`) | 5 | 5 | 3 | 3 | **4.3** | READY | none |
| **D-24** | Audit-cleanup bundle (LOW-severity catch-all, 11 items): `default_*` factory naming consistency (§6.1) + tests-location convention pass (§6.3) + promote `_redact_points` import-fail to raise (§8.5) + post-hoc-timeout docstring loud-warning (§8.6) + `unicodedata.normalize` in `verify_vinyl_chain` (§9.3) + `ProgrammePlanStore` size-threshold warning (§9.4) + `nan` propagation guard in `_loudness_to_band` (§10.3) + cold-start `verify_port` flag in `recall_preset` (§10.4) + extract `_BASE_SCENE` to shared constant (§11.3) + `hapax-audio-topology verify --profile vinyl` subcommand (§11.4) + Hypothesis property tests for `aggregate_mix_quality` + `_parse_verdict` (§11.6) | AUDIT §6.1, §6.3, §8.5, §8.6, §9.3, §9.4, §10.3, §10.4, §11.3, §11.4, §11.6 | 3 | 1 | 3 | 5 | **1.4** | READY | none |

**Score sanity check:** D-01 dominates because the body of work is tiny (review + maybe a clarifying patch) and it converts two already-shipped delta-side commits (`0dbaa1321` per CAPSTONE §1 row #197+#198) into deployed behavior. D-02 is high because *any* livestream regression is by definition gate-decay-affecting per `feedback_consent_latency_obligation` and `feedback_show_dont_tell_director` (memory index). D-05 (Ring 2 P1) is the heaviest standalone delta-shippable but the JS=8 divisor + the clarification gate keeps it below the small-ticket items. **D-22 lands at #3** because three coordinated documentation fixes (≤30 min total) eliminate ongoing reader-confusion at the spec/code/CLAUDE.md interface — high BV+TC over a JS=1 divisor produces a high WSJF. **D-17/D-18 tie at 7.0** with D-09 because wiring a shipped-but-dead governance module into a production caller is functionally equivalent to closing a Gate 1 sub-gap (per `feedback_grounding_exhaustive` memory: a module with 0 callers is indistinguishable from a dead bridge).

---

## §3.5 Audit-derived items (2026-04-20 d33be1a6e weave)

The 2026-04-20 six-hour audit (`docs/research/2026-04-20-six-hour-audit.md`, commit `d33be1a6e`) enumerated 25 findings across 8 axes (HIGH ×5, MEDIUM ×11, LOW ×9). This sub-section traces every audit finding to its disposition in the queue.

**Resolved out-of-band before weave (do not re-add):**

| Audit ref | Finding | Resolution commit |
|---|---|---|
| AUDIT §4.1 / §10.2 | Ring 2 Phase 1 uncommitted (4 files in working tree, including `ring2_classifier.py` modified-not-staged) | `d6a4d4753` (feat(demonet): Ring 2 Phase 1 — real per-surface LLM + 500-sample bench) |
| AUDIT §5.2 | Broken doc reference in `8816040eb` to missing rag-ingest handoff | `f89012131` (docs: backfill rag-ingest livestream-research handoff doc) |
| (operator WIP rescue, audit-adjacent) | speech_lexicon work-in-progress at risk of loss | `9fad053b5` (feat(speech): canonical pronunciation lexicon — operator WIP rescue) |
| AUDIT §5.1 | `eb1657358` capstone "queue cleared" claim under-delivered (now superseded by actual ship of D-05/D-13) | implicit; capstone narrative is historical |
| AUDIT §7.1 (ring2_classifier 0 callers) | Subset of dead-bridge finding | `896d8a52f` (feat(demonet): Ring 2 classifier integration into MonetizationRiskGate.assess()) |

**Newly-added items (D-17 through D-24):**

| New ID | Audit refs | Severity | Cluster type | Cross-zone? |
|---|---|---|---|---|
| D-17 | §7.1 (quiet_frame), §11 remediation row 4 | HIGH | individual (named module + named CLI fix) | no (delta governance zone) |
| D-18 | §7.1 (music_policy), §11 remediation rows 1–6 | HIGH | individual (named module + named call sites) | no (delta governance zone, but touches CPAL audio loop owned by alpha — flag for cross-zone review pre-merge) |
| D-19 | §8.1, §8.2, §12.2 | MEDIUM ×2 | concurrency theme (both are stateful-dataclass-without-lock variants of same anti-pattern) | no |
| D-20 | §8.3, §10.1, §9.1 | MEDIUM ×3 | crash-safety / state-cleanup theme (atomic-write window + monotonic state growth + transactional prune) | no |
| D-21 | §8.4 | MEDIUM | individual (systemd reconciler is a discrete new script) | no (delta sysadmin/governance overlap) |
| D-22 | §4.2, §6.2, §11.2 | MEDIUM ×3 | doc/spec drift theme (all three are documentation-only edits with no code change) | no (DEMONET-PLAN is delta-owned; workspace CLAUDE.md is shared but operator-decided edit) |
| D-23 | §7.2, §9.2, §11.1, §11.5 | MEDIUM ×4 | observability/robustness theme (all are "module shipped without operational instrumentation" variants) | no |
| D-24 | §6.1, §6.3, §8.5, §8.6, §9.3, §9.4, §10.3, §10.4, §11.3, §11.4, §11.6 | LOW ×11 | catch-all bundle (mechanical low-risk consistency / hardening / future-proofing; per WSJF guidance LOW items bundle into a single low-WSJF READY ticket) | no |

**Findings explicitly NOT promoted to queue items:**

| Audit ref | Reason |
|---|---|
| §12.1 (skeleton-then-defer anti-pattern) | Process-pattern observation, not a queue item; recorded here as a delta-self-discipline note. The fix is "future skeletons must include at least one production caller" — addressed structurally by D-17 / D-18 closure. |
| §12.3 (atomic-rename usage correct everywhere) | Positive finding; no action. |
| §12.5 (Co-Authored-By consistency) | Positive finding; no action. |
| §13 remediation rows 1, 3 | Already resolved above. |
| §13 remediation rows 2, 5 | Wired via D-13 (`896d8a52f`) and D-03 (`b0a02940e`); no further action. |

**Cross-references:** every audit finding section number above appears in at least one D-NN row's "Source" column in §3 master table, providing bidirectional traceability.

---

## §4. READY queue (rank-ordered, ship without further triage)

### §4.1 D-01 — Cross-zone PR review pickup for #197/#198 (WSJF 17.0)

**Action:** Watch `gh pr list --search 'voice-tier OR mode-d OR engine_session'` for alpha consumer-side PRs landing the work scoped in `~/.cache/hapax/relay/delta-to-alpha-cross-zone-handoff-20260420.md` (lines 18–60 voice_tier_3b; lines 62–103 mode_d_mutex_p3, both per PRE-COMPACT §6.1–§6.2). When PRs open, review for:

- `VoiceTierImpingement.try_from(imp)` correctly handles all 7 tier values (T0–T6) per PRE-COMPACT §9.1 line 215
- `engine_session()` consumer keyword matches the producer constant `VOICE_TIER_IMPINGEMENT_SOURCE` (PRE-COMPACT §6.1 line 145)
- Prometheus counter labels match the lazy-registered names `hapax_evil_pet_engine_acquires_total`, `hapax_evil_pet_engine_contention_total` (PRE-COMPACT §6.2 line 152)

**Acceptance:** approve or request changes; ship clarifying patches if alpha asks.

**Files to touch (likely none, possibly `shared/impingements.py` clarifier):** `agents/studio_compositor/director_loop.py` (alpha-owned, review only); `tests/studio_compositor/test_voice_tier_consumer.py` (alpha-owned, review only).

### §4.2 D-02 — Investigate operator-reported livestream regressions (WSJF 13.0)

**Action:** standing readiness — when operator surfaces a regression, dispatch `superpowers:systematic-debugging` per global CLAUDE.md "Proactive Plugin Usage" table. Apply `feedback_show_dont_tell_director.md` (memory index) and `feedback_never_drop_speech.md` as governance anchors during diagnosis.

**Acceptance:** root cause identified + fix shipped or dispatched, with citation back to the operator's surface message.

**Files to touch:** depends on regression. Most likely surfaces: `agents/hapax_daimonion/cpal_runner.py`, `agents/studio_compositor/director_loop.py`, `config/pipewire/voice-fx-*.conf`.

### §4.3 D-03 — Audio-topology Phase 5 verify sweep (WSJF 8.0)

**Action:** Phase 5 watchdog shipped (`138de264f` per PRE-COMPACT §9.3 line 237). Sweep is a verification pass: run `hapax-audio-topology verify` against current live graph, confirm exit 0 against the actual L6 + Cortado + Studio 24c topology after the operator's recent hardware moves. If non-zero, file follow-up; if zero, mark family closed in `delta.yaml`.

**Acceptance:** `hapax-audio-topology verify` exits 0 with current graph snapshot saved to `~/hapax-state/audio-topology/snapshot-20260420.json`.

**Files to touch:** none (read-only verify); maybe `delta.yaml` to mark family closed.

**Note:** FLOW §11 hour-3 (lines 421–430) was the original spec for this; that work is shipped, this is the verify-it-still-holds pass.

### §4.4 D-15 (when alpha returns spec) — rag-ingest livestream-compatible redesign

Currently NEEDS_RESEARCH; will re-rank as READY when alpha returns the spec dispatched in DELTA-YAML lines 30–38 / RAG-RESEARCH relay drop. Pre-scoping notes for the moment alpha returns:

- Embedder selection (CPU-only vs GPU-with-fortress-mode-gating)
- Docling vs alternatives (markdown-only direct-chunker bypass)
- Backfill semantics (retry-queue vs full-rescan cadence)
- Pacing primitive (existing examples: `shared/pacing.py`, none yet?)
- Observability (Prometheus + JSONL per existing patterns, see `shared.governance.monetization_egress_audit` PRE-COMPACT §9.5 line 254)
- Fortress-mode gating (read `~/.cache/hapax/working-mode`)

### §4.5 D-22 — Audit doc/spec-drift bundle (WSJF 11.0)

**Action:** Three coordinated documentation-only fixes from the 2026-04-20 audit. All three are mechanical edits that resolve reader-confusion at the spec/code/CLAUDE.md interface; no code touched.

1. **DEMONET-PLAN §0.1 path reconcile.** AUDIT §6.2 — plan prescribes `~/hapax-state/programmes/egress-audit/<date>/<hour>.jsonl`; shipped writer (`shared/governance/monetization_egress_audit.py:47`) uses flat `~/hapax-state/demonet-egress-audit.jsonl`. Decide: (a) update the plan to record the flat path actually shipped, OR (b) refactor the writer to nest-by-date (rotate hook already exists; this is a path-format change). Default to (a) — the flat path is operationally simpler and rotation is timer-driven, not directory-driven.
2. **DEMONET-PLAN §0.4 attribution update.** AUDIT §4.2 + §5.2 — `f893ddfbc` unilaterally resolved Path A vs Path B per "unblock yourself" directive, but plan still names it as a blocking operator-input gate. Update plan §0.4 to record "Path A (mute-and-transcript) was delta-defaulted on 2026-04-20 per `f893ddfbc`; operator may override to Path B per D-09."
3. **Workspace CLAUDE.md `Shared Infrastructure` rag-ingest GPU-isolated bullet.** AUDIT §11.2 — `8816040eb` cites the workspace CLAUDE.md GPU-isolation pattern but the doc still enumerates only ollama. Add a one-line bullet: "rag-ingest also runs CPU-only via `CUDA_VISIBLE_DEVICES=""` per `systemd/overrides/rag-ingest.service.d/gpu-isolate.conf`." Edit goes via dotfiles (`~/dotfiles/workspace-CLAUDE.md`), not `~/projects/CLAUDE.md`.

**Acceptance:** all three docs reflect the 2026-04-20 reality; `git diff` shows exactly three files modified.

**Files to touch:** `docs/superpowers/plans/2026-04-20-demonetization-safety-plan.md` (§0.1 + §0.4); `~/dotfiles/workspace-CLAUDE.md` (Shared Infrastructure section).

### §4.6 D-17 — Wire `quiet_frame` into production caller (WSJF 7.0)

**Action:** AUDIT §7.1 — `shared/governance/quiet_frame.py` ships with zero production callers. Wire two entry points:

1. **CLI `scripts/hapax-quiet-frame`** — operator-invokable, exposes `activate_quiet_frame()` + `deactivate_quiet_frame()` per AUDIT §11 remediation row 4. Add a `[scripts]` entry in `pyproject.toml` so it lands on `$PATH`.
2. **Pre-monetization-window programmatic call.** Audit recommends a call site in the broadcast-loop's pre-monetization-window logic. Suitable site: `agents/studio_compositor/director_loop.py` — when monetization-risk-gate transitions to `BLOCKED`, also `activate_quiet_frame()` with the current programme id; on transition back to `ALLOWED`, `deactivate_quiet_frame()`.

**Acceptance:** `Grep quiet_frame|QUIET_FRAME|activate_quiet_frame` returns ≥2 production import sites outside tests/docs (currently 0); `hapax-quiet-frame --help` works; one new test in `tests/studio_compositor/test_director_loop_quiet_frame.py` verifies the transition-driven activation.

**Files to touch:** `scripts/hapax-quiet-frame` (new), `pyproject.toml` ([scripts] section), `agents/studio_compositor/director_loop.py`, `tests/studio_compositor/test_director_loop_quiet_frame.py` (new).

**Cross-zone flag:** director_loop is alpha-touched. Coordinate via relay before merging to avoid mid-flight conflict; or scope D-17 to CLI-only and let alpha wire the director_loop call site as a follow-up.

### §4.7 D-18 — Wire `music_policy` into CPAL audio loop / compositor mute path (WSJF 7.0)

**Action:** AUDIT §7.1 — `shared/governance/music_policy.py` ships with zero production callers. Wire `default_policy().evaluate(audio_window)` into:

1. **CPAL audio capture loop** — `agents/hapax_daimonion/cpal_runner.py` (or the captured-audio buffer that feeds it). On every N-second window of captured audio, call `policy.evaluate(window)`; if `MusicAction.MUTE`, gate the output stream; if `MusicAction.RECORD_TRANSCRIPT`, log transcript per Path A.
2. **Studio compositor mute path** — when `policy.evaluate()` returns a mute decision, the studio compositor needs to also mute its own broadcast audio (not just CPAL). Use the existing impingement bus or a direct call into `agents/studio_compositor/audio_mute.py` (file may need to be created if no abstraction exists).

**Acceptance:** `Grep music_policy|MusicPolicy|MusicDetector` returns ≥1 production import site outside tests/docs (currently 0); 3-utterance smoketest with a known-music sample triggers Path A behavior; integration test in `tests/governance/test_music_policy_cpal_integration.py`.

**Files to touch:** `agents/hapax_daimonion/cpal_runner.py`, possibly `agents/studio_compositor/audio_mute.py` (new), `tests/governance/test_music_policy_cpal_integration.py` (new).

**Cross-zone flag:** CPAL is alpha's `feedback_grounding_critical` zone; coordinate via relay before merging. Per `feedback_no_stale_branches`, scope to a small PR and ship within one session-window or split into D-18a (CPAL wire) + D-18b (compositor wire).

**Dependencies:** D-19 should ship before D-18 in the ideal sequence — wiring music_policy without first adding the lock fixes the unsynchronized state issue under live concurrent CPAL+director_loop access. If D-18 ships first, document "single-thread caller" in MusicPolicy docstring as an interim contract.

### §4.8 D-19 — Concurrency hardening bundle (WSJF 6.5)

**Action:** Two coordinated lock additions; both are 5-line patches. Per AUDIT §12.2 cross-cutting pattern observation: stateful dataclasses without explicit lock contracts are a recurring anti-pattern in this window's governance modules.

1. **`_DEFAULT_WRITER` TOCTOU.** AUDIT §8.1 / `monetization_egress_audit.py:201-205` — wrap lazy init in module-level `threading.Lock` or use `functools.cache`. The latter is one line and idiomatic.
2. **`MusicPolicy._path_b_window_opened_at` lock.** AUDIT §8.2 / `music_policy.py:117-180` — add `_lock: threading.Lock = field(default_factory=threading.Lock)` and guard the read-then-write on the Path B branch.

**Acceptance:** both modules pass `pytest -k 'concurrent' tests/governance/` (add a thread-fuzzing test if not present); existing tests still green.

**Files to touch:** `shared/governance/monetization_egress_audit.py`, `shared/governance/music_policy.py`, `tests/governance/test_concurrent_default_writer.py` (new), `tests/governance/test_music_policy_concurrent_evaluate.py` (new).

### §4.9 D-21 — Repo-vs-systemd state divergence (WSJF 5.0)

**Action:** AUDIT §8.4 — `8816040eb` deleted `rag-ingest.timer` from the repo, but `systemctl --user list-unit-files | grep rag-ingest` still shows `rag-ingest.service linked enabled` (verified live during this weave: 2026-04-20). The repo-vs-systemd state divergence is identical-shape to the workspace `Subagent Git Safety` lost-work hazard, but for systemd state.

Ship `scripts/hapax-systemd-reconcile.sh` that:
1. Lists all `linked` user units under `~/.config/systemd/user/`.
2. Cross-references against `systemd/units/*.{service,timer,path,socket}` in the council repo.
3. For each linked unit absent from the repo: `systemctl --user disable --now <unit>` and unlink (with `--dry-run` default; `--apply` to act).
4. Emit a ntfy summary on completion.

Schedule via existing `claude-md-audit.timer` precedent — daily oneshot.

**Acceptance:** running `scripts/hapax-systemd-reconcile.sh --apply` disables rag-ingest.timer (the audit's specific case); idempotent on second invocation.

**Files to touch:** `scripts/hapax-systemd-reconcile.sh` (new), `systemd/units/hapax-systemd-reconcile.{service,timer}` (new), `tests/scripts/test_hapax_systemd_reconcile.py` (new).

### §4.10 D-20 — Crash-safety / atomic-write bundle (WSJF 4.3)

**Action:** Three small patches addressing AUDIT §8.3, §9.1, §10.1 — all are state-cleanup / atomic-write hygiene defects in the new governance / programme modules.

1. **`ProgrammePlanStore` `.tmp` orphan cleanup.** AUDIT §8.3 / `programme_store.py:189-196` — add `_cleanup_tmp()` startup hook that unlinks any `*.tmp` siblings of `self.path` left over from prior crashes. Alternatively, filter `.tmp` files in `all()`.
2. **`quiet_frame.activate_quiet_frame` no-op `if/else` collapse.** AUDIT §10.1 / `quiet_frame.py:130-145` — both branches call `st.add(programme)`. Collapse to a single `st.add(programme)`. Then add a `compact()` method on `ProgrammePlanStore` (or rely on dedup-at-read) so the store doesn't grow monotonically on every reactivation.
3. **`prune_old_archives` crash-safety.** AUDIT §9.1 / `monetization_egress_audit.py` prune loop — log start/end of prune so a crash mid-loop is visible; or move matched files to a quarantine dir then `shutil.rmtree`.

**Acceptance:** new tests verify `.tmp` cleanup-after-simulated-crash; quiet_frame reactivation doesn't grow the store; prune logs show start+end timestamps.

**Files to touch:** `shared/programme_store.py`, `shared/governance/quiet_frame.py`, `shared/governance/monetization_egress_audit.py`, plus three new test files.

### §4.11 D-23 — Detector exception fail-closed + egress-audit timer + Prometheus counters (WSJF 4.3)

**Action:** Robustness/observability bundle covering AUDIT §7.2, §9.2, §11.1, §11.5.

1. **Wrap `MusicPolicy.evaluate()` detector call.** AUDIT §9.2 — `self.detector.detect(audio_window)` raises propagate to broadcast loop. Wrap in try/except → `MusicDetectionResult(detected=False, source="error")` so the loop never crashes on a flaky detector.
2. **Ship egress-audit systemd timer.** AUDIT §7.2 — `bee082804` deferred the timer for daily rotate+prune. Without it, the 30-day retention promise is unenforced. Add `systemd/units/hapax-egress-audit-rotate.{service,timer}` calling `python -m shared.governance.monetization_egress_audit rotate`. ~10 LOC.
3. **Add `hapax_demonet_*` Prometheus counters across 8 new modules.** AUDIT §11.1 — at minimum `hapax_demonet_egress_records_total{risk,allowed}`, `hapax_classifier_unavailable_total{reason}`, `hapax_programme_store_active_count`, `hapax_quiet_frame_activations_total`, `hapax_music_policy_decisions_total{action}`. Per the existing `127.0.0.1:9482` Prometheus pattern.
4. **Optional `audit_writer` param on `classify_with_fallback`.** AUDIT §11.5 — composition hook: every fail-closed event becomes a `classifier_unavailable` egress record.

**Acceptance:** Grafana dashboard `dashboards/hapax-demonet.json` (new) shows live counts after a smoketest; `MusicPolicy` integration test with a raising detector passes; rotate timer fires per `systemctl --user list-timers`.

**Files to touch:** `shared/governance/music_policy.py`, `shared/governance/classifier_degradation.py`, `shared/governance/monetization_egress_audit.py`, `shared/governance/quiet_frame.py`, `shared/governance/ring2_classifier.py`, `shared/programme_store.py`, `systemd/units/hapax-egress-audit-rotate.{service,timer}` (new), `dashboards/hapax-demonet.json` (new), plus tests.

### §4.12 D-24 — Audit-cleanup bundle (WSJF 1.4)

**Action:** Catch-all bundle of 11 LOW-severity audit findings. Mechanical, low-risk, no operator question. Ship as a single PR; each item is independently revertable.

1. AUDIT §6.1 — `default_*` factory naming consistency: pick noun (`default_writer`, `default_policy`, `default_store`) or verb across `quiet_frame` family.
2. AUDIT §6.3 — tests-location convention: all `programme_store` consumers' tests live in `tests/governance/`, but `test_programme_store.py` itself is in `tests/shared/`. Decide one home.
3. AUDIT §8.5 — promote `_redact_points` import-failure from log+continue to raise (operator-decided per audit row 15; default to raise for fail-CLOSED).
4. AUDIT §8.6 — add a loud docstring warning to `classify_with_fallback` that timeout enforcement is post-hoc, not preemptive (until Phase 1+ classifier honors timeout itself).
5. AUDIT §9.3 — `unicodedata.normalize('NFKD', ...)` before lowercasing in `verify_vinyl_chain` substring matching.
6. AUDIT §9.4 — emit `warning` in `ProgrammePlanStore` if `self.path.stat().st_size > 1_000_000`.
7. AUDIT §10.3 — `if not math.isfinite(lufs): return None` guard in `_loudness_to_band`.
8. AUDIT §10.4 — optional `verify_port=True` flag on `recall_preset` to ping the MIDI port before issuing the burst.
9. AUDIT §11.3 — extract `_BASE_SCENE` from `shared/evil_pet_presets.py` to a shared constant; have `scripts/evil-pet-configure-base.py §3.8` import it.
10. AUDIT §11.4 — add `hapax-audio-topology verify --profile vinyl` subcommand wrapping `vinyl_chain_verify.verify_vinyl_chain` (overlaps with D-18 for a different module, but vinyl_chain_verify also has 0 callers per AUDIT §7.1).
11. AUDIT §11.6 — Hypothesis property-based tests for `aggregate_mix_quality` (algebraic over min-of-floats) and `_parse_verdict` (JSON-shape parser).

**Acceptance:** all 11 sub-items shipped; `pytest tests/ -q` green; `Grep` confirms naming consistency.

**Files to touch:** spans most new modules from this audit window; scope is wide but each diff is small.

---

## §5. NEEDS_CLARIFICATION queue (one question per item)

### §5.1 D-05 — Ring 2 classifier Phase 1 (WSJF 5.4)

**Sharpening question for operator:**

> For the 500-sample benchmark labelling (`benchmarks/demonet-ring2-500.jsonl`) — do you want me to (a) **synthesize** 500 samples from the existing `~/hapax-state/programmes/egress-audit/` JSONL, presenting them in a CLI for you to bucket none/low/medium/high; or (b) **generate** 500 fresh from the catalog × programme cross-product, then bucket? Synthesizing from real history calibrates against actual production traffic; synthetic gives full coverage but no production weighting. (Spec source: CAPSTONE §3 lines 58–73; PRE-COMPACT §4.2 lines 72–83.)

**Once answered:**

- Spec is locked. Implementation per CAPSTONE §3 "Recommended Phase 3 shape" (lines 113–145) with prompts sourced from `docs/research/2026-04-19-demonetization-safety-design.md` §6 (PRE-COMPACT §4.2 line 80).
- Estimated 400–600 LOC across `shared/governance/ring2_classifier.py` + `tests/governance/test_ring2_classifier.py` + `scripts/benchmark-ring2-classifier.py` + `benchmarks/demonet-ring2-500.jsonl`.

### §5.2 D-07 — Vinyl-broadcast signal-chain software wiring (WSJF 2.6)

**Sharpening question for operator:**

> The hardware signal chain is documented in `docs/research/2026-04-20-vinyl-broadcast-signal-chain-topology.md`. The software side I'd wire is one PipeWire conf + one verify test per channel-mapping. Confirm: for the "vinyl" path on the L6 ch 5–6 stereo input, the software writes (a) **a separate `hapax-vinyl-capture` filter-chain** mirroring `hapax-l6-evilpet-capture.conf`, or (b) **just a verify-only check** asserting the existing `pw-cat` consumers in `agents/studio_compositor/` see ch 5–6 stereo? (Source: TRIAGE §1 row 10; L6-RUNBOOK §1 lines 24–26.)

### §5.3 D-16 — Ring 2 per-`SurfaceKind` prompt design (WSJF 4.2)

**Sharpening question for operator:**

> Per-surface false-positive tolerance differs structurally — TTS false-positive cost is high (operator-audible re-recruitment); ward overlay FP cost is low (just visual swap). Per `SurfaceKind` (TTS / captions / overlay / ward), do I (a) **share a single base prompt** with surface-specific risk-tolerance constants; or (b) **author 4 distinct prompts** with per-surface few-shot exemplars? (a) is cheaper; (b) is more accurate per-surface. (Spec source: CAPSTONE §3 scope bullet 5; DEMONET-PLAN cross-ref to research §6.)

**Note:** D-16 is upstream of D-05 — answering it is a prerequisite for the Phase 1 prompt-author phase. Recommend operator answer §5.1 + §5.3 in one round.

---

## §6. NEEDS_RESEARCH queue (proposed dispatch brief per item)

### §6.1 D-08 — Audio-normalization ducking strategy (WSJF 3.7)

**Status per TRIAGE §1 row 8:** "Blocked. Unblock LADSPA syntax research first; then plan."

**LADSPA syntax research already shipped** as `docs/research/2026-04-20-ladspa-pipewire-syntax.md` per PRE-COMPACT §5.5 line 137. So D-08 is unblocked structurally — what's needed now is the *integration* research.

**Proposed dispatch brief (10–15 min subagent, research only):**

```yaml
to: research-subagent
mode: shared-directory (per global CLAUDE.md Subagent Git Safety #2)
deliverable: docs/research/2026-04-21-audio-normalization-ducking-integration.md
scope: |
  Given:
    - LADSPA syntax research shipped (docs/research/2026-04-20-ladspa-pipewire-syntax.md)
    - voice-fx-loudnorm.conf shipped (config/pipewire/voice-fx-loudnorm.conf)
    - Existing voice-fx chain (config/pipewire/voice-fx-chain.conf)
    - L6 multitrack topology per L6-RUNBOOK
  Produce a 1-page integration plan covering:
    - Where the ducking gate lives (pre-mix vs per-source)
    - How TTS-active signal reaches the ducker (impingement? direct sub-callback?)
    - 3-utterance smoketest acceptance criteria
    - Whether audio-topology.yaml needs a new node-kind
constraints: research only, no code, no plan-stub commits
```

### §6.2 D-15 — rag-ingest livestream-compatible redesign

Already dispatched per DELTA-YAML lines 30–38 + RAG-RESEARCH relay drop. Re-promotes to READY (D-01 shape) when alpha returns the spec+plan.

**Watch for:** `gh pr list --search 'rag-ingest'` and inbox for `~/.cache/hapax/relay/alpha-to-delta-rag-ingest-*.md`.

---

## §7. BLOCKED queue (what's blocking + when expected to unblock)

| ID | Item | Blocker | Unblock condition |
|---|---|---|---|
| D-04 | L6 retargets apply | hardware patching | operator patches Rode Wireless Pro on L6 ch 1 + confirms AUX 1 routing per L6-RUNBOOK §1 lines 28–32 |
| D-06 | LADSPA loudnorm operator-apply | manual `cp` + pipewire restart | one-time operator step per PRE-COMPACT §5.5 line 138 |
| D-09 | Music policy Path B switch | operator decision | operator flips `policy.path=B` per DELTA-YAML line 56 (Path A is shipped default; Path B is optional) |
| D-10 | Evil Pet `.evl` parser Phase 1 | physical SD card | operator delivers factory `.evl` per DELTA-YAML line 57 (note: CC-burst pack at `a19e8389f` already ships **without** `.evl` reverse — `.evl` is purely additive per CAPSTONE §1 row #194) |
| D-11 | Dual-FX Phase 6 (S-4 firmware) | firmware flash | operator flashes S-4 OS 2.1.4 per PRE-COMPACT §9.4 line 247 |
| D-12 | #202 Phase 2 | strict-serial after Phase 1 | D-05 ships first |
| D-13 | #202 Phase 3 | strict-serial after Phase 2 | D-12 ships first |
| D-14 | #202 Phase 4 | strict-serial after Phase 3 | D-13 ships first |

**Note on serial chain D-05 → D-12 → D-13 → D-14:** This is the longest delta-only chain remaining (FLOW §4.1 line 154). Estimated total 1300–2000 LOC across 4 phases. Each phase has its own infrastructure pre-wired per CAPSTONE §3.what's-pre-wired (`classifier_degradation`, `monetization_egress_audit`, `monetization_safety`, `quiet_frame`).

---

## §8. Recommended sequencing

**Note (post-audit-weave 2026-04-20 d33be1a6e+):** D-05 / D-13 / D-03 have shipped out-of-band (`d6a4d4753`, `896d8a52f`, `b0a02940e`); the sequencing below has been re-walked to reflect that and the 8 new audit-derived items.

### §8.1 Next 4 hours (T+0 → T+240)

**Goal:** clear the audit-derived READY queue (8 small items, dominated by D-22's high-WSJF doc bundle), then resume cross-zone monitoring + open-question surfacing.

- **T+00 to T+15** — Surface §5.1 + §5.3 questions to operator (one round, two questions). Critical: D-05 follow-on phases (D-12) still need answers; bundle them with the §10.3 / §10.4 / §10.5 lower-priority operator questions.
- **T+15 to T+45** — **D-22 (WSJF 11.0)** — three doc-only fixes (DEMONET-PLAN §0.1 path + §0.4 attribution + workspace CLAUDE.md rag-ingest GPU-isolated bullet). Self-contained, ≤30 min. Single commit/PR.
- **T+45 to T+105** — **D-19 (WSJF 6.5)** — concurrency hardening bundle (TOCTOU lock + MusicPolicy lock). Two 5-line patches + concurrency tests. Lands cleanly even if D-17/D-18 are not yet wired (hardens the modules in advance of wiring).
- **T+105 to T+150** — **D-21 (WSJF 5.0)** — systemd reconcile script. Self-contained; closes the audit's systemd-state-divergence finding (`rag-ingest.service` still `enabled` despite repo deletion).
- **T+150 to T+210** — D-01 + D-15 monitoring: poll for alpha's #197/#198 consumer PRs and rag-ingest research return. If either open, do reviews/promote.
- **T+210 to T+240** — Elective:
  - Option A: continue audit-cleanup with **D-20 (WSJF 4.3)** crash-safety bundle.
  - Option B: dispatch D-08 audio-normalization integration research subagent per §6.1 brief.
  - Option C: D-02 standing readiness — proactive sweep of `~/hapax-state/livestream-events/`.

**Default if no signals:** Option A (continue clearing audit-derived READY queue while operator-question + cross-zone polls are async).

### §8.2 Next 8 hours (T+240 → T+480)

**Goal:** wire the two truly-dead governance modules (D-17, D-18) into production callers and finish observability/robustness pass.

- **T+240 to T+330** — **D-17 (WSJF 7.0)** — wire `quiet_frame` (CLI + director_loop transition trigger). 90 min budget includes the cross-zone relay coordination.
- **T+330 to T+450** — **D-18 (WSJF 7.0)** — wire `music_policy` into CPAL audio loop (split into D-18a CPAL + D-18b compositor if scope creeps). Cross-zone with alpha; ship D-18a first, leave D-18b on the relay if alpha is mid-PR.
- **T+450 to T+480** — **D-23 (WSJF 4.3)** — robustness/observability bundle: detector try/except, egress-audit timer, Prometheus counters. Each sub-item independent; ship in one PR if time permits, else split.

### §8.3 Next 16 hours (T+480 → T+960)

- D-12 Phase 2 (#202 classifier-side opt-in negotiation) — assumes operator answered §5.1+§5.3. Per FLOW §4.4 line 178 ~250–350 LOC.
- D-14 Phase 4 (#202 degradation integration tests) — strict-serial after D-12. Small, smoothing pass.
- **D-24 (WSJF 1.4)** — audit-cleanup bundle (11 LOW-severity items). Use this as a "background while monitoring" task; ships as a single wide-scope-but-small-diff PR.
- After full Ring 2 chain: revisit BLOCKED items D-04 / D-06 / D-09 — reasonable chance operator has signalled by then.

### §8.4 Sequencing rationale changes (vs pre-audit-weave §8)

| Pre-weave assumption | Post-weave reality | Sequencing impact |
|---|---|---|
| D-03 audio-topology verify is the second-fastest READY item | D-03 shipped `b0a02940e`; D-22 doc-bundle now slot-2 (T+15) | T+15 to T+45 reassigned to D-22 |
| D-05 Ring 2 Phase 1 is the single big-ticket; needs operator answer | D-05 shipped `d6a4d4753`; only Phase 2/4 left (D-12, D-14) | §8.2 freed to wire D-17/D-18 dead modules instead |
| D-13 strict-serial after D-12 | D-13 shipped `896d8a52f` (out of strict-serial order, with own integration) | §8.3 freed to focus on D-24 cleanup + remaining BLOCKED revisits |
| READY queue size = 4 | READY queue size = 12 (4 + 8 audit-derived) | §8.1 now front-loads small-WSJF items D-22/D-19/D-21 instead of waiting on cross-zone polls |

---

## §9. Cross-zone coordination items (alpha-touches; coordination cost factor)

| ID | Item | Alpha-side scope | Cost-mult |
|---|---|---|---|
| D-01 | Cross-zone consumer PR review | review only; alpha owns the actual consumer code | 1.0 (no cost; ball is in alpha's court) |
| D-15 | rag-ingest research return | alpha returns spec; delta implements | 1.5 (round-trip latency) |

**Coordination cost factor applied:** all WSJF scores in §3 already include the round-trip cost in Job Size for items requiring alpha return. Items where the ball is purely in alpha's court (D-01) have JS=2 (review-only); items where delta reads a spec then implements (D-15) have JS=8 reflecting both legs.

**Cross-zone risk:** TRIAGE-RELAY lines 27–45 enumerates 11 alpha-zone unqueued items (HOMAGE-SCRIM family is the largest cluster). Delta does not own these; cited here only so the next session knows alpha has its own large unplanned backlog and shouldn't expect fast pickup of D-15-style returns.

---

## §10. Open questions for operator

These three operator answers unblock the entire queue downstream:

### §10.1 PRIORITY 1 — Ring 2 Phase 1 sample-set strategy (unblocks D-05, D-12, D-13, D-14)

> For the 500-sample Ring 2 benchmark, do you want me to **synthesize from existing egress-audit JSONL** (production-weighted) or **generate fresh from catalog × programme cross-product** (full-coverage)? See §5.1.

### §10.2 PRIORITY 1 — Ring 2 per-`SurfaceKind` prompt strategy (also unblocks D-05)

> Per `SurfaceKind` (TTS / captions / overlay / ward), shared base prompt with risk-tolerance constants, or 4 distinct prompts with surface-specific exemplars? See §5.3.

### §10.3 PRIORITY 2 — L6 retargets readiness (unblocks D-04)

> Has Rode Wireless Pro receiver been patched onto L6 ch 1, and is AUX 1 routing confirmed for the path
> `PC → L6 USB playback → AUX 1 send → AUX 1 out → Evil Pet L-in → L6 ch 3 → Main Mix → OBS`?
> See L6-RUNBOOK §1 lines 28–32.

### §10.4 PRIORITY 3 — Vinyl-broadcast wiring shape (unblocks D-07)

> Should I add a separate `hapax-vinyl-capture` filter-chain for L6 ch 5–6, or keep this as a verify-only assertion against existing consumers? See §5.2.

### §10.5 PRIORITY 4 — Music policy Path B (unblocks D-09)

> Path A (mute + transcript) is shipped default. Want to flip to Path B (≤30s clip windower) per `shared/governance/music_policy.py`? See PRE-COMPACT §5.3 lines 128–130.

**Bundling recommendation:** §10.1 + §10.2 are the two top-priority. Ask both at once to amortize the operator-context-switch cost.

---

## §11. Citation index (verification trail)

This document cites the following sources at the line/section ranges given. Total 32 distinct citation locations.

1. PRE-COMPACT §3 line 50 — working-tree-clean confirmation
2. PRE-COMPACT §4.2 lines 72–83 — #202 Phase 1 spec
3. PRE-COMPACT §4.4 line 91 — #197/#198 review pickup
4. PRE-COMPACT §4.5 lines 97–102 — livestream regression standing readiness
5. PRE-COMPACT §5.1 lines 110–114 — #202 Phase 2/3/4
6. PRE-COMPACT §5.2 + §7 line 191 — L6 retargets
7. PRE-COMPACT §5.3 lines 128–130 — music policy
8. PRE-COMPACT §5.4 lines 132–134 — Evil Pet `.evl`
9. PRE-COMPACT §5.5 lines 136–138 — LADSPA loudnorm
10. PRE-COMPACT §6.1 lines 145–148 — voice-tier 3b cross-zone
11. PRE-COMPACT §6.2 lines 150–154 — Mode D × voice-tier mutex 3 cross-zone
12. PRE-COMPACT §9.1 line 215 — voice-tier 7-tier catalog
13. PRE-COMPACT §9.3 lines 232–240 — audio-topology Phases 1–6
14. PRE-COMPACT §9.4 lines 246–247 — dual-FX Phase 6
15. PRE-COMPACT §9.5 line 254 — egress audit reference
16. FLOW §3 lines 88–94 — audio-topology dependency graph
17. FLOW §3 line 84 — Mode D shipped (Gate 2)
18. FLOW §3.2 line 145 — vinyl-broadcast software wiring
19. FLOW §4.1 line 154 — longest delta-only chain
20. FLOW §4.4 line 178 — Phase 2 size estimate
21. FLOW §6 line 240 — dual-FX Phase 6 operator gate
22. FLOW §10.3 line 390 — audio-norm research blockage history
23. FLOW §11 hour-3 lines 421–430 — audio-topology verify-sweep
24. TRIAGE §1 row 8 — audio-normalization-ducking blocked-then-unblocked
25. TRIAGE §1 row 10 — vinyl-broadcast software wiring
26. TRIAGE §3 row 36 — vinyl-broadcast signal-chain (operator-authored hardware)
27. TRIAGE-RELAY lines 27–45 — alpha-zone gap list
28. CAPSTONE §1 lines 11–33 — 35-ship table (post-resume + pre-crash)
29. CAPSTONE §3 lines 58–73 — #202 scope per plan §3
30. CAPSTONE §3 lines 113–145 — Recommended Phase 3 shape skeleton
31. DELTA-YAML lines 20–28 — VRAM fix shipped (`8816040eb`)
32. DELTA-YAML lines 30–38 — rag-ingest research dispatch to alpha
33. DELTA-YAML lines 51–66 — operator-gated items + next-session priorities
34. L6-RUNBOOK §1 lines 24–32 — pre-condition + pending operator confirms
35. DEMONET-PLAN §0.1 lines 38–62 — three-rings architecture (Phase 2/3/4 anchor)

---

## §12. Successor session entry checklist

1. **Read this file first.** It is the front-of-queue.
2. Read PRE-COMPACT (full file) for the exhaustive prior-state. Read AUDIT (`docs/research/2026-04-20-six-hour-audit.md`) for the d33be1a6e weave context.
3. Check operator inbox for answers to §10.1 + §10.2 — these unblock D-12 (#202 Phase 2 follow-on; D-05 itself shipped `d6a4d4753`).
4. `gh pr list --search 'voice-tier OR mode-d OR engine_session OR rag-ingest'` — check for alpha returns on D-01 / D-15.
5. **First action regardless of operator/alpha state:** ship D-22 (WSJF 11.0) — three coordinated doc-only fixes, ≤30 min, no dependencies. Closes the audit's spec-drift findings immediately.
6. **Second action:** D-19 (WSJF 6.5) concurrency hardening + D-21 (WSJF 5.0) systemd reconcile script. Both small, both READY, both unblock D-17/D-18 wiring downstream.
7. **Third action:** D-17 + D-18 — wire the two truly-dead governance modules (`quiet_frame`, `music_policy`) into production callers per AUDIT §7.1. These are HIGH-severity audit findings; do not leave them dead-bridged into the next session.
8. If operator answered §10.1+§10.2: start D-12 (#202 Phase 2 follow-on).
9. If alpha returned D-15 spec: start D-15 implementation.
10. Background-task: D-24 audit-cleanup bundle (WSJF 1.4) — 11 LOW-severity items, mechanical, can run alongside monitoring polls.
11. Refresh `delta.yaml` `next_delta_session_priorities` from this document's READY queue + remaining unblocked items.

---

*End of WSJF reorganization (audit-woven 2026-04-20 d33be1a6e). Next delta session executes the READY queue rank-ordered (D-22 → D-19 → D-21 → D-17 → D-18 → D-23 → D-20 → D-24) or escalates §10 questions to operator.*
