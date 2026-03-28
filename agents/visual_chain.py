"""Visual chain capability — semantic visual affordances for wgpu shader modulation.

Nine expressive dimensions (same as vocal chain) mapped to wgpu technique
uniforms instead of MIDI CCs. Registered in Qdrant for cross-modal
impingement activation alongside vocal_chain.*.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

SHM_PATH = Path("/dev/shm/hapax-visual/visual-chain-state.json")


@dataclass(frozen=True)
class ParameterMapping:
    """Maps an activation level to a specific wgpu technique uniform."""

    technique: str  # "gradient", "rd", "physarum", "compositor", "postprocess"
    param: str  # uniform name
    breakpoints: list[tuple[float, float]]  # (level, param_value)


@dataclass(frozen=True)
class VisualDimension:
    """A semantic visual modulation dimension."""

    name: str
    description: str
    parameter_mappings: list[ParameterMapping]


def param_value_from_level(level: float, breakpoints: list[tuple[float, float]]) -> float:
    """Interpolate parameter value from activation level using piecewise linear breakpoints."""
    level = max(0.0, min(1.0, level))
    if level <= breakpoints[0][0]:
        return breakpoints[0][1]
    if level >= breakpoints[-1][0]:
        return breakpoints[-1][1]
    for i in range(len(breakpoints) - 1):
        l0, v0 = breakpoints[i]
        l1, v1 = breakpoints[i + 1]
        if l0 <= level <= l1:
            t = (level - l0) / (l1 - l0) if l1 != l0 else 0.0
            return v0 + t * (v1 - v0)
    return breakpoints[-1][1]
