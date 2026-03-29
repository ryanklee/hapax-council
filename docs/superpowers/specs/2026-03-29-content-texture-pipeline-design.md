# Content Texture Pipeline Design

## Summary

Restore full 4-slot content texture management for Hapax Reverie. Imagination fragments produce JPEG images (text rasterizations, Qdrant results, camera frames, URLs, files) that are composited over the procedural field with Bachelard effects. Python decides what to show, Rust handles GPU upload and fade animation at framerate.

## Architecture

Three layers:

1. **Python (content selection):** DMN resolver writes JPEGs + slot manifest to shm
2. **Rust (GPU management):** `ContentTextureManager` decodes, uploads, fades at 60fps
3. **WGSL (compositing):** content_layer.wgsl screen-blends content over procedural field

## Python Side: Slot Manifest

The DMN resolver already writes JPEGs to `/dev/shm/hapax-imagination/content/`. Add a slot manifest that tells Rust what to display.

### Manifest format (`/dev/shm/hapax-imagination/content/active/slots.json`)

```json
{
  "fragment_id": "abc123",
  "slots": [
    {"index": 0, "path": "/dev/shm/hapax-imagination/content/active/abc123-0.jpg", "kind": "text", "salience": 0.7},
    {"index": 1, "path": "/dev/shm/hapax-compositor/overhead.jpg", "kind": "camera_frame", "salience": 0.5},
    {"index": 2, "path": "/dev/shm/hapax-imagination/content/active/abc123-2.jpg", "kind": "qdrant_query", "salience": 0.4}
  ],
  "continuation": false,
  "material": "fire"
}
```

- `slots` array: up to 4 entries, index 0–3. Each has a filesystem path to a JPEG, the content kind, and a per-slot salience (used as fade target).
- `continuation`: if false, fade out all existing slots before loading new ones. If true, add/replace without fading.
- `material`: Bachelard material for this fragment (water/fire/earth/air/void).

### Staging directory (fixes audit item I6)

The resolver writes all JEPGs to `/dev/shm/hapax-imagination/content/staging/` first. Once all references are resolved, it atomically moves the directory:

```python
staging = CONTENT_DIR / "staging"
active = CONTENT_DIR / "active"
# Write all JPEGs to staging/
# Write slots.json to staging/
# Atomic swap:
if active.exists():
    active.rename(CONTENT_DIR / "old")
staging.rename(active)
shutil.rmtree(CONTENT_DIR / "old", ignore_errors=True)
```

Rust reads only from `active/`. No race condition — the directory appears atomically.

### Content kind handling

| Kind | Resolver action | Path |
|------|----------------|------|
| `text` | Rasterize via PIL (already implemented) | `active/{id}-{i}.jpg` |
| `qdrant_query` | Query Qdrant, rasterize result text (already implemented) | `active/{id}-{i}.jpg` |
| `url` | Fetch image, resize, center on black (already implemented) | `active/{id}-{i}.jpg` |
| `camera_frame` | No resolver action — path points to live camera JPEG | `/dev/shm/hapax-compositor/{source}.jpg` |
| `file` | No resolver action — path is the file itself | As specified in content_reference |

### Resolver changes

- `resolve_references()` writes to `staging/` instead of directly to `content/`
- New `write_slot_manifest()` function builds and writes `slots.json`
- `cleanup_content_dir()` replaced by atomic staging swap
- DMN `_resolver_loop` calls `write_slot_manifest()` after resolving

## Rust Side: ContentTextureManager

New module in `hapax-visual` that manages 4 texture slots with JPEG decode and fade animation.

### State

```rust
struct SlotState {
    active: bool,
    opacity: f32,           // current (interpolated per frame)
    target_opacity: f32,    // from manifest salience
    fade_rate: f32,         // 2.0 per second
    fragment_id: String,    // which fragment loaded this slot
    path: String,           // filesystem path to JPEG
}
```

### Lifecycle

1. **Poll** (every 500ms, same cadence as StateReader): Read `active/slots.json`. If `fragment_id` changed:
   - If not continuation: set all slots' `target_opacity = 0.0` (fade out)
   - For each slot in manifest: decode JPEG via turbojpeg, upload to pool texture `content_slot_{i}`, set `target_opacity = salience`
2. **Tick** (every frame): Interpolate each slot's `opacity` toward `target_opacity` at `fade_rate * dt`. Deactivate slots that reach 0.
3. **Write uniforms**: Set `uniform_data.slot_opacities = [slot0.opacity, slot1.opacity, slot2.opacity, slot3.opacity]`

### Pool texture integration

The `ContentTextureManager` owns 4 `wgpu::Texture` objects (1920x1080 Rgba8UnormSrgb) created at init. It uploads JPEG data via `queue.write_texture()`. These textures are registered in the dynamic pipeline's texture pool as `content_slot_0` through `content_slot_3`.

The dynamic pipeline's `ensure_texture` creates textures at the pool's format (`Rgba8Unorm`). Content textures need `Rgba8UnormSrgb` for correct JPEG color. Two options:
- Use `Rgba8Unorm` and accept the slight gamma difference (JPEGs are sRGB but we skip the decode — visually close enough for mixed content)
- ContentTextureManager creates its own textures at `Rgba8UnormSrgb` and registers their views in the pool

Recommendation: use `Rgba8Unorm` for simplicity — content is blended over procedural output at the same format. JPEG bytes are sRGB-encoded, and `Rgba8Unorm` treats them as linear, which produces slightly washed-out content. This is acceptable for the dreamy Reverie aesthetic. If precision matters later, add sRGB textures.

### Placeholder texture

A 1x1 black texture for inactive slots (same pattern as the old content_layer.rs). The content_layer shader samples all 4 slots every frame — inactive slots sample the placeholder and get multiplied by opacity 0.

## WGSL Side: Content Compositing

Update `content_layer.wgsl` to accept 4 additional texture inputs and composite them over the procedural field.

### Bind group layout

The content_layer pass in the plan needs 6 inputs instead of 1:
- binding 0: procedural field (from previous pass)
- binding 1: sampler
- binding 2: content_slot_0
- binding 3: content_slot_1
- binding 4: content_slot_2
- binding 5: content_slot_3

### Compositing logic

For each slot:
1. Sample content texture at Bachelard-modulated UV (corner incubation + immensity + material distortion)
2. Apply materialization noise gate (from procedural noise, gated by slot opacity)
3. Apply material color adjustment
4. Multiply by `slot_opacities[i]` (fade opacity)
5. Screen-blend over the procedural field accumulator

```wgsl
// For each active slot:
let content = textureSample(content_slot_0, tex_sampler, modulated_uv);
let gated = content.rgb * materialization(uv_raw, slot_opacities[0], time);
let colored = material_color(gated, material_id);
let weighted = colored * slot_opacities[0];
// Screen blend: result = 1 - (1 - base) * (1 - layer)
result = 1.0 - (1.0 - result) * (1.0 - weighted);
```

The dwelling trace boost applies to the final blended result — brighter output persists longer in the feedback buffer.

## Files

### Create
- `hapax-logos/crates/hapax-visual/src/content_textures.rs` — ContentTextureManager (~150 lines)

### Modify
- `hapax-logos/crates/hapax-visual/src/lib.rs` — add `pub mod content_textures`
- `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs` — register content slot textures in pool, pass to content_layer pass
- `hapax-logos/src-imagination/src/main.rs` — create ContentTextureManager, tick it in render loop
- `agents/shaders/nodes/content_layer.wgsl` — add 4 content texture inputs, compositing logic
- `agents/shaders/nodes/content_layer.frag` — update GLSL source to match
- `agents/shaders/nodes/content_layer.json` — update inputs to declare content slots
- `agents/imagination_resolver.py` — staging directory, slot manifest writer
- `agents/dmn/__main__.py` — call write_slot_manifest after resolving
- `tests/test_imagination_resolver.py` — test staging swap and manifest generation

### No changes
- `uniform_buffer.rs` — slot_opacities already in UniformData
- `state.rs` — no new state files needed (ContentTextureManager reads slots.json directly)

## Testing

- **Python:** Test slot manifest generation, staging directory atomic swap, content kind routing
- **Rust:** Compilation check (no GPU unit tests). Visual verification with manual slots.json + JPEG files.
- **Integration:** Write a JPEG + slots.json to shm, run hapax-imagination, verify content appears over procedural field
