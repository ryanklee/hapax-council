# BudgetTracker wiring audit + FD leak incident + circular import + oversized text bug

**Date:** 2026-04-14
**Author:** delta (beta role — cam-stability focus)
**Scope:** Audit of the `BudgetTracker` call-site graph
from drop #1 era (pre-compaction Phase 10 PR #2).
Combined with a live incident retrospective — the
compositor was in `start-limit-hit` for ~10 minutes
when this audit started, caused by an fd leak that
had been building for ~2 hours. Five distinct bugs
surfaced. This drop is a compound finding report.
**Register:** scientific, neutral
**Status:** investigation — 5 findings, 1 live
incident resolved (compositor reset + restart), code
changes pending
**Companion:** drop #1 (BudgetTracker discovery,
pre-compaction), drop #33 (HLS race incident), drop
#36 (threading model), drop #39 (cairooverlay
streaming-thread cost)

## Headline

**Five stacked bugs in the compositor's
orchestration + observability layer**, discovered in
sequence while auditing the BudgetTracker call-site
graph:

1. **Layout-declared Cairo sources are NEVER
   STARTED.** `SourceRegistry.construct_backend`
   creates a `CairoSourceRunner` for each cairo
   source in `config/compositor-layouts/default.json`
   (token_pole, album, stream_overlay, sierpinski,
   reverie) and calls `register()`. But **nothing
   calls `.start()` on the registered backends.**
   Only the two legacy facades
   (`OverlayZoneManager` and `SierpinskiRenderer`)
   call `.start()` on their own internal runners.
   The four layout-declared cairo sources are
   constructed, registered, memory-resident — and
   dead. Their background render threads never run,
   their `get_current_surface()` always returns
   `None`, and `pip_draw_from_layout` silently
   skips them (`if src is None: continue`).
2. **Circular import** between
   `agents/studio_compositor/budget.py` and
   `agents/studio_compositor/budget_signal.py`.
   Logged as WARNING on every compositor startup:
   ```
   ImportError: cannot import name 'atomic_write_json'
   from partially initialized module 'agents.studio_compositor.budget'
   (most likely due to a circular import)
   ```
   The force-import of freshness gauges from
   `metrics.py` fails silently, and
   `compositor_publish_*` series is not registered
   on the expected path.
3. **`BudgetTracker.over_budget()` skip path is
   dead code.** `budget_ms` is not passed by any
   caller. `CairoSourceRunner._render_one_frame`'s
   skip-if-previous-was-over-budget check is
   structurally dead because
   `self._budget_ms is None` is always true.
4. **Nobody reads the degraded signal file.**
   `/dev/shm/hapax-compositor/degraded.json` is
   written every 1000 ms by
   `publish_degraded_signal`, but **no process in
   `agents/`, `logos/`, or `shared/` reads it.**
   The compositor → stimmung dimension pipeline
   connection promised in the docstring does not
   exist.
5. **FD leak + `GLib-ERROR: Creating pipes for
   GWakeup: Too many open files`** — the incident.
   The compositor core-dumped at 14:02:57 and again
   at 14:42:11 and 14:44:11 with OSErrors from
   routine file writes all hitting `[Errno 24] Too
   many open files`. GLib's internal wakeup pipe
   creation hit the same limit and aborted the
   process. systemd hit `start-limit-hit` after 5
   restart attempts. Compositor was down for
   ~10 minutes until `reset-failed && restart`.

## 1. Live incident (finding 5)

### 1.1 Timeline

- **14:02:57** — First core dump. Multiple OSError
  `[Errno 24] Too many open files` from
  `_write_status`, `_notify_camera_transition`,
  snapshot writes. GLib wakeup pipe failure aborted
  the process.
- **14:03:51** — systemd restarted the service.
- **14:40:05** — HLS sink began logging "Too many
  open files" errors for segment files. Drop #33's
  hls-sink error scope handled these as non-fatal —
  the compositor kept running, but fd pressure was
  building.
- **14:42:11** — Second core dump.
- **14:44:11** — Third core dump.
- **14:44:32+** — Restart attempts; multiple
  failures: circular import warning, cairo surface
  overflow from `~/.../track-lyrics.txt` (222,617
  characters → 141,162 pixel surface height → cairo
  error), c920-overhead bandwidth exhaustion.
- **14:46:05** — `start-limit-hit` reached. systemd
  stopped retrying.
- **14:55:00** (this session) — `reset-failed +
  restart`. Compositor back up, 5/6 cameras healthy.

### 1.2 Root cause: fd leak

The fd limit was reached while calling routine file
operations. Every restart clears the fd table, so
the problem is a slow leak in the long-running
process, not a one-shot.

**Suspected sources** (unverified without a live
process to inspect):

- **HLS sink or archive rotator** — the HLS branch
  writes segment files, and the archive rotator
  moves them. If either keeps an fd open past the
  file's lifecycle (drop #33's race), fds
  accumulate.
- **Per-camera snapshot writes** — `cameras.py:62`
  and `snapshots.py:51`, `snapshots.py:175` use
  `os.open` + `os.close` explicitly. If any
  exception path between open and close leaves the
  fd leaked, this would leak — but the code uses
  try/finally correctly. Probably not the leaker.
- **Python logging handler fd recycling** — some
  logging configs open a new fd per log record. If
  a custom handler is misconfigured, this leaks.
- **GStreamer internal fds** — each pipeline rebuild
  (camera producer restart, fallback swap,
  interpipesrc renegotiation) allocates GL context
  fds, UDS, eventfd. If any leaks on rebuild, a
  process that churns through many rebuilds
  (drops #27, #37) accumulates them.

### 1.3 Immediate workaround

**Add `LimitNOFILE=65536` to the systemd unit.**
The default for systemd user services is typically
1024-4096. Bumping to 64k buys time for the leak to
be tracked down without taking the compositor down.

```ini
# systemd/user/studio-compositor.service.d/limit-nofile.conf
[Service]
LimitNOFILE=65536
```

One-file drop-in. No code change. Zero risk.

### 1.4 Root-cause investigation needed

To actually find the leaker: take a `ls /proc/<pid>/fd`
census every 30 seconds for 30 minutes. Diff the set.
The growing file names will point at the leaker.

**Proposed observability gap closer**: add a
compositor metric `compositor_process_fd_count` that
reads `/proc/self/fd` count every status tick (5s
cadence). A rising count over time becomes
alertable.

## 2. BudgetTracker wiring audit (findings 1-4)

### 2.1 Finding 1 — layout-declared Cairo sources
never started

**Evidence trail:**

- `compositor.py:296` — `self._budget_tracker = BudgetTracker()`
- `compositor.py:297` — `self._overlay_zone_manager = OverlayZoneManager(budget_tracker=self._budget_tracker)`
- `compositor.py:526` — `backend = registry.construct_backend(source, budget_tracker=self._budget_tracker)` for each layout source
- `compositor.py:535` — `registry.register(source.id, backend)`
- **No `backend.start()` call anywhere in `compositor.py` or `lifecycle.py`.**

Live `costs.json` snapshot at 2026-04-14 ~14:45:

```json
{
  "sources": {
    "sierpinski-lines": {
      "source_id": "sierpinski-lines",
      "sample_count": 120,
      "last_ms": 27.893,
      "avg_ms": 34.009,
      "p95_ms": 65.575,
      "skip_count": 0
    },
    "overlay-zones": {
      "source_id": "overlay-zones",
      "sample_count": 120,
      "last_ms": 3.104,
      "avg_ms": 2.726,
      "p95_ms": 6.411,
      "skip_count": 0
    }
  }
}
```

**Only two sources recorded**: `sierpinski-lines`
and `overlay-zones`. These are the two legacy
facades' internal runners. The layout config
declares 5 sources (token_pole, album, stream_overlay,
sierpinski, reverie) — none of them appear.

`grep` confirms only two `.start()` call sites for
runners in the entire tree:

```text
agents/studio_compositor/overlay_zones.py:388:        self._runner.start()
agents/studio_compositor/sierpinski_renderer.py:363:        self._runner.start()
```

Neither of these is the SourceRegistry backend.

**Impact:**

- **Layout-declared cairo sources never render.**
  `token_pole`, `album`, `stream_overlay` are not
  visible in the livestream output via the intended
  `pip_draw_from_layout` path.
- **Drop #39 finding on pip_draw_from_layout was
  wrong.** I assumed 3-5 PiP blits per frame; the
  actual number is **zero** because every
  `source_registry.get_current_surface()` returns
  `None`.
- **The fx_chain post-fx `pip_overlay` cairooverlay
  is doing no useful work.** It runs `_pip_draw →
  pip_draw_from_layout`, which walks the layout and
  finds no surfaces. The cairooverlay callback still
  runs per frame on the streaming thread, but emits
  no blits.
- **Legacy Sierpinski renders via a different path.**
  The Sierpinski content visible in the livestream
  comes from `SierpinskiRenderer` (the legacy facade
  instantiated in `fx_chain.py:445`) → `on_draw` on
  the BASE path cairooverlay, not from the layout's
  `sierpinski` source entry.

**This is the single largest wiring gap in the
compositor's control plane.** Phase 9 Task 29 of
the compositor unification epic removed the legacy
facades' draw calls but never wired the replacement
path to start.

**Fix** (Ring 1): add a `start_all()` method to
`SourceRegistry` that iterates `_backends` and calls
`.start()` on any backend that has one. Call it
from `start_layout_only` after all registrations
complete. ~15 lines total.

```python
# source_registry.py
def start_all(self) -> None:
    """Start any registered backend that has a start() method.

    Layout-declared cairo sources need their background render
    threads started after registration; previously only the legacy
    facades (OverlayZoneManager, SierpinskiRenderer) started their
    runners, leaving layout-declared runners dead.
    """
    for source_id, backend in self._backends.items():
        if hasattr(backend, "start"):
            try:
                backend.start()
                log.info("SourceRegistry.start_all: started %s", source_id)
            except Exception:
                log.exception(
                    "SourceRegistry.start_all: failed to start %s", source_id
                )
```

```python
# compositor.py: at end of start_layout_only
self.source_registry.start_all()
```

### 2.2 Finding 2 — circular import

`metrics.py` → `budget_signal.py` → `budget.py` →
(circular) → `budget.py:atomic_write_json` not yet
defined at the time of the backwards import.

Full traceback from the live log:

```text
File "agents/studio_compositor/metrics.py", line 469, in <module>
    from agents.studio_compositor import (
  File "agents/studio_compositor/budget_signal.py", line 56, in <module>
    from agents.studio_compositor.budget import atomic_write_json
ImportError: cannot import name 'atomic_write_json' from partially initialized module
'agents.studio_compositor.budget' (most likely due to a circular import)
```

**Impact**: the force-import of freshness gauges
from `metrics.py` fails silently. The gauges for
`compositor_publish_costs_*` and
`compositor_publish_degraded_*` are NOT registered
on the compositor's custom `REGISTRY` via the
expected path.

Looking at live metrics, those series **do** appear
in the output, which means there's a secondary
registration path that succeeds (likely the lazy
path inside `budget.py` itself at import time). The
warning is non-fatal but cosmetically confusing.

**Fix** (Ring 1): break the cycle. `atomic_write_json`
could live in a small helper module
(`agents/studio_compositor/atomic_io.py`) imported
by both `budget.py` and `budget_signal.py`. ~15
lines.

### 2.3 Finding 3 — `budget_ms` parameter is dead

**Evidence**: grep for `budget_ms=` in call sites
returns zero non-definition matches. No caller passes
a value.

`CairoSourceRunner._render_one_frame` (cairo_source.py:379-400):

```python
if (
    self._budget_ms is not None
    and self._budget_tracker is not None
    and self._budget_tracker.over_budget(self._source_id, self._budget_ms)
):
    self._budget_tracker.record_skip(self._source_id)
    self._consecutive_skips += 1
    # ...
    return
```

**`self._budget_ms is not None` is always False** at
runtime, so this entire code path is dead. Skip
counts are always 0, which the live `degraded.json`
confirms:

```json
{
  "total_skip_count": 0,
  "degraded_source_count": 0,
  ...
  "worst_source": null
}
```

**Impact**: even if finding 1 were fixed and all
layout sources were started, none of them would be
skipped when over budget. The skip path needs a
budget value from somewhere. Per-source `budget_ms`
could come from the layout config
(`source.params.budget_ms`), from a central default,
or from the layout's overall `layout_budget_ms`
divided across sources.

**Fix** (Ring 2): add `budget_ms` parameter to the
layout schema's `SourceSchema.params`, read it in
`source_registry.construct_backend`, pass it to
`CairoSourceRunner`. ~10 lines.

### 2.4 Finding 4 — degraded.json is write-only

**Evidence trail**: `grep -rn 'compositor-degraded\|degraded\.json'`
across `agents/`, `logos/`, and `shared/` yields
zero non-compositor results. Only the compositor
writes it; no downstream process reads it.

**Impact**: the compositor → stimmung dimension
pipeline connection promised in
`budget_signal.py:4-5` docstring does not exist.
Per-source skip signal is observable via Prometheus
freshness gauge but has no closed-loop control
effect anywhere.

**Fix** (Ring 2 or Ring 3): either wire a reader
into VLA (`agents/visual_layer_aggregator/`) that
maps `per_source.skip_count` to a stimmung dimension
reading, OR document the signal as "Prometheus-only,
no file reader" and remove `publish_degraded_signal`
+ the `/dev/shm` write.

**Recommendation**: the Prometheus gauge is the
right observability surface. The
`/dev/shm/.../degraded.json` path was the original
intent but never found its consumer. **Remove the
file write** and keep only the Prometheus gauge.
Saves one atomic write per second and one
background maintenance obligation.

## 3. Ring summary

### Ring 1 — drop-everything (live compositor
stability)

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **BT-1** | `SourceRegistry.start_all()` + call from `start_layout_only` | `source_registry.py` + `compositor.py` | ~15 | **Layout-declared cairo sources actually render.** Biggest wiring gap closed. |
| **BT-2** | Break `budget.py ↔ budget_signal.py` circular import | new `atomic_io.py` | ~15 | Startup warning eliminated; clean import graph |
| **BT-3** | `LimitNOFILE=65536` drop-in for the systemd unit | `systemd/user/studio-compositor.service.d/limit-nofile.conf` | 3 | Buys time for fd leak to be tracked; prevents next outage |

**Risk profile**: BT-1 has medium risk. It starts
background threads that have been dormant — if any
of the layout sources has a latent bug in its
render function, the bug surfaces now. The
`try/except` in `CairoSourceRunner._render_one_frame`
catches and logs per-tick exceptions so a bad source
shouldn't crash the process, but a SLOW source
would surface immediately as an increased
`compositor_source_frame_*_age_seconds` metric.

### Ring 2 — observability + wiring

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **BT-4** | `budget_ms` parameter in layout schema + pass-through | `compositor_model.py`, `source_registry.py`, call sites | ~20 | Dead code path finding 3 becomes live; over-budget sources actually skip |
| **BT-5** | `compositor_process_fd_count` gauge read from `/proc/self/fd` | `metrics.py` + `_status_tick` | ~10 | Future fd leak becomes scrape-visible, alertable |
| **BT-6** | Remove `publish_degraded_signal` file write (keep Prometheus freshness gauge) | `budget_signal.py`, `lifecycle.py` | ~15 | Eliminates dead-path orphaned file |

### Ring 3 — root cause

| # | Fix | Action | Notes |
|---|---|---|---|
| **BT-7** | Track down the fd leak | `/proc/<pid>/fd` census + diff | ~30 min investigation on a live compositor |
| **BT-8** | Clamp `render_text_to_surface` input size | `text_render.py` | Reject text > 100k chars or surfaces > 16k pixels, log and skip |

## 4. Cross-drop impact

The compositor crashed **three times in 4 minutes**
today due to the compound effect of:

- fd leak (finding 5) eating file descriptors over
  hours
- Oversized text content triggering cairo surface
  overflow (BT-8)
- c920-overhead USB bandwidth issue (drop #34 / #38)
  contributing state churn

**Ring 1 BT-3 alone would have prevented the outage**
by giving the compositor 64× more fd headroom.

**Ring 1 BT-1 is orthogonal to the outage** but is
the biggest wiring gap in the entire compositor
control plane. Shipping it alone restores the PiP
content (token_pole, album, stream_overlay, reverie)
that the operator has been missing since Phase 9
Task 29 removed the legacy facades without wiring
the replacement.

## 5. Cross-references

- `agents/studio_compositor/compositor.py:294-297` —
  BudgetTracker instantiation
- `agents/studio_compositor/compositor.py:505-568` —
  `start_layout_only` (where `start_all()` is
  missing)
- `agents/studio_compositor/source_registry.py:72-132`
  — `construct_backend`
- `agents/studio_compositor/budget.py` — tracker +
  publish_costs (note: circular with budget_signal)
- `agents/studio_compositor/budget_signal.py` —
  degraded signal publisher (orphaned)
- `agents/studio_compositor/cairo_source.py:379-400`
  — dead `over_budget` skip path
- `agents/studio_compositor/lifecycle.py:214` — 1 Hz
  budget publish timer
- Live `costs.json` at
  `/dev/shm/hapax-compositor/costs.json`
- Live `degraded.json` at
  `/dev/shm/hapax-compositor/degraded.json`
  (write-only, no consumer)
- Journal incident sequence:
  `journalctl --user -u studio-compositor.service
  --since "2026-04-14 14:00:00" --until
  "2026-04-14 14:50:00"`
- Drop #1 (pre-compaction) — BudgetTracker discovery
- Drop #33 — HLS race + start-pre hang incident
- Drop #36 — compositor threading model
- Drop #39 — cairooverlay streaming-thread cost
  (now partially revised: pip_draw is doing no real
  work today)

## 6. Open questions for operator

1. **Is the PiP content (token_pole, album, chat
   stats) currently visible in the livestream
   output?** If no, this drop's Ring 1 BT-1 is the
   fix. If yes, there's another rendering path I
   haven't found and the wiring gap is less severe
   than finding 1 suggests.
2. **What typical output does the operator see when
   streaming?** A visual check of the livestream
   during normal operation would resolve finding 1
   in 30 seconds.
3. **Is the `track-lyrics.txt` write path a legacy
   music player integration that's been left
   configured?** Nothing in the current tree writes
   that file. It may be safe to remove the zone
   config, OR clamp the input size (BT-8) as a
   defensive fix.
