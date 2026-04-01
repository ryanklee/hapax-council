# Staleness Safety (P3 Remediation)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce staleness safety (SCM Property P3) across all perception backends and the imagination pipeline — no component should act on data older than its configured staleness threshold.

**Architecture:** Each backend gets a `STALE_THRESHOLD_S` constant and an `mtime` check before trusting `/dev/shm` trace files. Stale signals substitute safe defaults (e.g., `ir_person_detected=False`). Staleness impingements are rate-limited (one per source per 60s). The imagination loop skips ticks when observations are stale rather than generating fragments from old data.

**Tech Stack:** Python 3.12+, pydantic, `/dev/shm` mtime checks

**SCM Gaps Closed:** #9 (IR/vision backends skip freshness), #13 (imagination not freshness-driven)

**Depends on:** Nothing (Track C — can proceed immediately, parallel to A and B)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `shared/trace_reader.py` | Create | Shared utility for staleness-checked /dev/shm reads |
| `agents/hapax_daimonion/backends/ir_presence.py` | Modify | Add staleness gate on Pi reports |
| `agents/hapax_daimonion/backends/vision.py` | Modify | Add staleness gate on compositor snapshots |
| `agents/hapax_daimonion/backends/contact_mic.py` | Modify | Add cache age check |
| `agents/imagination_loop.py` | Modify | Skip ticks when observations stale |
| `tests/test_trace_reader.py` | Create | Verify staleness-checked reads |
| `tests/test_backend_staleness.py` | Create | Verify backends reject stale data |
| `tests/test_imagination_freshness.py` | Create | Verify imagination skips stale ticks |

---

### Task 1: Create Shared Trace Reader with Staleness Check

**Files:**
- Create: `shared/trace_reader.py`
- Test: `tests/test_trace_reader.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_trace_reader.py
"""Test staleness-checked trace reader."""

import json
import os
import time
from pathlib import Path

import pytest


def test_read_fresh_trace(tmp_path):
    """Fresh trace should be read successfully."""
    from shared.trace_reader import read_trace

    path = tmp_path / "state.json"
    path.write_text(json.dumps({"value": 42}))

    data = read_trace(path, stale_s=10.0)
    assert data is not None
    assert data["value"] == 42


def test_read_stale_trace_returns_none(tmp_path):
    """Stale trace should return None."""
    from shared.trace_reader import read_trace

    path = tmp_path / "state.json"
    path.write_text(json.dumps({"value": 42}))
    old_time = time.time() - 60
    os.utime(path, (old_time, old_time))

    data = read_trace(path, stale_s=10.0)
    assert data is None


def test_read_missing_trace_returns_none(tmp_path):
    """Missing file should return None."""
    from shared.trace_reader import read_trace

    data = read_trace(tmp_path / "missing.json", stale_s=10.0)
    assert data is None


def test_read_corrupt_trace_returns_none(tmp_path):
    """Corrupt JSON should return None."""
    from shared.trace_reader import read_trace

    path = tmp_path / "bad.json"
    path.write_text("{not valid json")

    data = read_trace(path, stale_s=10.0)
    assert data is None


def test_trace_age_returns_seconds(tmp_path):
    """trace_age should return file age in seconds."""
    from shared.trace_reader import trace_age

    path = tmp_path / "state.json"
    path.write_text("{}")

    age = trace_age(path)
    assert age is not None
    assert age < 2.0  # Just written


def test_trace_age_missing_returns_none(tmp_path):
    """trace_age on missing file should return None."""
    from shared.trace_reader import trace_age

    age = trace_age(tmp_path / "missing.json")
    assert age is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_trace_reader.py -v`
Expected: FAIL (no module shared.trace_reader)

- [ ] **Step 3: Implement trace reader**

```python
# shared/trace_reader.py
"""Staleness-checked /dev/shm trace reader.

Every component reading from /dev/shm should use read_trace() instead
of raw json.loads(path.read_text()). This enforces P3 (staleness safety)
from the SCM specification — no component acts on data older than its
configured staleness threshold.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def trace_age(path: Path) -> float | None:
    """Return the age of a trace file in seconds, or None if missing."""
    try:
        return time.time() - path.stat().st_mtime
    except OSError:
        return None


def read_trace(path: Path, stale_s: float) -> dict[str, Any] | None:
    """Read a JSON trace file with staleness check.

    Returns None if:
    - File is missing
    - File is older than stale_s seconds (by mtime)
    - File contains invalid JSON

    This is the standard read pattern for /dev/shm traces.
    Using raw json.loads() without staleness check violates P3.
    """
    try:
        age = time.time() - path.stat().st_mtime
        if age > stale_s:
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_trace_reader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add shared/trace_reader.py tests/test_trace_reader.py
git commit -m "feat: add shared trace reader with staleness check (P3 enforcement)"
```

---

### Task 2: Add Staleness Gate to IR Presence Backend

**Files:**
- Modify: `agents/hapax_daimonion/backends/ir_presence.py`
- Test: `tests/test_backend_staleness.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_backend_staleness.py
"""Test perception backends enforce staleness thresholds."""

import ast


def test_ir_presence_uses_trace_reader():
    """IR presence backend must use read_trace for staleness safety."""
    source = open("agents/hapax_daimonion/backends/ir_presence.py").read()
    assert "read_trace" in source or "trace_age" in source or "stale" in source.lower(), (
        "IR presence backend must check staleness of Pi reports"
    )


def test_vision_uses_trace_reader():
    """Vision backend must use read_trace for staleness safety."""
    source = open("agents/hapax_daimonion/backends/vision.py").read()
    assert "read_trace" in source or "trace_age" in source or "stale" in source.lower(), (
        "Vision backend must check staleness of compositor snapshots"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_backend_staleness.py::test_ir_presence_uses_trace_reader -v`
Expected: FAIL (IR presence doesn't currently check staleness)

- [ ] **Step 3: Add staleness gate to IR presence**

In `agents/hapax_daimonion/backends/ir_presence.py`, modify `contribute()` to use `read_trace`:

```python
from shared.trace_reader import read_trace

IR_STALE_S = 10.0  # Pi reports older than 10s are stale

def contribute(self, behaviors: dict[str, Behavior]) -> None:
    """Read Pi reports with staleness check. Stale → safe defaults."""
    reports = {}
    for role in ("desk", "room", "overhead"):
        path = Path(f"~/hapax-state/pi-noir/{role}.json").expanduser()
        data = read_trace(path, stale_s=IR_STALE_S)
        if data is not None:
            reports[role] = data

    if not reports:
        # All reports stale — set safe defaults
        behaviors["ir_person_detected"].update(False, time.time())
        behaviors["ir_person_count"].update(0, time.time())
        return

    # ... existing fusion logic using only fresh reports ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_backend_staleness.py::test_ir_presence_uses_trace_reader -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_daimonion/backends/ir_presence.py tests/test_backend_staleness.py
git commit -m "feat(ir): enforce staleness threshold on Pi reports (P3)"
```

---

### Task 3: Add Staleness Gate to Vision Backend

**Files:**
- Modify: `agents/hapax_daimonion/backends/vision.py`

- [ ] **Step 1: Add staleness check to vision backend**

In `agents/hapax_daimonion/backends/vision.py`, modify the compositor snapshot reading:

```python
from shared.trace_reader import read_trace

VISION_STALE_S = 30.0

def contribute(self, behaviors: dict[str, Behavior]) -> None:
    """Read compositor snapshots with staleness check."""
    # Replace raw JSON reads with staleness-checked reads
    snapshot_path = Path("/dev/shm/hapax-compositor/snapshot.jpg")
    state_path = Path("/dev/shm/hapax-compositor/visual-layer-state.json")

    state = read_trace(state_path, stale_s=VISION_STALE_S)
    if state is None:
        log.debug("Vision: compositor state stale or missing — skipping")
        return

    # ... existing vision processing with fresh state only ...
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_backend_staleness.py::test_vision_uses_trace_reader -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add agents/hapax_daimonion/backends/vision.py
git commit -m "feat(vision): enforce staleness threshold on compositor snapshots (P3)"
```

---

### Task 4: Imagination Freshness Gate

Skip imagination ticks when observations are stale — don't generate fragments from old data.

**Files:**
- Modify: `agents/imagination_loop.py`
- Test: `tests/test_imagination_freshness.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_imagination_freshness.py
"""Test imagination loop skips ticks when observations are stale."""

import time


def test_observations_freshness_check():
    """Imagination should detect stale observations."""
    from agents.imagination_loop import observations_are_fresh

    # Fresh observations (published 2s ago)
    assert observations_are_fresh(published_at=time.time() - 2, cadence_s=12.0) is True

    # Stale observations (published 30s ago, cadence is 12s → 2x = 24s threshold)
    assert observations_are_fresh(published_at=time.time() - 30, cadence_s=12.0) is False

    # Edge case: exactly at threshold
    assert observations_are_fresh(published_at=time.time() - 24, cadence_s=12.0) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_imagination_freshness.py -v`
Expected: FAIL (no observations_are_fresh function)

- [ ] **Step 3: Implement freshness check**

Add to `agents/imagination_loop.py`:

```python
def observations_are_fresh(*, published_at: float, cadence_s: float) -> bool:
    """Check if observations are fresh enough for imagination.

    Threshold: 2× current cadence. If observations are older than this,
    generating a fragment would be based on stale data.
    """
    age = time.time() - published_at
    return age <= cadence_s * 2.0
```

In the imagination daemon's `tick()` call (or in `agents/imagination_daemon/__main__.py`), add:

```python
# Before calling self._imagination.tick():
obs_data = json.loads(obs_path.read_text())
published_at = obs_data.get("published_at", 0)
if not observations_are_fresh(published_at=published_at, cadence_s=interval):
    log.debug("Skipping imagination tick — observations stale")
    continue
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_imagination_freshness.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/imagination_loop.py tests/test_imagination_freshness.py
git commit -m "feat(imagination): skip ticks when observations are stale (P3)"
```

---

### Task 5: Rate-Limited Staleness Impingements

When a backend detects stale data, it should emit a staleness impingement — but rate-limited to avoid flooding.

**Files:**
- Create: `shared/staleness_emitter.py`
- Test: `tests/test_staleness_emitter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_staleness_emitter.py
"""Test rate-limited staleness impingement emission."""

import time


def test_emits_on_first_staleness():
    """First staleness detection should emit an impingement."""
    from shared.staleness_emitter import StalenessEmitter

    emitter = StalenessEmitter(cooldown_s=60.0)
    imp = emitter.maybe_emit("ir_perception")
    assert imp is not None
    assert imp.source == "staleness.ir_perception"


def test_rate_limits_emission():
    """Second call within cooldown should return None."""
    from shared.staleness_emitter import StalenessEmitter

    emitter = StalenessEmitter(cooldown_s=60.0)
    imp1 = emitter.maybe_emit("ir_perception")
    assert imp1 is not None

    imp2 = emitter.maybe_emit("ir_perception")
    assert imp2 is None  # Within cooldown


def test_different_sources_emit_independently():
    """Different source names should have independent cooldowns."""
    from shared.staleness_emitter import StalenessEmitter

    emitter = StalenessEmitter(cooldown_s=60.0)
    imp1 = emitter.maybe_emit("ir_perception")
    imp2 = emitter.maybe_emit("vision")

    assert imp1 is not None
    assert imp2 is not None  # Different source — independent cooldown
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_staleness_emitter.py -v`
Expected: FAIL (no module shared.staleness_emitter)

- [ ] **Step 3: Implement rate-limited emitter**

```python
# shared/staleness_emitter.py
"""Rate-limited staleness impingement emitter.

Backends call maybe_emit(source) when they detect stale input data.
The emitter returns an Impingement on the first call per source, then
returns None for subsequent calls within the cooldown period.

This prevents flooding the impingement JSONL with repeated staleness
alerts from the same backend.
"""

from __future__ import annotations

import time

from shared.impingement import Impingement, ImpingementType


class StalenessEmitter:
    """Rate-limited staleness impingement emitter."""

    def __init__(self, cooldown_s: float = 60.0) -> None:
        self._cooldown_s = cooldown_s
        self._last_emit: dict[str, float] = {}

    def maybe_emit(self, source: str) -> Impingement | None:
        """Emit a staleness impingement if cooldown has elapsed for this source."""
        now = time.time()
        last = self._last_emit.get(source, 0)
        if now - last < self._cooldown_s:
            return None

        self._last_emit[source] = now
        return Impingement(
            timestamp=now,
            source=f"staleness.{source}",
            type=ImpingementType.ABSOLUTE_THRESHOLD,
            strength=0.4,
            content={"metric": f"{source}_staleness", "value": "stale"},
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_staleness_emitter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add shared/staleness_emitter.py tests/test_staleness_emitter.py
git commit -m "feat: rate-limited staleness impingement emitter"
```
