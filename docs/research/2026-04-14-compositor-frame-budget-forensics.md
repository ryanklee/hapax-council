# Compositor frame budget forensics

**Date:** 2026-04-14
**Author:** delta (beta role — livestream perf support)
**Scope:** Follow-up to the CPU audit that surfaced studio-compositor at ~560 %
CPU during R&D livestream mode. Asks: can the existing compositor telemetry
attribute that cost to individual sources, and — if not — what is the
smallest data-plane gap that has to close before cost-based optimization
can proceed.
**Register:** scientific, neutral
**Status:** investigation only — no code change

## Headline

**Three findings.**

1. **The Phase 7 budget enforcement machinery is installed but never used at
   runtime.** No caller in `agents/studio_compositor/` instantiates
   `BudgetTracker`, and the `publish_costs` / `publish_degraded_signal`
   publishers have `age_seconds = +Inf` on the live Prometheus exporter.
   Zero per-source frame-time samples are being recorded or exported as
   of 2026-04-14T14:37 UTC. Beta's PR #752 Phase 4 dead-path finding still
   holds, unchanged, 34 days after the FreshnessGauge was added to make it
   observable.
2. **The compositor's entire per-source cost telemetry is four binary
   freshness gauges.** `overlay_zones` and `sierpinski_lines` are alive
   with lifetime publish counts around 2×10⁵ and non-zero failure counts.
   The other four legacy gauges (`album`, `sierpinski`, `stream_overlay`,
   `token_pole`) all have `age_seconds = +Inf`. There is no per-source
   frame-time histogram, no per-source CPU counter, and no layout-level
   budget gauge anywhere in the 47-metric compositor namespace.
3. **`overlay_zones` has an intermittent 100 %-failure burst bug.** Live
   traffic shows ~50 `cairo.Error: invalid value` exceptions in a 4-second
   window at 09:36:22 CDT, traced to `text_render.py:188`
   (`cairo.ImageSurface(FORMAT_ARGB32, sw, sh)`). Outside the burst, the
   source publishes successfully. The burst onset at 09:36:22 falls 146 s
   after the Logos/Reverie rebuild restarted `hapax-imagination` at
   09:33:56, but causal chain is not established in this drop.

Consequence: **no targeted, cost-based livestream optimization at the
compositor is data-driven today**. Every "which source is expensive?"
question requires instrumentation work first. Before alpha ships any
frame-budget shedding, priority-weighted scheduling, or cost-aware
source gating, the BudgetTracker must be instantiated, fed, and
published.

## 1. Question

The Wave 2/5 execution plan assumes the compositor can answer the
question "which source is closest to starving the per-frame budget?"
so that the operator (and eventually the VLA) can drop the lowest-
priority source when sustained overruns occur. This drop asks:

- Is `BudgetTracker` wired into production?
- What per-source cost telemetry is actually on the wire today?
- Are there other metrics that could substitute while the budget path
  is dead?

## 2. Live measurement

Captured 2026-04-14T14:36–14:37 UTC, system in steady state, R&D
working-mode, studio-compositor PID 3013869, uptime since ~09:33 CDT
(process was rotated via `hapax-imagination` auto-restart during the
09:33:56 rebuild).

### 2.1 BudgetTracker instantiation audit

```text
$ grep -rn "BudgetTracker(" agents/studio_compositor/
(no matches)

$ grep -l "BudgetTracker" agents/studio_compositor/
agents/studio_compositor/budget.py           (class definition)
agents/studio_compositor/budget_signal.py    (TYPE_CHECKING import only)
agents/studio_compositor/cairo_source.py     (TYPE_CHECKING import only,
                                              optional __init__ parameter)
```

`cairo_source.py` accepts `budget_tracker: BudgetTracker | None = None`
as a constructor keyword argument (line 94). No caller in the package
passes one. The default is `None`, which short-circuits the record
path in `CairoSourceRunner._render_one_frame`. **The machinery is
opt-in per-source; no source has opted in.**

### 2.2 Compositor Prometheus namespace enumeration

47 `compositor_*` metrics on `http://127.0.0.1:9482/metrics`, grouped:

| Group | Count | Live | Notes |
|---|---|---|---|
| `compositor_publish_costs_*` | 5 | no | `age_seconds=+Inf`, counters 0 |
| `compositor_publish_degraded_*` | 5 | no | `age_seconds=+Inf`, counters 0 |
| `compositor_source_frame_overlay_zones_*` | 5 | **yes** | pub 197382, fail 1622, age 0.06 s |
| `compositor_source_frame_sierpinski_lines_*` | 5 | **yes** | pub 211887, fail 0, age 0.07 s |
| `compositor_source_frame_album_*` | 5 | no | `age_seconds=+Inf` |
| `compositor_source_frame_sierpinski_*` (legacy) | 5 | no | `age_seconds=+Inf` |
| `compositor_source_frame_stream_overlay_*` | 5 | no | `age_seconds=+Inf` |
| `compositor_source_frame_token_pole_*` | 5 | no | `age_seconds=+Inf` |
| `compositor_tts_client_timeout_total` | 2 | live | counter 0 |
| `compositor_audio_dsp_ms_*` (histogram) | 15 | live | 1.978 M samples, p99 ≲ 2 ms |

No per-source frame-time histogram. No per-source CPU attribution.
No layout-level budget gauge. No GStreamer pipeline-health counters
(frame drops, DTS jitter, appsrc back-pressure, interpipe switches,
NVENC encode latency).

### 2.3 Shared-memory artefact audit

```text
$ ls /dev/shm/hapax-compositor/ | grep -E "costs|degraded|budget"
(no matches)

$ ls /dev/shm/hapax-compositor/
album-cover.png       album-state.json
brio-operator.jpg     brio-room.jpg          brio-synths.jpg
c920-desk.jpg         c920-overhead.jpg      c920-room.jpg
consent-state.txt
fx-active.jpg         fx-ascii.jpg           fx-classify.jpg
fx-clean.jpg          fx-clean-smooth.jpg    fx-current.txt
fx-datamosh.jpg       …
```

No `costs.json`, no `degraded.json`, no `budget.json`. The
`publish_costs` spec says its output path is caller-supplied; no
caller means no path.

### 2.4 Freshness gauge cross-check

```text
compositor_publish_costs_age_seconds     +Inf
compositor_publish_costs_published_total  0.0
compositor_publish_costs_failed_total     0.0

compositor_publish_degraded_age_seconds     +Inf
compositor_publish_degraded_published_total  0.0
compositor_publish_degraded_failed_total     0.0
```

`+Inf` is the initial value; `published_total = 0` and `failed_total = 0`
together mean the publisher has never been called in this process. The
FreshnessGauge doing its job. The dead-path mitigation from the 2026-04-13
post-epic audit is working — the dead end is visible. No code has yet
closed the end-to-end gap.

### 2.5 `overlay_zones` failure-burst trace

Delta sampling on the counters:

```text
T=14:37:23 UTC   published_total 197349   failed_total 1622
T=14:37:33 UTC   published_total 197382   failed_total 1622   (+33 pub, +0 fail)
```

Steady state on the sample boundary: ~3.3 publishes/s, 0 failures.
But in a 4-second window at 09:36:22 CDT (14:36:22 UTC), journald
captured 20 ERROR events (shown below, trimmed). Comparing lifetime
counters before and after the burst:

```
before burst (≈09:36:20)   published ≈196558   failed ≈1572
after  burst (14:37:23)    published  197349   failed  1622

delta:                         ≈+791 pub         +50 fail
```

50 failures over a window that also saw ~791 successful publishes →
**failure rate during this 30-second window: ~6 %**. Outside the burst,
failure rate is < 0.1 %. Lifetime average (1622 / 198971) = 0.81 %.

Stack trace (abbreviated, same exception each tick):

```
ERROR CairoSource overlay-zones render failed
  cairo_source.py:418 _render_one_frame
  cairo_source.py:409 self._source.render(...)
  overlay_zones.py:358 zone.render(cr, canvas_w, canvas_h)
  overlay_zones.py:274 self._rebuild_surface(cr)
  overlay_zones.py:328 render_text_to_surface(style, padding_px=4)
  text_render.py:188   cairo.ImageSurface(FORMAT_ARGB32, sw, sh)

cairo.Error: invalid value (typically too big) for the size of
             the input (surface, pattern, etc.)
```

Error semantics for `cairo.ImageSurface`: raised when `sw` or `sh` is
`≤ 0` or exceeds the Cairo image-size limit (32 767 px in each
dimension for `ARGB32`). The error message's "typically too big" is
cairo's fixed wording; the literal failure can also be zero/negative.
At 5 Hz with full JSON-serialized tracebacks to journald, each
failure burst also costs kernel I/O bandwidth on top of the compute
waste on the rendering thread.

### 2.6 Rebuild coincidence window

```text
09:24:58  rebuild-logos.service starts
09:25:10  vite build starts
09:29:xx  vite build finishes, tauri cargo compile
09:33:54  Installed (not restarted — restart manually when ready)
09:33:55  auto-restarting hapax-imagination (binary newer by 6293 s)
09:33:56  rebuild-logos.service: Finished
          (new PIDs: hapax-logos 2650705, WebKit 2651039, hapax-imagination 2650664)

09:36:22  overlay_zones failure burst begins (≈50 failures over 4 s)
09:36:26  last burst entry in sample window
09:37:23  steady state resumed
```

Gap from `hapax-imagination` restart to failure burst onset: 146 s.
`overlay_zones` pulls text content from shared-memory state written
by the Visual Layer Aggregator (VLA), which in turn polls `logos-api`
and perception state. A plausible but unverified chain: a VLA tick
read stale/degraded state during the imagination cold-start window,
produced a zone with a 0-height or 0-width text style, and
`render_text_to_surface` asked Cairo for an invalid surface
rectangle. This drop does **not** verify that chain — the hypothesis
is flagged as an open question in § 4.

## 3. Hypothesis tests

### H1 — "BudgetTracker is instantiated but the publisher isn't called"

**Refuted.** Grep shows zero callers of `BudgetTracker(...)` in the
whole `agents/studio_compositor/` package. The machinery is installed
at the class-definition level only. The `cairo_source.py` runner
accepts a tracker but every construction site passes nothing, and the
runner's `None`-default short-circuits the record path. Any patch
that aims to "turn on" budget tracking must both instantiate the
tracker in the compositor main and thread it through every
`CairoSourceRunner` constructor in the compositor runtime.

### H2 — "Another publisher path exists (Grafana, waybar, a different port)"

**Refuted.** Checked the only compositor metric exporter on
`127.0.0.1:9482`. The 47-metric namespace contains no per-source
frame-time histogram, no layout-level budget gauge, and no alternate
`cost` / `budget` / `render_ms` families. The `hapax-council/docs/` tree
references one Grafana dashboard (`reverie-predictions` at
`localhost:3001/d/reverie-predictions/`) but that dashboard targets
the DMN prediction monitor, not the compositor. No second exporter
path is known.

### H3 — "Per-source attribution exists via the existing freshness gauges"

**Partially supported, but useless for budget.** Each
`compositor_source_frame_<id>_*` family exposes publish/failed/age
for one source. This is enough to detect whether a source is alive
and whether it's intermittently failing — both live-checked in § 2.5
for `overlay_zones`. But publish and failure are binary: the gauge
tells you a tick happened, not how long it took. Frame-time
distribution and budget headroom are absent. Cost-based optimization
cannot run on freshness-gauge data alone.

### H4 — "The `overlay_zones` failure burst is a sustained bug"

**Refuted.** Counter delta between 14:37:23 and 14:37:33 shows
+33 published / +0 failed → outside the burst, the source is
healthy. The burst is intermittent. Frequency over the process
lifetime cannot be established from a single sample; the 0.81 %
lifetime failure rate is an upper bound for what's happening now if
bursts are regular, and a lower bound if this was the first.

### H5 — "The failure burst is caused by the hapax-imagination restart"

**Unverified.** Timing is consistent (146 s gap, plausible VLA
propagation delay) but the causal chain through VLA → shared-memory
state → text style → invalid cairo dimension is not checked in this
drop. To confirm: compare the VLA-published overlay zone state
(`/dev/shm/hapax-compositor/overlay_zones_state.json` or equivalent,
path needs to be found) between 09:33:55 and 09:36:22. If the `width`
or `height` of any zone was 0 or negative during the burst window,
the hypothesis is supported. Handed off as § 4 item.

## 4. Open questions / follow-ups for alpha

In priority order for livestream smoothness:

1. **Instrument the data plane.** The smallest next step toward
   cost-based livestream optimization is to: instantiate one
   `BudgetTracker` in the compositor main, pass it to every
   `CairoSourceRunner` constructor, wire a 1 Hz
   `publish_costs(tracker, Path("/dev/shm/hapax-compositor/costs.json"))`
   timer, and confirm `compositor_publish_costs_age_seconds` drops
   from `+Inf` to `< 5 s`. This is 30–50 lines of code in the
   compositor shell — delta is not shipping it; flagging for alpha.
2. **Fix `text_render.py:188` against invalid sizes.** Add a guard
   `if sw <= 0 or sh <= 0 or sw > 32767 or sh > 32767: return None`
   and teach `overlay_zones._rebuild_surface` to skip the zone when
   the sub-surface is None. This makes the failure mode invisible
   to livestream output instead of logging 50 tracebacks/burst to
   journald. Note: delta is **not** asserting the guard is the
   complete fix — the upstream question is why the zone is ever
   sized 0 or > 32767 in the first place.
3. **Trace the VLA → overlay_zones → cairo chain.** Find the shared-
   memory artefact that carries zone state from VLA to
   `overlay_zones.py`, capture one snapshot during a failure burst,
   and inspect the width / height of every zone. Either confirms H5
   or falsifies it and opens a new investigation angle.
4. **Deprecate the four dead freshness gauges.** `album`,
   `sierpinski` (legacy), `stream_overlay`, `token_pole` are
   `age_seconds=+Inf` since process start. Either wire the source
   that should publish to them or remove the registration so the
   exporter stops advertising dead signals. Misleading telemetry is
   worse than no telemetry for an alpha session that has to trust
   the exporter to make decisions.
5. **Add GStreamer pipeline-health metrics.** There is currently no
   metric for frame drops, DTS jitter, appsrc back-pressure,
   interpipe hot-swap, or NVENC encode latency in the 47-metric
   compositor namespace. Livestream smoothness optimization without
   these counters is blind. This is a full sprint of work, not a
   single drop — delta will do a separate baseline survey (next drop)
   before proposing anything concrete.

## 5. References

- `agents/studio_compositor/budget.py` — `BudgetTracker`, `publish_costs`
- `agents/studio_compositor/budget_signal.py` — `publish_degraded_signal`
- `agents/studio_compositor/cairo_source.py` line 94 — dormant
  `budget_tracker` constructor param
- `agents/studio_compositor/text_render.py` line 188 — cairo surface
  allocation site that raises the invalid-size error
- `agents/studio_compositor/overlay_zones.py` lines 274, 328, 358 —
  call chain into text_render
- `docs/research/2026-04-13/round3-deep-dive/phase-3-finding-i-budget-layer.md`
  — prior beta research on the budget layer
- `docs/research/2026-04-13/post-option-a-stability/phase-3-budget-signal-dead-path.md`
  — the PR #752 Phase 4 dead-path finding
- `docs/superpowers/specs/2026-04-12-phase-7-budget-enforcement-design.md`
  — the original Phase 7 design that shipped the machinery
- `docs/superpowers/handoff/2026-04-13-alpha-post-epic-audit-retirement.md`
  — Follow-up ticket #6 (adding FreshnessGauge to dead paths), which
  is referenced verbatim in `budget.py` lines 45–82
- Scrape: `curl -s http://127.0.0.1:9482/metrics` at 14:37:23 and
  14:37:33 UTC (delta sampling for § 2.5)
- Journal: `journalctl --user -u studio-compositor.service --since
  "30 minutes ago"` for the 09:36:22 failure burst
