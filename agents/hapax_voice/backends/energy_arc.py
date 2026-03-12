"""Energy arc perception backend — macro energy trajectory of a session.

Stub backend: reserves behavior names and proves the protocol.
Actual implementation requires windowed energy analysis over the session timeline.

Supports source parameterization: ``EnergyArcBackend("monitor_mix")`` writes
to ``energy_arc_phase:monitor_mix`` instead of ``energy_arc_phase``.
"""

from __future__ import annotations

import logging

from agents.hapax_voice.perception import PerceptionTier
from agents.hapax_voice.primitives import Behavior
from agents.hapax_voice.source_naming import qualify, validate_source_id

log = logging.getLogger(__name__)

_BASE_NAMES = ("energy_arc_phase", "energy_arc_intensity")


class EnergyArcBackend:
    """PerceptionBackend for energy arc analysis.

    Provides:
      - energy_arc_phase: str (e.g. "building", "peak", "declining", "rest")
      - energy_arc_intensity: float (0.0-1.0)

    When ``source_id`` is provided, all behavior names are source-qualified.
    """

    def __init__(self, source_id: str | None = None) -> None:
        if source_id is not None:
            validate_source_id(source_id)
        self._source_id = source_id

    @property
    def name(self) -> str:
        if self._source_id:
            return f"energy_arc:{self._source_id}"
        return "energy_arc"

    @property
    def provides(self) -> frozenset[str]:
        if self._source_id:
            return frozenset(qualify(b, self._source_id) for b in _BASE_NAMES)
        return frozenset(_BASE_NAMES)

    @property
    def tier(self) -> PerceptionTier:
        return PerceptionTier.SLOW

    def available(self) -> bool:
        return False

    def contribute(self, behaviors: dict[str, Behavior]) -> None:
        pass

    def start(self) -> None:
        log.info("EnergyArc backend started (stub): %s", self.name)

    def stop(self) -> None:
        log.info("EnergyArc backend stopped (stub): %s", self.name)
