"""Tests for Continuous-Loop Research Cadence §3.2 — director-loop wire-up.

The ``_maybe_override_activity`` hook + module-level persistence helpers
in ``agents.studio_compositor.director_loop``.
"""

from __future__ import annotations

import json
from pathlib import Path


class TestPersistenceHelpers:
    def test_read_missing_returns_zero(self, tmp_path: Path):
        from agents.studio_compositor.director_loop import _read_last_override_at

        assert _read_last_override_at(tmp_path / "absent.json") == 0.0

    def test_read_malformed_json_returns_zero(self, tmp_path: Path):
        from agents.studio_compositor.director_loop import _read_last_override_at

        p = tmp_path / "bad.json"
        p.write_text("{not json", encoding="utf-8")
        assert _read_last_override_at(p) == 0.0

    def test_round_trip(self, tmp_path: Path):
        from agents.studio_compositor.director_loop import (
            _read_last_override_at,
            _write_last_override_at,
        )

        p = tmp_path / "state.json"
        _write_last_override_at(p, 1234.5)

        assert _read_last_override_at(p) == 1234.5
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data == {"last_override_at": 1234.5}

    def test_non_float_value_returns_zero(self, tmp_path: Path):
        from agents.studio_compositor.director_loop import _read_last_override_at

        p = tmp_path / "state.json"
        p.write_text(json.dumps({"last_override_at": "not a number"}), encoding="utf-8")
        assert _read_last_override_at(p) == 0.0

    def test_write_creates_parent_dir(self, tmp_path: Path):
        from agents.studio_compositor.director_loop import _write_last_override_at

        nested = tmp_path / "a" / "b" / "state.json"
        _write_last_override_at(nested, 100.0)
        assert nested.exists()


class TestOverrideMethodIsSafe:
    """The override hook must never crash the director loop."""

    def test_failures_fall_back_to_proposed(self, monkeypatch):
        """A blown-up activity_scoring import still returns the proposed activity."""
        from agents.studio_compositor import director_loop as dl

        # Create a minimal object with just the method dispatched (can't easily
        # instantiate the full DirectorLoop); simulate with a subclass that
        # binds the method to a trivial self.
        class _Stub:
            _maybe_override_activity = dl.DirectorLoop._maybe_override_activity
            _active_objective_activities = dl.DirectorLoop._active_objective_activities

        # Monkeypatch activity_scoring import to raise inside the method.
        import sys

        monkeypatch.setitem(
            sys.modules,
            "agents.chat_monitor.sink",
            type(sys)(name="_broken_sink_stub"),  # empty module, read_latest missing
        )

        result = _Stub._maybe_override_activity(_Stub(), "react")
        # Any error path returns the proposal unchanged.
        assert result == "react"
