# Dynamic System Anatomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded 9-node System Anatomy graph with a data-driven topology that discovers nodes from agent manifests, derives edges from layer rules + runtime observation, and uses dagre auto-layout.

**Architecture:** Agent manifests declare `pipeline_role`/`pipeline_layer`/`pipeline_state`/`gates`. The flow API scans manifests, reads SHM state files, builds edges from layer adjacency + gates + runtime observation. The frontend uses dagre for layout and renders three edge styles (confirmed/emergent/dormant).

**Tech Stack:** Python (FastAPI, pydantic), TypeScript (React, @xyflow/react, @dagrejs/dagre), YAML manifests

---

## File Structure

| File | Responsibility |
|------|---------------|
| `shared/agent_registry.py` | Modify: extend `AgentManifest` with pipeline fields |
| `agents/manifests/*.yaml` | Modify: add pipeline fields to ~13 manifests |
| `logos/api/routes/flow.py` | Rewrite: dynamic node discovery + edge derivation |
| `logos/api/flow_observer.py` | Create: runtime SHM flow correlation |
| `tests/test_flow_discovery.py` | Create: unit tests for node discovery + edge derivation |
| `tests/test_flow_observer.py` | Create: unit tests for runtime observer |
| `hapax-logos/src/pages/FlowPage.tsx` | Modify: dagre layout + edge styles |
| `hapax-logos/package.json` | Modify: add @dagrejs/dagre dependency |

---

### Task 1: Extend AgentManifest with pipeline fields

**Files:**
- Modify: `shared/agent_registry.py`
- Modify: 13 manifests in `agents/manifests/`
- Test: `tests/test_agent_registry.py` (existing, verify no breakage)

- [ ] **Step 1: Add pipeline fields to AgentManifest**

In `shared/agent_registry.py`, add to the `AgentManifest` class:

```python
class PipelineState(BaseModel):
    path: str = ""
    metrics: list[str] = []
    stale_threshold: float = 10.0

class AgentManifest(BaseModel):
    # ... existing fields ...

    # Pipeline participation (optional — absent means excluded from graph)
    pipeline_role: Literal["sensor", "processor", "integrator", "actuator"] | None = None
    pipeline_layer: Literal["perception", "cognition", "output"] | None = None
    pipeline_state: PipelineState | None = None
    gates: list[str] = []
```

- [ ] **Step 2: Run existing tests to verify no breakage**

```bash
uv run pytest tests/test_agent_registry.py -v
```

Expected: all existing tests pass (new fields are optional with defaults).

- [ ] **Step 3: Add pipeline fields to 13 manifests**

Update each manifest YAML with the pipeline fields. Here are all 13:

**`agents/manifests/ir_perception.yaml`** (create if not exists):
```yaml
pipeline_role: sensor
pipeline_layer: perception
pipeline_state:
  path: "~/hapax-state/pi-noir/desk.json"
  metrics: [person_detected, hand_activity, gaze_direction]
  stale_threshold: 15
```

**`agents/manifests/hapax_daimonion.yaml`**:
```yaml
pipeline_role: processor
pipeline_layer: perception
pipeline_state:
  path: "~/.cache/hapax-daimonion/perception-state.json"
  metrics: [flow_score, presence_probability, heart_rate_bpm, aggregate_confidence]
```

**`agents/manifests/stimmung_sync.yaml`** (find or create):
```yaml
pipeline_role: processor
pipeline_layer: perception
pipeline_state:
  path: "/dev/shm/hapax-stimmung/state.json"
  metrics: [overall_stance, health, operator_energy]
  stale_threshold: 120
```

**`agents/manifests/temporal_bands.yaml`** (find or create):
```yaml
pipeline_role: integrator
pipeline_layer: cognition
pipeline_state:
  path: "/dev/shm/hapax-temporal/bands.json"
  metrics: [retention_count, protention_count, max_surprise, flow_state]
```

**`agents/manifests/apperception.yaml`** (find or create):
```yaml
pipeline_role: integrator
pipeline_layer: cognition
pipeline_state:
  path: "/dev/shm/hapax-apperception/self-band.json"
  metrics: [coherence, system_awareness, continuity]
```

**`agents/manifests/phenomenal_context.yaml`** (create — synthetic node):
```yaml
pipeline_role: integrator
pipeline_layer: cognition
pipeline_state:
  path: ""
  metrics: [bound, coherence, surprise, active_dimensions]
```
Note: `path: ""` signals the backend to synthesize this node from temporal + apperception.

**`agents/manifests/dmn.yaml`** (find or create):
```yaml
pipeline_role: processor
pipeline_layer: cognition
pipeline_state:
  path: "/dev/shm/hapax-imagination/current.json"
  metrics: [id, salience, material]
```

**`agents/manifests/imagination_resolver.yaml`** (find or create):
```yaml
pipeline_role: integrator
pipeline_layer: cognition
pipeline_state:
  path: "/dev/shm/hapax-imagination/content/active/slots.json"
  metrics: [fragment_id, slots]
```

**`agents/manifests/consent.yaml`** (find or create):
```yaml
pipeline_role: integrator
pipeline_layer: cognition
gates: [voice_pipeline, compositor]
pipeline_state:
  path: ""
  metrics: [phase, coverage_pct, active_contracts]
```

**`agents/manifests/voice_pipeline.yaml`** (find or create):
```yaml
pipeline_role: actuator
pipeline_layer: output
pipeline_state:
  path: ""
  metrics: [state, routing_activation, turn_count]
```

**`agents/manifests/compositor.yaml`** (find or create):
```yaml
pipeline_role: actuator
pipeline_layer: output
pipeline_state:
  path: "/dev/shm/hapax-compositor/visual-layer-state.json"
  metrics: [display_state, signal_count, zone_opacities]
```

**`agents/manifests/reactive_engine.yaml`** (find or create):
```yaml
pipeline_role: actuator
pipeline_layer: output
pipeline_state:
  path: ""
  metrics: [events_processed, actions_executed, rules_evaluated]
```

**`agents/manifests/visual_surface.yaml`** (create):
```yaml
id: visual_surface
name: Visual Surface
version: "1.0.0"
category: output
pipeline_role: actuator
pipeline_layer: output
pipeline_state:
  path: "/dev/shm/hapax-visual/frame.jpg"
  metrics: [frame_age_s, pass_count]
```

- [ ] **Step 4: Verify manifest loading**

```bash
uv run pytest tests/test_agent_registry.py -v
```

Expected: all pass, no schema errors from new fields.

- [ ] **Step 5: Commit**

```bash
git add shared/agent_registry.py agents/manifests/
git commit -m "feat(flow): extend AgentManifest with pipeline fields for 13 agents"
```

---

### Task 2: Backend node discovery

**Files:**
- Create: `logos/api/flow_discovery.py`
- Create: `tests/test_flow_discovery.py`

- [ ] **Step 1: Write failing test for node discovery**

Create `tests/test_flow_discovery.py`:

```python
"""Tests for dynamic flow node discovery from agent manifests."""

from pathlib import Path
from unittest.mock import patch

from logos.api.flow_discovery import discover_pipeline_nodes, read_state_metrics


def test_discover_finds_pipeline_agents(tmp_path: Path):
    """Only agents with pipeline_role appear as nodes."""
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()

    # Pipeline agent
    (manifest_dir / "perception.yaml").write_text(
        "id: perception\nname: Perception\npipeline_role: processor\n"
        "pipeline_layer: perception\npipeline_state:\n  path: /tmp/test.json\n  metrics: [flow]\n"
    )
    # Non-pipeline agent (no pipeline_role)
    (manifest_dir / "backup.yaml").write_text(
        "id: backup\nname: Backup\ncategory: maintenance\n"
    )

    nodes = discover_pipeline_nodes(manifest_dir)
    assert len(nodes) == 1
    assert nodes[0]["id"] == "perception"
    assert nodes[0]["pipeline_layer"] == "perception"


def test_discover_reads_metrics(tmp_path: Path):
    """State file metrics are extracted correctly."""
    state_file = tmp_path / "state.json"
    state_file.write_text('{"flow": 0.75, "extra": "ignored", "timestamp": 1000}')

    metrics = read_state_metrics(str(state_file), ["flow"])
    assert metrics == {"flow": 0.75}


def test_discover_handles_missing_state(tmp_path: Path):
    """Missing state file returns empty metrics and offline status."""
    metrics = read_state_metrics("/nonexistent/path.json", ["flow"])
    assert metrics == {}


def test_discover_computes_age_and_status(tmp_path: Path):
    """Node status derived from state file age."""
    import time, json

    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"timestamp": time.time(), "flow": 1.0}))

    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    (manifest_dir / "test.yaml").write_text(
        f"id: test\nname: Test\npipeline_role: sensor\n"
        f"pipeline_layer: perception\npipeline_state:\n"
        f"  path: {state_file}\n  metrics: [flow]\n"
    )

    nodes = discover_pipeline_nodes(manifest_dir)
    assert len(nodes) == 1
    assert nodes[0]["status"] == "active"
    assert nodes[0]["age_s"] < 5
    assert nodes[0]["metrics"]["flow"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_flow_discovery.py -v
```

Expected: `ModuleNotFoundError: No module named 'logos.api.flow_discovery'`

- [ ] **Step 3: Implement flow_discovery.py**

Create `logos/api/flow_discovery.py`:

```python
"""Dynamic flow node discovery from agent manifests."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

MANIFESTS_DIR = Path(__file__).resolve().parent.parent.parent / "agents" / "manifests"


def _expand_home(path: str) -> str:
    if path.startswith("~/"):
        from os.path import expanduser
        return expanduser(path)
    return path


def _read_json(path: str) -> dict | None:
    try:
        return json.loads(Path(_expand_home(path)).read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _file_age(path: str) -> float:
    """Age in seconds since file was last modified."""
    try:
        return time.time() - Path(_expand_home(path)).stat().st_mtime
    except OSError:
        return 9999.0


def _status(age: float, stale_threshold: float = 10.0) -> str:
    if age < stale_threshold:
        return "active"
    if age < 30.0:
        return "stale"
    return "offline"


def read_state_metrics(path: str, metric_keys: list[str]) -> dict:
    """Read specific metric keys from a JSON state file."""
    if not path:
        return {}
    data = _read_json(path)
    if data is None:
        return {}
    result = {}
    for key in metric_keys:
        if key in data:
            val = data[key]
            # Extract .value from DimensionReading dicts
            if isinstance(val, dict) and "value" in val:
                val = val["value"]
            result[key] = val
    return result


def discover_pipeline_nodes(
    manifests_dir: Path | None = None,
) -> list[dict]:
    """Discover pipeline nodes from agent manifests.

    Returns a list of node dicts compatible with the flow API response.
    Only agents with ``pipeline_role`` are included.
    """
    if manifests_dir is None:
        manifests_dir = MANIFESTS_DIR

    nodes: list[dict] = []
    for path in sorted(manifests_dir.glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text()) or {}
        except Exception:
            continue

        role = raw.get("pipeline_role")
        if not role:
            continue

        layer = raw.get("pipeline_layer", "output")
        state_cfg = raw.get("pipeline_state") or {}
        state_path = state_cfg.get("path", "")
        metric_keys = state_cfg.get("metrics", [])
        stale_threshold = state_cfg.get("stale_threshold", 10.0)

        age = _file_age(state_path) if state_path else 9999.0
        metrics = read_state_metrics(state_path, metric_keys)

        nodes.append({
            "id": raw.get("id", path.stem),
            "label": raw.get("name", raw.get("id", path.stem)),
            "status": _status(age, stale_threshold),
            "age_s": round(age, 1),
            "metrics": metrics,
            "pipeline_role": role,
            "pipeline_layer": layer,
            "gates": raw.get("gates", []),
        })

    return nodes
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_flow_discovery.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add logos/api/flow_discovery.py tests/test_flow_discovery.py
git commit -m "feat(flow): dynamic node discovery from agent manifests"
```

---

### Task 3: Backend edge derivation

**Files:**
- Modify: `logos/api/flow_discovery.py`
- Modify: `tests/test_flow_discovery.py`

- [ ] **Step 1: Write failing tests for edge derivation**

Append to `tests/test_flow_discovery.py`:

```python
from logos.api.flow_discovery import build_declared_edges, composite_edges


def test_layer_edges_perception_to_cognition():
    """Perception nodes connect to cognition nodes automatically."""
    nodes = [
        {"id": "perc", "pipeline_layer": "perception", "status": "active", "age_s": 1, "gates": []},
        {"id": "cog", "pipeline_layer": "cognition", "status": "active", "age_s": 2, "gates": []},
        {"id": "out", "pipeline_layer": "output", "status": "active", "age_s": 3, "gates": []},
    ]
    edges = build_declared_edges(nodes)
    sources_targets = [(e["source"], e["target"]) for e in edges]
    assert ("perc", "cog") in sources_targets
    assert ("cog", "out") in sources_targets
    assert ("perc", "out") not in sources_targets  # no skip-layer


def test_gate_edges():
    """Gates create explicit cross-connections."""
    nodes = [
        {"id": "consent", "pipeline_layer": "cognition", "status": "active", "age_s": 1, "gates": ["voice"]},
        {"id": "voice", "pipeline_layer": "output", "status": "active", "age_s": 2, "gates": []},
    ]
    edges = build_declared_edges(nodes)
    gate_edges = [e for e in edges if e.get("label") == "gate"]
    assert len(gate_edges) == 1
    assert gate_edges[0]["source"] == "consent"
    assert gate_edges[0]["target"] == "voice"


def test_composite_confirmed():
    """Declared + observed = confirmed."""
    declared = [{"source": "a", "target": "b", "active": True, "label": "flow"}]
    observed = {("a", "b")}
    result = composite_edges(declared, observed)
    assert result[0]["edge_type"] == "confirmed"


def test_composite_emergent():
    """Observed only = emergent."""
    declared = []
    observed = {("x", "y")}
    result = composite_edges(declared, observed)
    emergent = [e for e in result if e["edge_type"] == "emergent"]
    assert len(emergent) == 1
    assert emergent[0]["source"] == "x"


def test_composite_dormant():
    """Declared only = dormant."""
    declared = [{"source": "a", "target": "b", "active": True, "label": "flow"}]
    observed = set()
    result = composite_edges(declared, observed)
    assert result[0]["edge_type"] == "dormant"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_flow_discovery.py -v -k "edge or composite"
```

Expected: `ImportError: cannot import name 'build_declared_edges'`

- [ ] **Step 3: Implement edge derivation**

Add to `logos/api/flow_discovery.py`:

```python
LAYER_ORDER = {"perception": 0, "cognition": 1, "output": 2}


def build_declared_edges(nodes: list[dict]) -> list[dict]:
    """Build edges from layer adjacency rules and gate declarations."""
    edges: list[dict] = []
    node_map = {n["id"]: n for n in nodes}

    # Layer adjacency: perception→cognition, cognition→output
    by_layer: dict[str, list[dict]] = {}
    for n in nodes:
        by_layer.setdefault(n["pipeline_layer"], []).append(n)

    layer_pairs = [("perception", "cognition"), ("cognition", "output")]
    for src_layer, dst_layer in layer_pairs:
        for src in by_layer.get(src_layer, []):
            for dst in by_layer.get(dst_layer, []):
                active = src["age_s"] < 30
                edges.append({
                    "source": src["id"],
                    "target": dst["id"],
                    "active": active,
                    "label": f"{src_layer}→{dst_layer}",
                })

    # Gate connections (explicit cross-layer)
    for n in nodes:
        for gate_target in n.get("gates", []):
            if gate_target in node_map:
                edges.append({
                    "source": n["id"],
                    "target": gate_target,
                    "active": n["age_s"] < 30,
                    "label": "gate",
                })

    return edges


def composite_edges(
    declared: list[dict],
    observed: set[tuple[str, str]],
) -> list[dict]:
    """Merge declared and observed edges, classify each.

    Returns edges with ``edge_type``: confirmed, emergent, or dormant.
    """
    result: list[dict] = []
    declared_pairs: set[tuple[str, str]] = set()

    for edge in declared:
        pair = (edge["source"], edge["target"])
        declared_pairs.add(pair)
        edge_type = "confirmed" if pair in observed else "dormant"
        result.append({**edge, "edge_type": edge_type})

    # Emergent: observed but not declared
    for src, tgt in observed:
        if (src, tgt) not in declared_pairs:
            result.append({
                "source": src,
                "target": tgt,
                "active": True,
                "label": "observed",
                "edge_type": "emergent",
            })

    return result
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_flow_discovery.py -v
```

Expected: all 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add logos/api/flow_discovery.py tests/test_flow_discovery.py
git commit -m "feat(flow): layer-based edge derivation + composite edge classification"
```

---

### Task 4: Runtime flow observer

**Files:**
- Create: `logos/api/flow_observer.py`
- Create: `tests/test_flow_observer.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_flow_observer.py`:

```python
"""Tests for runtime SHM flow observation."""

import time
from pathlib import Path

from logos.api.flow_observer import FlowObserver


def test_observer_detects_write(tmp_path: Path):
    """Observer correlates a writer with its state file."""
    obs = FlowObserver(shm_root=tmp_path, decay_seconds=60)

    # Simulate agent writing state
    agent_dir = tmp_path / "hapax-stimmung"
    agent_dir.mkdir()
    state_file = agent_dir / "state.json"
    state_file.write_text('{"stance": "cautious"}')

    obs.scan()

    writers = obs.get_writers()
    assert "hapax-stimmung" in writers
    assert "state.json" in writers["hapax-stimmung"]


def test_observer_builds_observed_edges(tmp_path: Path):
    """Observer produces edges from writer→reader correlations."""
    obs = FlowObserver(shm_root=tmp_path, decay_seconds=60)

    # Register known readers (from manifests)
    obs.register_reader("perception", "/dev/shm/hapax-stimmung/state.json")

    # Simulate stimmung writing
    agent_dir = tmp_path / "hapax-stimmung"
    agent_dir.mkdir()
    (agent_dir / "state.json").write_text("{}")

    obs.scan()

    edges = obs.get_observed_edges()
    assert ("hapax-stimmung", "perception") in edges or ("stimmung_sync", "perception") in edges


def test_observer_decays_stale_edges(tmp_path: Path):
    """Edges not observed recently are decayed."""
    obs = FlowObserver(shm_root=tmp_path, decay_seconds=0)  # immediate decay

    agent_dir = tmp_path / "hapax-test"
    agent_dir.mkdir()
    (agent_dir / "state.json").write_text("{}")
    obs.register_reader("consumer", str(agent_dir / "state.json"))

    obs.scan()
    assert len(obs.get_observed_edges()) > 0

    # After decay window
    import time
    time.sleep(0.1)
    obs.scan()
    assert len(obs.get_observed_edges()) == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_flow_observer.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement flow_observer.py**

Create `logos/api/flow_observer.py`:

```python
"""Runtime SHM flow observation — correlates writers with readers."""

from __future__ import annotations

import logging
import time
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_SHM_ROOT = Path("/dev/shm")


class FlowObserver:
    """Observes SHM directories to discover actual data flows.

    Correlates file writers (by directory name convention ``hapax-{agent}``)
    with registered readers (from manifest ``pipeline_state.path``).
    """

    def __init__(
        self,
        shm_root: Path = DEFAULT_SHM_ROOT,
        decay_seconds: float = 60.0,
    ):
        self._shm_root = shm_root
        self._decay_seconds = decay_seconds
        # {directory_name: {filename: last_modified_time}}
        self._writers: dict[str, dict[str, float]] = {}
        # {reader_agent_id: normalized_path}
        self._readers: dict[str, str] = {}
        # {(writer, reader): last_observed_time}
        self._observed: dict[tuple[str, str], float] = {}

    def register_reader(self, agent_id: str, state_path: str) -> None:
        """Register an agent as a reader of a specific state file."""
        self._readers[agent_id] = state_path

    def scan(self) -> None:
        """Scan SHM directories for recent writes and correlate with readers."""
        now = time.time()

        # Scan hapax-* directories
        for d in self._shm_root.iterdir():
            if not d.is_dir() or not d.name.startswith("hapax-"):
                continue
            writer_name = d.name
            for f in d.iterdir():
                if not f.is_file():
                    continue
                try:
                    mtime = f.stat().st_mtime
                except OSError:
                    continue
                self._writers.setdefault(writer_name, {})[f.name] = mtime

                # Correlate with readers
                full_path = str(f)
                for reader_id, reader_path in self._readers.items():
                    if reader_path == full_path or full_path.endswith(reader_path.split("/")[-1]):
                        if now - mtime < 30:  # only recent writes
                            self._observed[(writer_name, reader_id)] = now

        # Decay old observations
        expired = [k for k, v in self._observed.items() if now - v > self._decay_seconds]
        for k in expired:
            del self._observed[k]

    def get_writers(self) -> dict[str, dict[str, float]]:
        """Return current writer map."""
        return dict(self._writers)

    def get_observed_edges(self) -> set[tuple[str, str]]:
        """Return set of (writer, reader) pairs currently observed."""
        return set(self._observed.keys())
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_flow_observer.py -v
```

Expected: all 3 pass.

- [ ] **Step 5: Commit**

```bash
git add logos/api/flow_observer.py tests/test_flow_observer.py
git commit -m "feat(flow): runtime SHM flow observer for emergent edge discovery"
```

---

### Task 5: Rewrite flow.py to use discovery

**Files:**
- Modify: `logos/api/routes/flow.py`
- Modify: `tests/test_flow_state.py` (if exists)

- [ ] **Step 1: Rewrite get_flow_state**

Replace the body of `get_flow_state` in `logos/api/routes/flow.py`. Keep the existing helper functions (`_read`, `_age`, `_status`, `_stimmung_dimensions`, `_consent_coverage`, `_engine_status`) for the synthetic nodes (phenomenal_context, consent, voice, engine) that need special handling.

Replace the hardcoded node/edge building with:

```python
from logos.api.flow_discovery import discover_pipeline_nodes, build_declared_edges, composite_edges
from logos.api.flow_observer import FlowObserver

# Module-level observer (started once, scanned each poll)
_observer: FlowObserver | None = None

def _get_observer() -> FlowObserver:
    global _observer
    if _observer is None:
        _observer = FlowObserver()
        # Register readers from discovered nodes
        from logos.api.flow_discovery import MANIFESTS_DIR, discover_pipeline_nodes
        for node in discover_pipeline_nodes(MANIFESTS_DIR):
            state_path = node.get("_state_path", "")
            if state_path:
                _observer.register_reader(node["id"], state_path)
    return _observer


@router.get("/flow/state")
async def get_flow_state(request: Request) -> dict:
    # 1. Discover pipeline nodes from manifests
    nodes = discover_pipeline_nodes()

    # 2. Enrich synthetic nodes (phenomenal_context, consent, voice, engine)
    _enrich_synthetic_nodes(nodes, request)

    # 3. Build declared edges from layer rules + gates
    declared = build_declared_edges(nodes)

    # 4. Get observed edges from runtime observer
    observer = _get_observer()
    observer.scan()
    observed = observer.get_observed_edges()

    # 5. Composite edges
    edges = composite_edges(declared, observed)

    return {"nodes": nodes, "edges": edges, "timestamp": time.time()}
```

The `_enrich_synthetic_nodes` function handles nodes with `path: ""` by computing their metrics from other sources (same logic as current hardcoded nodes for phenomenal_context, consent, voice_pipeline, reactive_engine).

- [ ] **Step 2: Implement _enrich_synthetic_nodes**

Add to `flow.py`:

```python
def _enrich_synthetic_nodes(nodes: list[dict], request: Request) -> None:
    """Fill in metrics for synthetic nodes that don't have state files."""
    node_map = {n["id"]: n for n in nodes}

    # Phenomenal context: synthesized from temporal + apperception
    if "phenomenal_context" in node_map:
        pc = node_map["phenomenal_context"]
        temp = node_map.get("temporal_bands", {}).get("metrics", {})
        apper = node_map.get("apperception", {}).get("metrics", {})
        temp_age = node_map.get("temporal_bands", {}).get("age_s", 999)
        apper_age = node_map.get("apperception", {}).get("age_s", 999)
        pc["metrics"] = {
            "bound": temp_age < 30 and apper_age < 30,
            "coherence": apper.get("coherence", 0),
            "surprise": temp.get("max_surprise", 0),
            "active_dimensions": len([v for v in apper.values() if isinstance(v, (int, float)) and v > 0]),
        }
        pc["age_s"] = min(temp_age, apper_age)
        pc["status"] = _status(pc["age_s"])

    # Consent: from perception + Qdrant
    if "consent" in node_map:
        cn = node_map["consent"]
        perc = node_map.get("hapax_daimonion", {}).get("metrics", {})
        cov = _consent_coverage()
        cn["metrics"] = {
            "phase": perc.get("consent_phase", "none"),
            "coverage_pct": cov.get("coverage_pct", 0),
            "active_contracts": cov.get("active_contracts", 0),
        }
        perc_age = node_map.get("hapax_daimonion", {}).get("age_s", 999)
        cn["age_s"] = perc_age
        cn["status"] = "active" if cn["metrics"]["phase"] != "none" else "offline"

    # Voice pipeline: from perception voice_session
    if "voice_pipeline" in node_map:
        vp = node_map["voice_pipeline"]
        perc_path = node_map.get("hapax_daimonion", {}).get("_state_path", "")
        perc_data = _read(Path(perc_path)) if perc_path else None
        voice = (perc_data or {}).get("voice_session", {})
        vp["metrics"] = {
            "state": voice.get("state", "off"),
            "routing_activation": voice.get("routing_activation", 0),
            "turn_count": voice.get("turn_count", 0),
        }
        vp["status"] = "active" if voice.get("active") else "offline"
        vp["age_s"] = node_map.get("hapax_daimonion", {}).get("age_s", 999)

    # Reactive engine: from in-process engine
    if "reactive_engine" in node_map:
        re = node_map["reactive_engine"]
        engine = _engine_status(request)
        re["metrics"] = engine
        re["status"] = "active" if engine.get("uptime_s", 0) > 0 else "offline"
        re["age_s"] = 0 if re["status"] == "active" else 999
```

- [ ] **Step 3: Run all flow tests**

```bash
uv run pytest tests/test_flow_discovery.py tests/test_flow_observer.py tests/test_flow_state.py -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add logos/api/routes/flow.py
git commit -m "refactor(flow): replace hardcoded topology with dynamic discovery"
```

---

### Task 6: Frontend dagre layout + edge styles

**Files:**
- Modify: `hapax-logos/package.json`
- Modify: `hapax-logos/src/pages/FlowPage.tsx`

- [ ] **Step 1: Install dagre**

```bash
cd hapax-logos && pnpm add @dagrejs/dagre
```

- [ ] **Step 2: Replace hardcoded POSITIONS with dagre layout**

In `FlowPage.tsx`, remove the `POSITIONS` const and add dagre layout:

```typescript
import Dagre from "@dagrejs/dagre";

function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
): { nodes: Node[]; edges: Edge[] } {
  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 80, ranksep: 150 });

  // Use pipeline_layer as rank constraint
  const layerRank: Record<string, number> = { perception: 0, cognition: 1, output: 2 };

  nodes.forEach((node) => {
    g.setNode(node.id, {
      width: 220,
      height: 120,
      rank: layerRank[node.data?.pipeline_layer] ?? 1,
    });
  });

  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  Dagre.layout(g);

  const layoutedNodes = nodes.map((node) => {
    const pos = g.node(node.id);
    return {
      ...node,
      position: { x: pos.x - 110, y: pos.y - 60 },
    };
  });

  return { nodes: layoutedNodes, edges };
}
```

Update the `useEffect` that builds nodes/edges to call `getLayoutedElements` instead of using `POSITIONS`:

```typescript
useEffect(() => {
  if (!flowState) return;
  const p = palette;
  const am: Record<string, number> = {};
  flowState.nodes.forEach((n: FlowNode) => { am[n.id] = n.age_s; });

  const rawNodes = flowState.nodes.map((n: FlowNode) => ({
    id: n.id,
    type: "system",
    position: prevPos.current[n.id] || { x: 0, y: 0 },
    data: n,
    draggable: true,
  }));

  const rawEdges = flowState.edges.map((e: FlowEdge, i: number) => ({
    id: `${e.source}-${e.target}-${i}`,
    source: e.source,
    target: e.target,
    type: "flowing",
    data: {
      active: e.active,
      age_s: am[e.source] || 999,
      label: e.label,
      edge_type: e.edge_type || "confirmed",
    },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: edgeColor(am[e.source] || 999, e.active, p),
      width: 12,
      height: 12,
    },
  }));

  // Only run dagre if no user-dragged positions exist
  const hasPrevPos = Object.keys(prevPos.current).length > 0;
  if (hasPrevPos) {
    setNodes(rawNodes.map(n => ({
      ...n,
      position: prevPos.current[n.id] || n.position,
    })));
    setEdges(rawEdges);
  } else {
    const layouted = getLayoutedElements(rawNodes, rawEdges);
    setNodes(layouted.nodes);
    setEdges(layouted.edges);
  }
}, [flowState, setNodes, setEdges]);
```

- [ ] **Step 3: Add edge styles for confirmed/emergent/dormant**

Update the `FlowingEdge` component to render differently based on `data.edge_type`:

```typescript
function FlowingEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data }: EdgeProps) {
  const p = useTheme().palette;
  const [path] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition });
  const age = (data as any)?.age_s ?? 999;
  const active = (data as any)?.active ?? false;
  const edgeType = (data as any)?.edge_type ?? "confirmed";
  const label = (data as any)?.label ?? "";

  // Style by edge type
  let strokeDasharray: string | undefined;
  let strokeColor: string;
  let strokeOpacity: number;
  let strokeWidth: number;

  switch (edgeType) {
    case "confirmed":
      strokeDasharray = undefined;  // solid
      strokeColor = active ? edgeColor(age, true, p) : p["zinc-700"];
      strokeOpacity = active ? 0.7 : 0.15;
      strokeWidth = 1.5;
      break;
    case "emergent":
      strokeDasharray = "6 3";  // dashed
      strokeColor = p["yellow-400"];
      strokeOpacity = 0.8;
      strokeWidth = 2;
      break;
    case "dormant":
      strokeDasharray = "2 4";  // dotted
      strokeColor = p["zinc-600"];
      strokeOpacity = 0.2;
      strokeWidth = 1;
      break;
    default:
      strokeDasharray = undefined;
      strokeColor = p["zinc-700"];
      strokeOpacity = 0.15;
      strokeWidth = 1;
  }

  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        style={{
          stroke: strokeColor,
          strokeWidth,
          strokeOpacity,
          strokeDasharray,
          transition: "stroke 1s ease, stroke-opacity 1s ease",
        }}
      />
      {/* Animated particle for active/emergent edges */}
      {(edgeType === "confirmed" || edgeType === "emergent") && active && (
        <circle r={3} fill={strokeColor} opacity={0.6}>
          <animateMotion dur={`${2 + age * 0.3}s`} repeatCount="indefinite" path={path} />
        </circle>
      )}
      {/* Label on hover */}
      <text>
        <textPath href={`#${id}`} startOffset="50%" textAnchor="middle"
          style={{ fontSize: 9, fill: p["text-muted"], opacity: 0, transition: "opacity 0.3s" }}
          className="flow-edge-label"
        >
          {label}{edgeType === "emergent" ? " ⚡" : ""}
        </textPath>
      </text>
    </>
  );
}
```

- [ ] **Step 4: Add FlowEdge type to include edge_type**

Update the `FlowEdge` type near the top of `FlowPage.tsx`:

```typescript
interface FlowEdge {
  source: string;
  target: string;
  active: boolean;
  label: string;
  edge_type?: "confirmed" | "emergent" | "dormant";
}
```

- [ ] **Step 5: Build and verify**

```bash
cd hapax-logos && pnpm build 2>&1 | tail -5
```

Expected: builds without TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add hapax-logos/package.json hapax-logos/pnpm-lock.yaml hapax-logos/src/pages/FlowPage.tsx
git commit -m "feat(flow): dagre auto-layout + confirmed/emergent/dormant edge styles"
```

---
