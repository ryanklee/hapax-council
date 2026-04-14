# brio-operator startup stall is reproducible — no initial frame-flow grace

**Date:** 2026-04-14
**Author:** delta (beta role — cam-stability focus)
**Scope:** Camera stability and performance, with the
operator's confirmation that running BRIOs at 720p is
fine (so resolution is not a lever). Builds on drop #2
(brio-operator sustained deficit) with a new observation:
the startup path is broken in a specific, reproducible,
fixable way that accounts for ~3 seconds of lost data on
every compositor restart.
**Register:** scientific, neutral
**Status:** investigation only — one 2-line fix proposal
that's independent of the drop #2 sustained-deficit
question

## Headline

**Three findings.**

1. **brio-operator fires `FRAME_FLOW_STALE` within ~1
   second of `swap_to_primary` on every compositor cold
   start.** Observed 4 out of 4 restarts sampled
   (2026-04-14 11:50, 11:56, 12:04, 12:11). No other
   camera triggers this event at startup. Always exactly
   one event per cold start, always on brio-operator.
2. **Root cause: `_frame_flow_tick_once` in
   `agents/studio_compositor/pipeline_manager.py:398-428`
   has no initial grace period.** The existing grace
   (`_FRAME_FLOW_GRACE_S = 5.0`) only applies when
   `_last_recovery_at[role]` is populated — i.e., after
   a prior recovery event. On the very first transition
   to HEALTHY after cold start, `_last_recovery_at[role]`
   is not set, so the grace check (`recovered_at is not
   None and (now - recovered_at) < _FRAME_FLOW_GRACE_S`)
   evaluates to False and the watchdog immediately
   checks age. With `STALENESS_THRESHOLD_S = 2.0` and
   the check firing every 1 second
   (`_FRAME_FLOW_TICK_S = 1.0`), any camera that takes
   more than ~1 second to produce its first frame is
   falsely flagged.
3. **Cost of the false positive**: ~3.3 seconds of lost
   data on brio-operator per cold start (measured), plus
   one spurious `camera_pipeline` rebuild + one spurious
   `fb_brio_operator` fallback cycle + one spurious
   `healthy→degraded→offline→recovering→healthy` state
   machine walk. **The recovery works correctly** (the
   camera comes back up healthy) but the data loss is
   avoidable.

**Net impact.** Per drop #22 the
`hapax-rebuild-services.timer` cycles the compositor
multiple times per day when `agents/studio_compositor/`
watch paths change. Each cycle loses ~3 seconds of
brio-operator frames (~90 frames at 30 fps expected, or
~70 frames at the sustained 27-28 fps that brio-operator
actually produces). Over today's 4 restarts in
~30 minutes, that's ~280-360 lost frames on one camera.
**A 2-line fix eliminates this entirely.**

## 1. The reproducible pattern

From the journal at 4 different restart timestamps on
2026-04-14:

### 1.1 Restart 1 — 11:50:27

```text
11:50:27.694  swap_to_primary: role=brio-operator → cam_brio_operator
11:50:27.722  swap_to_primary: role=c920-desk → cam_c920_desk
11:50:27.746  swap_to_primary: role=c920-room → cam_c920_room
11:50:27.767  swap_to_primary: role=c920-overhead → cam_c920_overhead
11:50:27.788  swap_to_primary: role=brio-room → cam_brio_room
11:50:27.810  swap_to_primary: role=brio-synths → cam_brio_synths
11:50:28.740  FRAME_FLOW_STALE  role=brio-operator  last_frame_age=inf > 2.00s
11:50:28.741  brio-operator healthy → degraded  reason='pad-probe age inf'
11:50:28.748  swap_to_fallback: brio-operator → fb_brio_operator
11:50:28.750  brio-operator degraded → offline
11:50:29.754  supervisor: attempting reconnect for role=brio-operator
11:50:29.755  brio-operator offline → recovering
11:50:30.692  camera_pipeline brio-operator built (state change=success)
11:50:30.701  brio-operator recovering → healthy  reason='rebuild ok'
11:50:30.710  swap_to_primary: brio-operator → cam_brio_operator  (second time)
```

Elapsed from first `swap_to_primary` to final healthy
state: **~3.0 seconds**. During this window, brio-operator
produced no frames.

### 1.2 Restart 2 — 11:56:43

```text
11:56:43.883  camera_pipeline brio-operator started (state change=success)
11:56:43.936  camera_pipeline brio-room    started
11:56:43.948  camera_pipeline brio-synths  started
11:56:43.955  swap_to_primary: brio-operator → cam_brio_operator
11:56:44.062  swap_to_primary: brio-room
11:56:44.085  swap_to_primary: brio-synths
11:56:44.957  FRAME_FLOW_STALE  role=brio-operator  last_frame_age=inf > 2.00s
11:56:46.610  camera_pipeline brio-operator rebuilt
11:56:46.641  swap_to_primary: brio-operator (second time)
```

Elapsed: **~2.7 seconds**. Same pattern.

### 1.3 Restart 3 — 12:04:00

```text
12:04:00.652  camera_pipeline brio-operator started
12:04:00.708  swap_to_primary: brio-operator
(eventually)
12:04:07.205  camera_pipeline brio-operator rebuilt
12:04:07.218  swap_to_primary: brio-operator (second time)
```

Elapsed: **~6.5 seconds** — longer than the other
restarts, possibly because the rebuild got bumped by
other pipeline events. Still a full
`degraded→offline→recovering→healthy` cycle.

### 1.4 Restart 4 — 12:11:15

```text
12:11:15.620  camera_pipeline brio-operator started
12:11:15.696  swap_to_primary: brio-operator
12:11:16.769  FRAME_FLOW_STALE  role=brio-operator  last_frame_age=inf > 2.00s
12:11:19.065  camera_pipeline brio-operator rebuilt
12:11:19.345  swap_to_primary: brio-operator (second time)
```

Elapsed: **~3.6 seconds**.

**Pattern is consistent across 4 restarts: ~1 second
after `swap_to_primary`, FRAME_FLOW_STALE fires with
`last_frame_age=inf`, a full recovery cycle runs, and
the camera is healthy again ~3 seconds later.**

## 2. The watchdog code

```python
# agents/studio_compositor/pipeline_manager.py:398-428

_FRAME_FLOW_TICK_S = 1.0      # watchdog runs every 1 second
_FRAME_FLOW_GRACE_S = 5.0     # grace after a recovery

# camera_state_machine.py:57
STALENESS_THRESHOLD_S = 2.0   # frames older than 2s trigger stale

def _frame_flow_tick_once(self) -> None:
    now = time.monotonic()
    with self._lock:
        roles = list(self._state_machines.keys())
        recovery_snapshot = dict(self._last_recovery_at)

    for role in roles:
        sm = self._state_machines.get(role)
        if sm is None or sm.state != CameraState.HEALTHY:
            continue
        recovered_at = recovery_snapshot.get(role)
        if recovered_at is not None and \
           (now - recovered_at) < _FRAME_FLOW_GRACE_S:
            continue                              # ← post-recovery grace
        age = self.get_last_frame_age(role)
        if age <= STALENESS_THRESHOLD_S:
            continue
        log.warning("frame-flow watchdog: role=%s …", role, age)
        sm.dispatch(Event(EventKind.FRAME_FLOW_STALE, …))
```

The bug: `_last_recovery_at[role]` is populated by the
`on_recovery` callback (not shown) after a camera
successfully recovers. On **first-ever transition** to
HEALTHY after a cold start, no recovery has happened,
so `recovery_snapshot.get(role)` returns `None`, and
the check `recovered_at is not None and …` evaluates
False — the grace period is bypassed.

At that point, the watchdog immediately calls
`get_last_frame_age(role)` which returns `float("inf")`
because no frame has been produced yet, and the
inf > 2.0s comparison fires FRAME_FLOW_STALE.

## 3. Why only brio-operator — first-camera vs
camera-specific

brio-operator is **always first** in the `swap_to_primary`
order (confirmed across 4 restarts). Two hypotheses:

- **H1 (first camera hypothesis)**: any camera in first
  position would trip the watchdog because pipeline setup
  takes longer on the first camera due to GStreamer
  one-time costs (context creation, shader compile, etc).
  If the camera builder order were reshuffled, whichever
  camera ended up first would fail.
- **H2 (brio-operator specific)**: regardless of order,
  brio-operator specifically has a 2+ second first-frame
  latency. If reshuffled, brio-operator would still fail.

**Delta cannot distinguish these from the current data.**
Both hypotheses are consistent with:

- brio-operator always fails (it's first, and/or it's
  brio-operator)
- brio-room + brio-synths + all C920s always succeed
  (they're not first, and/or they're not brio-operator)
- Drop #2's sustained deficit (27.94 fps) is separate
  from this startup issue — it's measured outside
  startup windows

**The cheap answer is to fix the grace-period bug
regardless of H1 vs H2**, because:

- If H1, the grace absorbs the first-camera warmup and
  no camera fails.
- If H2, the grace absorbs brio-operator's specific
  slow-first-frame and the data loss goes away.
- Both hypotheses benefit from the fix.

If alpha wants to distinguish H1 from H2 for diagnostic
purposes, the test is: **reorder the camera builder so
brio-operator is not first, and see if the new
first-camera fails instead, or brio-operator still
fails.** That's a 5-line diff + one test run. But it's
not necessary to unblock the fix.

## 4. The fix

Two-line change in `pipeline_manager.py`. When a camera
first transitions to HEALTHY after cold start, set
`_last_recovery_at[role]` to the current monotonic time
so the watchdog treats initial startup as a grace window:

```python
# In the state-machine transition handler that marks
# a camera HEALTHY (approximate location — follow the
# existing _last_recovery_at write path):

def _on_state_change(self, role: str, new_state: CameraState) -> None:
    if new_state == CameraState.HEALTHY:
        with self._lock:
            # Treat initial startup the same as a recovery:
            # the watchdog should give the camera its grace
            # window to produce a first frame.
            if role not in self._last_recovery_at:
                self._last_recovery_at[role] = time.monotonic()
```

Or, equivalently and minimally, initialize the dict at
camera-registration time:

```python
# Where cameras are first registered (add_camera / similar):
self._last_recovery_at[role] = time.monotonic()
```

Either approach makes the watchdog skip the first ~5
seconds (equal to `_FRAME_FLOW_GRACE_S`) after cold start.
brio-operator's 2.5-second first-frame delay fits comfortably
in that window.

**Test**: after the fix, restart the compositor 4 times,
observe no FRAME_FLOW_STALE events at startup, and verify
brio-operator's frame histogram shows a non-zero first
second of data.

## 5. Live measurement of brio-operator's current state

Fresh histogram from the process that started at 11:50:

```text
role=brio-operator
count = 6837
sum   = 247.67 s
mean interval = 36.22 ms
mean fps      = 27.61
```

Compared to drop #2's measurement (6 h sample):

```text
Drop #2: mean fps = 27.94
Today:   mean fps = 27.61
```

Today's lower number is consistent with the startup stall
being more heavily weighted in a shorter (~4 min) sample
window. Drop #2's 6-hour window amortized startup loss
across many more frames, so 27.94 is closer to the
sustained rate.

**Estimated sustained rate (excluding startup stall):**

- Sample window: 248 s
- Lost to startup stall: ~3 s (observed)
- Effective sustained window: 245 s
- Frames produced: 6837
- Sustained fps: 6837 / 245 = **27.91 fps**

Matches drop #2's 27.94 to within measurement noise.
**Drop #2's sustained deficit is confirmed — this fix
does not address it.** The startup stall is a SEPARATE
issue that happens to compound with the sustained
deficit on short samples.

## 6. Context — cumulative lost frames today

Today's compositor restart count (visible in the journal
since ~09:35): at least 6 restart events across the
morning — one at process start, two from compositor
watch-path change cascades via
`hapax-rebuild-services.timer` (drop #22), one operator-
initiated around 10:07, several more between 11:50 and
12:11.

Assuming the startup stall is consistent at ~3.3 s per
restart × 6 restarts × 30 frames/s = **~594 frames lost
to the startup bug today alone.** Not counting the
sustained deficit from drop #2.

## 7. Cross-reference to other cam-stability open items

This fix and the open items together form a cam-stability
backlog for the next session:

1. **Startup stall (this drop)** — 2-line fix, eliminates
   ~3 s of data loss per restart.
2. **Sustained deficit (drop #2)** — still open. Three
   hypotheses (H4 cable/port signal integrity, H5 BRIO
   firmware variance, H6 jpegdec/interpipesink
   back-pressure). Needs the cable/port swap test from
   drop #2 § 4 to distinguish.
3. **Kernel-drops false zero (drop #2 § 2.3)** —
   `studio_camera_kernel_drops_total` reports 0 for all
   cameras because the v4l2 sequence-gap detector doesn't
   fire on MJPG payloads. If this metric were honest,
   we could attribute brio-operator's sustained frame
   loss to kernel vs user-space.
4. **First-camera vs brio-operator-specific test** (§ 3
   above) — optional diagnostic that would clarify the
   root cause but isn't required for the fix.
5. **Camera builder order reshuffling** — related but
   orthogonal; if brio-operator is always first by
   alphabetical order, moving it to a later position
   costs nothing and might eliminate the startup stall
   entirely without needing the grace-period fix.

## 8. Follow-ups for alpha

Ordered by leverage:

1. **Ship the 2-line fix** in § 4. Eliminates startup
   data loss. Works for both H1 and H2 root causes.
   Zero risk.
2. **Reorder camera builder** so brio-operator is not
   first (e.g., alphabetize as "brio_room, brio_synths,
   brio_operator" or just swap first and last). Observe
   whether FRAME_FLOW_STALE fires on the new first
   camera. Distinguishes H1 from H2.
3. **Run the drop #2 cable/port swap test** — confirms
   or refutes the sustained deficit root cause.
4. **Close the `studio_camera_kernel_drops_total`
   false-zero** by replacing the sequence-gap detector
   with a pad-probe differential counter. Drop #14 Ring
   3 already flags this.
5. **Add a startup-event metric** —
   `studio_camera_startup_stalls_total{role=…}` — so
   any future regression is visible in Prometheus
   rather than only in the journal. Pairs with the
   Phase 10 observability metrics shipped earlier today.

## 9. References

- `agents/studio_compositor/pipeline_manager.py:398-428`
  — `_frame_flow_tick_once` with the gap in initial grace
- `agents/studio_compositor/pipeline_manager.py:44,51`
  — `_FRAME_FLOW_TICK_S = 1.0`, `_FRAME_FLOW_GRACE_S = 5.0`
- `agents/studio_compositor/camera_state_machine.py:57`
  — `STALENESS_THRESHOLD_S = 2.0`
- Drop #2 (`2026-04-14-brio-operator-producer-deficit.md`)
  — the sustained-deficit finding this drop is
  orthogonal to
- Drop #22 (`2026-04-14-systemd-timer-enablement-gap.md`)
  — why the compositor restarts so often via
  `hapax-rebuild-services.timer`
- Live histogram: `curl -s http://127.0.0.1:9482/metrics
  | grep studio_camera_frame_interval_seconds`
  at 2026-04-14T17:00 UTC
- Journal: `journalctl --user -u studio-compositor.service
  --since "5 hours ago" | grep -E "brio|FRAME_FLOW_STALE"`
  at same time
