"""Cairo overlay rendering for the compositor."""

from __future__ import annotations

from typing import Any


def on_overlay_caps_changed(compositor: Any, overlay: Any, caps: Any) -> None:
    """Called when cairooverlay negotiates caps -- cache canvas size."""
    s = caps.get_structure(0)
    w = s.get_int("width")
    h = s.get_int("height")
    if w[0] and h[0]:
        compositor._overlay_canvas_size = (w[1], h[1])
    compositor._overlay_cache_surface = None


def on_draw(compositor: Any, overlay: Any, cr: Any, timestamp: int, duration: int) -> None:
    """Cairo draw callback -- renders Pango zone overlays only."""
    if not compositor.config.overlay_enabled:
        return

    canvas_w, canvas_h = compositor._overlay_canvas_size

    # Render content overlay zones (markdown/ANSI from Obsidian via Pango)
    if hasattr(compositor, "_overlay_zone_manager"):
        compositor._overlay_zone_manager.render(cr, canvas_w, canvas_h)
