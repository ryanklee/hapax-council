# Multi-Camera Graph Routing — Design Spec

**Date:** 2026-03-31
**Author:** delta session
**Status:** Design approved, pending implementation
**Motivation:** The effect graph currently operates on the post-composite output only. Individual camera feeds cannot be routed through the shader graph independently, preventing per-camera effects, split-screen compositions, and camera-aware visual reactions.
**Depends on:** 2026-03-31-studio-effects-consolidation-design.md (Stage 1)

---

## Problem

1. **Post-composite only.** The GStreamer compositor combines all 6 cameras into a single BGRA frame before the effect graph sees it. The graph can process the composite but cannot process individual cameras differently.
2. **No per-camera effects.** A preset cannot apply thermal to brio-operator while keeping c920-desk clean. All cameras receive the same effect chain.
3. **No camera-aware composition.** The `blend` node exists but has no concept of camera identity. You cannot build a graph that blends brio-operator (with trails) and c920-overhead (with edge detection) because neither feed is available as a named input.
4. **Three-layer limitation.** Only `@live`, `@smooth`, `@hls` are valid layer sources. These are temporal variants of the same composite — not independent camera feeds.

---

## Solution

Extend the layer source system to include per-camera feeds as first-class graph inputs. Each camera role becomes a named source (`@cam:brio-operator`, `@cam:c920-desk`, etc.) that can be wired into any graph node.

### Design Principles

- **D1: Camera feeds are layer sources, not nodes.** Cameras are external inputs like `@live`, not generator nodes like `noise_gen`. This preserves the DAG topology (no new node types needed).
- **D2: Opt-in per preset.** Camera sources only consume resources when referenced by the active graph. A preset that doesn't reference `@cam:brio-operator` incurs zero overhead for that feed.
- **D3: Shared memory delivery.** Camera frames reach the Rust GPU pipeline via `/dev/shm/hapax-imagination/cameras/{role}.rgba` — raw RGBA frames written by GStreamer, memory-mapped by Rust. No socket overhead.
- **D4: Existing composite preserved.** `@live`, `@smooth`, `@hls` continue to work exactly as before. Camera sources are additive.
- **D5: Resolution independence.** Camera sources carry their native resolution (BRIO 1920x1080, C920 1280x720). The GPU pipeline scales to pass target resolution as needed.

---

## Architecture

### Data Flow

```
GStreamer Compositor
  └─ per-camera tee (already exists in cameras.py)
      ├─ compositor pad (existing)
      ├─ recording branch (existing)
      ├─ snapshot branch (existing)
      └─ [NEW] graph-feed branch
           └─ queue → videoconvert (RGBA) → appsink
                └─ callback: write /dev/shm/hapax-imagination/cameras/{role}.rgba
                   + /dev/shm/hapax-imagination/cameras/{role}.meta (JSON: w, h, stride, timestamp)

Rust DynamicPipeline
  └─ CameraTexturePool (new module)
      └─ per-role: mmap /dev/shm file → upload to GPU texture → bind as "@cam:{role}"
```

### Layer Source Naming

| Source | Pattern | Example | Resolution |
|--------|---------|---------|-----------|
| Composite live | `@live` | `@live` | 1920x1080 |
| Composite smooth | `@smooth` | `@smooth` | 1920x1080 |
| Composite HLS | `@hls` | `@hls` | 1920x1080 |
| Individual camera | `@cam:{role}` | `@cam:brio-operator` | Native (1920x1080 or 1280x720) |

### Preset Example

A split-screen preset with independent effects per camera:

```json
{
  "name": "dual-cam-split",
  "nodes": {
    "trails_op": { "type": "trail", "params": { "decay": 0.92 } },
    "edge_desk": { "type": "edge_detect", "params": { "threshold": 0.3 } },
    "split": { "type": "blend", "params": { "mode": "split_h", "position": 0.5 } },
    "post": { "type": "postprocess", "params": {} },
    "content": { "type": "content_layer", "params": {} },
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
  ]
}
```

---

## Core Components

### 1. Python: Extended Layer Sources

**File:** `agents/effect_graph/compiler.py`

```python
VALID_LAYER_SOURCES = {"@live", "@smooth", "@hls"}
CAMERA_SOURCE_PREFIX = "@cam:"

def _is_valid_source(name: str) -> bool:
    if name in VALID_LAYER_SOURCES:
        return True
    if name.startswith(CAMERA_SOURCE_PREFIX):
        role = name[len(CAMERA_SOURCE_PREFIX):]
        return role in KNOWN_CAMERA_ROLES
    return False
```

**`KNOWN_CAMERA_ROLES`** loaded from compositor config or hardcoded:
```python
KNOWN_CAMERA_ROLES = {
    "brio-operator", "brio-room", "brio-synths",
    "c920-desk", "c920-room", "c920-overhead",
}
```

### 2. Python: WGSL Compiler Extension

**File:** `agents/effect_graph/wgsl_compiler.py`

Camera sources in plan.json inputs list exactly as they appear: `"@cam:brio-operator"`. The Rust pipeline resolves them from the camera texture pool.

### 3. GStreamer: Graph-Feed Branch

**File:** `agents/studio_compositor/cameras.py` (new function)

```python
def add_graph_feed_branch(
    pipeline: Gst.Pipeline,
    camera_tee: Gst.Element,
    role: str,
    width: int,
    height: int,
) -> None:
    """Add a branch that writes raw RGBA frames to /dev/shm for the GPU pipeline."""
    output_dir = Path("/dev/shm/hapax-imagination/cameras")
    output_dir.mkdir(parents=True, exist_ok=True)

    # queue → videoconvert (RGBA) → videoscale → appsink
    # appsink callback writes mmap'd RGBA + metadata JSON
```

**Activation:** Only added when the active preset references `@cam:{role}`. The compositor state reader checks `fx-current.txt` against a manifest of required camera sources.

### 4. Rust: CameraTexturePool

**File:** `hapax-logos/crates/hapax-visual/src/camera_textures.rs` (new)

```rust
pub struct CameraTexturePool {
    cameras: HashMap<String, CameraTexture>,
}

struct CameraTexture {
    role: String,
    mmap: Option<memmap2::Mmap>,
    texture: wgpu::Texture,
    view: wgpu::TextureView,
    width: u32,
    height: u32,
    last_timestamp: u64,
}

impl CameraTexturePool {
    /// Check for new frames and upload to GPU if changed
    pub fn poll_and_upload(&mut self, queue: &wgpu::Queue) { ... }

    /// Get texture view for a camera role
    pub fn view(&self, role: &str) -> Option<&wgpu::TextureView> { ... }
}
```

### 5. Rust: DynamicPipeline Input Resolution Extension

**File:** `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs`

Extend `create_input_bind_group()` to resolve `@cam:*` inputs:

```rust
} else if let Some(role) = name.strip_prefix("@cam:") {
    self.camera_pool.view(role)
        .unwrap_or_else(|| self.textures.get("final").unwrap().view())
}
```

---

## File Map

### New files

| File | Purpose |
|------|---------|
| `hapax-logos/crates/hapax-visual/src/camera_textures.rs` | Memory-mapped camera frame reader + GPU texture pool |

### Modified files

| File | Change |
|------|--------|
| `agents/effect_graph/compiler.py` | Extend `VALID_LAYER_SOURCES` validation to accept `@cam:{role}` |
| `agents/effect_graph/wgsl_compiler.py` | Pass camera sources through to plan.json inputs |
| `agents/studio_compositor/cameras.py` | Add `add_graph_feed_branch()` for demand-driven SHM writing |
| `agents/studio_compositor/state.py` | Parse active preset for camera source requirements |
| `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs` | Resolve `@cam:*` inputs from CameraTexturePool |
| `hapax-logos/crates/hapax-visual/src/lib.rs` | Export `camera_textures` module |

### New /dev/shm paths

| Path | Writer | Reader | Format | Cadence |
|------|--------|--------|--------|---------|
| `/dev/shm/hapax-imagination/cameras/{role}.rgba` | GStreamer appsink | Rust CameraTexturePool (mmap) | Raw RGBA | 30fps (when active) |
| `/dev/shm/hapax-imagination/cameras/{role}.meta` | GStreamer appsink | Rust CameraTexturePool | JSON (w, h, stride, ts) | 30fps (when active) |

---

## Acceptance Criteria

1. `@cam:brio-operator` is a valid layer source in graph compilation.
2. A preset referencing `@cam:brio-operator` compiles, generates correct plan.json, and renders in hapax-imagination with the live camera feed.
3. A preset referencing multiple camera sources (e.g., split-screen with two cameras) renders both feeds independently.
4. Presets that do NOT reference any `@cam:*` source incur zero additional overhead (no SHM writes, no GPU uploads).
5. Camera source availability is dynamic: disconnecting a camera causes graceful fallback (procedural fill or last-good frame).
6. All existing presets continue to work unchanged.
7. 56 existing nodes, 30 existing presets, 40 API endpoints remain unaffected.

## Constraints

- **VRAM budget:** Each camera source at 1920x1080 RGBA = ~8 MB GPU memory. 6 cameras = ~48 MB. Within the 380 MiB imagination budget.
- **SHM bandwidth:** 1920x1080x4 bytes x 30fps = ~237 MB/s per camera. PCIe 4.0 can handle this but CPU memcpy overhead matters. Limit active camera sources to 3 concurrent maximum.
- **Latency:** SHM write + mmap read + GPU upload adds ~2-5ms per camera per frame. Acceptable at 30fps (33ms budget).
- **GStreamer thread safety:** `add_graph_feed_branch()` must use `queue` element for thread isolation. Appsink callback must be non-blocking (write to pre-allocated mmap, not allocate).
