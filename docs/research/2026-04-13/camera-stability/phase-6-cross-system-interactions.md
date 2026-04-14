# Phase 6 — Cross-System Interaction Audit

**Session:** beta, camera-stability research pass (queue 022)
**Scope note:** read-only walk of compositor↔consumer signal seams, based on source inspection + live state of `/dev/shm/hapax-compositor/` at 16:25 CDT. A full consumer map across all council agents is out of budget for this pass; the highest-value gaps are documented below with follow-up ticket hooks for deeper exploration.

## Headline

- **`budget_signal.publish_degraded_signal()` is a fully dead end-to-end path.** The publisher is shipped, unit-tested, and has **no caller anywhere in the compositor source**. The file `/dev/shm/hapax-compositor/degraded.json` does not exist on disk at measurement time even though the compositor has been running 30+ min. The previously-documented gap (§`docs/superpowers/audits/2026-04-12-compositor-unification-audit.md` line 191) noted "no VLA subscriber" — reality is worse: **both producer and consumer sides are absent.** F3 of the unification epic is half-merged: the library is in place, the wiring is not.
- **sd_notify watchdog IS tied to real frame flow**, not just process liveness. `_watchdog_tick()` in `lifecycle.py` gates `sd_notify_watchdog()` on `any(s == "active" for s in compositor._camera_status.values())`. GLib timeout at 20 s interval, under the 60 s `WatchdogSec=` budget. If all six cameras drop simultaneously, the watchdog stops feeding and systemd will kill the unit after 60 s. This is correct liveness design for a camera-critical service.
- **`studio.toggle_livestream` affordance handler** was shipped in PR #730 (alpha session) and is live. Command reachable via `window.__logos.execute("studio.toggle_livestream", {...})` + MCP + voice. Tested end-to-end in the PR; no additional reverification in this pass.
- **`/dev/shm/hapax-compositor/` has 34 files** on a live compositor — a richer signal surface than just the documented `degraded.json`. Most are Cairo-layer state (album cover PNG, yt-attribution text files, yt-frame JPEGs, snapshot JPEGs, fx-snapshot, health.json, token-ledger.json, playlist.json, consent-state.txt, hls-analysis.json, memory-snapshot.json, etc.). The full consumer map for each of these is not enumerated in this pass.

## The degraded-signal dead path — detail

`agents/studio_compositor/budget_signal.py` defines:

- `DEFAULT_SIGNAL_PATH = Path("/dev/shm/hapax-compositor/degraded.json")`
- `build_degraded_signal(tracker: BudgetTracker) -> dict[str, object]` — pure function, takes a snapshot of per-source skip counts from `BudgetTracker` and returns the structured dict
- `publish_degraded_signal(tracker: BudgetTracker, path: Path | None = None) -> None` — writes the JSON to the path atomically via the shared `atomic_write_json` helper

`grep -rn 'publish_degraded_signal'` across the source tree returns:

```text
agents/studio_compositor/budget.py:295   — docstring reference in `publish_costs` (`:func:`) only
agents/studio_compositor/budget_signal.py:113   — the definition itself
docs/superpowers/handoff/2026-04-12-session-handoff.md   — PR #672 ship record
docs/superpowers/audits/2026-04-12-compositor-unification-audit.md   — audit entry: "no VLA subscriber"
tests/...   — unit test
```

**No production caller.** The compositor main loop does not invoke `publish_degraded_signal` at any frame cadence. The `BudgetTracker` that it would be given already runs inside the compositor (`publish_costs` is used to produce `costs.json`), but the `degraded.json` variant is never fed. This is consistent with what the `/dev/shm/hapax-compositor/` directory listing shows: there is a `health.json`, a `memory-snapshot.json`, a `costs.json` (per the `publish_costs` wiring), but **no `degraded.json`**.

**Implication for VLA stimmung gating:** the design intent was that the compositor's degradation pressure could transition stimmung state (to shed load, surface a banner, or gate SEEKING). In the current state, compositor degradation is **invisible to the rest of the council** — the stimmung dimension does not shift, the VLA does not see it, the operator cannot react to it. The only place the degradation is observable is inside the compositor process itself, where it is consumed by `BudgetTracker` to skip over-budget renders. The compositor protects itself but does not tell anyone.

This is the single most load-bearing cross-system finding from this phase.

## sd_notify watchdog — correct wiring verified

From `agents/studio_compositor/lifecycle.py` lines 157–186:

```python
from .__main__ import sd_notify_ready, sd_notify_status, sd_notify_watchdog

sd_notify_ready()
sd_notify_status(f"{cameras_active}/{len(compositor._camera_status)} cameras live")

def _watchdog_tick() -> bool:
    # Liveness gate: at least one camera currently flagged active.
    # The per-camera GStreamer watchdog (2s timeout) marks offline on
    # stalls, so "any active" = "at least one producer still flowing".
    with compositor._camera_status_lock:
        any_active = any(s == "active" for s in compositor._camera_status.values())
    if any_active and compositor._running:
        sd_notify_watchdog()
        try:
            from . import metrics
            metrics.mark_watchdog_fed()
        except Exception:
            pass
    return compositor._running

# 20s interval keeps us well under the 60s WatchdogSec.
GLib.timeout_add(20 * 1000, _watchdog_tick)
```

Observations:

- **Liveness is genuinely frame-flow-coupled.** The gating is on `compositor._camera_status[role] == "active"`, and `_camera_status` is written by the `PipelineManager.swap_to_primary` / `swap_to_fallback` methods and by state machine transitions. If every producer silently stops emitting frames, the per-camera GStreamer `watchdog` element (2 s element-local timeout per `camera_pipeline.py`) fires → state machine transitions the role out of HEALTHY → `_camera_status[role]` flips off "active" → the `_watchdog_tick` sees `any_active = False` → `sd_notify_watchdog` is **not** called → after 60 s, systemd kills the unit with SIGABRT.
- **GLib main loop dependency.** The timeout is added via `GLib.timeout_add`, so it fires only if the GLib main loop is running and responsive. If the main loop is blocked for > 40 s (the margin between 20 s tick and 60 s `WatchdogSec`), the watchdog misses a tick. The compositor unification epic's CairoSource refactor moved all Cairo rendering off the GLib streaming thread, so the main-loop-block class of failure should be rare. But **swap thrash during memory-leak trajectory (see Phase 2) could theoretically stall the main loop via page-in latency**. The actual 15:53 OOM-kill event was a SIGKILL from the kernel OOM killer, not a watchdog-expiry kill — systemd logged `'oom-kill'`, not `'watchdog'`. So at that failure event, the watchdog was still being fed right up until the kernel killed the process. `[inferred]` This suggests the leak trajectory did not stall the GLib main loop enough to trip the watchdog; OOM happened first.
- **Metric wiring:** `metrics.mark_watchdog_fed()` is called alongside `sd_notify_watchdog`, so `studio_compositor_watchdog_last_fed_seconds_ago` reflects the same cadence. Live reading at 16:07 was 16.23 s (< 20 s — plausible).

**Conclusion:** sd_notify watchdog is correctly frame-coupled. Under the swap-thrash-precedes-watchdog-trip hypothesis, this design is robust: swap thrash severe enough to stall the main loop beyond 40 s would be a *different* failure than the OOM kill seen in the 15:53 event.

## `studio.toggle_livestream` command surface — live

Per `alpha.yaml` at 20:49 CDT and PR #730 (`feat: studio.toggle_livestream affordance handler`):

- **Command name:** `studio.toggle_livestream`
- **Reachable via:**
  - `window.__logos.execute("studio.toggle_livestream", { ... })` from the hapax-logos Tauri frontend
  - WebSocket command relay on `ws://localhost:8052/ws/commands` (Rust, inside Tauri)
  - MCP via `hapax-mcp` (per council CLAUDE.md § Command Registry)
  - Voice via the affordance pipeline (toggle_livestream is registered as a Gibson-verb affordance)
- **Handler:** `agents/studio_compositor/compositor.py` + `state.py` + `pipeline.py` (grep confirms the three-module touch point)

This command was tested end-to-end in the PR that shipped it (2026-04-13 morning, before the camera epic retirement handoff). Not re-verified live in this research pass.

## `/dev/shm/hapax-compositor/` file inventory

34 files present at measurement time. Classified into three tiers:

**Tier 1 — known published signals (consumer presumed or verified):**

| file | likely consumer | status |
|---|---|---|
| `album-cover.png` + `album-state.json` | Cairo album overlay (intra-compositor) | live, seen in logs |
| `brio-operator.jpg`, `brio-room.jpg`, `brio-synths.jpg`, `c920-desk.jpg`, `c920-overhead.jpg`, `c920-room.jpg` | compositor camera snapshot tier (intra-compositor or external consumers) | live (files are recent, mtime within 1 s of observation) |
| `consent-state.txt` | compositor consent gate | `[inferred]` live, not grep-verified here |
| `fx-current.txt`, `fx-snapshot.jpg` | external monitoring (health dashboard?) | `[inferred]` live |
| `health.json` | health monitor, self-reported | live — health monitor presumably consumes |
| `hls-analysis.json` | HLS-side analysis (?) | `[inferred]` |
| `memory-snapshot.json` | something | `[inferred]`, worth a grep |
| `playlist.json` | director loop's playlist state | live (seen in compositor journal) |
| `smooth-snapshot.jpg`, `snapshot.jpg` | operator-facing preview | `[inferred]` |
| `token-ledger.json` | token pole overlay | live (journal: `TOKEN POLE EXPLOSION #N`) |

**Tier 2 — YouTube restream attribution:**

| file | purpose |
|---|---|
| `yt-attribution-0.txt`, `yt-attribution-1.txt`, `yt-attribution-2.txt` | video title/source for the three Sierpinski slots |
| `yt-frame-0.jpg`, `yt-frame-1.jpg`, `yt-frame-2.jpg` | per-slot frame snapshots |

**Tier 3 — notification and state:**

| file | purpose |
|---|---|
| `last-ntfy-<role>.txt` × 6 | per-camera ntfy throttle state (1 file per role) |
| `music-attribution.txt`, `track-lyrics.txt` | music subsystem |
| `visual-layer-state.json` | VLA state `[inferred]` |
| `watershed-events.json` | TBD |

**Missing but expected:**

- `degraded.json` — see § dead path above

**Follow-up tickets** for this inventory:
- **`docs(compositor): ship a `/dev/shm/hapax-compositor/` inventory reference`** — the 34 files should be enumerated with schema, cadence, and producer↔consumer relationships. The operator and future research sessions will need this. *(Severity: low-medium. Affects: researcher velocity.)*

## sdnotify-watchdog cross-reference with ALPHA-FINDING-1

Alpha's retirement summary (§`inflections/20260413-193500-alpha-session-retirement-summary.md`) hinted at a "swap-thrash-watchdog-trip theory" during the earlier session. Beta's Phase 2 § "Compositor restart boundary" confirms the 15:53 failure was **`oom-kill`, not `watchdog`** — `systemd[]: studio-compositor.service: Failed with result 'oom-kill'`. So the sequence at 15:53 was:

1. Pool/allocator leak grew anon-memory to the 6 GiB MemoryMax ceiling.
2. `MemoryHigh=infinity` disabled the kernel reclaim throttle.
3. Kernel did begin reclaiming to zram when it had no choice (Pss_Anon > MemoryMax), but reclaim is slower than allocation near the ceiling.
4. Kernel OOM-killer fired SIGKILL on the compositor process **before** the GLib main loop had stalled long enough to miss 2 watchdog ticks (40 s).
5. Systemd logged the oom-kill result and restarted the unit with 10 s delay (`RestartUSec=10s`).
6. PID 2529279 came up at 15:53:23.

**The watchdog did not fail** — it was racing with the kernel OOM and the OOM won. This is why the "swap-thrash-watchdog-trip" theory was not borne out for this specific event. In a future OOM with different memory pressure profiles, the race could tip the other way and watchdog-trip could fire first. Either outcome results in service restart; they differ only in which systemd unit result is logged (`oom-kill` vs `watchdog`).

## Post-ALPHA-FINDING-1-fix memory re-measurement plan

The brief asks beta to re-measure the compositor's steady-state memory footprint after alpha's Option A lands, as an independent check that the torch removal produced the expected memory drop. Current pre-fix baseline (for later comparison):

| signal | value on PID 2529279 at T+21 min | file |
|---|---|---|
| VmRSS | 6.06 GB (at 6 GiB cap, kernel reclaim active) | Phase 2 |
| VmSwap | 2.06 GB | Phase 2 |
| RssAnon | 5.44 GB | Phase 2 |
| libtorch mappings | 35 | Phase 2 |
| CUDA-family mappings | 126 | Phase 2 |
| threads | 109 | Phase 2 |
| OOM rate estimate (prior 51-min run) | ~74 MB/min VmRSS, 0 → OOM in 51 min | Phase 2 |

**Post-Option-A expectations:**

- `ls /proc/$PID/map_files/ | grep -c libtorch` → **0** (torch removed from process)
- VmRSS steady state → 1.5–2.0 GB range (alpha's estimate in Finding 1 audit)
- CUDA-family mappings → ≤ ~30 (GStreamer NVENC CUDA context only, no torch CUDA stack)
- Threads → ≤ ~80 (loses torch worker threads)
- NRestarts → stops growing (OOM path closed)

Re-measure ≥ 30 min after Option A PR merges and `hapax-rebuild-service.timer` picks up the new binary. File re-measurement under `docs/research/2026-04-13/camera-stability/phase-6-post-fix-memory.md` and cross-reference both numbers in the handoff.

## Follow-up tickets

1. **`fix(compositor): wire budget_signal.publish_degraded_signal into the compositor loop`** — the publisher is shipped but never called. Add a call at an appropriate cadence (every 1 s, or at end of every rendered frame, or on BudgetTracker threshold crossing). Second ticket needed to implement the VLA subscriber that maps the signal into a stimmung dimension. Mentioned in the 2026-04-12 audit as "no VLA subscriber", reality is worse: producer and consumer both absent. *(Severity: medium. Affects: cross-system observability of compositor render budget pressure. Implication: stimmung cannot gate SEEKING or surface banners on compositor load.)*

2. **`feat(vla): subscribe to /dev/shm/hapax-compositor/degraded.json`** — pair ticket with #1. After #1 lands, the VLA stimmung reader should poll `degraded.json` with the same cadence as other /dev/shm signal files, map `degraded_source_count / total_active_sources` to a stimmung dimension (candidate: shed-load pressure or a new `compositor_distress` field), and feed into the existing stimmung reader pipeline. *(Severity: medium, depends on #1.)*

3. **`docs(compositor): enumerate /dev/shm/hapax-compositor/ files with schema + consumer map`** — 34 files, ad-hoc inventory above. A reference doc would save every future research session a grep walk. *(Severity: low. Affects: research velocity.)*

4. **`research(compositor): re-measure memory footprint after ALPHA-FINDING-1 Option A lands`** — numbers from this doc are the baseline. Use the same commands (smaps_rollup, map_files, /proc/status) on the post-fix PID. File as `phase-6-post-fix-memory.md`. Blocked on Option A merge. *(Severity: high — this is the operator's primary validation of the fix. Affects: claim that Option A closed the leak.)*

5. **`fix(compositor): add wall_clock field + monotonic timestamp to `health.json` and other /dev/shm signal files without one`** — paired with audit recommendation. Readers cannot distinguish stale from current without `stat()`-ing the file, which is fragile across filesystem clock drift. *(Severity: low.)*

## Acceptance check

- [x] budget_signal end-to-end checked: publisher shipped but never called; consumer not shipped.
- [x] sdnotify watchdog wiring traced and cross-referenced with ALPHA-FINDING-1 OOM vs watchdog-trip race.
- [x] Post-FINDING-1 pre-fix baseline numbers captured and the post-fix re-measurement method documented.
- [x] 34-file `/dev/shm/hapax-compositor/` inventory with tiered consumer classification.
- [~] Full compositor command surface audit (command server → registry bridge, window.__logos commands, voice affordances, fortress-mode gates). Only `studio.toggle_livestream` explicitly verified; the remaining 5 compositor.* commands (per alpha's inherited-tickets list #5) are deferred. See follow-up.
- [ ] Full `visual-layer-aggregator` integration walk (which compositor signals flow into VLA stimmung vs which are dropped). Deferred — requires deeper walk beyond time budget.
