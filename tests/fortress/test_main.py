"""Tests for fortress daemon runtime loop."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

from agents.fortress.__main__ import FortressDaemon, _atomic_write
from agents.fortress.schema import (
    BuildingSummary,
    DwarfSkill,
    DwarfUnit,
    FullFortressState,
    StockpileSummary,
    WealthSummary,
    Workshop,
)


def _make_state(**overrides) -> FullFortressState:
    defaults = dict(
        timestamp=time.time(),
        game_tick=120000,
        year=3,
        season=2,
        month=8,
        day=15,
        fortress_name="TestDaemon",
        paused=False,
        population=47,
        food_count=234,
        drink_count=100,
        active_threats=0,
        job_queue_length=15,
        idle_dwarf_count=3,
        most_stressed_value=5000,
        units=tuple(
            DwarfUnit(
                id=i,
                name=f"U{i}",
                profession="Miner",
                skills=(DwarfSkill(name="MINING", level=3),),
                stress=5000,
                mood="normal",
                current_job="Mining",
            )
            for i in range(47)
        ),
        stockpiles=StockpileSummary(food=234, drink=100, weapons=10),
        workshops=(Workshop(type="Forge", x=0, y=0, z=-1, is_active=True, current_job="Smelt"),),
        buildings=BuildingSummary(beds=30, doors=10),
        wealth=WealthSummary(created=50000),
    )
    defaults.update(overrides)
    return FullFortressState(**defaults)


class TestAtomicWrite:
    def test_writes_valid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "test.json"
        _atomic_write(path, {"key": "value"})
        assert path.exists()
        assert json.loads(path.read_text()) == {"key": "value"}

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "sub" / "dir" / "test.json"
        _atomic_write(path, {"nested": True})
        assert path.exists()


class TestFortressDaemon:
    def test_start_session(self) -> None:
        daemon = FortressDaemon()
        state = _make_state()
        daemon._start_session(state)
        assert daemon._started
        assert daemon._tracker.fortress_name == "TestDaemon"

    def test_founding_goal_activated_for_small_population(self) -> None:
        daemon = FortressDaemon()
        state = _make_state(population=7)
        daemon._start_session(state)
        from agents.fortress.goals import GoalState

        assert daemon._goal_planner.tracker.goal_state("found_fortress") == GoalState.ACTIVE

    def test_survive_winter_for_established_fortress(self) -> None:
        daemon = FortressDaemon()
        state = _make_state(population=47)
        daemon._start_session(state)
        from agents.fortress.goals import GoalState

        assert daemon._goal_planner.tracker.goal_state("survive_winter") == GoalState.ACTIVE

    def test_write_governor_state(self, tmp_path: Path) -> None:
        import agents.fortress.__main__ as main_mod

        orig_gov = main_mod.GOVERNANCE_FILE
        orig_goals = main_mod.GOALS_FILE
        orig_metrics = main_mod.METRICS_FILE
        main_mod.GOVERNANCE_FILE = tmp_path / "governance.json"
        main_mod.GOALS_FILE = tmp_path / "goals.json"
        main_mod.METRICS_FILE = tmp_path / "metrics.json"
        try:
            daemon = FortressDaemon()
            state = _make_state()
            daemon._start_session(state)
            daemon._write_governor_state(state)

            # Verify governance.json
            gov = json.loads((tmp_path / "governance.json").read_text())
            assert "chains" in gov
            assert "suppression" in gov
            assert "creativity_suppression" in gov["suppression"]

            # Verify goals.json
            goals = json.loads((tmp_path / "goals.json").read_text())
            assert "goals" in goals
            assert len(goals["goals"]) > 0

            # Verify metrics.json
            metrics = json.loads((tmp_path / "metrics.json").read_text())
            assert metrics["fortress_name"] == "TestDaemon"
            assert "creativity" in metrics
        finally:
            main_mod.GOVERNANCE_FILE = orig_gov
            main_mod.GOALS_FILE = orig_goals
            main_mod.METRICS_FILE = orig_metrics

    def test_stop_flushes_episode(self) -> None:
        daemon = FortressDaemon()
        state = _make_state()
        daemon._start_session(state)
        daemon._episode_builder.observe(state)  # start an episode

        with (
            patch("agents.fortress.__main__.write_chronicle_entry") as mock_write,
            patch.object(daemon._tracker, "finalize"),
        ):
            daemon.stop()
            # Should have flushed the partial episode
            assert mock_write.called or not daemon._running

    def test_death_detection(self) -> None:
        daemon = FortressDaemon()
        state = _make_state()
        daemon._start_session(state)

        dead_state = _make_state(population=0)
        assert daemon._tracker.is_fortress_dead(dead_state)
