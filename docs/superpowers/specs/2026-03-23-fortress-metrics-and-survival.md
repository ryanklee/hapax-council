# Fortress Metrics and Survival Tracking

**Status:** Design (measurement specification)
**Date:** 2026-03-23
**Builds on:** Fortress State Schema, Fortress Governance Chains, Fortress Suppression Topology

---

## 1. Purpose

Survival time is the primary metric. A fortress that survives longer under compositional governance than under simpler approaches validates the architecture. Secondary metrics diagnose why the fortress lived or died: which governance chains contributed, which suppression fields fired, which CompoundGoals succeeded or failed.

---

## 2. Primary Metric — Survival Time

Survival time is measured in game ticks from embark to fortress death or retirement.

Fortress death is defined as: all citizens dead, OR no food AND no drink AND no seeds (unrecoverable state).

Session records are stored in `profiles/fortress-sessions.jsonl`, one JSON object per line.

Each session record:

```json
{
  "session_id": "uuid",
  "fortress_name": "Boatmurdered",
  "start_time": "ISO-8601 wall clock",
  "end_time": "ISO-8601 wall clock",
  "start_tick": 0,
  "end_tick": 483840,
  "survival_days": 403,
  "survival_years": 1.2,
  "peak_population": 67,
  "final_population": 0,
  "cause_of_death": "tantrum_spiral",
  "era_reached": "growth",
  "governance_config": { "...snapshot of chain configs..." },
  "total_llm_calls": 847,
  "total_llm_cost_usd": 12.50,
  "total_commands_issued": 3421,
  "events_summary": { "sieges": 2, "migrants": 5, "deaths": 34, "moods": 3 }
}
```

---

## 3. Secondary Metrics — Governance Effectiveness

Per governance chain, per session, the following counters are maintained:

- **Commands issued** — count, broken down by command type.
- **Commands vetoed** — count, broken down by veto predicate.
- **Commands arbitrated** — count of arbitration events, with win/loss outcome per chain.
- **Suppression field activity** — time spent suppressed as a percentage of session duration, maximum suppression level reached, total suppression events.
- **LLM usage** — call count, token count (input and output), cost in USD, mean and p95 latency.

These metrics are stored alongside the session record. They enable queries such as: "military_commander issued 45 commands, 12 were vetoed by resource_pressure, 3 were arbitrated against crisis_responder."

---

## 4. Tertiary Metrics — Decision Quality

### Per CompoundGoal

- Time from ACTIVE to COMPLETED (or FAILED), measured in game ticks.
- SubGoals activated versus SubGoals completed.
- Context selector accuracy: whether the selected subgoals addressed the actual need, evaluated retrospectively.
- Timeliness: whether the goal was completed before the crisis it was preparing for materialized.

### Per Episode (from EpisodeBuilder)

- Fortress state delta: population change, food stockpile change, wealth change during the episode window.
- Causal attribution: which governance chain's actions drove the observed delta.

---

## 5. Comparative Framework

To validate the forcing function thesis, three conditions are compared:

1. **Baseline** — Dwarf Fortress running with DFHack built-in automation only (labormanager, workflow, autolabor). No LLM involvement.
2. **Simple LLM** — A single LLM agent with full game state access. No governance primitives, no suppression, no arbitration.
3. **Compositional** — Full 6-chain governance with suppression topology, arbitration, and CompoundGoals.

Each condition runs a minimum of 5 sessions from identical embark conditions (same world seed, same embark location, same starting loadout). Survival time distributions are compared using the Mann-Whitney U test, appropriate for small sample sizes with non-normal distributions.

---

## 6. Langfuse Integration

All LLM calls within governance chains are traced to Langfuse with the following tags:

- `fortress_session_id` — links the trace to a specific session record.
- `governance_chain` — identifies which chain made the call.
- `compound_goal_id` — present when the call was made in service of a specific CompoundGoal.
- `game_tick` — the in-game tick at the time of the call.

This tagging enables Langfuse queries such as "show all LLM decisions during siege events" or "compute cost breakdown by governance chain across sessions."

---

## 7. Stimmung Integration

Fortress stimmung maps onto the existing 10-dimension model. Six dimensions are active in fortress mode; four biometric/voice dimensions are not applicable and are zeroed.

| Stimmung Dimension | Fortress Mapping | Source |
|---|---|---|
| health | fortress health_checks pass rate | health_monitor |
| resource_pressure | max(food_pressure, drink_pressure) | FortressState |
| error_rate | command failure rate | bridge results |
| processing_throughput | governance ticks per minute | chain activity |
| perception_confidence | state.json freshness (age since last poll) | bridge polling |
| llm_cost_pressure | session LLM cost relative to budget | Langfuse |
| operator_stress | N/A | — |
| operator_energy | N/A | — |
| physiological_coherence | N/A | — |
| grounding_quality | N/A | — |

The four N/A dimensions remain at zero. They do not contribute to stimmung calculations in fortress mode.

---

## 8. API Endpoints

- `GET /api/fortress/metrics` — returns current session metrics (live, updated each governance tick).
- `GET /api/fortress/sessions` — returns historical session list with survival times and summary statistics.
- `GET /api/fortress/sessions/{id}` — returns a detailed session record including per-chain governance metrics.
- `GET /api/fortress/compare` — returns a comparative summary across experimental conditions, including Mann-Whitney U statistics.

---

## 9. Notification Integration

Notifications are sent via the existing `shared/notify.py` infrastructure.

- **Fortress death** — ntfy urgent priority notification. Includes cause of death and total survival time.
- **New survival record** — ntfy default priority notification. Triggered when a session exceeds the previous longest survival time across all sessions of the same condition.
- **Siege start/end** — ntfy default priority notification. Includes siege force composition on start, outcome on end.
