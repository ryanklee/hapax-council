# Voxtral → Kokoro TTS Migration

**Date:** 2026-04-02
**Status:** Approved

---

## 1. Problem

Voxtral (Mistral's autoregressive audio LLM) returns empty audio for short phrases — "Yeah.", "Got it.", "Thinking on that." This is architectural: autoregressive models lack context from 1-3 words to anchor generation. T1 acknowledgments from the signal cache fail silently. The voice pipeline appears responsive (session opens, LLM responds) but the operator hears nothing for short outputs.

## 2. Solution

Replace Voxtral with Kokoro 82M v1.0 (StyleTTS2 + iSTFTNet, non-autoregressive). Kokoro outputs 24kHz PCM int16 mono — identical to Voxtral's format. The migration is contained within `TTSManager` and its consumers.

**Why Kokoro:**
- 82M params, <1GB VRAM (vs 4B params, API-only for Voxtral)
- 96x realtime on GPU — 2-second utterance synthesizes in ~20ms
- Non-autoregressive: no short-phrase vulnerability
- Apache 2.0, #1 open-weight on TTS Arena (ELO 1071)
- 54 voice presets (no voice cloning — not needed, character comes from hardware chain)
- Was previously in the stack before PR #371

## 3. Audio Format Contract

Unchanged. All consumers expect:
- Raw bytes: PCM int16 little-endian
- Sample rate: 24000 Hz
- Channels: 1 (mono)
- Duration: `len(pcm) / (2 * 24000)` seconds

Kokoro native output is 24kHz — no resampling needed.

## 4. Files to Modify

### 4.1 `agents/hapax_daimonion/tts.py`

Replace `_synthesize_voxtral()` with `_synthesize_kokoro()`. Keep the `synthesize(text, use_case)` public interface unchanged.

- Remove Mistral client, `_get_client()`, `_ref_audio_b64`, float32→int16 conversion
- Add Kokoro pipeline initialization (lazy, on first call)
- Kokoro API: `pipeline = KPipeline(lang_code="a")` for American English, `pipeline(text, voice="af_heart")` returns generator of (graphemes, phonemes, audio_tensor) tuples
- Convert audio tensor (float32 numpy) to int16 PCM bytes
- Voice selection: map `voice_id` config to Kokoro voice preset names

### 4.2 `agents/hapax_daimonion/config.py`

- Rename `voxtral_voice_id` → `tts_voice` (default: `"af_heart"`)
- Remove `voxtral_ref_audio` (no cloning in Kokoro)
- Keep `tts_bar_aligned` and `tts_lookahead_bars` (TTS pacing, not model-specific)

### 4.3 `agents/hapax_daimonion/daemon.py`

- Update `TTSManager` instantiation to use new config field names

### 4.4 `agents/hapax_daimonion/pipecat_tts.py`

- Rename `VoxtralTTSService` → `KokoroTTSService`
- Update to use Kokoro synthesis internally

### 4.5 `agents/hapax_daimonion/pipeline.py`

- Update `_build_tts()` to return `KokoroTTSService`
- Update sample rate constant name (`VOXTRAL_SAMPLE_RATE` → `TTS_SAMPLE_RATE = 24000`)

### 4.6 `agents/hapax_daimonion/consent_session_runner.py`

- Update to use renamed TTS builder

### 4.7 `agents/demo_pipeline/voice.py`

- Replace direct Mistral API calls with Kokoro synthesis
- Remove `check_voxtral_available()`, add `check_kokoro_available()`

### 4.8 `pyproject.toml`

- Add `kokoro>=0.9` dependency
- Keep `mistralai` (used elsewhere for Codestral/other Mistral models)

### 4.9 Tests

- Update `tests/test_hapax_daimonion_tts.py` — mock Kokoro pipeline instead of Mistral client
- Un-skip `tests/test_demo_timeline.py` Kokoro test

## 5. Kokoro Voice Presets

Kokoro v1.0 provides 54 voices. Relevant presets for conversational use:

| Preset | Gender | Style | Notes |
|--------|--------|-------|-------|
| `af_heart` | Female | Warm, conversational | Default recommendation |
| `af_bella` | Female | Clear, professional | Alternative |
| `am_adam` | Male | Neutral | Male option |
| `bf_emma` | Female | British | If British accent desired |

Config `tts_voice` maps directly to Kokoro preset name.

## 6. Presynthesis Impact

Signal cache (12 phrases) + bridge engine (52 phrases) = 64 phrases presynthesized at startup.

- **Voxtral**: 64 × ~500ms API call + 0.2s sleep = ~45 seconds startup cost
- **Kokoro**: 64 × ~20ms local synthesis = ~1.3 seconds startup cost

**34x faster presynthesis.** No rate limiting, no API key, no network dependency.

## 7. What's Dropped

- Voice cloning (Voxtral `ref_audio` parameter) — not in use (`voxtral_ref_audio = ""`)
- Mistral API dependency for TTS (kept for other Mistral services)
- Float32 streaming decode (Kokoro returns numpy arrays directly)

## 8. What's Unchanged

- `synthesize(text, use_case) -> bytes` interface
- PCM int16 24kHz mono output format
- `pw-cat --playback --raw --format s16 --rate 24000` command
- Signal cache categories and phrases
- Bridge engine phrases and selection logic
- TTS executor and beat-aligned playback
- All downstream audio consumers
