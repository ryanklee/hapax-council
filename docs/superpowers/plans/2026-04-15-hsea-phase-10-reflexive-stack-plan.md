# HSEA Phase 10 — Reflexive Stack (Cluster F) — Plan

**Date:** 2026-04-15
**Spec reference:** `docs/superpowers/specs/2026-04-15-hsea-phase-10-reflexive-stack-design.md`
**Branch target:** `feat/hsea-phase-10-reflexive-stack`
**Unified phase mapping:** UP-13 sibling (~1,400 LOC)

---

## 0. Preconditions

- [ ] LRR UP-0/UP-1/UP-9 closed
- [ ] HSEA UP-2/UP-4/UP-10 closed (ReflectiveMomentScorer calibration complete, `enabled=True`)
- [ ] LRR Phase 5a substrate swap closed with operator-ratified substrate per drop #62 §14
- [ ] Substrate narration quality gate: Phase 10 opener runs 3-5 fixture narration prompts; ≥3/5 Hapax-ness required to ship F-layers enabled
- [ ] Operator has seeded 20+ cliches in `~/hapax-state/f-cluster-cliche-corpus.jsonl` (for F10 anti-cliche gate)
- [ ] Session claims: `hsea-state.yaml::phase_statuses[10].status: open`

---

## Execution order (per spec §8): F10 → F2 → F7 → F11 → F4 → F5 → F9 → F6 → F8 → F13 → F12 → F14

### 1. F10 — Anti-cliche override (SHIPS FIRST per drop #59 fix)

- [ ] Tests: fixture cliche corpus + proposed F-layer output; cosine >0.9 → blocked; <0.9 → allowed; retry loop ≤3
- [ ] `agents/hapax_daimonion/f_cluster/f10_anti_cliche_override.py` (~250 LOC)
- [ ] `agents/hapax_daimonion/f_cluster/_cliche_corpus_loader.py` (~100 LOC)
- [ ] Qdrant NN query against `operator-corrections` collection
- [ ] Commit: `feat(hsea-phase-10): F10 anti-cliche override (ships FIRST)`

### 2. F2 — Directed reflect activity

- [ ] Tests: reflect output goes through F10 + ReflectiveMomentScorer gate
- [ ] `agents/hapax_daimonion/f_cluster/f2_directed_reflect.py` (~180 LOC)
- [ ] Extends HSEA Phase 2 3.3 reflect with research condition + persona stance direction
- [ ] Commit: `feat(hsea-phase-10): F2 directed reflect activity (gated by F10)`

### 3. F7 — Architectural narration

- [ ] Tests: fixture PR merge event → narration drop with PR number + service names
- [ ] `agents/hapax_daimonion/f_cluster/f7_architectural_narrator.py` (~200 LOC)
- [ ] Reads `/dev/shm/hapax-ci-state.json` (LRR Phase 9 item 9)
- [ ] Commit: `feat(hsea-phase-10): F7 architectural narration`

### 4. F11 — Stimmung self-narration

- [ ] Tests: dimension delta >0.3 → narration trigger
- [ ] `agents/hapax_daimonion/f_cluster/f11_stimmung_self_narration.py` (~180 LOC)
- [ ] Rate-limited + F10 anti-cliche gated
- [ ] Commit: `feat(hsea-phase-10): F11 stimmung self-narration`

### 5. F4 — Research-harness narration

- [ ] Tests: fixture condition transition → narration drop
- [ ] `agents/hapax_daimonion/f_cluster/f4_harness_narrator.py` (~200 LOC)
- [ ] Composes `ComposeDropActivity`
- [ ] Commit: `feat(hsea-phase-10): F4 research-harness narration on condition transitions`

### 6. F5 — Viewer-awareness ambient (aggregate only)

- [ ] Tests: aggregate chat engagement signals → awareness narration (1/hour max)
- [ ] `agents/hapax_daimonion/f_cluster/f5_viewer_awareness.py` (~180 LOC)
- [ ] NO per-viewer state (consent-safe)
- [ ] Commit: `feat(hsea-phase-10): F5 viewer-awareness ambient (aggregate only)`

### 7. F9 — Temporal self-comparison via Qdrant

- [ ] Tests: query Qdrant for similar prior reaction; narrate comparison
- [ ] `agents/hapax_daimonion/f_cluster/f9_temporal_self_comparison.py` (~220 LOC)
- [ ] Uses HSEA Phase 5 M4 drift detector's temporal indexing pattern
- [ ] Commit: `feat(hsea-phase-10): F9 temporal self-comparison via Qdrant NN`

### 8. F6 — Bayesian-loop self-reference (1/stream MAX)

- [ ] Tests: hard rate limit enforced via `~/hapax-state/f6-fire-count.json`
- [ ] `agents/hapax_daimonion/f_cluster/f6_bayesian_self_reference.py` (~150 LOC)
- [ ] Cites drops #54-#62 texts by specific tactic
- [ ] Commit: `feat(hsea-phase-10): F6 Bayesian-loop self-reference (1/stream max)`

### 9. F8 — Reading own research drops

- [ ] Tests: weekly selection + commentary composition
- [ ] `agents/hapax_daimonion/f_cluster/f8_drop_reader.py` (~180 LOC)
- [ ] Random walk + operator bias toward recent drops
- [ ] Commit: `feat(hsea-phase-10): F8 reading own research drops`

### 10. F13 — Operator-Hapax dialogue cameo

- [ ] Tests: retrieve authorized interaction from consent-gated Qdrant; narrate
- [ ] `agents/hapax_daimonion/f_cluster/f13_operator_dialogue_cameo.py` (~220 LOC)
- [ ] Consent contract check before emission
- [ ] Max 1/hour
- [ ] Commit: `feat(hsea-phase-10): F13 operator-Hapax dialogue cameo (consent-gated)`

### 11. F12 — Counterfactual substrate self-reference

- [ ] Tests: fixture historical substrate state → counterfactual narration
- [ ] `agents/hapax_daimonion/f_cluster/f12_counterfactual_substrate.py` (~200 LOC)
- [ ] Post-§14: counterfactuals reference historical prior substrates (Qwen 3.0, etc.) not Hermes
- [ ] Commit: `feat(hsea-phase-10): F12 counterfactual substrate self-reference (post-§14)`

### 12. F14 — Meta-meta-reflexivity (hard ≤3/stream)

- [ ] Tests: hard rate limit enforced via `~/hapax-state/f14-fire-count.json`
- [ ] `agents/hapax_daimonion/f_cluster/f14_meta_meta_reflexivity.py` (~150 LOC)
- [ ] Commit: `feat(hsea-phase-10): F14 meta-meta-reflexivity (≤3/stream hard rate limit)`

---

## Phase 10 close

- [ ] F10 ships first; F2-F14 all gated by F10 + ReflectiveMomentScorer
- [ ] All 13 F-layers registered with enable flag
- [ ] Substrate quality gate applied; layers disabled if <3/5 quality
- [ ] Spec §5 exit criteria verified
- [ ] Handoff doc
- [ ] `hsea-state.yaml::phase_statuses[10].status: closed`

---

## Cross-epic coordination

- **HSEA Phase 2 ReflectiveMomentScorer** (3.8, post-calibration) gates all F-layers
- **HSEA Phase 2 `ComposeDropActivity`** (3.6) composed by most F-layers
- **HSEA Phase 5 M4 drift detector** temporal indexing pattern reused by F9
- **LRR Phase 9 item 9 SHM publishers** (editor/git/CI) consumed by F7 architectural narration
- **Drop #62 §14 substrate gate** applied at phase open time

---

## End

Compact plan for HSEA Phase 10 Reflexive Stack / Cluster F. Pre-staging. F10 ships first per drop #59 fix.

— delta, 2026-04-15
