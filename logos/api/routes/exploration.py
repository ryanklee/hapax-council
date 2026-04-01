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

    boredom_scores = [s.get("boredom_index", 0.0) for s in signals.values()]
    curiosity_scores = [s.get("curiosity_index", 0.0) for s in signals.values()]
    agg_boredom = sum(boredom_scores) / len(boredom_scores)
    agg_curiosity = sum(curiosity_scores) / len(curiosity_scores)
    deficit = max(0.0, min(1.0, agg_boredom - agg_curiosity))

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
