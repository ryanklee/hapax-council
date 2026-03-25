# Fortress Pre-Integration Fixes — Gap Closure Before Live Testing

**Status:** Design (mechanical fixes)
**Date:** 2026-03-25
**Builds on:** Fortress Wiring Integration, Agent-Environment Boundary

---

## 1. Problem Statement

A deep audit of the fortress governance system identified 4 blocking issues and 3 high-priority issues that would cause failures or degradation during live integration with Dwarf Fortress + DFHack. All are mechanical wiring gaps — no architectural changes required.

## 2. Blocking Issues

### 2.1 Three Observation Tools Missing from Dispatch Table

**Current:** `__main__.py` dispatch table (lines 251-271) maps 9 tools. The tools registry (`tools_registry.py`) defines 12 tools and the deliberation prompt offers all 12 to the LLM.

**Missing:** `observe_region`, `describe_patch`, `survey_floor`

**Fix:** Add three entries to the dispatch dict in `__main__.py`:

```python
"observe_region": lambda patch_id="": observe_region(
    state, self._memory_store, budget, patch_id
),
"describe_patch": lambda patch_id="": describe_patch_tool(
    state, self._memory_store, budget, patch_id
),
"survey_floor": lambda z_level=0: survey_floor(
    state, self._memory_store, budget, z_level
),
```

Add the missing imports from `observation.py`: `observe_region`, `describe_patch_tool`, `survey_floor`.

### 2.2 Five Subgoal Check Predicates Always Return False

**Current:** Five subgoals in `goal_library.py` use `check=lambda s: False`, making them impossible to complete. Parent goals depending on these subgoals will block forever.

| Line | Subgoal | Parent Goal | Fix |
|------|---------|-------------|-----|
| 139 | stockpile_weapons | prepare_for_siege | Check `s.weapon_count >= 10` (or similar stockpile check) |
| 145 | build_defenses | prepare_for_siege | Check `s.building_count > 0` with defense types |
| 250 | provide_materials | handle_strange_mood | Check mood no longer active in events |
| 265 | prepare_trade_goods | manage_trade | Check `s.prepared_meals > 0 or s.crafted_goods > 0` |
| 280 | produce_mandated_item | handle_mandate | Check mandate no longer active |

**Fix:** Replace each `lambda s: False` with a real predicate using available `FastFortressState` fields. Where the exact field doesn't exist in the schema, use a reasonable proxy (e.g., total items in stockpile, absence of the triggering event).

### 2.3 AdvisorChain Instantiated But Never Evaluated

**Current:** `wiring.py` line 40 creates `self._advisor = AdvisorChain()` but `evaluate()` never calls it. The advisor chain exists as a module with a complete implementation.

**Fix:** The advisor is designed for on-demand strategic queries, not per-tick evaluation. It should not be called in the main evaluation loop. Remove the instantiation from `FortressGovernor.__init__()` — the advisor will be used via the deliberation loop's tool dispatch when the LLM requests strategic advice. No wiring change needed; just clean up the dead instantiation.

### 2.4 StorytellerChain Evaluated But Output Discarded

**Current:** `wiring.py` lines 164-165 evaluate the storyteller chain but the result is never used. The comment says "handled separately" but there is no separate handler.

**Fix:** The storyteller produces narrative observations, not game commands. Its output should feed into `EpisodeBuilder.observe()` which already exists in the governance loop. Wire the storyteller's action into the episode builder:

```python
story_veto, story_action = self._storyteller.evaluate(state)
if story_action.action != "no_action" and story_veto.allowed:
    # Storyteller narrative feeds episode builder, not command list
    self._last_story_action = story_action
```

Then in `__main__.py`'s governance loop, after `governor.evaluate()`:

```python
if governor._last_story_action:
    episode_builder.observe(governor._last_story_action)
    governor._last_story_action = None
```

## 3. High-Priority Issues

### 3.1 Dead Modules

Three files are never imported: `query.py`, `blueprints.py`, `arbiter_config.py`. These represent incomplete refactoring. The blueprint system has a base class with `NotImplementedError` and no subclasses.

**Fix:** Leave in place — these are future extension points, not bugs. Add a comment header to each marking them as stubs.

### 3.2 TODO: Wire Decision Log

`__main__.py` line 290 passes `recent_decisions=[]` to the deliberation loop. The deliberation prompt references recent decisions for context but always gets an empty list.

**Fix:** Track the last N commands produced by `governor.evaluate()` and pass them as `recent_decisions`.

## 4. Files Changed

| File | Change |
|------|--------|
| `agents/fortress/__main__.py` | Add 3 missing tool dispatch entries, wire decision log, wire storyteller→episode |
| `agents/fortress/goal_library.py` | Replace 5 `lambda s: False` with real predicates |
| `agents/fortress/wiring.py` | Remove unused AdvisorChain instantiation, add story_action output |

## 5. Scope Exclusions

- No new observation tools. Only wiring existing tools into dispatch.
- No schema changes. All predicates use existing `FastFortressState` fields.
- No test changes. Existing 567 tests should continue passing; new tests for the fixed predicates.
- No Lua changes. Bridge protocol unchanged.
