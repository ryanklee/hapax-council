"""Exploration signal observability endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter

from shared.exploration_writer import ExplorationReader

router = APIRouter(prefix="/api/exploration", tags=["exploration"])

_reader = ExplorationReader()


@router.get("")
def get_exploration_state() -> dict:
    """Return all component ExplorationSignals + system aggregates."""
    signals = _reader.read_all()
    if not signals:
        return {
            "components": {},
            "aggregate": {
                "boredom": 0.0,
                "curiosity": 0.0,
                "exploration_deficit": 0.0,
                "seeking": False,
            },
            "timestamp": time.time(),
        }

    boredom_scores = sorted(
        (s.get("boredom_index", 0.0) for s in signals.values()),
        reverse=True,
    )
    curiosity_scores = [s.get("curiosity_index", 0.0) for s in signals.values()]
    # Top-k aggregation: worst-case components drive deficit
    # PCT: reorganization pressure = intrinsic error (boredom)
    # Curiosity modulates exploration MODE (via control law), not deficit magnitude
    k = max(3, len(boredom_scores) // 3)
    agg_boredom = sum(boredom_scores[:k]) / k
    agg_curiosity = sum(curiosity_scores) / len(curiosity_scores)
    deficit = max(0.0, min(1.0, agg_boredom))

    return {
        "components": signals,
        "aggregate": {
            "boredom": round(agg_boredom, 4),
            "curiosity": round(agg_curiosity, 4),
            "exploration_deficit": round(deficit, 4),
            "seeking": deficit > 0.35,
            "component_count": len(signals),
        },
        "timestamp": time.time(),
    }


@router.get("/{component}")
def get_component_exploration(component: str) -> dict:
    """Return ExplorationSignal for a single component."""
    sig = _reader.read(component)
    if sig is None:
        return {
            "error": f"No exploration signal for '{component}'",
            "available": list(_reader.read_all().keys()),
        }
    return sig
