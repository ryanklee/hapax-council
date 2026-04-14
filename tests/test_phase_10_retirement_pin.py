"""LRR Phase 10 close handoff pin (2026-04-14).

Pins existence + required sections of the Phase 10 observability
polish handoff so it can't be silently renamed or pruned. Modeled
on tests/test_retirement_continuation_pin.py from the prior
retirement.
"""

from __future__ import annotations

from pathlib import Path

HANDOFF_PATH = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "superpowers"
    / "handoff"
    / "2026-04-14-lrr-phase-10-complete.md"
)

REQUIRED_SECTIONS: tuple[str, ...] = (
    "## Start state",
    "## What shipped this phase",
    "## LRR state at retirement",
    "## Test stats this phase",
    "## Items intentionally deferred from Phase 10",
    "## Known carry-overs from prior phases",
    "## Hardware milestone pending",
    "## Recommended next pickup",
    "## Final sanity checks",
)


class TestPhase10HandoffPin:
    def test_handoff_file_exists(self) -> None:
        assert HANDOFF_PATH.is_file(), f"Phase 10 handoff missing at {HANDOFF_PATH}."

    def test_handoff_has_required_sections(self) -> None:
        body = HANDOFF_PATH.read_text(encoding="utf-8")
        missing = [s for s in REQUIRED_SECTIONS if s not in body]
        assert not missing, f"Phase 10 handoff missing sections: {missing}"

    def test_handoff_documents_all_five_commits(self) -> None:
        body = HANDOFF_PATH.read_text(encoding="utf-8")
        assert "Phase 10 PR #1" in body
        assert "Phase 10 PR #2" in body
        assert "Phase 10 PR #3" in body
        assert "Phase 10 PR #4" in body
        assert "Phase 10 PR #5" in body

    def test_handoff_cites_completed_phases_set(self) -> None:
        body = HANDOFF_PATH.read_text(encoding="utf-8")
        assert "`[0, 1, 2, 9, 10]`" in body or "[0,1,2,9,10]" in body

    def test_handoff_links_to_prior_retirement(self) -> None:
        body = HANDOFF_PATH.read_text(encoding="utf-8")
        assert "2026-04-14-alpha-continuation-retirement" in body

    def test_handoff_cites_delta_picklist_source(self) -> None:
        """The delta perf-findings-rollup picklist MUST be cited as source."""
        body = HANDOFF_PATH.read_text(encoding="utf-8")
        assert "perf-findings-rollup" in body
        assert "metric-coverage-gaps" in body
