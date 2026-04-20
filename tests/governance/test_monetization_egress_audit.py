"""Tests for shared.governance.monetization_egress_audit — JSONL audit writer."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from shared.governance.monetization_egress_audit import (
    DEFAULT_RETENTION_DAYS,
    MonetizationEgressAudit,
)
from shared.governance.monetization_safety import RiskAssessment, SurfaceKind


@pytest.fixture
def audit(tmp_path: Path) -> MonetizationEgressAudit:
    return MonetizationEgressAudit(path=tmp_path / "demonet-egress-audit.jsonl")


def _assessment(allowed: bool = True, risk: str = "none", reason: str = "ok") -> RiskAssessment:
    return RiskAssessment(allowed=allowed, risk=risk, reason=reason)


class TestRecord:
    def test_single_write(self, audit: MonetizationEgressAudit) -> None:
        audit.record(
            "env.weather",
            _assessment(),
            now=1000.0,
        )
        line = audit.path.read_text().strip()
        record = json.loads(line)
        assert record["capability_name"] == "env.weather"
        assert record["allowed"] is True
        assert record["ts"] == 1000.0
        assert record["surface"] is None
        assert record["programme_id"] is None

    def test_multiple_appends(self, audit: MonetizationEgressAudit) -> None:
        for i in range(3):
            audit.record(f"cap.{i}", _assessment(), now=1000.0 + i)
        lines = audit.path.read_text().strip().splitlines()
        assert len(lines) == 3
        assert [json.loads(line)["capability_name"] for line in lines] == [
            "cap.0",
            "cap.1",
            "cap.2",
        ]

    def test_surface_and_programme_recorded(self, audit: MonetizationEgressAudit) -> None:
        audit.record(
            "knowledge.web_search",
            _assessment(allowed=False, risk="medium", reason="no programme opt-in"),
            surface=SurfaceKind.TTS,
            programme_id="showcase-001",
            now=1000.0,
        )
        record = json.loads(audit.path.read_text().strip())
        assert record["surface"] == "tts"
        assert record["programme_id"] == "showcase-001"
        assert record["allowed"] is False
        assert record["risk"] == "medium"

    def test_extra_payload(self, audit: MonetizationEgressAudit) -> None:
        audit.record(
            "cap",
            _assessment(),
            extra={"impingement_id": "abc123", "director_cycle": 42},
        )
        record = json.loads(audit.path.read_text().strip())
        assert record["extra"]["impingement_id"] == "abc123"
        assert record["extra"]["director_cycle"] == 42

    def test_parent_dir_created(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested" / "deeper" / "audit.jsonl"
        audit = MonetizationEgressAudit(path=nested)
        audit.record("cap", _assessment())
        assert nested.exists()
        assert nested.parent.is_dir()


class TestRotate:
    def test_noop_on_empty(self, audit: MonetizationEgressAudit) -> None:
        assert audit.rotate() is None

    def test_noop_on_missing_file(self, audit: MonetizationEgressAudit) -> None:
        assert not audit.path.exists()
        assert audit.rotate() is None

    def test_rotates_to_dated_archive(self, audit: MonetizationEgressAudit) -> None:
        audit.record("cap", _assessment(), now=1000.0)
        # Use a fixed UTC timestamp for the test — 2026-04-20 00:00 UTC.
        ts = datetime(2026, 4, 20, 0, 0, tzinfo=UTC).timestamp()
        archive = audit.rotate(now=ts)
        assert archive is not None
        assert archive.name == "demonet-egress-audit.2026-04-20.jsonl"
        assert archive.exists()
        # Live file is gone after rename.
        assert not audit.path.exists()

    def test_same_day_rotate_appends_to_existing_archive(
        self, audit: MonetizationEgressAudit
    ) -> None:
        """Two rotations on the same UTC day merge into one archive."""
        ts = datetime(2026, 4, 20, 0, 0, tzinfo=UTC).timestamp()
        audit.record("first", _assessment(), now=1000.0)
        audit.rotate(now=ts)
        audit.record("second", _assessment(), now=1001.0)
        audit.rotate(now=ts)
        archive = audit.path.with_suffix(".2026-04-20.jsonl")
        records = [json.loads(line) for line in archive.read_text().splitlines() if line]
        names = {r["capability_name"] for r in records}
        assert names == {"first", "second"}


class TestPrune:
    def _fabricate_archive(
        self, audit: MonetizationEgressAudit, date: str, content: str = "x\n"
    ) -> Path:
        path = audit.path.with_suffix(f".{date}.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_prune_removes_old_archives(self, audit: MonetizationEgressAudit) -> None:
        now = datetime(2026, 4, 20, 0, 0, tzinfo=UTC).timestamp()
        old = self._fabricate_archive(audit, "2026-01-01")  # 110 days old
        recent = self._fabricate_archive(audit, "2026-04-15")  # 5 days old
        pruned = audit.prune_old_archives(retention_days=30, now=now)
        assert old in pruned
        assert not old.exists()
        assert recent.exists()

    def test_prune_does_not_touch_live(self, audit: MonetizationEgressAudit) -> None:
        audit.record("cap", _assessment())
        now = datetime(2026, 4, 20, 0, 0, tzinfo=UTC).timestamp()
        pruned = audit.prune_old_archives(retention_days=0, now=now)
        # Live file NEVER pruned regardless of retention.
        assert audit.path.exists()
        assert audit.path not in pruned

    def test_prune_ignores_unrelated_files(self, audit: MonetizationEgressAudit) -> None:
        """Files that don't match <stem>.YYYY-MM-DD<suffix> are left alone."""
        now = datetime(2026, 4, 20, 0, 0, tzinfo=UTC).timestamp()
        stranger = audit.path.parent / "README.md"
        stranger.parent.mkdir(parents=True, exist_ok=True)
        stranger.write_text("# not ours\n")
        audit.prune_old_archives(retention_days=0, now=now)
        assert stranger.exists()

    def test_prune_ignores_malformed_date(self, audit: MonetizationEgressAudit) -> None:
        now = datetime(2026, 4, 20, 0, 0, tzinfo=UTC).timestamp()
        weird = audit.path.with_suffix(".not-a-date.jsonl")
        weird.parent.mkdir(parents=True, exist_ok=True)
        weird.write_text("x\n")
        audit.prune_old_archives(retention_days=0, now=now)
        assert weird.exists()

    def test_default_retention(self) -> None:
        assert DEFAULT_RETENTION_DAYS == 30


class TestThreadSafety:
    def test_concurrent_record_no_corruption(self, audit: MonetizationEgressAudit) -> None:
        """Many threads appending simultaneously — no interleaved bytes."""
        from concurrent.futures import ThreadPoolExecutor

        N = 100

        def writer(i: int) -> None:
            audit.record(f"cap.{i}", _assessment(), now=float(i))

        with ThreadPoolExecutor(max_workers=16) as ex:
            list(ex.map(writer, range(N)))

        lines = audit.path.read_text().splitlines()
        assert len(lines) == N
        # Every line parses cleanly — no interleaving corruption.
        parsed = [json.loads(line) for line in lines]
        names = {p["capability_name"] for p in parsed}
        assert names == {f"cap.{i}" for i in range(N)}
