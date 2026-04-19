"""Phase A4 emissive-rewrite regression for ``TokenPoleCairoSource``.

Pins:

- Smiley face DELETED — no eyes, no smile arc, no cheek draws. The
  render path executes without calling ``cr.arc`` twice in quick
  succession for the eye/cheek pair (the surface-level contract is that
  ``render_content`` runs cleanly and the sampled glyph region reads as
  a point of light, not a face).
- Token glyph renders as centre dot (``accent_yellow``) + halo
  (``accent_magenta``) + outer bloom (``accent_yellow`` low alpha).
- Status row at the top of the ward renders ``>>> [TOKEN | n/th]``
  through Pango (Px437).
- No ``cr.show_text`` calls in the rewritten render path.
- Goldens: 300×300 natural-size render of the ward at a deterministic
  ``self._position`` / ``self._pulse`` so the output is pixel-stable.
"""

from __future__ import annotations

import os
import random
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
_GOLDEN_PIXEL_TOLERANCE = 6


def _update_golden_requested() -> bool:
    return os.environ.get("HAPAX_UPDATE_GOLDEN", "").strip() not in ("", "0", "false")


@requires_cairo
def _render_tick(position: float = 0.6):
    import cairo

    from agents.studio_compositor import token_pole as tp

    random.seed(0)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, tp.NATURAL_SIZE, tp.NATURAL_SIZE)
    cr = cairo.Context(surface)
    with (
        patch.object(tp, "LEDGER_FILE", Path("/nonexistent/token-ledger.json")),
        patch.object(tp.time, "monotonic", return_value=1_000_000.0),
    ):
        source = tp.TokenPoleCairoSource()
        source._position = position
        source._target_position = position
        source._pulse = 0.0
        source._total_tokens = 1337
        source._threshold = 5000
        source.render_content(cr, tp.NATURAL_SIZE, tp.NATURAL_SIZE, t=0.0, state={})
    surface.flush()
    return surface


# ── Smiley-face deletion -------------------------------------------------


@requires_cairo
class TestSmileyFaceDeleted:
    def test_render_content_source_has_no_smile_or_cheek_or_eye_draws(self):
        """Smiley-face draws (eyes, cheeks, smile arc) are deleted.

        Matches on literal draw-call substrings rather than prose so
        doc-comments mentioning the deletion don't trigger false
        positives.
        """
        import inspect

        from agents.studio_compositor import token_pole as tp

        src = inspect.getsource(tp.TokenPoleCairoSource._draw_scene)
        # Former eye dots: two arcs at (gx ± 3.5, gy + bounce_y - 2, 1.5).
        assert "gx - 3.5, gy + bounce_y - 2, 1.5" not in src
        assert "gx + 3.5, gy + bounce_y - 2, 1.5" not in src
        # Former cheek dots: arcs at (gx ± 5, gy + bounce_y + 2, 3).
        assert "gx - 5, gy + bounce_y + 2, 3" not in src
        assert "gx + 5, gy + bounce_y + 2, 3" not in src
        # Former smile arc.
        assert "arc(gx, gy + bounce_y + 1, 3.5" not in src


# ── Emissive pipeline pin -----------------------------------------------


@requires_cairo
class TestEmissivePipeline:
    def test_render_tick_produces_non_blank_surface(self):
        surface = _render_tick()
        data = bytes(surface.get_data())
        assert any(byte != 0 for byte in data[:4096])

    def test_status_row_does_not_crash_without_ledger(self):
        # Pure import + render check; ledger is patched to /nonexistent
        # so the status row falls through to zeroes.
        _render_tick()

    def test_render_source_references_emissive_base(self):
        import inspect

        from agents.studio_compositor import token_pole as tp

        src = inspect.getsource(tp.TokenPoleCairoSource._draw_scene)
        assert "paint_emissive_point" in src
        assert "paint_emissive_stroke" in src
        assert "paint_emissive_bg" in src

    def test_no_show_text_in_rewritten_render_path(self):
        import inspect

        from agents.studio_compositor import token_pole as tp

        # The primary render path in ``_draw_scene`` and status-row helper
        # must not call Cairo's toy text API; it routes via Pango.
        scene_src = inspect.getsource(tp.TokenPoleCairoSource._draw_scene)
        status_src = inspect.getsource(tp.TokenPoleCairoSource._draw_status_row)
        cascade_src = inspect.getsource(tp.TokenPoleCairoSource._draw_cascade_marker)
        assert "show_text" not in scene_src
        assert "show_text" not in status_src
        assert "show_text" not in cascade_src


# ── Golden-image regression ---------------------------------------------


@requires_cairo
def test_token_pole_emissive_golden():
    """Render a deterministic 300×300 tick and match the golden PNG."""
    import cairo

    _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    golden_path = _GOLDEN_DIR / "token_pole_emissive.png"

    surface = _render_tick()

    if _update_golden_requested() or not golden_path.exists():
        surface.write_to_png(str(golden_path))
        return

    expected = cairo.ImageSurface.create_from_png(str(golden_path))
    a = bytes(surface.get_data())
    e = bytes(expected.get_data())
    assert len(a) == len(e), "golden size mismatch"
    max_delta = 0
    for ab, eb in zip(a, e, strict=True):
        d = abs(ab - eb)
        if d > max_delta:
            max_delta = d
    assert max_delta <= _GOLDEN_PIXEL_TOLERANCE, (
        f"golden mismatch: max delta {max_delta} > tolerance {_GOLDEN_PIXEL_TOLERANCE}"
    )
