# Optical Flow Shader Node — Implementation Plan

**Goal:** Add a temporal `optical_flow` node with motion vector output for motion-aware effects.
**Spec:** `~/.cache/hapax/specs/2026-03-31-optical-flow-node-design.md`
**Tech Stack:** WGSL (hand-authored), Python 3.12, Rust/wgpu, pytest

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans.

---

## Phase 1: Shader + Node Definition

### Task 1.1: Create optical_flow node manifest

**Files:**
- Create: `agents/shaders/nodes/optical_flow.json`

- [ ] **Step 1:** Write manifest:
  ```json
  {
    "type": "optical_flow",
    "description": "Lucas-Kanade optical flow — motion vector output",
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

- [ ] **Step 2:** Verify registry loads it: `uv run python -c "from agents.effect_graph.registry import ShaderRegistry; r = ShaderRegistry(); print('optical_flow' in r.node_types)"`

- [ ] **Step 3:** Commit: `feat(shaders): add optical_flow node manifest`

### Task 1.2: Write the WGSL shader

**Files:**
- Create: `agents/shaders/nodes/optical_flow.wgsl`

- [ ] **Step 1:** Implement combined 2-pass shader:
  - Pass logic selected by `u_pass_index` uniform (0 = gradient, 1 = LK integration)
  - Pass 0: Sobel Ix/Iy from luminance, temporal derivative It from prev frame
  - Pass 1: 5x5 weighted window, Cramer's rule for (dx, dy), encode to RG channels
  - Output: R = dx (0.5 = zero), G = dy (0.5 = zero), B = magnitude, A = confidence

- [ ] **Step 2:** Test shader compiles with naga: `naga agents/shaders/nodes/optical_flow.wgsl`

- [ ] **Step 3:** Commit: `feat(shaders): implement Lucas-Kanade optical flow WGSL shader`

### Task 1.3: Support multi-output nodes in compiler

**Files:**
- Modify: `agents/effect_graph/compiler.py`
- Modify: `agents/effect_graph/types.py`

- [ ] **Step 1:** Allow nodes with multiple output ports in `_build()`. Currently assumes single `out` port. Add support for named outputs (e.g., `optical_flow:motion`).

- [ ] **Step 2:** In edge resolution, allow `optical_flow:motion` as a source that maps to a secondary output texture.

- [ ] **Step 3:** Write tests: graph with `optical_flow:motion` → `trail:displacement` edge compiles.

- [ ] **Step 4:** Commit: `feat(compiler): support multi-output nodes`

---

## Phase 2: Pipeline Integration

### Task 2.1: Extend WGSL compiler for multi-output

**Files:**
- Modify: `agents/effect_graph/wgsl_compiler.py`

- [ ] **Step 1:** In `compile_to_wgsl_plan()`, emit secondary output in plan.json:
  ```json
  {
    "node_id": "flow",
    "outputs": { "out": "layer_2", "motion": "layer_2_motion" },
    "steps_per_frame": 2
  }
  ```

- [ ] **Step 2:** Downstream passes referencing `optical_flow:motion` resolve to `layer_2_motion`.

- [ ] **Step 3:** Run WGSL compiler tests.

- [ ] **Step 4:** Commit: `feat(wgsl-compiler): emit multi-output pass descriptors`

### Task 2.2: Extend Rust DynamicPipeline for multi-output

**Files:**
- Modify: `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs`

- [ ] **Step 1:** Support `outputs` object (not just single `output` string) in PlanPass.

- [ ] **Step 2:** Create multiple output textures when `outputs` has >1 entry.

- [ ] **Step 3:** Bind secondary output textures in render pass (MRT or separate pass with different output target).

- [ ] **Step 4:** Build: `cargo build -p hapax-visual`

- [ ] **Step 5:** Commit: `feat(dynamic-pipeline): multi-output texture support`

---

## Phase 3: Demo Preset + Validation

### Task 3.1: Create motion_trails preset

**Files:**
- Create: `presets/motion_trails.json`

- [ ] **Step 1:** Write preset that routes optical_flow:motion → trail:displacement.

- [ ] **Step 2:** Compile and verify plan.json structure.

- [ ] **Step 3:** End-to-end test: activate preset, verify trails follow motion.

- [ ] **Step 4:** Commit: `feat(presets): add motion_trails optical-flow demo preset`

---

## Acceptance Gates

| Gate | Condition |
|------|-----------|
| Phase 1 | Node loads in registry. Shader passes naga validation. Multi-output graphs compile. |
| Phase 2 | plan.json emits multi-output. Rust pipeline creates secondary textures. |
| Phase 3 | motion_trails preset renders with visible motion-dependent trail thickness. |
