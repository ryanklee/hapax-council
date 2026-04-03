# Proximity Detection Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace broken logind-based keyboard detection with raw evdev input, add bidirectional watch staleness as absence signal, add Blue Yeti ambient energy, add IR brightness body-heat proxy, and wire all into the Bayesian presence engine so `presence_probability` accurately tracks operator proximity at all times.

**Architecture:** Four new/modified perception backends feed the existing `PresenceEngine` Bayesian fusion. Each backend follows the existing pattern: `contribute()` writes `Behavior` objects to the shared dict, presence engine reads them in `_read_signals()`. No changes to the Bayesian math — only signal quality improvements.

**Tech Stack:** Python 3.12, evdev (already installed), pw-cat (PipeWire), numpy, existing perception backend protocol.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `agents/hapax_daimonion/backends/evdev_input.py` | CREATE | Raw HID event monitoring for physical keyboard + mouse |
| `agents/hapax_daimonion/backends/ambient_audio.py` | CREATE | Blue Yeti ambient energy via pw-cat |
| `agents/hapax_daimonion/backends/watch.py` | MODIFY | Add HR data timestamp tracking for staleness |
| `agents/hapax_daimonion/backends/ir_presence.py` | MODIFY | Add IR brightness rolling average + delta |
| `agents/hapax_daimonion/presence_engine.py` | MODIFY | Wire 4 new signals, replace keyboard_active source |
| `agents/hapax_daimonion/init_backends.py` | MODIFY | Register evdev_input + ambient_audio backends |
| `tests/hapax_daimonion/test_evdev_input.py` | CREATE | Tests for evdev backend |
| `tests/hapax_daimonion/test_ambient_audio.py` | CREATE | Tests for ambient audio backend |
| `tests/hapax_daimonion/test_watch_staleness.py` | CREATE | Tests for HR staleness logic |
| `tests/hapax_daimonion/test_ir_brightness.py` | CREATE | Tests for IR brightness delta |

---

### Task 1: Evdev Input Backend — Physical Keyboard/Mouse Monitoring

**Files:**
- Create: `agents/hapax_daimonion/backends/evdev_input.py`
- Test: `tests/hapax_daimonion/test_evdev_input.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for EvdevInputBackend — raw HID event monitoring."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agents.hapax_daimonion.backends.evdev_input import EvdevInputBackend
from agents.hapax_daimonion.primitives import Behavior


class TestEvdevInputBackendProtocol:
    def test_name(self):
        with patch("agents.hapax_daimonion.backends.evdev_input.evdev") as mock_evdev:
            mock_evdev.list_devices.return_value = []
            backend = EvdevInputBackend()
            assert backend.name == "evdev_input"

    def test_provides(self):
        with patch("agents.hapax_daimonion.backends.evdev_input.evdev") as mock_evdev:
            mock_evdev.list_devices.return_value = []
            backend = EvdevInputBackend()
            assert "real_keyboard_active" in backend.provides
            assert "real_idle_seconds" in backend.provides

    def test_contribute_defaults_idle(self):
        with patch("agents.hapax_daimonion.backends.evdev_input.evdev") as mock_evdev:
            mock_evdev.list_devices.return_value = []
            backend = EvdevInputBackend()
            behaviors: dict[str, Behavior] = {}
            backend.contribute(behaviors)
            assert behaviors["real_keyboard_active"].value is False
            assert behaviors["real_idle_seconds"].value > 0


class TestDeviceFiltering:
    def test_filters_virtual_devices(self):
        from agents.hapax_daimonion.backends.evdev_input import _is_physical_input

        assert _is_physical_input("Keychron  Keychron Link  Keyboard") is True
        assert _is_physical_input("Logitech USB Receiver Mouse") is True
        assert _is_physical_input("RustDesk UInput Keyboard") is False
        assert _is_physical_input("mouce-library-fake-mouse") is False
        assert _is_physical_input("ydotoold virtual device") is False


class TestIdleCalculation:
    def test_recent_event_is_active(self):
        from agents.hapax_daimonion.backends.evdev_input import _compute_idle

        import time

        now = time.monotonic()
        assert _compute_idle(now - 2.0, now) == (True, 2.0)

    def test_old_event_is_idle(self):
        from agents.hapax_daimonion.backends.evdev_input import _compute_idle

        import time

        now = time.monotonic()
        assert _compute_idle(now - 30.0, now) == (False, 30.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/hapax_daimonion/test_evdev_input.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write the evdev input backend**

```python
"""Raw HID input backend — physical keyboard/mouse via evdev.

Bypasses systemd-logind which is polluted by virtual input devices
(RustDesk UInput, mouce-library-fake-mouse). Reads directly from
physical device nodes, filtered by name.

Provides:
  - real_keyboard_active: bool (physical keystroke within 5s)
  - real_idle_seconds: float (seconds since last physical input)
"""

from __future__ import annotations

import logging
import select
import threading
import time

import evdev

from agents.hapax_daimonion.perception import PerceptionTier
from agents.hapax_daimonion.primitives import Behavior

log = logging.getLogger(__name__)

_ACTIVE_THRESHOLD_S = 5.0  # seconds of no input before "idle"

# Virtual device names to exclude (substring match)
_VIRTUAL_DEVICE_PATTERNS = [
    "UInput",
    "virtual",
    "fake-mouse",
    "ydotoold",
]

# Physical device name patterns to include (substring match)
_PHYSICAL_DEVICE_PATTERNS = [
    "Keychron",
    "Logitech USB Receiver",
    "Logitech MX",
]


def _is_physical_input(device_name: str) -> bool:
    """Check if a device name is a real physical input (not virtual)."""
    name_lower = device_name.lower()
    for pattern in _VIRTUAL_DEVICE_PATTERNS:
        if pattern.lower() in name_lower:
            return False
    for pattern in _PHYSICAL_DEVICE_PATTERNS:
        if pattern.lower() in name_lower:
            return True
    return False


def _compute_idle(last_event_ts: float, now: float) -> tuple[bool, float]:
    """Compute active state and idle seconds from last event timestamp."""
    idle_s = now - last_event_ts
    active = idle_s < _ACTIVE_THRESHOLD_S
    return active, round(idle_s, 1)


class EvdevInputBackend:
    """PerceptionBackend that monitors physical keyboard/mouse via evdev."""

    def __init__(self) -> None:
        self._last_event_ts: float = 0.0  # monotonic
        self._b_active: Behavior[bool] = Behavior(False)
        self._b_idle: Behavior[float] = Behavior(9999.0)
        self._devices: list[evdev.InputDevice] = []
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def name(self) -> str:
        return "evdev_input"

    @property
    def provides(self) -> frozenset[str]:
        return frozenset({"real_keyboard_active", "real_idle_seconds"})

    @property
    def tier(self) -> PerceptionTier:
        return PerceptionTier.FAST

    def available(self) -> bool:
        try:
            devices = [evdev.InputDevice(p) for p in evdev.list_devices()]
            return any(_is_physical_input(d.name) for d in devices)
        except Exception:
            return False

    def start(self) -> None:
        try:
            all_devices = [evdev.InputDevice(p) for p in evdev.list_devices()]
            self._devices = [d for d in all_devices if _is_physical_input(d.name)]
            if not self._devices:
                log.warning("EvdevInputBackend: no physical devices found")
                return
            log.info(
                "EvdevInputBackend started: %s",
                ", ".join(f"{d.name} ({d.path})" for d in self._devices),
            )
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._monitor_loop, daemon=True, name="evdev-input"
            )
            self._thread.start()
        except Exception:
            log.warning("EvdevInputBackend: failed to start", exc_info=True)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        for d in self._devices:
            try:
                d.close()
            except Exception:
                pass
        self._devices = []
        log.info("EvdevInputBackend stopped")

    def contribute(self, behaviors: dict[str, Behavior]) -> None:
        now = time.monotonic()
        active, idle_s = _compute_idle(self._last_event_ts, now)
        self._b_active.update(active, now)
        self._b_idle.update(idle_s, now)
        behaviors["real_keyboard_active"] = self._b_active
        behaviors["real_idle_seconds"] = self._b_idle

    def _monitor_loop(self) -> None:
        """Background thread: poll physical devices for any input event."""
        fds = {d.fd: d for d in self._devices}
        while not self._stop_event.is_set():
            try:
                r, _, _ = select.select(list(fds.keys()), [], [], 0.5)
                for fd in r:
                    device = fds.get(fd)
                    if device is None:
                        continue
                    for _event in device.read():
                        self._last_event_ts = time.monotonic()
            except Exception:
                if self._stop_event.is_set():
                    break
                time.sleep(0.5)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_daimonion/test_evdev_input.py -v`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check agents/hapax_daimonion/backends/evdev_input.py tests/hapax_daimonion/test_evdev_input.py
uv run ruff format agents/hapax_daimonion/backends/evdev_input.py tests/hapax_daimonion/test_evdev_input.py
git add agents/hapax_daimonion/backends/evdev_input.py tests/hapax_daimonion/test_evdev_input.py
git commit -m "feat: evdev input backend — physical keyboard/mouse, bypass virtual devices"
```

---

### Task 2: Wire Evdev Into Presence Engine (Replace Logind)

**Files:**
- Modify: `agents/hapax_daimonion/presence_engine.py` (lines 213-225)
- Modify: `agents/hapax_daimonion/init_backends.py`

- [ ] **Step 1: Register evdev backend in init_backends.py**

Add after the InputActivityBackend registration block (~line 108):

```python
    try:
        from agents.hapax_daimonion.backends.evdev_input import EvdevInputBackend

        daemon.perception.register_backend(EvdevInputBackend())
    except Exception:
        daemon.degradation_registry.record("backends", "EvdevInputBackend", "info", "not available")
```

- [ ] **Step 2: Replace keyboard_active signal source in presence_engine.py**

Replace lines 213-225 (the keyboard_active section) with:

```python
        # Keyboard/mouse active — from raw evdev (physical devices only).
        # Bypasses logind which is polluted by virtual input devices
        # (RustDesk UInput, mouce-library-fake-mouse, Claude Code subprocesses).
        # Falls back to logind input_active if evdev backend not available.
        b_real = behaviors.get("real_keyboard_active")
        b_real_idle = behaviors.get("real_idle_seconds")
        if b_real is not None:
            # Evdev backend available — use physical device data
            if b_real.value:
                obs["keyboard_active"] = True
            else:
                idle_s = float(b_real_idle.value) if b_real_idle is not None else 9999.0
                if idle_s > 300:
                    obs["keyboard_active"] = False  # genuinely idle >5min
                else:
                    obs["keyboard_active"] = None  # idle but not long enough to confirm absence
        else:
            # Fallback: logind (unreliable but better than nothing)
            b_active = behaviors.get("input_active")
            obs["keyboard_active"] = b_active.value if b_active is not None else None
```

- [ ] **Step 3: Run existing tests**

Run: `uv run pytest tests/hapax_daimonion/test_evdev_input.py tests/test_positive_feedback.py -v`
Expected: PASS

- [ ] **Step 4: Lint and commit**

```bash
uv run ruff check agents/hapax_daimonion/presence_engine.py agents/hapax_daimonion/init_backends.py
uv run ruff format agents/hapax_daimonion/presence_engine.py agents/hapax_daimonion/init_backends.py
git add agents/hapax_daimonion/presence_engine.py agents/hapax_daimonion/init_backends.py
git commit -m "feat: wire evdev input into presence engine, replace logind keyboard signal"
```

---

### Task 3: Watch HR Staleness as Bidirectional Absence Signal

**Files:**
- Modify: `agents/hapax_daimonion/backends/watch.py` (contribute method)
- Modify: `agents/hapax_daimonion/presence_engine.py` (watch_hr signal)
- Test: `tests/hapax_daimonion/test_watch_staleness.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for watch HR staleness as bidirectional presence signal."""

from __future__ import annotations

import time
from unittest.mock import MagicMock


def test_fresh_hr_is_presence():
    """HR data <30s old = True (presence evidence)."""
    from agents.hapax_daimonion.presence_engine import PresenceEngine

    engine = PresenceEngine()
    # Simulate: watch_hr_stale_seconds = 10 (fresh)
    from agents.hapax_daimonion.primitives import Behavior

    behaviors = {"heart_rate_bpm": Behavior(80), "watch_hr_stale_seconds": Behavior(10.0)}
    obs = engine._read_signals(behaviors)
    assert obs.get("watch_hr") is True


def test_medium_staleness_is_neutral():
    """HR data 30-120s old = None (neutral)."""
    from agents.hapax_daimonion.presence_engine import PresenceEngine
    from agents.hapax_daimonion.primitives import Behavior

    engine = PresenceEngine()
    behaviors = {"heart_rate_bpm": Behavior(80), "watch_hr_stale_seconds": Behavior(60.0)}
    obs = engine._read_signals(behaviors)
    assert obs.get("watch_hr") is None


def test_very_stale_hr_is_absence():
    """HR data >120s old = False (absence evidence — out of BLE range)."""
    from agents.hapax_daimonion.presence_engine import PresenceEngine
    from agents.hapax_daimonion.primitives import Behavior

    engine = PresenceEngine()
    behaviors = {"heart_rate_bpm": Behavior(80), "watch_hr_stale_seconds": Behavior(180.0)}
    obs = engine._read_signals(behaviors)
    assert obs.get("watch_hr") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/hapax_daimonion/test_watch_staleness.py -v`
Expected: FAIL (watch_hr_stale_seconds not provided by backend)

- [ ] **Step 3: Add HR staleness tracking to watch backend**

In `agents/hapax_daimonion/backends/watch.py`, add a new behavior. In `__init__`:

```python
        self._b_hr_stale: Behavior[float] = Behavior(9999.0)
```

Add `"watch_hr_stale_seconds"` to the `provides` frozenset.

In `contribute()`, after reading heartrate.json (~line 108), compute staleness from file mtime:

```python
        # Track HR data freshness for presence engine bidirectional signal
        hr_stale_s = 9999.0
        hr_path = self._reader._watch_dir / "heartrate.json"
        if hr_path.exists():
            try:
                hr_stale_s = time.time() - hr_path.stat().st_mtime
            except OSError:
                pass
        self._b_hr_stale.update(hr_stale_s, now)
```

At the end of contribute(), add:

```python
        behaviors["watch_hr_stale_seconds"] = self._b_hr_stale
```

- [ ] **Step 4: Update presence engine watch_hr signal to use staleness**

Replace the watch_hr section in `presence_engine.py` `_read_signals()`:

```python
        # Watch heart rate — bidirectional with staleness decay.
        # Fresh HR = presence evidence. Very stale = absence evidence (out of BLE range).
        b_hr = behaviors.get("heart_rate_bpm")
        b_stale = behaviors.get("watch_hr_stale_seconds")
        hr_stale = float(b_stale.value) if b_stale is not None and b_stale.value is not None else 9999.0
        if b_hr is not None and isinstance(b_hr.value, (int, float)) and b_hr.value > 0:
            if hr_stale < 30:
                obs["watch_hr"] = True  # fresh HR = present
            elif hr_stale < 120:
                obs["watch_hr"] = None  # medium stale = neutral (sync gap)
            else:
                obs["watch_hr"] = False  # very stale = absence (out of BLE range)
        else:
            obs["watch_hr"] = None  # no HR data at all = neutral
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/hapax_daimonion/test_watch_staleness.py -v`
Expected: PASS

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check agents/hapax_daimonion/backends/watch.py agents/hapax_daimonion/presence_engine.py
uv run ruff format agents/hapax_daimonion/backends/watch.py agents/hapax_daimonion/presence_engine.py
git add agents/hapax_daimonion/backends/watch.py agents/hapax_daimonion/presence_engine.py tests/hapax_daimonion/test_watch_staleness.py
git commit -m "feat: watch HR staleness as bidirectional absence signal (>120s = gone)"
```

---

### Task 4: Blue Yeti Ambient Audio Energy

**Files:**
- Create: `agents/hapax_daimonion/backends/ambient_audio.py`
- Test: `tests/hapax_daimonion/test_ambient_audio.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for AmbientAudioBackend — Blue Yeti room-level noise floor."""

from __future__ import annotations

import numpy as np

from agents.hapax_daimonion.primitives import Behavior


def test_backend_protocol():
    from agents.hapax_daimonion.backends.ambient_audio import AmbientAudioBackend

    backend = AmbientAudioBackend(source_name="Test Source")
    assert backend.name == "ambient_audio"
    assert "ambient_energy" in backend.provides


def test_rms_computation():
    from agents.hapax_daimonion.backends.ambient_audio import _compute_rms

    # Silence
    silence = np.zeros(480, dtype=np.int16).tobytes()
    assert _compute_rms(silence) == 0.0

    # Full-scale sine
    t = np.arange(480) / 16000.0
    loud = (0.5 * 32767 * np.sin(2 * np.pi * 440 * t)).astype(np.int16).tobytes()
    rms = _compute_rms(loud)
    assert 0.3 < rms < 0.4  # ~0.354 for 50% amplitude sine


def test_contribute_defaults():
    from agents.hapax_daimonion.backends.ambient_audio import AmbientAudioBackend

    backend = AmbientAudioBackend(source_name="Test Source")
    behaviors: dict[str, Behavior] = {}
    backend.contribute(behaviors)
    assert behaviors["ambient_energy"].value == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/hapax_daimonion/test_ambient_audio.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write the ambient audio backend**

```python
"""Ambient audio backend — room-level noise floor via Blue Yeti.

Captures from the Blue Yeti USB microphone via pw-cat. Computes
smoothed RMS energy as a room occupancy proxy: occupied rooms have
higher ambient noise (HVAC + movement + breathing) than empty rooms.

Provides:
  - ambient_energy: float (smoothed RMS, 0.0-1.0)
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time

import numpy as np

from agents.hapax_daimonion.perception import PerceptionTier
from agents.hapax_daimonion.primitives import Behavior

log = logging.getLogger(__name__)

_SAMPLE_RATE = 16000
_FRAME_MS = 30
_FRAME_SAMPLES = _SAMPLE_RATE * _FRAME_MS // 1000  # 480
_FRAME_BYTES = _FRAME_SAMPLES * 2  # int16
_SMOOTHING_ALPHA = 0.05  # slow smoothing for ambient level


def _compute_rms(frame: bytes) -> float:
    """Compute normalized RMS energy from int16 PCM frame."""
    samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(samples**2)))


class AmbientAudioBackend:
    """PerceptionBackend that captures ambient noise from Blue Yeti."""

    def __init__(self, source_name: str = "Yeti Stereo Microphone") -> None:
        self._source_name = source_name
        self._smoothed_energy: float = 0.0
        self._b_energy: Behavior[float] = Behavior(0.0)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def name(self) -> str:
        return "ambient_audio"

    @property
    def provides(self) -> frozenset[str]:
        return frozenset({"ambient_energy"})

    @property
    def tier(self) -> PerceptionTier:
        return PerceptionTier.FAST

    def available(self) -> bool:
        try:
            result = subprocess.run(
                ["pw-cli", "ls", "Node"],
                capture_output=True, text=True, timeout=3,
            )
            return self._source_name in result.stdout
        except Exception:
            return False

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="ambient-audio"
        )
        self._thread.start()
        log.info("AmbientAudioBackend started (source=%s)", self._source_name)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        log.info("AmbientAudioBackend stopped")

    def contribute(self, behaviors: dict[str, Behavior]) -> None:
        now = time.monotonic()
        self._b_energy.update(self._smoothed_energy, now)
        behaviors["ambient_energy"] = self._b_energy

    def _capture_loop(self) -> None:
        """Background thread: capture Yeti audio, compute smoothed RMS."""
        retry_delay = 2.0

        while not self._stop_event.is_set():
            proc = None
            try:
                cmd = [
                    "pw-cat", "--record",
                    "--target", self._source_name,
                    "--format", "s16",
                    "--rate", str(_SAMPLE_RATE),
                    "--channels", "1",
                    "-",
                ]
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
                )
                log.info("Ambient audio capturing via pw-cat (target=%s)", self._source_name)
                retry_delay = 2.0

                while not self._stop_event.is_set():
                    assert proc.stdout is not None
                    data = proc.stdout.read(_FRAME_BYTES)
                    if not data or len(data) < _FRAME_BYTES:
                        break
                    rms = _compute_rms(data)
                    self._smoothed_energy = (
                        _SMOOTHING_ALPHA * rms
                        + (1 - _SMOOTHING_ALPHA) * self._smoothed_energy
                    )

            except Exception:
                if self._stop_event.is_set():
                    break
                log.warning("Ambient audio pw-cat failed — retrying in %.0fs", retry_delay, exc_info=True)
            finally:
                if proc is not None:
                    try:
                        proc.terminate()
                        proc.wait(timeout=2)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass

            if not self._stop_event.is_set():
                self._stop_event.wait(timeout=retry_delay)
                retry_delay = min(retry_delay * 2, 30.0)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/hapax_daimonion/test_ambient_audio.py -v`
Expected: PASS

- [ ] **Step 5: Register backend and wire into presence engine**

In `init_backends.py`, add after ContactMicBackend registration:

```python
    try:
        from agents.hapax_daimonion.backends.ambient_audio import AmbientAudioBackend

        daemon.perception.register_backend(AmbientAudioBackend())
    except Exception:
        daemon.degradation_registry.record("backends", "AmbientAudioBackend", "info", "not available")
```

In `presence_engine.py`, add `"ambient_energy"` to `DEFAULT_SIGNAL_WEIGHTS`:

```python
    "ambient_energy": (0.60, 0.20),  # Room noise floor — occupied vs empty
```

In `_read_signals()`, add before the return:

```python
        # Ambient audio: positive-only. Room noise above baseline = occupied.
        # Silent room = neutral (could be quiet work, not necessarily empty).
        b = behaviors.get("ambient_energy")
        if b is not None and isinstance(b.value, (int, float)) and b.value > 0.001:
            obs["ambient_energy"] = True
        else:
            obs["ambient_energy"] = None
```

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check agents/hapax_daimonion/backends/ambient_audio.py agents/hapax_daimonion/init_backends.py agents/hapax_daimonion/presence_engine.py
uv run ruff format agents/hapax_daimonion/backends/ambient_audio.py
git add agents/hapax_daimonion/backends/ambient_audio.py agents/hapax_daimonion/init_backends.py agents/hapax_daimonion/presence_engine.py tests/hapax_daimonion/test_ambient_audio.py
git commit -m "feat: Blue Yeti ambient audio backend — room occupancy via noise floor"
```

---

### Task 5: IR Brightness Delta as Body-Heat Proxy

**Files:**
- Modify: `agents/hapax_daimonion/backends/ir_presence.py`
- Modify: `agents/hapax_daimonion/presence_engine.py`
- Test: `tests/hapax_daimonion/test_ir_brightness.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for IR brightness delta as body-heat proxy."""

from __future__ import annotations

from collections import deque


def test_stable_brightness_no_signal():
    from agents.hapax_daimonion.backends.ir_presence import _compute_brightness_delta

    history = deque([100.0] * 30, maxlen=30)
    assert _compute_brightness_delta(history, 100.0) == 0.0


def test_brightness_drop_signals_departure():
    from agents.hapax_daimonion.backends.ir_presence import _compute_brightness_delta

    history = deque([120.0] * 30, maxlen=30)
    # Body left — brightness dropped from 120 to 100
    delta = _compute_brightness_delta(history, 100.0)
    assert delta < -15  # significant drop


def test_brightness_rise_signals_arrival():
    from agents.hapax_daimonion.backends.ir_presence import _compute_brightness_delta

    history = deque([90.0] * 30, maxlen=30)
    # Body arrived — brightness rose from 90 to 115
    delta = _compute_brightness_delta(history, 115.0)
    assert delta > 15  # significant rise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/hapax_daimonion/test_ir_brightness.py -v`
Expected: FAIL (function not found)

- [ ] **Step 3: Add brightness delta tracking to IR backend**

In `agents/hapax_daimonion/backends/ir_presence.py`, add at module level:

```python
from collections import deque as _deque

def _compute_brightness_delta(
    history: _deque[float], current: float
) -> float:
    """Compute brightness delta: current vs rolling 30-sample average."""
    if len(history) < 10:
        return 0.0
    avg = sum(history) / len(history)
    return current - avg
```

In the `IrPresenceBackend.__init__()`, add:

```python
        self._brightness_history: _deque[float] = _deque(maxlen=30)
        self._b_brightness_delta: Behavior[float] = Behavior(0.0)
```

Add `"ir_brightness_delta"` to the `provides` frozenset.

In the `contribute()` method, after `self._fuse(reports, now)`, add:

```python
        # Track IR brightness rolling delta for body-heat proxy
        brightness = float(self._behaviors.get("ir_brightness", Behavior(0.0)).value or 0.0)
        self._brightness_history.append(brightness)
        delta = _compute_brightness_delta(self._brightness_history, brightness)
        self._b_brightness_delta.update(delta, now)
        behaviors["ir_brightness_delta"] = self._b_brightness_delta
```

- [ ] **Step 4: Wire into presence engine**

In `presence_engine.py`, add to `DEFAULT_SIGNAL_WEIGHTS`:

```python
    "ir_body_heat": (0.70, 0.15),  # IR brightness rise = body arrived
```

In `_read_signals()`, add before the return:

```python
        # IR brightness delta: body-heat proxy. Significant brightness rise = body
        # arrived (skin reflects 850nm). Significant drop = body left.
        b_delta = behaviors.get("ir_brightness_delta")
        if b_delta is not None and isinstance(b_delta.value, (int, float)):
            if b_delta.value > 15:
                obs["ir_body_heat"] = True  # brightness rose — body arrived
            elif b_delta.value < -15:
                obs["ir_body_heat"] = False  # brightness dropped — body left
            else:
                obs["ir_body_heat"] = None  # stable — no change
        else:
            obs["ir_body_heat"] = None
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/hapax_daimonion/test_ir_brightness.py -v`
Expected: PASS

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check agents/hapax_daimonion/backends/ir_presence.py agents/hapax_daimonion/presence_engine.py
uv run ruff format agents/hapax_daimonion/backends/ir_presence.py agents/hapax_daimonion/presence_engine.py
git add agents/hapax_daimonion/backends/ir_presence.py agents/hapax_daimonion/presence_engine.py tests/hapax_daimonion/test_ir_brightness.py
git commit -m "feat: IR brightness delta as body-heat proxy in presence engine"
```

---

### Task 6: Integration Test — Full Restart and Presence Diagnostic

**Files:** None (operational verification)

- [ ] **Step 1: Restart all affected services**

```bash
systemctl --user restart hapax-daimonion.service
systemctl --user restart hapax-reverie.service
systemctl --user restart logos-api.service
```

- [ ] **Step 2: Verify evdev backend registered**

```bash
journalctl --user -u hapax-daimonion --since "30 sec ago" --output cat | grep -i 'evdev\|EvdevInput'
```

Expected: `EvdevInputBackend started: Keychron Keychron Link Keyboard (...), Logitech USB Receiver Mouse (...)`

- [ ] **Step 3: Verify ambient audio backend registered**

```bash
journalctl --user -u hapax-daimonion --since "30 sec ago" --output cat | grep -i 'ambient\|AmbientAudio'
```

Expected: `AmbientAudioBackend started (source=Yeti Stereo Microphone)`

- [ ] **Step 4: Wait for presence diagnostic and verify signal landscape**

```bash
sleep 90 && journalctl --user -u hapax-daimonion --since "30 sec ago" --output cat | grep 'PRESENCE diag'
```

Expected: `signals={'real_keyboard_active': True, 'ir_hand_active': True, 'ambient_energy': True}` (or similar multi-signal output)

- [ ] **Step 5: Verify prediction monitor reads new presence value**

```bash
uv run python -m agents.reverie_prediction_monitor 2>&1 | grep P6
```

Expected: `P6_presence_differentiation: 0.999...` with `healthy=True`

- [ ] **Step 6: Final commit with updated CLAUDE.md**

Update the Bayesian Presence Detection section in `CLAUDE.md` to reflect new signals:
- `real_keyboard_active` (evdev, replaces logind)
- `watch_hr` (bidirectional with staleness)
- `ambient_energy` (Yeti noise floor)
- `ir_body_heat` (brightness delta proxy)

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with proximity overhaul signals"
git push origin main
```

---

### Task 7: Calibration Walk (Operator Required)

**Files:** None (data collection)

This task requires the operator to physically move. Cannot be automated.

- [ ] **Step 1: Start monitoring**

```bash
watch -n 2 'cat ~/.cache/hapax-daimonion/perception-state.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"presence={d.get(chr(39)presence_probability{chr(39),0):.3f} state={d.get(chr(39)presence_state{chr(39),chr(39)?{chr(39))}\")"'
```

Or use the Grafana dashboard Presence Posterior panel.

- [ ] **Step 2: Baseline — sit at desk 5 min**

Record: all signals active, posterior ~0.999

- [ ] **Step 3: Room center — stand up, move 2m from desk, wait 2 min**

Record: keyboard idle, contact mic silent, IR motion present, watch HR fresh
Expected posterior: 0.5-0.8

- [ ] **Step 4: Hallway — leave room, stand in hallway 2 min**

Record: all desk signals idle, watch HR staling (30-120s), IR motion absent
Expected posterior: 0.2-0.5

- [ ] **Step 5: Leave building — go outside 5 min**

Record: watch HR very stale (>120s = False), all signals neutral/absent
Expected posterior: <0.1

- [ ] **Step 6: Return — walk back to desk**

Record: time to recover to PRESENT state
Expected: <10s from first keystroke

- [ ] **Step 7: Document thresholds**

If any expected posteriors are wrong, adjust signal weights or thresholds in `presence_engine.py` and commit.
