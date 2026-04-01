"""Tests for exploration API endpoint."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from shared.exploration import ExplorationSignal
from shared.exploration_writer import publish_exploration_signal

try:
    import fastapi  # noqa: F401

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")


def _make_signal(component: str, boredom: float = 0.5, curiosity: float = 0.3) -> ExplorationSignal:
    return ExplorationSignal(
        component=component,
        timestamp=1000.0,
        mean_habituation=boredom,
        max_novelty_edge="test",
        max_novelty_score=curiosity,
        error_improvement_rate=0.0,
        chronic_error=0.0,
        mean_trace_interest=1.0 - boredom,
        stagnation_duration=0.0,
        local_coherence=0.5,
        dwell_time_in_coherence=0.0,
        boredom_index=boredom,
        curiosity_index=curiosity,
    )


class TestExplorationRoute:
    def test_get_exploration_empty(self) -> None:
        from logos.api.routes.exploration import get_exploration_state

        with patch("logos.api.routes.exploration._reader") as mock_reader:
            mock_reader.read_all.return_value = {}
            result = get_exploration_state()
        assert result["aggregate"]["exploration_deficit"] == 0.0
        assert result["components"] == {}

    def test_get_exploration_with_signals(self, tmp_path: Path) -> None:
        from shared.exploration_writer import ExplorationReader

        publish_exploration_signal(_make_signal("a", 0.6, 0.2), shm_root=tmp_path)
        publish_exploration_signal(_make_signal("b", 0.4, 0.3), shm_root=tmp_path)

        reader = ExplorationReader(shm_root=tmp_path)
        signals = reader.read_all()
        assert len(signals) == 2

        boredom_scores = [s["boredom_index"] for s in signals.values()]
        curiosity_scores = [s["curiosity_index"] for s in signals.values()]
        agg_boredom = sum(boredom_scores) / len(boredom_scores)
        agg_curiosity = sum(curiosity_scores) / len(curiosity_scores)
        deficit = max(0.0, agg_boredom - agg_curiosity)
        assert deficit > 0  # boredom > curiosity

    def test_get_component_missing(self) -> None:
        from logos.api.routes.exploration import get_component_exploration

        with patch("logos.api.routes.exploration._reader") as mock_reader:
            mock_reader.read.return_value = None
            mock_reader.read_all.return_value = {"a": {}, "b": {}}
            result = get_component_exploration("nonexistent")
        assert "error" in result

    def test_get_component_found(self) -> None:
        from logos.api.routes.exploration import get_component_exploration

        with patch("logos.api.routes.exploration._reader") as mock_reader:
            mock_reader.read.return_value = {"component": "dmn_pulse", "boredom_index": 0.42}
            result = get_component_exploration("dmn_pulse")
        assert result["component"] == "dmn_pulse"
