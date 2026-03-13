"""Tests for perceptual agreement invariants — 6 test layers.

Layer 1: Checker mechanics (debounce, event emission, agreement_ok)
Layer 2: Compatibility functions (identity, proximity, freshness, authority, exclusion)
Layer 3: Registry validation
Layer 4: Governance integration (MC + OBS veto chain)
Layer 5: Hypothesis property tests
Layer 6: Candidate invariant scenarios
"""

from __future__ import annotations

import time

from hypothesis import given
from hypothesis import strategies as st

from agents.hapax_voice.agreement import (
    AgreementChecker,
    AgreementRegistry,
    AgreementViolation,
    InvariantSpec,
    InvariantType,
    Role,
    Severity,
    SourceRole,
    authority_match,
    build_default_registry,
    freshness_entailment,
    identity_agreement,
    proximity_agreement,
    state_exclusion,
)
from agents.hapax_voice.governance import FreshnessRequirement, FusedContext
from agents.hapax_voice.primitives import Behavior, Stamped
from agents.hapax_voice.timeline import TimelineMapping, TransportState

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_agreement_behaviors(**kwargs: object) -> dict[str, Behavior]:
    """Create a dict of Behaviors from keyword arguments.

    Each kwarg becomes a Behavior with the given value and a fresh watermark.
    Special keys ending in '_wm' set custom watermarks for the base name.
    """
    wm = kwargs.pop("watermark", None) or time.monotonic()
    watermarks: dict[str, float] = {}
    values: dict[str, object] = {}

    for k, v in kwargs.items():
        if k.endswith("_wm"):
            watermarks[k[:-3]] = v
        else:
            values[k] = v

    behaviors: dict[str, Behavior] = {}
    for name, val in values.items():
        w = watermarks.get(name, wm)
        behaviors[name] = Behavior(val, watermark=w)
    return behaviors


def _make_spec(
    name: str = "test_invariant",
    check: CompatibilityFn | None = None,
    severity: Severity = Severity.HARD,
    min_violation_ticks: int = 3,
    preconditions: tuple[FreshnessRequirement, ...] = (),
) -> InvariantSpec:
    """Create a minimal InvariantSpec for testing."""
    if check is None:
        check = _always_pass
    return InvariantSpec(
        name=name,
        proposition=f"Test proposition for {name}",
        invariant_type=InvariantType.OBSERVATIONAL,
        sources=(SourceRole("test_signal", Role.OBSERVER),),
        check=check,
        severity=severity,
        min_violation_ticks=min_violation_ticks,
        preconditions=preconditions,
    )


def _make_checker(
    behaviors: dict[str, Behavior] | None = None,
    registry: AgreementRegistry | None = None,
) -> AgreementChecker:
    """Create an AgreementChecker with defaults."""
    if behaviors is None:
        behaviors = {}
    if registry is None:
        registry = AgreementRegistry()
    return AgreementChecker(registry, behaviors)


def _always_fail(behaviors: dict[str, Behavior], now: float) -> tuple[bool, str]:
    return False, "always fails"


def _always_pass(behaviors: dict[str, Behavior], now: float) -> tuple[bool, str]:
    return True, ""


# ===========================================================================
# LAYER 1: Checker Mechanics
# ===========================================================================


class TestAgreementCheckerMechanics:
    """Core checker behavior: debounce, event emission, agreement_ok."""

    def test_empty_registry_always_satisfied(self):
        checker = _make_checker()
        result = checker.check(now=100.0)
        assert result.satisfied is True
        assert len(result.violations) == 0
        assert checker.agreement_ok.value is True

    def test_single_invariant_pass(self):
        spec = _make_spec(check=_always_pass)
        registry = AgreementRegistry(invariants=(spec,))
        checker = _make_checker(registry=registry)
        result = checker.check(now=100.0)
        assert result.satisfied is True
        assert len(result.violations) == 0

    def test_single_invariant_fail_under_debounce(self):
        spec = _make_spec(check=_always_fail, min_violation_ticks=3)
        registry = AgreementRegistry(invariants=(spec,))
        checker = _make_checker(registry=registry)

        # Tick 1 and 2: fail but under debounce threshold
        r1 = checker.check(now=100.0)
        assert r1.satisfied is True
        r2 = checker.check(now=101.0)
        assert r2.satisfied is True

    def test_single_invariant_fail_after_debounce(self):
        spec = _make_spec(check=_always_fail, min_violation_ticks=3)
        registry = AgreementRegistry(invariants=(spec,))
        checker = _make_checker(registry=registry)

        checker.check(now=100.0)  # counter=1
        checker.check(now=101.0)  # counter=2
        r3 = checker.check(now=102.0)  # counter=3 >= 3 → violation
        assert r3.satisfied is False
        assert len(r3.violations) == 1
        assert r3.violations[0].invariant_name == "test_invariant"

    def test_recovery_resets_debounce_counter(self):
        """Two failures, then recovery, then three more failures needs full debounce again."""
        should_fail = [True]

        def _controllable(behaviors, now):
            if should_fail[0]:
                return False, "failing"
            return True, ""

        spec = _make_spec(check=_controllable, min_violation_ticks=3)
        registry = AgreementRegistry(invariants=(spec,))
        checker = _make_checker(registry=registry)

        checker.check(now=100.0)  # fail, counter=1
        checker.check(now=101.0)  # fail, counter=2

        should_fail[0] = False
        checker.check(now=102.0)  # pass, counter=0

        should_fail[0] = True
        checker.check(now=103.0)  # fail, counter=1
        checker.check(now=104.0)  # fail, counter=2
        r = checker.check(now=105.0)  # fail, counter=3 → violation
        assert r.satisfied is False

    def test_advisory_violations_dont_block_agreement_ok(self):
        spec = _make_spec(check=_always_fail, severity=Severity.ADVISORY, min_violation_ticks=1)
        registry = AgreementRegistry(invariants=(spec,))
        checker = _make_checker(registry=registry)

        result = checker.check(now=100.0)
        assert result.satisfied is False  # has violations
        assert checker.agreement_ok.value is True  # but advisory only

    def test_hard_violations_block_agreement_ok(self):
        spec = _make_spec(check=_always_fail, severity=Severity.HARD, min_violation_ticks=1)
        registry = AgreementRegistry(invariants=(spec,))
        checker = _make_checker(registry=registry)

        checker.check(now=100.0)
        assert checker.agreement_ok.value is False

    def test_multiple_invariants_all_must_pass(self):
        spec_a = _make_spec(name="a", check=_always_pass)
        spec_b = _make_spec(name="b", check=_always_fail, min_violation_ticks=1)
        registry = AgreementRegistry(invariants=(spec_a, spec_b))
        checker = _make_checker(registry=registry)

        result = checker.check(now=100.0)
        assert result.satisfied is False
        assert len(result.violations) == 1
        assert result.violations[0].invariant_name == "b"

    def test_precondition_not_met_skips_check(self):
        spec = _make_spec(
            check=_always_fail,
            min_violation_ticks=1,
            preconditions=(FreshnessRequirement("some_signal", 5.0),),
        )
        registry = AgreementRegistry(invariants=(spec,))
        # No behaviors → precondition fails → check skipped
        checker = _make_checker(registry=registry)
        result = checker.check(now=100.0)
        assert result.satisfied is True

    def test_violation_event_emitted_on_sustained_failure(self):
        spec = _make_spec(check=_always_fail, min_violation_ticks=2)
        registry = AgreementRegistry(invariants=(spec,))
        checker = _make_checker(registry=registry)

        received: list[AgreementViolation] = []
        checker.violation_event.subscribe(lambda ts, v: received.append(v))

        checker.check(now=100.0)  # counter=1, no event
        assert len(received) == 0
        checker.check(now=101.0)  # counter=2 >= 2, event emitted
        assert len(received) == 1
        assert received[0].violation.invariant_name == "test_invariant"

    def test_violation_event_not_emitted_on_transient_failure(self):
        spec = _make_spec(check=_always_fail, min_violation_ticks=5)
        registry = AgreementRegistry(invariants=(spec,))
        checker = _make_checker(registry=registry)

        received: list[AgreementViolation] = []
        checker.violation_event.subscribe(lambda ts, v: received.append(v))

        for t in range(4):
            checker.check(now=100.0 + t)

        assert len(received) == 0


# ===========================================================================
# LAYER 2: Compatibility Functions
# ===========================================================================


class TestIdentityAgreement:
    def test_same_values_pass(self):
        behaviors = _make_agreement_behaviors(a=42, b=42)
        ok, _ = identity_agreement("a", "b")(behaviors, 100.0)
        assert ok is True

    def test_different_values_fail(self):
        behaviors = _make_agreement_behaviors(a=42, b=99)
        ok, _ = identity_agreement("a", "b")(behaviors, 100.0)
        assert ok is False

    def test_missing_behavior_vacuous(self):
        behaviors = _make_agreement_behaviors(a=42)
        ok, msg = identity_agreement("a", "b")(behaviors, 100.0)
        assert ok is True
        assert "not present" in msg


class TestProximityAgreement:
    def test_within_distance_passes(self):
        behaviors = _make_agreement_behaviors(a=5.0, b=6.0)
        ok, _ = proximity_agreement("a", "b", max_distance=2.0)(behaviors, 100.0)
        assert ok is True

    def test_at_boundary_passes(self):
        behaviors = _make_agreement_behaviors(a=5.0, b=7.0)
        ok, _ = proximity_agreement("a", "b", max_distance=2.0)(behaviors, 100.0)
        assert ok is True

    def test_beyond_distance_fails(self):
        behaviors = _make_agreement_behaviors(a=5.0, b=8.0)
        ok, _ = proximity_agreement("a", "b", max_distance=2.0)(behaviors, 100.0)
        assert ok is False


class TestFreshnessEntailment:
    def test_fresh_and_check_passes(self):
        behaviors = _make_agreement_behaviors(signal=1.0, prop=5)
        fn = freshness_entailment("signal", "prop", lambda v: v > 0, max_staleness_s=5.0)
        ok, _ = fn(behaviors, behaviors["signal"].watermark + 1.0)
        assert ok is True

    def test_fresh_and_check_fails(self):
        behaviors = _make_agreement_behaviors(signal=1.0, prop=0)
        fn = freshness_entailment("signal", "prop", lambda v: v > 0, max_staleness_s=5.0)
        ok, _ = fn(behaviors, behaviors["signal"].watermark + 1.0)
        assert ok is False

    def test_stale_signal_vacuous(self):
        wm = 100.0
        behaviors = {"signal": Behavior(1.0, watermark=wm), "prop": Behavior(0, watermark=wm)}
        fn = freshness_entailment("signal", "prop", lambda v: v > 0, max_staleness_s=5.0)
        ok, msg = fn(behaviors, wm + 10.0)  # 10s stale > 5s max
        assert ok is True
        assert "stale" in msg or "vacuous" in msg


class TestAuthorityMatch:
    def test_match_passes(self):
        behaviors = _make_agreement_behaviors(auth="firefox", dep="firefox")
        ok, _ = authority_match("auth", "dep")(behaviors, 100.0)
        assert ok is True

    def test_mismatch_fails(self):
        behaviors = _make_agreement_behaviors(auth="firefox", dep="chrome")
        ok, _ = authority_match("auth", "dep")(behaviors, 100.0)
        assert ok is False

    def test_missing_vacuous(self):
        behaviors = _make_agreement_behaviors(auth="firefox")
        ok, msg = authority_match("auth", "dep")(behaviors, 100.0)
        assert ok is True
        assert "not present" in msg


class TestStateExclusion:
    def test_possible_state_passes(self):
        behaviors = _make_agreement_behaviors(
            activity_mode="working", vad_confidence=0.8, presence_score="definitely_present"
        )
        impossible = frozenset({("away", True, "definitely_present")})
        # Note: state_exclusion reads raw values, not derived "speaking"
        fn = state_exclusion(("activity_mode", "vad_confidence", "presence_score"), impossible)
        ok, _ = fn(behaviors, 100.0)
        assert ok is True

    def test_impossible_state_fails(self):
        behaviors = _make_agreement_behaviors(a="x", b="y")
        impossible = frozenset({("x", "y")})
        fn = state_exclusion(("a", "b"), impossible)
        ok, _ = fn(behaviors, 100.0)
        assert ok is False


# ===========================================================================
# LAYER 3: Registry Validation
# ===========================================================================


class TestAgreementRegistry:
    def test_duplicate_names_rejected(self):
        spec = _make_spec(name="dup")
        try:
            AgreementRegistry(invariants=(spec, spec))
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "Duplicate" in str(e)

    def test_empty_valid(self):
        reg = AgreementRegistry()
        assert len(reg.invariants) == 0

    def test_single_valid(self):
        spec = _make_spec(name="single")
        reg = AgreementRegistry(invariants=(spec,))
        assert len(reg.invariants) == 1

    def test_default_registry_names_unique(self):
        reg = build_default_registry()
        names = [s.name for s in reg.invariants]
        assert len(names) == len(set(names))

    def test_default_registry_count(self):
        reg = build_default_registry()
        assert len(reg.invariants) == 8


# ===========================================================================
# LAYER 4: Governance Integration
# ===========================================================================


def _make_mc_context_with_agreement(
    agreement_ok_val: bool = True,
    **kwargs,
) -> FusedContext:
    """Build a FusedContext with MC signals + agreement_ok."""
    trigger_time = kwargs.get("trigger_time", 1000.0)
    transport = kwargs.get("transport", TransportState.PLAYING)
    mapping = TimelineMapping(
        reference_time=trigger_time - 10.0,
        reference_beat=0.0,
        tempo=120.0,
        transport=transport,
    )
    samples = {
        "audio_energy_rms": Stamped(value=kwargs.get("energy_rms", 0.7), watermark=trigger_time),
        "emotion_arousal": Stamped(
            value=kwargs.get("emotion_arousal", 0.5), watermark=trigger_time
        ),
        "vad_confidence": Stamped(value=kwargs.get("vad_confidence", 0.0), watermark=trigger_time),
        "timeline_mapping": Stamped(value=mapping, watermark=trigger_time),
        "agreement_ok": Stamped(value=agreement_ok_val, watermark=trigger_time),
    }
    return FusedContext(
        trigger_time=trigger_time,
        trigger_value=trigger_time,
        samples=samples,
        min_watermark=trigger_time,
    )


class TestAgreementGovernanceIntegration:
    def test_agreement_ok_true_allows_mc(self):
        from agents.hapax_voice.mc_governance import build_mc_veto_chain

        ctx = _make_mc_context_with_agreement(agreement_ok_val=True)
        chain = build_mc_veto_chain()
        result = chain.evaluate(ctx)
        assert result.allowed is True

    def test_agreement_ok_false_vetoes_mc(self):
        from agents.hapax_voice.mc_governance import build_mc_veto_chain

        ctx = _make_mc_context_with_agreement(agreement_ok_val=False)
        chain = build_mc_veto_chain()
        result = chain.evaluate(ctx)
        assert result.allowed is False
        assert "agreement_ok" in result.denied_by

    def test_agreement_ok_in_wiring_unqualified(self):
        from agents.hapax_voice.wiring import GovernanceBinding

        binding = GovernanceBinding(energy_source="monitor_mix", emotion_source="face_cam")
        assert "agreement_ok" in binding.unqualified

    def test_agreement_ok_false_vetoes_obs(self):
        from agents.hapax_voice.obs_governance import build_obs_veto_chain

        trigger_time = 1000.0
        mapping = TimelineMapping(
            reference_time=trigger_time - 10.0,
            reference_beat=0.0,
            tempo=120.0,
            transport=TransportState.PLAYING,
        )
        samples = {
            "stream_bitrate": Stamped(value=4500.0, watermark=trigger_time),
            "stream_encoding_lag": Stamped(value=30.0, watermark=trigger_time),
            "timeline_mapping": Stamped(value=mapping, watermark=trigger_time),
            "agreement_ok": Stamped(value=False, watermark=trigger_time),
        }
        ctx = FusedContext(
            trigger_time=trigger_time,
            trigger_value=trigger_time,
            samples=samples,
            min_watermark=trigger_time,
        )
        chain = build_obs_veto_chain()
        result = chain.evaluate(ctx)
        assert result.allowed is False
        assert "agreement_ok" in result.denied_by

    def test_missing_agreement_ok_fails_open(self):
        from agents.hapax_voice.mc_governance import agreement_ok as mc_agreement_ok

        # Context without agreement_ok sample
        samples = {
            "audio_energy_rms": Stamped(value=0.7, watermark=1000.0),
        }
        ctx = FusedContext(
            trigger_time=1000.0,
            trigger_value=1000.0,
            samples=samples,
            min_watermark=1000.0,
        )
        assert mc_agreement_ok(ctx) is True

    def test_operator_identified_true_allows_mc(self):
        from agents.hapax_voice.mc_governance import build_mc_veto_chain

        ctx = _make_mc_context_with_agreement(agreement_ok_val=True)
        # Add operator_identified=True
        ctx = FusedContext(
            trigger_time=ctx.trigger_time,
            trigger_value=ctx.trigger_value,
            samples={
                **ctx.samples,
                "operator_identified": Stamped(value=True, watermark=ctx.trigger_time),
            },
            min_watermark=ctx.min_watermark,
        )
        chain = build_mc_veto_chain()
        result = chain.evaluate(ctx)
        assert result.allowed is True

    def test_operator_identified_false_vetoes_mc(self):
        from agents.hapax_voice.mc_governance import build_mc_veto_chain

        ctx = _make_mc_context_with_agreement(agreement_ok_val=True)
        ctx = FusedContext(
            trigger_time=ctx.trigger_time,
            trigger_value=ctx.trigger_value,
            samples={
                **ctx.samples,
                "operator_identified": Stamped(value=False, watermark=ctx.trigger_time),
            },
            min_watermark=ctx.min_watermark,
        )
        chain = build_mc_veto_chain()
        result = chain.evaluate(ctx)
        assert result.allowed is False
        assert "operator_identified" in result.denied_by

    def test_missing_operator_identified_fails_open_mc(self):
        from agents.hapax_voice.mc_governance import operator_identified as mc_op_id

        samples = {"audio_energy_rms": Stamped(value=0.7, watermark=1000.0)}
        ctx = FusedContext(
            trigger_time=1000.0,
            trigger_value=1000.0,
            samples=samples,
            min_watermark=1000.0,
        )
        assert mc_op_id(ctx) is True

    def test_operator_identified_false_vetoes_obs(self):
        from agents.hapax_voice.obs_governance import build_obs_veto_chain

        trigger_time = 1000.0
        mapping = TimelineMapping(
            reference_time=trigger_time - 10.0,
            reference_beat=0.0,
            tempo=120.0,
            transport=TransportState.PLAYING,
        )
        samples = {
            "stream_bitrate": Stamped(value=4500.0, watermark=trigger_time),
            "stream_encoding_lag": Stamped(value=30.0, watermark=trigger_time),
            "timeline_mapping": Stamped(value=mapping, watermark=trigger_time),
            "agreement_ok": Stamped(value=True, watermark=trigger_time),
            "operator_identified": Stamped(value=False, watermark=trigger_time),
        }
        ctx = FusedContext(
            trigger_time=trigger_time,
            trigger_value=trigger_time,
            samples=samples,
            min_watermark=trigger_time,
        )
        chain = build_obs_veto_chain()
        result = chain.evaluate(ctx)
        assert result.allowed is False
        assert "operator_identified" in result.denied_by

    def test_identity_in_wiring_unqualified(self):
        from agents.hapax_voice.wiring import GovernanceBinding

        binding = GovernanceBinding(energy_source="monitor_mix", emotion_source="face_cam")
        assert "operator_identified" in binding.unqualified
        assert "identity_confidence" in binding.unqualified


# ===========================================================================
# LAYER 5: Hypothesis Property Tests
# ===========================================================================


class TestAgreementProperties:
    @given(st.integers(min_value=1, max_value=20))
    def test_debounce_monotonicity(self, min_ticks: int):
        """Counter increments monotonically until threshold; higher threshold → more tolerance."""
        spec = _make_spec(check=_always_fail, min_violation_ticks=min_ticks)
        registry = AgreementRegistry(invariants=(spec,))
        checker = _make_checker(registry=registry)

        for t in range(min_ticks - 1):
            result = checker.check(now=100.0 + t)
            assert result.satisfied is True

        result = checker.check(now=100.0 + min_ticks - 1)
        assert result.satisfied is False

    @given(st.integers(min_value=1, max_value=10))
    def test_recovery_always_resets(self, fail_count: int):
        """Any number of failures followed by a pass resets the counter."""
        call_num = [0]

        def _check(behaviors, now):
            call_num[0] += 1
            if call_num[0] <= fail_count:
                return False, "fail"
            return True, ""

        spec = _make_spec(check=_check, min_violation_ticks=fail_count + 5)
        registry = AgreementRegistry(invariants=(spec,))
        checker = _make_checker(registry=registry)

        for t in range(fail_count + 1):
            checker.check(now=100.0 + t)

        # After recovery, counter is 0 — need min_violation_ticks new failures
        # Reset the check function to fail again
        call_num[0] = 0
        checker.check(now=200.0)  # fail, counter=1
        result = checker.check(now=201.0)  # fail, counter=2
        # Should not have reached threshold yet (threshold = fail_count + 5 ≥ 6)
        assert result.satisfied is True

    @given(st.lists(st.text(min_size=1, max_size=20), min_size=2, max_size=10, unique=True))
    def test_registry_uniqueness(self, names: list[str]):
        """Registry with unique names always succeeds."""
        specs = tuple(_make_spec(name=n) for n in names)
        reg = AgreementRegistry(invariants=specs)
        assert len(reg.invariants) == len(names)

    @given(st.integers(min_value=1, max_value=10))
    def test_advisory_never_affects_agreement_ok(self, ticks: int):
        """ADVISORY violations never set agreement_ok to False."""
        spec = _make_spec(check=_always_fail, severity=Severity.ADVISORY, min_violation_ticks=1)
        registry = AgreementRegistry(invariants=(spec,))
        checker = _make_checker(registry=registry)

        for t in range(ticks):
            checker.check(now=100.0 + t)
            assert checker.agreement_ok.value is True


# ===========================================================================
# LAYER 6: Candidate Invariant Scenarios
# ===========================================================================


class TestCandidateInvariantScenarios:
    def test_emotion_fresh_no_face_violation(self):
        """Invariant #1: emotion fresh but face_count=0 → violation after debounce."""
        registry = build_default_registry()
        wm = 100.0
        behaviors = {
            "emotion_valence": Behavior(0.6, watermark=wm),
            "face_count": Behavior(0, watermark=wm),
            "operator_present": Behavior(False, watermark=wm),
            "presence_score": Behavior("likely_absent", watermark=wm),
            "activity_mode": Behavior("unknown", watermark=wm),
            "vad_confidence": Behavior(0.0, watermark=wm),
        }
        checker = AgreementChecker(registry, behaviors)

        # Run enough ticks to exceed the default min_violation_ticks=3
        for t in range(3):
            checker.check(now=wm + t * 0.5)

        result = checker.check(now=wm + 1.5)
        # face_emotion_entails_presence should fire
        violation_names = [v.invariant_name for v in result.violations]
        assert "face_emotion_entails_presence" in violation_names

    def test_speech_and_absent_violation(self):
        """Invariant #4: activity=away + speaking + definitely_present → violation."""
        registry = build_default_registry()
        wm = 100.0
        behaviors = {
            "activity_mode": Behavior("away", watermark=wm),
            "vad_confidence": Behavior(0.9, watermark=wm),
            "presence_score": Behavior("definitely_present", watermark=wm),
            "operator_present": Behavior(True, watermark=wm),
            "face_count": Behavior(1, watermark=wm),
        }
        checker = AgreementChecker(registry, behaviors)

        for t in range(3):
            checker.check(now=wm + t * 0.5)

        result = checker.check(now=wm + 1.5)
        violation_names = [v.invariant_name for v in result.violations]
        assert "away_presence_exclusion" in violation_names

    def test_coherent_operator_state_no_violations(self):
        """All signals consistent with operator present → no violations."""
        registry = build_default_registry()
        wm = 100.0
        behaviors = {
            "emotion_valence": Behavior(0.5, watermark=wm),
            "emotion_arousal": Behavior(0.4, watermark=wm),
            "face_count": Behavior(1, watermark=wm),
            "operator_present": Behavior(True, watermark=wm),
            "operator_identified": Behavior(True, watermark=wm),
            "presence_score": Behavior("definitely_present", watermark=wm),
            "activity_mode": Behavior("coding", watermark=wm),
            "vad_confidence": Behavior(0.0, watermark=wm),
            "active_window": Behavior(None, watermark=wm),
        }
        checker = AgreementChecker(registry, behaviors)

        for t in range(5):
            result = checker.check(now=wm + t * 0.5)
            assert result.satisfied is True

    def test_coherent_empty_room_no_violations(self):
        """All signals consistent with empty room → no violations."""
        registry = build_default_registry()
        wm = 100.0
        behaviors = {
            "face_count": Behavior(0, watermark=wm),
            "operator_present": Behavior(False, watermark=wm),
            "presence_score": Behavior("likely_absent", watermark=wm),
            "activity_mode": Behavior("idle", watermark=wm),
            "vad_confidence": Behavior(0.0, watermark=wm),
        }
        # Emotion signals absent (stale/missing) — entailment is vacuous
        checker = AgreementChecker(registry, behaviors)

        for t in range(5):
            result = checker.check(now=wm + t * 0.5)
            assert result.satisfied is True

    def test_identity_emotion_coherence_advisory(self):
        """Invariant #8: emotion fresh but operator not identified → advisory violation."""
        registry = build_default_registry()
        wm = 100.0
        behaviors = {
            "emotion_valence": Behavior(0.5, watermark=wm),
            "emotion_arousal": Behavior(0.4, watermark=wm),
            "face_count": Behavior(1, watermark=wm),
            "operator_present": Behavior(True, watermark=wm),
            "operator_identified": Behavior(False, watermark=wm),
            "presence_score": Behavior("likely_present", watermark=wm),
            "activity_mode": Behavior("coding", watermark=wm),
            "vad_confidence": Behavior(0.0, watermark=wm),
        }
        checker = AgreementChecker(registry, behaviors)

        for t in range(4):
            checker.check(now=wm + t * 0.5)

        result = checker.check(now=wm + 2.0)
        violation_names = [v.invariant_name for v in result.violations]
        assert "identity_emotion_coherence" in violation_names
        # Advisory — should not block agreement_ok
        assert checker.agreement_ok.value is True

    def test_identity_presence_agreement_guests_only(self):
        """Faces detected + not identified + absent → acceptable (guests only)."""
        registry = build_default_registry()
        wm = 100.0
        behaviors = {
            "face_count": Behavior(2, watermark=wm),
            "operator_present": Behavior(False, watermark=wm),
            "operator_identified": Behavior(False, watermark=wm),
            "presence_score": Behavior("likely_absent", watermark=wm),
            "activity_mode": Behavior("idle", watermark=wm),
            "vad_confidence": Behavior(0.0, watermark=wm),
        }
        checker = AgreementChecker(registry, behaviors)

        for t in range(5):
            result = checker.check(now=wm + t * 0.5)
            # No presence_sensors_agree violation — guests-only is acceptable
            hard_violations = [v for v in result.violations if v.severity is Severity.HARD]
            assert len(hard_violations) == 0

    def test_transient_incoherence_debounced(self):
        """Brief disagreement (< min_violation_ticks) is not reported."""
        registry = build_default_registry()
        wm = 100.0
        behaviors = {
            "emotion_valence": Behavior(0.6, watermark=wm),
            "face_count": Behavior(0, watermark=wm),
            "operator_present": Behavior(False, watermark=wm),
            "presence_score": Behavior("likely_absent", watermark=wm),
            "activity_mode": Behavior("unknown", watermark=wm),
            "vad_confidence": Behavior(0.0, watermark=wm),
        }
        checker = AgreementChecker(registry, behaviors)

        # 2 ticks < min_violation_ticks=3, then recover
        checker.check(now=wm)
        r = checker.check(now=wm + 0.5)
        assert r.satisfied is True

        # Now fix the state
        behaviors["face_count"].update(1, wm + 1.0)
        behaviors["operator_present"].update(True, wm + 1.0)
        behaviors["presence_score"].update("definitely_present", wm + 1.0)

        for t in range(5):
            result = checker.check(now=wm + 1.0 + t * 0.5)
            assert result.satisfied is True
