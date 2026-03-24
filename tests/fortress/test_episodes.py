"""Tests for FortressEpisode and FortressEpisodeBuilder."""

from __future__ import annotations

import unittest

from agents.fortress.episodes import FortressEpisode, FortressEpisodeBuilder
from agents.fortress.schema import (
    DeathEvent,
    FastFortressState,
    MoodEvent,
    SiegeEvent,
)


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


class TestFortressEpisode(unittest.TestCase):
    """Test FortressEpisode construction and computed properties."""

    def test_population_delta(self) -> None:
        ep = FortressEpisode(population_start=50, population_end=60)
        self.assertEqual(ep.population_delta, 10)

    def test_food_delta(self) -> None:
        ep = FortressEpisode(food_start=500, food_end=400)
        self.assertEqual(ep.food_delta, -100)

    def test_duration_ticks(self) -> None:
        ep = FortressEpisode(game_tick_start=1000, game_tick_end=5000)
        self.assertEqual(ep.duration_ticks, 4000)

    def test_summary_text_without_narrative(self) -> None:
        ep = FortressEpisode(
            fortress_name="Boatmurdered",
            year=3,
            season=1,
            trigger="siege",
            population_start=50,
            population_end=45,
            food_start=500,
            food_end=480,
        )
        text = ep.summary_text()
        self.assertIn("Boatmurdered", text)
        self.assertIn("Year 3", text)
        self.assertIn("siege", text)
        self.assertIn("-5", text)

    def test_summary_text_with_narrative(self) -> None:
        ep = FortressEpisode(
            fortress_name="Boatmurdered",
            year=1,
            season=0,
            trigger="start",
            narrative="The dwarves struck the earth.",
        )
        text = ep.summary_text()
        self.assertIn("The dwarves struck the earth.", text)


class TestFortressEpisodeBuilder(unittest.TestCase):
    """Test episode boundary detection."""

    def test_first_observe_starts_episode(self) -> None:
        builder = FortressEpisodeBuilder(session_id="s1")
        state = _base_fast()
        result = builder.observe(state)
        self.assertIsNone(result)  # no closed episode on first observe

    def test_season_change_triggers_boundary(self) -> None:
        builder = FortressEpisodeBuilder(session_id="s1")
        s1 = _base_fast(season=0, game_tick=10000)
        s2 = _base_fast(season=1, game_tick=20000)
        builder.observe(s1)
        closed = builder.observe(s2)
        self.assertIsNotNone(closed)
        self.assertEqual(closed.trigger, "season_change")
        self.assertEqual(closed.game_tick_start, 10000)
        self.assertEqual(closed.game_tick_end, 20000)

    def test_siege_triggers_boundary(self) -> None:
        builder = FortressEpisodeBuilder(session_id="s1")
        s1 = _base_fast()
        siege_event = SiegeEvent(attacker_civ="goblins", force_size=30)
        s2 = _base_fast(game_tick=15000, pending_events=(siege_event,))
        builder.observe(s1)
        closed = builder.observe(s2)
        self.assertIsNotNone(closed)
        self.assertEqual(closed.trigger, "siege")

    def test_no_boundary_on_same_state(self) -> None:
        builder = FortressEpisodeBuilder(session_id="s1")
        s1 = _base_fast(game_tick=10000)
        s2 = _base_fast(game_tick=10100)
        builder.observe(s1)
        result = builder.observe(s2)
        self.assertIsNone(result)

    def test_flush_closes_partial(self) -> None:
        builder = FortressEpisodeBuilder(session_id="s1")
        builder.observe(_base_fast())
        flushed = builder.flush()
        self.assertIsNotNone(flushed)
        self.assertEqual(flushed.trigger, "flush")

    def test_flush_returns_none_without_state(self) -> None:
        builder = FortressEpisodeBuilder(session_id="s1")
        self.assertIsNone(builder.flush())

    def test_closed_episodes_drain(self) -> None:
        builder = FortressEpisodeBuilder(session_id="s1")
        builder.observe(_base_fast(season=0, game_tick=1000))
        builder.observe(_base_fast(season=1, game_tick=2000))
        builder.observe(_base_fast(season=2, game_tick=3000))

        episodes = builder.closed_episodes
        self.assertEqual(len(episodes), 2)
        # Second call should be empty (drained)
        self.assertEqual(len(builder.closed_episodes), 0)

    def test_death_event_triggers_boundary(self) -> None:
        builder = FortressEpisodeBuilder(session_id="s1")
        builder.observe(_base_fast())
        death = DeathEvent(unit_id=1, unit_name="Urist", cause="drowned")
        closed = builder.observe(_base_fast(game_tick=11000, pending_events=(death,)))
        self.assertIsNotNone(closed)
        self.assertEqual(closed.trigger, "death")

    def test_mood_event_triggers_boundary(self) -> None:
        builder = FortressEpisodeBuilder(session_id="s1")
        builder.observe(_base_fast())
        mood = MoodEvent(unit_id=2, mood_type="fey")
        closed = builder.observe(_base_fast(game_tick=11000, pending_events=(mood,)))
        self.assertIsNotNone(closed)
        self.assertEqual(closed.trigger, "mood")

    def test_population_shift_triggers_boundary(self) -> None:
        builder = FortressEpisodeBuilder(session_id="s1")
        builder.observe(_base_fast(population=50))
        closed = builder.observe(_base_fast(population=56, game_tick=11000))
        self.assertIsNotNone(closed)
        self.assertEqual(closed.trigger, "population_shift")

    def test_events_accumulate_within_episode(self) -> None:
        builder = FortressEpisodeBuilder(session_id="s1")
        builder.observe(_base_fast(game_tick=1000))
        # Same season, no boundary triggers, but has a caravan event
        from agents.fortress.schema import CaravanEvent

        caravan = CaravanEvent(civ="elves", goods_value=500)
        builder.observe(_base_fast(game_tick=1100, pending_events=(caravan,)))
        # Flush to get the episode and check events accumulated
        ep = builder.flush()
        self.assertIsNotNone(ep)
        self.assertEqual(len(ep.events), 1)
