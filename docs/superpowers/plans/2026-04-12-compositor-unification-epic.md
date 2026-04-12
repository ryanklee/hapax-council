# Compositor Unification Epic

> **For agentic workers:** This is the master organizing epic for the Source+Surface+Assignment migration. Each phase produces 1-4 PRs. Phases with approved specs in `docs/superpowers/specs/` can be executed via `superpowers:subagent-driven-development`. Phases without specs need `superpowers:brainstorming` first.

**Goal:** Migrate the hapax-council stream compositor from hardcoded layouts + duplicated rendering paths to a unified `Source + Surface + Assignment` model that makes content types pluggable and performant regardless of composition.

**Baseline:** As of 2026-04-12 the compositor is a working multi-content stream with 35 distinct content types, two independent pipelines (GStreamer → `/dev/video42`, wgpu → `hapax-visual/frame.jpg`), substantial duplicate code (5 Pango renderers, 5 image loaders, 3 YouTube paths), and 2 coexisting wgpu content backends (legacy `ContentTextureManager` + unified `ContentSourceManager`).

**Research foundation:** `docs/superpowers/research/2026-04-12-content-composition-architecture.md` — 695-line synthesis of codebase inventory, effect_graph analysis, wgpu content model, 25-system industry prior art, and 28-topic literature review.

---

## Epic structure

```
Phase 1: Cleanup & Unify (1-2 weeks)              [SAFE, REVERSIBLE]
  ├─ 1a: Delete dead code
  ├─ 1b: Unify wgpu content backends
  └─ 1c: Generalize @source:id in compiler

Phase 2: Source/Surface/Assignment data model (2-3 weeks)
  ├─ 2a: Pydantic schema + JSON layouts
  ├─ 2b: Extract phase (config → frame description)
  └─ 2c: Layout loader + hot-reload

Phase 3: Executor polymorphism (3-4 weeks)       [BIG]
  ├─ 3a: node.backend field in manifests
  ├─ 3b: Cairo backend
  ├─ 3c: Text backend (unified Pango)
  └─ 3d: Image_file backend (unified loader)

Phase 4: Compile phase improvements (2-3 weeks)
  ├─ 4a: Dead-source culling
  ├─ 4b: Version counters + cache boundaries
  └─ 4c: Transient texture pooling

Phase 5: Multi-output support (1-2 weeks)
  ├─ 5a: Relax single-output constraint
  └─ 5b: Unify GStreamer + wgpu under one model

Phase 6: Plugin system (2-3 weeks)
  ├─ 6a: Plugin directory + discovery
  ├─ 6b: Manifest validation
  └─ 6c: Reference plugin (clock widget)

Phase 7: Budget enforcement (1-2 weeks, optional)
  ├─ 7a: Per-source frame-time accounting
  └─ 7b: Skip-if-over-budget with fallback
```

**Total estimated effort:** 12-19 weeks.

**Critical path:** Phase 1 → Phase 2 → Phase 3 → Phase 5. Phases 4, 6, 7 can overlap or be deferred.

**Branch strategy:** Each phase gets its own epic branch (`epic/compositor-phase-{N}`). Each sub-phase gets a feature branch off the epic branch. PRs merge into epic branch; epic branch merges into main at phase completion.

This matches beta's Hermes 3 70B migration pattern — large multi-PR work on a long-lived epic branch with CI green at every merge to main.

---

## Phase 1: Cleanup & Unify

**Duration:** 1-2 weeks
**Risk:** Low
**Branches:** `epic/compositor-phase-1` → `feat/phase-1a-dead-code`, `feat/phase-1b-content-unify`, `feat/phase-1c-source-refs`
**Dependencies:** None — this is the entry point.

### Purpose

Reduce the surface area the next phases have to preserve. Delete dead code, collapse duplicate infrastructure, and establish a single content protocol on the wgpu side. Every change in this phase is self-contained and reversible — no architectural commitments yet.

### Tasks

#### 1a: Delete dead code

Identified dead paths from the research inventory (verify each before deletion):

| # | Path | Size | Why dead |
|---|------|------|----------|
| 1 | `agents/studio_compositor/visual_layer.py::render_visual_layer` + helpers | ~200 lines | No call site in `overlay.py::on_draw` |
| 2 | `agents/studio_compositor/fx_chain.py::YouTubeOverlay` + `PIP_EFFECTS` dict | ~250 lines | `_pip_draw` only calls `_album_overlay` and `_token_pole` |
| 3 | `agents/studio_compositor/pipeline.py::_add_camera_fx_sources` | ~50 lines | Disabled via comment, causes caps deadlock |
| 4 | `agents/studio_compositor/director_loop.py::_call_llm`, `_tick_playing`, `_tick_chat`, `_tick_vinyl`, `_tick_study` | ~400 lines | Only `_call_activity_llm` is called from `_loop`; the rest are legacy |
| 5 | `spawn_confetti` reference at `director_loop.py:417` | 1 line | Method not defined on `VideoSlotStub` — would AttributeError |
| 6 | `SpirographReactor` references (should be 0) | Audit | Replaced by SierpinskiLoader in PR #644 |
| 7 | `ReactorOverlay` type references (should be 0 or documented) | Audit | Never defined as a real type |

**Acceptance:** Dead code deleted. `uv run ruff check .` and `uv run pyright` clean. Compositor still runs and produces the same visual output.

**Scope:** Don't delete code that "might" be used. If a function is referenced anywhere, keep it for now. If a function is referenced only by other dead functions (transitive), delete the whole island.

#### 1b: Unify wgpu content backends

Delete `ContentTextureManager` + `slots.json` + `SierpinskiLoader._update_manifest`. Migrate to the unified `ContentSourceManager` protocol (`/dev/shm/hapax-imagination/sources/*/`).

Migration:
- `scripts/youtube-player.py` gains a write path to `/dev/shm/hapax-imagination/sources/yt-{0,1,2}/frame.rgba` with a matching manifest.json. Or: `SierpinskiLoader` is refactored to be a pure poller that reads yt-frame JPEGs and writes to the source protocol (zero-copy: symlink instead of copy).
- `ContentTextureManager` struct, `content_textures.rs`, and all references in `dynamic_pipeline.rs` and `main.rs` removed.
- The precedence logic in `dynamic_pipeline.rs:1124-1130` (source vs textures) simplifies to just source lookup.
- Bind group construction loses the `content_textures: Option<...>` parameter.
- The fade state machine in ContentTextureManager (continuation vs non-continuation fade, fragment_id tracking) is retired. ContentSourceManager uses linear fade per source, which is simpler and already live in the running system.

**Risk:** The fade behavior changes. Today ContentTextureManager has "fade-out → 500ms gap → fade-in" for non-continuation transitions; ContentSourceManager has linear per-source fades. Visual difference at transitions.

**Mitigation:** The live system already prefers ContentSourceManager when any source has opacity > 0.001. In practice the legacy path is already shadowed whenever affordance-recruited content is active. The non-continuation fade path is exercised only when fragment_id changes, which doesn't happen in the current SierpinskiLoader (fragment_id is hardcoded to `"sierpinski-yt"`). So the user-visible change is zero.

**Acceptance:** `ContentTextureManager` and all references deleted. `content_textures.rs` deleted. Live stream continues without visual regression. Content flows through `ContentSourceManager` exclusively.

#### 1c: Generalize `@source:id` in the compiler

Currently `wgsl_compiler.py:127-129` has a hardcoded tuple of node types that opt into content slot injection (`content_layer`, `sierpinski_content`). Generalize to a `requires_content_slots: bool` field in the node manifest JSON. Any node can opt in by setting this flag.

Similarly, the Rust bind group construction in `dynamic_pipeline.rs:1095-1130` has hardcoded logic for `content_slot_*` inputs. Generalize to match: any node pass with `requires_content_slots: true` in its plan entry gets the content slot bind group layout.

This is a small change but unlocks the Phase 3 executor polymorphism — new content-bearing shader nodes can be added without compiler changes.

**Acceptance:** `wgsl_compiler.py` no longer has hardcoded node type tuples for content slots. Node manifests declare `requires_content_slots: bool` (default false). Adding a new content-aware shader is a JSON edit, not a Python code change.

### PR breakdown

- **PR A** (`feat/phase-1a-dead-code`): Dead code deletion. ~900 line reduction. Low risk.
- **PR B** (`feat/phase-1b-content-unify`): Content backend unification. ~500 line reduction. Medium risk (visual behavior might diverge slightly).
- **PR C** (`feat/phase-1c-source-refs`): Generalize content slot opt-in. ~50 line change. Low risk.

Each PR merges into `epic/compositor-phase-1`. When all three merge, `epic/compositor-phase-1` merges into main.

---

## Phase 2: Source/Surface/Assignment data model

**Duration:** 2-3 weeks
**Risk:** Medium (introduces new abstractions but doesn't replace any yet)
**Branches:** `epic/compositor-phase-2` → `feat/phase-2a-schema`, `feat/phase-2b-extract`, `feat/phase-2c-layout-loader`
**Dependencies:** Phase 1 complete (reduced surface area).

### Purpose

Define the core data model. Validate it by writing the current layout as a JSON file. Don't migrate any rendering code yet — just have the model exist and be usable alongside the existing code.

### Tasks

#### 2a: Pydantic schema for Source/Surface/Assignment

Create `shared/compositor_model.py` with Pydantic models:

```python
class SourceSchema(BaseModel):
    id: str
    kind: Literal["camera", "video", "shader", "image", "text", "cairo",
                  "external_rgba", "ndi", "generative"]
    backend: str                    # dispatcher key
    params: dict[str, Any] = {}     # free-form per-backend
    update_cadence: Literal["always", "on_change", "manual", "rate"] = "always"
    rate_hz: float | None = None    # required if cadence == "rate"
    tags: list[str] = []

class SurfaceGeometry(BaseModel):
    kind: Literal["rect", "tile", "masked_region", "wgpu_binding",
                  "video_out", "ndi_out"]
    # Kind-specific geometry fields
    x: int | None = None
    y: int | None = None
    w: int | None = None
    h: int | None = None
    # For masked_region, a reference to a mask shape
    mask: str | None = None
    # For wgpu_binding, the binding name
    binding_name: str | None = None

class SurfaceSchema(BaseModel):
    id: str
    geometry: SurfaceGeometry
    effect_chain: list[str] = []   # ordered list of effect node IDs
    blend_mode: Literal["over", "plus", "in", "out", "atop"] = "over"
    z_order: int = 0
    update_cadence: Literal["always", "on_change", "manual"] = "always"

class Assignment(BaseModel):
    source: str  # source ID
    surface: str  # surface ID
    transform: dict[str, float] = {}  # optional per-assignment transform
    opacity: float = 1.0
    per_assignment_effects: list[str] = []  # additional effects

class Layout(BaseModel):
    name: str
    description: str = ""
    sources: list[SourceSchema]
    surfaces: list[SurfaceSchema]
    assignments: list[Assignment]
```

Add JSON serialization with schema validation. Write one unit test that round-trips the garage door layout through the types.

#### 2b: Extract phase implementation

Create `agents/studio_compositor/extract.py`:

```python
@dataclass(frozen=True)
class FrameDescription:
    """Immutable snapshot of compositor state for one frame.

    Produced by Extract phase, consumed by the render graph compiler.
    """
    timestamp: float
    layout: Layout
    source_frames: dict[str, bytes | None]  # source_id → latest frame bytes
    source_versions: dict[str, int]          # source_id → version counter
    shared_uniforms: SharedUniforms
```

The Extract phase is called once per render frame. It:
1. Locks the layout store (read lock, not write)
2. Walks every source in the layout, asks it for the latest buffer and current version
3. Releases the lock
4. Returns the immutable FrameDescription

The contract: after Extract returns, the FrameDescription is safe to pass to any thread; the layout store can be mutated freely on the config thread.

#### 2c: Layout loader + hot-reload

Create `agents/studio_compositor/layout_loader.py`:

```python
class LayoutStore:
    """Holds the current Layout. Watches a directory for JSON files.

    Hot-reload on mtime change. Active layout set by name via set_active(name).
    """
    def __init__(self, layout_dir: Path)
    def get_active(self) -> Layout
    def set_active(self, name: str) -> None
    def list_available(self) -> list[str]
```

Layouts live at `~/.config/hapax-compositor/layouts/*.json`. The current garage door layout is written as `garage-door.json` using the new schema. The compositor boots with `garage-door` as the default active layout.

**But** — at this phase, no rendering code reads the layout yet. The layout store exists, the FrameDescription is produced each frame, but the old rendering code runs alongside it. This is intentional: the schema and Extract machinery need to be validated before anything depends on them.

### PR breakdown

- **PR A** (`feat/phase-2a-schema`): Pydantic model + unit tests + the first layout JSON. ~600 lines added.
- **PR B** (`feat/phase-2b-extract`): Extract phase + FrameDescription + per-frame snapshot logic. ~400 lines added.
- **PR C** (`feat/phase-2c-layout-loader`): LayoutStore + mtime watcher + loading the garage door layout at startup. ~300 lines added.

### Acceptance

- `shared/compositor_model.py` defines Source/Surface/Assignment/Layout.
- `garage-door.json` layout exists at `~/.config/hapax-compositor/layouts/garage-door.json` and round-trips through the schema cleanly.
- `agents/studio_compositor/layout_loader.py::LayoutStore` loads it at startup.
- `agents/studio_compositor/extract.py::extract_frame_description()` produces FrameDescription objects per frame (verified via log output).
- No existing rendering code is modified. Visual output unchanged.

---

## Phase 3: Executor polymorphism

**Duration:** 3-4 weeks
**Risk:** High (touches the rendering path directly)
**Branches:** `epic/compositor-phase-3` → `feat/phase-3a-backend-field`, `feat/phase-3b-cairo`, `feat/phase-3c-text`, `feat/phase-3d-image`
**Dependencies:** Phase 1 complete (clean surface area), Phase 2 complete (data model exists).

### Purpose

Extend `effect_graph` so nodes can have different backend types — not just WGSL shaders. This is the single most important change — it promotes `effect_graph` from "GPU shader graph" to "content + effects graph."

### Tasks

#### 3a: `backend` field in node manifests

Add a `backend` field to `agents/shaders/nodes/*.json`. Default existing nodes to `"wgsl_render"`. The compiler reads this field and dispatches to a backend-specific code path.

The Python side (`wgsl_compiler.py`) already writes `plan.json`; it just needs to include `backend` in each pass. The Rust side (`dynamic_pipeline.rs`) needs a backend dispatch table — today it unconditionally treats every pass as a wgpu render pipeline.

For this sub-phase, the dispatch table has one entry: `wgsl_render`. Backends are added in the subsequent sub-phases.

**Acceptance:** Every node manifest has a `backend` field. Plan.json passes include the backend. The Rust executor reads the backend and dispatches (even though there's only one backend). Existing visual output unchanged.

#### 3b: Cairo backend

Add a `cairo` backend. A Python callback produces a Cairo `ImageSurface`; a bridge uploads to a wgpu texture via the source protocol.

Two stages:
1. **Rust side:** `cairo` backend means "look up this source's latest frame in ContentSourceManager, bind it as a texture, pass it through to the next stage." This is a no-op for the shader pipeline — the Cairo content has already been uploaded via the source protocol before the pass runs.
2. **Python side:** Cairo-rendering sources (SierpinskiRenderer, OverlayZones, AlbumOverlay, TokenPole) are refactored to implement a common `CairoSource` protocol. Each provides a `render(cr, canvas_w, canvas_h, t, state) -> None` method. A `CairoSourceRunner` wraps them, runs at the declared cadence in a background thread, and writes the result via `inject_rgba` to the source protocol.

After this sub-phase, Sierpinski, Pango zones, AlbumOverlay, and TokenPole are all registered as Cairo-backend sources. They're dispatched through the same machinery. The duplicate Pango renderer code consolidates into a shared `_pango_render` helper.

**Acceptance:** SierpinskiRenderer, OverlayZones, AlbumOverlay, TokenPole are all Cairo-backend sources. Visual output unchanged. Duplicate Pango code (5 → 1) and duplicate image loaders (5 → 1) are gone.

#### 3c: Text backend

Add a `text` backend for Pango-rendered text. A text source has params `(text, font, size, color, outline, width, height, wrap, align)`. The backend uses the shared `_pango_render` helper (consolidated in 3b) and re-renders when the content hash changes (on_change cadence).

Migrates: the "text zone" in OverlayZones, the AlbumOverlay attribution text, the YouTubeOverlay attribution, the TokenPole text fields, the imagination source protocol text rendering in `agents/imagination_source_protocol.py::_render_text_to_rgba`.

**Acceptance:** All text rendering uses the `text` backend. Visual output unchanged. Five duplicate Pango code paths collapsed into one.

#### 3d: Image_file backend

Add an `image_file` backend. A PNG/JPEG is loaded from disk with mtime caching and a single shared decoder path. The Vitruvian Man, album cover, folder overlay PNGs, and any other static image sources use this backend.

Migrates: TokenPole's PNG load, AlbumOverlay's cairo.create_from_png, OverlayZone's `_load_image`, SierpinskiRenderer's GdkPixbuf decode, ContentCapabilityRouter's PIL decode.

**Acceptance:** All image loading uses the `image_file` backend. Visual output unchanged. Five duplicate image loader paths collapsed into one.

### PR breakdown

- **PR A** (`feat/phase-3a-backend-field`): Add `backend` field to manifests, Rust dispatch table, no behavior change. ~300 lines.
- **PR B** (`feat/phase-3b-cairo`): Cairo backend + migration of 4 Cairo-rendering sources. ~800 lines.
- **PR C** (`feat/phase-3c-text`): Text backend + migration of 5 Pango renderers into one. ~500 lines, ~700 lines deleted.
- **PR D** (`feat/phase-3d-image`): Image backend + migration of 5 image loaders into one. ~400 lines, ~500 lines deleted.

### Acceptance

- Every non-shader content source in the codebase is dispatched through a unified backend mechanism.
- Duplicate rendering code (Pango, image load, Cairo surface management) is eliminated.
- The running compositor produces byte-for-byte identical output (same layouts, same timing).
- Adding a new content type is a `plugins/{name}/source.py` file + a manifest, not a Python code change in `studio_compositor/`.

---

## Phase 4: Compile phase improvements

**Duration:** 2-3 weeks
**Risk:** Medium
**Branches:** `epic/compositor-phase-4` → `feat/phase-4a-culling`, `feat/phase-4b-versions`, `feat/phase-4c-pooling`
**Dependencies:** Phase 3 complete (backend system exists).

### Purpose

Add the render graph compiler's performance-critical passes — dead source culling, version-based caching, transient texture pooling. This is where "performance regardless of content" actually happens.

### Tasks

#### 4a: Dead-source culling

After Extract produces the FrameDescription, walk backward from the assigned surfaces. Any source whose output is not reachable by any surface is skipped this frame.

This makes hidden cameras free. Sierpinski-not-active = all its sources skipped. Invisible text zones = no Pango render. Per-frame behavior adapts to the active layout without explicit "is visible" checks in source code.

Implementation: BFS from each surface's source references, mark reachable sources, skip unreachable.

#### 4b: Version counters + cache boundaries

Every source exposes a `version: int` counter that increments whenever its output would change. For shader sources, version bumps when any modulated param changes. For image sources, version bumps on mtime change. For text sources, version bumps on content hash change. For camera sources, version bumps every frame (content is always new).

The compiler diffs each source's current version against the previous frame's version. Unchanged sources have their previous frame's texture reused — no re-render, no upload, no pass execution.

Combined with dead-source culling, this gives free graceful degradation: if 80% of your content didn't change this frame, you do 20% of the work.

#### 4c: Transient texture pooling

Intermediate textures (effect chain outputs, non-final pass results) are allocated from a frame-local pool keyed by descriptor (width, height, format, usage). When a pass needs a texture with a given descriptor, it pops one from the pool if available, or allocates fresh. At frame end, all pool entries are returned and marked available for the next frame.

Not full render-graph aliasing (which requires declared read/write sets and barrier synthesis — too invasive for the current Rust executor). But it prevents texture thrashing and gives most of the memory win at a fraction of the complexity.

### Acceptance

- Hidden cameras consume zero GPU work per frame (measured via nvidia-smi or profiling).
- Static text overlays are rendered once and reused across frames.
- Memory peaks are bounded regardless of how many effect chains are active.
- Compositor total GPU memory usage is within 50% of the theoretical optimum.

---

## Phase 5: Multi-output support

**Duration:** 1-2 weeks
**Risk:** Medium-high (touches graph compiler and Rust pipeline)
**Branches:** `epic/compositor-phase-5` → `feat/phase-5a-multi-target`, `feat/phase-5b-unify-outputs`
**Dependencies:** Phase 4 complete.

### Purpose

Relax the single-output constraint so one frame description can produce multiple independent output targets (stream video + wgpu window + NDI out + thumbnail). This is the unification point for the two pipelines.

### Tasks

#### 5a: Relax single-output constraint

`agents/effect_graph/compiler.py:58-62` enforces exactly one `output` node. Relax to: multiple `output` nodes are permitted, each tagged with a target name. The compile emits a `targets: dict[str, list[ExecutionStep]]` instead of a flat `steps: list[ExecutionStep]`.

`wgsl_compiler.py` writes `plan.json` with:
```json
{"version": 2, "targets": {"main": {"passes": [...]}, "hud": {"passes": [...]}}}
```

The Rust `DynamicPipeline` reads targets, builds separate render passes for each, and the host decides which target's output to route where.

#### 5b: Unify GStreamer + wgpu under one model

Add `Surface(kind=video_out, id=obs-feed, target=gstreamer_video)` and `Surface(kind=video_out, id=wgpu-winit, target=wgpu_window)`. Both become targets in the compile phase.

The GStreamer compositor becomes a pure ingest layer — cameras, v4l2 sources, audio — producing textures that feed the wgpu compositor. The wgpu compositor produces the final frames that feed GStreamer's v4l2sink for `/dev/video42` output AND the winit window.

This is the longest-running change in this phase. It may need to happen as a series of smaller migrations where one content type at a time moves from GStreamer composition to wgpu composition, until the GStreamer side is pure ingest.

### Acceptance

- Plan.json format is v2 with `targets: {...}`.
- DynamicPipeline renders multiple targets per frame.
- One FrameDescription feeds both the OBS output and the wgpu window.
- Camera feeds are decoded once and visible in both outputs without duplication.

---

## Phase 6: Plugin system

**Duration:** 2-3 weeks
**Risk:** Low
**Branches:** `epic/compositor-phase-6` → `feat/phase-6a-discovery`, `feat/phase-6b-validation`, `feat/phase-6c-reference`
**Dependencies:** Phase 3 complete (backend system).

### Purpose

Formalize the plugin contract. A new content type becomes a directory with a manifest and lifecycle code. No central registry to edit.

### Tasks

#### 6a: Plugin directory + discovery

Plugins live at `plugins/{plugin_name}/` with:

```
plugins/my_source_type/
  manifest.json       # metadata + schema
  source.py           # Python lifecycle (init/tick/render/destroy)
  shader.wgsl         # optional WGSL if backend == wgsl_*
  README.md
```

On startup (and on file change in dev mode), scan the directory, load each manifest, register the source type, expose the schema to the UI. No import of Python modules unless the source type is actually instantiated (lazy load).

#### 6b: Manifest validation

Manifests are Pydantic-validated. Malformed manifests are logged and skipped, not crashed on. Schema introspection gives the operator UI typed form fields for parameters.

#### 6c: Reference plugin

Write the first third-party-shaped plugin: a clock widget that renders the current time as text. Demonstrates the end-to-end contract. Lives at `plugins/clock/`. A new operator can copy it as a template.

### Acceptance

- `plugins/` directory contains at least one reference plugin.
- Adding a new content type is a one-directory change, no Python code edits in `studio_compositor/`.
- Schema is auto-reflected into the operator UI.

---

## Phase 7: Budget enforcement (optional)

**Duration:** 1-2 weeks
**Risk:** Low
**Branches:** `epic/compositor-phase-7` → `feat/phase-7a-accounting`, `feat/phase-7b-skip-fallback`
**Dependencies:** Phase 4 complete.

### Purpose

Prevent expensive content from degrading the overall stream. Track per-source frame time; skip over-budget sources with a fallback.

### Tasks

#### 7a: Per-source frame-time accounting

Every source's render call is wrapped in a timer. Rolling average of the last N frames. Exposed as `source.last_frame_ms`, `source.avg_frame_ms`.

Aggregated stats published to `/dev/shm/hapax-compositor/source-costs.json` for observability.

#### 7b: Skip-if-over-budget with fallback

Each source has a `budget_ms` (default 5ms per frame). If last frame exceeded budget, skip this frame and use the cached texture from the previous frame. After N consecutive skips, fall back to a placeholder (black, or an error texture).

Exposes a `degraded_sources` count to stimmung so the system knows when it's running below spec.

### Acceptance

- Individual slow sources don't stall the whole compositor.
- Degraded sources are visible to the operator (logged + exposed to stimmung).
- Frame time stays within the target budget even under adversarial content.

---

## Cross-phase concerns

### Testing strategy

Each phase includes:
- **Unit tests** for new types and functions
- **Integration tests** validating the compositor still runs
- **Regression tests** verifying visual output (via fx-snapshot comparison)
- **Performance regression tests** tracking frame time percentiles

Phase 3 is the biggest risk for visual regression. It's validated by running the live system and comparing fx-snapshots against a pre-migration baseline. Small divergences (sub-pixel) are acceptable; structural differences are not.

### Documentation

Each phase adds or updates docs:
- Phase 1: deletion log (what was removed and why)
- Phase 2: `docs/compositor-model.md` (Source/Surface/Assignment data model reference)
- Phase 3: `docs/backend-plugins.md` (backend reference)
- Phase 5: `docs/multi-output.md` (multi-target render graph format)
- Phase 6: `docs/plugin-contract.md` (plugin directory layout + schema)

### Rollback plan

Every phase is designed to be reversible for 30 days after merge:
- Phase 1: git revert of the three deletion PRs.
- Phase 2: removing the layout_loader and extract instances (no rendering code depends on them yet).
- Phase 3: revert per sub-phase; the existing Python classes can be re-imported.
- Phase 4: revert the compile phase changes (pool, versioning, culling).
- Phase 5: revert multi-target plan format; v1 plans continue to work.
- Phase 6: delete `plugins/` dir + discovery code.
- Phase 7: delete budget accounting.

No cross-phase commits. Each PR is independently reversible.

### Measurement targets

Before Phase 1, capture baselines:
- Lines of code in `agents/studio_compositor/`
- Active content sources (per `fx-snapshot.jpg` inspection)
- Peak GPU memory (nvidia-smi)
- Frame time p50/p95/p99 (GStreamer + wgpu)
- CPU load average during steady-state stream

After each phase, re-measure. The targets:
- Phase 1: -10% LOC, no perf regression
- Phase 3: -25% LOC, no perf regression
- Phase 4: -30% peak GPU memory, +10% p95 frame time budget headroom
- Phase 7: p99 frame time within 2x p50 regardless of content

---

## Priority and sequencing

| Priority | Phase | Effort | Blocked By | Notes |
|----------|-------|--------|------------|-------|
| 1 | Phase 1 | ~1-2 weeks | Nothing | Entry point, low risk |
| 2 | Phase 2 | ~2-3 weeks | Phase 1 | Data model foundation |
| 3 | Phase 3 | ~3-4 weeks | Phase 2 | The big one |
| 4 | Phase 4 | ~2-3 weeks | Phase 3 | Performance substrate |
| 5 | Phase 5 | ~1-2 weeks | Phase 4 | Multi-output unification |
| 6 | Phase 6 | ~2-3 weeks | Phase 3 | Plugin system (can start earlier) |
| 7 | Phase 7 | ~1-2 weeks | Phase 4 | Optional, defer if needed |

Phase 6 can start as soon as Phase 3 completes — it doesn't need Phase 4 or 5. In practice, running 3+6 in parallel on two branches gets the most work done.

Phase 7 is optional. Defer if schedule is tight; revisit when expensive content starts causing frame drops.

---

## Parallel work / beta coordination

This epic is in alpha's workstream (governance, organelle, corpora, visual rendering). Beta's workstream (vocal/visual pipeline, perception, conversational behavior) is separate, so most of this work won't conflict with beta's concurrent development.

Potential conflict zones:
- `agents/hapax_daimonion/phenomenal_context.py` — beta may modify tier definitions. Phase 3 doesn't touch this but Phase 2 references it for modulation signal extraction.
- `shared/context.py` + `shared/context_compression.py` — used by the reactor enrichment (alpha) and by beta's prompt compression. Already stable; unlikely to conflict.
- `agents/effect_graph/modulator.py` — beta's SEEKING stance modulation lives here. Phase 4 adds per-source versioning which doesn't touch modulation.

Coordinate via relay status updates after each sub-phase merge. No direct file-level conflicts expected.

---

## Risks and mitigations

### High-risk: Phase 3 (executor polymorphism)

**Risk:** Backend dispatch is wrong, content renders to the wrong place, visual output diverges.

**Mitigation:** Phase 3 ships in 4 sub-phases with one backend per PR. Each sub-phase is validated against fx-snapshot baseline before the next is merged. If visual regression occurs at any sub-phase, rollback is one PR revert.

**Fallback:** If executor polymorphism proves too invasive for the current Rust pipeline, the alternative is "Python renders everything, writes to source protocol, Rust only does WGSL." The source protocol already supports arbitrary RGBA content. Phase 3 becomes "unify all Python backends behind one abstraction" without touching Rust. Sacrifices some latency but preserves the architecture.

### Medium-risk: Phase 5 (multi-output)

**Risk:** Plan.json v2 format breaks existing preset files.

**Mitigation:** v1 plans are automatically wrapped into v2 format at load time (`{"targets": {"main": {"passes": <v1 passes>}}}`). All existing presets continue to work.

### Low-risk: Phases 1, 2, 6, 7

These phases are additive (or pure deletion with no replacement). Risk is primarily test coverage.

---

## Success criteria (epic-level)

At the end of this epic:

1. **A new content type is a `plugins/{name}/` directory**, not a Python class in `studio_compositor/`.
2. **Adding a new layout is a JSON file**, not a code change.
3. **One content decode feeds all outputs** — camera feeds reach OBS and the wgpu window from a single decode.
4. **Cost scales with what's visible, not what's configured** — hidden cameras do zero work, static overlays render once.
5. **The effect_graph is the one rendering abstraction** — no parallel Cairo-only, Pango-only, image-only, or shader-only pipelines.
6. **Visual output is unchanged** across the migration (or deliberately improved in specific, documented ways).

The operator's day-to-day experience should improve: layouts are easier to design, new content types are easier to write, the system runs lighter, and nothing unexpected breaks.
