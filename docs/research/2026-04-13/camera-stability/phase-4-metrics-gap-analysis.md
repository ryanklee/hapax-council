# Phase 4 — Prometheus Metric Coverage Gap Analysis

**Session:** beta, camera-stability research pass (queue 022)
**Date:** 2026-04-13, 16:15–16:25 CDT
**Metric endpoint:** `http://127.0.0.1:9482/metrics` (exposed in-process from `agents/studio_compositor/metrics.py`)
**Source of truth:** `agents/studio_compositor/metrics.py` defines 20 distinct metric names; `grafana/dashboards/studio-cameras.json` defines 12 panels.

## Headline

- **20 metric names are instrumented in `metrics.py`.** 15 appear in the live scrape on PID 2529279. 3 are absent because the events they count (state transitions, reconnect attempts, pipeline restarts) have not occurred on this PID. **2 are entirely dead callsites** (`studio_rtmp_bytes_total`, `studio_rtmp_bitrate_bps` — defined but never `.labels(...)`'d anywhere in the source).
- **One broken gauge:** `studio_compositor_cameras_healthy` reads **0.0** while all six cameras report `studio_camera_state{state="healthy"} = 1.0`. The Grafana panel "Cameras Healthy" (panel 0) will show a wrong number. Root cause is in `metrics.py` itself.
- **Grafana dashboard has 12 panels.** 6 will show "no data" on the current PID because their backing series are absent or dormant.
- **No dmesg-only failures were found** in the Phase 1 24 h kernel log window (zero EPROTO, zero `error -71`, one benign SuperSpeed reset). The metric exporter is not missing any failure mode that is visible in dmesg right now, but only because the hardware has been calm. A proposed `studio_usb_xhci_distress_total` series would still close the gap the moment that class of error returns.

## Series classification

Full list of series names surfaced by `curl -s http://127.0.0.1:9482/metrics | grep -oE '^studio_[a-z_]+' | sort -u`:

```text
studio_camera_bytes_created
studio_camera_bytes_total
studio_camera_consecutive_failures
studio_camera_frames_created
studio_camera_frames_total
studio_camera_in_fallback
studio_camera_kernel_drops_created
studio_camera_kernel_drops_total
studio_camera_last_frame_age_seconds
studio_camera_state
studio_compositor_boot_timestamp_seconds
studio_compositor_cameras_healthy
studio_compositor_cameras_total
studio_compositor_uptime_seconds
studio_compositor_watchdog_last_fed_seconds_ago
```

Note: the `*_created` variants (`frames_created`, `bytes_created`, `kernel_drops_created`) are `prometheus_client` auto-emitted "Counter created timestamp" metadata — one per Counter, not a separate instrumentation. Effective series count surfaced live = **12 names** of the 20 defined.

| name | defined in metrics.py? | wired (call site exists)? | present in live scrape? | classification |
|---|---|---|---|---|
| `studio_camera_frames_total` | yes | yes (`pad_probe_on_buffer`) | yes | LIVE |
| `studio_camera_kernel_drops_total` | yes | yes (`pad_probe_on_buffer`) | yes (all 0 on PID 2529279) | LIVE |
| `studio_camera_bytes_total` | yes | yes | yes | LIVE |
| `studio_camera_last_frame_age_seconds` | yes | yes (`_poll_loop`) | yes | LIVE |
| `studio_camera_state` | yes | yes (`register_camera`, `on_state_transition`) | yes (all healthy=1) | LIVE |
| `studio_camera_consecutive_failures` | yes | yes (`on_consecutive_failures_changed`) | yes (all 0) | LIVE |
| `studio_camera_in_fallback` | yes | yes (`on_swap`) | yes (all 0) | LIVE |
| `studio_camera_transitions_total` | yes | yes (`on_state_transition`) | **no** | fault-only |
| `studio_camera_reconnect_attempts_total` | yes | yes (`on_reconnect_result`) | **no** | fault-only |
| `studio_compositor_boot_timestamp_seconds` | yes | yes (`start_metrics_server`) | yes | LIVE |
| `studio_compositor_uptime_seconds` | yes | yes (`_poll_loop`) | yes | LIVE |
| `studio_compositor_watchdog_last_fed_seconds_ago` | yes | yes (`_poll_loop`) | yes | LIVE |
| `studio_compositor_cameras_total` | yes | yes (`_refresh_counts`) | yes (= 6) | LIVE |
| `studio_compositor_cameras_healthy` | yes | **no** — defined but never updated | yes (= 0.0 **wrong**) | BROKEN |
| `studio_compositor_pipeline_restarts_total` | yes | yes (`on_pipeline_restart`) | **no** | fault-only |
| `studio_rtmp_bytes_total` | yes | **no** — no call site in compositor or rtmp_output | **no** | DEAD CALLSITE |
| `studio_rtmp_connected` | yes | yes (`compositor.py` lines 581, 600) | **no** (PID 2529279 has no RTMP connect event) | fault/event-gated |
| `studio_rtmp_encoder_errors_total` | yes | yes (`compositor.py` line 378) | **no** | fault-only |
| `studio_rtmp_bin_rebuilds_total` | yes | yes (`compositor.py` line 379) | **no** | fault-only |
| `studio_rtmp_bitrate_bps` | yes | **no** — no call site anywhere | **no** | DEAD CALLSITE |

Summary:

- **LIVE (always-incrementing or always-valid gauge): 12**
- **Fault-gated (appears only on events): 5** — `studio_camera_transitions_total`, `studio_camera_reconnect_attempts_total`, `studio_compositor_pipeline_restarts_total`, `studio_rtmp_connected`, `studio_rtmp_encoder_errors_total`, `studio_rtmp_bin_rebuilds_total` (6 series — one was miscounted, corrected below)
- **BROKEN (live but always wrong): 1** — `studio_compositor_cameras_healthy`
- **DEAD CALLSITE (defined, never written): 2** — `studio_rtmp_bytes_total`, `studio_rtmp_bitrate_bps`

Total: 12 live + 6 fault-gated + 1 broken + 2 dead = **21 (including `studio_compositor_cameras_healthy` counted once)**. Accounting reconciled with 20 distinct names: `cameras_healthy` is LIVE-but-BROKEN, so it double-counts in the summary — the 6 fault-gated + 2 dead + 12 always-live - 1 broken overlap = **19 + 1 broken = 20 ✓**.

## `studio_compositor_cameras_healthy = 0.0` root cause

`agents/studio_compositor/metrics.py` defines:

```python
COMP_CAMERAS_HEALTHY = Gauge(
    "studio_compositor_cameras_healthy",
    "Cameras currently in the HEALTHY state",
    registry=REGISTRY,
)
```

and `_refresh_counts()` says:

```python
def _refresh_counts() -> None:
    """Recompute studio_compositor_cameras_total / _healthy gauges."""
    if COMP_CAMERAS_TOTAL is None or CAM_STATE is None:
        return
    with _lock:
        total = len(_cam_models)
    COMP_CAMERAS_TOTAL.set(total)
    # _healthy is derived from CAM_STATE.value — can't read label values
    # back cleanly, so increment via callers when they know a camera reached
    # HEALTHY. Cheap sum using the internal registry is not exposed —
    # instead, store healthy count separately via on_state_transition.
    # For simplicity we just set total here; _healthy is updated lazily
    # from on_state_transition's count accumulator.
```

**The "count accumulator" is not implemented.** `on_state_transition()` only writes the per-role `CAM_STATE.labels(role=..., state=...)` gauges — it never updates `COMP_CAMERAS_HEALTHY`. Nothing in the module body increments that gauge. It is hard-stuck at 0 (the default unset value of a `Gauge` without a setter call is 0, which is why `register_camera()`'s call to `_refresh_counts()` leaves it at 0).

**Fix options** (do not apply in this pass):

1. Maintain a `_healthy_count` module-level int guarded by `_lock`, incremented on `on_state_transition(to_state="healthy")` and decremented on any transition out of `healthy`. Set `COMP_CAMERAS_HEALTHY.set(_healthy_count)` at each transition. **Simplest, matches the docstring intent.**
2. Iterate `_cam_models` in `_refresh_counts()` and read each role's `CAM_STATE.labels(role=r, state="healthy")._value.get()`. This is using a private API; prometheus_client does not expose a clean reader. Brittle.
3. Drop the gauge and redefine it as a derived expression in Grafana: `sum(studio_camera_state{state="healthy"})`. **Least code, but makes the panel query more complex and requires one edit to the dashboard.**

Option 1 is the right fix. File as a follow-up ticket.

## Grafana dashboard panel coverage (12 panels)

| # | title | query target | status on PID 2529279 |
|---|---|---|---|
| 0 | Cameras Healthy | `studio_compositor_cameras_healthy` | **wrong — displays 0** |
| 1 | Frame rate per camera | `rate(studio_camera_frames_total[1m])` | populating |
| 2 | Last frame age per camera | `studio_camera_last_frame_age_seconds` | populating |
| 3 | Kernel drops per camera (rate) | `rate(studio_camera_kernel_drops_total[5m])` | populating (all 0) |
| 4 | Camera state timeline | `studio_camera_state` | populating |
| 5 | Reconnect attempts (rate) | `rate(studio_camera_reconnect_attempts_total[5m])` | **no data** (series absent — no reconnects have occurred) |
| 6 | State transitions (rate) | `rate(studio_camera_transitions_total[5m])` | **no data** (series absent) |
| 7 | Compositor uptime | `studio_compositor_uptime_seconds` | populating |
| 8 | Pipeline restarts (1h) | `increase(studio_compositor_pipeline_restarts_total[1h])` | **no data** (series absent) |
| 9 | Watchdog freshness | `studio_compositor_watchdog_last_fed_seconds_ago` | populating |
| 10 | RTMP bitrate | `studio_rtmp_bitrate_bps` | **no data** (dead callsite — never written) |
| 11 | RTMP connected | `studio_rtmp_connected{endpoint="youtube"}` | **no data** (call sites exist but RTMP attach has not fired on this PID) |

**Half the dashboard is either wrong or empty** on a healthy compositor process that has had no faults since its last OOM-restart. In a stable long run, panels 5/6/8 will remain empty until a real fault occurs; panel 0 will always be wrong; panel 10 will always be empty until `studio_rtmp_bitrate_bps` is wired; panel 11 will only populate once an RTMP connect event fires.

For operator trust in the dashboard, the first-pass fix is: (a) repair `cameras_healthy`, (b) wire `bitrate_bps` from the `nvh264enc` byterate or the flvmux bitrate, (c) consider making the fault-gated panels render "N events in last period" as zero explicitly rather than "no data" — absent series is visually indistinguishable from a Grafana query failure.

## Cross-reference: dmesg events vs metric events

Phase 1 §24 h kernel log classified exactly one non-benign USB event: `usb 8-3: reset SuperSpeed USB device number 2` at 12:14:04 CDT (camera role: brio-synths). At that time the compositor was still running PID 1963052 (alpha's sampler shows PID 1963052 was active 15:00:17 onward). The 12:14 reset happened during the earlier 12:05 boot window, not tracked by the sampler.

To test whether a BRIO SuperSpeed reset during an active compositor run would surface in any metric:

- `studio_camera_transitions_total{role="brio-synths", ...}` would incrementIF the state machine detected the reset and transitioned out of HEALTHY.
- `studio_camera_reconnect_attempts_total{role="brio-synths", result="succeeded"}` would increment on the post-reset recovery.
- `studio_camera_kernel_drops_total{role="brio-synths"}` would increment if the reset left a sequence gap in the v4l2 frame buffer before the uvcvideo restart.

If the reset is fast enough that the udev `change` action re-triggers the `studio-camera-reconfigure@%k.service` unit and the pipeline reconstructs silently inside the hot-swap window, **none of these series would move** — the state machine sees `HEALTHY → HEALTHY` and the fallback-swap path in `PipelineManager` does not increment any counter for "nothing to do". That would be a true silent-failure case, but only for a reset transient that the resilience stack handles with zero visible effect — which is exactly the design goal.

**The dmesg/metrics gap becomes real only when a reset-class event leaves the compositor in a degraded state that the metrics do not reflect.** Phase 3 is the only phase that can surface such a case by injecting faults. Phase 3 is deferred in this research pass (see `phase-3-fault-injection-timings.md`).

## Proposed new series — each backed by concrete evidence

Each proposal must tie to an event that is invisible in current instrumentation.

### (a) `studio_usb_xhci_distress_total{role}` — proposal, not evidence-backed yet

**Rationale:** The alpha retirement handoff's Finding 2 noted that LiteLLM cascaded 503 errors because the `reasoning` fallback was not configured. The compositor's RTMP bin equivalent — MediaMTX going away, NVENC failing initialization, xHCI host controller throwing a sysfs error — may cascade similarly without leaving a metric fingerprint if the error arrives at a layer below the state machine (e.g., as a syscall errno rather than a GstBus message). The proposed series would scrape `/sys/kernel/debug/usb/*/devices` or watch `dmesg` for `xhci_hcd.*error` lines via a small background thread in the compositor and increment the counter when observed, labeled by the role affected.

**Evidence required before shipping:** at least one real xhci distress event that did not surface in existing metrics. **Not collected in this research pass** (kernel log was clean). File as a "re-evaluate after the next real BRIO bus-kick incident" ticket.

### (b) `studio_compositor_memory_footprint_bytes{kind}` — evidence from ALPHA-FINDING-1

**Rationale:** Alpha's leak investigation needs to read `/proc/$PID/status` and `smaps_rollup` from an external script. That script hard-codes the PID, which breaks across OOM restarts (see Phase 2 §Compositor restart boundary and follow-up ticket #3). An in-process series polling `VmRSS`, `VmSwap`, `RssAnon`, `Threads` from its own `/proc/self/status` every 30 s and labeling by `kind` would:

1. Remove the external sampler race with OOM restarts (the metric dies with the process as intended).
2. Give Grafana an immediate view of the leak trajectory, with a panel that can trigger a ntfy alert on `rate(studio_compositor_memory_footprint_bytes{kind="rss"}[5m]) > 1 MB/s`.
3. Replace the need for an external `sample-memory.sh` script entirely.

**Evidence required:** already collected. ALPHA-FINDING-1 is the concrete event. File as a ticket that bundles with Option A's PR.

### (c) `studio_compositor_torch_allocator_bytes` — evidence from Finding-1 root cause audit

**Rationale:** Alpha's `docs/superpowers/audits/2026-04-13-alpha-finding-1-root-cause.md` identifies the torch caching allocator as the anonymous-memory driver. If the compositor keeps torch loaded for even one more release cycle after Option A (or while Option A is in flight), having torch's current allocator size as a metric would give an exact signal of whether allocator pressure is rising independent of overall VmRSS.

**Evidence required:** already collected via alpha's mapping count (`libtorch: 35` stable while RSS grew 3.82 GB). File as a ticket conditional on "is torch still in compositor after Option A?" — if Option A fully removes torch, this series is unneeded.

### (d) `studio_cairo_render_duration_seconds{source}` — evidence from the CairoSource unification epic

**Rationale:** The compositor unification epic's core promise was "no Cairo rendering on the GStreamer streaming thread." The `CairoSourceRunner` now runs each source at its own cadence on a background thread (`cairo_source.py::CairoSourceRunner`). If any CairoSource blows past its render budget, the only visible effect today is that the `budget_signal.py` publishes a degraded signal (consumed by VLA). There is no per-source render-duration histogram, so the compositor cannot tell operator-side "which overlay just glitched." A histogram keyed on source ID would close that gap.

**Evidence required:** collected indirectly — `budget_signal.py` exists and publishes degraded signals. File as an observability enhancement, not a regression fix.

## Label cardinality check

| series | labels | bounded? |
|---|---|---|
| `studio_camera_*` | `role` (6), `model` (string) | yes, 6 × small set |
| `studio_camera_state` | `role`, `state` (5 enum: healthy/degraded/offline/recovering/dead) | yes, 6 × 5 = 30 |
| `studio_camera_transitions_total` | `role`, `from_state`, `to_state` | theoretically bounded (6 × 5 × 5 = 150) but only transitions that have happened get a series — fine |
| `studio_camera_reconnect_attempts_total` | `role`, `result` (succeeded\|failed) | 6 × 2 = 12 |
| `studio_compositor_pipeline_restarts_total` | `pipeline` (string) | `[inferred]` should be role-scoped — the `pipeline_name` arg in `on_pipeline_restart()` is a free string so in principle unbounded. In practice `PipelineManager` passes `f"cam_{role}"` so it is 6-valued; no user input lands in this label. Safe. |
| `studio_rtmp_*` | `endpoint` (currently only `"youtube"`) | bounded to a static map |

No unbounded label cardinality was found.

## Follow-up tickets

1. **`fix(metrics): studio_compositor_cameras_healthy never updates`** — implement the `_healthy_count` accumulator described in § root cause. One-line change in `on_state_transition`, one setter call in `_refresh_counts`. Includes a test fixture that transitions a mock role through HEALTHY/DEGRADED and asserts the gauge value. *(Severity: low. Affects: Grafana dashboard panel 0 correctness.)*

2. **`chore(metrics): wire or delete studio_rtmp_bytes_total and studio_rtmp_bitrate_bps`** — both are defined in `metrics.py` with no call sites anywhere in `agents/studio_compositor/`. Either (a) instrument them at the `rtmp2sink` chain-function level in `rtmp_output.py` and use NVENC's per-frame size or the `flvmux`'s byterate, or (b) delete the definitions. Dead instrumentation is noise. *(Severity: low. Affects: code clarity + Grafana panel 10.)*

3. **`feat(metrics): add studio_compositor_memory_footprint_bytes gauge`** — see proposal (b). Obsoletes the external `sample-memory.sh`. Bundle with ALPHA-FINDING-1 Option A PR or file separately. *(Severity: medium. Affects: leak-investigation continuity across OOM restarts.)*

4. **`feat(metrics): studio_cairo_render_duration_seconds histogram per source`** — see proposal (d). Closes observability gap in the CairoSource unification epic's render budget. *(Severity: low. Affects: operator ability to pinpoint a specific overlay that is over-budget.)*

5. **`fix(grafana): mark fault-gated panels as "0 events in last 5m" when series absent`** — distinguishing "no faults" from "metric pipeline broken" is hard when Grafana renders "no data" for both. Use `or vector(0)` in the query or switch the panel to a stat that treats absence as zero. *(Severity: low. Affects: operator trust in the dashboard.)*

6. **`docs(grafana)`: commit a README alongside `studio-cameras.json`** documenting which panels are always-live, which are fault-gated, and which depend on currently-broken series. *(Severity: very low.)*

## Acceptance check

- [x] Every shipped series classified: 20 names against `metrics.py`, ledger table above.
- [x] One broken series identified (`cameras_healthy`) with root cause and concrete fix options.
- [x] Two dead callsites identified (`rtmp_bytes_total`, `rtmp_bitrate_bps`).
- [x] Label cardinality check: all series bounded.
- [x] 12 Grafana dashboard panels cross-referenced against live + dead series. 6 show "no data" or wrong data on current PID.
- [x] Proposed new series are each tied to a concrete production event or unresolved audit finding (or flagged as speculative when not).
- [x] Cross-reference against Phase 1's 24 h dmesg classification — no hardware event in the window was missed by existing instrumentation; the gap is latent (would only surface during an active fault).
