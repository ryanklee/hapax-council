"""Imagination bus — fragment publishing and escalation to impingement cascade.

Produces ImaginationFragments: medium-agnostic creative signals with
content references, expressive dimensions, and salience scoring.
High-salience fragments escalate into Impingements for capability recruitment.
"""

from __future__ import annotations

import logging
import time as time_mod
import uuid
from pathlib import Path

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHM_DIR = Path("/dev/shm/hapax-imagination")
CURRENT_PATH = SHM_DIR / "current.json"
STREAM_PATH = SHM_DIR / "stream.jsonl"
STREAM_MAX_LINES = 50
ESCALATION_THRESHOLD = 0.6


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class ContentReference(BaseModel, frozen=True):
    """A reference to source material feeding an imagination fragment."""

    kind: str  # "qdrant_query", "camera_frame", "text", "url", "file", "audio_clip"
    source: str
    query: str | None = None
    salience: float = Field(ge=0.0, le=1.0)


class ImaginationFragment(BaseModel, frozen=True):
    """A single imagination output — medium-agnostic creative signal."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = Field(default_factory=time_mod.time)
    content_references: list[ContentReference]
    dimensions: dict[str, float]  # 9 expressive dimensions, medium-agnostic
    salience: float = Field(ge=0.0, le=1.0)
    continuation: bool
    narrative: str
    parent_id: str | None = None
