# Continuous Perception: Revert + Calibrated Path Forward

> **For agentic workers:** Execute sequentially. Each phase has a gate condition. Do not proceed until the gate passes.

**Goal:** Achieve continuous perception (buffer never goes deaf) through measured, calibrated echo discrimination — not guessed thresholds.

**Current state:** Four-layer echo stack deployed but uncalibrated. Hapax hears its own speech. Voice unusable.

**Target state:** Same four-layer stack, but thresholds derived from real room measurements. Gates removed only when data proves discrimination works.

---

## Phase 0: Revert to Working State (immediate)

**What:** Revert PRs #568 and #569 on main. Restore the buffer gates (`_speaking` and `in_cooldown`). Keep these commits that should stay:
- `a6211153` — grounding ledger always active (effort calibration for word limits)
- `f0351741` — max_tokens 4096 for Opus extended thinking
- `74834f77` — T1 echo cooldown (1s)

**What stays in codebase but inactive:**
- `energy_classifier.py` — TtsEnergyTracker + EnergyClassifier (new module, not wired)
- `speech_classifier.py` — DuringProductionClassifier (new module, not wired)
- `systemd/pipewire/echo-cancel.conf` — PipeWire webrtc AEC config (installed but daemon uses raw mic)
- `docs/superpowers/specs/2026-04-02-continuous-perception-design.md` — design spec
- `docs/research/echo-calibration-methodology.md` — calibration methodology

**Gate:** Voice works. Normal conversation. No echo loop. No truncated responses.

---

## Phase 1: Instrument (no behavior change)

**What:** Add passive `EchoCalibrationLogger` that records per-frame metrics during voice sessions. The buffer gates stay active — zero behavior change. The logger runs behind the gates, measuring what the energy classifier and VAD *would* decide if the gates weren't there.

**Per-frame metrics logged (CSV, env-var gated via HAPAX_ECHO_CALIBRATION=1):**

| Field | Source | Why |
|-------|--------|-----|
| `timestamp_ms` | `time.monotonic()` | Temporal alignment |
| `mic_rms_raw` | Frame before `echo_canceller.process()` | Raw echo energy from room |
| `mic_rms_aec` | Frame after `echo_canceller.process()` | Attenuated echo energy |
| `aec_attenuation_db` | `20 * log10(raw / aec)` | speexdsp effectiveness per frame |
| `tts_ref_rms` | `TtsEnergyTracker.expected_energy()` | What the classifier thinks TTS energy is |
| `vad_prob` | `presence._latest_vad_confidence` | Silero's opinion on attenuated frame |
| `energy_class` | `EnergyClassifier.classify()` | What Layer 2 would decide |
| `system_speaking` | `buffer._speaking` | Whether buffer thinks system is speaking |
| `tts_ended_ago_ms` | `now - buffer._speaking_ended_at` | Time since TTS stopped (decay measurement) |
| `operator_speaking` | Ground truth: manual annotation or heuristic | Needed for calibration |

**Operator ground truth:** During calibration sessions, use a simple protocol:
- Session 1: System speaks, operator silent → all non-silent frames are echo
- Session 2: Operator speaks, system silent → all frames are speech baseline
- Session 3: Normal conversation → mixed (labeled by temporal state)
- Session 4: Operator speaks DURING system speech → barge-in ground truth

**Implementation:**
- New file: `agents/hapax_daimonion/echo_calibration.py` (~100 lines)
- Wire into `run_loops.py` audio_loop: capture raw frame before AEC, log after
- Wire TtsEnergyTracker (passive, no behavior change) alongside EchoCanceller
- Activate: `HAPAX_ECHO_CALIBRATION=1` in systemd env or `.envrc`
- Output: `~/.cache/hapax/echo-calibration/session-{timestamp}.csv`

**Duration:** 3-5 voice sessions, ~15 minutes total. Can be done in one evening.

**Gate:** CSV files exist with >10,000 frames of data across all 4 scenarios.

---

## Phase 2: Analyze + Calibrate (offline)

**What:** Run analysis scripts on collected data. Compute actual echo/speech distributions. Derive calibrated thresholds. Validate offline.

**Analysis script:** `scripts/analyze-echo-calibration.py`

**Outputs:**
1. **Distribution plots:** Echo RMS histogram vs speech RMS histogram (post-AEC). Overlap region visible.
2. **AEC effectiveness:** Median attenuation in dB. If <10dB, speexdsp reference alignment needs fixing first.
3. **Calibrated thresholds:**
   - `_SILENCE_THRESHOLD` = ambient noise p99 × 1.2
   - `_ECHO_RATIO_CEILING` = echo ratio p95 + margin (validated against speech ratio p05)
   - `_SPEECH_FLOOR_DURING_TTS` = echo RMS p99 × 1.1
   - Adaptive VAD threshold = echo VAD p99 + 0.05
   - `_post_tts_window` = time for energy to decay below 2× ambient
4. **Offline replay validation:** Run all collected frames through classifier with proposed thresholds.

**Acceptance criteria (from methodology doc):**

| Metric | Target |
|--------|--------|
| Echo rejection rate (energy classifier) | >99% |
| Echo VAD rejection rate (adaptive threshold) | >99% |
| Clean speech pass-through rate | >99% |
| Barge-in acceptance (speech during TTS) | >80% |

**If distributions overlap (<1.5x separation):**
- Physical mitigations first: reduce monitor volume, reposition mic, tune AEC tail_ms
- Re-collect data after physical changes
- If still overlapping: accept that pure energy classification is insufficient for this room, plan spectral features or neural classifier

**Gate:** All four acceptance criteria met on offline replay.

---

## Phase 3: Deploy Calibrated Thresholds (gates stay, thresholds change)

**What:** Update `energy_classifier.py` constants and `conversation_buffer.py` adaptive thresholds with the values derived from Phase 2. The gates still exist but now use calibrated values.

**Changes:**
- `energy_classifier.py`: replace `_SILENCE_THRESHOLD`, `_ECHO_RATIO_CEILING`, `_SPEECH_FLOOR_DURING_TTS` with calibrated values
- `conversation_buffer.py`: replace `0.8` / `0.7` / `0.15` VAD thresholds with calibrated values
- `conversation_buffer.py`: replace `0.5` post-TTS window with measured decay time

**Verification:** 2-3 voice sessions with calibrated thresholds + logging still active. Compare classifier decisions against logged reality.

**Gate:** Live sessions show zero echo leaks AND zero dropped operator speech in the calibration log.

---

## Phase 4: Remove feed_audio Gate (frames always accumulated)

**What:** Remove the `if self._speaking: return` gate from `conversation_buffer.feed_audio()`. Frames always accumulate during speech detection. The energy classifier in `run_loops.py` still suppresses echo-classified frames from the buffer — this is the first real test of Layer 2.

**What stays gated:** `update_vad()` still uses adaptive thresholds (but calibrated). Utterance emission still requires sustained VAD above threshold.

**Monitoring:** Calibration logger stays active. Watch for:
- Echo frames leaking past energy classifier into buffer
- False utterance emissions during system speech

**Gate:** 3+ voice sessions with zero echo-triggered utterances.

---

## Phase 5: Remove update_vad Gate (adaptive thresholds are the only defense)

**What:** Remove the `if self._speaking: return` gate from `conversation_buffer.update_vad()`. VAD always runs. The adaptive threshold (calibrated in Phase 2) is the defense.

**This is the ideal state for Layers 1-3.** SpeexDSP attenuates, energy classifier filters, adaptive VAD handles residual. No frames dropped.

**Monitoring:** Calibration logger + manual barge-in testing. Operator speaks during system speech and verifies detection.

**Gate:** 3+ sessions with zero echo-triggered speech detection AND operator speech detected during system output.

---

## Phase 6: Enable Speech-During-Production Classifier

**What:** Wire `DuringProductionClassifier` into CPAL runner (the code from Task 7 of the original plan). Operator speech during system output is classified as backchannel → grounding ledger or floor claim → yield.

**This is the full ideal state.** Perception is continuous. Operator speech is always heard. Backchannels ground. Floor claims yield.

**Gate:** Backchannel "mm-hm" detected during system speech → grounding ledger updates. Full sentence during system speech → system yields and processes.

---

## Timeline

| Phase | Duration | Depends on |
|-------|----------|-----------|
| 0: Revert | 30 min | — |
| 1: Instrument | 1-2 hrs implementation + 1 evening data collection | Phase 0 |
| 2: Analyze | 1-2 hrs | Phase 1 data |
| 3: Deploy calibrated thresholds | 30 min + 1 evening verification | Phase 2 |
| 4: Remove feed_audio gate | 15 min + 1 evening verification | Phase 3 |
| 5: Remove update_vad gate | 15 min + 1 evening verification | Phase 4 |
| 6: Enable speech classifier | 30 min + 1 evening verification | Phase 5 |

**Total: ~5 evenings of voice sessions.** Each phase is one session. The work between sessions is small (apply thresholds, remove one gate). The measurement and analysis is front-loaded in Phases 1-2.

---

## What this preserves from the current work

- `energy_classifier.py` — stays in codebase, used passively in Phase 1, activated in Phase 4
- `speech_classifier.py` — stays in codebase, activated in Phase 6
- `echo_canceller.py` — stays active (speexdsp AEC, Layer 1)
- `register_tts_text()` on pipeline — stays (improves transcript echo detection even with gates)
- Adaptive VAD code in `conversation_buffer.py` — stays in codebase, activated in Phase 5
- CPAL speech classifier wiring — stays in codebase, activated in Phase 6
- Design spec and calibration methodology — reference documents

## What gets reverted

- Buffer gate removal (feed_audio, update_vad)
- Energy classifier gating in run_loops.py
- CPAL utterance dispatch changes (classify_during_production)
- Binary barge-in removal
