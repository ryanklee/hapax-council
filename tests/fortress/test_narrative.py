"""Tests for fortress narrative generation."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.fortress.episodes import FortressEpisode
from agents.fortress.narrative import (
    build_narrative_prompt,
    format_narrative_fallback,
    write_chronicle_entry,
)
from agents.fortress.schema import FastFortressState, SiegeEvent


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


def _episode(**overrides: object) -> FortressEpisode:
    defaults: dict = {
        "session_id": "s1",
        "fortress_name": "Boatmurdered",
        "game_tick_start": 10000,
        "game_tick_end": 20000,
        "season": 0,
        "year": 1,
        "trigger": "season_change",
        "population_start": 50,
        "population_end": 55,
        "food_start": 500,
        "food_end": 450,
    }
    defaults.update(overrides)
    return FortressEpisode(**defaults)


class TestBuildNarrativePrompt(unittest.TestCase):
    """Test prompt construction for LLM narrative generation."""

    def test_contains_fortress_name(self) -> None:
        ep = _episode(fortress_name="Daggercaves")
        state = _base_fast(fortress_name="Daggercaves")
        prompt = build_narrative_prompt(ep, state)
        self.assertIn("Daggercaves", prompt)

    def test_contains_season_name(self) -> None:
        ep = _episode(season=1)
        state = _base_fast()
        prompt = build_narrative_prompt(ep, state)
        self.assertIn("Mid Summer", prompt)

    def test_contains_trigger(self) -> None:
        ep = _episode(trigger="siege")
        state = _base_fast()
        prompt = build_narrative_prompt(ep, state)
        self.assertIn("siege", prompt)

    def test_contains_population_delta(self) -> None:
        ep = _episode(population_start=50, population_end=55)
        state = _base_fast()
        prompt = build_narrative_prompt(ep, state)
        self.assertIn("+5", prompt)

    def test_includes_events(self) -> None:
        siege = SiegeEvent(attacker_civ="goblins", force_size=30)
        ep = _episode(events=[siege])
        state = _base_fast()
        prompt = build_narrative_prompt(ep, state)
        self.assertIn("goblins", prompt)


class TestFormatNarrativeFallback(unittest.TestCase):
    """Test fallback narrative generation for each trigger type."""

    def test_season_change(self) -> None:
        ep = _episode(trigger="season_change", season=0, year=3)
        text = format_narrative_fallback(ep)
        self.assertIn("Spring", text)
        self.assertIn("Year 3", text)
        self.assertTrue(len(text) > 0)

    def test_siege(self) -> None:
        ep = _episode(trigger="siege")
        text = format_narrative_fallback(ep)
        self.assertIn("siege", text.lower())

    def test_migrant(self) -> None:
        ep = _episode(trigger="migrant", population_start=50, population_end=57)
        text = format_narrative_fallback(ep)
        self.assertIn("7", text)

    def test_death(self) -> None:
        ep = _episode(trigger="death")
        text = format_narrative_fallback(ep)
        self.assertIn("perished", text)

    def test_mood(self) -> None:
        ep = _episode(trigger="mood")
        text = format_narrative_fallback(ep)
        self.assertIn("mood", text)

    def test_start(self) -> None:
        ep = _episode(trigger="start")
        text = format_narrative_fallback(ep)
        self.assertIn("founded", text)

    def test_flush(self) -> None:
        ep = _episode(trigger="flush")
        text = format_narrative_fallback(ep)
        self.assertIn("pauses", text)

    def test_population_shift(self) -> None:
        ep = _episode(trigger="population_shift", population_start=50, population_end=56)
        text = format_narrative_fallback(ep)
        self.assertIn("+6", text)

    def test_unknown_trigger(self) -> None:
        ep = _episode(trigger="earthquake")
        text = format_narrative_fallback(ep)
        self.assertIn("earthquake", text)

    def test_no_food_delta_omits_food(self) -> None:
        ep = _episode(trigger="start", food_start=500, food_end=500)
        text = format_narrative_fallback(ep)
        self.assertNotIn("Food stores", text)


class TestWriteChronicleEntry(unittest.TestCase):
    """Test JSONL chronicle output."""

    def test_writes_valid_jsonl(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / "chronicle.jsonl"
            with patch("agents.fortress.narrative.CHRONICLE_PATH", tmp_path):
                ep = _episode(
                    narrative="The dwarves struck the earth.",
                    trigger="start",
                )
                write_chronicle_entry(ep)

                lines = tmp_path.read_text().strip().split("\n")
                self.assertEqual(len(lines), 1)
                entry = json.loads(lines[0])
                self.assertEqual(entry["fortress_name"], "Boatmurdered")
                self.assertEqual(entry["trigger"], "start")
                self.assertEqual(entry["narrative"], "The dwarves struck the earth.")
                self.assertEqual(entry["population_delta"], 5)

    def test_appends_multiple_entries(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / "chronicle.jsonl"
            with patch("agents.fortress.narrative.CHRONICLE_PATH", tmp_path):
                write_chronicle_entry(_episode(trigger="start"))
                write_chronicle_entry(_episode(trigger="siege"))

                lines = tmp_path.read_text().strip().split("\n")
                self.assertEqual(len(lines), 2)
                self.assertEqual(json.loads(lines[0])["trigger"], "start")
                self.assertEqual(json.loads(lines[1])["trigger"], "siege")
