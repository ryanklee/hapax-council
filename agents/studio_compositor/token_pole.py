"""token_pole.py — Golden Spiral token tracker over Vitruvian Man.

Da Vinci's Vitruvian Man (1490, public domain) as background. A golden
spiral overlaid on the figure — the token follows the spiral path from
outside in. Geometry is preserved pixel-for-pixel (spiral center,
navel anchor, 3 turns, 250 points) from the pre-HOMAGE revision; what
changed in #125 is purely aesthetic: the candy-rainbow palette is
replaced with the active :class:`HomagePackage`'s BitchX grammar —
Gruvbox/mIRC-grey skeleton + bright-identity accents. The rounded-
corner sepia card becomes a flat dark-terminal rectangle per HOMAGE
spec §5.5 (``rounded-corners`` is a refused anti-pattern).

Upper-left quadrant of the frame.

The per-tick logic lives in :class:`TokenPoleCairoSource`, which
conforms to the :class:`CairoSource` protocol and is driven by a
:class:`CairoSourceRunner` at 30fps on a background thread. The
pre-Phase-9 ``TokenPole`` wrapper was removed alongside the
``fx_chain._pip_draw`` legacy path in Phase 9 Task 29.
"""

from __future__ import annotations

import json
import logging
import math
import random
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .homage import get_active_package
from .homage.transitional_source import HomageTransitionalSource

if TYPE_CHECKING:
    import cairo  # noqa: F401

    from shared.homage_package import HomagePackage

log = logging.getLogger(__name__)

RENDER_FPS = 30

LEDGER_FILE = Path("/dev/shm/hapax-compositor/token-ledger.json")
VITRUVIAN_PATH = Path(__file__).parent.parent.parent / "assets" / "vitruvian_man_overlay.png"

# Natural size of the token-pole source — drawn at local origin (0, 0).
# The compositor places this surface at its assigned SurfaceSchema.geometry
# rather than hardcoding a canvas-relative position. The :class:`TokenPole`
# facade blits the output at (20, 20) for the legacy ``fx_chain._pip_draw``
# path until Phase 3 of the source-registry completion epic flips the
# render loop to walk LayoutState.
NATURAL_SIZE = 300

# Geometry invariants. These MUST stay constant per spec §Preservation
# Invariants — the navel anchor, the 3-turn spiral, the exponential
# decay coefficient and the starting-angle offset in ``_build_spiral``
# are load-bearing for the artefact's identity.
SPIRAL_CENTER_X = 0.50
SPIRAL_CENTER_Y = 0.52  # navel is slightly below center
SPIRAL_MAX_R = 0.45  # relative to overlay size

NUM_POINTS = 250
PHI = (1 + math.sqrt(5)) / 2

# --- Palette role names (HOMAGE spec §4.4) ---------------------------------
# The token-pole resolves all colour state through the active
# ``HomagePackage.palette`` at draw time; no hardcoded hex. The six
# roles below are the ones used by the trail gradient and the particle
# explosion. Ordered so the trail walks muted→bright via accent hops —
# a Gruvbox-monochrome skeleton with bright identity accents punching
# through, mirroring BitchX's grey-punctuation / bright-identity rule.
_TRAIL_ROLES: tuple[str, ...] = (
    "muted",
    "terminal_default",
    "accent_cyan",
    "accent_yellow",
    "accent_magenta",
    "bright",
)

# The explosion palette re-uses the accent roles plus ``bright``. All
# references are symbolic — a palette swap (e.g. consent-safe variant)
# recolours particles in flight without needing to re-emit them.
_EXPLOSION_ROLES: tuple[str, ...] = (
    "accent_cyan",
    "accent_magenta",
    "accent_yellow",
    "accent_green",
    "accent_red",
    "bright",
)


def _build_spiral(cx: float, cy: float, max_r: float, n: int) -> list[tuple[float, float]]:
    """Golden spiral from outside in, in pixel coordinates."""
    points = []
    max_turns = 3.0
    max_theta = max_turns * 2 * math.pi
    for i in range(n):
        t = i / (n - 1)
        theta = max_theta * (1 - t)
        r = max_r * math.exp(-0.2 * theta)
        x = cx + r * math.cos(theta + 0.5)  # offset so spiral starts upper-right
        y = cy + r * math.sin(theta + 0.5)
        points.append((x, y))
    return points


def _resolve_package() -> HomagePackage:
    """Return the active HomagePackage, or the BitchX fallback.

    The runtime returns ``None`` under the consent-safe layout
    (HOMAGE disabled per axiom ``it-irreversible-broadcast``). The
    token-pole still has to paint *something*, so we fall through to
    the baseline BitchX package — its greyscale grammar is already
    consent-safe by construction (no operator-identity accent that
    could leak into the broadcast; the consent-safe variant collapses
    all accents to the same grey).
    """
    pkg = get_active_package()
    if pkg is not None:
        return pkg
    from .homage.bitchx import BITCHX_PACKAGE

    return BITCHX_PACKAGE


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "role_index", "alpha", "size", "born")

    def __init__(self, x: float, y: float) -> None:
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3, 14)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - random.uniform(1, 4)
        # Palette-role index; resolved at draw time so a mid-flight
        # package swap recolours particles in place.
        self.role_index = random.randrange(len(_EXPLOSION_ROLES))
        self.alpha = 1.0
        self.size = random.uniform(3, 10)
        self.born = time.monotonic()

    def tick(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2
        self.vx *= 0.97
        self.vy *= 0.97
        age = time.monotonic() - self.born
        self.alpha = max(0, 1.0 - age / 1.5)
        self.size *= 0.98
        return self.alpha > 0.03


class TokenPoleCairoSource(HomageTransitionalSource):
    """HomageTransitionalSource implementation for the token-pole overlay.

    Owns the spiral path, animation state (position easing, pulse
    phase), particle system, ledger cache and background image. The
    runner calls :meth:`render_content` once per tick on a background
    thread — this drives the internal tick-state update (ledger I/O,
    easing, particle physics) AND the drawing, so the animation cadence
    matches the runner's target FPS (30).
    """

    def __init__(self) -> None:
        super().__init__(source_id="token_pole")
        self._position: float = 0.0
        self._target_position: float = 0.0
        self._explosions: int = 0
        self._total_tokens: int = 0
        self._threshold: int = 0
        self._particles: list[Particle] = []
        self._last_read: float = 0
        self._last_explosion_count: int = 0
        self._pulse: float = 0.0
        self._bg_surface: Any = None
        self._bg_loaded = False
        # Build spiral in local natural-size coordinates (origin at 0, 0).
        cx = NATURAL_SIZE * SPIRAL_CENTER_X
        cy = NATURAL_SIZE * SPIRAL_CENTER_Y
        max_r = NATURAL_SIZE * SPIRAL_MAX_R
        self._spiral = _build_spiral(cx, cy, max_r, NUM_POINTS)

    def render_content(
        self,
        cr: cairo.Context,
        canvas_w: int,
        canvas_h: int,
        t: float,
        state: dict[str, Any],
    ) -> None:
        """Advance internal animation state then paint a full scene.

        Per-ward visibility + alpha modulation happens in the runner
        (``cairo_source.CairoSourceRunner._render_one_frame``) so this
        method draws unconditionally. The runner's
        :func:`ward_render_scope` wrap has already short-circuited the
        call when the ward is hidden.
        """
        self._tick_state()
        self._draw_scene(cr)

    def _tick_state(self) -> None:
        """Ledger I/O, position easing, pulse phase, particle physics."""
        now = time.monotonic()
        if now - self._last_read > 0.5:
            self._last_read = now
            self._read_ledger()
        diff = self._target_position - self._position
        self._position += diff * 0.06
        self._pulse += 0.1
        self._particles = [p for p in self._particles if p.tick()]

    def _read_ledger(self) -> None:
        try:
            if LEDGER_FILE.exists():
                data = json.loads(LEDGER_FILE.read_text())
                self._target_position = data.get("pole_position", 0.0)
                self._total_tokens = data.get("total_tokens", 0)
                active = max(1, data.get("active_viewers", 1))
                self._threshold = int(5000 * math.log2(1 + math.log2(1 + active)))
                new_explosions = data.get("explosions", 0)
                if new_explosions > self._last_explosion_count and self._last_explosion_count > 0:
                    self._spawn_explosion()
                self._last_explosion_count = new_explosions
                self._explosions = new_explosions
        except (json.JSONDecodeError, OSError):
            pass

    def _spawn_explosion(self) -> None:
        cx = NATURAL_SIZE * SPIRAL_CENTER_X
        cy = NATURAL_SIZE * SPIRAL_CENTER_Y
        for _ in range(60):
            self._particles.append(Particle(cx, cy))

    def _load_bg(self, cr: Any) -> None:
        """Load Vitruvian Man as cairo surface (once).

        Phase 3d: delegates to the shared ImageLoader, which handles
        both PNG (native cairo) and JPEG (PIL → premultiplied ARGB)
        decode paths in one place. Replaces the previous PNG-or-temp-
        file fallback that wrote a temporary PNG just to call
        ``create_from_png`` on it.
        """
        del cr  # unused; the loader doesn't need a draw context
        if self._bg_loaded:
            return
        self._bg_loaded = True
        if not VITRUVIAN_PATH.exists():
            return
        from .image_loader import get_image_loader

        self._bg_surface = get_image_loader().load(VITRUVIAN_PATH)
        if self._bg_surface is not None:
            log.info(
                "Vitruvian Man loaded (%dx%d)",
                self._bg_surface.get_width(),
                self._bg_surface.get_height(),
            )
        else:
            log.warning("Failed to load Vitruvian Man background")

    def _draw_scene(self, cr: Any) -> None:
        self._load_bg(cr)

        pkg = _resolve_package()
        palette = pkg.palette

        # --- Flat dark terminal card --------------------------------------
        # Spec §5.5 refuses ``rounded-corners``; replace the prior sepia
        # rounded rect with a flat rectangle in the package's
        # ``background`` role. Near-black, α≈0.9 so the shader surface
        # still breathes through.
        bg_r, bg_g, bg_b, bg_a = palette.background
        cr.set_source_rgba(bg_r, bg_g, bg_b, bg_a)
        cr.rectangle(0, 0, NATURAL_SIZE, NATURAL_SIZE)
        cr.fill()

        # --- Vitruvian Man (transparent PNG, full alpha — ink lines pop) ---
        if self._bg_surface is not None:
            cr.save()
            sw = self._bg_surface.get_width()
            sh = self._bg_surface.get_height()
            scale = NATURAL_SIZE / max(sw, sh) if max(sw, sh) > 0 else 1
            cr.scale(scale, scale)
            cr.set_source_surface(self._bg_surface, 0, 0)
            cr.paint_with_alpha(1.0)
            cr.restore()

        # --- Spiral guide line (muted grey skeleton) ----------------------
        muted_r, muted_g, muted_b, _ = palette.muted
        cr.set_source_rgba(muted_r, muted_g, muted_b, 0.30)
        cr.set_line_width(1.0)
        for i, (x, y) in enumerate(self._spiral):
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.stroke()

        # --- Trail — muted→bright gradient via accent hops ----------------
        idx = int(self._position * (NUM_POINTS - 1))
        if idx > 1:
            cr.set_line_width(3.5)
            trail_rgba = tuple(pkg.resolve_colour(role) for role in _TRAIL_ROLES)  # type: ignore[arg-type]
            num_c = len(trail_rgba)
            for i in range(1, idx):
                progress = i / idx
                ci = progress * (num_c - 1)
                c0 = trail_rgba[int(ci) % num_c]
                c1 = trail_rgba[(int(ci) + 1) % num_c]
                f = ci - int(ci)
                r = c0[0] + (c1[0] - c0[0]) * f
                g = c0[1] + (c1[1] - c0[1]) * f
                b = c0[2] + (c1[2] - c0[2]) * f
                alpha = 0.15 + 0.65 * (progress**1.5)
                cr.set_source_rgba(r, g, b, alpha)
                x0, y0 = self._spiral[i - 1]
                x, y = self._spiral[i]
                cr.move_to(x0, y0)
                cr.line_to(x, y)
                cr.stroke()

        # --- Token glyph (bright identity ring, terminal body) ------------
        if idx < len(self._spiral):
            gx, gy = self._spiral[idx]
        else:
            gx = NATURAL_SIZE * SPIRAL_CENTER_X
            gy = NATURAL_SIZE * SPIRAL_CENTER_Y

        pulse_r = math.sin(self._pulse) * 2
        bounce_y = math.sin(self._pulse * 1.7) * 1.5
        glyph_r = 11 + pulse_r

        ring_r, ring_g, ring_b, _ = palette.accent_magenta
        body_r, body_g, body_b, _ = palette.accent_yellow
        inner_r, inner_g, inner_b, _ = palette.bright
        cheek_r, cheek_g, cheek_b, _ = palette.accent_red

        # Sparkle trail — bright identity, thinning
        for i in range(1, 4):
            trail_idx = max(0, idx - i * 5)
            if trail_idx < len(self._spiral):
                tx, ty = self._spiral[trail_idx]
                sr = (4 - i) * 1.5
                cr.set_source_rgba(inner_r, inner_g, inner_b, 0.6 - i * 0.15)
                cr.arc(tx, ty, sr, 0, 2 * math.pi)
                cr.fill()

        # Outer glow (accent_magenta, low alpha)
        cr.set_source_rgba(ring_r, ring_g, ring_b, 0.25)
        cr.arc(gx, gy + bounce_y, glyph_r + 8, 0, 2 * math.pi)
        cr.fill()

        # Identity ring
        cr.set_source_rgba(ring_r, ring_g, ring_b, 0.70)
        cr.set_line_width(2.5)
        cr.arc(gx, gy + bounce_y, glyph_r + 2, 0, 2 * math.pi)
        cr.stroke()

        # Body — accent_yellow (mIRC 8 highlight)
        cr.set_source_rgba(body_r, body_g, body_b, 0.95)
        cr.arc(gx, gy + bounce_y, glyph_r, 0, 2 * math.pi)
        cr.fill()

        # Center — bright identity
        cr.set_source_rgba(inner_r, inner_g, inner_b, 0.85)
        cr.arc(gx, gy + bounce_y, glyph_r * 0.55, 0, 2 * math.pi)
        cr.fill()

        # Cheeks — accent_red, half-alpha
        cr.set_source_rgba(cheek_r, cheek_g, cheek_b, 0.50)
        cr.arc(gx - 5, gy + bounce_y + 2, 3, 0, 2 * math.pi)
        cr.fill()
        cr.arc(gx + 5, gy + bounce_y + 2, 3, 0, 2 * math.pi)
        cr.fill()

        # Eyes + smile — muted (terminal-monochrome face on a bright ring)
        cr.set_source_rgba(muted_r, muted_g, muted_b, 1.0)
        cr.arc(gx - 3.5, gy + bounce_y - 2, 1.5, 0, 2 * math.pi)
        cr.fill()
        cr.arc(gx + 3.5, gy + bounce_y - 2, 1.5, 0, 2 * math.pi)
        cr.fill()

        cr.set_line_width(1.2)
        cr.arc(gx, gy + bounce_y + 1, 3.5, 0.2, math.pi - 0.2)
        cr.stroke()

        # --- Particles ----------------------------------------------------
        # Phase 2 of the source-registry completion epic dropped the old
        # Goal / Explosion-count / Token-count labels because they used
        # to live in the canvas margin just outside the overlay card,
        # which no longer exists once the source renders into a
        # self-contained 300×300 surface. The ledger state is still
        # tracked in ``_threshold`` / ``_explosions`` / ``_total_tokens``
        # so a future inside-the-card label layout can render them
        # without re-plumbing state.
        #
        # Particle colour is resolved per-frame via the active palette;
        # a mid-flight package swap recolours particles already in flight.
        for p in self._particles:
            role = _EXPLOSION_ROLES[p.role_index]
            pr, pg, pb, _ = pkg.resolve_colour(role)  # type: ignore[arg-type]
            cr.set_source_rgba(pr, pg, pb, p.alpha)
            cr.arc(p.x, p.y, p.size, 0, 2 * math.pi)
            cr.fill()


# The pre-Phase-9 ``TokenPole`` facade has been removed. Rendering now
# flows through ``TokenPoleCairoSource`` + the SourceRegistry + the
# layout walk in ``fx_chain.pip_draw_from_layout``.
