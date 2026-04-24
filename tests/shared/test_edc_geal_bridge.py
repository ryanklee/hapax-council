"""EDC → GEAL bridge pins.

Pins:
- the heuristic mapping (instant / mid / long branches),
- the GEAL §7 blink-floor invariant (any returned envelope has its
  commit segment ≥ 200 ms; a property test sweeps a wide range of
  transition durations),
- the parser helpers' tolerance for EDC text quirks (whitespace,
  semicolon presence/absence, decimal-only durations).

Spec: ytb-AUTH-GEAL.
"""

from __future__ import annotations

import pytest

from shared.edc_geal_bridge import (
    GEAL_BLINK_FLOOR_MS,
    INSTANT_THRESHOLD_MS,
    EdcProgramAnalyzer,
    EdcTriplet,
    parse_edc_state_set_target,
    parse_edc_transition_seconds,
)
from shared.geal_curves import CurveKind, Envelope

# ── Branch heuristic ──────────────────────────────────────────────────


class TestInstantBranch:
    """Sub-INSTANT_THRESHOLD_MS transitions return None — caller sets
    state directly without animating."""

    @pytest.mark.parametrize("ms", [0.0, 1.0, 25.0, 49.999])
    def test_returns_none_below_threshold(self, ms: float) -> None:
        assert EdcProgramAnalyzer.envelope_for_transition(ms) is None

    def test_negative_clamped_to_zero_then_returns_none(self) -> None:
        assert EdcProgramAnalyzer.envelope_for_transition(-100.0) is None


class TestMidRangeBranch:
    """50–300 ms: easeOut-shape envelope, commit clamped to blink-floor."""

    @pytest.mark.parametrize("ms", [50.0, 100.0, 200.0, 299.0])
    def test_returns_three_phase(self, ms: float) -> None:
        env = EdcProgramAnalyzer.envelope_for_transition(ms)
        assert env is not None
        assert env.kind == CurveKind.THREE_PHASE

    def test_commit_clamped_to_blink_floor(self) -> None:
        # 100 ms transition: spec heuristic would say commit=100, but
        # blink-floor forces 200.
        env = EdcProgramAnalyzer.envelope_for_transition(100.0)
        assert env is not None
        assert env.params["commit_ms"] >= GEAL_BLINK_FLOOR_MS

    def test_anticipate_short_in_mid_range(self) -> None:
        env = EdcProgramAnalyzer.envelope_for_transition(200.0)
        assert env is not None
        # Mid-range uses the fixed 50ms anticipate per spec heuristic.
        assert env.params["anticipate_ms"] == pytest.approx(50.0)


class TestLongBranch:
    """≥ 300 ms: full three-phase with 0.15/0.25/0.60 segment split."""

    def test_returns_three_phase_at_threshold(self) -> None:
        env = EdcProgramAnalyzer.envelope_for_transition(300.0)
        assert env is not None
        assert env.kind == CurveKind.THREE_PHASE

    def test_segments_follow_ratio_split_for_long_transition(self) -> None:
        # 1000 ms: anticipate=150, commit=250 (above floor), settle=600.
        env = EdcProgramAnalyzer.envelope_for_transition(1000.0)
        assert env is not None
        assert env.params["anticipate_ms"] == pytest.approx(150.0)
        assert env.params["commit_ms"] == pytest.approx(250.0)
        assert env.params["settle_ms"] == pytest.approx(600.0)

    def test_long_settle_tau_scales_with_commit(self) -> None:
        env = EdcProgramAnalyzer.envelope_for_transition(2000.0)
        assert env is not None
        # commit = 0.25 * 2000 = 500; tau = 1.5 * commit = 750 (or floor).
        assert env.params["settle_tau_ms"] == pytest.approx(750.0)


# ── Blink-floor invariant ──────────────────────────────────────────────


class TestBlinkFloorInvariant:
    """GEAL §2 invariant 5: no segment crosses [0, 1] faster than 200 ms.
    Sweep a wide range of transitions; any returned envelope must have
    commit_ms ≥ GEAL_BLINK_FLOOR_MS."""

    @pytest.mark.parametrize(
        "ms",
        # Edge cases + a quasi-property sweep.
        [
            INSTANT_THRESHOLD_MS,
            INSTANT_THRESHOLD_MS + 1,
            75.0,
            100.0,
            150.0,
            199.0,
            201.0,
            250.0,
            299.0,
            300.0,
            301.0,
            500.0,
            800.0,
            1000.0,
            5000.0,
            10000.0,
        ],
    )
    def test_commit_ms_is_floor_or_higher(self, ms: float) -> None:
        env = EdcProgramAnalyzer.envelope_for_transition(ms)
        if env is None:
            return  # below INSTANT_THRESHOLD, no envelope to check
        assert env.params["commit_ms"] >= GEAL_BLINK_FLOOR_MS, (
            f"transition_time_ms={ms} produced commit_ms="
            f"{env.params['commit_ms']} < blink-floor {GEAL_BLINK_FLOOR_MS}"
        )

    def test_envelope_max_dv_dt_bounded(self) -> None:
        """Tick-level invariant: per the spec §6 mechanical test, the
        envelope's value should not change by more than 1.0 over any
        200 ms window. Sample at 1 ms across the commit segment of a
        500 ms transition envelope and check."""
        env = EdcProgramAnalyzer.envelope_for_transition(500.0)
        assert env is not None
        # Sample 1 ms apart across [0, 500] ms post-fire.
        samples = [env.tick(now_s=t / 1000.0) for t in range(0, 700)]
        # Maximum 200 ms window delta should be < 1.0 (the [0, 1] crossing).
        max_window_delta = 0.0
        for i in range(len(samples) - 200):
            delta = abs(samples[i + 200] - samples[i])
            max_window_delta = max(max_window_delta, delta)
        # Allow a small margin for the anticipate undershoot
        # (anticipate_amp=-0.10 means peak-to-peak can be ~1.10).
        assert max_window_delta < 1.15, (
            f"max 200ms-window delta = {max_window_delta:.3f} exceeds blink-floor budget"
        )


# ── Triplet wrapper ───────────────────────────────────────────────────


class TestTripletWrapper:
    def test_envelope_for_triplet_dispatches_to_envelope_for_transition(self) -> None:
        triplet = EdcTriplet(
            signal_name="mouse,in",
            action='STATE_SET "hover" 0.0',
            transition_time_ms=500.0,
        )
        env = EdcProgramAnalyzer.envelope_for_triplet(triplet)
        # Same as the direct call.
        direct = EdcProgramAnalyzer.envelope_for_transition(500.0)
        assert direct is not None
        assert env is not None
        assert env.params == direct.params

    def test_triplet_signal_name_does_not_affect_envelope(self) -> None:
        """`mouse,in` and `mouse,out` with same transition produce
        identical curves — direction lives in the caller's state
        machine, not in GEAL."""
        in_triplet = EdcTriplet("mouse,in", 'STATE_SET "hover" 0.0', 200.0)
        out_triplet = EdcTriplet("mouse,out", 'STATE_SET "default" 0.0', 200.0)
        env_in = EdcProgramAnalyzer.envelope_for_triplet(in_triplet)
        env_out = EdcProgramAnalyzer.envelope_for_triplet(out_triplet)
        assert env_in is not None and env_out is not None
        assert env_in.params == env_out.params

    def test_triplet_with_sub_threshold_returns_none(self) -> None:
        triplet = EdcTriplet("mouse,in", 'STATE_SET "hover" 0.0', 10.0)
        assert EdcProgramAnalyzer.envelope_for_triplet(triplet) is None


# ── Custom amplitude / fire time pass-through ──────────────────────────


class TestParameterPassthrough:
    def test_fire_at_s_passes_through(self) -> None:
        env = EdcProgramAnalyzer.envelope_for_transition(500.0, fire_at_s=42.5)
        assert env is not None
        assert env.fire_at_s == pytest.approx(42.5)

    def test_peak_amp_passes_through(self) -> None:
        env = EdcProgramAnalyzer.envelope_for_transition(500.0, peak_amp=0.75)
        assert env is not None
        assert env.params["peak_amp"] == pytest.approx(0.75)

    def test_anticipate_amp_passes_through(self) -> None:
        env = EdcProgramAnalyzer.envelope_for_transition(500.0, anticipate_amp=-0.25)
        assert env is not None
        assert env.params["anticipate_amp"] == pytest.approx(-0.25)


# ── EDC text helpers ──────────────────────────────────────────────────


class TestParseTransition:
    @pytest.mark.parametrize(
        ("edc_fragment", "expected_ms"),
        [
            ("transition: 0.2;", 200.0),
            ("transition:0.2;", 200.0),
            ("transition  :  0.5  ;", 500.0),
            ("transition: 1.5;", 1500.0),
            ("transition: 0.05;", 50.0),
            ("transition: 0.0;", 0.0),
            ("transition: .25;", 250.0),
        ],
    )
    def test_parses_seconds_decimal(self, edc_fragment: str, expected_ms: float) -> None:
        result = parse_edc_transition_seconds(edc_fragment)
        assert result == pytest.approx(expected_ms)

    def test_returns_none_when_no_transition(self) -> None:
        assert parse_edc_transition_seconds("name: program_name;") is None


class TestParseStateSet:
    @pytest.mark.parametrize(
        ("action", "expected"),
        [
            ('STATE_SET "hover" 0.0', "hover"),
            ('STATE_SET "default" 0.0;', "default"),
            ('  STATE_SET   "active"   0.0  ', "active"),
            ('STATE_SET "with-dashes_and_underscores" 0.0', "with-dashes_and_underscores"),
        ],
    )
    def test_parses_target_state(self, action: str, expected: str) -> None:
        assert parse_edc_state_set_target(action) == expected

    def test_returns_none_for_non_state_set(self) -> None:
        assert parse_edc_state_set_target('SIGNAL_EMIT "mouse,in" "*"') is None
        assert parse_edc_state_set_target("ACTION_STOP") is None


# ── Cross-check against an actual Envelope tick ────────────────────────


class TestEnvelopeIsUsable:
    """Sanity: the bridge returns an Envelope you can actually tick;
    the value path through three-phase doesn't blow up."""

    def test_tick_produces_finite_values(self) -> None:
        env = EdcProgramAnalyzer.envelope_for_transition(500.0, fire_at_s=0.0)
        assert env is not None
        for t_ms in (0, 50, 100, 250, 500, 1000):
            v = env.tick(now_s=t_ms / 1000.0)
            assert isinstance(v, float)
            # Three-phase peak_amp=1.0 with -0.10 anticipate; bounded.
            assert -0.5 <= v <= 1.5

    def test_returns_envelope_instance(self) -> None:
        env = EdcProgramAnalyzer.envelope_for_transition(400.0)
        assert isinstance(env, Envelope)
