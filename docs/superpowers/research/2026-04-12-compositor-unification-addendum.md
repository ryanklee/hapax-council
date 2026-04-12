# Compositor Unification Research Addendum

**Date:** 2026-04-12
**Parent:** `docs/superpowers/research/2026-04-12-content-composition-architecture.md`
**Purpose:** Capture findings from the 5 parallel research streams that informed the Phase 1 spec and the 7-phase epic.

This addendum preserves the key findings that are too detailed for the epic plan but too important to lose. Five parallel research agents investigated loose ends from the main architecture research synthesis.

---

## 1. Shared memory streaming (Python → Rust at 30-60 fps)

**Verdict:** Use **iceoryx2** with Python+Rust bindings.

### Why iceoryx2 wins

iceoryx2 v0.7 (Sept 2025) shipped Python bindings via PyO3 directly on the Rust core — no C intermediate. v0.8 hardened cross-language memory-layout-compatible data types. The key API for streaming: `publisher.loan_slice_uninit(n_bytes)` returns a writable sample backed by shared memory. Populate it via the Python buffer protocol, then `sample.send()`. On Rust side, `subscriber.receive()` returns a zero-copy slice into the same shared memory page.

**Latency breakdown for 1080p RGBA:**
- Python render into shared slice (PIL/Cairo): 2-10ms (unavoidable, domain cost)
- iceoryx2 send: < 1ms
- Rust subscriber receive: < 100µs (pointer swap)
- wgpu `write_texture` CPU→GPU: 2-5ms (via StagingBelt)
- **Total: 7-20ms per source** at 1080p60

**Measured in the wild:**
- iceoryx iceperf: 240ns for a 64KB publish-subscribe hop
- ROS2 with CycloneDDS+iceoryx: 1.4ms → 0.3ms for 1MB images

### Install + API sketch

```
pip install iceoryx2
# Rust: iceoryx2 = "0.8" in Cargo.toml
```

Producer (Python):
```python
import iceoryx2 as ix2
service = ix2.Service.pub_sub("logos/sources/text-overlay").create()
publisher = service.publisher_builder().create()

# Per frame:
sample = publisher.loan_slice_uninit(width * height * 4)
# Render directly into sample.payload() via PIL or Cairo
img = Image.frombuffer("RGBA", (width, height), sample.payload(), "raw", "RGBA", 0, 1)
draw_into(img)
sample.send()
```

Consumer (Rust):
```rust
let service = Service::pub_sub("logos/sources/text-overlay").open()?;
let subscriber = service.subscriber_builder().create()?;
// Per frame:
if let Some(sample) = subscriber.receive()? {
    let pixels: &[u8] = sample.payload();
    queue.write_texture(&texture, pixels, layout, size);
}
```

### Alternatives considered and rejected

- **Raw mmap + atomic frame index** (approach #1): works but requires designing the memory ordering yourself. ~150 lines Python + ~200 lines Rust. Cross-language atomic semantics are portable only on x86 in practice.
- **dma-buf / GPU sharing**: Cairo's GL backend removed in 2022-2023. PIL has no GPU path. NVIDIA won't import foreign dma-bufs. Not viable.
- **tmpfs + mtime polling** (current approach): adds ~10ms latency per frame. Can't handle 30+ fps efficiently.
- **nng / nanomsg / Arrow IPC**: all involve a 5-10ms copy and don't help.

### Apply to hapax

**When needed:** Phase 3 backend polymorphism. Currently the Python content injector uses tmpfs + manifest.json + polling (acceptable for on-change content at 1-5 Hz). When we need 30+ fps Python-rendered content, iceoryx2 is the path.

**Start simple:** Keep the current file-based source protocol for Phase 1-2. Introduce iceoryx2 in Phase 3 as a new `iceoryx_rgba` backend type, alongside the existing `shm_rgba` backend. Sources declare which to use in their manifest. Gradual migration, not big-bang.

**Estimated effort:** 1 week to wire iceoryx2 as a new content backend (2 days for the Rust subscriber integration into `ContentSourceManager`, 2 days for a Python publisher helper, 3 days for validation + one reference source).

**Key references:**
- [iceoryx2 Python examples](https://github.com/eclipse-iceoryx/iceoryx2/tree/main/examples/python)
- [iceoryx2 v0.7.0 release announcement](https://ekxide.io/blog/iceoryx2-0-7-release/)

---

## 2. Multi-output render graph patterns

**Verdict:** Adopt **Bevy's camera-driven subgraph model**. Critical discovery: the hapax Rust side already supports named output textures — only the Python compiler's `exactly one output node` assertion is the barrier.

### Current hapax state (the critical finding)

`dynamic_pipeline.rs` already has `PlanPass.output: String` as a named string, defaulting to `"final"`. The texture pool is `HashMap<String, PoolTexture>`. The single-target constraint is NOT in the texture pool — it's in:
1. `agents/effect_graph/compiler.py:58-62` — hard assertion `exactly one output node`
2. Six hardcoded references to `textures.get("final")` in `dynamic_pipeline.rs` lines 289, 821, 863, 1104, 1129, 1142, 1147, 1192

**This dramatically lowers the cost of Phase 5.** We are not rewriting a render graph; we are lifting a single assertion and generalizing a sink resolver.

### Bevy's model (recommended)

`ExtractedCamera` carries `target` + `render_graph` + `order`:
```rust
pub struct ExtractedCamera {
    pub target: Option<NormalizedRenderTarget>,
    pub render_graph: Interned<dyn RenderSubGraph>,
    pub order: isize,
    // ...
}

pub enum NormalizedRenderTarget {
    Window(NormalizedWindowRef),
    Image(Handle<Image>),
    TextureView(ManualTextureViewHandle),
}
```

`CameraDriverNode` is the root-graph node that collects all cameras, sorts by `(target, order)`, and calls `run_sub_graph(camera.render_graph, inputs=[view_entity])` for each.

### Proposed hapax format for multi-target plan.json

Minimum-disruption generalization: promote `"output"` from a single hardcoded sink to named target nodes with per-target sink metadata:

```json
{
  "name": "Reverie Multitarget",
  "transition_ms": 2000,
  "nodes": {
    "cam_desk":  {"type": "camera_decode", "params": {"device": "c920-desk"}},
    "fx_bloom":  {"type": "bloom", "params": {...}},
    "fx_grade":  {"type": "colorgrade", "params": {...}},
    "letterbox": {"type": "letterbox_1080", "params": {}},
    "downscale": {"type": "downscale", "params": {"w": 1280, "h": 720}},

    "out_stream":  {"type": "target", "sink": "v4l2",  "size": [1920, 1080], "priority": 0},
    "out_overlay": {"type": "target", "sink": "winit", "size": [1920, 1080], "priority": 10},
    "out_ndi":     {"type": "target", "sink": "ndi",   "size": [1280, 720],  "priority": 20}
  },
  "edges": [
    ["cam_desk", "fx_bloom"],
    ["fx_bloom", "fx_grade"],
    ["fx_grade", "letterbox"],
    ["letterbox", "out_stream"],
    ["letterbox", "out_overlay"],
    ["fx_grade", "downscale"],
    ["downscale", "out_ndi"]
  ],
  "modulations": [],
  "layer_palettes": {}
}
```

Shared upstream (`cam_desk → fx_bloom → fx_grade`) is referenced three times. The compiler's backward walk naturally unions them; each node compiles once. This is the "share by node-id" CSE pattern from ML compilers.

### Required code changes

1. **`agents/effect_graph/types.py`**: `NodeInstance.kind: Literal["effect", "target"] = "effect"`, add `sink: dict | None`.
2. **`agents/effect_graph/compiler.py:58-62`**: replace `output_count != 1` with `target_count >= 1`. Emit `ExecutionPlan.targets: list[TargetPlan]` where each target carries sink metadata + its subset of steps.
3. **`hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs`**: `PlanPass.output` stays as a named string. Add a `targets: Vec<TargetInfo>` field to `PlanFile`. The six `textures.get("final")` call sites become target-aware lookups.
4. **Python plan emitter**: output a `targets` array in plan.json.

### wgpu multi-encoder constraint

**Important discovery from the research:** wgpu has a known issue (#5663) where you cannot create more than one `CommandEncoder` referencing views from the same surface texture. Workaround: one encoder per surface, shared via a single device. For hapax, this means:

```
frame():
    let mut enc = device.create_command_encoder(...);
    // all shared upstream passes write to pooled textures
    run_passes(enc, shared_passes)
    // per-target tail passes write to offscreen textures
    run_passes(enc, target_passes["stream_1080"])    // -> v4l2
    run_passes(enc, target_passes["ndi_720"])         // -> NDI
    run_passes(enc, target_passes["thumb_360"])       // -> JPEG
    queue.submit([enc.finish()])

    // THEN for the winit overlay window (only surface involved):
    let win_tex = window_surface.get_current_texture()?;
    let mut win_enc = device.create_command_encoder(...);
    blit_to_surface(win_enc, final_texture, win_tex);
    queue.submit([win_enc.finish()]);
    win_tex.present();
```

Single encoder for all offscreen targets, separate encoder for the surface. Matches existing `DynamicPipeline::frame()` structure.

**Apply to hapax:** Phase 5 spec should incorporate this pattern. The `out_overlay` target (winit window) gets its own encoder; everything else shares one.

### Why not Unreal RDG or Frostbite

- **Unreal RDG**: rich `RegisterExternalTexture` + view families model, but the full pattern requires a 5-week implementation effort. Overkill for hapax's current needs.
- **Frostbite**: imperative `AddCallbackPass` with lambdas. Requires setup/execute split that doesn't match Python+Rust split.
- **Granite**: single `set_backbuffer_source(name)` is the anti-pattern we're moving away from — it's what hapax has today.

Bevy's camera+subgraph model is the closest fit at the lowest cost.

---

## 3. wgpu dma-buf zero-copy on Linux/NVIDIA

**Verdict:** **Not viable on the current stack.** Ship the staging buffer copy path first; reserve zero-copy for when profiling shows a bottleneck.

### The two blockers

1. **UVC kernel driver** (all C920/BRIO cameras) cannot produce usable dma-bufs. Even with `io-mode=dmabuf`, UVC builds frames from USB packets in CPU-mapped memory; cache flushes are wrong, output is garbage.
2. **NVIDIA's proprietary driver** `VK_EXT_external_memory_dma_buf` only accepts dma-bufs whose backing memory originated from the NVIDIA driver itself. Cannot import foreign dma-bufs from v4l2, vaapi, intel, or amdgpu. Long-standing, deliberate limitation.

### The staging buffer reality

At 6 cameras × 1080p30:
- **249 MB/s** upload bandwidth needed per camera
- PCIe 3.0 x16 delivers ~16 GB/s (1.5% utilization per camera)
- Memcpy on Ryzen 5800XT DDR5 at ~20 GB/s → **~0.4 ms per frame per camera**, fully pipelined
- 6 cameras aggregate: ~2.4 ms CPU copy cost per frame

**This is not a bottleneck.** The ginokent blog post on wgpu video pipelines measures 249 MB/s at 1080p30 baseline; StagingBelt improves this for high-frequency cases. The hapax use case is well within the staging path's envelope.

### Optimization knobs that matter

1. **Reuse textures** — `create_texture` once, `write_texture` every frame. Never recreate.
2. **Upload NV12 directly** as two R8/RG8 plane textures; do YUV→RGB in a shader. `nvjpegdec` already outputs NV12; keep it.
3. **`COPY_DST | TEXTURE_BINDING`** only (no RENDER_ATTACHMENT) on upload-only textures — saves a layout transition.
4. **CUDA host-pinned memory** — `cudaMallocHost` for the appsink buffer. Pinned memory is ~2× faster than pageable for CPU→GPU copy.
5. **Ring of 2-3 staging buffers** indexed by frame slot. Upload and sample can overlap.

### When to revisit zero-copy

Don't pursue dma-buf on NVIDIA. If the copy cost becomes a bottleneck (60+ fps composition, 12+ camera layouts, 4K support), the correct next move is **CUDA-Vulkan OPAQUE_FD interop** — the same path documented in the 2026-03-16 CUDA-GL interop investigation memo. That's a ~4-8 week effort and requires custom C/Rust GStreamer plugins. Not urgent.

### wgpu PR #9366 — the new dma-buf API

**Merged 2 days ago (2026-04-09), not yet in any release.** Adds `texture_from_dmabuf_fd` to wgpu-hal Vulkan. Uses `VK_EXT_image_drm_format_modifier` and `VK_EXT_external_memory_dma_buf`. Single-plane only (NV12 multi-plane NOT supported — hard blocker for nvjpegdec NV12 output).

Bookmark for the future. If hapax ever moves cameras to libcamera-native sources (Pi IR fleet → CSI, or a vaapi decoder loop), this is the API to use.

### Apply to hapax

**Phase 5 sub-phase decision:** When unifying GStreamer ingest → wgpu compositing, use the staging buffer path with the optimizations above. Do not block on zero-copy. Budget: 3 days for the wiring, 2 days for benchmarking.

---

## 4. ContentTextureManager deletion impact

**Verdict:** Migration is cleaner than expected. The Rust `content_sources` precedence logic is already winning at runtime; ContentTextureManager is already shadowed in production. Deletion is "remove the shadowed-out path."

### Key findings

1. **Rust consumers:** Only 3 files touch `ContentTextureManager`: `content_textures.rs` (the module itself), `lib.rs` (pub mod), `dynamic_pipeline.rs` + `main.rs` (field, render args, bind group fork). No tests, no other files. Clean removal.

2. **Python writers of `slots.json`:** Three.
   - `SierpinskiLoader._update_manifest` — YouTube path, always `continuation: true`
   - `imagination_resolver.write_slot_manifest` — called alongside `write_source_protocol()` (both backends run in parallel today)
   - `scripts/smoke_test_reverie.py::write_manifest` — test helper

3. **The gap-fade code path is unused for the YouTube path.** SierpinskiLoader hardcodes `fragment_id: "sierpinski-yt"` and `continuation: true`. The fade-out → 500ms gap → fade-in sequence is only exercised by `imagination_resolver` when fragment.continuation is false. But imagination_resolver ALSO writes via `write_source_protocol()`, and runtime evidence shows `ContentSourceManager` is already shadowing it.

4. **Dead payload:** `kind` and `material` fields in slots.json are not deserialized by Rust. `kind` is writer-side bookkeeping; `material` duplicates the uniform buffer entry at `signal.material`.

5. **VRAM impact:** `ContentTextureManager` allocates 4× 1080p Rgba8Unorm at startup (~32 MB), permanently. Deleting frees this unconditionally.

6. **Latency improvement:** ContentTextureManager polls `slots.json` at 500ms. `ContentSourceManager` scans `/dev/shm/hapax-imagination/sources/` at 100ms. 5× faster slot-update latency after migration.

### Migration order (from the impact analysis)

1. Wire new SierpinskiLoader to write via `inject_jpeg`. Run alongside legacy manifest writer for one session. Verify.
2. Stop writing slots.json from SierpinskiLoader.
3. Delete `write_slot_manifest()` from imagination_resolver. Remove the call.
4. Delete the 6 slot-manifest tests.
5. Port or delete `scripts/smoke_test_reverie.py`.
6. Rust changes (single PR): delete `content_textures.rs`, strip args from `render()` and `create_input_bind_group()`, simplify slot-view resolution to always use `content_sources`.

Each step is independently validatable. Rust changes can be deferred until Python is fully off the manifest path.

### Surprising discoveries

1. **`SierpinskiLoader.set_active_slot()` is dead code.** Defined in sierpinski_loader.py:108, never called externally. DirectorLoop manages rotation through `is_active` on slot stubs, not through the reactor overlay.

2. **`director_loop.py:417` calls `spawn_confetti` on VideoSlotStub** which doesn't define the method. Would AttributeError. Lives in `_tick_playing` which is documented dead.

3. **The `/dev/shm/hapax-imagination/content/` directory** is read only by `ContentTextureManager`. Once deleted, the directory is garbage.

---

## 5. Comprehensive dead code audit

**Verdict:** More dead code than expected. Total deletable: **~1,673 lines** (conservative floor ~1,154 if operator confirms).

### Audit findings by confidence

| # | Path | Lines | Risk |
|---|---|---:|---|
| 1 | `spirograph_reactor.cpython-*.pyc` (stale cache files) | 0 | None — cache cleanup |
| 2 | `visual_layer.py` + scaffolding in compositor.py, state.py, config.py | **153** | Low — standalone module |
| 3 | `fx_chain.py::YouTubeOverlay` class | **244** | Medium — shared file with live code |
| 4 | `director_loop.py` legacy methods (_tick_*, _call_llm, _build_reactor_context, _build_activity_prompt, _load_research_excerpt, path_position_for_slot) | **401** | Medium — large in-file removal |
| 5 | `pipeline.py::_add_camera_fx_sources` | 48 | None — module-local dead function |
| 6 | `random_mode.py` (whole module) | **99** | Low — verify operator not invoking manually |
| 7 | `effect_graph/temporal_slot.py::TemporalSlotState` + tests | 112 | Low — only tests import it |
| 8 | `effect_graph/wgsl_transpiler.py` offline funcs + tests (keep `extract_wgsl_param_names`) | **~420** | Low — keep one function |
| 9 | `reverie/content_injector.py` unused funcs (inject_image, inject_jpeg, inject_url, inject_search, _extract_web_text, remove_source) | **~185** | **CONFLICT** — Phase 1b needs `inject_jpeg` |
| 10 | `compositor.py` + `state.py` visual-layer scaffolding cleanup after #2 | ~8 | None |
| 11 | `fx_chain.py::_yt_overlay = None` + `compositor.py:118` bus filter | 10 | None |

### Critical finding for Phase 1b: inject_jpeg is "dead"

The content_injector audit found that `inject_jpeg` has no external callers TODAY. But Phase 1b depends on using `inject_jpeg` to migrate SierpinskiLoader off the slot manifest path. **Resolution:** In Phase 1b, we add the first caller (`sierpinski_loader.py`). The function stays — it has a caller now. Update the audit to note that `inject_jpeg` is kept because Phase 1b uses it.

Other "dead" functions in content_injector (inject_image, inject_url, inject_search, inject_rgba) can be deleted if operator confirms they're not part of any planned feature. Keep `inject_text` (used by `_content_resolvers.py` and `system_reader.py`) and `inject_jpeg` (added in Phase 1b). Delete the rest in Phase 1b or defer.

### Alive paths that I thought might be dead

- `overlay_parser.py` — alive, called by `overlay_zones.py`
- `overlay_zones.py::ZONES` — alive, 2 zones wired through the manager
- `wgsl_transpiler.py::extract_wgsl_param_names` — alive, called by `wgsl_compiler.py:108`
- `wgsl_compiler.py::compile_to_wgsl_plan` — alive, called by `reverie/_satellites.py` and `reverie/bootstrap.py`
- All `effect_graph` runtime types (`GraphRuntime`, `UniformModulator`, `GraphCompiler`, `ShaderRegistry`) — alive
- `effect_graph/capability.py::ShaderGraphCapability` — alive, used by `reverie/mixer.py`
- All `agents/shaders/nodes/*.frag` files — alive, loaded by `ShaderRegistry`
- `PIP_EFFECTS` dict in fx_chain.py — **alive**, used by `AlbumOverlay._fx_func` line 454 (not only by the dead `YouTubeOverlay`). **KEEP THIS WHEN DELETING YouTubeOverlay.**

### Updated Phase 1a scope

Given the audit, Phase 1a can delete more than initially scoped:

| Target | Lines | Decision |
|---|---|---|
| visual_layer.py + scaffolding | 153 | Delete (Phase 1a) |
| YouTubeOverlay class (NOT PIP_EFFECTS) | 244 | Delete (Phase 1a) |
| YouTubeOverlay vestige cleanups | 10 | Delete (Phase 1a) |
| director_loop legacy methods | 401 | Delete (Phase 1a) |
| _add_camera_fx_sources | 48 | Delete (Phase 1a) |
| **Phase 1a minimum** | **856** | |
| random_mode.py | 99 | Defer — needs operator check |
| temporal_slot.py + tests | 112 | Defer — separate PR |
| wgsl_transpiler.py offline funcs + tests | 420 | Defer — separate PR (Phase 1d?) |
| content_injector.py unused funcs (keep inject_jpeg) | ~130 | Defer — after Phase 1b adds inject_jpeg caller |
| **Phase 1a extended** | **1,617** | |

Recommendation: stick with Phase 1a minimum (856 lines) to keep the scope tight. The other items can be a Phase 1d "extended cleanup" PR after the three primary sub-phases complete, or folded into Phase 6 (plugin system) when content_injector is replaced by a registered plugin.

---

## Summary of actionable insights

| Research stream | Key actionable insight | Applies to |
|---|---|---|
| Shared memory streaming | iceoryx2 for Python→Rust 30+ fps; file protocol for <5 fps | Phase 3 backend system |
| Multi-output graphs | Bevy model; Rust side already supports named outputs; the barrier is the Python `exactly one output` assertion | Phase 5 |
| wgpu dma-buf | Not viable on NVIDIA+UVC; ship staging buffer path; CUDA-Vulkan interop is the future option | Phase 5 |
| ContentTextureManager deletion | Cleaner than expected; already shadowed at runtime; 6 tests to delete, 3 Python writers to migrate, 3 Rust files to update | Phase 1b |
| Dead code audit | ~1,673 lines deletable total; Phase 1a gets 856; rest in extended cleanup | Phase 1a (+ optional Phase 1d) |

---

## What I did NOT research yet

These remained out of scope for this round:

1. **Cairo source backend implementation** — how Python Cairo callbacks bridge to wgpu textures. Needs prototyping in Phase 3.
2. **Text backend font handling** — Pango vs Freetype+Rust, what stable font rendering in a Rust backend looks like. Phase 3.
3. **Plugin directory watcher** — how hot-reload of plugin manifests works across Python+Rust. Phase 6.
4. **NDI output integration** — how NDI sources are registered and how the compositor exposes its output as NDI. Phase 5 or 6.
5. **Per-source frame-time accounting mechanics** — where to hook the timer, how to aggregate, how to expose to stimmung. Phase 7.

These are deferred to the specs of their respective phases.
