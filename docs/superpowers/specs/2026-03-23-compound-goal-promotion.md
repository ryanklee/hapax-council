# CompoundGoal Promotion: From Imperative to Declarative

**Status:** Design (type system extension specification)
**Date:** 2026-03-23
**Builds on:** Multi-Role Composition Design (§4, §9), Fortress Governance Chains, Perception Primitives Design

---

## §1 Why DF Forces the Promotion

The multi-role composition design specified CompoundGoals as imperative async methods with a B-path promotion criterion: ">10 goals or dynamic decomposition required." DF satisfies both criteria.

### 1.1 Count

DF requires 15+ compound goals minimum:

- `survive_winter` (food + shelter + clothing)
- `prepare_for_siege` (military + fortifications + stockpile weapons)
- `process_migrant_wave` (bedrooms + jobs + equipment)
- `establish_industry` (workshops + stockpiles + labor assignment)
- `respond_to_siege` (military deployment + burrow lockdown + medical)
- `handle_strange_mood` (workshop access + material sourcing)
- `establish_military` (forge equipment + create squads + train)
- `expand_fortress` (dig + build + furnish + assign rooms)
- `manage_trade` (depot + goods + negotiate)
- `breach_cavern` (military ready + wall off + explore)
- `establish_water` (cistern + well + irrigation)
- `handle_noble_demands` (production orders + room upgrades)
- `recover_from_crisis` (medical + morale + rebuild)
- `seasonal_planning` (crop rotation + caravan prep + construction schedule)
- `found_fortress` (initial embark sequence)

### 1.2 Dynamic Decomposition

`survive_winter` decomposes differently based on current food level, clothing availability, military threat, and population. The subgoal set is state-dependent and cannot be expressed as a fixed sequence.

---

## §2 CompoundGoal as a Type

CompoundGoal is promoted from pattern (imperative async) to type system primitive.

```python
@dataclass(frozen=True)
class SubGoal:
    id: str
    description: str
    chain: str  # which governance chain handles this
    preconditions: tuple[str, ...]  # SubGoal IDs that must complete first
    check: Callable[[FortressState], bool]  # is this subgoal satisfied?
    timeout_ticks: int  # max ticks before failure

@dataclass(frozen=True)
class CompoundGoal:
    id: str
    description: str
    subgoals: tuple[SubGoal, ...]
    context_selector: Callable[[FortressState], tuple[str, ...]]  # which subgoals to activate given current state
    priority: int
    created_at: float
```

Both types are frozen dataclasses. Immutability is required: goal definitions do not change after construction. State tracking is external to the goal definition.

---

## §3 Goal State Machine

```
PENDING -> ACTIVE -> COMPLETED
                  -> BLOCKED (subgoal dependency unmet for > timeout)
                  -> FAILED (all retries exhausted or fortress dead)
```

State transitions:

| From | To | Condition |
|------|----|-----------|
| PENDING | ACTIVE | Goal selected by goal planner |
| ACTIVE | COMPLETED | All context-selected subgoals satisfied |
| ACTIVE | BLOCKED | Dependency cycle detected or timeout exceeded |
| ACTIVE | FAILED | Critical subgoal impossible (e.g., required materials absent from embark) |
| BLOCKED | ACTIVE | Blocking condition resolved |
| FAILED | PENDING | Retry with different decomposition (LLM re-evaluates context) |

Invalid transitions (enforced by the state machine): COMPLETED to any state, FAILED to ACTIVE (must pass through PENDING for re-evaluation).

---

## §4 Goal Planner

The GoalPlanner is not a separate agent. It is a function called by the PipelineGovernor on each evaluation cycle.

```python
class GoalPlanner:
    active_goals: list[CompoundGoal]

    def evaluate(self, state: FortressState) -> list[SubGoal]:
        """Return subgoals that should be dispatched this tick."""
        # 1. For each active goal, run context_selector(state) to get relevant subgoals
        # 2. Filter to subgoals whose preconditions are met
        # 3. Filter to subgoals not already satisfied (check(state) == False)
        # 4. Sort by goal priority, then subgoal dependency order
        # 5. Return top N (bounded by governance semaphore)
```

Each returned SubGoal triggers its governance chain via Event publication. The chain handles it through the normal VetoChain/FallbackChain/Command flow. The GoalPlanner does not execute subgoals directly.

---

## §5 Context-Aware Decomposition

The `context_selector` function is the entry point for LLM reasoning within the goal system.

```python
def survive_winter_selector(state: FortressState) -> tuple[str, ...]:
    """Select subgoals based on current fortress state."""
    active = []
    if state.food_count < state.population * 10:
        active.append("emergency_food_production")
    if state.drink_count < state.population * 5:
        active.append("emergency_drink_production")
    if not has_warm_clothing(state):
        active.append("textile_production")
    if state.active_threats > 0:
        active.append("defensive_posture")  # can't forage if under siege
    return tuple(active)
```

Two categories of context_selector exist:

1. **Deterministic selectors.** Pure functions over FortressState. Used for goals with well-defined decomposition rules (e.g., `survive_winter`, `establish_water`).
2. **LLM-evaluated selectors.** Call the LLM with fortress state context for goals requiring tactical assessment (e.g., `respond_to_siege`, `breach_cavern`). The LLM output is constrained to return a subset of the goal's declared subgoal IDs.

---

## §6 Composition Ladder Integration

CompoundGoal occupies a new sublayer between L6 (ResourceArbiter) and L7 (governance composition):

| Layer | Existing | Addition |
|-------|----------|----------|
| L6 | ResourceArbiter, ExecutorRegistry, ScheduleQueue | -- |
| L6.5 | -- | GoalPlanner, CompoundGoal, SubGoal |
| L7 | compose_mc_governance, compose_obs_governance | compose_fortress_planner, compose_military_commander, etc. |

Data flow: GoalPlanner reads from L7 governance outputs (which subgoals are satisfied) and writes to L7 governance inputs (which subgoals to pursue). The GoalPlanner does not bypass the governance stack. All subgoal execution passes through the existing VetoChain and FallbackChain mechanisms.

---

## §7 Test Strategy

### 7.1 Matrix Dimensions

| Dimension | Coverage |
|-----------|----------|
| A: Construction | Create goals, subgoals, planners |
| B: Invariants | Frozen, DAG acyclic, no orphan subgoals |
| C: Operations | evaluate, context_select, state transitions |
| D: Boundaries | Empty subgoals, impossible goals, timeout=0 |
| E: Error paths | Circular dependencies, missing chains |
| F: Dog Star | Goal cannot bypass VetoChain, cannot dispatch without arbiter |
| G: Composition | GoalPlanner output is valid governance chain input |

### 7.2 Property-Based Tests

- For any CompoundGoal, `context_selector` never returns subgoal IDs not present in the goal's subgoal set.
- For any SubGoal, `preconditions` is a subset of the containing goal's subgoal IDs.
- `GoalPlanner.evaluate` is monotonic: once a subgoal is satisfied, it remains satisfied absent state regression.
- State machine transitions are valid: no COMPLETED to ACTIVE transition is reachable.

---

## §8 Backward Compatibility

The two existing imperative compound goals (`start_live_session`, `end_live_session`) are expressible as CompoundGoal instances with a trivial `context_selector` that always activates all subgoals in dependency order. The imperative async methods become syntactic sugar over the declarative type. No breaking changes to existing governance chains are required.
