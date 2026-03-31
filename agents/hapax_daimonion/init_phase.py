"""Init phase tracking for daemon startup."""

from __future__ import annotations

import enum

__all__ = ["InitPhase"]


class InitPhase(enum.Enum):
    """Tracks which initialization phases completed successfully."""

    CORE = "core"
    PERCEPTION = "perception"
    STATE = "state"
    VOICE = "voice"
    ACTUATION = "actuation"
