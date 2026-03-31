# Optical Flow Shader Node — Design Spec

**Date:** 2026-03-31
**Author:** delta session
**Status:** Design approved, pending implementation
**Motivation:** The effect graph has no motion estimation capability. Datamosh, displacement_map, and trail nodes operate blindly on pixel data without understanding motion. A Lucas-Kanade optical flow node would enable motion-aware effects: content-following trails, motion-vector-driven datamosh, and velocity-based color mapping.
**Depends on:** 2026-03-31-studio-effects-consolidation-design.md (Stage 1)

---

## Problem

1. **No motion information in the graph.** All 56 shader nodes operate on spatial data (current frame) or temporal data (accumulated frames). None compute motion vectors.
2. **Datamosh is fake.** The current `diff` node computes frame difference but cannot hallucinate motion vectors for authentic H.264-style datamosh (Takeshi Murata lineage per requirements doc §16).
3. **Displacement has no source.** The `displacement_map` node accepts a displacement texture but nothing generates one from actual motion.
4. **Trail thickness is uniform.** Per requirements §16, trails should have motion-dependent thickness. Without optical flow, this is impossible.

---

## Solution

Add an `optical_flow` temporal shader node that computes per-pixel motion vectors via a fragment-shader Lucas-Kanade approximation. Output is a FRAME-type texture where RG channels encode (dx, dy) motion vectors, usable as input to downstream nodes.

### Design Decisions

- **D1: Fragment shader, not compute.** Keeps compatibility with the existing render-pass pipeline. Lower quality than NVOFA but no CUDA dependency and works on any GPU.
- **D2: Dual-pass pyramid.** Two render passes per frame: (1) gradient computation (Sobel + temporal derivative), (2) local window integration (5x5 weighted). Stored as temporal ping-pong.
- **D3: Output as FRAME port.** Motion vectors encoded in RG channels (normalized to [-1, 1] → [0, 1] for texture storage). Blue channel = magnitude. This is a standard FRAME port, connectable to any node's input.
- **D4: Half-resolution.** Compute at 960x540 (half the 1920x1080 target) for performance. Bilinear upsample when consumed at full resolution.

---

## Architecture

### Node Definition

```json
{
  "type": "optical_flow",
  "inputs": { "in": "frame" },
  "outputs": { "out": "frame", "motion": "frame" },
  "params": {
    "window_size": { "type": "int", "default": 5, "min": 3, "max": 11 },
    "sensitivity": { "type": "float", "default": 1.0, "min": 0.1, "max": 5.0 },
    "threshold": { "type": "float", "default": 0.01, "min": 0.0, "max": 0.1 }
  },
  "temporal": true,
  "temporal_buffers": 2
}
```

**Ports:**
- `in` (FRAME): Current frame
- `out` (FRAME): Pass-through of input (for chaining)
- `motion` (FRAME): Motion vector texture (RG = dx/dy, B = magnitude, A = confidence)

### Shader Passes

**Pass 1: Gradient computation** (`optical_flow_grad.wgsl`)
- Input: current frame + previous frame (from temporal buffer)
- Compute: Sobel Ix, Iy (spatial gradients) + It (temporal derivative)
- Output: Gradient texture (R=Ix, G=Iy, B=It, A=luminance)

**Pass 2: Lucas-Kanade integration** (`optical_flow_lk.wgsl`)
- Input: Gradient texture
- Compute: Per-pixel 5x5 weighted window, solve 2x2 linear system (Cramer's rule)
- Output: Motion vector texture (R=dx, G=dy, B=magnitude, A=eigenvalue ratio for confidence)
- Threshold: Discard vectors where min eigenvalue < threshold (aperture problem)

### Integration Examples

**Motion-aware trails:**
```json
{
  "edges": [
    ["@live", "flow:in"],
    ["flow:motion", "trail:displacement"],
    ["flow:out", "trail:in"],
    ["trail:out", "out:in"]
  ]
}
```

**Authentic datamosh:**
```json
{
  "edges": [
    ["@live", "flow:in"],
    ["flow:motion", "datamosh:vectors"],
    ["flow:out", "datamosh:in"],
    ["datamosh:out", "out:in"]
  ]
}
```

---

## File Map

### New files

| File | Purpose |
|------|---------|
| `agents/shaders/nodes/optical_flow.json` | Node manifest (temporal, 2 buffers, 2 outputs) |
| `agents/shaders/nodes/optical_flow.wgsl` | Combined gradient + LK shader (2-pass via steps_per_frame) |
| `presets/motion_trails.json` | Demo preset: optical-flow-driven trails |

### Modified files

| File | Change |
|------|--------|
| `agents/effect_graph/compiler.py` | Support multi-output nodes (motion port routing) |
| `agents/effect_graph/wgsl_compiler.py` | Emit secondary output texture in plan.json |
| `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs` | Handle nodes with 2 output textures |

---

## Acceptance Criteria

1. `optical_flow` node loads in registry with 2 temporal buffers.
2. A preset using `optical_flow` compiles and generates valid plan.json with 2 passes.
3. Motion vector output visually correct: static regions = (0.5, 0.5, 0), moving regions = colored by direction.
4. `motion_trails` preset renders trails with motion-dependent thickness.
5. Performance: <5ms per frame at 960x540 on RTX 3090.
6. All existing presets unaffected (no regression).

## Constraints

- **Half-resolution:** 960x540 compute, bilinear upsample. Full-resolution LK is too expensive (~15ms).
- **No sub-pixel accuracy.** Fragment-shader LK is integer-pixel. Sufficient for visual effects, not for tracking.
- **Window size tradeoff.** Larger windows handle faster motion but blur small-object vectors. Default 5x5 balances.
- **Temporal buffers:** 2 required (current frame + previous frame for gradient). Adds ~4 MB VRAM at half-res.
- **Multi-output nodes:** This is the first node with 2 output ports. Requires compiler and pipeline extension (small).
