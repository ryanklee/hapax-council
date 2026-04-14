# Metric coverage gaps — consolidated observability backlog

**Date:** 2026-04-14
**Author:** delta (beta role)
**Scope:** Consolidates every "metric doesn't exist / is wrong /
is a dead path" finding from delta's 2026-04-14 perf drops into
one observability backlog for alpha. Asks: what's the shortest
path to an observability surface that can answer the questions
delta's research drops couldn't?
**Register:** scientific, neutral
**Status:** organizational — no new investigation

## Current state

```text
$ curl -s http://127.0.0.1:9482/metrics | grep "^# TYPE" | wc -l
86
```

86 metric types across 9 families: `compositor_audio`,
`compositor_publish`, `compositor_source`, `compositor_tts`,
`hapax_imagination`, `reverie_pool`, `studio_camera`,
`studio_compositor`, `studio_rtmp`. That's the compositor
exporter on `127.0.0.1:9482`. Host-level metrics from
`node-exporter` are down per sprint-6 N2. The other council
services (logos-api, officium-api, reverie-predictions,
litellm, qdrant) have their own exporters, not audited here.

## Gaps, grouped by severity

### Category A — dead path: metric exists, fires 0 samples

Metrics that the exporter advertises but never records. These
are either unwired or bugged.

| # | metric family | drop | problem | fix cost |
|---|---|---|---|---|
| A1 | `compositor_publish_costs_*` (5 metrics, age `+Inf`) | 1 | `BudgetTracker.publish_costs()` never called; Phase 7 machinery installed but no timer | **S** — one periodic timer call in the compositor main |
| A2 | `compositor_publish_degraded_*` (5 metrics, age `+Inf`) | 1 | same shape as A1 | **S** — same timer would publish both |
| A3 | `studio_camera_kernel_drops_total` (6 per-role labels, all `0.0` over 6 h, 650 k frames each) | 2 | v4l2 sequence-gap detector doesn't fire for MJPG payloads — **false zero** for the uvcvideo path | **M** — replace signal source or correct the help text; 1 errata drop |
| A4 | `compositor_source_frame_album/sierpinski/stream_overlay/token_pole_*` (4 legacy freshness gauges, age `+Inf` since process start) | 1 errata | sources were superseded by the Phase 7 registry but the metrics were not retired | **S** — remove registration, or wire new sources |

A1 + A2 share a single fix (instantiate BudgetTracker + wire
publish_costs into the compositor's periodic tick). A3 is an
observability correctness bug. A4 is metric hygiene.

### Category B — partial path: metric exists for some inputs, not all

| # | metric | drop | problem | fix cost |
|---|---|---|---|---|
| B1 | `compositor_source_frame_<camera>_*` | 1 errata | overlay_zones + sierpinski_lines fixed the hyphen bug; **the 6 camera-role freshness gauges still miss the hyphen fix** and don't register | **S** — replicate the name-mangling fix into the camera registration site |

### Category C — metric doesn't exist, would be load-bearing

Metrics I specifically needed to answer a question in one of
the perf drops but that don't exist on any exporter.

| # | proposed metric | shape | drop that needed it | why |
|---|---|---|---|---|
| C1 | **per-source frame-time histogram** | Histogram with buckets matching `studio_camera_frame_interval_seconds` | 1 | answers "which cairo source is closest to starving the layout budget" (the whole point of BudgetTracker) |
| C2 | **appsrc / v4l2src back-pressure** | Counter `studio_camera_appsrc_backpressure_total` | 2 | would distinguish a brio-operator kernel drop from a producer-thread stall; resolves drop #2 H3 |
| C3 | **DTS jitter histogram** | Histogram `studio_camera_dts_jitter_seconds` | 2 | pacing signal independent of frame count |
| C4 | **interpipe hot-swap counter** | Counter `studio_camera_interpipe_swap_total{role=…,direction=…}` | (sprint-6 N-gap) | visibility on camera FSM failover events |
| C5 | **NVENC encode latency** | Histogram `studio_rtmp_nvenc_encode_ms` | 4 | pacing signal at the encoder, pre-RTMP |
| C6 | **NVENC encoder queue depth** | Gauge `studio_rtmp_queue_buffers` | 4 | back-pressure signal into the encoder |
| C7 | **glfeedback shader recompile counter** | Counter `compositor_glfeedback_recompile_total{result=ok\|fail}` | 5 | trend visibility on drop #5's recompile storm; also gives a proof-of-fix metric when the diff check lands |
| C8 | **glfeedback accum-clear counter** | Counter `compositor_glfeedback_accum_clear_total` | 5 | visual-reset event count (proxy for livestream flicker frequency) |
| C9 | **PipeWire xrun counter** | Counter `studio_audio_xruns_total` | 11 | audio glitch trend visibility; no user-space counter exists for this on the box today |
| C10 | **director_loop LLM call counter** | Counter `director_loop_llm_calls_total`, Counter `director_loop_llm_tokens_total{direction=prompt\|completion\|cache_read\|cache_write}` | 8 | cost attribution for LRR research spend |
| C11 | **Anthropic prompt-cache hit ratio** | Counter + derivative: `anthropic_cache_read_tokens_total`, `anthropic_cache_create_tokens_total` per caller | 8, 9 | proof-of-fix metric for the prompt-cache sweep; already exposed in `usage.cache_*_input_tokens` response fields, just needs a scraper |
| C12 | **studio_fx effect CPU** | Gauge `studio_fx_effect_ms{effect=…}` | 6 | per-effect cost visibility; required to validate that the OpenCV CUDA fix actually reclaims CPU |

### Category D — missing diagnostic inputs (one-shot debug tools)

Not Prometheus metrics — these are capture-on-failure logging
enhancements that unblock specific root-cause investigations.

| # | proposal | drop | why |
|---|---|---|---|
| D1 | capture `(sw, sh, text_w, text_h, len(style.text), prefix(style.text, 120))` at `text_render.py:188` exception site | 3 | resolves drop #3 H1/H2/H3 in one burst observation |
| D2 | capture `(tracker_snapshot, frame_n)` at the hypothetical `over_layout_budget` path once A1 lands | 1 | would correlate visible stutter with source-specific budget overrun |
| D3 | structured log at compositor-startup announcing every optional feature that was probed: `_HAS_CUDA`, prometheus availability, BudgetTracker active, etc. Line format: `feature-probe: NAME=BOOL` | 6 | would have caught the `_HAS_CUDA = False` latent-feature pattern on day 1 without needing a research drop. Also applies to BudgetTracker: announce `budget-tracker: active=false` on startup |
| D4 | Verification fields for prompt-cache deployment: add `usage.cache_creation_input_tokens` and `usage.cache_read_input_tokens` to the existing `record_spend` call in `director_loop.py:680-685` — and in every sibling caller from drop #9's audit | 8, 9 | self-verifying rollout |

## Priority — what to land first

Three rings, in shipping order:

### Ring 1 — one-function patches unblocking everything else

1. **A1 + A2 + C1 together**: instantiate `BudgetTracker`, pass
   it to every `CairoSourceRunner` constructor in the
   compositor main, add a 1 Hz `publish_costs()` timer. One
   PR, ~30-50 LoC, unblocks the cost-attribution question I
   asked in drop #1 and every downstream drop.

### Ring 2 — proof-of-fix metrics (land with their fix)

2. **C7 + C8** land with the glfeedback diff check from drop
   #5. Emit one counter per shader recompile and one per
   accum clear. After the fix, the counters drop to ≤ 20/hour
   instead of 336/hour.
3. **C11 + D4** land with the prompt-cache sweep from drops
   #8/#9. Verifies that `cache_control` annotations are being
   honored end-to-end.
4. **C12** lands with the studio_fx OpenCV CUDA fix from drop
   #6. Lets alpha measure the CPU savings without trusting
   observation.

### Ring 3 — standing observability backlog (sprint-sized)

5. **C2, C3, C4, C5, C6** — GStreamer pipeline-health and
   encoder counters. These are a sprint of instrumentation
   work, not individual fixes. Bundle under
   "compositor-pipeline-health-instrumentation" and ship as
   a coherent set so the dashboards can light up together.
6. **C9** — PipeWire xrun counter. Separate from the
   GStreamer ones because the signal source is different
   (PipeWire internal vs GStreamer pad probe).
7. **A3** — kernel_drops false-zero correction. Lower
   priority because it's "fix observability, then re-enable
   the drop-diagnosis pipeline from drop #2" — it's
   prerequisite work for a future brio-operator root-cause
   drop.
8. **A4** — legacy freshness gauge hygiene. Pure housekeeping.
9. **B1** — 6 camera freshness gauges. Completes the sprint-6
   F5 hyphen fix.

### Ring 4 — diagnostic inputs (ship on demand)

10. **D1** — ship when alpha wants to close drop #3's H1/H2/H3.
11. **D2** — ship alongside A1/A2 from Ring 1.
12. **D3** — standalone hygiene. One line per probed feature
    at compositor startup. Would have saved delta 2 drops of
    investigation this session (drops 1 and 6).

## Why this matters more than it looks

Three of delta's ten drops today were fundamentally
"I couldn't answer the question because the metric didn't
exist or was zeroed":

- drop #1 (frame budget forensics): couldn't attribute CPU
  to sources → BudgetTracker is uninstalled
- drop #2 (brio-operator deficit): couldn't locate the 45 k
  frame loss → kernel_drops is a false zero
- drop #3 (overlay_zones burst): couldn't reproduce without
  a live capture → no diagnostic log line at the exception
  site

All three investigations would have been short if the
metrics existed. A single sprint of observability
instrumentation — Ring 1 + Ring 2 from § above — unlocks
most of the follow-up questions delta's drops leave open.
**That is the highest-leverage observability work alpha can
ship right now for future delta-style perf investigations.**

## References

- `2026-04-14-compositor-frame-budget-forensics.md` (drop 1) — A1, A2, C1, D2
- `2026-04-14-compositor-frame-budget-forensics-errata.md` — A4, B1
- `2026-04-14-brio-operator-producer-deficit.md` (drop 2) — A3, C2, C3
- `2026-04-14-overlay-zones-cairo-invalid-size.md` (drop 3) — D1
- `2026-04-14-sprint-5-delta-audit.md` (drop 4) — C4, C5, C6
- `2026-04-14-glfeedback-shader-recompile-storm.md` (drop 5) — C7, C8
- `2026-04-14-studio-fx-cpu-opencv-gpu-gap.md` (drop 6) — C12, D3
- `2026-04-14-director-loop-prompt-cache-gap.md` (drop 8) — C10, C11, D4
- `2026-04-14-prompt-cache-audit.md` (drop 9) — C11, D4 (additional sites)
- `2026-04-14-audio-path-baseline.md` (drop 11) — C9
- Live scrape: `curl -s http://127.0.0.1:9482/metrics | grep
  "^# TYPE" | wc -l` → 86 metric types
