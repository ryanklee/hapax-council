"""Z-plane depth constants for ward stratification.

Five semantic depth categories layer wards in a notional fishbowl
(scrim spatial design at ``docs/research/2026-04-20-nebulous-scrim-design.md``).
The default ``"on-scrim"`` is the legibility plane and renders without
visible attenuation; deeper planes attenuate via :func:`fx_chain.blit_with_depth`.

Kept as a separate module to avoid a circular import between
:mod:`fx_chain` and :mod:`ward_properties`.
"""

from __future__ import annotations

from typing import Final

# Per-plane base depth in [0.0 far, 1.0 near]. The blit path combines this
# base with the modulator-written ``z_index_float`` to produce an effective
# depth that drives opacity attenuation.
_Z_INDEX_BASE: Final[dict[str, float]] = {
    "beyond-scrim": 0.2,
    "mid-scrim": 0.5,
    "on-scrim": 0.9,
    "surface-scrim": 1.0,
}

DEFAULT_Z_PLANE: Final[str] = "on-scrim"
DEFAULT_Z_INDEX_FLOAT: Final[float] = 0.5

# Per-ward initial z-plane assignments (spec §4 taxonomy at
# ``docs/superpowers/specs/2026-04-21-ward-stimmung-modulator-design.md``).
# These apply only when no ward override exists yet — director
# ``placement_bias`` and explicit recruitment metadata still take
# precedence (spec §7). Wards not listed here resolve to the default
# ``"on-scrim"`` plane.
#
# - ``surface-scrim`` (foreground, opacity ≈ 1.0): always-legible chrome
#   that must read clearly even under heavy depth attenuation
# - ``mid-scrim`` (informational backdrop, opacity ≈ 0.8 at depth=0.5):
#   chrome that benefits from sitting slightly recessed so cameras +
#   sierpinski + reverie content read forward
# - ``beyond-scrim`` (atmosphere layer, opacity ≈ 0.68 at depth=0.5):
#   immersive background pieces that should fade as the imagination
#   ``depth`` dim rises
WARD_Z_PLANE_DEFAULTS: Final[dict[str, str]] = {
    # Surface — always legible
    "stream_overlay": "surface-scrim",
    # Mid — informational backdrop
    "chat_ambient": "mid-scrim",
    "impingement_cascade": "mid-scrim",
    "thinking_indicator": "mid-scrim",
    "hardm_dot_matrix": "mid-scrim",
    # Beyond — atmosphere
    "album": "beyond-scrim",
}

__all__ = [
    "_Z_INDEX_BASE",
    "DEFAULT_Z_INDEX_FLOAT",
    "DEFAULT_Z_PLANE",
    "WARD_Z_PLANE_DEFAULTS",
]
