"""Album-art → chrome color resonance — aesthetic linking of music + overlay.

Phase F2 of the Epic-2 hothouse plan. Operator directive 2026-04-17:
"symbols and text and proximity are fodder for grounding and raw
interpretive material." The legibility chrome (overlays, indicators,
HUD) sits alongside the album art; linking their color temperature
makes the surface feel authored rather than stacked.

Mechanism:
  1. Read `/dev/shm/hapax-compositor/album-cover.png` (written by
     `scripts/album-identifier.py` when vinyl is identified).
  2. Downsample to ~32px; compute a mean HSV.
  3. Smooth with a 5s first-order low-pass so chrome doesn't flash
     between tracks.
  4. Emit a warmth value in [-1, 1] to
     `/dev/shm/hapax-compositor/color-resonance.json`. -1 = cool,
     +1 = warm. Cairo sources can read and bias their palette accents.

Published schema:
    {
      "warmth": float,          # -1..1
      "mean_h": float,          # 0..360
      "mean_s": float,          # 0..1
      "mean_v": float,          # 0..1
      "updated_at": float       # UNIX epoch
    }

When no album cover is present (no vinyl, no fallback), warmth decays
to 0 (neutral) over the smoothing window.
"""

from __future__ import annotations

import colorsys
import json
import logging
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_ALBUM_COVER = Path("/dev/shm/hapax-compositor/album-cover.png")
_RESONANCE_OUT = Path("/dev/shm/hapax-compositor/color-resonance.json")
_SMOOTH_TAU_S = 5.0


class ColorResonance:
    """Stateful smoother; one instance drives the resonance publisher loop."""

    def __init__(self) -> None:
        self._last_warmth: float = 0.0
        self._last_h: float = 0.0
        self._last_s: float = 0.0
        self._last_v: float = 0.0
        self._last_update: float = time.time()
        self._last_cover_mtime: float = 0.0

    def tick(self) -> dict[str, Any]:
        now = time.time()
        dt = max(0.001, now - self._last_update)
        alpha = min(1.0, dt / _SMOOTH_TAU_S)

        target = self._sample_current_cover()
        if target is None:
            # Decay toward neutral when no cover is available.
            target = (0.0, 0.0, 0.0, 0.0)

        warmth_t, h_t, s_t, v_t = target
        self._last_warmth += alpha * (warmth_t - self._last_warmth)
        self._last_h += alpha * (h_t - self._last_h)
        self._last_s += alpha * (s_t - self._last_s)
        self._last_v += alpha * (v_t - self._last_v)
        self._last_update = now

        return {
            "warmth": round(self._last_warmth, 3),
            "mean_h": round(self._last_h, 2),
            "mean_s": round(self._last_s, 3),
            "mean_v": round(self._last_v, 3),
            "updated_at": now,
        }

    def _sample_current_cover(self) -> tuple[float, float, float, float] | None:
        """Return (warmth, mean_h, mean_s, mean_v) for the current cover, or None."""
        try:
            if not _ALBUM_COVER.exists():
                return None
            mtime = _ALBUM_COVER.stat().st_mtime
            if mtime == self._last_cover_mtime:
                # Same cover as last tick — let the existing smoothed state ride
                # but re-apply the current cover's target so we converge.
                return self._compute_palette(_ALBUM_COVER)
            self._last_cover_mtime = mtime
            return self._compute_palette(_ALBUM_COVER)
        except Exception:
            log.debug("color resonance sample failed", exc_info=True)
            return None

    def _compute_palette(self, cover_path: Path) -> tuple[float, float, float, float] | None:
        """Downsample to 32×32 and compute mean HSV + warmth score."""
        try:
            from PIL import Image
        except ImportError:
            log.debug("PIL not available — color resonance falls back to neutral")
            return None
        try:
            with Image.open(cover_path) as img:
                img = img.convert("RGB").resize((32, 32), Image.Resampling.LANCZOS)
                pixels = img.getdata()
                count = len(pixels)
                if count == 0:
                    return None
                sum_r = sum_g = sum_b = 0
                for r, g, b in pixels:
                    sum_r += r
                    sum_g += g
                    sum_b += b
                mean_r = sum_r / count / 255.0
                mean_g = sum_g / count / 255.0
                mean_b = sum_b / count / 255.0
                h, s, v = colorsys.rgb_to_hsv(mean_r, mean_g, mean_b)
                # Warmth: reds/oranges (h in 0..60 or 330..360) → +1,
                # blues/greens (h in 120..240) → -1. Sinusoidal mapping
                # so the value is smooth across hue rotations.
                import math

                warmth = math.cos(math.radians(h * 360.0))
                # Weight by saturation so gray covers don't push the chrome.
                warmth *= s
                return (warmth, h * 360.0, s, v)
        except Exception:
            log.debug("color resonance palette compute failed", exc_info=True)
            return None


def publish(state: dict[str, Any]) -> None:
    """Atomic write to /dev/shm/hapax-compositor/color-resonance.json."""
    try:
        _RESONANCE_OUT.parent.mkdir(parents=True, exist_ok=True)
        tmp = _RESONANCE_OUT.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state), encoding="utf-8")
        tmp.replace(_RESONANCE_OUT)
    except Exception:
        log.warning("color resonance publish failed", exc_info=True)


def read_current() -> dict[str, Any]:
    """Consumer-side read. Returns {} if no resonance file yet."""
    try:
        if _RESONANCE_OUT.exists():
            return json.loads(_RESONANCE_OUT.read_text(encoding="utf-8"))
    except Exception:
        log.debug("color resonance read failed", exc_info=True)
    return {}


__all__ = ["ColorResonance", "publish", "read_current"]
