# Phase 2 — Data-flow silent-failure sweep (beyond static grep)

**Queue item:** 025
**Phase:** 2 of 6
**Date:** 2026-04-13 CDT
**Register:** scientific, neutral (per `feedback_scientific_register.md`)

## Headline

Walking the top daimonion + compositor coroutine call graphs found
**1 CRITICAL** pattern that is worse than BETA-FINDING-K:

- **The daimonion has zero background-task supervision during
  normal operation.** `run_inner.py:135-180` creates 10
  `asyncio.create_task(...)` calls and appends them to
  `daemon._background_tasks`, but `_background_tasks` is only
  `await asyncio.gather(..., return_exceptions=True)`'d in the
  `finally` block of shutdown (line 226-228). **During normal
  operation, if any background task crashes, the exception is held
  inside the Task object and never observed.** The main control
  loop at lines 182-208 runs `while daemon._running: ...` without
  checking `task.done()` or `task.exception()` for any of the 10
  tasks. The daimonion can run as a zombie with a dead
  `CpalRunner.run()` coroutine and no operator-visible alarm.

Plus **8 High + 12 Medium** silent-failure sites in CPAL/compositor
hot paths, table below.

## The Critical finding: unsupervised background tasks

### Location

`agents/hapax_daimonion/run_inner.py`

- Lines 135–180: 10 `asyncio.create_task(...)` calls
- Lines 182–208: main control loop (`while daemon._running`)
- Lines 226–228: `asyncio.gather(..., return_exceptions=True)` — **only in the `finally` block at shutdown**

### The pattern

```python
# run_inner.py:135-180 (simplified)
daemon._background_tasks.append(asyncio.create_task(proactive_delivery_loop(daemon)))
daemon._background_tasks.append(asyncio.create_task(workspace_monitor.run()))
daemon._background_tasks.append(asyncio.create_task(audio_loop(daemon)))
daemon._background_tasks.append(asyncio.create_task(perception_loop(daemon)))
daemon._background_tasks.append(asyncio.create_task(ambient_refresh_loop(daemon)))
daemon._background_tasks.append(asyncio.create_task(daemon._cpal_runner.run()))
daemon._background_tasks.append(asyncio.create_task(_cpal_impingement_loop()))
daemon._background_tasks.append(asyncio.create_task(impingement_consumer_loop(daemon)))
daemon._background_tasks.append(asyncio.create_task(actuation_loop(daemon)))
# ...

# run_inner.py:182-208 — main control loop
try:
    while daemon._running:
        daemon.notifications.prune_expired()
        # wav sweep...
        await asyncio.sleep(1)
        # workspace_monitor analysis...
finally:
    # run_inner.py:226-228 — only here
    for task in daemon._background_tasks:
        task.cancel()
    await asyncio.gather(*daemon._background_tasks, return_exceptions=True)
```

### Why it matters

If `CpalRunner.run()` raises an exception (not
`CancelledError` — an actual bug — let's say Kokoro returns a
malformed tensor and the evaluator panics), the exception is
caught by `cpal/runner.py:156-157` and logged. Then the coroutine
exits via the `finally` block setting `_running = False`. The
enclosing `asyncio.Task` holds the exception result. **Nothing
ever awaits it.** The main loop continues ticking, audio input
continues, perception continues — but voice cognition is dead.

The operator sees:
- daimonion process alive (systemd green)
- CPU usage normal (other loops still running)
- No new "CPAL runner stopped" log lines after the initial one
- A completely silent voice pipeline

The only way to notice this is to grep for "CPAL runner stopped"
in the journal, which no one does.

Phase 4 of queue 024 observed exactly this symptom — *zero TTS log
lines in a 10-minute window* — and concluded the voice pipeline
was "alive but silent." The zombie interpretation was not named
but is the plausible explanation. Queue 024 Phase 4 did not trace
this root cause because it was focused on the voice pipeline, not
the supervision layer.

### Fix proposal

Add a supervisor loop that checks every task in
`daemon._background_tasks` each tick and re-raises or
re-creates on crash:

```python
# In the main loop, after prune_expired():
for task in daemon._background_tasks:
    if task.done() and not task.cancelled():
        exc = task.exception()
        if exc is not None:
            log.exception(
                "background task %s crashed — daemon is now in degraded state",
                task.get_name(),
                exc_info=exc,
            )
            # One of:
            # 1) raise SystemExit to trigger systemd restart (fail-loud)
            # 2) re-create the task with the same coroutine (resilient)
            # 3) increment a counter + continue (observability-only)
            raise SystemExit(1)  # fail-loud is strongest
```

Or use `asyncio.TaskGroup` (Python 3.11+) which automatically
propagates child task exceptions to the parent. TaskGroup requires
restructuring the main loop but gives the desired behavior for
free.

**Severity:** CRITICAL — this is the "silent zombie" failure mode
for the entire daimonion. Every unsupervised task is a silent
failure surface. The blast radius is the full voice pipeline.

**Effort:** ~30 lines for the supervisor loop variant;
`TaskGroup` restructure is ~100 lines but cleaner.

## High severity (8 sites)

### H1. CPAL `run()` on `_tick` exception silently stops the cognitive loop

`cpal/runner.py:134-160`:

```python
try:
    while self._running:
        await self._tick(dt)
        self._tick_count += 1
        ...
except asyncio.CancelledError:
    log.info("CPAL runner cancelled")
except Exception:
    log.exception("CPAL runner error")
finally:
    self._running = False
    log.info("CPAL runner stopped after %d ticks", self._tick_count)
```

On exception: logs, sets `_running = False`, exits the coroutine.
The task completes (exception captured in the Task object). The
main loop is now dead — no tick, no gain updates, no utterance
processing, no impingement surfacing. The daimonion continues but
voice is gone.

**This is the Critical finding's concrete propagation path.** Fix
the Critical finding and H1 is automatically addressed.

Axiom: `executive_function` (95) — the system must not silently
stop serving the operator's executive function needs.

### H2. Goodbye TTS failure at DEBUG level

`cpal/runner.py:195-205`:

```python
if d._conversation_pipeline and d._conversation_pipeline._audio_output:
    try:
        loop = asyncio.get_running_loop()
        pcm = await loop.run_in_executor(
            None, d.tts.synthesize, msg, "conversation"
        )
        if pcm:
            await loop.run_in_executor(
                None, d._conversation_pipeline._audio_output.write, pcm
            )
    except Exception:
        log.debug("Goodbye TTS failed", exc_info=True)
```

Goodbye message on session end is a user-experience feature. If
Kokoro fails, DEBUG-level swallow. No counter. Invisible.

Axiom: `executive_function` (95) — degrades the session-end
ritual.

### H3. CPAL `_check_stimmung` bare swallow

`cpal/runner.py:442-448`:

```python
def _check_stimmung(self) -> None:
    try:
        if _STIMMUNG_PATH.exists():
            data = json.loads(_STIMMUNG_PATH.read_text())
            stance = data.get("overall_stance", "nominal")
            self._evaluator.gain_controller.set_stimmung_ceiling(stance)
    except Exception:
        pass
```

Bare `except Exception: pass` — no log, no counter. If the
stimmung file is malformed or unreadable, the gain ceiling stays
at the default (`nominal`). The operator cannot see that the
stimmung integration has failed.

**Axiom link:** PR #756 Phase 6 noted the stimmung layer was designed
to gate voice behavior; if it silently reverts to default, the
axiom-intended behavior modulation is lost without trace.

### H4. CPAL `_publish_state` DEBUG-level swallow

`cpal/runner.py:458-475`:

```python
def _publish_state(self) -> None:
    try:
        gs = self._grounding.snapshot()
        result = self._evaluator._control_law.evaluate(...)
        publish_cpal_state(...)
    except Exception:
        log.debug("CPAL state publish failed", exc_info=True)
```

CPAL state is a published SHM signal consumed by the compositor
(PR #756 Phase 3 budget_signal finding). If the publish fails, the
compositor's view of CPAL state goes stale silently.

### H5. CPAL `generate_spontaneous_speech` DEBUG-level swallow

`cpal/runner.py:500-503`:

```python
if self._pipeline is not None and hasattr(
    self._pipeline, "generate_spontaneous_speech"
):
    try:
        await self._pipeline.generate_spontaneous_speech(impingement)
    except Exception:
        log.debug("Spontaneous speech failed", exc_info=True)
```

If spontaneous speech on impingement surfacing fails, DEBUG-level
swallow. The impingement is lost without trace. Over time, if a
systematic bug breaks spontaneous speech, the operator sees
"CPAL: impingement surfacing: X" logs but never hears the system
speak.

### H6. Compositor RTMP bus error metric increment bare swallow

`compositor.py:382-383`:

```python
try:
    from . import metrics
    metrics.RTMP_ENCODER_ERRORS_TOTAL.labels(endpoint="youtube").inc()
    metrics.RTMP_BIN_REBUILDS_TOTAL.labels(endpoint="youtube").inc()
except Exception:
    pass
```

Bare swallow on metric increment. If the metrics module import
fails or the Counter is not registered, RTMP error counts are lost.
Pair with Phase 2 of queue 024 (FINDING-H) which showed the
compositor is not even scraped by Prometheus — this swallow is a
second layer of "the RTMP error story is invisible."

### H7. Compositor `start_layout_only` layout persistence catch

`compositor.py:525-529`:

```python
except Exception:
    log.exception(
        "failed to start layout persistence threads — "
        "compositor continues without auto-save or hot-reload"
    )
```

Loud (uses `log.exception`) but still silently continues. The
compositor runs without auto-save — operator edits to layouts are
lost on next restart. The log message is informative but there is
no operator alarm.

### H8. Compositor `start_layout_only` command server catch

`compositor.py:555-559`:

```python
except Exception:
    log.exception(
        "failed to start compositor command server — "
        "runtime layout mutation via window.__logos / MCP is unavailable"
    )
```

Same pattern as H7. The compositor continues without runtime
layout mutation. `window.__logos.execute("terrain.focus",...)`
silently stops working. No gauge, no counter.

Axiom: `executive_function` (95) — runtime control via MCP/voice
is an executive-function affordance; silent degradation means the
operator cannot reach the compositor from their preferred UI.

## Medium severity (12 sites)

### M1. CPAL `_apply_gain_drivers` presence read bare swallow

`cpal/runner.py:332-340`:

```python
try:
    presence_path = Path("/dev/shm/hapax-perception/state.json")
    if presence_path.exists():
        state = json.loads(presence_path.read_text())
        presence = state.get("presence_score", "likely_absent")
        if presence == "likely_present" and gc.gain < 0.1:
            gc.apply(GainUpdate(delta=0.01, source="presence"))
except Exception:
    pass
```

Bare swallow. If the perception SHM file is malformed, the
presence gain driver silently becomes a no-op.

### M2. CPAL `_signal_tpn` OSError swallow

`cpal/runner.py:452-456`:

```python
try:
    _TPN_PATH.parent.mkdir(parents=True, exist_ok=True)
    _TPN_PATH.write_text("1" if active else "0", encoding="utf-8")
except OSError:
    pass
```

TPN signal write failure is silent. DMN anti-correlation degrades.

### M3. CPAL acknowledgment signal cache miss

`cpal/runner.py:370-383`: no explicit silent failure, but if
`ack = self._signal_cache.select("acknowledgment")` returns `None`
(cache empty or the selector finds nothing), the T1 signal is
silently skipped. No log, no counter.

### M4. `process_impingement` gain update skipped when effect is None

`cpal/runner.py:486-487`: `if effect.gain_update is not None:
self._evaluator.gain_controller.apply(effect.gain_update)` —
silently skips the gain update when None. Normally this is
correct (None means "no update") but there's no telemetry
confirming the adapter is producing updates at the expected rate.

### M5–M12. Compositor silent swallows at lines 351, 400, 483, 525, 555, 574, 580, 586, 626, 645

Per `grep "except Exception" compositor.py`:

| line | context | catch behavior |
|---|---|---|
| 351 | ntfy on camera transition | `log.exception` — loud |
| 382 | metric increment (H6) | `pass` — silent |
| 400 | FX source fallback after error | `log.exception` — loud, but continues |
| 483 | source backend construct failure | `log.exception` + `continue` — loud, non-fatal |
| 525 | layout persistence start (H7) | `log.exception` — loud but silent-degraded |
| 555 | command server start (H8) | `log.exception` — loud but silent-degraded |
| 574 | CommandServer.stop | `log.exception` — loud |
| 580 | LayoutFileWatcher.stop | `log.exception` — loud |
| 586 | LayoutAutoSaver.stop | `log.exception` — loud |
| 626 | rtmp attach side-effects | `log.exception` + "non-fatal" note |
| 645 | (rtmp detach side-effects, similar) | (similar) |

**Most compositor catches are at `log.exception` level**, which is
loud at the log stream level but still silent to the operator
unless they're actively tailing the journal. For the ones that
cause degraded-but-running states (H7, H8, 626, 645), add a
Prometheus gauge so the degradation is dashboard-visible.

## Classified table (Phase 2 target format)

| # | site | severity | axiom | operator symptom | fix class |
|---|---|---|---|---|---|
| C1 | `run_inner.py:135-228` — unsupervised background tasks | **Critical** | executive_function (95) | voice pipeline silently dies, daemon appears alive | **let it crash + supervise** (TaskGroup or supervisor loop) |
| H1 | `cpal/runner.py:156` — `run()` on `_tick` exception | High | executive_function (95) | CPAL loop stops, no restart | propagates from C1 fix |
| H2 | `cpal/runner.py:204` — goodbye TTS DEBUG swallow | High | executive_function (95) | no goodbye audio at session end | **structured error** — warning + counter |
| H3 | `cpal/runner.py:447` — stimmung bare swallow | High | management_governance (85) | gain ceiling stays at nominal | **structured error** — warning + counter |
| H4 | `cpal/runner.py:474` — publish_state DEBUG swallow | High | executive_function (95) | compositor's CPAL view goes stale | **structured error** |
| H5 | `cpal/runner.py:502` — spontaneous speech DEBUG swallow | High | executive_function (95) | impingements surfaced but not spoken | **structured error** + retry |
| H6 | `compositor.py:382` — RTMP metric bare swallow | High | executive_function (95) | RTMP error counts lost | **structured error** — explicit catch |
| H7 | `compositor.py:525` — layout persistence fail | High | executive_function (95) | edits lost on restart | **fail closed** — refuse to start |
| H8 | `compositor.py:555` — command server fail | High | executive_function (95) | MCP/voice cannot control compositor | **fail closed** OR **structured error** with gauge |
| M1 | `cpal/runner.py:339` — presence read bare swallow | Medium | executive_function (95) | presence gain driver dead | **structured error** |
| M2 | `cpal/runner.py:455` — TPN write OSError | Medium | - | DMN anti-correlation degraded | **structured error** |
| M3 | `cpal/runner.py:374` — signal cache miss | Medium | executive_function (95) | acknowledgment skipped | **structured error** + counter |
| M4 | `cpal/runner.py:486` — impingement None gain update | Medium | - | adapter health invisible | **observability only** — counter |
| M5 | `compositor.py:351` | Medium (loud) | - | - | already loud |
| M6 | `compositor.py:400` | Medium (loud-but-continues) | executive_function | FX fallback invisible | **observability** — counter |
| M7 | `compositor.py:483` | Medium (loud-but-continues) | - | source drops silently | **structured error** |
| M8 | `compositor.py:626` | Medium (loud-but-noted-non-fatal) | - | rtmp side effects invisible | **observability** |
| M9 | `compositor.py:645` | Medium | - | similar | similar |
| M10 | `compositor.py:574-586` | Medium (loud) | - | stop path already loud | fine as is |

**20 sites total.** 1 Critical + 8 High + 11 Medium.

## Top-5 fix proposals

1. **C1 — background task supervisor** [run_inner.py] — restructure to
   `asyncio.TaskGroup` OR add a supervisor loop that checks
   `task.done() + task.exception()` every tick and raises
   `SystemExit(1)` to trigger systemd restart. Blast radius =
   full voice pipeline + cognitive loop. Single biggest fix in
   the backlog.
2. **H1 — CPAL run() exception supervision** — propagates from C1.
   If the supervisor catches the crash, it can log with details
   and trigger a daemon restart or re-create the runner.
3. **H3 — stimmung bare swallow** — stimmung is the axiom-aware
   gain ceiling. Silent degradation means axiom-intended behavior
   modulation is off without trace. Log warning + counter.
4. **H6 — compositor RTMP metric catch** — the metric increment
   itself should never fail if the metrics module is imported
   once at startup. The `try/except: pass` is defensive-
   programming-over-defensive-programming. Remove the try/except,
   rely on the import succeeding at module load time.
5. **H7 + H8 — compositor layout persistence + command server** —
   these should fail-closed. A compositor without auto-save or
   MCP control is a degraded compositor masquerading as a healthy
   one. Better to crash and restart.

## Backlog additions (for retirement handoff)

96. **`feat(daimonion): background task supervisor`** [Phase 2 C1] — CRITICAL. Restructure run_inner.py to TaskGroup or add supervisor loop. Biggest single fix in the round-4 backlog.
97. **`fix(cpal): goodbye TTS catch to WARNING + counter`** [Phase 2 H2] — `hapax_session_goodbye_failures_total`.
98. **`fix(cpal): stimmung bare swallow to WARNING + counter`** [Phase 2 H3] — `hapax_stimmung_read_failures_total`. Pair with a gauge for the currently-applied ceiling.
99. **`fix(cpal): publish_state DEBUG to WARNING + counter`** [Phase 2 H4] — `hapax_cpal_state_publish_failures_total`.
100. **`fix(cpal): spontaneous speech DEBUG to WARNING + counter`** [Phase 2 H5] — `hapax_spontaneous_speech_failures_total`.
101. **`fix(compositor): RTMP metric swallow removed`** [Phase 2 H6] — delete the try/except/pass around metric increments; rely on import-time validation.
102. **`fix(compositor): layout persistence start fail-closed`** [Phase 2 H7] — refuse to start if LayoutAutoSaver or LayoutFileWatcher raises.
103. **`fix(compositor): command server start fail-closed OR counter`** [Phase 2 H8] — either raise or expose `studio_command_server_state` gauge.
104. **`fix(cpal): presence read bare swallow to WARNING`** [Phase 2 M1] — `hapax_presence_read_failures_total`.
105. **`fix(cpal): signal cache miss counter`** [Phase 2 M3] — `hapax_signal_cache_miss_total{signal_type}`.
106. **`feat(cpal): impingement gain update counter`** [Phase 2 M4] — `hapax_impingement_gain_updates_total{result="applied"|"skipped"}`.
107. **`research: apply this audit pattern to the reverie/imagination side`** [Phase 2 extension] — Phase 2 covered daimonion + compositor. The Rust imagination daemon and the reverie mixer have their own async call graphs that should get the same treatment.
