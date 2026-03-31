# Satellite Node Recruitment

**Date:** 2026-03-31
**Status:** Design approved
**Context:** Phase 3b of the Reverie Adaptive Compositor. The mixer can dynamically recruit any of 54 shader nodes into the live graph based on impingement cascade affordance matching.

---

## Design Decisions

| Question | Decision |
|----------|----------|
| Which nodes can be recruited | Any of the 54 shader nodes |
| Insertion strategy | Static layer classification (generation→color→spatial→temporal→content→effects→detection→post) |
| Recruitment trigger | Affordance match above 0.3 threshold |
| Dismissal | Decay-based (compressor release), dismissed below 0.05 |
| Graph rebuild mechanism | Mutate EffectGraph, recompile via existing compiler, hot-reload via inotify |
| Rust changes | None — DynamicPipeline already handles arbitrary graphs |

---

## 1. Layer Classification

Each node type has a layer index determining its position in the graph. When inserting a recruited satellite, it goes after existing nodes of its layer or earlier, before nodes of its layer or later.

```python
NODE_LAYERS: dict[str, int] = {
    # Layer 0: Generation (produce pixels from nothing)
    "noise_gen": 0, "solid": 0,
    # Layer 1: Reaction/Simulation (temporal self-organizing)
    "reaction_diffusion": 1, "fluid_sim": 1,
    # Layer 2: Color (palette, grading, mapping)
    "colorgrade": 2, "color_map": 2, "thermal": 2, "nightvision": 2, "invert": 2,
    # Layer 3: Spatial (displacement, warping, geometry)
    "drift": 3, "warp": 3, "displacement_map": 3, "fisheye": 3, "mirror": 3,
    "kaleidoscope": 3, "tile": 3, "tunnel": 3, "droste": 3,
    # Layer 4: Temporal (feedback, trails, stutters)
    "breathing": 4, "feedback": 4, "trail": 4, "echo": 4, "stutter": 4,
    "slitscan": 4, "syrup": 4,
    # Layer 5: Content (compositing, blending)
    "content_layer": 5, "blend": 5, "crossfade": 5,
    # Layer 6: Effects (stylization, artifacts)
    "bloom": 6, "chromatic_aberration": 6, "glitch_block": 6, "pixsort": 6,
    "halftone": 6, "ascii": 6, "dither": 6, "vhs": 6, "datamosh": 6,
    "scanlines": 6, "noise_overlay": 6, "strobe": 6,
    # Layer 7: Detection (analysis, keying)
    "edge_detect": 7, "diff": 7, "luma_key": 7, "chroma_key": 7,
    "silhouette": 7, "threshold": 7, "emboss": 7, "sharpen": 7,
    # Layer 8: Post (final processing)
    "postprocess": 8, "vignette": 8, "rutt_etra": 8, "waveform_render": 8,
    "posterize": 8, "circular_mask": 8,
}
DEFAULT_LAYER = 6  # Effects — safe middle position for unknown nodes
```

This is a signal-flow classification, not a semantic mapping. Generation happens first, post happens last.

---

## 2. Graph Builder

`agents/reverie/_graph_builder.py` — builds an EffectGraph from the core vocabulary plus recruited satellites.

```python
def build_graph(
    core_vocab: dict,
    recruited: dict[str, float],
) -> EffectGraph:
    """Build graph with core nodes + recruited satellites inserted at layer-appropriate positions."""
```

Algorithm:
1. Start with core vocabulary nodes and edges
2. For each recruited node type, create a node with default params from the shader registry
3. Sort all nodes by layer index
4. Build edges as a linear chain following the sorted order
5. Return EffectGraph

The `output` node is always last. The `content_layer` node retains its special `content_slot_N` inputs regardless of position.

---

## 3. Mixer Integration

In `ReverieMixer`:

**State:**
```python
self._recruited: dict[str, float] = {}  # node_type → activation strength
self._last_graph_rebuild = 0.0
self._graph_rebuild_cooldown = 2.0  # seconds
self._core_vocab: dict = {}  # loaded from reverie_vocabulary.json at init
```

**In `dispatch_impingement()`:**
When a `node.*` affordance matches above 0.3:
```python
node_type = candidate.capability_name.removeprefix("node.")
self._recruited[node_type] = max(
    self._recruited.get(node_type, 0.0),
    candidate.combined,
)
```

**In `tick()`:**
After decaying visual chain dimensions, also decay satellite strengths:
```python
for node_type in list(self._recruited):
    self._recruited[node_type] -= self._decay_rate * dt
    if self._recruited[node_type] < 0.05:
        del self._recruited[node_type]
```

If the set of recruited node types changed and cooldown has elapsed, rebuild the graph:
```python
if self._recruited_set_changed() and self._can_rebuild():
    graph = build_graph(self._core_vocab, self._recruited)
    plan = compile_to_wgsl_plan(graph)
    write_wgsl_pipeline(plan)
    log.info("Graph rebuilt: %d passes (%d satellites)", len(plan["passes"]), len(self._recruited))
```

---

## 4. Bootstrap Change

`agents/reverie/bootstrap.py` — expose the loaded vocabulary dict so the mixer can clone it:

```python
def load_vocabulary() -> dict:
    """Load the vocabulary preset as a raw dict (for mixer to clone and mutate)."""
    preset_path = PRESET_DIR / VOCABULARY_PRESET
    return json.loads(preset_path.read_text())
```

The mixer calls this at init to cache `self._core_vocab`.

---

## 5. Monitoring

Visual salience output adds `satellites_active`:
```json
{
  "source": "reverie",
  "signals": {
    "salience": 0.6,
    "content_density": 2,
    "satellites_active": 3,
    "regime_shift": false
  }
}
```

Recruitment and dismissal logged at INFO level.
