"""Tests for agents.programme_manager.abort_evaluator — Phase 10.

Verifies:
  - Empty registry / unregistered predicate names → no abort
  - Registered predicate true → AbortDecision returned
  - First-true-wins over multiple registered predicates
  - Predicate exception → treated as not-fired (no abort)
  - Veto impingement within window cancels pending abort
  - Veto impingement OUTSIDE window is a no-op (abort stays)
  - Wrong intent_family on impingement → no veto
  - commit_abort during veto window → None
  - commit_abort after veto window → returns the AbortDecision + clears state
  - Pending abort blocks further evaluate() calls (FSM single-in-flight)
  - GROUNDING-EXPANSION: predicates are EVALUATED by registered callables;
    no hardcoded "at t+Xs, abort" exists in the source
"""

from __future__ import annotations

from pathlib import Path

from agents.programme_manager.abort_evaluator import (
    DEFAULT_VETO_WINDOW_S,
    VETO_INTENT_FAMILY,
    AbortDecision,
    AbortEvaluator,
)
from shared.impingement import Impingement, ImpingementType
from shared.programme import (
    Programme,
    ProgrammeRole,
    ProgrammeSuccessCriteria,
)


def _programme(
    *,
    abort_predicates: list[str] | None = None,
) -> Programme:
    return Programme(
        programme_id="prog-test-001",
        role=ProgrammeRole.LISTENING,
        planned_duration_s=300.0,
        success=ProgrammeSuccessCriteria(
            abort_predicates=abort_predicates or [],
        ),
        parent_show_id="show-test",
    )


def _imp(*, family: str | None = None, source: str = "test") -> Impingement:
    return Impingement(
        timestamp=0.0,
        source=source,
        type=ImpingementType.PATTERN_MATCH,
        strength=1.0,
        content={"narrative": "test"},
        intent_family=family,
    )


class _Clock:
    """Manual clock for deterministic veto-window tests."""

    def __init__(self, t0: float = 0.0) -> None:
        self.t = t0

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


# ── Empty / unregistered ────────────────────────────────────────────────


class TestEmptyRegistry:
    def test_no_predicates_no_abort(self) -> None:
        evaluator = AbortEvaluator()
        prog = _programme(abort_predicates=["operator_left_room_for_10min"])
        assert evaluator.evaluate(prog) is None

    def test_unregistered_predicate_skipped(self) -> None:
        evaluator = AbortEvaluator(predicates={"known": lambda p, s: True})
        prog = _programme(abort_predicates=["unknown_one", "unknown_two"])
        assert evaluator.evaluate(prog) is None

    def test_no_abort_predicates_listed_no_abort(self) -> None:
        evaluator = AbortEvaluator(predicates={"any": lambda p, s: True})
        prog = _programme(abort_predicates=[])
        assert evaluator.evaluate(prog) is None


# ── Predicate firing ────────────────────────────────────────────────────


class TestPredicateFiring:
    def test_registered_true_predicate_fires_abort(self) -> None:
        evaluator = AbortEvaluator(predicates={"vinyl_done": lambda p, s: True})
        prog = _programme(abort_predicates=["vinyl_done"])
        decision = evaluator.evaluate(prog)
        assert decision is not None
        assert isinstance(decision, AbortDecision)
        assert decision.predicate_name == "vinyl_done"

    def test_first_true_predicate_wins(self) -> None:
        evaluator = AbortEvaluator(
            predicates={
                "first": lambda p, s: True,
                "second": lambda p, s: True,
            }
        )
        prog = _programme(abort_predicates=["first", "second"])
        decision = evaluator.evaluate(prog)
        assert decision is not None
        assert decision.predicate_name == "first"

    def test_false_predicates_skip_to_next(self) -> None:
        evaluator = AbortEvaluator(
            predicates={
                "false_one": lambda p, s: False,
                "false_two": lambda p, s: False,
                "true_one": lambda p, s: True,
            }
        )
        prog = _programme(abort_predicates=["false_one", "false_two", "true_one"])
        decision = evaluator.evaluate(prog)
        assert decision is not None
        assert decision.predicate_name == "true_one"

    def test_predicate_raising_treated_as_not_fired(self) -> None:
        def boom(p: Programme, s: dict) -> bool:
            raise RuntimeError("predicate broken")

        evaluator = AbortEvaluator(predicates={"boom": boom})
        prog = _programme(abort_predicates=["boom"])
        assert evaluator.evaluate(prog) is None

    def test_perceptual_snapshot_passed_to_predicate(self) -> None:
        captured: list[dict] = []

        def snapshot_capturing(p: Programme, s: dict) -> bool:
            captured.append(s)
            return False

        evaluator = AbortEvaluator(predicates={"capture": snapshot_capturing})
        prog = _programme(abort_predicates=["capture"])
        evaluator.evaluate(prog, {"ir_presence": 0.0, "vla_pressure": 0.95})
        assert captured == [{"ir_presence": 0.0, "vla_pressure": 0.95}]


# ── Veto window ─────────────────────────────────────────────────────────


class TestVetoWindow:
    def test_default_veto_window_is_five_seconds(self) -> None:
        assert DEFAULT_VETO_WINDOW_S == 5.0

    def test_decision_carries_veto_deadline(self) -> None:
        clock = _Clock(t0=100.0)
        evaluator = AbortEvaluator(
            predicates={"x": lambda p, s: True},
            veto_window_s=5.0,
            now_fn=clock,
        )
        prog = _programme(abort_predicates=["x"])
        decision = evaluator.evaluate(prog)
        assert decision is not None
        assert decision.triggered_at == 100.0
        assert decision.veto_deadline_at == 105.0

    def test_veto_within_window_cancels_pending(self) -> None:
        clock = _Clock(t0=100.0)
        evaluator = AbortEvaluator(
            predicates={"x": lambda p, s: True},
            now_fn=clock,
        )
        prog = _programme(abort_predicates=["x"])
        evaluator.evaluate(prog)
        clock.advance(2.0)  # 2s into the 5s window
        veto = _imp(family=VETO_INTENT_FAMILY)
        assert evaluator.handle_veto_impingement(veto) is True
        assert evaluator.pending_abort is None

    def test_veto_outside_window_is_no_op(self) -> None:
        clock = _Clock(t0=100.0)
        evaluator = AbortEvaluator(
            predicates={"x": lambda p, s: True},
            now_fn=clock,
        )
        prog = _programme(abort_predicates=["x"])
        evaluator.evaluate(prog)
        clock.advance(10.0)  # past the 5s window
        veto = _imp(family=VETO_INTENT_FAMILY)
        assert evaluator.handle_veto_impingement(veto) is False
        assert evaluator.pending_abort is not None  # still pending

    def test_wrong_intent_family_does_not_veto(self) -> None:
        evaluator = AbortEvaluator(predicates={"x": lambda p, s: True})
        prog = _programme(abort_predicates=["x"])
        evaluator.evaluate(prog)
        wrong = _imp(family="not.the.veto.family")
        assert evaluator.handle_veto_impingement(wrong) is False
        assert evaluator.pending_abort is not None

    def test_veto_with_no_pending_abort_is_no_op(self) -> None:
        evaluator = AbortEvaluator()
        veto = _imp(family=VETO_INTENT_FAMILY)
        assert evaluator.handle_veto_impingement(veto) is False


# ── Commit FSM ─────────────────────────────────────────────────────────


class TestCommitAbort:
    def test_commit_during_window_returns_none(self) -> None:
        clock = _Clock(t0=100.0)
        evaluator = AbortEvaluator(
            predicates={"x": lambda p, s: True},
            now_fn=clock,
        )
        prog = _programme(abort_predicates=["x"])
        evaluator.evaluate(prog)
        clock.advance(2.0)  # still within window
        assert evaluator.commit_abort() is None
        assert evaluator.pending_abort is not None  # still pending

    def test_commit_after_window_returns_decision_and_clears(self) -> None:
        clock = _Clock(t0=100.0)
        evaluator = AbortEvaluator(
            predicates={"x": lambda p, s: True},
            now_fn=clock,
        )
        prog = _programme(abort_predicates=["x"])
        evaluator.evaluate(prog)
        clock.advance(10.0)  # past the window
        committed = evaluator.commit_abort()
        assert committed is not None
        assert committed.predicate_name == "x"
        assert evaluator.pending_abort is None

    def test_commit_with_no_pending_returns_none(self) -> None:
        evaluator = AbortEvaluator()
        assert evaluator.commit_abort() is None


# ── FSM single-in-flight ───────────────────────────────────────────────


class TestSingleInFlight:
    def test_pending_abort_blocks_further_evaluation(self) -> None:
        evaluator = AbortEvaluator(predicates={"x": lambda p, s: True})
        prog = _programme(abort_predicates=["x"])
        first = evaluator.evaluate(prog)
        assert first is not None
        # Second call sees pending abort and returns None.
        second = evaluator.evaluate(prog)
        assert second is None

    def test_after_veto_evaluation_can_fire_again(self) -> None:
        clock = _Clock(t0=100.0)
        evaluator = AbortEvaluator(
            predicates={"x": lambda p, s: True},
            now_fn=clock,
        )
        prog = _programme(abort_predicates=["x"])
        evaluator.evaluate(prog)
        clock.advance(2.0)
        evaluator.handle_veto_impingement(_imp(family=VETO_INTENT_FAMILY))
        # State cleared; new evaluation can fire again.
        again = evaluator.evaluate(prog)
        assert again is not None


# ── Runtime registration ───────────────────────────────────────────────


class TestRegister:
    def test_register_adds_predicate(self) -> None:
        evaluator = AbortEvaluator()
        assert evaluator.registered_names() == ()
        evaluator.register("new_one", lambda p, s: True)
        assert "new_one" in evaluator.registered_names()

    def test_register_replaces_existing(self) -> None:
        evaluator = AbortEvaluator(predicates={"x": lambda p, s: False})
        evaluator.register("x", lambda p, s: True)
        prog = _programme(abort_predicates=["x"])
        decision = evaluator.evaluate(prog)
        assert decision is not None  # replaced predicate now fires


# ── Grounding-expansion: no hardcoded abort thresholds ─────────────────


class TestGroundingExpansion:
    """Pin: every abort decision flows through registered predicates.

    A future regression that hardcodes an abort condition (e.g. "abort
    after 10 minutes always") would bypass the registry. Negative-
    existence test on the source.
    """

    def test_source_has_no_hardcoded_time_thresholds(self) -> None:
        from agents.programme_manager import abort_evaluator as mod

        source = Path(mod.__file__).read_text()
        # Any of these patterns would indicate hardcoded abort logic:
        forbidden = [
            "elapsed_s >",
            "elapsed >",
            "time.time() -",
            "now - active.actual_started_at",
        ]
        for token in forbidden:
            assert token not in source, (
                f"abort_evaluator.py contains hardcoded threshold {token!r} — "
                "every abort decision MUST flow through a registered predicate"
            )
