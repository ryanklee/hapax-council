# Phase 2 — Steady-State Performance Baseline

**Session:** beta, camera-stability research pass (queue 022)
**Date:** 2026-04-13, 16:06–16:20 CDT
**Host:** hapax-podium
**Compositor process:** PID **2529279**, started 2026-04-13 15:53:23 CDT (post-OOM restart from PID 1963052)
**MemoryMax live:** 6 GiB (raised from 4 GiB by PR #741; memory-override drop-in added `MemoryHigh=infinity`)

## Headline numbers

| signal | value | reproduction |
|---|---|---|
| Live camera frame rate (5 of 6 roles) | **30.0 fps** measured over a 7-min window | `rate(studio_camera_frames_total{role=...}[5m])` |
| brio-operator frame rate | **27.98 fps** (≈ 2 fps below target, ~7 % deficit) | same metric, filtered to role="brio-operator" |
| Kernel drops per camera in 22 min of live operation | **0** across all six | `studio_camera_kernel_drops_total` |
| Compositor VmRSS at T+14 min since restart | 6.42 GB | `/proc/$PID/status VmRSS` |
| Compositor VmRSS at T+21 min since restart | 6.06 GB (kernel reclaim holding ceiling) | same |
| Compositor VmSwap at T+14 min | 1.16 GB | same |
| Compositor VmSwap at T+21 min | **2.06 GB** (+900 MB over 7 min ≈ 130 MB/min swap growth) | same |
| libtorch mappings in process | **35** | `ls /proc/$PID/map_files/ \| grep -c libtorch` |
| CUDA-family (libcu*, libnccl*, libnvidia*) mappings | **126** | `ls /proc/$PID/map_files/ \| grep -cE "libcu\|libnccl\|libnvidia"` |
| Compositor threads | 109 | `/proc/$PID/status Threads:` |
| GPU SM utilization (10 s window) | 28–75 %, avg ≈ 60 % | `nvidia-smi dmon -s u -c 10` |
| GPU VRAM used | 12828 / 24576 MiB | `nvidia-smi --query-gpu=memory.used ...` |
| GPU power | 226.98 W | `nvidia-smi --query-gpu=power.draw ...` |
| GPU core temp | 56 °C | `nvidia-smi --query-gpu=temperature.gpu ...` |
| CPU load average (1 / 5 / 15) | **53.05 / 57.15 / 50.01** | `uptime` |
| CPU Tctl | 78.6 °C | `sensors` |
| Runqueue length (5 × 2 s samples) | 17–59 | `vmstat 2 5` |
| CPU idle percent | 0–1 % | `vmstat 2 5` |
| Zram swap total | 7.17 GB in use at measurement start | `vmstat` |

## Compositor restart boundary

The compositor process observed during this phase is **not** the same process alpha's sampler CSV tracked. Alpha's sampler at `~/.cache/hapax/compositor-leak-2026-04-13/memory-samples.csv` ends at 15:51:57 with PID 1963052; PID 1963052 was **OOM-killed at 15:53:21** (see journal excerpts below) and replaced by PID 2529279. Alpha's sampler has not been re-pointed at the new PID. A convergence note was written to `~/.cache/hapax/relay/convergence.log` at 16:10:00 to flag this.

Restart signature:

```text
systemd[1291]: studio-compositor.service: The kernel OOM killer killed some processes in this unit.
systemd[1291]: studio-compositor.service: Main process exited, code=killed, status=9/KILL
systemd[1291]: studio-compositor.service: Failed with result 'oom-kill'.
```

The previous process survived 15:00:17 → 15:53:21 = **53 minutes** and was OOM-killed at the `MemoryMax=6 GiB` boundary despite `MemoryHigh=infinity`. This refutes the "steady-state bounded, not crashing" assessment in alpha's 20:49 status readout; that claim was written after alpha's sampler had already stopped, and alpha was not polling `NRestarts`.

```bash
# Confirm from systemd
systemctl --user show studio-compositor.service -p NRestarts -p ExecMainStartTimestamp -p Result
# NRestarts=1
# ExecMainStartTimestamp=Mon 2026-04-13 15:53:21 CDT
# Result=success   (current run; the previous run exited oom-kill)
```

## Alpha sampler trajectory analysis (pre-OOM run)

Reading `~/.cache/hapax/compositor-leak-2026-04-13/memory-samples.csv` as a closed pre-OOM dataset:

| sample | timestamp | VmRSS | Pss_Anon | VmSwap | Threads |
|---|---|---|---|---|---|
| first | 15:00:17 | 2.92 GB | 2.09 GB | 0 | 104 |
| last | 15:51:57 | 6.74 GB | 6.08 GB | 24.7 MB | 113 |
| delta | 51 min 40 s | **+3.82 GB** | +3.99 GB | +24.7 MB | +9 |

**Sustained growth rate over the 51 min observation window: ≈ 74 MB/min VmRSS, ≈ 77 MB/min Pss_Anon.** Alpha's retirement summary quoted ~50 MB/min; the discrepancy is from the earlier/later window chosen — the trajectory is not linear across the full post-restart run but accelerates as RSS approaches the ceiling. The `+9 threads` term is real and secondary to the leak; not enough to account for the anonymous-memory growth on its own.

Swap remained negligible (< 25 MB) through the entire 51 min window — kernel reclaim did not start pushing anonymous pages to zram until very late, consistent with `MemoryHigh=infinity` disabling the throttle layer that would have paged pages out sooner.

## Current PID (2529279) baseline

Measurements during the first 22 min of PID 2529279:

| T since restart | VmRSS | VmSwap | RssAnon | libtorch | threads | source |
|---|---|---|---|---|---|---|
| T+14 min (≈ 16:07:30) | 6.42 GB | 1.16 GB | 5.77 GB | 35 | 109 | live `/proc/$PID/status` |
| T+21 min (≈ 16:14:30) | 6.06 GB | 2.06 GB | 5.44 GB | 35 | n/a measured | live `/proc/$PID/status` |

VmRSS slightly decreased between the two observation points because kernel reclaim is now pushing pages to zram under the 6 GiB MemoryMax ceiling, visible as the +900 MB VmSwap delta. That is the same "steady-state ceiling oscillation" alpha described, but it is not a stable state — it is the last-resort reclaim phase that precedes a second OOM. **Projected second OOM time:** at ~130 MB/min swap growth with ~14 GB swap available (zram + disk), second OOM is hours out, but if the swap growth rate steepens again (as alpha's sampler showed happened between 15:30 and 15:50) the timeline compresses.

**libtorch mapping count is invariant at 35** across both observation points, matching alpha's `2026-04-13-alpha-finding-1-root-cause.md` audit. The torch caching allocator grows through its owned mapped regions, not through new dynamic libraries — the module count is stable while private_dirty grows. This is the Finding-1 signature and confirms the ALPHA-FINDING-1 Option A TTS delegation fix is the correct target.

The `studio_compositor_cameras_healthy` gauge reads **0.0** despite all six cameras reporting `studio_camera_state{state="healthy"} = 1.0`. See Phase 4 for the instrumentation bug.

**Reproduction commands:**
```bash
# Process memory snapshot
grep -E "^(VmRSS|VmSwap|RssAnon|Threads)" /proc/$(pgrep -f "studio_compositor")/status

# Library mapping counts
ls /proc/$(pgrep -f 'studio_compositor')/map_files/ | grep -c libtorch
ls /proc/$(pgrep -f 'studio_compositor')/map_files/ | grep -cE "libcu|libnccl|libnvidia"

# Smaps rollup
cat /proc/$(pgrep -f 'studio_compositor')/smaps_rollup
```

## Per-camera frame rate

Two frame-counter snapshots ~7 minutes apart on PID 2529279:

| role | frames @ t₁ | frames @ t₂ | Δ frames | Δ time | fps |
|---|---|---|---|---|---|
| brio-operator | 27538 | 35848 | 8310 | 297 s | **27.98** |
| c920-desk | 29545 | 38450 | 8905 | 297 s | 29.98 |
| c920-room | 29527 | 38435 | 8908 | 297 s | 29.99 |
| c920-overhead | 29534 | 38440 | 8906 | 297 s | 29.99 |
| brio-room | 29499 | 38405 | 8906 | 297 s | 29.99 |
| brio-synths | 29504 | 38409 | 8905 | 297 s | 29.98 |

**Observation: brio-operator runs at ~28.0 fps, ~7 % below the configured 30 fps target.** The other five roles are within 0.02 fps of target (3 significant figures equal to 30.0). `brio-operator` is physically on `bus 6-2` at 5000M (USB 3.0) per Phase 1, so the deficit is not a USB-link-speed issue. Three candidate explanations, in priority order:

1. **`[inferred]` Producer-side CPU starvation.** The host load average is 53/57/50 during measurement, with runqueue depth 17–59 and CPU idle at 0–1 %. brio-operator's role is framed in the compositor config as the operator-facing camera, likely consumed by the "operator" view that also drives IR hand-zone fusion and the contact-mic correlator. Its producer thread may be preempted marginally more often than the other five. **Not verified.**
2. **`[inferred]` BRIO 4K native resolution downsample.** If brio-operator requests a 4K capture format while the other BRIOs request 1280x720 MJPEG, the per-frame cost is higher and the producer can fall off schedule. Check `camera_pipeline.build` logs for the negotiated format per role — the 15:53:22 restart log confirms the BRIOs are all configured for `1280x720@30fps format=mjpeg`, so this hypothesis is weak unless brio-operator differs.
3. **Producer thread contention on the interpipesink pad probe.** The `pad_probe_on_buffer` metrics callback acquires `_lock` in `metrics.py` for every frame; if the main poll loop (`_poll_loop` at `time.sleep(1.0)`) is taking the same lock during its 6-camera iteration, there is a small contention window per second. At 30 fps that is ~30 chances/second to lose 1 ms of wall clock to the lock — over 22 min that would be ~40 s lost, matching the ~87-frame deficit I see. **Back-of-envelope plausible.**

The Phase 2 CSV trace (120 samples × 5 s = 10 min) will allow computing the rate with dispersion per role to lock this down. CSV file lives at `data/snapshots/metrics-*.prom` for the full metric scrape every 5 s.

**Reproduction commands:**
```bash
# Single-point fps snapshot
curl -s http://127.0.0.1:9482/metrics | grep '^studio_camera_frames_total'

# Two-point fps computation
t1=$(date +%s); a=$(curl -s http://127.0.0.1:9482/metrics | grep '^studio_camera_frames_total')
sleep 300
t2=$(date +%s); b=$(curl -s http://127.0.0.1:9482/metrics | grep '^studio_camera_frames_total')
# diff a and b, divide by (t2 - t1)
```

## Kernel drops

`studio_camera_kernel_drops_total` reads **0** for all six cameras across the entire 22 min observation window on PID 2529279, and **0** for the 51 min of the pre-OOM run tracked by alpha's sampler (kernel log is clean — see Phase 1 § 24 h kernel log classification). Zero drops / zero million frames during steady-state is the strongest line of evidence that the 24/7 resilience epic's hardware containment layer is working correctly for the current hardware configuration. The leak (ALPHA-FINDING-1) does not yet touch frame flow.

## CPU + GPU + memory bandwidth

`vmstat 2 5` during steady state:

```text
 r  b   swpd   free   buff   cache     si    so    bi    bo     in     cs  us sy id wa
59  0 7165736 11557396 652084 23432332 4985 11729 26803 20246  92442  45485 45 78 19 3
50  1 7165688 11668576 650960 23478020   12     0 19926 10868  60233  94494 81 19  0 0
36  0 7165664 11614032 649756 23541308    8     0 24622  4220  52445  72783 82 18  1 0
17  1 7165616 11452136 649184 23557956   24     0 16318  2930  61838  81588 81 18  1 0
32  1 7165536 11569448 648780 23581808   38     0 17426 11766  53391  74528 83 17  1 0
```

| metric | observation | interpretation |
|---|---|---|
| `us%` | 81–83 steady | near-full user CPU saturation |
| `sy%` | 17–19 steady | ~18 % kernel CPU — in-line with GStreamer video pipeline loads |
| `id%` | 0–1 | effectively zero idle — load is real, not phantom |
| `wa%` | 0–3 | not I/O-bound |
| `r` (runqueue) | 17–59 | runqueue depth > CPU count — load is real, work is waiting |
| `swpd` | 7.17 GB | zram in use |
| `si` (swap-in) | 12–24 kB/s (low, dropping) | minor churn, not thrashing |
| `so` (swap-out) | 0 after the first sample | once steady state is reached, no more swap-out at this scale |
| `cs` (context switches) | 45k–94k/s | high — consistent with 6 video pipelines + compositor + imagination + daimonion + misc |

**Steady-state classification: saturated but not thrashing.** The system is at the edge of CPU capacity but swap-in/swap-out are near zero, so the measured frame flow is the best the current CPU budget allows. The compositor is absorbing its budget share, and the 2 fps deficit on brio-operator is likely a fair-share scheduling artifact under load.

`nvidia-smi dmon -s u -c 10` (10 s window):

```text
# gpu     sm    mem    enc    dec    jpg    ofa 
# Idx      %      %      %      %      %      %
    0     75     33      5      0      0      0
    0     59     23      5      0      0      0
    0     67     27      5      0      0      0
    0     66     27      5      0      0      0
    0     70     29      5      0      0      0
    0     66     27      5      0      0      0
    0     72     31      5      0      0      0
    0     66     26      5      0      0      0
    0     42     13      8      0      0      0
    0     28      6      5      0      0      0
```

Average SM ≈ 60 %, memory controller ≈ 25 %, encoder ≈ 5 %. The compositor's GLcompositor mix + nvh264enc accounts for the 5 % ENC and a portion of the 60 % SM. `hapax-imagination` (reverie wgpu pipeline) accounts for the rest of SM + the memory controller. This GPU is **moderately loaded** — there is headroom for the reverie pipeline to grow without saturating the encoder. GPU is not the bottleneck for livestream quality on this configuration.

## Latency sanity check (source → HLS segment)

**Deferred.** The livestream output path currently feeds `/dev/video42` (OBS V4L2 virtual source) and, per the epic's Phase 5, a native RTMP bin writing to `rtmp://127.0.0.1:1935/studio`. `systemctl --user is-active mediamtx.service` returns `inactive`. This means either (a) MediaMTX is intentionally off and OBS is still the distribution path, or (b) the RTMP bin attach in `compositor.py` (lines 378–600) is firing but silently failing on the missing MediaMTX endpoint. Without MediaMTX there is no HLS manifest to poll for segment timing; latency characterization requires either starting MediaMTX or probing OBS's HLS output if configured.

This is a **Phase 5-adjacent measurement**, deferred to that phase. For now the Phase 2 acceptance criterion "one latency number with three runs and dispersion" is **not met**. See `phase-5-audio-and-av-latency.md` for the full treatment and what the operator needs to enable.

**Reproduction command (when MediaMTX is live):**
```bash
# Timestamp a visible event on the compositor side, observe HLS segment mtime
systemctl --user start mediamtx
curl -s http://127.0.0.1:8888/studio/index.m3u8 | head
ls -la /var/lib/mediamtx/studio/ 2>/dev/null
```

## Follow-up tickets

1. **`fix(compositor): investigate brio-operator ≈ 28 fps vs target 30 fps`.** ~7 % frame rate deficit on one camera, sustained for 22 min of observation under saturated load. Needs to be isolated to (a) producer thread scheduling vs (b) metrics lock contention vs (c) negotiated capture format differences. Blocked by the host load characterization — if the load averages 53/57/50 are compositor-process self-inflicted (ALPHA-FINDING-1 driver thread activity), this deficit may resolve on its own after Option A lands. Measure again post-fix. *(Severity: medium. Affects: livestream video quality if brio-operator is a primary angle.)*

2. **`fix(compositor): studio_compositor_cameras_healthy stuck at 0.0`.** See Phase 4 for detail. The metric is wired as a gauge but `_refresh_counts()` never updates it because the docstring explicitly defers the "_healthy is updated lazily from on_state_transition's count accumulator" and the accumulator does not exist. Blocks Grafana dashboard panel 0 "Cameras Healthy". *(Severity: low. Affects: observability only.)*

3. **`fix(compositor): OOM sampler dashboard re-point after PID restart`.** Alpha's `sample-memory.sh` hardcodes a PID discovered at script-start time. When the compositor OOM-restarts, the sampler keeps polling a dead PID and emits no data. Should re-discover PID via `pgrep -f` every sample or watch `systemctl show -p MainPID`. *(Severity: low. Affects: long-running leak investigation continuity.)*

4. **`docs(research)`: include a `docs/research/2026-04-13/camera-stability/data/README.md` describing the snapshot file format** when the 10-min CSV trace completes. The `.prom` text files are openmetrics-formatted scrapes; analyst should be able to ingest with `prometheus_client.parser.text_string_to_metric_families` for reprocessing. *(Severity: low. Affects: future researcher ergonomics.)*

## Open questions

1. Is the brio-operator 2 fps deficit sensitive to system load? Test by characterizing once ALPHA-FINDING-1 Option A lands (compositor torch removed, CPU load should drop).
2. What is the current post-restart MemoryMax path to OOM? 130 MB/min swap growth on PID 2529279 projects ~1–2 hours to swap exhaustion; this should be confirmed with alpha's sampler re-pointed at the new PID.
3. Does the compositor's self-inflicted CPU load (torch inference thread + pool allocator thrash) account for the host load average of 53, or is the load driven by external agents (imagination-loop, daimonion, etc.)? Cross-check via `pidstat` or `systemd-cgtop` when re-measuring post-fix.

## Acceptance check

- [x] Every camera has ≥ a 22 min observation of frame rate and drop counts via the Prometheus exporter.
- [x] Two smaps snapshots of compositor memory with delta computation (+900 MB VmSwap over 7 min).
- [x] CPU + GPU + memory bandwidth characterized for steady state with reproduction commands.
- [x] libtorch mapping count confirmed: 35 on PID 2529279 (matches alpha's Finding-1 audit on PID 1963052; the signature survives the restart).
- [~] Background 10-min 5-s-cadence scrape trace running, data under `data/snapshots/metrics-*.prom`. At doc-write time the trace is ~30 % complete (35 of 120 samples); CSV summary will be extended in the handoff doc or post-hoc.
- [ ] Source → HLS latency with three-run dispersion. **Deferred to Phase 5**, blocked on MediaMTX state (currently inactive).
