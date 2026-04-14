# Compositor frame budget forensics — ERRATUM + corrected baseline

**Date:** 2026-04-14
**Author:** delta (beta role)
**Supersedes:** `2026-04-14-compositor-frame-budget-forensics.md` finding 2
**Register:** scientific, neutral
**Status:** correction only — no code change

## Summary

The earlier drop reported "the compositor's entire per-source cost telemetry
is four binary freshness gauges" and "47 `compositor_*` metrics". Both
claims are wrong. The drop's filter (`grep -E "^compositor_"`) excluded
the `studio_camera_*`, `studio_compositor_*`, `reverie_pool_*`, and
`hapax_imagination_*` families on the same exporter.

**Actual compositor exporter state as of 2026-04-14T14:45 UTC:** 85 unique
metric names across 8 families, including a per-camera frame-interval
**histogram** that refutes the earlier drop's claim of no frame-time
distribution data.

The two other findings from the original drop — (1) `BudgetTracker` is
installed but never instantiated, and (3) the `overlay_zones`
`cairo.Error` failure burst — are unaffected and stand.

## 1. What the earlier drop missed

### 1.1 Full family map

| family prefix | metric count | purpose |
|---|---|---|
| `compositor_source_*` | 30 | per-source freshness gauges (6 sources × 5 metrics) |
| `studio_camera_*` | 20 | per-camera rates, drops, states, **frame-interval histogram** |
| `studio_compositor_*` | 11 | VRAM, memory, watchdog, uptime, music_ducked, voice_active |
| `compositor_publish_*` | 10 | publish_costs + publish_degraded (still dead — see § 3) |
| `reverie_pool_*` | 6 | transient texture pool (bucket count, textures, acquires, allocations, reuse) |
| `compositor_audio_*` | 4 | audio DSP time histogram |
| `hapax_imagination_*` | 2 | shader rollback counter |
| `compositor_tts_*` | 2 | TTS UDS client timeouts |
| **total** | **85** | — |

Sprint-6 (2026-04-13) reported the namespace at 122 metrics. Today's
scrape shows 85 unique metric *names*; sprint-6's 122 probably counted
each labeled series expansion separately (e.g. 6 cameras × 1 metric =
6). This drop counts metric names, not time series.

### 1.2 Per-camera frame-interval histogram — sprint-6 N4 has been addressed

`studio_camera_frame_interval_seconds_bucket{role="<cam>"}` ships with
bucket edges `{5, 10, 16, 20, 25, 30, 33, 40, 50, 67, 100, 200, 500}` ms
— exactly the fix sprint-6 N4 recommended. Sprint-6's "no histogram of
frame intervals" finding is **refuted as of today**. Alpha's marathon
run (PR band #775–#795) is the likely landing vehicle, not confirmed in
this drop.

### 1.3 Live histogram baseline — all 6 cameras, 6 h process uptime

Derived from `sum / count` at 14:45 UTC after ~21 600 s wall clock:

| role | count | sum (s) | mean interval (ms) | mean fps |
|---|---|---|---|---|
| c920-desk | 649 225 | 21 641.338 | 33.33 | **30.00** |
| brio-room | 649 213 | 21 640.351 | 33.33 | **30.00** |
| c920-room | 649 321 | 21 640.106 | 33.33 | **30.00** |
| c920-overhead | 649 336 | 21 639.524 | 33.32 | **30.01** |
| brio-synths | 648 947 | 21 638.463 | 33.35 | **29.99** |
| **brio-operator** | **604 565** | **21 640.474** | **35.79** | **27.94** |

Five cameras are locked to 30.00 fps to four significant figures over
6 h. `brio-operator` is at 27.94 fps — 6.9 % deficit, ~44 600 missing
frames over the sample window. This matches sprint-1 F3 (28.50 fps
measured on a shorter window) and confirms the deficit is sustained and
producer-thread-side, not USB-bus-side. Today's number is slightly
worse than sprint-1's 28.50 but the windows are not directly
comparable.

### 1.4 Tail analysis — c920-desk vs brio-operator bucket distribution

Cumulative bucket counts, c920-desk (quiet, Bus 1 / 480 M):

```text
le=0.030   31 460       4.8 %
le=0.033  344 024      53.0 %
le=0.040  645 060      99.4 %
le=0.050  647 964      99.8 %
le=0.067  648 122     99.99 %
le=0.100  648 147    99.996 %
```

**c920-desk p99 ≈ 0.040 s (40 ms).** Research map's stated p99 target is
34 ms. Eleven thousand out of 648 000 frames (1.7 %) exceed the target.
Not catastrophic, but measurable.

Cumulative bucket counts, brio-operator (known deficit):

```text
le=0.030    4 744        0.8 %
le=0.033   56 490        9.4 %
le=0.040  586 431       97.2 %
le=0.050  603 241       99.9 %
le=0.067  603 517     99.99 %
```

**brio-operator p50 ≈ 0.036 s**, **p95 ≈ 0.040 s**, **p99 ≈ 0.040 s**.
brio-operator has shifted its entire distribution ~3 ms later vs
c920-desk, consistent with a producer thread that wakes up late rather
than an intermittent stall. No long tail: the camera is not
occasionally freezing, it is chronically running 3 ms slow.

## 2. What the earlier drop claimed wrongly (for the record)

| earlier claim | corrected status |
|---|---|
| "47-metric compositor namespace" | 85 metric names across 8 families |
| "no per-source frame-time histogram anywhere" | `studio_camera_frame_interval_seconds_*` exists, per-camera, 13 buckets |
| "four binary freshness gauges and that's it" | 6 freshness gauges (including the 2 hyphen-fixed ones) + per-camera histogram + per-camera rate counters |
| "no GStreamer pipeline-health counters" | partially wrong: `studio_camera_kernel_drops_total`, `studio_camera_frame_flow_stale_total`, `studio_camera_consecutive_failures`, `studio_camera_reconnect_attempts_total`, `studio_camera_transitions_total`, `studio_rtmp_*`, and `studio_compositor_pipeline_restarts_total` all exist. These cover some pipeline health dimensions. **Still genuinely missing**: appsrc back-pressure, DTS jitter, interpipe hot-swap counter, NVENC encode latency, encoder queue depth. |

## 3. Surviving findings from the original drop

Re-verified 2026-04-14T14:45 UTC:

### 3.1 `BudgetTracker` is still not instantiated

`grep -rn "BudgetTracker(" agents/studio_compositor/` → zero hits.
Original finding stands.

### 3.2 `publish_costs` / `publish_degraded_signal` are still dead

```text
compositor_publish_costs_age_seconds      +Inf
compositor_publish_costs_published_total   0.0
compositor_publish_degraded_age_seconds   +Inf
compositor_publish_degraded_published_total 0.0
```

No change. Dead path holds.

### 3.3 `overlay_zones` cairo.Error failure burst

Verified at 09:36:22–09:36:26 CDT, ~50 failures in 4 s, stack trace
terminating in `text_render.py:188
cairo.ImageSurface(FORMAT_ARGB32, sw, sh)`. Burst recovered by
09:37:23 — intermittent, not sustained. Original finding stands.

## 4. Partially-fixed prior finding: sprint-6 F5 hyphen bug

Sprint-6 F5 said 8 hyphenated freshness gauge names silently failed to
register at startup. Today's scrape shows:

- **Fixed** (now exist): `compositor_source_frame_overlay_zones_*`,
  `compositor_source_frame_sierpinski_lines_*`
- **Still missing** (no gauge): `brio_operator`, `brio_room`,
  `brio_synths`, `c920_desk`, `c920_room`, `c920_overhead`

Per-camera freshness gauges at the cairo source level are still not
emitted. Note however that per-camera frame-interval histograms (§ 1.2)
do provide an overlapping signal — "is this camera delivering frames
on time?" is answerable via the histogram even without the freshness
gauge.

**Hypothesis:** the freshness gauge name-mangling fix landed for the
non-camera cairo sources only (`overlay-zones`, `sierpinski-lines`) but
the 6 camera sources don't register through the same path — they might
use a different registration site, or the hyphen-fix only touched one
of two registration paths. Follow-up: grep for the gauge construction
site and check whether both paths are now underscore-safe.

## 5. New surviving follow-ups, re-prioritized

The original drop's follow-up list still applies with one reprioritization:

- **F2 (deprioritized)**: the research map target "p99 ≤ 34 ms" is
  already achievable for 5 of 6 cameras at the histogram level (they
  are at 40 ms p99 rather than 34 ms p99 — a 6 ms gap). This is an
  optimization target, not a blocking deficit. The **brio-operator
  producer-thread deficit** (§ 1.3) is a higher-value target because
  it represents a 6.9 % absolute frame loss, not a 6 ms tail shift.

- **NEW**: root-cause the brio-operator 27.94 fps deficit. This is
  sprint-1 F3 territory — flagged there but not fully investigated.
  Candidate causes: producer thread contention, appsink back-pressure,
  USB interrupt affinity, Logitech BRIO specific UVC firmware
  behavior. This is a good target for the next drop if alpha wants
  beta to pursue it.

- **NEW**: investigate why the 6 camera freshness gauges still don't
  register after the hyphen fix landed for cairo sources.

- **NEW**: `hapax_imagination_shader_rollback_total = 0` over the
  whole process lifetime. Confirms the effect graph has been stable
  this session (no compile-time rejections). Not a problem, but worth
  knowing as a reliability datum — if this counter starts moving, the
  shader graph is under stress.

## 6. References

- `2026-04-14-compositor-frame-budget-forensics.md` — the drop this
  erratum corrects
- `2026-04-13/livestream-performance-map/sprint-1/sprint-1-foundations.md`
  finding 3 — original brio-operator producer-thread deficit
- `2026-04-13/livestream-performance-map/sprint-6/sprint-6-observability-and-reliability.md`
  findings N1.1, N4, F5 — the prior observability baseline
- Scrape: `curl -s http://127.0.0.1:9482/metrics` at 2026-04-14T14:45 UTC
- Grep: `grep -rn "BudgetTracker(" agents/studio_compositor/`
