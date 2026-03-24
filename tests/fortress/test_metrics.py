"""Tests for fortress metrics and session tracking."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.fortress.metrics import ChainMetrics, FortressSessionTracker
from agents.fortress.schema import FastFortressState


def _base_fast(**overrides: object) -> FastFortressState:
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


class TestChainMetrics(unittest.TestCase):
    def test_defaults(self) -> None:
        m = ChainMetrics()
        self.assertEqual(m.commands_issued, 0)
        self.assertEqual(m.commands_vetoed, 0)
        self.assertEqual(m.llm_calls, 0)


class TestFortressSessionTracker(unittest.TestCase):
    """Test session tracking lifecycle."""

    def test_start_initializes(self) -> None:
        tracker = FortressSessionTracker()
        state = _base_fast(fortress_name="Daggercaves", population=30)
        tracker.start(state)
        self.assertEqual(tracker.fortress_name, "Daggercaves")
        self.assertEqual(tracker.peak_population, 30)
        self.assertEqual(tracker.start_tick, 10000)
        self.assertIn("fortress_planner", tracker.chain_metrics)
        self.assertIn("advisor", tracker.chain_metrics)

    def test_update_tracks_population(self) -> None:
        tracker = FortressSessionTracker()
        tracker.start(_base_fast(population=50, game_tick=1000))
        tracker.update(_base_fast(population=70, game_tick=2000))
        self.assertEqual(tracker.peak_population, 70)
        self.assertEqual(tracker.final_population, 70)
        self.assertEqual(tracker.end_tick, 2000)

    def test_peak_population_preserved_on_decline(self) -> None:
        tracker = FortressSessionTracker()
        tracker.start(_base_fast(population=50, game_tick=1000))
        tracker.update(_base_fast(population=80, game_tick=2000))
        tracker.update(_base_fast(population=60, game_tick=3000))
        self.assertEqual(tracker.peak_population, 80)
        self.assertEqual(tracker.final_population, 60)

    def test_record_command(self) -> None:
        tracker = FortressSessionTracker()
        tracker.start(_base_fast())
        tracker.record_command("fortress_planner")
        tracker.record_command("fortress_planner")
        tracker.record_command("fortress_planner", vetoed=True)
        self.assertEqual(tracker.chain_metrics["fortress_planner"].commands_issued, 2)
        self.assertEqual(tracker.chain_metrics["fortress_planner"].commands_vetoed, 1)
        self.assertEqual(tracker.total_commands, 2)

    def test_record_command_unknown_chain(self) -> None:
        tracker = FortressSessionTracker()
        tracker.record_command("new_chain")
        self.assertEqual(tracker.chain_metrics["new_chain"].commands_issued, 1)

    def test_record_event(self) -> None:
        tracker = FortressSessionTracker()
        tracker.record_event("siege")
        tracker.record_event("siege")
        tracker.record_event("migrant")
        self.assertEqual(tracker.events_summary["siege"], 2)
        self.assertEqual(tracker.events_summary["migrant"], 1)

    def test_survival_ticks(self) -> None:
        tracker = FortressSessionTracker()
        tracker.start_tick = 1000
        tracker.end_tick = 13000
        self.assertEqual(tracker.survival_ticks, 12000)

    def test_survival_days(self) -> None:
        tracker = FortressSessionTracker()
        tracker.start_tick = 0
        tracker.end_tick = 12000
        self.assertEqual(tracker.survival_days, 10)  # 12000 // 1200

    def test_survival_years(self) -> None:
        tracker = FortressSessionTracker()
        tracker.start_tick = 0
        tracker.end_tick = 403200
        self.assertAlmostEqual(tracker.survival_years, 1.0)

    def test_is_fortress_dead_zero_pop(self) -> None:
        tracker = FortressSessionTracker()
        state = _base_fast(population=0)
        self.assertTrue(tracker.is_fortress_dead(state))

    def test_is_fortress_dead_no_food_no_drink(self) -> None:
        tracker = FortressSessionTracker()
        state = _base_fast(population=10, food_count=0, drink_count=0)
        self.assertTrue(tracker.is_fortress_dead(state))

    def test_is_fortress_alive_with_food(self) -> None:
        tracker = FortressSessionTracker()
        state = _base_fast(population=10, food_count=100, drink_count=0)
        self.assertFalse(tracker.is_fortress_dead(state))

    def test_is_fortress_alive_with_drink(self) -> None:
        tracker = FortressSessionTracker()
        state = _base_fast(population=10, food_count=0, drink_count=50)
        self.assertFalse(tracker.is_fortress_dead(state))

    def test_finalize_writes_valid_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / "sessions.jsonl"
            with patch("agents.fortress.metrics.SESSIONS_PATH", tmp_path):
                tracker = FortressSessionTracker(session_id="test123")
                tracker.start(_base_fast(game_tick=1000))
                tracker.update(_base_fast(game_tick=13000, population=60))
                tracker.record_command("fortress_planner")
                record = tracker.finalize(cause="starvation")

                self.assertEqual(record["session_id"], "test123")
                self.assertEqual(record["cause_of_death"], "starvation")
                self.assertEqual(record["survival_days"], 10)
                self.assertEqual(record["peak_population"], 60)

                lines = tmp_path.read_text().strip().split("\n")
                self.assertEqual(len(lines), 1)
                stored = json.loads(lines[0])
                self.assertEqual(stored["session_id"], "test123")
