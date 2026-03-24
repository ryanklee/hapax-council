"""Tests for CompoundGoal, GoalTracker, and GoalPlanner."""

from __future__ import annotations

import unittest

from agents.fortress.goals import (
    CompoundGoal,
    GoalPlanner,
    GoalState,
    GoalTracker,
    SubGoal,
)
from agents.fortress.schema import FastFortressState


def _base_fast(**overrides: object) -> FastFortressState:
    """Build a FastFortressState with sensible defaults."""
    defaults: dict = {
        "timestamp": 1.0,
        "game_tick": 10000,
        "year": 1,
        "season": 0,
        "month": 0,
        "day": 0,
        "fortress_name": "Boatmurdered",
        "paused": False,
        "population": 50,
        "food_count": 500,
        "drink_count": 250,
        "active_threats": 0,
        "job_queue_length": 10,
        "idle_dwarf_count": 5,
        "most_stressed_value": 0,
        "pending_events": (),
    }
    defaults.update(overrides)
    return FastFortressState(**defaults)


# ---------------------------------------------------------------------------
# SubGoal / CompoundGoal validation
# ---------------------------------------------------------------------------


class TestCompoundGoalValidation(unittest.TestCase):
    """Test DAG validation: referential integrity and cycle detection."""

    def test_valid_linear_chain(self) -> None:
        goal = CompoundGoal(
            id="test",
            description="linear",
            context_selector=lambda _: ("a", "b", "c"),
            subgoals=(
                SubGoal(id="a", description="first", chain="x"),
                SubGoal(id="b", description="second", chain="x", preconditions=("a",)),
                SubGoal(id="c", description="third", chain="x", preconditions=("b",)),
            ),
        )
        goal.validate()  # should not raise

    def test_valid_diamond_dag(self) -> None:
        goal = CompoundGoal(
            id="test",
            description="diamond",
            context_selector=lambda _: ("a", "b", "c", "d"),
            subgoals=(
                SubGoal(id="a", description="root", chain="x"),
                SubGoal(id="b", description="left", chain="x", preconditions=("a",)),
                SubGoal(id="c", description="right", chain="x", preconditions=("a",)),
                SubGoal(id="d", description="join", chain="x", preconditions=("b", "c")),
            ),
        )
        goal.validate()  # should not raise

    def test_unknown_precondition_raises(self) -> None:
        goal = CompoundGoal(
            id="test",
            description="broken ref",
            context_selector=lambda _: ("a",),
            subgoals=(
                SubGoal(
                    id="a",
                    description="ref missing",
                    chain="x",
                    preconditions=("nonexistent",),
                ),
            ),
        )
        with self.assertRaises(ValueError, msg="unknown precondition"):
            goal.validate()

    def test_self_cycle_raises(self) -> None:
        goal = CompoundGoal(
            id="test",
            description="self-ref",
            context_selector=lambda _: ("a",),
            subgoals=(SubGoal(id="a", description="self", chain="x", preconditions=("a",)),),
        )
        with self.assertRaises(ValueError, msg="Cycle"):
            goal.validate()

    def test_two_node_cycle_raises(self) -> None:
        goal = CompoundGoal(
            id="test",
            description="mutual",
            context_selector=lambda _: ("a", "b"),
            subgoals=(
                SubGoal(id="a", description="a", chain="x", preconditions=("b",)),
                SubGoal(id="b", description="b", chain="x", preconditions=("a",)),
            ),
        )
        with self.assertRaises(ValueError, msg="Cycle"):
            goal.validate()

    def test_three_node_cycle_raises(self) -> None:
        goal = CompoundGoal(
            id="test",
            description="triangle",
            context_selector=lambda _: ("a", "b", "c"),
            subgoals=(
                SubGoal(id="a", description="a", chain="x", preconditions=("c",)),
                SubGoal(id="b", description="b", chain="x", preconditions=("a",)),
                SubGoal(id="c", description="c", chain="x", preconditions=("b",)),
            ),
        )
        with self.assertRaises(ValueError, msg="Cycle"):
            goal.validate()

    def test_no_subgoals_validates(self) -> None:
        goal = CompoundGoal(
            id="empty",
            description="empty",
            context_selector=lambda _: (),
            subgoals=(),
        )
        goal.validate()  # should not raise


# ---------------------------------------------------------------------------
# GoalTracker
# ---------------------------------------------------------------------------


class TestGoalTracker(unittest.TestCase):
    """Test GoalTracker state transitions."""

    def setUp(self) -> None:
        self.tracker = GoalTracker()
        self.goal = CompoundGoal(
            id="g1",
            description="test goal",
            context_selector=lambda _: ("s1", "s2"),
            subgoals=(
                SubGoal(
                    id="s1",
                    description="sub1",
                    chain="x",
                    check=lambda s: s.food_count > 100,
                ),
                SubGoal(
                    id="s2",
                    description="sub2",
                    chain="x",
                    check=lambda s: s.drink_count > 100,
                ),
            ),
        )

    def test_initial_state_is_pending(self) -> None:
        self.assertEqual(self.tracker.goal_state("g1"), GoalState.PENDING)
        self.assertEqual(self.tracker.subgoal_state("g1", "s1"), GoalState.PENDING)

    def test_activate_sets_active(self) -> None:
        self.tracker.activate(self.goal, tick=1000)
        self.assertEqual(self.tracker.goal_state("g1"), GoalState.ACTIVE)
        self.assertEqual(self.tracker.subgoal_state("g1", "s1"), GoalState.PENDING)
        self.assertEqual(self.tracker.subgoal_state("g1", "s2"), GoalState.PENDING)

    def test_mark_subgoal(self) -> None:
        self.tracker.activate(self.goal, tick=1000)
        self.tracker.mark_subgoal("g1", "s1", GoalState.COMPLETED)
        self.assertEqual(self.tracker.subgoal_state("g1", "s1"), GoalState.COMPLETED)
        self.assertEqual(self.tracker.subgoal_state("g1", "s2"), GoalState.PENDING)

    def test_check_completion_all_satisfied(self) -> None:
        self.tracker.activate(self.goal, tick=1000)
        state = _base_fast(food_count=200, drink_count=200)
        self.assertTrue(self.tracker.check_completion(self.goal, state))
        self.assertEqual(self.tracker.goal_state("g1"), GoalState.COMPLETED)

    def test_check_completion_partial(self) -> None:
        self.tracker.activate(self.goal, tick=1000)
        state = _base_fast(food_count=200, drink_count=50)
        self.assertFalse(self.tracker.check_completion(self.goal, state))
        self.assertEqual(self.tracker.goal_state("g1"), GoalState.ACTIVE)

    def test_check_timeouts(self) -> None:
        self.tracker.activate(self.goal, tick=1000)
        self.tracker.mark_subgoal("g1", "s1", GoalState.ACTIVE)
        # Within timeout
        timed_out = self.tracker.check_timeouts(self.goal, current_tick=5000)
        self.assertEqual(timed_out, [])
        # Past timeout (default 12000 ticks)
        timed_out = self.tracker.check_timeouts(self.goal, current_tick=14000)
        self.assertEqual(timed_out, ["s1"])
        self.assertEqual(self.tracker.subgoal_state("g1", "s1"), GoalState.BLOCKED)

    def test_timeout_ignores_non_active_subgoals(self) -> None:
        self.tracker.activate(self.goal, tick=1000)
        # s1 stays PENDING, s2 is COMPLETED
        self.tracker.mark_subgoal("g1", "s2", GoalState.COMPLETED)
        timed_out = self.tracker.check_timeouts(self.goal, current_tick=99999)
        self.assertEqual(timed_out, [])


# ---------------------------------------------------------------------------
# GoalPlanner
# ---------------------------------------------------------------------------


class TestGoalPlanner(unittest.TestCase):
    """Test GoalPlanner evaluation and dispatch logic."""

    def _make_goal(
        self,
        goal_id: str = "g1",
        priority: int = 50,
        subgoals: tuple[SubGoal, ...] | None = None,
        context_selector: object = None,
    ) -> CompoundGoal:
        return CompoundGoal(
            id=goal_id,
            description=f"test goal {goal_id}",
            priority=priority,
            context_selector=context_selector or (lambda _: ("s1",)),
            subgoals=subgoals
            or (
                SubGoal(
                    id="s1",
                    description="sub1",
                    chain="x",
                    check=lambda s: s.food_count > 9999,
                ),
            ),
        )

    def test_no_active_goals_returns_empty(self) -> None:
        planner = GoalPlanner(goals=[self._make_goal()])
        state = _base_fast()
        result = planner.evaluate(state)
        self.assertEqual(result, [])

    def test_activated_goal_dispatches_subgoals(self) -> None:
        planner = GoalPlanner(goals=[self._make_goal()])
        planner.activate_goal("g1", tick=1000)
        state = _base_fast(food_count=100)
        result = planner.evaluate(state)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "s1")

    def test_satisfied_subgoal_not_dispatched(self) -> None:
        planner = GoalPlanner(goals=[self._make_goal()])
        planner.activate_goal("g1", tick=1000)
        state = _base_fast(food_count=99999)  # satisfies check
        result = planner.evaluate(state)
        self.assertEqual(result, [])

    def test_preconditions_block_dispatch(self) -> None:
        goal = CompoundGoal(
            id="g1",
            description="precond test",
            priority=50,
            context_selector=lambda _: ("s1", "s2"),
            subgoals=(
                SubGoal(id="s1", description="first", chain="x", check=lambda _: False),
                SubGoal(
                    id="s2",
                    description="second",
                    chain="x",
                    preconditions=("s1",),
                    check=lambda _: False,
                ),
            ),
        )
        planner = GoalPlanner(goals=[goal])
        planner.activate_goal("g1", tick=1000)
        state = _base_fast()
        result = planner.evaluate(state)
        # Only s1 should be dispatched (s2 blocked by precondition)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "s1")

    def test_preconditions_met_allows_dispatch(self) -> None:
        goal = CompoundGoal(
            id="g1",
            description="precond met",
            priority=50,
            context_selector=lambda _: ("s1", "s2"),
            subgoals=(
                SubGoal(id="s1", description="first", chain="x", check=lambda _: False),
                SubGoal(
                    id="s2",
                    description="second",
                    chain="x",
                    preconditions=("s1",),
                    check=lambda _: False,
                ),
            ),
        )
        planner = GoalPlanner(goals=[goal])
        planner.activate_goal("g1", tick=1000)

        state = _base_fast()
        # First evaluate dispatches s1
        planner.evaluate(state)
        # Mark s1 as completed
        planner.tracker.mark_subgoal("g1", "s1", GoalState.COMPLETED)
        # Second evaluate should dispatch s2
        result = planner.evaluate(state)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "s2")

    def test_priority_ordering(self) -> None:
        low = self._make_goal(goal_id="low", priority=10)
        high = self._make_goal(
            goal_id="high",
            priority=90,
            subgoals=(
                SubGoal(
                    id="s1",
                    description="high sub",
                    chain="x",
                    check=lambda _: False,
                ),
            ),
            context_selector=lambda _: ("s1",),
        )
        planner = GoalPlanner(goals=[low, high])
        planner.activate_goal("low", tick=1000)
        planner.activate_goal("high", tick=1000)
        state = _base_fast(food_count=100)
        result = planner.evaluate(state)
        # High-priority goal's subgoal should come first
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].id, "s1")  # from "high"

    def test_completed_goal_not_dispatched_again(self) -> None:
        # Goal with a check that's already satisfied
        goal = CompoundGoal(
            id="g1",
            description="already done",
            priority=50,
            context_selector=lambda _: ("s1",),
            subgoals=(
                SubGoal(
                    id="s1",
                    description="done",
                    chain="x",
                    check=lambda s: s.food_count > 100,
                ),
            ),
        )
        planner = GoalPlanner(goals=[goal])
        planner.activate_goal("g1", tick=1000)
        state = _base_fast(food_count=500)
        # First evaluate marks completion
        result = planner.evaluate(state)
        self.assertEqual(result, [])
        self.assertEqual(planner.tracker.goal_state("g1"), GoalState.COMPLETED)
        # Second evaluate also returns empty
        result2 = planner.evaluate(state)
        self.assertEqual(result2, [])

    def test_blocked_subgoals_skipped(self) -> None:
        goal = CompoundGoal(
            id="g1",
            description="blocked test",
            priority=50,
            context_selector=lambda _: ("s1", "s2"),
            subgoals=(
                SubGoal(id="s1", description="blocked", chain="x", check=lambda _: False),
                SubGoal(id="s2", description="ok", chain="x", check=lambda _: False),
            ),
        )
        planner = GoalPlanner(goals=[goal])
        planner.activate_goal("g1", tick=1000)
        planner.tracker.mark_subgoal("g1", "s1", GoalState.BLOCKED)
        state = _base_fast()
        result = planner.evaluate(state)
        # Only s2 dispatched, s1 is blocked
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "s2")

    def test_evaluate_is_deterministic(self) -> None:
        """Multiple evaluations with same state produce same order."""
        goals = [self._make_goal(goal_id=f"g{i}", priority=50 + i) for i in range(5)]
        state = _base_fast(food_count=100)

        results: list[list[str]] = []
        for _ in range(3):
            planner = GoalPlanner(goals=list(goals))
            for g in goals:
                planner.activate_goal(g.id, tick=1000)
            result = planner.evaluate(state)
            results.append([sg.id for sg in result])

        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])

    def test_context_selector_filters_subgoals(self) -> None:
        """Only context-selected subgoals are dispatched."""
        goal = CompoundGoal(
            id="g1",
            description="selective",
            priority=50,
            context_selector=lambda _: ("s2",),  # only s2
            subgoals=(
                SubGoal(id="s1", description="not selected", chain="x", check=lambda _: False),
                SubGoal(id="s2", description="selected", chain="x", check=lambda _: False),
            ),
        )
        planner = GoalPlanner(goals=[goal])
        planner.activate_goal("g1", tick=1000)
        state = _base_fast()
        result = planner.evaluate(state)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "s2")

    def test_validation_on_init_rejects_cycles(self) -> None:
        bad_goal = CompoundGoal(
            id="bad",
            description="cyclic",
            priority=50,
            context_selector=lambda _: ("a", "b"),
            subgoals=(
                SubGoal(id="a", description="a", chain="x", preconditions=("b",)),
                SubGoal(id="b", description="b", chain="x", preconditions=("a",)),
            ),
        )
        with self.assertRaises(ValueError):
            GoalPlanner(goals=[bad_goal])


if __name__ == "__main__":
    unittest.main()
