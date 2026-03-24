# Fortress Narrative and Query Interface

**Status:** Design (narrative system specification)
**Date:** 2026-03-23
**Builds on:** Fortress Governance Chains (storyteller/advisor roles), Fortress State Schema, Fortress Metrics

---

## 1. Narrative Generation Architecture

The Storyteller governance chain produces narrative text from fortress episodes. It is not a separate system. It uses the existing episode, temporal band, and content scheduler infrastructure.

Flow:

1. `EpisodeBuilder` detects a fortress episode boundary (season change, siege start/end, migrant wave, death event, mood event).
2. The episode is stored in Qdrant (`operator-episodes` collection) with fortress-specific metadata.
3. The Storyteller chain is triggered by the episode boundary `Event`.
4. The Storyteller samples full `FortressState` and episode history via Combinator.
5. The LLM generates narrative text (1-3 sentences) from state and episode context.
6. The narrative is published to three destinations:
   - (a) Logos ground surface ambient text.
   - (b) Qdrant episode record (`narrative` field).
   - (c) `profiles/fortress-chronicle.jsonl`.

---

## 2. Episode Schema for Fortress

`FortressEpisode` extends the existing `Episode` dataclass with fortress-domain fields:

```python
class FortressEpisode(Episode):
    fortress_name: str
    game_tick_start: int
    game_tick_end: int
    season: int
    year: int
    trigger: str  # "season_change" | "siege" | "migrant" | "death" | "mood" | "milestone"
    population_delta: int
    food_delta: int
    wealth_delta: int
    events: list[FortressEvent]  # all events during this episode
    narrative: str  # LLM-generated narrative text
    governance_summary: dict[str, int]  # commands per chain during episode
```

The summary text used for vector embedding follows this template:

```
"{fortress_name} Year {year} {season}: {trigger}. Pop {pop_delta:+d}, food {food_delta:+d}. {narrative}"
```

This format ensures that semantic search over episodes captures the fortress identity, temporal position, trigger type, quantitative deltas, and generated narrative in a single embedding.

---

## 3. Query Interface

The operator queries the fortress via the investigation overlay. Query dispatch routes fortress-domain queries to the Advisor governance chain.

### 3.1 Query Types

| Type | Example | Resolution |
|------|---------|------------|
| **Temporal** | "What happened since the last siege?" | Retrieve episodes by time range, chain chronologically, synthesize narrative. |
| **Causal** | "Why did Urist die?" | Locate the `DeathEvent`, retrieve the surrounding episode, trace governance decisions that preceded the event. |
| **Strategic** | "Should I breach the cavern?" | Assess military readiness, stockpile levels, and historical outcomes from past sessions. |
| **Comparative** | "How does this fortress compare to my best run?" | Query `fortress-sessions.jsonl`, compare metrics across sessions. |
| **Predictive** | "Will we survive winter?" | The protention engine extrapolates food/drink consumption trends and evaluates military threat levels. |

### 3.2 Dispatch

All fortress queries are routed to the Advisor chain. The Advisor has read access to:

- Full `FortressState` (current snapshot).
- `operator-episodes` collection (filtered by `type: "fortress"`).
- `fortress-sessions.jsonl` (cross-session history).
- `fortress-chronicle.jsonl` (narrative log).

The Advisor synthesizes an answer from these sources and returns it to the investigation overlay for display.

---

## 4. Narrative Style

The Storyteller LLM prompt defines the following constraints:

- **Persona:** Fortress chronicler. Neutral, factual, occasionally wry. The tone matches Dwarf Fortress's own generated prose.
- **Length:** 1-3 sentences per episode.
- **Content:** What happened, to whom, what changed, and what the event means for the fortress.
- **Register:** Consistent with DF's textual conventions (e.g., "Urist McSmith has been struck down by a goblin pikeman. The fortress mourns.").
- **Exclusions:** No meta-commentary about the AI system, governance chains, or compositional architecture.

### 4.1 Examples

> Late Autumn, Year 3. A goblin siege of 40 strong arrived at the gates. The military held the killbox while 12 civilians were locked in burrows.

> Urist McFarmer has entered a fey mood and claimed a craftsdwarf's workshop. She demands turtle shell and rough gems.

> The caravan from the mountainhomes departed with 14,000\u2606 in trade goods. Our coffers grow.

---

## 5. Chronicle Persistence

`profiles/fortress-chronicle.jsonl` is an append-only log. Each line records one fortress episode:

```json
{
  "session_id": "uuid",
  "fortress_name": "Boatmurdered",
  "game_tick": 120000,
  "year": 3,
  "season": 2,
  "trigger": "siege",
  "narrative": "Late Autumn, Year 3. A goblin siege...",
  "population": 47,
  "food": 234,
  "wealth": 145000,
  "timestamp": "ISO-8601"
}
```

This file serves as a human-readable fortress history. It can be rendered as a scrollable timeline in Logos core depth.

---

## 6. Qdrant Integration

Fortress episodes are stored in the `operator-episodes` collection, shared with perception episodes.

- A `type: "fortress"` payload field distinguishes fortress episodes from perception episodes.
- Episodes are searchable by semantic query (e.g., "find me episodes where food was critically low").
- Cross-session retrieval is supported: past fortress knowledge remains available to the Advisor chain for strategic recommendations in subsequent sessions.

---

## 7. Content Scheduler Integration

Fortress narrative feeds into the existing `ContentScheduler` infrastructure.

| Parameter | Value |
|-----------|-------|
| Content source | `FORTRESS_NARRATIVE` |
| Relevance | Always high when fortress mode is active |
| Dwell time | 10-15 seconds per narrative fragment |
| Notification level | `make_aware` for normal events; `interrupt` for siege and death events |

---

## 8. Ground Surface Integration

When fortress mode is active, ambient text cycling on the ground surface displays fortress narratives in place of philosophical fragments. The same CSS animation is used (3-second ease-out fade with `translateY`). A secondary text line displays the fortress headline.
