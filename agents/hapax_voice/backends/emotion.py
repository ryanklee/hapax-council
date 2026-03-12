"""Emotion perception backend — valence, arousal, and dominant emotion.

Stub backend: reserves behavior names and proves the protocol.
Actual implementation requires audio/video emotion model inference.

Supports source parameterization: ``EmotionBackend("face_cam")`` writes
to ``emotion_valence:face_cam`` instead of ``emotion_valence``.
"""

from __future__ import annotations

import logging

from agents.hapax_voice.perception import PerceptionTier
from agents.hapax_voice.primitives import Behavior
from agents.hapax_voice.source_naming import qualify, validate_source_id

log = logging.getLogger(__name__)

_BASE_NAMES = ("emotion_valence", "emotion_arousal", "emotion_dominant")


class EmotionBackend:
    """PerceptionBackend for emotion analysis.

    Provides:
      - emotion_valence: float (-1.0 to 1.0)
      - emotion_arousal: float (0.0 to 1.0)
      - emotion_dominant: str (e.g. "neutral", "happy", "tense")

    When ``source_id`` is provided, all behavior names are source-qualified.
    """

    def __init__(self, source_id: str | None = None) -> None:
        if source_id is not None:
            validate_source_id(source_id)
        self._source_id = source_id

    @property
    def name(self) -> str:
        if self._source_id:
            return f"emotion:{self._source_id}"
        return "emotion"

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
        log.info("Emotion backend started (stub): %s", self.name)

    def stop(self) -> None:
        log.info("Emotion backend stopped (stub): %s", self.name)
