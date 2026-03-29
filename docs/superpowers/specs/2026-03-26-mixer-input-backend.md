# Mixer Master Input Backend

**Date:** 2026-03-26
**Status:** Design approved
**Depends on:** PipeWire routing (mixer_master node, configured)

## Summary

A new perception backend that captures the mixer master output via the Studio 24c left channel. Provides clean, direct audio analysis signals — beat detection, RMS energy, spectral analysis — from the actual production output rather than airborne mic capture. This is the authoritative music signal for the visual governance system.

## Why

The current `audio_energy_rms` and `audio_beat` come from the `StudioIngestionBackend` which captures airborne audio via the Blue Yeti every 12 seconds. This is:
- Delayed (12s capture window)
- Contaminated (room acoustics, ambient noise, voice)
- Low-resolution (single RMS value per 12s window)

The mixer master output is:
- Real-time (frame-by-frame at 48kHz)
- Clean (direct line-level, no room acoustics)
- High-resolution (per-frame RMS, onset detection, spectral bands)

## PipeWire Routing

Already configured. The Studio 24c stereo input is split:
- `contact_mic` — right channel (FR), Input 2, contact microphone
- `mixer_master` — left channel (FL), Input 1, mixer master output

Both are mono PipeWire virtual sources available via `pactl set-default-source`.

## Component: MixerInputBackend

**File:** `agents/hapax_daimonion/backends/mixer_input.py`

### Architecture

Same pattern as ContactMicBackend: daemon thread captures audio via PyAudio (default source set to `mixer_master` via pactl), computes DSP per frame, writes to thread-safe cache. `contribute()` reads cache in <1ms (FAST tier).

### Behaviors Provided

| Behavior | Type | Range | Description |
|----------|------|-------|-------------|
| `mixer_energy` | float | 0.0-1.0 | RMS energy of mixer output (smoothed) |
| `mixer_beat` | float | 0.0-1.0 | Beat/onset detection pulse (fast attack, slow decay) |
| `mixer_bass` | float | 0.0-1.0 | Sub-250Hz band energy (for displacement/scale modulation) |
| `mixer_mid` | float | 0.0-1.0 | 250-2000Hz band energy (for texture/motion modulation) |
| `mixer_high` | float | 0.0-1.0 | 2000Hz+ band energy (for brightness/sparkle modulation) |
| `mixer_active` | bool | true/false | Whether mixer is outputting signal above noise floor |

### DSP Pipeline

1. **RMS energy** — same as contact mic, exponential smoothing (α=0.3)
2. **Onset/beat detection** — adaptive threshold crossing (same as calibrated contact mic approach). When RMS spikes above 1.5× slow baseline → beat pulse = 1.0, then exponential decay (×0.85 per frame). This produces a clean kick-locked pulse from the direct audio.
3. **3-band spectral split** — single 1024-point FFT per frame, sum magnitude in three bands:
   - Bass: 0-250 Hz (bins 0-5 at 48kHz/1024)
   - Mid: 250-2000 Hz (bins 5-42)
   - High: 2000-8000 Hz (bins 42-170)
   - Normalize each band to 0-1 via peak tracking with slow decay
4. **Activity detection** — `mixer_active = True` when RMS > noise floor threshold (calibrate from silence)

### Sample Rate

48kHz (native mixer output rate — no resampling needed, higher quality than contact mic's 16kHz). FFT size 1024 gives 46.9 Hz frequency resolution and 21.3ms frame time.

### Device Access

Same `pactl set-default-source` pattern as ContactMicBackend. The backend sets `mixer_master` as default, captures, then the next backend to capture restores its own default. Since both backends run in separate daemon threads and PipeWire handles fan-out natively, they don't conflict.

**Actually:** both backends setting default source would race. Better approach: each backend captures from the PipeWire `pulse` device but targets a specific source via `PULSE_SOURCE` environment variable or `pa_context_set_default_source` before opening. Simplest: set default source once at startup based on which backend starts first, and have the other use a named device.

**Simplest correct approach:** The MixerInputBackend uses `pw-record --target mixer_master` via subprocess pipe instead of PyAudio. This avoids the default-source race entirely — `pw-record` targets the node by name. The ContactMicBackend already uses the default source. No conflict.

### Registration

Added to `_register_perception_backends()` in `__main__.py`:

```python
try:
    from agents.hapax_daimonion.backends.mixer_input import MixerInputBackend
    self.perception.register_backend(MixerInputBackend())
except Exception:
    log.info("MixerInputBackend not available, skipping")
```

### Perception State Export

Add to `_perception_state_writer.py`:

```python
"mixer_energy": _safe_float(_bval("mixer_energy", 0.0)),
"mixer_beat": _safe_float(_bval("mixer_beat", 0.0)),
"mixer_bass": _safe_float(_bval("mixer_bass", 0.0)),
"mixer_mid": _safe_float(_bval("mixer_mid", 0.0)),
"mixer_high": _safe_float(_bval("mixer_high", 0.0)),
"mixer_active": bool(_bval("mixer_active", False)),
```

### Compositor Integration

Add to OverlayData:

```python
mixer_energy: float = 0.0
mixer_beat: float = 0.0
mixer_bass: float = 0.0
mixer_mid: float = 0.0
mixer_high: float = 0.0
mixer_active: bool = False
```

Add to signals dict:

```python
signals["mixer_energy"] = data.mixer_energy
signals["mixer_beat"] = data.mixer_beat
signals["mixer_bass"] = data.mixer_bass
signals["mixer_mid"] = data.mixer_mid
signals["mixer_high"] = data.mixer_high
```

### Impact on Visual Governance

The default modulation template gains richer signal sources:

- `mixer_bass` → bloom.alpha, displacement (bass = weight, per crossmodal research)
- `mixer_mid` → drift.speed, trail.opacity (mids = motion, texture)
- `mixer_high` → noise_overlay.intensity, vignette.strength (highs = sparkle, detail)
- `mixer_beat` replaces `audio_beat` as the authoritative beat pulse (direct, not derived from energy)
- `mixer_energy` replaces `audio_rms` for overall intensity (clean signal)

The existing `audio_rms`/`audio_beat` from airborne capture remain available but become secondary — useful for detecting ambient/conversation energy when no music is playing.

## File Inventory

| Action | Path | Scope |
|--------|------|-------|
| Create | `agents/hapax_daimonion/backends/mixer_input.py` | Backend: capture, DSP, cache, behaviors |
| Create | `tests/hapax_daimonion/test_mixer_input_backend.py` | Unit tests |
| Edit | `agents/hapax_daimonion/__main__.py` | Register backend |
| Edit | `agents/hapax_daimonion/_perception_state_writer.py` | Export 6 mixer_* fields |
| Edit | `agents/studio_compositor.py` | OverlayData + signals dict |
| Edit | `presets/_default_modulations.json` | Update sources: mixer_bass → bloom, etc. |

## Testing

| Component | Method |
|-----------|--------|
| RMS computation | Unit test with synthetic PCM |
| Beat detection | Unit test: silence → loud spike → verify pulse |
| 3-band split | Unit test: synthetic sine at 100Hz, 1000Hz, 5000Hz → correct band |
| Activity detection | Unit test: below/above threshold |
| Backend protocol | Unit test: provides, contribute, available |
| Integration | Manual: play music through mixer, verify mixer_energy in perception-state.json |

## Constraints

- Capture uses `pw-record --target mixer_master` subprocess pipe (avoids PyAudio default-source race with ContactMicBackend)
- 48kHz sample rate, 1024-sample frames (21.3ms, ~47 fps)
- Spectral band boundaries hardcoded to standard VJ frequency splits (bass < 250Hz, mid 250-2kHz, high 2-8kHz)
- Beat pulse decay rate (0.85/frame) gives ~200ms release at 47fps — matches the asymmetric envelope principle
- mixer_active threshold needs calibration (run silence baseline, same as contact mic)
