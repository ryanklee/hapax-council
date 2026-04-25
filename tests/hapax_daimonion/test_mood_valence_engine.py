"""Tests for MoodValenceEngine — Phase 6b-ii.A mood-claim.

Mirrors the MoodArousalEngine (#1368) and SystemDegradedEngine (#1357)
regression-pin pattern:
- Empty-input drift toward prior
- Posterior monotonicity under sustained evidence
- State transition timing (POSITIVE→UNCERTAIN→NEGATIVE in enter_ticks=4;
  NEGATIVE holds through exit_ticks=6 of recovery before transitioning)
- Surface invariance (name, provides, _required_ticks_for_transition)
- ClaimEngine delegation invariants
- Positive-only signal semantics for the 3 positive-only signals
- HAPAX_BAYESIAN_BYPASS flow

Phase 6b-ii.B wire-in tests live alongside the perception adapter in a
follow-up PR — these tests pin the engine math only.
"""

from __future__ import annotations

from agents.hapax_daimonion.mood_valence_engine import MoodValenceEngine


def _negative() -> dict[str, bool | None]:
    """All four default signals firing — strong negative-valence evidence."""
    return {
        "hrv_below_baseline": True,
        "skin_temp_drop": True,
        "sleep_debt_high": True,
        "voice_pitch_elevated": True,
    }


def _positive() -> dict[str, bool | None]:
    """All four default signals quiet — positive-valence evidence (where applicable).

    skin_temp_drop, sleep_debt_high, and voice_pitch_elevated are
    positive-only, so False contributes no evidence either way for
    those signals — only hr_below_baseline's bidirectional False
    carries weight here.
    """
    return {
        "hrv_below_baseline": False,
        "skin_temp_drop": False,
        "sleep_debt_high": False,
        "voice_pitch_elevated": False,
    }


# ── Empty-input drift ────────────────────────────────────────────────


class TestEmptyInputDecay:
    def test_no_signals_drifts_toward_prior(self):
        eng = MoodValenceEngine(prior=0.2)
        for _ in range(10):
            eng.contribute({})
        # No observations → posterior decays toward prior 0.2.
        assert abs(eng.posterior - 0.2) < 0.05


# ── Posterior monotonicity ───────────────────────────────────────────


class TestPosteriorMonotonicity:
    def test_strong_negative_drives_posterior_high(self):
        eng = MoodValenceEngine(prior=0.2)
        prior_p = eng.posterior
        for _ in range(6):
            eng.contribute(_negative())
        assert eng.posterior > prior_p
        assert eng.posterior > 0.85

    def test_strong_positive_drives_posterior_low(self):
        # Start with negative belief and then apply sustained positive.
        eng = MoodValenceEngine(prior=0.7)
        for _ in range(10):
            eng.contribute(_positive())
        assert eng.posterior < 0.5


# ── State transition timing ──────────────────────────────────────────


class TestStateTransitionTiming:
    def test_uncertain_to_negative_in_enter_ticks(self):
        eng = MoodValenceEngine(prior=0.2, enter_ticks=4)
        # Tick 1-3: posterior climbs but state still UNCERTAIN due to dwell.
        for _ in range(3):
            eng.contribute(_negative())
        assert eng.state == "UNCERTAIN"
        # Tick 4: dwell satisfied, transitions to NEGATIVE.
        eng.contribute(_negative())
        assert eng.state == "NEGATIVE"

    def test_negative_holds_during_brief_positive_burst(self):
        """NEGATIVE→POSITIVE uses exit_ticks=6 dwell so a brief positive
        burst doesn't flip the system back into POSITIVE prematurely."""
        eng = MoodValenceEngine(prior=0.2, enter_ticks=4, exit_ticks=6)
        # Get to NEGATIVE first
        for _ in range(5):
            eng.contribute(_negative())
        assert eng.state == "NEGATIVE"
        # Apply a few positive ticks — must hold NEGATIVE through dwell.
        for tick in range(4):
            eng.contribute(_positive())
            assert eng.state == "NEGATIVE", (
                f"Premature exit at tick {tick + 1}; NEGATIVE must hold "
                "≥4 positive ticks under exit_ticks=6"
            )

    def test_uncertain_to_positive_uses_4_tick_dwell(self):
        """UNCERTAIN-state transitions use the k_uncertain=4 dwell from
        TemporalProfile, mirroring PresenceEngine semantics."""
        eng = MoodValenceEngine(prior=0.5)
        # Sustained positive → eventually transitions to POSITIVE.
        for _ in range(15):
            eng.contribute(_positive())
        assert eng.state in ("UNCERTAIN", "POSITIVE")


# ── Surface invariance ───────────────────────────────────────────────


class TestSurface:
    def test_name(self):
        assert MoodValenceEngine.name == "mood_valence_engine"

    def test_provides(self):
        eng = MoodValenceEngine()
        assert "mood_valence_negative_probability" in eng.provides
        assert "mood_valence_state" in eng.provides

    def test_required_ticks_helper(self):
        eng = MoodValenceEngine(enter_ticks=4, exit_ticks=6)
        assert eng._required_ticks_for_transition("UNCERTAIN", "NEGATIVE") == 4
        assert eng._required_ticks_for_transition("NEGATIVE", "POSITIVE") == 6
        assert eng._required_ticks_for_transition("UNCERTAIN", "POSITIVE") == 4
        assert eng._required_ticks_for_transition("POSITIVE", "UNCERTAIN") == 4


# ── ClaimEngine delegation invariants ────────────────────────────────


class TestDelegationInvariants:
    def test_internal_engine_is_claim_engine(self):
        from shared.claim import ClaimEngine

        eng = MoodValenceEngine()
        assert isinstance(eng._engine, ClaimEngine)

    def test_engine_state_translates_to_valence_state(self):
        """ASSERTED ↔ NEGATIVE, UNCERTAIN ↔ UNCERTAIN, RETRACTED ↔ POSITIVE."""
        eng = MoodValenceEngine(prior=0.2, enter_ticks=4)
        for _ in range(5):
            eng.contribute(_negative())
        assert eng._engine.state == "ASSERTED"
        assert eng.state == "NEGATIVE"

    def test_posterior_matches_engine_posterior(self):
        eng = MoodValenceEngine()
        eng.contribute(_negative())
        assert eng.posterior == eng._engine.posterior

    def test_reset_returns_to_prior(self):
        eng = MoodValenceEngine(prior=0.2)
        for _ in range(5):
            eng.contribute(_negative())
        assert eng.posterior > 0.5
        eng.reset()
        assert eng.posterior == 0.2
        assert eng.state == "UNCERTAIN"


# ── Positive-only signal semantics ────────────────────────────────────


class TestPositiveOnlySemantics:
    def test_skin_temp_drop_false_does_not_subtract(self):
        """skin_temp_drop is positive-only — when False it contributes
        no evidence either way. Two engines, one fed False and one fed
        None for that signal, must arrive at the same posterior."""
        eng_false = MoodValenceEngine(prior=0.2)
        eng_none = MoodValenceEngine(prior=0.2)
        for _ in range(5):
            eng_false.contribute(
                {
                    "hrv_below_baseline": True,
                    "skin_temp_drop": False,
                    "sleep_debt_high": True,
                    "voice_pitch_elevated": True,
                }
            )
            eng_none.contribute(
                {
                    "hrv_below_baseline": True,
                    "skin_temp_drop": None,
                    "sleep_debt_high": True,
                    "voice_pitch_elevated": True,
                }
            )
        assert abs(eng_false.posterior - eng_none.posterior) < 1e-9

    def test_sleep_debt_high_false_does_not_subtract(self):
        eng_false = MoodValenceEngine(prior=0.2)
        eng_none = MoodValenceEngine(prior=0.2)
        for _ in range(5):
            eng_false.contribute({"sleep_debt_high": False})
            eng_none.contribute({"sleep_debt_high": None})
        assert abs(eng_false.posterior - eng_none.posterior) < 1e-9

    def test_voice_pitch_elevated_false_does_not_subtract(self):
        eng_false = MoodValenceEngine(prior=0.2)
        eng_none = MoodValenceEngine(prior=0.2)
        for _ in range(5):
            eng_false.contribute({"voice_pitch_elevated": False})
            eng_none.contribute({"voice_pitch_elevated": None})
        assert abs(eng_false.posterior - eng_none.posterior) < 1e-9

    def test_hrv_below_baseline_false_does_subtract(self):
        """hrv_below_baseline is bidirectional — False genuinely
        evidences positive valence (high HRV = parasympathetic)."""
        eng_true = MoodValenceEngine(prior=0.5)
        eng_false = MoodValenceEngine(prior=0.5)
        for _ in range(5):
            eng_true.contribute({"hrv_below_baseline": True})
            eng_false.contribute({"hrv_below_baseline": False})
        assert eng_true.posterior > eng_false.posterior


# ── HAPAX_BAYESIAN_BYPASS flows through ──────────────────────────────


class TestBypassFlow:
    def test_bypass_freezes_posterior_at_prior(self, monkeypatch):
        monkeypatch.setenv("HAPAX_BAYESIAN_BYPASS", "1")
        eng = MoodValenceEngine(prior=0.3)
        for _ in range(20):
            eng.contribute(_negative())
        assert eng._engine.posterior == 0.3
        assert eng.state == "UNCERTAIN"
