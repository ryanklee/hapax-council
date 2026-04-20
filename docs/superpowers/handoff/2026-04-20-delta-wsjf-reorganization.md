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

---

## §1. TL;DR

**Top 5 by WSJF (highest score = ship first):**

| Rank | Item | WSJF | State |
|---|---|---|---|
| 1 | Cross-zone PR review pickup for #197/#198 (alpha consumer side) | **17.0** | READY |
| 2 | Investigate operator-reported livestream regressions (standing readiness) | **13.0** | READY |
| 3 | Audio-topology Phase 5 verifier sweep against current live graph | **8.0** | READY |
| 4 | L6 retargets apply (5 configs) | **7.6** | BLOCKED-operator |
| 5 | #202 Ring 2 classifier Phase 1 (real prompts + 500-sample bench) | **5.4** | NEEDS_CLARIFICATION |

**Ship-readiness distribution (16 items):**

- **READY:** 4 (queue-runnable now without operator input)
- **NEEDS_CLARIFICATION:** 3 (one-question sharpening unblocks)
- **NEEDS_RESEARCH:** 2 (research dispatch required first)
- **BLOCKED:** 7 (operator decision/hardware/peer-agent)

**Headline:** delta exited the prior session with the queue genuinely cleared (CAPSTONE §1 lines 11–33 lists 35 ships; PRE-COMPACT §3 line 50 confirms working-tree clean on `main`). The VRAM emergency closed cleanly (`8816040eb` shipped per DELTA-YAML lines 20–28; rag-ingest now drip-only inotify, 370 MB RSS, zero GPU). Remaining work is dominated by cross-zone wait-states and operator-gated apply-steps. The single big-ticket implementation item — Ring 2 Phase 1 — needs operator labelling before it can start.

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

**Score sanity check:** D-01 dominates because the body of work is tiny (review + maybe a clarifying patch) and it converts two already-shipped delta-side commits (`0dbaa1321` per CAPSTONE §1 row #197+#198) into deployed behavior. D-02 is high because *any* livestream regression is by definition gate-decay-affecting per `feedback_consent_latency_obligation` and `feedback_show_dont_tell_director` (memory index). D-05 (Ring 2 P1) is the heaviest standalone delta-shippable but the JS=8 divisor + the clarification gate keeps it below the small-ticket items.

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

### §8.1 Next 4 hours (T+0 → T+240)

**Goal:** complete READY queue + answer pending operator questions.

- **T+00 to T+15** — Surface §5.1 + §5.3 questions to operator (one round, two questions). Critical: D-05 cannot start without these; bundle them.
- **T+15 to T+30** — D-03 audio-topology verify-sweep. Self-contained; no dependencies. Closes the audio-topology family officially.
- **T+30 to T+90** — D-15 monitoring: poll for alpha's rag-ingest research return; if returned, promote to READY and consume the spec+plan, ship the implementation behind it. If not returned, defer to next block.
- **T+90 to T+150** — D-01 monitoring: poll for alpha's #197/#198 consumer PRs. If open, do reviews; if not, defer.
- **T+150 to T+240** — Elective:
  - Option A: if operator answered §5 questions, **start D-05** (Ring 2 Phase 1 prompt-author phase per CAPSTONE §3 Recommended Phase 3 shape, lines 113–145).
  - Option B: dispatch D-08 audio-normalization integration research subagent per §6.1 brief.
  - Option C: D-02 standing readiness — proactive sweep of `~/hapax-state/livestream-events/` for any anomalies since last session.

**Default if no signals:** Option B (research dispatch is async, frees delta context to monitor D-01/D-15 polls in parallel).

### §8.2 Next 8 hours (T+240 → T+480) — assumes §5 answered

- **T+240 to T+360** — D-05 implementation (heavy; Ring 2 Phase 1). Per CAPSTONE §3 size estimate 400–600 LOC. Ship `shared/governance/ring2_classifier.py` + tests + benchmark script + first-pass labelled set.
- **T+360 to T+420** — Run 500-sample benchmark; tune thresholds; commit benchmark results JSONL.
- **T+420 to T+480** — D-12 Phase 2 start (classifier-side opt-in negotiation; smaller scope per FLOW §4.4 line 178 ~250–350 LOC).

### §8.3 Next 16 hours (T+480 → T+960)

- D-13 Phase 3 (verdict integration into `MonetizationRiskGate.assess()`) — strict-serial after D-12. Heaviest of the chain because it touches the production decision tree.
- D-14 Phase 4 (degradation integration tests) — small, smoothing pass.
- After full Ring 2 chain: revisit BLOCKED items D-04 / D-06 / D-09 — reasonable chance operator has signalled by then.

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
2. Read PRE-COMPACT (full file) for the exhaustive prior-state.
3. Check operator inbox for answers to §10.1 + §10.2 — these unblock the heaviest items.
4. `gh pr list --search 'voice-tier OR mode-d OR engine_session OR rag-ingest'` — check for alpha returns on D-01 / D-15.
5. If operator answers §10.1+§10.2: start D-05.
6. If alpha returned D-15 spec: start D-15 implementation.
7. If neither: execute §8.1 default (Option B research dispatch + D-03 verify-sweep).
8. Refresh `delta.yaml` `next_delta_session_priorities` from this document's READY queue + remaining unblocked items.

---

*End of WSJF reorganization. Next delta session executes the READY queue rank-ordered or escalates §10 questions to operator.*
