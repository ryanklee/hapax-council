"""Fortress configuration — bridge paths, poll intervals, governance defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class BridgeConfig:
    """DFHack bridge file paths and polling intervals."""

    state_dir: Path = field(default_factory=lambda: Path("/dev/shm/hapax-df"))
    state_file: str = "state.json"
    commands_file: str = "commands.json"
    results_file: str = "results.json"
    staleness_threshold_s: float = 30.0

    @property
    def state_path(self) -> Path:
        return self.state_dir / self.state_file

    @property
    def commands_path(self) -> Path:
        return self.state_dir / self.commands_file

    @property
    def results_path(self) -> Path:
        return self.state_dir / self.results_file


@dataclass(frozen=True)
class SuppressionConfig:
    """Default suppression field timing parameters."""

    crisis_attack_s: float = 0.1
    crisis_release_s: float = 5.0
    military_attack_s: float = 0.5
    military_release_s: float = 3.0
    resource_attack_s: float = 1.0
    resource_release_s: float = 2.0
    planner_attack_s: float = 0.3
    planner_release_s: float = 0.5
    suppression_floor: float = 0.0
    suppression_ceiling: float = 0.95


@dataclass(frozen=True)
class FortressConfig:
    """Top-level fortress agent configuration."""

    bridge: BridgeConfig = field(default_factory=BridgeConfig)
    suppression: SuppressionConfig = field(default_factory=SuppressionConfig)
    min_population_for_military: int = 10
    food_critical_threshold: int = 10  # per capita
    drink_critical_threshold: int = 5  # per capita
    recovery_cooldown_ticks: int = 2400  # 2 days
