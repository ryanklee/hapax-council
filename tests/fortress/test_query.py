"""Tests for fortress query dispatch."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.fortress.query import (
    build_query_context,
    load_chronicle,
    load_sessions,
)


class TestLoadChronicle(unittest.TestCase):
    def test_returns_empty_for_missing_file(self) -> None:
        with patch("agents.fortress.query.CHRONICLE_PATH", Path("/nonexistent/file.jsonl")):
            self.assertEqual(load_chronicle(), [])

    def test_loads_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "chronicle.jsonl"
            entries = [
                {"year": 1, "season": 0, "trigger": "start", "narrative": "Founded."},
                {"year": 1, "season": 1, "trigger": "season_change", "narrative": "Summer."},
            ]
            p.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
            with patch("agents.fortress.query.CHRONICLE_PATH", p):
                result = load_chronicle()
                self.assertEqual(len(result), 2)
                self.assertEqual(result[0]["trigger"], "start")
                self.assertEqual(result[1]["trigger"], "season_change")

    def test_respects_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "chronicle.jsonl"
            entries = [{"year": i, "trigger": f"t{i}"} for i in range(10)]
            p.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
            with patch("agents.fortress.query.CHRONICLE_PATH", p):
                result = load_chronicle(limit=3)
                self.assertEqual(len(result), 3)
                # Should be the last 3
                self.assertEqual(result[0]["year"], 7)

    def test_skips_malformed_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "chronicle.jsonl"
            p.write_text('{"valid": true}\nnot json\n{"also": "valid"}\n')
            with patch("agents.fortress.query.CHRONICLE_PATH", p):
                result = load_chronicle()
                self.assertEqual(len(result), 2)


class TestLoadSessions(unittest.TestCase):
    def test_returns_empty_for_missing_file(self) -> None:
        with patch("agents.fortress.query.SESSIONS_PATH", Path("/nonexistent/file.jsonl")):
            self.assertEqual(load_sessions(), [])

    def test_loads_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sessions.jsonl"
            entries = [
                {"fortress_name": "A", "survival_days": 100, "cause_of_death": "siege"},
                {"fortress_name": "B", "survival_days": 200, "cause_of_death": "starvation"},
            ]
            p.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
            with patch("agents.fortress.query.SESSIONS_PATH", p):
                result = load_sessions()
                self.assertEqual(len(result), 2)
                self.assertEqual(result[0]["fortress_name"], "A")


class TestBuildQueryContext(unittest.TestCase):
    def test_includes_query(self) -> None:
        ctx = build_query_context("why did Urist die?", chronicle=[], sessions=[])
        self.assertIn("why did Urist die?", ctx)

    def test_includes_chronicle_entries(self) -> None:
        chronicle = [
            {"year": 1, "season": 0, "narrative": "The fortress was founded."},
            {"year": 1, "season": 1, "narrative": "Summer arrived."},
        ]
        ctx = build_query_context("what happened?", chronicle=chronicle, sessions=[])
        self.assertIn("The fortress was founded.", ctx)
        self.assertIn("Summer arrived.", ctx)
        self.assertIn("Recent chronicle entries:", ctx)

    def test_includes_session_history(self) -> None:
        sessions = [
            {"fortress_name": "Boatmurdered", "survival_days": 365, "cause_of_death": "tantrum"},
        ]
        ctx = build_query_context("how long?", chronicle=[], sessions=sessions)
        self.assertIn("Boatmurdered", ctx)
        self.assertIn("365", ctx)
        self.assertIn("tantrum", ctx)
        self.assertIn("Historical sessions:", ctx)

    def test_empty_data_produces_minimal_context(self) -> None:
        ctx = build_query_context("test", chronicle=[], sessions=[])
        self.assertIn("Operator query: test", ctx)
        self.assertNotIn("Recent chronicle", ctx)
        self.assertNotIn("Historical sessions", ctx)

    def test_chronicle_capped_at_10(self) -> None:
        chronicle = [{"year": i, "season": 0, "narrative": f"Entry {i}"} for i in range(20)]
        ctx = build_query_context("test", chronicle=chronicle, sessions=[])
        # Should only include the last 10
        self.assertIn("Entry 19", ctx)
        self.assertIn("Entry 10", ctx)
        self.assertNotIn("Entry 9", ctx)

    def test_sessions_capped_at_3(self) -> None:
        sessions = [
            {"fortress_name": f"Fort{i}", "survival_days": i * 10, "cause_of_death": "unknown"}
            for i in range(10)
        ]
        ctx = build_query_context("test", chronicle=[], sessions=sessions)
        self.assertIn("Fort9", ctx)
        self.assertIn("Fort7", ctx)
        self.assertNotIn("Fort6", ctx)
