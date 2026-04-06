"""token_pole.py — Token Pole visual overlay for the studio compositor.

Renders a vertical progress bar on the left side of the screen with a climbing
token glyph. When the pole fills, triggers a particle explosion. Reads state
from /dev/shm/hapax-compositor/token-ledger.json (written by token_ledger.py).

Visual elements:
  - Vertical pole (left sidebar, ~40px wide)
  - Token glyph that climbs from bottom to top
  - Gradient fill showing progress
  - Particle explosion when pole fills (vampire survivor style)
  - Token count display
  - Explosion counter

All rendering via Cairo on the post-FX cairooverlay.
"""

from __future__ import annotations

import json
import logging
import math
import random
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

LEDGER_FILE = Path("/dev/shm/hapax-compositor/token-ledger.json")

# Layout
POLE_X = 30  # left margin
POLE_Y_TOP = 80
POLE_Y_BOTTOM = 1000
POLE_WIDTH = 32
POLE_HEIGHT = POLE_Y_BOTTOM - POLE_Y_TOP

# Colors (gruvbox-adjacent)
COLOR_POLE_BG = (0.12, 0.12, 0.12, 0.7)
COLOR_POLE_FILL_BOTTOM = (0.98, 0.28, 0.20)  # red/orange at bottom
COLOR_POLE_FILL_TOP = (0.72, 0.73, 0.15)  # yellow-green at top
COLOR_GLYPH = (1.0, 0.85, 0.30)  # gold token
COLOR_TEXT = (0.92, 0.86, 0.70, 0.9)
COLOR_EXPLOSION = [
    (1.0, 0.85, 0.30),  # gold
    (0.98, 0.28, 0.20),  # red
    (0.72, 0.73, 0.15),  # green
    (0.51, 0.65, 0.60),  # teal
    (0.83, 0.53, 0.10),  # orange
    (0.69, 0.38, 0.53),  # purple
]


class Particle:
    """A single explosion particle with physics."""

    __slots__ = ("x", "y", "vx", "vy", "color", "alpha", "size", "born")

    def __init__(self, x: float, y: float) -> None:
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3, 12)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - random.uniform(2, 6)  # upward bias
        self.color = random.choice(COLOR_EXPLOSION)
        self.alpha = 1.0
        self.size = random.uniform(4, 12)
        self.born = time.monotonic()

    def tick(self) -> bool:
        """Update particle. Returns False when dead."""
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.3  # gravity
        self.vx *= 0.98  # drag
        age = time.monotonic() - self.born
        self.alpha = max(0, 1.0 - age / 1.2)
        self.size *= 0.97
        return self.alpha > 0.03


class TokenPole:
    """Renders the token pole + particles on the post-FX cairooverlay."""

    def __init__(self) -> None:
        self._position: float = 0.0
        self._target_position: float = 0.0
        self._explosions: int = 0
        self._total_tokens: int = 0
        self._particles: list[Particle] = []
        self._last_read: float = 0
        self._last_explosion_count: int = 0
        self._glyph_wobble: float = 0.0

    def tick(self) -> None:
        """Read ledger state and update animation."""
        now = time.monotonic()

        # Read ledger every 0.5s (not every frame)
        if now - self._last_read > 0.5:
            self._last_read = now
            self._read_ledger()

        # Smooth pole position (ease toward target)
        diff = self._target_position - self._position
        self._position += diff * 0.08  # smooth easing

        # Glyph wobble
        self._glyph_wobble += 0.15

        # Tick particles
        self._particles = [p for p in self._particles if p.tick()]

    def _read_ledger(self) -> None:
        """Read token-ledger.json for current state."""
        try:
            if LEDGER_FILE.exists():
                data = json.loads(LEDGER_FILE.read_text())
                self._target_position = data.get("pole_position", 0.0)
                self._total_tokens = data.get("total_tokens", 0)
                new_explosions = data.get("explosions", 0)

                # Trigger particle explosion if explosion count increased
                if new_explosions > self._last_explosion_count and self._last_explosion_count > 0:
                    self._spawn_explosion()
                self._last_explosion_count = new_explosions
                self._explosions = new_explosions
        except (json.JSONDecodeError, OSError):
            pass

    def _spawn_explosion(self) -> None:
        """Spawn 50 particles from the top of the pole."""
        cx = POLE_X + POLE_WIDTH / 2
        cy = POLE_Y_TOP
        for _ in range(50):
            self._particles.append(Particle(cx, cy))
        log.info("Token pole EXPLOSION! (%d particles)", 50)

    def draw(self, cr: Any) -> None:
        """Render the token pole on the cairooverlay."""
        import cairo

        # --- Pole background ---
        cr.set_source_rgba(*COLOR_POLE_BG)
        cr.rectangle(POLE_X, POLE_Y_TOP, POLE_WIDTH, POLE_HEIGHT)
        cr.fill()

        # --- Pole border ---
        cr.set_source_rgba(0.4, 0.4, 0.4, 0.5)
        cr.set_line_width(1.5)
        cr.rectangle(POLE_X, POLE_Y_TOP, POLE_WIDTH, POLE_HEIGHT)
        cr.stroke()

        # --- Gradient fill ---
        fill_height = int(POLE_HEIGHT * self._position)
        if fill_height > 0:
            fill_y = POLE_Y_BOTTOM - fill_height
            pat = cairo.LinearGradient(POLE_X, POLE_Y_BOTTOM, POLE_X, fill_y)
            pat.add_color_stop_rgba(0, *COLOR_POLE_FILL_BOTTOM, 0.9)
            pat.add_color_stop_rgba(1, *COLOR_POLE_FILL_TOP, 0.9)
            cr.set_source(pat)
            cr.rectangle(POLE_X + 2, fill_y, POLE_WIDTH - 4, fill_height)
            cr.fill()

        # --- Token glyph (circle with T) ---
        glyph_y = POLE_Y_BOTTOM - fill_height
        glyph_x = POLE_X + POLE_WIDTH / 2
        wobble_x = math.sin(self._glyph_wobble) * 2
        glyph_r = 14

        # Glow
        cr.set_source_rgba(*COLOR_GLYPH, 0.3)
        cr.arc(glyph_x + wobble_x, glyph_y, glyph_r + 4, 0, 2 * math.pi)
        cr.fill()

        # Token body
        cr.set_source_rgba(*COLOR_GLYPH, 0.95)
        cr.arc(glyph_x + wobble_x, glyph_y, glyph_r, 0, 2 * math.pi)
        cr.fill()

        # Token border
        cr.set_source_rgba(0.6, 0.5, 0.1, 0.8)
        cr.set_line_width(2)
        cr.arc(glyph_x + wobble_x, glyph_y, glyph_r, 0, 2 * math.pi)
        cr.stroke()

        # "T" on the token
        cr.set_source_rgba(0.15, 0.1, 0.0, 1.0)
        cr.select_font_face("monospace", 0, 1)  # bold
        cr.set_font_size(16)
        cr.move_to(glyph_x + wobble_x - 5, glyph_y + 6)
        cr.show_text("T")

        # --- Goal marker at top ---
        cr.set_source_rgba(*COLOR_TEXT)
        cr.select_font_face("monospace", 0, 0)
        cr.set_font_size(11)

        # Explosion count
        if self._explosions > 0:
            cr.move_to(POLE_X - 2, POLE_Y_TOP - 8)
            cr.show_text(f"x{self._explosions}")

        # Token count at bottom
        if self._total_tokens > 0:
            label = self._format_tokens(self._total_tokens)
            cr.set_font_size(10)
            cr.move_to(POLE_X - 5, POLE_Y_BOTTOM + 18)
            cr.show_text(label)

        # Percentage
        pct = int(self._position * 100)
        cr.set_font_size(10)
        cr.move_to(POLE_X + 2, POLE_Y_BOTTOM + 32)
        cr.show_text(f"{pct}%")

        # --- Particles ---
        for p in self._particles:
            cr.set_source_rgba(*p.color, p.alpha)
            cr.arc(p.x, p.y, p.size, 0, 2 * math.pi)
            cr.fill()

    @staticmethod
    def _format_tokens(n: int) -> str:
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:.1f}K"
        return str(n)
