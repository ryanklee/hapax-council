"""Phase 6c-i regression for ``SpeakerIsOperatorEngine``.

Pins the asymmetric temporal-profile semantics + calibrated-posterior
delegation to ``ClaimEngine[bool]``. Mirrors the structure of
``test_presence_engine_phase1_regression.py``.

Spec: ``docs/research/2026-04-24-universal-bayesian-claim-confidence.md``.
"""

from __future__ import annotations

from agents.hapax_daimonion.speaker_is_operator_engine import (
    CLAIM_NAME,
    DEFAULT_LR,
    DEFAULT_TEMPORAL_PROFILE,
    SESSION_SPEAKER_SIGNAL,
    SpeakerIsOperatorEngine,
)


class TestEngineInit:
    def test_starts_at_prior(self) -> None:
        eng = SpeakerIsOperatorEngine(prior=0.5)
        assert abs(eng.posterior - 0.5) < 1e-9

    def test_starts_uncertain(self) -> None:
        eng = SpeakerIsOperatorEngine()
        assert eng.state == "UNCERTAIN"

    def test_constants_match_dispatch(self) -> None:
        """Pin the dispatch-specified temporal-profile constants."""
        assert DEFAULT_TEMPORAL_PROFILE.enter_threshold == 0.7
        assert DEFAULT_TEMPORAL_PROFILE.exit_threshold == 0.3
        assert DEFAULT_TEMPORAL_PROFILE.k_enter == 2
        assert DEFAULT_TEMPORAL_PROFILE.k_exit == 10

    def test_single_signal_lr_record(self) -> None:
        """Phase 6c-i ships single-signal claim; future phases compose."""
        assert DEFAULT_LR.signal_name == SESSION_SPEAKER_SIGNAL
        assert DEFAULT_LR.claim_name == CLAIM_NAME
        assert DEFAULT_LR.positive_only is False  # bidirectional


class TestFastEnter:
    """Operator speaks → assert in ~2 ticks per the asymmetric profile."""

    def test_two_consecutive_true_asserts(self) -> None:
        eng = SpeakerIsOperatorEngine(prior=0.5)
        eng.tick(session_speaker_says_operator=True)
        eng.tick(session_speaker_says_operator=True)
        assert eng.state == "ASSERTED"

    def test_one_true_does_not_assert(self) -> None:
        """k_enter=2 — one tick above threshold is not enough."""
        eng = SpeakerIsOperatorEngine(prior=0.5)
        eng.tick(session_speaker_says_operator=True)
        # After one tick: posterior raised but state still uncertain.
        assert eng.state == "UNCERTAIN"


class TestSlowExit:
    """Silence (False) does NOT immediately retract the assertion."""

    def _enter_asserted(self) -> SpeakerIsOperatorEngine:
        eng = SpeakerIsOperatorEngine(prior=0.5)
        # Drive into ASSERTED.
        for _ in range(4):
            eng.tick(session_speaker_says_operator=True)
        assert eng.state == "ASSERTED"
        return eng

    def test_one_false_does_not_retract(self) -> None:
        eng = self._enter_asserted()
        eng.tick(session_speaker_says_operator=False)
        # Posterior dipped, but state stays ASSERTED (k_exit=10).
        assert eng.state == "ASSERTED"

    def test_few_falses_does_not_retract(self) -> None:
        eng = self._enter_asserted()
        for _ in range(3):
            eng.tick(session_speaker_says_operator=False)
        assert eng.state == "ASSERTED"

    def test_sustained_false_retracts(self) -> None:
        eng = self._enter_asserted()
        for _ in range(20):
            eng.tick(session_speaker_says_operator=False)
        assert eng.state == "RETRACTED"


class TestNoneObservations:
    """``None`` (session inactive) lets posterior drift toward prior."""

    def test_none_does_not_crash(self) -> None:
        eng = SpeakerIsOperatorEngine()
        eng.tick(session_speaker_says_operator=None)
        # After one None tick, no-op; posterior unchanged from prior.

    def test_none_after_assert_holds_state(self) -> None:
        eng = SpeakerIsOperatorEngine(prior=0.5)
        for _ in range(4):
            eng.tick(session_speaker_says_operator=True)
        for _ in range(3):
            eng.tick(session_speaker_says_operator=None)
        # None ticks don't apply LR — state holds.
        assert eng.state == "ASSERTED"


class TestAssertedConvenience:
    """``asserted()`` is the wire-in shape — replaces raw bool consumer."""

    def test_default_threshold_07(self) -> None:
        eng = SpeakerIsOperatorEngine(prior=0.5)
        # At prior 0.5, asserted(threshold=0.7) is False.
        assert eng.asserted() is False

    def test_after_drive_high_returns_true(self) -> None:
        eng = SpeakerIsOperatorEngine(prior=0.5)
        for _ in range(5):
            eng.tick(session_speaker_says_operator=True)
        assert eng.asserted() is True

    def test_threshold_override(self) -> None:
        eng = SpeakerIsOperatorEngine(prior=0.5)
        eng.tick(session_speaker_says_operator=True)
        # After one tick the posterior has lifted but well below 0.99.
        assert eng.asserted(threshold=0.99) is False


class TestPosteriorMonotonicity:
    """All-True drives posterior monotonically toward 1.0."""

    def test_monotone_increase_under_true(self) -> None:
        eng = SpeakerIsOperatorEngine(prior=0.5)
        last = eng.posterior
        for _ in range(6):
            eng.tick(session_speaker_says_operator=True)
            cur = eng.posterior
            assert cur >= last
            last = cur

    def test_monotone_decrease_under_false(self) -> None:
        eng = SpeakerIsOperatorEngine(prior=0.5)
        last = eng.posterior
        for _ in range(6):
            eng.tick(session_speaker_says_operator=False)
            cur = eng.posterior
            assert cur <= last
            last = cur


class TestSurfaceInvariance:
    """Properties are read-only mirrors of the underlying engine."""

    def test_posterior_in_unit_interval(self) -> None:
        eng = SpeakerIsOperatorEngine()
        for _ in range(20):
            eng.tick(session_speaker_says_operator=True)
            assert 0.0 <= eng.posterior <= 1.0
        for _ in range(40):
            eng.tick(session_speaker_says_operator=False)
            assert 0.0 <= eng.posterior <= 1.0

    def test_state_is_one_of_three_values(self) -> None:
        eng = SpeakerIsOperatorEngine()
        for _ in range(30):
            eng.tick(session_speaker_says_operator=True)
            assert eng.state in {"ASSERTED", "UNCERTAIN", "RETRACTED"}
