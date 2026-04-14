# OBS output node (v4l2loopback /dev/video42) interactions walk

**Date:** 2026-04-14
**Author:** delta (beta role — cam-stability focus)
**Scope:** First drop in a new systematic walk covering
the **OBS-bound output node** — `/dev/video42`, a
v4l2loopback kernel device that the compositor writes
to and OBS reads from. This drop audits the full
interaction surface between the compositor's v4l2sink
branch and the kernel loopback, including the
modprobe topology, GstV4l2Sink element properties,
caps negotiation workarounds, and the currently-absent
OBS consumer side. Plus a live finding on an **fd leak
of 13,615 dmabuf handles** that the LimitNOFILE=65536
drop-in (drop #41 BT-3) is currently absorbing.
**Register:** scientific, neutral
**Status:** investigation — 9 findings. No code changed.
**Companion:** drop #32 (encoder + output path walk),
drop #41 (FD leak root-cause still pending)

## Headline

**The compositor writes frames to `/dev/video42` (a
v4l2loopback device) blindly — it has no awareness of
whether OBS is actually consuming.** The kernel device
is in "capture" state per sysfs but no OBS process is
running; the compositor is writing to a dead end.

**Three configuration-level observations:**

1. **v4l2loopback kernel module has `max_buffers=2`**
   (default). With the compositor's upstream
   `queue_v4l2` at 5 buffers (drop #31 Ring 1 fix A,
   shipped) + the 2 kernel buffers, the total cushion
   is 7 frames ≈ 230 ms at 30 fps. Drop #31 Ring 1 fix
   B recommended `max_buffers=8` but requires a
   modprobe reload (disconnects all consumers). Still
   pending.
2. **`exclusive_caps=1` on video42** — the device
   announces either `VIDEO_CAPTURE` (to readers) or
   `VIDEO_OUTPUT` (to writers), but not both
   simultaneously. Required for OBS's v4l2 source to
   see the device as "a webcam to read from" rather
   than "a device to write to". Working as designed.
3. **Card label `StudioCompositor`** — set via
   `/etc/modprobe.d/v4l2loopback.conf`. Cosmetic; OBS
   users see this as the camera name.

**Six findings:**

4. **FD leak** (new, not about OBS directly): the
   compositor has **13,615 `/dmabuf:` file descriptors**
   plus 30 `/dev/nvidia0` handles. At the current
   ~90-minute process uptime, leak rate is ~150 fds/min.
   LimitNOFILE=65536 (drop #41 BT-3) is absorbing the
   leak but it's growing.
5. **Compositor holds TWO fds on /dev/video42** (not
   one). GStreamer v4l2sink opens the device once
   internally but the second fd source is unidentified
   — possibly from the identity element's drop-allocation
   path or an internal device-control fd. With
   `max_openers=10` this is fine, but it's worth
   documenting.
6. **`video10` is a dead reserved slot**. The modprobe
   config reserves it as `OBS_Virtual_Camera` with
   `exclusive_caps=1`, but nothing opens it. Presumably
   intended for a future OBS virtual camera use case
   that never landed.
7. **v4l2sink uses YUY2 format** (drop #32 finding 6
   reaffirmed). At 1920×1080 × 30 fps, YUY2 is ~124 MB/s
   vs NV12's ~93 MB/s. Net waste: ~31 MB/s of CPU
   memory bandwidth through v4l2sink's `videoconvert →
   capsfilter → identity → sink` chain. OBS supports
   both formats; the trade-off is compositor-side
   conversion cost and OBS-side operator familiarity
   (YUY2 is the historical default for OBS v4l2
   sources).
8. **v4l2sink has only 2 properties set: `device` and
   `sync=false`**. Everything else at defaults —
   `io-mode=auto`, `qos=true` (QoS events propagate
   upstream to the fx chain), `max-lateness=5000000`
   (5 ms but inactive with sync=false),
   `processing-deadline=15000000` (15 ms hint),
   `enable-last-sample=true` (keeps 1 frame in memory
   for the `last-sample` property — unnecessary for a
   pure output sink).
9. **Compositor has no awareness of OBS consumer
   presence**. The writer just pushes frames into
   v4l2loopback regardless of whether there's a
   consumer. When OBS is absent, the kernel queue
   cycles 2 buffers in a tight loop doing wasted QBUF
   / DQBUF work on every frame. A sysfs watch on
   `/sys/devices/virtual/video4linux/video42/state`
   could tell the compositor whether to skip the
   v4l2sink write path entirely when no consumer is
   present.

## 1. v4l2loopback kernel module topology

### 1.1 Module info

```text
Module: v4l2loopback
Version: 0.15.3 (upstream current)
Kernel: 6.18.16-1-cachyos-lts
```

### 1.2 Modprobe configuration

`/etc/modprobe.d/v4l2loopback.conf`:

```text
options v4l2loopback
  devices=5
  video_nr=10,42,50,51,52
  card_label="OBS_Virtual_Camera,StudioCompositor,YouTube0,YouTube1,YouTube2"
  exclusive_caps=1,1,0,0,0
```

**Device inventory:**

| Node | Card Label | `exclusive_caps` | Role |
|---|---|---|---|
| `/dev/video10` | `OBS_Virtual_Camera` | 1 | **Dead** — reserved but no producer/consumer |
| `/dev/video42` | `StudioCompositor` | 1 | **Compositor → OBS** |
| `/dev/video50` | `YouTube0` | 0 | ffmpeg YT stream 0 → compositor |
| `/dev/video51` | `YouTube1` | 0 | ffmpeg YT stream 1 → compositor |
| `/dev/video52` | `YouTube2` | 0 | ffmpeg YT stream 2 → compositor |

**`exclusive_caps` semantics:**

- `exclusive_caps=1` → the device announces `VIDEO_CAPTURE`
  xor `VIDEO_OUTPUT` to each opener based on the first
  streaming opener's mode. OBS sees the device as a
  capture device (webcam-like).
- `exclusive_caps=0` → announces both
  `VIDEO_CAPTURE|VIDEO_OUTPUT` simultaneously. Breaks
  OBS's v4l2 source detection (OBS skips devices that
  advertise OUTPUT caps).

video42's `exclusive_caps=1` is **mandatory** for OBS
compatibility. Without it, OBS wouldn't offer
`/dev/video42` as a selectable source.

### 1.3 `max_buffers=2` limitation

```text
$ cat /sys/module/v4l2loopback/parameters/max_buffers
2
```

**Default is 2.** Drop #31 Ring 1 fix B recommends
bumping to 8 for the camera-pipeline cushion benefit,
but the fix requires `modprobe -r v4l2loopback &&
modprobe v4l2loopback max_buffers=8` which
**disconnects all currently-open consumers** (OBS,
ffmpeg YouTube players, compositor itself). Needs a
planned downtime window.

**Upstream buffer cushion today** (drop #31 Ring 1
fix A shipped):

```text
v4l2sink element pool: 2 kernel buffers (max_buffers=2)
queue_v4l2 upstream:   5 leaky-downstream buffers
----------
Total:                 7 frames ≈ 233 ms at 30 fps
```

**With max_buffers=8** (pending):

```text
v4l2sink element pool: 8 kernel buffers
queue_v4l2 upstream:   5 leaky-downstream buffers
----------
Total:                 13 frames ≈ 433 ms at 30 fps
```

The ~200 ms delta is the drop #31 Ring 1 fix B benefit.
Target: livestream cushion for OBS scene transitions,
encoder hiccups, recording restarts.

### 1.4 Live device state

```text
$ cat /sys/devices/virtual/video4linux/video42/{name,state,buffers,max_openers,format}
StudioCompositor
capture
2
10
YUYV:1920x1080@30
```

**`state=capture` is stale** — it reflects the most
recent opener's mode, not currently-active state. OBS
is not running (pgrep returns no obs processes); the
compositor's v4l2sink opens in OUTPUT mode. The
"capture" reading likely reflects a prior OBS session
that has since exited.

**`buffers=2` matches `max_buffers=2`** — 2 kernel-side
allocation buffers currently active.

**`max_openers=10`** — up to 10 simultaneous openers.
Currently 1 (the compositor).

## 2. Compositor v4l2sink branch

### 2.1 Element chain

`agents/studio_compositor/pipeline.py:162-229`:

```text
output_tee
  → queue-v4l2 (leaky=downstream, max-size-buffers=5)
  → convert-out (videoconvert, dither=none)
  → sink-caps (capsfilter: video/x-raw,format=YUY2,1920x1080@30fps)
  → v4l2-identity (identity, drop-allocation=true)
  → output (v4l2sink, device=/dev/video42, sync=false)
```

The **caps dedup probe** is attached to the
`queue-v4l2` sink pad, filtering out redundant CAPS
events that input-selector produces during source
switching.

### 2.2 v4l2sink property audit

```python
sink = Gst.ElementFactory.make("v4l2sink", "output")
sink.set_property("device", compositor.config.output_device)
sink.set_property("sync", False)
```

**Council sets exactly 2 properties.** Everything else
at GstV4l2Sink defaults:

| Property | Default | Effect |
|---|---|---|
| `io-mode` | `auto` | Auto-picks MMAP for v4l2loopback |
| `async` | `true` | Async state transition to PAUSED |
| `qos` | `true` | QoS events flow upstream when buffers drop |
| `max-lateness` | `5000000` (5 ms) | Late-buffer drop threshold — inactive with sync=false |
| `processing-deadline` | `15000000` (15 ms) | Upstream latency hint |
| `render-delay` | `0` | No extra delay |
| `throttle-time` | `0` | No throttling |
| `enable-last-sample` | `true` | Keeps 1 frame in memory for `last-sample` property |
| `force-aspect-ratio` | `true` | Aspect preserved |
| `stats` (read-only) | {rendered, dropped, average-rate} | Per-element counters — **never scraped** |

**Finding 8a — `enable-last-sample=true` is unnecessary
for a pure output sink.** The property keeps a
reference to the last pushed sample so downstream
code can `get_property("last-sample")`. Nothing in
the compositor reads this. 1 frame of memory
(~4 MB at 1920×1080 BGRA) wasted. **OBS-N1**: set
`enable-last-sample=false`. 1 line.

**Finding 8b — `stats` property is unscraped.**
`GstV4l2Sink.stats` returns a `GstStructure` with
`rendered`, `dropped`, and `average-rate` counters.
**Drop #41 finding on unpopulated metrics reaffirmed:**
the counters are read-only and populated by GStreamer
on every buffer, but no Prometheus gauge scrapes them.
Would directly reveal OBS-bound frame drops. **OBS-N2**:
scrape `stats.rendered` and `stats.dropped` into
Prometheus counters every status tick. ~10 lines.

**Finding 8c — `qos=true` feedback loop**. When
v4l2sink drops a frame (due to kernel buffer full or
late arrival), it sends a QoS event upstream. The
upstream receivers are `identity → capsfilter →
videoconvert → queue_v4l2`. QoS events cascade
through the queue and reach the `pre_fx_tee → fx
chain → output_tee → pre_fx_tee` loop. **Per drop #35
finding 1**, cudacompositor's aggregator has
`latency=0` and is sensitive to upstream QoS
pressure. A v4l2sink drop under OBS contention could
propagate back to cudacompositor as "slow down"
signal, causing visible stutter on all output
targets.

**OBS-N3**: set `qos=false` on v4l2sink. This
prevents the v4l2loopback's 2-buffer bottleneck from
propagating QoS throttling back through the fx chain
to the composite input. ~1 line. Trade-off: if OBS
is genuinely slow, the compositor won't slow down to
match — the queue just drops more frames at the
v4l2sink branch. **That's fine** because drop
#31 Ring 1 fix A already set the queue to leaky=downstream
with 5 frames of cushion.

### 2.3 `identity drop-allocation=true` workaround

`pipeline.py:186-189`:

```python
# identity drop-allocation=true: standard v4l2loopback workaround for
# allocation query renegotiation (defense-in-depth alongside caps probe)
identity = Gst.ElementFactory.make("identity", "v4l2-identity")
identity.set_property("drop-allocation", True)
```

**What this prevents**: GStreamer's allocation query
is how downstream elements (v4l2sink) tell upstream
elements (videoconvert) "I'm going to provide buffer
memory from my own pool, please use it". For
v4l2loopback, the sink's buffer pool is the kernel's
v4l2 MMAP buffers (`max_buffers=2`). If upstream honors
the allocation query, it tries to use v4l2loopback's
buffers for every frame.

**v4l2loopback's known quirk**: when the upstream
capsfilter's caps differ from what v4l2loopback
announced, v4l2loopback rejects the allocation query
or returns a degraded result that causes upstream to
allocate a new buffer pool. This repeats on every
frame → constant allocation churn.

**The fix**: the `identity` element with
`drop-allocation=true` swallows the allocation query
as it flows upstream, so upstream never receives it.
Upstream then uses its own buffer pool (not v4l2's),
avoids the renegotiation trap, and copies frames into
v4l2's pool at the sink boundary.

**Trade-off**: one extra memcpy per frame at the
v4l2sink input (the copy from upstream pool to v4l2
pool). For 1920×1080 YUY2 that's ~4 MB/frame × 30 fps
= **120 MB/s of CPU memcpy work** that could be
avoided with a proper zero-copy path. But the
alternative (renegotiation churn) is worse.

**This is a well-known v4l2loopback workaround**.
Council's implementation matches the standard pattern.
No fix needed.

### 2.4 Caps dedup probe

`pipeline.py:202-225`:

```python
# Caps dedup probe: drop CAPS events with identical content to prevent
# v4l2sink renegotiation when input-selector switches between sources.
# GStreamer uses pointer comparison for event identity — even identical
# caps from a different pad trigger full renegotiation without this.
_last_caps: list[Any] = [None]

def _caps_dedup_probe(pad: Any, info: Any) -> Any:
    event = info.get_event()
    if event is None or event.type != Gst.EventType.CAPS:
        return Gst.PadProbeReturn.OK
    try:
        result = event.parse_caps()
        caps = result[1] if isinstance(result, tuple) else result
    except Exception:
        return Gst.PadProbeReturn.OK
    if _last_caps[0] is not None and _last_caps[0].is_equal(caps):
        return Gst.PadProbeReturn.DROP
    _last_caps[0] = caps
    return Gst.PadProbeReturn.OK
```

**What this prevents**: when the `input-selector`
element in the fx chain switches between camera
sources, each source sends a CAPS event downstream
even if the caps are byte-identical. GStreamer
compares event identity by pointer, not by content,
so a CAPS event from a different pad is treated as a
new format even when it isn't. v4l2sink reacts by
tearing down and re-creating its buffer pool —
expensive and causes a visible glitch.

**The probe intercepts CAPS events, parses their
content, compares against `_last_caps`, and drops
the event if equal.** This is byte-accurate comparison
that survives pointer-identity churn.

**Good pattern**. Worth documenting as a template for
any future element that's sensitive to CAPS event
churn.

**Finding**: the probe stores `_last_caps[0]` as a
mutable list element to work around Python closure
rules. A `nonlocal` variable would be cleaner but
this pattern is idiomatic and works. No change
needed.

## 3. FD leak observation (cross-cut)

Live state check at 2026-04-14 ~17:00:

```text
$ pid=$(pgrep -f studio_compositor | head -1)
$ ls -la /proc/$pid/fd 2>&1 | awk '{print $NF}' | sort | uniq -c | sort -rn | head -10
  13615 /dmabuf:
     30 /dev/nvidia0
     15 anon_inode:[eventfd]
      7 /dev/nvidiactl
      7 /dev/nvidia1
      2 socket:[5123310]
      2 pipe:[5133370]
      2 pipe:[5133369]
      2 pipe:[5115858]
      2 pipe:[5115857]
```

**13,615 `/dmabuf:` fds.** Plus 30 `/dev/nvidia0`
handles. Compositor process uptime at time of
measurement: ~90 minutes. Implied leak rate:

- `dmabuf`: ~150 fds/minute (13,615 / 90)
- `nvidia0`: ~0.33 fds/minute (30 / 90, much slower)

**Total: 20,557 fds**. LimitNOFILE is 65,536 (drop
#41 BT-3 drop-in). **The leak is currently absorbed**
but will hit the limit in roughly:

```text
(65536 - 20557) / 150 ≈ 300 minutes ≈ 5 hours of runtime
```

After which the compositor hits EMFILE again (drop
#41 finding 5 pattern).

**Root cause hypothesis**: dmabuf fds are leaking from
the GStreamer GL pipeline. Modern `glupload` /
`gldownload` on NVIDIA uses dmabuf for zero-copy
texture import/export. If every buffer allocation
creates a new dmabuf handle without releasing the
prior one, the count grows linearly with frame count.

**At 30 fps × 90 min = 162,000 frames**, if every
frame leaked a single dmabuf, we'd see ~162k fds.
Observed ~13.6k suggests **1 in ~12 frames leaks a
dmabuf fd**. Consistent with a conditional leak path
— e.g., "leak on glfeedback recompile" (drop #5 era)
or "leak on camera producer rebuild" (drops #27,
#37). The latter is more likely: each camera
rebuild tears down and rebuilds a producer pipeline,
and buffer pool handoff between old and new can
leak dmabuf references.

**Not OBS-node-specific**, but pertinent because:

- The FD leak is the loudest ticking time bomb in
  the compositor's live state
- Drop #41 BT-7 (track down the fd leak) is still
  open
- Drop #41 BT-5 (add `compositor_process_fd_count`
  gauge) is still open — without it, the leak grows
  silently until the next EMFILE crash

**Finding OBS-N4**: the OBS output path via v4l2sink
+ v4l2loopback **uses v4l2 MMAP buffers** which are
managed inside the kernel via `vb2_queue`. The v4l2
buffer mmap mechanism creates a dmabuf handle per
buffer when the producer uses GL zero-copy. **If the
v4l2sink is a source of the leak**, each v4l2loopback
buffer rotation could leak one dmabuf. With
`max_buffers=2` cycling at 30 fps, that's 60
dmabuf-per-second which would explain the 150/min
observed rate (within the noise of other leak
sources). **Speculative — needs direct verification.**

**Ring 3 action BT-7**: instrument dmabuf fd creation
via bpftrace or kprobes, or run the compositor under
`strace -e openat,close` filtered on `/dmabuf:` for
30 seconds and count the net leak. Either approach
identifies the leaking code path definitively.

## 4. Ring summary

### Ring 1 — OBS output node immediate wins

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **OBS-N1** | Set `v4l2sink.enable-last-sample=false` | `pipeline.py:190-192` | 1 | 1 frame × ~4 MB of memory saved |
| **OBS-N2** | Scrape `v4l2sink.stats` into Prometheus counters | `metrics.py` + status tick | ~10 | OBS-bound frame drops become scrape-visible |
| **OBS-N3** | Set `v4l2sink.qos=false` | `pipeline.py:190-192` | 1 | Prevents v4l2loopback QoS back-pressure from propagating through fx chain to cudacompositor |

**Risk profile**: all three are zero-risk property
changes on element creation.

### Ring 2 — scheduled downtime window

| # | Fix | Action | Impact |
|---|---|---|---|
| **OBS-N5** | Ship drop #31 Ring 1 fix B (`v4l2loopback max_buffers=2 → 8`) | `modprobe -r v4l2loopback && modprobe v4l2loopback max_buffers=8` | ~200 ms additional frame cushion; requires OBS disconnect + reconnect |
| **OBS-N6** | Drop the YUY2 format → NV12 (drop #32 finding 6) | `pipeline.py:181-184` capsfilter | ~31 MB/s memory bandwidth saved; requires OBS source reload to re-read format |

**Risk profile**: both need operator coordination
with OBS. OBS-N5 is more invasive (kernel module
reload). OBS-N6 is simpler (one capsfilter edit +
OBS v4l2 source refresh).

### Ring 3 — fd leak investigation

| # | Fix | Action |
|---|---|---|
| **OBS-N4** | Instrument dmabuf fd creation to find the leak | `bpftrace -e 'kprobe:dma_buf_fd { @[comm] = count(); }'` |
| **BT-5** (drop #41) | `compositor_process_fd_count` Prometheus gauge | Makes leak growth scrape-visible |

## 5. Cleanup / dead device

| # | Fix | Action |
|---|---|---|
| **OBS-N7** | Remove `/dev/video10` reservation from modprobe | Edit `/etc/modprobe.d/v4l2loopback.conf` to drop the first device slot |

video10 is reserved as `OBS_Virtual_Camera` but
nothing opens it. Either:
- There was an intent to use it for a virtual camera
  (OBS → compositor feedback loop?) that never
  landed
- Or it's a copy-paste artifact from an older config

Dropping it saves one `struct video_device` kernel
allocation and one unused /dev node. Trivial but
cleaner.

## 6. Cross-references

- `/etc/modprobe.d/v4l2loopback.conf` — modprobe
  config (5 devices, card labels, exclusive_caps)
- `/sys/devices/virtual/video4linux/video42/` —
  sysfs interface (name, state, buffers, format,
  max_openers)
- `agents/studio_compositor/pipeline.py:162-229` —
  v4l2sink branch construction (caps dedup probe,
  identity drop-allocation workaround, sink property
  set)
- `agents/studio_compositor/config.py` —
  `output_device` config (defaults to `/dev/video42`)
- `gst-inspect-1.0 v4l2sink` — element property
  reference
- Drop #31 Ring 1 fix A — `queue_v4l2` buffer
  bump 1 → 5 (shipped PR #807)
- Drop #31 Ring 1 fix B — v4l2loopback `max_buffers`
  2 → 8 (pending, requires downtime)
- Drop #32 finding 6 — YUY2 → NV12 format change
  (pending, requires OBS source reload)
- Drop #33 — HLS race incident (unrelated but same
  era)
- Drop #34 — USB topology H4 closeout
- Drop #41 finding 5 + BT-3 — `LimitNOFILE=65536`
  drop-in (shipped, absorbing the current leak)
- Drop #41 BT-5 — `compositor_process_fd_count`
  gauge (still open)
- Drop #41 BT-7 — fd leak root cause investigation
  (still open)

## 7. Walk continuation

**What's unexplored on the OBS output side after
this drop:**

1. **OBS v4l2 source configuration**: OBS's own
   source element (v4l2-input.c or similar) has
   properties for buffer depth, format selection,
   YUV conversion. Not auditable from the compositor
   side; requires OBS's config + state when OBS is
   running.
2. **Caps negotiation handshake**: what happens
   when OBS opens /dev/video42 while the compositor
   is streaming. The exclusive_caps=1 semantics say
   OBS sees the device as CAPTURE-only. The format
   negotiation uses `VIDIOC_G_FMT` → OBS accepts or
   falls back.
3. **Buffer contention under heavy OBS load**:
   with max_buffers=2, if OBS is slow to DQBUF (e.g.,
   while encoding a scene transition), the compositor
   blocks or drops. No direct test available without
   a live OBS load scenario.
4. **Reconnect behavior**: when OBS is restarted or
   swaps scenes, does the v4l2loopback handle the
   brief disconnect gracefully? The compositor
   doesn't watch for consumer presence (OBS-N5 area).
5. **The `/dev/video10` potential OBS virtual camera
   path**: why was it reserved? Worth asking the
   operator if a future use case exists.

**Next drop target**: live-capture-session audit —
what happens during an actual operator OBS session,
including scene transitions, recording, streaming.
Can only be done with OBS running. Deferred until
needed.
