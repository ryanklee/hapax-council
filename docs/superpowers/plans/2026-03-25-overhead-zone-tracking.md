# Overhead Zone Tracking — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add instrument zone detection from overhead camera and fuse with contact mic desk_activity for high-confidence production activity classification.

**Architecture:** Static instrument zones in cameras.py, MediaPipe hand centroid mapping in vision backend, desk_activity injected via set_desk_context() cache pattern, fusion rules in _infer_cross_modal_activity().

**Tech Stack:** MediaPipe GestureRecognizer (existing), NumPy, OpenCV (existing), no new dependencies

**Spec:** `docs/superpowers/specs/2026-03-25-overhead-zone-tracking.md`

---

## Task 1: Zone Definitions + Unit Tests

**Files:**
- Edit: `shared/cameras.py`
- Create: `tests/test_cameras_zones.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for instrument zone mapping."""
from __future__ import annotations
from shared.cameras import InstrumentZone, OVERHEAD_ZONES, point_in_zone

class TestInstrumentZone:
    def test_zone_count(self):
        assert len(OVERHEAD_ZONES) == 4

    def test_zone_names(self):
        names = {z.name for z in OVERHEAD_ZONES}
        assert names == {"turntable", "pads", "mixer", "keyboard"}

class TestPointInZone:
    def test_turntable_center(self):
        assert point_in_zone(200, 300) == "turntable"

    def test_pads_center(self):
        assert point_in_zone(600, 350) == "pads"

    def test_keyboard_center(self):
        assert point_in_zone(1000, 450) == "keyboard"

    def test_outside_all_zones(self):
        assert point_in_zone(1279, 0) == "unknown"

    def test_boundary_inclusive(self):
        z = OVERHEAD_ZONES[0]  # turntable
        assert point_in_zone(z.x1, z.y1) == "turntable"
        assert point_in_zone(z.x2, z.y2) == "turntable"
```

- [ ] **Step 2: Run tests — verify fail**
- [ ] **Step 3: Add to cameras.py** (after CAMERAS tuple, before derived lookups):

```python
@dataclass(frozen=True)
class InstrumentZone:
    """Bounding box for an instrument zone in the overhead frame."""
    name: str
    x1: int
    y1: int
    x2: int
    y2: int

OVERHEAD_ZONES: tuple[InstrumentZone, ...] = (
    InstrumentZone("turntable", 0, 100, 400, 550),
    InstrumentZone("pads", 400, 150, 800, 500),
    InstrumentZone("mixer", 300, 0, 550, 200),
    InstrumentZone("keyboard", 800, 300, 1280, 600),
)

def point_in_zone(x: int, y: int) -> str:
    for z in OVERHEAD_ZONES:
        if z.x1 <= x <= z.x2 and z.y1 <= y <= z.y2:
            return z.name
    return "unknown"
```

- [ ] **Step 4: Run tests — verify pass**
- [ ] **Step 5: Lint + commit**

---

## Task 2: Vision Backend — Overhead Hand Zones + Fusion

**Files:**
- Edit: `agents/hapax_voice/backends/vision.py`
- Create: `tests/hapax_voice/test_overhead_zones.py`

This is the largest task. Follow the spec closely for:
1. `_run_overhead_hand_zones()` method using `self._gesture_recognizer`
2. `set_desk_context()` on `_VisionCache` (mirrors `set_audio_context`)
3. `desk_activity` parameter on `_infer_cross_modal_activity()`
4. Fusion rules before existing rules
5. `overhead_hand_zones` behavior in provides/contribute
6. `num_hands=2` change
7. Per-camera cache storage of hand_zones

Tests should mock MediaPipe and test the fusion rules directly.

- [ ] **Step 1: Write tests for fusion rules**

```python
"""Tests for overhead zone tracking in vision backend."""
from __future__ import annotations
from agents.hapax_voice.backends.vision import _infer_cross_modal_activity

class TestCrossModalFusionWithZones:
    def test_scratching_turntable_zone(self):
        per_cam = {"overhead": {"hand_zones": "turntable", "person_count": 1}}
        activity, conf = _infer_cross_modal_activity(
            per_cam, "production", "unknown", 0.5, desk_activity="scratching"
        )
        assert activity == "scratching"
        assert conf == 0.95

    def test_pads_drumming(self):
        per_cam = {"overhead": {"hand_zones": "pads", "person_count": 1}}
        activity, conf = _infer_cross_modal_activity(
            per_cam, "production", "unknown", 0.5, desk_activity="drumming"
        )
        assert activity == "playing_pads"

    def test_keyboard_typing(self):
        per_cam = {"overhead": {"hand_zones": "keyboard", "person_count": 1}}
        activity, conf = _infer_cross_modal_activity(
            per_cam, "idle", "unknown", 0.0, desk_activity="typing"
        )
        assert activity == "coding"

    def test_no_desk_activity_falls_through(self):
        per_cam = {"overhead": {"hand_zones": "turntable", "person_count": 1}}
        activity, conf = _infer_cross_modal_activity(
            per_cam, "production", "unknown", 0.5, desk_activity=""
        )
        assert activity == "producing"  # falls through to existing rule

    def test_backward_compatible_no_desk_activity(self):
        per_cam = {"operator": {"person_count": 1, "gaze_direction": "screen"}}
        activity, conf = _infer_cross_modal_activity(
            per_cam, "production", "unknown", 0.5
        )
        assert activity == "producing"
```

- [ ] **Step 2: Run tests — verify fail**
- [ ] **Step 3: Implement all changes per spec**
- [ ] **Step 4: Run tests — verify pass**
- [ ] **Step 5: Lint + commit**

---

## Task 3: Pipeline Wiring + Push

**Files:**
- Edit: `agents/hapax_voice/_perception_state_writer.py`
- Edit: `agents/studio_compositor.py`

- [ ] **Step 1: Add overhead_hand_zones to state writer**
- [ ] **Step 2: Add overhead_hand_zones to OverlayData**
- [ ] **Step 3: Run all tests**
- [ ] **Step 4: Lint + commit**
- [ ] **Step 5: Push and update PR #333**
