"""Audio energy perception backend — RMS energy and onset detection.

Stub backend: reserves behavior names and proves the protocol.
Actual implementation requires real-time audio analysis.

Supports source parameterization: ``AudioEnergyBackend("monitor_mix")`` writes
to ``audio_energy_rms:monitor_mix`` instead of ``audio_energy_rms``.
"""

from __future__ import annotations

import logging

from agents.hapax_voice.perception import PerceptionTier
from agents.hapax_voice.primitives import Behavior
from agents.hapax_voice.source_naming import qualify, validate_source_id

log = logging.getLogger(__name__)

_BASE_NAMES = ("audio_energy_rms", "audio_onset")


class AudioEnergyBackend:
    """PerceptionBackend for audio energy analysis.

    Provides:
      - audio_energy_rms: float (0.0-1.0, current RMS energy)
      - audio_onset: bool (True on transient onset detection)

    When ``source_id`` is provided, all behavior names are source-qualified.
    """

    def __init__(self, source_id: str | None = None) -> None:
        if source_id is not None:
            validate_source_id(source_id)
        self._source_id = source_id

    @property
    def name(self) -> str:
        if self._source_id:
            return f"audio_energy:{self._source_id}"
        return "audio_energy"

    @property
    def provides(self) -> frozenset[str]:
        if self._source_id:
            return frozenset(qualify(b, self._source_id) for b in _BASE_NAMES)
        return frozenset(_BASE_NAMES)

    @property
    def tier(self) -> PerceptionTier:
        return PerceptionTier.FAST

    def available(self) -> bool:
        return False

    def contribute(self, behaviors: dict[str, Behavior]) -> None:
        pass

    def start(self) -> None:
        log.info("AudioEnergy backend started (stub): %s", self.name)

    def stop(self) -> None:
        log.info("AudioEnergy backend stopped (stub): %s", self.name)
