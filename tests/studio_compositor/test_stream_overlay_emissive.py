"""Phase A4 emissive-rewrite regression for ``StreamOverlayCairoSource``.

Pins:

- Row strings follow ``>>> [FIELD|VALUE]`` grammar — ``>>> [FX|...]``,
  ``>>> [VIEWERS|N]``, ``>>> [CHAT|status]``.
- Font descriptions use ``Px437 IBM VGA 8x16`` family.
- No ``cr.show_text`` / ``cr.select_font_face`` in the render path.
- Render content sources colours through the active HomagePackage.
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
# Mostly-strict tolerance. Text rendered through PangoCairo shows
# occasional 1-byte-over-tolerance drifts across runs on some
# fontconfig caches, so we gate on a byte-over count rather than a raw
# max-delta (see ``_surfaces_match_loose`` below).
_GOLDEN_PIXEL_TOLERANCE = 8
_GOLDEN_BYTE_OVER_BUDGET = 0.02  # ≤2% of bytes may exceed tolerance


def _update_golden_requested() -> bool:
    return os.environ.get("HAPAX_UPDATE_GOLDEN", "").strip() not in ("", "0", "false")


class TestStreamOverlayGrammar:
    def test_format_preset_emits_bitchx_grammar(self):
        from agents.studio_compositor.stream_overlay import _format_preset

        assert _format_preset("foo_preset").startswith(">>> [FX|")
        assert _format_preset("") == ">>> [FX|—]"

    def test_format_viewers_emits_bitchx_grammar(self):
        from agents.studio_compositor.stream_overlay import _format_viewers

        assert _format_viewers({"active_viewers": 5}) == ">>> [VIEWERS|5]"
        assert _format_viewers({}) == ">>> [VIEWERS|—]"

    def test_format_chat_emits_bitchx_grammar(self):
        from agents.studio_compositor.stream_overlay import _format_chat

        assert _format_chat({"total_messages": 0, "unique_authors": 0}) == ">>> [CHAT|idle]"
        assert _format_chat({}) == ">>> [CHAT|idle]"
        assert ">>> [CHAT|" in _format_chat({"total_messages": 5, "unique_authors": 2})


class TestStreamOverlayTypography:
    def test_font_preset_is_px437(self):
        from agents.studio_compositor.stream_overlay import FONT_PRESET

        assert FONT_PRESET.startswith("Px437 IBM VGA 8x16")

    def test_font_metrics_is_px437(self):
        from agents.studio_compositor.stream_overlay import FONT_METRICS

        assert FONT_METRICS.startswith("Px437 IBM VGA 8x16")


class TestStreamOverlayNoToyText:
    def test_no_show_text_in_module(self):
        from agents.studio_compositor import stream_overlay

        src = inspect.getsource(stream_overlay)
        assert "cr.show_text" not in src
        assert "cr.select_font_face" not in src

    def test_render_content_uses_active_package(self):
        from agents.studio_compositor import stream_overlay

        src = inspect.getsource(stream_overlay.StreamOverlayCairoSource.render_content)
        assert "active_package" in src
        assert "resolve_colour" in src


@requires_cairo
def test_stream_overlay_emissive_golden():
    import cairo

    from agents.studio_compositor import stream_overlay as so

    _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    golden_path = _GOLDEN_DIR / "stream_overlay_emissive.png"

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 400, 200)
    cr = cairo.Context(surface)

    with (
        patch("pathlib.Path.read_text") as mock_read,
        patch("json.loads") as mock_loads,
    ):
        mock_read.return_value = ""
        mock_loads.return_value = {}
        source = so.StreamOverlayCairoSource()
        source.render_content(cr, 400, 200, t=0.0, state={})
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
        f"golden mismatch: {over}/{len(a)} bytes ({ratio:.3%}) exceeded "
        f"tolerance {_GOLDEN_PIXEL_TOLERANCE}, budget {_GOLDEN_BYTE_OVER_BUDGET:.1%}"
    )
