"""Satellite recruitment state management for the Reverie mixer.

Tracks which shader nodes are recruited, handles decay/dismissal,
and triggers graph rebuilds when the set changes.
"""

from __future__ import annotations

import logging
import time

from agents.effect_graph.wgsl_compiler import compile_to_wgsl_plan, write_wgsl_pipeline
from agents.reverie._graph_builder import build_graph

log = logging.getLogger("reverie.satellites")

RECRUITMENT_THRESHOLD = 0.3
DISMISSAL_THRESHOLD = 0.05
REBUILD_COOLDOWN_S = 2.0


class SatelliteManager:
    """Manages satellite node recruitment, decay, and graph rebuilds."""

    def __init__(self, core_vocab: dict, decay_rate: float = 0.02) -> None:
        self._core_vocab = core_vocab
        self._decay_rate = decay_rate
        self._recruited: dict[str, float] = {}
        self._active_set: frozenset[str] = frozenset()
        self._last_rebuild = 0.0

    @property
    def recruited(self) -> dict[str, float]:
        return dict(self._recruited)

    @property
    def active_count(self) -> int:
        return len(self._recruited)

    def recruit(self, node_type: str, strength: float) -> None:
        """Recruit a satellite node (or boost its strength if already recruited)."""
        if strength < RECRUITMENT_THRESHOLD:
            return
        prev = self._recruited.get(node_type, 0.0)
        self._recruited[node_type] = max(prev, strength)
        if node_type not in self._active_set:
            log.info("Satellite recruited: %s (strength=%.2f)", node_type, strength)

    def decay(self, dt: float) -> None:
        """Decay all satellite strengths, dismiss below threshold."""
        for node_type in list(self._recruited):
            self._recruited[node_type] -= self._decay_rate * dt
            if self._recruited[node_type] < DISMISSAL_THRESHOLD:
                del self._recruited[node_type]
                log.info("Satellite dismissed: %s", node_type)

    def maybe_rebuild(self) -> bool:
        """Rebuild the shader graph if the recruited set changed. Returns True if rebuilt."""
        current_set = frozenset(self._recruited.keys())
        if current_set == self._active_set:
            return False

        now = time.monotonic()
        if now - self._last_rebuild < REBUILD_COOLDOWN_S:
            return False

        graph = build_graph(self._core_vocab, self._recruited)
        plan = compile_to_wgsl_plan(graph)
        write_wgsl_pipeline(plan)

        pass_count = len(plan.get("passes", []))
        log.info(
            "Graph rebuilt: %d passes (%d satellites: %s)",
            pass_count,
            len(self._recruited),
            ", ".join(sorted(self._recruited.keys())) or "none",
        )

        self._active_set = current_set
        self._last_rebuild = now
        return True
