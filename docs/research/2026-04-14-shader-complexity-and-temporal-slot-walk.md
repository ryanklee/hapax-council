# Shader complexity survey + temporal slot dead code

**Date:** 2026-04-14
**Author:** delta (beta role — cam-stability focus)
**Scope:** Second drop in the effect-system walk. Drop
#44 covered the preset + layer + governance control
plane. This drop inventories the **shader node library
itself** — the 59 GLSL fragment shaders that actually
run on the GPU when a preset's execution plan activates.
Identifies the expensive shaders, quantifies per-fragment
sample counts, and flags one more dead feature in the
effect_graph module (`TemporalSlotState`).
**Register:** scientific, neutral
**Status:** investigation — 4 findings. No code changed.
**Companion:** drop #38 (SlotPipeline architecture),
drop #44 (preset + governance walk)

## Headline

**bloom and thermal both do a full 5×5 kernel (26 texture
samples per fragment).** At 1920×1080 × 30 fps that's
**~1.6 billion texture samples per second** per slot if
either shader is active. Both appear in
`_default_modulations.json`, meaning they're targets for
default modulations whenever a preset includes them — so
they're the dominant GPU cost among the shader nodes
likely to be active.

**Four findings:**

1. **`TemporalSlotState` is dead code** — no caller
   imports it. glfeedback's Rust plugin owns ping-pong
   buffer state internally; the Python class is orphaned.
2. **`temporal_buffers` field in node manifests is
   declaratively meaningless at runtime.** `stutter.json`
   declares `temporal_buffers=8` but `stutter.frag` only
   uses one `tex_accum` uniform. glfeedback allocates
   exactly 1 accumulation buffer per slot regardless of
   the declared count.
3. **Three shaders dominate GPU cost**: `bloom` (26
   samples, 5×5 kernel), `thermal` (27 samples, 5×5
   kernel + threshold-based colormap), `pixsort` (up to
   ~130 samples per fragment in interval detection + sort
   loops, plus 12-element bubble sort and dynamic
   indexing).
4. **`ascii`, `glitch_block`, `pixsort` have heavy
   branching**: 12, 8, and 13 conditionals respectively.
   Modern GPUs handle warp divergence but per-fragment
   branching still causes execution serialization within
   warps.

## 1. Shader node library

```text
agents/shaders/nodes/
  *.json   — 59 node manifests
  *.frag   — 55 GLSL fragment shaders (matching manifests)
  *.wgsl   — 56 WGSL alternatives (for the Reverie wgpu path)
```

**Temporal nodes** (8 nodes):

```text
node_type              temporal_buffers  uses tex_accum
diff                                  1  yes
echo                                  1  yes
feedback                              1  yes
fluid_sim                             1  yes
reaction_diffusion                    1  yes
slitscan                              1  yes
stutter                               8  yes (but only 1 sampler)
trail                                 1  yes
```

**All 8 temporal shaders use exactly one `tex_accum`
uniform.** The 8 declared in `stutter.json` is either
a documentation error or an aspirational marker that was
never implemented.

## 2. Findings

### 2.1 Finding 1 — `TemporalSlotState` is dead code

`agents/effect_graph/temporal_slot.py` — 63 lines
implementing a `TemporalSlotState` class that tracks
ping-pong texture IDs, current index, and swap state.

```text
$ grep -rn 'TemporalSlotState\|temporal_slot' agents/ | grep -v '__pycache__' | grep -v 'temporal_slot.py'
(no results)
```

**No caller imports it.** The class was written for an
earlier Python-side ping-pong implementation that was
superseded when the `glfeedback` Rust plugin took over
buffer management. The file was never removed.

**Fix** (Ring 1): delete `agents/effect_graph/temporal_slot.py`.
63 lines of dead surface area eliminated. Zero risk.

**Cumulative with drop #44**: this is the **third dead
feature** in the effect_graph module, after `LayerPalette`
and `PresetInput`/`resolve_preset_inputs`. Combined
LOC reduction if all three ship: ~100+ lines.

### 2.2 Finding 2 — `temporal_buffers` declaration is
meaningless at runtime

`agents/shaders/nodes/stutter.json`:

```json
{
  "node_type": "stutter",
  ...
  "temporal": true,
  "temporal_buffers": 8
}
```

`stutter.frag` uses exactly one `tex_accum` uniform:

```glsl
uniform sampler2D tex;
uniform sampler2D tex_accum;   // ← one
```

No `tex_accum_1`, `tex_accum_2`, etc. No ring-buffer
addressing. The shader implements stutter/freeze behavior
by conditionally holding `tex_accum` (the single previous
frame) for N ticks — it's a 1-buffer state held across
multiple frames, not an 8-frame ring.

The `temporal_buffers=8` declaration in JSON is parsed
into `LoadedShaderDef.temporal_buffers` in the shader
registry and exposed via `ExecutionStep.temporal_buffers`
in the compiler, but **nothing downstream uses the
value**. glfeedback's Rust plugin allocates 1 tex_accum
per slot regardless.

**Observation**: this is a declarative intention that was
never implemented. Either:

- **Option A**: implement multi-buffer temporal accumulation
  in glfeedback (large Rust change)
- **Option B**: remove `temporal_buffers` from the
  manifest schema and from `LoadedShaderDef` /
  `ExecutionStep` (cleanup)
- **Option C**: leave it as is, document the mismatch

**Recommendation**: Option B is safest (~20 lines of
removal across schema + compiler + runtime). Option A is
meaningful feature work if the operator wants true N-frame
stutter behavior but it's not requested.

### 2.3 Finding 3 — bloom and thermal dominate GPU cost

Loop-aware static analysis of the 55 shader sources:

```text
shader                       literal  simple  nested  est_samples
pixsort.frag                       5       3       0           29
bloom.frag                         2       0       1           27
thermal.frag                       2       0       1           27
fluid_sim.frag                    11       0       0           11
edge_detect.frag                   9       0       0            9
glitch_block.frag                  7       0       0            7
reaction_diffusion.frag            6       0       0            6
sharpen.frag                       5       0       0            5
ascii.frag                         4       0       0            4
chromatic_aberration.frag          4       0       0            4
slitscan.frag                      4       0       0            4
vhs.frag                           4       0       0            4
```

(`literal` = direct `texture2D(tex, ...)` calls outside
loops; `simple` = single for-loop with texture sampling;
`nested` = nested for-loops with texture sampling.
`est_samples` is an upper-bound per fragment assuming
5-element loop bodies.)

**bloom.frag**:

```glsl
void main() {
    vec4 c = texture2D(tex, v_texcoord);                  // 1 sample
    ...
    for (float x=-2.0; x<=2.0; x+=1.0)
        for (float y=-2.0; y<=2.0; y+=1.0) {
            vec4 s = texture2D(tex, v_texcoord + vec2(x,y)*tx);  // 25 samples
            ...
        }
    ...
}
```

**5×5 kernel = 25 samples + 1 center = 26 samples per
fragment.** At 1920×1080 × 30 fps:

- **~1.6 billion texture samples per second** when bloom
  is active
- GPU memory bandwidth: 26 samples × 4 bytes × 2.07M
  pixels × 30 fps ≈ **6.5 GB/s** of texture memory
  bandwidth per frame

**thermal.frag** has the same 5×5 kernel structure (5×5
neighborhood sample for thermal mapping). Same cost profile.

**pixsort.frag** is worse in theory (has 2 outer interval
detection loops capped at 64 each, plus sample collection
+ bubble sort) — up to **~130 samples per fragment** in
the worst case. But most fragments short-circuit on the
brightness threshold gate and sample only 1 texel.

**Context from presets** (grep of which presets use which
shaders):

- **bloom**: `heartbeat`, `neon`, `mirror_rorschach`,
  `screwed`, `ambient` (5 presets)
- **thermal**: `thermal_preset` only
- **pixsort**: `pixsort_preset` only

And `_default_modulations.json` has default modulations
for `bloom` (alpha), `vignette`, `chromatic_aberration`,
`colorgrade`, `trail`, `drift`, `noise_overlay` —
**`bloom` is one of the 7 nodes with a default
modulation**, so any preset that includes bloom
automatically gets its alpha modulated by the audio
sidechain.

**This means bloom is the single most common expensive
shader** in actively-used presets (5 out of 28 presets
include it, and it's one of the heaviest per-fragment).

**Optimization options**:

- **FXS-1**: Separable Gaussian blur — bloom's nested
  5×5 kernel is mathematically equivalent to two passes
  of 5×1 blur (horizontal then vertical). 5+5=10 samples
  per fragment instead of 25, across 2 passes = 20
  texture-sample operations total, or **23% reduction**
  in sampling work. Requires rewriting bloom.frag to
  support directional mode + the fx chain to run it as 2
  slots instead of 1. Medium effort.
- **FXS-2**: Reduce kernel to 3×3 — 9 samples instead of
  25 (**64% reduction** in sampling work). Changes visual
  result (tighter bloom). Operator visual verification
  needed.
- **FXS-3**: Downsample approach — sample a
  half-resolution copy for the blur, then upscale. Cuts
  pixel count by 4, trades bandwidth for one extra pass.
  Standard bloom optimization in real-time graphics.

**Recommendation**: FXS-2 (3×3) is the cheapest change
and most likely operator-acceptable as a baseline
optimization. FXS-1 (separable) is the principled fix but
requires more infrastructure. FXS-3 (downsample) is the
best quality-for-cost but requires significant pipeline
changes.

### 2.4 Finding 4 — branch-heavy shaders

Conditional counts (static analysis of `if` and `for`):

```text
shader                          conditionals  loops
pixsort.frag                              13      6
ascii.frag                                12      0
glitch_block.frag                          8      0
thermal.frag                               6      2
vhs.frag                                   4      1
slitscan.frag                              3      0
stutter.frag                               3      0
feedback.frag                              3      0
```

**GPU warp divergence implications**: modern NVIDIA GPUs
execute 32 threads (fragments) in lock-step per warp. When
fragments within a warp take different branches, the warp
serializes each branch — effectively multiplying the
shader cost by the number of divergent paths.

**pixsort** has the worst divergence pattern:

- First `for` loop: walks backward from the fragment's
  position, breaking on brightness threshold or screen
  edge. **Early-exit behavior varies per pixel** within a
  warp.
- Second `for` loop: walks forward with the same
  behavior.
- Bubble sort: 11 outer passes × 11 inner iterations =
  121 fixed operations per eligible fragment.

For fragments where `lum < threshold_low || lum >
threshold_high`, the shader short-circuits on line 31
and all the loops are skipped. But for fragments inside
the threshold, the interval-detection and sort loops
run.

**If a warp contains some inside-threshold and some
outside-threshold fragments**, the entire warp pays the
inside cost (all 32 threads execute the loops; the
outside threads just discard their results).

**This is unavoidable for pixsort's algorithmic
structure** (it inherently requires per-pixel decisions),
but worth documenting as "pixsort is expected to have
high per-pixel variance under divergent content".

**ascii** has 12 conditionals for character glyph
selection but no loops — fewer divergence problems, just
a cascade of if-else.

**glitch_block** has 8 conditionals for block-displacement
decisions, relatively tame.

**No fix recommended**: these are all algorithmic
requirements of the shaders. Worth **documenting** in the
shader node manifests (`"complexity": "high"` as a hint
to preset authors), but no code change improves the GPU
cost meaningfully.

## 3. Preset coverage of expensive shaders

Cross-referencing presets against high-cost shaders:

```text
preset                     uses bloom  uses thermal  uses pixsort
heartbeat                         yes           no           no
neon                              yes           no           no
mirror_rorschach                  yes           no           no
screwed                           yes           no           no
ambient                           yes           no           no
thermal_preset                    no            yes          no
pixsort_preset                    no            no           yes
```

**bloom** is in 5/28 presets (~18%). **thermal** and
**pixsort** are each in 1/28 presets. The other 21
presets use none of the expensive shaders directly — but
`_default_modulations.json` applies a `bloom.alpha`
modulation, so **any preset that happens to have a
`bloom` node gets its alpha audio-modulated by default**.

**Effective hot-shader coverage**: ~18% of presets run
the 5×5 kernel. The auto-governance atmospheric selector
(drop #44) picks presets by stance × energy, and some of
the "high energy" cells point at
`feedback_preset` / `kaleidodream` / `datamosh` — none of
those contain bloom directly. So **bloom is a low-baseline
cost that kicks in occasionally**, not a sustained hot
spot.

## 4. Ring summary

### Ring 1 — dead code removal

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **FXS-1** | Delete `temporal_slot.py` | `agents/effect_graph/temporal_slot.py` | 63 | Dead code removed |
| **FXS-2** | Retire `temporal_buffers` field from schema | `registry.py`, `compiler.py`, `types.py`, node JSONs | ~30 | Declarative meaninglessness fixed |

**Risk profile**: zero for both. Pure deletion.

### Ring 2 — optional shader cost reduction

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **FXS-3** | Reduce bloom kernel 5×5 → 3×3 | `bloom.frag` | ~5 line edit | ~64% reduction in bloom sample count; changes visual result |
| **FXS-4** | Implement separable Gaussian bloom (2-pass 5×1) | `bloom.frag` + fx_chain | ~40 | ~23% reduction in sample work; preserves visual result |
| **FXS-5** | Implement downsample + upsample bloom | `bloom.frag` + fx_chain | ~60 | Best quality-for-cost; medium infrastructure work |

**Risk profile**: FXS-3 changes visual output; operator
verification required. FXS-4 preserves output but adds
pipeline complexity. FXS-5 is best long-term but requires
mipmap / downsample shader infrastructure.

### Ring 3 — documentation

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **FXS-6** | Add `"complexity": "high"/"medium"/"low"` hint to expensive shader manifests | Node JSONs | ~10 | Preset authors see cost hints |
| **FXS-7** | Document bloom/thermal/pixsort as GPU-heavy in preset-authoring README | `presets/README.md` (new) | ~20 | Surfaces the hot shader set |

## 5. Cumulative impact estimate

**Ring 1 alone**: 93 lines of dead code removed
(temporal_slot.py + temporal_buffers schema).

**Ring 1 combined with drop #44 Ring 2**: the effect_graph
module is cumulatively ~170+ lines lighter if all
dead-feature removals ship (LayerPalette + PresetInput +
temporal_slot + temporal_buffers). Still leaves a working
system intact.

**Ring 2 FXS-3** (bloom 3×3): saves ~64% of bloom's
sample cost. When bloom is in the active preset, that's
~4 GB/s of GPU memory bandwidth reclaimed. Modest but
measurable under load.

## 6. Cross-references

- `agents/effect_graph/temporal_slot.py` — dead class
- `agents/effect_graph/registry.py:40-61` — `_load`
  (reads the dead `temporal_buffers` field)
- `agents/effect_graph/compiler.py:263-294` — `_build`
  (passes `temporal_buffers` into `ExecutionStep`)
- `agents/shaders/nodes/bloom.frag` — 5×5 kernel (hot
  shader)
- `agents/shaders/nodes/thermal.frag` — 5×5 kernel (hot
  shader, single preset use)
- `agents/shaders/nodes/pixsort.frag` — interval + bubble
  sort (heaviest algorithmic cost, single preset use)
- `agents/shaders/nodes/stutter.json` —
  `temporal_buffers=8` declaration that doesn't match
  the shader
- Drop #5 — glfeedback diff check (prevents redundant
  shader recompile; this drop reaffirms that the
  recompile prevention is valuable because recompiling
  bloom / thermal / pixsort would be especially
  expensive)
- Drop #38 — 24-slot SlotPipeline architecture (context
  for how many of these shaders can run simultaneously)
- Drop #44 — preset control plane (which presets reference
  which shaders)
