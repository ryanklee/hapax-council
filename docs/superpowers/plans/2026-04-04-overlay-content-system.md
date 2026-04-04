# Overlay Content System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded overlay text with a configurable content system: markdown/ANSI parsed via Pango, content sourced from cycling Obsidian notes or files.

**Architecture:** Overlay zones read `.md`/`.ansi` files from disk. A parser converts markdown or ANSI to Pango markup. PangoLayout objects are cached and re-rendered only on content change. A folder mode cycles through notes on a timer.

**Tech Stack:** Python, Cairo, Pango (via gi.repository), GStreamer cairooverlay

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `agents/studio_compositor/overlay_parser.py` | Create | Markdown-to-Pango and ANSI-to-Pango parsers |
| `agents/studio_compositor/overlay_zones.py` | Create | Zone config, file reading, folder cycling, Pango layout caching |
| `agents/studio_compositor/overlay.py` | Modify | Replace visual_layer text with Pango zone rendering |
| `agents/studio_compositor/state.py` | Modify | Tick overlay zone file watches in state loop |

---

### Task 1: Markdown and ANSI parsers

**Files:**
- Create: `agents/studio_compositor/overlay_parser.py`

- [ ] **Step 1: Create overlay_parser.py**

```python
"""Convert markdown and ANSI text to Pango markup for overlay rendering."""

from __future__ import annotations

import re

# Gruvbox-mapped ANSI 16-color palette
ANSI_COLORS: dict[int, str] = {
    30: "#282828", 31: "#cc241d", 32: "#98971a", 33: "#d79921",
    34: "#458588", 35: "#b16286", 36: "#689d6a", 37: "#a89984",
    90: "#928374", 91: "#fb4934", 92: "#b8bb26", 93: "#fabd2f",
    94: "#83a598", 95: "#d3869b", 96: "#8ec07c", 97: "#ebdbb2",
}


def markdown_to_pango(text: str) -> str:
    """Convert basic markdown to Pango markup."""
    # Strip YAML frontmatter
    text = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)

    # Escape Pango special characters first
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    # Headings (must come before bold since ## starts with bold-like pattern)
    text = re.sub(
        r"^## (.+)$", r'<span size="large"><b>\1</b></span>', text, flags=re.MULTILINE
    )
    text = re.sub(
        r"^# (.+)$", r'<span size="x-large"><b>\1</b></span>', text, flags=re.MULTILINE
    )

    # Bold, italic, strikethrough, code
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)
    text = re.sub(r"`(.+?)`", r'<tt>\1</tt>', text)

    # Bullet points: preserve as-is (Pango renders the unicode)

    return text.strip()


def ansi_to_pango(text: str) -> str:
    """Convert ANSI escape codes to Pango <span foreground> markup."""
    # Escape Pango special characters
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    result: list[str] = []
    current_fg: str | None = None
    i = 0

    while i < len(text):
        # Match ANSI escape sequence: ESC[ ... m
        m = re.match(r"\x1b\[([0-9;]*)m", text[i:])
        if m:
            codes = m.group(1).split(";") if m.group(1) else ["0"]
            for code_str in codes:
                code = int(code_str) if code_str.isdigit() else 0
                if code == 0:
                    # Reset
                    if current_fg:
                        result.append("</span>")
                        current_fg = None
                elif code in ANSI_COLORS:
                    if current_fg:
                        result.append("</span>")
                    current_fg = ANSI_COLORS[code]
                    result.append(f'<span foreground="{current_fg}">')
            i += m.end()
        else:
            result.append(text[i])
            i += 1

    if current_fg:
        result.append("</span>")

    return "".join(result)


def parse_overlay_content(text: str, is_ansi: bool = False) -> str:
    """Parse text to Pango markup based on format."""
    if is_ansi:
        return ansi_to_pango(text)
    return markdown_to_pango(text)
```

- [ ] **Step 2: Verify**

```bash
uv run python -c "from agents.studio_compositor.overlay_parser import markdown_to_pango, ansi_to_pango; print(markdown_to_pango('# Hello\n**bold** *italic*')); print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add agents/studio_compositor/overlay_parser.py
git commit -m "feat: markdown and ANSI to Pango markup parsers"
```

---

### Task 2: Overlay zone manager with folder cycling

**Files:**
- Create: `agents/studio_compositor/overlay_zones.py`

- [ ] **Step 1: Create overlay_zones.py**

```python
"""Overlay zone manager — reads content files, cycles folders, caches Pango layouts."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

from .overlay_parser import parse_overlay_content

log = logging.getLogger(__name__)

SNAPSHOT_DIR = Path("/dev/shm/hapax-compositor")

# Default zone configuration
ZONES: list[dict[str, Any]] = [
    {
        "id": "main",
        "folder": None,  # Set to a folder path to enable cycling
        "file": str(SNAPSHOT_DIR / "overlay-main.md"),
        "cycle_seconds": 45,
        "x": 20,
        "y": 160,
        "max_width": 700,
        "font": "JetBrains Mono 11",
        "color": (0.92, 0.86, 0.70, 0.9),
    },
    {
        "id": "art",
        "folder": None,
        "file": str(SNAPSHOT_DIR / "overlay-art.ansi"),
        "cycle_seconds": 60,
        "x": 20,
        "y": 800,
        "max_width": 900,
        "font": "MxPlus IBM VGA 9x16 12",
        "color": (0.92, 0.86, 0.70, 0.85),
    },
]


class OverlayZone:
    """Manages a single overlay content zone."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.id = config["id"]
        self.folder = config.get("folder")
        self.file = config.get("file")
        self.cycle_seconds = config.get("cycle_seconds", 45)
        self.x = config["x"]
        self.y = config["y"]
        self.max_width = config.get("max_width", 700)
        self.font_desc = config.get("font", "JetBrains Mono 11")
        self.color = config.get("color", (0.92, 0.86, 0.70, 0.9))

        # State
        self._layout: Any = None  # PangoLayout, cached
        self._content_hash: int = 0
        self._last_mtime: float = 0
        self._folder_files: list[Path] = []
        self._folder_index: int = 0
        self._folder_last_scan: float = 0
        self._cycle_start: float = 0

    def tick(self) -> None:
        """Called from state loop (~100ms). Check for content changes."""
        now = time.monotonic()

        if self.folder:
            self._tick_folder(now)
        elif self.file:
            self._tick_file()

    def _tick_folder(self, now: float) -> None:
        """Cycle through files in a folder."""
        folder = Path(self.folder).expanduser()
        if not folder.is_dir():
            return

        # Re-scan folder every 60s
        if now - self._folder_last_scan > 60.0 or not self._folder_files:
            self._folder_files = sorted(
                f for f in folder.iterdir()
                if f.suffix in (".md", ".ansi", ".txt") and f.is_file()
            )
            self._folder_last_scan = now
            if not self._folder_files:
                return

        # Cycle to next file
        if self._cycle_start == 0:
            self._cycle_start = now
        elif now - self._cycle_start >= self.cycle_seconds:
            self._folder_index = (self._folder_index + 1) % len(self._folder_files)
            self._cycle_start = now

        # Read current file
        if self._folder_files:
            idx = self._folder_index % len(self._folder_files)
            self._read_file(self._folder_files[idx])

    def _tick_file(self) -> None:
        """Read a single file if modified."""
        path = Path(self.file)
        if not path.exists():
            if self._content_hash != 0:
                self._layout = None
                self._content_hash = 0
            return
        try:
            mtime = os.path.getmtime(path)
            if mtime != self._last_mtime:
                self._read_file(path)
                self._last_mtime = mtime
        except OSError:
            pass

    def _read_file(self, path: Path) -> None:
        """Read file and update cached Pango markup."""
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return

        content_hash = hash(raw)
        if content_hash == self._content_hash:
            return

        is_ansi = path.suffix == ".ansi"
        markup = parse_overlay_content(raw, is_ansi=is_ansi)
        self._content_hash = content_hash
        self._pango_markup = markup
        self._layout = None  # Force layout rebuild on next render
        log.debug("Overlay zone '%s' updated from %s (%d chars)", self.id, path.name, len(raw))

    def render(self, cr: Any, canvas_w: int, canvas_h: int) -> None:
        """Render this zone's content onto the Cairo context using Pango."""
        if not hasattr(self, "_pango_markup") or not self._pango_markup:
            return

        import gi
        gi.require_version("Pango", "1.0")
        gi.require_version("PangoCairo", "1.0")
        from gi.repository import Pango, PangoCairo

        # Create or reuse layout
        if self._layout is None:
            layout = PangoCairo.create_layout(cr)
            font = Pango.FontDescription.from_string(self.font_desc)
            layout.set_font_description(font)
            layout.set_width(int(self.max_width * Pango.SCALE))
            layout.set_wrap(Pango.WrapMode.WORD_CHAR)
            layout.set_markup(self._pango_markup, -1)
            self._layout = layout

        # Draw background box
        _w, _h = self._layout.get_pixel_size()
        pad = 6
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.5)
        cr.rectangle(self.x - pad, self.y - pad, _w + pad * 2, _h + pad * 2)
        cr.fill()

        # Draw text
        cr.move_to(self.x, self.y)
        cr.set_source_rgba(*self.color)
        PangoCairo.show_layout(cr, self._layout)


class OverlayZoneManager:
    """Manages all overlay content zones."""

    def __init__(self, zone_configs: list[dict[str, Any]] | None = None) -> None:
        configs = zone_configs or ZONES
        self.zones = [OverlayZone(cfg) for cfg in configs]

    def tick(self) -> None:
        """Called from state loop. Updates all zones."""
        for zone in self.zones:
            zone.tick()

    def render(self, cr: Any, canvas_w: int, canvas_h: int) -> None:
        """Render all zones onto the Cairo context."""
        for zone in self.zones:
            zone.render(cr, canvas_w, canvas_h)
```

- [ ] **Step 2: Verify import**

```bash
uv run python -c "from agents.studio_compositor.overlay_zones import OverlayZoneManager; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add agents/studio_compositor/overlay_zones.py
git commit -m "feat: overlay zone manager — file/folder content with Pango rendering"
```

---

### Task 3: Wire zones into compositor overlay and state loop

**Files:**
- Modify: `agents/studio_compositor/overlay.py`
- Modify: `agents/studio_compositor/state.py`
- Modify: `agents/studio_compositor/compositor.py` (init zone manager)

- [ ] **Step 1: Initialize zone manager in compositor**

Read `agents/studio_compositor/compositor.py` and find where overlay state is initialized (likely in `__init__`). Add:

```python
from .overlay_zones import OverlayZoneManager
```

In `__init__`, after the overlay cache variables, add:

```python
self._overlay_zone_manager = OverlayZoneManager()
```

- [ ] **Step 2: Tick zones in state loop**

In `agents/studio_compositor/state.py`, in the `state_reader_loop` function, before the `time.sleep(0.1)` at the end, add:

```python
        # Tick overlay content zones (file watches + folder cycling)
        if hasattr(compositor, "_overlay_zone_manager"):
            compositor._overlay_zone_manager.tick()
```

- [ ] **Step 3: Render zones in overlay**

In `agents/studio_compositor/overlay.py`, in the `on_draw` function, after `render_visual_layer(compositor, cr, canvas_w, canvas_h)`, add:

```python
    # Render content overlay zones (markdown/ANSI via Pango)
    if hasattr(compositor, "_overlay_zone_manager"):
        compositor._overlay_zone_manager.render(cr, canvas_w, canvas_h)
```

Note: This renders the zones OUTSIDE the cache check, since zone content has its own caching via `_layout`. The zone render is sub-millisecond per zone when layout is cached.

- [ ] **Step 4: Verify compositor starts**

```bash
systemctl --user restart studio-compositor
sleep 15
systemctl --user status studio-compositor --no-pager | head -5
```

- [ ] **Step 5: Test with a markdown file**

```bash
echo '# Legomena Live
**building AI** + *making beats*
`24fps` shader pipeline' > /dev/shm/hapax-compositor/overlay-main.md
sleep 2
# Check the FX snapshot for visible overlay text
python3 -c "from PIL import Image; import numpy as np; img=np.array(Image.open('/dev/shm/hapax-compositor/fx-snapshot.jpg')); print(f'mean={img.mean():.1f}')"
```

- [ ] **Step 6: Commit**

```bash
git add agents/studio_compositor/overlay.py agents/studio_compositor/state.py agents/studio_compositor/compositor.py
git commit -m "feat: wire overlay zones into compositor — Pango rendering live"
```

---

### Task 4: Test folder cycling with Obsidian notes

- [ ] **Step 1: Create a test overlay folder**

```bash
mkdir -p ~/Documents/Personal/30-areas/stream-overlays
echo '# Welcome
**Legomena Live** — building AI + making beats' > ~/Documents/Personal/30-areas/stream-overlays/01-welcome.md
echo '## Studio Gear
- MPC Live II
- SP-404 MKII
- Technics SL-1200
- Cortado contact mic' > ~/Documents/Personal/30-areas/stream-overlays/02-gear.md
echo '## Links
**GitHub**: github.com/ryanklee
**Stream**: youtube.com/@legomenalive' > ~/Documents/Personal/30-areas/stream-overlays/03-links.md
```

- [ ] **Step 2: Configure zone to use folder**

Edit the `ZONES` list in `agents/studio_compositor/overlay_zones.py` to set the main zone's folder:

```python
{
    "id": "main",
    "folder": "~/Documents/Personal/30-areas/stream-overlays/",
    "file": None,
    "cycle_seconds": 15,  # 15s for testing, increase for production
    ...
}
```

- [ ] **Step 3: Restart and verify cycling**

```bash
systemctl --user restart studio-compositor
sleep 20
# Should see first note, then after 15s the second note appears
```

- [ ] **Step 4: Commit**

```bash
git add agents/studio_compositor/overlay_zones.py
git commit -m "feat: overlay folder cycling — Obsidian notes rotate on timer"
git push origin main
```
