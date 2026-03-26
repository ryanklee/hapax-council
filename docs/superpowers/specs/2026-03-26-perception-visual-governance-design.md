# Perception-Visual Governance

**Date:** 2026-03-26
**Status:** Design approved
**Depends on:** Contact Mic Integration (merged), Effect Graph System (compositor session, in progress)

## Summary

A three-tier governance system that makes the compositor's visual effects breathe with the operator's production session. Atmospheric signals select which effect preset is active. Gestural signals adjust parameters within that preset. Rhythmic signals modulate shader uniforms frame-by-frame. A breathing substrate ensures the system is never visually dead.

## Architecture

Three independent layers, each at its own timescale, composing downward into the existing effect graph runtime:

```
ATMOSPHERIC (minutes+)           GESTURAL (1-10s)              RHYTHMIC (sub-second)
stimmung stance                  desk_activity                  desk_energy (32 Hz)
operator_energy/stress           production_activity            desk_onset_rate (32 Hz)
music_genre                      gaze_direction                 beat_position (24 PPQN)
circadian_alignment              detected_action                sink_volume
sleep_quality                    person_count
        │                               │                              │
        ▼                               ▼                              ▼
┌─────────────────┐          ┌────────────────────┐         ┌──────────────────┐
│ Preset Selector │          │ Effect Mix Governor │         │ UniformModulator │
│ (state machine) │──graph──▶│ (parameter offsets) │──patch─▶│ (expanded inputs)│
└─────────────────┘          └────────────────────┘         └──────────────────┘
                                                                    │
                                                                    ▼
                                                           GStreamer uniforms
                                                           (GPU render @ 60Hz)
```

Each tier only talks downward. Atmospheric selects the graph. Gestural nudges parameters within that graph. Rhythmic modulates frame-by-frame within those parameters. No tier reaches into another's domain.

## Design Principles

1. **One reactive channel per visual parameter.** desk_energy → bloom. onset_rate → stutter. beat_position → rotation. Never one signal driving everything.
2. **Asymmetric envelopes everywhere.** Fast attack, slow release. Built into smoothing values: low smoothing (0.3) for beat_pulse, high smoothing (0.95) for stress.
3. **Perlin noise on every parameter at rest.** 1-3% wobble below 1 Hz. Nothing perfectly still.
4. **Phase-offset multiple parameters.** Different smoothing rates create natural decorrelation.
5. **Beat-lock the punctuation, free-run the atmosphere.** Kick-driven displacement locks to clock. Color drift runs free.
6. **Magnitude → magnitude, quality → quality.** Amplitude → brightness (prothetic). Spectral content → hue (metathetic). Never cross the boundary.
7. **Silence is a visual event.** When signal drops, visuals settle slowly with their own decay envelope.
8. **Stimmung modulates the dynamic range ceiling.** Not just intensity but complexity.
9. **Contact mic = physical layer. Audio = musical layer.** Two independent reactive vocabularies.
10. **Temporal complexity over temporal precision.** 5-20ms jitter in sync improves perceived naturalness.

## Component 1: Atmospheric Layer — Preset Selection State Machine

**File:** `agents/effect_graph/visual_governance.py`

A state machine that maps atmospheric signals to preset families. Transitions have minimum 30s dwell time with 3-5s dissolve crossfade between presets.

### State Matrix

States derive from two axes — stimmung stance and energy level:

| | Low Energy (idle/typing) | Medium Energy (tapping/mixing) | High Energy (drumming/scratching) |
|---|---|---|---|
| **NOMINAL** | clean, ambient | trails, ghost | feedback, kaleidodream |
| **CAUTIOUS** | ambient | ghost | trails |
| **DEGRADED** | dithered_retro, vhs | vhs | screwed |
| **CRITICAL** | silhouette | silhouette | silhouette |

Each cell is a **preset family** — a ranked list. The first available preset loads. Genre signal modulates within the family:

- Hip hop / trap → favor trap, screwed, ghost (dark, lo-fi)
- Lo-fi / jazz / soul → favor vhs, dithered_retro, ambient (warm, analog)
- Electronic / ambient → favor voronoi_crystal, tunnel_vision, kaleidodream (geometric, procedural)

### Transition Behavior

- Atmospheric transitions: 3-5s dissolve crossfade between presets
- Minimum dwell: 30s before another atmospheric transition (prevents oscillation)
- Stimmung stance changes bypass dwell time (system health is urgent)
- Energy level derived from `desk_activity`: idle/typing = low, tapping = medium, drumming/scratching = high

### Type

```python
@dataclass(frozen=True)
class PresetFamily:
    """Ranked list of preset names for a state cell."""
    presets: tuple[str, ...]

    def first_available(self, loaded_presets: set[str]) -> str | None:
        for p in self.presets:
            if p in loaded_presets:
                return p
        return None
```

## Component 2: Gestural Layer — Effect Mix Governor

A function in `visual_governance.py` called from the compositor's perception tick. Adjusts node parameters based on gestural signals. Works within whatever preset the atmospheric layer selected.

### Activity-Driven Parameter Offsets

| Activity Transition | Parameter Changes | Envelope |
|---|---|---|
| → scratching | trail.opacity +0.2, bloom.alpha +0.15, drift.speed ×2 | 1s attack |
| → drumming | bloom.alpha +0.2, stutter.freeze_chance +0.1 | 500ms attack |
| → tapping (pads) | trail.opacity +0.1, bloom.alpha +0.1 | 800ms attack |
| → typing | All modulation depth reduced 50% | 2s attack (settling) |
| → idle | All parameters drift toward preset defaults | 5s release (slow settle) |
| Any → idle | Perlin noise amplitude increases (system breathes more in silence) | 3s |

These are **additive offsets** to the preset's base parameters, not absolute values.

### Contextual Modifiers

**Gaze-driven emphasis:**
- `hardware` → boost hardware-camera tile brightness/saturation
- `screen` → reduce effect intensity (operator is reading, don't distract)
- `away` → increase ambient drift (nobody watching, let the visuals wander)

**Person count:**
- 0 people → effects more experimental/aggressive
- 1 person → standard reactivity
- 2+ people → reduce intensity, consent-aware restraint

### Implementation

`apply_gestural_offsets(base_params, perception_state) -> patched_params` — pure function. Returns `{(node_id, param_name): offset_value}`.

## Component 3: Rhythmic Layer — Expanded Modulator Signals

The existing `UniformModulator` is unchanged. The `signals` dict expands from 4 to ~12.

### New Signals

| Signal | Source | Range | Smoothing | Visual Role |
|---|---|---|---|---|
| `desk_energy` | ContactMicBackend | 0.0-1.0 | 0.85 | Primary amplitude — bloom, glow, intensity |
| `desk_onset_rate` | ContactMicBackend | 0.0-~20.0 | 0.7 | Strike frequency — stutter, noise burst, pulse |
| `desk_centroid` | ContactMicBackend | 0.0-1.0 (normalized) | 0.9 | Timbre → hue shift (quality→quality) |
| `beat_phase` | MIDI clock | 0.0-1.0 sawtooth/beat | 0.0 (raw) | Phase-locked rotation, cycling |
| `bar_phase` | MIDI clock | 0.0-1.0 sawtooth/bar | 0.0 (raw) | Bar-level transitions |
| `beat_pulse` | Derived | 0→1 spike, fast decay | 0.3 | Kick-locked bloom burst, displacement |
| `heart_rate` | Watch | 0.0-1.0 (normalized) | 0.95 | Breathing rate, organic rhythm |
| `stress` | Stimmung | 0.0-1.0 | 0.95 | Warmth/coolness, chromatic aberration |
| `perlin_drift` | time-derived | -0.03 to +0.03 | 0.0 (raw) | Breathing substrate wobble |

### Derived Signal Computation

```python
# Beat pulse: spike on downbeat, exponential decay
if beat_phase < prev_beat_phase:  # phase wrapped (new beat)
    beat_pulse_raw = 1.0
beat_pulse_raw *= 0.85  # decay per frame (~200ms release at 60fps)

# Bar phase: normalize beat position to 0-1 per bar
bar_phase = (beat_position % beats_per_bar) / beats_per_bar

# Centroid normalization: Hz to 0-1
desk_centroid = min(1.0, desk_spectral_centroid / 4000.0)

# Perlin drift: slow noise, scales inversely with activity
base_drift = noise(time * 0.1) * 0.03
activity_suppression = min(1.0, desk_energy * 5.0)
perlin_drift = base_drift * (1.0 - activity_suppression)
```

### Default Modulation Template

File: `agents/shaders/presets/_default_modulations.json`

```json
{
  "default_modulations": [
    {"param": "bloom.alpha", "source": "desk_energy", "scale": 0.3, "offset": 0.0, "smoothing": 0.85},
    {"param": "bloom.alpha", "source": "beat_pulse", "scale": 0.15, "offset": 0.0, "smoothing": 0.3},
    {"param": "trail.opacity", "source": "desk_energy", "scale": 0.2, "offset": 0.0, "smoothing": 0.85},
    {"param": "colorgrade.hue_rotate", "source": "desk_centroid", "scale": 30.0, "offset": -15.0, "smoothing": 0.92},
    {"param": "drift.speed", "source": "desk_onset_rate", "scale": 0.1, "offset": 0.0, "smoothing": 0.8},
    {"param": "breathing.rate", "source": "heart_rate", "scale": 1.5, "offset": 0.3, "smoothing": 0.95},
    {"param": "noise_overlay.intensity", "source": "stress", "scale": 0.05, "offset": 0.0, "smoothing": 0.95},
    {"param": "vignette.strength", "source": "perlin_drift", "scale": 1.0, "offset": 0.0, "smoothing": 0.0}
  ]
}
```

Template binds only to nodes present in the active graph — missing nodes silently skipped. Preset's own bindings for the same `(node, param)` win.

## Component 4: Breathing Substrate

### Perlin Drift Signal

`perlin_drift = noise(time * 0.1) * 0.03` fed as modulation source. Amplitude scales inversely with signal activity: high desk_energy → drift approaches zero. Quiet → drift is the only thing moving.

### Idle Escalation

When `desk_activity == "idle"` for >60s, drift amplitude increases from 3% toward 8% over 5 minutes. Resets instantly on any onset.

### Silence as Decay

When rhythmic signals drop, modulated parameters decay along release envelopes (smoothing 0.85-0.95). The visual equivalent of a struck bell.

## Integration with Compositor Session

Three additive touch points:

1. **Signals dict expansion** — Add ~8 entries to the `signals` dict in `studio_compositor.py` by reading from `perception-state.json`.
2. **Graph loading hook** — Atmospheric preset selector calls `runtime.load_graph()` on transitions.
3. **Default modulation merge** — ~10 lines in graph loader to merge `_default_modulations.json`. Preset's own bindings win.

**NOT touched:** SlotPipeline, UniformModulator internals, any shader GLSL, any existing preset JSON, contact_mic.py, vision.py, any frontend code.

### Re-adjustment Plan

When compositor session merges:
1. Check `signals` dict location/shape — update insertion point
2. Check preset loading path — update template merge location
3. New presets inherit defaults automatically
4. Run tests

## File Inventory

| Action | Path | Purpose |
|--------|------|---------|
| Create | `agents/effect_graph/visual_governance.py` | Atmospheric state machine + gestural offset logic |
| Create | `agents/shaders/presets/_default_modulations.json` | Default modulation template |
| Create | `tests/effect_graph/test_visual_governance.py` | Unit tests |
| Edit | `agents/studio_compositor.py` | Expand signals dict, call governance per tick, merge default modulations |
| Edit | `agents/effect_graph/runtime.py` | Default modulation template merge in `load_graph()` |
| Edit | `agents/effect_graph/types.py` | Add `PresetFamily` type |

## Testing

| Component | Method |
|-----------|--------|
| Atmospheric state machine | Unit test: stance × energy → expected preset family. Dwell enforcement. Stance bypass. |
| Gestural offsets | Unit test: activity → expected parameter offsets. Additive. Gaze/person modifiers. |
| Signal expansion | Unit test: mock perception state → expected signals dict. Derived signals correct. |
| Default modulation merge | Unit test: preset inherits defaults. Override wins. Missing nodes skipped. |
| Breathing substrate | Unit test: idle >60s → drift increases. Activity → reset. Signal suppresses drift. |
| Integration | Manual: verify perception signals modulate shader parameters in real-time. |

## Constraints

- Atmospheric transitions minimum 30s dwell prevents visual thrashing
- Default modulation template applies only to nodes present in the active graph
- Smoothing values encode the asymmetric envelope principle
- beat_pulse requires MIDI transport; decays to 0 when stopped
- Perlin drift amplitude inversely proportional to signal activity
- All gestural offsets are additive, never absolute
- heart_rate gracefully absent when watch disconnected (breathing node uses internal rate)
