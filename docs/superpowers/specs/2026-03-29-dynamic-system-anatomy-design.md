# Dynamic System Anatomy — Design Spec

## Goal

Replace the hardcoded 9-node System Anatomy graph with a data-driven topology that discovers nodes from agent manifests, derives edges from layer rules, and observes actual runtime data flows to surface emergent relationships.

## Architecture

Three layers of topology information, composited into a single graph:

1. **Declared topology** — Agent manifests declare `pipeline_role`, `pipeline_layer`, `gates`. Edges derived from layer adjacency rules.
2. **Runtime observation** — The backend correlates SHM file writers (by systemd unit → agent manifest) with readers (by declared `pipeline_state.path`) to build observed edges.
3. **Visual composite** — The frontend renders confirmed, emergent, and dormant flows with distinct visual treatments.

**Data flow:** Agent manifests (YAML) → `flow.py` discovers pipeline nodes → layer rules + gates build declared edges → runtime SHM correlation builds observed edges → dagre auto-layout (frontend) → React Flow render with three edge styles.

## Manifest Schema Extension

Each pipeline-participating manifest gets new optional fields:

```yaml
# agents/manifests/hapax_daimonion.yaml
id: hapax_daimonion
name: Hapax Daimonion
# ... existing fields ...

# NEW: Pipeline participation (absent = excluded from graph)
pipeline_role: processor          # sensor | processor | integrator | actuator
pipeline_layer: perception        # perception | cognition | output
pipeline_state:
  path: "~/.cache/hapax-daimonion/perception-state.json"
  metrics:                        # keys to extract for node display
    - flow_score
    - presence_probability
    - heart_rate_bpm
    - aggregate_confidence
gates: []                         # explicit cross-layer edges
```

**Roles:**
- `sensor` — Raw input (IR fleet, biometrics, ambient classifiers)
- `processor` — Transforms sensory input into structured state (perception engine, stimmung)
- `integrator` — Synthesizes multiple inputs into higher-order state (apperception, phenomenal context, consent)
- `actuator` — Produces output (voice pipeline, compositor, reactive engine)

**Layers:**
- `perception` — Sensory tier (sensors + processors that produce perceptual state)
- `cognition` — Reasoning tier (integrators that synthesize perception into understanding)
- `output` — Expression tier (actuators that produce behavior)

Agents without `pipeline_role` are excluded from the graph. Of ~45 manifests, ~13 participate.

## Pipeline Nodes

| Agent | Role | Layer | State path | Key metrics |
|-------|------|-------|-----------|-------------|
| ir_perception | sensor | perception | `~/hapax-state/pi-noir/*.json` | person_detected, hand_activity, gaze |
| hapax_daimonion | processor | perception | `~/.cache/hapax-daimonion/perception-state.json` | flow_score, presence, heart_rate_bpm |
| stimmung_sync | processor | perception | `/dev/shm/hapax-stimmung/state.json` | overall_stance, health, operator_energy |
| temporal_bands | integrator | cognition | `/dev/shm/hapax-temporal/bands.json` | retention_count, protention_count, max_surprise |
| apperception | integrator | cognition | `/dev/shm/hapax-apperception/self-band.json` | coherence, system_awareness, continuity |
| phenomenal_context | integrator | cognition | (synthesized from temporal + apperception) | bound, coherence, surprise, active_dimensions |
| dmn | processor | cognition | `/dev/shm/hapax-imagination/current.json` | fragment_id, salience, material, ref_count |
| imagination | integrator | cognition | `/dev/shm/hapax-imagination/content/active/slots.json` | slot_count, fragment_id, material |
| consent | integrator | cognition | (perception-state + Qdrant) | phase, coverage_pct, active_contracts |
| hapax_daimonion_voice | actuator | output | (voice_session in perception-state) | state, routing_activation, turn_count |
| compositor | actuator | output | `/dev/shm/hapax-compositor/visual-layer-state.json` | display_state, signal_count, zone_opacities |
| reactive_engine | actuator | output | (in-process) | events_processed, actions_executed, rules_evaluated |
| visual_surface | actuator | output | `/dev/shm/hapax-visual/frame.jpg` | frame_age_s, preset, pass_count |

## Edge Derivation

### Declared Edges (from layer rules + gates)

Automatic edges flow between adjacent layers:

```
perception → cognition → output
```

Every active perception node gets an edge to every active cognition node. Every active cognition node gets an edge to every active output node. This produces the default pipeline topology.

**Gate overrides:** A manifest's `gates` field declares explicit cross-connections that supplement the layer defaults:

```yaml
# consent manifest
gates: [hapax_daimonion_voice, compositor]  # consent gates these actuators
```

Gate edges are always rendered regardless of layer adjacency.

**Edge activation:** An edge is `active` if the source node's state file age is below the stale threshold (10s default, 120s for stimmung).

### Observed Edges (from runtime correlation)

The backend discovers actual data flows by:

1. **Writer identification:** For each `/dev/shm/hapax-*/` state file, record the writer's PID → resolve via `/proc/{pid}/cgroup` → systemd unit name → agent manifest ID.
2. **Reader identification:** Each manifest's `pipeline_state.path` declares what it reads. Cross-reference with known writer agents.
3. **Timestamp correlation:** If agent A's state file updates within 2s of agent B's state file updating, and B's `pipeline_state.path` points to A's output, record an observed edge A → B.

The runtime observer runs as a background task in the logos-api process, polling `/dev/shm/hapax-*/` every 5 seconds. It maintains a `dict[str, set[str]]` of observed `writer → reader` pairs, decaying edges that haven't been observed in 60 seconds.

### Visual Composite

Three edge styles in the frontend:

| Condition | Style | Meaning |
|-----------|-------|---------|
| Declared AND observed | Solid line, full opacity, animated particles | Confirmed: designed and functioning |
| Observed only | Dashed line, accent color (amber), animated particles | Emergent: happening but not designed |
| Declared only | Dotted line, dim (0.2 opacity), no particles | Dormant: designed but not functioning |

Emergent edges are visually prominent — they're the discoveries worth investigating.

## Frontend Layout

Replace hardcoded `POSITIONS` dict with dagre auto-layout:

- **Direction:** top-to-bottom (TB)
- **Layer grouping:** dagre `rank` constraint per `pipeline_layer` (perception=0, cognition=1, output=2)
- **Node spacing:** `nodesep: 80`, `ranksep: 150`
- **User dragging:** overrides dagre position for that session (stored in ref, not persisted)
- **Responsive:** fitView recalculates on container resize
- **Library:** dagre via `@dagrejs/dagre` (already a common React Flow companion)

`SystemNode` component unchanged — it renders any metrics dict. The `metrics` field from the manifest tells the backend which keys to extract.

## Backend Changes (flow.py)

`GET /api/flow/state` becomes:

```python
@router.get("/flow/state")
async def get_flow_state():
    # 1. Discover pipeline nodes from manifests
    nodes = discover_pipeline_nodes()  # reads agents/manifests/*.yaml

    # 2. Read live state for each node
    for node in nodes:
        node["metrics"] = read_state_metrics(node["state_path"], node["metric_keys"])
        node["age_s"] = compute_age(node["state_path"])
        node["status"] = classify_status(node["age_s"], node.get("stale_threshold", 10))

    # 3. Build declared edges from layer rules + gates
    declared_edges = build_declared_edges(nodes)

    # 4. Get observed edges from runtime observer
    observed_edges = get_observed_edges()  # from background correlation task

    # 5. Composite: merge declared + observed, classify each
    edges = composite_edges(declared_edges, observed_edges)

    return {"nodes": nodes, "edges": edges, "timestamp": time.time()}
```

Response shape stays compatible — `nodes` and `edges` arrays. Each edge gains an `edge_type` field: `"confirmed"`, `"emergent"`, or `"dormant"`.

## What Stays the Same

- `SystemNode` React component (renders any metrics dict)
- `FlowingEdge` component (gains dashed/dotted variants for new edge types)
- 3-second frontend poll interval
- Status thresholds (active < 10s, stale < 30s, offline > 30s)
- Sparkline rendering (first metric in list)
- Detail panel on node click
- `/flow` route (terrain migration deferred to separate spec)

## What Changes

| Component | Before | After |
|-----------|--------|-------|
| Node discovery | Hardcoded 9 nodes in flow.py | Scanned from manifests with `pipeline_role` |
| Edge definition | Hardcoded 16 edges in flow.py | Layer rules + gates + runtime observation |
| Layout | Hardcoded POSITIONS dict | Dagre auto-layout with layer rank constraints |
| Edge styles | Single style (active/inactive) | Three styles (confirmed/emergent/dormant) |
| Node count | Fixed 9 | Dynamic ~13 (grows with manifests) |
| New nodes | — | DMN, Imagination, IR Perception, Visual Surface |

## Testing

- Unit tests for `discover_pipeline_nodes()` with mock manifest directory
- Unit tests for `build_declared_edges()` with known layer assignments
- Unit tests for `composite_edges()` covering all three edge type classifications
- Integration test: write test manifests, verify API response shape
- Visual verification: dagre layout produces readable graph with 13 nodes

## Scope Exclusions

- Terrain integration (separate spec)
- Agent manifest schema migration tool (manual updates to ~13 files)
- Historical flow recording/replay
- Flow graph persistence (layout resets on refresh)
