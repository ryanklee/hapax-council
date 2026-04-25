"""Tests for ``agents.refusal_brief.writer``."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from agents.refusal_brief.writer import (
    REASON_MAX_CHARS,
    RefusalEvent,
    append,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _read_lines(path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


# ── RefusalEvent model ─────────────────────────────────────────────


class TestRefusalEventModel:
    def test_minimal_construction(self):
        ev = RefusalEvent(
            timestamp=_now(),
            axiom="single_user",
            surface="x",
            reason="y",
        )
        assert ev.public is False
        assert ev.refusal_brief_link is None

    def test_reason_max_length_enforced(self):
        oversized = "x" * (REASON_MAX_CHARS + 1)
        with pytest.raises(ValidationError):
            RefusalEvent(
                timestamp=_now(),
                axiom="x",
                surface="y",
                reason=oversized,
            )

    def test_unknown_field_rejected(self):
        """extra='forbid' — drift in the writer fails at validation."""
        with pytest.raises(ValidationError):
            RefusalEvent.model_validate(
                {
                    "timestamp": _now().isoformat(),
                    "axiom": "x",
                    "surface": "y",
                    "reason": "z",
                    "narrative_apology": "we're sorry",  # no narrative voice allowed
                }
            )

    def test_frozen(self):
        ev = RefusalEvent(timestamp=_now(), axiom="x", surface="y", reason="z")
        with pytest.raises((TypeError, ValidationError)):
            ev.surface = "mutated"

    def test_optional_brief_link_persists(self):
        ev = RefusalEvent(
            timestamp=_now(),
            axiom="full_auto_or_nothing",
            surface="bandcamp",
            reason="ToS prohibits AI",
            refusal_brief_link="docs/refusal-briefs/bandcamp.md",
        )
        assert ev.refusal_brief_link == "docs/refusal-briefs/bandcamp.md"


# ── append() ───────────────────────────────────────────────────────


class TestAppend:
    def test_writes_one_line_per_event(self, tmp_path):
        path = tmp_path / "log.jsonl"
        ok1 = append(
            RefusalEvent(timestamp=_now(), axiom="x", surface="a", reason="r1"),
            log_path=path,
        )
        ok2 = append(
            RefusalEvent(timestamp=_now(), axiom="y", surface="b", reason="r2"),
            log_path=path,
        )
        assert ok1 is True
        assert ok2 is True
        records = _read_lines(path)
        assert len(records) == 2
        assert records[0]["surface"] == "a"
        assert records[1]["surface"] == "b"

    def test_creates_parent_dir(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "log.jsonl"
        ok = append(
            RefusalEvent(timestamp=_now(), axiom="x", surface="y", reason="z"),
            log_path=path,
        )
        assert ok is True
        assert path.exists()

    def test_unwritable_returns_false(self, tmp_path, monkeypatch):
        """Failure path: log + return False, don't raise."""

        def _fail_mkdir(*_a, **_k):
            raise OSError("read-only fs")

        from pathlib import Path as _Path

        monkeypatch.setattr(_Path, "mkdir", _fail_mkdir)
        ok = append(
            RefusalEvent(timestamp=_now(), axiom="x", surface="y", reason="z"),
            log_path=tmp_path / "blocked" / "log.jsonl",
        )
        assert ok is False

    def test_unicode_preserved(self, tmp_path):
        path = tmp_path / "log.jsonl"
        append(
            RefusalEvent(
                timestamp=_now(),
                axiom="x",
                surface="y",
                reason="declined: café résumé",
            ),
            log_path=path,
        )
        records = _read_lines(path)
        assert records[0]["reason"] == "declined: café résumé"


# ── Thread safety ──────────────────────────────────────────────────


class TestConcurrency:
    def test_concurrent_appends_serialise(self, tmp_path):
        """4 threads × 25 appends = 100 well-formed lines (no interleaving)."""
        path = tmp_path / "log.jsonl"

        def burst(start: int) -> None:
            for i in range(25):
                append(
                    RefusalEvent(
                        timestamp=_now(),
                        axiom="concurrency_test",
                        surface=f"s-{start}-{i}",
                        reason=f"thread {start} event {i}",
                    ),
                    log_path=path,
                )

        threads = [threading.Thread(target=burst, args=(s,)) for s in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        records = _read_lines(path)
        assert len(records) == 100
        # Per-line atomicity: every record parses + carries the right shape.
        for r in records:
            assert "timestamp" in r
            assert r["axiom"] == "concurrency_test"
            assert r["surface"].startswith("s-")
