"""Shared Cairo rendering helpers used by every HOMAGE-migrated ward.

HOMAGE spec §4.2 grammar rules are implemented uniformly via this
module so each ward's ``render_content`` doesn't redo the boilerplate.
The helpers all take the active :class:`HomagePackage` as an argument
and resolve palette / typography from there — no hardcoded hex.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agents.studio_compositor.homage import get_active_package
from shared.homage_package import HomagePackage

if TYPE_CHECKING:
    import cairo

log = logging.getLogger(__name__)


def active_package() -> HomagePackage:
    """Return the active package, or the BitchX fallback when registry
    resolution fails (consent-safe path, tests in isolation)."""
    pkg = get_active_package()
    if pkg is not None:
        return pkg
    from agents.studio_compositor.homage.bitchx import BITCHX_PACKAGE

    return BITCHX_PACKAGE


def select_bitchx_font(cr: cairo.Context, size: int, *, bold: bool = False) -> None:
    """Select the active package's primary font + the requested size.

    Cairo falls back gracefully when the primary font is missing. The
    guarantee we care about is monospacing, which every entry in the
    BitchX fallback chain provides.
    """
    import cairo as _c

    pkg = active_package()
    cr.select_font_face(
        pkg.typography.primary_font_family,
        _c.FONT_SLANT_NORMAL,
        _c.FONT_WEIGHT_BOLD if bold else _c.FONT_WEIGHT_NORMAL,
    )
    cr.set_font_size(size)


def paint_bitchx_bg(
    cr: cairo.Context,
    w: float,
    h: float,
    pkg: HomagePackage,
    *,
    border_rgba: tuple[float, float, float, float] | None = None,
) -> None:
    """Fill a flat CP437-style background — sharp corners, no rounded
    rects (spec §5.5 refuses ``rounded-corners``). When ``border_rgba``
    is supplied, paints a 1px border around the rectangle; otherwise no
    border. The legibility-source sites thread in the stream-mode accent
    colour via this parameter."""
    r, g, b, a = pkg.resolve_colour("background")
    cr.save()
    cr.set_source_rgba(r, g, b, a)
    cr.rectangle(0, 0, w, h)
    cr.fill()
    if border_rgba is not None:
        cr.set_source_rgba(*border_rgba)
        cr.set_line_width(1.0)
        cr.rectangle(0.5, 0.5, w - 1.0, h - 1.0)
        cr.stroke()
    cr.restore()


def irc_line_start(cr: cairo.Context, x: float, y: float, pkg: HomagePackage) -> float:
    """Draw the package's line-start marker at (x, y) in the muted role.

    Returns the updated x-cursor position.
    """
    muted = pkg.resolve_colour(pkg.grammar.punctuation_colour_role)
    marker = pkg.grammar.line_start_marker + " "
    cr.set_source_rgba(*muted)
    cr.move_to(x, y)
    cr.show_text(marker)
    return x + cr.text_extents(marker).x_advance


__all__ = [
    "active_package",
    "irc_line_start",
    "paint_bitchx_bg",
    "select_bitchx_font",
]
