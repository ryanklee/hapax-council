# cudacompositor + per-camera consumer chain systematic walk

**Date:** 2026-04-14
**Author:** delta (beta role — cam-stability focus)
**Scope:** Systematic walk of the composite-side camera
pipeline: `interpipesrc → tee → queue → cudaupload →
cudaconvert → cudascale → cudacompositor`. Drops #28-#30
walked the producer side (`v4l2src → jpegdec →
interpipesink`) and drop #32 walked the output side
(post-fx tee to v4l2sink/HLS/RTMP). This drop covers
the middle: how six producer pipelines converge into
one composite frame. Also audits the `cudacompositor`
element itself, its GStreamer-aggregator inheritance,
and its per-pad properties. Pairs with drop #31
(cam-stability rollup) — extends the picklist with
seven new findings focused on the composite-side chain.
**Register:** scientific, neutral
**Status:** investigation — 7 findings, 4 observability
gaps, no code changed in this drop
**Companion:** drops #28-#30 (producer walk), drop #31
(rollup), drop #32 (output walk), drop #34 (USB
topology H4 closeout)
**Constraint:** all 6 cameras permanently at 1280×720
MJPEG; do not propose resolution changes (operator
decision 2026-04-14)

## Headline

**cudacompositor is configured with ONE property
(`cuda-device-id=0`) and every other property at
default.** Two of those defaults are actively harmful
for a live 6-camera composite with hot-swap:

- `latency=0` — no grace period for late inputs.
  Every aggregator tick, any pad whose buffer arrives
  after the output deadline has its buffer skipped
  (or the aggregator repeats the last frame).
  At 30 fps this means any camera with a momentary
  stall of even 1 ms beyond its deadline loses a
  frame from the composite.
- `ignore-inactive-pads=false` — if any sink pad has
  no data at all, the aggregator refuses to produce
  output. During a primary→fallback interpipesrc swap,
  there is a brief window where the consumer has no
  buffer yet, and this default can freeze the entire
  composite until the swap settles.

**`cudaconvertscale` is available** (GStreamer 1.28.2
`gst-plugins-bad` nvcodec plugin, source released
2026-04-07). The consumer chain currently uses two
separate elements (`cudaconvert` + `cudascale`) per
camera, adding 12 element boundaries (6 cameras × 2
elements) where 6 would suffice.

**cudacompositor's per-pad `current-level-buffers`
/ `current-level-bytes` / `current-level-time`
properties are READABLE at runtime.** The compositor
does not scrape them. Per-camera backpressure at the
composite-sink level is fully unobserved.

## 1. The chain, element-by-element

### 1.1 Producer-side (covered in drops #28-#30)

```text
v4l2src[usb-device] → capsfilter(image/jpeg) → watchdog(2000ms)
    → queue(max-size-buffers=1, leaky=downstream)
    → jpegdec → videoconvert(dither=0) → capsfilter(NV12)
    → interpipesink(cam_<role>, sync=false, async=false)
```

One such producer pipeline per camera (6 total) plus
one fallback producer (`fb_<role>`) per camera (6
total). All 12 producer pipelines are isolated
GstPipeline instances — errors on one do not
propagate to others.

### 1.2 Consumer-side (this drop's scope)

```text
interpipesrc(listen-to=cam_<role>,
             is-live=true,
             format=TIME,
             stream-sync=restart-ts,
             allow-renegotiation=true)
    → tee(allow-not-linked=true, per-camera)
      ├── consumer branch to cudacompositor:
      │   queue(leaky=2, max-size-buffers=2)
      │     → cudaupload
      │     → cudaconvert
      │     → cudascale
      │     → capsfilter(NV12 in CUDAMemory, tile.w × tile.h)
      │     → cudacompositor.sink_%u[xpos,ypos,w,h]
      ├── snapshot branch (covered in drop #28)
      └── [optional] recording branch (covered in drop #32)
```

**One such consumer chain per camera × 6.** All six
sink pads converge on a single `cudacompositor`
instance.

### 1.3 Post-compositor (covered in drop #30)

```text
cudacompositor → cudadownload → videoconvert(BGRA)
    → capsfilter(BGRA, 1920×1080) → pre-fx tee
      → [fx chain] → output tee → v4l2sink / smooth_delay / hls / rtmp
      → [snapshot + fx_snapshot branches]
```

## 2. The cudacompositor element — property audit

### 2.1 Properties set by council

`agents/studio_compositor/pipeline.py:41-60`:

```python
comp_element = Gst.ElementFactory.make("cudacompositor", "compositor")
compositor._use_cuda = comp_element is not None
if comp_element is None:
    log.warning("cudacompositor unavailable — falling back to CPU compositor")
    comp_element = Gst.ElementFactory.make("compositor", "compositor")
    ...
else:
    try:
        comp_element.set_property("cuda-device-id", 0)
    except Exception:
        log.debug("cudacompositor: cuda-device-id property not supported", exc_info=True)
pipeline.add(comp_element)
```

**Exactly one property is set: `cuda-device-id=0`.**

### 2.2 Properties at default (from `gst-inspect-1.0 cudacompositor`)

| Property | Default | Effect on 6-cam live composite |
|---|---|---|
| `force-live` | false | Aggregator lives-or-dies based on upstream liveness detection. With interpipesrc `is-live=true`, live mode should activate automatically. Safe but untested on this stack. |
| `ignore-inactive-pads` | **false** | **Aggregator blocks if any sink pad has no data.** Problematic during primary→fallback swap when one pad briefly has no buffer. |
| `latency` | **0 ns** | **No grace period for late inputs.** Any camera whose buffer arrives after the deadline has its buffer dropped or replaced by the last-repeated frame. |
| `min-upstream-latency` | 0 ns | No floor on assumed upstream latency. |
| `start-time-selection` | zero | Aggregator uses timestamp 0 as its start reference. |
| `emit-signals` | false | No per-frame signals to Python handlers. |

**The default `latency=0` is the biggest leverage point
in this drop.** In GStreamer aggregator semantics, `latency`
is additional wall-clock time beyond the deadline that
the aggregator will wait for a slow pad. At 30 fps the
deadline interval is 33 ms; `latency=0` means "the
deadline is exact, not a hint." A pad that is 1 ms late
loses its buffer for this tick.

### 2.3 Per-pad properties (from `gst-inspect-1.0 cudacompositor`)

`GstCudaCompositorPad` exposes:

| Property | Default | Set by council |
|---|---|---|
| `xpos` | 0 | ✓ (tile.x from layout) |
| `ypos` | 0 | ✓ (tile.y from layout) |
| `width` | 0 | ✓ (tile.w from layout) |
| `height` | 0 | ✓ (tile.h from layout) |
| `alpha` | 1.0 | unset (default opaque) |
| `operator` | "over" | unset |
| `sizing-policy` | "none" | unset (stretch to fit) |
| `max-last-buffer-repeat` | `UINT64_MAX` | unset (repeat forever) |
| `repeat-after-eos` | false | unset |
| `current-level-buffers` | — (read-only) | **never read** |
| `current-level-bytes` | — (read-only) | **never read** |
| `current-level-time` | — (read-only) | **never read** |
| `emit-signals` | false | unset |

Three observations:

1. **`max-last-buffer-repeat` default is `UINT64_MAX`**
   — which means "repeat the last buffer forever".
   This is *good* for a camera composite: if a
   producer stalls, the compositor holds the last
   frame instead of producing a black pad. This
   default works in our favor.
2. **`sizing-policy=none`** stretches the input to
   fit the pad rectangle. Since the council chain
   pre-scales with `cudascale` to the exact tile
   size, this is a no-op at steady state. But if a
   camera ever produces a different-sized buffer
   (e.g., during renegotiation), it will be
   stretched without preserving aspect ratio. A
   `keep-aspect-ratio` policy would be safer but
   causes black bars on mismatched inputs.
3. **`current-level-*` properties are readable in
   real time.** The compositor could scrape these
   every tick and publish them as Prometheus
   histograms, giving per-camera back-pressure
   visibility *at the composite-sink level*. Today
   this data is collected by the aggregator but
   never exported.

## 3. The consumer chain — per-camera element audit

### 3.1 Element-by-element, with findings

`agents/studio_compositor/cameras.py:86-208`, per-camera
consumer branch:

```python
src = Gst.ElementFactory.make("interpipesrc", f"consumer_{role}")
src.set_property("listen-to", f"cam_{role}")
src.set_property("stream-sync", "restart-ts")
src.set_property("allow-renegotiation", True)
src.set_property("is-live", True)
src.set_property("format", Gst.Format.TIME)

camera_tee = Gst.ElementFactory.make("tee", f"tee_{role}")
camera_tee.set_property("allow-not-linked", True)

queue_comp = Gst.ElementFactory.make("queue", f"queue-comp-{role}")
queue_comp.set_property("leaky", 2)          # downstream
queue_comp.set_property("max-size-buffers", 2)

upload = Gst.ElementFactory.make("cudaupload", f"upload_{role}")
cuda_convert = Gst.ElementFactory.make("cudaconvert", f"cudaconv_{role}")
scale = Gst.ElementFactory.make("cudascale", f"scale_{role}")
scale_caps = Gst.ElementFactory.make("capsfilter", f"scalecaps_{role}")
scale_caps.set_property(
    "caps",
    Gst.Caps.from_string(f"video/x-raw(memory:CUDAMemory),width={tile.w},height={tile.h}"),
)
```

### 3.2 Findings

**Finding 1 — `queue_comp` cushion too small.** Only
2 buffers × 33 ms = **66 ms** of cushion before
cudaupload. If the upload stalls (GPU contention with
reverie, cudacompositor ticking, fx_chain shader
compile), frames drop at this queue. **Bump to 5
buffers = 167 ms cushion**, same rationale as drop #31
Ring 1 fix A for the v4l2sink branch.

**Finding 2 — cudaconvert + cudascale are separate
elements.** This adds an element boundary between
them: two pad allocations, two caps negotiations, and
no opportunity for the nvcodec plugin to optimize the
combined operation. **`cudaconvertscale` is available**
and ships in the same plugin (nvcodec 1.28.2, source
date 2026-04-07) — verified via `gst-inspect-1.0
cudaconvertscale`. Merging the two elements into one
`cudaconvertscale` per camera saves 6 element
boundaries, lets the plugin fuse format conversion
and scaling in a single CUDA kernel pass, and reduces
the per-frame setup overhead.

**Finding 3 — element order is `cudaconvert →
cudascale`.** Convert happens *before* scale, which
means format conversion operates on the full 1280×720
input. If the tile size is smaller (e.g., 640×360 for
a 2×3 grid on 1920×1080), scaling afterwards discards
pixels that were just converted. **Scale-then-convert
is theoretically more efficient** — operate the
conversion on fewer pixels. In practice,
`cudaconvertscale` handles this internally when the
two operations are merged (finding 2), so finding 2
subsumes finding 3.

**Finding 4 — `allow-not-linked=true` on the per-camera
tee hides branch failures.** The tee fans out to 3
branches (composite, snapshot, recording). If any
branch fails to link or has a pad error, the other
branches continue silently — including the composite
branch. This is *defensive* but removes observability:
if the recording branch breaks, nothing logs.
**Mitigation**: add a bus message probe that logs tee
branch state on WARNING level when a branch enters a
degraded state.

**Finding 5 — no per-pad metric scraping.**
cudacompositor exposes `current-level-buffers` on
every sink pad in real time. Reading all 6 pads each
tick and publishing as `studio_compositor_aggregator_pad_level_buffers{role}`
histogram gives per-camera composite-side back-pressure
visibility that is currently a complete black hole.

**Finding 6 — `latency=0` gives no grace for late
producers.** Drop #2's brio-operator hits 27.94 fps,
meaning ~2 frames per second arrive late relative to
the 30 fps cadence. Drop #34 confirmed this is USB
topology, not a fixable producer-side issue. With
`latency=0`, every one of those late buffers is
skipped at the aggregator level. **Setting
`latency=33000000` (one frame = 33 ms)** gives the
aggregator a full frame of grace: a buffer arriving
anywhere in the next output tick is still accepted.
The cost is one frame of additional wall-clock
latency in the worst case.

**Finding 7 — `ignore-inactive-pads=false` blocks
output during swaps.** When the pipeline manager
swaps a camera from primary to fallback (e.g., because
brio-operator producer failed), there is a ~100-200
ms window where the consumer's interpipesrc is
renegotiating caps and has no buffer. With
`ignore-inactive-pads=false`, the cudacompositor
aggregator may block output waiting for the missing
pad. **Setting `ignore-inactive-pads=true`** tells
the aggregator "produce output with whatever pads
currently have data", using the last-repeated buffer
for the swap-in-progress pad. The downside: if a pad
never produces data at all, the aggregator will show
a frozen last frame there. That is already the
desired behavior (via `max-last-buffer-repeat`
default), so this change is aligned.

### 3.3 Hidden tile finding

**Finding 8 — hidden tiles in sierpinski mode don't
save upstream work.** `layout.py:32-39`:

```python
def _hidden_tile() -> TileRect:
    """Tile rect for a camera that should not appear in the output.

    Width 1 + negative x position — GStreamer compositor accepts this and
    effectively removes the camera from view without triggering pad
    renegotiation.
    """
    return TileRect(x=-10, y=-10, w=1, h=1)
```

In sierpinski mode, 3 cameras occupy triangle corners
and the remaining 3 are "hidden" via this 1×1
off-canvas rect. **The producer pipeline for each
hidden camera still runs at 30 fps**, still consumes
USB bandwidth, still writes to interpipesink, still
gets consumed by interpipesrc, still flows through
the tee + queue + cudaupload + cudaconvert + cudascale
chain, and still lands on a 1×1 pixel cudacompositor
sink pad.

**Cost per hidden camera**:

- 1 USB isoc slot (drop #34's contention is worse if
  hidden cameras still stream)
- 1 jpegdec CPU core share
- 1 cudaupload (~1.4 MB × 30 fps = 42 MB/s CPU→GPU)
- 1 cudaconvert + cudascale pass
- 1 cudacompositor aggregator pad slot

**3 hidden cameras** in sierpinski mode = 3× the above
= 126 MB/s of wasted CPU→GPU bandwidth, 3 CPU cores'
worth of jpegdec work, 3 USB isoc slots held for data
that will never be displayed.

**Fix options**:

- **Option A** — detach the hidden camera's consumer
  branch from cudacompositor entirely (unlink the pad,
  release the request pad). The producer pipeline
  still runs (for fast re-attach) but the consumer
  chain's CUDA work stops. Requires pipeline mutation
  on layout change — non-trivial but not unprecedented.
- **Option B** — pause the producer pipeline of a
  hidden camera (transition to READY state). Stops
  the USB isoc allocation and the jpegdec work
  entirely. Re-activation takes ~200-500 ms which is
  perceptible on layout switches.
- **Option C** — leave as-is; accept the waste as
  the cost of instant layout switching.

Today the code does option C (implicitly). A
deliberate decision here would be valuable.

## 4. Counting the CUDA ops per composite frame

Per composite frame at 30 fps, with 6 healthy cameras:

| Operation | Count | Data volume | GPU time hint |
|---|---|---|---|
| cudaupload (CPU→GPU) | 6 | 6 × 1.4 MB = 8.3 MB/frame | ~0.5 ms/frame |
| cudaconvert | 6 | in-place format conversion | ~0.3 ms/frame |
| cudascale | 6 | 1280×720 → tile.w × tile.h | ~0.2 ms/frame |
| cudacompositor blit | 6 | blit 6 tiles to output | ~0.5 ms/frame |
| cudadownload (GPU→CPU) | 1 | 1920×1080 NV12 = 3.1 MB | ~0.8 ms/frame |

**Per-frame total**: ~2.3 ms of GPU work dedicated to
the composite step, plus ~250 MB/s of CPU↔GPU bandwidth
(248 up + 94 down ≈ 342 MB/s total).

At 30 fps this is ~70 ms of GPU time per second (~7%
of one GPU stream's budget). Very modest in isolation.
The real cost is the **CPU↔GPU bandwidth** (already
flagged in drop #28), which pairs with the ~1 GB/s
reclaimable in drops #28-#32 Ring 3 items.

### 4.1 With `cudaconvertscale` merge (finding 2)

| Operation | Count | Notes |
|---|---|---|
| cudaupload | 6 | unchanged |
| cudaconvertscale | 6 | merged into single op |
| cudacompositor blit | 6 | unchanged |
| cudadownload | 1 | unchanged |

Element count goes from 7 per camera (queue,
cudaupload, cudaconvert, cudascale, capsfilter, pad
+ interpipesrc, tee shared) to **6 per camera**. Each
camera loses one element boundary, which is ~50 µs of
pad setup per frame × 6 cameras × 30 fps = **9 ms/sec
of pad-activation overhead reclaimed**. Modest but
measurable.

More importantly, the nvcodec plugin can then fuse
the convert+scale into one CUDA kernel launch per
camera instead of two, which reduces CUDA command
submission overhead.

## 5. Observability gaps

Five gaps on the composite-side chain:

1. **No per-pad `current-level-buffers` scrape** —
   already discussed in finding 5. Single biggest
   visibility gap.
2. **No per-camera `cudaupload` byte throughput
   metric** — we know cumulatively it's ~248 MB/s but
   not per-camera. A single-camera spike would be
   invisible.
3. **No per-camera `cudascale` / `cudaconvert`
   element-time metric** — element-level timing
   histograms would show which camera's chain is
   slow.
4. **No metric for aggregator "wait time per output
   frame"** — i.e., how long cudacompositor blocked
   waiting for the slowest pad before producing output.
   This is the direct indicator of which camera is
   the composite bottleneck.
5. **No metric for `queue_comp` drop events** — the
   leaky=downstream queues silently drop old frames
   under sustained pressure. A drop counter per
   camera would surface producer-consumer mismatch
   at the composite side.

All 5 gaps could be closed with Python pad probes +
Prometheus histograms defined in
`agents/studio_compositor/metrics.py`. None require
GStreamer element modification.

## 6. Ring summary

### Ring 1 — drop-everything (2 fixes, 2 lines each)

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **COMP-1** | `cudacompositor.set_property("latency", 33_000_000)` | `pipeline.py:41-60` | 1 | Gives aggregator 33 ms grace for late pads; saves ~7% of brio-operator frames (the ones arriving late in the aggregator deadline) |
| **COMP-2** | `cudacompositor.set_property("ignore-inactive-pads", True)` | `pipeline.py:41-60` | 1 | Aggregator produces output when pads are mid-swap; eliminates fallback-swap composite freeze |

**Risk profile:** zero — both are property settings on
element creation, aligned with the element's
documented semantics for live-composite use.

### Ring 2 — small refactors

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **COMP-3** | Merge `cudaconvert` + `cudascale` → `cudaconvertscale` per camera | `cameras.py:149-158` | ~8 | 6 element boundaries removed, nvcodec plugin fuses the ops |
| **COMP-4** | Bump `queue_comp max-size-buffers` from 2 to 5 | `cameras.py:148` | 1 | Matches drop #31 Ring 1 fix A rationale: 167 ms of cushion instead of 66 ms |

**Risk profile:** COMP-3 requires verifying the merged
element produces byte-identical output to the
separate pair (it should, per GStreamer docs). COMP-4
is a pure tuning change.

### Ring 3 — observability (all in metrics.py + pad probes)

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **COMP-5** | Scrape per-pad `current-level-buffers` → histogram | `metrics.py` + tick loop | ~40 | Per-camera composite-side back-pressure visibility |
| **COMP-6** | Per-camera cudaupload byte throughput probe | `cameras.py` pad probe | ~20 | Per-camera CPU→GPU traffic |
| **COMP-7** | Aggregator wait-time-per-frame histogram | `metrics.py` + `_on_new_sample` | ~30 | "Which camera is the composite bottleneck?" becomes scrape-visible |
| **COMP-8** | `queue_comp` drop counter (buffer probe on leaky queue) | `cameras.py` | ~25 | Per-camera producer-consumer mismatch signal |

**Risk profile:** all Ring 3 items are pure additions
to Python code, no GStreamer modification. Medium
priority — they are not urgent but pair with drop
#32's output-side observability gaps to complete the
compositor observability map.

### Hidden tile decision (finding 8)

| # | Fix | Options |
|---|---|---|
| **COMP-9** | Detach or pause hidden camera branches in sierpinski mode | Option A (detach pad), Option B (pause producer), Option C (leave as-is with documented waste) |

This is a **decision**, not a fix. The three options
have different cost/complexity tradeoffs. Recommend
filing as an open question for the operator: "do you
ever switch to sierpinski mode, and if so is it worth
spending the engineering budget to stop the hidden
cameras from consuming resources?"

## 7. Cumulative impact estimate

If council ships **Ring 1 (COMP-1 + COMP-2)**:

- brio-operator's 27.94 fps no longer causes
  proportional frame loss at the composite level
  (aggregator grace absorbs the lateness)
- Fallback swaps no longer produce composite freeze
  windows
- Zero performance cost; ~2 lines of code

If council additionally ships **Ring 2 (COMP-3 +
COMP-4)**:

- 6 element boundaries removed from the consumer chain
- Per-camera queue cushion triples
- Modest element-activation overhead savings
  (~9 ms/sec reclaimed)

If council ships **Ring 3 observability (COMP-5 →
COMP-8)**:

- 4 new metric families publishing per-camera
  composite-side telemetry
- Future regressions in the consumer chain become
  scrape-visible instead of requiring journal grep
- Pairs with drop #32's output-side observability
  for a complete compositor observability map

## 8. Cross-references

- `agents/studio_compositor/pipeline.py:41-60` —
  cudacompositor element creation
- `agents/studio_compositor/cameras.py:86-208` —
  `add_camera_branch` consumer chain construction
- `agents/studio_compositor/layout.py:32-39` —
  `_hidden_tile()` and sierpinski layout
- `gst-inspect-1.0 cudacompositor` — element + pad
  properties
- `gst-inspect-1.0 cudaconvertscale` — confirms the
  merged element is available (nvcodec 1.28.2,
  2026-04-07)
- Drops #28-#30 — producer-side walk
- Drop #31 — cam-stability rollup
- Drop #32 — output-side walk
- Drop #34 — USB topology H4 closeout

## 9. Follow-ups

1. **Today / next session**: Ring 1 (COMP-1,
   COMP-2). Two lines, zero risk.
2. **Within a week**: Ring 2 (COMP-3, COMP-4). Small
   refactor, test with all 6 cameras healthy.
3. **Background investigation**: Ring 3 observability
   (COMP-5 through COMP-8). Pairs with drop #32's
   output-side observability work.
4. **Operator decision required**: finding 8 (hidden
   tiles). Does sierpinski mode's "waste 3 cameras
   for responsiveness" tradeoff need changing?
5. **Open**: is `cudacompositor` running in its
   live-or-async mode? The `force-live=false` default
   means the element auto-detects. With interpipesrc
   `is-live=true`, detection should succeed, but
   nothing verifies. **Quick test**: add a log line
   at compositor startup reading `comp_element.get_latency()`
   and check it's non-zero after PLAYING.
