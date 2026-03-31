# Studio & Effects Pipeline — Consolidation Spec

**Date:** 2026-03-31
**Author:** delta session
**Status:** Design approved
**Motivation:** The studio/effects pipeline reached production maturity across 7 days of intensive development (PRs #300-#477). No single normative spec captures the as-built system. Existing specs are phase-specific (Phase 1, Phase 2, Reverie, Dynamic Shader Pipeline) and sometimes contradict each other on counts, naming, and contracts. This consolidation freezes the implemented state as the authoritative reference and closes the remaining minor gaps.
**Supersedes:** 2026-03-25-effect-node-graph-design.md (Phase 1), 2026-03-26-effect-graph-phase2-design.md (Phase 2), 2026-03-29-dynamic-shader-pipeline-design.md (Phase 3), 2026-03-29-reverie-bachelard-design.md (Amendments), 2026-03-31-compositor-frontend-polish-design.md (Phase 4)

---

## Problem

1. **Spec fragmentation.** Six design specs and four implementation plans describe overlapping slices of the same system. No single document is authoritative for the as-built state.
2. **Count discrepancies.** Requirements doc says 54 nodes; registry loads 56. Frontend exposes 20 effect sources; backend has 30 presets. These are correct (categories differ) but undocumented.
3. **One truncated function.** `effects.py::switch_fx_preset()` is incomplete at line 150. Graph-based presets work via `try_graph_preset()` but the legacy fallback path is broken.
4. **Stimmung path inconsistency.** Rust StateReader reads `/dev/shm/hapax-stimmung/state.json`; requirements doc says `/dev/shm/hapax-visual/stimmung.json`. Both may exist; only one is canonical.
5. **No normative /dev/shm contract.** Paths are scattered across Python constants, Rust constants, and CLAUDE.md. No single table is authoritative.

---

## Solution

One consolidation spec (this document) that:
- Freezes all counts, paths, and interfaces as normative
- Reconciles discrepancies with verified-correct values from the audit
- Identifies the three minor fixes needed and their exact locations
- Becomes the single reference for future work (Stages 2-4)

No architectural changes. No new features. Pure documentation + three minor code fixes.

---

## 1. Normative Node Registry

**56 shader nodes** registered. The requirements doc said 54 because `output` and `solid` were miscounted as non-shader nodes. The registry loads all 56 from `agents/shaders/nodes/*.json`.

| Category | Count | Examples |
|----------|-------|---------|
| Source/Generator | 8 | noise_gen, solid, waveform_render, particle_system, voronoi_overlay, reaction_diffusion, fluid_sim, content_layer |
| Processing | 38 | colorgrade, bloom, chromatic_aberration, edge_detect, drift, breathing, postprocess, ... |
| Temporal | 7 | trail, stutter, feedback, slitscan, diff, echo, fluid_sim (dual-classified) |
| Compositing | 3 | blend, crossfade, luma_key |
| Terminal | 1 | output (identity pass-through, no shader) |
| **Total** | **56** | (1 node dual-classified: fluid_sim is both source and temporal) |

**Asset counts:**
- `.json` manifests: 56
- `.wgsl` shaders: 54 (output has no shader; content_layer is hand-authored WGSL, not transpiled)
- `.frag` shaders: 53 (content_layer has no GLSL source — WGSL-native)

---

## 2. Normative Preset Inventory

**30 backend presets** in `presets/*.json`. **20 frontend effect sources** in `effectSources.ts` (1 camera + 19 fx-prefixed).

The difference is correct: 10 backend presets are not exposed in the frontend picker because they are either:
- Atmospheric-only (selected by governance, not user): ambient, heartbeat
- Compound variants: datamosh_heavy, echo
- Permanent (not switchable): reverie_vocabulary
- Experimental: fisheye_pulse, voronoi_crystal, tunnelvision, mirror_rorschach, sculpture

| Category | Backend Presets | Frontend Sources |
|----------|----------------|-----------------|
| Ambient/Minimal | clean, ambient | fx-clean, fx-ambient |
| Temporal | ghost, trails, feedback_preset, echo | fx-ghost, fx-trails, fx-feedback |
| Color/Style | neon, silhouette, sculpture, dither_retro, vhs_preset, nightvision | fx-neon, fx-silhouette, fx-vhs, fx-nightvision |
| Glitch/Data | datamosh, datamosh_heavy, glitch_blocks_preset, pixsort_preset, slitscan_preset | fx-datamosh, fx-glitchblocks, fx-pixsort, fx-slitscan |
| Geometric | kaleidodream, mirror_rorschach, tunnelvision, voronoi_crystal, fisheye_pulse | — (governance-only) |
| Reactive | heartbeat, screwed, trap | fx-screwed, fx-trap |
| Technical | ascii_preset, halftone_preset, thermal_preset, diff_preset | fx-ascii, fx-halftone, fx-thermal, fx-diff |
| Permanent | reverie_vocabulary | — (always running in hapax-imagination) |
| **Total** | **30** | **20** (1 camera + 19 fx) |

---

## 3. Normative /dev/shm Contract

This table is the single source of truth for all shared-memory paths.

### Imagination Pipeline

| Path | Writer | Reader | Format | Cadence |
|------|--------|--------|--------|---------|
| `/dev/shm/hapax-imagination/pipeline/plan.json` | Python wgsl_compiler | Rust DynamicPipeline (file watcher) | JSON | On preset change |
| `/dev/shm/hapax-imagination/pipeline/*.wgsl` | Python wgsl_compiler | Rust DynamicPipeline | WGSL text | On preset change |
| `/dev/shm/hapax-imagination/pipeline/uniforms.json` | Python reverie actuation | Rust DynamicPipeline | JSON | 1s (actuation tick) |
| `/dev/shm/hapax-imagination/current.json` | Python imagination loop | Rust StateReader | JSON | 4-12s (fragment cadence) |

### Visual Surface

| Path | Writer | Reader | Format | Cadence |
|------|--------|--------|--------|---------|
| `/dev/shm/hapax-visual/frame.jpg` | Rust hapax-imagination (turbojpeg) | Tauri HTTP :8053, DMN vision | JPEG Q80 | 30fps |
| `/dev/shm/hapax-visual/state.json` | Rust hapax-imagination | Tauri HTTP :8053 | JSON | Per frame |
| `/dev/shm/hapax-visual/visual-chain-state.json` | Python visual_chain | Rust StateReader | JSON | Per activation |
| `/dev/shm/hapax-visual/control.json` | Tauri visual commands | Rust StateReader | JSON | On user action |

### Stimmung

| Path | Writer | Reader | Format | Cadence |
|------|--------|--------|--------|---------|
| `/dev/shm/hapax-stimmung/state.json` | Python stimmung agent | Rust StateReader, VLA | JSON | Every stimmung tick |

**Note:** The path `/dev/shm/hapax-visual/stimmung.json` referenced in the requirements doc is **incorrect**. The canonical path is `/dev/shm/hapax-stimmung/state.json` as read by Rust `state.rs` line 38.

### Compositor

| Path | Writer | Reader | Format | Cadence |
|------|--------|--------|--------|---------|
| `/dev/shm/hapax-compositor/snapshot.jpg` | GStreamer snapshot branch | API `/studio/stream/snapshot` | JPEG Q85 | 10fps |
| `/dev/shm/hapax-compositor/fx-snapshot.jpg` | GStreamer FX snapshot branch | API `/studio/stream/fx` | JPEG Q85 | 12fps |
| `/dev/shm/hapax-compositor/{role}.jpg` | GStreamer per-camera branch | API `/studio/stream/camera/{role}` | JPEG Q92 | 5fps |
| `/dev/shm/hapax-compositor/smooth-snapshot.jpg` | GStreamer smooth delay branch | Internal | JPEG | 10fps |
| `/dev/shm/hapax-compositor/visual-layer-state.json` | Python VLA | Compositor overlay, Tauri commands | JSON | Every VLA tick (3s) |
| `/dev/shm/hapax-compositor/visual-layer-enabled.txt` | API toggle | VLA renderer | Text (0/1) | On toggle |
| `/dev/shm/hapax-compositor/fx-request.txt` | API preset activation | Compositor state reader | Text | On preset change |
| `/dev/shm/hapax-compositor/fx-current.txt` | Compositor effects module | API status | Text | On preset change |
| `/dev/shm/hapax-compositor/effect-select.json` | Tauri select_effect command | Compositor state reader | JSON | On user action |

### DMN

| Path | Writer | Reader | Format | Cadence |
|------|--------|--------|--------|---------|
| `/dev/shm/hapax-dmn/visual-observation.txt` | Python DMN vision (gemini-flash) | Python imagination loop | Text | 30s (evaluative tick) |

---

## 4. Normative API Surface

**40 endpoints** across two route files (not 20 as the requirements doc stated).

### studio.py (23 endpoints)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/studio/status` | Pipeline status (cameras, resolution, HLS, consent) |
| GET | `/studio/cameras` | Camera fleet status |
| GET | `/studio/stream/snapshot` | Pre-FX composite JPEG |
| GET | `/studio/stream/fx` | Post-FX composite JPEG |
| GET | `/studio/stream/camera/{role}` | Per-camera JPEG |
| GET | `/studio/stream/batch` | Multipart batch of all camera snapshots |
| GET | `/studio/stream/mjpeg/{source}` | MJPEG stream (long-poll) |
| POST | `/studio/recording/start` | Start per-camera recording |
| POST | `/studio/recording/stop` | Stop recording |
| GET | `/studio/recording/status` | Recording state |
| GET | `/studio/perception` | Perception state summary |
| GET | `/studio/visual-layer` | VLA state |
| GET | `/studio/consent` | Consent phase |
| POST | `/studio/consent/override` | Manual consent override |
| GET | `/studio/disk` | Recording disk usage |
| POST | `/studio/activity-correction` | Correct activity classification |
| GET | `/studio/ambient-content` | Current ambient text fragments |
| GET | `/studio/profiles` | Camera profile list |
| POST | `/studio/profiles/{name}/activate` | Activate camera profile |
| GET | `/studio/layout` | Current tile layout |
| POST | `/studio/layout/hero` | Set hero camera |
| GET | `/studio/overlay` | Overlay state |
| POST | `/studio/overlay/toggle` | Toggle overlay visibility |

### studio_effects.py (17 endpoints)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/studio/effect/graph` | Current effect graph |
| PUT | `/studio/effect/graph` | Replace entire graph |
| PATCH | `/studio/effect/graph` | Topology mutation (add/remove nodes+edges) |
| GET | `/studio/effect/graph/state` | Full graph state (runtime snapshot) |
| GET | `/studio/effect/nodes` | Node registry (all 56 schemas) |
| GET | `/studio/effect/nodes/{type}` | Single node schema |
| PATCH | `/studio/effect/node/{id}` | Update node params |
| DELETE | `/studio/effect/node/{id}` | Remove node |
| GET | `/studio/effect/modulations` | Current modulation bindings |
| PUT | `/studio/effect/modulations` | Replace all modulations |
| GET | `/studio/effect/layers` | Layer palettes (@live, @smooth, @hls) |
| PATCH | `/studio/effect/layers/{id}` | Update layer palette |
| GET | `/studio/effect/presets` | List all presets |
| GET | `/studio/effect/presets/{name}` | Get preset by name |
| POST | `/studio/effect/select` | Activate preset |
| PUT | `/studio/effect/presets/{name}` | Save/update preset |
| DELETE | `/studio/effect/presets/{name}` | Delete user preset |

---

## 5. Normative Uniform Buffer

The shared GPU uniform struct, as implemented in both Rust (`uniform_buffer.rs`) and WGSL (`uniforms.wgsl`):

```wgsl
struct Uniforms {
    // Core timing
    time: f32,
    dt: f32,
    resolution: vec2<f32>,

    // Stimmung state
    stance: u32,          // 0=nominal, 1=cautious, 2=degraded, 3=critical
    color_warmth: f32,    // 0.0=teal(h=180°), 1.0=warm(h=25°)
    speed: f32,
    turbulence: f32,
    brightness: f32,

    // 9 Expressive Dimensions (semantic bridge: cognitive state → visual)
    intensity: f32,           // visual energy/density [0,1]
    tension: f32,             // pattern tightness [0,1]
    depth: f32,               // recessive space [-1,1]
    coherence: f32,           // pattern regularity [0,1]
    spectral_color: f32,      // warmth/saturation [0,1]
    temporal_distortion: f32, // animation speed [0,1]
    degradation: f32,         // signal corruption [0,1]
    pitch_displacement: f32,  // hue rotation [0,1]
    diffusion: f32,           // visual scatter [0,1]

    // Content layer
    slot_opacities: vec4<f32>,    // 4 content texture slots

    // Per-node custom parameters (from plan.json uniforms field)
    custom: array<vec4<f32>, 8>,  // 32 floats, packed as 8 vec4s
}
```

**Std140 alignment:** Rust struct includes `_align_pad` fields. WGSL struct matches exactly.

---

## 6. Normative Service Architecture

| Service | Binary | Port/Socket | VRAM | MemoryMax | Restart |
|---------|--------|-------------|------|-----------|---------|
| `hapax-imagination` | Rust standalone | UDS + :8053 (HTTP) | ~380 MiB | 4G | always, 2s |
| `studio-compositor` | Python GStreamer | /dev/video42 | ~3.5 GB (incl. smooth buffer) | 4G | on-failure, 10s |
| `visual-layer-aggregator` | Python async | — | — | 1G | on-failure |
| `logos-api` | FastAPI | :8051 | — | 2G | on-failure |
| `hapax-dmn` | Python async | — | ~5.6 GB (Ollama) | — | always |

**Boot chain:** hapax-secrets → hapax-imagination → logos-api → {studio-compositor, visual-layer-aggregator} (parallel). hapax-dmn independent.

---

## 7. Normative Reverie Vocabulary

The permanent 7-pass graph (`presets/reverie_vocabulary.json`), always running in `hapax-imagination`:

| Pass | Node ID | Shader Type | Key Parameters | Temporal |
|------|---------|-------------|----------------|----------|
| 1 | `noise` | noise_gen | octaves, persistence, lacunarity, scale | No |
| 2 | `color` | colorgrade | saturation, brightness, contrast, hue_rotate | No |
| 3 | `drift` | drift | speed, direction, scale | No |
| 4 | `breath` | breathing | rate (~60 BPM), depth | No |
| 5 | `fb` | feedback | decay, zoom, rotate, trace_center/radius/strength | **Yes** (@accum_fb) |
| 6 | `content` | content_layer | salience, intensity, material (water/fire/earth/air/void) | No |
| 7 | `post` | postprocess | vignette_strength, sediment | No |
| 8 | `out` | output | — (terminal) | No |

**Edge chain:** noise→color→drift→breath→fb→content→post→out (linear).

---

## 8. Three Minor Fixes

These are the only code changes required by this consolidation:

### Fix 1: Complete `switch_fx_preset()` truncation

**File:** `agents/studio_compositor/effects.py:~150`
**Problem:** Function body truncated. Legacy preset names (ascii, diff, etc.) may not apply post-process uniforms when graph-based activation fails.
**Fix:** Complete the function or replace with a redirect to `try_graph_preset()` since all presets now have graph definitions. The legacy path is dead code.
**Recommendation:** Delete `switch_fx_preset()` entirely. Replace calls with `try_graph_preset()`. The graph system handles all 30 presets.

### Fix 2: Update requirements doc stimmung path

**File:** `~/.cache/hapax/STUDIO-EFFECTS-REQUIREMENTS.md` §13.1
**Problem:** Lists `/dev/shm/hapax-visual/stimmung.json` but the canonical path is `/dev/shm/hapax-stimmung/state.json`.
**Fix:** Correct the path in the requirements doc (or supersede with this spec).

### Fix 3: Update requirements doc counts

**File:** `~/.cache/hapax/STUDIO-EFFECTS-REQUIREMENTS.md` §3.1, §10, §12
**Problem:** Says 54 nodes (actual: 56), 20 API endpoints (actual: 40), 32 presets (actual: 30).
**Fix:** Correct counts (or supersede with this spec).

---

## Acceptance Criteria

1. This document is the single authoritative reference for the studio/effects pipeline as-built state.
2. All counts in this document match the running system (56 nodes, 30 presets, 40 API endpoints).
3. All /dev/shm paths in §3 are verified against actual code (writer and reader both confirmed).
4. The three fixes in §8 are either completed or explicitly deferred.
5. Future design docs (Stages 2-4) reference this document, not the phase-specific specs.
6. The requirements doc at `~/.cache/hapax/STUDIO-EFFECTS-REQUIREMENTS.md` is either updated or marked as superseded.

## Constraints

- PR #477 blocks writes to the repository. This spec must be staged in `~/.cache/hapax/specs/` until the PR is merged.
- No architectural changes. This is documentation + three trivial fixes.
- The phase-specific specs remain in `docs/superpowers/specs/` for historical reference but are no longer authoritative.
