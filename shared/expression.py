"""Cross-modal expression coordination.

When imagination escalates a fragment and the affordance pipeline recruits
multiple modalities (speech + visual), the coordinator ensures they express
the same content — same ImaginationFragment, different media.

Phase 5 of capability parity (queue #021).
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class ExpressionCoordinator:
    """Coordinates expression across modalities for a single impingement.

    When the affordance pipeline recruits both speech and visual capabilities
    for the same impingement, this coordinator distributes the source fragment
    to each recruited capability.
    """

    def __init__(self) -> None:
        self._last_fragment: dict | None = None

    def coordinate(
        self,
        impingement_content: dict,
        recruited: list[tuple[str, Any]],
    ) -> list[dict]:
        """Distribute expression across recruited capabilities.

        Args:
            impingement_content: The impingement's content dict (may contain
                "fragment" key with ImaginationFragment data)
            recruited: List of (capability_name, capability_instance) tuples
                from AffordancePipeline.select()

        Returns:
            List of activation records [{capability, modality, fragment}]
        """
        fragment = impingement_content.get("fragment") or impingement_content.get("narrative")
        if fragment is None:
            return []

        if isinstance(fragment, str):
            fragment = {"narrative": fragment}

        self._last_fragment = fragment
        activations: list[dict] = []

        for name, cap in recruited:
            modality = _infer_modality(name, cap)
            activations.append(
                {
                    "capability": name,
                    "modality": modality,
                    "fragment": fragment,
                }
            )
            log.info(
                "Cross-modal coordination: %s (%s) receives fragment",
                name,
                modality,
            )

        return activations

    @property
    def last_fragment(self) -> dict | None:
        """Most recently coordinated fragment (for debugging)."""
        return self._last_fragment


# ── Dimension mapping for visual expression ──────────────────────────────────

FRAGMENT_TO_SHADER: dict[str, str] = {
    "luminosity": "bloom.alpha",
    "density": "particle.count",
    "velocity": "drift.speed",
    "turbulence": "noise.scale",
    "warmth": "color.temperature",
    "depth": "parallax.layers",
    "rhythm": "stutter.freeze_chance",
    "opacity": "master.alpha",
}

MATERIAL_TO_PRESET: dict[str, str] = {
    "water": "voronoi_crystal",
    "fire": "feedback_preset",
    "earth": "dither",
    "air": "kaleidodream",
    "void": "silhouette",
}


def map_fragment_to_visual(fragment: dict) -> dict[str, float]:
    """Map ImaginationFragment dimensions to shader parameter targets.

    Returns dict of {shader_param: value} for visual modulation.
    """
    dimensions = fragment.get("dimensions", {})
    result: dict[str, float] = {}
    for dim_name, shader_param in FRAGMENT_TO_SHADER.items():
        if dim_name in dimensions:
            result[shader_param] = float(dimensions[dim_name])
    return result


def map_fragment_to_preset(fragment: dict) -> str | None:
    """Map ImaginationFragment material to a preset name."""
    material = fragment.get("material")
    if material and isinstance(material, str):
        return MATERIAL_TO_PRESET.get(material.lower())
    return None


def _infer_modality(name: str, cap: Any) -> str:
    """Infer modality from capability name or category."""
    from shared.capability import CapabilityCategory

    if hasattr(cap, "category"):
        if cap.category == CapabilityCategory.EXPRESSION:
            if "speech" in name or "voice" in name:
                return "speech"
            if "shader" in name or "visual" in name:
                return "visual"
            return "expression"
    return "unknown"
