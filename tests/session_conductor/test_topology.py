"""Tests for workspace topology config loader."""

from __future__ import annotations

from pathlib import Path

import yaml

from agents.session_conductor.topology import load_topology


def test_load_topology_from_file(tmp_path: Path):
    config_path = tmp_path / "workspace-topology.yaml"
    data = {
        "monitors": [{"name": "DP-1", "width": 2560, "height": 1440}],
        "workspaces": [
            {"id": 1, "name": "main", "monitor": "DP-1"},
            {"id": 10, "name": "testing", "monitor": "HDMI-1"},
        ],
        "playwright": {
            "testing_workspace": 10,
            "screenshot_max_bytes": 400000,
            "never_switch_operator_focus": True,
        },
        "smoke_test": {
            "workspace": 10,
            "fullscreen": True,
            "launch_method": "fuzzel",
            "screenshot_interval_ms": 2000,
        },
    }
    config_path.write_text(yaml.dump(data))

    topology = load_topology(config_path)
    assert len(topology.monitors) == 1
    assert topology.monitors[0].name == "DP-1"
    assert len(topology.workspaces) == 2
    assert topology.playwright.testing_workspace == 10
    assert topology.playwright.screenshot_max_bytes == 400000
    assert topology.smoke_test.workspace == 10
    assert topology.smoke_test.launch_method == "fuzzel"


def test_missing_file_defaults(tmp_path: Path):
    topology = load_topology(tmp_path / "nonexistent.yaml")
    assert topology.playwright.testing_workspace == 10
    assert topology.playwright.screenshot_max_bytes == 500000
    assert topology.playwright.never_switch_operator_focus is True
    assert topology.smoke_test.workspace == 10
    assert topology.smoke_test.fullscreen is True
    assert topology.smoke_test.launch_method == "fuzzel"
    assert topology.smoke_test.screenshot_interval_ms == 2000


def test_get_workspace_monitor(tmp_path: Path):
    config_path = tmp_path / "workspace-topology.yaml"
    data = {
        "workspaces": [
            {"id": 1, "name": "main", "monitor": "DP-1"},
            {"id": 10, "name": "testing", "monitor": "HDMI-1"},
        ],
    }
    config_path.write_text(yaml.dump(data))
    topology = load_topology(config_path)
    assert topology.get_workspace_monitor(1) == "DP-1"
    assert topology.get_workspace_monitor(10) == "HDMI-1"
    assert topology.get_workspace_monitor(99) is None
