# Reverie Gap Closure — Complete Feedback Loop & Parameter Alignment

**Date:** 2026-03-30
**Status:** Design
**Context:** Exhaustive audit of Reverie implementation against the Bachelardian model revealed 8 gaps, 3 HIGH severity. Two break the reflective feedback loop (the philosophical core of Reverie). One disconnects the entire visual chain parameter pathway.

## Gaps Addressed

| # | Gap | Severity | Phase |
|---|-----|----------|-------|
| 1 | Feedback node missing from vocabulary graph — Amendment 2 traces never render | HIGH | 1 |
| 2 | Reverberation uses text-only Ollama, not multimodal — DMN can't perceive rendered frame | HIGH | 1 |
| 3 | `diffusion` dimension dead on GPU — `formant_character` occupies 9th slot | MEDIUM | 2 |
| 4 | Visual chain params silently dropped — per-node param override bridge never built | HIGH | 2 |
| 5 | Hard 0.8 pre-filter on proactive gate partially negates soft escalation | LOW | 3 |
| 6 | Immensity entry direction time-based, not per-slot | LOW | 3 |
| 7 | Continuation crossfade timing not differentiated in Rust | LOW | 3 |
| 8 | Trace center always (0.5, 0.5), no per-slot tracking | LOW | 3 |

---

## Phase 1: Feedback Loop Completion

### 1A. Add Feedback Node to Vocabulary Graph

The `presets/reverie_vocabulary.json` graph is `noise_gen → colorgrade → drift → breathing → content_layer → postprocess → output`. The feedback shader exists (`agents/shaders/nodes/feedback.wgsl`) with full trace-aware decay, but it's not in the graph. Without it, Amendment 2 (dwelling/trace) can never produce visible afterimages.

**Change:** Insert a feedback node between `breathing` and `content_layer`. The feedback node is temporal — it reads its own previous output via `@accum_fb`, creating the frame-to-frame persistence that makes traces visible.

New graph: `noise_gen → colorgrade → drift → breathing → feedback → content_layer → postprocess → output`

The feedback node's params include `trace_center_x`, `trace_center_y`, `trace_radius`, `trace_strength`. These are already written by the actuation loop to `uniforms.json`. The Phase 2 per-node param bridge will deliver them to the shader.

**File:** `presets/reverie_vocabulary.json`

Add after `"breath"`:
```json
"fb": {
    "type": "feedback",
    "params": {
        "decay": 0.05,
        "zoom": 1.005,
        "rotate": 0.003,
        "blend_mode": 1.0,
        "hue_shift": 0.5,
        "trace_center_x": 0.5,
        "trace_center_y": 0.5,
        "trace_radius": 0.0,
        "trace_strength": 0.0
    }
}
```

Update edges: `["breath", "fb"], ["fb", "content"], ...`

**Verification:** After this change, the compiled plan.json will include a temporal feedback pass with `@accum_fb` input. The Rust pipeline already supports temporal passes. When trace_strength > 0, the feedback shader reduces decay in the trace region, creating the ghostly afterimage.

### 1B. Multimodal Visual Observation

The DMN's `_write_visual_observation()` in `pulse.py` currently calls text-only `qwen3.5:4b` via Ollama with metadata about the frame — it never reads the actual JPEG. The reverberation loop depends on the DMN being surprised by what it *sees*, not what it *knows*.

**Change:** Replace the text-only Ollama call with a multimodal `gemini-flash` call via LiteLLM. Read `/dev/shm/hapax-visual/frame.jpg`, base64-encode it, and pass it as an image alongside a terse prompt.

The existing pattern is established in `agents/hapax_daimonion/screen_analyzer.py` — `AsyncOpenAI` client, `gemini-flash` model, base64 image_url content type.

**Implementation:**

New function in `agents/dmn/pulse.py`, using the same `openai.AsyncOpenAI` + LiteLLM pattern established in `screen_analyzer.py`:

```python
async def _generate_visual_observation(frame_path: str, imagination_narrative: str) -> str:
    """Describe the rendered visual surface using a vision-capable model."""
    frame = Path(frame_path)
    if not frame.exists():
        return ""
    b64 = base64.b64encode(frame.read_bytes()).decode()

    from openai import AsyncOpenAI
    client = AsyncOpenAI(
        base_url="http://localhost:4000",
        api_key=os.environ.get("LITELLM_API_KEY", "sk-dummy"),
    )
    try:
        resp = await client.chat.completions.create(
            model="gemini-flash",
            messages=[
                {"role": "system", "content": VISUAL_OBSERVATION_SYSTEM},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": f"The system intended to show: {imagination_narrative}"},
                ]},
            ],
            temperature=0.1,
            max_tokens=100,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        log.debug("Visual observation generation failed", exc_info=True)
        return ""
```

Replace `_write_visual_observation()` to call this function with the frame path from the sensor snapshot. The prompt stays the same (describe what you see, one sentence). The model now actually sees the rendered frame.

**Cost control:** `gemini-flash` is cheap. The evaluative tick runs every 30s. At ~100 tokens per call, this is negligible. The call is skipped when the frame is stale (age > threshold).

**Files:**
- Modify: `agents/dmn/pulse.py` — replace `_write_visual_observation()`
- No new dependencies (httpx already imported)

---

## Phase 2: Dimension & Parameter Alignment

### 2A. Rename `formant_character` → `diffusion`

The 9th uniform slot is `formant_character` — a vocal chain dimension with no visual meaning. No shader reads it. The imagination fragment model defines `diffusion` as a medium-agnostic dimension, but it has no GPU pathway because the uniform field doesn't exist.

**Change:** Rename the field in 4 locations:

1. `hapax-logos/crates/hapax-visual/src/uniform_buffer.rs` — struct field + default + from_state()
2. `hapax-logos/crates/hapax-visual/src/shaders/uniforms.wgsl` — struct field
3. `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs` — signal override match arm
4. Comments referencing the old name

The byte offset (68), alignment padding, and struct size are unchanged. This is a pure rename with zero ABI risk.

**Files:**
- Modify: `uniform_buffer.rs` (3 lines)
- Modify: `uniforms.wgsl` (1 line)
- Modify: `dynamic_pipeline.rs` (1 line)

### 2B. Build Per-Node Parameter Override Bridge

This is the biggest gap. The visual chain computes parameter deltas (e.g., `gradient.brightness: 0.5`) and writes them to `uniforms.json`. The Rust pipeline reads `uniforms.json` but only processes `signal.*` keys. Per-node params (`node.param` keys) are initialized once at plan reload and never updated at runtime.

**Root cause:** `DynamicPass` stores a `params_buffer` (GPU buffer) that's written once at reload time. No code updates it per-frame from `uniforms.json`.

**Change:** In `dynamic_pipeline.rs`, after reading `uniforms.json`, apply `node.param` overrides to each pass's params buffer:

```rust
// After processing signal.* keys:
for pass in &self.passes {
    if let (Some(ref buf), true) = (&pass.params_buffer, !pass.param_order.is_empty()) {
        let mut updated = false;
        let mut data: Vec<f32> = pass.current_params.clone(); // need to store current values
        for (i, name) in pass.param_order.iter().enumerate() {
            let key = format!("{}.{}", pass.node_id, name);
            if let Some(&val) = overrides.get(&key) {
                data[i] = val as f32;
                updated = true;
            }
        }
        if updated {
            while data.len() < 4 { data.push(0.0); }
            while (data.len() * 4) % 16 != 0 { data.push(0.0); }
            queue.write_buffer(buf, 0, bytemuck::cast_slice(&data));
        }
    }
}
```

This requires:
1. Adding `param_order: Vec<String>` and `current_params: Vec<f32>` to `DynamicPass` (currently only plan_pass has param_order)
2. Copying them from the plan pass at reload time
3. Applying overrides each frame (only when values change)

### 2C. Fix Visual Chain Technique Names

With 2B built, the node.param keys must match the actual graph node IDs. Currently `visual_chain.py` uses legacy technique names (`"gradient"`, `"rd"`, `"compositor"`, `"postprocess"`, `"physarum"`, `"feedback"`). The vocabulary graph uses different IDs (`"noise"`, `"color"`, `"drift"`, `"breath"`, `"fb"`, `"content"`, `"post"`).

**Approach:** Rather than hardcoding a mapping, make the visual chain technique names match the vocabulary graph. The vocabulary graph is the authority — the visual chain adapts to it.

**Change:** In `visual_chain.py`, update all `ParameterMapping` technique names:

| Old name | New name | Vocabulary node |
|----------|----------|-----------------|
| `"gradient"` | `"noise"` | noise_gen (gradient params live here) |
| `"compositor"` | — | **Remove** — no compositor node in dynamic pipeline |
| `"postprocess"` | `"post"` | postprocess |
| `"rd"` | — | **Remove** — not in default vocabulary |
| `"physarum"` | — | **Remove** — not in default vocabulary |
| `"feedback"` | `"fb"` | feedback |

Compositor opacity params (`opacity_rd`, `opacity_wave`, `opacity_physarum`, `opacity_feedback`) are legacy from the old hardcoded pipeline. They controlled technique layer blending in the compositor. In the dynamic pipeline, there is no compositor — each node is a graph pass. These bindings are dead and should be removed.

For RD, physarum, and wave: these nodes can be added to custom presets but are not in the vocabulary. Visual chain bindings for absent nodes are harmless (the params write to uniforms.json, get matched against the plan, find no matching node_id, and are ignored). Keep them for when those nodes are used in non-vocabulary presets, but update the technique name to match the node type name used in presets.

**Practical approach:** Only update technique names for nodes present in the vocabulary. Remove compositor bindings entirely. Keep rd/physarum/wave bindings with their current names (they match the node type names used in presets that contain those nodes).

**Files:**
- Modify: `agents/visual_chain.py` — update ParameterMapping technique names
- Modify: `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs` — add per-frame param override bridge

---

## Phase 3: Behavioral Refinements

### 3A. Soften Proactive Gate Pre-Filter

The daimonion impingement consumer routes imagination impingements to ProactiveGate only when `imp.strength >= 0.8`. The sigmoid gate (midpoint=0.75) is designed to probabilistically pass 0.65-0.8 range. The hard pre-filter kills this range.

**Change:** Lower the pre-filter from 0.8 to 0.65 in the daimonion impingement consumer. This lets the sigmoid gate make the probabilistic decision across its full designed range.

**File:** `agents/hapax_daimonion/run_loops_aux.py` (or wherever the 0.8 threshold lives)

### 3B. Per-Slot Immensity Entry Direction

Currently `immensity_entry()` in `content_layer.wgsl` uses `time` for direction. All 4 slots enter from the same direction. The spec says each slot should have a distinct entry angle based on slot index.

**Change:** Pass slot index to the function and use it instead of time for direction:

```wgsl
fn immensity_entry(uv: vec2<f32>, salience: f32, slot_index: f32) -> vec2<f32> {
    let entry_progress = smoothstep(0.0, 0.5, salience);
    let entry_offset = (1.0 - entry_progress) * 0.4;
    let entry_dir = vec2<f32>(sin(slot_index * 2.1), cos(slot_index * 1.7));
    return uv + entry_dir * entry_offset;
}
```

In `main_1()`, call with per-slot index when blending each slot. This requires restructuring the blend loop to pass slot index — currently UV is computed once for all slots.

**Approach:** Compute per-slot UVs inside each `sample_and_blend_slot` call rather than pre-computing a single UV.

**File:** `agents/shaders/nodes/content_layer.wgsl`

### 3C. Continuation-Aware Crossfade in Rust

`ContentTextureManager` uses uniform `FADE_RATE = 2.0` for all transitions. The spec describes:
- Continuation: 2.0s simultaneous crossfade
- Non-continuation: 3.5s (1.5s out + 0.5s gap + 1.5s in)

**Change:** Read the `continuation` flag from the slot manifest. When continuation is true, use FADE_RATE=2.0 (current behavior). When false, use a two-phase approach:
- Old slots: target_opacity=0.0, fade_rate=1.5
- New slots: target_opacity delayed by ~2s (old must fade first), then fade_rate=1.5

**Implementation:** Add a `fade_phase: FadePhase` enum to `SlotState`:
```rust
enum FadePhase { Active, FadingOut, Gap, FadingIn }
```

Track phase per slot. On non-continuation fragment arrival, existing slots enter `FadingOut`. After they reach 0.0, a brief `Gap` timer (0.5s), then new slots enter `FadingIn`.

**File:** `hapax-logos/crates/hapax-visual/src/content_textures.rs`

### 3D. Per-Slot Trace Center Tracking

The actuation loop always sets trace center to (0.5, 0.5). For more accurate traces, track the approximate screen position of fading content.

**Change:** In the actuation loop `_update_trace()`, read the content layer's slot index and compute a center based on the UV modulation that slot experienced. Since exact per-pixel position is unknowable from Python, use the slot index to approximate:

```python
# Approximate center from slot index (matches content_layer.wgsl entry direction)
import math
slot_centers = {
    0: (0.4, 0.4),
    1: (0.6, 0.4),
    2: (0.4, 0.6),
    3: (0.6, 0.6),
}
```

This is a rough approximation but better than always-center. The exact values are less important than the directional variety.

**File:** `agents/reverie/actuation.py`

---

## Implementation Order

Phase 1 (feedback loop) and Phase 2 (dimension/parameter) are independent and can be parallelized.
Phase 3 depends on nothing and can run after either.

Within phases:
- **1A** (vocabulary graph) is trivial, do first
- **1B** (multimodal observation) is independent
- **2A** (diffusion rename) is trivial, do first
- **2B** (param bridge) is the most complex change, core of Phase 2
- **2C** (technique names) depends on 2B working
- **3A-3D** are all independent of each other

## Testing

### Phase 1
- **1A:** Verify plan.json includes feedback pass with `@accum_fb` input. Verify temporal pass flag. Visual verification: feedback zoom/rotate visible on running surface.
- **1B:** Mock httpx to verify gemini-flash call with base64 image. Integration: verify visual-observation.txt contains visual description (not metadata). Test reverberation_check against vision-model output vs. imagination narrative.

### Phase 2
- **2A:** Cargo build succeeds. `diffusion` field readable in WGSL. Existing tests pass (no regressions).
- **2B:** Write uniforms.json with `fb.decay: 0.1`. Verify Rust reads it and updates the feedback pass params buffer. Write `noise.speed: 0.5`. Verify noise_gen pass params buffer updates.
- **2C:** Integration: activate visual_chain.intensity. Verify `noise.brightness` appears in uniforms.json with correct value. Verify Rust applies it.

### Phase 3
- **3A:** Test proactive gate with salience 0.7 — should reach sigmoid (was previously filtered).
- **3B:** Visual verification: 4 simultaneous content slots enter from different directions.
- **3C:** Visual verification: non-continuation fragments show gap between old and new content.
- **3D:** Verify trace center varies with slot index when content fades.

## Constraints

- **Rust rebuild required** for Phase 2A, 2B, 3C. The `hapax-imagination` binary must be rebuilt and the systemd service restarted.
- **No new dependencies.** All required libraries (httpx, base64, Pillow, turbojpeg) are already available.
- **VRAM budget unchanged.** No new GPU allocations — feedback node reuses temporal texture pool. Per-node param buffers already allocated at plan reload.
- **Cost:** gemini-flash visual observation adds ~100 tokens per 30s evaluative tick. Negligible.
