# tests/test_context_enrichment.py
"""Tests for shared context enrichment."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from shared.context import ContextAssembler, EnrichmentContext


class TestEnrichmentContext(unittest.TestCase):
    def test_frozen(self):
        ctx = EnrichmentContext(timestamp=time.time())
        with self.assertRaises(AttributeError):
            ctx.timestamp = 0.0

    def test_defaults(self):
        ctx = EnrichmentContext(timestamp=1.0)
        assert ctx.stimmung_stance == "nominal"
        assert ctx.active_goals == []
        assert ctx.health_summary == {}
        assert ctx.pending_nudges == []
        assert ctx.dmn_observations == []
        assert ctx.imagination_fragments == []
        assert ctx.perception_snapshot == {}


class TestContextAssembler(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._stimmung_path = Path(self._tmpdir) / "stimmung" / "state.json"
        self._stimmung_path.parent.mkdir(parents=True, exist_ok=True)
        self._dmn_path = Path(self._tmpdir) / "dmn" / "buffer.txt"
        self._dmn_path.parent.mkdir(parents=True, exist_ok=True)
        self._imagination_path = Path(self._tmpdir) / "imagination" / "current.json"
        self._imagination_path.parent.mkdir(parents=True, exist_ok=True)

    def _write_stimmung(self, stance="nominal"):
        self._stimmung_path.write_text(
            json.dumps(
                {
                    "overall_stance": stance,
                    "health": {"value": 0.1, "trend": "stable", "freshness_s": 0.0},
                    "timestamp": time.time(),
                }
            )
        )

    def _make_assembler(self, **overrides):
        defaults = {
            "stimmung_path": self._stimmung_path,
            "dmn_buffer_path": self._dmn_path,
            "imagination_path": self._imagination_path,
            "goals_fn": lambda: [],
            "health_fn": lambda: {},
            "nudges_fn": lambda: [],
            "perception_fn": lambda: {},
        }
        defaults.update(overrides)
        return ContextAssembler(**defaults)

    def test_assemble_returns_enrichment_context(self):
        self._write_stimmung("cautious")
        asm = self._make_assembler()
        ctx = asm.assemble()
        assert isinstance(ctx, EnrichmentContext)
        assert ctx.stimmung_stance == "cautious"

    def test_assemble_reads_goals(self):
        self._write_stimmung()
        asm = self._make_assembler(goals_fn=lambda: [{"title": "Ship feature"}])
        ctx = asm.assemble()
        assert len(ctx.active_goals) == 1
        assert ctx.active_goals[0]["title"] == "Ship feature"

    def test_assemble_reads_dmn_buffer(self):
        self._write_stimmung()
        self._dmn_path.write_text("Operator is typing actively.")
        asm = self._make_assembler()
        ctx = asm.assemble()
        assert "typing" in ctx.dmn_observations[0]

    def test_assemble_reads_imagination(self):
        self._write_stimmung()
        self._imagination_path.write_text(
            json.dumps(
                {
                    "narrative": "A field of stars",
                    "salience": 0.7,
                }
            )
        )
        asm = self._make_assembler()
        ctx = asm.assemble()
        assert len(ctx.imagination_fragments) == 1

    def test_assemble_caches_with_ttl(self):
        self._write_stimmung("nominal")
        asm = self._make_assembler()
        ctx1 = asm.assemble()
        # Modify stimmung
        self._write_stimmung("degraded")
        ctx2 = asm.assemble()
        # Should return cached (same object)
        assert ctx2 is ctx1
        assert ctx2.stimmung_stance == "nominal"

    def test_cache_expires(self):
        self._write_stimmung("nominal")
        asm = self._make_assembler()
        asm._cache_ttl = 0.0  # expire immediately
        ctx1 = asm.assemble()
        self._write_stimmung("degraded")
        ctx2 = asm.assemble()
        assert ctx2 is not ctx1
        assert ctx2.stimmung_stance == "degraded"

    def test_missing_stimmung_defaults_nominal(self):
        # Don't write stimmung file
        asm = self._make_assembler()
        ctx = asm.assemble()
        assert ctx.stimmung_stance == "nominal"

    def test_missing_dmn_returns_empty(self):
        self._write_stimmung()
        # Don't write DMN buffer
        asm = self._make_assembler()
        ctx = asm.assemble()
        assert ctx.dmn_observations == []

    def test_callable_failure_returns_empty(self):
        self._write_stimmung()

        def bad_goals():
            raise RuntimeError("broken")

        asm = self._make_assembler(goals_fn=bad_goals)
        ctx = asm.assemble()
        assert ctx.active_goals == []

    def test_perception_snapshot(self):
        self._write_stimmung()
        asm = self._make_assembler(
            perception_fn=lambda: {"desk_activity": "typing", "flow_score": 0.8}
        )
        ctx = asm.assemble()
        assert ctx.perception_snapshot["desk_activity"] == "typing"
