"""CBIP (Chess Boxing Interpretive Plane) — album ward enhancement system.

Spec: ``docs/superpowers/specs/2026-04-21-cbip-phase-1-design.md``.
Concept: ``docs/research/2026-04-20-cbip-1-name-cultural-lineage.md``.
Enhancement families: ``docs/research/2026-04-20-cbip-vinyl-enhancement-research.md``.

Phase 0 (PR #1112) — deterministic per-album hash tint, foundation.
Phase 1 (this module) — first two enhancement families + intensity router
+ override surface + recognizability harness + Ring-2 pre-render gate.
"""

from agents.studio_compositor.cbip.intensity_router import (
    DEGRADED_COHERENCE_THRESHOLD,
    CbipIntensity,
    intensity_for_stimmung,
    resolve_effective_intensity,
)
from agents.studio_compositor.cbip.override import (
    DEFAULT_OVERRIDE_PATH,
    OverrideValue,
    read_override,
    write_override,
)

__all__ = [
    "DEFAULT_OVERRIDE_PATH",
    "DEGRADED_COHERENCE_THRESHOLD",
    "CbipIntensity",
    "OverrideValue",
    "intensity_for_stimmung",
    "read_override",
    "resolve_effective_intensity",
    "write_override",
]
