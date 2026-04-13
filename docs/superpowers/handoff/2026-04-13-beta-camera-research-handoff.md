# Beta Session Retirement Handoff — Camera Stability Research (Queue 022)

**Session:** beta
**Worktree:** `hapax-council--beta` @ `research/camera-stability` (post-sync to 80b137bd1)
**Date:** 2026-04-13, 15:00–16:40 CDT
**Queue item:** 022 — camera-stability-research
**Inflection:** `20260413-210000-alpha-beta-camera-research-brief.md`
**Register:** scientific, neutral (per `feedback_scientific_register.md`)

## One-paragraph summary

Beta completed a six-phase camera performance and stability research pass. Phase 1 (hardware topology), Phase 2 (steady-state performance), Phase 4 (Prometheus metric coverage), and Phase 6 (cross-system interactions) shipped full deliverables. Phase 3 (fault injection) and Phase 5 (audio + A/V latency) are partially deferred because they require (a) operator-action cooperation, (b) coordination with alpha's running memory sampler, and (c) MediaMTX to be active (it is currently inactive). The single most load-bearing finding is that **`studio-compositor.service` was OOM-killed at 15:53:21 CDT** during this research session — refuting alpha's 20:49 claim that the ALPHA-FINDING-1 leak was "steady-state bounded, not crashing", and elevating Option A from "architecturally correct" to **"necessary to maintain 24/7 operation."** Two more live gaps were found: `studio_compositor_cameras_healthy` gauge is broken (reads 0.0 while all six cameras are healthy), and `budget_signal.publish_degraded_signal` is a completely dead end-to-end path (publisher shipped, consumer not shipped, file never written). Complete data for the pass lives under `docs/research/2026-04-13/camera-stability/`.

## Phase ship record

| phase | doc | status | acceptance |
|---|---|---|---|
| 1 — hardware topology | `phase-1-hardware-topology.md` | **shipped** | met |
| 2 — steady-state performance | `phase-2-steady-state-baseline.md` | **shipped** | met for frame-rate / drops / memory / CPU / GPU. HLS latency deferred to Phase 5 |
| 3 — controlled fault injection | `phase-3-fault-injection-timings.md` | **deferred** (documented plan only) | run method + design-budget analysis provided for next session |
| 4 — metric coverage gap | `phase-4-metrics-gap-analysis.md` | **shipped** | met |
| 5 — audio + A/V latency | `phase-5-audio-and-av-latency.md` | **partially shipped** (steady state only) | latency numbers deferred |
| 6 — cross-system interaction | `phase-6-cross-system-interactions.md` | **shipped** | met for budget signal dead path, sdnotify wiring, memory baseline; full consumer map deferred |

Supporting data:
- `docs/research/2026-04-13/camera-stability/data/metric-series-list.txt` — full dump of `studio_*` metric names at measurement time
- `docs/research/2026-04-13/camera-stability/data/frames-10min.csv` — parsed per-5-s trace, 720 rows (120 samples × 6 cameras)
- `docs/research/2026-04-13/camera-stability/data/snapshots/metrics-*.prom` — 120 raw openmetrics scrapes at 5 s cadence

## Ranked fix backlog

Ordered by operator impact (highest first). Source phase indicated in brackets.

### High

1. **`fix(compositor): ALPHA-FINDING-1 Option A — remove in-process TTS, delegate to daimonion via UDS`** [P2, P6] — alpha already has this in flight on `fix/compositor-tts-delegation`. Beta's evidence elevates priority: the leak is not bounded, and the compositor OOM-killed during this research session. Beta has the pre-fix baseline captured (VmRSS 6.06 GB, VmSwap 2.06 GB, libtorch mappings 35, 109 threads, ~74 MB/min growth) for post-fix comparison.

2. **`research(compositor): physically migrate BRIO 43B0576A off bus 5-4 (the USB 2.0-only port)`** [P1] — the degraded link speed survived the resilience epic and a reboot. Software can only contain this; it cannot fix it. The epic's prior research flagged this for hardware inspection; no action has been taken. Operator hand required.

3. **`research(compositor): re-measure memory footprint after Option A lands`** [P6] — validation of the leak fix. Expected post-fix: libtorch mappings → 0, VmRSS → 1.5–2.0 GB, threads → ≤ 80, NRestarts stops growing. File as `phase-6-post-fix-memory.md`. Blocked on Option A merge.

### Medium

4. **`fix(compositor): studio_compositor_cameras_healthy stuck at 0.0`** [P4] — simple instrumentation bug. Grafana dashboard panel 0 displays a wrong number. `_refresh_counts()` in `metrics.py` explicitly defers the `_healthy` accumulator to a callsite that does not exist. Fix: add a `_healthy_count` module-level int guarded by `_lock`, update on `on_state_transition(to_state="healthy")` and on any transition out of healthy, set `COMP_CAMERAS_HEALTHY` at each transition.

5. **`fix(compositor): wire budget_signal.publish_degraded_signal into the compositor loop + ship VLA subscriber`** [P6] — end-to-end dead path. Publisher exists (F3 of unification epic, PR #672), has a unit test, but has no production caller. `/dev/shm/hapax-compositor/degraded.json` never exists on disk. No VLA subscriber either. Two sub-tickets: (a) add publish call at a reasonable cadence in the compositor loop, (b) ship a stimmung reader that consumes `degraded.json` and maps it to a dimension.

6. **`fix(metrics): studio_compositor_memory_footprint_bytes gauge`** [P4] — evidence-backed new series that obsoletes the external `sample-memory.sh` script. Polls `/proc/self/status` in-process every 30 s, labeled by kind (rss, swap, rss_anon, threads). Removes the PID-hardcoding race during OOM-restarts. Bundle with Option A or file separately.

7. **`fix(compositor): investigate brio-operator sustained 28 fps vs 30 fps target`** [P2] — 7 % frame-rate deficit on one camera, sustained for 10+ min of 5-s-cadence tracing (mean 27.972 fps, σ=1.39; others are 29.987–29.993 fps). Three candidate causes: producer-thread starvation under load, 4K native capture, metrics lock contention. Re-measure after Option A (compositor CPU load should drop, exposing whether the 53-load was compositor-self-inflicted).

### Low

8. **`chore(metrics): wire or delete studio_rtmp_bytes_total and studio_rtmp_bitrate_bps`** [P4] — 2 dead metric callsites. No call site in `rtmp_output.py` or `compositor.py`. Either instrument at `rtmp2sink` chain-function or delete the definitions.

9. **`fix(udev): reassert `power/control=on` on BRIOs reliably`** [P1] — latent drift. Rule says `on`, live state on all three BRIOs is `auto`. Benign today (autosuspend_delay_ms=-1 dominates), latent for future kernels. Options: periodic reassertion, startup write, or `change`-action rule.

10. **`fix(udev): add BRIO 43B0576A and 9726C031 to `90-webcams.rules``** [P1] — only one BRIO has a stable `/dev/webcam-brio` symlink. Add `webcam-brio-2` / `webcam-brio-3` symlinks anchored on serial.

11. **`fix(udev): include C920 082d in 70-studio-cameras.rules Phase 3 reconfigure hook`** [P1] — older C920 has PID 082d; only covered by the 99-webcam-power fallback, not by the epic's `studio-camera-reconfigure@%k.service` trigger. Add the PID to the reconfigure block.

12. **`docs(compositor): enumerate /dev/shm/hapax-compositor/ file inventory with schema + consumer map`** [P6] — 34 files ad-hoc, no reference doc. Saves every future research session a grep walk.

13. **`feat(state-machine): parallel-failure aware retry scheduling for host-controller resets`** [P3, speculative] — when multiple cameras on the same xHCI controller fail simultaneously, exponential backoff aligns and compounds pressure. Jitter each retry by `role_hash % 500 ms`. Evidence not collected — blocked on real xHCI event.

14. **`fix(grafana): mark fault-gated panels as "0 events in last 5m" when series absent`** [P4] — distinguishing "no faults" from "metric pipeline broken" is hard. Use `or vector(0)` in queries or switch panel to a stat that treats absence as zero.

15. **`fix(compositor): confirm-or-document whether native RTMP bin is currently in production use`** [P5] — MediaMTX is inactive and `studio_rtmp_connected` is absent from the live scrape, inconsistent with "native RTMP shipping". Needs a one-sentence clarification in the epic handoff doc.

16. **`research(compositor): complete Phase 3 fault injection + Phase 5 A/V latency measurements post-Option-A`** [P3, P5] — the deferred measurements themselves, to be run by a future session once alpha's coordination constraint is lifted.

## Convergence-critical findings (repeated from phase docs for handoff legibility)

### Finding B-1: Compositor OOM-killed at 15:53:21 — leak is NOT steady-state bounded

Captured in `convergence.log` at 16:10:00 CDT. Journal:

```text
systemd[]: studio-compositor.service: The kernel OOM killer killed some processes in this unit.
systemd[]: studio-compositor.service: Main process exited, code=killed, status=9/KILL
systemd[]: studio-compositor.service: Failed with result 'oom-kill'.
```

Previous PID 1963052 survived 15:00:17 → 15:53:21 = **53 minutes** before OOM. `MemoryMax=6 GiB` + `MemoryHigh=infinity` did not prevent the kill. Alpha's 20:49 status said "runtime ~52 min continuous, RSS oscillates 6.19-6.49 GB, ... not crashing" — that readout is stale by 52 minutes, written at 20:49 about a process that had been OOM-killed at 15:53. Alpha's sampler CSV at `~/.cache/hapax/compositor-leak-2026-04-13/memory-samples.csv` ends at 15:51:57 — the last sample before OOM — and has **not been re-pointed** at the new PID 2529279. Alpha's `compositor_leak_current_state` section in `alpha.yaml` should be refreshed.

### Finding B-2: `studio_compositor_cameras_healthy` permanently wrong

Grafana dashboard panel 0 shows 0 while all six cameras are healthy. Root cause is a `_refresh_counts()` TODO comment promising a count accumulator that never got implemented. Single-file fix in `agents/studio_compositor/metrics.py`.

### Finding B-3: `budget_signal.publish_degraded_signal` is a fully dead end-to-end path

The compositor unification epic's F3 followup shipped a publisher library (`build_degraded_signal` + `publish_degraded_signal`), a unit test, and a consumer-side design for the VLA stimmung reader. The consumer was noted as "out of scope" in the epic. **The publisher was also never wired into the compositor main loop.** Result: compositor degradation under render-budget pressure is invisible to the rest of the council. `/dev/shm/hapax-compositor/degraded.json` does not exist. This is the "half-merged observability" failure pattern that beta's 2026-04-13 03:03 discovery sweep (see prior `beta.yaml` findings A/B/C) identified as systemic — the Phase 8 `FreshnessGauge` work addressed the imagination-loop case but not this case.

## Coordination notes

- **Alpha is active on `fix/compositor-tts-delegation`** as of this handoff. Beta did not touch any files under `agents/hapax_daimonion/` or `agents/studio_compositor/` during this research pass. The only compositor-adjacent file read was `metrics.py` / `budget_signal.py` / `lifecycle.py` for code analysis. No merge conflict risk.
- **Beta did NOT restart `studio-compositor.service`** during this research pass. The 15:53 OOM was not caused by beta — it happened before beta started measuring. Convergence log flagged this for alpha at 16:10 with the advisory that alpha's sampler CSV is now stale.
- **Alpha's sampler is dead** — polling a non-existent PID 1963052. Should either be re-pointed at PID 2529279 (next session) or replaced with the in-process `studio_compositor_memory_footprint_bytes` gauge proposed in fix backlog #6.
- Beta's research branch `research/camera-stability` is local-only (not pushed to origin). Next session should push + open a docs PR.

## What the next session should read first

1. `docs/research/2026-04-13/camera-stability/phase-2-steady-state-baseline.md` § "Compositor restart boundary" — the OOM finding.
2. `docs/research/2026-04-13/camera-stability/phase-6-cross-system-interactions.md` § "The degraded-signal dead path" — the half-merged F3 gap.
3. `docs/research/2026-04-13/camera-stability/phase-1-hardware-topology.md` § "Device inventory" — the standing brio-room USB 2.0 question.

If Option A lands during the next session, read `phase-6-cross-system-interactions.md` § "Post-ALPHA-FINDING-1-fix memory re-measurement plan" and run the matching commands against the new PID. The comparison is what validates the fix.

## Open questions left for alpha + operator

1. **(operator)** The brio-operator 28 fps deficit: is this a pre-existing observation, or new with the current compositor run? If pre-existing, it is likely a role-configuration issue (capture format, scheduling weight). If new, it correlates with the load-average 53 that appeared during this research window.
2. **(alpha)** Is the native RTMP bin (`rtmp://127.0.0.1:1935/studio`) intended to be the current egress path, given that MediaMTX is `inactive` and `studio_rtmp_connected` is absent from the live scrape? One-sentence answer would clarify whether Phase 5 latency measurements should run against the compositor path or against OBS.
3. **(alpha)** Should the `MemoryHigh=infinity` drop-in be promoted into the repo systemd unit alongside Option A landing, or left as a machine-local override? Beta's evidence says the drop-in did not prevent OOM, so it is not load-bearing for keeping the compositor alive today — but it also did not make things worse. Decision can be deferred until post-Option-A when the memory trajectory flattens.

## Beta retirement status

Beta considers queue item 022 substantively complete for the scope of this session. The deferred phases (3 fault injection, 5 A/V latency) are documented in full with reproduction commands, so a future session can execute them without re-reading the brief from scratch. Beta will update `beta.yaml` with a `RETIRING` status, commit the research docs to `research/camera-stability`, and push the branch for the docs PR.

`~/.cache/hapax/relay/beta.yaml` will point at this handoff doc as the authoritative closeout. No other beta work is in flight.
