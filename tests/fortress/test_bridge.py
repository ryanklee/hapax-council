"""Tests for DFHack bridge — file-based communication."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from agents.fortress.bridge import DFHackBridge
from agents.fortress.config import BridgeConfig
from agents.fortress.schema import FastFortressState, SiegeEvent


@pytest.fixture
def tmp_bridge(tmp_path: Path) -> tuple[DFHackBridge, Path]:
    """Create a bridge with state dir pointing to tmp_path."""
    config = BridgeConfig(state_dir=tmp_path)
    bridge = DFHackBridge(config=config)
    return bridge, tmp_path


def _write_state(path: Path, **overrides: object) -> None:
    """Write a minimal valid state.json."""
    state = {
        "timestamp": time.time(),
        "game_tick": 120000,
        "year": 3,
        "season": 2,
        "month": 8,
        "day": 15,
        "fortress_name": "TestFort",
        "paused": False,
        "population": 47,
        "food_count": 234,
        "drink_count": 100,
        "active_threats": 0,
        "job_queue_length": 15,
        "idle_dwarf_count": 3,
        "most_stressed_value": 5000,
        "pending_events": [],
    }
    state.update(overrides)
    (path / "state.json").write_text(json.dumps(state))


class TestReadState:
    def test_reads_fast_state(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, path = tmp_bridge
        _write_state(path)
        state = bridge.read_state()
        assert state is not None
        assert isinstance(state, FastFortressState)
        assert state.fortress_name == "TestFort"
        assert state.population == 47

    def test_no_file_returns_none(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, _ = tmp_bridge
        assert bridge.read_state() is None

    def test_stale_file_returns_last_known(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, path = tmp_bridge
        _write_state(path)

        # First read: succeeds
        state = bridge.read_state()
        assert state is not None

        # Make file stale
        import os

        state_file = path / "state.json"
        old_time = time.time() - 60
        os.utime(state_file, (old_time, old_time))

        # Second read: returns last known state (not None)
        state2 = bridge.read_state()
        assert state2 is not None
        assert state2.fortress_name == "TestFort"

    def test_invalid_json_returns_last_known(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, path = tmp_bridge
        _write_state(path)
        bridge.read_state()  # cache a valid state

        (path / "state.json").write_text("not valid json{{{")
        state = bridge.read_state()
        assert state is not None  # returns cached

    def test_detects_full_state(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, path = tmp_bridge
        _write_state(
            path,
            units=[
                {
                    "id": 1,
                    "name": "Urist",
                    "profession": "Miner",
                    "skills": [],
                    "stress": 0,
                    "mood": "normal",
                    "current_job": "idle",
                    "military_squad_id": None,
                }
            ],
        )
        state = bridge.read_state()
        assert state is not None
        from agents.fortress.schema import FullFortressState

        assert isinstance(state, FullFortressState)

    def test_events_parsed(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, path = tmp_bridge
        _write_state(
            path,
            pending_events=[
                {"type": "siege", "attacker_civ": "Goblins", "force_size": 30},
            ],
        )
        state = bridge.read_state()
        assert state is not None
        assert len(state.pending_events) == 1
        assert state.pending_events[0].type == "siege"


class TestIsActive:
    def test_no_file_is_inactive(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, _ = tmp_bridge
        assert bridge.is_active is False

    def test_fresh_file_is_active(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, path = tmp_bridge
        _write_state(path)
        assert bridge.is_active is True

    def test_stale_file_is_inactive(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, path = tmp_bridge
        _write_state(path)
        import os

        state_file = path / "state.json"
        old_time = time.time() - 60
        os.utime(state_file, (old_time, old_time))
        assert bridge.is_active is False


class TestSendCommand:
    def test_writes_command_file(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, path = tmp_bridge
        cmd_id = bridge.send_command("pause", state=True)
        assert len(cmd_id) == 12

        cmds_file = path / "commands.json"
        assert cmds_file.exists()
        cmds = json.loads(cmds_file.read_text())
        assert len(cmds) == 1
        assert cmds[0]["id"] == cmd_id
        assert cmds[0]["action"] == "pause"

    def test_appends_to_existing(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, path = tmp_bridge
        bridge.send_command("pause", state=True)
        bridge.send_command("save")

        cmds = json.loads((path / "commands.json").read_text())
        assert len(cmds) == 2
        assert cmds[0]["action"] == "pause"
        assert cmds[1]["action"] == "save"

    def test_unique_ids(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, _ = tmp_bridge
        id1 = bridge.send_command("pause")
        id2 = bridge.send_command("save")
        assert id1 != id2


class TestPollResults:
    def test_no_file_returns_empty(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, _ = tmp_bridge
        assert bridge.poll_results() == {}

    def test_reads_and_clears(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, path = tmp_bridge
        results = {"abc123": {"success": True}, "def456": {"success": False, "error": "oops"}}
        (path / "results.json").write_text(json.dumps(results))

        got = bridge.poll_results()
        assert got["abc123"]["success"] is True
        assert got["def456"]["success"] is False

        # File should be deleted
        assert not (path / "results.json").exists()


class TestExtractEvents:
    def test_empty_state(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, _ = tmp_bridge
        assert bridge.extract_events(None) == []

    def test_with_events(self, tmp_bridge: tuple[DFHackBridge, Path]):
        bridge, _ = tmp_bridge
        state = FastFortressState(
            timestamp=0.0,
            game_tick=0,
            year=0,
            season=0,
            month=0,
            day=0,
            fortress_name="Test",
            paused=False,
            population=0,
            food_count=0,
            drink_count=0,
            active_threats=0,
            job_queue_length=0,
            idle_dwarf_count=0,
            most_stressed_value=0,
            pending_events=(SiegeEvent(attacker_civ="Goblins", force_size=20),),
        )
        events = bridge.extract_events(state)
        assert len(events) == 1
        assert events[0].type == "siege"
