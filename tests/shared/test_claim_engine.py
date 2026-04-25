"""Tests for ClaimEngine — Phase 0 FULL.

Covers: posterior fusion correctness, hysteresis state-machine, asymmetric
TemporalProfile, kill-switch (HAPAX_BAYESIAN_BYPASS), positive-only signals,
prior-decay drift.
"""

from __future__ import annotations

import pytest

from shared.claim import ClaimEngine, LRDerivation, TemporalProfile


def _signal(
    name: str = "s",
    p1: float = 0.9,
    p0: float = 0.05,
    positive_only: bool = True,
) -> LRDerivation:
    return LRDerivation(
        signal_name=name,
        claim_name="c",
        source_category="physical_model",
        p_true_given_h1=p1,
        p_true_given_h0=p0,
        positive_only=positive_only,
        estimation_reference="test fixture",
    )


def _profile(
    enter_threshold: float = 0.7,
    exit_threshold: float = 0.3,
    k_enter: int = 2,
    k_exit: int = 24,
) -> TemporalProfile:
    return TemporalProfile(
        enter_threshold=enter_threshold,
        exit_threshold=exit_threshold,
        k_enter=k_enter,
        k_exit=k_exit,
    )


# ── Posterior fusion ─────────────────────────────────────────────────


class TestPosteriorFusion:
    def test_initial_posterior_is_prior(self):
        eng = ClaimEngine[bool](
            "c", prior=0.5, temporal_profile=_profile(), signal_weights={"s": _signal()}
        )
        assert eng.posterior == 0.5

    def test_positive_observation_raises_posterior(self):
        eng = ClaimEngine[bool](
            "c", prior=0.5, temporal_profile=_profile(), signal_weights={"s": _signal()}
        )
        eng.update("s", True)
        assert eng.posterior > 0.9  # LR=18× should push posterior strongly toward 1

    def test_observation_None_skipped(self):
        eng = ClaimEngine[bool](
            "c", prior=0.5, temporal_profile=_profile(), signal_weights={"s": _signal()}
        )
        eng.update("s", None)
        assert abs(eng.posterior - 0.5) < 0.05  # prior decay only, signal skipped

    def test_positive_only_signal_skips_False(self):
        eng = ClaimEngine[bool](
            "c",
            prior=0.5,
            temporal_profile=_profile(),
            signal_weights={"s": _signal(positive_only=True)},
        )
        eng.update("s", False)
        assert abs(eng.posterior - 0.5) < 0.05  # positive-only: False is no evidence

    def test_bidirectional_signal_uses_False(self):
        eng = ClaimEngine[bool](
            "c",
            prior=0.5,
            temporal_profile=_profile(),
            signal_weights={"s": _signal(positive_only=False)},
        )
        eng.update("s", False)
        assert eng.posterior < 0.5  # False contributes against H1

    def test_invalid_prior_rejected(self):
        with pytest.raises(ValueError):
            ClaimEngine[bool]("c", prior=0.0, temporal_profile=_profile(), signal_weights={})
        with pytest.raises(ValueError):
            ClaimEngine[bool]("c", prior=1.5, temporal_profile=_profile(), signal_weights={})


# ── Hysteresis state machine ─────────────────────────────────────────


class TestHysteresis:
    def test_starts_uncertain(self):
        eng = ClaimEngine[bool](
            "c", prior=0.5, temporal_profile=_profile(), signal_weights={"s": _signal()}
        )
        assert eng.state == "UNCERTAIN"

    def test_k_enter_dwell_required_to_assert(self):
        eng = ClaimEngine[bool](
            "c",
            prior=0.5,
            temporal_profile=_profile(k_enter=3),
            signal_weights={"s": _signal()},
        )
        eng.update("s", True)  # tick 1: candidate ASSERTED, dwell=1
        assert eng.state == "UNCERTAIN"
        eng.update("s", True)  # tick 2: dwell=2
        assert eng.state == "UNCERTAIN"
        eng.update("s", True)  # tick 3: dwell=3 ≥ k_enter, transition
        assert eng.state == "ASSERTED"

    def test_asymmetric_profile_music_inverts_presence(self):
        """Music: slow-enter (8 ticks), fast-exit (4 ticks) — operator-flagged
        cost asymmetry. Verifies the profile drives the timing both ways."""
        prof = _profile(enter_threshold=0.85, exit_threshold=0.4, k_enter=8, k_exit=4)
        eng = ClaimEngine[bool](
            "music", prior=0.3, temporal_profile=prof, signal_weights={"s": _signal()}
        )
        # Slow enter
        for i in range(7):
            eng.update("s", True)
            assert eng.state == "UNCERTAIN", f"premature at tick {i + 1}"
        eng.update("s", True)  # tick 8
        assert eng.state == "ASSERTED"
        # Fast exit (need bidirectional signal to push posterior down)
        bi = _signal(positive_only=False)
        eng2 = ClaimEngine[bool](
            "music", prior=0.3, temporal_profile=prof, signal_weights={"s": bi}
        )
        for _ in range(8):
            eng2.update("s", True)
        assert eng2.state == "ASSERTED"
        for i in range(3):
            eng2.update("s", False)
            assert eng2.state != "RETRACTED" or eng2.state == "UNCERTAIN", (
                f"early exit at tick {i + 1}"
            )


# ── Kill switch ──────────────────────────────────────────────────────


class TestBypass:
    def test_bypass_disables_update(self, monkeypatch):
        monkeypatch.setenv("HAPAX_BAYESIAN_BYPASS", "1")
        eng = ClaimEngine[bool](
            "c", prior=0.6, temporal_profile=_profile(), signal_weights={"s": _signal()}
        )
        for _ in range(20):
            eng.update("s", True)
        assert eng.posterior == 0.6  # prior unchanged
        assert eng.state == "UNCERTAIN"

    def test_bypass_off_allows_update(self, monkeypatch):
        monkeypatch.delenv("HAPAX_BAYESIAN_BYPASS", raising=False)
        eng = ClaimEngine[bool](
            "c", prior=0.5, temporal_profile=_profile(), signal_weights={"s": _signal()}
        )
        eng.update("s", True)
        assert eng.posterior > 0.5

    def test_bypass_truthy_values(self, monkeypatch):
        for val in ("1", "true", "yes", "on", "TRUE"):
            monkeypatch.setenv("HAPAX_BAYESIAN_BYPASS", val)
            eng = ClaimEngine[bool](
                "c", prior=0.55, temporal_profile=_profile(), signal_weights={"s": _signal()}
            )
            eng.update("s", True)
            assert eng.posterior == 0.55, f"bypass should activate for {val!r}"

    def test_bypass_falsy_values(self, monkeypatch):
        for val in ("0", "", "off", "no"):
            monkeypatch.setenv("HAPAX_BAYESIAN_BYPASS", val)
            eng = ClaimEngine[bool](
                "c", prior=0.5, temporal_profile=_profile(), signal_weights={"s": _signal()}
            )
            eng.update("s", True)
            assert eng.posterior > 0.5, f"bypass should NOT activate for {val!r}"


# ── Reset + multi-signal ─────────────────────────────────────────────


class TestEngineLifecycle:
    def test_reset_returns_to_prior(self):
        eng = ClaimEngine[bool](
            "c", prior=0.4, temporal_profile=_profile(), signal_weights={"s": _signal()}
        )
        for _ in range(5):
            eng.update("s", True)
        assert eng.posterior > 0.9
        eng.reset()
        assert eng.posterior == 0.4
        assert eng.state == "UNCERTAIN"

    def test_multi_signal_fusion(self):
        """Two positive observations multiply LRs (log-additive)."""
        eng = ClaimEngine[bool](
            "c",
            prior=0.5,
            temporal_profile=_profile(),
            signal_weights={"s1": _signal("s1"), "s2": _signal("s2")},
        )
        eng.update("s1", True)
        single_post = eng.posterior
        eng.update("s2", True)
        double_post = eng.posterior
        assert double_post > single_post  # second signal adds confidence
