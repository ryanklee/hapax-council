# Phase 3 — Controlled Fault Injection + Recovery Timing

**Session:** beta, camera-stability research pass (queue 022)
**Status:** **DEFERRED.** This phase is documented as a plan + design-budget analysis; the live fault injection runs themselves are not executed in this research pass.

## Why deferred

Two interlocking constraints block execution of the full phase in this session:

1. **Coordination with alpha.** Alpha is implementing ALPHA-FINDING-1 Option A on the `fix/compositor-tts-delegation` branch and is simultaneously observing the compositor memory trajectory (the sampler CSV at `~/.cache/hapax/compositor-leak-2026-04-13/memory-samples.csv`, currently ending at the 15:53 OOM). Injecting a USB reset on any camera will (a) fire state-machine transitions, (b) possibly cause a fallback-swap + consumer re-listen cycle that moves the compositor memory trajectory in a way alpha's next sampler window would have to account for, and (c) if the post-recovery cycle itself triggers any torch path, could be mis-attributed to the leak investigation. The research brief from alpha explicitly asks beta to post a convergence note **before** any compositor restart for exactly this reason (§Coordinate with alpha, bullet 2).

2. **Operator supervision required for fault classes A and D.** Class A (physical unplug/replug) needs operator action — beta cannot touch studio hardware. Class D (MediaMTX kill/restart) requires MediaMTX to be running first; §Phase 2 verified MediaMTX is inactive, so there is nothing to kill. Class B (`studio-simulate-usb-disconnect.sh`) and C (SIGSTOP the UVC driver / hold the device open) can be run autonomously, but each of them triggers the same coordination issue from (1).

**Action:** the phase is documented with the planned method, the design-budget math, the acceptance criteria, and a reproduction checklist that the next session can execute once Option A has landed and alpha's sampler is re-pointed at a stable PID. When that session runs, it should announce the plan on `convergence.log`, execute, and file the per-event table.

## Design budget for the recovery path (from the epic)

From `agents/studio_compositor/camera_state_machine.py` and `docs/superpowers/specs/2026-04-12-camera-recovery-state-machine-design.md`:

| state | entry event | exit event | dwell budget |
|---|---|---|---|
| HEALTHY | frame flow live | first missed-frame / frame-age threshold | n/a |
| DEGRADED | frame age > threshold (producer starved but not errored) | frames resume | 0 (transient) |
| OFFLINE | v4l2 ioctl failure / producer gst-bus error | reconnect attempt fires | 0 (enters backoff immediately) |
| RECOVERING | reconnect attempt in flight | reconnect succeeded / failed | per attempt |
| BACKING_OFF | reconnect failed | next attempt fires | **1 + 2 + 4 + 8 + 16 + 32 + 60 + 60 + 60 + 60 s** |
| DEAD | too many failures | operator intervention | indefinite |

Total budget from first failure to "gave up": **303 s** ≈ **5 min 3 s**. Individual retries at 1, 3, 7, 15, 31, 63, 123, 183, 243, 303 s marks.

**Open question from the brief:** is 303 s the right budget for the real fault distribution? The answer depends on the class of fault:

- **Fast-recoverable transients (bus reset, USBDEVFS_RESET, interpipe stall):** the resilience stack's hot-swap to fallback producer happens in O(100 ms), and the primary re-attach typically succeeds on the first or second retry (1 s or 3 s after fault). For this class, the budget is **over-provisioned** — the stall ends before the first exponential ramp matters.
- **Cable / VBUS fault:** BRIO loses link, re-enumerates. Recovery requires either replug or automated `usbreset`. The `udev change` event fires quickly once the port re-enumerates; the pipeline rebuild on the `studio-camera-reconfigure@%k.service` trigger is O(1 s). For this class, 303 s is **comfortable** — the budget covers multiple re-enumerations even under intermittent cable contact.
- **Host controller reset (xhci_hcd fatal):** the xHCI driver re-initializes the whole bus, which is O(seconds to tens of seconds). During the window, all cameras on that controller drop simultaneously. The state machine would see N-camera parallel failures. For this class the budget is **under-provisioned for simultaneous retries** — each camera ramps its exponential in lockstep and all will reach their final slot at the same time, which compounds host controller pressure.
- **uvcvideo kernel module hang:** module needs reloading (`modprobe -r uvcvideo; modprobe uvcvideo`) or a full reboot. For this class, 303 s is **insufficient** — no amount of software retry fixes a hung module.

**Proposed Phase 3 result template** when the next session runs the injection:

```text
fault_class,role,attempt_index,dwell_ms,end_state
A,brio-operator,1,234,HEALTHY
A,brio-operator,2,412,HEALTHY
A,brio-operator,3,198,HEALTHY
B,brio-operator,1,?,?
...
```

Report format: histogram per class × per camera, with dwell-time p50/p95/p99, plus a "budget utilization" column (observed p95 ÷ 303 s). A p95 ≤ 10 % of budget → "over-provisioned, safe to shrink budget". A p95 ≥ 80 % → "under-provisioned, investigate before shrinking".

## Planned method (for execution by a future session)

**Pre-run checks (5 min):**

```bash
# 1. Check alpha's sampler status — re-point or pause if needed
pgrep -af "compositor-leak\|memory-samples\|sample-memory"

# 2. Verify compositor is on a stable post-FINDING-1-fix PID
systemctl --user show studio-compositor.service -p NRestarts -p MainPID
# Expect: NRestarts == 1 (from the 15:53 OOM) and not growing

# 3. Confirm metric exporter is up
curl -sf http://127.0.0.1:9482/metrics | head -1

# 4. Post convergence note
echo "$(date -Iseconds) | ADVISORY | beta: Phase 3 fault injection starting ... | alpha: ..." >> ~/.cache/hapax/relay/convergence.log
```

**Pre-stage three terminal tails (continuous during run):**

```bash
# Terminal 1
journalctl --user -u studio-compositor.service -f \
  | jq -r 'select(.module == "camera_state_machine" or .module == "pipeline_manager" or .module == "camera_pipeline")
           | "\(.timestamp) \(.level) \(.message)"'

# Terminal 2
while true; do
  date +%s
  curl -s http://127.0.0.1:9482/metrics | grep -E '^studio_camera_(state|in_fallback|consecutive_failures|transitions|reconnect)'
  sleep 2
done

# Terminal 3
dmesg -w | grep -iE "usb|xhci"
```

### Fault class A — USB unplug / replug (operator-action)

For each BRIO in turn:

1. Unplug cable at the host-side USB port.
2. Start stopwatch when the cable leaves. Record `t_unplug`.
3. Watch terminal 1 for `role=<cam> healthy → degraded → offline → recovering → backing_off` sequence and tail-of-fallback producer swap.
4. Watch terminal 2 for `studio_camera_in_fallback{role=<cam>} 0 → 1`. Record `t_fallback_visible` (should be O(100 ms) per the epic design).
5. Wait 10 s in BACKING_OFF.
6. Replug the cable. Record `t_replug`.
7. Watch for `recovering → healthy` transition. Record `t_healthy`.

Three repetitions per camera. Log: `t_fallback_visible - t_unplug`, `t_healthy - t_replug`, and the full state transition sequence.

**Operator action required.** Not runnable autonomously.

### Fault class B — simulated USBDEVFS_RESET via existing sim script

The sim script is at `scripts/studio-simulate-usb-disconnect.sh`. Role is required:

```bash
scripts/studio-simulate-usb-disconnect.sh brio-operator
scripts/studio-simulate-usb-disconnect.sh brio-room   # the USB 2.0 BRIO
scripts/studio-simulate-usb-disconnect.sh brio-synths
# ... etc for each of the 6 roles
```

The script does a `USBDEVFS_RESET` ioctl via a Python helper; this does not cut VBUS so the device re-enumerates on the same bus slot. Expected recovery timeline: reset fires → uvcvideo re-initializes in ≤ 500 ms → state machine sees producer gst-bus error → reconnect at attempt 1 (1 s dwell) → success. p95 dwell ≤ 2 s.

Run three reps per role. Autonomous. Does not need operator.

### Fault class C — watchdog element trip

The epic ships a GStreamer `watchdog` element in each camera pipeline (producer chain) and a compositor-level sdnotify watchdog tied to the 60 s `WatchdogSec=` in the systemd unit. The GStreamer element fires when no buffer arrives within its timeout.

To test: hold the v4l2 device open from a second process that does not read. This prevents the compositor's producer from negotiating caps.

```bash
# Second terminal
python3 -c 'import os,time; fd=os.open("/dev/v4l/by-id/usb-046d_Logitech_BRIO_43B0576A-video-index0", os.O_RDWR); time.sleep(30); os.close(fd)'
```

Alternative: SIGSTOP the compositor-internal uvcvideo kworker (hard to target without debug symbols). Prefer the O_RDWR-hold approach.

Expected: `studio_camera_last_frame_age_seconds{role=<cam>}` climbs to the watchdog element's timeout (check the default in `camera_pipeline.py`), then producer errors and the standard recovery FSM fires. Three runs total across whichever BRIO is expendable.

### Fault class D — MediaMTX kill

**Precondition: MediaMTX must be running.** Currently inactive (Phase 2). Restart it first:

```bash
systemctl --user start mediamtx
sleep 5
systemctl --user status mediamtx
curl -s http://127.0.0.1:1935 > /dev/null && echo "rtmp up" || echo "rtmp down"
```

Then:

```bash
# Mid-stream, kill MediaMTX
systemctl --user stop mediamtx
sleep N       # observe
systemctl --user start mediamtx
```

Watch `studio_rtmp_connected{endpoint="youtube"}` flip 1 → 0 → 1. Watch `studio_rtmp_bin_rebuilds_total{endpoint="youtube"}` for the rebuild count. The brief asks whether the `rtmp_` src-name filter in the composite pipeline's bus message handler correctly isolates the error to the RTMP bin without disturbing the rest of the pipeline — confirm by watching all six `studio_camera_frames_total` rates during the outage; they should NOT dip.

Three reps total. Autonomous, but depends on MediaMTX being configured and whatever YouTube ingest URL is set in the endpoint.

## Follow-up tickets

1. **`research(camera): execute Phase 3 fault injection run in a post-FINDING-1-fix session`** — not executable in this pass because of alpha coordination + operator-action requirement for class A. Ship this ticket with the full method documented above; assign to beta + operator. *(Severity: low. Affects: empirical validation of the 303 s design budget.)*

2. **`feat(state-machine): parallel-failure aware retry scheduling for host-controller resets`** — when multiple cameras on the same xHCI controller fail simultaneously, their exponential backoff aligns and compounds pressure on the re-enumerating controller. Consider jittering each camera's retry schedule by `role_hash % 500 ms`. Evidence needed: a real host-controller reset event captured in both dmesg and the state machine's transition log. **Speculative until observed.** *(Severity: medium if the event ever happens. Affects: multi-camera recovery cascade.)*

3. **`docs(compositor): document which fault classes the 303 s budget is tuned for`** — the current spec describes the schedule without stating which fault class it was designed around. Classifying the schedule explicitly against the four fault classes in this doc lets the operator reason about budget changes. *(Severity: low. Affects: spec clarity.)*

## Acceptance check

- [ ] Four fault classes × three runs per camera × six cameras × per-event dwell table. **Not met. Deferred.**
- [x] Design budget analyzed against the four fault-class taxonomy.
- [x] Pre-run checklist and per-class method documented for the next executing session.
- [x] Cross-coordination constraint with alpha's sampler documented with the explicit convergence-note step.
