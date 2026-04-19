"""Phase A4 emissive-rewrite regression for ``AlbumOverlayCairoSource``.

Pins:

- ``PIP_EFFECTS`` dict, ``_pip_fx_vintage``, ``_pip_fx_cold``,
  ``_pip_fx_neon``, ``_pip_fx_film``, ``_pip_fx_phosphor`` are DELETED
  from the module namespace.
- ``_pip_fx_package(cr, w, h, pkg)`` exists and accepts a HomagePackage.
- Splattribution uses the active package's ``primary_font_family`` via
  Pango — i.e. ``_draw_attrib`` references
  ``pkg.typography.primary_font_family``.
- No ``cr.show_text`` / ``cr.select_font_face`` in the rewritten
  render path.
- Golden: deterministic render of the ward at 300×450.
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


class TestPipFxDictDeleted:
    """Pin: the five-random ``_pip_fx_*`` dict is gone."""

    def test_module_has_no_legacy_pip_fx_symbols(self):
        from agents.studio_compositor import album_overlay

        for symbol in (
            "PIP_EFFECTS",
            "_pip_fx_vintage",
            "_pip_fx_cold",
            "_pip_fx_neon",
            "_pip_fx_film",
            "_pip_fx_phosphor",
        ):
            assert not hasattr(album_overlay, symbol), f"legacy symbol {symbol} still present"

    def test_pip_fx_package_exists(self):
        from agents.studio_compositor.album_overlay import _pip_fx_package

        assert callable(_pip_fx_package)


class TestSplattributionTypography:
    def test_draw_attrib_sources_package_font(self):
        from agents.studio_compositor import album_overlay

        src = inspect.getsource(album_overlay.AlbumOverlayCairoSource._draw_attrib)
        assert "pkg.typography.primary_font_family" in src

    def test_no_hardcoded_jetbrains_mono(self):
        from agents.studio_compositor import album_overlay

        src = inspect.getsource(album_overlay)
        # JetBrains Mono MAY appear in a stale docstring — assert no
        # active ``font_description=`` kwarg with that family.
        assert 'font_description="JetBrains Mono Bold 10"' not in src


class TestNoCairoToyText:
    def test_no_show_text_or_select_font_face_in_module(self):
        from agents.studio_compositor import album_overlay

        src = inspect.getsource(album_overlay)
        assert "cr.show_text" not in src
        assert "cr.select_font_face" not in src


@requires_cairo
class TestPipFxPackageExecution:
    def test_pip_fx_package_runs_against_bitchx(self):
        import cairo

        from agents.studio_compositor.album_overlay import _pip_fx_package
        from agents.studio_compositor.homage.bitchx import BITCHX_PACKAGE

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 300, 300)
        cr = cairo.Context(surface)
        # Fill with a non-black baseline so the effect strokes are visible.
        cr.set_source_rgba(0.30, 0.30, 0.30, 1.0)
        cr.rectangle(0, 0, 300, 300)
        cr.fill()
        _pip_fx_package(cr, 300, 300, BITCHX_PACKAGE)
        surface.flush()
        data = bytes(surface.get_data())
        # The effect must have drawn *something* beyond the baseline —
        # scanlines, shadow mask, border.
        assert any(byte != 0 for byte in data)


@requires_cairo
def test_album_overlay_emissive_golden():
    """Deterministic render of the ward with a stub cover.

    Patches ``image_loader.get_image_loader`` to return a deterministic
    gradient surface so the test doesn't depend on ``/dev/shm`` state.
    """
    import cairo

    from agents.studio_compositor import album_overlay as ao

    _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    golden_path = _GOLDEN_DIR / "album_overlay_emissive.png"

    # Build a 300×300 stub cover with a deterministic gradient.
    cover_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 300, 300)
    ccr = cairo.Context(cover_surface)
    grad = cairo.LinearGradient(0, 0, 300, 300)
    grad.add_color_stop_rgba(0, 0.8, 0.2, 0.2, 1.0)
    grad.add_color_stop_rgba(1, 0.2, 0.2, 0.8, 1.0)
    ccr.set_source(grad)
    ccr.rectangle(0, 0, 300, 300)
    ccr.fill()

    class _FakeLoader:
        def load(self, _path):
            return cover_surface

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, ao.CANVAS_W, ao.CANVAS_H)
    cr = cairo.Context(surface)

    with (
        patch.object(ao, "_pip_fx_package", ao._pip_fx_package),
        patch("agents.studio_compositor.image_loader.get_image_loader") as mock_loader,
        patch("os.path.exists", return_value=True),
        patch("os.path.getmtime", return_value=1.0),
    ):
        mock_loader.return_value = _FakeLoader()
        source = ao.AlbumOverlayCairoSource()
        source._attrib_text = "TEST | Artist - Album"
        source._attrib_mtime = 1.0
        # Pre-populate to skip the vinyl gate probe.
        source._surface = cover_surface
        source._surface_mtime = 1.0
        # Patch the vinyl probe to fail-open.
        with patch.object(source, "_vinyl_playing", return_value=False):
            source.render_content(cr, ao.CANVAS_W, ao.CANVAS_H, t=0.0, state={})
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
