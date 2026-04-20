"""Tests for shared/programme_outcome_log.py — Phase 9 Critical #5 (B3 audit).

Verifies the per-programme JSONL writer + size-based rotation +
defensive failure paths. Programme is structurally typed (caller
passes any object with the right attributes) so tests use a tiny
stub class instead of importing the real Pydantic model.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from shared.programme_outcome_log import (
    DEFAULT_KEEP_GENERATIONS,
    DEFAULT_MAX_BYTES,
    ProgrammeOutcomeLog,
    get_default_log,
)


class _StubProgramme:
    def __init__(
        self,
        *,
        programme_id: str = "prog-001",
        parent_show_id: str = "show-A",
        role: str = "deep_focus",
        planned_duration_s: float = 1800.0,
        elapsed_s: float | None = None,
    ) -> None:
        self.programme_id = programme_id
        self.parent_show_id = parent_show_id
        self.role = role
        self.planned_duration_s = planned_duration_s
        self.elapsed_s = elapsed_s


@pytest.fixture()
def log(tmp_path: Path) -> ProgrammeOutcomeLog:
    return ProgrammeOutcomeLog(root=tmp_path)


# ── Path composition ──────────────────────────────────────────────────


class TestPathComposition:
    def test_path_layout_show_then_programme_jsonl(
        self, log: ProgrammeOutcomeLog, tmp_path: Path
    ) -> None:
        prog = _StubProgramme(programme_id="prog-A1", parent_show_id="show-X")
        log.record_event(prog, "started")
        expected = tmp_path / "show-X" / "prog-A1.jsonl"
        assert expected.exists()

    def test_show_id_sanitised(self, log: ProgrammeOutcomeLog, tmp_path: Path) -> None:
        """A show_id with a path separator must NOT escape the root."""
        prog = _StubProgramme(parent_show_id="../etc/passwd")
        log.record_event(prog, "started")
        # No file at the escaped path.
        escaped = tmp_path.parent / "etc" / "passwd"
        assert not escaped.exists()
        # File lands under the sanitised show name.
        survivors = list((tmp_path).rglob("*.jsonl"))
        assert len(survivors) == 1
        assert ".." not in str(survivors[0])

    def test_programme_id_sanitised(self, log: ProgrammeOutcomeLog, tmp_path: Path) -> None:
        prog = _StubProgramme(programme_id="prog-A/../shadow")
        log.record_event(prog, "started")
        survivors = list((tmp_path).rglob("*.jsonl"))
        assert len(survivors) == 1
        assert ".." not in str(survivors[0])


# ── Entry shape ───────────────────────────────────────────────────────


class TestEntryShape:
    def test_started_event_serialised(self, log: ProgrammeOutcomeLog, tmp_path: Path) -> None:
        prog = _StubProgramme(elapsed_s=None)
        ts = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)
        log.record_event(prog, "started", emitted_at=ts)
        path = tmp_path / "show-A" / "prog-001.jsonl"
        line = path.read_text(encoding="utf-8").strip()
        rec = json.loads(line)
        assert rec["event"] == "started"
        assert rec["emitted_at"] == ts.isoformat()
        assert rec["programme_id"] == "prog-001"
        assert rec["show_id"] == "show-A"
        assert rec["role"] == "deep_focus"
        assert rec["planned_duration_s"] == 1800.0
        assert rec["elapsed_s"] is None

    def test_ended_event_carries_elapsed(self, log: ProgrammeOutcomeLog, tmp_path: Path) -> None:
        prog = _StubProgramme(elapsed_s=1742.5)
        log.record_event(prog, "ended_planned")
        rec = json.loads(
            (tmp_path / "show-A" / "prog-001.jsonl").read_text(encoding="utf-8").strip()
        )
        assert rec["event"] == "ended_planned"
        assert rec["elapsed_s"] == 1742.5

    def test_metadata_passes_through(self, log: ProgrammeOutcomeLog, tmp_path: Path) -> None:
        prog = _StubProgramme()
        log.record_event(prog, "ended_aborted", metadata={"reason": "operator_left_room"})
        rec = json.loads(
            (tmp_path / "show-A" / "prog-001.jsonl").read_text(encoding="utf-8").strip()
        )
        assert rec["metadata"]["reason"] == "operator_left_room"


# ── Append behavior + read_all ────────────────────────────────────────


class TestAppendAndRead:
    def test_multiple_events_appended_chronologically(self, log: ProgrammeOutcomeLog) -> None:
        prog = _StubProgramme()
        log.record_event(prog, "started", emitted_at=datetime(2026, 4, 20, 12, 0, tzinfo=UTC))
        log.record_event(
            prog, "ended_planned", emitted_at=datetime(2026, 4, 20, 12, 30, tzinfo=UTC)
        )
        records = log.read_all(prog)
        assert len(records) == 2
        assert records[0]["event"] == "started"
        assert records[1]["event"] == "ended_planned"

    def test_read_all_missing_file_returns_empty(self, log: ProgrammeOutcomeLog) -> None:
        prog = _StubProgramme(programme_id="never-written")
        assert log.read_all(prog) == []

    def test_read_all_skips_malformed_lines(self, log: ProgrammeOutcomeLog, tmp_path: Path) -> None:
        prog = _StubProgramme()
        log.record_event(prog, "started")
        path = tmp_path / "show-A" / "prog-001.jsonl"
        # Append a bad line
        with path.open("a", encoding="utf-8") as f:
            f.write("not valid json\n")
        log.record_event(prog, "ended_planned")
        records = log.read_all(prog)
        assert [r["event"] for r in records] == ["started", "ended_planned"]


# ── Rotation ──────────────────────────────────────────────────────────


class TestRotation:
    def test_rotation_at_max_bytes(self, tmp_path: Path) -> None:
        # Tiny budget so a single record triggers rotation.
        log = ProgrammeOutcomeLog(root=tmp_path, max_bytes=200, keep_generations=3)
        prog = _StubProgramme()
        for i in range(5):
            log.record_event(prog, "started", metadata={"i": i})
        path = tmp_path / "show-A" / "prog-001.jsonl"
        # Active file exists.
        assert path.exists()
        # At least one rotated generation exists.
        rotated_1 = path.with_suffix(".jsonl.1")
        assert rotated_1.exists(), "first rotation generation missing"

    def test_keep_generations_caps_count(self, tmp_path: Path) -> None:
        log = ProgrammeOutcomeLog(root=tmp_path, max_bytes=120, keep_generations=2)
        prog = _StubProgramme()
        for i in range(20):
            log.record_event(prog, "started", metadata={"i": i})
        path = tmp_path / "show-A" / "prog-001.jsonl"
        # Only .jsonl + .jsonl.1 — no .jsonl.2 with keep=2.
        assert path.exists()
        assert path.with_suffix(".jsonl.1").exists()
        assert not path.with_suffix(".jsonl.2").exists()

    def test_read_all_includes_rotated_generations(self, tmp_path: Path) -> None:
        # 600 bytes ≈ 2-3 records per generation; with keep=3 that gives
        # roughly 6-9 surviving records out of 8 written.
        log = ProgrammeOutcomeLog(root=tmp_path, max_bytes=600, keep_generations=3)
        prog = _StubProgramme()
        for i in range(8):
            log.record_event(prog, "started", metadata={"i": i})
        records = log.read_all(prog)
        # The most-recent record (i=7) must be in the active file.
        assert any(r["metadata"].get("i") == 7 for r in records)
        # At least one rotated generation contributed records.
        path = tmp_path / "show-A" / "prog-001.jsonl"
        assert path.with_suffix(".jsonl.1").exists(), "rotation never fired"
        # read_all must include records from BOTH active + rotated files.
        active_only = ProgrammeOutcomeLog._read_one(path)
        assert len(records) > len(active_only), (
            "read_all must include rotated generations; "
            f"got {len(records)} but active alone has {len(active_only)}"
        )


# ── Defensive paths ───────────────────────────────────────────────────


class TestDefensivePaths:
    def test_record_event_swallows_exceptions(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A filesystem failure in record_event must not raise — the
        lifecycle path must keep running."""
        log = ProgrammeOutcomeLog(root=tmp_path)
        prog = _StubProgramme()

        def _broken_open(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(Path, "open", _broken_open)
        # Must not raise.
        log.record_event(prog, "started")

    def test_record_event_with_attribute_failure_uses_unknown(
        self, log: ProgrammeOutcomeLog, tmp_path: Path
    ) -> None:
        """Programme stub missing all the load-bearing attributes
        still produces a usable record (fields default to "unknown"
        rather than crash)."""

        class _MinimalStub:
            pass

        log.record_event(_MinimalStub(), "ended_aborted")
        survivors = list(tmp_path.rglob("*.jsonl"))
        assert len(survivors) == 1
        rec = json.loads(survivors[0].read_text(encoding="utf-8").strip())
        assert rec["programme_id"] == "unknown"
        assert rec["show_id"] == "unknown"
        assert rec["role"] == "unknown"


# ── Module-level singleton ────────────────────────────────────────────


class TestSingleton:
    def test_get_default_log_returns_same_instance(self) -> None:
        a = get_default_log()
        b = get_default_log()
        assert a is b

    def test_default_log_uses_canonical_root(self) -> None:
        # The default singleton's root matches the documented vault path.
        log = get_default_log()
        assert log.root.name == "programmes"
        assert log.root.parent.name == "hapax-state"

    def test_default_max_bytes_matches_audit(self) -> None:
        assert DEFAULT_MAX_BYTES == 5 * 1024 * 1024  # 5 MiB

    def test_default_keep_generations_matches_audit(self) -> None:
        assert DEFAULT_KEEP_GENERATIONS == 3
