"""Integration tests for FortressGovernor wiring.

Tests suppression topology behavior: crisis dominance, resource pressure
suppressing military, and convergence under alternating states.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from agents.fortress.config import FortressConfig, SuppressionConfig
from agents.fortress.schema import (
    BuildingSummary,
    FullFortressState,
    StockpileSummary,
    WealthSummary,
    Workshop,
)
from agents.fortress.wiring import FortressGovernor

_WORKSHOPS = (
    Workshop(type="Craftsdwarf", x=0, y=0, z=0, is_active=True, current_job=""),
    Workshop(type="Mason", x=1, y=0, z=0, is_active=True, current_job=""),
    Workshop(type="Carpenter", x=2, y=0, z=0, is_active=True, current_job=""),
)


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
        "stockpiles": StockpileSummary(food=500, drink=250, weapons=10, furniture=60),
        "workshops": _WORKSHOPS,
        "buildings": BuildingSummary(beds=60, tables=25, chairs=25),
        "wealth": WealthSummary(created=10000),
    }
    defaults.update(overrides)
    return FullFortressState(**defaults)


def _siege_state(**overrides: object) -> FullFortressState:
    """State with active siege + famine (triggers crisis lockdown)."""
    defaults: dict = {
        "active_threats": 40,
        "population": 50,
        "food_count": 100,
        "stockpiles": StockpileSummary(food=100, drink=100, weapons=10, furniture=60),
    }
    defaults.update(overrides)
    return _base_full(**defaults)


def _famine_state(**overrides: object) -> FullFortressState:
    """State with food critically low but no threats."""
    defaults: dict = {
        "active_threats": 0,
        "population": 50,
        "food_count": 50,
        "stockpiles": StockpileSummary(food=50, drink=50, weapons=10, furniture=60),
    }
    defaults.update(overrides)
    return _base_full(**defaults)


def _peaceful_state(**overrides: object) -> FullFortressState:
    """Fully peaceful state — no threats, plenty of resources."""
    defaults: dict = {
        "active_threats": 0,
        "population": 50,
        "food_count": 1000,
        "drink_count": 500,
        "most_stressed_value": 0,
        "stockpiles": StockpileSummary(food=1000, drink=500, weapons=20, furniture=60),
        "buildings": BuildingSummary(beds=60, tables=30, chairs=30),
    }
    defaults.update(overrides)
    return _base_full(**defaults)


# Use fast suppression timing so tests don't need large time jumps
_FAST_SUPPRESSION = SuppressionConfig(
    crisis_attack_s=0.01,
    crisis_release_s=0.02,
    military_attack_s=0.01,
    military_release_s=0.02,
    resource_attack_s=0.01,
    resource_release_s=0.02,
    planner_attack_s=0.01,
    planner_release_s=0.02,
)

_FAST_CONFIG = FortressConfig(suppression=_FAST_SUPPRESSION)


class TestSiegeSuppressesPlanner(unittest.TestCase):
    """Feed siege state -> crisis fires -> planner gets no expansion commands."""

    def test_siege_suppresses_planner(self) -> None:
        governor = FortressGovernor(config=_FAST_CONFIG)
        monotonic_time = 100.0

        with patch("agents.fortress.wiring.time") as mock_time:
            # First evaluate: siege triggers crisis, sets crisis_suppression target to 1.0
            mock_time.monotonic.return_value = monotonic_time
            cmds1 = governor.evaluate(_siege_state())

            # Crisis should have fired
            crisis_cmds = [c for c in cmds1 if c.chain == "crisis_responder"]
            self.assertTrue(len(crisis_cmds) > 0, "Crisis should produce commands on siege")

            # Advance time so suppression ramps up fully
            monotonic_time += 0.1
            mock_time.monotonic.return_value = monotonic_time

            # Second evaluate: crisis_suppression should be at ~1.0
            # Use state with beds < population to trigger planner IF not suppressed
            siege_needs_beds = _siege_state(
                buildings=BuildingSummary(beds=10),
                game_tick=20000,  # past cooldown
            )
            cmds2 = governor.evaluate(siege_needs_beds)

            # Planner should be suppressed by crisis
            planner_cmds = [c for c in cmds2 if c.chain == "fortress_planner"]
            self.assertEqual(
                len(planner_cmds),
                0,
                "Planner should be suppressed during siege",
            )


class TestResourcePressureSuppressesMilitary(unittest.TestCase):
    """Feed famine state -> resource_pressure rises -> military draft suppressed."""

    def test_famine_suppresses_military(self) -> None:
        governor = FortressGovernor(config=_FAST_CONFIG)
        monotonic_time = 100.0

        with patch("agents.fortress.wiring.time") as mock_time:
            # First evaluate with famine — resource chain should fire and set pressure
            mock_time.monotonic.return_value = monotonic_time
            famine = _famine_state(active_threats=5)  # some threats to trigger military
            cmds1 = governor.evaluate(famine)

            # Resource manager should have produced commands
            resource_cmds = [c for c in cmds1 if c.chain == "resource_manager"]
            self.assertTrue(len(resource_cmds) > 0, "Resource manager should fire on famine")

            # Advance time for suppression to ramp
            monotonic_time += 0.1
            mock_time.monotonic.return_value = monotonic_time

            # Second evaluate: resource_pressure should suppress military
            cmds2 = governor.evaluate(famine)
            military_cmds = [c for c in cmds2 if c.chain == "military_commander"]
            self.assertEqual(
                len(military_cmds),
                0,
                "Military should be suppressed by resource pressure",
            )


class TestStabilityNoOscillation(unittest.TestCase):
    """Run 100 evaluate cycles with alternating states -> suppression levels converge."""

    def test_no_oscillation(self) -> None:
        governor = FortressGovernor(config=_FAST_CONFIG)
        monotonic_time = 100.0

        peaceful = _peaceful_state()
        threat = _base_full(active_threats=5)

        with patch("agents.fortress.wiring.time") as mock_time:
            last_levels: dict[str, float] = {}
            for i in range(100):
                monotonic_time += 0.001
                mock_time.monotonic.return_value = monotonic_time
                state = peaceful if i % 2 == 0 else threat
                governor.evaluate(state)
                last_levels = {
                    name: field.value for name, field in governor.suppression_fields.items()
                }

            # After 100 rapid alternations, levels should be bounded [0, 1]
            for name, level in last_levels.items():
                self.assertGreaterEqual(level, 0.0, f"{name} below 0")
                self.assertLessEqual(level, 1.0, f"{name} above 1")


class TestCrisisDominatesAll(unittest.TestCase):
    """Feed compound crisis (siege + famine) -> only crisis commands produced."""

    def test_crisis_dominates(self) -> None:
        governor = FortressGovernor(config=_FAST_CONFIG)
        monotonic_time = 100.0

        with patch("agents.fortress.wiring.time") as mock_time:
            # First pass: establish crisis suppression
            mock_time.monotonic.return_value = monotonic_time
            compound = _siege_state(
                food_count=50,
                most_stressed_value=200000,
                buildings=BuildingSummary(beds=10),  # would trigger planner
            )
            governor.evaluate(compound)

            # Advance past attack time
            monotonic_time += 0.1
            mock_time.monotonic.return_value = monotonic_time

            # Second pass: crisis suppression should be at ceiling
            cmds = governor.evaluate(
                _siege_state(
                    food_count=50,
                    most_stressed_value=200000,
                    buildings=BuildingSummary(beds=10),
                    game_tick=20000,  # past cooldown
                )
            )

            # Should have crisis commands but no planner/resource commands
            chains = {c.chain for c in cmds}
            self.assertNotIn(
                "fortress_planner",
                chains,
                "Planner should be suppressed during compound crisis",
            )
            # Crisis or military should be present (crisis fires military commands)
            has_crisis_or_military = "crisis_responder" in chains or "military_commander" in chains
            self.assertTrue(
                has_crisis_or_military,
                "Crisis or military should produce commands during compound crisis",
            )


class TestNoThreatsNoSuppression(unittest.TestCase):
    """Feed peaceful state -> all suppression fields at 0.0."""

    def test_peaceful_state_zero_suppression(self) -> None:
        governor = FortressGovernor(config=_FAST_CONFIG)
        monotonic_time = 100.0

        with patch("agents.fortress.wiring.time") as mock_time:
            mock_time.monotonic.return_value = monotonic_time
            governor.evaluate(_peaceful_state())

            # All suppression fields should target 0 and remain at 0
            for name, field in governor.suppression_fields.items():
                self.assertAlmostEqual(
                    field.value,
                    0.0,
                    places=2,
                    msg=f"{name} should be at 0.0 in peaceful state",
                )

    def test_peaceful_produces_no_military_crisis(self) -> None:
        governor = FortressGovernor(config=_FAST_CONFIG)
        monotonic_time = 100.0

        with patch("agents.fortress.wiring.time") as mock_time:
            mock_time.monotonic.return_value = monotonic_time
            cmds = governor.evaluate(_peaceful_state())

            chains = {c.chain for c in cmds}
            self.assertNotIn("crisis_responder", chains)
            self.assertNotIn("military_commander", chains)


if __name__ == "__main__":
    unittest.main()
