# Camera Profile Automation — Design Spec

**Date:** 2026-03-31
**Author:** delta session
**Status:** Design approved, pending implementation
**Motivation:** Camera V4L2 controls (exposure, gain, white balance) are set once at service start via `studio-camera-setup.sh`. The `profiles.py` module implements schedule and condition evaluation, but no profile library exists. Cameras cannot adapt to lighting changes, recording modes, or time of day.
**Depends on:** 2026-03-31-studio-effects-consolidation-design.md (Stage 1)

---

## Problem

1. **Static camera settings.** All cameras use fixed V4L2 controls set at boot. Night sessions are too dark; day sessions can be overexposed.
2. **No recording optimization.** Recording mode should prefer lower gain (less noise) and locked exposure for consistent footage. Live mode can be more aggressive with auto-gain.
3. **Profile infrastructure exists but is empty.** `profiles.py` has `evaluate_active_profile()` and `apply_camera_profile()` — both functional — but `CompositorConfig.camera_profiles` is always empty because no YAML profile definitions exist.
4. **Per-camera control divergence.** BRIOs and C920s have different optimal settings. Current setup script hardcodes per-model values but doesn't adapt dynamically.

---

## Solution

A YAML-driven camera profile library with schedule-based and condition-based activation. Profiles define per-camera V4L2 control overrides. The existing evaluation engine in `profiles.py` selects the active profile every 10 seconds.

### Design Decisions

- **D1: YAML not JSON.** Camera profiles are human-authored operational config, not machine-generated data. YAML is more readable for V4L2 control names and ranges.
- **D2: Per-model defaults + per-role overrides.** A profile defines defaults for `brio` and `c920` models, then optional per-role overrides (e.g., `brio-operator` gets different exposure than `brio-room`).
- **D3: Schedule + condition union.** A profile activates when its schedule matches OR its condition matches. Conditions take precedence over schedules when both match.
- **D4: Transition smoothing.** V4L2 exposure/gain changes can cause visible jumps. Apply changes gradually over 3 frames (write intermediate values on each tick).

---

## Architecture

### Profile YAML Schema

```yaml
# ~/.config/hapax/camera-profiles/night.yaml
name: night
description: Low-light optimization for evening sessions
schedule: "20:00-06:00"   # or "night" shorthand
priority: 10              # higher wins when multiple match

defaults:
  brio:
    exposure_time_absolute: 500     # longer exposure for low light
    gain: 120
    white_balance_temperature: 3800  # warmer
    sharpness: 100
  c920:
    exposure_time_absolute: 500
    gain: 180
    white_balance_temperature: 3800
    sharpness: 90

overrides:
  brio-operator:
    exposure_time_absolute: 400     # hero camera slightly faster for less blur
    gain: 100
```

### Profile Library Location

`~/.config/hapax/camera-profiles/*.yaml`

Bundled defaults in repo: `config/camera-profiles/` (copied to ~/.config on first run if missing).

### Evaluation Flow

```
Every 10 seconds (state.py):
  1. List all profiles from ~/.config/hapax/camera-profiles/
  2. Filter: schedule matches current time OR condition matches current state
  3. Sort by priority (descending)
  4. If top match differs from current active → transition
  5. For each camera:
     a. Start with model defaults (brio or c920)
     b. Apply per-role overrides
     c. Compute delta from current V4L2 values
     d. If delta exists: apply via v4l2-ctl (smoothed over 3 ticks)
```

---

## Core Components

### 1. Profile Model Extension

**File:** `agents/studio_compositor/models.py`

```python
class CameraProfileDef(BaseModel):
    name: str
    description: str = ""
    schedule: str | None = None        # "night", "day", "HH:MM-HH:MM"
    condition: dict[str, str] | None = None  # {"production_activity": "recording"}
    priority: int = 0
    defaults: dict[str, dict[str, int]]  # {"brio": {...}, "c920": {...}}
    overrides: dict[str, dict[str, int]] = {}  # {"brio-operator": {...}}
```

### 2. Profile Library Loader

**File:** `agents/studio_compositor/profile_library.py` (new)

```python
def load_profiles(profile_dir: Path) -> list[CameraProfileDef]:
    """Load all .yaml profiles from directory, sorted by priority."""

def resolve_controls(
    profile: CameraProfileDef,
    role: str,
    model: str,  # "brio" or "c920"
) -> dict[str, int]:
    """Merge model defaults + role overrides into final V4L2 control dict."""
```

### 3. Transition Smoother

**File:** `agents/studio_compositor/profiles.py` (extend)

```python
class ProfileTransition:
    """Gradually apply V4L2 control changes over N ticks."""
    target: dict[str, dict[str, int]]   # role → {control: value}
    current: dict[str, dict[str, int]]  # role → {control: value}
    remaining_steps: int = 3

    def step(self) -> dict[str, dict[str, int]]:
        """Return interpolated controls for this tick. Decrement remaining."""
```

### 4. Bundled Default Profiles

**night.yaml:** Long exposure, high gain, warm white balance
**day.yaml:** Short exposure, low gain, neutral white balance
**recording.yaml:** Condition: `production_activity=recording`. Locked exposure, minimal gain, maximum sharpness
**streaming.yaml:** Condition: `production_activity=streaming`. Balanced settings, auto-friendly

---

## File Map

### New files

| File | Purpose |
|------|---------|
| `agents/studio_compositor/profile_library.py` | YAML loader + control resolver |
| `config/camera-profiles/night.yaml` | Bundled default: low-light profile |
| `config/camera-profiles/day.yaml` | Bundled default: daylight profile |
| `config/camera-profiles/recording.yaml` | Bundled default: recording-optimized |
| `config/camera-profiles/streaming.yaml` | Bundled default: streaming-optimized |
| `tests/studio_compositor/test_profiles.py` | Profile loading, evaluation, and resolution tests |

### Modified files

| File | Change |
|------|--------|
| `agents/studio_compositor/models.py` | Add `CameraProfileDef` model |
| `agents/studio_compositor/profiles.py` | Add `ProfileTransition` smoother, integrate library loader |
| `agents/studio_compositor/config.py` | Add `CAMERA_PROFILE_DIR` constant |
| `agents/studio_compositor/state.py` | Wire profile evaluation into 10s tick |

---

## Acceptance Criteria

1. 4 bundled profile YAML files install to `~/.config/hapax/camera-profiles/` on first run.
2. `night` profile activates automatically between 20:00-06:00.
3. `recording` profile activates when `production_activity=recording` condition matches.
4. Profile transitions apply V4L2 changes gradually over 3 ticks (no visible jump).
5. Per-role overrides work: `brio-operator` can have different exposure than `brio-room`.
6. Adding a new `.yaml` file to the profile directory is picked up within 10 seconds (no restart).
7. Removing all profiles reverts to `studio-camera-setup.sh` defaults.

## Constraints

- **V4L2 latency.** `v4l2-ctl` is a subprocess call (~50ms). Smoothed over 3 ticks = 30 seconds between full transitions.
- **No auto-exposure.** All profiles use manual exposure. Auto-exposure is disabled globally because it causes flicker under mixed lighting (fluorescent + LED).
- **Camera model detection.** Profile `defaults` key must match camera model prefix. Model is derived from camera role name (`brio-*` or `c920-*`).
- **Thread safety.** `apply_camera_profile()` runs in the state reader thread. V4L2 calls are thread-safe (separate process).
