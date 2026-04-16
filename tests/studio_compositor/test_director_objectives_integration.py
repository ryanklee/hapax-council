"""Tests for _render_active_objectives_block — LRR Phase 8 §3.3 integration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml


def _write_obj(directory: Path, obj_id: str, **kwargs) -> None:
    defaults = {
        "objective_id": obj_id,
        "title": f"Title for {obj_id}",
        "status": "active",
        "priority": "normal",
        "opened_at": datetime(2026, 4, 16, tzinfo=UTC).isoformat(),
        "linked_claims": [],
        "linked_conditions": [],
        "success_criteria": ["criterion"],
        "activities_that_advance": ["study"],
    }
    defaults.update(kwargs)
    body = "---\n" + yaml.safe_dump(defaults, sort_keys=False) + "---\n"
    (directory / f"{obj_id}.md").write_text(body)


class TestRenderActiveObjectives:
    def test_empty_dir_returns_empty(self, tmp_path, monkeypatch):
        from agents.studio_compositor import director_loop

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        assert director_loop._render_active_objectives_block() == ""

    def test_single_active_objective_renders(self, tmp_path, monkeypatch):
        from agents.studio_compositor import director_loop

        objectives_dir = tmp_path / "Documents" / "Personal" / "30-areas" / "hapax-objectives"
        objectives_dir.mkdir(parents=True)
        _write_obj(objectives_dir, "obj-001", title="Close LRR epic", priority="high")

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        block = director_loop._render_active_objectives_block()
        assert "Research Objectives" in block
        assert "Close LRR epic" in block
        assert "priority: high" in block
        assert "advance via: study" in block

    def test_closed_objectives_excluded(self, tmp_path, monkeypatch):
        from agents.studio_compositor import director_loop

        objectives_dir = tmp_path / "Documents" / "Personal" / "30-areas" / "hapax-objectives"
        objectives_dir.mkdir(parents=True)
        _write_obj(objectives_dir, "obj-001", title="Active one")
        _write_obj(
            objectives_dir,
            "obj-002",
            title="Closed one",
            status="closed",
            closed_at=datetime(2026, 4, 15, tzinfo=UTC).isoformat(),
        )

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        block = director_loop._render_active_objectives_block()
        assert "Active one" in block
        assert "Closed one" not in block

    def test_sorts_by_priority_then_recency(self, tmp_path, monkeypatch):
        from agents.studio_compositor import director_loop

        objectives_dir = tmp_path / "Documents" / "Personal" / "30-areas" / "hapax-objectives"
        objectives_dir.mkdir(parents=True)
        _write_obj(objectives_dir, "obj-001", title="low-prio", priority="low")
        _write_obj(objectives_dir, "obj-002", title="high-prio", priority="high")
        _write_obj(objectives_dir, "obj-003", title="normal-prio", priority="normal")

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        block = director_loop._render_active_objectives_block()
        lines = block.splitlines()
        # First bullet is high-prio, second is normal-prio, third is low-prio
        obj_lines = [ln for ln in lines if ln.startswith("- **")]
        assert "high-prio" in obj_lines[0]
        assert "normal-prio" in obj_lines[1]
        assert "low-prio" in obj_lines[2]

    def test_caps_at_top_3(self, tmp_path, monkeypatch):
        from agents.studio_compositor import director_loop

        objectives_dir = tmp_path / "Documents" / "Personal" / "30-areas" / "hapax-objectives"
        objectives_dir.mkdir(parents=True)
        for i in range(1, 6):
            _write_obj(objectives_dir, f"obj-00{i}", title=f"title-{i}")

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        block = director_loop._render_active_objectives_block()
        obj_lines = [ln for ln in block.splitlines() if ln.startswith("- **")]
        assert len(obj_lines) == 3

    def test_malformed_objective_skipped(self, tmp_path, monkeypatch):
        from agents.studio_compositor import director_loop

        objectives_dir = tmp_path / "Documents" / "Personal" / "30-areas" / "hapax-objectives"
        objectives_dir.mkdir(parents=True)
        (objectives_dir / "obj-001.md").write_text("---\nnot valid frontmatter\n")
        _write_obj(objectives_dir, "obj-002", title="Valid")

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        block = director_loop._render_active_objectives_block()
        assert "Valid" in block
