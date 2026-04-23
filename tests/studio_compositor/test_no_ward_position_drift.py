"""2026-04-23 operator directive: wards must not drift off-screen.

Right-edge wards at x ≈ 1800 with ±20 px drift-amplitude push content past
the 1920×1080 canvas. Operator feedback after PR #1236 (scale_bump disable):
"still off screen".

Fix: ``overlay_zones.OverlayZone.draw`` hard-zeros ``position_offset_x`` and
``position_offset_y`` at the blit site. Drift-sine / drift-circle
capabilities still populate the ward-properties field, but the render
path ignores them.

This test pins the neutralization both at runtime (render a ward with a
large offset and confirm the blit origin is unchanged) and at source
level (static scan rejects any re-introduction of ``+ offset_x`` /
``+ offset_y`` arithmetic applied to the blit coordinates).
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

from agents.studio_compositor.overlay_zones import OverlayZone
from agents.studio_compositor.ward_properties import WardProperties

_REPO_ROOT = Path(__file__).parents[2]
_OVERLAY_ZONES = _REPO_ROOT / "agents" / "studio_compositor" / "overlay_zones.py"


def _make_props(offset_x: float = 0.0, offset_y: float = 0.0) -> WardProperties:
    return WardProperties(position_offset_x=offset_x, position_offset_y=offset_y)


def _make_zone(zone_id: str, x: int, y: int) -> OverlayZone:
    zone = OverlayZone({"id": zone_id, "x": x, "y": y, "max_width": 300})
    zone._pango_markup = "hi"
    zone._cached_surface = MagicMock()
    return zone


def _render_with_offsets(zone: OverlayZone, offset_x: float, offset_y: float) -> MagicMock:
    cr = MagicMock()
    props = _make_props(offset_x=offset_x, offset_y=offset_y)
    with patch(
        "agents.studio_compositor.ward_properties.resolve_ward_properties",
        return_value=props,
    ):
        zone.render(cr, canvas_w=1920, canvas_h=1080)
    return cr


def test_render_ignores_position_offset_x() -> None:
    """Large position_offset_x does not shift the blit origin."""
    zone = _make_zone("z1", x=100, y=200)
    cr = _render_with_offsets(zone, offset_x=250.0, offset_y=0.0)
    assert cr.set_source_surface.called
    _surface, x_arg, _y_arg = cr.set_source_surface.call_args.args
    assert x_arg == zone.x - 2, (
        f"position_offset_x leaked into blit origin: x={x_arg}, expected {zone.x - 2}"
    )


def test_render_ignores_position_offset_y() -> None:
    """Large position_offset_y does not shift the blit origin."""
    zone = _make_zone("z2", x=100, y=200)
    cr = _render_with_offsets(zone, offset_x=0.0, offset_y=-180.0)
    assert cr.set_source_surface.called
    _surface, _x_arg, y_arg = cr.set_source_surface.call_args.args
    assert y_arg == zone.y - 2, (
        f"position_offset_y leaked into blit origin: y={y_arg}, expected {zone.y - 2}"
    )


def test_render_ignores_combined_offsets() -> None:
    """Combined drift: both axes must remain at baseline."""
    zone = _make_zone("z3", x=1800, y=290)
    cr = _render_with_offsets(zone, offset_x=20.0, offset_y=20.0)
    _surface, x_arg, y_arg = cr.set_source_surface.call_args.args
    assert x_arg == zone.x - 2, f"combined drift leaked into x: {x_arg}"
    assert y_arg == zone.y - 2, f"combined drift leaked into y: {y_arg}"


def test_overlay_zones_source_has_no_offset_arithmetic() -> None:
    """Static scan: reject `self.x ± offset_x` / `self.y ± offset_y` patterns."""
    src = _OVERLAY_ZONES.read_text()
    forbidden = [
        re.compile(r"self\.x\s*[+\-]\s*\d+\s*\+\s*offset_x"),
        re.compile(r"self\.x\s*\+\s*offset_x(?!\s*=)"),
        re.compile(r"self\.y\s*[+\-]\s*\d+\s*\+\s*offset_y"),
        re.compile(r"scroll_y\s*\+\s*offset_y"),
    ]
    for pattern in forbidden:
        matches = pattern.findall(src)
        reachable_matches = [m for m in matches if not _is_in_guarded_block(src, m)]
        assert not reachable_matches, (
            f"overlay_zones.py contains drift-applying arithmetic: "
            f"pattern={pattern.pattern!r}, matches={reachable_matches!r}. "
            f"position_offset_x/y must remain neutralized per 2026-04-23 directive."
        )


def _is_in_guarded_block(src: str, match_text: str) -> bool:
    """After neutralization, the arithmetic still appears but only where offset_x/y = 0.

    The current implementation keeps the `+ offset_x` / `+ offset_y` expressions in
    source but with the inputs hard-zeroed. Confirm that the surrounding block
    contains the hard-zero assignments.
    """
    idx = src.find(match_text)
    if idx < 0:
        return False
    window = src[max(0, idx - 400) : idx]
    return "offset_x = 0" in window and "offset_y = 0" in window
