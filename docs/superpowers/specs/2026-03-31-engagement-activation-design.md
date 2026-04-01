# Engagement-Based Activation Model

**Date:** 2026-03-31
**Status:** Design
**Replaces:** Wake word detection (WakeWordDetector, WhisperWakeWord, openWakeWord)

## Problem

The wake word paradigm ("Hey Hapax") implies the system is asleep until summoned. This contradicts the daimonion's design as a continuous cognitive presence. The operator should not need to summon the system — it should already be attending when the operator is present, and should speak when it has something worth saying.

## Design Principles

1. **The system is always attending when the operator is present.** No summons needed.
2. **The system speaks when it has something worth saying.** Proactive, not reactive-only.
3. **Hotkey exists as escape hatch**, not primary activation.
4. **Graceful degradation.** If any signal is unavailable, fall back to remaining signals. Never hard-fail.
5. **Consent is preserved.** Guest detection and consent gating remain unchanged.

## Architecture

### Engagement Classifier (replaces WakeWordDetector)

Three-stage pipeline running continuously when operator is present. Each stage is a filter — speech only reaches the next stage if the prior stage passes.

#### Stage 1: Speech gate (always on, ~0ms latency)

VAD (Silero, already running in audio loop) detects human speech. If no speech, nothing happens. Zero additional compute. This is the existing `PresenceDetector.process_audio()` path.

**Gate:** VAD confidence >= 0.5 for >= 3 frames (~90ms). Same as current SPEECH_START threshold.

#### Stage 2: Directed-speech classifier (~300ms)

When VAD fires AND `BayesianPresenceEngine.state == PRESENT`, run a lightweight multi-signal check. Any single signal passing is sufficient (OR logic with confidence weighting).

**Signal 2a: Conversation context window**
If the system spoke within the last 30 seconds, any operator speech is assumed directed. No classification needed — just a timestamp check against `session.last_tts_end`.

Implementation: `time.monotonic() - self._last_system_speech < 30.0`

**Signal 2b: Phone call exclusion**
If `phone_call_active` behavior is True, suppress activation. Operator is talking to someone else.

Implementation: read from perception behaviors dict (already available in audio loop context).

**Signal 2c: Head orientation**
If IR presence backend reports `ir_gaze_zone == "desk"` or `ir_screen_looking == True`, operator is facing the system. Combined with speech, this strongly indicates directed speech.

Implementation: read from perception state (2.5s cadence, already flowing). Accept staleness up to 5s.

**Signal 2d: Activity mode exclusion**
If `activity_mode` is `meeting` or `phone_call`, suppress. Operator is engaged elsewhere.

Implementation: read from perception behaviors (already in ContextGate, move check earlier).

**Fusion:** Weighted OR. Any positive signal (2a, 2c) activates. Any negative signal (2b, 2d) suppresses. If no signals available (camera down, no phone data), fall through to Stage 3.

Confidence score: `engagement_score = max(context_window_score, gaze_score) * (1 - phone_active) * (1 - meeting_active)`

**Threshold:** `engagement_score >= 0.4` → proceed to activation. `engagement_score < 0.2` → suppress. Between 0.2 and 0.4 → Stage 3.

#### Stage 3: Semantic confirmation (~500ms, only when Stage 2 ambiguous)

Buffer 1-2s of speech audio (pre-roll buffer already exists in ConversationBuffer). Run speculative STT on the buffered audio. Feed transcript to salience router.

**Gate:** `activation_score >= 0.3` → directed (engage). Below 0.3 → background speech (suppress).

This reuses the existing speculative STT + salience router infrastructure. Currently this runs AFTER session open (cognitive loop OPERATOR_SPEAKING phase). Here it runs BEFORE session open as a gate.

Implementation: `ResidentSTT.transcribe(buffered_audio)` → `SalienceRouter.route(transcript)` → check `breakdown.final_activation`.

### Activation path (new)

```
audio_loop frame (30ms)
    |
    v
VAD (Silero) -- Stage 1
    | speech detected
    v
BayesianPresenceEngine.state == PRESENT?
    | yes
    v
EngagementClassifier.evaluate() -- Stage 2
    | check context_window, phone_call, gaze, activity_mode
    | engagement_score >= 0.4 --> ACTIVATE
    | engagement_score < 0.2  --> SUPPRESS
    | 0.2-0.4                 --> Stage 3
    v
Speculative STT + Salience -- Stage 3 (only when ambiguous)
    | activation_score >= 0.3 --> ACTIVATE
    | activation_score < 0.3  --> SUPPRESS
    v
ContextGate.check() -- existing vetoes (session_active, stress, drowsiness, etc.)
    | eligible
    v
SessionManager.open(trigger="engagement")
    v
start_conversation_pipeline()
```

### Follow-up window

After a session closes (30s silence timeout), maintain a 30s follow-up window. During this window, Stage 2 threshold drops to 0.1 — any speech from a present operator re-engages.

Implementation: `self._follow_up_until = time.monotonic() + 30.0` set on session close.

### Proactive speech gate

The other half of not relying on hotkey: the system speaks first.

The proactive path exists: DMN impingement → affordance pipeline → speech capability → TTS. The missing piece is a well-tuned gate for when to actually speak.

**Proactive gate conditions (all must be true):**

1. Operator is present (`presence_engine.state == PRESENT`)
2. Operator is not in focused production (`activity_mode not in ("production", "meeting", "phone_call")`)
3. Impingement salience exceeds threshold (`strength >= 0.7`)
4. System hasn't spoken proactively in the last 5 minutes (prevent pestering)
5. No active phone call
6. Stimmung is not critical
7. No active voice session (don't interrupt an ongoing conversation)

**Proactive cooldown:** 5 minutes between unsolicited utterances. Resets when operator initiates conversation (showing receptivity).

Implementation: add these checks to `_proactive_delivery_gate()` in `run_loops_aux.py` or equivalent. Most conditions are already readable from perception state and behaviors dict.

## What gets deleted

- `agents/hapax_daimonion/wake_word.py` — base class
- `agents/hapax_daimonion/wake_word_whisper.py` — Whisper-based wake word
- `agents/hapax_daimonion/wake_word_porcupine.py` — Porcupine wake word
- References to `openWakeWord` ONNX model
- `wake_word_engine` config option
- Wake word processing in audio loop (`run_loops.py`)
- Wake word loading in `run_inner.py`

## What gets created

- `agents/hapax_daimonion/engagement.py` — `EngagementClassifier` class (~120 lines)
  - `process_audio(frame)` — feeds VAD, triggers evaluation when speech detected
  - `evaluate()` — runs Stage 2 + Stage 3 pipeline
  - `_check_context_window()` → float
  - `_check_gaze()` → float
  - `_check_exclusions()` → float (phone, meeting)
  - `_speculative_classify(audio)` → float (Stage 3)
  - Callback: `on_engagement_detected` (same interface as `on_wake_word`)

## What gets modified

- `agents/hapax_daimonion/run_loops.py` — replace wake word frame distribution with engagement classifier
- `agents/hapax_daimonion/run_inner.py` — replace wake word loading with engagement classifier init
- `agents/hapax_daimonion/session_events.py` — replace `on_wake_word` with `on_engagement_detected`
- `agents/hapax_daimonion/config.py` — remove `wake_word_engine`, add engagement thresholds
- `agents/hapax_daimonion/daemon.py` — replace `wake_word` attribute with `engagement`
- `agents/hapax_daimonion/run_loops_aux.py` — tune proactive delivery gate conditions

## What stays unchanged

- ContextGate (still runs on activation, same vetoes)
- SessionManager (still manages session lifecycle)
- BayesianPresenceEngine (still provides presence signal)
- CognitiveLoop (still runs after session opens)
- ConversationPipeline (still processes utterances)
- Hotkey server (still provides escape hatch)
- Consent system (still gates guest interactions)

## Deferred (v2)

- Personalized prosodic register learning (operator's "device voice")
- Dedicated DDSD model fine-tuned on operator speech
- Full-duplex semantic VAD (0.5B model predicting turn-control tokens)
- Adaptive session timeout based on engagement level
- Adaptive proactive cooldown based on operator receptivity patterns

## Research basis

- Apple DDSD (2023-2025): multi-signal fusion achieves 7.5% EER, prosody adds 8.5% improvement
- Amazon Natural Turn-Taking: head orientation + acoustic fusion for conversation mode
- CHI 2025 "Inner Thoughts": continuous covert deliberation drives proactive timing (82% preference over turn prediction)
- Meta EMNLP 2024: full-duplex synchronous LLMs — the direction for v2
- Frontiers 2021: humans develop routinized device-directed speech register — learnable for single operator
- Apple modality dropout (NeurIPS 2024): train for graceful degradation when signals are missing

## Testing

1. **Stage 1 only (VAD gate):** Verify speech detection fires correctly — should already work.
2. **Stage 2a (context window):** System speaks, operator responds within 30s → auto-engage.
3. **Stage 2c (gaze):** Operator faces desk and speaks → engage. Operator faces away and speaks → suppress.
4. **Stage 2b/2d (exclusions):** Simulate phone call → verify suppression.
5. **Stage 3 (semantic):** Speak a system-relevant sentence → engage. Speak a self-directed mutter → suppress.
6. **Proactive gate:** Write high-salience impingement → verify system speaks within 60s.
7. **False positive rate:** Run for 1 hour of normal work. Count false activations. Target: < 2/hour.
8. **Hotkey fallback:** Verify hotkey still opens session regardless of classifier state.
