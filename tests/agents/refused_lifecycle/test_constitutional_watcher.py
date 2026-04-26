"""Tests for ``agents.refused_lifecycle.constitutional_watcher``.

Covers the pure ``probe_constitutional`` decision logic — daemon I/O
(watchdog observer + debounce loop) is smoke-tested via systemd in
production, not unit-tested. Probe semantics:

- type-B uses ``lift_polarity: absent`` — keyword *removed* from the
  watched constitutional surface signals lift
- target file not in the changed set → unchanged (no work)
- conditional_path missing or empty → unchanged (no probe configured)
"""

from __future__ import annotations

from pathlib import Path

from agents.refused_lifecycle.constitutional_watcher import (
    WATCHED_PATHS,
    probe_constitutional,
)
from agents.refused_lifecycle.state import RefusalTask


def _constitutional_task(
    *,
    conditional_path: str | None = "/tmp/memory.md",
    lift_keywords: list[str] | None = None,
    lift_polarity: str = "absent",
) -> RefusalTask:
    return RefusalTask(
        slug="awareness-refused-pending-review-inboxes",
        path="/tmp/x.md",
        automation_status="REFUSED",
        refusal_reason="full_automation_or_no_engagement",
        evaluation_trigger=["constitutional"],
        evaluation_probe={
            "url": None,
            "conditional_path": conditional_path,
            "depends_on_slug": None,
            "lift_keywords": lift_keywords or ["feedback_no_operator_approval_waits"],
            "lift_polarity": lift_polarity,
            "last_etag": None,
            "last_lm": None,
            "last_fingerprint": None,
        },
    )


# ── probe_constitutional ─────────────────────────────────────────────


class TestProbeConstitutional:
    def test_keyword_still_present_re_affirms_with_absent_polarity(self, tmp_path: Path):
        memory = tmp_path / "memory.md"
        memory.write_text("## Feedback\n- feedback_no_operator_approval_waits\n", encoding="utf-8")
        task = _constitutional_task(
            conditional_path=str(memory),
            lift_polarity="absent",
        )
        result = probe_constitutional(task, {memory})
        assert result.changed is False  # keyword still there → still prohibited

    def test_keyword_absent_signals_lift_with_absent_polarity(self, tmp_path: Path):
        memory = tmp_path / "memory.md"
        memory.write_text("## Feedback\n- (axiom retired)\n", encoding="utf-8")
        task = _constitutional_task(
            conditional_path=str(memory),
            lift_polarity="absent",
        )
        result = probe_constitutional(task, {memory})
        assert result.changed is True
        assert result.evidence_url == str(memory)

    def test_present_polarity_inverts_logic(self, tmp_path: Path):
        # Type-A-like polarity: keyword PRESENT means lift
        memory = tmp_path / "memory.md"
        memory.write_text("upload api permitted\n", encoding="utf-8")
        task = _constitutional_task(
            conditional_path=str(memory),
            lift_keywords=["upload api"],
            lift_polarity="present",
        )
        result = probe_constitutional(task, {memory})
        assert result.changed is True

    def test_unchanged_path_returns_unchanged(self, tmp_path: Path):
        memory = tmp_path / "memory.md"
        memory.write_text("anything", encoding="utf-8")
        task = _constitutional_task(conditional_path=str(memory))
        # changed_paths set does NOT include the conditional_path
        unrelated = tmp_path / "unrelated.md"
        result = probe_constitutional(task, {unrelated})
        assert result.changed is False

    def test_missing_conditional_path_returns_unchanged_with_error(self):
        task = _constitutional_task(conditional_path=None)
        result = probe_constitutional(task, set())
        assert result.changed is False
        assert result.error is not None

    def test_target_file_does_not_exist(self, tmp_path: Path):
        ghost = tmp_path / "missing.md"
        # File never written, but it appears in the inotify changed-set
        # (e.g., MOVED_FROM event). Probe should re-affirm with error.
        task = _constitutional_task(conditional_path=str(ghost))
        result = probe_constitutional(task, {ghost})
        assert result.changed is False
        assert result.error is not None


# ── Watched-paths registry ───────────────────────────────────────────


class TestWatchedPaths:
    def test_includes_axiom_registry(self):
        assert any("axioms/registry.yaml" in str(p) for p in WATCHED_PATHS)

    def test_includes_memory(self):
        assert any("MEMORY.md" in str(p) for p in WATCHED_PATHS)
