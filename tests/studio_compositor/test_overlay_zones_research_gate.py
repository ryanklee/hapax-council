"""Tests for the LRR Phase 8 item 12 research-zone activity gate.

The ``active_when_activities`` field on a zone configuration gates the
zone's content cycling on whether any active objective's
``activities_that_advance`` list intersects with the configured set. The
gate is re-evaluated every few seconds so activating or closing an
objective takes visible effect without restarting the compositor.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


class TestReadActiveObjectiveActivities:
    def test_missing_dir_returns_empty(self, tmp_path: Path):
        from agents.studio_compositor.overlay_zones import _read_active_objective_activities

        assert _read_active_objective_activities(tmp_path / "nope") == frozenset()

    def test_reads_active_objectives(self, tmp_path: Path):
        from agents.studio_compositor.overlay_zones import _read_active_objective_activities

        (tmp_path / "a.md").write_text(
            "---\n"
            "id: claim-5\n"
            "status: active\n"
            "activities_that_advance: [study, react]\n"
            "---\n\nbody\n",
            encoding="utf-8",
        )
        (tmp_path / "b.md").write_text(
            "---\nid: claim-7\nstatus: closed\nactivities_that_advance: [chat]\n---\n",
            encoding="utf-8",
        )
        (tmp_path / "c.md").write_text(
            "---\nid: claim-9\nstatus: active\nactivities_that_advance: [vinyl]\n---\n",
            encoding="utf-8",
        )
        activities = _read_active_objective_activities(tmp_path)
        assert activities == frozenset({"study", "react", "vinyl"})

    def test_ignores_malformed_files(self, tmp_path: Path):
        from agents.studio_compositor.overlay_zones import _read_active_objective_activities

        (tmp_path / "not-frontmatter.md").write_text("no frontmatter here\n", encoding="utf-8")
        (tmp_path / "bad-yaml.md").write_text(
            "---\nstatus: active\n  activities_that_advance: [unclosed\n---\n",
            encoding="utf-8",
        )
        (tmp_path / "good.md").write_text(
            "---\nstatus: active\nactivities_that_advance: [study]\n---\n",
            encoding="utf-8",
        )
        assert _read_active_objective_activities(tmp_path) == frozenset({"study"})


class TestZoneGate:
    def _make_zone(self, **overrides):
        from agents.studio_compositor.overlay_zones import OverlayZone

        config = {
            "id": "research",
            "folder": "/tmp/does-not-matter",
            "x": 0,
            "y": 0,
            "max_width": 500,
            "active_when_activities": ("study",),
        }
        config.update(overrides)
        return OverlayZone(config)

    def test_default_always_on(self, monkeypatch: pytest.MonkeyPatch):
        from agents.studio_compositor.overlay_zones import OverlayZone

        z = OverlayZone({"id": "m", "folder": "/tmp", "x": 0, "y": 0})
        assert z._gate_open is True
        # tick without active_when never calls the reader.
        called = {"n": 0}
        monkeypatch.setattr(
            "agents.studio_compositor.overlay_zones._read_active_objective_activities",
            lambda *a, **kw: called.update(n=called["n"] + 1) or frozenset(),
        )
        z.tick()
        assert called["n"] == 0

    def test_gate_closed_when_no_active_objectives(self, monkeypatch: pytest.MonkeyPatch):
        z = self._make_zone()
        monkeypatch.setattr(
            "agents.studio_compositor.overlay_zones._read_active_objective_activities",
            lambda *a, **kw: frozenset(),
        )
        z.tick()
        assert z._gate_open is False
        assert z._pango_markup == ""
        assert z._cached_surface is None

    def test_gate_closed_when_activity_mismatch(self, monkeypatch: pytest.MonkeyPatch):
        z = self._make_zone()
        monkeypatch.setattr(
            "agents.studio_compositor.overlay_zones._read_active_objective_activities",
            lambda *a, **kw: frozenset({"vinyl", "chat"}),
        )
        z.tick()
        assert z._gate_open is False

    def test_gate_open_when_activity_matches(self, monkeypatch: pytest.MonkeyPatch):
        z = self._make_zone()
        monkeypatch.setattr(
            "agents.studio_compositor.overlay_zones._read_active_objective_activities",
            lambda *a, **kw: frozenset({"study", "react"}),
        )
        z.tick()
        assert z._gate_open is True

    def test_gate_ttl_caches_reader_call(self, monkeypatch: pytest.MonkeyPatch):
        """Rapid ticks should not pound the filesystem — reader is throttled."""
        z = self._make_zone()
        calls = {"n": 0}

        def fake(*_a, **_kw):
            calls["n"] += 1
            return frozenset({"study"})

        monkeypatch.setattr(
            "agents.studio_compositor.overlay_zones._read_active_objective_activities", fake
        )

        z.tick()
        z.tick()
        z.tick()
        assert calls["n"] == 1  # subsequent ticks within TTL reuse cached verdict

    def test_gate_reopens_after_activity_appears(self, monkeypatch: pytest.MonkeyPatch):
        """After the cache TTL elapses the reader is consulted again."""
        z = self._make_zone()
        monkeypatch.setattr(
            "agents.studio_compositor.overlay_zones._ACTIVITY_CACHE_TTL_S", 0.0, raising=False
        )
        verdicts = [frozenset(), frozenset({"study"})]
        monkeypatch.setattr(
            "agents.studio_compositor.overlay_zones._read_active_objective_activities",
            lambda *a, **kw: verdicts.pop(0) if verdicts else frozenset({"study"}),
        )

        z.tick()
        assert z._gate_open is False
        z.tick()
        assert z._gate_open is True


class TestShippedZoneConfig:
    def test_research_zone_registered_and_gated(self):
        from agents.studio_compositor.overlay_zones import ZONES

        by_id = {z["id"]: z for z in ZONES}
        assert "research" in by_id
        assert by_id["research"].get("active_when_activities") == ("study",)
        assert "research/" in by_id["research"]["folder"]

    def test_other_zones_still_always_on(self):
        from agents.studio_compositor.overlay_zones import ZONES

        by_id = {z["id"]: z for z in ZONES}
        assert "main" in by_id
        assert "active_when_activities" not in by_id["main"]
        assert "lyrics" in by_id
        assert "active_when_activities" not in by_id["lyrics"]
