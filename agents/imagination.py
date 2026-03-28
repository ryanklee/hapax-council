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


# ---------------------------------------------------------------------------
# SHM publisher
# ---------------------------------------------------------------------------


def publish_fragment(
    fragment: ImaginationFragment,
    current_path: Path | None = None,
    stream_path: Path | None = None,
    max_lines: int = STREAM_MAX_LINES,
) -> None:
    """Publish a fragment to shared memory (atomic write + append stream)."""
    if current_path is None:
        current_path = CURRENT_PATH
    if stream_path is None:
        stream_path = STREAM_PATH

    current_path = Path(current_path)
    stream_path = Path(stream_path)

    # Ensure directories exist
    current_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.parent.mkdir(parents=True, exist_ok=True)

    payload = fragment.model_dump_json()

    # Atomic write to current.json via tmp+rename
    tmp_path = current_path.with_suffix(".tmp")
    tmp_path.write_text(payload)
    tmp_path.rename(current_path)

    # Append to stream.jsonl
    with stream_path.open("a") as f:
        f.write(payload + "\n")

    # Cap stream at max_lines
    lines = stream_path.read_text().splitlines()
    if len(lines) > max_lines:
        stream_path.write_text("\n".join(lines[-max_lines:]) + "\n")
