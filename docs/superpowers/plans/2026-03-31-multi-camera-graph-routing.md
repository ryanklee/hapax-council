# Multi-Camera Graph Routing — Implementation Plan

**Goal:** Enable individual camera feeds as first-class effect graph inputs via `@cam:{role}` layer sources.
**Spec:** `~/.cache/hapax/specs/2026-03-31-multi-camera-graph-routing-design.md`
**Tech Stack:** Python 3.12, GStreamer (v4l2src, appsink), Rust/wgpu (memmap2), Pydantic, pytest

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans.

---

## Phase 1: Python Graph Engine (no GPU changes)

### Task 1.1: Extend compiler to accept @cam:* sources

**Files:**
- Modify: `agents/effect_graph/compiler.py`
- Modify: `agents/effect_graph/types.py` (add KNOWN_CAMERA_ROLES constant)

- [ ] **Step 1:** Add `KNOWN_CAMERA_ROLES` set to `types.py`:
  ```python
  KNOWN_CAMERA_ROLES: set[str] = {
      "brio-operator", "brio-room", "brio-synths",
      "c920-desk", "c920-room", "c920-overhead",
  }
  CAMERA_SOURCE_PREFIX = "@cam:"
  ```

- [ ] **Step 2:** Replace hardcoded validation in `compiler.py:_validate()` (line ~67):
  ```python
  from .types import KNOWN_CAMERA_ROLES, CAMERA_SOURCE_PREFIX

  def _is_valid_layer_source(name: str) -> bool:
      if name in VALID_LAYER_SOURCES:
          return True
      if name.startswith(CAMERA_SOURCE_PREFIX):
          return name[len(CAMERA_SOURCE_PREFIX):] in KNOWN_CAMERA_ROLES
      return False
  ```

- [ ] **Step 3:** Write tests in `tests/effect_graph/test_camera_sources.py`:
  - Graph with `@cam:brio-operator` edge compiles successfully
  - Graph with `@cam:invalid-camera` raises `GraphValidationError`
  - Graph mixing `@live` and `@cam:brio-operator` compiles
  - Existing presets still compile (regression)

- [ ] **Step 4:** Run tests: `uv run pytest tests/effect_graph/ -v`

- [ ] **Step 5:** Commit: `feat(effect-graph): accept @cam:{role} layer sources in compiler`

### Task 1.2: Extend WGSL compiler to emit camera inputs in plan.json

**Files:**
- Modify: `agents/effect_graph/wgsl_compiler.py`

- [ ] **Step 1:** In `compile_to_wgsl_plan()`, camera source inputs pass through to plan.json unchanged (they already should — verify that `@cam:brio-operator` appears in the `inputs` array of the relevant pass).

- [ ] **Step 2:** Add test: compile a graph with `@cam:brio-operator` input, assert plan.json pass has `"@cam:brio-operator"` in inputs list.

- [ ] **Step 3:** Run tests: `uv run pytest tests/effect_graph/test_wgsl_compiler.py -v`

- [ ] **Step 4:** Commit: `feat(wgsl-compiler): pass @cam sources through to plan.json`

### Task 1.3: Create sample multi-camera preset

**Files:**
- Create: `presets/dual_cam_split.json`

- [ ] **Step 1:** Write the preset:
  ```json
  {
    "name": "dual-cam-split",
    "description": "Split-screen: brio-operator (trails) | c920-desk (edge detect)",
    "transition_ms": 500,
    "nodes": {
      "trails_op": { "type": "trail", "params": { "decay": 0.92 } },
      "edge_desk": { "type": "edge_detect", "params": { "threshold": 0.3 } },
      "split": { "type": "blend", "params": { "mode": 1.0, "mix": 0.5 } },
      "content": { "type": "content_layer", "params": {} },
      "post": { "type": "postprocess", "params": {} },
      "out": { "type": "output", "params": {} }
    },
    "edges": [
      ["@cam:brio-operator", "trails_op:in"],
      ["@cam:c920-desk", "edge_desk:in"],
      ["trails_op:out", "split:a"],
      ["edge_desk:out", "split:b"],
      ["split:out", "content:in"],
      ["content:out", "post:in"],
      ["post:out", "out:in"]
    ],
    "modulations": [],
    "layer_palettes": {}
  }
  ```

- [ ] **Step 2:** Verify it compiles: `uv run python -c "from agents.effect_graph.compiler import GraphCompiler; ..."`

- [ ] **Step 3:** Commit: `feat(presets): add dual-cam-split multi-camera preset`

---

## Phase 2: GStreamer Camera Feed Export

### Task 2.1: Add graph-feed branch to camera pipeline

**Files:**
- Modify: `agents/studio_compositor/cameras.py`
- Modify: `agents/studio_compositor/config.py` (add SHM path constant)

- [ ] **Step 1:** Add constant to `config.py`:
  ```python
  CAMERA_FEED_DIR = Path("/dev/shm/hapax-imagination/cameras")
  ```

- [ ] **Step 2:** Add `add_graph_feed_branch()` function to `cameras.py`:
  - Request pad from camera_tee
  - queue (leaky=2, max-size-buffers=2) → videoconvert (RGBA) → appsink
  - Appsink callback: write raw RGBA to mmap'd file + metadata JSON
  - Only activated when compositor detects active preset needs this camera

- [ ] **Step 3:** Add activation tracking in `compositor.py`:
  - `_active_camera_feeds: set[str]` — which roles have graph-feed branches active
  - `_update_camera_feeds(required_roles)` — add/remove branches dynamically

- [ ] **Step 4:** Test manually: activate `dual-cam-split` preset, verify RGBA files appear in `/dev/shm/hapax-imagination/cameras/`

- [ ] **Step 5:** Commit: `feat(compositor): export per-camera RGBA frames to SHM for GPU pipeline`

### Task 2.2: Demand-driven activation via preset analysis

**Files:**
- Modify: `agents/studio_compositor/state.py`
- Modify: `agents/studio_compositor/effects.py`

- [ ] **Step 1:** In `state.py`, when processing `fx-request.txt`, parse the preset JSON to extract `@cam:*` edge sources.

- [ ] **Step 2:** Pass required camera roles to compositor for branch activation/deactivation.

- [ ] **Step 3:** When preset changes to one without camera sources, deactivate all graph-feed branches (stop SHM writes).

- [ ] **Step 4:** Commit: `feat(compositor): demand-driven camera feed activation from preset analysis`

---

## Phase 3: Rust GPU Integration

### Task 3.1: CameraTexturePool module

**Files:**
- Create: `hapax-logos/crates/hapax-visual/src/camera_textures.rs`
- Modify: `hapax-logos/crates/hapax-visual/src/lib.rs`

- [ ] **Step 1:** Implement `CameraTexturePool`:
  - `new(device)` — initialize empty pool
  - `update_from_plan(plan)` — scan pass inputs for `@cam:*`, open/close mmaps
  - `poll_and_upload(queue)` — check timestamps, upload changed frames to GPU textures
  - `view(role)` — return `&TextureView` for binding

- [ ] **Step 2:** Memory-map implementation:
  - Open `/dev/shm/hapax-imagination/cameras/{role}.meta` — read width, height, stride, timestamp
  - Open `/dev/shm/hapax-imagination/cameras/{role}.rgba` — mmap read-only
  - On timestamp change: `queue.write_texture()` from mmap buffer

- [ ] **Step 3:** Export in `lib.rs`: `pub mod camera_textures;`

- [ ] **Step 4:** Commit: `feat(hapax-visual): camera texture pool with mmap + GPU upload`

### Task 3.2: Integrate into DynamicPipeline

**Files:**
- Modify: `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs`

- [ ] **Step 1:** Add `camera_pool: CameraTexturePool` field to DynamicPipeline.

- [ ] **Step 2:** In `try_reload()`, call `camera_pool.update_from_plan(&new_plan)`.

- [ ] **Step 3:** In render loop, call `camera_pool.poll_and_upload(queue)` before pass execution.

- [ ] **Step 4:** In `create_input_bind_group()`, extend resolution:
  ```rust
  } else if let Some(role) = name.strip_prefix("@cam:") {
      self.camera_pool.view(role)
          .unwrap_or(&self.fallback_view)
  }
  ```

- [ ] **Step 5:** Build and test: `cargo build -p hapax-visual`

- [ ] **Step 6:** Commit: `feat(dynamic-pipeline): resolve @cam:* inputs from camera texture pool`

### Task 3.3: End-to-end test

- [ ] **Step 1:** Start hapax-imagination + studio-compositor
- [ ] **Step 2:** Activate `dual-cam-split` preset via API
- [ ] **Step 3:** Verify frame.jpg shows split-screen with independent effects
- [ ] **Step 4:** Switch to `clean` preset — verify camera feed SHM writes stop
- [ ] **Step 5:** Verify VRAM usage stays within budget (~48 MB for 6 cameras)

---

## Acceptance Gates

| Gate | Condition |
|------|-----------|
| Phase 1 | All Python tests pass. Sample preset compiles. |
| Phase 2 | Camera RGBA frames appear in SHM when preset active. Stop when inactive. |
| Phase 3 | End-to-end: split-screen preset renders with independent per-camera effects. |
