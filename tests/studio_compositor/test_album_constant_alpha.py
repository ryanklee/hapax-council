"""2026-04-23 Gemini-reapproach Plan B Phase B3 regression pin.

The CBIP (album-cover) ward must be audio-reactive without ANY alpha-
beat modulation. Gemini's reverted ``d4a4b0113`` shipped
``paint_with_alpha(0.4 + beat_smooth * 0.3)`` — the exact pattern
``feedback_no_blinking_homage_wards`` forbids.

This test renders ``_pip_fx_package`` with synthetic ``bass_band``
values sweeping across [0.0, 1.0] and samples the surface alpha
channel at a fixed patch. ALPHA MUST be constant across the sweep.
RGB channels may vary — that's the chromatic-aberration effect.
"""

from __future__ import annotations

from pathlib import Path

import cairo
import pytest

from agents.studio_compositor import album_overlay as ao


class _FakePackage:
    def resolve_colour(self, role: str) -> tuple[float, float, float, float]:
        return (0.5, 0.5, 0.5, 1.0)


def _render_one(bass_band: float) -> cairo.ImageSurface:
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, ao.SIZE, ao.SIZE)
    cr = cairo.Context(surf)
    cr.set_source_rgb(0.4, 0.4, 0.4)
    cr.paint()

    cover = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
    cover_cr = cairo.Context(cover)
    cover_cr.set_source_rgb(0.6, 0.3, 0.8)
    cover_cr.paint()

    ao._pip_fx_package(
        cr,
        ao.SIZE,
        ao.SIZE,
        _FakePackage(),
        cover_surface=cover,
        bass_band=bass_band,
        cover_scale=1.0,
    )
    return surf


def _patch_alpha_mean(surface: cairo.ImageSurface) -> float:
    data = memoryview(surface.get_data()).cast("B")
    stride = surface.get_stride()
    cx, cy = ao.SIZE // 2, ao.SIZE // 2
    half = 16
    total = 0
    count = 0
    for y in range(cy - half, cy + half):
        row_offset = y * stride
        for x in range(cx - half, cx + half):
            total += data[row_offset + 4 * x + 3]
            count += 1
    return total / (count * 255.0)


@pytest.mark.parametrize(
    "bass_band",
    [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0],
)
def test_album_alpha_constant_across_bass_sweep(bass_band: float) -> None:
    """Alpha of centre patch must equal silent-state alpha within 1/255."""
    surf_silent = _render_one(0.0)
    silent_alpha = _patch_alpha_mean(surf_silent)

    surf_active = _render_one(bass_band)
    active_alpha = _patch_alpha_mean(surf_active)

    tolerance = 1.0 / 255.0
    assert abs(active_alpha - silent_alpha) <= tolerance, (
        f"alpha drift at bass_band={bass_band}: silent={silent_alpha:.4f}, "
        f"active={active_alpha:.4f}, delta={abs(active_alpha - silent_alpha):.4f} "
        f"(> {tolerance:.4f} quantization unit). feedback_no_blinking_homage_wards "
        "forbids alpha modulation."
    )


def test_album_fn_signature_accepts_new_kwargs() -> None:
    import inspect

    sig = inspect.signature(ao._pip_fx_package)
    assert "cover_surface" in sig.parameters
    assert "bass_band" in sig.parameters
    assert "cover_scale" in sig.parameters
    assert sig.parameters["cover_surface"].default is None
    assert sig.parameters["bass_band"].default == 0.0


def test_album_module_has_no_alpha_beat_expressions() -> None:
    """Static-scan pin. No alpha-beat-modulation expressions allowed."""
    import re

    src = Path(ao.__file__).read_text()
    forbidden = re.compile(
        r"paint_with_alpha\([^)]*(?:beat|bass_band|onset|rms)"
        r"|set_source_rgba\([^)]+,\s*[0-9.]+\s*[+\-]\s*(?:beat|bass_band|onset|rms)"
    )
    for lineno, line in enumerate(src.splitlines(), 1):
        m = forbidden.search(line)
        assert not m, (
            f"album_overlay.py:{lineno} matches forbidden alpha-beat-modulation "
            f"pattern: {line.strip()!r}"
        )
