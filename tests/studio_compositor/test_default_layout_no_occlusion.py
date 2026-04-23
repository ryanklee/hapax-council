"""2026-04-23 Gemini-reapproach Plan B Phase B1 regression pin.

Operator reported in session 2 (2026-04-23 06:34 → 13:01 UTC) that
HOMAGE wards were overlapping each other — HARDM's 256×256 block at
(1600, 20) was underneath thinking-indicator-tr (1620, 20) and
stance-indicator-tr (1800, 24), producing visible z-order collisions
on the broadcast even with z-dominance fixes in place.

This test enforces that no two HOMAGE / legibility / hothouse surfaces
geometrically overlap in the default layout. Axis-aligned rectangle
intersection check; surfaces are non-overlapping iff one's right-edge
is left-of or equal-to the other's left-edge OR one's bottom-edge is
above or equal-to the other's top-edge.

Only overlay surfaces are checked — `pip-*` quadrant surfaces host
multiple assigned sources and intentionally overlap with their own
content (reverie can pass through pip-ur, HARDM at hardm-dot-matrix-ur
can visually sit adjacent to pip-ur, etc.), and `video_out_*` surfaces
are output sinks outside the 1920×1080 rendering canvas.
"""

from __future__ import annotations

import json
from pathlib import Path

_DEFAULT_JSON = Path(__file__).parents[2] / "config" / "compositor-layouts" / "default.json"

# Surfaces to check for overlap. Upper-band (y < 400) overlay surfaces
# must not collide with each other; lower-band legibility + GEM must not
# collide either. pip-* hosts its assigned source; HARDM is adjacent to
# pip-ur intentionally; captions_strip is allowed to sit under the
# retired captions assignment.
_OVERLAY_SURFACE_IDS = {
    "activity-header-top",
    "stance-indicator-tr",
    "chat-legend-right",
    "grounding-ticker-bl",
    "impingement-cascade-midright",
    "recruitment-candidate-top",
    "thinking-indicator-tr",
    "pressure-gauge-ul",
    "activity-variety-log-mid",
    "whos-here-tr",
    "hardm-dot-matrix-ur",
    "gem-mural-bottom",
}


def _rects_intersect(a: dict, b: dict) -> bool:
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = ax1 + a["w"], ay1 + a["h"]
    bx1, by1 = b["x"], b["y"]
    bx2, by2 = bx1 + b["w"], by1 + b["h"]
    return not (ax2 <= bx1 or bx2 <= ax1 or ay2 <= by1 or by2 <= ay1)


def test_no_overlay_surface_overlap() -> None:
    raw = json.loads(_DEFAULT_JSON.read_text())
    geos = {
        s["id"]: s["geometry"]
        for s in raw["surfaces"]
        if s["id"] in _OVERLAY_SURFACE_IDS and s["geometry"]["kind"] == "rect"
    }
    missing = _OVERLAY_SURFACE_IDS - geos.keys()
    assert not missing, f"expected overlay surfaces missing from default.json: {missing}"

    pairs = sorted(geos.items())
    overlaps = []
    for i, (a_id, a) in enumerate(pairs):
        for b_id, b in pairs[i + 1 :]:
            if _rects_intersect(a, b):
                overlaps.append(
                    (a_id, (a["x"], a["y"], a["w"], a["h"]), b_id, (b["x"], b["y"], b["w"], b["h"]))
                )
    assert not overlaps, (
        "overlay surfaces must not geometrically overlap — z-order dominance "
        "is not sufficient for operator legibility. Collisions:\n"
        + "\n".join(f"  {a} {ag} overlaps {b} {bg}" for a, ag, b, bg in overlaps)
    )


def test_hardm_thinking_stance_whos_here_spatial_separation() -> None:
    """Explicit pin for the 2026-04-23 Plan B Phase B1 fix.

    The upper-right cluster (HARDM + thinking + stance + whos-here) was
    the specific operator complaint. Pins their new positions so a
    future refactor can't silently re-introduce the overlap.
    """
    raw = json.loads(_DEFAULT_JSON.read_text())
    geos = {s["id"]: s["geometry"] for s in raw["surfaces"] if s["geometry"]["kind"] == "rect"}

    hardm = geos["hardm-dot-matrix-ur"]
    thinking = geos["thinking-indicator-tr"]
    stance = geos["stance-indicator-tr"]
    whos = geos["whos-here-tr"]

    # Thinking must be to the LEFT of HARDM with some gap.
    assert thinking["x"] + thinking["w"] <= hardm["x"], (
        f"thinking-indicator-tr right edge ({thinking['x'] + thinking['w']}) must be "
        f"<= HARDM left edge ({hardm['x']})"
    )

    # Stance must be BELOW HARDM (fully below HARDM's bottom edge).
    hardm_bottom = hardm["y"] + hardm["h"]
    assert stance["y"] >= hardm_bottom, (
        f"stance-indicator-tr top ({stance['y']}) must be >= HARDM bottom ({hardm_bottom})"
    )

    # whos-here is stacked BELOW thinking-indicator (both left of HARDM).
    assert whos["y"] >= thinking["y"] + thinking["h"], (
        f"whos-here-tr top ({whos['y']}) must be >= "
        f"thinking-indicator-tr bottom ({thinking['y'] + thinking['h']})"
    )
    # whos-here must also be left of HARDM.
    assert whos["x"] + whos["w"] <= hardm["x"], (
        f"whos-here-tr right edge ({whos['x'] + whos['w']}) must be "
        f"<= HARDM left edge ({hardm['x']})"
    )
