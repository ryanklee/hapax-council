"""CBIP endpoints — operator intensity-override surface.

Spec: ``docs/superpowers/specs/2026-04-21-cbip-phase-1-design.md`` §6.2.

Two endpoints:

* ``GET /api/cbip/intensity-override`` — current value (numeric or "auto")
* ``PUT /api/cbip/intensity-override`` — set to a numeric value or "auto"

Backed by ``agents/studio_compositor/cbip/override.py`` which atomically
manages ``~/.cache/hapax/cbip/intensity-override.json``.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/cbip", tags=["cbip"])


class IntensityOverridePayload(BaseModel):
    """Operator-set CBIP intensity override.

    ``value`` accepts either ``"auto"`` (use stimmung-derived default)
    or a number in ``[0.0, 1.0]``. Out-of-band numbers are clamped on
    write — clients do not need to clamp.
    """

    value: float | str = Field(
        description="Override value: numeric in [0.0, 1.0] or the string 'auto'."
    )


class IntensityOverrideResponse(BaseModel):
    """Current override state."""

    value: float | None = Field(
        description="Current override (None == 'auto'); numeric in [0.0, 1.0] otherwise."
    )


@router.get("/intensity-override", response_model=IntensityOverrideResponse)
async def get_intensity_override() -> IntensityOverrideResponse:
    """Return the current operator intensity override."""

    def _read() -> Any:
        from agents.studio_compositor.cbip.override import read_override

        return read_override().value

    value = await asyncio.to_thread(_read)
    return IntensityOverrideResponse(value=value)


@router.put("/intensity-override", response_model=IntensityOverrideResponse)
async def put_intensity_override(payload: IntensityOverridePayload) -> IntensityOverrideResponse:
    """Set the operator intensity override.

    ``value="auto"`` (or any non-numeric string) reverts to the stimmung-
    derived default. Numeric values are clamped to ``[0.0, 1.0]``.
    """

    def _write() -> Any:
        from agents.studio_compositor.cbip.override import read_override, write_override

        v = payload.value
        if isinstance(v, str):
            write_override(None)
        else:
            write_override(float(v))
        return read_override().value

    value = await asyncio.to_thread(_write)
    return IntensityOverrideResponse(value=value)
