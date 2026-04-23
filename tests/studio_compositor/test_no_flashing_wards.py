"""2026-04-23 operator directive: no flashing of any kind on any homage ward.

Comprehensive regression pin covering ALL ward rendering paths, not
just album_overlay. Extends the Phase B3 alpha-constant test to scan
every cairo source for time-varying-alpha patterns.

Background:
- Phase B3 (#1233) eliminated alpha-beat modulation in ``album_overlay.py``
  and added a regex-lint scoped to that file only.
- Operator reported 2026-04-23: "CBIP and any other wards that are
  flashing" — the scope was too narrow. Other sources still applied
  sinusoidal alpha via ``paint_breathing_alpha`` + ``_flash_alpha``
  + ``ward_properties.stroke_border_pulse`` + ``token_pole`` shimmer.
- This fix neuters all four primitives:
  1. ``paint_breathing_alpha`` returns ``baseline`` (constant, no sine)
  2. ``_flash_alpha`` returns 0.0 (no inverse-flash envelope)
  3. ``stroke_border_pulse`` uses ``a_base`` directly (no phase mod)
  4. ``ward_properties._apply_scale_bump`` disabled (off-screen fix)
- Static scan below is the regression guard.
"""

from __future__ import annotations

import math
import re
import time
from pathlib import Path

from agents.studio_compositor.homage.emissive_base import paint_breathing_alpha
from agents.studio_compositor.legibility_sources import _flash_alpha

_REPO_ROOT = Path(__file__).parents[2]
_STUDIO_COMPOSITOR = _REPO_ROOT / "agents" / "studio_compositor"


# ── Runtime invariants ──────────────────────────────────────────────────────


def test_paint_breathing_alpha_is_constant_over_time() -> None:
    """Samples paint_breathing_alpha across 60 time-points; all equal."""
    samples = [paint_breathing_alpha(t / 10.0, hz=1.0, phase=0.0) for t in range(60)]
    first = samples[0]
    for i, s in enumerate(samples):
        assert s == first, f"paint_breathing_alpha modulated at t={i / 10.0}: {s} != {first}"


def test_paint_breathing_alpha_returns_baseline() -> None:
    """The returned constant IS the baseline arg."""
    assert paint_breathing_alpha(0.0, baseline=0.5) == 0.5
    assert paint_breathing_alpha(1.0, baseline=0.85) == 0.85
    assert paint_breathing_alpha(5.0, baseline=0.3, amplitude=0.9, hz=3.0) == 0.3


def test_flash_alpha_always_zero() -> None:
    """_flash_alpha never returns a non-zero value."""
    now = time.monotonic()
    assert _flash_alpha(now, None) == 0.0
    assert _flash_alpha(now, now) == 0.0
    assert _flash_alpha(now, now - 0.1) == 0.0
    assert _flash_alpha(now, now - 0.5) == 0.0
    assert _flash_alpha(now, now + 0.1) == 0.0


# ── Static scan across all cairo sources ────────────────────────────────────


_FORBIDDEN_PATTERNS = [
    # paint_with_alpha(... sin/cos/time/beat/bass/rms ...)
    re.compile(
        r"paint_with_alpha\s*\([^)]*\b(?:math\.sin|math\.cos|time\.monotonic|"
        r"time\.time|\bsin\(|\bcos\(|beat_smooth|beat_pulse|_beat_|bass_band|"
        r"mid_band|treble_band|rms|onset|zcr|energy|shimmer|_pulse\b|pulse_phase|"
        r"pulse_alpha)"
    ),
    # set_source_rgba(r, g, b, <expr with sin/cos/beat/...>) — 4th arg
    re.compile(
        r"set_source_rgba\s*\([^,)]+,\s*[^,)]+,\s*[^,)]+,\s*"
        r"[^)]*?(?:math\.sin|math\.cos|\bsin\(|\bcos\(|beat_smooth|beat_pulse|"
        r"_beat_|bass_band|rms|onset|shimmer|pulse_alpha|pulse_phase|_wave_)"
    ),
    # Simpler: "alpha = baseline + amp * sin(...)" — explicit modulation forms
    re.compile(r"(?:alpha|_alpha|pulse|shimmer|breath)\s*=\s*[^\n]*?\b(?:math\.)?sin\("),
]

_ALLOWLIST_PATHS: tuple[str, ...] = (
    # Audio DSP module: analyses audio, writes to SHM bus. Not a cairo
    # ward renderer — its internal sin/cos is for signal analysis.
    "agents/studio_compositor/audio_capture.py",
    # Reactivity adapter: converts bus signals to translate offsets etc.
    "agents/studio_compositor/reactivity_adapters.py",
    # Scene classifier: the word ``flash`` refers to Gemini Flash LLM.
    "agents/studio_compositor/scene_classifier.py",
)


def _path_is_allowlisted(rel: Path) -> bool:
    s = str(rel).replace("\\", "/")
    return any(s.endswith(allowed) for allowed in _ALLOWLIST_PATHS)


def test_no_time_varying_alpha_in_any_cairo_source() -> None:
    """Every file under ``agents/studio_compositor/`` and its subpackages
    must be free of time-varying alpha expressions. Homage sources live
    under ``.../homage/``; legibility sources directly under the package.
    """
    offending: list[tuple[Path, int, str, str]] = []
    for py in sorted(_STUDIO_COMPOSITOR.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        rel = py.relative_to(_REPO_ROOT)
        if _path_is_allowlisted(rel):
            continue
        text = py.read_text()
        for lineno, line in enumerate(text.splitlines(), 1):
            # Skip comment-only lines — they may narrate the forbidden pattern.
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            for pat in _FORBIDDEN_PATTERNS:
                m = pat.search(line)
                if m:
                    offending.append((rel, lineno, m.group(0), line.strip()))
                    break
    assert not offending, (
        "time-varying alpha expression detected in ward rendering code — "
        "feedback_no_blinking_homage_wards forbids this. Matches:\n"
        + "\n".join(f"  {p}:{n}  [{match!r}]  {snippet}" for p, n, match, snippet in offending)
    )


_ = math  # exported for potential future matrix-test extensions.
