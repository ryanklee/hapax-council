"""Aggregate mesh-wide health from per-component control signals.

Reads /dev/shm/hapax-*/health.json files and computes E_mesh
(mean control error across all fresh components).
"""

from __future__ import annotations

import json
import time
from pathlib import Path


def aggregate_mesh_health(*, shm_root: Path = Path("/dev/shm"), stale_s: float = 120.0) -> dict:
    """Compute mesh-wide health from component health files.

    Returns dict with:
    - e_mesh: mean control error across fresh components
    - component_count: number of fresh components reporting
    - worst_component: component name with highest error
    - components: dict of component -> error
    """
    components: dict[str, float] = {}
    now = time.time()

    for health_file in sorted(shm_root.glob("hapax-*/health.json")):
        try:
            data = json.loads(health_file.read_text(encoding="utf-8"))
            ts = data.get("timestamp", 0)
            if now - ts > stale_s:
                continue
            components[data["component"]] = data["error"]
        except (OSError, json.JSONDecodeError, KeyError):
            continue

    if not components:
        return {
            "e_mesh": 1.0,
            "component_count": 0,
            "worst_component": "none",
            "components": {},
        }

    e_mesh = sum(components.values()) / len(components)
    worst = max(components, key=components.get)  # type: ignore[arg-type]

    return {
        "e_mesh": e_mesh,
        "component_count": len(components),
        "worst_component": worst,
        "components": components,
    }
