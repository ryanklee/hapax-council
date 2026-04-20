"""Tests for shared.governance.scrim_invariants.anti_visualizer.

OQ-02 bound 3 oracle. The discriminating regression pin is
``agree × φ_lock``: modulation-only fixtures must score below threshold
even with strong audio reactivity, and visualizer-register fixtures must
score above threshold AND fire ``should_dampen()`` after the hysteresis
window. See ``docs/research/2026-04-20-oq02-anti-visualizer-metric.md``.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from shared.audio_reactivity import AudioSignals
from shared.governance.scrim_invariants.anti_visualizer import (
    ALPHA,
    BETA,
    COUPLING_GAIN_FLOOR,
    GAMMA,
    HYSTERESIS_WINDOWS,
    MIN_AUDIO_RMS,
    S_THRESHOLD,
    TARGET_FPS,
    AntiVisualizerOracle,
    ScrimObservables,
    VisualizerScore,
    _autocorrelation_period,
    calibrate,
    combine,
    compute_period_agreement,
    compute_phase_lock,
    compute_radial_on_beat,
    compute_spectral_ratio_match,
    make_default_projector,
)

# ── Helpers ────────────────────────────────────────────────────────────────


def _audio(rms: float = 0.0, onset: float = 0.0, bpm: float = 0.0) -> AudioSignals:
    return AudioSignals(
        rms=rms,
        onset=onset,
        centroid=0.0,
        zcr=0.0,
        bpm_estimate=bpm,
        energy_delta=0.0,
        bass_band=rms,
        mid_band=rms,
        treble_band=rms,
    )


def _obs(
    *,
    mean: float = 0.5,
    variance: float = 0.0,
    radial: float = 0.0,
    second_moment: float = 0.0,
) -> ScrimObservables:
    return ScrimObservables(
        mean_luminance=mean,
        luminance_variance=variance,
        radial_symmetry_index=radial,
        rotational_second_moment=second_moment,
    )


def _feed(
    oracle: AntiVisualizerOracle,
    *,
    n: int,
    obs_fn,
    audio_fn,
    fps: float = TARGET_FPS,
    t0: float = 0.0,
) -> None:
    """Push ``n`` samples sourced from index-aware factories."""
    for i in range(n):
        ts = t0 + i / fps
        oracle.push(ts, obs_fn(i, ts), audio_fn(i, ts))


# ── Pure sub-metric tests ──────────────────────────────────────────────────


class TestAutocorrelationPeriod:
    def test_silence_returns_none(self) -> None:
        assert _autocorrelation_period(np.zeros(64)) is None

    def test_short_signal_returns_none(self) -> None:
        assert _autocorrelation_period(np.array([0.0, 1.0])) is None

    def test_periodic_signal_recovers_period(self) -> None:
        period = 10.0
        n = 150
        sig = np.sin(2.0 * np.pi * np.arange(n) / period)
        recovered = _autocorrelation_period(sig)
        assert recovered is not None
        # Allow ±1 sample tolerance for discrete autocorrelation peaks.
        assert abs(recovered - period) <= 1.5


class TestPeriodAgreement:
    def test_none_inputs_yield_zero(self) -> None:
        assert compute_period_agreement(None, 10.0) == 0.0
        assert compute_period_agreement(10.0, None) == 0.0
        assert compute_period_agreement(None, None) == 0.0

    def test_exact_match_yields_one(self) -> None:
        assert compute_period_agreement(15.0, 15.0) == pytest.approx(1.0)

    def test_doubling_collapses_to_zero(self) -> None:
        assert compute_period_agreement(10.0, 20.0) == pytest.approx(0.0)

    def test_clipped_to_unit_interval(self) -> None:
        s = compute_period_agreement(10.0, 12.0)
        assert 0.0 <= s <= 1.0


class TestPhaseLock:
    def test_empty_inputs_zero(self) -> None:
        assert compute_phase_lock(np.array([]), np.array([1.0]), 1.0) == 0.0
        assert compute_phase_lock(np.array([1.0]), np.array([]), 1.0) == 0.0
        assert compute_phase_lock(np.array([1.0]), np.array([1.0]), 0.0) == 0.0

    def test_perfect_lock_yields_one(self) -> None:
        period = 1.0
        onsets = np.arange(0.0, 5.0, period)
        peaks = onsets.copy()
        assert compute_phase_lock(onsets, peaks, period) == pytest.approx(1.0)

    def test_random_phases_yield_low_R(self) -> None:
        period = 1.0
        rng = np.random.default_rng(0)
        onsets = rng.uniform(0.0, 100.0, size=200)
        peaks = rng.uniform(0.0, 100.0, size=200)
        r = compute_phase_lock(onsets, peaks, period)
        # Random phases should not produce strong coherence.
        assert r < 0.4


class TestRadialOnBeat:
    def test_no_onsets_zero(self) -> None:
        rs = np.full(20, 0.5)
        assert compute_radial_on_beat(rs, np.zeros(20)) == 0.0

    def test_radial_lift_on_onsets(self) -> None:
        n = 30
        rs = np.zeros(n)
        on = np.zeros(n)
        for i in (5, 12, 20):
            rs[i] = 1.0
            on[i] = 1.0
        score = compute_radial_on_beat(rs, on)
        assert score > 0.5


class TestSpectralRatioMatch:
    def test_short_signals_zero(self) -> None:
        assert compute_spectral_ratio_match(np.array([1.0]), np.array([1.0])) == 0.0

    def test_identical_signals_high_match(self) -> None:
        n = 64
        period = 8
        sig = np.sin(2.0 * np.pi * np.arange(n) / period)
        m = compute_spectral_ratio_match(sig, sig)
        assert m > 0.9

    def test_orthogonal_signals_low_match(self) -> None:
        n = 64
        a = np.sin(2.0 * np.pi * np.arange(n) / 4.0)
        b = np.sin(2.0 * np.pi * np.arange(n) / 16.0)
        m = compute_spectral_ratio_match(a, b)
        assert m < 0.7  # different harmonic ladders


class TestCombine:
    def test_zero_inputs_zero(self) -> None:
        assert combine(0.0, 0.0, 0.0, 0.0) == 0.0

    def test_max_inputs_clipped(self) -> None:
        s = combine(1.0, 1.0, 1.0, 1.0)
        assert s == pytest.approx(ALPHA + BETA + GAMMA)
        assert 0.0 <= s <= 1.0

    def test_phase_lock_only_without_agree_collapses_alpha(self) -> None:
        # The discriminator: agree × φ_lock — both must be high for α to fire.
        s = combine(0.0, 1.0, 0.0, 0.0)
        assert s == 0.0
        s2 = combine(1.0, 0.0, 0.0, 0.0)
        assert s2 == 0.0


# ── Oracle integration tests ──────────────────────────────────────────────


class TestOracleSilence:
    def test_silence_quiescent_yields_zero(self) -> None:
        oracle = AntiVisualizerOracle()
        _feed(
            oracle,
            n=int(TARGET_FPS * 5),
            obs_fn=lambda i, t: _obs(),
            audio_fn=lambda i, t: _audio(rms=0.0),
        )
        result = oracle.evaluate()
        assert result.silence_guard is True
        assert result.score == 0.0

    def test_silent_drifting_observables_still_silence(self) -> None:
        oracle = AntiVisualizerOracle()
        _feed(
            oracle,
            n=int(TARGET_FPS * 5),
            obs_fn=lambda i, t: _obs(mean=0.5, variance=0.05 * np.sin(t * 2.0), radial=0.3),
            audio_fn=lambda i, t: _audio(rms=0.0),
        )
        result = oracle.evaluate()
        assert result.silence_guard is True
        assert result.score == 0.0

    def test_empty_oracle_silence_guard_true(self) -> None:
        oracle = AntiVisualizerOracle()
        result = oracle.evaluate()
        assert result.silence_guard is True
        assert result.score == 0.0


class TestOracleModulation:
    """Modulation-only: brightness lifts uniformly with audio RMS."""

    def test_modulation_only_below_threshold(self) -> None:
        oracle = AntiVisualizerOracle()
        rng = np.random.default_rng(7)
        rms_signal = 0.05 + 0.3 * rng.random(int(TARGET_FPS * 5))
        _feed(
            oracle,
            n=rms_signal.size,
            # Mean luminance follows audio RMS uniformly; variance flat.
            obs_fn=lambda i, t: _obs(
                mean=0.3 + 0.5 * float(rms_signal[i]),
                variance=0.001,
                radial=0.0,
            ),
            audio_fn=lambda i, t: _audio(rms=float(rms_signal[i]), onset=0.0),
        )
        result = oracle.evaluate()
        assert result.silence_guard is False
        assert result.score < S_THRESHOLD


class TestOracleVisualizerRegister:
    """Synthetic visualizer fixtures must score above threshold."""

    def test_milkdrop_radial_bloom_above_threshold(self) -> None:
        oracle = AntiVisualizerOracle()
        # 120 BPM = 2 onsets/sec → at TARGET_FPS=30 → period = 15 samples.
        period_samples = 15
        n = int(TARGET_FPS * 5)

        def obs_fn(i: int, t: float) -> ScrimObservables:
            # Sharp pulse at every period onset → high variance, high radial.
            beat = 1.0 if (i % period_samples) == 0 else 0.0
            return _obs(
                mean=0.4 + 0.5 * beat,
                variance=0.01 + 0.5 * beat,
                radial=0.1 + 0.85 * beat,
                second_moment=0.5,
            )

        def audio_fn(i: int, t: float) -> AudioSignals:
            beat = 1.0 if (i % period_samples) == 0 else 0.0
            return _audio(rms=0.3 + 0.6 * beat, onset=beat, bpm=120.0)

        _feed(oracle, n=n, obs_fn=obs_fn, audio_fn=audio_fn)
        result = oracle.evaluate()
        assert result.silence_guard is False
        assert result.score > S_THRESHOLD
        assert result.radial_on_beat > 0.5

    def test_spectrum_bars_above_threshold(self) -> None:
        oracle = AntiVisualizerOracle()
        period_samples = 12
        n = int(TARGET_FPS * 5)

        def obs_fn(i: int, t: float) -> ScrimObservables:
            beat = 1.0 if (i % period_samples) == 0 else 0.0
            # Vertical bars carve high luminance variance at the beat.
            return _obs(
                mean=0.5,
                variance=0.05 + 0.4 * beat,
                radial=0.0,  # bars are not radially symmetric
                second_moment=0.3,
            )

        def audio_fn(i: int, t: float) -> AudioSignals:
            beat = 1.0 if (i % period_samples) == 0 else 0.0
            return _audio(rms=0.4 + 0.4 * beat, onset=beat, bpm=150.0)

        _feed(oracle, n=n, obs_fn=obs_fn, audio_fn=audio_fn)
        result = oracle.evaluate()
        assert result.silence_guard is False
        # Period agreement + spectral match should drive S above threshold
        # even without radial-on-beat contribution.
        assert result.period_agreement > 0.5
        assert result.score > S_THRESHOLD


class TestOracleDeterministic:
    """Deterministic (audio-independent) effect → S = 0 (silence guard)."""

    def test_deterministic_pattern_under_silence(self) -> None:
        oracle = AntiVisualizerOracle()
        n = int(TARGET_FPS * 5)
        period_samples = 17  # arbitrary, unrelated to any audio

        def obs_fn(i: int, t: float) -> ScrimObservables:
            beat = 1.0 if (i % period_samples) == 0 else 0.0
            return _obs(variance=0.01 + 0.4 * beat, radial=0.1 + 0.7 * beat)

        _feed(
            oracle,
            n=n,
            obs_fn=obs_fn,
            audio_fn=lambda i, t: _audio(rms=0.0),
        )
        result = oracle.evaluate()
        assert result.silence_guard is True
        assert result.score == 0.0


class TestOracleHysteresis:
    """should_dampen() fires only after K consecutive failing windows."""

    def _fill_with_visualizer(self, oracle: AntiVisualizerOracle) -> None:
        period_samples = 15
        n = int(TARGET_FPS * 5)

        def obs_fn(i: int, t: float) -> ScrimObservables:
            beat = 1.0 if (i % period_samples) == 0 else 0.0
            return _obs(
                mean=0.4 + 0.5 * beat,
                variance=0.01 + 0.5 * beat,
                radial=0.1 + 0.85 * beat,
            )

        def audio_fn(i: int, t: float) -> AudioSignals:
            beat = 1.0 if (i % period_samples) == 0 else 0.0
            return _audio(rms=0.3 + 0.6 * beat, onset=beat, bpm=120.0)

        # Replace any prior samples cleanly.
        oracle.samples.clear()
        _feed(oracle, n=n, obs_fn=obs_fn, audio_fn=audio_fn)

    def _fill_with_quiescent(self, oracle: AntiVisualizerOracle) -> None:
        n = int(TARGET_FPS * 5)
        oracle.samples.clear()
        _feed(
            oracle,
            n=n,
            obs_fn=lambda i, t: _obs(mean=0.5, variance=0.001),
            audio_fn=lambda i, t: _audio(rms=0.05, onset=0.0),
        )

    def test_three_failing_windows_dampen(self) -> None:
        oracle = AntiVisualizerOracle()
        for _ in range(HYSTERESIS_WINDOWS):
            self._fill_with_visualizer(oracle)
            oracle.should_dampen()
        assert oracle.should_dampen() is True

    def test_single_failing_window_no_dampen(self) -> None:
        oracle = AntiVisualizerOracle()
        self._fill_with_visualizer(oracle)
        assert oracle.should_dampen() is False

    def test_recovery_after_passing_window(self) -> None:
        oracle = AntiVisualizerOracle()
        for _ in range(HYSTERESIS_WINDOWS + 1):
            self._fill_with_visualizer(oracle)
            oracle.should_dampen()
        assert oracle.should_dampen() is True
        # Switch to quiescent: score collapses well below threshold − Δ.
        self._fill_with_quiescent(oracle)
        # First post-failure call may still hold dampen until the recovery
        # band (threshold - delta) is crossed, which it will be since score
        # is approximately zero on quiescent.
        result = oracle.should_dampen()
        assert result is False


class TestCouplingGain:
    def test_coupling_gain_floors_at_floor(self) -> None:
        oracle = AntiVisualizerOracle()
        # Force many failing windows.
        period_samples = 15
        n = int(TARGET_FPS * 5)
        for _ in range(50):
            oracle.samples.clear()
            for i in range(n):
                ts = i / TARGET_FPS
                beat = 1.0 if (i % period_samples) == 0 else 0.0
                oracle.push(
                    ts,
                    _obs(variance=0.01 + 0.5 * beat, radial=0.1 + 0.85 * beat),
                    _audio(rms=0.4 + 0.5 * beat, onset=beat, bpm=120.0),
                )
            oracle.should_dampen()
        assert oracle.coupling_gain >= COUPLING_GAIN_FLOOR
        assert oracle.coupling_gain < 1.0  # was attenuated

    def test_coupling_gain_never_zero(self) -> None:
        oracle = AntiVisualizerOracle()
        for _ in range(200):
            oracle.samples.clear()
            for i in range(int(TARGET_FPS * 5)):
                ts = i / TARGET_FPS
                oracle.push(
                    ts,
                    _obs(variance=0.5, radial=0.95),
                    _audio(rms=0.9, onset=1.0 if i % 15 == 0 else 0.0, bpm=120.0),
                )
            oracle.should_dampen()
        assert oracle.coupling_gain > 0.0
        assert oracle.coupling_gain >= COUPLING_GAIN_FLOOR


# ── Default projector + calibration ────────────────────────────────────────


class TestDefaultProjector:
    def test_uniform_frame_zero_variance(self) -> None:
        projector = make_default_projector()
        frame = np.full((180, 320, 3), 128, dtype=np.uint8)
        obs = projector.project(frame)
        assert obs.luminance_variance == pytest.approx(0.0, abs=1e-6)
        assert 0.0 <= obs.radial_symmetry_index <= 1.0

    def test_radial_bloom_high_variance(self) -> None:
        projector = make_default_projector()
        h, w = 180, 320
        cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
        yy, xx = np.indices((h, w), dtype=np.float64)
        r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        bloom = np.clip(255.0 * np.exp(-r / 30.0), 0, 255).astype(np.uint8)
        frame = np.stack([bloom, bloom, bloom], axis=-1)
        obs = projector.project(frame)
        assert obs.luminance_variance > 0.01
        assert obs.radial_symmetry_index > 0.7


class TestCalibration:
    def test_calibrate_writes_trace(self, tmp_path: Path) -> None:
        out = tmp_path / "calibration.json"
        neg = [
            VisualizerScore(
                score=s,
                period_agreement=0.0,
                phase_lock=0.0,
                radial_on_beat=0.0,
                spectral_ratio=0.0,
                silence_guard=False,
            )
            for s in (0.10, 0.12, 0.15, 0.18, 0.20)
        ]
        pos = [
            VisualizerScore(
                score=s,
                period_agreement=0.0,
                phase_lock=0.0,
                radial_on_beat=0.0,
                spectral_ratio=0.0,
                silence_guard=False,
            )
            for s in (0.65, 0.70, 0.72, 0.75, 0.80)
        ]
        threshold = calibrate(
            negative_fixtures=neg,
            positive_fixtures=pos,
            out_path=out,
        )
        assert 0.0 <= threshold <= 1.0
        # Threshold must be a 0.05 multiple.
        assert abs((threshold * 20) - round(threshold * 20)) < 1e-9
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["schema_version"] == 1
        assert data["threshold"] == threshold
        assert data["negative_n"] == 5
        assert data["positive_n"] == 5

    def test_calibrate_requires_fixtures(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            calibrate(negative_fixtures=[], positive_fixtures=[], out_path=tmp_path / "x.json")


# ── Hypothesis property: modulation never crosses threshold ────────────────


@st.composite
def _modulation_audio_streams(draw):
    n = draw(st.integers(min_value=60, max_value=150))
    # RMS in [MIN_AUDIO_RMS, 1.0]; onset stays at 0 (modulation, not illustration).
    rms = draw(
        st.lists(
            st.floats(
                min_value=MIN_AUDIO_RMS * 5, max_value=1.0, allow_nan=False, allow_infinity=False
            ),
            min_size=n,
            max_size=n,
        )
    )
    return rms


class TestModulationOnlyProperty:
    @settings(max_examples=20, deadline=None)
    @given(rms_stream=_modulation_audio_streams())
    def test_modulation_only_never_crosses_threshold(self, rms_stream) -> None:
        """Property: radial_symmetry_index ≡ 0 and luminance_variance ≡ const,
        regardless of audio, must score below 0.2 (well under threshold)."""
        oracle = AntiVisualizerOracle()
        for i, r in enumerate(rms_stream):
            ts = i / TARGET_FPS
            oracle.push(
                ts,
                _obs(mean=0.3 + 0.5 * r, variance=0.001, radial=0.0),
                _audio(rms=float(r), onset=0.0),
            )
        result = oracle.evaluate()
        assert result.score < 0.2
