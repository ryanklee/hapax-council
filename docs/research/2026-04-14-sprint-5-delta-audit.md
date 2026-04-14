# Sprint-5 delta audit — output / encoding / streaming

**Date:** 2026-04-14
**Author:** delta (beta role)
**Scope:** 24-hour reconciliation against sprint-5's eight findings
(F1–F8) on the compositor output and RTMP path. Asks: which of
sprint-5's fix proposals have landed, which are unchanged, and
what is the current runtime state of the encoding / streaming
subsystem?
**Register:** scientific, neutral
**Status:** audit only — no code change

## Headline

**Reconciliation table — eight sprint-5 findings, 2026-04-14 state:**

| # | Sprint-5 finding | Priority | Runtime state 2026-04-14 | Fix landed? |
|---|---|---|---|---|
| F1 | NVENC on GPU 1 (3090) | HIGH | Compositor now runs on **GPU 0 (5060 Ti)** — effectively resolved by CUDA enumeration, but **not pinned**. The fix (F1-C `CUDA_VISIBLE_DEVICES=0`) is not in `studio-compositor.service`. Could silently flip on any CUDA reorder. | No (runtime resolved, config fragile) |
| F2 | swap `nvh264enc` → `nvautogpuh264enc` | MEDIUM | `rtmp_output.py:90` still uses `nvh264enc` | No |
| F3 | `nvav1enc` plugin missing | LOW | `gst-inspect-1.0 nvav1enc` still "No such element" | No |
| F4 | HLS sink missing | HIGH/MED | MediaMTX has `hls: yes`, `hlsAddress: :8888`, `hlsVariant: lowLatency`. **But no `studio` path in `mediamtx.yml`**, so `curl http://127.0.0.1:8888/studio/index.m3u8` → 404. Cheap path (Sprint-5 F4 recommendation) is half-enabled. | Partial |
| F5 | bitrate ≥ 6000 kbps | MEDIUM | `pipeline.py:203 bitrate_kbps=6000`, `rtmp_output.py:41` default 6000 | **Already satisfied** |
| F6 | `cudacompositor` not GPU-pinned | HIGH | `pipeline.py:41` still constructs `cudacompositor` without `cuda-device-id`. Same runtime-state as F1 (lands on GPU 0 by default), same config fragility. | No |
| F7 | MediaMTX upstream relay | MEDIUM | `/etc/mediamtx/mediamtx.yml` `paths:` block is **empty** apart from the default `all_others:` stub. No `runOnReady`, no `studio` path, no YouTube / Twitch bridge. | No |
| F8 | tee architecture | INFO | Confirmed sound, no change | N/A |

**Summary.** Five of the eight findings are unchanged from 2026-04-13.
One (F1) is runtime-resolved but not durably pinned. One (F5) was
already satisfied at sprint-5 writing (default was 6000 kbps and
sprint-5 under-claimed). One (F4) is half-resolved via MediaMTX's
HLS listener but the `studio` publish path is missing from
`mediamtx.yml`. **Backlog items 193, 194, 196, 197, 198 remain open;
item 195 can close.**

## 1. F1 — NVENC GPU assignment

### 1.1 Current allocation (2026-04-14T14:45 UTC)

```text
$ nvidia-smi --query-compute-apps=pid,process_name,gpu_uuid,used_memory --format=csv
pid      process_name                                  gpu_uuid                                      used_gpu_memory
2812855  …/hapax-council/.venv/bin/python              GPU-347222d9-00af-5a94-a365-c57c09dfddcd      3015 MiB
2821577  …/hapax-council/.venv/bin/python              GPU-347222d9-00af-5a94-a365-c57c09dfddcd       286 MiB
2873960  …/hapax-imagination                           GPU-347222d9-00af-5a94-a365-c57c09dfddcd       302 MiB
1509     …/tabbyAPI/venv/bin/python3                   GPU-2d94387f-adb2-51b2-b40f-0c576022d1a9      5792 MiB
2807249  …/hapax-council/.venv/bin/python              GPU-2d94387f-adb2-51b2-b40f-0c576022d1a9      3360 MiB

$ nvidia-smi --query-gpu=index,name,uuid --format=csv
0, NVIDIA GeForce RTX 5060 Ti, GPU-347222d9-00af-5a94-a365-c57c09dfddcd
1, NVIDIA GeForce RTX 3090, GPU-2d94387f-adb2-51b2-b40f-0c576022d1a9
```

- `studio_compositor` (PID 2812855): **GPU 0 = 5060 Ti**, 3 015 MiB
- `studio_person_detector` (PID 2821577): **GPU 0 = 5060 Ti**, 286 MiB
- `hapax-imagination` (PID 2873960): **GPU 0 = 5060 Ti**, 302 MiB
- `tabbyapi` (PID 1509): **GPU 1 = 3090**, 5 792 MiB
- `hapax-daimonion` (PID 2807249): **GPU 1 = 3090**, 3 360 MiB

**Desired sprint-5 partition achieved.** All visual work on GPU 0
(Blackwell NVENC). All inference on GPU 1 (Ampere). Sprint-5
reported the compositor on GPU 1 — the runtime has since migrated,
either via operator action between sprint-5 and this audit, or by
CUDA enumeration reordering after the 5060 Ti was promoted to GPU 0.

### 1.2 The fragility: no durable pin

```text
$ systemctl --user cat studio-compositor.service | grep -iE "CUDA_VISIBLE|Environment"
Environment=PATH=…
Environment=HOME=…
Environment=XDG_RUNTIME_DIR=/run/user/1000
EnvironmentFile=/run/user/1000/hapax-secrets.env
Environment=OTEL_BSP_…
Environment=GST_GL_WINDOW=x11
Environment=DISPLAY=:0
```

`CUDA_VISIBLE_DEVICES` is not set. `cuda-device-id` is not set on
`nvh264enc` or `cudacompositor`. The compositor's GPU 0 residency
is a property of CUDA's current enumeration order, nothing stronger.
Any of: a driver update, a reboot re-enumerating PCI devices in a
different order, a `gsettings` / `prime-select` switch, or a manual
`CUDA_VISIBLE_DEVICES` override on some other context — could flip
the compositor back to GPU 1 without anyone noticing until TabbyAPI
suddenly shares SM with a CBR encoder.

**Backlog item 193 is still the correct fix.** The runtime is
already in the desired state; the unit file needs to lock it in.

### 1.3 Current NVENC session count

```text
$ nvidia-smi --query-gpu=index,encoder.stats.sessionCount,encoder.stats.averageFps --format=csv
0, 0, 0
1, 0, 0
```

**Zero NVENC sessions on both GPUs.** No encoder is currently
running. Matches the RTMP bin state (§ 5.1 below): the bin is
*constructed but detached*, waiting for a `toggle_livestream`
event. The compositor is compositing and driving the V4L2 loopback
to `/dev/video42`; the RTMP branch is cold. **When F1 eventually
matters is on the next `toggle_livestream` event; until then no
NVENC is running on either device.**

## 2. F2 / F3 — encoder element choices

```text
$ grep -nE "nvh264enc|nvautogpuh264enc|cuda-device-id" \
    agents/studio_compositor/rtmp_output.py
15:    tee → queue → videoconvert → nvh264enc → h264parse →
90:    encoder = Gst.ElementFactory.make("nvh264enc", "rtmp_nvh264enc")
92:    log.error("rtmp bin: nvh264enc factory failed")

$ gst-inspect-1.0 nvav1enc
No such element or plugin 'nvav1enc'
```

Unchanged from sprint-5. `nvh264enc` is still the factory; no
`cuda-device-id` is set on it; `nvav1enc` is still absent from the
GStreamer plugin set. Backlog items 194 and 196 remain open exactly
as written. Note the docstring comment on line 15 still describes
the pipeline with the old encoder — if a swap lands, the comment
updates too.

## 3. F4 — HLS sink

```text
$ ls /dev/shm/hapax-compositor/hls/
ls: cannot access '/dev/shm/hapax-compositor/hls/': No such file or directory

$ grep -n "hlssink" agents/studio_compositor/pipeline.py
(no matches)

$ sudo grep -E "^hls" /etc/mediamtx/mediamtx.yml | head -5
hls: yes
hlsAddress: :8888
hlsEncryption: no
hlsVariant: lowLatency
hlsAlwaysRemux: no

$ curl -sI http://127.0.0.1:8888/studio/index.m3u8 | head -1
HTTP/1.1 404 Not Found
```

Compositor side: unchanged — no `hlssink` element, no `hls/`
directory. MediaMTX side: HLS listener is running on `:8888` with
low-latency variant. But `curl` returns 404 because MediaMTX has no
`studio` path configured (see F7 below). **The cheap path from
sprint-5 F4 — "MediaMTX serves HLS off any RTMP path it receives"
— is blocked by two preconditions: (a) compositor pushes RTMP to
MediaMTX (requires `toggle_livestream`), and (b) MediaMTX has a
path for `studio` either explicit or via `all_others`. Neither is
satisfied right now.**

When a livestream is active and RTMP is pushing to
`rtmp://127.0.0.1:1935/studio`, MediaMTX's `all_others:` default
*might* accept the publish implicitly (its default is usually
"accept any publisher") — this audit did not test live publish
behavior because that would require toggling livestream on, which
is operator-level. A single 30 s test would resolve this.

## 4. F5 — bitrate

```text
$ grep -nE "bitrate_kbps" agents/studio_compositor/pipeline.py \
                         agents/studio_compositor/rtmp_output.py
agents/studio_compositor/pipeline.py:203:    bitrate_kbps=6000,
agents/studio_compositor/rtmp_output.py:41:        bitrate_kbps: int = 6000,
agents/studio_compositor/rtmp_output.py:94:            encoder.set_property("bitrate", self._bitrate_kbps)
```

Already at 6 000 kbps at both construction sites. Sprint-5 F5
recommended ≥ 6 000 kbps; the current value matches the floor.
**Backlog item 195 can close** unless alpha wants a bump above
6 000 for additional headroom.

## 5. F6 — `cudacompositor` pinning

```text
$ grep -nE "cudacompositor|cuda-device-id" agents/studio_compositor/pipeline.py
40:    # Try cudacompositor first, fall back to CPU compositor
41:    comp_element = Gst.ElementFactory.make("cudacompositor", "compositor")
44:    log.warning("cudacompositor unavailable — falling back to CPU compositor")
```

Unchanged. No `cuda-device-id` set. Same observation as F1: the
current runtime has `cudacompositor` running on GPU 0 via CUDA
default enumeration, but nothing guarantees this persists across
a reboot or driver update. Backlog item 193 (single
`CUDA_VISIBLE_DEVICES=0` env var) also fixes this.

### 5.1 RTMP bin lifecycle clarification

```text
$ journalctl --user -u studio-compositor.service --since "09:48:30" | grep rtmp
09:48:39 … "rtmp output bin constructed (detached until toggle_livestream)"
```

The RTMP bin is constructed at compositor startup but **detached
from the tee until an explicit `toggle_livestream` event**. This
is the expected mode-gated design (fortress vs rnd vs research).
It means all the RTMP-path findings (F1 NVENC GPU, F2 encoder
swap, F4 HLS, F5 bitrate, F6 cudacompositor, F7 upstream relay)
are *latent* — they only take effect the next time the operator
toggles livestream on. Zero NVENC sessions on both GPUs confirms
no encoding is happening right now.

## 6. F7 — MediaMTX upstream relay

```text
$ sudo grep -A 5 "^paths:" /etc/mediamtx/mediamtx.yml
paths:
  # example:
  # my_camera:
  #   source: rtsp://my_camera
  #
  # Settings under path "all_others" are applied to all paths that
  # do not match another entry.
  all_others:
```

`paths:` block is empty beyond the `all_others:` default stub.
There is no `studio:` path, no `runOnReady`, no upstream
`source: …` rule, no YouTube / Twitch relay. Any RTMP push to
`rtmp://127.0.0.1:1935/studio` will be accepted by `all_others:`
(MediaMTX's default policy on unlisted paths) but the stream
terminates at MediaMTX — no forward relay. **The operator's
current YouTube livestream path is almost certainly OBS reading
from `/dev/video42` and encoding/publishing independently, not
the compositor's RTMP bin → MediaMTX → upstream path.**

Backlog item 198 (wire the upstream relay rule) remains open.

## 7. F8 — tee architecture

Unchanged. The tee/v4l2sink/rtmp_bin design is sound per sprint-5
F8 and this audit adds no new observations. OBS decoupling from
RTMP failures is still guaranteed by the architecture: a YouTube
ingest hiccup via the rtmp_bin path cannot interfere with OBS's
V4L2 consumption.

## 8. Side observations (not sprint-5 scope but noted while auditing)

### 8.1 Compositor restarted at 09:48:39 CDT — automated, not operator

```text
09:46:52  systemd: Starting Hapax Python services — rebuild from main...
09:48:10  hapax-rebuild-compositor: main advanced: 0ae2a986 → f502bc54 — updating
09:48:10  systemd: Stopping Studio Compositor
09:48:25  systemd: Stopped Studio Compositor
09:48:39  compositor new PID 2812855 started
09:49:28  systemd: Finished Hapax Python services — rebuild from main.
```

29 s graceful stop / start cycle, driven by the
`hapax-rebuild-services.timer` → `hapax-rebuild-services.service`
chain on its 09:46:52 tick. The service runs
`scripts/rebuild-service.sh` once per tracked service with a
per-service `--watch` path filter; when a watched path has
changed between the last-rebuilt SHA and `origin/main` HEAD, the
helper pulls and restarts. The compositor's watch paths are
`agents/studio_compositor/ agents/effect_graph/ shared/` — a
commit landed in that set between the previous compositor
rebuild and f502bc54. Not operator-initiated, not a crash, not
the rebuild-logos chain that shipped the DetectionOverlay/
AmbientShader fixes earlier. Alongside the compositor, the
09:46:52 tick also restarted `visual-layer-aggregator`,
`hapax-watch-receiver`, `hapax-imagination-loop`, `studio-fx`,
and `studio-person-detector` — all services whose watch paths
intersected commits between their respective previous SHAs and
f502bc54.

This drop's § 1.1 measurements come from the **new** process
(uptime ~20 min at audit time), not the process drop #2's
histograms reflect. Brio-operator fps deficit persists in the
new process (27.85 fps over 10 min of fresh data, matches
drop #2's 27.94 over 6 h from the old process — the deficit is
structural, not a process-state artifact, re-confirming
drop #2).

### 8.2 `glfeedback` Rust plugin shader-recompile burst at startup

```text
09:48:56 (t+18 s) GST_RUST … shader_dirty detected — recompiling
09:48:56 (t+18 s) GST_RUST … Shader recompiled OK (165 chars), accum cleared
09:48:56 (t+18 s) GST_RUST … shader_dirty detected — recompiling
(~2 s window, hundreds of recompile pairs, each ~1–2 ms apart)
```

The `glfeedback` Rust GL filter (from the effect-graph plugin
memory) enters a hot shader-recompile loop in the ~2 s post-boot
window. Each pair is a `shader_dirty → recompile → accum
cleared` sequence taking 1–2 ms. Over the burst window, hundreds
of recompiles fire. **Not verified whether this continues at
steady state.** Worth a separate drop if the burst repeats on
every tick — but the trace here is consistent with a warmup
phase where the effect graph rapidly loads and compiles its
vocabulary presets before settling. Add to follow-up list.

### 8.3 Startup TTS failure (09:47:08)

```text
09:47:08 WARNING tts_client: server closed before header
```

One TTS client timeout on the old compositor process ~1 minute
before the restart. Probably unrelated to the restart (no error
cascade in the 09:47–09:48 window that I read). Noted only for
traceability in case alpha is investigating TTS reliability.

## 9. Follow-ups

Fresh items to backlog (not already captured by sprint-5 or prior
drops):

1. **Investigate `glfeedback` shader-recompile burst** — is it a
   2-second warmup or a sustained loop? Attach a metrics
   counter, or log a summary line when the dirty flag settles.
2. **`all_others:` publish behavior verification** — one 30 s
   test with `toggle_livestream` on and `curl
   http://127.0.0.1:8888/studio/index.m3u8` to confirm MediaMTX
   does serve HLS off the default path. Would close sprint-5 F4
   cheap path definitively.
3. **Backlog item 195 closure** — the bitrate is already 6 000
   kbps. Either close the item or bump the target above
   6 000 kbps.

Existing sprint-5 backlog items that remain open verbatim:

- **193** — `CUDA_VISIBLE_DEVICES=0` in studio-compositor.service
  (still the correct fix for F1 + F6 durability)
- **194** — `nvh264enc` → `nvautogpuh264enc` swap
- **196** — `nvav1enc` plugin availability research
- **197** — MediaMTX HLS endpoint as Logos preview source
- **198** — MediaMTX upstream YouTube/Twitch relay rule

## 10. References

- `2026-04-13/livestream-performance-map/sprint-5/sprint-5-output-and-streaming.md`
  — the eight findings this audit reconciles against
- `2026-04-14-brio-operator-producer-deficit.md` — referenced in
  § 8.1 for the cross-process brio-operator persistence check
- Scrape: `nvidia-smi --query-compute-apps` at 2026-04-14T14:45 UTC
- Scrape: `curl -s http://127.0.0.1:9482/metrics | grep studio_rtmp`
- `/etc/mediamtx/mediamtx.yml` — F4 and F7 evidence
- `agents/studio_compositor/rtmp_output.py` lines 15, 41, 90, 94 — F1, F2, F5
- `agents/studio_compositor/pipeline.py` lines 41, 203 — F5, F6
- `systemctl --user cat studio-compositor.service` — F1 env vars
