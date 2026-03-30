"""Vendored sensor protocol for the agents package.

Sensor backend protocol -- self-modulating data acquisition with impingement emission.
Sensors write atomic state snapshots to /dev/shm/hapax-sensors/ and emit
impingements to the cross-daemon JSONL transport on state change.
"""

from __future__ import annotations

import json
import logging
import time
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from shared.impingement import Impingement, ImpingementType

log = logging.getLogger("sensor")

SENSOR_SHM_DIR = Path("/dev/shm/hapax-sensors")
IMPINGEMENTS_FILE = Path("/dev/shm/hapax-dmn/impingements.jsonl")


class SensorTier(StrEnum):
    """Sensor update frequency tier."""

    FAST = "fast"
    MODERATE = "moderate"
    SLOW = "slow"
    EVENT = "event"


@runtime_checkable
class SensorBackend(Protocol):
    """Protocol for pluggable data sensors."""

    @property
    def name(self) -> str: ...

    @property
    def provides(self) -> frozenset[str]: ...

    @property
    def tier(self) -> SensorTier: ...

    def available(self) -> bool: ...

    def poll(self) -> dict[str, Any] | None: ...


def write_sensor_state(sensor_name: str, state: dict[str, Any]) -> None:
    """Write atomic state snapshot to /dev/shm for DMN consumption."""
    SENSOR_SHM_DIR.mkdir(parents=True, exist_ok=True)
    path = SENSOR_SHM_DIR / f"{sensor_name}.json"
    try:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state), encoding="utf-8")
        tmp.rename(path)
    except OSError:
        log.debug("Failed to write sensor state for %s", sensor_name)


def emit_sensor_impingement(
    sensor_name: str,
    dimension: str,
    changed_keys: list[str],
    strength: float = 0.3,
) -> None:
    """Emit a low-strength impingement for a sensor data change."""
    imp = Impingement(
        timestamp=time.time(),
        source=f"sensor.{sensor_name}",
        type=ImpingementType.PATTERN_MATCH,
        strength=strength,
        content={
            "metric": "profile_dimension_updated",
            "dimension": dimension,
            "keys": changed_keys,
            "sensor": sensor_name,
        },
        interrupt_token="profile_dimension_updated",
    )

    try:
        from agents._config import embed_safe
        from shared.impingement import render_impingement_text

        text = render_impingement_text(imp)
        vec = embed_safe(text, prefix="search_query")
        if vec is not None:
            imp = imp.model_copy(update={"embedding": vec})
    except Exception:
        pass

    try:
        IMPINGEMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with IMPINGEMENTS_FILE.open("a", encoding="utf-8") as f:
            f.write(imp.model_dump_json() + "\n")
    except OSError:
        log.debug("Failed to emit sensor impingement for %s", sensor_name)
