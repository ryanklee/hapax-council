"""Tests for scripts/hapax-objectives.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parent.parent.parent / "scripts" / "hapax-objectives.py"


@pytest.fixture
def ho_module():
    """Import scripts/hapax-objectives.py under a module name ok for Python."""
    spec = importlib.util.spec_from_file_location("hapax_objectives", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hapax_objectives"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def workdir(tmp_path):
    objectives = tmp_path / "objectives"
    events = tmp_path / "state" / "events.jsonl"
    return objectives, events


def _run(ho_module, argv):
    return ho_module.main(argv)


class TestOpen:
    def test_open_allocates_id_and_writes_file(self, ho_module, workdir, capsys):
        objectives, events = workdir
        rc = _run(
            ho_module,
            [
                "--dir",
                str(objectives),
                "--events-file",
                str(events),
                "open",
                "Close LRR epic",
                "--priority",
                "high",
                "--activity",
                "study",
                "--activity",
                "observe",
                "--success",
                "All phases have handoffs",
            ],
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert out.startswith("obj-001\t")
        assert (objectives / "obj-001.md").exists()
        event_lines = events.read_text().strip().splitlines()
        assert len(event_lines) == 1
        event = json.loads(event_lines[0])
        assert event["kind"] == "open"
        assert event["objective_id"] == "obj-001"

    def test_missing_activity_is_error(self, ho_module, workdir):
        objectives, events = workdir
        rc = _run(
            ho_module,
            [
                "--dir",
                str(objectives),
                "--events-file",
                str(events),
                "open",
                "x",
                "--success",
                "y",
            ],
        )
        assert rc == 2

    def test_missing_success_is_error(self, ho_module, workdir):
        objectives, events = workdir
        rc = _run(
            ho_module,
            [
                "--dir",
                str(objectives),
                "--events-file",
                str(events),
                "open",
                "x",
                "--activity",
                "study",
            ],
        )
        assert rc == 2

    def test_sequential_opens_allocate_increasing_ids(self, ho_module, workdir, capsys):
        objectives, events = workdir
        for i in range(3):
            _run(
                ho_module,
                [
                    "--dir",
                    str(objectives),
                    "--events-file",
                    str(events),
                    "open",
                    f"title-{i}",
                    "--activity",
                    "study",
                    "--success",
                    "ok",
                ],
            )
        ids = sorted(p.stem for p in objectives.glob("*.md"))
        assert ids == ["obj-001", "obj-002", "obj-003"]


class TestList:
    def _seed(self, ho_module, workdir, extra_args_list):
        objectives, events = workdir
        for extra in extra_args_list:
            _run(
                ho_module,
                [
                    "--dir",
                    str(objectives),
                    "--events-file",
                    str(events),
                    "open",
                    extra["title"],
                    "--priority",
                    extra.get("priority", "normal"),
                    "--activity",
                    "study",
                    "--success",
                    "x",
                ],
            )
        return objectives, events

    def test_list_all(self, ho_module, workdir, capsys):
        objectives, events = self._seed(
            ho_module,
            workdir,
            [{"title": "a"}, {"title": "b"}],
        )
        capsys.readouterr()  # reset
        _run(
            ho_module,
            ["--dir", str(objectives), "--events-file", str(events), "list"],
        )
        lines = capsys.readouterr().out.strip().splitlines()
        assert len(lines) == 2

    def test_list_status_filter(self, ho_module, workdir, capsys):
        objectives, events = self._seed(ho_module, workdir, [{"title": "a"}, {"title": "b"}])
        _run(
            ho_module,
            ["--dir", str(objectives), "--events-file", str(events), "close", "obj-001"],
        )
        capsys.readouterr()  # reset
        _run(
            ho_module,
            [
                "--dir",
                str(objectives),
                "--events-file",
                str(events),
                "list",
                "--status",
                "active",
            ],
        )
        lines = capsys.readouterr().out.strip().splitlines()
        assert len(lines) == 1
        assert lines[0].startswith("obj-002")


class TestCurrent:
    def test_highest_priority_active_wins(self, ho_module, workdir, capsys):
        objectives, events = workdir
        for t, prio in [("low-a", "low"), ("high-b", "high"), ("normal-c", "normal")]:
            _run(
                ho_module,
                [
                    "--dir",
                    str(objectives),
                    "--events-file",
                    str(events),
                    "open",
                    t,
                    "--priority",
                    prio,
                    "--activity",
                    "study",
                    "--success",
                    "x",
                ],
            )
        capsys.readouterr()
        rc = _run(
            ho_module,
            ["--dir", str(objectives), "--events-file", str(events), "current"],
        )
        assert rc == 0
        assert "high-b" in capsys.readouterr().out

    def test_no_active_returns_nonzero(self, ho_module, workdir, capsys):
        objectives, events = workdir
        capsys.readouterr()
        rc = _run(
            ho_module,
            ["--dir", str(objectives), "--events-file", str(events), "current"],
        )
        assert rc == 1
        assert "no active" in capsys.readouterr().out


class TestAdvance:
    def test_emits_event(self, ho_module, workdir):
        objectives, events = workdir
        _run(
            ho_module,
            [
                "--dir",
                str(objectives),
                "--events-file",
                str(events),
                "open",
                "x",
                "--activity",
                "study",
                "--success",
                "ok",
            ],
        )
        _run(
            ho_module,
            [
                "--dir",
                str(objectives),
                "--events-file",
                str(events),
                "advance",
                "obj-001",
                "study",
            ],
        )
        lines = events.read_text().strip().splitlines()
        advance_events = [
            json.loads(line) for line in lines if json.loads(line)["kind"] == "advance"
        ]
        assert len(advance_events) == 1
        assert advance_events[0]["activity"] == "study"

    def test_unknown_activity_rejected(self, ho_module, workdir):
        objectives, events = workdir
        rc = _run(
            ho_module,
            [
                "--dir",
                str(objectives),
                "--events-file",
                str(events),
                "advance",
                "obj-001",
                "sleep",
            ],
        )
        assert rc == 2


class TestCloseDefer:
    def test_close_updates_status(self, ho_module, workdir):
        objectives, events = workdir
        _run(
            ho_module,
            [
                "--dir",
                str(objectives),
                "--events-file",
                str(events),
                "open",
                "x",
                "--activity",
                "study",
                "--success",
                "ok",
            ],
        )
        _run(
            ho_module,
            [
                "--dir",
                str(objectives),
                "--events-file",
                str(events),
                "close",
                "obj-001",
            ],
        )
        path = objectives / "obj-001.md"
        text = path.read_text()
        assert "status: closed" in text
        assert "closed_at:" in text

    def test_defer_updates_status(self, ho_module, workdir):
        objectives, events = workdir
        _run(
            ho_module,
            [
                "--dir",
                str(objectives),
                "--events-file",
                str(events),
                "open",
                "x",
                "--activity",
                "study",
                "--success",
                "ok",
            ],
        )
        _run(
            ho_module,
            [
                "--dir",
                str(objectives),
                "--events-file",
                str(events),
                "defer",
                "obj-001",
            ],
        )
        path = objectives / "obj-001.md"
        text = path.read_text()
        assert "status: deferred" in text

    def test_close_missing_id_errors(self, ho_module, workdir):
        objectives, events = workdir
        rc = _run(
            ho_module,
            [
                "--dir",
                str(objectives),
                "--events-file",
                str(events),
                "close",
                "obj-999",
            ],
        )
        assert rc == 1
