# Delete CognitiveLoop — CPAL as Sole Conversation Coordinator

**Date:** 2026-04-02
**Status:** Approved — ready for implementation planning

---

## 1. Problem

Two conversation coordinators run simultaneously: CognitiveLoop (legacy) and CpalRunner. Both poll ConversationBuffer for utterances, both process speech, both publish perception behaviors. The `use_cpal` config flag creates conditional branches throughout `run_inner.py`, `session_events.py`, and `pipeline_start.py`. CPAL was designed as the replacement but CognitiveLoop was never removed, causing:

- Race conditions on utterance polling (both consume from the same buffer)
- Engagement path confusion (CPAL's callback doesn't open sessions, legacy's does)
- Dead code paths behind `use_cpal` flag
- Unclear ownership of session lifecycle, turn phase, buffer activation

## 2. Solution

Delete CognitiveLoop entirely. CPAL owns the full conversation lifecycle. Remove `use_cpal` flag — there is no legacy path.

## 3. Files to Delete

| File | Reason |
|------|--------|
| `agents/hapax_daimonion/cognitive_loop.py` | Replaced by CpalRunner |

## 4. Files to Modify

### 4.1 `agents/hapax_daimonion/config.py`

Remove `use_cpal` field from `DaimonionConfig`. No flag, no conditional.

### 4.2 `agents/hapax_daimonion/run_inner.py`

Remove all `if daemon.cfg.use_cpal` / `else` branches. The remaining code is the CPAL-only path:

- Always create CpalRunner (current CPAL block)
- Always use `on_engagement_detected` (renamed from `on_engagement_detected_cpal`)
- Always start CPAL runner + impingement consumer as background tasks
- Always presynthesized signal cache (keep bridge presynthesis too — it's needed for wake greetings)
- Remove legacy `engagement_processor` and `impingement_consumer_loop` task creation

Session timeout check (currently gated on `not use_cpal`): move into CPAL runner's tick.

### 4.3 `agents/hapax_daimonion/session_events.py`

- Delete `on_engagement_detected` (legacy callback that just sets signal)
- Delete `engagement_processor` (legacy coroutine that waits on signal → opens session → starts pipeline)
- Rename `on_engagement_detected_cpal` → `on_engagement_detected`
- Add session open to the engagement callback: when engagement fires and no session active, open session, activate buffer, ensure pipeline exists
- Add axiom veto check from legacy `engagement_processor` (the compliance gate)

### 4.4 `agents/hapax_daimonion/pipeline_start.py`

- Delete `_start_cognitive_loop()` function
- Delete `CognitiveLoop` import
- In `start_conversation_pipeline()`: remove the cognitive loop creation. Pipeline is created and wired to CPAL runner via `set_pipeline()`. No CognitiveLoop wrapping.

### 4.5 `agents/hapax_daimonion/run_loops.py`

- Keep `audio_loop` with the inline engagement check (it's the only engagement path now)
- Remove the duplicate `engagement_processor` function (if still present)
- Clean up any `use_cpal` references

### 4.6 `agents/hapax_daimonion/cpal/runner.py`

Add three responsibilities previously owned by CognitiveLoop:

**A. Session lifecycle in `_tick()`:**
```
if utterance detected and not session.is_active:
    session.open(trigger="engagement")
    buffer.activate()

if session.is_active and silence > silence_timeout_s:
    session.close()
    buffer.deactivate()
    session.mark_activity() reset
```

**B. Session activity marking:**
During utterance processing or TTS playback, call `session.mark_activity()` to prevent premature timeout.

**C. Perception behavior publishing:**
CognitiveLoop published 4 behaviors: `turn_phase`, `cognitive_readiness`, `conversation_temperature`, `predicted_tier`. CPAL publishes simplified equivalents:
- `turn_phase`: `"hapax_speaking"` during TTS, `"mutual_silence"` otherwise
- `cognitive_readiness`: `1.0` when pipeline exists, `0.0` otherwise
- `conversation_temperature`: `0.0` (dropped — conversation model not ported)
- `predicted_tier`: `""` (dropped — speculative routing not ported)

### 4.7 `agents/hapax_daimonion/daemon.py`

- Remove `_cognitive_loop` attribute
- Remove any `CognitiveLoop` imports

## 5. Engagement Flow (Post-Migration)

```
[Operator speaks]
    ↓
[audio_loop: VAD detects speech (confidence ≥ 0.3)]
    ↓
[audio_loop: inline engagement check — presence=PRESENT, no active session]
    ↓
[EngagementClassifier.on_speech_detected(behaviors)]
    ↓
[on_engagement_detected(daemon)]
    ├─ Axiom veto check (compliance gate)
    ├─ Boost CPAL gain
    ├─ Open session (daemon.session.open)
    ├─ Activate conversation buffer
    └─ Ensure pipeline exists (daemon._start_pipeline → set_pipeline on runner)
    ↓
[ConversationBuffer accumulates speech frames, detects utterance boundary]
    ↓
[CpalRunner._tick() polls: utterance = perception.get_utterance()]
    ↓
[CpalRunner._process_utterance(utterance)]
    ├─ T0: Visual signal
    ├─ T1: Acknowledgment (presynthesized PCM)
    └─ T3: pipeline.process_utterance(utterance) → STT → LLM → TTS → audio
    ↓
[Session timeout: no utterance for silence_timeout_s → session.close()]
```

## 6. What's Intentionally Dropped

| Feature | Reason | Recovery path |
|---------|--------|---------------|
| Speaker verification | Single operator, no guests | Add to CPAL when multi-person needed |
| Active silence / wind-down | Nicety, not necessity | Add as CPAL tick behavior |
| Conversation temperature | Fed spontaneous speech which works via impingements | Port ConversationalModel if needed |
| 5-phase turn tracking | CPAL uses 2-state (producing/not-producing) | Extend if finer phases needed |
| Speculative STT sophistication | CPAL does basic speculation | Enhance incrementally |

## 7. Testing

- Smoke test: operator speaks → hapax responds with audio
- Session opens on engagement, closes on silence timeout
- `grep -r CognitiveLoop` returns zero hits
- `grep -r use_cpal` returns zero hits
- Existing perception tests pass (behaviors still published)
- Engagement → session → utterance → STT → LLM → TTS → playback verified in logs
