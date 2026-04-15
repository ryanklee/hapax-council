# HSEA Phase 5 — Biometric + Studio + Archival Triad (M-series) — Plan

**Date:** 2026-04-15
**Spec reference:** `docs/superpowers/specs/2026-04-15-hsea-phase-5-m-series-triad-design.md`
**Branch target:** `feat/hsea-phase-5-m-series-triad`
**Unified phase mapping:** UP-12 parallel cluster (substrate-agnostic)

---

## 0. Preconditions

- [ ] LRR UP-0/UP-1/UP-3 closed
- [ ] HSEA UP-2/UP-4/UP-10 closed
- [ ] LRR Phase 8 (UP-11 portion) closed — M1/M3 use Phase 8 attention-bid channels
- [ ] hapax-watch streaming biometrics; contact mic + IR perception producing signals
- [ ] Reverie pipeline running + param bridge operational
- [ ] Qdrant `stream-reactions` has 2,758+ points (for M4 drift detector)
- [ ] Session claims: `hsea-state.yaml::phase_statuses[5].status: open`

---

## Execution order: M5 → M2 → M1 → M3 → M4 → M6-M23 as bandwidth allows

### 1. M5 Reverie wgpu cognitive state write channel (ships FIRST)

- [ ] Tests: fixture cognitive event → 9-dim transform → Reverie uniforms.json update
- [ ] `agents/reverie/gpu_state_signal_affordance.py` (~250 LOC)
- [ ] `shared/gpu_state_signal_registry.yaml` — 5 starting event mappings (frozen-files-block, drift-detection, anomaly-resolution, research-integrity-flip, condition-transition)
- [ ] Hook wiring from each event source → affordance pipeline
- [ ] Commit: `feat(hsea-phase-5): M5 Reverie wgpu cognitive state write channel`

### 2. M2 retrieval-augmented operator memory in voice

- [ ] Tests: mock Qdrant → cosine > 0.85 → surface prior answer; cosine < 0.85 → fresh generation
- [ ] `agents/hapax_daimonion/m_series/m2_retrieval_memory.py` (~350 LOC)
- [ ] Voice query dispatcher extension to invoke M2 before fresh generation
- [ ] Sierpinski slot renderer for citation card (~100 LOC)
- [ ] Commit: `feat(hsea-phase-5): M2 retrieval-augmented operator memory`

### 3. M1 biometric-driven proactive intervention loop

- [ ] Tests: fixture HRV drop + desk-streak → daimonion impingement via operator-only audio sink
- [ ] `agents/hapax_daimonion/m_series/m1_biometric_loop.py` (~300 LOC)
- [ ] `agents/studio_compositor/biometric_strip_source.py` Cairo strip (~250 LOC)
- [ ] `config/m1-thresholds.yaml` operator-editable thresholds
- [ ] Use Phase 8 attention-bid channel for private delivery
- [ ] Commit: `feat(hsea-phase-5): M1 biometric proactive intervention loop`

### 4. M3 studio creative-state composition daemon

- [ ] Tests: fixture BPM + MIDI + stimmung SEEKING + prior-session-exists → suggestion delivered operator-private
- [ ] `agents/hapax_daimonion/m_series/m3_studio_composition.py` (~400 LOC)
- [ ] `agents/studio_compositor/studio_scaffold_pill_source.py` Cairo pill (~120 LOC)
- [ ] Commit: `feat(hsea-phase-5): M3 studio creative-state composition daemon`

### 5. M4 long-horizon stream-reactions drift detector

- [ ] Tests: fixture 6-week reactions with deliberate drift → PCA detects it → drop composed
- [ ] `agents/hapax_daimonion/m_series/m4_drift_detector.py` (~350 LOC PCA + trajectory)
- [ ] `systemd/user/hapax-m4-drift-detector.timer` + `.service` (weekly cadence)
- [ ] `agents/studio_compositor/drift_trajectory_source.py` Sierpinski renderer (~150 LOC)
- [ ] Commit: `feat(hsea-phase-5): M4 long-horizon stream-reactions drift detector`

### 6. M6-M23 stretch touch points (as bandwidth allows)

Each M6-M23 item is a separate PR following the pattern: test + implementation module + any needed Cairo source or config file. Execution order within stretch items is opener's discretion.

Priority shortlist for stretch (if bandwidth is limited):

- **M15** daimonion-narrated commit walkthrough — valuable + isolated
- **M22** operator-absent dream-sequence content — elegant + audience-facing
- **M9** album-identifier editorial expansion — extends existing feature
- **M21** operator-correction live filter — research-quality feature

Defer to later phases if bandwidth constrained:

- **M6** accountability ledger surfacing (needs vault schema decision)
- **M13** spawn-budget heatmap (needs longer data accumulation)
- **M18** vault daily-note → prompt context bridge (operator schema decision)
- **M8** audience-driven preset chain (consent-safety review needed)

---

## Phase 5 close

### Smoke tests

- M1: simulated HRV drop triggers impingement; operator-private delivery verified
- M2: real voice query retrieves prior answer above threshold; citation card renders
- M3: simulated session triggers suggestion + studio-scaffold pill renders on stream
- M4: weekly timer runs; if drift detected, drop composed + trajectory renders
- M5: cognitive event → GPU signature verified for at least 1 of 5 events

### Handoff doc

- `docs/superpowers/handoff/2026-04-15-hsea-phase-5-complete.md`
- `hsea-state.yaml::phase_statuses[5].status: closed`

### Cross-epic coordination

- **LRR Phase 8** Phase 8 attention-bid channels used by M1/M3 for private delivery
- **HSEA Phase 2 ComposeDropActivity** used by M4 drift detector
- **HSEA Phase 0 governance queue + spawn budget** used by all M-deliverables
- **Reverie pipeline** param bridge extended by M5 cognitive state channel

---

## End

Compact plan for HSEA Phase 5 M-series. Substrate-agnostic. Pre-staging.

— delta, 2026-04-15
