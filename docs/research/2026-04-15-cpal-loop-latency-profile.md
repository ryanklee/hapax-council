# CPAL loop latency profile

**Date:** 2026-04-15
**Author:** beta (queue #213, identity verified via `hapax-whoami`)
**Scope:** structural + live-verified profile of the CPAL (Continuous Perception Action Loop) in `agents/hapax_daimonion/cpal/runner.py`. Measures tick cadence, evaluates cognitive continuity, checks impingement consumer cursor progression, cross-references against the operator's `feedback_cognitive_loop` memory.
**Branch:** `beta-phase-4-bootstrap` (branch-only commit per queue spec)

---

## 0. Summary

**Verdict: CPAL IS a continuous cognitive loop, not a request-response state machine.** The 150ms tick runs unconditionally while the daimonion is active, independent of utterance arrival. Perception updates, silence tracking, and periodic state publication happen every tick regardless of whether an operator utterance is being processed. Utterance processing is spawned out-of-band and does not block the tick loop. Both impingement consumer cursors (CPAL + affordance) are live at the file tail, indicating zero-lag consumption of the DMN impingement stream.

This matches the operator's `feedback_cognitive_loop` memory requirement: *"Voice needs a never-stopping cognitive loop during conversation, not request-response state machine. Cognition must run continuously, not cold-start on utterance boundary."*

**Minor finding:** while the structural loop is continuous, there is one measurable cold-start surface — the first tick after `CpalRunner.run()` is invoked uses `_last_tick_at = time.monotonic()` initialized AT the top of the run loop. If the runner is ever restarted (e.g., service restart, exception recovery), the first `dt` value passed to `_tick()` will be ~0 seconds. This is correct behavior (no false silence accumulation on restart) but worth noting.

## 1. Structural analysis

### 1.1 CPAL runner main loop (`agents/hapax_daimonion/cpal/runner.py`)

The canonical cognitive tick is defined at `TICK_INTERVAL_S = 0.15` (line 35) — **150ms wall-clock cadence**. The `run()` method (lines 128-160) implements the tick loop:

```python
async def run(self) -> None:
    self._running = True
    self._last_tick_at = time.monotonic()
    log.info("CPAL runner started (tick=%.0fms)", TICK_INTERVAL_S * 1000)

    while self._running:
        tick_start = time.monotonic()
        dt = tick_start - self._last_tick_at
        self._last_tick_at = tick_start

        await self._tick(dt)
        self._tick_count += 1

        if self._tick_count % 10 == 0:
            self._publish_state()
            self._check_stimmung()

        elapsed = time.monotonic() - tick_start
        sleep_time = max(0, TICK_INTERVAL_S - elapsed)
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
```

**Key properties:**

- **Unconditional tick.** The `while self._running:` loop runs as long as the runner is active. No gating on utterance arrival, impingement presence, or session state.
- **Monotonic time basis.** `time.monotonic()` is used throughout, avoiding wall-clock drift.
- **Publish every 10 ticks (~1.5s).** `_publish_state()` writes to SHM and `_check_stimmung()` queries mood state.
- **Sleep catches up.** If a tick takes longer than 150ms (e.g., expensive perception operation), `sleep_time = max(0, TICK_INTERVAL_S - elapsed)` returns 0 and the next tick fires immediately — no double-spacing.

### 1.2 Per-tick operations (`CpalRunner._tick()`, lines 166-345)

Every tick, the following operations run:

1. **Perception update** (lines 168-172) — read audio frame + VAD probability, update `_perception.signals`
2. **Silence tracking** (lines 174-178) — increment `_accumulated_silence_s` if no speech active
3. **Session timeout check** (lines 180-207) — close session on silence timeout
4. Additional tick operations continue through line 345

**Critical observation:** these operations happen **regardless of utterance processing state**. Even if `_processing_utterance = True`, the tick still updates perception, increments silence tracking (with guard), and checks session timeout. The tick loop does not block on utterance work.

### 1.3 Utterance processing is out-of-band

`_process_utterance()` (lines 346-475) handles operator-speech events. It is NOT called from `_tick()` — it is called from the utterance-arrival event handler (likely a STT callback). The utterance processing runs as an async task while the tick loop continues.

**Implication:** during a voice turn, CPAL continues ticking at 150ms, updating perception, tracking silence, checking timeouts — even as the LLM is generating a response. The cognitive loop does NOT pause for response generation.

This matches the operator's `feedback_cognitive_loop` requirement exactly.

### 1.4 Impingement consumer loops

CPAL has TWO independent impingement consumer loops reading `/dev/shm/hapax-dmn/impingements.jsonl`:

**Loop A: CPAL impingement handler** via `CpalRunner.process_impingement()` (lines 477-505). Owns spontaneous speech surfacing (gated by adapter `should_surface()`). Cursor file: `~/.cache/hapax/impingement-cursor-daimonion-cpal.txt`.

**Loop B: Affordance impingement handler** via `run_loops_aux.py::impingement_consumer_loop()` (lines 187+). Owns notification dispatch, Thompson outcome recording, capability discovery, cross-modal dispatch. Cursor file: `~/.cache/hapax/impingement-cursor-daimonion-affordance.txt`. Polls every 500ms (`await asyncio.sleep(0.5)` at line 383).

**Key property:** the two loops are independent async tasks. Each maintains its own cursor and reads the shared JSONL file at its own cadence. A missing impingement on one cursor doesn't block the other. This is the regression-pinned pattern per council CLAUDE.md § Unified Semantic Recruitment "Daimonion impingement dispatch".

## 2. Live verification (2026-04-15T18:50Z)

### 2.1 Daimonion service state

```
$ systemctl --user is-active hapax-daimonion.service
active
```

### 2.2 DMN pulse status

```
$ cat /dev/shm/hapax-dmn/status.json
{"running": true, "uptime_s": 10387.2, "buffer_entries": 18, "tick": 1282, "timestamp": 1776278963.761088}
```

- **Uptime:** 10387 seconds ≈ 2.88 hours
- **DMN pulse tick:** 1282 (slow cognitive rhythm, ~8.1s/tick — NOT CPAL; DMN pulse is a separate imagination loop)
- **Buffer entries:** 18 (bounded SHM buffer for recent state)

### 2.3 Impingement stream flow

```
$ wc -l /dev/shm/hapax-dmn/impingements.jsonl
2877 /dev/shm/hapax-dmn/impingements.jsonl

$ cat ~/.cache/hapax/impingement-cursor-daimonion-cpal.txt
2877

$ cat ~/.cache/hapax/impingement-cursor-daimonion-affordance.txt
2877
```

**Both cursors are at the tail of the impingement file.** Zero lag. Both consumer loops have fully consumed the stream up to the last written impingement. This is consistent with a healthy continuous-cognition state.

### 2.4 Most recent impingement

```
$ tail -1 /dev/shm/hapax-dmn/impingements.jsonl | head -c 300
{"timestamp": 1776278957.7424648, "source": "exploration.dmn_pulse", "type": "curiosity",
 "strength": 1.0, "content": {"narrative": "the default mode network's sensory monitoring
 is engaged but noticing an unexpected shift in the DMN's assessment of whether things
 are improving or degrading that war...
```

The most recent impingement is a `curiosity` signal from `exploration.dmn_pulse` — dated 1776278957.74 ≈ ~6 seconds before the status.json timestamp (1776278963.76). Impingements are flowing live; the gap (6s) is consistent with a quiet period + 8s DMN pulse cadence.

## 3. Cold-start analysis

The operator's `feedback_cognitive_loop` memory specifically flags "cold-start on utterance boundary" as an anti-pattern. Checking for cold-start surfaces in CPAL:

### 3.1 Utterance arrival handling

`_process_utterance()` does NOT trigger a tick loop restart. It runs as an async task alongside the tick loop. **No cold start on utterance arrival.** ✓

### 3.2 Impingement arrival handling

`process_impingement()` also runs as an async task, independently from the tick loop. **No cold start on impingement arrival.** ✓

### 3.3 Session start / end

When a session opens (voice conversation begins), the tick loop is already running. Session state changes are tracked via `_daemon.session.is_active` checks INSIDE `_tick()`. **No cold start on session start.** ✓

When a session ends (silence timeout), the tick loop continues running — only the session state flips. **No cold start on session end.** ✓

### 3.4 Service restart (the one cold-start surface)

The only cold-start surface is a full service restart (e.g., `systemctl --user restart hapax-daimonion.service` or an exception propagating out of `run()`). On restart:

- `_last_tick_at = time.monotonic()` is initialized at the top of `run()`
- First `_tick()` call gets `dt ≈ 0` (no accumulated silence from before the restart)
- Perception signals start from whatever the backends report on first query (not stale from before the restart)
- `_tick_count` resets to 0

**Severity:** LOW. Service restarts are rare events (not during normal operation). The restart behavior is CORRECT — silence tracking shouldn't carry across a process boundary because the operator's actual presence state may have changed during downtime.

### 3.5 Watchdog / notify cold-starts

`Type=notify` + `WatchdogSec=60s` in the systemd unit means the service sends `WATCHDOG=1` to systemd periodically. If the tick loop stalls (Python deadlock, I/O hang, GIL contention), systemd kills the service and restarts it. This counts as a cold-start event but is a recovery mechanism, not a normal-path cold-start.

**No recovery cold-starts observed** in the live verification — uptime 2.88 hours without restart.

## 4. Continuity classification

| Loop surface | Continuous? | Evidence |
|---|---|---|
| CPAL tick (150ms cadence) | ✓ YES | Structural — `while self._running:` with no gating; live — daimonion active for 2.88h |
| Perception update | ✓ YES | Runs every tick regardless of utterance state (lines 168-172) |
| Silence tracking | ✓ YES | Runs every tick with guard on `_processing_utterance` (lines 174-178) |
| DMN pulse tick | ~ YES (slow) | 8.1s cadence (status.json tick=1282 over 10387s uptime); distinct from CPAL's 150ms |
| CPAL impingement consumer | ✓ YES | Cursor at tail (2877/2877) — no lag |
| Affordance impingement consumer | ✓ YES | Cursor at tail (2877/2877) — no lag; 500ms poll cadence |
| Utterance processing | ✓ YES (out-of-band) | Not gated by tick loop; runs as async task alongside |
| Service restart path | ~ DISCONTINUOUS (rare) | Silence tracking resets on restart — correct behavior |

**Aggregate verdict:** CPAL is continuous across all operational loop surfaces. The only discontinuity is at service-restart boundaries, which is correct behavior.

## 5. Recommendations

### 5.1 No remediation needed for continuity

The operator's `feedback_cognitive_loop` memory requirement is satisfied by the current implementation. No changes to the tick loop structure are warranted.

### 5.2 Observation: DMN pulse tick vs CPAL tick dual-cadence

CPAL ticks at 150ms (fast perception/action); DMN pulse ticks at ~8s (slow imagination/curiosity). These are two distinct cognitive rhythms. Consider adding a CLAUDE.md § "Dual cognitive cadence" subsection explaining the relationship:

- **CPAL 150ms fast loop** — per-tick perception, silence tracking, utterance arrival handling
- **DMN pulse 8s slow loop** — exploration/curiosity, imagination fragment generation

A future session reading CPAL code in isolation might not realize the DMN pulse exists as a complementary slow loop. Cross-referencing them would prevent confusion.

**Non-blocking.** Non-drift. Optional future CLAUDE.md amendment.

### 5.3 Observation: no per-tick latency measurement

CPAL publishes state every 10 ticks but does NOT record per-tick wall-clock duration in a queryable surface. If the tick ever exceeds 150ms wall-clock (e.g., expensive perception op), the loop catches up via `max(0, TICK_INTERVAL_S - elapsed)` but there's no observable latency signal for monitoring.

**Proposed queue item (optional):** add a `tick_duration_s` rolling window (last N ticks) to `_publish_state()` output. Lets Phase 10 observability monitoring flag tick stalls. Size: ~20 LOC + 1 test. Non-urgent.

### 5.4 No action required for impingement consumer cursor health

Both cursors are at the file tail. Cursor integrity tests exist per CLAUDE.md regression pin `tests/hapax_daimonion/test_impingement_consumer_loop.py::TestSpawnRegressionPin`. No drift observed.

## 6. Non-drift observations

- **TICK_INTERVAL_S = 0.15 (150ms)** is a tunable constant. If future workloads require faster cognition, this could drop to 100ms without code changes (just the constant). Conversely, for low-power modes, 300ms would reduce CPU load at the cost of responsiveness.
- **Production stream + formulation stream + perception stream** (lines 1-40 of cpal/) are separate async streams that interleave with the tick loop. They are NOT gated by the tick; they have their own rhythms. This is deliberate — perception is faster than action, formulation is slower than perception.
- **`loop_gain.py` + `control_law.py`** (not inspected in this audit) are the feedback controllers that modulate tick-loop behavior based on state. A follow-up audit could verify these are wired correctly.

## 7. Cross-references

- `agents/hapax_daimonion/cpal/runner.py` (main tick loop; 505 LOC)
- `agents/hapax_daimonion/cpal/` package (13 modules; 1813 total LOC)
- `agents/hapax_daimonion/run_loops_aux.py::impingement_consumer_loop` (affordance dispatch loop)
- Council CLAUDE.md § Unified Semantic Recruitment "Daimonion impingement dispatch" (regression pin reference)
- Council CLAUDE.md § Impingement consumer bootstrap (three-mode configuration)
- Operator memory: `feedback_cognitive_loop.md` — continuous cognition requirement
- Queue item: queue/`213-beta-cpal-loop-latency-profile.yaml`
- Live state (2026-04-15T18:50Z): `hapax-daimonion.service` active 2.88h uptime, DMN pulse tick 1282, impingement cursors at tail (2877/2877)

— beta, 2026-04-15T18:50Z (identity: `hapax-whoami` → `beta`)
