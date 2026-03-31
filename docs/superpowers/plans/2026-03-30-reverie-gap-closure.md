# Reverie Gap Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all 8 gaps between the Reverie implementation and its Bachelardian design model — completing the reflective feedback loop, wiring dimension/parameter pathways, and refining behavioral thresholds.

**Architecture:** Three phases: (1) feedback loop completion (vocabulary graph + multimodal vision), (2) dimension & parameter alignment (Rust uniform rename + per-node param bridge + visual chain name fix), (3) behavioral refinements (gate softening, per-slot shader fixes, crossfade, trace centers). Phases 1 and 2 are independent. Phase 3 is independent of both.

**Tech Stack:** Python 3.12 (pydantic, httpx, openai), Rust (wgpu, serde, turbojpeg), WGSL shaders

**Spec:** `docs/superpowers/specs/2026-03-30-reverie-gap-closure-design.md`

---

## Phase 1: Feedback Loop Completion

### Task 1: Add feedback node to vocabulary graph

**Files:**
- Modify: `presets/reverie_vocabulary.json`
- Test: verify compiled plan.json

- [ ] **Step 1: Read the current preset**

Read `presets/reverie_vocabulary.json` to confirm current graph: noise → color → drift → breath → content → post → out.

- [ ] **Step 2: Add feedback node and update edges**

In `presets/reverie_vocabulary.json`, add the `"fb"` node after `"breath"` in the nodes object:

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

Update the edges array to route through the feedback node:

```json
"edges": [
    ["noise", "color"],
    ["color", "drift"],
    ["drift", "breath"],
    ["breath", "fb"],
    ["fb", "content"],
    ["content", "post"],
    ["post", "out"]
]
```

- [ ] **Step 3: Verify compilation produces temporal pass**

Run: `cd ~/projects/hapax-council && uv run python -c "
import json
from agents.effect_graph.types import EffectGraph
from agents.effect_graph.wgsl_compiler import compile_to_wgsl_plan
raw = json.loads(open('presets/reverie_vocabulary.json').read())
graph = EffectGraph(**raw)
plan = compile_to_wgsl_plan(graph)
fb_pass = [p for p in plan['passes'] if p['node_id'] == 'fb'][0]
assert fb_pass.get('temporal') is True, 'feedback pass must be temporal'
assert '@accum_fb' in fb_pass['inputs'], 'feedback pass must have @accum_fb input'
print('OK: feedback pass is temporal with @accum_fb input')
print(f'Total passes: {len(plan[\"passes\"])}')
for p in plan['passes']:
    print(f'  {p[\"node_id\"]}: {p[\"type\"]} inputs={p[\"inputs\"]} output={p[\"output\"]}')
"`

Expected: feedback pass marked temporal with `@accum_fb` in inputs. 7 passes total (was 6).

- [ ] **Step 4: Commit**

```bash
git add presets/reverie_vocabulary.json
git commit -m "feat(reverie): add feedback node to vocabulary graph — enables Amendment 2 traces"
```

---

### Task 2: Multimodal visual observation for reverberation

**Files:**
- Modify: `agents/dmn/pulse.py`
- Test: `tests/test_dmn_visual_observation.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_dmn_visual_observation.py`:

```python
"""Tests for multimodal visual observation (reverberation feedback loop)."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def tmp_frame(tmp_path: Path) -> Path:
    """Create a minimal JPEG file for testing."""
    # Minimal valid JPEG: SOI + APP0 + EOI
    jpeg_bytes = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00,
        0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xD9,
    ])
    p = tmp_path / "frame.jpg"
    p.write_bytes(jpeg_bytes)
    return p


@pytest.fixture
def tmp_observation_path(tmp_path: Path) -> Path:
    return tmp_path / "visual-observation.txt"


async def test_visual_observation_sends_image_to_gemini(tmp_frame, tmp_observation_path):
    """The visual observation function must send the actual JPEG to gemini-flash."""
    from agents.dmn.pulse import _generate_visual_observation

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "A dark swirling pattern with blue noise"

    with patch("agents.dmn.pulse._get_vision_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await _generate_visual_observation(str(tmp_frame), "abstract noise field")

    assert result == "A dark swirling pattern with blue noise"
    call_args = mock_client.chat.completions.create.call_args
    assert call_args.kwargs["model"] == "gemini-flash"
    # Verify image was sent as base64
    user_content = call_args.kwargs["messages"][1]["content"]
    image_parts = [p for p in user_content if p.get("type") == "image_url"]
    assert len(image_parts) == 1
    assert image_parts[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")


async def test_visual_observation_returns_empty_on_missing_frame(tmp_path):
    """Must return empty string when frame doesn't exist."""
    from agents.dmn.pulse import _generate_visual_observation

    result = await _generate_visual_observation(str(tmp_path / "nonexistent.jpg"), "test")
    assert result == ""


async def test_visual_observation_returns_empty_on_api_failure(tmp_frame):
    """Must return empty string on API failure, not raise."""
    from agents.dmn.pulse import _generate_visual_observation

    with patch("agents.dmn.pulse._get_vision_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API down"))
        mock_get_client.return_value = mock_client

        result = await _generate_visual_observation(str(tmp_frame), "test")

    assert result == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/projects/hapax-council && uv run pytest tests/test_dmn_visual_observation.py -v`

Expected: ImportError or AttributeError — `_generate_visual_observation` and `_get_vision_client` don't exist yet.

- [ ] **Step 3: Implement multimodal visual observation**

In `agents/dmn/pulse.py`, add imports at the top (after existing imports):

```python
import base64
import os
```

Add a singleton client helper after the existing `_ollama_generate` function:

```python
_vision_client = None


def _get_vision_client():
    """Lazy-init AsyncOpenAI client for vision calls via LiteLLM."""
    global _vision_client
    if _vision_client is None:
        from openai import AsyncOpenAI

        _vision_client = AsyncOpenAI(
            base_url="http://localhost:4000",
            api_key=os.environ.get("LITELLM_API_KEY", "sk-dummy"),
        )
    return _vision_client


async def _generate_visual_observation(frame_path: str, imagination_narrative: str) -> str:
    """Describe the rendered visual surface using a vision-capable model.

    Reads the actual JPEG frame and sends it to gemini-flash via LiteLLM.
    Returns a one-sentence visual description, or empty string on failure.
    """
    frame = Path(frame_path)
    if not frame.exists():
        return ""
    try:
        b64 = base64.b64encode(frame.read_bytes()).decode()
    except OSError:
        return ""

    client = _get_vision_client()
    try:
        resp = await client.chat.completions.create(
            model="gemini-flash",
            messages=[
                {"role": "system", "content": VISUAL_OBSERVATION_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                        {
                            "type": "text",
                            "text": f"The system intended to show: {imagination_narrative}",
                        },
                    ],
                },
            ],
            temperature=0.1,
            max_tokens=100,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        log.debug("Visual observation generation failed", exc_info=True)
        return ""
```

Replace the existing `_write_visual_observation` method body (around line 242-256) to use the new function:

```python
async def _write_visual_observation(self, snapshot: dict) -> None:
    """Generate and write a visual observation of the rendered surface."""
    visual = snapshot.get("visual_surface", {})
    if not visual or visual.get("stale", True):
        return
    frame_path = visual.get("frame_path")
    if not frame_path:
        return
    imagination = snapshot.get("imagination", {})
    narrative = imagination.get("narrative", "")

    result = await _generate_visual_observation(frame_path, narrative)
    if result:
        try:
            VISUAL_OBSERVATION_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp = VISUAL_OBSERVATION_PATH.with_suffix(".tmp")
            tmp.write_text(result)
            tmp.rename(VISUAL_OBSERVATION_PATH)
        except OSError:
            pass
```

- [ ] **Step 4: Run tests**

Run: `cd ~/projects/hapax-council && uv run pytest tests/test_dmn_visual_observation.py -v`

Expected: 3 tests PASS.

- [ ] **Step 5: Run existing DMN tests for regressions**

Run: `cd ~/projects/hapax-council && uv run pytest tests/test_dmn_imagination_wiring.py tests/test_reverberation.py -v`

Expected: All existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add agents/dmn/pulse.py tests/test_dmn_visual_observation.py
git commit -m "feat(reverie): multimodal visual observation — DMN perceives rendered frame via gemini-flash"
```

---

## Phase 2: Dimension & Parameter Alignment

### Task 3: Rename `formant_character` → `diffusion` in Rust + WGSL

**Files:**
- Modify: `hapax-logos/crates/hapax-visual/src/uniform_buffer.rs`
- Modify: `hapax-logos/crates/hapax-visual/src/shaders/uniforms.wgsl`
- Modify: `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs`

- [ ] **Step 1: Rename in uniform_buffer.rs**

In `hapax-logos/crates/hapax-visual/src/uniform_buffer.rs`, make 3 changes:

Line 30: `pub formant_character: f32,` → `pub diffusion: f32,`

Line 31-32, update the comment: `// formant_character ends at offset 72` → `// diffusion ends at offset 72`

Line 59: `formant_character: 0.0,` → `diffusion: 0.0,`

Line 148: `formant_character: *dims.get("formant_character").unwrap_or(&0.0) as f32,` → `diffusion: *dims.get("diffusion").unwrap_or(&0.0) as f32,`

- [ ] **Step 2: Rename in uniforms.wgsl**

In `hapax-logos/crates/hapax-visual/src/shaders/uniforms.wgsl`, line 20:

`formant_character: f32,` → `diffusion: f32,`

- [ ] **Step 3: Rename in dynamic_pipeline.rs signal override**

In `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs`, line 557:

`"formant_character" => uniform_data.formant_character = v,` → `"diffusion" => uniform_data.diffusion = v,`

- [ ] **Step 4: Verify cargo build**

Run: `cd ~/projects/hapax-council/hapax-logos && cargo build --release -p hapax-visual 2>&1 | tail -5`

Expected: Compiles without errors.

- [ ] **Step 5: Commit**

```bash
git add hapax-logos/crates/hapax-visual/src/uniform_buffer.rs \
       hapax-logos/crates/hapax-visual/src/shaders/uniforms.wgsl \
       hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs
git commit -m "refactor(reverie): rename formant_character → diffusion in GPU uniform buffer"
```

---

### Task 4: Build per-node parameter override bridge in Rust

**Files:**
- Modify: `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs`

- [ ] **Step 1: Add param_order and current_params to DynamicPass**

In `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs`, add two fields to the `DynamicPass` struct (around line 82-94):

```rust
struct DynamicPass {
    node_id: String,
    render_pipeline: Option<wgpu::RenderPipeline>,
    compute_pipeline: Option<wgpu::ComputePipeline>,
    uniform_bind_group: Option<wgpu::BindGroup>,
    input_bind_group_layout: Option<wgpu::BindGroupLayout>,
    params_buffer: Option<wgpu::Buffer>,
    params_bind_group: Option<wgpu::BindGroup>,
    param_order: Vec<String>,
    current_params: Vec<f32>,
    inputs: Vec<String>,
    output: String,
    steps_per_frame: u32,
}
```

Remove the `#[allow(dead_code)]` from `params_buffer` since we'll now use it.

- [ ] **Step 2: Populate param_order and current_params at reload time**

In `try_reload()`, where `DynamicPass` is constructed (around line 494-505 for render passes, and the similar block for compute passes), add the new fields:

For the render pass construction (around line 494):
```rust
new_passes.push(DynamicPass {
    node_id: plan_pass.node_id.clone(),
    render_pipeline: Some(render_pipeline),
    compute_pipeline: None,
    uniform_bind_group: None,
    input_bind_group_layout: None,
    params_buffer: pbuf,
    params_bind_group: pbg,
    param_order: plan_pass.param_order.clone(),
    current_params: {
        let mut v: Vec<f32> = plan_pass.param_order.iter()
            .map(|name| plan_pass.uniforms.get(name).copied().unwrap_or(0.0) as f32)
            .collect();
        while v.len() < 4 { v.push(0.0); }
        while (v.len() * 4) % 16 != 0 { v.push(0.0); }
        v
    },
    inputs: plan_pass.inputs.clone(),
    output: plan_pass.output.clone(),
    steps_per_frame: plan_pass.steps_per_frame,
});
```

Do the same for compute pass construction (find the similar `new_passes.push(DynamicPass {` block for compute passes and add the same `param_order` and `current_params` fields).

- [ ] **Step 3: Apply per-node overrides each frame**

In the `render()` method, after the `signal.*` processing loop (after line 562, before `self.uniform_buffer.update(queue, &uniform_data);`), add the per-node override bridge:

```rust
                    // node.param keys: apply to per-pass params buffers
                    for pass in &mut self.passes {
                        if pass.params_buffer.is_none() || pass.param_order.is_empty() {
                            continue;
                        }
                        let mut updated = false;
                        for (i, name) in pass.param_order.iter().enumerate() {
                            if i >= pass.current_params.len() {
                                break;
                            }
                            let key = format!("{}.{}", pass.node_id, name);
                            if let Some(&val) = overrides.get(&key) {
                                let v = val as f32;
                                if (pass.current_params[i] - v).abs() > f32::EPSILON {
                                    pass.current_params[i] = v;
                                    updated = true;
                                }
                            }
                        }
                        if updated {
                            if let Some(ref buf) = pass.params_buffer {
                                queue.write_buffer(buf, 0, bytemuck::cast_slice(&pass.current_params));
                            }
                        }
                    }
```

This must be placed **inside** the `if let Ok(overrides) = ...` block, after the signal loop but before the closing braces.

- [ ] **Step 4: Remove the misleading comment**

Replace the comment at line 561:
```rust
                    // node.param keys handled per-pass via params buffers at reload time
```
With nothing (delete the line). The bridge code above now handles it.

- [ ] **Step 5: Fix borrow checker — change `&self.passes` to `&mut self.passes`**

The render method signature already takes `&mut self`. The loop over `self.passes` in the new code needs mutable access. Ensure the new loop uses `for pass in &mut self.passes` (not `&self.passes`). Also ensure there are no conflicting immutable borrows of `self.passes` in the same scope.

- [ ] **Step 6: Verify cargo build**

Run: `cd ~/projects/hapax-council/hapax-logos && cargo build --release -p hapax-visual 2>&1 | tail -10`

Expected: Compiles without errors.

- [ ] **Step 7: Commit**

```bash
git add hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs
git commit -m "feat(reverie): per-node param override bridge — visual chain deltas reach GPU shaders"
```

---

### Task 5: Fix visual chain technique names

**Files:**
- Modify: `agents/visual_chain.py`
- Test: `tests/test_visual_chain.py`

- [ ] **Step 1: Write test for correct param key format**

Add to `tests/test_visual_chain.py`:

```python
def test_param_deltas_use_vocabulary_node_ids():
    """Parameter delta keys must use vocabulary graph node IDs, not legacy technique names."""
    from agents.visual_chain import VisualChainCapability

    cap = VisualChainCapability()
    # Activate intensity to non-zero
    from agents._impingement import Impingement, ImpingementType

    imp = Impingement(
        timestamp=0.0,
        source="test",
        type=ImpingementType.SALIENCE_INTEGRATION,
        strength=0.8,
        content={},
    )
    cap.activate_dimension("visual_chain.intensity", imp, 0.8)

    deltas = cap.compute_param_deltas()
    # Must use vocabulary node IDs
    assert any(k.startswith("noise.") for k in deltas), f"Expected 'noise.' keys, got: {list(deltas.keys())}"
    assert any(k.startswith("post.") for k in deltas), f"Expected 'post.' keys, got: {list(deltas.keys())}"
    # Must NOT use legacy names
    assert not any(k.startswith("gradient.") for k in deltas), "Legacy 'gradient.' keys found"
    assert not any(k.startswith("compositor.") for k in deltas), "Legacy 'compositor.' keys found"
    assert not any(k.startswith("postprocess.") for k in deltas), "Legacy 'postprocess.' keys found"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/projects/hapax-council && uv run pytest tests/test_visual_chain.py::test_param_deltas_use_vocabulary_node_ids -v`

Expected: FAIL — keys currently start with `gradient.`, `compositor.`, `postprocess.`.

- [ ] **Step 3: Update technique names in visual_chain.py**

In `agents/visual_chain.py`, update all `ParameterMapping` instances in the `VISUAL_DIMENSIONS` dict:

Replace all occurrences of these technique names:
- `"gradient"` → `"noise"` (the noise_gen node receives gradient params like brightness, speed, turbulence, hue_offset, color_warmth, chroma_boost)
- `"postprocess"` → `"post"` (matches vocabulary node ID)
- `"feedback"` → `"fb"` (matches vocabulary node ID)
- Remove ALL `ParameterMapping` entries with technique `"compositor"` — the compositor node no longer exists. These are the bindings referencing `opacity_rd`, `opacity_wave`, `opacity_physarum`, `opacity_feedback`.

Leave `"rd"` and `"physarum"` unchanged — they match their node type names for when those nodes appear in custom presets.

Specifically, the full updated `VISUAL_DIMENSIONS` dict should have these technique names:

For `visual_chain.intensity`:
- `ParameterMapping("noise", "brightness", _STANDARD)` (was `"gradient"`)
- Remove `ParameterMapping("compositor", "opacity_rd", ...)` — dead
- `ParameterMapping("post", "vignette_strength", _INVERTED)` (was `"postprocess"`)

For `visual_chain.tension`:
- `ParameterMapping("rd", "f_delta", ...)` (unchanged)
- Remove `ParameterMapping("compositor", "opacity_wave", ...)` — dead
- `ParameterMapping("noise", "turbulence", ...)` (was `"gradient"`)

For `visual_chain.diffusion`:
- `ParameterMapping("physarum", "sensor_dist", ...)` (unchanged)
- `ParameterMapping("rd", "da_delta", ...)` (unchanged)
- Remove `ParameterMapping("compositor", "opacity_feedback", ...)` — dead

For `visual_chain.degradation`:
- `ParameterMapping("physarum", "deposit_amount", ...)` (unchanged)
- Remove `ParameterMapping("compositor", "opacity_physarum", ...)` — dead
- `ParameterMapping("post", "sediment_height", ...)` (was `"postprocess"`)

For `visual_chain.depth`:
- `ParameterMapping("noise", "brightness", _INVERTED)` (was `"gradient"`)
- `ParameterMapping("post", "vignette_strength", _STANDARD)` (was `"postprocess"`)
- Remove `ParameterMapping("compositor", "opacity_feedback", ...)` — dead

For `visual_chain.pitch_displacement`:
- `ParameterMapping("noise", "hue_offset", ...)` (was `"gradient"`)
- `ParameterMapping("fb", "hue_shift", ...)` (was `"feedback"`)
- `ParameterMapping("noise", "chroma_boost", ...)` (was `"gradient"`)

For `visual_chain.temporal_distortion`:
- `ParameterMapping("noise", "speed", ...)` (was `"gradient"`)
- `ParameterMapping("physarum", "move_speed", ...)` (unchanged)

For `visual_chain.spectral_color`:
- `ParameterMapping("noise", "color_warmth", ...)` (was `"gradient"`)
- `ParameterMapping("noise", "chroma_boost", ...)` (was `"gradient"`)

For `visual_chain.coherence`:
- `ParameterMapping("noise", "turbulence", _STANDARD)` (was `"gradient"`)
- `ParameterMapping("rd", "f_delta", ...)` (unchanged)
- `ParameterMapping("physarum", "turn_speed", ...)` (unchanged)

- [ ] **Step 4: Run tests**

Run: `cd ~/projects/hapax-council && uv run pytest tests/test_visual_chain.py -v`

Expected: All tests pass including the new one.

- [ ] **Step 5: Commit**

```bash
git add agents/visual_chain.py tests/test_visual_chain.py
git commit -m "fix(reverie): visual chain technique names match vocabulary graph node IDs"
```

---

### Task 6: Update actuation loop uniform key format

**Files:**
- Modify: `agents/reverie/actuation.py`

The actuation loop writes trace params as `feedback.trace_center_x`. With the vocabulary rename, these must become `fb.trace_center_x`.

- [ ] **Step 1: Update trace uniform keys in actuation.py**

In `agents/reverie/actuation.py`, in `_write_uniforms()` (around lines 217-222), update the key prefixes:

```python
        # Add trace state for feedback shader (Amendment 2: dwelling)
        if self._trace_strength > 0:
            uniforms["fb.trace_center_x"] = self._trace_center[0]
            uniforms["fb.trace_center_y"] = self._trace_center[1]
            uniforms["fb.trace_radius"] = self._trace_radius
            uniforms["fb.trace_strength"] = self._trace_strength
```

(Change `"feedback."` prefix to `"fb."` on all 4 lines.)

- [ ] **Step 2: Run existing tests**

Run: `cd ~/projects/hapax-council && uv run pytest tests/ -k "reverie or actuation or visual_chain" -v`

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add agents/reverie/actuation.py
git commit -m "fix(reverie): actuation loop uses 'fb.' prefix for feedback node params"
```

---

## Phase 3: Behavioral Refinements

### Task 7: Soften proactive gate pre-filter

**Files:**
- Modify: `agents/hapax_daimonion/run_loops_aux.py:146`
- Test: existing `tests/test_proactive_gate.py`

- [ ] **Step 1: Lower the pre-filter threshold**

In `agents/hapax_daimonion/run_loops_aux.py`, line 146:

```python
                            if imp.source == "imagination" and imp.strength >= 0.8:
```

Change to:

```python
                            if imp.source == "imagination" and imp.strength >= 0.65:
```

- [ ] **Step 2: Run proactive gate tests**

Run: `cd ~/projects/hapax-council && uv run pytest tests/test_proactive_gate.py -v`

Expected: All pass (the gate's internal sigmoid still governs behavior).

- [ ] **Step 3: Commit**

```bash
git add agents/hapax_daimonion/run_loops_aux.py
git commit -m "fix(reverie): soften proactive gate pre-filter 0.8 → 0.65 to match sigmoid range"
```

---

### Task 8: Per-slot immensity entry direction in content_layer shader

**Files:**
- Modify: `agents/shaders/nodes/content_layer.wgsl`

- [ ] **Step 1: Update immensity_entry to accept slot_index**

In `agents/shaders/nodes/content_layer.wgsl`, change the `immensity_entry` function (lines 50-55):

```wgsl
fn immensity_entry(uv: vec2<f32>, salience: f32, slot_index: f32) -> vec2<f32> {
    let entry_progress = smoothstep(0.0, 0.5, salience);
    let entry_offset = (1.0 - entry_progress) * 0.4;
    let entry_dir = vec2<f32>(sin(slot_index * 2.1), cos(slot_index * 1.7));
    return uv + entry_dir * entry_offset;
}
```

- [ ] **Step 2: Update sample_and_blend_slot to compute per-slot UVs**

Change `sample_and_blend_slot` to accept and use a slot_index parameter:

```wgsl
fn sample_and_blend_slot(
    slot_tex: texture_2d<f32>,
    samp: sampler,
    uv_base: vec2<f32>,
    uv_raw: vec2<f32>,
    opacity: f32,
    material_id: u32,
    time: f32,
    slot_index: f32,
    base: vec3<f32>,
) -> vec3<f32> {
    if opacity < 0.001 {
        return base;
    }
    // Per-slot UV: corner incubation + per-slot immensity + material
    var uv = corner_incubation(uv_raw, opacity);
    uv = immensity_entry(uv, opacity, slot_index);
    uv = material_uv(uv, material_id, time);

    let content = textureSample(slot_tex, samp, uv);
    let gated = content.rgb * materialization(uv_raw, opacity, time);
    let colored = material_color(gated, material_id);
    let weighted = colored * opacity;
    return 1.0 - (1.0 - base) * (1.0 - weighted);
}
```

- [ ] **Step 3: Update main_1 to pass slot indices and remove pre-computed UV**

Replace the `main_1` function:

```wgsl
fn main_1() {
    let uv_raw = v_texcoord_1;
    let time = uniforms.time;
    let material_id = u32(round(uniforms.custom[0][0]));

    // Sample procedural field at original UV (background unaffected by content distortion)
    var base = textureSample(tex, tex_sampler, uv_raw).rgb;

    // Screen-blend each content slot — per-slot UV with distinct immensity direction
    base = sample_and_blend_slot(content_slot_0, tex_sampler, uv_raw, uv_raw,
        uniforms.slot_opacities[0], material_id, time, 0.0, base);
    base = sample_and_blend_slot(content_slot_1, tex_sampler, uv_raw, uv_raw,
        uniforms.slot_opacities[1], material_id, time, 1.0, base);
    base = sample_and_blend_slot(content_slot_2, tex_sampler, uv_raw, uv_raw,
        uniforms.slot_opacities[2], material_id, time, 2.0, base);
    base = sample_and_blend_slot(content_slot_3, tex_sampler, uv_raw, uv_raw,
        uniforms.slot_opacities[3], material_id, time, 3.0, base);

    // Dwelling trace boost on final composited result
    let max_salience = max(max(uniforms.slot_opacities[0], uniforms.slot_opacities[1]),
                           max(uniforms.slot_opacities[2], uniforms.slot_opacities[3]));
    let trace_boost = dwelling_trace_boost(max_salience);
    base *= trace_boost;

    fragColor = vec4<f32>(base, 1.0);
    return;
}
```

- [ ] **Step 4: Verify WGSL compiles**

Run: `cd ~/projects/hapax-council && uv run python -c "
from agents.effect_graph.wgsl_transpiler import validate_wgsl
from pathlib import Path
src = Path('agents/shaders/nodes/content_layer.wgsl').read_text()
# Prepend uniforms struct for validation
uniforms = Path('hapax-logos/crates/hapax-visual/src/shaders/uniforms.wgsl').read_text()
print('Validating content_layer.wgsl...')
# naga validation if available
import subprocess
result = subprocess.run(['naga', '--validate', 'agents/shaders/nodes/content_layer.wgsl'], capture_output=True, text=True)
print(result.stdout or 'OK')
if result.returncode != 0:
    print('WARN:', result.stderr)
"`

If naga is not available for standalone WGSL validation, verify via compilation test:
Run: `cd ~/projects/hapax-council && uv run python -c "
import json
from agents.effect_graph.types import EffectGraph
from agents.effect_graph.wgsl_compiler import compile_to_wgsl_plan, write_wgsl_pipeline
raw = json.loads(open('presets/reverie_vocabulary.json').read())
graph = EffectGraph(**raw)
plan = compile_to_wgsl_plan(graph)
print('Compilation OK:', len(plan['passes']), 'passes')
"`

- [ ] **Step 5: Commit**

```bash
git add agents/shaders/nodes/content_layer.wgsl
git commit -m "feat(reverie): per-slot immensity entry direction — slots arrive from different angles"
```

---

### Task 9: Continuation-aware crossfade in Rust

**Files:**
- Modify: `hapax-logos/crates/hapax-visual/src/content_textures.rs`

- [ ] **Step 1: Add FadePhase enum and update SlotState**

In `hapax-logos/crates/hapax-visual/src/content_textures.rs`, add after the `ManifestSlot` struct:

```rust
#[derive(Debug, Clone, Copy, PartialEq)]
enum FadePhase {
    Idle,
    Active,
    FadingOut,
    Gap,
    FadingIn,
}
```

Update `SlotState` to include fade_phase and a gap timer:

```rust
struct SlotState {
    active: bool,
    opacity: f32,
    target_opacity: f32,
    path: String,
    fade_phase: FadePhase,
}

impl Default for SlotState {
    fn default() -> Self {
        Self {
            active: false,
            opacity: 0.0,
            target_opacity: 0.0,
            path: String::new(),
            fade_phase: FadePhase::Idle,
        }
    }
}
```

Add a field to `ContentTextureManager`:

```rust
    gap_timer: f32,
    pending_manifest: Option<SlotManifest>,
```

Initialize in `new()`:
```rust
    gap_timer: 0.0,
    pending_manifest: None,
```

- [ ] **Step 2: Update poll() for continuation-aware behavior**

Replace the `poll()` method:

```rust
    pub fn poll(&mut self, queue: &wgpu::Queue) {
        if self.last_poll.elapsed().as_millis() < 500 {
            return;
        }
        self.last_poll = Instant::now();

        let manifest = match Self::read_manifest() {
            Some(m) => m,
            None => return,
        };

        if manifest.fragment_id == self.current_fragment_id {
            return;
        }

        if manifest.continuation {
            // Continuation: simultaneous crossfade (existing behavior)
            self.apply_manifest(queue, &manifest);
            self.current_fragment_id = manifest.fragment_id.clone();
        } else {
            // Non-continuation: fade out first, then gap, then fade in
            for slot in &mut self.slots {
                if slot.active {
                    slot.target_opacity = 0.0;
                    slot.fade_phase = FadePhase::FadingOut;
                }
            }
            self.pending_manifest = Some(manifest);
            self.gap_timer = 0.0;
        }
    }

    fn apply_manifest(&mut self, queue: &wgpu::Queue, manifest: &SlotManifest) {
        for ms in &manifest.slots {
            if ms.index >= MAX_SLOTS { continue; }
            if ms.path != self.slots[ms.index].path {
                self.upload_jpeg(queue, ms.index, &ms.path);
            }
            self.slots[ms.index].active = true;
            self.slots[ms.index].target_opacity = ms.salience.clamp(0.0, 1.0);
            self.slots[ms.index].path = ms.path.clone();
            self.slots[ms.index].fade_phase = FadePhase::FadingIn;
        }
    }
```

- [ ] **Step 3: Update tick_fades for phase-aware behavior**

Replace `tick_fades()`:

```rust
    pub fn tick_fades(&mut self, dt: f32, queue: &wgpu::Queue) {
        let continuation_rate = FADE_RATE;       // 2.0 — ~0.5s crossfade
        let non_continuation_rate = 1.5_f32;     // slower fade for non-continuation

        // Check if all fading-out slots have finished
        if self.pending_manifest.is_some() {
            let all_faded = self.slots.iter().all(|s| {
                s.fade_phase != FadePhase::FadingOut || s.opacity <= 0.001
            });
            if all_faded {
                self.gap_timer += dt;
                if self.gap_timer >= 0.5 {
                    // Gap complete — apply pending manifest
                    if let Some(manifest) = self.pending_manifest.take() {
                        self.apply_manifest(queue, &manifest);
                        self.current_fragment_id = manifest.fragment_id.clone();
                    }
                    self.gap_timer = 0.0;
                }
            }
        }

        for slot in &mut self.slots {
            if !slot.active && slot.opacity <= 0.001 { continue; }

            let rate = match slot.fade_phase {
                FadePhase::FadingOut => non_continuation_rate,
                FadePhase::FadingIn => non_continuation_rate,
                _ => continuation_rate,
            };

            let diff = slot.target_opacity - slot.opacity;
            let step = rate * dt;
            if diff.abs() < step {
                slot.opacity = slot.target_opacity;
            } else {
                slot.opacity += diff.signum() * step;
            }
            if slot.opacity <= 0.001 && slot.target_opacity <= 0.001 {
                slot.active = false;
                slot.opacity = 0.0;
                slot.fade_phase = FadePhase::Idle;
            }
            if slot.opacity >= slot.target_opacity - 0.001 && slot.fade_phase == FadePhase::FadingIn {
                slot.fade_phase = FadePhase::Active;
            }
        }
    }
```

- [ ] **Step 4: Update tick_fades call site in main.rs**

The `tick_fades` method now takes `(dt, queue)` instead of just `(dt)`. Find the call site in `hapax-logos/src-imagination/src/main.rs` and update it. Search for `tick_fades` and pass the queue reference.

- [ ] **Step 5: Verify cargo build**

Run: `cd ~/projects/hapax-council/hapax-logos && cargo build --release -p hapax-imagination 2>&1 | tail -10`

Expected: Compiles without errors.

- [ ] **Step 6: Commit**

```bash
git add hapax-logos/crates/hapax-visual/src/content_textures.rs hapax-logos/src-imagination/src/main.rs
git commit -m "feat(reverie): continuation-aware crossfade — gap between non-continuation fragments"
```

---

### Task 10: Per-slot trace center tracking

**Files:**
- Modify: `agents/reverie/actuation.py`

- [ ] **Step 1: Add slot-based trace center approximation**

In `agents/reverie/actuation.py`, replace the `_update_trace` method:

```python
    # Per-slot approximate centers (matches content_layer.wgsl immensity_entry directions)
    _SLOT_CENTERS = {
        0: (0.4, 0.4),
        1: (0.6, 0.4),
        2: (0.4, 0.6),
        3: (0.6, 0.6),
    }

    def _update_trace(self, imagination: dict[str, object] | None, dt: float) -> None:
        """Update trace state for dwelling/trace effect (Bachelard Amendment 2).

        When content salience drops (fading out), the trace activates at the
        content's approximate position based on its slot index.
        """
        current_salience = imagination.get("salience", 0.0) if imagination else 0.0

        # Detect salience drop → activate trace
        if self._last_salience > 0.2 and current_salience < self._last_salience * 0.5:
            self._trace_strength = min(1.0, self._last_salience)
            self._trace_radius = 0.3 + self._last_salience * 0.2

            # Approximate center from primary content slot
            slot_idx = 0
            if imagination:
                refs = imagination.get("content_references", [])
                if refs and isinstance(refs, list) and len(refs) > 0:
                    # Use the highest-salience reference's index position
                    slot_idx = min(len(refs) - 1, 3)
            self._trace_center = self._SLOT_CENTERS.get(slot_idx, (0.5, 0.5))

            log.info(
                "Trace activated: strength=%.2f radius=%.2f center=%s (salience %.2f→%.2f)",
                self._trace_strength,
                self._trace_radius,
                self._trace_center,
                self._last_salience,
                current_salience,
            )

        # Decay trace strength over time
        if self._trace_strength > 0:
            self._trace_strength = max(0.0, self._trace_strength - self._trace_decay_rate * dt)

        self._last_salience = current_salience
```

- [ ] **Step 2: Run tests**

Run: `cd ~/projects/hapax-council && uv run pytest tests/ -k "reverie or actuation or visual_chain" -v`

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add agents/reverie/actuation.py
git commit -m "feat(reverie): per-slot trace center — afterimages positioned near fading content"
```

---

## Final: Build & Deploy

### Task 11: Rebuild hapax-imagination binary and verify

- [ ] **Step 1: Full cargo build**

Run: `cd ~/projects/hapax-council/hapax-logos && cargo build --release -p hapax-imagination 2>&1 | tail -15`

Expected: Build succeeds.

- [ ] **Step 2: Install binary**

Run: `cp ~/projects/hapax-council/hapax-logos/target/release/hapax-imagination ~/.local/bin/hapax-imagination`

- [ ] **Step 3: Restart service**

Run: `systemctl --user restart hapax-imagination.service && sleep 2 && systemctl --user status hapax-imagination.service`

Expected: Active (running).

- [ ] **Step 4: Recompile vocabulary graph**

Run: `cd ~/projects/hapax-council && uv run python -c "
from agents.reverie.bootstrap import write_vocabulary_plan
ok = write_vocabulary_plan()
print('Vocabulary written:', ok)
"`

Expected: `Vocabulary written: True`

- [ ] **Step 5: Run full test suite**

Run: `cd ~/projects/hapax-council && uv run pytest tests/ -q --ignore=tests/hapax_daimonion -x`

Expected: All tests pass.

- [ ] **Step 6: Run lint**

Run: `cd ~/projects/hapax-council && uv run ruff check agents/dmn/pulse.py agents/visual_chain.py agents/reverie/actuation.py agents/shaders/nodes/content_layer.wgsl`

Expected: Clean.

- [ ] **Step 7: Final commit if any lint fixes**

```bash
git add -A && git commit -m "chore: lint fixes" || echo "nothing to commit"
```
