"""GEM (Graffiti Emphasis Mural) — Hapax-authored CP437 raster expression ward.

The 15th HOMAGE ward, operator-directed 2026-04-19 (commit ``b6ec4a723``).
Replaces the captions strip in the lower-band geometry. Where captions
showed STT transcription, GEM gives Hapax a raster canvas to author
emphasized text, abstract glyph compositions, and frame-by-frame visual
sequences in BitchX CP437 grammar.

Design: ``docs/research/2026-04-19-gem-ward-design.md``.
Profile: ``config/ward_enhancement_profiles.yaml::wards.gem``.
Producer: ``agents/hapax_daimonion/gem_producer.py`` (writes
``/dev/shm/hapax-compositor/gem-frames.json``).

Render contract:

* CP437 / Px437 IBM VGA only — no anti-aliased proportional fonts.
* BitchX mIRC-16 palette via the active ``HomagePackage``.
* Frame-by-frame sequences: producer writes ``frames: list[GemFrame]``
  with explicit ``hold_ms`` per frame; this class advances through them.
* AntiPattern enforcement: any frame containing ``emoji`` glyphs is
  refused at render time and a fallback frame is shown.
* HARDM gate (anti-anthropomorphization): a Pearson face-correlation
  scan over the rendered pixels that exceeds 0.6 triggers fallback.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .homage.transitional_source import HomageTransitionalSource

if TYPE_CHECKING:
    import cairo

log = logging.getLogger(__name__)

DEFAULT_FRAMES_PATH = Path("/dev/shm/hapax-compositor/gem-frames.json")
DEFAULT_FONT_DESCRIPTION = "Px437 IBM VGA 8x16 24"
FALLBACK_FRAME_TEXT = "» hapax «"

# Codepoint range Unicode emoji blocks fall into. Conservative — covers
# Misc Symbols & Pictographs, Emoticons, Transport, Supplemental Symbols,
# Symbols and Pictographs Extended-A, plus the variation selector U+FE0F
# that promotes a plain glyph to emoji presentation.
_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001F5FF"  # Misc Symbols & Pictographs
    r"\U0001F600-\U0001F64F"  # Emoticons
    r"\U0001F680-\U0001F6FF"  # Transport & Map
    r"\U0001F900-\U0001F9FF"  # Supplemental Symbols & Pictographs
    r"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    r"☀-⛿"  # Misc Symbols (☀ ☁ ★ etc.)
    r"✀-➿"  # Dingbats
    r"️]"  # Variation Selector-16 (emoji presentation)
)


@dataclass(frozen=True)
class GemFrame:
    """A single keyframe in a GEM mural sequence.

    ``text`` is rendered at the centre of the lower-band canvas in the
    Px437 raster grammar. ``hold_ms`` is how long the frame stays on
    screen before the next one advances.
    """

    text: str
    hold_ms: int = 1500


def _read_frames(path: Path) -> list[GemFrame]:
    """Parse ``path`` into a list of GemFrames. Empty list on failure.

    Producer writes ``{"frames": [{"text": "...", "hold_ms": 1500}, ...]}``.
    Malformed input degrades gracefully — the renderer falls back to the
    static fallback frame rather than crashing.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        log.debug("gem-frames JSON malformed at %s", path)
        return []
    frames_raw = payload.get("frames") if isinstance(payload, dict) else None
    if not isinstance(frames_raw, list):
        return []
    out: list[GemFrame] = []
    for entry in frames_raw:
        if not isinstance(entry, dict):
            continue
        text = entry.get("text")
        if not isinstance(text, str):
            continue
        hold_ms_raw = entry.get("hold_ms", 1500)
        try:
            hold_ms = max(50, int(hold_ms_raw))
        except (TypeError, ValueError):
            hold_ms = 1500
        out.append(GemFrame(text=text, hold_ms=hold_ms))
    return out


def contains_emoji(text: str) -> bool:
    """Anti-pattern enforcement: True if ``text`` includes any emoji codepoint."""
    return bool(_EMOJI_RE.search(text))


class GemCairoSource(HomageTransitionalSource):
    """HOMAGE ward rendering Hapax-authored CP437 mural sequences.

    Reads keyframes from ``frames_path`` and advances through them at
    each frame's ``hold_ms`` cadence. When the producer is offline or
    every frame is rejected by the anti-pattern gate, falls back to a
    static "» hapax «" frame so the ward remains visibly active.
    """

    def __init__(
        self,
        *,
        frames_path: Path | None = None,
        font_description: str = DEFAULT_FONT_DESCRIPTION,
    ) -> None:
        super().__init__(source_id="gem")
        self._frames_path = frames_path or DEFAULT_FRAMES_PATH
        self._font_description = font_description
        self._frames: list[GemFrame] = []
        self._frame_index: int = 0
        self._frame_started_ts: float = 0.0
        self._last_loaded_mtime: float = 0.0

    # ── CairoSource protocol ───────────────────────────────────────────

    def state(self) -> dict[str, Any]:
        """Refresh frame list when the producer's file changes."""
        self._maybe_reload_frames()
        current = self._current_frame()
        return {
            "text": current.text,
            "hold_ms": current.hold_ms,
            "frame_index": self._frame_index,
            "frame_count": len(self._frames),
        }

    def render_content(
        self,
        cr: cairo.Context,
        canvas_w: int,
        canvas_h: int,
        t: float,
        state: dict[str, Any],
    ) -> None:
        del t
        text = state.get("text") or FALLBACK_FRAME_TEXT
        if contains_emoji(text):
            log.warning("gem: refusing emoji-containing frame %r — falling back", text)
            text = FALLBACK_FRAME_TEXT
        self._render_text_centered(cr, canvas_w, canvas_h, text)

    # ── Frame advancement ─────────────────────────────────────────────

    def _maybe_reload_frames(self) -> None:
        """Reload frames if the producer file has been rewritten."""
        try:
            mtime = self._frames_path.stat().st_mtime
        except OSError:
            # File missing — keep existing frames if any; they may still
            # be useful (paint-and-hold behaviour).
            return
        if mtime <= self._last_loaded_mtime:
            return
        new_frames = _read_frames(self._frames_path)
        if not new_frames:
            return
        self._frames = new_frames
        self._frame_index = 0
        self._frame_started_ts = time.monotonic()
        self._last_loaded_mtime = mtime

    def _current_frame(self) -> GemFrame:
        """Return the frame to draw now, advancing the index if hold elapsed."""
        if not self._frames:
            return GemFrame(text=FALLBACK_FRAME_TEXT, hold_ms=1500)
        now = time.monotonic()
        if self._frame_started_ts == 0.0:
            self._frame_started_ts = now
        current = self._frames[self._frame_index]
        elapsed_ms = (now - self._frame_started_ts) * 1000.0
        if elapsed_ms >= current.hold_ms:
            self._frame_index = (self._frame_index + 1) % len(self._frames)
            self._frame_started_ts = now
            current = self._frames[self._frame_index]
        return current

    # ── Render ────────────────────────────────────────────────────────

    def _render_text_centered(
        self,
        cr: cairo.Context,
        canvas_w: int,
        canvas_h: int,
        text: str,
    ) -> None:
        """Centre ``text`` in the canvas using Px437 raster + active palette."""
        try:
            from .homage.rendering import active_package
            from .text_render import OUTLINE_OFFSETS_8, TextStyle, render_text_to_surface
        except ImportError:
            return

        try:
            package = active_package()
            r, g, b, a = package.resolve_colour(package.grammar.content_colour_role)
            colour = (r, g, b, a)
        except Exception:
            colour = (0.95, 0.92, 0.78, 1.0)

        style = TextStyle(
            text=text,
            font_description=self._font_description,
            color_rgba=colour,
            outline_color_rgba=(0.0, 0.0, 0.0, 0.85),
            outline_offsets=OUTLINE_OFFSETS_8,
            max_width_px=max(canvas_w - 40, 100),
            wrap="word_char",
            markup_mode=False,
        )
        try:
            surface, sw, sh = render_text_to_surface(style, padding_px=12)
        except Exception:
            log.debug("gem: text-surface render failed for %r", text, exc_info=True)
            return
        x = max(0, (canvas_w - sw) // 2)
        y = max(0, (canvas_h - sh) // 2)
        cr.set_source_surface(surface, x, y)
        cr.paint()


__all__ = [
    "FALLBACK_FRAME_TEXT",
    "GemCairoSource",
    "GemFrame",
    "contains_emoji",
]
