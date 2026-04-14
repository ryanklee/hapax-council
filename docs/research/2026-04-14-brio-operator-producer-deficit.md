# brio-operator producer-thread frame deficit — root-cause probe

**Date:** 2026-04-14
**Author:** delta (beta role)
**Scope:** Follow-up to sprint-1 F3 (brio-operator at 28.50 fps, deficit
attributed to producer-thread side) and to the compositor frame-budget
errata (today's histogram baseline: brio-operator 27.94 fps sustained,
six-hour window). Asks: what component in the brio-operator capture
path is dropping ~45 300 frames over a 6 h window relative to its
peers?
**Register:** scientific, neutral
**Status:** investigation only — no code change. No root cause
concluded; four rival hypotheses remain open.

## Headline

**Five findings.**

1. **The deficit is sustained and uniform, not bursty.** Six-hour
   histogram for brio-operator: p50 ≈ 35.8 ms, p95 ≈ 40 ms, p99 ≈ 40 ms,
   no long tail beyond 50 ms. Every frame runs ~3 ms later than its
   c920-desk peer; no frames occasionally freeze. A stall would show a
   long tail, it doesn't. This is a rate-shift, not a stall profile.
2. **Every system-level variable that could explain the deficit is
   identical to brio-operator's 30-fps peer on the same bus.** Same
   xHCI controller (AMD Matisse, PCI 09:00.3), same IRQ (66), same
   CPU (7), same USB 3.0 link speed (5000 Mbps), same USB power
   control (`on`), same compositor config (exposure 333, sharpness 128),
   same negotiated v4l2 format (1280×720 MJPG 30.000 fps), same GStreamer
   pipeline template. brio-synths, sharing every one of these, runs at
   29.99 fps (648 178 frames in the same window).
3. **The compositor's `studio_camera_kernel_drops_total` counter reports
   `0.0` for all six cameras** over a 6-hour window at 30 fps with
   ~650 000 frames each — including c920-desk which has been through
   USB bus-kicks and recoveries. This counter is almost certainly a
   dead metric for the MJPG BRIO/C920 path: the v4l2 sequence-gap
   detector that feeds it is not firing because uvcvideo's MJPG
   payload does not expose a monotonic sequence field the detector
   can observe. **There is currently no way, in compositor metrics
   alone, to distinguish a kernel-layer drop from a producer-thread
   stall.**
4. **v4l2 layer and producer layer disagree.** v4l2-ctl against
   brio-operator says 30.000 fps (30/1) in the streaming parameters.
   The `studio_camera_frame_interval_seconds` histogram, measured
   at the producer interpipesink sink pad, says 27.94 fps. ~45 300
   frames exist between the v4l2 advertised rate and the interpipesink
   rate. Kernel-drops counter stays 0. Frames are either being dropped
   inside the v4l2src → jpegdec → interpipesink chain with no counter,
   or the camera firmware is delivering frames to the kernel at
   27.94 fps and the 30-fps advertisement is aspirational.
5. **brio-operator had one `FRAME_FLOW_STALE` transition** in this
   process uptime (at 09:35:21 CDT, the session's cold start). The
   watchdog bumped it `healthy → degraded → offline → recovering →
   healthy` in ~3 s, then back to steady state.
   `studio_camera_transitions_total` confirms 4 transitions, 1 of each
   edge, which matches a single recovery cycle. **No further
   transitions for the remaining ~10 h.** The 6.9 % deficit is
   happening in the *healthy* state, not during any reconnect event.

## 1. Question

The research map target is rock-steady 30 fps on every camera source
before compositing. Sprint-1 F3 (2026-04-13) established that
brio-operator's deficit is not USB-2.0-bandwidth-bound — the camera
sits on a 5000 Mbps bus with headroom — and the deficit must therefore
originate on the producer-thread side. Twelve hours later, what
specifically on the producer side is responsible, and can any of the
compositor's existing counters identify it?

## 2. Live measurement

All observations captured 2026-04-14T14:45–15:00 UTC on a
`studio-compositor` process uptime of ~21 600 s (launched 09:35 CDT).
Six cameras live, `hapax_working_mode=rnd`.

### 2.1 Histogram baseline — six-hour window

From `studio_camera_frame_interval_seconds_sum / _count`:

| role | count | mean interval (ms) | mean fps | frames missed vs peer |
|---|---|---|---|---|
| c920-desk | 649 225 | 33.33 | 30.00 | (reference) |
| brio-room | 649 213 | 33.33 | 30.00 | +12 |
| c920-room | 649 321 | 33.33 | 30.00 | −96 |
| c920-overhead | 649 336 | 33.32 | 30.01 | −111 |
| brio-synths | 648 947 | 33.35 | 29.99 | +278 |
| **brio-operator** | **604 565** | **35.79** | **27.94** | **+44 660** |

brio-operator is the only outlier. The other five cameras are within
±0.05 % of each other.

### 2.2 Bucket distribution — rate shift vs stall signature

c920-desk cumulative:

```text
le=0.030   31 460       4.8 %
le=0.033  344 024      53.0 %   ← median
le=0.040  645 060      99.4 %   ← p99 ≈ 40 ms
le=0.050  647 964      99.8 %
le=0.067  648 122     99.99 %
```

brio-operator cumulative:

```text
le=0.030    4 744        0.8 %
le=0.033   56 490        9.4 %   ← only 9.4 % of frames under 33 ms
le=0.040  586 431       97.2 %   ← p95 ≈ 40 ms
le=0.050  603 241       99.9 %
le=0.067  603 517     99.99 %
```

**Interpretation.** c920-desk's median is at 33 ms (perfect 30 fps);
brio-operator's median is at ~36 ms. Both have the same shape of long
tail (< 0.1 % beyond 50 ms). Every frame in brio-operator's histogram
is shifted ~3 ms later than c920-desk's. **A producer-thread stall or
USB reset would show a long tail beyond 50 ms — it does not.** What
brio-operator shows is a uniform rate reduction, not an occasional
hang.

### 2.3 Kernel-drops counter is a silent dead metric

```text
studio_camera_kernel_drops_total{role="brio-operator"}  0.0
studio_camera_kernel_drops_total{role="brio-room"}      0.0
studio_camera_kernel_drops_total{role="brio-synths"}    0.0
studio_camera_kernel_drops_total{role="c920-desk"}      0.0
studio_camera_kernel_drops_total{role="c920-overhead"}  0.0
studio_camera_kernel_drops_total{role="c920-room"}      0.0
```

Zero for all six, over 6 h of 30 fps capture with ~650 000 frames
each. The metric help text: _"Frames dropped at the kernel/USB
level (from v4l2 sequence gaps)"_. The v4l2 sequence field is only
populated for MMAP buffers with drivers that expose monotonic
sequence — uvcvideo's MJPG payload path is known not to expose
reliable sequence numbers. This counter is almost certainly a false
zero for the MJPG BRIO/C920 path. **Whatever is producing the
brio-operator deficit is not discoverable through this metric.**

### 2.4 System-level variables — all identical to 30 fps peer

| variable | brio-operator (27.94 fps) | brio-synths (29.99 fps) | brio-room (30.00 fps) |
|---|---|---|---|
| xHCI controller PCI | 0000:09:00.3 (AMD Matisse) | 0000:09:00.3 | 0000:01:00.0 (AMD 500) |
| xHCI IRQ | 66 | 66 | 57 |
| CPU handling IRQ | 7 | 7 | 5 |
| USB link speed | 5000 Mbps | 5000 Mbps | 480 Mbps |
| USB power control | `on` | `on` | `auto` |
| v4l2 format | 1280×720 MJPG | 1280×720 MJPG | 1280×720 MJPG |
| v4l2 advertised rate | 30.000 fps (30/1) | 30.000 fps (30/1) | 30.000 fps (30/1) |
| configured exposure | 333 | 333 | 333 |
| configured sharpness | 128 | 128 | 128 |
| physical port | usb4/4-3 | usb4/4-1 | usb1/1-3 |
| serial | 5342C819 | 9726C031 | 43B0576A |

**brio-synths is the control variable.** It shares the xHCI
controller, IRQ, CPU, link speed, power control, v4l2 config, and
GStreamer pipeline template with brio-operator, differing only in
physical port and device serial. brio-synths runs at 29.99 fps; the
6.9 % deficit therefore cannot be explained by any variable that
brio-operator shares with brio-synths.

**brio-room is the cross-controller control.** Different xHCI, lower
USB link speed, different IRQ and CPU, slower bus. Runs at 30.00 fps.
USB 2.0 speed is therefore ruled out as a ceiling (brio-room hits
30 fps on USB 2.0 HS).

### 2.5 GStreamer pipeline config — identical

All six cameras go through the `camera_pipeline_<role>` template with
identical element construction: `v4l2src` → `jpegdec` → `interpipesink`.
Configured at `1280x720@30fps, format=mjpeg` for all six per the
compositor journal at process start. No per-camera branch in the
template that could explain the deficit.

### 2.6 Compositor scheduling

```text
taskset -p 3013869   → affinity mask: ffff (all 16 threads)
chrt    -p 3013869   → SCHED_OTHER, priority 0, runtime parameter 1.4e6
/proc/3013869/stat   → nice -12
```

CFS, nice −12, no CPU pinning. Compositor has high CPU priority
access across all cores. Scheduler class is the same for every camera
producer thread inside the process. No differential thread affinity is
configured in the compositor for individual cameras.

## 3. Hypothesis tests

### H1 — "USB 2.0 bus speed limits brio-operator"

**Refuted** (sprint-1 F3, re-confirmed today). brio-operator is on a
5000 Mbps USB 3.0 Gen 1 link at `/sys/bus/usb/devices/4-3/speed=5000`.
brio-room runs at 30 fps on a 480 Mbps link. Bus speed is not the
cap.

### H2 — "IRQ affinity / CPU contention on AMD Matisse xHCI"

**Refuted.** brio-synths is on the same xHCI controller, same IRQ 66,
same CPU 7, same link speed. If IRQ contention were the cause,
brio-synths would also be slow. brio-synths is not slow. 105 M
interrupts on CPU 7 have been absorbed over the session with no
throughput penalty for brio-synths.

### H3 — "v4l2 kernel drops from buffer starvation"

**Not directly testable with current telemetry.**
`studio_camera_kernel_drops_total` is almost certainly a dead metric
for MJPG (see § 2.3). Buffer starvation inside v4l2src remains
possible but cannot be confirmed or refuted against the existing
counters. To close: capture `v4l2-ctl --verbose --stream-count=300
--stream-to=/dev/null` on brio-operator and brio-synths side-by-side
and compare reported frame counts to wall-clock. If brio-operator
reports 272 frames in 10 s while brio-synths reports 300, the v4l2
layer itself is losing them. If both report 300, the loss is
downstream (jpegdec, interpipesink, queue back-pressure).

### H4 — "Physical-layer (port or cable) signal integrity"

**Unrefuted and supported by elimination.** After ruling out bus
speed, IRQ affinity, compositor scheduling, power control, v4l2
config, and GStreamer template, the remaining differential between
brio-operator and brio-synths is physical port (4-3 vs 4-1) and
device serial. Either could be the cause. USB 3.0 Gen 1 links are
sensitive to cable length, connector wear, and EMI on the differential
pair. Signal retries cost framing time but may not register as kernel
drops if the USB 3.0 link layer recovers them transparently.
**Falsification test:** physically swap the brio-operator and
brio-synths cables (leave cameras, bus ports, and compositor
untouched). If the deficit follows the cable, cable. If the deficit
stays with brio-operator's USB port, port. If the deficit follows
the camera serial, firmware or sensor.

### H5 — "Device firmware variance between BRIO serials"

**Unrefuted, complementary to H4.** The three BRIOs have serials
`5342C819` (brio-operator), `9726C031` (brio-synths), `43B0576A`
(brio-room). Logitech shipped BRIOs at different times with different
firmware. Sprint-1 F4 already noted brio-synths has 2 v4l2 interfaces
with no driver bound — an anomaly suggesting its own firmware quirk.
If firmware variance is the cause, H4's swap test falsifies it by
keeping the camera in place and swapping only the cable + port — if
deficit stays with the camera, firmware.

### H6 — "jpegdec or interpipesink back-pressure specific to this producer chain"

**Unrefuted but unexplained.** Same pipeline template, same config,
same decode target. No obvious asymmetry. Testable by temporarily
swapping the jpegdec element chain on two cameras and checking
whether the deficit migrates with the decode path.

## 4. Follow-ups for alpha

Ordered by minimal invasion:

1. **Cable/port swap test** (H4 vs H5): 60 s operator-in-the-loop
   action, unambiguous result. The only test that distinguishes a
   physical-layer issue from a firmware-layer issue.
2. **v4l2-ctl streaming diagnostic** (H3): a single `v4l2-ctl
   --stream-count=300 --stream-to=/dev/null` run on brio-operator and
   brio-synths in parallel, wall-clock timed, tells us whether the
   loss is above or below v4l2src. Non-invasive, takes 15 s.
3. **`studio_camera_kernel_drops_total` is a dead metric.** The
   sequence-gap detector for MJPG streams from uvcvideo needs
   replacement or removal. If the metric is going to stay, it must
   use a signal source that actually fires on MJPG (e.g.
   `bytesused == 0` buffers, or a differential between v4l2src's
   `num-buffers` accumulator and the pad probe's counter). Right
   now, no operator can tell whether a camera is dropping frames
   at the kernel layer. This is an observability bug, not just a
   performance one.
4. **The metric's help text is also misleading.** "Frames dropped at
   the kernel/USB level (from v4l2 sequence gaps)" suggests the counter
   is authoritative, which it is not. Either fix the source or fix
   the docstring.
5. **Propose a per-source `v4l2_buffer_starvation_total` counter**
   that increments when v4l2src signals its upstream `gst_buffer_pool`
   ran dry. That is the exact signal needed for hypothesis H3 and it
   is accessible via GStreamer's `buffer-pool-used` probe without
   needing driver cooperation.

## 5. References

- `2026-04-13/livestream-performance-map/sprint-1/sprint-1-foundations.md`
  finding 3 — the initial identification of the producer-thread
  deficit
- `2026-04-14-compositor-frame-budget-forensics-errata.md` § 1.3 —
  the six-hour histogram baseline this drop builds on
- Scrape: `curl -s http://127.0.0.1:9482/metrics` at
  2026-04-14T14:45 UTC — all tables in § 2
- `/sys/bus/usb/devices/4-3/…` and `/sys/bus/usb/devices/4-1/…` —
  USB device state comparison in § 2.4
- `/proc/interrupts` — xHCI IRQ affinity map in § 2.4
- `taskset` / `chrt` / `/proc/3013869/stat` — compositor scheduling
  info in § 2.6
- `v4l2-ctl --device=... --get-fmt-video --get-parm` — advertised
  v4l2 format comparison in § 2.4
