# v4l2sink stall prevention — engineering investigation

**Date:** 2026-04-20
**Author:** alpha (research dispatch)
**Status:** research → recommended ship plan
**Trigger:** 2026-04-20 incident — `studio-compositor.service` stayed `Active: running` with `STATUS="6/6 cameras live"` for several minutes while the v4l2sink branch silently stopped pushing frames to `/dev/video42`. OBS spammed `v4l2-input: /dev/video42: select timed out` until `systemctl restart studio-compositor.service` cleared it (3-second blackout).
**Companion drops:** `2026-03-16-v4l2loopback-direct-investigation.md`,
`2026-04-14-compositor-output-stall-live-incident-root-cause.md`,
`2026-04-14-cudacompositor-consumer-chain-walk.md`,
`2026-04-20-tauri-decommission-freed-resources.md`
**Register:** scientific, neutral

---

## §1 TL;DR

**What is happening.** The compositor's systemd watchdog is gated on
"any camera producer is active" (`agents/studio_compositor/lifecycle.py:305-322`),
not on "v4l2sink actually pushed a frame." This means the producer
chain (camera → cudacompositor) can be healthy while the sink chain
(`pre_fx_tee → fx → output_tee → queue-v4l2 → v4l2sink`,
`agents/studio_compositor/pipeline.py:144-256`) is quiescent and the
service still satisfies the 60s `WatchdogSec`. The pattern matches the
2026-04-14 78-minute stall (drop #50, root cause cascading dmabuf fd
leak from rebuild thrash) and the OBS-side `select timed out`
signature first reported upstream in
[obs-studio#11295](https://github.com/obsproject/obs-studio/issues/11295)
and [obs-studio#4926](https://github.com/obsproject/obs-studio/issues/4926).

**Most likely root cause for tonight (single paragraph
justification).** The v4l2sink branch on `/dev/video42` is exposed to
two coupled risk surfaces: (a) v4l2loopback's small kernel-side ring
(`max_buffers=8` in `/etc/modprobe.d/v4l2loopback.conf`, but
`exclusive_caps=1` for `/dev/video42` makes the device single-producer
and forces format pinning at first VIDIOC_S_FMT) — when OBS holds the
device with a different read posture, format renegotiation can deadlock
silently as documented in
[v4l2loopback#97](https://github.com/umlaeute/v4l2loopback/issues/97)
and [v4l2loopback#116](https://github.com/v4l2loopback/v4l2loopback/issues/116);
and (b) the upstream NVIDIA GL chain (`cudacompositor → cudadownload →
videoconvert → tee` with the FX chain wrapped in `glupload`/`gldownload`,
`pipeline.py:126-149`) intermittently posts non-fatal QoS / GL-context
warnings under contention that propagate as silent back-pressure even
though `qos=False` is set on the v4l2sink itself
(`pipeline.py:216-219`). The 2026-04-20 EBUSY-while-OBS-held signature,
combined with the fact that restart cleared it cleanly, is most
consistent with a **format renegotiation / caps-event glitch on the
v4l2loopback side** that pinned the producer queue without surfacing
an error message — the dedup probe at `pipeline.py:233-252` defends
against repeated identical CAPS events but does not defend against
a CAPS event whose downstream allocation query stalls. v4l2loopback
0.15.3 is known to mis-negotiate buffer pool sizes when multiple
GStreamer elements are attached
([v4l2loopback#36](https://github.com/v4l2loopback/v4l2loopback/issues/36)).

**Recommended phased plan.**

| Phase | Scope | Recovery time | LOC | Ship by |
|---|---|---|---|---|
| 1 | Heartbeat probe on v4l2sink + Prometheus counter + WATCHDOG=1 gating | n/a (detect only) | ~60 LOC | tonight |
| 2 | In-process v4l2sink branch rebuild on stall detection (no service restart) | <1s | ~250 LOC | this week |
| 3 | Dual-output redundancy `/dev/video42` + `/dev/video43`, OBS scene auto-switch | 0s (OBS-side) | ~120 LOC + OBS scene config | next sprint |
| 4 | Root-cause investigation + fix at GStreamer / v4l2loopback / NVIDIA layer | n/a | depends | longest |

**Phase 1 ready-to-ship outline (target ~60 LOC, three files).** See
[§13](#§13-recommended-phased-ship-plan) for the full snippet. Summary:

1. In `pipeline.py`, after the v4l2sink is created, add a
   `Gst.PadProbeType.BUFFER` probe on the sink's static `sink` pad
   that calls a `_v4l2_frame_seen()` callback (~5 LOC).
2. In `compositor.py`, add `self._v4l2_last_frame_monotonic: float = 0.0`
   and the callback that updates it under a lock (~10 LOC).
3. In `lifecycle.py:_watchdog_tick`, replace the `any_active` camera
   gate with `(any_active and v4l2_frame_seen_within(20.0))`. Optional:
   call `sd_notify_status()` with the staleness so `systemctl status`
   shows it (~15 LOC).
4. In `metrics.py`, register a new `Gauge("studio_compositor_v4l2sink_last_frame_seconds_ago")`
   updated from the same callback path (~15 LOC).
5. In `agents/studio_compositor/__main__.py`, expose
   `sd_notify_status` already-present helper (~0 LOC, already there).

Net behavior change: when the v4l2sink stops pushing frames for >20s,
the watchdog ping stops, systemd `WatchdogSec=60s` fires, postmortem
script runs, service restarts. **3-second blackout instead of
indefinite stall** — the only visible change tonight.

---

## §2 Root cause taxonomy — ways a v4l2sink branch can stall silently

### §2.1 NVIDIA GL context loss / driver-side suspend

`cudacompositor → cudadownload → videoconvert → tee` lives on the
NVIDIA GL context. If the driver loses the context (suspend/wake,
`__NV_DISABLE_EXPLICIT_SYNC=1` interaction with the syncobj path,
or proprietary-driver bus reset), the GL-side path can emit no
error but stop producing buffers downstream of `cudadownload`. The
NVIDIA-Linux thread
[470.74 driver crash with gl elements in gstreamer pipeline](https://forums.developer.nvidia.com/t/470-74-driver-crash-when-using-gl-elements-in-gstreamer-pipeline/203029)
captures the upstream signature; the
[NVIDIA preserve-video-memory thread](https://bbs.archlinux.org/viewtopic.php?id=290126)
captures the suspend/wake variant. We are pinned at 590.48.01 per
the `feedback_nvidia_595_crash` memory; this risk surface is stable
but non-zero.

### §2.2 Format renegotiation deadlock when OBS reopens with different caps

v4l2loopback is single-pipe: producer pushes a format, consumer
reads it. When `exclusive_caps=1` (our `/dev/video42` case per
`/etc/modprobe.d/v4l2loopback.conf`), reopening the consumer with
a different format triggers a renegotiation that can deadlock.
Documented in
[v4l2loopback#97](https://github.com/umlaeute/v4l2loopback/issues/97)
("Internal data flow error / not-negotiated -4"),
[v4l2loopback#116](https://github.com/v4l2loopback/v4l2loopback/issues/116),
and
[v4l2loopback#36](https://github.com/v4l2loopback/v4l2loopback/issues/36)
("Could not negotiate format"). Our `pipeline.py:233-252` caps-dedup
probe defends against repeated identical CAPS events but does not
defend against a CAPS event whose downstream allocation query stalls.

### §2.3 v4l2loopback driver buffer exhaustion under back-pressure

Our module is loaded with `max_buffers=8` (verified in
`/etc/modprobe.d/v4l2loopback.conf`). When the consumer (OBS) is
slower than the producer, the kernel ring fills, `VIDIOC_QBUF` blocks
the producer thread. v4l2loopback documents this as the producer
"appearing to stall" with no error message. The
[v4l2loopback DeepWiki](https://deepwiki.com/v4l2loopback/v4l2loopback)
covers buffer management. Our `qos=False` on v4l2sink (`pipeline.py:216-219`)
prevents back-pressure from propagating up the pipeline, but the
v4l2sink itself can still spin on a blocked QBUF.

### §2.4 V4L2 driver `select()` timeout because producer's frame-push is blocked

This is the OBS-side symptom, not a separate cause. OBS's
`linux-v4l2/v4l2-input.c` calls `select()` on the device fd; when no
new frame arrives within the timeout, it logs `select timed out`.
The bug surfaces in [obs-studio#11295](https://github.com/obsproject/obs-studio/issues/11295)
(C920 case) and [obs-studio#4926](https://github.com/obsproject/obs-studio/issues/4926)
(negative timeout from NaN framerate). When the producer side of
v4l2loopback stops pushing, OBS spams this message at log-flood rate.
Our 2026-04-20 incident matches this exact signature.

### §2.5 Internal queue stall (preceding `queue` element backed up)

`queue-v4l2` is configured with `leaky=2` (downstream — drop oldest)
and `max-size-buffers=5` (`pipeline.py:163-175`). Under normal
back-pressure this queue drops frames at the boundary instead of
stalling upstream. However, if the *downstream* element (`v4l2sink`)
is fully blocked on QBUF, the queue's leaky behavior cannot help —
buffers cannot be popped at all. The
[GStreamer queue documentation](https://gstreamer.freedesktop.org/documentation/coreelements/queue.html)
notes that leaky mode drops new or old buffers when the queue fills,
but if the sink's chain function is blocked, the queue's source pad
push is what blocks.

### §2.6 `glcolorconvert` or `gldownload` element entering paused state without notifying the bus

`gldownload` runs on the GL thread. If the GL command pipeline stalls
(driver-internal sync wait, suspended client buffer, NVIDIA sync-fd
issue), the element produces no buffers downstream and posts no bus
message. The `pipeline.py:126-128` cudadownload + videoconvert chain
sits on this risk surface every frame. The
[470.74 thread](https://forums.developer.nvidia.com/t/470-74-driver-crash-when-using-gl-elements-in-gstreamer-pipeline/203029)
and the
[Servo GL-context issue #27013](https://github.com/servo/servo/issues/27013)
both report silent stall variants.

### §2.7 Multi-thread issue: GLib main loop vs render thread

The compositor uses one GLib main loop for the bus + watchdog tick
(`lifecycle.py:322`) and GStreamer's internal streaming threads for
each pipeline branch. If the GLib main loop blocks (e.g. a Cairo
source render holding the GIL too long during a hotpath, or a sync
file write inside `_status_tick` at `compositor.py:797-815`), the
watchdog tick can be delayed but the *streaming threads* keep running.
Conversely, if a streaming thread blocks, GLib keeps ticking and the
watchdog continues to ping — this is the failure mode that allowed
the 78-minute stall on 2026-04-14.

### §2.8 dmabuf fd leak / file descriptor exhaustion

Documented in
[`docs/research/2026-04-14-compositor-output-stall-live-incident-root-cause.md`](2026-04-14-compositor-output-stall-live-incident-root-cause.md).
The cascading dmabuf fd leak from camera producer rebuild thrash
exhausted file descriptors on the cudadownload path; downstream
elements stalled silently while the per-camera producer snapshots
stayed fresh. This is the primary historical example of "watchdog
gates on cameras, sink branch dead" failure.

---

## §3 Reproduction conditions

Each of these can be deliberately triggered to surface stall
vulnerability before going live (see also §10):

1. **Restart OBS while compositor is pushing.** OBS releases the
   reader fd, then reopens; the producer must survive without
   renegotiation.
2. **Open OBS V4L2 source with format different from compositor's
   NV12/720p30** (e.g. select YUYV in OBS source properties). With
   `exclusive_caps=1`, this forces a full caps renegotiation cycle.
3. **Sleep+wake cycle on the workstation** (NVIDIA suspend path).
   Most fragile — driver state changes, GL contexts may need rebind.
4. **Trigger NVIDIA driver state change** by toggling
   `CUDA_VISIBLE_DEVICES` on a sibling process or `nvidia-smi
   --gpu-reset` (cannot do during stream — too destructive).
5. **Disconnect/reconnect a camera** (USB bus event). Already handled
   by the camera 24/7 epic, but the udev event briefly reorders bus
   enumeration; the v4l2 setup script (`systemd/units/studio-camera-setup.sh`)
   re-runs.
6. **High GPU load spike** (encoder oversubscription). Run another
   workload on the 3090 (e.g. inference batch in TabbyAPI) to push
   GPU >95% for a few seconds; v4l2sink's GL-fed branch may stall.
7. **Hold the device with ffprobe**: `ffprobe -f v4l2 /dev/video42`
   while OBS also has it open. Triggers EBUSY paths similar to
   tonight's incident.
8. **Run a second producer** against the device (compositor + a stray
   `gst-launch v4l2sink` instance). With `exclusive_caps=1`, the
   second open fails — but a partial failure mid-negotiation can
   leave the device in a bad state, per
   [v4l2loopback#442](https://github.com/v4l2loopback/v4l2loopback/issues/442).

---

## §4 v4l2loopback module options — preventive configuration

Source: [v4l2loopback README](https://github.com/v4l2loopback/v4l2loopback/blob/main/README.md),
[v4l2loopback DeepWiki](https://deepwiki.com/v4l2loopback/v4l2loopback),
[v4l2loopback-ctl manpage](https://manpages.org/v4l2loopback-ctl).

Current state (`/etc/modprobe.d/v4l2loopback.conf`):

```
options v4l2loopback devices=5 video_nr=10,42,50,51,52
  card_label="OBS_Virtual_Camera,StudioCompositor,YouTube0,YouTube1,YouTube2"
  exclusive_caps=1,1,0,0,0 max_buffers=8
```

| Parameter | Default | Current | Recommendation | Source |
|---|---|---|---|---|
| `devices` | 1 | 5 | keep | README |
| `video_nr` | auto | 10,42,50,51,52 | keep | README |
| `card_label` | "v4l2loopback" | per-device | keep | README |
| `exclusive_caps` | 0 | 1 (for /dev/video42) | **review for /dev/video42 — see below** | README; [issue #442](https://github.com/v4l2loopback/v4l2loopback/issues/442) |
| `max_buffers` | 2 | 8 | keep | README |
| `max_openers` | 10 | unset | consider explicit `max_openers=2` for /dev/video42 | DeepWiki |
| `announce_all_caps` | 1 | unset | leave at default (compositor pins NV12 via capsfilter) | source `v4l2loopback.c` |

**`exclusive_caps=1` analysis.** The
[issue #442 thread](https://github.com/v4l2loopback/v4l2loopback/issues/442)
documents that with `exclusive_caps=1`, OBS can do *one* invocation of
"Start Virtual Camera"; subsequent invocations fail until the module
is reloaded. Because OBS is the *consumer* of /dev/video42 (not the
producer in our case), this risk is asymmetric — but the same single-
producer pinning that enables the failure mode applies to format
renegotiation.

**Sysfs-tunable controls** (not modprobe options — set per-device via
`v4l2-ctl -d /dev/video42 -c ...`):

| Control | Default | Recommendation | Notes |
|---|---|---|---|
| `keep_format` | 0 | **set to 1** after compositor's first VIDIOC_S_FMT succeeds | Pins the negotiated format permanently — defends against the §2.2 renegotiation deadlock. README. |
| `sustain_framerate` | 0 | consider 1 | Producer-side frame duplication when producer stalls — papers over short stalls but masks our heartbeat signal. **Tradeoff: defeats §7 detection.** Do not enable. |
| `timeout` | 0 (disabled) | **set to 2000 ms** with a custom timeout image | After 2s with no producer frames, v4l2loopback emits a timeout image (e.g. "DEGRADED — RECOVERING"). OBS sees frames, blackout becomes a slate. README + `v4l2loopback-ctl set-timeout-image`. |
| `timeout_image_io` | 0 | leave default | next-opener writes timeout frames; we do not need this |

The
[Arch wiki v4l2loopback page](https://wiki.archlinux.org/title/V4l2loopback)
and
[Gentoo wiki](https://wiki.gentoo.org/wiki/V4l2loopback) cover the
modprobe and sysfs surfaces.

---

## §5 GStreamer pipeline hardening

Current v4l2sink branch (`pipeline.py:163-227`):

```
output_tee → queue-v4l2 (leaky=2, max-size-buffers=5)
           → videoconvert → capsfilter (NV12/720/30)
           → identity (drop-allocation=true)
           → v4l2sink (sync=false, qos=false, enable-last-sample=false)
```

Already-applied hardening (good):
- `queue leaky=downstream` per
  [GStreamer queue docs](https://gstreamer.freedesktop.org/documentation/coreelements/queue.html);
  drops oldest under back-pressure rather than blocking upstream.
- `identity drop-allocation=true` — standard v4l2loopback workaround for
  allocation query renegotiation, per
  [v4l2loopback wiki GStreamer page](https://github.com/v4l2loopback/v4l2loopback/wiki/Gstreamer).
- `sync=false` — don't wait on clock for the v4l2 boundary.
- `qos=false` (`pipeline.py:216-219`) — defends against §2.5 back-pressure
  propagation.
- `enable-last-sample=false` — defends against the dead-pinning of the
  most recent BGRA buffer (~4 MB per frame indefinitely).
- Caps dedup probe (`pipeline.py:233-252`) — drops repeated identical
  CAPS events to prevent renegotiation loops.

Recommended additional hardening:

1. **Add `videorate` before the v4l2sink capsfilter.** Forces strict
   30 fps regardless of upstream jitter — `videorate ! video/x-raw,
   framerate=30/1`. Source-side jitter has been observed when
   `cudacompositor latency=33000000` (`pipeline.py:69-72`) interacts
   with a slow camera pad. Adds a frame of latency but makes the
   producer-side cadence deterministic.
2. **Add `max-size-time=200000000` (200 ms) to `queue-v4l2`.**
   Currently only `max-size-buffers=5` is set; under a frame-rate
   spike the buffer count can fill before the time bound. Defense in
   depth.
3. **Add the GStreamer `watchdog` element from gst-plugins-bad
   immediately upstream of v4l2sink** with `timeout=3000` (3s). Per
   [gst-plugins-bad/watchdog docs](https://gstreamer.freedesktop.org/documentation/debugutilsbad/watchdog.html),
   the element posts an `ERROR` bus message when no buffer crosses
   it within the timeout. Our `compositor.py:680-745` bus handler
   already filters errors by `src_name`; add a branch for
   `src_name == "v4l2-watchdog"` that triggers Phase 2 in-process
   rebuild instead of `self.stop()`.
4. **Capture WARNING messages from v4l2sink** (`compositor.py:746-748`
   already logs them generically; add structured handling). Specifically
   filter for "Internal data flow error" and "not-negotiated" patterns
   per [v4l2loopback#97](https://github.com/umlaeute/v4l2loopback/issues/97).
5. **Pin the v4l2sink's `device-fd` lifecycle.** Currently we let
   v4l2sink open and close the fd; if v4l2loopback gets into a bad
   state, reopening can fail. Consider opening the device manually
   in Python and passing the fd via `device-fd` property — gives us
   a single owner that survives v4l2sink rebuild.

References:
- [GStreamer queue tutorial / leaky modes](https://walterfan.github.io/gstreamer-cookbook/4.plugin/queue.html)
- [Discourse: control queue size before dropping frames](https://discourse.gstreamer.org/t/control-queue-size-before-dropping-frames/190)
- [v4l2sink reference](https://gstreamer.freedesktop.org/documentation/video4linux2/v4l2sink.html)

---

## §6 GStreamer bus message monitoring for stall detection

The bus is already wired (`compositor.py:680-753`). Add structured
handlers for stall-relevant message types:

### §6.1 GST_MESSAGE_QOS

Per
[GStreamer QoS design doc](https://gstreamer.freedesktop.org/documentation/additional/design/qos.html),
QoS messages are posted whenever a sink drops a buffer for QoS reasons
or changes processing strategy. Even with `qos=False` on v4l2sink, the
upstream chain can post QoS. Listen for it:

```python
elif t == Gst.MessageType.QOS:
    fmt, processed, dropped = message.parse_qos_stats()
    src_name = message.src.get_name() if message.src else "unknown"
    if dropped > 0:
        try:
            from . import metrics
            metrics.QOS_DROPS_TOTAL.labels(element=src_name).inc(dropped)
        except Exception:
            pass
```

### §6.2 GST_MESSAGE_WARNING from v4l2sink

Already partially handled at `compositor.py:746-748`. Add structured
filtering for the v4l2loopback signatures:

- `"not-negotiated"` → Phase 2 trigger (caps stuck)
- `"No free buffer found in the pool"` → buffer exhaustion (per
  [v4l2loopback#36](https://github.com/v4l2loopback/v4l2loopback/issues/36))
- `"Internal data flow error"` → producer pipeline issue
- `"Device or resource busy"` → consumer holding the fd

### §6.3 Buffer-counting probe (the Phase 1 ship)

Per [GStreamer GstPad docs](https://gstreamer.freedesktop.org/documentation/gstreamer/gstpad.html)
and the [Probes design doc](https://gstreamer.freedesktop.org/documentation/additional/design/probes.html),
attach a `Gst.PadProbeType.BUFFER` probe to the v4l2sink's `sink`
static pad; the callback fires for every buffer that crosses. Increment
a monotonic counter, write a heartbeat file, expose a Prometheus gauge.
See [§7](#§7-heartbeat-instrumentation-patterns) for the implementation
pattern.

### §6.4 GstClock-based detection

Per
[Clocks and synchronization docs](https://gstreamer.freedesktop.org/documentation/application-development/advanced/clocks.html):
GstClock reports a monotonic absolute time. Compare the v4l2sink's
internal clock-tick time against the wall-clock time from the buffer
probe — if the sink's clock advances but no buffers cross, the sink
is alive but starved upstream. Less precise than the buffer probe;
not needed for Phase 1.

References:
- [GstMessage reference](https://gstreamer.freedesktop.org/documentation/gstreamer/gstmessage.html)
- [Pipeline manipulation / probes](https://gstreamer.freedesktop.org/documentation/application-development/advanced/pipeline-manipulation.html)
- [Probes handling in GStreamer pipelines (Medium)](https://erit-lvx.medium.com/probes-handling-in-gstreamer-pipelines-3f96ea367f31)

---

## §7 Heartbeat instrumentation patterns

The Phase 1 ship. Goal: detect within 2-3s when the v4l2sink stops
pushing frames, regardless of where upstream the stall is.

### §7.1 Per-frame callback via GstPad probe

Attach to `v4l2sink.get_static_pad("sink")` with
`Gst.PadProbeType.BUFFER`:

```python
# pipeline.py — after sink is created at line 197
def _v4l2_buffer_probe(pad, info):
    compositor._on_v4l2_frame_pushed()
    return Gst.PadProbeReturn.OK

sink.get_static_pad("sink").add_probe(
    Gst.PadProbeType.BUFFER, _v4l2_buffer_probe
)
```

The probe callback runs on the streaming thread; keep it O(1) — just
an atomic counter increment and timestamp store.

### §7.2 Compositor-side counter

```python
# compositor.py — in __init__
self._v4l2_frame_count = 0
self._v4l2_last_frame_monotonic = 0.0
self._v4l2_lock = threading.Lock()

def _on_v4l2_frame_pushed(self) -> None:
    """Called from v4l2sink BUFFER probe. Streaming-thread hot path."""
    now = time.monotonic()
    with self._v4l2_lock:
        self._v4l2_frame_count += 1
        self._v4l2_last_frame_monotonic = now

def v4l2_frame_seen_within(self, seconds: float) -> bool:
    """Read-side check for the watchdog."""
    with self._v4l2_lock:
        if self._v4l2_last_frame_monotonic == 0.0:
            return False  # never seen a frame yet
        return (time.monotonic() - self._v4l2_last_frame_monotonic) < seconds
```

### §7.3 Heartbeat file (optional, for external watchers)

A 1Hz GLib timer writes the monotonic timestamp to
`/dev/shm/hapax-compositor/v4l2-heartbeat`:

```python
def _v4l2_heartbeat_tick() -> bool:
    if not compositor._running:
        return False
    try:
        ts = compositor._v4l2_last_frame_monotonic
        Path("/dev/shm/hapax-compositor/v4l2-heartbeat").write_text(f"{ts:.3f}\n")
    except OSError:
        pass
    return True

GLib.timeout_add(1000, _v4l2_heartbeat_tick)
```

This enables a separate watchdog process (Phase 3) without coupling
to the compositor's address space.

### §7.4 Latency-to-detect

- Probe callback latency: O(microseconds), runs on the streaming
  thread.
- Watchdog tick interval: 20s currently (`lifecycle.py:322`). With a
  5s window check, we detect stall within 25s worst-case.
- For Phase 2 (in-process rebuild), reduce watchdog tick to 2s and
  detection window to 3s — sub-5s detection, sub-1s recovery.

### §7.5 Where to put the probe (sink-side, not source-side)

**Always on the v4l2sink's `sink` pad**, not the queue-v4l2 sink pad
or the tee src pad. The sink pad is the last point inside our pipeline
before the kernel; if the kernel's QBUF blocks, the chain function
returns from upstream's perspective but the buffer never actually
landed. Buffer-probe count = "GStreamer pushed it to the sink"; this
is the closest userspace can get to "v4l2loopback received a frame"
without polling the kernel.

References:
- [GstPad / probes](https://gstreamer.freedesktop.org/documentation/gstreamer/gstpad.html)
- [Probes design doc](https://gstreamer.freedesktop.org/documentation/additional/design/probes.html)
- [GstBuffer reference](https://gstreamer.freedesktop.org/documentation/gstreamer/gstbuffer.html)

---

## §8 systemd watchdog integration

Current state: `Type=notify` + `WatchdogSec=60s` in
`systemd/units/studio-compositor.service:14-19`. Watchdog ping at
20s interval (`lifecycle.py:305-322`), gated on
`any(s == "active" for s in compositor._camera_status.values())`.

**The bug.** The gate is "any camera producer is active," not "the
output sink received a frame." Per the camera 24/7 epic design
(`docs/superpowers/plans/2026-04-12-camera-247-resilience-epic.md` § 1.6),
this was deliberate — the per-camera GStreamer watchdog already
covers producer stalls. But the gate has a coverage gap: anything
between cudacompositor and v4l2sink is invisible to it. The 2026-04-14
78-minute stall and tonight's incident both exploit this gap.

**The fix (Phase 1).** Conjoin the existing camera-active gate with
v4l2-frame-seen-within(20s):

```python
# lifecycle.py — replace _watchdog_tick body
def _watchdog_tick() -> bool:
    with compositor._camera_status_lock:
        any_active = any(s == "active" for s in compositor._camera_status.values())
    v4l2_alive = compositor.v4l2_frame_seen_within(20.0)
    if any_active and v4l2_alive and compositor._running:
        sd_notify_watchdog()
        try:
            from . import metrics
            metrics.mark_watchdog_fed()
        except Exception:
            pass
    elif any_active and not v4l2_alive:
        sd_notify_status(f"DEGRADED — v4l2sink silent for >20s")
    return compositor._running
```

When v4l2sink stops pushing for >20s, the watchdog ping stops; at the
60s `WatchdogSec` boundary, systemd kills the unit (SIGABRT), the
postmortem hook captures state, the unit restarts. **3-second
blackout instead of indefinite stall.**

References:
- [systemd sd_notify(3) manpage](https://www.freedesktop.org/software/systemd/man/latest/sd_notify.html)
- [Using watchdog and sd-notify functionality for systemd in Python 3 (stigok blog)](https://blog.stigok.com/2020/01/26/sd-notify-systemd-watchdog-python-3.html)
- [Basic Systemd sd_notify + watchdog usage gist](https://gist.github.com/hacst/ee12cd91167aa55b19444fc74c91a8e8)
- [bb4242/sdnotify — pure-Python sd_notify](https://github.com/bb4242/sdnotify) (the `sdnotify` package we already use)
- [systemd-watchdog package on PyPI](https://pypi.org/project/systemd-watchdog/) (alternative implementation)

---

## §9 Auto-recovery patterns — minimize blackout

### §9.1 Service restart (current — Phase 1 ceiling)

Triggered by the `WatchdogSec=60s` timeout once the Phase 1 heartbeat
gate is in place. Blackout: **3 seconds**, dominated by:
- 60s wait for SIGABRT (because the watchdog detection requires the
  ping to *stop*, not signal failure)
- 2-3s for postmortem hook + camera setup + GStreamer init

To shrink the 60s wait: reduce `WatchdogSec` to 30s, raise the
heartbeat tick to 5s, with detection window 10s. Trade-off: false
positives during legitimate brief stalls (e.g. caps re-negotiation
during snapshot tee adjustment).

### §9.2 In-process v4l2sink branch rebuild (Phase 2 — sub-1s blackout)

Pattern from
[MaZderMind dynamic-gstreamer-pipelines-cookbook](https://github.com/MaZderMind/dynamic-gstreamer-pipelines-cookbook):

1. Stall detected (v4l2_frame_seen_within(3.0) returns False).
2. Block the `output_tee`'s src pad feeding `queue-v4l2` with
   `Gst.PadProbeType.BLOCK` probe.
3. In the block callback (runs on the streaming thread):
   - Set the v4l2 branch elements to `Gst.State.NULL`
   - Remove them from the pipeline
   - Release the tee's request pad
   - Build a fresh v4l2 branch (queue → videoconvert → capsfilter →
     identity → v4l2sink)
   - Add to pipeline, `sync_state_with_parent()`
   - Request a new tee pad, link
4. Return `Gst.PadProbeReturn.REMOVE` to unblock.

Cameras + cudacompositor + fx chain stay alive throughout. Blackout
is bounded by element teardown + setup time + the v4l2loopback
device's first VIDIOC_S_FMT — typically <500 ms. OBS may briefly
log `select timed out` but recovers when frames resume.

References:
- [GStreamer Dynamic Pipelines (slomo's blog)](https://coaxion.net/blog/2014/01/gstreamer-dynamic-pipelines/)
- [Dynamically adding and removing branches of a tee (gst-devel mailing list)](https://gstreamer-devel.narkive.com/vbgoUaBv/gst-devel-dynamically-adding-and-removing-branches-of-a-tee)
- [Pipeline manipulation chapter](https://gstreamer.freedesktop.org/documentation/application-development/advanced/pipeline-manipulation.html)
- [Basic tutorial 7: multithreading and pad availability](https://gstreamer.freedesktop.org/documentation/tutorials/basic/multithreading-and-pad-availability.html)

### §9.3 Dual-output redundancy (Phase 3 — 0s blackout)

Compositor writes to **both** `/dev/video42` and `/dev/video43`
simultaneously. OBS has both as separate scenes; an Advanced Scene
Switcher
([OBS Advanced Scene Switcher resource](https://obsproject.com/forum/resources/advanced-scene-switcher.395/))
macro auto-switches when V4L2-A returns no frames for >2s.

Pipeline change in `pipeline.py`:
- Add `/dev/video43` to `/etc/modprobe.d/v4l2loopback.conf` (devices=6,
  video_nr adds 43, exclusive_caps adds another 1).
- Build a second v4l2sink branch off `output_tee` identical to the
  first but with `device=/dev/video43`.
- Each branch carries an independent watchdog probe; either branch
  can stall without taking the other down.

Cost: 2× v4l2sink CPU work (small — videoconvert + memcpy), 2×
v4l2loopback kernel ring memory. Win: zero viewer-visible blackout
because OBS already has the fallback as a hot scene.

### §9.4 Last-frame-replay (Phase 3 alternative)

A separate process subscribes to the v4l2 heartbeat file (§7.3); when
staleness >1s, it pushes the last good frame from
`/dev/shm/hapax-compositor/snapshot.jpg` (the existing snapshot
appsink, `snapshots.py:40-63`) into a *secondary* v4l2loopback device
(`/dev/video43`). OBS sees frames continuously even during compositor
restart.

Lighter than §9.3 (no double-encode) but introduces a fallback-render
process that must itself be watchdog-monitored. Recommendation: ship
§9.3 first; §9.4 if §9.3's CPU cost proves problematic.

### §9.5 v4l2loopback timeout image (no-process fallback)

Per §4, setting `v4l2-ctl -d /dev/video42 -c timeout=2000` makes
v4l2loopback emit a "DEGRADED" slate after 2s of producer silence. No
extra process needed; viewer sees the slate during compositor restart
instead of a blackout. Stack with §9.3 for belt-and-suspenders.

---

## §10 Pre-stream sanity protocol

Concrete operator checklist before going live. Run after the §13
Phase 1 ship.

### §10.1 60-second pre-stream watch

```bash
# Watch the v4l2sink heartbeat counter
watch -n 1 'cat /dev/shm/hapax-compositor/v4l2-heartbeat'
# Should advance by ~1.0 every second (monotonic timestamp).
# If it stops advancing for >3s, abort go-live.
```

### §10.2 Smoke-test routine

Deliberately stress the pipeline before going live:

1. **OBS reload.** Close + reopen OBS. Check heartbeat keeps advancing.
2. **OBS source toggle.** Disable + re-enable the V4L2 source in
   OBS's source list. Should not stall the producer.
3. **OBS source format change.** Change OBS's V4L2 source format to
   YUYV, then back to NV12. Tests §2.2 renegotiation handling.
4. **GPU pressure.** Run `nvidia-smi --loop=1` in a terminal alongside
   `glmark2` for 30s. Heartbeat should stay alive.
5. **EBUSY simulation.** `ffprobe -f v4l2 /dev/video42` while OBS has
   it open. Confirm OBS's `select timed out` does not trigger compositor
   stall.
6. **Camera disconnect/reconnect.** Unplug + replug one camera. Per
   the camera 24/7 epic, the compositor handles this — confirm the
   v4l2sink heartbeat does not pause during the swap.

### §10.3 Operator checklist

```
[ ] systemctl --user is-active studio-compositor.service
[ ] journalctl --user -u studio-compositor.service -n 50 (no errors)
[ ] curl -s 127.0.0.1:9482/metrics | grep v4l2sink_last_frame_seconds_ago
    (value <2.0)
[ ] cat /dev/shm/hapax-compositor/status.json | jq '.cameras'
    (all "active")
[ ] mpv v4l2:///dev/video42 --no-cache (visual confirm — frames flowing)
[ ] OBS V4L2 source preview shows the composite
[ ] OBS auto-reset on timeout enabled (see §11)
[ ] OBS fallback scene configured (Phase 3)
[ ] v4l2loopback timeout image installed (§4 + §9.5)
[ ] Pre-stream smoke routine §10.2 passed
```

---

## §11 OBS-side mitigations

These are operator-side settings that reduce blast radius when the
compositor does stall.

### §11.1 Auto-reset on timeout (in-tree feature)

OBS Studio's linux-v4l2 plugin includes an auto-reset feature added
in [PR #4005](https://github.com/obsproject/obs-studio/pull/4005). When
`select()` times out for longer than the configured frame-time threshold
(2-120 frames), the source is disabled and re-enabled — effectively a
soft reset. **Enable this.** Setting: source properties → "Auto-reset
on timeout" + "Frame timeout (frames)" set to ~10 (≈333 ms at 30 fps).

Default is off because it can cause issues with chronically-slow
devices; v4l2loopback is not chronically slow, so the trade-off is
favorable for us.

### §11.2 Use Buffering

OBS V4L2 source has a "Use Buffering" toggle. Enabled, OBS holds a
small frame buffer; brief sub-100 ms producer stalls are masked.
Slightly increases viewer-side latency. **Enable for /dev/video42.**

### §11.3 Auto-fallback scene via Advanced Scene Switcher

[OBS Advanced Scene Switcher](https://obsproject.com/forum/resources/advanced-scene-switcher.395/)
plugin supports macro conditions on source health. Configure:
- Macro: "When V4L2 /dev/video42 source has no frames for 2s, switch
  to scene 'Compositor Recovery'".
- 'Compositor Recovery' scene = static slate or pre-recorded loop.
- Reverse macro: when frames return, switch back.

Pairs naturally with Phase 3 dual-output (§9.3): the fallback scene
can be the /dev/video43 V4L2 source.

### §11.4 OBS-side logging discipline

When compositor recovers but OBS log is full of `select timed out`
spam, OBS's per-source log buffer can rotate too fast to be useful.
Mitigation: edit OBS log level for `linux-v4l2` to suppress repeated
`select timed out` lines. Less important now that we are detecting
producer-side; mostly cosmetic.

References:
- [OBS V4L2 source plugin source code](https://github.com/obsproject/obs-studio/blob/master/plugins/linux-v4l2/v4l2-input.c)
- [OBS V4L2 plugin auto-reset PR #4005](https://github.com/obsproject/obs-studio/pull/4005)
- [Selective stream restart commit (8814e2b)](https://github.com/obsproject/obs-studio/commit/8814e2bf4c77e2aae87d23ae0123119be69e3833)
- [obs-studio#11295 (C920 select-timed-out)](https://github.com/obsproject/obs-studio/issues/11295)
- [obs-studio#4926 (negative timeout / NaN framerate)](https://github.com/obsproject/obs-studio/issues/4926)

---

## §12 NVIDIA-specific known issues

### §12.1 GL elements + NVIDIA proprietary driver

[NVIDIA forum: 470.74 driver crash with gl elements in gstreamer pipeline](https://forums.developer.nvidia.com/t/470-74-driver-crash-when-using-gl-elements-in-gstreamer-pipeline/203029)
documents the upstream signature. We are pinned at 590.48.01, but
the failure mode generalizes — `glupload`/`gldownload`/`glcolorconvert`
intermittently crash or hang under load. Our `pipeline.py:126-149`
chain sits on this surface every frame.

### §12.2 Wayland + NVIDIA + GL context

The `__NV_DISABLE_EXPLICIT_SYNC=1` workaround
(`docs/issues/tauri-wayland-protocol-error.md`) is active on this
system. It patches around webkit2gtk's syncobj bug but also affects
GL fence behavior generally. No documented direct interaction with
GStreamer's GL chain, but worth noting as a state-change risk surface.

### §12.3 GPU-fallen-off-the-bus

[Arch BBS thread: Nvidia GPU has fallen off the bus](https://bbs.archlinux.org/viewtopic.php?id=304020)
is the worst-case variant — driver lost the device, cannot recover
without reboot. Detectable via `nvidia-smi -q | grep -i "GPU is lost"`.
Our compositor cannot recover from this; it would need to escalate
out-of-band (ntfy alert, manual operator intervention). The
postmortem hook at `studio-compositor.service:54` already captures
`nvidia-smi` output.

### §12.4 Suspend/wake

Per [Arch BBS PreserveVideoMemoryAllocation](https://bbs.archlinux.org/viewtopic.php?id=290126),
NVIDIA suspend/wake without `NVreg_PreserveVideoMemoryAllocations=1`
loses GL context state. Our workstation is configured to never
suspend during streams (manual operator gate). Phase 4 work item:
verify the systemd suspend-inhibit is active when the compositor is
running.

### §12.5 Encoder oversubscription

NVENC has finite session slots (RTX 3090: ~3 concurrent sessions
per process pre-NV-driver-550, unlocked since). Our compositor uses
one NVENC session for the RTMP egress branch (`rtmp_output.py`).
TabbyAPI can also touch NVENC under some configurations. If a
sibling process opens an NVENC session and all slots are taken, the
compositor's nvh264enc emits an error and the RTMP branch dies — but
the v4l2sink branch continues. Verified this is not the 2026-04-20
failure mode.

References:
- [NVIDIA PreserveVideoMemoryAllocation suspend fix gist](https://gist.github.com/bmcbm/375f14eaa17f88756b4bdbbebbcfd029)
- [NVIDIA GPU is lost ramdomly thread](https://forums.developer.nvidia.com/t/gpu-is-lost-ramdomly-and-nvidia-smi-asks-for-a-reboot-to-recover-it/109240)
- [GStreamer pipeline hangs after hours (Jetson Xavier NX, generalizable)](https://forums.developer.nvidia.com/t/gstreamer-pipeline-hangs-after-hours-due-to-errors/174219)
- [Servo GStreamer GL context issue #27013](https://github.com/servo/servo/issues/27013)
- [GStreamer freedesktop OpenGL design doc](https://gstreamer.freedesktop.org/documentation/additional/design/opengl.html)

---

## §13 Recommended phased ship plan

### §13.1 Phase 1 (today, ~60 LOC) — heartbeat + watchdog gate

**Files:**
1. `agents/studio_compositor/pipeline.py` (+10 LOC)
2. `agents/studio_compositor/compositor.py` (+25 LOC)
3. `agents/studio_compositor/lifecycle.py` (+15 LOC)
4. `agents/studio_compositor/metrics.py` (+10 LOC)

**`pipeline.py` patch (insert after line 219, before
`for el in [queue_v4l2, ...]`):**

```python
# v4l2sink frame-push heartbeat probe (Phase 1 stall detection).
# Increments compositor._v4l2_frame_count and updates
# _v4l2_last_frame_monotonic on every buffer that crosses the sink
# pad. The watchdog tick conjoins v4l2_frame_seen_within(20.0) with
# the existing camera-active gate, so the systemd WatchdogSec=60s
# fires when the v4l2sink branch stalls — even if cameras are still
# live. Ref: docs/research/2026-04-20-v4l2sink-stall-prevention.md §7-§8.
def _v4l2_buffer_probe(pad, info):
    compositor._on_v4l2_frame_pushed()
    return Gst.PadProbeReturn.OK

sink.get_static_pad("sink").add_probe(
    Gst.PadProbeType.BUFFER, _v4l2_buffer_probe
)
```

**`compositor.py` patch (in `__init__`, alongside the camera_status
setup at line 501):**

```python
# v4l2sink heartbeat (Phase 1). Updated by pipeline.py's BUFFER probe
# on the v4l2sink's static sink pad — fires on every frame pushed.
self._v4l2_frame_count: int = 0
self._v4l2_last_frame_monotonic: float = 0.0
self._v4l2_lock = threading.Lock()
```

Add two methods anywhere convenient (e.g. near `_write_status`):

```python
def _on_v4l2_frame_pushed(self) -> None:
    """Called from the v4l2sink BUFFER probe. Streaming-thread hot path."""
    now = time.monotonic()
    with self._v4l2_lock:
        self._v4l2_frame_count += 1
        self._v4l2_last_frame_monotonic = now

def v4l2_frame_seen_within(self, seconds: float) -> bool:
    """True if v4l2sink pushed a frame within the last `seconds`."""
    with self._v4l2_lock:
        if self._v4l2_last_frame_monotonic == 0.0:
            return False
        return (time.monotonic() - self._v4l2_last_frame_monotonic) < seconds
```

**`lifecycle.py` patch (replace lines 305-322):**

```python
def _watchdog_tick() -> bool:
    # Conjoin camera-active and v4l2sink-frame-seen gates. Either
    # silent for >20s and the watchdog ping stops; systemd
    # WatchdogSec=60s then SIGABRTs the unit. Ref:
    # docs/research/2026-04-20-v4l2sink-stall-prevention.md §8.
    with compositor._camera_status_lock:
        any_active = any(s == "active" for s in compositor._camera_status.values())
    v4l2_alive = compositor.v4l2_frame_seen_within(20.0)
    if any_active and v4l2_alive and compositor._running:
        sd_notify_watchdog()
        try:
            from . import metrics
            metrics.mark_watchdog_fed()
            metrics.V4L2SINK_LAST_FRAME_AGE.set(
                time.monotonic() - compositor._v4l2_last_frame_monotonic
                if compositor._v4l2_last_frame_monotonic > 0 else 9999.0
            )
        except Exception:
            pass
    elif any_active and not v4l2_alive:
        sd_notify_status("DEGRADED — v4l2sink silent for >20s")
        log.warning("v4l2sink stall detected — withholding watchdog ping")
    return compositor._running
```

**`metrics.py` patch (add to the metrics block near
`COMP_WATCHDOG_LAST_FED`):**

```python
V4L2SINK_LAST_FRAME_AGE = Gauge(
    "studio_compositor_v4l2sink_last_frame_seconds_ago",
    "Seconds since the v4l2sink BUFFER probe last fired",
    registry=REGISTRY,
)
V4L2SINK_FRAMES_TOTAL = Counter(
    "studio_compositor_v4l2sink_frames_total",
    "Cumulative buffers crossing the v4l2sink sink pad",
    registry=REGISTRY,
)
```

**Net LOC: ~60.** Net behavior: v4l2sink stall detected within 25s,
recovered via service restart in ~3s, postmortem captured.

### §13.2 Phase 2 (this week, ~250 LOC) — in-process branch rebuild

Goal: sub-1s blackout instead of 3s.

**New module:** `agents/studio_compositor/v4l2_branch_recovery.py`
(~180 LOC). Implements pad-block-driven hot-swap of the v4l2 branch
elements per [§9.2](#§92-in-process-v4l2sink-branch-rebuild-phase-2--sub-1s-blackout).

**`compositor.py` integration** (~40 LOC): add a recovery thread
that polls `v4l2_frame_seen_within(3.0)`; on stall, calls the recovery
module's `rebuild_branch(pipeline, output_tee)`. Bounded by max-3
attempts before falling through to the systemd-watchdog path.

**`lifecycle.py` integration** (~10 LOC): start the recovery thread
in the same place the watchdog tick is registered.

**`metrics.py`** (~20 LOC): counters for rebuild attempts, success,
failure, time-to-recover.

### §13.3 Phase 3 (next sprint, ~120 LOC + OBS scene config)

Dual-output redundancy + OBS auto-fallback per §9.3. v4l2loopback
config update + a second v4l2sink branch in `pipeline.py`. OBS
Advanced Scene Switcher macro authored manually by operator.

### §13.4 Phase 4 (longest) — root cause investigation

Empirical reproduction harness for §3 conditions. Targets:
- Format renegotiation deadlock — file v4l2loopback issue with
  reproduction steps if not already covered.
- NVIDIA GL stall under contention — file gst-rs / gstreamer issue
  if reproducible without driver upgrade.
- Driver upgrade re-validation — once 590.48.01 → 595.x is feasible
  (gated on Dwarf Fortress re-validation per `feedback_nvidia_595_crash`),
  re-test the GL chain stall surface.

---

## §14 Open questions

1. **Is the `keep_format=1` v4l2-ctl setting compatible with our
   compositor restart cycle?** The setting persists per-device until
   the module is unloaded. After a compositor restart with
   `keep_format=1` set, the new compositor process re-issues
   `VIDIOC_S_FMT` with the same params — should be a no-op, but
   needs empirical verification.
2. **Does `qos=False` on v4l2sink fully prevent QoS message
   propagation, or do upstream elements still post QoS based on
   their own clock observations?** Need to scrape the bus for
   `GST_MESSAGE_QOS` over a 24h run to confirm.
3. **What is the actual blackout time of a Phase 2 in-process
   rebuild on a quiescent stream vs. one with active OBS read?**
   Need to measure with `time` instrumentation around the
   pad-block-and-rebuild critical section.
4. **Can the systemd `WatchdogSec` be reduced from 60s to 30s
   without false positives?** Camera 24/7 epic chose 60s for a
   reason — need to confirm with delta whether that reason still
   binds post-Tauri-decom.
5. **Is the v4l2loopback module 0.15.3 we are running the latest
   stable, or has the v4l2loopback project shipped fixes for the
   buffer-pool negotiation issue
   ([#36](https://github.com/v4l2loopback/v4l2loopback/issues/36))
   in a newer release?** Check at next pacman sync.
6. **Do we want the §9.5 timeout-image fallback even if Phase 3
   ships?** Slate-during-rebuild is operationally distinct from
   scene-switch-fallback; the two are complementary, not
   redundant.

---

## §15 Sources

### v4l2loopback
- [v4l2loopback GitHub repository](https://github.com/v4l2loopback/v4l2loopback)
- [v4l2loopback README (main branch)](https://github.com/v4l2loopback/v4l2loopback/blob/main/README.md)
- [v4l2loopback DeepWiki](https://deepwiki.com/v4l2loopback/v4l2loopback)
- [v4l2loopback-ctl manpage](https://manpages.org/v4l2loopback-ctl)
- [v4l2loopback-ctl Ubuntu manpage](https://manpages.ubuntu.com/manpages/xenial/man1/v4l2loopback-ctl.1.html)
- [v4l2loopback wiki — GStreamer page](https://github.com/v4l2loopback/v4l2loopback/wiki/Gstreamer)
- [Arch wiki: V4l2loopback](https://wiki.archlinux.org/title/V4l2loopback)
- [Gentoo wiki: V4l2loopback](https://wiki.gentoo.org/wiki/V4l2loopback)
- [v4l2loopback#36 — Could not negotiate format](https://github.com/v4l2loopback/v4l2loopback/issues/36)
- [v4l2loopback#97 — Internal data flow error / not-negotiated -4](https://github.com/umlaeute/v4l2loopback/issues/97)
- [v4l2loopback#116 — Cannot use v4l2loopback as sink for gstreamer1.0](https://github.com/v4l2loopback/v4l2loopback/issues/116)
- [v4l2loopback#169 — Failed in directing gstreamer NV12 video](https://github.com/umlaeute/v4l2loopback/issues/169)
- [v4l2loopback#174 — Internal data flow error from videotestsrc](https://github.com/v4l2loopback/v4l2loopback/issues/174)
- [v4l2loopback#204 — V4L2Loopback support for NV12 stream in Chromium](https://github.com/v4l2loopback/v4l2loopback/issues/204)
- [v4l2loopback#427 — Resolution change on the fly / producer disconnect](https://github.com/v4l2loopback/v4l2loopback/issues/427)
- [v4l2loopback#442 — exclusive_caps limits to single producer open](https://github.com/v4l2loopback/v4l2loopback/issues/442)
- [v4l2loopback#519 — Gstreamer RTSP videostream freezes after first frame](https://github.com/v4l2loopback/v4l2loopback/issues/519)
- [Issues with v4l2loopback and OBS — fpvmorais.com writeup](https://fpvmorais.com/post/issues_with_v4l2loopback/)
- [Anyone else with a v4l2loopback issue (Arch BBS)](https://bbs.archlinux.org/viewtopic.php?id=305169)

### GStreamer documentation
- [GStreamer v4l2sink reference](https://gstreamer.freedesktop.org/documentation/video4linux2/v4l2sink.html)
- [GStreamer v4l2src reference](https://gstreamer.freedesktop.org/documentation/video4linux2/v4l2src.html)
- [GStreamer queue reference](https://gstreamer.freedesktop.org/documentation/coreelements/queue.html)
- [GStreamer queue2 reference](https://gstreamer.freedesktop.org/documentation/coreelements/queue2.html)
- [GStreamer watchdog (gst-plugins-bad)](https://gstreamer.freedesktop.org/documentation/debugutilsbad/watchdog.html)
- [GstPad reference](https://gstreamer.freedesktop.org/documentation/gstreamer/gstpad.html)
- [GstBuffer reference](https://gstreamer.freedesktop.org/documentation/gstreamer/gstbuffer.html)
- [GstMessage reference](https://gstreamer.freedesktop.org/documentation/gstreamer/gstmessage.html)
- [GstBin reference](https://gstreamer.freedesktop.org/documentation/gstreamer/gstbin.html)
- [GStreamer Probes design doc](https://gstreamer.freedesktop.org/documentation/additional/design/probes.html)
- [GStreamer QoS design doc](https://gstreamer.freedesktop.org/documentation/additional/design/qos.html)
- [GStreamer Quality of Service plugin development](https://gstreamer.freedesktop.org/documentation/plugin-development/advanced/qos.html)
- [GStreamer Pipeline manipulation chapter](https://gstreamer.freedesktop.org/documentation/application-development/advanced/pipeline-manipulation.html)
- [GStreamer Caps negotiation chapter](https://gstreamer.freedesktop.org/documentation/plugin-development/advanced/negotiation.html)
- [GStreamer Clocks and synchronization chapter](https://gstreamer.freedesktop.org/documentation/application-development/advanced/clocks.html)
- [GStreamer Buffering chapter](https://gstreamer.freedesktop.org/documentation/application-development/advanced/buffering.html)
- [GStreamer OpenGL design doc](https://gstreamer.freedesktop.org/documentation/additional/design/opengl.html)
- [Basic tutorial 7: Multithreading and Pad Availability](https://gstreamer.freedesktop.org/documentation/tutorials/basic/multithreading-and-pad-availability.html)
- [Pipeline manipulation: dynamic pipelines (slomo's blog)](https://coaxion.net/blog/2014/01/gstreamer-dynamic-pipelines/)
- [Probes handling in GStreamer pipelines (Erit Lvx, Medium)](https://erit-lvx.medium.com/probes-handling-in-gstreamer-pipelines-3f96ea367f31)
- [MaZderMind dynamic-gstreamer-pipelines-cookbook](https://github.com/MaZderMind/dynamic-gstreamer-pipelines-cookbook)
- [MaZderMind cookbook — add-and-remove-network-sink example](https://github.com/MaZderMind/dynamic-gstreamer-pipelines-cookbook/blob/master/05-add-and-remove-network-sink.py)
- [Discourse: control queue size before dropping frames](https://discourse.gstreamer.org/t/control-queue-size-before-dropping-frames/190)
- [GStreamer queue plugin tutorial (Walter Fan cookbook)](https://walterfan.github.io/gstreamer-cookbook/4.plugin/queue.html)
- [Virtual web cam using GStreamer and v4l2loopback (A Weird Imagination)](https://aweirdimagination.net/2020/07/12/virtual-web-cam-using-gstreamer-and-v4l2loopback/)

### OBS Studio
- [OBS V4L2 source plugin (v4l2-input.c)](https://github.com/obsproject/obs-studio/blob/master/plugins/linux-v4l2/v4l2-input.c)
- [obs-studio#11295 — C920 select timed out / failed to log status](https://github.com/obsproject/obs-studio/issues/11295)
- [obs-studio#4926 — negative select timeouts from NaN framerate](https://github.com/obsproject/obs-studio/issues/4926)
- [obs-studio#5797 — bogus timeout value -9223372036854775808us](https://github.com/obsproject/obs-studio/issues/5797)
- [obs-studio PR #4005 — Add auto reset on timeout option](https://github.com/obsproject/obs-studio/pull/4005)
- [obs-studio commit 8814e2b — selective stream restart](https://github.com/obsproject/obs-studio/commit/8814e2bf4c77e2aae87d23ae0123119be69e3833)
- [obs-studio#10215 — V4L2 capture stays active on scene switch](https://github.com/obsproject/obs-studio/issues/10215)
- [OBS Forums — V4L2 plugin discussion](https://obsproject.com/forum/threads/video-capture-device-v4l2-plugin.17358/)
- [OBS Forums — OBS to v4l2loopback question](https://obsproject.com/forum/threads/obs-to-v4l2loopback.62677/)
- [OBS Forums — Advanced Scene Switcher resource](https://obsproject.com/forum/resources/advanced-scene-switcher.395/)
- [OBS Forums — Huge amount of error logs (camera framerate)](https://obsproject.com/forum/threads/huge-amount-of-error-logs-when-camera-doesnt-return-framerate.145191/)
- [How to setup v4l2 loopback for use with OBS (gist)](https://gist.github.com/ioquatix/18720c80a7f7eb997c19eef8afd6901e)
- [OBS Studio Automatic Stop/Restart Video Input (ataridogdaze)](https://ataridogdaze.com/tech/obs-auto-refresh-input.html)

### NVIDIA / GL
- [NVIDIA forum — 470.74 driver crash with gl elements in gstreamer pipeline](https://forums.developer.nvidia.com/t/470-74-driver-crash-when-using-gl-elements-in-gstreamer-pipeline/203029)
- [NVIDIA forum — GStreamer pipeline hangs after hours (Jetson Xavier NX)](https://forums.developer.nvidia.com/t/gstreamer-pipeline-hangs-after-hours-due-to-errors/174219)
- [NVIDIA forum — Gstreamer and v4l2loopback (Jetson Nano)](https://forums.developer.nvidia.com/t/gstreamer-and-v4l2loopback/175254)
- [NVIDIA forum — Watchdog for detecting a faulty camera (Xavier)](https://forums.developer.nvidia.com/t/watchdog-for-detecting-a-faulty-camera/259738)
- [NVIDIA forum — GPU is lost ramdomly](https://forums.developer.nvidia.com/t/gpu-is-lost-ramdomly-and-nvidia-smi-asks-for-a-reboot-to-recover-it/109240)
- [Arch BBS — Nvidia GPU has fallen off the bus](https://bbs.archlinux.org/viewtopic.php?id=304020)
- [Arch BBS — NVIDIA cannot resume from suspend with PreserveVideoMemoryAllocation](https://bbs.archlinux.org/viewtopic.php?id=290126)
- [NVIDIA suspend fix gist (bmcbm)](https://gist.github.com/bmcbm/375f14eaa17f88756b4bdbbebbcfd029)
- [Servo issue #27013 — GStreamer plugin fails to get GL context](https://github.com/servo/servo/issues/27013)
- [GStreamer GitLab issue #1300 — pipeline freezes after recording rapidly changing images](https://gitlab.freedesktop.org/gstreamer/gstreamer/-/issues/1300)

### systemd / sd_notify
- [systemd sd_notify(3) manpage](https://www.freedesktop.org/software/systemd/man/latest/sd_notify.html)
- [Using watchdog and sd-notify for systemd in Python 3 (stigok blog)](https://blog.stigok.com/2020/01/26/sd-notify-systemd-watchdog-python-3.html)
- [Basic Systemd sd_notify + watchdog usage gist (hacst)](https://gist.github.com/hacst/ee12cd91167aa55b19444fc74c91a8e8)
- [Showing off the systemd watchdog in Python (Spindel gist)](https://gist.github.com/Spindel/1d07533ef94a4589d348)
- [bb4242/sdnotify — pure-Python sd_notify](https://github.com/bb4242/sdnotify)
- [systemd-watchdog package on PyPI](https://pypi.org/project/systemd-watchdog/)
- [AaronDMarasco/systemd-watchdog](https://github.com/AaronDMarasco/systemd-watchdog)

### Hapax codebase
- `agents/studio_compositor/pipeline.py:30-310` — pipeline construction
- `agents/studio_compositor/pipeline.py:163-256` — v4l2sink branch (queue, convert, capsfilter, identity, sink, caps-dedup probe)
- `agents/studio_compositor/pipeline.py:233-252` — caps dedup probe (drops repeated identical CAPS events)
- `agents/studio_compositor/snapshots.py:15-79` — composited snapshot branch (CPU jpegenc to /dev/shm/hapax-compositor/snapshot.jpg)
- `agents/studio_compositor/snapshots.py:82-239` — fx snapshot branch (NVENC, recently bumped to p5 + 9 Mbps)
- `agents/studio_compositor/output_router.py:69-88` — sink kind inference (v4l2 inferred from `/dev/video*` prefix)
- `agents/studio_compositor/compositor.py:680-753` — bus message handler (already has special v4l2sink renegotiation case at line 715-716)
- `agents/studio_compositor/compositor.py:755-815` — `_write_status` and `_status_tick` (writes status.json + fd count gauge)
- `agents/studio_compositor/__main__.py:20-56` — sd_notify helpers (READY=1, WATCHDOG=1, STATUS=)
- `agents/studio_compositor/lifecycle.py:295-324` — sd_notify wiring + watchdog tick (gates on `any(s == "active" ...)` — the bug)
- `agents/studio_compositor/metrics.py:406-459` — Prometheus metrics (boot timestamp, watchdog last fed, fd count, rebuild count)
- `systemd/units/studio-compositor.service:14-19` — Type=notify + WatchdogSec=60s
- `systemd/units/studio-compositor.service:48-54` — ExecStart + ExecStopPost postmortem hook
- `systemd/units/studio-camera-setup.sh` — pre-start v4l2-ctl camera config
- `/etc/modprobe.d/v4l2loopback.conf` — `devices=5 video_nr=10,42,50,51,52 exclusive_caps=1,1,0,0,0 max_buffers=8`
- `docs/research/2026-03-16-v4l2loopback-direct-investigation.md` — prior direct-write investigation
- `docs/research/2026-04-14-compositor-output-stall-live-incident-root-cause.md` — 78-minute stall postmortem (dmabuf fd leak)
- `docs/research/2026-04-14-cudacompositor-consumer-chain-walk.md` — companion walk
- `docs/research/2026-04-20-tauri-decommission-freed-resources.md` — recent NVENC bitrate bump rationale
- `docs/issues/tauri-wayland-protocol-error.md` — `__NV_DISABLE_EXPLICIT_SYNC=1` workaround context
- `docs/superpowers/plans/2026-04-12-camera-247-resilience-epic.md` § 1.6 — sd_notify + WatchdogSec design rationale
