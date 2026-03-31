# Real-Time Flow Events — Directional Call Visualization

**Date:** 2026-03-31
**Status:** Implemented
**Scope:** Backend event bus + instrumentation across 6 sources + Tauri SSE bridge + frontend dot animation + verified consumption map

## Problem

The system anatomy visualization shows topology (which nodes exist, which edges connect them) and discrete state (active/stale/offline). It does not show behavior — when agents communicate, what triggers what, how data flows through the system in real time. The operator cannot observe distributed behaviors: cascading rule firings, LLM call patterns, data flow through the filesystem-as-bus, or external service interactions.

## Design

### Principle

Every dot moving along an edge represents a real event that just happened. No dot moves without a corresponding system event. The visualization shows the system's actual distributed behavior as it occurs.

### Event Bus

In-process async event bus inside logos-api. Singleton, created at app startup, injected via FastAPI `app.state`.

```python
class EventBus:
    emit(event: FlowEvent)        # non-blocking, drops if buffer full
    subscribe() -> AsyncIterator   # SSE consumers connect here
    _ring: deque[FlowEvent](500)   # bounded buffer, newest wins
```

**FlowEvent schema:**

| Field | Type | Description |
|---|---|---|
| `ts` | float | Unix timestamp (time.time()) |
| `kind` | str | `shm.write` &#124; `engine.rule` &#124; `engine.action` &#124; `llm.call` &#124; `qdrant.op` &#124; `pi.detection` |
| `source` | str | Source agent/node ID |
| `target` | str | Target agent/node ID |
| `label` | str | Human-readable (rule name, model name, collection name) |
| `duration_ms` | float &#124; None | For calls with measurable duration |

**SSE endpoint:** `GET /api/events/stream` — JSON-encoded FlowEvents as they occur.

### Event Sources

Six sources, each wired to `emit()` at the point where the action happens:

| Source | Instrumentation point | `kind` | `source` → `target` | Latency |
|---|---|---|---|---|
| SHM write detection | FlowObserver scan loop — compare mtimes between scans, emit on change | `shm.write` | writer agent → each registered reader agent | 100-500ms (scan interval) |
| Engine rule fire | `ReactiveEngine._dispatch()` — after rule matches, before action execution | `engine.rule` | triggering file's agent → rule name | <1ms |
| Engine action execution | `ReactiveEngine._execute_action()` — after action completes | `engine.action` | rule → downstream agent (mapped via action handler name) | <1ms after action |
| LLM call | Wrap LiteLLM proxy call path — emit after response received | `llm.call` | calling agent → `llm` node | Post-response |
| Qdrant operation | Wrap `get_qdrant()` search/upsert methods | `qdrant.op` | calling agent → `qdrant` node | Post-response |
| Pi fleet POST | `logos/api/routes/pi.py` POST handlers | `pi.detection` | Pi node ID → `perception` | On receipt |

**Agent identity resolution:**
- SHM writes: directory naming convention (`/dev/shm/hapax-{agent}/`)
- Engine sources: mapping from action handler names to agent IDs (added to manifests as `engine_actions: [action_name]`)
- LLM/Qdrant: `agent_name` parameter threaded through call sites. Calls without identity get `source: "unknown"`.

### External Service Nodes

Three synthetic nodes representing external services. Fourth layer below output layer.

| Node ID | Label | Status logic | Metrics |
|---|---|---|---|
| `llm` | LLM Gateway | Active if any LLM call in last 60s | Recent call count, last model used |
| `qdrant` | Vector DB | Active if any Qdrant op in last 60s | Recent op count, last collection |
| `pi_fleet` | Pi Fleet | Active if any Pi POST in last 60s | Online Pi count, last detection role |

**Lifecycle:** External nodes appear on the graph only when the event bus has recent events of the corresponding kind. They disappear after 60s of inactivity. No dormant external nodes.

**Edges:** Edges to/from external nodes are synthetic, created from recent events. They use **emergent** style (dashed amber). An `llm.call` event from `stimmung_sync` creates a transient edge `stimmung_sync → llm`.

### Frontend — Transient Dot Traversal

When the frontend receives a FlowEvent via SSE, it renders a one-shot dot animation along the corresponding edge.

**Dot properties:**
- Size: 3px radius circle
- Color: source node's status color (green-400 if active, yellow-400 if stale)
- Travel: SVG `animateMotion` along the edge's bezier path, 800ms duration
- Fade: opacity 1.0 → 0.0 over the last 200ms of traversal
- On completion: DOM element removed

**Multiple events:** Each event spawns its own dot independently. A burst of 5 events on one edge produces 5 dots staggered by arrival time. No batching, no throttling — if the system is noisy, the edge looks busy. If quiet, nothing moves.

**Event buffer:** Frontend ring buffer (50 events) for the SSE stream. Events not matching any visible edge are dropped.

**SSE connection:** Tauri SSE bridge pattern (same as agent output streaming in `commands/streaming.rs`). Rust subscribes to `GET /api/events/stream`, re-emits as Tauri events (`flow-event`). Frontend listens via `@tauri-apps/api/event`.

**Edge creation for unknown edges:** Events referencing edges not in the current topology cause the flow state endpoint to create them as emergent edges on the next poll. The dot for the triggering event may be missed (arrives before edge exists), but subsequent events on the same path will visualize correctly.

### Data Flow

```
Agent code / Engine / Pi handler
         | emit(FlowEvent)
         v
    EventBus (in-process, 500-entry ring)
         |
    +----+------------------+
    |                       |
    v                       v
/api/events/stream      /api/flow/state
(SSE, real-time)        (enriched: external
                         nodes + edges from
                         recent events)
    |
    v
Tauri SSE bridge
(commands/streaming.rs)
    |
    v
Tauri event: "flow-event"
    |
    v
FlowPage.tsx listener
-> spawn dot on matching edge
```

Two consumers of the event bus:

1. **SSE stream** — real-time events for dot animations. Frontend subscribes on mount, unsubscribes on unmount.
2. **Flow state endpoint** — `/api/flow/state` reads recent events from ring buffer to build synthetic external nodes and emergent edges. Existing 3s polling cadence, enriched with event data.

## Files to Create

| File | Purpose |
|---|---|
| `logos/event_bus.py` | EventBus class, FlowEvent dataclass |
| `logos/api/routes/events.py` | `GET /api/events/stream` SSE endpoint |
| `hapax-logos/src-tauri/src/commands/flow_events.rs` | Tauri SSE bridge for flow events |

## Files to Modify

| File | Changes |
|---|---|
| `logos/engine/engine.py` | Emit `engine.rule` and `engine.action` events after dispatch/execution |
| `logos/api/flow_observer.py` | Emit `shm.write` events when mtime changes between scans |
| `logos/api/routes/pi.py` | Emit `pi.detection` events on POST receipt |
| `logos/api/routes/flow.py` | Read recent events to build external nodes and emergent edges |
| `shared/config.py` | Wrap `get_qdrant()` with event-emitting proxy |
| `logos/api/app.py` | Create EventBus singleton at startup, attach to app.state |
| `hapax-logos/src-tauri/src/main.rs` | Register flow events command |
| `hapax-logos/src/pages/FlowPage.tsx` | Listen for `flow-event` Tauri events, render transient dots on edges |

## Implementation Notes

### Verified consumption map

The original design routed SHM write events to all declared topology edges from the source node. This inflated a single file write into N fake "calls" — the topology says paths exist, not that data flowed on each one simultaneously. We know the source wrote but not which targets consumed it.

The implementation uses a static verified consumption map (`_VERIFIED_CONSUMERS` in `flow_observer.py`) derived from a codebase audit of actual `json.loads(path.read_text())` calls across agent source code. Only edges where Agent B's source code provably reads Agent A's SHM file produce dot events.

| Producer | Verified Consumers |
|---|---|
| `stimmung_sync` | `hapax_daimonion`, `reactive_engine`, `studio_compositor` |
| `temporal_bands` | `hapax_daimonion`, `studio_compositor` |
| `apperception` | `hapax_daimonion` |
| `studio_compositor` | `hapax_daimonion` |
| `dmn` | `hapax_daimonion`, `studio_compositor` |
| `hapax_daimonion` | `studio_compositor` |

This map must be updated when agent consumption patterns change in source code.

### Dot animation

Dots traverse edge bezier paths over 2s (ease-out spline), with soft fade-in over the first 15% and fade-out over the last 25%. A Gaussian blur filter provides a subtle glow halo. Each event spawns one dot; bursts appear as clusters.

### Additional fixes during implementation

- **VLA readiness bug**: Missing `Path` import in `stimmung_methods.py` crashed the entire `_api_poll_loop`, preventing `poll_ambient_content` from running, keeping terrain readiness stuck at "collecting" forever.
- **SHM writer ID mismatch**: SHM directory names (e.g., `compositor`) don't match node IDs (e.g., `studio_compositor`). Fixed with `_writer_node_map` populated from manifest state paths plus explicit entries for agents without SHM state paths.
- **Events router prefix**: Events SSE endpoint was at `/events/stream` but Tauri bridge expected `/api/events/stream`. Added `/api` prefix to router.
- **Stimmung stance field**: Dynamic discovery returns `overall_stance` not `stance`. Added fallback at all read sites.

## Out of Scope

- Persistent event storage (events are ephemeral — ring buffer only)
- Event filtering/search UI
- Historical replay
- Per-event detail panel (click on dot to see event details)
- Cost/latency aggregation from events
- Modifying the existing node body renderers
- Changing the stimmung-driven breathing system
