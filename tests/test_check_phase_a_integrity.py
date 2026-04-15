"""Tests for scripts/check-phase-a-integrity.py — LRR Phase 4 §3.6
mid-collection integrity check.

Covers:

- CheckState load / save round trip
- check_current_condition — pointer present, pointer missing, pointer drift
- check_frozen_files_clean — script missing (graceful skip)
- check_channel_split — both channels advancing, reaction stall, score stall,
  first run bootstrap (both growth timestamps zero)
- run_checks — dry-run end-to-end: current condition + channel split only

The external-service checks (Qdrant + Langfuse) are NOT exercised in unit
tests — they require live infrastructure. Their branches are verified via
``--dry-run`` which skips both.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

# Load the script as a module despite its hyphenated filename.
_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "check-phase-a-integrity.py"
_spec = importlib.util.spec_from_file_location("check_phase_a_integrity", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
check_phase_a_integrity = importlib.util.module_from_spec(_spec)
sys.modules["check_phase_a_integrity"] = check_phase_a_integrity
_spec.loader.exec_module(check_phase_a_integrity)  # type: ignore[union-attr]


class TestCheckState:
    def test_load_returns_default_when_file_missing(self, tmp_path: Path) -> None:
        state = check_phase_a_integrity.CheckState.load(tmp_path / "missing.json")
        assert state.last_check_ts == 0.0
        assert state.last_reaction_count == 0
        assert state.last_score_count == 0

    def test_load_returns_default_on_malformed_json(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("not-json {{{")
        state = check_phase_a_integrity.CheckState.load(f)
        assert state.last_reaction_count == 0

    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        state = check_phase_a_integrity.CheckState(
            last_check_ts=12345.0,
            last_reaction_count=42,
            last_score_count=17,
            last_reaction_growth_ts=12000.0,
            last_score_growth_ts=12100.0,
        )
        state.save(path)

        loaded = check_phase_a_integrity.CheckState.load(path)
        assert loaded.last_check_ts == 12345.0
        assert loaded.last_reaction_count == 42
        assert loaded.last_score_count == 17
        assert loaded.last_reaction_growth_ts == 12000.0
        assert loaded.last_score_growth_ts == 12100.0


class TestCheckCurrentCondition:
    def test_returns_ok_when_current_matches(self, tmp_path: Path) -> None:
        (tmp_path / "current.txt").write_text("cond-phase-a-baseline-qwen-001\n")
        ok, msg, actual = check_phase_a_integrity.check_current_condition(
            "cond-phase-a-baseline-qwen-001", tmp_path
        )
        assert ok is True
        assert actual == "cond-phase-a-baseline-qwen-001"

    def test_fails_when_current_missing(self, tmp_path: Path) -> None:
        ok, msg, actual = check_phase_a_integrity.check_current_condition(
            "cond-phase-a-baseline-qwen-001", tmp_path
        )
        assert ok is False
        assert "missing" in msg.lower() or "empty" in msg.lower()
        assert actual is None

    def test_fails_when_current_empty(self, tmp_path: Path) -> None:
        (tmp_path / "current.txt").write_text("")
        ok, _, actual = check_phase_a_integrity.check_current_condition(
            "cond-phase-a-baseline-qwen-001", tmp_path
        )
        assert ok is False
        assert actual is None

    def test_fails_when_current_drifted(self, tmp_path: Path) -> None:
        (tmp_path / "current.txt").write_text("cond-something-else-123\n")
        ok, msg, actual = check_phase_a_integrity.check_current_condition(
            "cond-phase-a-baseline-qwen-001", tmp_path
        )
        assert ok is False
        assert "drifted" in msg
        assert actual == "cond-something-else-123"


class TestCheckFrozenFiles:
    def test_returns_ok_when_script_missing(self, tmp_path: Path) -> None:
        """If the repo doesn't have the check-frozen-files.py script, the
        integrity check silently passes (downgrades gracefully)."""
        ok, msg = check_phase_a_integrity.check_frozen_files_clean(tmp_path)
        assert ok is True
        assert "skipped" in msg.lower() or "not found" in msg.lower()


class TestCheckChannelSplit:
    def test_both_channels_advancing(self) -> None:
        state = check_phase_a_integrity.CheckState(
            last_reaction_count=10,
            last_score_count=5,
            last_reaction_growth_ts=1000.0,
            last_score_growth_ts=1000.0,
        )
        ok, msg = check_phase_a_integrity.check_channel_split(
            state,
            reaction_count=20,  # grew
            score_count=10,  # grew
            now_ts=2000.0,
        )
        assert ok is True
        assert state.last_reaction_growth_ts == 2000.0
        assert state.last_score_growth_ts == 2000.0

    def test_reaction_channel_stalled_long(self) -> None:
        state = check_phase_a_integrity.CheckState(
            last_reaction_count=10,
            last_score_count=5,
            last_reaction_growth_ts=1000.0,  # 1 hour ago
            last_score_growth_ts=4000.0,
        )
        ok, msg = check_phase_a_integrity.check_channel_split(
            state,
            reaction_count=10,  # no growth
            score_count=10,  # grew
            now_ts=4600.0,  # 3600s after last reaction growth
        )
        assert ok is False
        assert "reactions stalled" in msg

    def test_score_channel_stalled_long(self) -> None:
        state = check_phase_a_integrity.CheckState(
            last_reaction_count=10,
            last_score_count=5,
            last_reaction_growth_ts=4000.0,
            last_score_growth_ts=1000.0,  # 1 hour ago
        )
        ok, msg = check_phase_a_integrity.check_channel_split(
            state,
            reaction_count=20,  # grew
            score_count=5,  # no growth
            now_ts=4600.0,
        )
        assert ok is False
        assert "scores stalled" in msg

    def test_first_run_bootstrap_zero_timestamps_not_flagged(self) -> None:
        """On the very first run, both last_*_growth_ts are 0.0. The
        check must NOT flag this as a 30-minute stall — stall detection
        kicks in only after the first observed growth."""
        state = check_phase_a_integrity.CheckState(
            last_reaction_count=0,
            last_score_count=0,
            last_reaction_growth_ts=0.0,
            last_score_growth_ts=0.0,
        )
        ok, msg = check_phase_a_integrity.check_channel_split(
            state,
            reaction_count=10,
            score_count=5,
            now_ts=99999.0,
        )
        assert ok is True
        assert state.last_reaction_growth_ts == 99999.0
        assert state.last_score_growth_ts == 99999.0

    def test_short_stall_not_flagged(self) -> None:
        """Stalls under 30 min are acceptable (maybe the stream was
        briefly quiet or the operator walked away)."""
        state = check_phase_a_integrity.CheckState(
            last_reaction_count=10,
            last_score_count=5,
            last_reaction_growth_ts=1000.0,
            last_score_growth_ts=1000.0,
        )
        ok, msg = check_phase_a_integrity.check_channel_split(
            state,
            reaction_count=10,  # no growth
            score_count=5,  # no growth
            now_ts=1500.0,  # 500s later — under 30 min
        )
        assert ok is True


class TestRunChecksDryRun:
    """End-to-end dry-run: only the file-based checks (current condition +
    channel split + state persistence) execute. Qdrant + Langfuse +
    frozen-files are skipped."""

    def test_dry_run_all_checks_pass_with_valid_condition(self, tmp_path: Path) -> None:
        registry_dir = tmp_path / "registry"
        registry_dir.mkdir()
        (registry_dir / "current.txt").write_text("cond-phase-a-baseline-qwen-001\n")

        state_file = tmp_path / "state.json"

        args = check_phase_a_integrity.build_parser().parse_args(
            [
                "--expected-condition",
                "cond-phase-a-baseline-qwen-001",
                "--state-file",
                str(state_file),
                "--registry-dir",
                str(registry_dir),
                "--dry-run",
            ]
        )

        result = check_phase_a_integrity.run_checks(args)

        assert result.ok is True
        assert result.exit_code == 0
        assert "current_condition" in result.checks
        assert result.checks["current_condition"]["ok"] is True
        assert state_file.exists()

        loaded = json.loads(state_file.read_text())
        assert loaded["last_check_ts"] > 0

    def test_dry_run_fails_fast_when_condition_drifted(self, tmp_path: Path) -> None:
        registry_dir = tmp_path / "registry"
        registry_dir.mkdir()
        (registry_dir / "current.txt").write_text("cond-wrong-drifted-999\n")

        state_file = tmp_path / "state.json"

        args = check_phase_a_integrity.build_parser().parse_args(
            [
                "--expected-condition",
                "cond-phase-a-baseline-qwen-001",
                "--state-file",
                str(state_file),
                "--registry-dir",
                str(registry_dir),
                "--dry-run",
            ]
        )

        result = check_phase_a_integrity.run_checks(args)

        assert result.ok is False
        assert result.exit_code == 1
        assert "drifted" in result.reason

    def test_dry_run_fails_when_registry_missing(self, tmp_path: Path) -> None:
        registry_dir = tmp_path / "registry"
        # Do NOT create the directory

        state_file = tmp_path / "state.json"

        args = check_phase_a_integrity.build_parser().parse_args(
            [
                "--expected-condition",
                "cond-phase-a-baseline-qwen-001",
                "--state-file",
                str(state_file),
                "--registry-dir",
                str(registry_dir),
                "--dry-run",
            ]
        )

        result = check_phase_a_integrity.run_checks(args)

        assert result.ok is False
        assert result.exit_code == 1


class TestBuildParser:
    def test_default_expected_condition(self) -> None:
        args = check_phase_a_integrity.build_parser().parse_args([])
        assert args.expected_condition == "cond-phase-a-baseline-qwen-001"

    def test_json_flag(self) -> None:
        args = check_phase_a_integrity.build_parser().parse_args(["--json"])
        assert args.as_json is True

    def test_dry_run_flag(self) -> None:
        args = check_phase_a_integrity.build_parser().parse_args(["--dry-run"])
        assert args.dry_run is True
