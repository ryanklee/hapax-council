# Sierpinski Triangle Visual Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the spirograph reactor with a Sierpinski triangle visual layout — 3 YouTube videos in corner triangle regions, waveform in center, synthwave line work overlay — rendered in the wgpu shader pipeline.

**Architecture:** Two new WGSL shader nodes (`sierpinski_content` for triangle-masked video compositing, `sierpinski_lines` for line work overlay) replace the `content_layer` node in the vocabulary graph. A Python `SierpinskiLoader` replaces `SpirographReactor`, writing YouTube frame JPEGs to the content slot manifest that the Rust `ContentTextureManager` already polls. The existing content injection pipeline (`/dev/shm/hapax-imagination/content/active/slots.json`) is reused with no Rust changes.

**Tech Stack:** WGSL shaders (wgpu), Python 3.12, JSON manifests, turbojpeg (Rust side, unchanged)

**Spec:** `docs/superpowers/specs/2026-04-11-sierpinski-visual-layout-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `agents/shaders/nodes/sierpinski_content.wgsl` | Create | Triangle-region UV masking for 3 video slots + waveform |
| `agents/shaders/nodes/sierpinski_content.json` | Create | Node type definition |
| `agents/shaders/nodes/sierpinski_lines.wgsl` | Create | Triangle line work overlay (synthwave palette) |
| `agents/shaders/nodes/sierpinski_lines.json` | Create | Node type definition |
| `presets/reverie_vocabulary.json` | Edit | Replace `content_layer` with `sierpinski_content` → `sierpinski_lines` |
| `agents/studio_compositor/sierpinski_loader.py` | Create | YouTube frame loader, writes content slot manifest |
| `agents/studio_compositor/fx_chain.py` | Edit | Replace SpirographReactor init with SierpinskiLoader |
| `agents/studio_compositor/fx_chain.py` | Edit | Replace spirograph draw/tick with SierpinskiLoader tick |
| `agents/studio_compositor/spirograph_reactor.py` | Delete | Replaced |

---

### Task 1: Sierpinski Content Shader

Creates the triangle-masked video compositing shader that replaces `content_layer`.

**Files:**
- Create: `agents/shaders/nodes/sierpinski_content.wgsl`
- Create: `agents/shaders/nodes/sierpinski_content.json`

- [ ] **Step 1: Create the node type definition**

Create `agents/shaders/nodes/sierpinski_content.json`:

```json
{"node_type":"sierpinski_content","glsl_fragment":"sierpinski_content.frag","inputs":{"in":"frame","content_slot_0":"frame","content_slot_1":"frame","content_slot_2":"frame","content_slot_3":"frame"},"outputs":{"out":"frame"},"params":{"salience":{"type":"float","default":0.0,"min":0.0,"max":1.0},"intensity":{"type":"float","default":0.0,"min":0.0,"max":1.0},"time":{"type":"float","default":0.0},"tri_scale":{"type":"float","default":0.85,"min":0.3,"max":1.0},"tri_y_offset":{"type":"float","default":0.05,"min":-0.5,"max":0.5}},"temporal":false,"temporal_buffers":0}
```

Fields: same 4 content slot inputs as `content_layer`. Params add `tri_scale` (triangle size relative to viewport) and `tri_y_offset` (vertical centering offset). `salience` and `intensity` retained for active-slot modulation.

- [ ] **Step 2: Create the WGSL shader**

Create `agents/shaders/nodes/sierpinski_content.wgsl`:

```wgsl
// Sierpinski content — triangle-masked video compositing.
// 3 YouTube videos in corner triangle regions, waveform data in center.
// Replaces content_layer for the Sierpinski visual layout.

struct Params {
    u_salience: f32,
    u_intensity: f32,
    u_time: f32,
    u_tri_scale: f32,
    u_tri_y_offset: f32,
}

struct FragmentOutput {
    @location(0) fragColor: vec4<f32>,
}

var<private> fragColor: vec4<f32>;
var<private> v_texcoord_1: vec2<f32>;

@group(1) @binding(0) var tex: texture_2d<f32>;
@group(1) @binding(1) var tex_sampler: sampler;
@group(1) @binding(2) var content_slot_0: texture_2d<f32>;
@group(1) @binding(3) var content_slot_1: texture_2d<f32>;
@group(1) @binding(4) var content_slot_2: texture_2d<f32>;
@group(1) @binding(5) var content_slot_3: texture_2d<f32>;

@group(2) @binding(0) var<uniform> global: Params;

// --- Sierpinski geometry ---

// Signed area of triangle (positive if CCW)
fn cross2d(a: vec2<f32>, b: vec2<f32>) -> f32 {
    return a.x * b.y - a.y * b.x;
}

// Point-in-triangle test using barycentric coordinates
fn point_in_triangle(p: vec2<f32>, a: vec2<f32>, b: vec2<f32>, c: vec2<f32>) -> bool {
    let v0 = c - a;
    let v1 = b - a;
    let v2 = p - a;
    let d00 = dot(v0, v0);
    let d01 = dot(v0, v1);
    let d02 = dot(v0, v2);
    let d11 = dot(v1, v1);
    let d12 = dot(v1, v2);
    let inv = 1.0 / (d00 * d11 - d01 * d01);
    let u = (d11 * d02 - d01 * d12) * inv;
    let v = (d00 * d12 - d01 * d02) * inv;
    return u >= 0.0 && v >= 0.0 && (u + v) <= 1.0;
}

// Map UV to triangle-local coordinates for texture sampling
fn triangle_uv(p: vec2<f32>, a: vec2<f32>, b: vec2<f32>, c: vec2<f32>) -> vec2<f32> {
    // Map point to unit square within triangle bounding box
    let min_xy = min(min(a, b), c);
    let max_xy = max(max(a, b), c);
    let size = max_xy - min_xy;
    return (p - min_xy) / size;
}

// Main equilateral triangle vertices (aspect-ratio corrected)
fn get_main_triangle(scale: f32, y_offset: f32) -> array<vec2<f32>, 3> {
    let aspect = 16.0 / 9.0;
    let h = scale * 0.866; // sqrt(3)/2
    let cx = 0.5;
    let cy = 0.5 + y_offset;
    // Equilateral triangle: top, bottom-left, bottom-right
    return array<vec2<f32>, 3>(
        vec2<f32>(cx, cy - h * 0.667),                         // top
        vec2<f32>(cx - scale * 0.5 / aspect, cy + h * 0.333),  // bottom-left
        vec2<f32>(cx + scale * 0.5 / aspect, cy + h * 0.333),  // bottom-right
    );
}

// Get the 3 corner sub-triangles and center void at subdivision level 1
fn get_corner_triangles(tri: array<vec2<f32>, 3>) -> array<array<vec2<f32>, 3>, 3> {
    let m01 = (tri[0] + tri[1]) * 0.5;
    let m12 = (tri[1] + tri[2]) * 0.5;
    let m02 = (tri[0] + tri[2]) * 0.5;
    return array<array<vec2<f32>, 3>, 3>(
        array<vec2<f32>, 3>(tri[0], m01, m02),   // top corner
        array<vec2<f32>, 3>(m01, tri[1], m12),   // bottom-left corner
        array<vec2<f32>, 3>(m02, m12, tri[2]),   // bottom-right corner
    );
}

// Determine which region a point falls in: 0-2 = corner slots, 3 = center, -1 = outside
fn classify_point(p: vec2<f32>, tri: array<vec2<f32>, 3>) -> i32 {
    if !point_in_triangle(p, tri[0], tri[1], tri[2]) {
        return -1;
    }
    let corners = get_corner_triangles(tri);
    if point_in_triangle(p, corners[0][0], corners[0][1], corners[0][2]) { return 0; }
    if point_in_triangle(p, corners[1][0], corners[1][1], corners[1][2]) { return 1; }
    if point_in_triangle(p, corners[2][0], corners[2][1], corners[2][2]) { return 2; }
    return 3; // center void
}

// --- Waveform rendering ---

fn waveform_bar(uv: vec2<f32>, bar_index: f32, bar_count: f32, amplitude: f32) -> f32 {
    let bar_width = 1.0 / bar_count;
    let bar_x = bar_index * bar_width;
    let in_bar = step(bar_x, uv.x) * step(uv.x, bar_x + bar_width * 0.7);
    let bar_height = amplitude * 0.8;
    let in_height = step(0.5 - bar_height * 0.5, uv.y) * step(uv.y, 0.5 + bar_height * 0.5);
    return in_bar * in_height;
}

// --- Main ---

fn main_1() {
    let uv = v_texcoord_1;
    let time = global.u_time;
    let scale = global.u_tri_scale;
    let y_off = global.u_tri_y_offset;

    let base = textureSample(tex, tex_sampler, uv).rgb;
    let tri = get_main_triangle(scale, y_off);
    let region = classify_point(uv, tri);

    var result = base;

    if region == 0 {
        // Top corner — slot 0
        let corners = get_corner_triangles(tri);
        let slot_uv = triangle_uv(uv, corners[0][0], corners[0][1], corners[0][2]);
        let content = textureSample(content_slot_0, tex_sampler, slot_uv);
        let lum = dot(content.rgb, vec3(0.299, 0.587, 0.114));
        let presence = smoothstep(0.02, 0.08, lum);
        let opacity = uniforms.slot_opacities[0] * presence;
        result = mix(base, content.rgb, opacity);
    } else if region == 1 {
        // Bottom-left — slot 1
        let corners = get_corner_triangles(tri);
        let slot_uv = triangle_uv(uv, corners[1][0], corners[1][1], corners[1][2]);
        let content = textureSample(content_slot_1, tex_sampler, slot_uv);
        let lum = dot(content.rgb, vec3(0.299, 0.587, 0.114));
        let presence = smoothstep(0.02, 0.08, lum);
        let opacity = uniforms.slot_opacities[1] * presence;
        result = mix(base, content.rgb, opacity);
    } else if region == 2 {
        // Bottom-right — slot 2
        let corners = get_corner_triangles(tri);
        let slot_uv = triangle_uv(uv, corners[2][0], corners[2][1], corners[2][2]);
        let content = textureSample(content_slot_2, tex_sampler, slot_uv);
        let lum = dot(content.rgb, vec3(0.299, 0.587, 0.114));
        let presence = smoothstep(0.02, 0.08, lum);
        let opacity = uniforms.slot_opacities[2] * presence;
        result = mix(base, content.rgb, opacity);
    } else if region == 3 {
        // Center void — waveform from slot 3 or procedural
        // Use mel band data from uniforms.custom if available
        let center_tri = get_corner_triangles(tri);
        let m01 = (tri[0] + tri[1]) * 0.5;
        let m12 = (tri[1] + tri[2]) * 0.5;
        let m02 = (tri[0] + tri[2]) * 0.5;
        let wf_uv = triangle_uv(uv, m01, m12, m02);

        // Simple 8-bar waveform using custom uniforms (mel bands)
        var wf = 0.0;
        for (var i = 0u; i < 8u; i++) {
            let amp = uniforms.custom[i / 4u][i % 4u] * 0.5 + 0.1;
            wf = max(wf, waveform_bar(wf_uv, f32(i), 8.0, amp));
        }
        // Synthwave cyan glow
        let wf_color = vec3<f32>(0.0, 0.9, 1.0) * wf * 1.5;
        result = result + wf_color;
    }

    fragColor = vec4<f32>(result, 1.0);
    return;
}

@fragment
fn main(@location(0) v_texcoord: vec2<f32>) -> FragmentOutput {
    v_texcoord_1 = v_texcoord;
    main_1();
    let _e11 = fragColor;
    return FragmentOutput(_e11);
}
```

- [ ] **Step 3: Validate the shader compiles**

Run: `cd ~/projects/hapax-council && naga agents/shaders/nodes/sierpinski_content.wgsl 2>&1`
Expected: No errors (naga validates WGSL syntax)

If naga is not installed: `cargo install naga-cli` or skip — the wgsl_compiler validates at plan compilation time.

- [ ] **Step 4: Commit**

```bash
git add agents/shaders/nodes/sierpinski_content.wgsl agents/shaders/nodes/sierpinski_content.json
git commit -m "feat(shaders): add sierpinski_content node — triangle-masked video compositing"
```

---

### Task 2: Sierpinski Lines Shader

Creates the triangle line work overlay with synthwave palette.

**Files:**
- Create: `agents/shaders/nodes/sierpinski_lines.wgsl`
- Create: `agents/shaders/nodes/sierpinski_lines.json`

- [ ] **Step 1: Create the node type definition**

Create `agents/shaders/nodes/sierpinski_lines.json`:

```json
{"node_type":"sierpinski_lines","glsl_fragment":"sierpinski_lines.frag","inputs":{"in":"frame"},"outputs":{"out":"frame"},"params":{"opacity":{"type":"float","default":0.5,"min":0.0,"max":1.0},"line_width":{"type":"float","default":2.0,"min":0.5,"max":8.0},"glow_radius":{"type":"float","default":4.0,"min":0.0,"max":20.0},"time":{"type":"float","default":0.0},"intensity":{"type":"float","default":0.5,"min":0.0,"max":1.0},"spectral_color":{"type":"float","default":0.5,"min":0.0,"max":1.0},"tri_scale":{"type":"float","default":0.85,"min":0.3,"max":1.0},"tri_y_offset":{"type":"float","default":0.05,"min":-0.5,"max":0.5}},"temporal":false,"temporal_buffers":0}
```

- [ ] **Step 2: Create the WGSL shader**

Create `agents/shaders/nodes/sierpinski_lines.wgsl`:

```wgsl
// Sierpinski lines — fractal triangle line work overlay.
// 2-3 levels of subdivision, synthwave color palette (neon pink/cyan/purple).
// Audio-reactive line width and glow via intensity param.

struct Params {
    u_opacity: f32,
    u_line_width: f32,
    u_glow_radius: f32,
    u_time: f32,
    u_intensity: f32,
    u_spectral_color: f32,
    u_tri_scale: f32,
    u_tri_y_offset: f32,
}

struct FragmentOutput {
    @location(0) fragColor: vec4<f32>,
}

var<private> fragColor: vec4<f32>;
var<private> v_texcoord_1: vec2<f32>;

@group(1) @binding(0) var tex: texture_2d<f32>;
@group(1) @binding(1) var tex_sampler: sampler;

@group(2) @binding(0) var<uniform> global: Params;

// --- Synthwave palette ---

fn synthwave_color(t: f32, time: f32) -> vec3<f32> {
    // Cycle through neon pink → cyan → purple
    let phase = t + time * 0.1;
    let r = 0.5 + 0.5 * sin(phase * 6.283 + 0.0);
    let g = 0.5 + 0.5 * sin(phase * 6.283 + 2.094);
    let b = 0.5 + 0.5 * sin(phase * 6.283 + 4.189);
    // Boost into neon range
    return vec3<f32>(
        mix(0.8, 1.0, r),
        mix(0.0, 1.0, g),
        mix(0.6, 1.0, b),
    );
}

// --- Distance to line segment ---

fn dist_to_segment(p: vec2<f32>, a: vec2<f32>, b: vec2<f32>) -> f32 {
    let pa = p - a;
    let ba = b - a;
    let t = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * t);
}

// --- Distance to triangle edges ---

fn dist_to_triangle(p: vec2<f32>, a: vec2<f32>, b: vec2<f32>, c: vec2<f32>) -> f32 {
    let d0 = dist_to_segment(p, a, b);
    let d1 = dist_to_segment(p, b, c);
    let d2 = dist_to_segment(p, c, a);
    return min(min(d0, d1), d2);
}

// --- Sierpinski geometry (shared with sierpinski_content) ---

fn get_main_triangle(scale: f32, y_offset: f32) -> array<vec2<f32>, 3> {
    let aspect = 16.0 / 9.0;
    let h = scale * 0.866;
    let cx = 0.5;
    let cy = 0.5 + y_offset;
    return array<vec2<f32>, 3>(
        vec2<f32>(cx, cy - h * 0.667),
        vec2<f32>(cx - scale * 0.5 / aspect, cy + h * 0.333),
        vec2<f32>(cx + scale * 0.5 / aspect, cy + h * 0.333),
    );
}

fn subdivide(tri: array<vec2<f32>, 3>) -> array<array<vec2<f32>, 3>, 4> {
    let m01 = (tri[0] + tri[1]) * 0.5;
    let m12 = (tri[1] + tri[2]) * 0.5;
    let m02 = (tri[0] + tri[2]) * 0.5;
    return array<array<vec2<f32>, 3>, 4>(
        array<vec2<f32>, 3>(tri[0], m01, m02),
        array<vec2<f32>, 3>(m01, tri[1], m12),
        array<vec2<f32>, 3>(m02, m12, tri[2]),
        array<vec2<f32>, 3>(m01, m12, m02),   // center (inverted)
    );
}

// --- Main ---

fn main_1() {
    let uv = v_texcoord_1;
    let time = global.u_time;
    let base = textureSample(tex, tex_sampler, uv).rgb;

    // Pixel size for resolution-independent line width
    let pixel = 1.0 / 1080.0;
    let line_w = global.u_line_width * pixel * (1.0 + global.u_intensity * 0.5);
    let glow_r = global.u_glow_radius * pixel * (1.0 + global.u_intensity * 0.3);

    let tri = get_main_triangle(global.u_tri_scale, global.u_tri_y_offset);

    // Level 0: outer triangle
    var min_dist = dist_to_triangle(uv, tri[0], tri[1], tri[2]);

    // Level 1: 4 sub-triangles (3 corners + center)
    let sub1 = subdivide(tri);
    for (var i = 0u; i < 4u; i++) {
        let d = dist_to_triangle(uv, sub1[i][0], sub1[i][1], sub1[i][2]);
        min_dist = min(min_dist, d);
    }

    // Level 2: subdivide each level-1 corner (not center)
    for (var i = 0u; i < 3u; i++) {
        let sub2 = subdivide(sub1[i]);
        for (var j = 0u; j < 4u; j++) {
            let d = dist_to_triangle(uv, sub2[j][0], sub2[j][1], sub2[j][2]);
            min_dist = min(min_dist, d);
        }
    }

    // Line rendering with glow
    let line_alpha = 1.0 - smoothstep(0.0, line_w, min_dist);
    let glow_alpha = (1.0 - smoothstep(line_w, line_w + glow_r, min_dist)) * 0.4;
    let total_alpha = max(line_alpha, glow_alpha) * global.u_opacity;

    // Synthwave color based on distance and spectral_color param
    let color_t = global.u_spectral_color + min_dist * 50.0;
    let line_color = synthwave_color(color_t, time);

    // Additive blend over base
    let result = base + line_color * total_alpha;

    fragColor = vec4<f32>(result, 1.0);
    return;
}

@fragment
fn main(@location(0) v_texcoord: vec2<f32>) -> FragmentOutput {
    v_texcoord_1 = v_texcoord;
    main_1();
    let _e11 = fragColor;
    return FragmentOutput(_e11);
}
```

- [ ] **Step 3: Validate the shader compiles**

Run: `cd ~/projects/hapax-council && naga agents/shaders/nodes/sierpinski_lines.wgsl 2>&1`

- [ ] **Step 4: Commit**

```bash
git add agents/shaders/nodes/sierpinski_lines.wgsl agents/shaders/nodes/sierpinski_lines.json
git commit -m "feat(shaders): add sierpinski_lines node — synthwave fractal line overlay"
```

---

### Task 3: Update Vocabulary Preset

Replace `content_layer` with `sierpinski_content → sierpinski_lines` in the vocabulary graph.

**Files:**
- Modify: `presets/reverie_vocabulary.json`

- [ ] **Step 1: Update the vocabulary preset**

Edit `presets/reverie_vocabulary.json`. Replace the `"content"` node and add a `"lines"` node. Update edges accordingly.

Replace the full file with:

```json
{
    "name": "Reverie Vocabulary",
    "description": "Permanent visual vocabulary — the shader graph that Reverie always runs. Params driven by imagination fragments. There is no idle state.",
    "transition_ms": 2000,
    "nodes": {
        "noise": {
            "type": "noise_gen",
            "params": {
                "frequency_x": 1.5,
                "frequency_y": 1.0,
                "octaves": 3,
                "amplitude": 0.7,
                "speed": 0.08
            }
        },
        "rd": {
            "type": "reaction_diffusion",
            "params": {
                "feed_rate": 0.055,
                "kill_rate": 0.062,
                "diffusion_a": 1.0,
                "diffusion_b": 0.5,
                "speed": 1.0
            }
        },
        "color": {
            "type": "colorgrade",
            "params": {
                "brightness": 1.0,
                "saturation": 1.0,
                "contrast": 0.8,
                "sepia": 0.0,
                "hue_rotate": 0.0
            }
        },
        "drift": {
            "type": "drift",
            "params": {
                "speed": 0.0,
                "amplitude": 0,
                "frequency": 0.8,
                "coherence": 0.6
            }
        },
        "breath": {
            "type": "breathing",
            "params": {
                "rate": 0.0,
                "amplitude": 0.0
            }
        },
        "fb": {
            "type": "feedback",
            "params": {
                "decay": 0.12,
                "zoom": 1.0,
                "rotate": 0.0,
                "blend_mode": 3.0,
                "hue_shift": 0.0,
                "trace_center_x": 0.5,
                "trace_center_y": 0.5,
                "trace_radius": 0.0,
                "trace_strength": 0.0
            }
        },
        "content": {
            "type": "sierpinski_content",
            "params": {
                "salience": 0.0,
                "intensity": 0.0,
                "time": 0.0,
                "tri_scale": 0.85,
                "tri_y_offset": 0.05
            }
        },
        "lines": {
            "type": "sierpinski_lines",
            "params": {
                "opacity": 0.5,
                "line_width": 2.0,
                "glow_radius": 4.0,
                "time": 0.0,
                "intensity": 0.5,
                "spectral_color": 0.5,
                "tri_scale": 0.85,
                "tri_y_offset": 0.05
            }
        },
        "post": {
            "type": "postprocess",
            "params": {
                "vignette_strength": 0.4,
                "sediment_strength": 0.05,
                "master_opacity": 1.0
            }
        },
        "out": {
            "type": "output",
            "params": {}
        }
    },
    "edges": [
        ["noise", "rd"],
        ["rd", "color"],
        ["color", "drift"],
        ["drift", "breath"],
        ["breath", "fb"],
        ["fb", "content"],
        ["content", "lines"],
        ["lines", "post"],
        ["post", "out"]
    ],
    "modulations": [],
    "layer_palettes": {}
}
```

Key changes:
- `"content"` node type changed from `content_layer` to `sierpinski_content` with `tri_scale` and `tri_y_offset` params
- New `"lines"` node of type `sierpinski_lines` inserted between `content` and `post`
- Edge list updated: `fb → content → lines → post`

- [ ] **Step 2: Commit**

```bash
git add presets/reverie_vocabulary.json
git commit -m "feat(preset): update vocabulary graph with Sierpinski content + lines nodes"
```

---

### Task 4: Sierpinski Content Loader

Python module that replaces the spirograph reactor's video frame loading responsibility.

**Files:**
- Create: `agents/studio_compositor/sierpinski_loader.py`

- [ ] **Step 1: Create the content loader**

Create `agents/studio_compositor/sierpinski_loader.py`:

```python
"""Sierpinski content loader — writes YouTube video frames to the wgpu content slot manifest.

Replaces SpirographReactor. Polls yt-frame-{0,1,2}.jpg snapshots from the youtube-player
daemon and writes them to the content slot manifest that the Rust ContentTextureManager
polls every 500ms.

The Sierpinski triangle shader (sierpinski_content.wgsl) handles the triangle-region
masking and compositing on the GPU side. This loader is the data pipeline.
"""

from __future__ import annotations

import json
import logging
import shutil
import threading
import time
from pathlib import Path

log = logging.getLogger(__name__)

CONTENT_DIR = Path("/dev/shm/hapax-imagination/content")
ACTIVE_DIR = CONTENT_DIR / "active"
YT_FRAME_DIR = Path("/dev/shm/hapax-compositor")
MANIFEST_PATH = ACTIVE_DIR / "slots.json"


class SierpinskiLoader:
    """Loads YouTube video frames into the wgpu content slot pipeline."""

    def __init__(self) -> None:
        self._running = False
        self._thread: threading.Thread | None = None
        self._active_slot = 0

    def start(self) -> None:
        """Start the frame polling thread."""
        self._running = True
        ACTIVE_DIR.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="sierpinski-loader"
        )
        self._thread.start()
        log.info("SierpinskiLoader started")

    def stop(self) -> None:
        self._running = False

    def set_active_slot(self, slot_id: int) -> None:
        """Called by director loop when active slot changes."""
        self._active_slot = slot_id

    def _poll_loop(self) -> None:
        """Poll YouTube frame snapshots and write content slot manifest."""
        while self._running:
            try:
                self._update_manifest()
            except Exception:
                log.debug("Manifest update failed", exc_info=True)
            time.sleep(0.4)  # Slightly faster than Rust's 500ms poll

    def _update_manifest(self) -> None:
        """Write slots.json manifest pointing at current YouTube frame JPEGs."""
        slots = []
        for slot_id in range(3):
            frame_path = YT_FRAME_DIR / f"yt-frame-{slot_id}.jpg"
            if not frame_path.exists():
                continue
            # Active slot gets full salience, others reduced
            salience = 0.9 if slot_id == self._active_slot else 0.3
            # Copy frame to content active dir for Rust to load
            dest = ACTIVE_DIR / f"slot_{slot_id}.jpg"
            try:
                shutil.copy2(str(frame_path), str(dest))
            except OSError:
                continue
            slots.append({
                "index": slot_id,
                "path": str(dest),
                "kind": "camera_frame",
                "salience": salience,
            })

        manifest = {
            "fragment_id": "sierpinski-yt",
            "slots": slots,
            "continuation": True,
            "material": "void",
        }
        tmp = MANIFEST_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(manifest))
        tmp.rename(MANIFEST_PATH)
```

- [ ] **Step 2: Lint**

Run: `cd ~/projects/hapax-council && uv run ruff check agents/studio_compositor/sierpinski_loader.py && uv run ruff format agents/studio_compositor/sierpinski_loader.py`

- [ ] **Step 3: Commit**

```bash
git add agents/studio_compositor/sierpinski_loader.py
git commit -m "feat(compositor): add SierpinskiLoader — YouTube frame content pipeline"
```

---

### Task 5: Wire Up and Remove Spirograph

Replace SpirographReactor with SierpinskiLoader in fx_chain.py. Remove spirograph draw/tick calls.

**Files:**
- Modify: `agents/studio_compositor/fx_chain.py:780-789` (init)
- Modify: `agents/studio_compositor/fx_chain.py:544-548` (draw)
- Modify: `agents/studio_compositor/fx_chain.py:1028-1031` (tick)
- Delete: `agents/studio_compositor/spirograph_reactor.py`

- [ ] **Step 1: Replace SpirographReactor init in fx_chain.py**

In `agents/studio_compositor/fx_chain.py`, find the spirograph init block (around line 780-789):

```python
    try:
        from .spirograph_reactor import SpirographReactor

        compositor._spirograph_reactor = SpirographReactor()
        compositor._yt_overlay = None
        log.info("SpirographReactor created")
    except Exception:
        log.exception("SpirographReactor failed, falling back to YouTubeOverlay")
        compositor._spirograph_reactor = None
        compositor._yt_overlay = YouTubeOverlay()
```

Replace with:

```python
    from .sierpinski_loader import SierpinskiLoader

    compositor._sierpinski_loader = SierpinskiLoader()
    compositor._sierpinski_loader.start()
    compositor._spirograph_reactor = None  # removed — Sierpinski replaces it
    compositor._yt_overlay = None
    log.info("SierpinskiLoader created")
```

- [ ] **Step 2: Remove spirograph draw from _pip_draw**

In `_pip_draw` (around line 544-548), remove the spirograph draw call:

```python
    spiro = getattr(compositor, "_spirograph_reactor", None)
    if spiro is not None:
        spiro.draw(cr)
```

Replace with nothing (just delete these 3 lines). The Sierpinski rendering happens in the GPU shader pipeline, not in Cairo.

- [ ] **Step 3: Replace spirograph tick in fx_tick_callback**

In `fx_tick_callback` (around line 1028-1031), remove:

```python
    # Spirograph reactor
    spiro = getattr(compositor, "_spirograph_reactor", None)
    if spiro:
        spiro.tick()
```

No replacement needed — the SierpinskiLoader runs its own polling thread. It doesn't need a per-frame tick.

- [ ] **Step 4: Delete spirograph_reactor.py**

```bash
git rm agents/studio_compositor/spirograph_reactor.py
```

- [ ] **Step 5: Search for remaining spirograph references**

Run: `cd ~/projects/hapax-council && grep -rn "spirograph\|SpirographReactor" agents/studio_compositor/ --include="*.py" | grep -v __pycache__`

Remove or update any remaining references. Common locations:
- Imports in `__init__.py`
- References in `director_loop.py` (the `_reactor` field may reference spirograph methods like `set_text`, `set_speaking`, `feed_pcm`, `set_header`)

Check which spirograph methods the director loop calls:

Run: `cd ~/projects/hapax-council && grep -n "_reactor\." agents/studio_compositor/director_loop.py | head -20`

The director loop calls `self._reactor.set_text()`, `set_speaking()`, `feed_pcm()`, `set_header()`. These are overlay display methods, not video frame methods. They may need to remain as a text overlay or be removed if the Sierpinski layout doesn't show reaction text.

If the director loop's `_reactor` is the spirograph's overlay component, it needs a replacement. Create a minimal stub or keep the overlay part separate. **Check what `reactor_overlay` is in the DirectorLoop constructor** — if it's the SpirographReactor, the director loop needs adaptation.

- [ ] **Step 6: Lint all changed files**

Run: `cd ~/projects/hapax-council && uv run ruff check agents/studio_compositor/fx_chain.py && uv run ruff format agents/studio_compositor/fx_chain.py`

- [ ] **Step 7: Commit**

```bash
git add agents/studio_compositor/fx_chain.py agents/studio_compositor/sierpinski_loader.py
git rm agents/studio_compositor/spirograph_reactor.py
git add -u
git commit -m "feat(compositor): replace SpirographReactor with SierpinskiLoader + Sierpinski shaders"
```

---

### Task 6: Integration Verification

**Files:** None (verification only)

- [ ] **Step 1: Recompile the shader pipeline**

Run: `cd ~/projects/hapax-council && uv run python -c "
from agents.effect_graph.wgsl_compiler import compile_to_wgsl_plan
from agents.effect_graph.registry import ShaderNodeRegistry
from agents.effect_graph.models import EffectGraph
from pathlib import Path
import json

registry = ShaderNodeRegistry(Path('agents/shaders/nodes'))
print(f'Registered nodes: {list(registry.list_types())}')

preset = json.loads(Path('presets/reverie_vocabulary.json').read_text())
graph = EffectGraph.from_preset(preset, registry)
plan = compile_to_wgsl_plan(graph)
print(f'Compiled {len(plan[\"passes\"])} passes')
for p in plan['passes']:
    print(f'  {p[\"node_id\"]}: {p[\"shader\"]}')
"`

Expected: `sierpinski_content` and `sierpinski_lines` appear in the pass list. No compilation errors.

- [ ] **Step 2: Restart compositor**

```bash
systemctl --user restart studio-compositor.service
journalctl --user -eu studio-compositor --no-pager --since "30s ago" | grep -i "sierpinski\|loader\|error"
```

Expected: "SierpinskiLoader created" in logs, no errors.

- [ ] **Step 3: Verify visual output**

Check that the Reverie visual surface shows:
- Sierpinski triangle line work (synthwave colors)
- YouTube video content in the 3 corner regions
- Waveform visualization in the center triangle
- No spirograph circles/orbiting

- [ ] **Step 4: Verify content manifest updates**

```bash
cat /dev/shm/hapax-imagination/content/active/slots.json | python3 -m json.tool
```

Expected: 3 slots pointing at `slot_0.jpg`, `slot_1.jpg`, `slot_2.jpg` with salience values.

- [ ] **Step 5: Verify director loop still works**

Confirm the director loop cycles between slots, speaks reactions, and the active slot changes in the visual surface (brighter opacity on active video).
