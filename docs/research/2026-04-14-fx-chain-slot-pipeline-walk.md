# fx_chain SlotPipeline internals + passthrough slot cost walk

**Date:** 2026-04-14
**Author:** delta (beta role — cam-stability focus)
**Scope:** Systematic walk of the fx chain's `SlotPipeline`
— the 24-slot chain of `glfeedback` shaders that runs
between `glvideomixer` output and `glcolorconvert →
gldownload`. Drop #30 covered the GPU↔CPU boundaries
around this chain (the glupload/gldownload round-trip);
this drop covers what runs *inside* the chain itself,
slot by slot, and quantifies the cost of unused slots.
**Register:** scientific, neutral
**Status:** investigation — 3 findings, 2 observability
gaps, 1 architectural decision for the operator. No
code changed.
**Companion:** drops #30 (fx_chain GPU↔CPU audit), #5
(glfeedback diff check — already shipped), #36
(threading/tick cadence)

## Headline

**The fx chain contains a fixed chain of 24 `glfeedback`
elements, linearly linked with no inter-slot queues.**
Every frame goes through all 24 slots regardless of how
many are actually doing meaningful work.

**Typical preset size is 5-9 nodes.** Empirical measurement
across the 30 presets in `presets/*.json`:

```text
preset node count distribution:
  0 nodes: 1 preset (empty template)
  5 nodes: 4 presets
  6 nodes: 10 presets  ← modal
  7 nodes: 8 presets
  8 nodes: 6 presets
  9 nodes: 1 preset
  max: 9 nodes
```

With 24 slots available and a modal preset of 6 nodes,
**18 slots on every output frame run the PASSTHROUGH
fragment shader** — a do-nothing copy from input
texture to output framebuffer. Even the largest preset
(9 nodes) leaves 15 slots as passthrough.

**Live GPU utilization** at 2026-04-14 ~14:30:
`nvidia-smi dmon -c 3 -s u` on GPU 0 shows SM 59-89%,
shared between the compositor's fx chain and reverie's
wgpu pipeline. The utilization is not low — removing
passthrough waste is real GPU headroom.

## 1. The chain, as built

`agents/effect_graph/pipeline.py:44-146` constructs and
links the slots:

```python
def create_slots(self, Gst: Any, plan: ExecutionPlan | None = None) -> list[Any]:
    """Create N glfeedback slot elements.

    All slots use glfeedback which applies shaders instantly via property
    (no create-shader signal timing issues) and provides tex_accum for
    temporal effects. Falls back to glshader if glfeedback not installed.
    """
    for i in range(self._num_slots):
        if has_glfeedback:
            slot = Gst.ElementFactory.make("glfeedback", f"effect-slot-{i}")
            slot.set_property("fragment", PASSTHROUGH_SHADER)
            ...
        self._slots.append(slot)
```

And linking (`pipeline.py:118-132`):

```python
def link_chain(self, pipeline: Any, Gst: Any, upstream: Any, downstream: Any) -> None:
    """Link slots directly between upstream and downstream.

    No inter-slot queues: all GL filter elements share a single GL context
    (single GPU command stream), so adding queues/threads between them only
    adds synchronization overhead without enabling actual GPU parallelism.
    """
    prev = upstream
    for slot in self._slots:
        if not prev.link(slot):
            log.error("Failed to link %s → %s", prev.get_name(), slot.get_name())
        prev = slot
    if not prev.link(downstream):
        log.error("Failed to link %s → %s", prev.get_name(), downstream.get_name())
```

**Pipeline layout at steady state:**

```text
glvideomixer → glcolorconvert → effect-slot-0 → effect-slot-1 → ...
  → effect-slot-23 → glcolorconvert → gldownload → videoconvert → output_tee
```

24 slots. Linear. One GL context. One command stream.

### 1.1 The PASSTHROUGH shader

`agents/effect_graph/pipeline.py` (module top):

```glsl
#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;
void main() { gl_FragColor = texture2D(tex, v_texcoord); }
```

One texture sample per fragment. One write to the
framebuffer. At 1920×1080 that's:

- **2,073,600 texels read** per frame per slot
- **2,073,600 texels written** per frame per slot
- **~16.6 MB of GPU memory traffic per slot per frame**
  (RGBA8 = 4 bytes per texel × 2 directions = 8 bytes ×
  2.07M texels ≈ 16.6 MB)
- **At 30 fps: ~498 MB/s per passthrough slot**

### 1.2 `activate_plan` — how slots get assigned shaders

`pipeline.py:148-220`:

```python
def activate_plan(self, plan: ExecutionPlan) -> None:
    """Assign graph nodes to slots in topological order."""
    ...
    # Default all slots to passthrough
    for i in range(self._num_slots):
        self._slot_pending_frag[i] = PASSTHROUGH_SHADER

    # Assign actual shaders to used slots sequentially
    slot_idx = 0
    for step in plan.steps:
        if step.node_type == "output":
            continue
        if slot_idx >= self._num_slots:
            log.warning("More nodes than slots (%d) — truncating", self._num_slots)
            break
        if step.shader_source:
            self._slot_pending_frag[slot_idx] = step.shader_source
            self._slot_assignments[slot_idx] = step.node_type
            self._slot_base_params[slot_idx] = dict(step.params)
            ...
            slot_idx += 1
    ...
```

**Plan activation does not rebuild the pipeline.** It
re-assigns fragment shaders to existing slots via
`set_property("fragment", ...)`. Unused slots (indices
≥ plan size) are set to PASSTHROUGH. This is the drop
#5 era design: **fast plan switching via property
writes, paid for by always running 24 slots**.

The drop #5 fix (`glfeedback diff check`, PR #807 era)
ensured that **re-setting the same fragment on a slot
doesn't trigger a shader recompile**. That fixed the
recompile-storm problem. The passthrough-cost problem
— 15-19 slots running a do-nothing shader on every
frame — was not addressed and is the subject of this
drop.

## 2. Findings

### 2.1 Finding 1 — passthrough slot cost

**Per-frame cost of one passthrough slot** at 1920×1080
RGBA:

| Resource | Cost |
|---|---|
| Draw call | 1 |
| Framebuffer switch | 1 |
| Texture sample | 2,073,600 |
| Framebuffer write | 2,073,600 |
| GPU memory bandwidth (read+write) | ~16.6 MB |

**At 30 fps**: one slot ≈ 498 MB/s of GPU memory
bandwidth + 30 draw calls/sec + 30 FB switches/sec.

**With 15 passthrough slots** (typical for a 9-node
preset — the largest in the current set):

- **~7.5 GB/s** of wasted GPU memory bandwidth
- **450 unnecessary draw calls/sec**
- **450 unnecessary framebuffer switches/sec**

**With 18 passthrough slots** (typical for a 6-node
preset — the modal preset in the current set):

- **~9 GB/s** of wasted GPU memory bandwidth
- **540 unnecessary draw calls/sec**
- **540 unnecessary framebuffer switches/sec**

**Is 7.5-9 GB/s significant?** Modern GPUs have
200-500+ GB/s of memory bandwidth, so **~3-5% of total
bandwidth**. Not a crisis, but not free either.

Combined with the ~70 MB/s GPU memory traffic the
actual fx chain work consumes (drops #29/#30 estimates),
**passthrough slots dominate the bandwidth cost of the
fx chain**. The actual shader work is a rounding error
compared to the passthrough overhead.

### 2.2 Finding 2 — `num_slots=24` is hardcoded and
not plan-aware

`agents/studio_compositor/fx_chain.py:344`:

```python
compositor._slot_pipeline = SlotPipeline(registry, num_slots=24)
```

Hardcoded `24`. No mechanism to change at runtime.
The pipeline is built once during `build_inline_fx_chain`
and the chain shape is fixed for the process lifetime.

**Rationale (from code comments + drop #5 context):** 24
gives headroom for any future preset that needs more
nodes than today's 9-node maximum. Fast hot-swap is
preserved because `activate_plan` only writes
properties, never re-links.

**Trade-off**: today's preset ceiling is 9 nodes.
**15 slots of headroom carries a permanent ~7.5 GB/s
passthrough cost** for no current benefit. A preset
scan at startup could set `num_slots = max(preset_size)
+ safety_buffer` dynamically.

### 2.3 Finding 3 — glfeedback maintains `tex_accum`
even in passthrough mode (unverified)

`glfeedback` is used specifically for its temporal
accumulation buffer (`tex_accum`), which lets feedback
shaders read the previous frame's output. For
non-temporal slots, the accumulation is unused — but
glfeedback's Rust implementation may still be
maintaining the FBO on every frame.

**Unverified from this drop**: does `tex_accum` incur
additional write bandwidth per passthrough slot? The
Rust side would need inspection (`gst-plugin-glfeedback/src/glfeedback/imp.rs`).

If yes: each passthrough slot is writing to BOTH the
output framebuffer AND the accumulation FBO per frame,
roughly doubling the per-slot bandwidth cost.

If no: the numbers in finding 1 stand.

**Follow-up**: 10-minute code read on the Rust side to
confirm.

## 3. Observability gaps

1. **No per-slot execution time histogram.** GL query
   objects (`glBeginQuery(GL_TIME_ELAPSED_EXT, q);
   glEndQuery(GL_TIME_ELAPSED_EXT); glGetQueryObjectui64v`)
   can measure per-draw GPU time. Each slot could be
   wrapped in a timer query and reported via
   `compositor_fx_slot_duration_us{slot,shader}`.
   **Cost**: non-trivial — requires gst-gl element
   modification or a custom pad probe using the GL
   context. Not shippable without architectural work.

2. **No counter for passthrough-slot frame count.**
   Easier observability: count the number of slots set
   to PASSTHROUGH after each `activate_plan`. Already
   tracked internally (`_slot_pending_frag == PASSTHROUGH_SHADER`);
   just needs a gauge:
   `compositor_fx_passthrough_slots`. This is free
   (Python-side property, no GL) and directly answers
   "how much fx chain overhead are we paying right now?"

## 4. Architectural options

### Option A — shrink `num_slots` to a calculated max

```python
# In build_inline_fx_chain or SlotPipeline.__init__:
max_preset_size = max(
    len(load_preset(p).steps)
    for p in glob("presets/*.json")
    if is_valid_preset(p)
)
num_slots = max_preset_size + 3  # safety buffer
```

**Effect**: if max preset is 9, use 12 slots instead of
24. Saves 12 passthrough slots worth of GPU bandwidth
(~6 GB/s) at the cost of locking out future presets
>12 nodes until the max is recomputed + compositor
restarted.

**Risk**: **medium**. A new preset that exceeds
`max_preset_size` would be silently truncated by
`activate_plan`'s `slot_idx >= self._num_slots` check.
Need a preset-registration-time validation to catch
this early.

### Option B — dynamic slot chain rebuild on plan change

```python
# In activate_plan:
if len(plan.steps) > self._num_slots:
    self._rebuild_chain(len(plan.steps) + 3)
```

**Effect**: chain length matches the active plan
exactly. Zero passthrough waste. But rebuild cost is
~100-500 ms of pipeline reconfiguration, which causes
a visible stutter every time the operator switches to
a larger preset.

**Risk**: **high**. Stutters during plan switches
defeat the entire point of the fast-switch architecture.

### Option C — bypass passthrough slots via pad
manipulation

```python
# At plan activation:
for i in range(len(plan.steps), self._num_slots):
    self._slots[i].set_property("bypass", True)  # if glfeedback supports it
```

**Effect**: passthrough slots still exist in the chain
but don't execute their fragment shader. Depends on
glfeedback having a bypass mode (likely it doesn't —
needs verification).

**Risk**: **unknown** — depends on element capabilities.

### Option D — accept the waste as the cost of fast
hot-swap

**Effect**: do nothing. Accept ~7.5-9 GB/s of GPU
memory bandwidth loss in exchange for instantaneous
plan switching.

**Risk**: **zero**. The cost is bounded and predictable.

## 5. Operator decision

The right option depends on live measurement. Without
per-slot GPU timing (observability gap 1), we can't
say whether the passthrough waste is causing actual
frame drops or just using headroom. The live
`nvidia-smi dmon` showed GPU 0 at 59-89% SM which is
*not* low — but that's shared with reverie imagination
too, so attribution is unclear.

**Recommendation**:

1. **Ship observability gap 2** first
   (`compositor_fx_passthrough_slots` gauge). Free,
   immediate, scrape-visible.
2. **Measure** steady-state fx-chain frame rate at
   current 24-slot chain vs a manually-reduced 12-slot
   chain (10 minutes of comparison, one config tweak).
3. **Then decide** between options A/D based on
   measurement.

## 6. Ring summary

### Ring 1 — free observability

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **FX-1** | `compositor_fx_passthrough_slots` gauge | `metrics.py` + `pipeline.py:activate_plan` | ~5 | Makes the passthrough cost scrape-visible |

### Ring 2 — targeted measurement

| # | Action | Tool | Notes |
|---|---|---|---|
| **FX-2** | Run compositor with `num_slots=12` vs `num_slots=24` for 10 minutes each, compare frame drop counters + GPU SM utilization | manual experiment | Decides whether Ring 3 Option A is worth shipping |

### Ring 3 — architectural (deferred until FX-2)

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **FX-3** | Dynamic `num_slots = max_preset_size + 3` computed at build time | `fx_chain.py:344`, `pipeline.py:__init__` | ~15 | 12 slots of passthrough waste removed |

### Ring 4 — verification

| # | Action | What to read |
|---|---|---|
| **FX-4** | Confirm glfeedback's `tex_accum` behavior in passthrough mode | `gst-plugin-glfeedback/src/glfeedback/imp.rs` |

## 7. Cumulative impact estimate

If council ships FX-1 (observability) and confirms
via FX-2 measurement that FX-3 is worthwhile:

- **~6 GB/s of GPU memory bandwidth reclaimed** (at
  modal 6-node preset)
- **~360 unnecessary draw calls/sec eliminated**
- **No user-visible change** (presets continue working,
  hot-swap remains fast)

Combined with prior drop Ring 1+2 estimates:

- Drop #31 Ring 1+2: ~900 MB/s CPU↔GPU
- Drop #32 Ring 1+2: ~33 MB/s
- Drop #36 Ring 2: ~275-350 MB/s CPU memory
- **Drop #38 Ring 3: ~6 GB/s GPU memory**

**Cumulative potential reclamation across camera+output+
compositor+fx path: ~7+ GB/s of memory bandwidth** if
all Ring 1+2+3 items ship across drops #28-#38.

## 8. Cross-references

- `agents/studio_compositor/fx_chain.py:286-453` —
  fx chain construction + 24-slot SlotPipeline
  creation
- `agents/effect_graph/pipeline.py:25-220` —
  `SlotPipeline` class + `activate_plan`
- `agents/effect_graph/pipeline.py` module top —
  `PASSTHROUGH_SHADER` definition
- `presets/*.json` — 30 presets, node counts 5-9
- `gst-plugin-glfeedback/src/glfeedback/imp.rs` —
  Rust implementation (drop #5 diff check lives here)
- Drop #5 — glfeedback shader recompile storm +
  diff-check fix
- Drop #29 — camera pipeline walk followups
- Drop #30 — fx_chain GPU↔CPU audit (covered
  glupload/gldownload boundaries)
- Drop #35 — cudacompositor + consumer chain walk
- Drop #36 — compositor threading + tick cadence

## 9. Open questions for the operator

1. **How often does the operator switch plans during
   a livestream?** If rarely, Ring 3 Option B
   (rebuild on switch) becomes more acceptable —
   the stutter cost is paid infrequently.
2. **Is there a pending preset expansion that would
   need >12 slots?** If yes, Option A's
   `num_slots = max_preset_size + 3` would lock in
   a lower bound that prevents the new preset.
3. **Does operator observe fx chain stutter under
   current load?** If yes, Ring 3 becomes urgent;
   if no, it can be deferred.

These questions could be answered in 2 minutes of
operator conversation + 10 minutes of measurement
before any architectural work ships.
