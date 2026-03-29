"""Stimmung state endpoint for the Hapax Obsidian plugin v2."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/stimmung", tags=["stimmung"])

_SHM_STATE = Path("/dev/shm/hapax-stimmung/state.json")

_DIMENSION_KEYS = [
    "health",
    "resource_pressure",
    "error_rate",
    "processing_throughput",
    "perception_confidence",
    "llm_cost_pressure",
    "grounding_quality",
    "operator_stress",
    "operator_energy",
    "physiological_coherence",
]


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _build_dimensions(raw: dict) -> dict[str, dict]:
    """Build structured dimension objects from flat stimmung state keys."""
    dimensions: dict[str, dict] = {}
    for key in _DIMENSION_KEYS:
        value = raw.get(key, 0.0)
        trend = raw.get(f"{key}_trend", "stable")
        dimensions[key] = {"value": value, "trend": trend}
    return dimensions


@router.get("")
async def get_stimmung() -> dict:
    """Return structured stimmung state from /dev/shm/hapax-stimmung/state.json."""
    raw = _read_json(_SHM_STATE)
    if raw is None:
        return {"overall_stance": "unknown", "dimensions": {}, "timestamp": 0}

    dimensions = _build_dimensions(raw)
    overall_stance = raw.get("overall_stance", "unknown")
    timestamp = raw.get("timestamp", 0)

    return {
        "dimensions": dimensions,
        "overall_stance": overall_stance,
        "timestamp": timestamp,
    }
