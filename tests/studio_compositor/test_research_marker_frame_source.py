"""Tests for ResearchMarkerFrameSource.

LRR Phase 2 item 4. Verifies the epoch-based transition detector,
3-second banner window, and Cairo render contract.

Spec: docs/superpowers/specs/2026-04-15-lrr-phase-2-archive-research-instrument-design.md §3.4
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import cairo

from agents.studio_compositor.research_marker_frame_source import (
    BANNER_VISIBLE_SECONDS,
    ResearchMarkerFrameSource,
)
from shared.research_marker import MarkerState


def _make_marker(epoch: int, condition_id: str = "cond-phase-a-baseline-qwen-001") -> MarkerState:
    return MarkerState(
        condition_id=condition_id,
        set_at=datetime.now(UTC),
        set_by="test",
        epoch=epoch,
    )


def _render_surface(source: ResearchMarkerFrameSource, t: float, w: int = 1920, h: int = 1080):
    """Build a Cairo ImageSurface + context, render the source into it, return surface."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surface)
    source.render(ctx, w, h, t, {})
    return surface


def _surface_is_blank(surface: cairo.ImageSurface) -> bool:
    """Return True if every pixel in the surface is zeroed (transparent)."""
    data = bytes(surface.get_data())
    return all(b == 0 for b in data)


class TestFirstObservationNoBanner:
    """First marker observation must NOT fire a banner (compositor restart)."""

    def test_first_observation_initializes_epoch_without_firing(self):
        source = ResearchMarkerFrameSource()
        marker = _make_marker(epoch=5)
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker", return_value=marker
        ):
            surface = _render_surface(source, t=0.0)
        assert _surface_is_blank(surface)
        assert source._last_epoch == 5
        assert source._banner_start_t is None


class TestNoMarkerNoBanner:
    """Missing marker means transparent render."""

    def test_missing_marker_renders_blank(self):
        source = ResearchMarkerFrameSource()
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker", return_value=None
        ):
            surface = _render_surface(source, t=0.0)
        assert _surface_is_blank(surface)
        assert source._last_epoch is None

    def test_marker_vanishes_after_previous_observation_clears_epoch(self):
        source = ResearchMarkerFrameSource()
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker",
            return_value=_make_marker(epoch=3),
        ):
            _render_surface(source, t=0.0)
        assert source._last_epoch == 3
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker",
            return_value=None,
        ):
            surface = _render_surface(source, t=1.0)
        assert _surface_is_blank(surface)
        assert source._last_epoch is None


class TestEpochTransitionFiresBanner:
    """An epoch change starts a banner that lasts 3 seconds."""

    def test_second_observation_with_new_epoch_starts_banner(self):
        source = ResearchMarkerFrameSource()
        # First observation at t=0 initializes epoch without firing
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker",
            return_value=_make_marker(epoch=1, condition_id="cond-a"),
        ):
            _render_surface(source, t=0.0)
        assert source._banner_start_t is None
        # Second observation at t=1 with new epoch starts banner
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker",
            return_value=_make_marker(epoch=2, condition_id="cond-b"),
        ):
            surface = _render_surface(source, t=1.0)
        assert source._banner_start_t == 1.0
        assert source._banner_condition_id == "cond-b"
        assert source._last_epoch == 2
        # Banner is visible → pixels are drawn
        assert not _surface_is_blank(surface)

    def test_same_epoch_does_not_restart_banner(self):
        source = ResearchMarkerFrameSource()
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker",
            return_value=_make_marker(epoch=7),
        ):
            _render_surface(source, t=0.0)
            _render_surface(source, t=1.0)
            _render_surface(source, t=2.0)
        assert source._banner_start_t is None  # Never fired


class TestThreeSecondWindow:
    """Banner visible for exactly 3 seconds then stops."""

    def test_banner_visible_within_window(self):
        source = ResearchMarkerFrameSource()
        source._last_epoch = 0
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker",
            return_value=_make_marker(epoch=1, condition_id="cond-test-001"),
        ):
            # t=5 starts the banner
            _render_surface(source, t=5.0)
            # t=5.5 (0.5s later) — still visible
            surface_mid = _render_surface(source, t=5.5)
        assert not _surface_is_blank(surface_mid)

    def test_banner_invisible_after_window_expires(self):
        source = ResearchMarkerFrameSource()
        source._last_epoch = 0
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker",
            return_value=_make_marker(epoch=1),
        ):
            _render_surface(source, t=10.0)  # Banner starts
        # Banner visible until t=10 + 3.0 = 13.0; at t=13.5 it's expired
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker",
            return_value=_make_marker(epoch=1),  # Same epoch — no new fire
        ):
            surface = _render_surface(source, t=13.5)
        assert _surface_is_blank(surface)

    def test_banner_boundary_exactly_at_window_end(self):
        """At exactly t=start+3.0s, banner should be invisible (half-open window)."""
        source = ResearchMarkerFrameSource()
        source._last_epoch = 0
        source._banner_start_t = 0.0
        source._banner_condition_id = "cond-boundary"
        # At t = BANNER_VISIBLE_SECONDS (exact boundary) banner must be gone.
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker",
            return_value=_make_marker(epoch=0),
        ):
            surface = _render_surface(source, t=BANNER_VISIBLE_SECONDS)
        assert _surface_is_blank(surface)


class TestBannerContent:
    """Rendered banner contains readable non-blank pixels."""

    def test_banner_draws_non_trivial_pixels(self):
        source = ResearchMarkerFrameSource()
        source._last_epoch = 0
        source._banner_start_t = 0.0
        source._banner_condition_id = "cond-content-check-001"
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker",
            return_value=_make_marker(epoch=0, condition_id="cond-content-check-001"),
        ):
            surface = _render_surface(source, t=0.5)
        # Quick sanity check: banner occupies ~middle third vertically.
        # Pixel at (center_x, center_y) should be non-zero (banner bg).
        data = bytes(surface.get_data())
        stride = surface.get_stride()
        cx, cy = 960, 540
        pixel_offset = cy * stride + cx * 4
        # ARGB32: at least one of B/G/R/A is non-zero
        assert any(b != 0 for b in data[pixel_offset : pixel_offset + 4])

    def test_banner_handles_none_condition_id(self):
        """If read_marker returns a MarkerState with condition_id set but the
        internal _banner_condition_id is None, render uses '(unknown)' as
        fallback without crashing."""
        source = ResearchMarkerFrameSource()
        source._last_epoch = 0
        source._banner_start_t = 0.0
        source._banner_condition_id = None
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker",
            return_value=_make_marker(epoch=0),
        ):
            # Must not raise
            surface = _render_surface(source, t=0.5)
        # Non-blank — banner drew the "(unknown)" fallback
        assert not _surface_is_blank(surface)


class TestReadMarkerErrorSwallowed:
    """If read_marker raises, the source logs + treats it as missing."""

    def test_read_marker_raising_does_not_break_render(self):
        source = ResearchMarkerFrameSource()
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker",
            side_effect=RuntimeError("boom"),
        ):
            # Must not raise
            surface = _render_surface(source, t=0.0)
        assert _surface_is_blank(surface)


class TestMultipleTransitions:
    """Multiple epoch advances each fire a fresh banner."""

    def test_second_transition_replaces_first_banner(self):
        source = ResearchMarkerFrameSource()
        # Initial observation
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker",
            return_value=_make_marker(epoch=1, condition_id="cond-a"),
        ):
            _render_surface(source, t=0.0)
        # First transition
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker",
            return_value=_make_marker(epoch=2, condition_id="cond-b"),
        ):
            _render_surface(source, t=1.0)
        assert source._banner_condition_id == "cond-b"
        assert source._banner_start_t == 1.0
        # Second transition 5s later (after first banner would have expired)
        with patch(
            "agents.studio_compositor.research_marker_frame_source.read_marker",
            return_value=_make_marker(epoch=3, condition_id="cond-c"),
        ):
            surface = _render_surface(source, t=6.0)
        assert source._banner_condition_id == "cond-c"
        assert source._banner_start_t == 6.0
        assert not _surface_is_blank(surface)
