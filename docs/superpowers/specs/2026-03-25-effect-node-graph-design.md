# Effect Node Graph — Design Spec

**Date:** 2026-03-25
**Status:** Design approved, pending implementation plan
**Supersedes:** 2026-03-25-effects-system-repair.md, effects-repair-round2.md, effects-repair-round3.md

## Problem

The Logos composite/effects system has failed three successive repair attempts. The root causes are architectural, not parametric:

1. **CompositeCanvas.tsx is a 724-line monolith** — a single `useEffect` owns frame fetching, ring buffers, trail persistence (ping-pong back buffer), warp transforms, stutter state machine, filter crossfade, noise generation, bloom extraction, strobe, circular masking, overlay compositing, and post-effects. Every effect is a hardcoded code path inside `render()`. Touching anything touches everything.

2. **CSS filter strings are the wrong rendering primitive.** Effects like `"saturate(0.4) sepia(0.55) hue-rotate(-10deg)"` are opaque strings that can't be composed, inspected, interpolated, or reasoned about programmatically. Channel-level operations (RGB split, thermal palette mapping) are impossible.

3. **Presets are flat config bags, not composable effect chains.** Each preset specifies every parameter in a monolithic object. No way to say "VHS but with Neon's bloom." The `effectOverrides` system only toggles booleans. The creative vocabulary — blend modes, alpha curves, temporal behavior — is locked inside preset definitions with no recombination.

4. **Effects look the same.** Every effect runs through identical CSS filter + Canvas 2D trail accumulator + post-effects pipeline. There is one rendering voice; presets are just parameters to that voice. VHS, Neon, and Thermal are all variations of "tinted ghost trails with optional scanline overlay."

## Solution

Replace the frontend canvas rendering engine with a **backend GPU node graph**. The compositor (GStreamer + GLSL on RTX 3090) becomes the single source of all visual effects. The frontend becomes a dumb display surface.

### Design Principles

- **Backend renders everything.** All effects execute as GLSL shaders in the GStreamer pipeline. The frontend displays HLS or snapshots — no canvas rendering.
- **Composable node graph.** Effects are nodes with typed ports. Nodes connect into a DAG. Presets are saved graph configurations (JSON files), not code.
- **Automatable.** Every parameter is patchable via API. Modulation bindings connect node params to perceptual signals (audio, emotion, flow, biometrics). Agents drive the graph programmatically.
- **Distinct shaders per effect.** VHS does actual RGB channel displacement. Thermal maps luminance to an IR palette. Datamosh uses optical flow for motion-vector corruption. Each node has a dedicated GLSL shader that does one thing.

## Architecture

### Three Persistent Layers

Three always-running source streams exist outside the effect graph:

| Layer | Source | Latency | Buffer |
|-------|--------|---------|--------|
| **Live** (`@live`) | Camera feed, lowest-latency path | Real-time | None |
| **Smooth** (`@smooth`) | Same camera, 5-second circular FBO buffer | Fixed 5s delay | ~150 frames in GPU memory |
| **HLS** (`@hls`) | NVENC → hlssink2 → hls.js playback | ~4-6s (segment buffering) | HLS segment window |

Each layer has an independent **color palette** (colorgrade shader: saturation, brightness, contrast, sepia, hue_rotate) applied at the source level before the effect graph. Palette changes lerp over configurable duration (default 300ms) via uniform interpolation.

The effect graph references layers via `@live`, `@smooth`, `@hls` prefixes in edge definitions. Any/all three can feed into the graph simultaneously.

### Smooth Layer Implementation

Ring of FBOs in GPU memory. At 30fps, 5 seconds = 150 frames. The compositor writes every frame; the smooth source reads from `write_head - 150`.

Memory estimate at full 1920x1080 RGBA: ~150 × 8.3MB = 1.2GB VRAM. At half resolution (960x540): ~300MB. Resolution is configurable.

### Node Graph Model

#### Port Types

- **frame** — GPU texture (RGBA framebuffer)
- **scalar** — float (normalized 0-1 or unbounded with range metadata)
- **color** — vec4 RGBA

#### Node Categories

**Source nodes** (0 frame inputs, 1+ frame outputs):
- `@live`, `@smooth`, `@hls` — persistent layer references
- `solid` — flat color fill
- `noise_gen` — procedural Perlin/Simplex/Worley/FBM noise texture
- `waveform_render` — audio waveform/FFT/lissajous as visual element
- `sdf_scene` — raymarched geometry (metaballs, fractals, terrain)

**Processing nodes** (1 frame in, 1 frame out, stateless):
- `colorgrade` — saturation, brightness, contrast, sepia, hue_rotate
- `vhs` — chroma shift, head-switch noise, tracking jitter
- `thermal` — luminance → IR palette with edge glow
- `halftone` — print dot grid pattern
- `pixsort` — luminance-gated horizontal pixel sorting
- `ascii` — character grid lookup
- `bloom` — bright-pass → downsample → blur → additive composite
- `scanlines` — horizontal line overlay
- `vignette` — radial gradient darkening
- `band_displacement` — random horizontal glitch bands
- `noise_overlay` — grain texture composite
- `circular_mask` — hard circular alpha clip
- `warp` — pan/rotate/zoom/slice/breath
- `strobe` — full-frame flash
- `syrup` — linear gradient overlay
- `invert` — channel inversion
- `edge_detect` — Sobel/Laplacian edge detection
- `chromatic_aberration` — RGB channel spatial displacement
- `displacement_map` — UV warp from arbitrary texture (noise, camera, audio)
- `threshold` — binary luminance cutoff with configurable colors
- `color_map` — luminance → arbitrary color gradient (generalized false color)
- `posterize` — color level quantization
- `fisheye` — barrel/pincushion lens distortion
- `mirror` — bilateral/quad reflection
- `kaleidoscope` — N-segment angular reflection
- `dither` — ordered/noise dithering (Bayer, blue noise)
- `emboss` — directional relief convolution
- `sharpen` — unsharp mask
- `rutt_etra` — scan-line terrain displacement from luminance
- `voronoi_overlay` — Voronoi cell segmentation/stylization
- `tile` — NxM image repeat with optional mirror
- `drift` — slow organic UV displacement (animated noise field)
- `breathing` — rhythmic scale oscillation (syncable to heart rate / BPM)
- `tunnel` — cylindrical tunnel warp with forward motion
- `transform` — scale, rotate, translate with configurable border handling

**Temporal nodes** (1 frame in, 1 frame out, persistent FBO state):
- `trail` — accumulator with fade, blend mode, drift, opacity. Float-precision FBO eliminates 8-bit ghosting.
- `stutter` — freeze/replay state machine with configurable probability and duration
- `feedback` — recursive self-feeding with decay, zoom, rotate, blend mode
- `slitscan` — temporal vertical displacement buffer
- `diff` — motion detection (current vs N frames ago)
- `datamosh` — motion-vector frame corruption using optical flow
- `optical_flow` — per-pixel motion vector computation (NVOFA hardware). Sensing node that feeds datamosh, motion trails, displacement.
- `echo` — fixed-size frame ring with weighted blending (linear, exponential, equal decay)
- `time_displacement` — per-pixel temporal sampling based on luminance displacement map
- `motion_trail` — motion-selective trailing (traces moving elements, keeps static areas clean)
- `reaction_diffusion` — Gray-Scott organic pattern simulation, seedable from camera/audio
- `fluid_sim` — 2D Navier-Stokes, injection from audio energy / camera motion
- `particle_system` — GPU particles spawned from audio peaks / camera motion / points
- `droste` — recursive zoom (Escher spiral), zoom speed syncable to BPM

**Compositing nodes** (2+ frame inputs, 1 frame output):
- `blend` — arbitrary blend mode (lighter, multiply, difference, screen, overlay, soft-light) with alpha
- `crossfade` — timed interpolation between two streams
- `luma_key` — luminance-based transparency
- `chroma_key` — color-based transparency
- `camera_select` — multi-cam switching with transition types (cut, dissolve, wipe), auto-mode (beat, motion, flow)
- `split_screen` — multi-region camera layout (halves, thirds, quad, diagonal)
- `pip` — picture-in-picture inset with position, size, border, corner radius

#### Topology Rules

1. Graph must be a DAG with exactly one `output` sink. No external cycles.
2. Every node's inputs must be connected.
3. Temporal nodes are the only nodes with mutable state between frames. Their internal FBO state (feedback loop, frame ring, simulation state) is not a graph cycle.
4. Multi-input compositing nodes use named ports (`a`, `b`) in edge definitions: `["trail", "blend:a"]`, `["@smooth", "blend:b"]`.

### Shader Registry

Each node type maps to a registered shader:

```python
@dataclass
class ShaderDef:
    node_type: str
    glsl_fragment: str                    # path to .frag file
    inputs: dict[str, PortType]           # named input ports
    outputs: dict[str, PortType]          # named output ports
    params: dict[str, ParamDef]           # uniforms with type, range, default
    temporal: bool = False                # owns persistent FBO state
    temporal_buffers: int = 0             # FBOs to allocate
    compute: bool = False                 # uses compute shader (fluid_sim, particles)

@dataclass
class ParamDef:
    type: Literal["float", "int", "vec2", "vec3", "vec4", "bool"]
    default: Any
    min: float | None = None
    max: float | None = None
    description: str = ""
```

Shaders live in `shaders/nodes/`, one `.frag` (or `.comp`) per node type, with a companion `.json` manifest declaring ports, params, and metadata. Adding a new effect means adding shader + manifest — no Python changes.

### Graph Runtime Engine

#### Three Mutation Levels

**1. Parameter patch** (zero-cost, no pipeline rebuild):
```
PATCH /api/studio/effect/graph/node/{id}/params
{ "opacity": 0.3, "fade": 0.02 }
```
Updates shader uniforms on the next frame tick. Numeric params lerp over `transition_ms` (default 200ms). This is the primary automation interface.

**2. Topology mutation** (lightweight rebuild):
```
PATCH /api/studio/effect/graph
{ "add_nodes": {...}, "remove_nodes": [...], "add_edges": [...], "remove_edges": [...] }
```
Graph compiler diffs current vs new topology. Unchanged subchains keep their GStreamer elements and FBO state. Temporal nodes preserve history across mutations. Crossfade (default 500ms) blends old→new output during transition.

**3. Full graph replace** (preset switch):
```
PUT /api/studio/effect/graph
{ "nodes": {...}, "edges": [...] }
```
Dual-pipeline crossfade: old graph → FBO A, new graph → FBO B, output shader `mix(A, B, t)` over transition duration. Old pipeline torn down after crossfade completes.

#### Graph Compiler

1. **Topological sort** — resolve execution order from edges
2. **FBO allocation** — nodes feeding multiple consumers get dedicated FBOs; linear chains share via ping-pong
3. **Shader binding** — each node type maps to `glshader` element with fragment shader + uniform bindings
4. **Temporal state** — temporal node FBOs allocated outside graph lifecycle, survive mutations
5. **Validation** — reject cycles, disconnected nodes, type mismatches

#### Crossfade Engine

All transitions use the same mechanism at the output stage:
- **Param changes**: Uniform lerp in shader (no extra machinery)
- **Topology changes**: Dual-pipeline render to FBO A + B, blend shader `mix(A, B, t)`, tear down old after complete
- **Preset switches**: Same as topology change with full replace

### Uniform Modulation System

Replaces hardcoded `_fx_tick_callback` beat-reactive code with a declarative binding system:

```python
class UniformModulator:
    def bind(self, node_id: str, param: str, source: str,
             scale: float = 1.0, offset: float = 0.0,
             smoothing: float = 0.85):
        """Bind a node param to a perceptual signal source."""
```

Available sources:
- `audio_rms` — overall audio energy
- `audio_beat` — beat onset detection (0→1 spike on transient)
- `audio_bass`, `audio_mid`, `audio_high` — frequency band energy
- `stimmung_valence` — emotional valence (-1 to 1)
- `stimmung_arousal` — emotional arousal (0 to 1)
- `flow_score` — flow state depth (0 to 1)
- `heart_rate` — BPM from watch biometrics
- `time_of_day` — normalized 0-1
- `optical_flow_magnitude` — average motion energy from optical flow node

Each tick (30fps GLib timeout), the modulator reads signals, applies `value * scale + offset` with exponential smoothing, and patches bound uniforms. Agents configure bindings via API.

## API Surface

### Graph Management

```
PUT    /api/studio/effect/graph                          — Full graph replace
PATCH  /api/studio/effect/graph                          — Topology mutation
GET    /api/studio/effect/graph                          — Current graph state
PATCH  /api/studio/effect/graph/node/{id}/params         — Parameter patch
DELETE /api/studio/effect/graph/node/{id}                — Remove node + edges
```

### Layer Control

```
PATCH  /api/studio/layer/{live|smooth|hls}/palette       — Per-layer color grade
GET    /api/studio/layer/status                          — Layer status (fps, resolution, palette)
PATCH  /api/studio/layer/{live|smooth|hls}/enabled       — Enable/disable layer
PATCH  /api/studio/layer/smooth/delay                    — Temporal offset (default 5s)
```

### Modulation

```
PUT    /api/studio/effect/graph/modulations              — Replace all bindings
PATCH  /api/studio/effect/graph/modulations              — Add/remove bindings
GET    /api/studio/effect/graph/modulations              — Current bindings
```

### Presets

```
GET    /api/studio/presets                               — List presets
GET    /api/studio/presets/{name}                        — Full graph JSON
PUT    /api/studio/presets/{name}                        — Save graph as preset
DELETE /api/studio/presets/{name}                        — Delete preset
POST   /api/studio/presets/{name}/activate               — Load preset (crossfade)
```

Presets stored as JSON in `~/.config/hapax/effect-presets/`. The 20 legacy presets + 8 new presets ship as defaults.

### Node Registry

```
GET    /api/studio/effect/nodes                          — All node types with schemas
GET    /api/studio/effect/nodes/{type}                   — Single node type schema
```

### Camera Control

```
GET    /api/studio/cameras                               — Available cameras
POST   /api/studio/camera/select                         — Set hero camera
```

## Frontend Changes

### Deleted (moves to backend)

- `CompositeCanvas.tsx` — entire 724-line canvas rendering engine
- `compositePresets.ts` — replaced by JSON preset files
- `compositeFilters.ts` — replaced by per-layer palette API
- `useSnapshotPoll.ts` ring buffer logic — simplified to single-image poll
- `useImagePool.ts` — no longer needed

### Retained (simplified)

- **HLS.js player** — primary display mode, shows the fully-rendered backend output
- **Snapshot `<img>`** — fallback when HLS unavailable, single JPEG poll at ~10fps
- **Preset selector UI** — grid of chips, calls `POST /presets/{name}/activate`
- **Per-layer palette dropdowns** — calls `PATCH /layer/{id}/palette`
- **Effect toggle grid** — sends topology mutations (`PATCH /graph`) to insert/remove nodes
- **Keyboard shortcuts** — same ergonomics, different API calls

### New frontend components

- **`GraphInspector`** (dev/debug) — read-only visualization of current node graph topology. Collapsible panel.
- **`NodeParamSlider`** — auto-generated sliders from node registry schema. Sends `PATCH /graph/node/{id}/params`.

## FPS Strategy

- **Live layer**: Camera native fps (30fps from v4l2src; use higher if cameras support it)
- **Smooth layer**: Same fps as live, 5-second delay
- **Effect graph render loop**: Ticks at fastest source fps. Temporal nodes operate in frame-time, not wall-clock.
- **HLS output**: Configurable independently (30fps default, 60fps possible with NVENC)
- **Snapshot output**: Decoupled — samples graph output at requested rate
- **v4l2loopback**: Matches render fps

GStreamer queues with leaky buffers prevent backpressure from slow outputs affecting render rate.

## Preset Migration

All 20 current presets + 8 new presets as JSON graph files:

### Legacy presets (reimplemented with dedicated shaders)

| Preset | Node Chain | Key Difference |
|--------|-----------|----------------|
| Ghost | `@live` → `trail(lighter)` → `bloom` → `out` | Float-precision GPU trail, no 8-bit ghosting |
| Trails | `@live` → `trail(lighter, high_count)` → `bloom` → `noise_overlay` → `out` | Proper float accumulator |
| Screwed | `@live` → `warp(slice)` → `stutter` → `trail` → `syrup` → `scanlines` → `out` | Real GPU slice warp |
| Datamosh | `@live` → `optical_flow` → `datamosh` → `stutter` → `band_displacement` → `out` | Real motion-vector corruption |
| VHS | `@live` → `vhs` → `trail(lighter)` → `scanlines` → `noise_overlay` → `vignette` → `out` | Actual RGB channel displacement |
| Neon | `@live` → `feedback(hue_rotate)` → `bloom(high)` → `chromatic_aberration` → `out` | True recursive feedback |
| Trap | `@live` → `colorgrade(dark)` → `trail(multiply)` → `syrup` → `noise_overlay(heavy)` → `vignette` → `out` | Float-precision multiply blend |
| Diff | `@live` → `diff` → `threshold` → `colorgrade(high_contrast)` → `out` | Real frame differencing |
| NightVision | `@live` → `colorgrade(green)` → `bloom` → `scanlines` → `noise_overlay(animated)` → `circular_mask` → `out` | Proper shader execution |
| Silhouette | `@live` → `threshold` → `invert` → `edge_detect` → `out` | Clean binary silhouette |
| Thermal | `@live` → `color_map(ir_palette)` → `edge_detect` → `bloom` → `out` | Proper luminance→palette |
| Pixsort | `@live` → `pixsort` → `scanlines` → `out` | Real horizontal pixel reorder (compute shader) |
| Slit-scan | `@live` → `slitscan` → `colorgrade` → `out` | True temporal column buffer |
| Feedback | `@live` → `feedback(heavy, hue_rotate)` → `bloom(heavy)` → `chromatic_aberration` → `out` | Deep recursive self-feeding |
| Halftone | `@live` → `halftone` → `colorgrade` → `out` | Proper dot-grid sampling |
| Glitch Blocks | `@live` → `glitch_block` → `chromatic_aberration` → `band_displacement` → `stutter` → `out` | Real block displacement + RGB split |
| ASCII | `@live` → `ascii` → `scanlines` → `out` | Character grid in shader |
| Ambient | `@smooth` → `colorgrade(dim)` → `drift` → `bloom(subtle)` → `out` | Uses smooth layer's 5s delay |
| Clean | `@live` → `colorgrade` → `vignette(light)` → `out` | Minimal processing |

### New presets (previously impossible)

| Preset | Node Chain |
|--------|-----------|
| Datamosh Heavy | `@live` → `optical_flow` → `datamosh(aggressive)` → `chromatic_aberration` → `out` |
| Fluid | `fluid_sim(audio_inject)` → `blend(@live, screen)` → `out` |
| Organism | `reaction_diffusion(camera_seed)` → `blend(@live, overlay)` → `out` |
| Tunnelvision | `@live` → `tunnel(camera_texture)` → `bloom` → `chromatic_aberration` → `out` |
| Droste Loop | `@live` → `droste(bpm_sync)` → `colorgrade` → `out` |
| Sculpture | `@live` → `rutt_etra` → `bloom` → `out` |
| Heartbeat | `@live` → `breathing(heartrate)` → `drift` → `bloom` → `out` |
| Particles | `particle_system(audio_peaks)` → `blend(@live, lighter)` → `out` |

## Example Graph JSON

VHS preset as a complete graph document:

```json
{
  "name": "VHS",
  "description": "Lo-fi tape — soft, warm, tracking noise",
  "transition_ms": 500,
  "nodes": {
    "stut": {
      "type": "stutter",
      "params": {
        "check_interval": 20,
        "freeze_chance": 0.15,
        "freeze_min": 2,
        "freeze_max": 5,
        "replay_frames": 2
      }
    },
    "vhs": {
      "type": "vhs",
      "params": {
        "chroma_shift": 4.0,
        "noise_speed": 0.003,
        "head_switch": true,
        "head_switch_height": 0.08
      }
    },
    "trail": {
      "type": "trail",
      "params": {
        "fade": 0.04,
        "blend_mode": "lighter",
        "opacity": 0.25,
        "count": 3,
        "drift_x": 0,
        "drift_y": 0
      }
    },
    "scan": {
      "type": "scanlines",
      "params": { "opacity": 0.12, "spacing": 4.0, "thickness": 1.5 }
    },
    "band": {
      "type": "band_displacement",
      "params": { "chance": 0.2, "max_shift": 12, "band_height": 16 }
    },
    "vig": {
      "type": "vignette",
      "params": { "strength": 0.4, "radius": 0.7, "softness": 0.3 }
    },
    "grain": {
      "type": "noise_overlay",
      "params": { "intensity": 0.06, "animated": false, "blend_mode": "overlay" }
    },
    "out": { "type": "output" }
  },
  "edges": [
    ["@live", "stut"],
    ["stut", "vhs"],
    ["vhs", "trail"],
    ["trail", "scan"],
    ["scan", "band"],
    ["band", "vig"],
    ["vig", "grain"],
    ["grain", "out"]
  ],
  "modulations": [
    { "node": "vhs", "param": "chroma_shift", "source": "audio_beat", "scale": 6.0, "offset": 4.0, "smoothing": 0.7 },
    { "node": "band", "param": "chance", "source": "audio_rms", "scale": 0.3, "offset": 0.2, "smoothing": 0.85 }
  ],
  "layer_palettes": {
    "live": { "saturation": 0.4, "sepia": 0.55, "hue_rotate": -10, "contrast": 1.25, "brightness": 1.1 }
  }
}
```

## Node Parameter Reference

### Processing Nodes

**colorgrade**: `saturation` (0-2, def 1.0), `brightness` (0-2, def 1.0), `contrast` (0-2, def 1.0), `sepia` (0-1, def 0), `hue_rotate` (-180–180, def 0)

**vhs**: `chroma_shift` (0-20px, def 4), `noise_speed` (0-0.05, def 0.003), `head_switch` (bool, def true), `head_switch_height` (0-0.2, def 0.08), `tracking_jitter` (0-10, def 2)

**thermal**: `palette` (enum: warm/cold/custom, def warm), `edge_strength` (0-1, def 0.3), `blend_original` (0-1, def 0)

**halftone**: `dot_size` (1-20, def 6), `angle` (0-90, def 45), `color_mode` (enum: mono/cmyk/rgb, def mono)

**pixsort**: `threshold` (0-1, def 0.3), `direction` (enum: horizontal/vertical, def horizontal), `segment_length` (10-500, def 100)

**ascii**: `cell_size` (4-24, def 8), `charset` (enum: full/simple/blocks, def full), `color_mode` (enum: mono/original, def original)

**bloom**: `threshold` (0-1, def 0.5), `radius` (1-20, def 8), `alpha` (0-1, def 0.3)

**scanlines**: `opacity` (0-0.5, def 0.12), `spacing` (2-8, def 4), `thickness` (0.5-3, def 1.5)

**vignette**: `strength` (0-1, def 0.35), `radius` (0.2-0.9, def 0.7), `softness` (0.1-0.5, def 0.3)

**band_displacement**: `chance` (0-1, def 0.25), `max_shift` (1-50px, def 20), `band_height` (2-30px, def 10)

**noise_overlay**: `intensity` (0-0.3, def 0.06), `animated` (bool, def false), `blend_mode` (enum: overlay/additive/multiply, def overlay)

**circular_mask**: `radius` (0.1-0.5, def 0.42), `softness` (0-0.1, def 0.02)

**warp**: `pan_x` (0-20, def 0), `pan_y` (0-20, def 0), `rotate` (0-0.1, def 0), `zoom` (0.8-1.5, def 1.0), `breath` (0-0.02, def 0), `slice_count` (0-30, def 0), `slice_amplitude` (0-10, def 0)

**strobe**: `chance` (0-0.1, def 0.02), `color` (vec4, def white), `duration` (1-5 frames, def 2)

**syrup**: `color` (vec3, def "30,15,45"), `top_alpha` (0-0.3, def 0), `bottom_alpha` (0-0.5, def 0.25)

**invert**: `strength` (0-1, def 1.0)

**edge_detect**: `threshold` (0-1, def 0.1), `color_mode` (enum: luminance/original/white, def luminance), `method` (enum: sobel/laplacian, def sobel)

**chromatic_aberration**: `offset` (vec2, def [3,0]), `radial` (bool, def false), `intensity` (0-1, def 0.5), `channel_order` (enum: RGB/RBG/GBR, def RGB)

**displacement_map**: `strength` (vec2, def [10,10]), `mode` (enum: displace/refract, def displace), `channel` (enum: RG/luminance, def RG). Map input on port `b`.

**threshold**: `level` (0-1, def 0.5), `softness` (0-0.1, def 0.02), `color_above` (vec4, def white), `color_below` (vec4, def black)

**color_map**: `gradient` (array of {position, color} stops), `range` (vec2, def [0,1]), `blend` (0-1, def 1.0)

**posterize**: `levels` (2-64, def 6), `per_channel` (bool, def false), `gamma` (0.5-2, def 1.0)

**fisheye**: `strength` (−1 to 2, def 0.5), `center` (vec2, def [0.5,0.5]), `zoom` (0.5-2, def 1.0)

**mirror**: `axis` (enum: H/V/both/quad, def V), `position` (0-1, def 0.5)

**kaleidoscope**: `segments` (2-32, def 6), `center` (vec2, def [0.5,0.5]), `rotation` (0-360, def 0), `offset` (0-1, def 0)

**dither**: `matrix_size` (enum: 2/4/8/16, def 4), `color_levels` (2-256, def 4), `method` (enum: bayer/blue_noise/white_noise, def bayer), `monochrome` (bool, def false)

**emboss**: `angle` (0-360, def 135), `strength` (0-2, def 1.0), `blend` (0-1, def 0.5)

**sharpen**: `amount` (0-3, def 1.0), `radius` (0.5-5, def 1.0), `threshold` (0-0.1, def 0.02)

**rutt_etra**: `displacement` (0-100, def 30), `line_density` (20-200, def 80), `perspective` (vec3, def [0,0.3,1]), `line_width` (0.5-3, def 1.0), `color_mode` (enum: luminance/original/gradient, def luminance)

**voronoi_overlay**: `cell_count` (10-500, def 50), `edge_width` (0-3, def 1.0), `mode` (enum: fill/edges/stained_glass, def edges), `animation_speed` (0-2, def 0.5), `jitter` (0-1, def 0.8)

**tile**: `count` (ivec2, def [2,2]), `mirror` (bool, def false), `gap` (0-10px, def 0), `offset` (vec2, def [0,0])

**drift**: `speed` (0-2, def 0.3), `amplitude` (0-30px, def 8), `frequency` (0.5-5, def 1.5), `coherence` (0-1, def 0.7)

**breathing**: `rate` (0.1-4 Hz, def 1.0), `amplitude` (0-0.1, def 0.02), `source` (enum: fixed/heartrate/bpm/breath, def fixed), `curve` (enum: sine/ease/sharp, def sine)

**tunnel**: `speed` (0-5, def 1.0), `twist` (0-2, def 0.3), `radius` (0.2-1, def 0.5), `texture_source` (enum: camera/noise/gradient, def camera), `distortion` (0-1, def 0.3)

**transform**: `position` (vec2, def [0,0]), `scale` (vec2, def [1,1]), `rotation` (0-360, def 0), `pivot` (vec2, def [0.5,0.5]), `border` (enum: clamp/repeat/mirror/black, def clamp)

### Temporal Nodes

**trail**: `fade` (0.001-0.2, def 0.04), `blend_mode` (enum: lighter/multiply/difference/screen/overlay, def lighter), `opacity` (0-1, def 0.5), `count` (1-16, def 4), `drift_x` (0-10, def 0), `drift_y` (0-10, def 0)

**stutter**: `check_interval` (5-60 frames, def 20), `freeze_chance` (0-0.5, def 0.15), `freeze_min` (1-10, def 2), `freeze_max` (2-20, def 5), `replay_frames` (1-8, def 2)

**feedback**: `decay` (0.01-0.2, def 0.05), `zoom` (0.95-1.1, def 1.02), `rotate` (0-0.1, def 0.01), `blend_mode` (enum: lighter/screen/overlay, def lighter), `hue_shift` (0-30, def 0)

**slitscan**: `direction` (enum: horizontal/vertical, def vertical), `speed` (0.5-5, def 1.0), `buffer_frames` (30-300, def 150)

**diff**: `threshold` (0-0.3, def 0.05), `color_mode` (enum: binary/grayscale/original, def grayscale), `frame_delay` (1-30, def 1)

**datamosh**: `flow_strength` (0-2, def 1.0), `keyframe_interval` (10-300 frames, def 60), `blend_mode` (enum: replace/additive, def replace), `decay` (0-0.1, def 0.02), `motion_threshold` (0-0.5, def 0.1)

**optical_flow**: `resolution` (enum: full/half/quarter, def half), `smoothing` (0-1, def 0.5), `output` (enum: flow_field/magnitude/visualization, def flow_field)

**echo**: `frame_count` (2-32, def 8), `decay_curve` (enum: linear/exponential/equal, def exponential), `blend_mode` (enum: average/additive/max, def average)

**time_displacement**: `max_delay` (2-150 frames, def 30), `map_source` (enum: luminance/external/noise, def luminance), `blend` (0-1, def 1.0)

**motion_trail**: `length` (2-30, def 8), `decay` (0.01-0.2, def 0.05), `hue_shift` (0-30, def 0), `motion_threshold` (0-0.3, def 0.05), `blend_mode` (enum: additive/screen, def additive)

**reaction_diffusion**: `feed_rate` (0.01-0.1, def 0.055), `kill_rate` (0.01-0.07, def 0.062), `diffusion_a` (0.5-1.5, def 1.0), `diffusion_b` (0.1-0.8, def 0.5), `seed_source` (enum: noise/camera/audio, def noise), `speed` (0.5-5, def 1.0)

**fluid_sim**: `viscosity` (0-0.01, def 0.001), `diffusion` (0-0.01, def 0.001), `vorticity` (0-5, def 2.0), `dissipation` (0.9-1.0, def 0.98), `inject_source` (enum: audio/camera_motion/manual, def audio), `color_mode` (enum: dye/camera_sample, def dye)

**particle_system**: `emit_rate` (10-10000, def 500), `lifetime` (0.5-10s, def 3.0), `velocity` (vec2, def [0,-50]), `gravity` (vec2, def [0,50]), `turbulence` (0-50, def 10), `size` (1-10px, def 2), `color_over_life` (gradient), `emit_source` (enum: point/line/camera_motion/audio_peaks, def audio_peaks)

**droste**: `zoom_speed` (0-5, def 1.0), `spiral` (0-3, def 0.5), `center` (vec2, def [0.5,0.5]), `branches` (1-6, def 1)

### Compositing Nodes

**blend**: `mode` (enum: lighter/multiply/difference/screen/overlay/soft_light/hard_light, def screen), `alpha` (0-1, def 0.5)

**crossfade**: `mix` (0-1, def 0.5), `duration` (0-5000ms, def 500)

**luma_key**: `threshold` (0-1, def 0.5), `softness` (0-0.3, def 0.1), `invert` (bool, def false), `channel` (enum: luma/R/G/B, def luma)

**chroma_key**: `key_color` (vec3, def [0,1,0]), `tolerance` (0-1, def 0.3), `softness` (0-0.3, def 0.1), `spill_suppression` (0-1, def 0.5)

**camera_select**: `source` (int, camera index), `transition` (enum: cut/dissolve/wipe_L/wipe_R, def dissolve), `duration` (0-2000ms, def 300), `auto_mode` (enum: manual/beat/motion/flow, def manual)

**split_screen**: `layout` (enum: halves_h/halves_v/thirds/quad/diagonal, def halves_v), `sources` (array of camera indices), `border_width` (0-5px, def 1), `border_color` (vec4, def black)

**pip**: `position` (vec2, def [0.7,0.7]), `size` (vec2, def [0.25,0.25]), `corner_radius` (0-20px, def 4), `border` (0-3px, def 1), `border_color` (vec4, def white), `opacity` (0-1, def 1.0)

### Generative Nodes

**noise_gen**: `type` (enum: perlin/simplex/worley/fbm, def simplex), `frequency` (vec3, def [2,2,1]), `octaves` (1-8, def 4), `lacunarity` (1-3, def 2.0), `amplitude` (0-1, def 1.0), `speed` (0-3, def 1.0), `seed` (float, def 0)

**waveform_render**: `source` (enum: waveform/fft/lissajous, def fft), `shape` (enum: linear/circular/spiral, def circular), `thickness` (1-10, def 2), `color` (vec4, def [0,1,0.8,0.8]), `smoothing` (0-1, def 0.7), `position` (vec2, def [0.5,0.5]), `scale` (0.1-2, def 0.8)

**sdf_scene**: `scene_type` (enum: metaballs/fractal/terrain/toroid, def metaballs), `complexity` (1-10, def 4), `color_palette` (gradient), `camera_orbit` (vec3, def [0,0,3]), `morph` (0-1, def 0.5), `audio_bind` (enum: bass/mid/high/energy, def energy)

**solid**: `color` (vec4, def [0,0,0,1])
