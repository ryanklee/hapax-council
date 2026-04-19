"""Phase A4 classification pin for ``VinylPlatterCairoSource``.

The vinyl_platter ward was classified as a Cairo source that ALREADY
routes through Pango (no ``cr.show_text``, package typography). This
test pins the classification so a future regression that reintroduces
``cr.show_text`` or Cairo toy font-face selection fails loudly. Also
seeds a golden-image regression for the BitchX border rendering path.
"""

from __future__ import annotations

import inspect
import os
from pathlib import Path
from unittest.mock import patch

import pytest


def _cairo_available() -> bool:
    try:
        import cairo  # noqa: F401
    except ImportError:
        return False
    return True


_HAS_CAIRO = _cairo_available()
requires_cairo = pytest.mark.skipif(not _HAS_CAIRO, reason="pycairo not installed")

_GOLDEN_DIR = Path(__file__).parent / "golden_images" / "content"
_GOLDEN_PIXEL_TOLERANCE = 8
_GOLDEN_BYTE_OVER_BUDGET = 0.02


def _update_golden_requested() -> bool:
    return os.environ.get("HAPAX_UPDATE_GOLDEN", "").strip() not in ("", "0", "false")


class TestVinylPlatterEmissiveClassification:
    def test_no_show_text_call_in_module(self):
        """Match the executable call site, not the doc-comment mention."""
        from agents.studio_compositor import vinyl_platter

        src = inspect.getsource(vinyl_platter)
        assert "cr.show_text(" not in src

    def test_no_select_font_face_call_in_module(self):
        from agents.studio_compositor import vinyl_platter

        src = inspect.getsource(vinyl_platter)
        assert "cr.select_font_face(" not in src

    def test_renders_through_text_render_pango_path(self):
        from agents.studio_compositor import vinyl_platter

        src = inspect.getsource(vinyl_platter.VinylPlatterCairoSource._draw_labels)
        assert "render_text" in src
        assert "TextStyle" in src


@requires_cairo
def test_vinyl_platter_border_emissive_golden():
    """Deterministic render of the BitchX border + labels path.

    Patches camera-snapshot loading to skip the disk/platter path and
    exercises only the border + label renderers, which are the emissive
    surfaces touched by Phase A4.
    """
    import cairo

    from agents.studio_compositor import vinyl_platter as vp
    from agents.studio_compositor.homage.bitchx import BITCHX_PACKAGE

    _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    golden_path = _GOLDEN_DIR / "vinyl_platter_border_emissive.png"

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, vp.CANVAS_W, vp.CANVAS_H)
    cr = cairo.Context(surface)
    # Emissive-clean background fill so the border pops.
    bg = BITCHX_PACKAGE.resolve_colour("background")
    cr.set_source_rgba(*bg)
    cr.rectangle(0, 0, vp.CANVAS_W, vp.CANVAS_H)
    cr.fill()

    with patch.object(vp, "get_active_package", return_value=BITCHX_PACKAGE):
        vp.VinylPlatterCairoSource._draw_border(cr, vp.CANVAS_W, vp.CANVAS_H, BITCHX_PACKAGE)
        vp.VinylPlatterCairoSource._draw_labels(cr, vp.CANVAS_W, rate=1.0, pkg=BITCHX_PACKAGE)
    surface.flush()

    if _update_golden_requested() or not golden_path.exists():
        surface.write_to_png(str(golden_path))
        return

    expected = cairo.ImageSurface.create_from_png(str(golden_path))
    a = bytes(surface.get_data())
    e = bytes(expected.get_data())
    assert len(a) == len(e)
    over = 0
    for ab, eb in zip(a, e, strict=True):
        if abs(ab - eb) > _GOLDEN_PIXEL_TOLERANCE:
            over += 1
    ratio = over / max(1, len(a))
    assert ratio <= _GOLDEN_BYTE_OVER_BUDGET, (
        f"golden mismatch: {over}/{len(a)} bytes ({ratio:.3%}) over tolerance"
    )
