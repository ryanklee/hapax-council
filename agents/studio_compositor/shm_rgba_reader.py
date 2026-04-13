"""ShmRgbaReader — reads RGBA frames from a shared-memory file + sidecar.

Sidecar format (``<path>.json``):
    {"w": int, "h": int, "stride": int, "frame_id": int}

The reader caches the last wrapped ``cairo.ImageSurface`` by ``frame_id`` and
re-wraps when the sidecar reports a new id. Missing file / missing sidecar /
unreadable JSON / short buffer all resolve to ``get_current_surface() -> None``
without raising — consumers get a clean "no frame yet" signal and the
compositor's ``compositor_source_frame_age_seconds`` metric catches chronic
staleness.

Part of the compositor source-registry epic PR 1. See
``docs/superpowers/specs/2026-04-12-compositor-source-registry-foundation-design.md``
§ "Source backends".
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import cairo

log = logging.getLogger(__name__)


class ShmRgbaReader:
    """Wraps an RGBA shared-memory file as a ``cairo.ImageSurface``.

    The file at ``path`` holds raw BGRA bytes (cairo FORMAT_ARGB32 is
    little-endian BGRA on all current platforms). The sidecar at
    ``<path>.json`` describes the current frame layout and the monotonic
    ``frame_id`` that increments on every producer write.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._sidecar_path = self._path.with_suffix(self._path.suffix + ".json")
        self._cached_surface: cairo.ImageSurface | None = None
        self._cached_frame_id: int | None = None

    def _read_sidecar(self) -> dict[str, Any] | None:
        if not self._sidecar_path.exists():
            return None
        try:
            return json.loads(self._sidecar_path.read_text())
        except (OSError, json.JSONDecodeError):
            log.debug(
                "ShmRgbaReader failed to read sidecar %s",
                self._sidecar_path,
                exc_info=True,
            )
            return None

    def get_current_surface(self) -> cairo.ImageSurface | None:
        """Return the current frame as a cairo.ImageSurface, or None.

        The return value is cached by ``frame_id``: consecutive calls with
        the same sidecar ``frame_id`` return the same surface instance, so
        callers can rely on identity for short-term caching.
        """
        meta = self._read_sidecar()
        if meta is None:
            return None
        if not self._path.exists():
            return None

        frame_id = meta.get("frame_id")
        if frame_id == self._cached_frame_id and self._cached_surface is not None:
            return self._cached_surface

        try:
            w = int(meta["w"])
            h = int(meta["h"])
            stride = int(meta["stride"])
        except (KeyError, TypeError, ValueError):
            log.debug("ShmRgbaReader sidecar %s missing w/h/stride", self._sidecar_path)
            return None

        try:
            raw = self._path.read_bytes()
        except OSError:
            log.debug("ShmRgbaReader failed to read %s", self._path, exc_info=True)
            return None
        if len(raw) < stride * h:
            log.debug("ShmRgbaReader buffer short: got %d, want %d", len(raw), stride * h)
            return None

        # Import cairo lazily so the module is importable in environments
        # without pycairo (e.g. documentation builders). The test suite
        # imports cairo unconditionally so this is transparent at runtime.
        import cairo

        data = bytearray(raw[: stride * h])
        surface = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, w, h, stride)
        self._cached_surface = surface
        self._cached_frame_id = frame_id
        return surface
