"""Bound 3 (anti-audio-visualizer) oracle for the Nebulous Scrim invariants.

Computes a visualizer-register score ``S`` in ``[0, 1]`` over a 5 s rolling
window of egress-frame observables + audio reactivity bus snapshots. High
``S`` means the surface has drifted into Winamp / MilkDrop register:
geometry-observable periodicity matches audio periodicity AND audio onsets
phase-lock to geometry peaks AND radial symmetry pulses on the beat.

Composite metric (per research §1):

    S = α · agree(P_audio, P_geom) · φ_lock
        + β · radial_on_beat
        + γ · spectral_ratio_match

with ``α + β + γ = 1``. The discriminator is the ``agree × φ_lock`` term —
both must fail for a chain to register as visualizer. Modulation lifts
pixels together (low geometry-period structure); illustration carves
frame-spatial structure period-locked to audio.

Intended consumer: Phase 5 runtime check. When ``S`` exceeds the threshold
for ``K`` consecutive windows, the consumer dampens the audio→geometry
coupling gain via asymmetric decay (0.85 down per failing window, 1.05 up
per passing, floor 0.3 — never mute).

Spec: ``docs/research/2026-04-20-oq02-anti-visualizer-metric.md``
Parent epic: ``docs/research/2026-04-20-nebulous-scrim-three-bound-invariants-triage.md``

Style mirror: ``shared/governance/scrim_invariants/scrim_translucency.py``
— pure stateless functions for sub-metrics + a stateful tracker class.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Protocol

import numpy as np

from shared.audio_reactivity import AudioSignals

# ── Calibrated thresholds (see §3 of the metric design doc) ─────────────────
S_THRESHOLD: Final[float] = 0.45  # placeholder; pinned post-calibration
HYSTERESIS_WINDOWS: Final[int] = 3  # consecutive windows above S_THRESHOLD
RECOVERY_DELTA: Final[float] = 0.10
WINDOW_SECONDS: Final[float] = 5.0
TARGET_FPS: Final[float] = 30.0  # egress frame-rate sample target
MIN_AUDIO_RMS: Final[float] = 1e-3  # below this we report S=0 (silence guard)

# Combination weights (research §1: α + β + γ = 1).
ALPHA: Final[float] = 0.55  # period-agreement × phase-lock
BETA: Final[float] = 0.30  # radial-symmetry-on-beat
GAMMA: Final[float] = 0.15  # spectral-ratio match

# Coupling-gain dampening parameters (research §7).
COUPLING_GAIN_DECAY: Final[float] = 0.85
COUPLING_GAIN_RECOVERY: Final[float] = 1.05
COUPLING_GAIN_FLOOR: Final[float] = 0.30
COUPLING_GAIN_CEILING: Final[float] = 1.00

# Onset detection: smoothed onset signal above this threshold counts as a peak.
ONSET_PEAK_THRESHOLD: Final[float] = 0.5

DEFAULT_CALIBRATION_PATH: Final[Path] = Path("presets/scrim_invariants/calibration.json")


# ── Data classes ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ScrimObservables:
    """Per-frame scalar projections of egress geometry.

    All four observables are deliberately cheap (single pass over a
    downsampled luma map). Together they capture the signal content a
    visualizer-register surface would carve into the frame.
    """

    mean_luminance: float  # global mean — lifts uniformly under modulation
    luminance_variance: float  # spatial structure — rises under illustration
    radial_symmetry_index: float  # 0..1, polar moment of luma about centre
    rotational_second_moment: float  # 0..1, second-moment in polar coords


@dataclass(frozen=True)
class VisualizerScore:
    """Output of one window evaluation."""

    score: float  # combined S in [0, 1]
    period_agreement: float  # 1 - |P_geom - P_audio| / P_audio, clipped
    phase_lock: float  # circular-mean coherence (Kuramoto R) in [0, 1]
    radial_on_beat: float  # variance-vs-uniform correlated with onsets
    spectral_ratio: float  # geometry/audio onset spectrum agreement
    silence_guard: bool  # True when audio RMS below MIN_AUDIO_RMS


class FrameProjector(Protocol):
    """Implementations turn an egress RGBA / YUV frame into observables.

    Consumer-supplied: Phase 5 runtime check wires this to the V4L2 sink the
    compositor writes; tests provide deterministic projectors over fixture
    frames.
    """

    def project(self, frame: np.ndarray) -> ScrimObservables: ...


# ── Pure sub-metric functions ───────────────────────────────────────────────


def _autocorrelation_period(signal: np.ndarray, *, min_lag: int = 2) -> float | None:
    """Dominant period (in samples) via autocorrelation peak-picking.

    Uses ``np.correlate`` (no FFT) on a mean-subtracted signal. Returns
    ``None`` when the signal is too flat (no informative peak above zero
    lag) or shorter than ``2 * min_lag``.

    Pure function: same input → same output.
    """
    n = signal.size
    if n < 2 * min_lag:
        return None
    x = signal.astype(np.float64) - float(signal.mean())
    if not np.any(x):
        return None
    full = np.correlate(x, x, mode="full")
    ac = full[full.size // 2 :]  # lags >= 0
    # Look for the first local maximum past min_lag.
    if ac.size <= min_lag + 1:
        return None
    search = ac[min_lag:]
    # Local maxima: strictly greater than both neighbours.
    if search.size < 3:
        return None
    rel = (search[1:-1] > search[:-2]) & (search[1:-1] > search[2:])
    if not np.any(rel):
        return None
    candidates = np.where(rel)[0] + 1  # offset for [1:-1] view
    # Pick the candidate with the largest autocorrelation value.
    best = candidates[np.argmax(search[candidates])]
    if search[best] <= 0.0:
        return None
    return float(best + min_lag)


def compute_period_agreement(
    p_audio: float | None,
    p_geom: float | None,
    *,
    tolerance: float = 1.0,
) -> float:
    """``1 - |P_geom - P_audio| / P_audio`` clipped to ``[0, 1]``.

    Returns 0.0 if either period is unknown. ``tolerance`` caps how far
    apart the two periods may be before agreement falls to 0 (in units of
    ``P_audio``: a tolerance of 1.0 means a doubling/halving collapses
    agreement to 0).
    """
    if p_audio is None or p_geom is None:
        return 0.0
    if p_audio <= 0.0:
        return 0.0
    diff = abs(p_geom - p_audio) / p_audio
    return float(max(0.0, min(1.0, 1.0 - diff / tolerance)))


def compute_phase_lock(
    onset_times: np.ndarray,
    geom_peak_times: np.ndarray,
    period: float,
) -> float:
    """Kuramoto circular-mean order parameter ``R`` in ``[0, 1]``.

    For each onset time ``t_i`` we find the nearest geometry-peak time
    ``g_j`` and compute the phase residual ``φ_i = 2π · (t_i - g_j) / P``.
    The order parameter is ``R = |Σ exp(i · φ_i)| / N``. ``R → 1`` means
    onsets phase-lock to geometry peaks; ``R → 0`` means uniformly
    distributed phases.
    """
    if onset_times.size == 0 or geom_peak_times.size == 0 or period <= 0.0:
        return 0.0
    phases = []
    for t in onset_times:
        idx = int(np.argmin(np.abs(geom_peak_times - t)))
        residual = (t - geom_peak_times[idx]) / period
        phases.append(2.0 * np.pi * residual)
    arr = np.array(phases, dtype=np.float64)
    r = np.abs(np.exp(1j * arr).mean())
    return float(max(0.0, min(1.0, r)))


def compute_radial_on_beat(
    radial_symmetry: np.ndarray,
    onset_signal: np.ndarray,
    *,
    threshold: float = ONSET_PEAK_THRESHOLD,
) -> float:
    """Mean radial-symmetry value at sample-indices where onset > threshold.

    Returns 0.0 when no onsets fire in the window. The metric rises when
    radial structure peaks coincide with audio onsets — the MilkDrop
    radial-bloom signature.
    """
    if radial_symmetry.size == 0 or onset_signal.size == 0:
        return 0.0
    n = min(radial_symmetry.size, onset_signal.size)
    rs = radial_symmetry[:n].astype(np.float64)
    on = onset_signal[:n].astype(np.float64)
    mask = on > threshold
    if not np.any(mask):
        return 0.0
    on_value = float(rs[mask].mean())
    off_value = float(rs[~mask].mean()) if np.any(~mask) else 0.0
    # Lift = (on - off) clamped to [0, 1]. A radial-bloom-on-beat surface
    # has a strong positive lift; an unrelated chain has lift ≈ 0.
    return float(max(0.0, min(1.0, on_value - off_value)))


def compute_spectral_ratio_match(
    geom_signal: np.ndarray,
    onset_signal: np.ndarray,
) -> float:
    """Cosine similarity between magnitude spectra of the two signals.

    Cheap proxy for "does the geometry spectrum live at the same harmonic
    ladder as the audio onset spectrum?" — Winamp spectrum-bar surfaces
    score high; broadband modulation chains score low.
    """
    if geom_signal.size < 4 or onset_signal.size < 4:
        return 0.0
    n = min(geom_signal.size, onset_signal.size)
    g = geom_signal[:n].astype(np.float64) - float(geom_signal[:n].mean())
    o = onset_signal[:n].astype(np.float64) - float(onset_signal[:n].mean())
    if not np.any(g) or not np.any(o):
        return 0.0
    g_spec = np.abs(np.fft.rfft(g))
    o_spec = np.abs(np.fft.rfft(o))
    g_norm = float(np.linalg.norm(g_spec))
    o_norm = float(np.linalg.norm(o_spec))
    if g_norm <= 0.0 or o_norm <= 0.0:
        return 0.0
    return float(max(0.0, min(1.0, float(np.dot(g_spec, o_spec)) / (g_norm * o_norm))))


def combine(
    period_agree: float,
    phase_lock: float,
    radial_on_beat: float,
    spectral_ratio: float,
    *,
    alpha: float = ALPHA,
    beta: float = BETA,
    gamma: float = GAMMA,
) -> float:
    """Composite ``S = α·agree·φ + β·radial + γ·spectral``, clipped to [0, 1].

    The ``agree × φ_lock`` product is the discriminator — both must fail
    for a chain to register as visualizer (research §2 hard distinction).
    """
    s = alpha * period_agree * phase_lock + beta * radial_on_beat + gamma * spectral_ratio
    return float(max(0.0, min(1.0, s)))


# ── Stateful oracle ─────────────────────────────────────────────────────────


@dataclass
class _Sample:
    ts: float
    obs: ScrimObservables
    audio: AudioSignals


@dataclass
class AntiVisualizerOracle:
    """Rolling-window oracle.

    Owns a fixed-size deque of ``(timestamp, observables, audio)`` triples
    sampled at ~``target_fps``. ``evaluate()`` returns a ``VisualizerScore``
    based on the current contents; ``should_dampen()`` applies the
    hysteresis rule and is the integration entry point for the Phase 5
    runtime check.
    """

    window_seconds: float = WINDOW_SECONDS
    target_fps: float = TARGET_FPS
    threshold: float = S_THRESHOLD
    hysteresis: int = HYSTERESIS_WINDOWS
    recovery_delta: float = RECOVERY_DELTA
    samples: deque[_Sample] = field(init=False)
    _consec_failing: int = field(default=0, init=False)
    _dampen_active: bool = field(default=False, init=False)
    _coupling_gain: float = field(default=COUPLING_GAIN_CEILING, init=False)

    def __post_init__(self) -> None:
        capacity = max(8, int(round(self.window_seconds * self.target_fps)))
        self.samples = deque(maxlen=capacity)

    # ── Sample ingestion ─────────────────────────────────────────────────

    def push(
        self,
        ts: float,
        observables: ScrimObservables,
        audio: AudioSignals,
    ) -> None:
        """Append a sample. Oldest is dropped when window full."""
        self.samples.append(_Sample(ts=float(ts), obs=observables, audio=audio))

    # ── Window evaluation ────────────────────────────────────────────────

    def evaluate(self) -> VisualizerScore:
        """Compute ``S`` over the current window.

        Silence guard short-circuits to ``S = 0`` when the audio RMS in the
        window falls below ``MIN_AUDIO_RMS``. Without an audio period there
        is nothing to phase-lock against; geometry periodicity in silence
        is by construction not an illustration of audio (research §8).
        """
        if not self.samples:
            return VisualizerScore(
                score=0.0,
                period_agreement=0.0,
                phase_lock=0.0,
                radial_on_beat=0.0,
                spectral_ratio=0.0,
                silence_guard=True,
            )

        rms_signal = np.array([s.audio.rms for s in self.samples], dtype=np.float64)
        if float(rms_signal.mean()) < MIN_AUDIO_RMS:
            return VisualizerScore(
                score=0.0,
                period_agreement=0.0,
                phase_lock=0.0,
                radial_on_beat=0.0,
                spectral_ratio=0.0,
                silence_guard=True,
            )

        onset_signal = np.array([s.audio.onset for s in self.samples], dtype=np.float64)
        radial_signal = np.array(
            [s.obs.radial_symmetry_index for s in self.samples], dtype=np.float64
        )
        # Geometry periodicity rides on luminance variance: a uniformly-lifted
        # frame has flat variance; an illustrated radial bloom modulates it.
        geom_signal = np.array([s.obs.luminance_variance for s in self.samples], dtype=np.float64)
        ts_signal = np.array([s.ts for s in self.samples], dtype=np.float64)

        p_audio = self._dominant_period_audio(onset_signal)
        p_geom = self._dominant_period_geometry(geom_signal)
        period_agree = compute_period_agreement(p_audio, p_geom)

        phase_lock = 0.0
        if p_audio is not None and p_audio > 0.0:
            onset_times = self._peak_times(onset_signal, ts_signal, ONSET_PEAK_THRESHOLD)
            geom_peak_times = self._geometry_peak_times(geom_signal, ts_signal)
            # Period in seconds = period_in_samples / target_fps.
            period_seconds = float(p_audio) / max(self.target_fps, 1e-6)
            phase_lock = compute_phase_lock(onset_times, geom_peak_times, period_seconds)

        radial_on_beat = compute_radial_on_beat(radial_signal, onset_signal)
        spectral_ratio = compute_spectral_ratio_match(geom_signal, onset_signal)
        score = combine(period_agree, phase_lock, radial_on_beat, spectral_ratio)

        return VisualizerScore(
            score=score,
            period_agreement=period_agree,
            phase_lock=phase_lock,
            radial_on_beat=radial_on_beat,
            spectral_ratio=spectral_ratio,
            silence_guard=False,
        )

    # ── Hysteresis + coupling-gain dampening ─────────────────────────────

    def should_dampen(self) -> bool:
        """Hysteresis-applied predicate driving coupling-gain dampening.

        Fires only after ``hysteresis`` consecutive failing windows.
        Recovers when one window passes at ``threshold - recovery_delta``.
        Side effect: updates the internal coupling-gain via asymmetric
        decay (research §7) — ``coupling_gain`` is exposed via
        :py:meth:`coupling_gain`.
        """
        score = self.evaluate().score
        if score > self.threshold:
            self._consec_failing += 1
            self._coupling_gain = max(
                COUPLING_GAIN_FLOOR, self._coupling_gain * COUPLING_GAIN_DECAY
            )
            if self._consec_failing >= self.hysteresis:
                self._dampen_active = True
        else:
            recovery_band = self.threshold - self.recovery_delta
            if score < recovery_band:
                self._consec_failing = 0
                self._dampen_active = False
            self._coupling_gain = min(
                COUPLING_GAIN_CEILING, self._coupling_gain * COUPLING_GAIN_RECOVERY
            )
        return self._dampen_active

    @property
    def coupling_gain(self) -> float:
        """Current coupling-gain in ``[FLOOR, CEILING]``. Never reaches 0."""
        return self._coupling_gain

    # ── Internal stages, each independently testable ──────────────────────

    def _dominant_period_audio(self, onset_signal: np.ndarray) -> float | None:
        """Period (in samples) of the dominant audio-onset rhythm."""
        return _autocorrelation_period(onset_signal)

    def _dominant_period_geometry(self, geom_signal: np.ndarray) -> float | None:
        """Period (in samples) of the dominant geometry-observable rhythm."""
        return _autocorrelation_period(geom_signal)

    def _peak_times(
        self,
        signal: np.ndarray,
        timestamps: np.ndarray,
        threshold: float,
    ) -> np.ndarray:
        """Timestamps of samples where ``signal`` exceeds ``threshold``."""
        if signal.size == 0:
            return np.array([], dtype=np.float64)
        n = min(signal.size, timestamps.size)
        mask = signal[:n] > threshold
        return timestamps[:n][mask]

    def _geometry_peak_times(
        self,
        signal: np.ndarray,
        timestamps: np.ndarray,
    ) -> np.ndarray:
        """Timestamps where geometry-observable exceeds its mean (peaks)."""
        if signal.size == 0:
            return np.array([], dtype=np.float64)
        n = min(signal.size, timestamps.size)
        mean = float(signal[:n].mean())
        # Peaks: above-mean samples bordered by below-mean neighbours.
        s = signal[:n]
        if s.size < 3:
            mask = s > mean
        else:
            mid = s[1:-1]
            mask_mid = (mid > mean) & (mid >= s[:-2]) & (mid >= s[2:])
            mask = np.concatenate([[False], mask_mid, [False]])
        return timestamps[:n][mask]


# ── Default projector + calibration helper ──────────────────────────────────


def _radial_symmetry(luma: np.ndarray) -> float:
    """Polar-moment radial-symmetry index in ``[0, 1]``.

    Bins the frame into 8 angular sectors around the centroid, computes
    the variance of per-sector mean-luminance vs the uniform expectation.
    Low variance → high radial symmetry.
    """
    h, w = luma.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.indices((h, w), dtype=np.float64)
    angles = np.arctan2(yy - cy, xx - cx)
    sectors = np.floor((angles + np.pi) / (2.0 * np.pi) * 8.0).astype(np.int64)
    sectors = np.clip(sectors, 0, 7)
    means = np.array(
        [float(luma[sectors == k].mean()) if np.any(sectors == k) else 0.0 for k in range(8)]
    )
    spread = float(means.std())
    # Map: spread 0 → symmetry 1; spread 0.5 (uniform 0/1) → symmetry 0.
    return float(max(0.0, min(1.0, 1.0 - spread / 0.5)))


def _rotational_second_moment(luma: np.ndarray) -> float:
    """Normalised second polar moment about the centroid in ``[0, 1]``."""
    h, w = luma.shape
    if h < 2 or w < 2:
        return 0.0
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.indices((h, w), dtype=np.float64)
    r2 = (yy - cy) ** 2 + (xx - cx) ** 2
    weight = float(luma.sum())
    if weight <= 0.0:
        return 0.0
    moment = float((luma * r2).sum() / weight)
    norm = float((h / 2.0) ** 2 + (w / 2.0) ** 2)
    return float(max(0.0, min(1.0, moment / max(norm, 1.0))))


def _to_grayscale(frame: np.ndarray) -> np.ndarray:
    """HxWx3 RGB uint8 → HxW float32 luminance in [0, 1]."""
    if frame.ndim == 2:
        return frame.astype(np.float32) / 255.0
    if frame.ndim != 3 or frame.shape[2] not in (3, 4):
        raise ValueError(f"expected HxWx3 or HxW frame; got shape {frame.shape}")
    rgb = frame[..., :3].astype(np.float32) / 255.0
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


class _DefaultFrameProjector:
    """Default projector: downsample to 64×36, compute observables.

    Cost target: <0.5 ms per call on a single CPU core.
    """

    def __init__(self, *, target_size: tuple[int, int] = (36, 64)) -> None:
        self.target_size = target_size

    def project(self, frame: np.ndarray) -> ScrimObservables:
        luma = _to_grayscale(frame)
        # Cheap downsample via slicing.
        ty, tx = self.target_size
        h, w = luma.shape
        if h > ty and w > tx:
            sy = max(1, h // ty)
            sx = max(1, w // tx)
            luma = luma[::sy, ::sx]
        return ScrimObservables(
            mean_luminance=float(luma.mean()),
            luminance_variance=float(luma.var()),
            radial_symmetry_index=_radial_symmetry(luma),
            rotational_second_moment=_rotational_second_moment(luma),
        )


def make_default_projector() -> FrameProjector:
    """Default frame projector.

    Cost target: <0.5 ms per call on a single CPU core.
    """
    return _DefaultFrameProjector()


def calibrate(
    *,
    negative_fixtures: list[VisualizerScore],
    positive_fixtures: list[VisualizerScore],
    out_path: Path | None = None,
) -> float:
    """Derive ``S_threshold`` per §3 of the metric design doc.

    ``S_threshold = (S_neg_max + S_pos_min) / 2``, rounded down to the
    nearest 0.05 for stability across re-calibrations. Writes the
    calibration trace to ``out_path`` (default
    ``presets/scrim_invariants/calibration.json``) so threshold drift is
    auditable.
    """
    if not negative_fixtures or not positive_fixtures:
        raise ValueError("calibrate() requires at least one negative and one positive fixture")
    neg = np.array([f.score for f in negative_fixtures], dtype=np.float64)
    pos = np.array([f.score for f in positive_fixtures], dtype=np.float64)
    s_neg_max = float(neg.mean() + 2.0 * neg.std())
    s_pos_min = float(pos.mean() - 2.0 * pos.std())
    raw = (s_neg_max + s_pos_min) / 2.0
    threshold = float(np.floor(raw / 0.05) * 0.05)
    threshold = max(0.0, min(1.0, threshold))

    target = out_path or DEFAULT_CALIBRATION_PATH
    trace = {
        "schema_version": 1,
        "s_neg_max": s_neg_max,
        "s_pos_min": s_pos_min,
        "threshold": threshold,
        "negative_n": int(neg.size),
        "positive_n": int(pos.size),
        "negative_scores": neg.tolist(),
        "positive_scores": pos.tolist(),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    return threshold
