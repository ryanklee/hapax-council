# Impingement Cascade Architecture

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire 3 cascade paths through the cognitive mesh so a single impingement can propagate across components, add positive feedback (engagement → imagination acceleration), and enable cascade tracing via `parent_id`.

**Architecture:** Three cascade paths: (1) Perception STATISTICAL_DEVIATION → Apperception prediction_error CascadeEvent, (2) Stimmung stance transition → DMN cadence adjustment, (3) Imagination SALIENCE_INTEGRATION → perception sensitivity boost. Each hop reduces strength by 0.7× to prevent runaway cascades. Maximum cascade depth: 3. `parent_id` links form a traceable chain.

**Tech Stack:** Python 3.12+, pydantic, ImpingementConsumer (shared/impingement_consumer.py), `/dev/shm` JSONL

**SCM Gaps Closed:** #11 (no cascade), #12 (no positive feedback)

**Depends on:** Plan 1 (DMN extraction) for clean daemon boundaries

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `shared/impingement.py` | Modify | Add cascade depth tracking, strength decay helper |
| `agents/_apperception.py` | Modify | Consume perception impingements as cascade events |
| `agents/dmn/pulse.py` | Modify | React to stimmung transitions via impingements |
| `agents/imagination_loop.py` | Modify | Positive feedback from perception engagement |
| `tests/test_cascade_depth.py` | Create | Verify depth limiting and strength decay |
| `tests/test_cascade_perception_apperception.py` | Create | Verify Path 1 |
| `tests/test_positive_feedback.py` | Create | Verify engagement → imagination acceleration |

---

### Task 1: Add Cascade Helpers to Impingement

**Files:**
- Modify: `shared/impingement.py`
- Test: `tests/test_cascade_depth.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cascade_depth.py
"""Test impingement cascade depth limiting and strength decay."""

import time


def test_cascade_depth_from_parent_chain():
    """Verify cascade_depth computes correctly from parent chain."""
    from shared.impingement import Impingement, ImpingementType, cascade_depth

    root = Impingement(
        timestamp=time.time(),
        source="perception.vad",
        type=ImpingementType.STATISTICAL_DEVIATION,
        strength=0.8,
    )
    assert cascade_depth(root) == 0  # no parent


def test_child_impingement_with_decayed_strength():
    """Verify child_impingement reduces strength by decay factor."""
    from shared.impingement import Impingement, ImpingementType, child_impingement

    parent = Impingement(
        timestamp=time.time(),
        source="perception.vad",
        type=ImpingementType.STATISTICAL_DEVIATION,
        strength=0.8,
    )

    child = child_impingement(
        parent=parent,
        source="apperception.prediction_error",
        type=ImpingementType.SALIENCE_INTEGRATION,
        content={"cascade": "test"},
        decay=0.7,
    )

    assert child.parent_id == parent.id
    assert child.strength == pytest.approx(0.56)  # 0.8 * 0.7
    assert child.source == "apperception.prediction_error"


def test_child_impingement_blocked_at_max_depth():
    """Verify child_impingement returns None when max depth exceeded."""
    from shared.impingement import Impingement, ImpingementType, child_impingement

    parent = Impingement(
        timestamp=time.time(),
        source="test",
        type=ImpingementType.STATISTICAL_DEVIATION,
        strength=0.8,
        content={"_cascade_depth": 3},  # already at max
    )

    child = child_impingement(
        parent=parent,
        source="test.child",
        type=ImpingementType.SALIENCE_INTEGRATION,
        content={},
        max_depth=3,
    )

    assert child is None


import pytest
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cascade_depth.py -v`
Expected: FAIL (no cascade_depth or child_impingement functions)

- [ ] **Step 3: Add cascade helpers**

Add to `shared/impingement.py`:

```python
import time as _time


def cascade_depth(imp: Impingement) -> int:
    """Get the cascade depth of an impingement (0 = root, no parent)."""
    return imp.content.get("_cascade_depth", 0)


def child_impingement(
    *,
    parent: Impingement,
    source: str,
    type: ImpingementType,
    content: dict[str, Any],
    decay: float = 0.7,
    max_depth: int = 3,
) -> Impingement | None:
    """Create a child impingement with decayed strength and parent tracing.

    Returns None if max cascade depth exceeded.
    """
    depth = cascade_depth(parent) + 1
    if depth > max_depth:
        return None

    return Impingement(
        timestamp=_time.time(),
        source=source,
        type=type,
        strength=parent.strength * decay,
        content={**content, "_cascade_depth": depth},
        context=parent.context,
        parent_id=parent.id,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cascade_depth.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add shared/impingement.py tests/test_cascade_depth.py
git commit -m "feat(impingement): add cascade depth tracking and strength decay helpers"
```

---

### Task 2: Cascade Path 1 — Perception → Apperception

Wire perception STATISTICAL_DEVIATION impingements into the apperception cascade as prediction_error events.

**Files:**
- Modify: `agents/_apperception.py`
- Test: `tests/test_cascade_perception_apperception.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cascade_perception_apperception.py
"""Test perception impingements feed apperception cascade."""

import time


def test_statistical_deviation_maps_to_prediction_error():
    """Perception STATISTICAL_DEVIATION should map to apperception prediction_error."""
    from agents._apperception import impingement_to_cascade_event
    from shared.impingement import Impingement, ImpingementType

    imp = Impingement(
        timestamp=time.time(),
        source="perception.vad_confidence",
        type=ImpingementType.STATISTICAL_DEVIATION,
        strength=0.6,
        content={"metric": "vad_confidence", "value": 0.2, "delta": -0.5},
    )

    event = impingement_to_cascade_event(imp)
    assert event is not None
    assert event.source.value == "prediction_error"
    assert event.magnitude == pytest.approx(0.6)


def test_non_statistical_deviation_ignored():
    """Only STATISTICAL_DEVIATION maps to prediction_error."""
    from agents._apperception import impingement_to_cascade_event
    from shared.impingement import Impingement, ImpingementType

    imp = Impingement(
        timestamp=time.time(),
        source="dmn.resolver",
        type=ImpingementType.ABSOLUTE_THRESHOLD,
        strength=0.6,
        content={"metric": "resolver_failures"},
    )

    event = impingement_to_cascade_event(imp)
    assert event is None  # Not a perception deviation — don't cascade


import pytest
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cascade_perception_apperception.py -v`
Expected: FAIL (no impingement_to_cascade_event function)

- [ ] **Step 3: Add impingement → cascade event mapping**

Add to `agents/_apperception.py`:

```python
from shared.impingement import Impingement, ImpingementType


def impingement_to_cascade_event(imp: Impingement) -> CascadeEvent | None:
    """Map a perception impingement to an apperception cascade event.

    Only STATISTICAL_DEVIATION from perception sources maps to prediction_error.
    Other types are not perceptual surprises and should not enter the cascade.
    """
    if imp.type != ImpingementType.STATISTICAL_DEVIATION:
        return None
    if not imp.source.startswith("perception."):
        return None

    metric = imp.content.get("metric", imp.source)
    value = imp.content.get("value", "")
    delta = imp.content.get("delta", 0)

    return CascadeEvent(
        source=Source.PREDICTION_ERROR,
        text=f"Perception signal {metric} deviated: value={value}, delta={delta}",
        magnitude=imp.strength,
        metadata={"impingement_id": imp.id, "metric": metric},
        timestamp=imp.timestamp,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cascade_perception_apperception.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/_apperception.py tests/test_cascade_perception_apperception.py
git commit -m "feat(apperception): map perception impingements to cascade events"
```

---

### Task 3: Positive Feedback — Engagement → Imagination Acceleration

**Files:**
- Modify: `agents/imagination_loop.py`
- Test: `tests/test_positive_feedback.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_positive_feedback.py
"""Test positive feedback: high engagement accelerates imagination."""

import json
import time
from pathlib import Path


def test_high_engagement_accelerates_cadence():
    """When presence + audio energy are high, imagination should accelerate."""
    from agents.imagination_loop import should_accelerate_from_engagement

    perception = {
        "presence_probability": 0.9,
        "audio_energy": 0.5,
    }

    assert should_accelerate_from_engagement(perception) is True


def test_low_engagement_does_not_accelerate():
    """When presence is low, engagement-based acceleration should not trigger."""
    from agents.imagination_loop import should_accelerate_from_engagement

    perception = {
        "presence_probability": 0.2,
        "audio_energy": 0.1,
    }

    assert should_accelerate_from_engagement(perception) is False


def test_moderate_engagement_threshold():
    """Borderline engagement should not trigger (avoid noise-driven acceleration)."""
    from agents.imagination_loop import should_accelerate_from_engagement

    perception = {
        "presence_probability": 0.6,  # Below 0.7 threshold
        "audio_energy": 0.4,
    }

    assert should_accelerate_from_engagement(perception) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_positive_feedback.py -v`
Expected: FAIL (no should_accelerate_from_engagement function)

- [ ] **Step 3: Implement engagement-based acceleration**

Add to `agents/imagination_loop.py`:

```python
PRESENCE_THRESHOLD = 0.7
AUDIO_ENERGY_THRESHOLD = 0.3


def should_accelerate_from_engagement(perception: dict) -> bool:
    """Check if operator engagement is high enough to accelerate imagination.

    Positive feedback loop: high presence + audio energy → faster imagination
    → more expressive visual surface → richer environment → more engagement.

    Thresholds are conservative to avoid noise-driven acceleration.
    """
    presence = perception.get("presence_probability", 0.0)
    audio = perception.get("audio_energy", 0.0)
    return presence >= PRESENCE_THRESHOLD and audio >= AUDIO_ENERGY_THRESHOLD
```

In the `tick()` method (or in the imagination daemon's main loop), after generating a fragment:

```python
# Engagement-based positive feedback
snapshot_perception = snapshot.get("perception", {})
if should_accelerate_from_engagement(snapshot_perception):
    self.cadence._accelerated = True  # Use accelerated interval (4s)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_positive_feedback.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/imagination_loop.py tests/test_positive_feedback.py
git commit -m "feat(imagination): positive feedback loop — engagement accelerates cadence"
```

---

### Task 4: Wire Apperception to Consume Impingements from JSONL

Currently apperception cascade events are generated internally. This task wires the ImpingementConsumer so apperception reads perception impingements from the shared JSONL.

**Files:**
- Modify: `agents/_apperception.py`
- Test: `tests/test_apperception_impingement_consumer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_apperception_impingement_consumer.py
"""Test apperception consumes impingements from JSONL."""

import json
import time
from pathlib import Path


def test_consume_impingements_from_jsonl(tmp_path):
    """Apperception should read and process perception impingements from JSONL."""
    from agents._apperception import consume_perception_impingements
    from shared.impingement import Impingement, ImpingementType

    # Write a perception impingement to JSONL
    jsonl_path = tmp_path / "impingements.jsonl"
    imp = Impingement(
        timestamp=time.time(),
        source="perception.ir_person_detected",
        type=ImpingementType.STATISTICAL_DEVIATION,
        strength=0.7,
        content={"metric": "ir_person_detected", "value": 0, "delta": -1.0},
    )
    jsonl_path.write_text(imp.model_dump_json() + "\n")

    events = consume_perception_impingements(path=jsonl_path, cursor=0)
    assert len(events) >= 1
    assert events[0].source.value == "prediction_error"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_apperception_impingement_consumer.py -v`
Expected: FAIL (no consume_perception_impingements)

- [ ] **Step 3: Add consumer function**

Add to `agents/_apperception.py`:

```python
from shared.impingement_consumer import ImpingementConsumer

_IMPINGEMENTS_PATH = Path("/dev/shm/hapax-dmn/impingements.jsonl")
_consumer = ImpingementConsumer(_IMPINGEMENTS_PATH)


def consume_perception_impingements(
    *, path: Path | None = None, cursor: int = 0
) -> list[CascadeEvent]:
    """Read new perception impingements from JSONL and convert to cascade events."""
    consumer = ImpingementConsumer(path or _IMPINGEMENTS_PATH)
    consumer._cursor = cursor

    events = []
    for imp in consumer.read_new():
        event = impingement_to_cascade_event(imp)
        if event is not None:
            events.append(event)
    return events
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_apperception_impingement_consumer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/_apperception.py tests/test_apperception_impingement_consumer.py
git commit -m "feat(apperception): consume perception impingements from cross-daemon JSONL"
```
