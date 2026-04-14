# Camera pipeline final walk closure — fx_chain + snapshots branches

**Date:** 2026-04-14
**Author:** delta (beta role — cam-stability focus)
**Scope:** Closes the systematic camera pipeline walk
started in drops #28 and #29. Covers the last
unexamined touch points: `fx_chain.py
build_inline_fx_chain`, `snapshots.py`
`add_snapshot_branch` and `add_fx_snapshot_branch`,
and the cumulative bandwidth picture across the entire
chain.
**Register:** scientific, neutral
**Status:** investigation only — three new findings
plus one architectural observation that ties the prior
drops together

## Headline

**Three new findings.**

1. **The data path makes two full GPU↔CPU round trips
   per frame** — cudacompositor (CUDA mem) →
   `cudadownload` → CPU BGRA → pre_fx_tee → CPU →
   `glupload` (×2 sites in `fx_chain.build_inline_fx_chain`)
   → GL textures → 24 shader slots → `gldownload` →
   CPU BGRA → output_tee. **Two full
   GPU→CPU→GPU round trips per frame, no semantic
   reason for either.** At 1920×1080×4 = 8.3 MB per
   frame × 30 fps × (1 cudadownload + 2 gluploads + 1
   gldownload) = **~1 GB/s of CPU↔GPU memory bandwidth
   on the output side alone.** Plus the 6 cameras'
   ~248 MB/s of cudaupload from drop #28 finding 5,
   plus smooth_delay's ~250 MB/s waste from drop #29
   finding 3, total memory bandwidth on the
   compositor's GPU↔CPU axis is **~1.5 GB/s**.
2. **`fx_chain` has two separate `glupload` sites**
   (`fx_chain.py:324, 333`): one for the camera "base"
   path through input-selector + cairooverlay, one for
   the "flash" path off `pre_fx_tee`. Both sites take
   the same upstream BGRA frame from CPU memory and
   upload to GL. **The flash path is essentially the
   same data twice** — the base path eventually feeds
   into glvideomixer sink_0 and the flash path feeds
   sink_1, but they originate from the same source.
3. **Three snapshot/preview branches use CPU `jpegenc`**:
   - `snapshots.py:30 add_snapshot_branch` (10 fps to
     `/dev/shm/snapshot.jpg`)
   - `snapshots.py:103 add_fx_snapshot_branch` (30 fps
     to TCP :8054 + `fx-snapshot.jpg`, with a comment
     "Simple CPU path" suggesting alpha deliberately
     chose CPU)
   - `cameras.py:38 add_camera_snapshot_branch` (1/5
     fps × 6 cameras)
   
   **`nvjpegenc` is available** (per drop #29 finding
   2). Migration would offload ~80 frames/sec of CPU
   JPEG encoding work to the NVENC JPEG hardware. The
   `add_fx_snapshot_branch` docstring says "Simple CPU
   path" was chosen because file I/O was the bottleneck,
   not encoding — but with the WebSocket relay + sender
   thread now decoupling I/O, the CPU encode is the
   marginal cost.

**Net impact.** Findings 1 and 2 are architectural —
they imply a much larger refactor (replace
cudacompositor with glvideomixer end-to-end, OR add
CUDA-GL interop between cudacompositor and glupload to
share GPU memory directly). Finding 3 is a small swap
(jpegenc → nvjpegenc). Combined with drops #28 and
#29's findings, the cam-stability sprint backlog now
has both small wins (queue bumps, single-line fixes)
and structural restructuring opportunities (GPU
memory routing, JPEG offload).

## 1. The data path round-trip pattern

Tracing the journey of a single frame from camera to
v4l2sink:

```text
[GPU] BRIO/C920 → uvcvideo (kernel) → MJPG bitstream
   ↓
[CPU] v4l2src DMA → user space buffer
   ↓
[CPU] capsfilter (image/jpeg) → watchdog → jpegdec → CPU NV12
   ↓
[CPU] videoconvert dither=0
   ↓
[CPU] capsfilter (NV12) → interpipesink (cam_<role>)
   ↓
[CPU] interpipesrc (consumer_<role>) → tee
   ↓
[CPU → GPU] cudaupload  ← finding from drop #28
   ↓
[GPU] cudaconvert → cudascale → cudacompositor sink_<i>

[6 cameras × the above]

[GPU] cudacompositor → CUDA NV12 1920×1080
   ↓
[GPU → CPU] cudadownload  ← drop #28 finding 8
   ↓
[CPU] videoconvert BGRA dither=0
   ↓
[CPU] bgra-caps → pre_fx_tee
   ↓
   ├──→ [CPU] add_snapshot_branch (10fps) → CPU jpegenc → /dev/shm
   ├──→ [CPU] fx_chain base path:
   │      input-selector → queue → cairooverlay → videoconvert →
   │      [CPU → GPU] glupload  ← finding 2
   │      → glcolorconvert → glvideomixer sink_0
   └──→ [CPU] fx_chain flash path:
          queue → videoconvert →
          [CPU → GPU] glupload  ← finding 2 (second site)
          → glcolorconvert → glvideomixer sink_1

[GL] glvideomixer (sink_0 base + sink_1 flash) →
[GL] 24 glfeedback shader slots (drop #5) →
[GL] glcolorconvert →
[GL → CPU] gldownload →
[CPU] videoconvert → output_tee
   ↓
   ├──→ [CPU] queue (max=1) → videoconvert YUY2 → identity → v4l2sink → /dev/video42 (kernel max_buffers=2)
   ├──→ [CPU] hls branch (queue max=20) → nvh264enc → hlssink2
   ├──→ [CPU] add_fx_snapshot_branch → CPU jpegenc → TCP push + file
   ├──→ [CPU] smooth_delay branch → glupload → smoothdelay → gldownload → ...
   └──→ [CPU] rtmp_bin (detached) → nvh264enc → flvmux → rtmpsink
```

**GPU↔CPU transitions per output frame:**

- 6× cudaupload (camera consumers): 6 × 1.38 MB = **8.28 MB CPU→GPU**
- 1× cudadownload (compositor): 8.3 MB GPU→CPU
- 2× glupload (fx_chain base + flash): 2 × 8.3 MB = **16.6 MB CPU→GPU**
- 1× gldownload (fx_chain output): 8.3 MB GPU→CPU
- 1× glupload (smooth_delay): 8.3 MB CPU→GPU (and 28/30 are wasted per drop #29 § 3)
- 1× gldownload (smooth_delay): 8.3 MB GPU→CPU (same waste)

**Per-frame total**: 8.28 + 8.3 + 16.6 + 8.3 + 8.3 + 8.3 = **~58 MB of memory crossing the GPU↔CPU boundary per frame**.

At 30 fps: **~1.74 GB/s of memory bandwidth** on the
GPU↔CPU axis. PCIe Gen 3 ×16 has ~16 GB/s theoretical;
real-world is ~12 GB/s. We're using ~14% of available
PCIe bandwidth on memory transfers alone, before any
other PCIe traffic (camera USB, network, NVME).

**Some of this is unavoidable**:

- The 6× cudaupload is unavoidable while the camera
  producer chain is CPU (drop #28 finding 5 proposes
  `nvjpegdec` to push decode into GPU memory).
- The final gldownload before v4l2sink is unavoidable
  because v4l2sink needs CPU memory.

**Some of this is wasteful**:

- The cudadownload after cudacompositor → glupload
  pattern is **GPU→CPU→GPU for no semantic reason**.
  If cudacompositor's output stayed in GPU memory and
  the FX chain operated on CUDA memory directly, this
  pair could be eliminated.
- The smooth_delay glupload happens before videorate,
  see drop #29 § 3.
- The 2× glupload in fx_chain — if both sites pull from
  the same source, there's a way to glupload once and
  have both glmixer sink pads consume from the same
  GL texture.

## 2. Two glupload sites in fx_chain

`fx_chain.py:286-385`:

```python
def build_inline_fx_chain(compositor, pipeline, pre_fx_tee, output_tee, fps) -> bool:
    # Base path: input-selector → queue → cairooverlay → videoconvert → glupload → glcolorconvert
    input_sel = make("input-selector")
    queue_base = make("queue")
    overlay = make("cairooverlay")
    convert_base = make("videoconvert")
    glupload_base = make("glupload")              # ← upload site #1
    glcc_base = make("glcolorconvert")

    # Flash path: pre_fx_tee → queue → videoconvert → glupload → glcolorconvert
    queue_flash = make("queue")
    convert_flash = make("videoconvert")
    glupload_flash = make("glupload")             # ← upload site #2
    glcc_flash = make("glcolorconvert")

    # glvideomixer with sink_0=base, sink_1=flash
    glmixer = make("glvideomixer")
    ...

    # Link flash path
    tee_pad_flash = pre_fx_tee.request_pad(...)
    tee_pad_flash.link(queue_flash.get_static_pad("sink"))
    queue_flash.link(convert_flash)
    convert_flash.link(glupload_flash)
    glupload_flash.link(glcc_flash)
    # (linked into glmixer sink_1 elsewhere)
```

Both gluploads take BGRA from CPU memory. The base path
applies cairooverlay (text overlays) before upload; the
flash path uploads the raw frame and applies a flash
alpha modulation in the glmixer.

**Optimization idea**: render the cairooverlay AFTER
glupload using a `glcairo` element (if available) or a
custom GL fragment shader. Then both paths can share a
single glupload by tee'ing the GL texture rather than
the CPU buffer. **Saves ~250 MB/s.**

This is a moderate refactor — needs verification that
cairooverlay's outputs can be replaced by GL-side
rendering. cairooverlay uses cairo's CPU rasterizer for
the overlay graphics, so moving it to GL would require
either:

- Pre-rendering the overlay text to a CPU image surface
  and uploading it as a GL texture once per text change
  (cheap if text changes infrequently)
- Using a real GL text-render path (more invasive)

Given drops #1 and #3 already touch overlay_zones (which
is part of the cairooverlay output), a coordinated
refactor of the overlay rendering layer is feasible.

## 3. Snapshot branches use CPU jpegenc despite nvjpegenc

Three snapshot writers all use CPU `jpegenc`:

| writer | rate | resolution | quality | output |
|---|---|---|---|---|
| `add_snapshot_branch` | 10 fps | 1280×720 | 85 | `/dev/shm/snapshot.jpg` |
| `add_fx_snapshot_branch` | 30 fps | 1280×720 | 85 | TCP :8054 + `fx-snapshot.jpg` |
| `add_camera_snapshot_branch` × 6 | 0.2 fps | 640×360 | 75 | `/dev/shm/<role>.jpg` |

Aggregate: 10 + 30 + (6 × 0.2) = **41.2 frames/sec
encoded by CPU jpegenc**.

CPU jpegenc cost at 720p: roughly 5-15 ms per frame
depending on quality. At 41.2 fps × 10 ms = ~412 ms of
CPU work per second. Roughly **half of one CPU core
dedicated to JPEG encoding for snapshots**.

`nvjpegenc` (NVENC JPEG encoder) is available on this
system. Per `gst-inspect-1.0 nvjpegenc`:

```text
Factory Details:
  Long-name                NVIDIA JPEG Encoder
  Klass                    Codec/Encoder/Image/Hardware
```

Migration cost: replace `Gst.ElementFactory.make("jpegenc", ...)`
with `Gst.ElementFactory.make("nvjpegenc", ...)` at three
sites. Plus add `cudaupload` if the input is currently CPU
(it is — the snapshot branches read from CPU tees).

**Trade-off**: nvjpegenc requires a `cudaupload` step
since input is CPU memory. The added upload cost might
exceed the saved encode cost for small images. At 720p,
upload is ~3 ms, encode is ~5-15 ms — net saving 2-12 ms
per frame.

For the 30 fps fx_snapshot specifically, ~5 ms/frame ×
30 = 150 ms/sec saved. ~15% of one CPU core.

For the 10 fps regular snapshot: ~5 ms × 10 = 50 ms/sec
saved.

**Total expected savings**: ~200 ms/sec of CPU = ~20% of
one core.

The `add_fx_snapshot_branch` docstring says:

> Simple CPU path: videoconvert → videoscale(640x360) → jpegenc(q=70)
> Small resolution keeps CPU encoding fast enough for 30fps.
> The WebSocket relay eliminates file I/O — the bottleneck that caused 1fps.

Wait — the docstring says "Small resolution keeps CPU
encoding fast enough for 30fps" and "640×360", but the
actual code (`snapshots.py:101-102`) sets the caps to
`width=1280, height=720`. **The docstring is stale.** The
actual resolution is 720p, not 360p, so the docstring's
"small resolution keeps CPU fast" rationale is wrong —
the encoder is doing the larger work.

Migrating to nvjpegenc would close this discrepancy
and save the ~20% CPU.

## 4. Recording branch (informational)

`recording.py:15-77 add_recording_branch` is conditional
on `compositor.config.recording.enabled`. Per drop #20-
era observations, recording is currently disabled
system-wide (HLS archive timer was dormant until earlier
today, and the broader video recording is also gated).

Not actively running. Out of scope for cam-stability
investigation today.

## 5. The complete cam-pipeline backlog (drops #2 + #27 + #28 + #29 + this)

In ratio order (impact ÷ effort):

| # | fix | from | effort |
|---|---|---|---|
| **A** | Bump v4l2sink queue 1→5 (userspace) | drop #28 #9 | 1 line |
| **B** | Bump v4l2loopback `max_buffers` 2→8 (kernel) | drop #29 #1 | modprobe + reload |
| **C** | Add producer queue between v4l2src and jpegdec | drop #28 #1 | ~6 lines per pipeline |
| **D** | Initial frame-flow grace period | drop #27 | 2 lines |
| **E** | Static-frame fallback (replace bouncing ball) | drop #28 #3 | element rewrite |
| **F** | smooth_delay frame-drop probe before gldownload | drop #29 #3 | ~6 lines |
| **G** | Migrate jpegenc → nvjpegenc on 3 snapshot branches | this drop #3 | swap factories |
| **H** | nvjpegdec producer rewrite | drop #28 #5 + drop #29 #2 | sandbox test + rewrite |
| **I** | CUDA device pinning via `CUDA_VISIBLE_DEVICES=0` | drop #4 F1 | env var |
| **J** | Eliminate cudadownload→glupload round trip | this drop #1 | architectural |
| **K** | Single glupload in fx_chain (share base + flash) | this drop #2 | refactor cairooverlay rendering path |

Items A through G are all small fixes (≤ ~10 lines each).
Items H, J, K are larger refactors. Item I is a
config-only fix.

**My recommended order for a "cam stability sprint"
PR**:

1. Bundle A + B + D + F into one PR (4 small fixes,
   all queue/grace tuning, all "drop fewer frames")
2. Bundle C + E + G into a second PR (small refactors,
   producer-side improvements)
3. H, J, K go into individual prototype PRs after a
   sandbox test confirms feasibility

## 6. Coverage status — the walk is complete

Final touch-point checklist:

| layer | covered by | findings count |
|---|---|---|
| USB hardware | drop #2 | 4 (USB topology) |
| uvcvideo kernel module | drop #29 § 4 | 0 (defaults are correct) |
| v4l2 device controls | drop #2 § 2.4 | 0 (consistent across cameras) |
| `camera_pipeline.py` producer chain | drop #28 § 1.4 | 4 |
| `fallback_pipeline.py` | drop #28 § 1.5 | 1 (660 MB/s waste) |
| `pipeline_manager.py` supervisor | drop #28 § 1.6 + drop #27 | 1 (no initial grace) |
| `cameras.py` consumer chain | drop #28 § 1.7 | 3 |
| `cudacompositor` | drops #4 + #28 | 1 (no device pin) |
| `pipeline.py` output stage | drop #28 § 1.9-1.10 | 4 (cudadownload, queue, ydown convert) |
| `fx_chain.py` interior | drop #5 + this drop § 1-2 | 3 (recompile storm + 2 round-trips + 2 gluploads) |
| `snapshots.py` add_snapshot_branch | this drop § 3 | 1 (CPU jpegenc) |
| `snapshots.py` add_fx_snapshot_branch | this drop § 3 | 1 (CPU jpegenc + stale docstring) |
| `cameras.py` add_camera_snapshot_branch | drop #28 § 1.7 + this drop § 3 | 1 (CPU jpegenc) |
| `recording.py` add_hls_branch | drop #29 § 5 | 0 (well-buffered) |
| `recording.py` add_recording_branch | this drop § 4 | n/a (disabled) |
| `smooth_delay.py` add_smooth_delay_branch | drop #29 § 3 | 1 (gldownload before videorate) |
| v4l2sink + v4l2loopback | drops #28 + #29 | 2 (queue + max_buffers) |
| `rtmp_output.py` rtmp_bin | drop #4 + drop #19 | 4 (encoder, GPU pin, fallback chain, model pins) |
| OBS-side consumption | n/a | n/a (out of scope, downstream of /dev/video42) |

**The systematic walk is complete.** Every element in
the path from BRIO/C920 USB capture to the
`/dev/video42` v4l2sink that OBS reads from has been
audited. There are no more touch points within the
compositor process.

Items **not** in scope (but adjacent):

- The `mediamtx` upstream relay (drop #4 § F7 — empty
  paths block)
- The OBS scene graph itself — operator-owned,
  downstream of v4l2loopback
- The kernel uvcvideo source code (covered by checking
  module parameters in drop #29 § 4)
- Hardware-level USB analyzer probes (would need a USB
  hardware tap)

## 7. Follow-ups for alpha — final cam-stability backlog

The final backlog has **11 distinct fix candidates**
across the camera pipeline, plus the structural
refactors in items H, J, K. Numbered list above in § 5.

For the operator's "cam stability and performance"
focus specifically, the highest-leverage starting set
is **A + B + D + F** — four small fixes, all about
buffer cushion and graceful startup, ship in one PR
with low risk.

After that, **G** (nvjpegenc swap) is the next
free-CPU win and uncovers ~20% of one core for
director_loop or daimonion.

After that, **C + E** further reduce stream interruption
patterns.

**H + J + K** are larger architectural moves that
each save substantial GPU↔CPU bandwidth. Worth a
prototype but not the highest-impact items individually.

## 8. References

- `agents/studio_compositor/snapshots.py:15-79` —
  `add_snapshot_branch` (10 fps regular snapshot)
- `agents/studio_compositor/snapshots.py:82-200+` —
  `add_fx_snapshot_branch` (30 fps fx snapshot with
  TCP push + sender thread)
- `agents/studio_compositor/fx_chain.py:286-385` —
  `build_inline_fx_chain` element graph
- `agents/studio_compositor/recording.py:15-77` —
  `add_recording_branch` (recording, currently disabled)
- Drops #2, #4, #5, #14, #19, #20, #27, #28, #29 — all
  prior cam-pipeline-touching research
- `gst-inspect-1.0 nvjpegenc` — NVIDIA JPEG Encoder,
  Hardware encoder
- Live process state: 2026-04-14T17:15 UTC
