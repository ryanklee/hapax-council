"""Tests for agents/programme_manager/abort_predicates.py — Phase 10 / B3 Critical #3.

Verifies the 5 named predicates' decision boundaries + the
conservative fail-open posture (missing fields → False, never
abort on sensor uncertainty).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from agents.programme_manager.abort_predicates import (
    DEFAULT_ABORT_PREDICATES,
    DEFAULT_OPERATOR_AWAY_S,
    DEFAULT_PRESSURE_DURATION_S,
    DEFAULT_PRESSURE_THRESHOLD,
    consent_contract_expired,
    get_default_abort_predicates,
    impingement_pressure_above_0_8_for_3min,
    operator_left_room_for_10min,
    operator_voice_contradicts_programme_intent,
    vinyl_side_a_finished,
)


@dataclass
class _StubContent:
    narrative_beat: str | None = None


@dataclass
class _StubProgramme:
    role: str = "deep_focus"
    content: _StubContent | None = None


# ── operator_left_room_for_10min ──────────────────────────────────────


class TestOperatorLeftRoom:
    def test_present_returns_false(self) -> None:
        snap = {"ir_present": True, "ir_absent_since_s": 999.0}
        assert operator_left_room_for_10min(_StubProgramme(), snap) is False

    def test_absent_under_threshold_returns_false(self) -> None:
        snap = {"ir_present": False, "ir_absent_since_s": 300.0}
        assert operator_left_room_for_10min(_StubProgramme(), snap) is False

    def test_absent_over_threshold_returns_true(self) -> None:
        snap = {"ir_present": False, "ir_absent_since_s": 700.0}
        assert operator_left_room_for_10min(_StubProgramme(), snap) is True

    def test_absent_at_exact_threshold_returns_true(self) -> None:
        snap = {"ir_present": False, "ir_absent_since_s": DEFAULT_OPERATOR_AWAY_S}
        assert operator_left_room_for_10min(_StubProgramme(), snap) is True

    def test_missing_snapshot_returns_false(self) -> None:
        assert operator_left_room_for_10min(_StubProgramme(), None) is False

    def test_missing_field_returns_false(self) -> None:
        assert operator_left_room_for_10min(_StubProgramme(), {}) is False

    def test_non_numeric_field_returns_false(self) -> None:
        snap = {"ir_present": False, "ir_absent_since_s": "forever"}
        assert operator_left_room_for_10min(_StubProgramme(), snap) is False


# ── impingement_pressure_above_0_8_for_3min ───────────────────────────


class TestPressurePredicate:
    def test_pressure_below_threshold_returns_false(self) -> None:
        snap = {"vla_pressure": 0.5, "vla_pressure_above_threshold_since_s": 999.0}
        assert impingement_pressure_above_0_8_for_3min(_StubProgramme(), snap) is False

    def test_pressure_above_threshold_short_duration_returns_false(self) -> None:
        snap = {"vla_pressure": 0.95, "vla_pressure_above_threshold_since_s": 60.0}
        assert impingement_pressure_above_0_8_for_3min(_StubProgramme(), snap) is False

    def test_pressure_sustained_returns_true(self) -> None:
        snap = {
            "vla_pressure": 0.85,
            "vla_pressure_above_threshold_since_s": 200.0,
        }
        assert impingement_pressure_above_0_8_for_3min(_StubProgramme(), snap) is True

    def test_threshold_constants_match_audit(self) -> None:
        assert DEFAULT_PRESSURE_THRESHOLD == 0.8
        assert DEFAULT_PRESSURE_DURATION_S == 180.0

    def test_missing_fields_returns_false(self) -> None:
        assert impingement_pressure_above_0_8_for_3min(_StubProgramme(), {}) is False


# ── consent_contract_expired ──────────────────────────────────────────


class TestConsentContractExpired:
    def test_no_contracts_returns_false(self) -> None:
        snap = {"now_epoch": 1000.0}
        assert consent_contract_expired(_StubProgramme(role="deep_focus"), snap) is False

    def test_role_not_in_contracts_returns_false(self) -> None:
        snap = {"consent_contracts": {"other": 100.0}, "now_epoch": 1000.0}
        assert consent_contract_expired(_StubProgramme(role="deep_focus"), snap) is False

    def test_contract_still_valid_returns_false(self) -> None:
        snap = {"consent_contracts": {"deep_focus": 2000.0}, "now_epoch": 1000.0}
        assert consent_contract_expired(_StubProgramme(role="deep_focus"), snap) is False

    def test_contract_expired_returns_true(self) -> None:
        snap = {"consent_contracts": {"deep_focus": 500.0}, "now_epoch": 1000.0}
        assert consent_contract_expired(_StubProgramme(role="deep_focus"), snap) is True

    def test_missing_now_returns_false(self) -> None:
        """Without a clock anchor, conservative posture: don't abort."""
        snap = {"consent_contracts": {"deep_focus": 100.0}}
        assert consent_contract_expired(_StubProgramme(role="deep_focus"), snap) is False


# ── vinyl_side_a_finished ─────────────────────────────────────────────


class TestVinylSideAFinished:
    def test_side_a_tail_in_returns_true(self) -> None:
        snap = {"vinyl_side": "A", "vinyl_tail_in": True}
        assert vinyl_side_a_finished(_StubProgramme(), snap) is True

    def test_side_a_not_tail_in_returns_false(self) -> None:
        snap = {"vinyl_side": "A", "vinyl_tail_in": False}
        assert vinyl_side_a_finished(_StubProgramme(), snap) is False

    def test_side_b_returns_false(self) -> None:
        """Side B finishing is a different programme decision."""
        snap = {"vinyl_side": "B", "vinyl_tail_in": True}
        assert vinyl_side_a_finished(_StubProgramme(), snap) is False

    def test_missing_side_returns_false(self) -> None:
        snap = {"vinyl_tail_in": True}
        assert vinyl_side_a_finished(_StubProgramme(), snap) is False


# ── operator_voice_contradicts_programme_intent ───────────────────────


class TestVoiceContradiction:
    def test_no_narrative_beat_returns_false(self) -> None:
        """No frame to contradict → never fires."""
        prog = _StubProgramme(content=_StubContent(narrative_beat=None))
        snap = {"contradiction_score": 0.99}
        assert operator_voice_contradicts_programme_intent(prog, snap) is False

    def test_low_score_returns_false(self) -> None:
        prog = _StubProgramme(content=_StubContent(narrative_beat="reflective"))
        snap = {"contradiction_score": 0.4}
        assert operator_voice_contradicts_programme_intent(prog, snap) is False

    def test_high_score_returns_true(self) -> None:
        prog = _StubProgramme(content=_StubContent(narrative_beat="reflective"))
        snap = {"contradiction_score": 0.85}
        assert operator_voice_contradicts_programme_intent(prog, snap) is True

    def test_at_exact_threshold_returns_true(self) -> None:
        prog = _StubProgramme(content=_StubContent(narrative_beat="reflective"))
        snap = {"contradiction_score": 0.7}
        assert operator_voice_contradicts_programme_intent(prog, snap) is True

    def test_missing_score_returns_false(self) -> None:
        prog = _StubProgramme(content=_StubContent(narrative_beat="reflective"))
        assert operator_voice_contradicts_programme_intent(prog, {}) is False


# ── Registry shape ────────────────────────────────────────────────────


class TestRegistryShape:
    def test_all_five_named_predicates_present(self) -> None:
        """The audit pinned 5 named predicates; the registry MUST surface
        every one. Renaming is a compatibility break."""
        expected = {
            "operator_left_room_for_10min",
            "impingement_pressure_above_0.8_for_3min",
            "consent_contract_expired",
            "vinyl_side_a_finished",
            "operator_voice_contradicts_programme_intent",
        }
        assert set(DEFAULT_ABORT_PREDICATES.keys()) == expected

    def test_all_predicates_callable(self) -> None:
        for name, fn in DEFAULT_ABORT_PREDICATES.items():
            assert callable(fn), f"predicate {name!r} not callable"

    def test_get_default_returns_mutable_copy(self) -> None:
        """The module-level registry must NOT be mutated by callers."""
        a = get_default_abort_predicates()
        a["custom"] = lambda p, s: True
        b = get_default_abort_predicates()
        assert "custom" not in b
        assert "custom" not in DEFAULT_ABORT_PREDICATES

    def test_every_predicate_returns_false_on_empty_snapshot(self) -> None:
        """Conservative fail-open posture: empty snapshot → never abort.
        A regressed predicate that defaults to True would silently abort
        every programme on the first tick."""
        for name, fn in DEFAULT_ABORT_PREDICATES.items():
            assert fn(_StubProgramme(), {}) is False, (
                f"predicate {name!r} fired on empty snapshot — fail-open posture broken"
            )

    def test_every_predicate_returns_false_on_none_snapshot(self) -> None:
        for name, fn in DEFAULT_ABORT_PREDICATES.items():
            assert fn(_StubProgramme(), None) is False, (
                f"predicate {name!r} fired on None snapshot — defensive read broken"
            )


# ── Wire-in compatibility (AbortEvaluator round-trip) ────────────────


class TestEvaluatorRoundTrip:
    """The whole point of this module is to be hand-able to
    AbortEvaluator(predicates=...). Pin the integration shape so a
    future evaluator-API change can't silently disconnect this."""

    def test_evaluator_accepts_default_registry(self) -> None:
        from agents.programme_manager.abort_evaluator import AbortEvaluator

        evaluator = AbortEvaluator(predicates=get_default_abort_predicates())
        names = evaluator.registered_names()
        assert "operator_left_room_for_10min" in names
        assert "vinyl_side_a_finished" in names
        # Sanity: the evaluator surfaces all 5 names back.
        assert len(names) == 5

    def test_evaluator_fires_when_predicate_true(self) -> None:
        """End-to-end: register the real predicate, set the snapshot
        field that triggers it, verify the evaluator calls it."""
        from dataclasses import dataclass

        from agents.programme_manager.abort_evaluator import AbortEvaluator

        @dataclass
        class _SuccessStub:
            abort_predicates: list[str]

        @dataclass
        class _ProgStub:
            programme_id: str
            success: _SuccessStub
            content: _StubContent | None = None
            role: str = "deep_focus"

        evaluator = AbortEvaluator(predicates=get_default_abort_predicates())
        prog = _ProgStub(
            programme_id="prog-x",
            success=_SuccessStub(abort_predicates=["operator_left_room_for_10min"]),
        )
        snap = {"ir_present": False, "ir_absent_since_s": 700.0}
        decision = evaluator.evaluate(prog, perceptual_snapshot=snap)
        assert decision is not None, "evaluator did not fire on triggering snapshot"
        assert decision.predicate_name == "operator_left_room_for_10min"


# ── Module-level wiring sanity ────────────────────────────────────────


@pytest.mark.parametrize("predicate_name", list(DEFAULT_ABORT_PREDICATES.keys()))
def test_predicate_named_export_matches_registry(predicate_name: str) -> None:
    """Every registry entry's name should follow the plan's vocabulary
    (lowercase, snake_case with optional dot-separated thresholds).
    A name typo here desyncs from ProgrammeSuccessCriteria.abort_predicates
    strings."""
    # snake_case + optional dot for the "0.8" threshold form
    allowed = set("abcdefghijklmnopqrstuvwxyz_0123456789.")
    assert set(predicate_name) <= allowed, (
        f"predicate name {predicate_name!r} contains unexpected chars"
    )
