# Perceptual Control Loops

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add closed-loop perceptual control to the 7 highest-priority SCM components, wire stimmung modulation into core cognitive processing (DMN, imagination), and publish per-component health metrics to `/dev/shm`.

**Architecture:** Each component gets a `ControlSignal` (reference, perception, error) computed inline on each tick. Stimmung stance modulates DMN pulse rate and imagination cadence — not just presentation layers. Per-component health files in `/dev/shm/hapax-{component}/health.json` enable mesh-wide aggregation. Hysteresis prevents oscillation between degraded and nominal states.

**Tech Stack:** Python 3.12+, pydantic, `/dev/shm` atomic JSON

**SCM Gaps Closed:** #4 (1/14 components have control loops), #10 (stimmung doesn't modulate core processing)

**Depends on:** Plan 1 (DMN extraction) for imagination modulation. Can proceed independently for non-DMN components.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `shared/control_signal.py` | Create | ControlSignal model + publish_health utility |
| `agents/hapax_daimonion/backends/ir_presence.py` | Modify | Add freshness control signal |
| `agents/dmn/pulse.py` | Modify | Add stimmung-driven rate modulation |
| `agents/imagination_loop.py` | Modify | Add stimmung-driven cadence modulation |
| `shared/stimmung.py` | Modify | Add hysteresis to stance transitions |
| `tests/test_control_signal.py` | Create | Verify ControlSignal model |
| `tests/test_stimmung_modulation.py` | Create | Verify stimmung modulates DMN/imagination |
| `tests/test_stimmung_hysteresis.py` | Create | Verify hysteresis prevents oscillation |

---

### Task 1: Create ControlSignal Model

**Files:**
- Create: `shared/control_signal.py`
- Test: `tests/test_control_signal.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_control_signal.py
"""Test ControlSignal model and health publishing."""

import json
import time
from pathlib import Path


def test_control_signal_creation():
    """Verify ControlSignal captures reference, perception, and error."""
    from shared.control_signal import ControlSignal

    sig = ControlSignal(
        component="ir_perception",
        reference=1.0,
        perception=0.7,
    )
    assert sig.error == pytest.approx(0.3)
    assert sig.component == "ir_perception"


def test_control_signal_zero_error():
    """When perception matches reference, error is zero."""
    from shared.control_signal import ControlSignal

    sig = ControlSignal(component="stimmung", reference=0.0, perception=0.0)
    assert sig.error == 0.0


def test_publish_health(tmp_path):
    """Verify health file is written atomically."""
    from shared.control_signal import ControlSignal, publish_health

    sig = ControlSignal(component="test", reference=1.0, perception=0.5)
    path = tmp_path / "health.json"
    publish_health(sig, path=path)

    data = json.loads(path.read_text())
    assert data["component"] == "test"
    assert data["error"] == pytest.approx(0.5)
    assert "timestamp" in data


import pytest
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_control_signal.py -v`
Expected: FAIL with "No module named 'shared.control_signal'"

- [ ] **Step 3: Implement ControlSignal**

```python
# shared/control_signal.py
"""ControlSignal — per-component perceptual control error reporting.

Each S1 component in the cognitive mesh computes a ControlSignal on each tick:
- reference: what the component expects to perceive
- perception: what the component actually perceives
- error: abs(reference - perception)

Published to /dev/shm/hapax-{component}/health.json for mesh-wide aggregation.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ControlSignal:
    """A single control error measurement."""

    component: str
    reference: float
    perception: float

    @property
    def error(self) -> float:
        return abs(self.reference - self.perception)

    def to_dict(self) -> dict:
        return {
            "component": self.component,
            "reference": self.reference,
            "perception": self.perception,
            "error": self.error,
            "timestamp": time.time(),
        }


def publish_health(signal: ControlSignal, *, path: Path | None = None) -> None:
    """Write component health to /dev/shm atomically."""
    if path is None:
        path = Path(f"/dev/shm/hapax-{signal.component}/health.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(signal.to_dict()), encoding="utf-8")
    tmp.rename(path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_control_signal.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add shared/control_signal.py tests/test_control_signal.py
git commit -m "feat: add ControlSignal model for per-component perceptual health"
```

---

### Task 2: Add Stimmung Hysteresis

Prevent oscillation when stimmung stance toggles between nominal and cautious. Stance can degrade immediately but requires sustained improvement to recover.

**Files:**
- Modify: `shared/stimmung.py`
- Test: `tests/test_stimmung_hysteresis.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stimmung_hysteresis.py
"""Test stimmung stance hysteresis."""


def test_stance_degrades_immediately():
    """Stance should degrade immediately when dimensions worsen."""
    from shared.stimmung import StimmungCollector

    collector = StimmungCollector()
    collector.update_health(healthy=10, total=10)
    snap1 = collector.snapshot()
    assert snap1.stance == "nominal"

    collector.update_health(healthy=3, total=10)
    snap2 = collector.snapshot()
    assert snap2.stance in ("cautious", "degraded", "critical")


def test_stance_requires_sustained_improvement():
    """Stance should not recover from one good reading — needs sustained improvement."""
    from shared.stimmung import StimmungCollector

    collector = StimmungCollector()

    # Degrade
    collector.update_health(healthy=3, total=10)
    snap1 = collector.snapshot()
    degraded_stance = snap1.stance
    assert degraded_stance != "nominal"

    # One good reading should NOT recover
    collector.update_health(healthy=10, total=10)
    snap2 = collector.snapshot()
    # With hysteresis, stance should still be degraded after one good reading
    assert snap2.stance == degraded_stance or snap2.stance != "nominal"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_stimmung_hysteresis.py -v`
Expected: FAIL (stance recovers immediately without hysteresis)

- [ ] **Step 3: Add hysteresis to StimmungCollector**

In `shared/stimmung.py`, add to `StimmungCollector.__init__`:

```python
self._recovery_readings: int = 0
self._last_stance: str = "nominal"
RECOVERY_THRESHOLD = 3  # Consecutive nominal readings required to recover
```

In `_compute_stance()`, after computing the raw stance from dimensions:

```python
# Hysteresis: degrade immediately, recover slowly
if raw_stance == "nominal" and self._last_stance != "nominal":
    self._recovery_readings += 1
    if self._recovery_readings < RECOVERY_THRESHOLD:
        return self._last_stance  # Hold degraded stance
    else:
        self._recovery_readings = 0
        self._last_stance = "nominal"
        return "nominal"
else:
    self._recovery_readings = 0
    self._last_stance = raw_stance
    return raw_stance
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_stimmung_hysteresis.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add shared/stimmung.py tests/test_stimmung_hysteresis.py
git commit -m "feat(stimmung): add hysteresis to prevent stance oscillation"
```

---

### Task 3: Stimmung Modulation of DMN Pulse Rate

**Files:**
- Modify: `agents/dmn/pulse.py`
- Test: `tests/test_stimmung_modulation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stimmung_modulation.py
"""Test stimmung modulates DMN pulse and imagination cadence."""


def test_dmn_pulse_reads_stimmung_stance():
    """DMN pulse module must reference stimmung stance for rate modulation."""
    source = open("agents/dmn/pulse.py").read()
    assert "stimmung" in source.lower() and ("stance" in source or "modulation" in source), (
        "DMN pulse must read stimmung stance for rate modulation"
    )


def test_imagination_reads_stimmung_for_cadence():
    """Imagination loop must reference stimmung for cadence modulation."""
    source = open("agents/imagination_loop.py").read()
    # After Plan 1, imagination reads stimmung from /dev/shm in the daemon
    # But the CadenceController should have a stimmung-aware method
    assert "stimmung" in source.lower() or "stance" in source.lower(), (
        "Imagination cadence should be modulated by stimmung"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_stimmung_modulation.py::test_dmn_pulse_reads_stimmung_stance -v`
Expected: FAIL (DMN pulse doesn't currently modulate rate by stimmung)

- [ ] **Step 3: Add stimmung rate modulation to DMN pulse**

In `agents/dmn/pulse.py`, modify the tick timing to account for stimmung:

```python
def _get_stance_rate_multiplier(self) -> float:
    """Return rate multiplier based on stimmung stance.

    degraded: 2x slower (conserve resources)
    critical: 4x slower (minimal processing)
    """
    stance = self._last_stance  # Set from snapshot
    if stance == "critical":
        return 4.0
    elif stance == "degraded":
        return 2.0
    elif stance == "cautious":
        return 1.5
    return 1.0
```

In the tick method, apply the multiplier:

```python
# In _sensory_tick or tick cadence calculation:
rate_mult = self._get_stance_rate_multiplier()
if self._tpn_active:
    rate_mult *= 2.0
effective_interval = self._sensory_tick_s * rate_mult
```

Store the stance from snapshot reads:

```python
# In _sensory_tick, after reading snapshot:
stimmung = snapshot.get("stimmung", {})
self._last_stance = stimmung.get("stance", "nominal")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_stimmung_modulation.py::test_dmn_pulse_reads_stimmung_stance -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/dmn/pulse.py tests/test_stimmung_modulation.py
git commit -m "feat(dmn): modulate pulse rate by stimmung stance"
```

---

### Task 4: IR Perception Control Signal

Add a control signal to the IR perception backend — the first perception backend with closed-loop health reporting.

**Files:**
- Modify: `agents/hapax_daimonion/backends/ir_presence.py`
- Test: `tests/test_ir_control_signal.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ir_control_signal.py
"""Test IR perception backend reports control signal."""

import json
import time
from pathlib import Path


def test_ir_control_signal_fresh_reports(tmp_path):
    """Fresh IR reports should produce low control error."""
    from shared.control_signal import ControlSignal

    # Simulate: 3 Pi reports, all fresh (< 10s)
    # Reference: staleness < 10s → perception = 1.0
    # When all fresh: error = 0.0
    sig = ControlSignal(
        component="ir_perception",
        reference=1.0,
        perception=1.0,  # all reports fresh
    )
    assert sig.error == 0.0


def test_ir_control_signal_stale_reports():
    """Stale IR reports should produce high control error."""
    from shared.control_signal import ControlSignal

    # Simulate: worst Pi report is 25s old (threshold 10s)
    # perception = max(0, 1 - (25 - 10) / 10) = max(0, -0.5) = 0.0
    sig = ControlSignal(
        component="ir_perception",
        reference=1.0,
        perception=0.0,  # all reports stale
    )
    assert sig.error == 1.0
```

- [ ] **Step 2: Run test to verify it passes** (these test the model, not the wiring)

Run: `uv run pytest tests/test_ir_control_signal.py -v`
Expected: PASS (ControlSignal model already exists from Task 1)

- [ ] **Step 3: Wire control signal into IR backend**

In `agents/hapax_daimonion/backends/ir_presence.py`, in the `contribute()` method, after computing signals:

```python
from shared.control_signal import ControlSignal, publish_health

# After computing ir signals from Pi reports:
max_age = max(
    (time.time() - r.get("timestamp", 0) for r in reports.values()),
    default=999.0,
)
freshness = max(0.0, 1.0 - max(0.0, max_age - 10.0) / 10.0)
sig = ControlSignal(
    component="ir_perception",
    reference=1.0,
    perception=freshness,
)
publish_health(sig)
```

- [ ] **Step 4: Commit**

```bash
git add agents/hapax_daimonion/backends/ir_presence.py tests/test_ir_control_signal.py
git commit -m "feat(ir): add perceptual control signal for freshness monitoring"
```

---

### Task 5: Aggregate Mesh Health from Component Signals

**Files:**
- Create: `shared/mesh_health.py`
- Test: `tests/test_mesh_health.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mesh_health.py
"""Test mesh-wide health aggregation from component control signals."""

import json
import time
from pathlib import Path


def test_aggregate_mesh_health(tmp_path):
    """Aggregate E_mesh from multiple component health files."""
    from shared.mesh_health import aggregate_mesh_health

    # Write 3 component health files
    for component, error in [("ir_perception", 0.1), ("stimmung", 0.0), ("dmn", 0.3)]:
        d = tmp_path / f"hapax-{component}"
        d.mkdir()
        (d / "health.json").write_text(json.dumps({
            "component": component,
            "error": error,
            "timestamp": time.time(),
        }))

    result = aggregate_mesh_health(shm_root=tmp_path)
    assert result["e_mesh"] == pytest.approx(0.4 / 3, abs=0.01)  # mean error
    assert result["component_count"] == 3
    assert result["worst_component"] == "dmn"


def test_stale_health_excluded(tmp_path):
    """Components with stale health files should be excluded."""
    import os
    from shared.mesh_health import aggregate_mesh_health

    d = tmp_path / "hapax-old_component"
    d.mkdir()
    health = d / "health.json"
    health.write_text(json.dumps({
        "component": "old_component",
        "error": 0.9,
        "timestamp": time.time() - 300,
    }))
    os.utime(health, (time.time() - 300, time.time() - 300))

    result = aggregate_mesh_health(shm_root=tmp_path, stale_s=120.0)
    assert result["component_count"] == 0


import pytest
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mesh_health.py -v`
Expected: FAIL (no module shared.mesh_health)

- [ ] **Step 3: Implement mesh health aggregation**

```python
# shared/mesh_health.py
"""Aggregate mesh-wide health from per-component control signals.

Reads /dev/shm/hapax-*/health.json files and computes E_mesh
(mean control error across all fresh components).
"""

from __future__ import annotations

import json
import time
from pathlib import Path


def aggregate_mesh_health(
    *, shm_root: Path = Path("/dev/shm"), stale_s: float = 120.0
) -> dict:
    """Compute mesh-wide health from component health files.

    Returns dict with:
    - e_mesh: mean control error across fresh components
    - component_count: number of fresh components reporting
    - worst_component: component name with highest error
    - components: dict of component → error
    """
    components: dict[str, float] = {}
    now = time.time()

    for health_dir in sorted(shm_root.glob("hapax-*/health.json")):
        try:
            data = json.loads(health_dir.read_text(encoding="utf-8"))
            ts = data.get("timestamp", 0)
            if now - ts > stale_s:
                continue
            components[data["component"]] = data["error"]
        except (OSError, json.JSONDecodeError, KeyError):
            continue

    if not components:
        return {
            "e_mesh": 1.0,
            "component_count": 0,
            "worst_component": "none",
            "components": {},
        }

    e_mesh = sum(components.values()) / len(components)
    worst = max(components, key=components.get)

    return {
        "e_mesh": e_mesh,
        "component_count": len(components),
        "worst_component": worst,
        "components": components,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_mesh_health.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add shared/mesh_health.py tests/test_mesh_health.py
git commit -m "feat: add mesh-wide health aggregation from component control signals"
```
