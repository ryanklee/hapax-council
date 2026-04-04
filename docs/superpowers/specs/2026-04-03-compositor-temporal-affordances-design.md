# Compositor Temporal Feedback + Studio Affordances — Design Specification

**Date:** 2026-04-03
**Status:** Draft
**Scope:** GStreamer SlotPipeline temporal feedback via glfilterapp + studio control affordances
**Depends on:** Total Affordance Field (2026-04-03), Effect Graph system, Studio Compositor
**Preserves:** SCM Property 1 (compositor and Reverie remain separate S1 components), Bachelard generative substrate (untouched), VSM viability (independent failure modes)

---

## 1. Problem Statement

The GStreamer SlotPipeline uses `glshader` elements that process frames statelessly — no temporal feedback between frames. 8 of 56 node types require temporal state (trail, feedback, echo, stutter, slitscan, diff, reaction_diffusion, fluid_sim). These nodes compile but produce no visible effect because `tex_accum` is never bound. 5 presets are structurally broken (datamosh, glitch_blocks, screwed use stutter; slitscan_preset uses slitscan; diff_preset uses diff).

Additionally, the studio compositor has 20+ control surfaces (preset selection, node parameters, layer control, modulation binding, graph manipulation, camera selection) exposed via API endpoints but NOT registered as affordances. The system cannot recruit compositor controls through the affordance pipeline.

## 2. Theoretical Compliance

### 2.1 Why this is NOT the Reverie merger

The compositor and Reverie are distinct S1 components (SCM S1 table). They have different controlled perceptions ("camera composition" vs "expressive visual field"), different output traces, different control laws, different failure modes. This spec adds temporal feedback to the compositor's OWN GL pipeline — it does not route camera processing through Reverie.

The generative substrate principle is preserved: the vocabulary graph always runs, never recruited. Camera FX presets are "expression styles, not expression capabilities" (USR spec §8.3) — they are aesthetic processing of perception, not imagination-driven expression.

### 2.2 Studio affordances as Gibson-verb capabilities

Studio controls are affordances of the production environment. In Gibson's ecological framework, the mixing desk affords adjustment, the camera affords perspective selection, the effect chain affords aesthetic transformation. These are genuine affordances of the operator's niche — the hip hop production studio.

Registering them in the shared affordance registry means:
- The DMN imagination can recruit "adjust visual warmth" when imagining about atmosphere
- The voice daemon can recruit "switch to thermal view" when the operator mentions heat
- Reverie can recruit "activate glitch preset" when imagination narrative matches corruption/disruption

Each faculty discovers these affordances through its own dynamics. The compositor handles the activation. Pure stigmergic coordination.

## 3. Architecture

### 3.1 Temporal Feedback via glfilterapp

Replace `glshader` with `glfilterapp` for slots where `ExecutionStep.temporal == True`. The `glfilterapp` element emits a `render` signal on the GL thread, giving us direct GL context access to manage ping-pong FBOs.

**Data flow for a temporal slot:**

```
Frame N arrives at glfilterapp sink pad
  → GStreamer calls render(context, input_texture_id, output_fbo)
  → Callback:
    1. Bind the compiled GstGLShader
    2. Bind input_texture_id as sampler uniform "tex" (current frame)
    3. Bind accum_texture_id as sampler uniform "tex_accum" (previous output)
    4. Set float uniforms (u_fade, u_opacity, etc.)
    5. Draw fullscreen quad into output_fbo
    6. Copy output_fbo color attachment → accum_texture (for next frame)
    7. Swap ping-pong if using double-buffering
```

**Implementation in SlotPipeline:**

- `_temporal_textures: dict[int, int]` — slot_idx → GL texture ID for accumulation buffer
- `_temporal_shaders: dict[int, GstGL.GLShader]` — slot_idx → compiled shader (held across frames)
- `create_slots()`: temporal steps get `glfilterapp` instead of `glshader`
- `_on_render(element, context, fbo, slot_idx)`: the render callback implementing the ping-pong
- `activate_plan()`: allocates GL textures for temporal slots via the GL context
- Non-temporal slots continue using `glshader` (zero performance overhead)

### 3.2 Studio Affordances

Register compositor controls in `shared/affordance_registry.py` as a new `studio_control` domain. Add relay commands for each control. Wire dispatch in the daimonion consumer loop.

**Affordance categories:**

| Category | Affordances | Handler |
|---|---|---|
| Preset | `studio.activate_preset`, `studio.cycle_preset` | POST /studio/effect/select |
| Node params | `studio.adjust_node_param` | PATCH /studio/effect/graph/node/{id}/params |
| Layer | `studio.toggle_layer`, `studio.adjust_layer_palette` | PATCH /studio/layer/{layer}/enabled, palette |
| Modulation | `studio.bind_modulation` | PUT /studio/effect/graph/modulations |
| Graph | `studio.add_node`, `studio.remove_node` | PATCH /studio/effect/graph |
| Camera | `studio.select_camera` | POST /studio/camera/select |
| Recording | `studio.toggle_recording` | POST /studio/recording/enable/disable |
| Composition | `studio.adjust_composition` | Composite control |

Each affordance gets a Gibson-verb description for Qdrant embedding:
- `studio.activate_preset`: "Transform the camera aesthetic by activating a visual effect preset"
- `studio.adjust_warmth`: "Shift the visual warmth and color temperature of the camera composition"
- `studio.select_camera`: "Choose which camera perspective dominates the studio composition"
- etc.

### 3.3 Dynamic Output Node Affordances

Output destinations are also affordances. Each output path in the compositor represents a different way the visual result can be expressed:

| Output | Affordance | Description |
|---|---|---|
| v4l2sink (virtual webcam) | `studio.output_webcam` | Route the composed visual to the virtual webcam for streaming or conferencing |
| HLS stream | `studio.output_stream` | Broadcast the composed visual as an HLS live stream |
| FX snapshot | `studio.output_snapshot` | Capture the current effected frame as a high-quality still |
| Smooth delay | `studio.output_smooth` | Route through the temporal smoothing delay branch |
| Recording | `studio.output_record` | Record the composed visual to disk as a video segment |
| Fullscreen preview | `studio.output_fullscreen` | Display the composed visual fullscreen with overlay controls |

These are dynamically available — the system can recruit "capture a snapshot" or "start recording" based on imagination or operator intent. Output nodes in the React Flow graph should also register as affordances when they exist, so the graph's own topology feeds the affordance space.

## 4. Implementation Plan

### Phase 1: Temporal Feedback (SlotPipeline)

1. Extend `SlotPipeline` to detect temporal steps and create `glfilterapp` elements
2. Implement the `render` callback with ping-pong FBO management
3. Wire shader compilation and uniform setting for glfilterapp slots
4. Test with trails, feedback, stutter, echo, diff, slitscan presets
5. Verify temporal effects visible in fullscreen output at 10fps 720p

### Phase 2: Studio Affordances

1. Add ~15 studio control affordances to `shared/affordance_registry.py`
2. Add relay commands in `hapax-logos/src/lib/commands/studio.ts`
3. Wire dispatch in daimonion consumer loop for `studio.*` affordances
4. Verify recruitment: imagination narrative about "glitch" recruits `studio.activate_preset`

### Phase 3: Preset Audit

With temporal effects working, systematically verify all 28 presets against their 4 defining characteristics.

## 5. Performance

- `glfilterapp` has negligible overhead vs `glshader` — same GL context, same thread
- Ping-pong FBO management adds one `glCopyTexSubImage2D` per temporal slot per frame
- At 1080p with 2 temporal slots: ~0.5ms per frame overhead (texture copy only)
- Non-temporal slots unchanged — zero regression for spatial effects
- Total budget: <2ms per frame at 30fps (well within the 33ms frame budget)
