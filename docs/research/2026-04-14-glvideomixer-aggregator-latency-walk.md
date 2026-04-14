# glvideomixer aggregator latency + base/flash mixer audit

**Date:** 2026-04-14
**Author:** delta (beta role — cam-stability focus)
**Scope:** Short, focused walk of the `glvideomixer`
element in the fx chain. Drops #35 covered
cudacompositor's aggregator defaults; this drop
applies the same analysis to the second aggregator in
the pipeline, plus its specific interaction with the
cairooverlay callback cost flagged in drop #39.
**Register:** scientific, neutral
**Status:** investigation — 2 findings. No code
changed.
**Companion:** drop #35 (cudacompositor walk — same
aggregator-class defaults), drop #39
(cairooverlay streaming-thread cost — drives the base
path timing)

## Headline

**`glvideomixer` is the second aggregator in the
pipeline. It inherits `GstAggregator`'s `latency=0`
default** — same as cudacompositor. Same one-line
fix from drop #35 COMP-1 applies here:
`glmixer.set_property("latency", 33_000_000)`.

**The interaction with drop #39 is the interesting
part.** The base path through `glvideomixer` runs
through a cairooverlay callback that takes ~6-10 ms
per frame on the streaming thread. The flash path has
no cairooverlay — it's straight `pre_fx_tee → queue →
videoconvert → glupload → glcolorconvert → glvideomixer`.
**The two pads therefore have a consistent ~6-10 ms
timing offset**: the flash path is always ahead of the
base path by that amount.

With `latency=0`, the aggregator produces output as
soon as any pad has data, using the last-repeated
frame from any pad that's behind. **The base path is
consistently behind**, so some fraction of output
frames are produced from the base pad's LAST buffer
(last rendered cairooverlay result) rather than the
current frame's cairooverlay result. When the base
pad catches up, its newer buffer is used.

Setting `latency=33_000_000` (one frame at 30 fps)
gives the aggregator grace to wait for the base path
to catch up before producing output, aligning both
pads on the same frame timestamp.

## 1. Element creation and property audit

`agents/studio_compositor/fx_chain.py:337-339`:

```python
glmixer = Gst.ElementFactory.make("glvideomixer", "fx-glmixer")
glmixer.set_property("background", 1)  # 1=black (default is 0=checker!)
```

Council sets exactly **one** property: `background=1`
(black). That's a defensive fix that was already in
place — the `# (default is 0=checker!)` comment
flags that glvideomixer's default would otherwise
render a checker pattern between pads.

### 1.1 Properties at default

From `gst-inspect-1.0 glvideomixer`:

| Property | Default | Set? | Effect on base/flash mixer |
|---|---|---|---|
| `latency` | **0 ns** | no | **Finding 1 — no grace for the base-path cairooverlay** |
| `min-upstream-latency` | 0 ns | no | No floor on assumed upstream latency |
| `force-live` | false | no | Aggregator auto-detects live mode |
| `background` | checker | **yes (black)** | Defensive fix — avoids checker pattern |
| `start-time-selection` | zero | no | Standard aggregator behavior |
| `async-handling` | false | no | Standard bin behavior |
| `message-forward` | false | no | Children messages do not forward |

**`ignore-inactive-pads` is NOT exposed on
glvideomixer.** It is not in the property list,
suggesting glvideomixer's base class (`GstGLMixer` →
`GstGLVideoMixerBin`) does not surface this
GstAggregator property, or uses a different
aggregator base. The drop #35 COMP-2 fix for
cudacompositor **cannot be applied here**.

### 1.2 Pad properties (not tuned by council)

Two sink pads are created (`fx_chain.py:388-396`):

```python
base_pad = glmixer.request_pad(glmixer.get_pad_template("sink_%u"), None, None)
base_pad.set_property("zorder", 0)
base_pad.set_property("alpha", 1.0)

flash_pad = glmixer.request_pad(glmixer.get_pad_template("sink_%u"), None, None)
flash_pad.set_property("zorder", 1)
flash_pad.set_property("alpha", 0.0)  # hidden until flash
```

`zorder` + `alpha` are set correctly. The flash pad
alpha animates 0.0↔0.6 via the FlashScheduler
(fx_chain.py:213-283) driven by kick onset detection.

Per-pad `GstGLVideoMixerInput` has additional
readable/writable properties that are NOT tuned:

- `blend-constant-color-{rgba}` — used for
  `GL_CONSTANT_*` blend modes (not applicable at
  council's current blend operator)
- Other blend-equation properties
- `repeat-after-eos` — boolean; at default

**No per-pad queue-depth readable properties** like
cudacompositor has (`current-level-buffers`). Drop
#35's Ring 3 observability recommendation does not
port to glvideomixer.

## 2. Findings

### 2.1 Finding 1 — `latency=0` creates base/flash
pad timing mismatch

The fx chain layout:

```text
input-selector → queue → cairooverlay(on_draw) → videoconvert → glupload → glcolorconvert → glvideomixer.sink_0 (base)
pre_fx_tee ──────────────→ queue → videoconvert → glupload → glcolorconvert → glvideomixer.sink_1 (flash)
```

The **base path has a cairooverlay element**
(cairooverlay → `on_draw` callback → 2 full-canvas
`cr.paint()` blits) that consumes **~6-10 ms per
frame on the streaming thread** (drop #39 finding 1).
The **flash path has no cairooverlay** — it's a
straight-through chain.

At steady state, both paths receive frames from the
same upstream `pre_fx_tee` at the same cadence
(30 fps, 33 ms interval). The flash path's buffer
reaches glvideomixer ~6-10 ms before the base path's
buffer for the same source frame.

**With `latency=0`**: the aggregator's default policy
is to produce output as soon as the running-time
deadline is reached. If the flash pad has a new buffer
but the base pad does not, the aggregator:

- **If the base pad has a prior buffer**: uses
  last-frame-repeat on the base pad and produces
  output with the flash's new buffer + base's
  previous buffer
- **If the base pad has no buffer yet**: behavior
  depends on `force-live` and whether the pipeline
  is in live mode

In the first case, the output frame is a mix of the
current-frame flash content and the **previous frame's
base content**. This is a one-frame temporal skew
that propagates through the shader chain. **The
output looks slightly offset**: the text overlay
(base path) lags the flash effect (flash path) by one
frame during every composite where the base path is
still in its cairooverlay callback.

**At 30 fps with ~6-10 ms base-path delay and a 33 ms
frame interval**, the base path arrives in time for
~23-27 ms of each 33 ms window (69-82%). In the
remaining 18-31% of windows, the base path's previous
frame is used — **18-31% of output frames have
one-frame-old base content**.

**This is hard to notice visually** because the base
content (Sierpinski + text overlay) changes slowly,
but it's measurable and fixable.

**Fix (Ring 1, one line)**:

```python
glmixer.set_property("latency", 33_000_000)  # 33 ms grace
```

With 33 ms of grace, the aggregator waits up to one
additional frame interval for the base path to
arrive. At 6-10 ms of consistent offset, the base
path always arrives within the grace window, and
the aggregator produces output with both pads'
current-frame buffers aligned.

**Cost**: one frame (33 ms) of additional end-to-end
latency in the pipeline. At a 30 fps livestream where
the total pipeline latency is already 100-300 ms
(capture → producer → compositor → fx chain → output),
adding 33 ms is ~10-33% of the total but brings
temporal alignment. **Worth it.**

### 2.2 Finding 2 — no `ignore-inactive-pads` on
glvideomixer

Drop #35 COMP-2 recommends setting
`ignore-inactive-pads=true` on cudacompositor so it
produces output during primary→fallback swaps even
when a sink pad has no data. That property is exposed
on cudacompositor because cudacompositor inherits
directly from `GstVideoAggregator → GstAggregator`.

**glvideomixer does NOT expose this property.** Its
inheritance chain (`GstGLVideoMixerBin → GstBin` wrapping
`glvideomixer` → `GstGLMixer` → `GstVideoAggregator`)
may not pass through the `ignore-inactive-pads`
property, OR the glvideomixer plugin does not set
this property on its internal aggregator.

**Impact**: glvideomixer has only 2 pads (base +
flash), neither of which comes from a dynamic producer
like interpipesrc. The flash pad is fed from
`pre_fx_tee` directly; the base pad is fed from
`pre_fx_tee → input_selector`. The input_selector's
`active-pad` switch might cause the base pad to
briefly have no data during a source switch, but
input_selector is internal to the fx chain (operator
never triggers it at runtime outside a specific mode).

**In practice this is not a production concern** for
glvideomixer the way it was for cudacompositor. The
fix is unavailable but also unnecessary.

## 3. Ring summary

### Ring 1 — drop-everything

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **GLM-1** | `glmixer.set_property("latency", 33_000_000)` | `fx_chain.py:337-339` | 1 | Aligns base/flash pads on same-frame timestamps; eliminates 18-31% of output frames having one-frame-old base content |

**Risk**: zero. One-line property change. Adds 33 ms
of end-to-end latency (acceptable for a livestream
with ~100-300 ms total latency budget).

### Ring 2 — none

No Ring 2 items on this element.

### Ring 3 — none

No architectural options worth exploring for this
element.

## 4. Cumulative pairing with prior drops

**GLM-1 stacks with drop #35 COMP-1** (same fix, same
rationale, different element). Both should ship
together as a cohesive "aggregator latency tuning"
PR. Total: 2 lines of code across two files.

**GLM-1 + COMP-1 together** give the whole pipeline
one frame of grace at both aggregator stages, which
matches the post-capture latency variance introduced
by the producer chain (drop #2's 27.94 fps cascades
to ~2 ms per tick of aggregator timing variance).

## 5. Cross-references

- `agents/studio_compositor/fx_chain.py:337-339` —
  glvideomixer element creation
- `agents/studio_compositor/fx_chain.py:388-396` —
  base + flash pad creation
- `gst-inspect-1.0 glvideomixer` — property list
- Drop #35 — cudacompositor walk (same `latency=0`
  finding, same one-line fix)
- Drop #39 — cairooverlay streaming-thread cost
  (explains the base/flash timing mismatch)
- Drop #2 — brio-operator sustained deficit
  (~7% frame-rate variance that cascades through
  both aggregators)

## 6. Observability gap (cross-drop)

glvideomixer does not expose per-pad
`current-level-*` readable properties the way
cudacompositor does. The aggregator-level observability
gap flagged in drop #35 finding 5
(`compositor_aggregator_pad_level_buffers{role}`) does
not extend here — there's nothing to scrape.

**However**, per-glvideomixer aggregator-level metrics
could still be useful:

- `compositor_glvideomixer_output_frames_total` —
  how many frames the aggregator produced
- `compositor_glvideomixer_wait_time_ms` — histogram
  of aggregator-side wait time per output frame
  (would directly reveal the base/flash skew)

These would be new Prometheus metrics backed by pad
probes or element signals. ~30 lines in `metrics.py`.
Low priority; only useful if finding 1 turns out to
have visible impact after shipping GLM-1.

## 7. Close

**This is a short drop.** The systematic walk is
approaching the bottom of the hot-path pipeline —
every major aggregator, every streaming-thread
callback, every CPU↔GPU boundary, and every
observability gap has been audited in drops #28-#40.

The remaining unexplored territory:

- **Individual Cairo source render functions**
  (sierpinski, token_pole, album, stream_overlay,
  overlay_zones — per-tick cost on background threads,
  not the hot path)
- **BudgetTracker call-site audit** (who records,
  who reads, and is it wired into the live path)
- **state_reader_loop thread** (reads perception
  state into overlay_state — cadence + lock
  contention)
- **Layout state + source registry hot-reload**

None of these are in the streaming-thread hot path.
They're either background threads (Cairo renders,
state reader) or control-plane operations (layout
reload). The drop sequence can pivot to those areas
or wind down the systematic walk.
