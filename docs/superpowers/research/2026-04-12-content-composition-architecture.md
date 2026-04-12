# Content Composition Architecture — Research Synthesis

**Date:** 2026-04-12
**Status:** Research / Design exploration
**Question:** Make the stream compositor's content layout (1) easy to extend/modify and (2) highly performant regardless of what content is on the table.

---

## 0. Problem framing

The current stream output is one of many possible compositions: YouTube video reactions masked into Sierpinski corners, a waveform in the center void, two Pango overlay zones, a Vitruvian Man + golden spiral in the upper-left, an album cover in the lower-left, 24 shader effect slots on top of everything, and 6 cameras laid out underneath — plus a parallel wgpu surface with its own 8-pass vocabulary graph and affordance-recruited content injections.

This specific layout is arbitrary. What's **not** arbitrary is the pattern: **content sources of varying kinds, layered or injected into containers, with effects applied.** Tomorrow's layout might be a grid of recorded takes with a talking-head overlay. The week after, a floating heads-up display with real-time MIDI visualizations. The goal is to stop hardcoding layouts and content types, and to make the compositor handle whatever comes next without degrading.

This document synthesizes 35+ content-source inventory, a deep-dive on the existing effect_graph system, a map of the emerging unified content abstraction in the wgpu pipeline, an industry survey of 25 compositing systems, and a literature review of 28 research topics on render graphs, dataflow programming, and live production.

---

## 1. Where we actually are

### 1.1 Two independent pipelines

There are two render paths, fully separate:

1. **GStreamer compositor** (`agents/studio_compositor/`) — cameras → `cudacompositor` → `cairooverlay` → 24 `glfeedback` slots → `/dev/video42` → OBS → YouTube. Python wraps a GStreamer pipeline with custom plugin `gst-plugin-glfeedback` for temporal effects.
2. **wgpu Reverie surface** (`hapax-logos/crates/hapax-visual/`) — Rust binary `hapax-imagination` running a `DynamicPipeline` that hot-loads plan.json from `/dev/shm/hapax-imagination/pipeline/` → WGSL passes → winit window + JPEG readback → `/dev/shm/hapax-visual/frame.jpg` → Tauri HTTP server on `:8053` → React `VisualSurface`.

They share **no structural code**. The coupling is filesystem-as-bus: JSON manifests, JPEG snapshots, raw-RGBA files in `/dev/shm/`. Six cross-process content paths use the same `write → rename` atomicity pattern.

### 1.2 The complete content source inventory

The codebase exploration surfaced **35 distinct content types** feeding the two pipelines. Grouped by category:

| Category | Count | Examples |
|---|---|---|
| **Camera tiles** | 2 | 6 USB cameras into compositor grid; single-camera FX source switching |
| **YouTube PiP / video** | 3 | v4l2 loopback → FX chain; JPEG snapshot → Sierpinski mask; bouncing PiP (dormant) |
| **Sierpinski** | 3 | Triangle geometry, video masking, center waveform |
| **Cairo overlay zones** | 3 | Pango folder-cycle (markdown/ANSI/txt/PNG), Pango file-watch scrolling, PNG image |
| **Fixed Cairo overlays** | 7 | Album cover + attribution, Vitruvian Man, golden spiral, token glyph, token trail, particle explosions, PIP stylings |
| **Audio-driven visual** | 1 | FlashScheduler (alpha animation, not new pixels) |
| **Shader content nodes** | 5 | noise_gen, solid, waveform_render, content_layer, sierpinski_content |
| **Shader processing nodes** | ~54 | The rest — ascii, bloom, feedback, slitscan, reaction_diffusion, etc. |
| **wgpu content slots (legacy)** | 1 | ContentTextureManager — 4 fixed slots from slots.json, JPEG decode |
| **wgpu content sources (unified)** | 8 | ContentSourceManager — 16 dynamic slots, RGBA manifest protocol; affordance-recruited: camera-*, content-narrative_text, knowledge_recall, profile_recall, episodic_recall, waveform_viz, inject_url, inject_search |
| **Orphaned / dead** | 3 | `visual_layer.py` 6-zone HUD, `YouTubeOverlay.PIP_EFFECTS`, `spawn_confetti` |
| **Detection overlays** | 0 | None exist. Rich IR/face/pose detection feeds presence engine but nothing draws on the rendered output. |

Key observations from the inventory:

- **The "5 Pango overlay zones" don't exist yet** — only 2 are wired. The 6-zone HUD is in an orphaned module (`visual_layer.py::render_visual_layer`) that has no call site in `on_draw()`.
- **Three readers of the same YouTube JPEG source**: `SierpinskiRenderer._load_frame` (Cairo mask), `SierpinskiLoader._update_manifest` (wgpu slot manifest copier), and the now-dormant `YouTubeOverlay`. Plus `/dev/video50-52` v4l2 loopbacks for FX chain input selection. Four parallel transports for the same 3 video slots.
- **Two parallel content slot abstractions run simultaneously** on the wgpu side: `ContentTextureManager` (4 fixed slots, JPEG manifest, only `SierpinskiLoader` writes) and `ContentSourceManager` (16 dynamic sources, RGBA protocol, the affordance-recruited path). Live evidence shows both active.
- **Vitruvian Man is a static PNG asset** under `TokenPole`. Single-use, not abstracted, not configurable. The golden spiral and the particle system are all hand-coded in `token_pole.py`.
- **Pango rendering is duplicated** in at least five different classes (OverlayZone, AlbumOverlay, YouTubeOverlay, TokenPole, `_render_text_to_rgba` in the source protocol). Each re-implements font selection, outline rendering, layout creation.
- **Image loading is duplicated**: `GdkPixbuf` (Sierpinski), `cairo.create_from_png` (AlbumOverlay), PIL (ContentCapabilityRouter), manual ImageSurface (OverlayZone). Five different caching policies.

### 1.3 Abstractions that already exist (and are good)

Despite the duplication, several strong abstractions are already present:

1. **`ShaderRegistry` + node JSON manifests.** `agents/effect_graph/registry.py` + `agents/shaders/nodes/*.json`. Typed ports, typed params, temporal flag, parallel GLSL+WGSL variants, same manifests serve both pipelines. Already supports ~57 node types.

2. **`EffectGraph` + `GraphCompiler` + `GraphRuntime`.** `agents/effect_graph/types.py` + `compiler.py` + `runtime.py`. Pydantic-based DAG data model, topological sort, port validation, layer-source semantics (`@live`, `@smooth`, `@hls`, `@accum_*`, `content_slot_*`), hot-reloadable patches.

3. **`wgsl_compiler.write_wgsl_pipeline()` + Rust inotify hot-reload.** `agents/effect_graph/wgsl_compiler.py` + `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs`. Python writes `plan.json` + WGSL shaders; Rust watcher fires, `DynamicPipeline.try_reload()` rebuilds all wgpu pipelines on the next frame. Mid-frame swap not supported; frame-level atomic swap is.

4. **`UniformModulator` + ModulationBindings.** `agents/effect_graph/modulator.py`. Maps named signals to `(node, param)` pairs through linear scale/offset, exponential smoothing, or asymmetric attack/decay. The binding model is sound — asymmetric envelope is the killer feature (fast snap, slow release for audio reactivity).

5. **`VisualGovernance` atmospheric selector.** `agents/effect_graph/visual_governance.py`. `(stance, energy_level, genre)` → `PresetFamily.first_available()` → preset name. Deny-wins consent veto. Priority-ordered fallbacks. 30-second dwell timer.

6. **`ContentSourceManager` + source manifest protocol.** `hapax-logos/crates/hapax-visual/src/content_sources.rs` + `agents/reverie/content_injector.py`. 16-slot dynamic registry scanned every 100ms. TTL-based expiry. Z-ordered projection to 4 GPU bindings. Already accepts arbitrary RGBA content from any Python producer.

7. **Shared uniforms contract.** 9 canonical expressive dimensions (intensity, tension, depth, coherence, spectral_color, temporal_distortion, degradation, pitch_displacement, diffusion) flow from stimmung state to shader uniforms in a fixed struct layout. The same format works for both pipelines.

8. **Atomic write via `tmp + rename`.** Used consistently for every shm-manifest write.

### 1.4 Where the abstractions don't go

**Single-output constraint in effect_graph.** `compiler.py:58-62` enforces exactly one `output` node. No multi-surface output, no named render targets, no "main view + HUD" split.

**Executor is shader-only.** The Rust `DynamicPipeline` executes WGSL fragment/compute passes. A node cannot be a Cairo surface, a text renderer, a Python function, or a memory-mapped external frame. The external content pathway (`content_slot_*`) is hand-coded for two specific node types (`content_layer`, `sierpinski_content`) — not a generic mechanism.

**4-slot dimensionality is load-bearing.** `content_slot_0..3` is the fixed GPU interface for external content. `ContentSourceManager` has 16 sources internally but projects to 4 slot views by sorting on `z_order`. Beyond the top 4 z-ordered sources, content is simply invisible.

**Texture pool is homogeneous.** Every texture is 2D RGBA8Unorm at the surface size. No sub-region rendering, no off-screen targets at different resolutions, no non-image resources.

**No per-node resource budgets.** Nothing enforces frame-time accounting per pass. If a preset is too heavy, it just runs slow. No graceful skip-if-over-budget, no fallback path.

**`LayerPalette` only applies to compositor layer sources.** Not to content slots, not to per-node outputs. Ortho to the graph, applied at ingest only.

**GStreamer and wgpu pipelines share node manifests but not execution.** Two completely separate runtimes (`SlotPipeline` in Python for glfeedback, `DynamicPipeline` in Rust for wgpu). A node exists in both but is compiled twice from GLSL and WGSL sources respectively.

**Cairo overlay layer split is ad-hoc.** Pre-FX overlay (gets shader styling) vs post-FX overlay (raw on top). Which layer a given overlay lives in is encoded per class — Sierpinski and OverlayZones go pre-FX, Album/TokenPole go post-FX — no shared "depth" or "z-order" abstraction.

---

## 2. Industry prior art — what every good system shares

The 25-system survey and 28-topic literature review produced a strong signal. Every system that handles "extensible content + effects" well shares a small set of patterns. The patterns are independent enough to adopt a la carte.

### 2.1 Collapse content and effects into one type

OBS, Nuke, TouchDesigner, Bevy, Fusion, and Unreal RDG all do this. A "source" and an "effect" are user-facing labels; at the engine level they're the same abstract thing — a node with N inputs and 1 output, a lifecycle, a schema, some parameters. OBS goes furthest: **filters are sources**. A filter is a source with `type = OBS_SOURCE_TYPE_FILTER` attached to a parent.

Why this matters: the moment a user writes a plugin that blurs the line — a camera-with-built-in-LUT, a generator-that-reads-a-trigger-input, an effect-that-produces-new-content-on-edges — hardcoded type hierarchies fall over. Avoid this from day one.

### 2.2 DAG, not stack or tree

Every serious extensible compositor is a DAG: Nuke, Fusion, TouchDesigner, Notch, Unreal RDG, Frostbite. Layer stacks (Photoshop, After Effects, Resolume, OBS scenes) are the special case "linear DAG." Start with the general form — you can always render a linear DAG as a stack in the UI.

A DAG also gives you free support for:
- Multi-output sources (a camera that simultaneously feeds the main view, a PiP, and a chroma-key branch)
- Shared upstream work (reaction-diffusion accumulator read by both the center waveform and the corner content masks)
- Conditional routing (selector nodes that pick one of N upstreams)

### 2.3 Pull-based lazy evaluation

TouchDesigner, Nuke, and every render graph use this. **Nothing runs unless its output is observed.** Viewer visibility, scene selection, window compositing, and output writing define the "interested endpoints" each frame. From them, the scheduler walks backward through dependencies and cooks only what reachable subgraphs need.

Applied to a studio compositor: if a camera tile is not currently visible in any layout mode or routed to any output, its upload, decode, and effect chain should all be skipped automatically. This gives you free graceful degradation when a camera goes offline.

### 2.4 Build the graph every frame, then compile

This is the Frostbite FrameGraph / Unreal RDG / Maister Granite pattern, and it's counterintuitive until you realize the rebuild is cheap (sub-millisecond for hundreds of passes) compared to the benefits:

- **Dead pass culling** — backward BFS from passes with side effects; anything unreachable drops entirely. Hidden camera = zero work without any explicit "is visible" check in the camera code.
- **Transient memory aliasing** — compute first-use / last-use intervals; aliased physical allocations for disjoint intervals. Peak memory `<<` sum of all transient memory.
- **Automatic barrier synthesis** — every resource's usage transitions are implicit in the declared read/write sets. No hand-placed barriers. No barrier bugs.
- **Zero hot-reload cost** — the graph is constructed from imperative code each frame; swap in a new plugin, the next frame sees it automatically.

The "rebuild cost" objection goes away in practice because the graph is small and the compile is simple. You're rebuilding a description, not rebuilding GPU pipelines.

### 2.5 Retained state at explicit cache boundaries

Flutter has **repaint boundaries**. Slate has **invalidation panels**. Chromium has **composited layers**. TouchDesigner has **Cache TOP**. Each one solves the same problem: some subtrees of the composition change on a different cadence than others; the compositor should persist the cached output across frames instead of re-rendering.

The control is usually explicit — the user says "this is stable, cache it" — rather than automatic. Automatic layerization (as in Chromium) is a minefield of memory bloat and unpredictable update cost.

For your 6-camera + shader stream:
- Camera tile renders at 30Hz (source rate).
- Text overlay renders at 1Hz (when content changes).
- Shader effect renders every frame (params modulate every tick).
- A PNG logo renders once.

Treating these with a single render cadence is wasteful on both ends — too fast for the logo, too slow for the shaders. Explicit cache boundaries (`repaint_when: "params_changed"`, `repaint_when: "source_mtime_changed"`, `repaint_when: "always"`) let the compositor reuse the cached texture until invalidation.

### 2.6 Separate authoring topology from runtime topology

Unity Shader Graph compiles to HLSL. Notch Builder exports a Block. Unreal RDG builds its graph from imperative C++ every frame. TouchDesigner has one authoring DAG but the TOPs may fuse into fewer GPU passes. **The node graph the user sees is never the data structure the engine runs.**

This means your pluggability surface and your performance surface are different things. Users add nodes; the compiler decides what to do with them. You get to optimize the runtime independently of the UX.

### 2.7 Plugin contract = callbacks + schema + I/O

Every system converges on the same shape:
- **Lifecycle callbacks**: init, tick, render, destroy.
- **Schema**: declared parameters with types, defaults, ranges, labels. Auto-reflected into the inspector UI.
- **Typed I/O**: N texture (or other) inputs, 1 output.

OBS's `obs_source_info` struct, TouchDesigner's Custom Operator SDK, Resolume's FFGL, Bevy's `RenderPlugin` — all the same shape with different concrete types. Parameter schema is the point where plugins get their UI for free.

### 2.8 Separate content sources from output surfaces

MadMapper has `Media` (content) and `Surface` (physical output region) as independent namespaces with assignment at a third layer. NDI advertises `Source` objects on the LAN with discovery; any receiver can subscribe. Fusion has named nodes you can `save/load` by path. WebRTC's simulcast model has stream IDs, and subscribers choose which to forward.

The common pattern: a source doesn't know what pixel grid it's going to. A surface doesn't know where its content comes from. They meet at a named assignment.

For your system, this means camera feeds, YouTube PiPs, overlays, and shaders should all be **sources** in a shared namespace. The Sierpinski triangle corners, the lower-third region, the PiP slot, the full-frame FX-source input — all these should be **surfaces**. The compositor configuration is then just a mapping `{surface: source}` (plus per-assignment transform and effect chain), not a hardcoded Python class per layout.

### 2.9 Direct-render optimization

OBS does this and calls it out explicitly: when a source has exactly one filter and custom drawing is disabled, the filter skips the intermediate texture and draws directly. This is a big win — intermediate textures dominate cost in deep filter chains. Detect "effect chain length == 1" at compile time and fuse.

### 2.10 Porter-Duff + premultiplied alpha is the correct math

Porter & Duff (1984) formalized compositing with 12 canonical operators. Five of them (`DST_OVER`, `SRC_IN`, `SRC_ATOP`, `DST_ATOP`, `SRC_XOR`) literally cannot be expressed with non-premultiplied alpha and a single blend function. Bilinear sampling is only correct over transparent regions with premultiplied. FBO round-trips only work with premultiplied.

For a live compositor, default everything to `over` with premultiplied storage. Expose `plus` (additive) for particles/bloom overlays. Expose `in`/`out`/`atop` for advanced clipping.

---

## 3. The design space — five orthogonal axes

Every live compositor design has to pick a value on five independent axes. (Credit: research literature synthesis.)

| Axis | Values | Consequence |
|---|---|---|
| **A. Frame description model** | Retained scene graph / Immediate rebuild / Hybrid (retained scene → immediate graph compile) | How UI state becomes GPU state |
| **B. Execution scheduling** | Push (data-driven) / Pull (demand-driven) / Clock-driven (fixed tick) | When nodes run; how rates are reconciled |
| **C. Resource management** | Manual / Pooled / Full render-graph aliasing | Memory efficiency vs code complexity |
| **D. Ingest topology** | Sources drive clock / Renderer drives clock / Two-clock bridge | Latency, jitter handling, A/V sync |
| **E. Composition operators** | Porter-Duff only / Named blend modes / Node-graph shaders / Full DSL | Creative ceiling |

Common template shapes:

**Template 1 — OBS model (production-proven):** retained scene, clock-driven with async sources, manual resource management, renderer clock, named blend modes. Battle-tested. Every new source type is a C plugin. Low creative ceiling.

**Template 2 — Bevy / Frostbite model (engine-style):** hybrid retained-scene-immediate-graph-rebuild, two-clock (sim + render), full render-graph aliasing, renderer clock, node-graph shaders. Highest performance, best memory, clean plugin story. Significant up-front design cost.

**Template 3 — TouchDesigner model (live art-style):** retained DAG, pull-based evaluation, pooled resources, internal source clocks pulled at display rate, full node-graph shaders. Interactive, exploratory. Resource overhead per node.

**Template 4 — GStreamer compositor model (pure pipeline):** flat pipeline graph, push scheduling with QoS backpressure, manual resources, source clocks with aggregator, fixed blend. Zero-copy end-to-end, minimum latency. Low creative ceiling; every effect is a new element with format negotiation.

Our current system is roughly Template 1 (the GStreamer compositor side) overlaid with Template 2 (the wgpu side). This explains both the strengths (robust ingest, clean render graph) and the pain (heterogeneous content is bolted onto each pipeline separately; there's no unifying abstraction between them).

### Combinations that conflict
- **Pull scheduling + async sources**: if a source produces its frame late, pull either blocks the output or serves stale data. Push + latest-frame wins for live streaming.
- **Full render-graph aliasing + plugin-contributed passes that don't declare resources**: one missing annotation breaks barrier correctness. Either enforce strict declaration or don't alias.
- **Immediate-mode content layer tree + heavy per-item caching**: IMGUI assumes cheap per-frame rebuild; caching adds retained state that defeats the model. Pick one.
- **Deep compositing + realtime budget**: incompatible at 1080p60 on one GPU. Use 2D with shallow depth hints if you need occlusion.
- **Fragment-shader-only composition + multi-pixel kernels**: forces N fullscreen passes scaling N×resolution bandwidth. Use compute fusion.

---

## 4. Recommended architecture

Based on the inventory, the existing abstractions, and the prior art, the right architectural move for hapax is **Template 2 with Template 4's ingest boundary**, plus three additions specific to this system.

### 4.1 The core model: Source + Surface + Assignment

Adopt the MadMapper/NDI/OBS shape. Three namespaces:

1. **Source** — a typed content producer with a schema. Can be a camera feed, a YouTube video, a Cairo-rendered text layer, a WGSL shader output, a PNG file, an RGBA frame from affordance recruitment, another compositor's output via NDI. A source has:
   - `id` (globally unique, human-readable string)
   - `kind` (camera, video, shader, image, text, cairo, external_rgba, ndi, ...)
   - `schema` (typed parameters)
   - `output_type` (texture_rgba, texture_rgba_premul, video_stream, ...)
   - `update_cadence` (always, on_change, manual)
   - Lifecycle callbacks: `init`, `tick(dt)`, `render(ctx)`, `destroy`

2. **Surface** — a typed destination region with geometry. Can be the full output frame, a tile in a grid, an inscribed rectangle in a triangle corner, a fixed screen region, a named wgpu texture binding (`content_slot_0`), an NDI output source, the primary OBS output. A surface has:
   - `id`
   - `kind` (rect, tile, masked_region, wgpu_binding, ndi_out, video_out)
   - `geometry` (how to compute its bounds per frame — constants, math expressions, or references to sibling surfaces)
   - `effect_chain` (an ordered list of effect node IDs applied to whatever content is assigned here)
   - `blend_mode` (over, plus, in, out, atop)
   - `z_order`

3. **Assignment** — a binding of source to surface with per-assignment transform, opacity, and optional per-assignment effect chain.

This immediately collapses the current zoo into structure:

| Current | As Source | As Surface |
|---|---|---|
| C920-desk camera | `Source(kind=camera, id=c920-desk)` | — |
| YouTube slot 0 | `Source(kind=youtube, id=yt-0)` | — |
| Sierpinski corner top | — | `Surface(kind=masked_region, id=sier-corner-top, geometry=inscribed_rect(tri_top))` |
| Album cover | `Source(kind=image, id=album-art)` | `Surface(kind=rect, id=lower-left-square)` |
| Vitruvian Man | `Source(kind=image, id=vitruvian)` | — |
| Golden spiral | `Source(kind=cairo, id=golden-spiral)` | — |
| TokenPole region | — | `Surface(kind=rect, id=upper-left-square)` |
| Pango zone 1 | `Source(kind=text, id=obsidian-cycle)` | `Surface(kind=rect, id=overlay-main-float)` |
| Sierpinski line work | `Source(kind=cairo, id=sierpinski-lines)` | — |
| Content slot 0..3 (wgpu) | — | `Surface(kind=wgpu_binding, id=content_slot_N)` |
| Halftone shader | `Source(kind=shader, id=halftone)` | — |
| Final stream output | — | `Surface(kind=video_out, id=obs-feed)` |

Layouts become **named assignment sets**. The current arrangement is one assignment set. A new layout is a new set, loadable from disk, swappable at runtime.

### 4.2 Retained config + immediate frame compile

Operator UI mutates a retained store of sources, surfaces, and assignments. Each frame, the Extract phase snapshots this store + the latest available frame for each source, producing an immutable frame description. The frame description feeds a render graph compiler that produces the concrete pass list for that frame.

- **Retained**: survives across frames, serializable to JSON, hot-reloadable from disk.
- **Extract**: single sync point between config-mutation threads and the render thread. Cheap (pointer copy, latest-buffer pick).
- **Compile**: takes the frame description, culls dead sources (no assignment consumes them), orders the effect chains by dependency, allocates transient textures by first-use/last-use interval, emits a linear pass list.
- **Execute**: runs the passes, writes to named surfaces.

This is the Bevy / Frostbite shape adapted to live video.

### 4.3 Unify the two pipelines behind one model

The GStreamer compositor and the wgpu visual surface are today two completely separate code paths. In the new model, they become two **output surfaces** in the same namespace:

- `Surface(kind=video_out, id=obs-feed)` — the old `/dev/video42` path
- `Surface(kind=video_out, id=wgpu-winit-window)` — the old Reverie React VisualSurface

The source namespace and the assignment set are shared. A camera can be assigned to both outputs simultaneously (same source, two assignments, two surfaces). The frame description compiler emits two pass lists — one targeting each output — and they execute independently, potentially on different hardware queues.

The pragmatic migration path: keep GStreamer as the **ingest layer** for cameras and hardware sources (its reconnection, format negotiation, v4l2 handling are battle-tested), produce dma-buf textures, and import them zero-copy into wgpu. All compositing happens in wgpu render graphs. GStreamer becomes pure capture; it no longer owns layout.

This kills the duplication:
- One camera decode, used by both outputs
- One Pango text rendering, used by both outputs
- One Cairo renderer wrapper, used by both outputs
- One shader effect chain compiler, used by both outputs

It also kills the cross-process filesystem bus for cases where both outputs want the same content. Filesystem shm stays for genuine cross-process coupling (e.g., the DMN multimodal vision loop reading frame.jpg), but becomes the exception, not the default.

### 4.4 Extend the effect_graph system as the node host

The Python `effect_graph` system is the strongest abstraction in the codebase. Keep it. But generalize the executor so it can host heterogeneous nodes, not just WGSL fragment shaders:

**Node backend types:**
- `wgsl_render` (today's default) — fragment shader, WGSL, one texture output
- `wgsl_compute` — compute shader dispatch, arbitrary bindings
- `glsl_render` — fragment shader, GLSL, for the GStreamer glfeedback path
- `cairo` — Python callback produces a Cairo ImageSurface → zero-copy upload to GPU
- `text` — Pango-rendered text → Cairo surface → GPU upload
- `image_file` — PNG/JPEG loaded from disk, watched by mtime
- `video_external` — v4l2 / dma-buf import of an externally-decoded video stream
- `shm_rgba` — raw RGBA read from `/dev/shm/` (for cross-process sources)
- `python_callback` — pure Python function (producer ticks at a specified rate, writes to a GPU texture via upload)

The node manifest JSON adds a `backend` field:
```json
{"node_type": "pango_text", "backend": "text", "inputs": {}, "outputs": {"out": "frame"},
 "params": {"text": {...}, "font": {...}, "color": {...}, "width": {...}, "height": {...}},
 "update_cadence": "on_param_change"}
```

The compiler reads `backend` and dispatches to the correct executor. The Rust `DynamicPipeline` becomes a polymorphic node host — for non-WGSL backends, it delegates to a Python IPC bridge or a dedicated Rust backend.

**This is the single most important change.** It promotes `effect_graph` from "GPU shader graph" to "content + effects graph," and it's the natural extension — the graph type system already supports it; only the executor needs to grow.

### 4.5 Generalize the external content mechanism

Today `content_slot_0..3` is hand-coded in the compiler for two specific node types, and the content-bearing shader (`content_layer`) has a hardcoded 4-slot bind group layout.

Generalize this into **named source references**:

- A source has an ID (`camera-c920-desk`, `text-obsidian-zone-1`).
- A shader node's input can be declared as `@source:camera-c920-desk` or `@surface:obs-feed` instead of a named layer.
- The compiler resolves these at graph-build time, allocates the right binding slot, and sets up the texture path (camera dma-buf, Cairo upload, Pango render).

This makes the existing `@live`, `@smooth`, `@hls` pattern — a small allowlist of hardcoded external layer sources — into a first-class, open namespace. Any source can be an input to any shader, not just the blessed three.

### 4.6 Per-source update cadence + cache boundaries

Every source declares its update cadence:
- `"always"` — cook every frame (cameras, real-time generators)
- `"on_change"` — cook when inputs change (text, shader with static params)
- `"manual"` — cook only when explicitly invalidated
- `"rate:N"` — cook N times per second (regardless of display rate)

The render graph compiler uses this to skip unchanged sources. A text overlay whose content hasn't changed is rendered once, cached in a texture, reused every frame until its content hash changes. A shader with no modulated params is rendered once, cached, reused. A camera renders every frame because its input timestamp changes every frame.

This is TouchDesigner's Cache TOP generalized into a universal source property. It's the single biggest knob for performance-under-arbitrary-content.

### 4.7 Per-layer (surface) effect chains + global effect chain

Resolume separates **per-layer effects** from **composition-level effects**. Use the same model:

- Each surface has its own effect chain applied to the assigned source before compositing.
- The final mixed output passes through a global effect chain (the existing 24-slot shader stack).

This cleanly separates "what does this content look like" from "what does the whole scene look like." A Sierpinski corner can have its own little shader chain (e.g., soft-vignette the edges) without affecting other corners, and the whole composition still gets halftone + scanlines on top.

### 4.8 Plugin contract

A content type plugin is a directory:
```
plugins/my_source_type/
  manifest.json       # {backend, inputs, outputs, params schema, update_cadence}
  source.py           # Python lifecycle: init/tick/render/destroy
  shader.wgsl         # Optional WGSL if backend == wgsl_*
  README.md
```

The compositor scans a plugin directory at startup (and optionally on file change in dev mode), loads each manifest, registers the source type, and exposes its parameters to the UI via schema introspection. No central registry to edit. A new content type is one directory.

### 4.9 Pull-based invalidation

Every source exposes a monotonically increasing `version` counter, incremented on every change that would affect its output. The compiler's Extract phase reads each source's current version; if unchanged since last frame, the cached texture is reused (if the source's `update_cadence` permits). This is the minimal "dirty" tracking that doesn't require per-pixel comparison.

Combined with dead-source culling and the update cadence system, this gives you free graceful scaling: if 80% of your content didn't change this frame, you do 20% of the work.

---

## 5. Migration path from the current state

This is a large architecture, but it can be adopted incrementally. The existing system has several features that already match parts of the target; the migration is mostly extending what exists, not replacing it.

### Phase 1 — Foundations (1-2 weeks)

1. **Unify the two content backends on the wgpu side.** Delete `ContentTextureManager` + `slots.json` + `SierpinskiLoader`. Migrate YouTube frame injection to `ContentSourceManager` via the source protocol (`inject_image` with z_order=5, content_type=rgba). This is a self-contained cleanup that removes ~500 lines of duplicate code and proves the unified abstraction is feature-complete.

2. **Generalize `@source:id` in the effect graph.** Extend `wgsl_compiler.py` + `dynamic_pipeline.rs` so any node can declare an input as `@source:name` instead of only `content_slot_*`. This is a ~100 line change on each side — most of the infrastructure exists.

3. **Promote `ContentSourceManager` slot count from 4 to "all active sources."** The hardcoded 4-slot GPU binding becomes a dynamic texture array. The Rust side already sorts by z_order; the cap is just an arbitrary limit. Requires a shader binding layout change.

### Phase 2 — Source/surface/assignment model (2-3 weeks)

4. **Introduce the `Source` / `Surface` / `Assignment` data model.** Start as a pure data model in `shared/compositor_model.py` (Pydantic). Add a JSON serialization for layouts. Write the current "garage door" layout as the first JSON file. Don't use it yet — just define the types.

5. **Build the Extract phase.** In the GStreamer compositor, add a frame-level Extract step that reads the current assignment set and snapshots latest buffers. Feed it to the existing rendering logic as a readonly description. This doesn't change runtime behavior — it's a structural refactoring.

6. **Migrate the Pango overlay zones to sources.** The `OverlayZone` class becomes `Source(kind=text, id="...", backend="text")`. The two currently wired zones are two assignments. The six-zone HUD from the orphaned `visual_layer.py` is resurrected as additional assignments to the same source type — zero new code needed.

7. **Migrate AlbumOverlay, TokenPole, Sierpinski to sources.** Each becomes a `Source` with a Cairo backend. The current hardcoded positions become `Surface` geometries in the assignment set.

### Phase 3 — Executor polymorphism (3-4 weeks)

8. **Add the `backend` field to node manifests.** Default all existing nodes to `backend: "wgsl_render"` (no behavior change).

9. **Implement the `cairo` backend.** A Python callback produces a Cairo surface; the bridge uploads to a wgpu texture via `queue.write_texture`. The SierpinskiRenderer, OverlayZones, AlbumOverlay, TokenPole all become `cairo`-backend nodes in the effect graph.

10. **Implement the `text` backend.** Unify the 5 duplicate Pango renderers into one. Caches by content hash. The existing `_render_text_to_rgba` in `agents/imagination_source_protocol.py` is the starting point.

11. **Implement the `image_file` backend.** One PNG/JPEG loader with mtime cache to replace the five existing image loaders.

12. **Implement the `video_external` backend.** v4l2 / dma-buf import of an external video stream (cameras, YouTube v4l2 loopbacks). This subsumes the current `@live` / `@smooth` / `@hls` hardcoded sources.

### Phase 4 — Compile phase (2-3 weeks)

13. **Add dead-source culling.** After Extract produces the frame description, walk backward from assigned surfaces; sources with no reachable consumer are skipped this frame.

14. **Add update-cadence tracking.** Each source has a `version: u64`. The compiler diffs against the previous frame's versions and reuses cached textures for unchanged sources.

15. **Add transient texture pooling.** Intermediate effect-chain textures are allocated from a frame-local pool keyed by descriptor. Reuse when compatible; allocate fresh otherwise. Spill to multi-frame pool when the frame-local fills.

### Phase 5 — Multi-output (1-2 weeks)

16. **Relax the single-output constraint.** The compiler emits a `targets` map: `{"main": final_texture, "hud": hud_texture}`. Each target can be blitted to a different surface (video out, wgpu window, NDI out).

17. **Unify the GStreamer and wgpu outputs.** Both pipelines become "surfaces" in the same model. A camera can feed both via two assignments. The compositor runs one render graph with two output targets.

### Phase 6 — Plugin system (2-3 weeks)

18. **Define the plugin directory layout.** `plugins/{name}/manifest.json + source.py + {optional shader files}`.

19. **Implement plugin discovery.** Scan at startup, hot-reload on file change in dev mode, register source types from manifests.

20. **Document the plugin contract.** Write the first third-party plugin (a simple one — maybe a clock or a weather widget) as a reference.

### Phase 7 — Budget enforcement (1-2 weeks, optional but high-value)

21. **Add per-source frame-time accounting.** Track `last_frame_render_ms` per source.

22. **Implement skip-if-over-budget.** A source whose `last_frame_render_ms > budget_ms` is skipped for N frames (configurable grace period), and a fallback texture is shown instead.

23. **Add a system health gauge.** Total frame time → stimmung `processing_throughput` dimension. Already wired in the other direction; now the effect_graph can see its own cost.

**Total effort estimate: 2-3 months of focused work**, produced as 7 sequenced PRs each validating the next. The system stays runnable throughout — every phase is a no-regression step.

---

## 6. Specific extraction patterns worth stealing verbatim

Beyond the broad architecture, a handful of small-scale patterns from the research are worth copying directly:

### 6.1 OBS direct-render optimization

When a source has exactly one filter, skip the intermediate texture. Detect this at compile time:

```
if len(effect_chain) == 1 and filter_supports_direct_render(effect_chain[0]):
    render_source_through_filter_directly(source, filter, target)
else:
    render_source_to_temp_texture(source, temp)
    for filter in effect_chain:
        apply_filter(filter, temp, next_temp)
    blit(next_temp, target)
```

This is the single highest-value optimization in a deep filter chain. Free intermediate-texture elimination.

### 6.2 TouchDesigner's Cache TOP primitive

Expose an explicit cache node in the effect graph:

```json
{"node_type": "cache", "backend": "cache",
 "inputs": {"in": "frame"}, "outputs": {"out": "frame"},
 "params": {"invalidate_on": "param_change | mtime | never | hash",
            "hash_source": "string"}}
```

Inserting a `cache` node anywhere in a graph makes that subgraph's output persist across frames until the invalidation condition fires. Apply to: expensive shader parameters that don't change; text layers that rebuild only on content change; image overlays; anything whose output is a pure function of slow-moving inputs.

### 6.3 Flutter repaint boundaries at the surface level

Every `Surface` in the new model gets an `update_cadence` that defaults to the cadence of its assigned source but can be overridden:

```python
Surface(
    id="sierpinski-corner-top",
    geometry=...,
    update_cadence="on_change",  # override; cached until its assigned source or its geometry changes
    effect_chain=[...],
)
```

This is Flutter's repaint boundary idea applied to your compositor: each surface is an optional cache point.

### 6.4 FrameGraph-style resource lifetime analysis

The compile phase produces, for each transient texture, a `first_use_pass` and `last_use_pass` index. Two textures whose intervals don't overlap can alias physical memory. For a typical effect chain of ~8 passes this doesn't save much — but when you have multiple surface targets and many transient intermediates, the peak live memory can be halved.

### 6.5 Bevy's Extract phase sync point

The Extract phase is the **single sync point** between the mutable config store and the immutable render description. One lock acquired, one snapshot taken, lock released. Everything downstream operates on the snapshot; the config can be mutated freely on other threads while rendering runs.

This is how you get parallel config-edit + rendering without complex synchronization.

### 6.6 Premultiplied alpha everywhere internally

All internal textures are RGBA premultiplied. Convert on ingest from sources that provide straight alpha (PNG default, most JPEG-to-RGBA paths). Convert on egress if a consumer requires straight alpha. Everything else stays premultiplied.

This is a 1-day investment that eliminates a whole class of compositing bugs (sampling fringes, FBO round-trip errors, blend-mode incorrectness).

### 6.7 Porter-Duff operator menu

Per-assignment blend mode is one of:
- `over` (default — foreground over background)
- `plus` / `add` (additive — light, particles, bloom overlays)
- `in` (foreground masked by background coverage)
- `out` (foreground masked by inverse of background coverage)
- `atop` (foreground over background but only where background exists)

This covers 95% of live compositing needs. Advanced users can request more; the five-operator menu stays stable for operators.

---

## 7. Performance strategy by content type

With the unified abstraction, performance becomes a per-content-type problem that the framework can address uniformly. Specific strategies:

### 7.1 Camera feeds (always-update)
- Keep on GStreamer capture side; zero-copy dma-buf to wgpu.
- Direct-render when chain length == 1.
- Skip when no assignment consumes them (dead-source culling).
- Downsample upstream when the target surface is smaller than the source.

### 7.2 YouTube videos (always-update)
- Same zero-copy path.
- Single decode (`youtube-player.py`) serves all consumers via named source ID.
- Delete the duplicate readers (Cairo decode, manifest copier, dormant bouncing overlay).

### 7.3 Text overlays (on-change)
- Content hash as version counter.
- Render once, cache until hash changes.
- One Pango renderer, one cache, one upload path.

### 7.4 Image files (on-change)
- Mtime as version counter.
- One image loader, one decode, shared across all consumers.

### 7.5 Cairo-rendered content (varies)
- Run the Cairo callback in a background thread (already done for Sierpinski).
- Blit only on the render thread (~0.5ms per blit regardless of content).
- Update cadence from the source (Sierpinski is audio-reactive → 10fps; static overlays are on-change).

### 7.6 Shader effects (varies)
- If params are modulated: always-update, cached only as "last frame's output" for temporal accumulators.
- If params are static: on-change (invalidated when a param writes to uniforms.json).
- Fuse compatible passes at compile time (like Frostbite).
- Compute shaders for multi-pixel kernels (blur, bloom, tonemap) to save bandwidth.

### 7.7 Affordance-recruited content (manual)
- Invalidated explicitly when the affordance pipeline recruits.
- TTL-based expiry already in place.
- Z-order determines precedence (already in place).

### 7.8 Always-on generative (vocabulary graph)
- Run every frame at the render rate.
- Temporal accumulators persisted across frames (already works).
- The 8-pass vocabulary becomes the "base layer" for the wgpu output surface; everything else composites over it.

### 7.9 The 24-shader slot stack
- Stays the global composition-level effect chain (Resolume's Composition FX level).
- Direct-render optimization: if only one slot is active, skip the slot pipeline entirely and draw to output directly.
- Per-preset analysis at load time: skip passthrough slots.

---

## 8. Risks and open questions

### 8.1 The Rust polyglot node executor is a significant engineering effort

The current `DynamicPipeline` is ~1200 lines of Rust that knows only about wgpu render pipelines. Adding polymorphism for `cairo`, `text`, `image_file`, `video_external`, `python_callback` backends is substantial work. Each backend needs:
- Its own resource lifecycle
- Its own upload path to wgpu textures
- Its own invalidation strategy
- Cross-language IPC for Python-backed nodes

The pragmatic starting point is: keep WGSL as the primary backend in Rust; Python handles all other backends and writes the result to the source protocol (`/dev/shm/hapax-imagination/sources/{id}/frame.rgba`). This is the current affordance-recruited path, and it works. The only "polymorphism" in Rust is the source registry itself.

Trade-off: one filesystem round trip per frame for Python-rendered content. Measured: turbojpeg encode + tmp+rename + Rust poll + turbojpeg decode is ~5-10ms total. Fine for on-change content; not fine for always-update 60fps content.

If 60fps Python-rendered content becomes a requirement, the alternative is a shared-memory ring buffer (single shm file per source, atomic frame index, no decode). Not needed for the current requirements.

### 8.2 GStreamer compositor vs pure wgpu compositor

The recommendation keeps GStreamer as pure ingest and moves composition to wgpu. But the current compositor uses GStreamer's `cudacompositor` + `glfeedback` + `cairooverlay` extensively. Migrating away is ~2000 lines of Python rewrites.

The pragmatic intermediate: keep the GStreamer compositor for `/dev/video42` and add the wgpu-unified model only for *new* content types. Old content types (Sierpinski, album cover, TokenPole, Pango zones) stay in the GStreamer Cairo-overlay path; new content types go through the unified source/surface/assignment model and render to the wgpu surface.

This produces the awkward situation of the "new model" rendering on one surface and the "old model" on the other, with no bridging between them. The cleaner end state requires full migration — but Phase 1-2 of the migration path works within each pipeline independently without breaking the other.

### 8.3 Dead code cleanup gives the biggest short-term win

The inventory surfaced substantial dead/orphaned code that adds complexity without value:
- `agents/studio_compositor/visual_layer.py` — 6-zone HUD with no call site
- `YouTubeOverlay.PIP_EFFECTS` — 5 stylization functions, never invoked (`_pip_draw` only renders `_album_overlay` and `_token_pole`)
- `spawn_confetti` — referenced in `director_loop.py:417` against `VideoSlotStub` which doesn't define the method (would AttributeError)
- `ContentTextureManager` + `slots.json` + `SierpinskiLoader._update_manifest` — legacy single-purpose backend shadowed at runtime by `ContentSourceManager`
- Dead `_add_camera_fx_sources` in `pipeline.py:183-230` (documented as broken, commented-out)
- Dead `_call_llm` and `_tick_*` methods in `director_loop.py` (not called from main loop; live in the file as vestigial)

Deleting these is one week of work, zero new architecture. Does not move the pluggability story forward, but reduces the "surface area" that any future architectural change has to preserve or migrate.

### 8.4 Render graph aliasing vs plugin trust

Full render graph aliasing (transient memory reuse) requires every plugin to correctly declare its resource reads/writes. A missing annotation produces GPU hazard. The options:

- **Strict static verification** — at plugin load time, parse the shader source and verify declared reads/writes match the actual sampled textures and render targets. Rejects plugins that lie.
- **Defensive allocation** — don't alias plugin-contributed resources. Pool them separately with stricter lifetimes. Accept the memory cost.
- **Signed trusted plugins only** — aliasing enabled only for plugins in a trusted list.

For a single-operator system, defensive allocation is fine. You're not trying to support untrusted plugins; you're trying to make your own plugins easy to write. Pool all plugin resources separately and don't alias them.

### 8.5 The operator mental model question

The technical architecture is one thing; the UX is another. The research showed that "every node-graph UI took years of iteration" (Nuke, Fusion, TouchDesigner, Notch). Premature exposure of a DAG UI is a trap.

The recommendation is: start with a flat list of sources assigned to named surfaces + a per-source effect chain. This is the OBS/Resolume mental model — scene, sources, filters. Users who want power can drop to a JSON layout file. Upgrade to a full DAG UI only if users start asking for routing that the flat model can't express.

---

## 9. What the architecture does NOT solve

Some things this architecture cannot fix and are worth being explicit about:

- **Content type discovery vs quality.** A plugin contract makes it easy to add content types. It does not make new content types good. The Vitruvian Man + golden spiral is a handcrafted visual idea; you can't plugin-ify creativity.

- **Real-time 4K or higher resolution.** This architecture targets 1080p60. Scaling up to 4K changes the memory bandwidth math; pass fusion (compute) and aliasing become mandatory, not optional.

- **Multi-GPU or multi-machine.** Single-workstation assumptions throughout. Multi-machine would need NDI as the primary inter-machine transport and a distributed assignment model.

- **Frame-accurate A/V sync under jitter.** The current system has ~16-33ms of jitter on camera → output latency. An architectural change does not fix this; it requires a clock-reconciliation layer (GStreamer's QoS is one model; PTP synchronization is another; SMPTE 2110 is the broadcast standard).

- **Automatic layout intelligence.** The architecture makes layouts pluggable but does not generate them. "Director-driven autonomous layout selection based on activity" is a separate feature layer (hapax stimmung + affordance recruitment) that sits above this architecture.

---

## 10. Decision summary

**What to do:**

1. Adopt **Source + Surface + Assignment** as the core data model. Currently hardcoded layouts become JSON files.
2. Unify the two pipelines behind this model; GStreamer becomes pure ingest, wgpu becomes the compositor.
3. Extend `effect_graph` with a `backend` field so nodes can be shader, Cairo, text, image, or video. The existing type system supports this; only the executor needs to grow.
4. Promote `ContentSourceManager` from a 4-slot fixed bind interface to a fully dynamic `@source:id` reference system in shader inputs.
5. Add per-source update cadence + version counters for cache-based graceful degradation.
6. Add an explicit `cache` node in the effect graph for user-controlled repaint boundaries.
7. Add a compile phase that culls dead sources, pools transient textures, and fuses compatible passes.
8. Keep the 24-slot shader stack as the composition-level effect chain (above per-surface effect chains).

**What to steal directly:**
- OBS's direct-render optimization (when filter chain length == 1)
- TouchDesigner's Cache TOP pattern
- Flutter's explicit repaint boundaries
- Frostbite's resource lifetime analysis
- Bevy's Extract-phase sync point
- Premultiplied alpha everywhere
- Porter-Duff five-operator menu

**What to delete:**
- ContentTextureManager + slots.json + SierpinskiLoader manifest writing
- visual_layer.py orphaned HUD
- YouTubeOverlay.PIP_EFFECTS dead code
- spawn_confetti stub
- The five duplicate Pango renderers (unify into one)
- The five duplicate image loaders (unify into one)

**What to defer:**
- Full DAG UI (start with flat list + JSON)
- Polyglot node executor in Rust (start with Python-side backends writing to the source protocol)
- Multi-GPU / multi-machine
- 4K+ resolutions

---

## 11. Appendix: Research inputs

This synthesis draws on five parallel research streams:

1. **Content surface inventory** — 35 distinct content types across both pipelines, every producer/destination/cadence/cost mapped with file paths.
2. **Effect graph architecture deep-dive** — types, compiler, modulator, governance, hot-reload, content slot injection, limits and extension points.
3. **wgpu content model analysis** — the legacy slot manifest vs unified source protocol, the Rust precedence logic, the affordance recruitment path, the two-backend coexistence.
4. **Industry prior art survey (25 systems)** — Resolume, TouchDesigner, Notch, VDMX, MadMapper, OBS, vMix, Unreal Render Graph, Unity SRP, Shader Graph, Chromium compositor, Flutter layers, Nuke, Fusion, ATEM, WebRTC SFU, NDI, Unreal Slate, Coherent GT, Noesis, Frostbite FrameGraph, Maister Granite, retained vs immediate, dirty rectangles, ECS rendering.
5. **Research literature review (28 topics)** — FrameGraph theory, Vulkan render graphs, reordering/merging, resource aliasing, scene graph evolution, dataflow languages, FRP, TouchDesigner evaluation model, Bevy renderer, Unity DOTS, Porter-Duff, premultiplied alpha, deep compositing, GPU batching, compute vs fragment, texture atlases, async compute, NDI protocol, simulcast/SVC, hardware overlay obsolescence, OBS source architecture, GStreamer compositor internals, MLT Framework, declarative compositing (Chang et al. ICFP 2017), temporal caching (Nehab et al. 2007), GPU bandwidth optimization, tile-based rendering.

Primary sources with links live in the individual research outputs; the complete bibliography is ~150 references. Key foundational papers for anyone implementing this:

- O'Donnell, **"FrameGraph: Extensible Rendering Architecture in Frostbite"** (GDC 2017) — the canonical render graph paper. https://www.gdcvault.com/play/1024612/FrameGraph-Extensible-Rendering-Architecture-in
- Porter & Duff, **"Compositing Digital Images"** (SIGGRAPH 1984) — the canonical compositing paper. https://keithp.com/~keithp/porterduff/p253-porter.pdf
- Arntzen, **"Render graphs and Vulkan — a deep dive"** (Granite engine blog, 2017) — the open-source reference implementation. https://themaister.net/blog/2017/08/15/render-graphs-and-vulkan-a-deep-dive/
- Chang et al., **"Super 8 Languages for Making Movies"** (ICFP 2017) — declarative compositing as a pure-functional DSL. http://www.ccs.neu.edu/home/stchang/pubs/acm-icfp17.pdf
- Nehab et al., **"Accelerating Real-Time Shading with Reverse Reprojection Caching"** (GH 2007) — temporal caching foundation. https://gfx.cs.princeton.edu/pubs/Nehab_2007_ARS/NehEtAl07.pdf
- OBS Studio source architecture documentation — https://docs.obsproject.com/reference-sources
- Unreal Engine **Render Dependency Graph** documentation — https://dev.epicgames.com/documentation/en-us/unreal-engine/render-dependency-graph-in-unreal-engine
- Bevy **render architecture walkthrough** — https://github.com/bevyengine/bevy/discussions/9897
