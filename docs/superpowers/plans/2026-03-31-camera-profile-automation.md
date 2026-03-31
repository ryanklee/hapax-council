# Camera Profile Automation — Implementation Plan

**Goal:** YAML-driven camera profile library with schedule/condition-based automatic V4L2 control changes.
**Spec:** `~/.cache/hapax/specs/2026-03-31-camera-profile-automation-design.md`
**Tech Stack:** Python 3.12, PyYAML, Pydantic, v4l2-ctl (subprocess), pytest

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans.

---

## Phase 1: Profile Model + Library Loader

### Task 1.1: Add CameraProfileDef model

**Files:**
- Modify: `agents/studio_compositor/models.py`

- [ ] **Step 1:** Add Pydantic model:
  ```python
  class CameraProfileDef(BaseModel):
      name: str
      description: str = ""
      schedule: str | None = None
      condition: dict[str, str] | None = None
      priority: int = 0
      defaults: dict[str, dict[str, int]]  # model → {control: value}
      overrides: dict[str, dict[str, int]] = {}  # role → {control: value}
  ```

- [ ] **Step 2:** Commit: `feat(compositor): add CameraProfileDef model`

### Task 1.2: Create profile library loader

**Files:**
- Create: `agents/studio_compositor/profile_library.py`

- [ ] **Step 1:** Implement `load_profiles(profile_dir: Path) -> list[CameraProfileDef]`:
  - Glob `*.yaml` files
  - Parse with PyYAML + validate with Pydantic
  - Sort by priority descending
  - Log and skip malformed files

- [ ] **Step 2:** Implement `resolve_controls(profile, role, model) -> dict[str, int]`:
  - Start with `profile.defaults[model]`
  - Merge `profile.overrides[role]` if present
  - Return final control dict

- [ ] **Step 3:** Write tests in `tests/studio_compositor/test_profile_library.py`:
  - Load valid YAML → CameraProfileDef
  - Resolve controls with model defaults only
  - Resolve controls with per-role overrides
  - Malformed YAML skipped gracefully
  - Empty directory returns empty list

- [ ] **Step 4:** Run: `uv run pytest tests/studio_compositor/test_profile_library.py -v`

- [ ] **Step 5:** Commit: `feat(compositor): YAML profile library loader + resolver`

---

## Phase 2: Bundled Profiles + First-Run Install

### Task 2.1: Write four default profiles

**Files:**
- Create: `config/camera-profiles/night.yaml`
- Create: `config/camera-profiles/day.yaml`
- Create: `config/camera-profiles/recording.yaml`
- Create: `config/camera-profiles/streaming.yaml`

- [ ] **Step 1:** Write `night.yaml`:
  ```yaml
  name: night
  description: Low-light optimization (20:00-06:00)
  schedule: "night"
  priority: 10
  defaults:
    brio:
      exposure_time_absolute: 500
      gain: 120
      white_balance_temperature: 3800
      sharpness: 100
    c920:
      exposure_time_absolute: 500
      gain: 180
      white_balance_temperature: 3800
      sharpness: 90
  overrides:
    brio-operator:
      exposure_time_absolute: 400
      gain: 100
  ```

- [ ] **Step 2:** Write `day.yaml` (schedule: "day", shorter exposure, lower gain, 5000K)

- [ ] **Step 3:** Write `recording.yaml` (condition: `production_activity: recording`, locked exposure, low gain, max sharpness, priority: 20)

- [ ] **Step 4:** Write `streaming.yaml` (condition: `production_activity: streaming`, balanced, priority: 15)

- [ ] **Step 5:** Commit: `feat(compositor): bundled default camera profiles`

### Task 2.2: First-run copy mechanism

**Files:**
- Modify: `agents/studio_compositor/config.py`

- [ ] **Step 1:** Add constant:
  ```python
  CAMERA_PROFILE_DIR = Path("~/.config/hapax/camera-profiles").expanduser()
  BUNDLED_PROFILES = Path(__file__).parent.parent.parent / "config" / "camera-profiles"
  ```

- [ ] **Step 2:** Add `ensure_profile_dir()`:
  - If `CAMERA_PROFILE_DIR` doesn't exist or is empty: copy from `BUNDLED_PROFILES`
  - If it exists with files: do nothing (user may have customized)

- [ ] **Step 3:** Call from `__main__.py` before compositor start.

- [ ] **Step 4:** Commit: `feat(compositor): first-run profile directory bootstrap`

---

## Phase 3: Transition Smoother + Integration

### Task 3.1: Implement ProfileTransition

**Files:**
- Modify: `agents/studio_compositor/profiles.py`

- [ ] **Step 1:** Add `ProfileTransition` class:
  - Stores target + current control dicts per role
  - `step()` returns linearly interpolated values, decrementing `remaining_steps`
  - Integer rounding for V4L2 controls (they're integer-only)

- [ ] **Step 2:** Integrate into `evaluate_active_profile()`:
  - If new profile differs from active: create `ProfileTransition` with 3 steps
  - On each 10s tick: if transition active, call `step()` and apply

- [ ] **Step 3:** Test: transition from night → day profile applies 3 intermediate v4l2-ctl calls.

- [ ] **Step 4:** Commit: `feat(compositor): profile transition smoother (3-step)`

### Task 3.2: Wire into state reader loop

**Files:**
- Modify: `agents/studio_compositor/state.py`

- [ ] **Step 1:** In the 10s profile evaluation tick, load profiles from `CAMERA_PROFILE_DIR`.

- [ ] **Step 2:** Pass current `OverlayData` for condition evaluation.

- [ ] **Step 3:** If profile changes: log transition, start `ProfileTransition`.

- [ ] **Step 4:** Test end-to-end: change system clock past 20:00, verify night profile activates.

- [ ] **Step 5:** Commit: `feat(compositor): wire profile evaluation into state reader`

---

## Phase 4: API + Documentation

### Task 4.1: Add profile API endpoints

**Files:**
- Modify: `logos/api/routes/studio.py`

- [ ] **Step 1:** `GET /studio/profiles` — list loaded profiles with active indicator
- [ ] **Step 2:** `POST /studio/profiles/{name}/activate` — manual override (bypasses schedule/condition)
- [ ] **Step 3:** `POST /studio/profiles/reset` — clear manual override, return to automatic evaluation

- [ ] **Step 4:** Commit: `feat(api): camera profile list + manual activation endpoints`

---

## Acceptance Gates

| Gate | Condition |
|------|-----------|
| Phase 1 | Profile model + loader with tests. |
| Phase 2 | 4 YAML profiles. First-run install. |
| Phase 3 | Auto-activation by schedule. Smooth transition. |
| Phase 4 | API endpoints for manual override. |
