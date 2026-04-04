# Audio Reactivity Expansion

## Goal

Make shader effects react to audio from the PreSonus Studio 24c with <50ms latency. Every beat hit, scratch, pad tap, and bass drop should produce an immediate visible response on the stream.

## Problem

The current signal path has 2.5-second latency:

```
24c → pw-cat (mixer_input backend, 21ms DSP frames)
  → perception loop (2.5s tick interval)
  → perception-state.json (file write)
  → compositor state loop (100ms poll)
  → modulator → shader
```

Audio-reactive visuals arrive 2.5 seconds after the sound. When OBS muxes this video with the live audio, viewers see the beat hit, then 2.5 seconds later see the visual response.

## Solution

### Direct PipeWire capture in the compositor process

Add a lightweight audio capture thread to the compositor that reads from `mixer_master` (PipeWire) and runs DSP inline. Signals feed directly into the modulator with zero file I/O.

```
24c → PipeWire → compositor audio thread (pw-cat subprocess, 21ms frames)
  → inline DSP (RMS, beat detect, 3-band split)
  → shared signal dict (thread-safe)
  → tick_modulator reads signals each frame (~42ms at 24fps)
  → shader uniforms update
```

**Total latency: ~60ms** (21ms audio frame + 42ms render frame).

### Architecture

New file: `agents/studio_compositor/audio_capture.py`

```python
class CompositorAudioCapture:
    """Captures mixer audio in compositor process for low-latency reactivity."""
    
    def __init__(self, target: str = "mixer_master", rate: int = 48000, chunk: int = 1024):
        self.signals = {
            "mixer_energy": 0.0,
            "mixer_bass": 0.0,
            "mixer_mid": 0.0,
            "mixer_high": 0.0,
            "mixer_beat": 0.0,
            "beat_pulse": 0.0,
        }
        self._lock = threading.Lock()
        # Spawns pw-cat subprocess, reads PCM, runs DSP
    
    def get_signals(self) -> dict[str, float]:
        """Thread-safe read of current audio signals."""
        with self._lock:
            return dict(self.signals)
```

DSP is the same as `mixer_input.py` (proven working): RMS energy, 3-band FFT split, beat detection via spike threshold.

### Signal flow change in tick_modulator

Currently `tick_modulator` reads from `compositor._overlay_state._data` (the 2.5s-stale perception state). Change it to read audio signals from the direct capture instead:

```python
def tick_modulator(compositor, t, energy, b):
    # Audio signals from direct capture (low latency)
    if hasattr(compositor, "_audio_capture"):
        audio = compositor._audio_capture.get_signals()
        signals.update(audio)
    # Non-audio signals still from perception state (flow, stimmung, etc.)
    ...
```

Non-audio signals (flow_score, stimmung, heart_rate, stress) stay on the perception-state.json path — they don't need low latency.

### Expanded modulation bindings

Current: 8 bindings, mostly conservative. New default set:

| Param | Signal | Scale | Offset | Effect |
|-------|--------|-------|--------|--------|
| bloom.alpha | mixer_bass | 0.5 | 0.1 | Bass → bloom explosion |
| bloom.alpha | beat_pulse | 0.3 | 0.0 | Beat hit → bloom flash |
| trail.opacity | mixer_energy | 0.4 | 0.2 | Energy → trail persistence |
| colorgrade.brightness | beat_pulse | 0.15 | 1.0 | Beat → brightness flash |
| colorgrade.saturation | mixer_mid | 0.4 | 1.0 | Mid freq → saturation boost |
| colorgrade.hue_rotate | desk_centroid | 30 | -15 | Spectral → hue shift |
| chromatic_aberration.offset_x | beat_pulse | 8 | 0 | Beat → chroma split |
| noise_overlay.intensity | mixer_high | 0.15 | 0.02 | Highs → noise/grain |
| vignette.strength | mixer_energy | -0.3 | 0.3 | Energy → vignette opens |
| fisheye.zoom | beat_pulse | 0.03 | 1.0 | Beat → subtle zoom punch |
| warp.slice_amplitude | desk_onset_rate | 2 | 0 | Onsets → glitch displacement |
| drift.speed | desk_onset_rate | 0.1 | 0 | Onsets → drift speed |

### OBS audio sync

With <50ms visual latency, OBS's natural A/V mux will be close enough — human perception threshold for audio-visual sync is ~45ms for music, ~100ms for speech. No audio delay needed in OBS.

## Files

| File | Action |
|------|--------|
| `agents/studio_compositor/audio_capture.py` | Create — PipeWire capture + DSP |
| `agents/studio_compositor/fx_tick.py` | Modify — read direct audio signals |
| `agents/studio_compositor/compositor.py` | Modify — init audio capture |
| `presets/_default_modulations.json` | Modify — expand to 12 bindings |

## What this does NOT include

- MIDI input reactivity (OXI One) — future
- Per-preset custom modulation profiles — future (presets already support per-graph modulations)
- Sidechain-style ducking (audio gates visual intensity) — future
- Audio-to-video latency measurement tool — future
