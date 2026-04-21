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

__all__ = ["_Z_INDEX_BASE", "DEFAULT_Z_PLANE", "DEFAULT_Z_INDEX_FLOAT"]
