# OQ-02 Bound 3 — Anti-Audio-Visualizer Metric Selection

**Status:** RESEARCH — METRIC SELECTION (input to phased plan §4 Phase 1 of `2026-04-20-nebulous-scrim-three-bound-invariants-triage.md`)
**Owner:** alpha (HOMAGE / scrim family)
**Cross-link:** Phase 5 runtime check (rolling-window egress oracle, 5 s) and Phase 1 oracle authoring of the parent epic.
**Operator constraint (verbatim):** *"It must NEVER look like a simple audio visualizer. That is NOT the point. Although AUDIO reactivity remains key."*
**Negative space (operator):** no FFT-to-geometry mapping, no beat-synced symmetric pulses, no waveform/spectrum wards.

## 1. Metric choice

**Selected: candidate (c) — BPM-periodicity vs geometry-periodicity *coherence with phase-lock penalty*.**

The metric computes, over a 5 s sliding window, three quantities and combines them into a single visualizer-register score `S ∈ [0, 1]`:

1. `P_audio(τ)` — the dominant audio-tempo period inferred from the unified reactivity bus' `bpm_estimate` field (`shared/audio_reactivity.py:107`) cross-checked with onset-stream autocorrelation. Period in samples at the egress frame-rate.
2. `P_geom(τ)` — the dominant period of a small set of scalar *geometry observables* extracted from the egress frame (per-frame mean luminance variance, radial-symmetry index, and rotational-second-moment). Computed from the autocorrelation of each observable over the 5 s window.
3. `φ_lock` — circular-mean phase coherence between audio onsets and geometry-observable peaks within the window (cf. Kuramoto order parameter).

`S = α · agree(P_audio, P_geom) · φ_lock + β · radial_symmetry_on_beat + γ · spectral_ratio_match`, with `α + β + γ = 1`. All three components individually fall in `[0, 1]`; the failure mode is high-coherence + high-phase-lock + radial symmetry pulsing on the beat — i.e. exactly what a Winamp / MilkDrop oscilloscope or radial bloom ring does.

### Rationale vs the other three candidates

- **(a) FFT↔geometry cross-correlation.** Conceptually right but the wrong primitive for runtime: requires per-frame FFT of an image observable and per-frame FFT of an audio frame, then a full cross-correlation in a 2D feature space. Every cheaper observable we'd settle on (mean luminance, edge-density) is a *projection* of geometry, so the cross-correlation reduces in practice to (c) plus a constant. Picking (c) directly removes the FFT machinery and avoids false positives on broadband reactive scenes that share spectral envelope shape without actually illustrating audio.
- **(b) Radial-symmetry-on-beat detector.** A *necessary* component — kept as the `β` term — but insufficient as the sole metric. Many legitimate scrim chains (drift + bloom + colorgrade) produce some radial symmetry without being visualizer-register; many visualizer-register surfaces (waveform wards, spectrum bars) are *not* radially symmetric. Used alone it both false-positives on `bloom + dark_vignette` chains and misses Winamp-classic spectrum bars entirely.
- **(d) Learned classifier.** Discriminative on the canonical Winamp/MilkDrop register, but: requires labelled training data (we have none), opaque failure mode (the Phase 5 runtime check needs to be auditable when it dampens reactivity gain), and the inference cost of even a small CNN on a 5 s windowed slice exceeds the ~2 ms egress budget. Kept as a *future* offline test-set generator (Phase 4 CI gate) to validate the (c)+(b) score on captured fixtures from real visualizer software, but not as the runtime oracle.

The combined `S` is closer to (a)'s spirit while inheriting (b) as a sub-component and remaining cheap enough for the 5 s window. The discriminating power comes from `agree × φ_lock`: audio-modulation that does not phase-lock to onsets fails one of the two terms; periodic geometry that is not synchronised to the audio period fails the other.

## 2. The hard distinction — modulates vs illustrates

The operator's constraint distinguishes two regimes that are easily conflated in causal terms (audio drives uniform → uniform drives shader → shader changes pixels) but are clearly distinguishable in the *frequency / phase* domain.

| Property | Audio *modulates* the scrim (good) | Audio *illustrates* the scrim (bad) |
|---|---|---|
| Geometry-observable autocorrelation peak at audio period | Weak / absent (`P_geom ≠ P_audio`) | Strong (`P_geom ≈ P_audio`, agree → 1) |
| Phase coherence between audio onsets and geometry peaks | Low (`φ_lock < 0.3`) | High (`φ_lock > 0.7`) |
| Spectral ratio (geometry-observable spectrum vs audio-onset spectrum) | Diverges; geometry dominated by render-loop, drift, temporal feedback | Concentrated at the same harmonic ladder |
| Radial symmetry index | Whatever the chain produces, untied to onsets | Cyclical, peaks within ±50 ms of every onset |
| Long-tail temporal coherence (Bachelard Amendment 2 feedback) | Geometry "remembers" prior frames, smearing phase | Sharp, low-memory pulses |

A `colorgrade.brightness` modulation driven by `mixer_energy` (shared/audio_reactivity.py:104) modulates the surface — every part of the frame brightens together, no geometric structure is illustrated. The scalar `geometry_observable` (mean luminance variance) stays roughly constant; only the global mean luminance changes. That is `agree → 0`.

Conversely a `radial_bloom.glow_strength` driven by `onset` peaks the radial-symmetry index every onset and the geometry-observable autocorrelation will lock onto `P_audio`. That is `agree → 1, φ_lock → 1`. Visualizer-register.

The hard line is therefore not "does audio touch the shader" but "does the audio-driven path produce *frame-spatial structure* whose period matches the audio period and whose phase is locked to it". Modulation lifts/smears every pixel together; illustration carves spatially-coherent shapes that breathe with the audio.

## 3. Threshold derivation

Three calibration steps, each producing a numeric threshold pinned in `shared/governance/scrim_invariants/anti_visualizer.py`.

1. **Negative-fixture floor.** Render 60 s of every shipped preset family chain (`presets/*.json`) under each of the four standard audio profiles (silence, broadband, periodic-beat, full-mix music) — same matrix as Phase 2 of the parent epic. Compute `S` per 5 s window. Set `S_neg_max = max + 2σ` over all (preset, audio) windows; this is the floor below which legitimate reactive scrim must fall. Initial expectation, given the modulation primitives in `agents/effect_graph/modulator.py`: `S_neg_max < 0.25` even with aggressive `mixer_energy → glow_strength` bindings, because none of the shipped chains carve frame-spatial structure synchronised to onsets.
2. **Positive-fixture ceiling.** Synthesise a small set of canonical visualizer-register surfaces directly in WGSL: (i) Winamp oscilloscope (waveform → vertical-line raster), (ii) MilkDrop radial bloom (onset → centred Gaussian pulse), (iii) FFT spectrum bars (8 mel bands → 8 vertical bars), (iv) waveform-shaped ward content. Compute `S`. Set `S_pos_min = min - 2σ`. Expectation: `S_pos_min > 0.6`.
3. **Threshold.** `S_threshold = (S_neg_max + S_pos_min) / 2`, rounded down to the nearest 0.05 for stability across re-calibrations. Re-calibrate on every new shipped preset family or new shader node. Record the calibration trace in `presets/scrim_invariants/calibration.json` so threshold drift is auditable.

Hysteresis: the runtime check fires only on `S > S_threshold` for `≥ K = 3` consecutive 5 s windows (15 s sustained), recovers when `S < S_threshold − 0.1` for 1 window. Avoids single-window thrash from a transient camera flash or a one-shot SFX hit.

## 4. Prototype module sketch

Path: `shared/governance/scrim_invariants/anti_visualizer.py`. Skeleton only — full implementation is Phase 1 of the parent epic.

```python
"""Bound 3 (anti-audio-visualizer) oracle for the Nebulous Scrim invariants.

Computes a visualizer-register score S in [0, 1] over a 5 s rolling window
of egress frames + audio reactivity bus snapshots. High S means the surface
has drifted into Winamp/MilkDrop register: geometry-observable periodicity
matches audio periodicity AND audio onsets phase-lock to geometry peaks
AND radial symmetry pulses on the beat.

Intended consumer: Phase 5 runtime check. When S exceeds the threshold for
K consecutive windows, the consumer dampens the audio->geometry coupling
gain (does not mute audio reactivity entirely). See module-level docstring
in `agents/effect_graph/modulator.py` for the binding shape this dampens.

Spec: docs/research/2026-04-20-oq02-anti-visualizer-metric.md
Parent epic: docs/research/2026-04-20-nebulous-scrim-three-bound-invariants-triage.md
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from shared.audio_reactivity import AudioSignals, BusSnapshot

# ── Calibrated thresholds (see §3 of the metric design doc) ─────────────────
S_THRESHOLD: float = 0.45      # placeholder; pinned post-calibration
HYSTERESIS_WINDOWS: int = 3    # consecutive 5 s windows above S_THRESHOLD
RECOVERY_DELTA: float = 0.10
WINDOW_SECONDS: float = 5.0
TARGET_FPS: float = 30.0       # egress frame-rate sample target
MIN_AUDIO_RMS: float = 1e-3    # below this we report S=0 (silence guard)


@dataclass(frozen=True)
class ScrimObservables:
    """Per-frame scalar projections of egress geometry.

    All three observables are deliberately cheap (single pass over a
    downsampled luma map). Together they capture the signal content a
    visualizer-register surface would carve into the frame.
    """

    mean_luminance: float           # global mean — lifts uniformly under modulation
    luminance_variance: float       # spatial structure — rises under illustration
    radial_symmetry_index: float    # 0..1, cf. polar moment of luma about centre
    rotational_second_moment: float # 0..1, second-moment in polar coords


@dataclass(frozen=True)
class VisualizerScore:
    """Output of one window evaluation."""

    score: float                    # combined S in [0, 1]
    period_agreement: float         # |1 - |P_geom - P_audio| / P_audio|, clipped
    phase_lock: float               # circular-mean coherence in [0, 1]
    radial_on_beat: float           # mean radial-symmetry across onset windows
    silence_guard: bool             # True when audio RMS below MIN_AUDIO_RMS


class FrameProjector(Protocol):
    """Implementations turn an egress RGBA / YUV frame into observables.

    The projector is provided by the consumer (Phase 5 runtime check
    wires this to the V4L2 sink the compositor writes; tests provide
    deterministic projectors over fixture frames).
    """

    def project(self, frame: np.ndarray) -> ScrimObservables: ...


class AntiVisualizerOracle:
    """Rolling-window oracle.

    Owns a fixed-size deque of (timestamp, observables, audio) triples
    sampled at TARGET_FPS. `evaluate()` returns a VisualizerScore based
    on the current contents; `should_dampen()` applies the hysteresis
    rule and is the integration entry point for the Phase 5 runtime
    check.
    """

    def __init__(
        self,
        *,
        window_seconds: float = WINDOW_SECONDS,
        target_fps: float = TARGET_FPS,
        threshold: float = S_THRESHOLD,
        hysteresis: int = HYSTERESIS_WINDOWS,
    ) -> None: ...

    def push(
        self,
        ts: float,
        observables: ScrimObservables,
        audio: AudioSignals,
    ) -> None:
        """Append a sample. Drops oldest when window full."""
        ...

    def evaluate(self) -> VisualizerScore:
        """Compute S over the current window. O(N log N) (FFT) on N≤150."""
        ...

    def should_dampen(self) -> bool:
        """Hysteresis-applied predicate driving coupling-gain dampening."""
        ...

    # ── Internal stages, each independently testable ────────────────────

    def _dominant_period_audio(self) -> float | None: ...
    def _dominant_period_geometry(self) -> float | None: ...
    def _phase_lock(self, period: float) -> float: ...
    def _radial_on_beat(self) -> float: ...
    def _combine(
        self,
        period_agree: float,
        phase_lock: float,
        radial_on_beat: float,
    ) -> float: ...


def make_default_projector() -> FrameProjector:
    """Default frame projector: downsample to 64x36, polar grid sampling.

    Cost target: <0.5 ms per call on a single CPU core.
    """
    ...


def calibrate(
    *,
    negative_fixtures: list[tuple[ScrimObservables, AudioSignals]],
    positive_fixtures: list[tuple[ScrimObservables, AudioSignals]],
) -> float:
    """Derive S_threshold per §3 of the metric design doc.

    Writes the calibration trace to
    presets/scrim_invariants/calibration.json so threshold drift is auditable.
    """
    ...
```

The five `_dominant_*` / `_phase_lock` / `_radial_on_beat` methods are each pure functions of the deque contents, so each can be unit-tested in isolation against synthesised fixtures (§5). The public `evaluate()` is just the composition of the four sub-stages plus `_combine()`.

## 5. Acceptance test sketch

Path: `tests/effect_graph/invariants/test_anti_visualizer.py`. Fixtures live alongside under `tests/effect_graph/invariants/fixtures/`.

Fixtures (each is a 5 s sequence of `(ScrimObservables, AudioSignals)`):

| Fixture | Audio | Observables | Expected outcome |
|---|---|---|---|
| `silence_quiescent` | RMS = 0, no onsets | constant observables | `silence_guard = True`, `S = 0`, `should_dampen = False` |
| `silence_drifting` | RMS = 0 | drift / temporal-feedback observables changing | `silence_guard = True`, `S = 0` (silence overrides) |
| `broadband_modulation` | white-ish, no clear period | `mean_luminance` follows RMS | `S < S_THRESHOLD`, `period_agreement → 0` |
| `periodic_beat_legitimate` | 120 BPM kick | `mean_luminance` modulates, `luminance_variance` flat | `period_agreement` mid, `phase_lock` low, `S < S_THRESHOLD` |
| `full_mix_music_legitimate` | recorded hip-hop loop, 90 BPM | shipped chain output (drift + bloom + colorgrade) | `S < S_THRESHOLD` over every 5 s window |
| `winamp_oscilloscope_synth` | sine-tone | waveform-derived `luminance_variance` | `S > S_THRESHOLD`, `phase_lock → 1` |
| `milkdrop_radial_synth` | 120 BPM kick | radial bloom centred, peaks on every kick | `S > S_THRESHOLD`, `radial_on_beat → 1` |
| `spectrum_bars_synth` | full mix | 8 vertical bars from mel bands | `S > S_THRESHOLD`, `period_agreement → 1` |
| `flicker_transient` | one onset | one luminance spike then quiescent | `S` may briefly exceed; `should_dampen() = False` (hysteresis) |
| `deterministic_pattern` | silent | observables follow a fixed period unrelated to audio | `S = 0` (silence guard); even with audio, `agree → 0` since no audio period |

Assertions:

- `oracle.evaluate().silence_guard is True` for both silence fixtures.
- For each legitimate fixture: `oracle.evaluate().score < S_THRESHOLD` for every contiguous 5 s window when fed at TARGET_FPS.
- For each visualizer-register fixture: `oracle.evaluate().score > S_THRESHOLD` for ≥ HYSTERESIS_WINDOWS windows ⇒ `should_dampen() is True`.
- For `flicker_transient`: `should_dampen() is False` despite a single high-`S` window (hysteresis).
- Property test (Hypothesis): for any synthesised `ScrimObservables` sequence with `radial_symmetry_index ≡ 0` and `luminance_variance ≡ const`, `score < 0.2` regardless of audio.

## 6. Runtime cost

Per 5 s window (assume 30 fps egress, 150 samples):

- `FrameProjector.project()`: target < 0.5 ms / frame; called once per frame on the egress thread (already producing JPEG snapshots at 10 fps for `/dev/shm/hapax-visual/frame.jpg`, see council CLAUDE.md § Tauri-Only Runtime). The projector can ride on the same downsampled luma the snapshot path already produces — net additional cost ≈ 0.1 ms / frame.
- `_dominant_period_*`: one numpy FFT on N ≤ 150 + argmax. ~50 µs each.
- `_phase_lock`: linear scan over onsets in window, circular mean. < 100 µs.
- `_radial_on_beat`: gather radial-symmetry-index at onset timestamps, mean. < 50 µs.
- `_combine`: scalar arithmetic. Negligible.
- `evaluate()` total per call: < 1 ms.

`evaluate()` runs at the window cadence (worst case once per second for the rolling check, even though the window itself is 5 s wide), not per frame. Total CPU budget: ~1 ms/s, well under the egress-thread headroom (Phase 6 of the source-registry completion epic established < 16 ms / frame budget end-to-end, see `docs/superpowers/specs/2026-04-13-reverie-source-registry-completion-design.md`). No GPU cost.

Memory: 150 × (4 × float32 observables + 9 × float32 audio + float64 ts) ≈ 8 KiB per oracle instance. Fixed-size deque, no allocation churn.

## 7. Integration with Phase 5 coupling-gain dampening

Phase 5 of the parent epic specifies: *"if [S is] above threshold, dampen audio→geometry coupling gain (do NOT mute audio reactivity entirely; lower the slope)"*. The integration point is `agents/effect_graph/modulator.py:31` — the `UniformModulator.tick()` loop where each `ModulationBinding.scale` multiplies `signals.get(b.source)` to produce the `target` value.

Wiring (no full implementation here, called out for the plan):

1. Add `coupling_gain: float = 1.0` to `UniformModulator` (default no-op).
2. In `tick()`: `target = raw * b.scale * coupling_gain + b.offset`.
3. The Phase 5 runtime daemon owns one `AntiVisualizerOracle` per egress target, polls it once per second, and writes `coupling_gain` per-binding-class. Suggested decay: `coupling_gain ← max(0.3, coupling_gain × 0.85)` per failing window; recovery: `coupling_gain ← min(1.0, coupling_gain × 1.05)` per passing window. Floor at 0.3 — never mute, only attenuate.
4. The dampening applies *only* to bindings whose `source` is in the audio-reactivity namespace (`mixer.*`, `desk.*`, future `input{N}.*`). Stimmung-driven and operator-driven bindings are untouched. This is the "modulates vs illustrates" enforcement at the binding level: we keep audio responsiveness intact while flattening the slope through which audio shapes geometry.
5. Per-binding-class attenuation is preferable to per-binding because a single offending binding (e.g. `bloom.glow_strength ← onset_kick`) can be the dominant contributor to high `S`; the Phase 5 daemon should rank bindings by their per-binding contribution to `_radial_on_beat` and `_phase_lock` (deterministic from the binding's `source`) and attenuate the worst offenders first. This is auditable via the existing `presets/scrim_invariants/` directory.
6. Emit a degraded-signal event (`shared/governance/agent_governor.py` pattern) with `kind="anti_visualizer"`, payload `{score, P_audio, P_geom, phase_lock, attenuated_bindings}`, so the operator can see *why* the slope dropped — same auditability principle as the OQ-01 brightness ceiling.

The dampening must be reversible and slow enough that the operator never feels a "yank". The 0.85 / 1.05 asymmetric decay reaches the 0.3 floor in ~7 s of sustained failure and recovers to 1.0 in ~10 s of clean windows. Both timescales are below the operator's expressive cadence and above the per-onset transient — so legitimate audio-driven peaks pass through, and only sustained visualizer-register drift is corrected.

## 8. Failure modes

**Silence (audio RMS below `MIN_AUDIO_RMS`).** The oracle returns `silence_guard = True, S = 0` unconditionally. Without an audio period there is nothing to phase-lock against, and any geometry periodicity is necessarily *not* an illustration of audio. A deterministic shader pattern under silence is by construction allowed; if the operator decides such a pattern is undesirable on independent grounds, that is a bound-2 (anti-opacity) concern, not bound-3.

**Deterministic effects.** A purely deterministic chain (no audio bindings) produces `period_agreement → 0` whenever `P_audio ≠ P_geom`, and even when the two periods coincidentally align, `phase_lock` will fail because the geometry phase is determined by render-clock seed, not audio-onset timing. The metric correctly reports such surfaces as legitimate. The only failure case is if a deterministic shader happens to draw radial pulses *and* the audio happens to be at a matching tempo *and* a coincidental phase alignment persists for ≥ 15 s — which has probability on the order of `(1 / period_count) × (1 / phase_resolution)` per window and is bounded out by the hysteresis.

**Audio-reactive but visually degenerate (e.g. preset blacks out).** When `mean_luminance → 0`, all observables collapse to ≈ 0 and `_radial_on_beat → 0`; the metric reports `S → 0`. This is a bound-2 violation (the studio has dissolved) but bound-3 is satisfied — correct separation of concerns. The Phase 5 bound-2 check fires independently.

**Camera artifacts injecting periodic structure.** Rolling-shutter banding, flicker fusion at fluorescent-light frequencies (50 / 60 Hz aliasing into the egress frame-rate as a slow beat), CRT scan artefacts in fixtures: these can produce `luminance_variance` periodicity *not* tied to audio. They reduce `period_agreement` and so reduce `S`. They can be mistaken for legitimate audio modulation; if the operator later complains that a camera-banding scene was treated as legitimate when it should have been bound-3-flagged, that is a bound-2 (legibility) problem and not a bound-3 false-negative.

**Bus dormant (`HAPAX_UNIFIED_REACTIVITY_ACTIVE` unset).** When the unified bus is not running, the oracle should be passed an `AudioSignals.zero()` snapshot. This collapses to the silence case (`silence_guard = True`). The Phase 5 daemon can also fall back to reading `agents/studio_compositor/audio_capture.py` directly via the same legacy path the rest of the compositor uses, but the cleaner integration is to ride exclusively on `read_shm_snapshot` (`shared/audio_reactivity.py:374`) and let the bus's "no signal" case propagate naturally.

**Adversarial preset.** A maliciously-crafted preset could shape audio modulation to ride just below the phase-lock threshold while still being a clear visualizer in operator perception. The metric is *necessary, not sufficient* for bound-3; the Phase 4 CI gate plus a learned classifier (candidate (d), promoted to a CI-only oracle) covers the residual. Runtime is the cheap floor; CI is the ceiling.

**Onset stream sparse / missing.** The unified bus emits `onset` as a max-blended scalar (`shared/audio_reactivity.py:329`) but does not preserve the onset *time series*. The oracle's `_phase_lock` needs onset timestamps within the window; the simplest fix is to push `(ts, audio.onset)` into the deque on every `push()` and detect onset peaks within the deque (`audio.onset > 0.5` after smoothing). When the egress sample rate drops below 10 fps the phase resolution degrades and `_phase_lock` falls back to a coarser bin (8 phase bins instead of 16). The hysteresis still holds.

**Calibration drift.** Threshold drift is the most likely long-run failure: as new shader nodes ship, `S_neg_max` may creep upward and a stale threshold either over- or under-fires. The `calibrate()` helper writes its trace to `presets/scrim_invariants/calibration.json`; the Phase 4 CI gate re-runs calibration on every PR adding a shader node or preset and fails when the new `S_neg_max` exceeds the pinned threshold (forcing a deliberate threshold bump in the same PR rather than silent drift).

## 9. Sources

- `docs/research/2026-04-20-nebulous-scrim-three-bound-invariants-triage.md` — parent epic, §B3 (candidates) and §4 Phase 5 (runtime check shape).
- `shared/audio_reactivity.py:93-161` — `AudioSignals` dataclass, the input shape this oracle consumes via `BusSnapshot`.
- `shared/audio_reactivity.py:374-401` — `read_shm_snapshot`, the cross-process read path the Phase 5 daemon uses.
- `agents/studio_compositor/reactivity_adapters.py:48-99` — `CompositorAudioCaptureSource`, source of the per-band signals the metric leans on for `bpm_estimate` and onset.
- `agents/effect_graph/modulator.py:31-57` — `UniformModulator.tick()`, the integration point for the Phase 5 coupling-gain dampening hook.
- `docs/superpowers/specs/2026-04-18-audio-reactivity-contract-design.md` — namespacing and bus contract (the metric is namespace-agnostic; it only needs the blended `AudioSignals`).
- `docs/superpowers/specs/2026-04-13-reverie-source-registry-completion-design.md` — egress frame-budget envelope (< 16 ms / frame) the oracle must fit under.
- Memory: `project_hardm_anti_anthropomorphization` — visual sibling principle (raw signal density on a grid; never face iconography). Bound-3 is the audio-reactive analogue.
- Memory: `feedback_show_dont_tell_director` — bound-3 in spirit: action *is* the communication; the scrim is not a music-illustration device.
