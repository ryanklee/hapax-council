# DEVIATION-040: Total Affordance Field Expansion

**Date:** 2026-04-03
**Phase at time of change:** Cycle 2, Phase A (baseline collection, 0 valid sessions)
**Filed by:** Alpha session (Claude Code)
**Approved by:** Operator

## Original Protocol

The Cycle 2 pre-registration (§9) requires that any post-data-collection code change to frozen paths be documented as a deviation. The experiment freeze enforcement hook prevents changes to frozen files (`grounding_ledger.py`, `grounding_evaluator.py`, `stats.py`, `experiment_runner.py`, `eval_grounding.py`). Changes to behavioral paths (`conversation_pipeline.py`, `persona.py`, `conversational_policy.py`) require deviation records.

## Deviation Description

The Total Affordance Field epic (spec: `docs/superpowers/specs/2026-04-03-total-affordance-field-design.md`) introduces:

1. **Phase 1 — Shared Pheromone Field:** Fixed `render_impingement_text()` narrative inclusion, stimmung stance field mismatch, plan defaults cache, visual chain physarum retargeting, cross-daemon activation summaries. PR #573, merged.

2. **Phase 2 — World Perception:** Promoted sensors (weather, time, music, goals) into imagination context, created centralized affordance registry (81 affordances across 9 domains), wired Reverie to shared registry, audited backend coverage. PR #574.

3. **Phase 3 — Total Expression (Track A):** Implemented 5 content resolvers for recruited affordances (narrative text, episodic/knowledge/profile recall via Qdrant, waveform viz). Extended mixer dispatch for `knowledge.*` and `space.*` domains.

## Frozen Paths Affected

**None.** No frozen experiment files were modified:

| Frozen file | Modified? | Verification |
|---|---|---|
| `grounding_ledger.py` | No | `git diff origin/main -- agents/hapax_daimonion/grounding_ledger.py` = empty |
| `grounding_evaluator.py` | No | Same |
| `stats.py` | No | Same |
| `experiment_runner.py` | No | Same |
| `eval_grounding.py` | No | Same |
| `conversation_pipeline.py` | No | Same |
| `persona.py` | No | Same |
| `conversational_policy.py` | No | Same |

## Behavioral Paths: Impact Analysis

### Tool recruitment path (`conversation_pipeline.py:995-1009`)

The tool recruitment gate fires at line 995: `if self.tools and self._tool_recruitment_gate:`. During experiment sessions, `self.tools` is empty (tools disabled by experiment configuration). The affordance expansion registers new affordances in the shared Qdrant collection, but the tool recruitment gate only fires when tools are populated — which they are not during experiment sessions. **Zero impact on experiment DVs.**

### Volatile content gate (`conversation_pipeline.py:360-431`)

All volatile content (goals, health, nudges, DMN, imagination, phenomenal context, salience) is gated behind `_lockdown = self._experiment_flags.get("volatile_lockdown", False)`. During Phase A, `volatile_lockdown=True`. The affordance expansion adds new content to the DMN imagination context and Reverie visual surface — neither of which reaches the conversation pipeline's system prompt during lockdown. **Zero impact on experiment DVs.**

### Impingement consumer loop (`run_loops_aux.py`)

The affordance expansion changes what the impingement consumer loop can recruit (more affordances in Qdrant), but the consumer loop's speech production path is gated by session state and `turn_count >= 1`. During experiment sessions, these gates are controlled by the experiment runner, not by the affordance pipeline. The proactive speech gate (`should_speak()`) is independent of which affordances are registered. **Zero impact on experiment DVs.**

### Reverie and DMN subsystems

All Phase 1-3 changes operate in the Reverie mixer, DMN sensor layer, and imagination daemon — independent processes from the voice daemon's conversation pipeline. They share `/dev/shm` trace files (stigmergic coordination) but do not write to any file the conversation pipeline reads during experiment sessions. **Zero impact on experiment DVs.**

## Impact on Specific Claims

| Claim | Affected? | Justification |
|---|---|---|
| Claim 1 (stable frame) | No | Phase A baseline is `volatile_lockdown=True`, no tools. Affordance changes cannot reach the system prompt. |
| Claim 2 (message drop) | No | Message drop logic is internal to conversation pipeline. |
| Claim 3 (cross-session) | No | Session memory uses `operator-episodes` Qdrant collection. Affordance registry uses `affordances` collection. No interaction. |
| Claim 4 (sentinel) | No | Sentinel is a static prompt injection, unrelated to affordance retrieval. |
| Claim 5 (salience correlation) | No | `activation_score` is computed by SalienceRouter, not AffordancePipeline. The salience router code is unchanged. |
| Claim 6 (Bayesian tools) | **Noted** | USR is the mechanism Claim 6 wants to test. The tool recruitment gate (`ToolRecruitmentGate`) already exists and uses the AffordancePipeline for tool selection. Expanding the affordance registry does not change the gate's mechanism — it changes what tools are available. Claim 6's Phase A ("monolithic tools") can still be reconstructed by setting `self.tools` to the full tool list without the gate. Pre-registration of Claim 6 should document this architectural state. |

## Conclusion

The Total Affordance Field expansion operates entirely in subsystems orthogonal to the experiment's measurement path. The experiment's `volatile_lockdown` and `experiment_mode` gates provide complete isolation. No frozen files were touched. No behavioral paths were modified. Phase A baseline collection is unaffected.

The formal deviation is filed for transparency and to document the verification, not because any frozen path was actually modified.

## Compensating Controls

1. Experiment freeze pre-commit hook remains active and would have blocked any accidental frozen-path modifications
2. All new tests (16 total) pass alongside existing experiment test infrastructure
3. The `experiment_mode` gate in `conversation_pipeline.py` was verified by code inspection (lines 360-431, 995-1009) to prevent affordance content from reaching experiment sessions
