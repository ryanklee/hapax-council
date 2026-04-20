"""Tests for monetization_egress_audit.prune_old_archives logging (D-20)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest

from shared.governance.monetization_egress_audit import MonetizationEgressAudit


@pytest.fixture
def audit(tmp_path: Path) -> MonetizationEgressAudit:
    return MonetizationEgressAudit(path=tmp_path / "demonet-egress-audit.jsonl")


class TestPruneLogging:
    def test_start_and_end_log_messages(
        self, audit: MonetizationEgressAudit, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A prune run logs a start + end line at INFO so a crash mid-loop is visible."""
        now = datetime(2026, 4, 20, 0, 0, tzinfo=UTC).timestamp()
        with caplog.at_level(logging.INFO, logger="shared.governance.monetization_egress_audit"):
            audit.prune_old_archives(retention_days=0, now=now)
        messages = [r.message for r in caplog.records]
        assert any("prune_old_archives: start" in m for m in messages)
        assert any("prune_old_archives: end" in m for m in messages)

    def test_end_log_reports_pruned_count(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The end line includes the pruned=N count for operator attribution."""
        audit = MonetizationEgressAudit(path=tmp_path / "demonet-egress-audit.jsonl")
        # Fabricate an old archive.
        old = audit.path.with_suffix(".2026-01-01.jsonl")
        old.parent.mkdir(parents=True, exist_ok=True)
        old.write_text("x\n")
        now = datetime(2026, 4, 20, 0, 0, tzinfo=UTC).timestamp()
        with caplog.at_level(logging.INFO, logger="shared.governance.monetization_egress_audit"):
            audit.prune_old_archives(retention_days=30, now=now)
        end_messages = [r.message for r in caplog.records if "end" in r.message]
        assert any("pruned=1" in m for m in end_messages)

    def test_missing_parent_dir_skips_both_logs(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When parent dir doesn't exist we short-circuit — no logs."""
        audit = MonetizationEgressAudit(path=tmp_path / "nonexistent" / "audit.jsonl")
        now = datetime(2026, 4, 20, 0, 0, tzinfo=UTC).timestamp()
        with caplog.at_level(logging.INFO, logger="shared.governance.monetization_egress_audit"):
            result = audit.prune_old_archives(retention_days=30, now=now)
        assert result == []
        # No start/end logs because the short-circuit happens BEFORE the
        # logging block.
        assert not any("prune_old_archives" in r.message for r in caplog.records)
