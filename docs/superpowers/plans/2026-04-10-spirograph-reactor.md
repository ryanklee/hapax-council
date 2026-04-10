# Spirograph Reactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three YouTube videos orbit a glowing spirograph path with a four-beat rotation: each video takes a turn playing (stationary) then the daimonion reacts via TTS, Pango transcript, and waveform — deciding when to cut via LLM.

**Architecture:** Compositor-level overlay system (post-FX cairooverlay, same layer as existing PiP/album/token pole). Director loop coordinates the rotation state machine. YouTube player daemon extended to manage 3 independent slots. TTS via Kokoro imported directly (no daimonion process dependency).

**Tech Stack:** Python 3.12, Cairo/PangoCairo, ffmpeg subprocesses, v4l2loopback, LiteLLM (Claude Opus), Kokoro TTS, PipeWire audio output.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `agents/studio_compositor/spirograph_reactor.py` | CREATE | SpirographPath, VideoSlot, ConfettiParticle, ReactorOverlay, SpirographReactor (main class) |
| `agents/studio_compositor/director_loop.py` | CREATE | DirectorLoop: state machine, LLM perception, cut decision, TTS, Obsidian log |
| `agents/studio_compositor/fx_chain.py:559-569` | MODIFY | Add spirograph_reactor to `_pip_draw` callback |
| `agents/studio_compositor/fx_chain.py:1023-1038` | MODIFY | Add spirograph_reactor to `fx_tick_callback` |
| `scripts/youtube-player.py` | MODIFY | Multi-slot architecture: 3 independent ffmpeg processes |
| `/etc/modprobe.d/v4l2loopback.conf` | MODIFY | Add video51, video52 loopback devices |
| `tests/studio_compositor/test_spirograph_reactor.py` | CREATE | Unit tests for spirograph path, video slot, confetti, reactor |
| `tests/studio_compositor/test_director_loop.py` | CREATE | Unit tests for state machine, rotation logic |

---

### Task 1: v4l2loopback — Add Two More Loopback Devices

**Files:**
- Modify: `/etc/modprobe.d/v4l2loopback.conf`

- [ ] **Step 1: Update modprobe config**

```bash
sudo tee /etc/modprobe.d/v4l2loopback.conf <<'EOF'
options v4l2loopback devices=5 video_nr=10,42,50,51,52 card_label="OBS_Virtual_Camera,StudioCompositor,YouTube0,YouTube1,YouTube2" exclusive_caps=1,1,1,1,1
EOF
```

- [ ] **Step 2: Reload module**

```bash
sudo modprobe -r v4l2loopback && sudo modprobe v4l2loopback
```

Run: `ls /dev/video{50,51,52}`
Expected: All three devices exist.

Note: If modprobe -r fails because devices are in use, this requires a reboot. In that case, just save the config and reboot before stream launch.

- [ ] **Step 3: Verify**

```bash
v4l2-ctl --list-devices
```

Expected: `YouTube0`, `YouTube1`, `YouTube2` appear at `/dev/video50`, `/dev/video51`, `/dev/video52`.

---

### Task 2: YouTube Player — Multi-Slot Architecture

**Files:**
- Modify: `scripts/youtube-player.py`
- Test: `tests/scripts/test_youtube_player_slots.py`

- [ ] **Step 1: Write failing test for slot management**

Create `tests/scripts/test_youtube_player_slots.py`:

```python
"""Tests for multi-slot YouTube player."""

import json
import threading
import time
import urllib.request
from unittest.mock import MagicMock, patch

import pytest


def test_slot_status_returns_three_slots():
    """GET /slots returns status for all 3 slots."""
    from scripts import youtube_player as yp

    yp.slots = [yp.VideoSlot(i) for i in range(3)]
    status = yp.get_all_slots_status()
    assert len(status) == 3
    assert all(s["slot"] == i for i, s in enumerate(status))
    assert all(not s["playing"] for s in status)


def test_slot_play_sets_url():
    """Playing a URL in a slot populates its state."""
    from scripts import youtube_player as yp

    slot = yp.VideoSlot(0)
    with patch.object(yp, "extract_urls", return_value=("v", "a", "Title", "Chan")):
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=123)
            slot.play("https://youtube.com/watch?v=test")
    assert slot.title == "Title"
    assert slot.channel == "Chan"
    assert slot.url == "https://youtube.com/watch?v=test"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scripts/test_youtube_player_slots.py -v`
Expected: FAIL — `VideoSlot` not defined.

- [ ] **Step 3: Refactor youtube-player.py to multi-slot**

Replace the global state variables (lines 42-46) with a `VideoSlot` class:

```python
V4L2_DEVICES = ["/dev/video50", "/dev/video51", "/dev/video52"]


class VideoSlot:
    """Independent video playback slot with its own ffmpeg process."""

    def __init__(self, slot_id: int) -> None:
        self.slot_id = slot_id
        self.device = V4L2_DEVICES[slot_id]
        self.process: subprocess.Popen | None = None
        self.url: str = ""
        self.title: str = ""
        self.channel: str = ""
        self.paused: bool = False
        self.lock = threading.Lock()

    def play(self, youtube_url: str) -> None:
        """Start ffmpeg decoding to this slot's v4l2 device."""
        self.stop()
        try:
            video_url, audio_url, title, channel = extract_urls(youtube_url)
        except Exception as e:
            log.error("Slot %d URL extraction failed: %s", self.slot_id, e)
            return

        log.info("Slot %d playing: %s by %s", self.slot_id, title, channel)
        self.url = youtube_url
        self.title = title
        self.channel = channel
        self.paused = False

        # Write per-slot attribution
        attr_file = SHM_DIR / f"yt-attribution-{self.slot_id}.txt"
        try:
            attr_file.write_text(f"{title}\n{channel}\n{youtube_url}")
        except OSError:
            pass

        cmd = [
            "ffmpeg", "-y",
            "-reconnect", "1", "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-i", video_url, "-i", audio_url,
            "-map", "0:v", "-vf", "scale=1920:1080",
            "-pix_fmt", "yuyv422", "-f", "v4l2", self.device,
            "-map", "1:a", "-f", "pulse", "-ac", "2",
            f"youtube-audio-{self.slot_id}",
        ]
        self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        log.info("Slot %d ffmpeg started (PID %d)", self.slot_id, self.process.pid)

    def stop(self) -> None:
        """Stop playback on this slot."""
        attr_file = SHM_DIR / f"yt-attribution-{self.slot_id}.txt"
        attr_file.unlink(missing_ok=True)
        if self.process is not None:
            try:
                self.process.send_signal(signal.SIGTERM)
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
            self.url = ""
            self.title = ""
            self.channel = ""
            self.paused = False

    def toggle_pause(self) -> bool:
        if self.process is None:
            return False
        if self.paused:
            self.process.send_signal(signal.SIGCONT)
            self.paused = False
        else:
            self.process.send_signal(signal.SIGSTOP)
            self.paused = True
        return self.paused

    def is_playing(self) -> bool:
        return self.process is not None and self.process.poll() is None and not self.paused

    def is_finished(self) -> bool:
        """True if ffmpeg exited (video ended or error)."""
        return self.process is not None and self.process.poll() is not None

    def get_status(self) -> dict:
        running = self.process is not None and self.process.poll() is None
        return {
            "slot": self.slot_id,
            "playing": running and not self.paused,
            "paused": self.paused,
            "url": self.url,
            "title": self.title,
            "channel": self.channel,
            "finished": self.is_finished(),
        }


SHM_DIR = Path("/dev/shm/hapax-compositor")

# Module-level slot list
slots: list[VideoSlot] = [VideoSlot(i) for i in range(3)]


def get_all_slots_status() -> list[dict]:
    return [s.get_status() for s in slots]
```

- [ ] **Step 4: Add HTTP endpoints for per-slot control**

In the `Handler` class, add slot routing:

```python
    def do_GET(self) -> None:
        if self.path == "/status":
            # Backward compat: slot 0
            self._json(slots[0].get_status())
        elif self.path == "/slots":
            self._json(get_all_slots_status())
        elif self.path.startswith("/slot/") and self.path.endswith("/status"):
            slot_id = int(self.path.split("/")[2])
            if 0 <= slot_id < 3:
                self._json(slots[slot_id].get_status())
            else:
                self._json({"error": "invalid slot"}, 400)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        content_len = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_len)) if content_len > 0 else {}

        # Per-slot endpoints: /slot/{n}/play, /slot/{n}/pause, /slot/{n}/stop
        if self.path.startswith("/slot/"):
            parts = self.path.split("/")
            if len(parts) >= 4:
                slot_id = int(parts[2])
                action = parts[3]
                if not (0 <= slot_id < 3):
                    self._json({"error": "invalid slot"}, 400)
                    return
                slot = slots[slot_id]
                if action == "play":
                    url = body.get("url", "")
                    if not url:
                        self._json({"error": "url required"}, 400)
                        return
                    with slot.lock:
                        slot.play(url)
                    self._json({"status": "playing", "slot": slot_id})
                elif action == "pause":
                    with slot.lock:
                        p = slot.toggle_pause()
                    self._json({"paused": p, "slot": slot_id})
                elif action == "stop":
                    with slot.lock:
                        slot.stop()
                    self._json({"status": "stopped", "slot": slot_id})
                else:
                    self._json({"error": "unknown action"}, 404)
                return

        # Legacy endpoints operate on slot 0
        if self.path == "/play":
            url = body.get("url", "")
            if not url:
                self._json({"error": "url required"}, 400)
                return
            with slots[0].lock:
                slots[0].play(url)
            self._json({"status": "playing", "url": url})
        elif self.path == "/pause":
            with slots[0].lock:
                p = slots[0].toggle_pause()
            self._json({"paused": p})
        elif self.path == "/skip":
            # Legacy skip not applicable to multi-slot
            self._json({"status": "use /slot/N/stop"})
        elif self.path == "/stop":
            with slots[0].lock:
                slots[0].stop()
            self._json({"status": "stopped"})
        else:
            self._json({"error": "not found"}, 404)
```

- [ ] **Step 5: Update auto_advance_loop for multi-slot**

The auto_advance_loop now monitors all slots:

```python
def auto_advance_loop() -> None:
    """Watch for ffmpeg exits across all slots."""
    while True:
        time.sleep(1)
        for slot in slots:
            with slot.lock:
                if slot.process is not None and slot.process.poll() is not None:
                    rc = slot.process.returncode
                    log.info("Slot %d video ended (exit %d)", slot.slot_id, rc)
                    # Write finished marker for director loop to detect
                    marker = SHM_DIR / f"yt-finished-{slot.slot_id}"
                    marker.write_text(str(rc))
                    slot.process = None
```

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/scripts/test_youtube_player_slots.py -v`
Expected: PASS

- [ ] **Step 7: Restart youtube-player and verify**

```bash
systemctl --user restart youtube-player
curl -s http://127.0.0.1:8055/slots | python3 -m json.tool
```

Expected: 3 slots, all not playing.

- [ ] **Step 8: Commit**

```bash
git add scripts/youtube-player.py tests/scripts/test_youtube_player_slots.py
git commit -m "feat(streaming): multi-slot YouTube player — 3 independent playback slots"
```

---

### Task 3: Spirograph Path + Video Slots + Confetti

**Files:**
- Create: `agents/studio_compositor/spirograph_reactor.py`
- Test: `tests/studio_compositor/test_spirograph_reactor.py`

- [ ] **Step 1: Write failing tests**

Create `tests/studio_compositor/test_spirograph_reactor.py`:

```python
"""Tests for spirograph path, video slots, and confetti."""

import math

import pytest


def test_spirograph_path_produces_points():
    from agents.studio_compositor.spirograph_reactor import SpirographPath

    path = SpirographPath(center_x=960, center_y=540, scale=400)
    points = path.points
    assert len(points) == path.NUM_POINTS
    # All points should be within canvas bounds (with margin)
    for x, y in points:
        assert -100 < x < 2020
        assert -100 < y < 1180


def test_spirograph_path_position_at_t():
    from agents.studio_compositor.spirograph_reactor import SpirographPath

    path = SpirographPath(center_x=960, center_y=540, scale=400)
    # t=0 and t=1 should give different positions (path is not a single point)
    p0 = path.position_at(0.0)
    p1 = path.position_at(0.5)
    assert p0 != p1


def test_confetti_particle_fades():
    from agents.studio_compositor.spirograph_reactor import ConfettiParticle

    p = ConfettiParticle(100, 100)
    # Particle should be alive initially
    assert p.alive
    # After many ticks it should die
    for _ in range(200):
        p.tick()
    assert not p.alive


def test_video_slot_initial_state():
    from agents.studio_compositor.spirograph_reactor import VideoSlot

    slot = VideoSlot(slot_id=0, device="/dev/video50")
    assert not slot.is_active
    assert slot.orbit_t == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/studio_compositor/test_spirograph_reactor.py -v`
Expected: FAIL — modules not found.

- [ ] **Step 3: Implement SpirographPath**

Create `agents/studio_compositor/spirograph_reactor.py`:

```python
"""Spirograph reactor — multi-video PiP with daimonion react overlay."""

from __future__ import annotations

import math
import random
import struct
import threading
import time
from pathlib import Path
from typing import Any

import logging

log = logging.getLogger(__name__)

# Synthwave confetti palette
CONFETTI_COLORS = [
    (1.0, 0.08, 0.58),   # neon pink
    (0.0, 1.0, 1.0),     # electric cyan
    (1.0, 0.0, 0.8),     # hot magenta
    (0.2, 1.0, 0.2),     # laser green
    (0.5, 0.0, 1.0),     # ultraviolet blue
    (1.0, 0.85, 0.0),    # synthwave gold
]

SHM_DIR = Path("/dev/shm/hapax-compositor")


class SpirographPath:
    """Hypotrochoid parametric curve with iridescent glow rendering."""

    NUM_POINTS = 1000
    # R=5, r=3, d=3 → 5-petal pattern
    R = 5.0
    r = 3.0
    d = 3.0

    def __init__(self, center_x: float = 960, center_y: float = 540, scale: float = 380) -> None:
        self.center_x = center_x
        self.center_y = center_y
        self.scale = scale
        self.points = self._compute_points()
        self._hue_offset = 0.0

    def _compute_points(self) -> list[tuple[float, float]]:
        pts = []
        R, r, d = self.R, self.r, self.d
        # Full curve closes after lcm period
        t_max = 2 * math.pi * r / math.gcd(int(R), int(r))
        for i in range(self.NUM_POINTS):
            t = t_max * i / self.NUM_POINTS
            x = (R - r) * math.cos(t) + d * math.cos((R - r) / r * t)
            y = (R - r) * math.sin(t) - d * math.sin((R - r) / r * t)
            pts.append((
                self.center_x + x * self.scale / (R + d),
                self.center_y + y * self.scale / (R + d),
            ))
        return pts

    def position_at(self, t: float) -> tuple[float, float]:
        """Get position on path at normalized parameter t in [0, 1)."""
        idx = int(t * self.NUM_POINTS) % self.NUM_POINTS
        return self.points[idx]

    def draw(self, cr: Any) -> None:
        """Draw the spirograph path as a faintly glowing iridescent thread."""
        import cairo

        self._hue_offset += 0.002  # slow drift
        n = len(self.points)

        # Glow pass: wider, very faint
        for width, alpha in [(4.0, 0.04), (2.0, 0.06), (1.0, 0.10)]:
            cr.set_line_width(width)
            cr.move_to(*self.points[0])
            for i in range(1, n):
                cr.line_to(*self.points[i])
            cr.close_path()
            # Iridescent: hue shifts along path length
            hue = (self._hue_offset) % 1.0
            r, g, b = _hsv_to_rgb(hue, 0.5, 1.0)
            cr.set_source_rgba(r, g, b, alpha)
            cr.stroke()

        # Segment-colored pass for iridescence
        cr.set_line_width(1.0)
        for i in range(n - 1):
            hue = (self._hue_offset + i / n) % 1.0
            r, g, b = _hsv_to_rgb(hue, 0.6, 1.0)
            cr.set_source_rgba(r, g, b, 0.08)
            cr.move_to(*self.points[i])
            cr.line_to(*self.points[i + 1])
            cr.stroke()


class ConfettiParticle:
    """Synthwave confetti particle with gravity and spin."""

    __slots__ = ("x", "y", "vx", "vy", "color", "alpha", "w", "h", "angle", "spin", "born")

    def __init__(self, x: float, y: float) -> None:
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(4, 16)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - random.uniform(2, 6)
        self.color = random.choice(CONFETTI_COLORS)
        self.alpha = 1.0
        self.w = random.uniform(3, 6)
        self.h = random.uniform(1.5, 3)
        self.angle = random.uniform(0, 2 * math.pi)
        self.spin = random.uniform(-0.3, 0.3)
        self.born = time.monotonic()

    @property
    def alive(self) -> bool:
        return self.alpha > 0.03

    def tick(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.5  # gravity
        self.vx *= 0.97
        self.vy *= 0.97
        self.angle += self.spin
        age = time.monotonic() - self.born
        self.alpha = max(0, 1.0 - age / 2.0)
        return self.alive

    def draw(self, cr: Any) -> None:
        cr.save()
        cr.translate(self.x, self.y)
        cr.rotate(self.angle)
        cr.rectangle(-self.w / 2, -self.h / 2, self.w, self.h)
        r, g, b = self.color
        cr.set_source_rgba(r, g, b, self.alpha)
        cr.fill()
        cr.restore()


class VideoSlot:
    """A video window on the spirograph path."""

    WIDTH = 384
    HEIGHT = 216
    FRAME_SIZE = 384 * 216 * 4  # BGRA
    ALPHA = 0.85

    def __init__(self, slot_id: int, device: str) -> None:
        self.slot_id = slot_id
        self.device = device
        self.orbit_t: float = slot_id / 3.0  # evenly spaced
        self.orbit_speed: float = 1.0 / (90 * 30)  # full orbit in 90s at 30fps
        self.is_active: bool = False  # True when this slot is the playing video
        self._surface = None
        self._surface_lock = threading.Lock()
        self._ffmpeg_proc = None
        self._reader_thread = None
        self._fx_name = ""
        self._fx_func = None
        self._title = ""
        self._channel = ""
        self._confetti: list[ConfettiParticle] = []
        self._finished = False

    def start_capture(self) -> None:
        """Start reading frames from this slot's v4l2 device."""
        import subprocess as _sp
        import os

        if not os.path.exists(self.device):
            log.warning("VideoSlot %d: device %s not found", self.slot_id, self.device)
            return

        from agents.studio_compositor.fx_chain import PIP_EFFECTS

        self._fx_name, self._fx_func = random.choice(list(PIP_EFFECTS.items()))

        try:
            self._ffmpeg_proc = _sp.Popen(
                [
                    "ffmpeg", "-f", "v4l2",
                    "-video_size", "1920x1080", "-input_format", "yuyv422",
                    "-i", self.device,
                    "-vf", f"scale={self.WIDTH}:{self.HEIGHT}",
                    "-f", "rawvideo", "-pix_fmt", "bgra", "-an", "-v", "error",
                    "pipe:1",
                ],
                stdout=_sp.PIPE, stderr=_sp.DEVNULL,
            )
            self._reader_thread = threading.Thread(
                target=self._read_frames, daemon=True,
                name=f"spirograph-video-{self.slot_id}",
            )
            self._reader_thread.start()
            log.info("VideoSlot %d capture started (effect=%s)", self.slot_id, self._fx_name)
        except Exception:
            log.exception("VideoSlot %d capture failed", self.slot_id)

    def stop_capture(self) -> None:
        if self._ffmpeg_proc is not None:
            try:
                self._ffmpeg_proc.kill()
                self._ffmpeg_proc.wait(timeout=2)
            except Exception:
                pass
            self._ffmpeg_proc = None
        with self._surface_lock:
            self._surface = None

    def _read_frames(self) -> None:
        import cairo

        proc = self._ffmpeg_proc
        if proc is None or proc.stdout is None:
            return
        while proc.poll() is None:
            try:
                data = proc.stdout.read(self.FRAME_SIZE)
                if len(data) != self.FRAME_SIZE:
                    break
                surface = cairo.ImageSurface.create_for_data(
                    bytearray(data), cairo.FORMAT_ARGB32, self.WIDTH, self.HEIGHT,
                )
                with self._surface_lock:
                    self._surface = surface
            except Exception:
                break
        log.info("VideoSlot %d frame reader exited", self.slot_id)

    def check_finished(self) -> bool:
        """Check if the youtube-player reported this slot finished."""
        marker = SHM_DIR / f"yt-finished-{self.slot_id}"
        if marker.exists():
            marker.unlink(missing_ok=True)
            self._finished = True
            return True
        return False

    def spawn_confetti(self, x: float, y: float) -> None:
        """Spawn synthwave confetti explosion at video center."""
        for _ in range(80):
            self._confetti.append(ConfettiParticle(x, y))

    def tick(self, path: SpirographPath) -> tuple[float, float]:
        """Update orbit position. Returns (x, y) screen position."""
        if not self.is_active:
            self.orbit_t = (self.orbit_t + self.orbit_speed) % 1.0
        pos = path.position_at(self.orbit_t)
        # Tick confetti
        self._confetti = [p for p in self._confetti if p.tick()]
        return pos

    def draw(self, cr: Any, x: float, y: float) -> None:
        """Draw video frame at position with effect and attribution."""
        # Draw video frame
        with self._surface_lock:
            surface = self._surface
        if surface is not None:
            cr.save()
            cr.translate(x - self.WIDTH / 2, y - self.HEIGHT / 2)
            cr.set_source_surface(surface, 0, 0)
            cr.paint_with_alpha(self.ALPHA)
            if self._fx_func is not None:
                self._fx_func(cr, self.WIDTH, self.HEIGHT)
            cr.restore()

        # Draw confetti
        for p in self._confetti:
            p.draw(cr)

    def update_metadata(self) -> None:
        """Read attribution from shm file."""
        attr_file = SHM_DIR / f"yt-attribution-{self.slot_id}.txt"
        if attr_file.exists():
            try:
                lines = attr_file.read_text().strip().split("\n")
                self._title = lines[0] if lines else ""
                self._channel = lines[1] if len(lines) > 1 else ""
            except OSError:
                pass


class ReactorOverlay:
    """Pango box for reactor transcript + waveform visualization."""

    BOX_X = 1350
    BOX_Y = 750
    BOX_W = 500
    BOX_H = 250
    WAVE_H = 60
    WAVE_Y = BOX_Y - 70  # above the box

    def __init__(self) -> None:
        self._text: str = ""
        self._visible_chars: int = 0
        self._speaking: bool = False
        self._pcm_samples: list[float] = []  # recent audio samples for waveform
        self._border_pulse: float = 0.0

    def set_text(self, text: str) -> None:
        """Set react text. Characters revealed progressively."""
        self._text = text
        self._visible_chars = 0

    def set_speaking(self, speaking: bool) -> None:
        self._speaking = speaking
        if speaking:
            self._border_pulse = 1.0

    def feed_pcm(self, pcm_bytes: bytes) -> None:
        """Feed PCM int16 samples for waveform display."""
        n = len(pcm_bytes) // 2
        samples = struct.unpack(f"<{n}h", pcm_bytes[:n * 2])
        # Downsample to ~100 points for display
        step = max(1, n // 100)
        self._pcm_samples = [samples[i] / 32768.0 for i in range(0, n, step)][:100]

    def tick(self) -> None:
        """Advance text reveal and decay pulse."""
        if self._speaking and self._visible_chars < len(self._text):
            self._visible_chars = min(self._visible_chars + 2, len(self._text))
        self._border_pulse *= 0.95
        if not self._speaking:
            self._pcm_samples = []

    def draw(self, cr: Any) -> None:
        """Draw the reactor box, transcript, and waveform."""
        import cairo

        try:
            import gi
            gi.require_version("Pango", "1.0")
            gi.require_version("PangoCairo", "1.0")
            from gi.repository import Pango, PangoCairo
        except Exception:
            return

        # Background card
        cr.set_source_rgba(0.05, 0.04, 0.08, 0.85)
        _rounded_rect(cr, self.BOX_X, self.BOX_Y, self.BOX_W, self.BOX_H, 8)
        cr.fill()

        # Border (pulses on turn start)
        pulse_alpha = 0.3 + 0.5 * self._border_pulse
        cr.set_source_rgba(0.7, 0.5, 1.0, pulse_alpha)
        cr.set_line_width(1.0)
        _rounded_rect(cr, self.BOX_X, self.BOX_Y, self.BOX_W, self.BOX_H, 8)
        cr.stroke()

        # Header: "REACTOR"
        cr.set_source_rgba(0.7, 0.5, 1.0, 0.9)
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(Pango.FontDescription.from_string("JetBrains Mono Bold 10"))
        layout.set_text("REACTOR", -1)
        cr.move_to(self.BOX_X + 12, self.BOX_Y + 8)
        PangoCairo.show_layout(cr, layout)

        # Transcript text
        if self._text and self._visible_chars > 0:
            visible = self._text[:self._visible_chars]
            cr.set_source_rgba(0.95, 0.92, 0.85, 0.9)
            layout = PangoCairo.create_layout(cr)
            layout.set_font_description(Pango.FontDescription.from_string("JetBrains Mono 16"))
            layout.set_width((self.BOX_W - 24) * Pango.SCALE)
            layout.set_wrap(Pango.WrapMode.WORD_CHAR)
            layout.set_text(visible, -1)
            cr.move_to(self.BOX_X + 12, self.BOX_Y + 30)
            PangoCairo.show_layout(cr, layout)

        # Waveform
        if self._pcm_samples:
            cr.set_source_rgba(0.7, 0.5, 1.0, 0.8)
            cr.set_line_width(1.5)
            n = len(self._pcm_samples)
            mid_y = self.WAVE_Y + self.WAVE_H / 2
            for i, s in enumerate(self._pcm_samples):
                x = self.BOX_X + i * (self.BOX_W / n)
                y = mid_y + s * (self.WAVE_H / 2)
                if i == 0:
                    cr.move_to(x, y)
                else:
                    cr.line_to(x, y)
            cr.stroke()
        else:
            # Flat line when silent
            cr.set_source_rgba(0.7, 0.5, 1.0, 0.15)
            cr.set_line_width(1.0)
            mid_y = self.WAVE_Y + self.WAVE_H / 2
            cr.move_to(self.BOX_X, mid_y)
            cr.line_to(self.BOX_X + self.BOX_W, mid_y)
            cr.stroke()


def _rounded_rect(cr: Any, x: float, y: float, w: float, h: float, r: float) -> None:
    """Draw a rounded rectangle path."""
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[float, float, float]:
    """Convert HSV [0-1] to RGB [0-1]."""
    import colorsys
    return colorsys.hsv_to_rgb(h, s, v)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/studio_compositor/test_spirograph_reactor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/spirograph_reactor.py tests/studio_compositor/test_spirograph_reactor.py
git commit -m "feat(streaming): spirograph path, video slots, confetti, reactor overlay"
```

---

### Task 4: Director Loop — State Machine + LLM + TTS

**Files:**
- Create: `agents/studio_compositor/director_loop.py`
- Test: `tests/studio_compositor/test_director_loop.py`

- [ ] **Step 1: Write failing tests**

Create `tests/studio_compositor/test_director_loop.py`:

```python
"""Tests for the director loop state machine."""

import pytest
from unittest.mock import MagicMock, patch


def test_state_machine_initial():
    from agents.studio_compositor.director_loop import DirectorLoop

    dl = DirectorLoop.__new__(DirectorLoop)
    dl._state = "PLAYING_VIDEO"
    dl._active_slot = 0
    assert dl._state == "PLAYING_VIDEO"
    assert dl._active_slot == 0


def test_next_slot_cycles():
    from agents.studio_compositor.director_loop import DirectorLoop

    dl = DirectorLoop.__new__(DirectorLoop)
    dl._active_slot = 0
    dl._next_slot()
    assert dl._active_slot == 1
    dl._next_slot()
    assert dl._active_slot == 2
    dl._next_slot()
    assert dl._active_slot == 0


def test_parse_llm_response_with_cut():
    from agents.studio_compositor.director_loop import DirectorLoop

    dl = DirectorLoop.__new__(DirectorLoop)
    react, cut = dl._parse_llm_response('{"react": "Wow.", "cut": true}')
    assert react == "Wow."
    assert cut is True


def test_parse_llm_response_without_cut():
    from agents.studio_compositor.director_loop import DirectorLoop

    dl = DirectorLoop.__new__(DirectorLoop)
    react, cut = dl._parse_llm_response('{"react": "Interesting.", "cut": false}')
    assert react == "Interesting."
    assert cut is False


def test_parse_llm_response_malformed():
    from agents.studio_compositor.director_loop import DirectorLoop

    dl = DirectorLoop.__new__(DirectorLoop)
    react, cut = dl._parse_llm_response("Just some text without JSON")
    assert react == "Just some text without JSON"
    assert cut is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/studio_compositor/test_director_loop.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement DirectorLoop**

Create `agents/studio_compositor/director_loop.py`:

```python
"""Director loop — orchestrates the four-beat spirograph rotation.

State machine: PLAYING_VIDEO(n) → REACTOR_SPEAKING → PLAYING_VIDEO(n+1)

The director:
1. Periodically captures the playing video's frame + compositor snapshot
2. Sends both to the LLM (Claude Opus) with reactor context
3. When the LLM signals CUT, transitions to the reactor's speaking turn
4. Synthesizes the react text via Kokoro TTS
5. Logs the reaction to Obsidian
6. Advances to the next video slot
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

SHM_DIR = Path("/dev/shm/hapax-compositor")
OBSIDIAN_LOG = Path(
    os.path.expanduser("~/Documents/Personal/30-areas/legomena-live/reactor-log.md")
)
ALBUM_STATE_FILE = SHM_DIR / "album-state.json"
FX_SNAPSHOT = SHM_DIR / "fx-snapshot.jpg"

LITELLM_URL = "http://localhost:4000/v1/chat/completions"
LITELLM_KEY = ""

PERCEPTION_INTERVAL = 8.0  # seconds between LLM perception calls during video
MIN_VIDEO_DURATION = 15.0  # minimum seconds before allowing CUT

# --- Reactor context template ---
REACTOR_CONTEXT = """<reactor_context>
You are the daimonion — the persistent cognitive substrate of the Hapax system.
You are participating in Legomena Live, a 36-hour continuous livestream on YouTube.

SITUATION:
- Four-beat rotation: Video 1 → You → Video 2 → You → Video 3 → You → repeat
- You just watched: {video_title} by {video_channel}
- The other videos: {other_videos}
- Viewers see: 6 cameras through a 24-slot GPU shader FX chain with audio-reactive sidechain
- Music: vinyl on the turntable ({album_info})
- Overlays: album cover with splattributions, token pole (Vitruvian golden spiral),
  bouncing text (philosophy/literature excerpts), and the spirograph with video windows

YOUR ROLE:
- React to what you just saw. Your reaction is spoken aloud via TTS and displayed
  as a transcript with a waveform visualization.
- You are not performing. You are the system expressing genuine cognitive response.
- 1-3 sentences. Concise. Pointed. Sometimes funny, sometimes contemplative,
  sometimes connecting unexpected threads between the video and the environment.

RESPONSE FORMAT (JSON only):
{{"react": "Your 1-3 sentence reaction", "cut": true/false}}

- "cut": true means this video's turn should end NOW (you've seen enough, natural break).
- "cut": false means keep watching, you'll react again in ~8 seconds.
- Always set cut=true after {max_watch}s of watching — don't let any video run forever.
</reactor_context>"""


def _get_litellm_key() -> str:
    global LITELLM_KEY
    if not LITELLM_KEY:
        try:
            result = subprocess.run(
                ["pass", "show", "litellm/master-key"],
                capture_output=True, text=True, timeout=5,
            )
            LITELLM_KEY = result.stdout.strip()
        except Exception:
            pass
    return LITELLM_KEY


def _read_album_info() -> str:
    try:
        if ALBUM_STATE_FILE.exists():
            data = json.loads(ALBUM_STATE_FILE.read_text())
            artist = data.get("artist", "unknown")
            title = data.get("title", "unknown")
            track = data.get("current_track", "")
            return f"{title} by {artist}" + (f", track: {track}" if track else "")
    except Exception:
        pass
    return "unknown"


def _capture_frame_b64(path: Path) -> str | None:
    """Read image file and return base64-encoded string."""
    import base64
    try:
        if path.exists():
            data = path.read_bytes()
            return base64.b64encode(data).decode()
    except Exception:
        pass
    return None


class DirectorLoop:
    """Orchestrates the spirograph four-beat rotation."""

    def __init__(self, video_slots: list, reactor_overlay) -> None:
        self._slots = video_slots  # list of VideoSlot
        self._reactor = reactor_overlay  # ReactorOverlay
        self._state = "PLAYING_VIDEO"  # PLAYING_VIDEO | REACTOR_SPEAKING
        self._active_slot = 0
        self._video_start_time = 0.0
        self._last_perception = 0.0
        self._accumulated_reacts: list[str] = []
        self._final_react = ""
        self._tts_manager = None
        self._tts_lock = threading.Lock()
        self._running = False
        self._thread = None

        # Audio output for TTS playback
        self._audio_proc = None

    def start(self) -> None:
        self._running = True
        self._video_start_time = time.monotonic()
        # Mark first slot as active
        if self._slots:
            self._slots[self._active_slot].is_active = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="director-loop")
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _next_slot(self) -> None:
        self._active_slot = (self._active_slot + 1) % len(self._slots)

    def _loop(self) -> None:
        """Main director loop — runs in background thread."""
        while self._running:
            try:
                if self._state == "PLAYING_VIDEO":
                    self._tick_playing()
                elif self._state == "REACTOR_SPEAKING":
                    self._tick_speaking()
            except Exception:
                log.exception("Director loop error")
            time.sleep(0.5)

    def _tick_playing(self) -> None:
        """During video playback: periodically perceive and check for CUT."""
        now = time.monotonic()
        elapsed = now - self._video_start_time

        # Check if video finished naturally
        slot = self._slots[self._active_slot]
        if slot.check_finished():
            # Video ended — spawn confetti, move to reactor
            pos = slot.tick(None)  # get current position (won't actually tick)
            # Confetti will be spawned by the main tick when it reads _finished
            self._transition_to_reactor(f"Video ended naturally.")
            return

        # Don't perceive too frequently
        if now - self._last_perception < PERCEPTION_INTERVAL:
            return

        # Minimum duration before allowing cut
        if elapsed < MIN_VIDEO_DURATION:
            self._last_perception = now
            return

        self._last_perception = now

        # Capture video frame (from the slot's v4l2 device snapshot)
        # We use the compositor fx-snapshot which shows the full output
        snapshot_b64 = _capture_frame_b64(FX_SNAPSHOT)
        if not snapshot_b64:
            return

        # Build LLM call
        slot = self._slots[self._active_slot]
        other_titles = [
            f"{s._title} by {s._channel}"
            for i, s in enumerate(self._slots) if i != self._active_slot
        ]

        context = REACTOR_CONTEXT.format(
            video_title=slot._title or f"Video {self._active_slot}",
            video_channel=slot._channel or "unknown",
            other_videos=", ".join(other_titles) if other_titles else "none loaded",
            album_info=_read_album_info(),
            max_watch="60",
        )

        # Force cut after 60s
        force_cut = elapsed > 60.0

        react, cut = self._call_llm(context, snapshot_b64, force_cut)
        if react:
            self._accumulated_reacts.append(react)

        if cut or force_cut:
            final = react or (self._accumulated_reacts[-1] if self._accumulated_reacts else "...")
            self._transition_to_reactor(final)

    def _transition_to_reactor(self, react_text: str) -> None:
        """Switch from video to reactor turn."""
        slot = self._slots[self._active_slot]
        slot.is_active = False
        self._final_react = react_text
        self._state = "REACTOR_SPEAKING"
        self._reactor.set_text(react_text)
        self._reactor.set_speaking(True)
        log.info("Reactor turn: %s", react_text[:80])

        # Synthesize and play TTS in background
        threading.Thread(
            target=self._speak_and_advance, args=(react_text,),
            daemon=True, name="reactor-tts",
        ).start()

    def _speak_and_advance(self, text: str) -> None:
        """Synthesize TTS, play audio, log to Obsidian, advance to next video."""
        try:
            pcm = self._synthesize(text)
            if pcm:
                self._reactor.feed_pcm(pcm)
                self._play_audio(pcm)
            # Brief pause after speaking
            time.sleep(1.0)
        except Exception:
            log.exception("Reactor TTS error")

        # Log to Obsidian
        self._log_to_obsidian(text)

        # Advance
        self._reactor.set_speaking(False)
        self._reactor.set_text("")
        self._accumulated_reacts.clear()
        self._next_slot()
        self._slots[self._active_slot].is_active = True
        self._video_start_time = time.monotonic()
        self._last_perception = 0.0
        self._state = "PLAYING_VIDEO"
        log.info("Now playing slot %d", self._active_slot)

    def _tick_speaking(self) -> None:
        """During reactor turn: just wait for TTS thread to finish."""
        self._reactor.tick()

    def _synthesize(self, text: str) -> bytes:
        """Synthesize text via Kokoro TTS."""
        with self._tts_lock:
            if self._tts_manager is None:
                from agents.hapax_daimonion.tts import TTSManager
                self._tts_manager = TTSManager()
                self._tts_manager.preload()
            return self._tts_manager.synthesize(text, "conversation")

    def _play_audio(self, pcm: bytes) -> None:
        """Play PCM int16 24kHz mono via PipeWire."""
        try:
            proc = subprocess.Popen(
                [
                    "pw-cat", "--playback",
                    "--format", "s16", "--rate", "24000", "--channels", "1",
                    "-",
                ],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            proc.stdin.write(pcm)
            proc.stdin.close()
            proc.wait(timeout=30)
        except Exception:
            log.exception("Audio playback error")

    def _call_llm(self, context: str, image_b64: str, force_cut: bool) -> tuple[str, bool]:
        """Call LLM with video frame + context. Returns (react_text, should_cut)."""
        key = _get_litellm_key()
        if not key:
            return ("", force_cut)

        messages = [
            {"role": "system", "content": context},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                    },
                    {
                        "type": "text",
                        "text": "React to what you see."
                        + (" You MUST set cut=true now — maximum watch time reached." if force_cut else ""),
                    },
                ],
            },
        ]

        body = json.dumps({
            "model": "balanced",
            "messages": messages,
            "max_tokens": 200,
            "temperature": 0.8,
        }).encode()

        try:
            req = urllib.request.Request(
                LITELLM_URL, body,
                {"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())

            # Record token spend
            try:
                from token_ledger import record_spend
                usage = data.get("usage", {})
                record_spend("reactor", usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
            except Exception:
                pass

            raw = data["choices"][0]["message"]["content"].strip()
            return self._parse_llm_response(raw)
        except Exception:
            log.exception("LLM call failed")
            return ("", force_cut)

    def _parse_llm_response(self, raw: str) -> tuple[str, bool]:
        """Parse LLM JSON response. Falls back to treating raw text as react."""
        try:
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()
            obj = json.loads(raw)
            return (obj.get("react", ""), obj.get("cut", False))
        except (json.JSONDecodeError, KeyError):
            return (raw, False)

    def _log_to_obsidian(self, text: str) -> None:
        """Append reaction to Obsidian reactor log."""
        try:
            OBSIDIAN_LOG.parent.mkdir(parents=True, exist_ok=True)
            slot = self._slots[self._active_slot]
            ts = datetime.now().strftime("%H:%M")
            album = _read_album_info()
            entry = (
                f"- **{ts}** | Reacting to: *{slot._title}* by {slot._channel}\n"
                f"  > {text}\n"
                f"  Album: {album}\n\n"
            )
            with open(OBSIDIAN_LOG, "a") as f:
                f.write(entry)
        except OSError:
            log.debug("Failed to write reactor log")
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/studio_compositor/test_director_loop.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/director_loop.py tests/studio_compositor/test_director_loop.py
git commit -m "feat(streaming): director loop — LLM-directed rotation + TTS + Obsidian log"
```

---

### Task 5: Wire Into Compositor

**Files:**
- Modify: `agents/studio_compositor/fx_chain.py:559-569` (`_pip_draw`)
- Modify: `agents/studio_compositor/fx_chain.py:1023-1038` (`fx_tick_callback`)

- [ ] **Step 1: Add spirograph reactor to `_pip_draw`**

In `fx_chain.py`, modify `_pip_draw` (line 559):

```python
def _pip_draw(compositor: Any, cr: Any) -> None:
    """Post-FX cairooverlay callback: draws all overlays."""
    # Spirograph reactor (draws spirograph + video windows + reactor box)
    spiro = getattr(compositor, "_spirograph_reactor", None)
    if spiro is not None:
        spiro.draw(cr)

    # Original overlays (album and token pole remain; YouTube PiP replaced by spirograph)
    album = getattr(compositor, "_album_overlay", None)
    if album is not None:
        album.draw(cr)
    token_pole = getattr(compositor, "_token_pole", None)
    if token_pole is not None:
        token_pole.draw(cr)
```

- [ ] **Step 2: Add spirograph reactor to `fx_tick_callback`**

In `fx_chain.py`, add after the token_pole tick (line 1036):

```python
    # Spirograph reactor: orbit positions, confetti, reactor text reveal
    spiro = getattr(compositor, "_spirograph_reactor", None)
    if spiro:
        spiro.tick()
```

- [ ] **Step 3: Add SpirographReactor.tick() and .draw() orchestration methods**

In `spirograph_reactor.py`, add the top-level `SpirographReactor` class that owns all components:

```python
class SpirographReactor:
    """Top-level orchestrator — owns spirograph, video slots, reactor overlay, director."""

    DEVICES = ["/dev/video50", "/dev/video51", "/dev/video52"]
    INITIAL_URLS = [
        "https://www.youtube.com/watch?v=ED1fL1YpPEs&list=PL-4nvD1KwuH--sViEAFY2cHVmS6_B4CQ5&index=6",
        "https://www.youtube.com/watch?v=DbfejwP1d3c&list=PL-4nvD1KwuH--sViEAFY2cHVmS6_B4CQ5&index=5",
        "https://www.youtube.com/watch?v=KnyERpdX_0g&list=PL-4nvD1KwuH--sViEAFY2cHVmS6_B4CQ5&index=4",
    ]

    def __init__(self) -> None:
        self.path = SpirographPath()
        self.video_slots = [VideoSlot(i, self.DEVICES[i]) for i in range(3)]
        self.reactor_overlay = ReactorOverlay()
        self.director = None  # lazy init
        self._initialized = False

    def initialize(self) -> None:
        """Load initial videos and start capture + director. Call once."""
        if self._initialized:
            return
        self._initialized = True

        # Start frame capture for all slots
        for slot in self.video_slots:
            slot.start_capture()

        # Load initial videos via youtube-player HTTP API
        for i, url in enumerate(self.INITIAL_URLS):
            try:
                body = json.dumps({"url": url}).encode()
                req = urllib.request.Request(
                    f"http://127.0.0.1:8055/slot/{i}/play", body,
                    {"Content-Type": "application/json"},
                )
                urllib.request.urlopen(req, timeout=10)
                log.info("Loaded slot %d: %s", i, url)
            except Exception:
                log.exception("Failed to load slot %d", i)

        # Wait briefly for metadata to populate
        time.sleep(3)
        for slot in self.video_slots:
            slot.update_metadata()

        # Start director loop
        from agents.studio_compositor.director_loop import DirectorLoop
        self.director = DirectorLoop(self.video_slots, self.reactor_overlay)
        self.director.start()

    def tick(self) -> None:
        """Called every frame (30fps) from fx_tick_callback."""
        if not self._initialized:
            self.initialize()

        # Update video slot orbits
        for slot in self.video_slots:
            slot.tick(self.path)

        # Reactor overlay animation
        self.reactor_overlay.tick()

    def draw(self, cr) -> None:
        """Called every frame from _pip_draw."""
        # 1. Draw spirograph path (background)
        self.path.draw(cr)

        # 2. Draw video slots at their orbital positions
        for slot in self.video_slots:
            pos = self.path.position_at(slot.orbit_t)
            slot.draw(cr, pos[0], pos[1])

        # 3. Draw reactor overlay (foreground)
        self.reactor_overlay.draw(cr)
```

- [ ] **Step 4: Initialize spirograph reactor in compositor startup**

Find where `_yt_overlay` is created in the compositor lifecycle (likely in `lifecycle.py` or `__init__.py`) and add:

```python
from agents.studio_compositor.spirograph_reactor import SpirographReactor

compositor._spirograph_reactor = SpirographReactor()
# Remove or disable the old single YouTubeOverlay:
# compositor._yt_overlay = None
```

- [ ] **Step 5: Verify compositor starts without crash**

```bash
systemctl --user restart studio-compositor
sleep 3
systemctl --user status studio-compositor | head -8
```

Expected: `active (running)`

- [ ] **Step 6: Grab a screenshot and verify visual output**

```bash
cp /dev/shm/hapax-compositor/fx-snapshot.jpg ~/gdrive-drop/spirograph-test.jpg
```

Visually confirm: spirograph path visible, video windows on path, reactor box in lower-right.

- [ ] **Step 7: Commit**

```bash
git add agents/studio_compositor/fx_chain.py agents/studio_compositor/spirograph_reactor.py agents/studio_compositor/director_loop.py
git commit -m "feat(streaming): wire spirograph reactor into compositor pipeline"
```

---

### Task 6: Integration Test — End-to-End Rotation

- [ ] **Step 1: Verify v4l2 devices exist**

```bash
ls /dev/video{50,51,52}
```

- [ ] **Step 2: Verify youtube-player multi-slot API**

```bash
curl -s http://127.0.0.1:8055/slots | python3 -m json.tool
```

Expected: 3 slots with titles populated.

- [ ] **Step 3: Watch compositor logs for director rotation**

```bash
journalctl --user -u studio-compositor -f --no-pager | grep -i "reactor\|director\|slot\|playing\|cut"
```

Expected: See rotation messages — "Reactor turn:", "Now playing slot N", LLM react text.

- [ ] **Step 4: Verify Obsidian log receives entries**

```bash
cat ~/Documents/Personal/30-areas/legomena-live/reactor-log.md
```

Expected: Timestamped reaction entries.

- [ ] **Step 5: Verify TTS audio plays**

Listen for Kokoro TTS voice during reactor turns. If no audio, check PipeWire:

```bash
pw-cli ls Node | grep pw-cat
```

- [ ] **Step 6: Take final screenshot for operator review**

```bash
cp /dev/shm/hapax-compositor/fx-snapshot.jpg ~/gdrive-drop/spirograph-final.jpg
```

- [ ] **Step 7: Commit any fixes**

```bash
git add -u
git commit -m "fix(streaming): integration fixes from spirograph reactor e2e test"
```
