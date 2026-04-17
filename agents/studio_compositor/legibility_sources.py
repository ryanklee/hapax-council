"""Legibility Cairo sources — on-frame authorship indicators.

Phase 4 of the volitional-grounded-director epic (PR #1017, spec §3.5).
These five sources render on-frame the director's current state so a
viewer can read Hapax's authorship without internal access:

- :class:`ActivityHeaderCairoSource` — current activity + gloss
- :class:`StanceIndicatorCairoSource` — current stance (Stance enum)
- :class:`ChatKeywordLegendCairoSource` — chat participation vocabulary
- :class:`GroundingProvenanceTickerCairoSource` — signals that grounded the last move
- (captions live in ``captions_source.py`` — already present)

Every source reads either ``/dev/shm/hapax-director/narrative-state.json``
(written by the director loop after each intent emission) or
``~/hapax-state/stream-experiment/director-intent.jsonl`` (tail for the
last line). Readers are wrapped in try/except; absent files render
neutral/empty states.

Typography + color per ``docs/logos-design-language.md`` §1.6/§3. The
design-language palette switches on working-mode toggle — these sources
read working_mode through the shared helper so no per-source wiring is
needed.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import cairo

from agents.studio_compositor.cairo_source import CairoSource

log = logging.getLogger(__name__)

_NARRATIVE_STATE = Path("/dev/shm/hapax-director/narrative-state.json")
_DIRECTOR_INTENT_JSONL = Path(
    os.path.expanduser("~/hapax-state/stream-experiment/director-intent.jsonl")
)
_WORKING_MODE_FILE = Path(os.path.expanduser("~/.cache/hapax/working-mode"))


# Palette tuples (r, g, b, a) — Solarized Dark (research) vs Gruvbox Hard
# Dark (rnd). Values come from docs/logos-design-language.md §3.
_PALETTE = {
    "research": {
        "fg_primary": (0.830, 0.830, 0.740, 1.0),  # base3
        "accent_nominal": (0.522, 0.601, 0.000, 1.0),  # green
        "accent_seeking": (0.797, 0.477, 0.022, 1.0),  # orange
        "accent_cautious": (0.708, 0.536, 0.000, 1.0),  # yellow
        "accent_warning": (0.796, 0.294, 0.086, 1.0),  # red
        "bg_overlay": (0.000, 0.169, 0.212, 0.75),  # base03 + alpha
    },
    "rnd": {
        "fg_primary": (0.922, 0.859, 0.699, 1.0),  # fg1
        "accent_nominal": (0.596, 0.591, 0.102, 1.0),  # green
        "accent_seeking": (0.843, 0.596, 0.129, 1.0),  # orange
        "accent_cautious": (0.843, 0.757, 0.490, 1.0),  # yellow
        "accent_warning": (0.800, 0.141, 0.114, 1.0),  # red
        "bg_overlay": (0.157, 0.157, 0.157, 0.78),  # bg0_h + alpha
    },
}


def _read_working_mode() -> str:
    try:
        if _WORKING_MODE_FILE.exists():
            text = _WORKING_MODE_FILE.read_text(encoding="utf-8").strip()
            if text in ("research", "rnd"):
                return text
    except Exception:
        pass
    return "research"


def _palette() -> dict:
    return _PALETTE[_read_working_mode()]


def _read_narrative_state() -> dict:
    try:
        if _NARRATIVE_STATE.exists():
            return json.loads(_NARRATIVE_STATE.read_text(encoding="utf-8"))
    except Exception:
        log.debug("narrative-state read failed", exc_info=True)
    return {}


def _read_latest_intent() -> dict:
    try:
        if _DIRECTOR_INTENT_JSONL.exists():
            # Efficient tail — read last 4 KiB.
            size = _DIRECTOR_INTENT_JSONL.stat().st_size
            with _DIRECTOR_INTENT_JSONL.open("rb") as fh:
                fh.seek(max(0, size - 4096))
                tail = fh.read().decode("utf-8", errors="ignore")
            lines = [line for line in tail.splitlines() if line.strip()]
            if lines:
                return json.loads(lines[-1])
    except Exception:
        log.debug("director-intent tail failed", exc_info=True)
    return {}


# ── 1. Activity header ────────────────────────────────────────────────────


class ActivityHeaderCairoSource(CairoSource):
    """Top-center strip: current activity (uppercase) + short gloss.

    Gloss comes from the highest-salience compositional impingement's
    narrative, truncated to ~48 chars.
    """

    def render(
        self,
        cr: cairo.Context,
        canvas_w: int,
        canvas_h: int,
        t: float,
        state: dict[str, Any],
    ) -> None:
        ns = _read_narrative_state()
        intent = _read_latest_intent()
        activity = (ns.get("activity") or intent.get("activity") or "—").upper()
        # Pull first compositional impingement's narrative as gloss.
        gloss = ""
        imps = intent.get("compositional_impingements") or []
        if imps:
            # Pick the highest-salience impingement
            best = max(imps, key=lambda i: i.get("salience", 0.0))
            gloss = str(best.get("narrative", ""))[:48]

        pal = _palette()
        _draw_rounded_rect(cr, 0, 0, canvas_w, canvas_h, 8, pal["bg_overlay"])

        cr.set_source_rgba(*pal["fg_primary"])
        cr.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(22)
        cr.move_to(16, 28)
        cr.show_text(activity)

        if gloss:
            cr.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(14)
            cr.move_to(16, 50)
            cr.show_text(gloss)


# ── 2. Stance indicator ───────────────────────────────────────────────────


_STANCE_COLORS = {
    "nominal": "accent_nominal",
    "seeking": "accent_seeking",
    "cautious": "accent_cautious",
    "degraded": "accent_cautious",
    "critical": "accent_warning",
}


class StanceIndicatorCairoSource(CairoSource):
    """Small top-right badge: current stance with colored dot."""

    def render(
        self,
        cr: cairo.Context,
        canvas_w: int,
        canvas_h: int,
        t: float,
        state: dict[str, Any],
    ) -> None:
        ns = _read_narrative_state()
        stance = str(ns.get("stance") or "nominal").lower()
        pal = _palette()
        accent_key = _STANCE_COLORS.get(stance, "accent_nominal")
        _draw_rounded_rect(cr, 0, 0, canvas_w, canvas_h, 6, pal["bg_overlay"])

        # Dot
        cr.set_source_rgba(*pal[accent_key])
        dot_r = 6
        cx = 14
        cy = canvas_h / 2
        cr.arc(cx, cy, dot_r, 0, 6.283185)
        cr.fill()

        # Label
        cr.set_source_rgba(*pal["fg_primary"])
        cr.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(13)
        cr.move_to(28, canvas_h / 2 + 5)
        cr.show_text(stance.upper())


# ── 3. Chat keyword legend ────────────────────────────────────────────────


# Hardcoded mapping (derived from the current PresetReactor keyword index).
# If the chat_reactor exposes a richer dynamic map in future, swap to read it.
_CHAT_KEYWORDS: list[tuple[str, str]] = [
    ("!glitch", "dense/intense"),
    ("!calm", "slow/textural"),
    ("!warm", "ambient/minimal"),
    ("!react", "beat/sound"),
    ("!vinyl", "turntable"),
    ("!study", "focused"),
]


class ChatKeywordLegendCairoSource(CairoSource):
    """Side strip listing chat keywords viewers can type."""

    def render(
        self,
        cr: cairo.Context,
        canvas_w: int,
        canvas_h: int,
        t: float,
        state: dict[str, Any],
    ) -> None:
        pal = _palette()
        _draw_rounded_rect(cr, 0, 0, canvas_w, canvas_h, 6, pal["bg_overlay"])

        cr.set_source_rgba(*pal["fg_primary"])
        cr.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(12)
        cr.move_to(8, 18)
        cr.show_text("CHAT VOCABULARY")

        cr.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(11)
        y = 40
        for keyword, meaning in _CHAT_KEYWORDS[:8]:
            cr.move_to(8, y)
            cr.show_text(f"{keyword}")
            cr.move_to(60, y)
            cr.set_source_rgba(*pal["accent_nominal"])
            cr.show_text(meaning)
            cr.set_source_rgba(*pal["fg_primary"])
            y += 18


# ── 4. Grounding provenance ticker ────────────────────────────────────────


class GroundingProvenanceTickerCairoSource(CairoSource):
    """Bottom-left diagnostic strip: which signals grounded the last move."""

    def render(
        self,
        cr: cairo.Context,
        canvas_w: int,
        canvas_h: int,
        t: float,
        state: dict[str, Any],
    ) -> None:
        intent = _read_latest_intent()
        prov = intent.get("grounding_provenance") or []
        pal = _palette()
        _draw_rounded_rect(cr, 0, 0, canvas_w, canvas_h, 4, pal["bg_overlay"])

        cr.set_source_rgba(*pal["fg_primary"])
        cr.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(11)

        label = "▸ " + " · ".join(str(s) for s in prov[:6]) if prov else "▸ (ungrounded)"
        cr.move_to(8, canvas_h / 2 + 4)
        cr.show_text(label[:120])


# ── Helpers ────────────────────────────────────────────────────────────────


def _draw_rounded_rect(
    cr: cairo.Context,
    x: float,
    y: float,
    w: float,
    h: float,
    r: float,
    fill_rgba: tuple[float, float, float, float],
) -> None:
    cr.new_path()
    cr.move_to(x + r, y)
    cr.line_to(x + w - r, y)
    cr.arc(x + w - r, y + r, r, -1.5708, 0)
    cr.line_to(x + w, y + h - r)
    cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
    cr.line_to(x + r, y + h)
    cr.arc(x + r, y + h - r, r, 1.5708, 3.1416)
    cr.line_to(x, y + r)
    cr.arc(x + r, y + r, r, 3.1416, 4.7124)
    cr.close_path()
    cr.set_source_rgba(*fill_rgba)
    cr.fill()


# ── Registry registration ─────────────────────────────────────────────────

# Do NOT register at import — the compositor layout loader calls
# get_cairo_source_class(name) and expects the registration to happen once.
# Wiring is done in agents.studio_compositor.cairo_sources.__init__.
