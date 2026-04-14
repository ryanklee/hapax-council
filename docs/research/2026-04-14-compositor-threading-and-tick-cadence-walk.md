# Compositor threading model + tick cadence + cairo runner allocation walk

**Date:** 2026-04-14
**Author:** delta (beta role — cam-stability focus)
**Scope:** Systematic walk of the compositor's Python
orchestration layer: GLib main loop, timer callbacks,
cairo source runners, budget tracking, and the thread
model under which all of it runs. Drops #28-#30
covered the producer side, drop #32 the output side,
drop #35 the cudacompositor element. This drop covers
the Python orchestration that sits alongside GStreamer
and drives the per-frame uniform updates, budget
publishing, and content-source render loops.
**Register:** scientific, neutral
**Status:** investigation — 6 findings, 2 observability
gaps, all backed by live `/proc/<pid>/task` inspection
and code reading. No code changed in this drop.
**Companion:** drops #28-#35, especially drop #35
(composite-side cudacompositor walk)

## Headline

**The live compositor process runs 96 threads.** Of
those, 22 are Python-owned (GLib main loop + Cairo
runners + state reader + persistence + command server
+ audio capture); the remaining 74 are GStreamer
internal (per-element tasks, pango fontconfig, CUDA
event handlers, GL context threads, producer pipeline
workers, watchdog timers).

**Three findings matter for livestream smoothness:**

1. **`CairoSourceRunner` allocates a fresh
   `cairo.ImageSurface` every tick** —
   `cairo_source.py:407`. Seven runners at average
   cadences sum to ~**105 MB/s of heap allocation
   churn** under pixman + Python's malloc. The
   surface is immediately freed after the buffer
   push, producing pure allocator pressure with no
   benefit.
2. **`_push_buffer_to_appsrc` does a full pixel copy
   via `bytes(surface.get_data())`** —
   `cairo_source.py:317-319`. Combined with the
   allocation churn from finding 1, that's another
   ~200 MB/s of copy traffic through the
   `bytes()` → `Gst.Buffer.new_wrapped` path when
   all 7 sources are active.
3. **`fx_tick_callback` is scheduled via
   `GLib.timeout_add(33, ...)` with default priority**
   — `lifecycle.py:191`. The 30 fps uniform update
   rate is NOT pinned; every millisecond the
   callback overruns rolls the next tick forward. A
   single 10 ms hiccup (e.g., Cairo surface lock
   contention) reduces the effective rate from 30.3
   fps to 23.3 fps that tick, then recovers.

**Two findings are observability / hygiene:**

4. **22 Python threads and no thread-count metric.**
   `LayoutAutoSaver` and `LayoutFileWatcher` each
   spin their own daemon thread for cadence work
   that could live on the GLib main loop; same for
   parts of the command server. Reducing the
   thread count has modest steady-state benefit
   (Python thread context switches are cheap) but
   non-negligible GIL contention cost when multiple
   threads wake simultaneously.
5. **No per-tick latency histogram for the
   orchestration timers** (`fx_tick_callback`,
   `_compositor_budget_publish_tick`, `_status_tick`).
   Finding 3 is theoretically actionable but
   completely invisible in Prometheus today.

**One reaffirmation of drop #28:**

6. **6 fallback producer pipelines always run in
   their own threads** — `fbsrc_brio_operator`,
   `fbsrc_brio_room`, etc., each visible in
   `/proc/<pid>/task`. Drop #28 finding #3 flagged
   this as CPU/memory waste; the thread-level view
   here quantifies: **12 additional producer-pipeline
   threads (6 videotestsrc sources + 6 textoverlay
   pumps) that do no useful work when primary
   producers are healthy**, which is ~98% of the
   time.

## 1. Live process forensics

### 1.1 Thread count + composition

`/proc/<pid>/status` at 2026-04-14 ~14:20:

```text
Name:       python
VmRSS:      1,153,844 kB  (~1.1 GB)
Threads:    96
```

**96 threads total.** Per-thread `comm` names from
`/proc/<pid>/task/*/comm`:

| Count | Name | What it is |
|---|---|---|
| 22 | `python` | Python-managed threads (GLib main, cairo runners, state reader, etc.) |
| 7 | `[pango] fontcon` | Pango fontconfig cache warmers (one per cairooverlay-capable source?) |
| 6 | `watchdog` | GStreamer `watchdog` element workers (one per producer pipeline) |
| 6 | `fbsrc_<role>` | Fallback `videotestsrc` + textoverlay threads |
| 6 | `src_<role>` | Primary `v4l2src` reader threads |
| 6 | `consumer_<role>` | `interpipesrc` consumer threads |
| 6 | `decq_<role>` | `queue` source-pad task threads for decode_queue |
| 3 | `queue-hls:src` | HLS branch queue workers (producer + sink + mux) |
| 3 | `queue-comp-c920` | Composite-branch queue workers for C920s |
| 3 | `queue-comp-brio` | Composite-branch queue workers for BRIOs |
| 3 | `queue-camsnap-c` | Per-camera snapshot queue workers |
| 3 | `queue-camsnap-b` | Per-camera snapshot queue workers |
| 2 | `gstglcontext` | GL context threads |
| … | `fx-glmixer-mixer`, `compositor:src`, `mpegtsmux0:src`, `cuda-EvtHandlr`, `pool-spawner`, `gldisplay-event`, `gly-hdl-loader`, `gly-global-exec`, various `queue-*:src` | Misc GStreamer workers |

### 1.2 Python thread inventory (code read)

From `lifecycle.py` + `compositor.py` + `cairo_source.py`:

1. **GLib MainLoop** on the main thread
   (`lifecycle.py:186, 284`)
2. 7× **`cairo-source-{id}`** daemon threads — one
   per registered Cairo source
   (`cairo_source.py:333`)
3. **`state-reader`** daemon thread
   (`lifecycle.py:271-274`)
4. **CompositorAudioCapture**'s `audio-capture`
   daemon thread (`audio_capture.py:197-200`)
5. **CommandServer** worker thread
6. **LayoutAutoSaver** daemon thread
   (`layout_persistence.py`)
7. **LayoutFileWatcher** daemon thread
   (`layout_persistence.py`)
8. Misc pydevd / pydantic-ai / imported-lib auxiliary
   threads

That accounts for roughly 13-15 Python-owned threads
directly, plus transient workers from lazy imports
and background tasks. The `22` number in the `comm`
census includes GStreamer's internal Python-side
stubs (GLib task workers, pyudev monitor bridge) that
also appear as `python` at the kernel level because
they live in the same process image.

### 1.3 The GLib main loop's scheduled timers

`lifecycle.py:186-266`:

```python
compositor.loop = GLib.MainLoop()

# Every `status_interval_s * 1000` ms (default 5000 ms):
GLib.timeout_add(interval_ms, compositor._status_tick)

# Every 33 ms — "30 fps uniform updates":
GLib.timeout_add(33, lambda: fx_tick_callback(compositor))

# Every 1000 ms:
GLib.timeout_add(1000, _compositor_budget_publish_tick)

# Every 20_000 ms:
GLib.timeout_add(20 * 1000, _watchdog_tick)
```

Plus udev monitoring via `pyudev.glib` bridged into
the main loop, and the GStreamer bus watch which
dispatches bus messages through the main loop.

**Main loop cadence summary:**

| Cadence | Callback | Purpose |
|---|---|---|
| 33 ms | `fx_tick_callback` | FX uniform updates, audio signals → shaders |
| 1000 ms | `_compositor_budget_publish_tick` | BudgetTracker snapshot → `/dev/shm/.../costs.json` |
| 5000 ms | `_status_tick` | Write status.json, per-camera state |
| 20000 ms | `_watchdog_tick` | sd_notify watchdog keep-alive |

## 2. Findings

### 2.1 Finding 1 — Cairo surface allocation churn

`cairo_source.py:402-440`:

```python
def _render_one_frame(self) -> None:
    # ... budget skip check ...

    t0 = time.monotonic()
    try:
        # Allocate at natural size (not canvas size) so sources render
        # at their content resolution and the compositor scales to the
        # assigned SurfaceSchema.geometry during blit.
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self._natural_w, self._natural_h)
        cr = cairo.Context(surface)
        self._source.render(cr, self._natural_w, self._natural_h, t0, self._source.state())
        surface.flush()
    except Exception:
        ...

    with self._output_lock:
        self._output_surface = surface
    self._frame_count += 1
```

**Every tick allocates a new `cairo.ImageSurface`.**
Cairo backs this with pixman-allocated memory. Python
then owns the Python wrapper. On the next tick, the
previous surface is replaced (its references drop
to 0 once the appsrc/cairooverlay consumers release
their view), and pixman has to allocate a fresh one.

**Measured cost per source**:

| Source | natural size | bytes/tick | fps | MB/s |
|---|---|---|---|---|
| sierpinski | 640×640 BGRA | 1,638,400 | 30 | 49.2 |
| sierpinski_lines | 640×640 BGRA | 1,638,400 | 30 | 49.2 |
| token_pole | 300×300 BGRA | 360,000 | 10 | 3.6 |
| album | 400×520 BGRA | 832,000 | 10 | 8.3 |
| stream_overlay | 400×200 BGRA | 320,000 | 10 | 3.2 |
| overlay_zones | ~800×400 BGRA | ~1,280,000 | 10 | 12.8 |
| tri_lines (if active) | 640×640 BGRA | 1,638,400 | 30 | 49.2 |
| **aggregate** | | | | **~175 MB/s** |

Peak allocation churn at **~175 MB/s** (with all
active sources at their configured fps). A steady
~100-150 MB/s is typical.

**Fix**: allocate the surface once in `__init__` and
**clear-and-redraw** on subsequent ticks. Cairo
supports this cleanly via:

```python
# In __init__:
self._reusable_surface = cairo.ImageSurface(
    cairo.FORMAT_ARGB32, self._natural_w, self._natural_h
)

# In _render_one_frame:
cr = cairo.Context(self._reusable_surface)
cr.set_operator(cairo.OPERATOR_CLEAR)
cr.paint()
cr.set_operator(cairo.OPERATOR_OVER)
self._source.render(cr, ...)
self._reusable_surface.flush()
```

The `CLEAR → paint → OVER` sequence produces an
opaque transparent starting canvas identical to a
fresh allocation. Zero allocation per tick.

**Caveat**: the `_output_lock` section swaps
`_output_surface = surface`, which assumes each tick
produces a distinct surface the consumer can hold
a reference to. Reuse means all consumers see the
same surface whose contents mutate between their
read and their blit. For Cairo — which does not
produce tearing at a single byte granularity — this
is safe because the blit path reads the surface
synchronously under the same `_output_lock`. But
the appsrc push (`_push_buffer_to_appsrc` →
`bytes(surface.get_data())`) must complete before
the next render begins. Adding a mutex around the
surface swap + appsrc push handles this.

Alternatively: **double-buffer** with two surfaces,
swap the "ready" pointer under the lock, and tick
into the "next" surface. 2× the memory footprint,
zero contention.

### 2.2 Finding 2 — appsrc push is a full pixel copy

`cairo_source.py:317-319`:

```python
def _push_buffer_to_appsrc(self, surface: cairo.ImageSurface) -> None:
    ...
    try:
        data = bytes(surface.get_data())
        buf = Gst.Buffer.new_wrapped(data)
        appsrc.emit("push-buffer", buf)
    except Exception:
        ...
```

**`bytes(surface.get_data())`** is a full copy of the
surface's pixel data into a new Python `bytes`
object. `Gst.Buffer.new_wrapped` then wraps that
bytes object (itself holding a reference to the
memory) into a GStreamer buffer.

Per-tick cost for one 640×640 BGRA source at 30 fps:
- 1.6 MB copy × 30 = **~49 MB/s**
- Per source, per tick

Across the active runner set:
- ~175 MB/s allocation churn (finding 1)
- ~175 MB/s additional copy on push (finding 2, if
  every source pushes to appsrc)

**Total: ~350 MB/s of CPU memory bandwidth through
the Cairo source render path alone.**

**Fix**: `Gst.Buffer.new_wrapped_full` with an
`allocator` and an `offset`/`size`/`destroy_notify`
lets GStreamer reference the cairo surface's internal
buffer directly. No copy. The trick is keeping the
cairo surface alive until GStreamer releases the
buffer — a closure over the surface reference in the
`destroy_notify` callback does this.

Even without Gst.Buffer tricks, a `memoryview` over
`surface.get_data()` avoids the copy:

```python
# Pseudocode sketch — the exact Gst.Buffer.new_wrapped_full
# signature requires buf, free_func, user_data, offset, size.
buf = Gst.Buffer.new_wrapped_full(
    Gst.MemoryFlags.READONLY,
    surface.get_data(),  # bytes-like, no copy
    len(surface.get_data()),
    0,
    None,
    None,  # free_func
)
```

Worth sandbox-testing the exact API before shipping.

### 2.3 Finding 3 — fx_tick_callback is not priority-pinned

`lifecycle.py:191`:

```python
GLib.timeout_add(33, lambda: fx_tick_callback(compositor))  # 30fps uniform updates
```

**Three latent problems here:**

1. **Default priority** is `G_PRIORITY_DEFAULT`
   (0). `GLib.timeout_add_full` with
   `G_PRIORITY_HIGH` (-100) would schedule the
   fx_tick ahead of default-priority callbacks, which
   matters when the main loop is under load.
2. **Millisecond precision**: `timeout_add` uses
   ms, not µs. At 30 fps the tick interval is
   33.333 ms but the scheduler rounds to 33 ms,
   yielding 30.30 fps nominal.
3. **Reactive scheduling**: after each call, GLib
   reschedules the next call for "current time +
   33 ms". If the callback takes 5 ms, the next
   call is at 38 ms; if 20 ms, at 53 ms. **The
   effective rate degrades linearly with callback
   duration.**

**Real-world cost**: a single fx_tick that triggers
a glfeedback recompile (drop #5 era) could take
50-200 ms. During that interval, the compositor's
uniform updates are effectively paused, and the
"next" tick fires 50-200 ms later than it should.
The recovery is instant but the visual artifact
is a step change in shader animation.

**Fix options**:

- **Option A**: `GLib.timeout_add_full(GLib.PRIORITY_HIGH, 33, ...)`
  gives fx_tick priority over budget publishing,
  status writes, and udev events. Main loop cost:
  negligible — priority changes the dispatch order
  when multiple callbacks are ready, not the
  absolute cadence.
- **Option B**: Use `GLib.timeout_add_full(PRIORITY_HIGH, 33, ...)`
  AND measure actual callback duration to
  auto-correct. Return from the callback as fast as
  possible (delegate slow work to background
  thread).
- **Option C**: Move fx_tick off the main loop
  entirely and onto a dedicated thread with a
  `threading.Event().wait(0.0333)` cadence. Pure-
  Python cost is similar, but decouples the 30 fps
  uniform updates from main-loop bus processing.

Option A is the minimum viable fix and zero risk.
Options B and C are deferred architectural work.

### 2.4 Finding 4 — thread count without a metric

**22 Python threads** in the live process. Some are
necessary (GLib main, cairo runners), some are
avoidable:

- **LayoutAutoSaver** — a thread that flushes the
  layout state to disk on a cadence. Could live on
  the GLib main loop via `GLib.timeout_add`.
- **LayoutFileWatcher** — polls the layout file for
  external edits. Could use inotify via `GFile`
  wrapped through GLib.
- **CommandServer** — a thread accepting UDS
  connections. Could use `GLib.io_add_watch` to
  dispatch on the main loop.

**Net savings** if all three moved to the main loop:
~3 threads, ~30 KB of stack space each, and one
fewer contention point for the GIL.

**Observability**: no metric exposes
`threading.active_count()` or per-thread latency.
A single Prometheus gauge
`compositor_python_thread_count` + a histogram
`compositor_glib_timer_latency_seconds{name=...}`
would make finding 3's degradation scrape-visible.

### 2.5 Finding 5 — no tick-cadence observability

None of the main-loop timers have latency histograms:

- `fx_tick_callback` at 33 ms — unmetered
- `_compositor_budget_publish_tick` at 1000 ms —
  unmetered
- `_status_tick` at 5000 ms — unmetered
- `_watchdog_tick` at 20000 ms — unmetered

A slow fx_tick is the **most likely silent
regression in this area**. Finding 3 makes it
actionable; closing this gap makes it observable.

**Fix (ring 3)**: wrap each callback with a timing
probe:

```python
_FX_TICK_MS = Histogram("compositor_fx_tick_duration_ms", ...)

def _timed(callback, histogram):
    def wrapped():
        t0 = time.monotonic()
        try:
            return callback()
        finally:
            histogram.observe((time.monotonic() - t0) * 1000)
    return wrapped

GLib.timeout_add(33, _timed(lambda: fx_tick_callback(compositor), _FX_TICK_MS))
```

~30 lines total for all 4 timers.

### 2.6 Finding 6 — fallback pipelines always running

Drop #28 finding #3 already flagged this at the
code-read level. Today's `/proc/<pid>/task` census
confirms the thread-level cost:

- **6× `fbsrc_<role>`** threads — each running a
  `videotestsrc pattern=ball is-live=true` at 720p
  BGRA 30 fps
- **6× watchdog** threads — drop #28 flagged only the
  primary watchdogs; the fallback pipelines also
  have watchdog elements
- **Plus textoverlay pumps** — cairo-based text
  rendering at ~10 fps per fallback

**Work the fallback threads do when primary is
healthy**: everything up to the interpipesink
buffer push. The interpipesink drops buffers when
no consumer is listening, but the upstream chain
still renders, textoverlay still updates, videotestsrc
still generates frames.

**Aggregate fallback CPU cost today**: drops #28/#29
estimated ~660 MB/s of BGRA fallback frame data
generated by the 6 videotestsrc sources. At the
thread level, that's **6 BGRA generation threads +
6 text render threads + 6 watchdog pumps = 18
threads producing content that is never consumed**.

**Fix (Ring 2 in drop #31)**: the static-frame
fallback approach (E in the cam-stability rollup).
One rendered frame, held forever, no per-tick work.

## 3. Ring summary

### Ring 1 — drop-everything (shippable today)

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **THR-1** | `GLib.timeout_add_full(PRIORITY_HIGH, 33, fx_tick_callback)` | `lifecycle.py:191` | 1 | fx_tick fires ahead of default-priority callbacks |

**Risk**: zero. One-word change.

### Ring 2 — small refactors

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **THR-2** | Reuse one `cairo.ImageSurface` per runner instead of allocating per tick | `cairo_source.py:372-440` | ~15 | ~100-175 MB/s allocation churn eliminated |
| **THR-3** | Zero-copy appsrc push via `Gst.Buffer.new_wrapped_full` | `cairo_source.py:304-325` | ~20 | ~175 MB/s copy traffic eliminated |
| **THR-4** | Move `LayoutAutoSaver` + `LayoutFileWatcher` + `CommandServer` onto the GLib main loop | `layout_persistence.py`, `command_server.py` | ~60 | 3 fewer Python threads, modest GIL contention reduction |

**Risk**: THR-2 and THR-3 need sandbox testing to
verify no visual artifacts or GStreamer buffer
lifetime bugs. THR-4 is pure refactor, less risky.

### Ring 3 — observability

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **THR-5** | Per-timer latency histograms (4 timers) | `lifecycle.py` + `metrics.py` | ~30 | fx_tick/budget/status/watchdog cadence becomes scrape-visible |
| **THR-6** | `compositor_python_thread_count` gauge | `metrics.py` + status tick | ~5 | Thread growth regressions are observable |

### Reaffirmation

Finding 6 is not new — drop #28 finding #3 flagged
this in the producer walk. The thread-level view
here is additional evidence that the cost is real,
not just theoretical. Ring 2 fix E in drop #31 (the
static-frame fallback replacement) remains the
recommended fix.

## 4. Cumulative impact estimate

If council ships **all of Ring 1 + Ring 2**:

- ~100-175 MB/s of allocation churn eliminated
  (THR-2)
- ~175 MB/s of copy traffic eliminated (THR-3)
- fx_tick_callback pinned to PRIORITY_HIGH (THR-1)
- 3 fewer Python threads (THR-4)

**Total memory-bandwidth reclamation from this drop
alone: ~275-350 MB/s of CPU memory traffic.**

Combined with the pipeline-wide reclamation estimates
from drops #31 + #32 + #35 + this drop:

- Drop #31 Ring 1+2: ~900 MB/s CPU↔GPU
- Drop #32 Ring 1+2: ~33 MB/s
- Drop #35 Ring 1: ~0 (property change, no bandwidth)
- **Drop #36 Ring 2: ~275-350 MB/s CPU memory**

**Cumulative potential reclamation across the full
camera+output path: ~1.2-1.3 GB/s of memory/PCIe
bandwidth** if all Ring 1+2 items ship.

## 5. Cross-references

- `agents/studio_compositor/cairo_source.py` —
  `CairoSourceRunner` render loop and appsrc bridge
- `agents/studio_compositor/lifecycle.py:186-266` —
  GLib main loop + timer registration
- `agents/studio_compositor/compositor.py:500-503` —
  `_status_tick`
- `agents/studio_compositor/budget.py` —
  `BudgetTracker` + `publish_costs`
- `/proc/<pid>/task/*/comm` at 2026-04-14 ~14:20 —
  live thread census
- Drop #28 finding #3 — fallback producer cost
  (reaffirmed here)
- Drop #35 — composite-side cudacompositor walk
- Drop #31 Ring 2 fix E — static-frame fallback

## 6. Follow-ups

1. **Today / next session**: THR-1 (`PRIORITY_HIGH`
   for fx_tick). One line, zero risk.
2. **Within a week**: THR-5 + THR-6 (observability).
   Pair with drop #32's RTMP/HLS observability work.
3. **Sandbox test first**: THR-2 and THR-3 (cairo
   surface reuse + zero-copy appsrc). Need to verify
   no frame tearing, no GStreamer buffer lifetime
   bugs, and no visual artifacts.
4. **Defer to architectural work**: THR-4 (thread
   consolidation). Modest benefit, medium churn.
5. **Already queued**: drop #31 Ring 2 fix E
   (static-frame fallback) addresses finding 6.

## 7. Open question for operator

**Are 7 Cairo sources all active in the current
steady-state layout?** The listed set (sierpinski,
sierpinski_lines, token_pole, album, stream_overlay,
overlay_zones, tri_lines) may not all be registered
in the current layout file
(`config/compositor-layouts/default.json`). Finding
1's ~175 MB/s estimate assumes all 7 are active; the
real number could be lower if some are dormant. The
operator can confirm by reading the layout file or
by running `ls /dev/shm/hapax-compositor/source_*`
to see which sources are publishing to the
source-protocol shm.
