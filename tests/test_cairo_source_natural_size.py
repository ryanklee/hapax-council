"""CairoSourceRunner natural_w/natural_h tests.

The compositor source-registry epic decouples a cairo source's render
resolution from the full-canvas dimensions. A source declares its natural
content size (e.g. 300×300 for the Vitruvian Man overlay) and the runner
allocates the render surface at that size. The compositor then places the
rendered surface at the assigned SurfaceSchema.geometry via scale-on-blit.

Plan task 4/29. See
``docs/superpowers/plans/2026-04-12-compositor-source-registry-foundation-plan.md``
§ Phase B Task 4.
"""

from __future__ import annotations

from agents.studio_compositor.cairo_source import CairoSource, CairoSourceRunner


class _FillSource(CairoSource):
    """Fills the passed canvas with solid red so we can inspect the surface size."""

    def render(self, cr, canvas_w, canvas_h, t, state):  # noqa: D401
        cr.set_source_rgba(1.0, 0.0, 0.0, 1.0)
        cr.rectangle(0, 0, canvas_w, canvas_h)
        cr.fill()


class TestNaturalSizeAllocation:
    def test_natural_size_smaller_than_canvas_allocates_natural(self):
        runner = CairoSourceRunner(
            source_id="red",
            source=_FillSource(),
            canvas_w=1920,
            canvas_h=1080,
            target_fps=10.0,
            natural_w=300,
            natural_h=300,
        )
        runner.tick_once()
        out = runner.get_output_surface()
        assert out is not None
        assert out.get_width() == 300
        assert out.get_height() == 300

    def test_natural_size_defaults_to_canvas_when_unset(self):
        """Backward compat: existing callers that don't pass natural_w/h keep working."""
        runner = CairoSourceRunner(
            source_id="red",
            source=_FillSource(),
            canvas_w=640,
            canvas_h=360,
            target_fps=10.0,
        )
        runner.tick_once()
        out = runner.get_output_surface()
        assert out is not None
        assert out.get_width() == 640
        assert out.get_height() == 360

    def test_render_receives_natural_dims_not_canvas(self):
        """The CairoSource.render() method is invoked with natural dims.

        A source that draws 'full rectangle' expects its render to fill the
        natural surface, not the canvas. If the runner passes canvas dims,
        the resulting surface has only a corner filled.
        """
        runner = CairoSourceRunner(
            source_id="red",
            source=_FillSource(),
            canvas_w=1920,
            canvas_h=1080,
            target_fps=10.0,
            natural_w=50,
            natural_h=50,
        )
        runner.tick_once()
        out = runner.get_output_surface()
        assert out is not None
        assert out.get_width() == 50
        assert out.get_height() == 50
        # Every pixel should be red (0xFF red in ARGB32 little-endian → B=0, G=0, R=0xFF, A=0xFF)
        data = bytes(out.get_data())
        stride = out.get_stride()
        # Check corner pixel
        r_byte, g_byte, b_byte = data[2], data[1], data[0]
        assert (r_byte, g_byte, b_byte) == (0xFF, 0x00, 0x00)
        # Check center pixel
        cx_off = (25 * stride) + 25 * 4
        r_byte, g_byte, b_byte = data[cx_off + 2], data[cx_off + 1], data[cx_off + 0]
        assert (r_byte, g_byte, b_byte) == (0xFF, 0x00, 0x00)
