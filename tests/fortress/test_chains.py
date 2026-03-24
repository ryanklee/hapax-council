"""Tests for all six fortress governance chains."""

from __future__ import annotations

import unittest

from agents.fortress.chains.advisor import AdvisorChain
from agents.fortress.chains.crisis import CrisisResponderChain
from agents.fortress.chains.military import MilitaryCommanderChain
from agents.fortress.chains.planner import FortressPlannerChain
from agents.fortress.chains.resource import ResourceManagerChain
from agents.fortress.chains.storyteller import StorytellerChain
from agents.fortress.config import FortressConfig
from agents.fortress.schema import (
    BuildingSummary,
    FastFortressState,
    FullFortressState,
    MigrantEvent,
    StockpileSummary,
    WealthSummary,
    Workshop,
)


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


def _base_full(**overrides: object) -> FullFortressState:
    """Build a FullFortressState with sensible defaults."""
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
        "stockpiles": StockpileSummary(food=500, drink=250, weapons=10, furniture=10),
        "workshops": (
            Workshop(type="Craftsdwarf", x=0, y=0, z=0, is_active=True, current_job=""),
            Workshop(type="Mason", x=1, y=0, z=0, is_active=True, current_job=""),
            Workshop(type="Carpenter", x=2, y=0, z=0, is_active=True, current_job=""),
        ),
        "buildings": BuildingSummary(beds=50, tables=25, chairs=25),
        "wealth": WealthSummary(created=10000),
    }
    defaults.update(overrides)
    return FullFortressState(**defaults)


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------


class TestPlannerChain(unittest.TestCase):
    """Test FortressPlannerChain vetoes and fallback."""

    def setUp(self) -> None:
        self.chain = FortressPlannerChain()

    def test_population_floor_veto(self) -> None:
        state = _base_full(population=2)
        veto, sel = self.chain.evaluate(state)
        self.assertFalse(veto.allowed)
        self.assertIn("population_floor", veto.denied_by)
        self.assertEqual(sel.action, "no_action")

    def test_population_floor_passes(self) -> None:
        state = _base_full(population=3)
        veto, _ = self.chain.evaluate(state)
        self.assertTrue(veto.allowed)

    def test_needs_bedrooms(self) -> None:
        state = _base_full(
            population=20,
            buildings=BuildingSummary(beds=10),
        )
        veto, sel = self.chain.evaluate(state)
        self.assertTrue(veto.allowed)
        self.assertEqual(sel.action, "expand_bedrooms")

    def test_enough_beds_skips_to_workshops(self) -> None:
        state = _base_full(
            population=50,
            buildings=BuildingSummary(beds=60),
            workshops=(),  # no workshops
        )
        veto, sel = self.chain.evaluate(state)
        self.assertTrue(veto.allowed)
        self.assertEqual(sel.action, "expand_workshops")

    def test_all_satisfied_returns_no_action(self) -> None:
        state = _base_full(
            population=20,
            buildings=BuildingSummary(beds=30),
            stockpiles=StockpileSummary(weapons=10, furniture=30),
            workshops=(
                Workshop(type="A", x=0, y=0, z=0, is_active=True, current_job=""),
                Workshop(type="B", x=1, y=0, z=0, is_active=True, current_job=""),
                Workshop(type="C", x=2, y=0, z=0, is_active=True, current_job=""),
            ),
            wealth=WealthSummary(created=1000),
        )
        veto, sel = self.chain.evaluate(state)
        self.assertTrue(veto.allowed)
        self.assertEqual(sel.action, "no_action")


# ---------------------------------------------------------------------------
# Military
# ---------------------------------------------------------------------------


class TestMilitaryChain(unittest.TestCase):
    """Test MilitaryCommanderChain vetoes and threat response."""

    def setUp(self) -> None:
        self.chain = MilitaryCommanderChain()

    def test_minimum_population_veto_at_9(self) -> None:
        state = _base_full(population=9)
        veto, sel = self.chain.evaluate(state)
        self.assertFalse(veto.allowed)
        self.assertIn("minimum_population", veto.denied_by)

    def test_minimum_population_passes_at_10(self) -> None:
        state = _base_full(population=10)
        veto, _ = self.chain.evaluate(state)
        # May still be denied by food_critical_no_draft, but min pop passes
        self.assertNotIn("minimum_population", veto.denied_by)

    def test_equipment_veto(self) -> None:
        state = _base_full(
            stockpiles=StockpileSummary(weapons=0, food=500, drink=250),
        )
        veto, _ = self.chain.evaluate(state)
        self.assertFalse(veto.allowed)
        self.assertIn("equipment_available", veto.denied_by)

    def test_food_critical_veto(self) -> None:
        state = _base_full(
            population=20,
            stockpiles=StockpileSummary(weapons=5, food=50, drink=100),
        )
        veto, _ = self.chain.evaluate(state)
        self.assertFalse(veto.allowed)
        self.assertIn("food_critical_no_draft", veto.denied_by)

    def test_full_assault_on_large_threat(self) -> None:
        state = _base_full(active_threats=25)
        veto, sel = self.chain.evaluate(state)
        self.assertTrue(veto.allowed)
        self.assertEqual(sel.action, "full_assault")

    def test_defensive_on_small_threat(self) -> None:
        state = _base_full(active_threats=5)
        veto, sel = self.chain.evaluate(state)
        self.assertTrue(veto.allowed)
        self.assertEqual(sel.action, "defensive_position")

    def test_civilian_burrow_small_pop_threat(self) -> None:
        state = _base_full(
            population=15,
            active_threats=5,
            stockpiles=StockpileSummary(weapons=5, food=500, drink=250),
        )
        veto, sel = self.chain.evaluate(state)
        self.assertTrue(veto.allowed)
        self.assertEqual(sel.action, "civilian_burrow")

    def test_no_threats_no_action(self) -> None:
        state = _base_full(active_threats=0)
        veto, sel = self.chain.evaluate(state)
        self.assertTrue(veto.allowed)
        self.assertEqual(sel.action, "no_action")


# ---------------------------------------------------------------------------
# Resource
# ---------------------------------------------------------------------------


class TestResourceChain(unittest.TestCase):
    """Test ResourceManagerChain vetoes and production priority."""

    def setUp(self) -> None:
        self.chain = ResourceManagerChain()

    def test_workshop_veto(self) -> None:
        state = _base_full(workshops=())
        veto, sel = self.chain.evaluate(state)
        self.assertFalse(veto.allowed)
        self.assertIn("workshop_available", veto.denied_by)

    def test_food_production_priority(self) -> None:
        state = _base_full(
            population=50,
            stockpiles=StockpileSummary(food=100, drink=500, weapons=10),
        )
        _, sel = self.chain.evaluate(state)
        self.assertEqual(sel.action, "food_production")

    def test_drink_production_when_food_ok(self) -> None:
        state = _base_full(
            population=50,
            stockpiles=StockpileSummary(food=600, drink=100, weapons=10),
        )
        _, sel = self.chain.evaluate(state)
        self.assertEqual(sel.action, "drink_production")

    def test_equipment_production(self) -> None:
        state = _base_full(
            population=50,
            stockpiles=StockpileSummary(food=600, drink=300, weapons=2),
        )
        _, sel = self.chain.evaluate(state)
        self.assertEqual(sel.action, "equipment_production")

    def test_all_stocked_no_action(self) -> None:
        state = _base_full(
            population=50,
            stockpiles=StockpileSummary(food=600, drink=300, weapons=20),
        )
        _, sel = self.chain.evaluate(state)
        self.assertEqual(sel.action, "no_action")


# ---------------------------------------------------------------------------
# Storyteller
# ---------------------------------------------------------------------------


class TestStorytellerChain(unittest.TestCase):
    """Test StorytellerChain narrative selection."""

    def setUp(self) -> None:
        self.chain = StorytellerChain()

    def test_dramatic_on_threats(self) -> None:
        state = _base_fast(active_threats=5)
        veto, sel = self.chain.evaluate(state)
        self.assertTrue(veto.allowed)
        self.assertEqual(sel.action, "dramatic_narrative")

    def test_factual_on_pending_events(self) -> None:
        event = MigrantEvent(count=7)
        state = _base_fast(pending_events=(event,))
        _, sel = self.chain.evaluate(state)
        self.assertEqual(sel.action, "factual_summary")

    def test_brief_update_default(self) -> None:
        state = _base_fast()
        _, sel = self.chain.evaluate(state)
        self.assertEqual(sel.action, "brief_update")

    def test_threats_take_priority_over_events(self) -> None:
        event = MigrantEvent(count=3)
        state = _base_fast(active_threats=1, pending_events=(event,))
        _, sel = self.chain.evaluate(state)
        self.assertEqual(sel.action, "dramatic_narrative")

    def test_never_vetoed(self) -> None:
        state = _base_fast()
        veto, _ = self.chain.evaluate(state)
        self.assertTrue(veto.allowed)
        self.assertEqual(veto.denied_by, ())


# ---------------------------------------------------------------------------
# Advisor
# ---------------------------------------------------------------------------


class TestAdvisorChain(unittest.TestCase):
    """Test AdvisorChain query routing."""

    def setUp(self) -> None:
        self.chain = AdvisorChain()

    def test_threat_assessment(self) -> None:
        state = _base_full(active_threats=3)
        _, sel = self.chain.evaluate(state)
        self.assertEqual(sel.action, "threat_assessment")

    def test_resource_assessment_low_food(self) -> None:
        state = _base_full(
            population=50,
            stockpiles=StockpileSummary(food=100, weapons=10),
        )
        _, sel = self.chain.evaluate(state)
        self.assertEqual(sel.action, "resource_assessment")

    def test_general_assessment_default(self) -> None:
        state = _base_full()
        _, sel = self.chain.evaluate(state)
        self.assertEqual(sel.action, "general_assessment")

    def test_never_vetoed(self) -> None:
        state = _base_full()
        veto, _ = self.chain.evaluate(state)
        self.assertTrue(veto.allowed)


# ---------------------------------------------------------------------------
# Crisis
# ---------------------------------------------------------------------------


class TestCrisisChain(unittest.TestCase):
    """Test CrisisResponderChain cooldown, famine+siege, stress."""

    def setUp(self) -> None:
        self.config = FortressConfig(recovery_cooldown_ticks=1000)
        self.chain = CrisisResponderChain(config=self.config)

    def test_immediate_lockdown_famine_and_siege(self) -> None:
        state = _base_full(
            active_threats=35,
            population=50,
            stockpiles=StockpileSummary(food=100, weapons=10),
        )
        veto, sel = self.chain.evaluate(state)
        self.assertTrue(veto.allowed)
        self.assertEqual(sel.action, "immediate_lockdown")

    def test_targeted_response_on_threat(self) -> None:
        state = _base_full(active_threats=5)
        _, sel = self.chain.evaluate(state)
        self.assertEqual(sel.action, "targeted_response")

    def test_heightened_alert_extreme_stress(self) -> None:
        state = _base_full(most_stressed_value=200000)
        _, sel = self.chain.evaluate(state)
        self.assertEqual(sel.action, "heightened_alert")

    def test_no_action_calm(self) -> None:
        state = _base_full()
        _, sel = self.chain.evaluate(state)
        self.assertEqual(sel.action, "no_action")

    def test_cooldown_veto(self) -> None:
        # First activation should work
        state1 = _base_full(active_threats=5, game_tick=10000)
        veto1, sel1 = self.chain.evaluate(state1)
        self.assertTrue(veto1.allowed)
        self.assertEqual(sel1.action, "targeted_response")

        # Second activation within cooldown should be vetoed
        state2 = _base_full(active_threats=5, game_tick=10500)
        veto2, sel2 = self.chain.evaluate(state2)
        self.assertFalse(veto2.allowed)
        self.assertIn("not_in_cooldown", veto2.denied_by)
        self.assertEqual(sel2.action, "no_action")

    def test_cooldown_expires(self) -> None:
        # Activate
        state1 = _base_full(active_threats=5, game_tick=10000)
        self.chain.evaluate(state1)

        # After cooldown period
        state2 = _base_full(active_threats=5, game_tick=11001)
        veto, sel = self.chain.evaluate(state2)
        self.assertTrue(veto.allowed)
        self.assertEqual(sel.action, "targeted_response")

    def test_no_action_does_not_trigger_cooldown(self) -> None:
        state1 = _base_full(game_tick=10000)  # no threats, no stress
        _, sel1 = self.chain.evaluate(state1)
        self.assertEqual(sel1.action, "no_action")

        # Should not be in cooldown since no_action doesn't record activation
        state2 = _base_full(active_threats=5, game_tick=10001)
        veto, sel2 = self.chain.evaluate(state2)
        self.assertTrue(veto.allowed)
        self.assertEqual(sel2.action, "targeted_response")


if __name__ == "__main__":
    unittest.main()
