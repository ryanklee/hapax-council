"""Tests for SystemDegradedEngine — Phase 6d-i.A meta-claim.

Mirrors the Phase 1 PresenceEngine regression-pin pattern:
- Empty-input drift toward prior
- Posterior monotonicity under sustained evidence
- State transition timing (HEALTHY→UNCERTAIN→DEGRADED in enter_ticks;
  DEGRADED holds through exit_ticks of recovery before transitioning)
- Surface invariance (name, provides, _required_ticks_for_transition)
- ClaimEngine delegation invariants
- HAPAX_BAYESIAN_BYPASS flow

Phase 6d-i.B wire-in tests live alongside the perception adapter in a
follow-up PR — these tests pin the engine math only.
"""

from __future__ import annotations

from agents.hapax_daimonion.system_degraded_engine import SystemDegradedEngine


def _degraded() -> dict[str, bool | None]:
    """All four default signals firing — strong degradation evidence."""
    return {
        "engine_queue_depth_high": True,
        "drift_significant": True,
        "gpu_pressure_high": True,
        "director_cadence_missed": True,
    }


def _healthy() -> dict[str, bool | None]:
    """All four default signals quiet — strong healthy evidence."""
    return {
        "engine_queue_depth_high": False,
        "drift_significant": False,
        "gpu_pressure_high": False,
        "director_cadence_missed": False,
    }


# ── Empty-input drift ────────────────────────────────────────────────


class TestEmptyInputDecay:
    def test_no_signals_drifts_toward_prior(self):
        eng = SystemDegradedEngine(prior=0.1)
        for _ in range(10):
            eng.contribute({})
        # No observations → posterior decays toward prior 0.1.
        assert abs(eng.posterior - 0.1) < 0.05


# ── Posterior monotonicity ───────────────────────────────────────────


class TestPosteriorMonotonicity:
    def test_strong_degradation_drives_posterior_high(self):
        eng = SystemDegradedEngine(prior=0.1)
        prior_p = eng.posterior
        for _ in range(5):
            eng.contribute(_degraded())
        assert eng.posterior > prior_p
        assert eng.posterior > 0.9

    def test_strong_healthy_drives_posterior_low(self):
        # Start with degradation belief and then apply sustained healthy.
        eng = SystemDegradedEngine(prior=0.7)
        for _ in range(5):
            eng.contribute(_healthy())
        assert eng.posterior < 0.5


# ── State transition timing ──────────────────────────────────────────


class TestStateTransitionTiming:
    def test_uncertain_to_degraded_in_enter_ticks(self):
        eng = SystemDegradedEngine(prior=0.1, enter_ticks=2)
        # Tick 1: posterior shoots up but state still UNCERTAIN due to dwell.
        eng.contribute(_degraded())
        assert eng.state == "UNCERTAIN"
        # Tick 2: dwell satisfied, transitions to DEGRADED.
        eng.contribute(_degraded())
        assert eng.state == "DEGRADED"

    def test_degraded_holds_during_recovery_dwell(self):
        """DEGRADED→HEALTHY uses exit_ticks=12 dwell so a brief healthy
        burst doesn't flip the system back into HEALTHY prematurely."""
        eng = SystemDegradedEngine(prior=0.1, enter_ticks=2, exit_ticks=12)
        # Get to DEGRADED first
        for _ in range(3):
            eng.contribute(_degraded())
        assert eng.state == "DEGRADED"
        # Apply sustained healthy — must hold DEGRADED through dwell.
        for tick in range(8):
            eng.contribute(_healthy())
            assert eng.state == "DEGRADED", (
                f"Premature exit at tick {tick + 1}; DEGRADED must hold "
                "≥8 healthy ticks under exit_ticks=12"
            )

    def test_uncertain_to_healthy_uses_4_tick_dwell(self):
        """UNCERTAIN-state transitions use the k_uncertain=4 dwell from
        TemporalProfile, mirroring PresenceEngine semantics."""
        eng = SystemDegradedEngine(prior=0.5)
        # Sustained healthy → eventually transitions to HEALTHY.
        for _ in range(10):
            eng.contribute(_healthy())
        assert eng.state in ("UNCERTAIN", "HEALTHY")


# ── Surface invariance ───────────────────────────────────────────────


class TestSurface:
    def test_name(self):
        assert SystemDegradedEngine.name == "system_degraded_engine"

    def test_provides(self):
        eng = SystemDegradedEngine()
        assert "system_degraded_probability" in eng.provides
        assert "system_degraded_state" in eng.provides

    def test_required_ticks_helper(self):
        eng = SystemDegradedEngine(enter_ticks=2, exit_ticks=12)
        assert eng._required_ticks_for_transition("UNCERTAIN", "DEGRADED") == 2
        assert eng._required_ticks_for_transition("DEGRADED", "HEALTHY") == 12
        assert eng._required_ticks_for_transition("UNCERTAIN", "HEALTHY") == 4
        assert eng._required_ticks_for_transition("HEALTHY", "UNCERTAIN") == 4


# ── ClaimEngine delegation invariants ────────────────────────────────


class TestDelegationInvariants:
    def test_internal_engine_is_claim_engine(self):
        from shared.claim import ClaimEngine

        eng = SystemDegradedEngine()
        assert isinstance(eng._engine, ClaimEngine)

    def test_engine_state_translates_to_degraded_state(self):
        """ASSERTED ↔ DEGRADED, UNCERTAIN ↔ UNCERTAIN, RETRACTED ↔ HEALTHY."""
        eng = SystemDegradedEngine(prior=0.1, enter_ticks=2)
        for _ in range(3):
            eng.contribute(_degraded())
        assert eng._engine.state == "ASSERTED"
        assert eng.state == "DEGRADED"

    def test_posterior_matches_engine_posterior(self):
        eng = SystemDegradedEngine()
        eng.contribute(_degraded())
        assert eng.posterior == eng._engine.posterior

    def test_reset_returns_to_prior(self):
        eng = SystemDegradedEngine(prior=0.1)
        for _ in range(5):
            eng.contribute(_degraded())
        assert eng.posterior > 0.5
        eng.reset()
        assert eng.posterior == 0.1
        assert eng.state == "UNCERTAIN"


# ── HAPAX_BAYESIAN_BYPASS flows through ──────────────────────────────


class TestBypassFlow:
    def test_bypass_freezes_posterior_at_prior(self, monkeypatch):
        monkeypatch.setenv("HAPAX_BAYESIAN_BYPASS", "1")
        eng = SystemDegradedEngine(prior=0.2)
        for _ in range(20):
            eng.contribute(_degraded())
        assert eng._engine.posterior == 0.2
        assert eng.state == "UNCERTAIN"
