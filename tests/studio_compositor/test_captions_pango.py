"""Phase A4 typography-swap regression for captions_source.

Pins:

- ``STYLE_PUBLIC.font_description`` uses ``Px437 IBM VGA 8x16`` family.
- ``STYLE_SCIENTIFIC.font_description`` uses ``Px437 IBM VGA 8x16`` family.
- Module-level font-availability probe emits a WARN when Px437 is not
  resolvable via Pango.
- Golden: deterministic 1920×110 render of a short caption through the
  scientific style.
"""

from __future__ import annotations

import logging
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


class TestCaptionTypography:
    def test_public_style_uses_px437(self):
        from agents.studio_compositor.captions_source import STYLE_PUBLIC

        assert STYLE_PUBLIC.font_description.startswith("Px437 IBM VGA 8x16")
        assert STYLE_PUBLIC.font_description.endswith("36")

    def test_scientific_style_uses_px437(self):
        from agents.studio_compositor.captions_source import STYLE_SCIENTIFIC

        assert STYLE_SCIENTIFIC.font_description.startswith("Px437 IBM VGA 8x16")
        assert STYLE_SCIENTIFIC.font_description.endswith("22")

    def test_no_jetbrains_mono_in_caption_styles(self):
        from agents.studio_compositor.captions_source import STYLE_PUBLIC, STYLE_SCIENTIFIC

        assert "JetBrains" not in STYLE_PUBLIC.font_description
        assert "JetBrains" not in STYLE_SCIENTIFIC.font_description

    def test_no_noto_sans_in_caption_styles(self):
        from agents.studio_compositor.captions_source import STYLE_PUBLIC, STYLE_SCIENTIFIC

        assert "Noto Sans" not in STYLE_PUBLIC.font_description
        assert "Noto Sans" not in STYLE_SCIENTIFIC.font_description


class TestFontAvailabilityProbe:
    def test_probe_warns_when_px437_missing(self, caplog):
        # Re-import captions_source with text_render.has_font stubbed to
        # return False. The probe fires at module import time, so we
        # reload the module inside the patch.
        import importlib
        import sys

        # Drop the cached module so reimport fires the probe again.
        sys.modules.pop("agents.studio_compositor.captions_source", None)
        with (
            caplog.at_level(logging.WARNING, logger="agents.studio_compositor.captions_source"),
            patch(
                "agents.studio_compositor.text_render.has_font",
                return_value=False,
            ),
        ):
            importlib.import_module("agents.studio_compositor.captions_source")
        # The probe logs a WARNING that mentions Px437.
        combined = "\n".join(record.getMessage() for record in caplog.records)
        assert "Px437 IBM VGA 8x16" in combined
        assert "NOT FOUND" in combined

    def test_probe_silent_when_px437_present(self, caplog):
        import importlib
        import sys

        sys.modules.pop("agents.studio_compositor.captions_source", None)
        with (
            caplog.at_level(logging.WARNING, logger="agents.studio_compositor.captions_source"),
            patch(
                "agents.studio_compositor.text_render.has_font",
                return_value=True,
            ),
        ):
            importlib.import_module("agents.studio_compositor.captions_source")
        # No Px437-missing warning should appear.
        assert not any("NOT FOUND" in r.getMessage() for r in caplog.records)


@requires_cairo
def test_captions_pango_golden():
    """Deterministic render of one caption line through the scientific
    Px437 style."""
    import cairo

    from agents.studio_compositor.captions_source import (
        STYLE_SCIENTIFIC,
        CaptionsCairoSource,
    )

    _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    golden_path = _GOLDEN_DIR / "captions_pango.png"

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1920, 110)
    cr = cairo.Context(surface)
    source = CaptionsCairoSource()
    source._render_caption(
        cr,
        1920,
        110,
        "SCIENTIFIC REGISTER — Px437 IBM VGA 8x16 via Pango",
        STYLE_SCIENTIFIC,
    )
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
