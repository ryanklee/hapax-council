"""Workspace topology configuration loader."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

DEFAULT_TOPOLOGY_PATH = Path.home() / ".config" / "hapax" / "workspace-topology.yaml"


@dataclass
class MonitorConfig:
    name: str
    width: int = 0
    height: int = 0


@dataclass
class WorkspaceConfig:
    id: int
    name: str
    monitor: str = ""


@dataclass
class PlaywrightConfig:
    testing_workspace: int = 10
    screenshot_max_bytes: int = 500000
    never_switch_operator_focus: bool = True


@dataclass
class SmokeTestConfig:
    workspace: int = 10
    fullscreen: bool = True
    launch_method: str = "fuzzel"
    screenshot_interval_ms: int = 2000


@dataclass
class TopologyConfig:
    monitors: list[MonitorConfig] = field(default_factory=list)
    workspaces: list[WorkspaceConfig] = field(default_factory=list)
    playwright: PlaywrightConfig = field(default_factory=PlaywrightConfig)
    smoke_test: SmokeTestConfig = field(default_factory=SmokeTestConfig)

    def get_workspace_monitor(self, workspace: int) -> str | None:
        """Return the monitor name for the given workspace id, or None if not found."""
        for ws in self.workspaces:
            if ws.id == workspace:
                return ws.monitor or None
        return None


def load_topology(path: Path | None = None) -> TopologyConfig:
    """Load topology config from YAML file. Returns defaults if file is missing."""
    config_path = path if path is not None else DEFAULT_TOPOLOGY_PATH

    if not config_path.exists():
        log.debug("Topology config not found at %s; using defaults", config_path)
        return TopologyConfig()

    try:
        raw = yaml.safe_load(config_path.read_text()) or {}
    except Exception:
        log.exception("Failed to parse topology config at %s; using defaults", config_path)
        return TopologyConfig()

    monitors = [
        MonitorConfig(
            name=m["name"],
            width=m.get("width", 0),
            height=m.get("height", 0),
        )
        for m in raw.get("monitors", [])
    ]

    workspaces = [
        WorkspaceConfig(
            id=w["id"],
            name=w.get("name", ""),
            monitor=w.get("monitor", ""),
        )
        for w in raw.get("workspaces", [])
    ]

    pw_raw = raw.get("playwright", {})
    playwright = PlaywrightConfig(
        testing_workspace=pw_raw.get("testing_workspace", 10),
        screenshot_max_bytes=pw_raw.get("screenshot_max_bytes", 500000),
        never_switch_operator_focus=pw_raw.get("never_switch_operator_focus", True),
    )

    st_raw = raw.get("smoke_test", {})
    smoke_test = SmokeTestConfig(
        workspace=st_raw.get("workspace", 10),
        fullscreen=st_raw.get("fullscreen", True),
        launch_method=st_raw.get("launch_method", "fuzzel"),
        screenshot_interval_ms=st_raw.get("screenshot_interval_ms", 2000),
    )

    return TopologyConfig(
        monitors=monitors,
        workspaces=workspaces,
        playwright=playwright,
        smoke_test=smoke_test,
    )
