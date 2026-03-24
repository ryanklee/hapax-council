# Fortress Wiring Integration — Runtime Loop and Gap Resolution

**Status:** Design (integration specification)
**Date:** 2026-03-24
**Builds on:** All 11 prior fortress specs

This specification resolves the 28 audit findings by defining: (1) the missing runtime entrypoint, (2) governor state exposure for API consumption, (3) wiring of all disconnected components.

---

## 1. Problem Statement

The fortress governance system contains 20+ modules, 441 tests, 7 chains, 5 suppression fields, spatial memory, attention budget, creativity system, episodes, narrative, metrics, goals, and blueprints. All components pass unit tests in isolation but have never been connected into a running system. The root cause is a missing `__main__.py` entrypoint that instantiates and orchestrates all components. Every module functions correctly in its own test harness; no module participates in a live governance loop.

---

## 2. Runtime Entrypoint (`agents/fortress/__main__.py`)

The entrypoint follows the `visual_layer_aggregator` daemon pattern established in the council codebase.

```python
async def main():
    governor = FortressGovernor(config)
    bridge = DFHackBridge(config.bridge)

    while running:
        state = bridge.read_state()
        if state is None:
            await asyncio.sleep(5.0)  # DF not running, poll slowly
            continue

        # Governor evaluation cycle
        commands = governor.evaluate(state)

        # Dispatch commands through bridge
        for cmd in commands:
            bridge.send_command(cmd.action, **cmd.params)

        # Episode lifecycle
        episode = episode_builder.observe(state)
        if episode:
            narrative = format_narrative_fallback(episode)
            episode.narrative = narrative
            write_chronicle_entry(episode)

        # Metrics update
        tracker.update(state)
        if tracker.is_fortress_dead(state):
            tracker.finalize(cause="detected")
            break

        # Expose state for API
        write_governor_state_to_shm(governor, tracker, goal_planner)

        await asyncio.sleep(2.0)  # 2s tick
```

Two concurrent loops run via `asyncio.gather()`:

- **Governance loop (2s tick):** Read state, evaluate chains, dispatch commands, observe episodes, update metrics.
- **Maintenance loop (30s tick):** Spatial memory consolidation and pruning, goal timeout checks, creativity metrics snapshot.

---

## 3. Governor State Exposure

Live state is written to `/dev/shm/hapax-fortress/` for API consumption. This follows the same pattern used by `visual-layer-state.json`.

Files:

- `/dev/shm/hapax-fortress/governance.json` — Chain activity, suppression levels, last actions taken.
- `/dev/shm/hapax-fortress/goals.json` — Active CompoundGoals with subgoal states.
- `/dev/shm/hapax-fortress/metrics.json` — Live session metrics.

All writes use the atomic write-then-rename pattern: write to a temporary file in the same directory, then `os.rename()` to the target path. This guarantees readers never observe a partial write.

---

## 4. Component Wiring Checklist

| Component | Current State | Fix |
|-----------|---------------|-----|
| GoalPlanner | Dead code | Instantiate with `DEFAULT_GOALS`, call `evaluate()` before chains |
| EpisodeBuilder | Dead code | Instantiate, call `observe()` each tick |
| SessionTracker | Dead code | Instantiate, `start()`/`update()`/`finalize()` lifecycle |
| CreativityMetrics | Dead code | Instantiate, `record_action()` on each dispatched command |
| SpatialMemoryStore | Dead code | Instantiate, pass to observation tools |
| AttentionBudget | Dead code | Instantiate, reset at day boundary |
| Advisor chain | Instantiated, never evaluated | Add `evaluate()` call (query-driven, not every tick) |
| Storyteller output | Computed, discarded | Feed to episode narrative on boundary |
| Command factories | Never used | Replace inline `FortressCommand` construction |
| Bridge `extract_events` | Never called | Use in episode boundary detection |
| FortressPosition | Never used | Compute from state, include in `/dev/shm` exposure |

---

## 5. Creativity Suppression Fix

`chains/creativity.py` contains a bug: predicates call `creativity_available(stress, 0.0)` with a hardcoded zero suppression value. The suppression field is computed elsewhere but never passed through to the creativity chain's evaluation.

Fix: set the suppression value as an attribute on `CreativityChain` before evaluation:

```python
self._creativity.suppression_value = creativity_supp
creat_veto, creat_action = self._creativity.evaluate(state)
```

This is preferred over passing suppression as an `evaluate()` parameter because it preserves the uniform `evaluate(state)` signature across all chains. The alternative — computing `creativity_available` in `wiring.py` and injecting the result as a context value into `VetoChain` predicates — adds indirection without benefit.

---

## 6. Goal Predicate Fixes

Several goal predicates return hardcoded `False`, bypassing actual state inspection. Replace these with type-dispatched checks using `isinstance`:

```python
def _has_beds(state: FastFortressState) -> bool:
    if isinstance(state, FullFortressState):
        return state.buildings.beds >= state.population
    return False  # Unknown without full state

def _has_workshops(state: FastFortressState) -> bool:
    if isinstance(state, FullFortressState):
        return len(state.workshops) >= 3
    return False

def _has_entrance(state: FastFortressState) -> bool:
    if isinstance(state, FullFortressState):
        return state.buildings.doors > 0
    return False
```

When only a `FastFortressState` is available, predicates conservatively return `False`. Goals remain unresolved until a full state read provides the data required for evaluation.

---

## 7. API Route Wiring

Replace placeholder returns in fortress API routes with `/dev/shm` reads:

```python
@router.get("/governance")
async def get_fortress_governance():
    path = Path("/dev/shm/hapax-fortress/governance.json")
    if not path.exists():
        raise HTTPException(503, "Governor not running")
    return json.loads(path.read_text())
```

The same pattern applies to `/goals` and `/metrics`. A 503 response indicates the governor process is not running or has not yet written its first state snapshot. This is consistent with the convention used by other `/dev/shm`-backed routes in the logos API.

---

## 8. Path Normalization

All relative `Path("profiles/...")` references must be replaced with `shared.config.PROFILES_DIR / "..."`. Affected files:

- `narrative.py` — `CHRONICLE_PATH`
- `metrics.py` — `SESSIONS_PATH`
- `query.py` — both path references

Relative paths break when the process working directory differs from the repository root. The systemd unit sets `WorkingDirectory` to the repository root, but defensive path resolution prevents failures if the unit configuration changes.

---

## 9. Systemd Unit

```ini
[Unit]
Description=Fortress Governor — DF forcing function governance loop
After=logos-api.service hapax-secrets.service
Requires=hapax-secrets.service

[Service]
Type=simple
WorkingDirectory=/home/hapax/projects/hapax-council
EnvironmentFile=/run/user/1000/hapax-secrets.env
ExecStart=/home/hapax/projects/hapax-council/.venv/bin/python -m agents.fortress
Restart=on-failure
RestartSec=10
MemoryMax=512M
SyslogIdentifier=fortress-governor

[Install]
WantedBy=default.target
```

The unit depends on `hapax-secrets.service` (credential loading) and orders after `logos-api.service` (API must be available for state exposure). `MemoryMax=512M` bounds resource consumption; the governor holds only the current tick's state in memory and writes episodes to disk.

---

## 10. Files Changed

**New:**

- `agents/fortress/__main__.py` — Runtime entrypoint (governance loop, maintenance loop, `/dev/shm` state writer).
- `systemd/units/fortress-governor.service` — Systemd user unit.

**Modified:**

- `agents/fortress/wiring.py` — Wire GoalPlanner, EpisodeBuilder, SessionTracker, CreativityMetrics, SpatialMemoryStore, AttentionBudget.
- `agents/fortress/chains/creativity.py` — Fix suppression passthrough (remove hardcoded zero).
- `agents/fortress/goal_library.py` — Fix predicate hardcodes with `isinstance` dispatch.
- `agents/fortress/narrative.py` — Replace relative path with `PROFILES_DIR`.
- `agents/fortress/metrics.py` — Replace relative path with `PROFILES_DIR`.
- `agents/fortress/query.py` — Replace relative paths with `PROFILES_DIR`.
- `logos/api/routes/fortress.py` — Read from `/dev/shm` instead of returning placeholders.
