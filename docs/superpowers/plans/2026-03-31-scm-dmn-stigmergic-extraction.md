# DMN Stigmergic Extraction

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the DMN monolith into independent stigmergic daemons that coordinate through `/dev/shm` traces, eliminating direct imports, TPN control flags, and bidirectional JSONL coupling.

**Architecture:** The current DMN daemon (`agents/dmn/__main__.py`) contains three conceptual components coupled by Python imports: DMN pulse (sensory/evaluative ticks), ImaginationLoop (fragment generation), and content resolver (reference resolution). This plan extracts the imagination loop into an independent daemon and the content resolver into an independent daemon, leaving the DMN as a pure pulse/buffer service. Inter-daemon coordination uses `/dev/shm` atomic JSON files and cursor-tracked JSONL — no imports, no function calls, no flags.

**Tech Stack:** Python 3.12+, pydantic, pydantic-ai, systemd user units, `/dev/shm` atomic JSON, JSONL cursor tracking

**SCM Gaps Closed:** #1 (DMN monolith), #2 (TPN flag), #3 (Fortress bidirectional coupling)

**Depends on:** Nothing (Track A — can proceed immediately)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `agents/dmn/__main__.py` | Modify | Remove ImaginationLoop + resolver. Pure pulse/buffer daemon. |
| `agents/dmn/sensor.py` | Modify | Add `publish_snapshot()` writing to `/dev/shm` |
| `agents/imagination_daemon/__init__.py` | Create | Package init |
| `agents/imagination_daemon/__main__.py` | Create | Independent imagination loop daemon |
| `agents/content_resolver/__init__.py` | Create | Package init |
| `agents/content_resolver/__main__.py` | Create | Independent content resolver daemon |
| `systemd/units/hapax-imagination-loop.service` | Create | Systemd unit for imagination daemon |
| `systemd/units/hapax-content-resolver.service` | Create | Systemd unit for content resolver daemon |
| `systemd/units/hapax-dmn.service` | Modify | Remove imagination/resolver deps, reduce memory |
| `tests/test_dmn_extraction.py` | Create | Verify DMN operates without imagination imports |
| `tests/test_imagination_daemon.py` | Create | Verify imagination daemon reads traces correctly |
| `tests/test_content_resolver_daemon.py` | Create | Verify content resolver watches fragments |

---

### Task 1: Publish Sensor Snapshot to /dev/shm

The imagination loop currently calls `read_all()` in-process. After extraction, it needs to read sensor data from a shared trace. The DMN daemon will publish sensor snapshots to `/dev/shm`.

**Files:**
- Modify: `agents/dmn/sensor.py`
- Test: `tests/test_sensor_snapshot.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sensor_snapshot.py
"""Test sensor snapshot publishing to /dev/shm."""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest


def test_publish_snapshot_writes_atomic_json(tmp_path):
    """Verify publish_snapshot writes atomically via .tmp rename."""
    from agents.dmn.sensor import publish_snapshot

    snapshot = {"stimmung": {"stance": "nominal"}, "perception": {"vad_confidence": 0.8}}
    out = tmp_path / "snapshot.json"
    publish_snapshot(snapshot, path=out)

    assert out.exists()
    data = json.loads(out.read_text())
    assert data["stimmung"]["stance"] == "nominal"
    assert data["perception"]["vad_confidence"] == 0.8
    assert "published_at" in data


def test_publish_snapshot_no_tmp_file_remains(tmp_path):
    """After publish, no .tmp file should exist."""
    from agents.dmn.sensor import publish_snapshot

    snapshot = {"test": True}
    out = tmp_path / "snapshot.json"
    publish_snapshot(snapshot, path=out)

    assert not (tmp_path / "snapshot.json.tmp").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sensor_snapshot.py -v`
Expected: FAIL with "cannot import name 'publish_snapshot'"

- [ ] **Step 3: Implement publish_snapshot**

Add to `agents/dmn/sensor.py`:

```python
import json
import time
from pathlib import Path

SNAPSHOT_PATH = Path("/dev/shm/hapax-sensors/snapshot.json")


def publish_snapshot(snapshot: dict, *, path: Path = SNAPSHOT_PATH) -> None:
    """Write sensor snapshot atomically to /dev/shm for cross-daemon consumption."""
    path.parent.mkdir(parents=True, exist_ok=True)
    enriched = {**snapshot, "published_at": time.time()}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(enriched), encoding="utf-8")
    tmp.rename(path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_sensor_snapshot.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/dmn/sensor.py tests/test_sensor_snapshot.py
git commit -m "feat(dmn): add publish_snapshot for cross-daemon sensor sharing"
```

---

### Task 2: Publish DMN Observations to /dev/shm

The imagination loop currently reads observations from `self._buffer.recent_observations(5)` in-process. After extraction, it reads from a published trace.

**Files:**
- Modify: `agents/dmn/buffer.py`
- Test: `tests/test_dmn_observation_publish.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dmn_observation_publish.py
"""Test DMN buffer publishes observations to /dev/shm."""

import json
from pathlib import Path


def test_publish_observations_writes_list(tmp_path):
    """Verify publish_observations writes a JSON list of recent observations."""
    from agents.dmn.buffer import DMNBuffer

    buf = DMNBuffer()
    buf.add_observation("First observation", [], raw_sensor="")
    buf.add_observation("Second observation", [], raw_sensor="")

    out = tmp_path / "observations.json"
    buf.publish_observations(5, path=out)

    data = json.loads(out.read_text())
    assert len(data["observations"]) == 2
    assert data["observations"][0] == "First observation"


def test_publish_observations_limits_count(tmp_path):
    """Verify publish_observations respects the count limit."""
    from agents.dmn.buffer import DMNBuffer

    buf = DMNBuffer()
    for i in range(10):
        buf.add_observation(f"Obs {i}", [], raw_sensor="")

    out = tmp_path / "observations.json"
    buf.publish_observations(3, path=out)

    data = json.loads(out.read_text())
    assert len(data["observations"]) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dmn_observation_publish.py -v`
Expected: FAIL with "DMNBuffer has no attribute 'publish_observations'"

- [ ] **Step 3: Implement publish_observations**

Add to `agents/dmn/buffer.py`:

```python
import json
import time
from pathlib import Path

OBSERVATIONS_PATH = Path("/dev/shm/hapax-dmn/observations.json")


def publish_observations(self, count: int, *, path: Path = OBSERVATIONS_PATH) -> None:
    """Write recent observations atomically to /dev/shm for imagination daemon."""
    path.parent.mkdir(parents=True, exist_ok=True)
    observations = self.recent_observations(count)
    data = {"observations": observations, "tick": self.tick, "published_at": time.time()}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    tmp.rename(path)
```

Add this method to the `DMNBuffer` class.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_dmn_observation_publish.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/dmn/buffer.py tests/test_dmn_observation_publish.py
git commit -m "feat(dmn): publish observations to /dev/shm for imagination daemon"
```

---

### Task 3: Create Independent Imagination Daemon

The core extraction — ImaginationLoop becomes a standalone daemon reading traces from `/dev/shm`.

**Files:**
- Create: `agents/imagination_daemon/__init__.py`
- Create: `agents/imagination_daemon/__main__.py`
- Test: `tests/test_imagination_daemon.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_imagination_daemon.py
"""Test imagination daemon reads from /dev/shm traces."""

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch


def test_read_observations_from_shm(tmp_path):
    """Verify daemon reads observations from published trace."""
    from agents.imagination_daemon.__main__ import read_observations

    obs_path = tmp_path / "observations.json"
    obs_path.write_text(json.dumps({
        "observations": ["The operator is typing rapidly", "Audio energy rising"],
        "tick": 42,
        "published_at": time.time(),
    }))

    result = read_observations(path=obs_path, stale_s=30.0)
    assert result is not None
    assert len(result) == 2
    assert "typing" in result[0]


def test_read_observations_returns_none_when_stale(tmp_path):
    """Verify daemon rejects stale observations."""
    from agents.imagination_daemon.__main__ import read_observations

    obs_path = tmp_path / "observations.json"
    obs_path.write_text(json.dumps({
        "observations": ["Old observation"],
        "tick": 1,
        "published_at": time.time() - 60.0,
    }))

    result = read_observations(path=obs_path, stale_s=30.0)
    assert result is None


def test_read_snapshot_from_shm(tmp_path):
    """Verify daemon reads sensor snapshot from published trace."""
    from agents.imagination_daemon.__main__ import read_snapshot

    snap_path = tmp_path / "snapshot.json"
    snap_path.write_text(json.dumps({
        "stimmung": {"stance": "nominal"},
        "published_at": time.time(),
    }))

    result = read_snapshot(path=snap_path, stale_s=30.0)
    assert result is not None
    assert result["stimmung"]["stance"] == "nominal"


def test_read_snapshot_returns_none_when_missing(tmp_path):
    """Verify daemon returns None for missing snapshot."""
    from agents.imagination_daemon.__main__ import read_snapshot

    result = read_snapshot(path=tmp_path / "nonexistent.json", stale_s=30.0)
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_imagination_daemon.py -v`
Expected: FAIL with "No module named 'agents.imagination_daemon'"

- [ ] **Step 3: Create imagination daemon package**

```python
# agents/imagination_daemon/__init__.py
```

```python
# agents/imagination_daemon/__main__.py
"""Imagination daemon — independent stigmergic imagination loop.

Reads observations and sensor snapshot from /dev/shm traces published
by the DMN pulse daemon. Generates ImaginationFragment objects and
publishes them to /dev/shm/hapax-imagination/current.json.

Emits impingements for high-salience fragments to the cross-daemon
JSONL transport.

Usage:
    uv run python -m agents.imagination_daemon
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import time
from pathlib import Path

from agents.imagination import CURRENT_PATH
from agents.imagination_loop import ImaginationLoop
from shared.impingement import Impingement

log = logging.getLogger("imagination-daemon")

OBSERVATIONS_PATH = Path("/dev/shm/hapax-dmn/observations.json")
SNAPSHOT_PATH = Path("/dev/shm/hapax-sensors/snapshot.json")
STIMMUNG_PATH = Path("/dev/shm/hapax-stimmung/state.json")
IMPINGEMENTS_FILE = Path("/dev/shm/hapax-dmn/impingements.jsonl")

OBSERVATION_STALE_S = 30.0
SNAPSHOT_STALE_S = 30.0


def read_observations(
    *, path: Path = OBSERVATIONS_PATH, stale_s: float = OBSERVATION_STALE_S
) -> list[str] | None:
    """Read observations from DMN pulse trace. Returns None if stale or missing."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        published_at = data.get("published_at", 0)
        if time.time() - published_at > stale_s:
            return None
        return data.get("observations", [])
    except (OSError, json.JSONDecodeError, KeyError):
        return None


def read_snapshot(
    *, path: Path = SNAPSHOT_PATH, stale_s: float = SNAPSHOT_STALE_S
) -> dict | None:
    """Read sensor snapshot from /dev/shm. Returns None if stale or missing."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        published_at = data.get("published_at", 0)
        if time.time() - published_at > stale_s:
            return None
        return data
    except (OSError, json.JSONDecodeError):
        return None


def _read_stimmung_stance() -> str:
    """Read current stimmung stance for cadence modulation."""
    try:
        data = json.loads(STIMMUNG_PATH.read_text(encoding="utf-8"))
        return data.get("stance", "nominal")
    except (OSError, json.JSONDecodeError):
        return "nominal"


def _emit_impingements(impingements: list[Impingement]) -> None:
    """Append impingements to cross-daemon JSONL transport."""
    if not impingements:
        return
    try:
        IMPINGEMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with IMPINGEMENTS_FILE.open("a", encoding="utf-8") as f:
            for imp in impingements:
                f.write(imp.model_dump_json() + "\n")
    except OSError:
        log.warning("Failed to write impingements", exc_info=True)


class ImaginationDaemon:
    """Independent imagination loop daemon reading from /dev/shm traces."""

    def __init__(self) -> None:
        self._imagination = ImaginationLoop()
        self._running = True

    async def run(self) -> None:
        log.info("Imagination daemon starting")

        while self._running:
            try:
                observations = read_observations()
                snapshot = read_snapshot()

                if observations is not None and snapshot is not None:
                    await self._imagination.tick(observations, snapshot)

                    # Drain and emit impingements
                    impingements = self._imagination.drain_impingements()
                    _emit_impingements(impingements)
                else:
                    log.debug(
                        "Skipping tick — observations=%s snapshot=%s",
                        "fresh" if observations is not None else "stale/missing",
                        "fresh" if snapshot is not None else "stale/missing",
                    )
            except Exception:
                log.warning("Imagination tick failed", exc_info=True)

            interval = self._imagination.cadence.current_interval()

            # Stimmung modulation: double cadence when degraded, pause when critical
            stance = _read_stimmung_stance()
            if stance == "critical":
                interval = 60.0  # effectively pause
            elif stance == "degraded":
                interval *= 2.0

            await asyncio.sleep(interval)

        log.info("Imagination daemon stopped")

    def stop(self) -> None:
        self._running = False


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    daemon = ImaginationDaemon()

    loop = asyncio.new_event_loop()

    def _handle_signal(sig: int, frame: object) -> None:
        daemon.stop()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    try:
        loop.run_until_complete(daemon.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_imagination_daemon.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/imagination_daemon/ tests/test_imagination_daemon.py
git commit -m "feat: create independent imagination daemon reading from /dev/shm traces"
```

---

### Task 4: Create Independent Content Resolver Daemon

**Files:**
- Create: `agents/content_resolver/__init__.py`
- Create: `agents/content_resolver/__main__.py`
- Test: `tests/test_content_resolver_daemon.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_content_resolver_daemon.py
"""Test content resolver daemon watches for new fragments."""

import json
import time
from pathlib import Path


def test_detect_new_fragment(tmp_path):
    """Verify resolver detects new fragment IDs."""
    from agents.content_resolver.__main__ import check_for_new_fragment

    current = tmp_path / "current.json"
    current.write_text(json.dumps({"id": "abc123", "content_references": []}))

    frag_id, data = check_for_new_fragment(last_id="", path=current)
    assert frag_id == "abc123"
    assert data is not None


def test_skip_same_fragment(tmp_path):
    """Verify resolver skips already-processed fragment."""
    from agents.content_resolver.__main__ import check_for_new_fragment

    current = tmp_path / "current.json"
    current.write_text(json.dumps({"id": "abc123", "content_references": []}))

    frag_id, data = check_for_new_fragment(last_id="abc123", path=current)
    assert frag_id is None


def test_handle_missing_file(tmp_path):
    """Verify resolver handles missing current.json gracefully."""
    from agents.content_resolver.__main__ import check_for_new_fragment

    frag_id, data = check_for_new_fragment(last_id="", path=tmp_path / "missing.json")
    assert frag_id is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_content_resolver_daemon.py -v`
Expected: FAIL with "No module named 'agents.content_resolver'"

- [ ] **Step 3: Create content resolver daemon**

```python
# agents/content_resolver/__init__.py
```

```python
# agents/content_resolver/__main__.py
"""Content resolver daemon — resolves slow imagination content references.

Watches /dev/shm/hapax-imagination/current.json for new fragments.
Resolves slow content types (text, qdrant_query, url) to JPEG files.
Writes resolved content to /dev/shm/hapax-imagination/content/active/.

Usage:
    uv run python -m agents.content_resolver
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import time
from pathlib import Path

from agents.imagination import CURRENT_PATH, ImaginationFragment
from agents.imagination_resolver import CONTENT_DIR, resolve_references_staged

log = logging.getLogger("content-resolver")

POLL_INTERVAL_S = 0.5
MAX_FAILURES_PER_FRAGMENT = 5
SKIP_DURATION_S = 60.0


def check_for_new_fragment(
    last_id: str, *, path: Path = CURRENT_PATH
) -> tuple[str | None, dict | None]:
    """Check for a new imagination fragment. Returns (id, data) or (None, None)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        frag_id = data.get("id", "")
        if frag_id and frag_id != last_id:
            return frag_id, data
        return None, None
    except (OSError, json.JSONDecodeError):
        return None, None


class ContentResolverDaemon:
    """Watches for new imagination fragments and resolves slow content."""

    def __init__(self) -> None:
        self._running = True
        self._failures: dict[str, int] = {}
        self._skip_until: dict[str, float] = {}
        self._last_fragment_id = ""

    async def run(self) -> None:
        log.info("Content resolver daemon starting")
        CONTENT_DIR.mkdir(parents=True, exist_ok=True)

        while self._running:
            try:
                frag_id, data = check_for_new_fragment(self._last_fragment_id)
                if frag_id is not None and data is not None:
                    skip_until = self._skip_until.get(frag_id)
                    if skip_until and time.time() < skip_until:
                        pass
                    else:
                        if skip_until:
                            del self._skip_until[frag_id]
                        self._last_fragment_id = frag_id
                        try:
                            frag = ImaginationFragment.model_validate(data)
                            resolve_references_staged(frag)
                            self._failures.pop(frag_id, None)
                            log.debug("Resolved content for fragment %s", frag_id)
                        except Exception:
                            count = self._failures.get(frag_id, 0) + 1
                            self._failures[frag_id] = count
                            if count >= MAX_FAILURES_PER_FRAGMENT:
                                self._skip_until[frag_id] = time.time() + SKIP_DURATION_S
                                log.warning(
                                    "Skipping fragment %s after %d failures", frag_id, count
                                )
                            else:
                                log.debug("Resolver failed for %s (%d/%d)", frag_id, count, MAX_FAILURES_PER_FRAGMENT)
            except Exception:
                log.warning("Resolver tick failed", exc_info=True)

            await asyncio.sleep(POLL_INTERVAL_S)

        log.info("Content resolver daemon stopped")

    def stop(self) -> None:
        self._running = False


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    daemon = ContentResolverDaemon()

    loop = asyncio.new_event_loop()

    def _handle_signal(sig: int, frame: object) -> None:
        daemon.stop()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    try:
        loop.run_until_complete(daemon.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_content_resolver_daemon.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/content_resolver/ tests/test_content_resolver_daemon.py
git commit -m "feat: create independent content resolver daemon"
```

---

### Task 5: Strip DMN Daemon of Imagination and Resolver

Remove the extracted components from the DMN daemon. After this, DMN is a pure pulse/buffer service.

**Files:**
- Modify: `agents/dmn/__main__.py`
- Test: `tests/test_dmn_extraction.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dmn_extraction.py
"""Verify DMN daemon no longer imports imagination modules."""

import ast
import textwrap


def test_dmn_main_does_not_import_imagination_loop():
    """DMN __main__.py must not import ImaginationLoop."""
    source = open("agents/dmn/__main__.py").read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "imagination_loop" in node.module:
                raise AssertionError(
                    f"DMN still imports from {node.module} — extraction incomplete"
                )


def test_dmn_main_does_not_import_imagination_resolver():
    """DMN __main__.py must not import imagination_resolver."""
    source = open("agents/dmn/__main__.py").read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "imagination_resolver" in node.module:
                raise AssertionError(
                    f"DMN still imports from {node.module} — extraction incomplete"
                )


def test_dmn_main_does_not_reference_tpn_active():
    """DMN must not read TPN active flag directly (use perception signals instead)."""
    source = open("agents/dmn/__main__.py").read()
    assert "tpn_active" not in source.lower() or "# legacy" in source.lower(), (
        "DMN still references tpn_active — replace with perception signal observation"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dmn_extraction.py -v`
Expected: FAIL (DMN still imports ImaginationLoop and imagination_resolver)

- [ ] **Step 3: Strip DMN daemon**

Modify `agents/dmn/__main__.py`:

1. Remove these imports:
```python
# REMOVE:
from agents.imagination import CURRENT_PATH, ImaginationFragment
from agents.imagination_loop import ImaginationLoop
from agents.imagination_resolver import CONTENT_DIR, resolve_references_staged
```

2. Remove from `DMNDaemon.__init__`:
```python
# REMOVE:
self._imagination = ImaginationLoop()
self._resolver_failures: dict[str, int] = {}
self._resolver_skip_until: dict[str, float] = {}
self._resolver_consecutive_failures: int = 0
```

3. Remove from `DMNDaemon.run()`:
```python
# REMOVE:
asyncio.create_task(self._imagination_loop())
asyncio.create_task(self._resolver_loop())

# REMOVE the first imagination tick block (lines 84-92)
```

4. Remove these entire methods:
- `_imagination_loop()`
- `_resolver_loop()`
- `_emit_resolver_degraded()`

5. In `_write_output()`, remove imagination drain:
```python
# REMOVE:
impingements.extend(self._imagination.drain_impingements())
```

6. Remove `_read_tpn_active()` function entirely.

7. In `_write_output()`, remove TPN active reading:
```python
# REMOVE:
self._pulse.set_tpn_active(_read_tpn_active())
```

8. Add snapshot publishing to `_write_output()`:
```python
from agents.dmn.sensor import read_all, publish_snapshot

# In _write_output(), after writing buffer:
try:
    snapshot = read_all()
    publish_snapshot(snapshot)
except Exception:
    log.warning("Failed to publish sensor snapshot", exc_info=True)

# Publish observations for imagination daemon
try:
    self._buffer.publish_observations(5)
except Exception:
    log.warning("Failed to publish observations", exc_info=True)
```

9. In `_write_output()`, remove status fields referencing imagination:
```python
# REMOVE from status dict:
"imagination_active": self._imagination.activation_level > 0,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_dmn_extraction.py -v`
Expected: PASS

- [ ] **Step 5: Verify DMN still starts**

Run: `uv run python -c "from agents.dmn.__main__ import DMNDaemon; print('DMN imports clean')"`
Expected: "DMN imports clean"

- [ ] **Step 6: Commit**

```bash
git add agents/dmn/__main__.py tests/test_dmn_extraction.py
git commit -m "refactor(dmn): strip imagination loop and content resolver from DMN daemon"
```

---

### Task 6: Separate Fortress Feedback into Dedicated File

Replace the bidirectional read-write on `impingements.jsonl` with Fortress writing to its own file.

**Files:**
- Modify: `agents/dmn/__main__.py`
- Test: `tests/test_fortress_feedback_separation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fortress_feedback_separation.py
"""Test fortress feedback uses separate JSONL file."""

import json
import time
from pathlib import Path


def test_consume_fortress_feedback_reads_separate_file(tmp_path):
    """Verify DMN reads fortress feedback from dedicated file, not impingements.jsonl."""
    from agents.dmn.__main__ import DMNDaemon
    from shared.impingement import Impingement, ImpingementType

    # Write fortress feedback to dedicated path
    feedback_path = tmp_path / "fortress-actions.jsonl"
    imp = Impingement(
        timestamp=time.time(),
        source="fortress.action_taken",
        type=ImpingementType.PATTERN_MATCH,
        strength=0.5,
        content={"action": "drink_ordered"},
    )
    feedback_path.write_text(imp.model_dump_json() + "\n")

    daemon = DMNDaemon()
    daemon._consume_fortress_feedback(path=feedback_path)

    # Should have consumed 1 feedback item (no assert crash = success)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_fortress_feedback_separation.py -v`
Expected: FAIL (_consume_fortress_feedback doesn't accept path parameter)

- [ ] **Step 3: Modify _consume_fortress_feedback to read from dedicated file**

In `agents/dmn/__main__.py`, change `_consume_fortress_feedback`:

```python
FORTRESS_ACTIONS_FILE = DMN_STATE_DIR / "fortress-actions.jsonl"

def _consume_fortress_feedback(self, *, path: Path = FORTRESS_ACTIONS_FILE) -> None:
    """Read fortress action feedback from dedicated JSONL (one-way, no dedup needed)."""
    if not path.exists():
        return
    try:
        size = path.stat().st_size
        if size <= self._feedback_cursor:
            return
        with path.open("r", encoding="utf-8") as f:
            f.seek(self._feedback_cursor)
            feedback = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    imp = Impingement.model_validate_json(line)
                    feedback.append(imp)
                except Exception:
                    continue
            self._feedback_cursor = f.tell()
        if feedback:
            self._pulse.consume_fortress_feedback(feedback)
            log.debug("Consumed %d fortress feedback items", len(feedback))
    except OSError:
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_fortress_feedback_separation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/dmn/__main__.py tests/test_fortress_feedback_separation.py
git commit -m "refactor(dmn): separate fortress feedback into dedicated JSONL file"
```

---

### Task 7: Create Systemd Units for New Daemons

**Files:**
- Create: `systemd/units/hapax-imagination-loop.service`
- Create: `systemd/units/hapax-content-resolver.service`
- Modify: `systemd/units/hapax-dmn.service`

- [ ] **Step 1: Create imagination loop service unit**

```ini
# systemd/units/hapax-imagination-loop.service
[Unit]
Description=Hapax Imagination Loop Daemon
After=hapax-secrets.service hapax-dmn.service
Wants=hapax-dmn.service
PartOf=hapax-visual-stack.target

[Service]
Type=simple
EnvironmentFile=/run/user/1000/hapax-secrets.env
Environment=OMP_NUM_THREADS=2
Environment=MKL_NUM_THREADS=2
ExecStart=%h/.local/bin/uv run python -m agents.imagination_daemon
WorkingDirectory=%h/projects/hapax-council
MemoryMax=1G
Restart=on-failure
RestartSec=10
StartLimitBurst=5
StartLimitIntervalSec=300
OnFailure=notify-failure@%n.service

[Install]
WantedBy=hapax-visual-stack.target
```

- [ ] **Step 2: Create content resolver service unit**

```ini
# systemd/units/hapax-content-resolver.service
[Unit]
Description=Hapax Content Resolver Daemon
After=hapax-secrets.service hapax-imagination-loop.service
Wants=hapax-imagination-loop.service
PartOf=hapax-visual-stack.target

[Service]
Type=simple
EnvironmentFile=/run/user/1000/hapax-secrets.env
ExecStart=%h/.local/bin/uv run python -m agents.content_resolver
WorkingDirectory=%h/projects/hapax-council
MemoryMax=512M
Restart=on-failure
RestartSec=10
StartLimitBurst=5
StartLimitIntervalSec=300
OnFailure=notify-failure@%n.service

[Install]
WantedBy=hapax-visual-stack.target
```

- [ ] **Step 3: Update DMN service unit — reduce memory**

Modify `systemd/units/hapax-dmn.service`: change `MemoryMax=2G` to `MemoryMax=1G` (no longer hosts imagination LLM calls).

- [ ] **Step 4: Commit**

```bash
git add systemd/units/hapax-imagination-loop.service systemd/units/hapax-content-resolver.service systemd/units/hapax-dmn.service
git commit -m "feat(systemd): add units for extracted imagination and content resolver daemons"
```

---

### Task 8: Update Fortress to Write to Dedicated Actions File

**Files:**
- Modify: `agents/fortress/__main__.py` (or wherever fortress writes action_taken impingements)
- Test: `tests/test_fortress_actions_file.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fortress_actions_file.py
"""Test fortress writes action feedback to dedicated file."""

from pathlib import Path


def test_fortress_actions_path_constant():
    """Verify fortress uses the correct dedicated actions path."""
    # The fortress daemon should write to fortress-actions.jsonl, not impingements.jsonl
    source = open("agents/fortress/__main__.py").read()
    assert "fortress-actions.jsonl" in source or "FORTRESS_ACTIONS_FILE" in source, (
        "Fortress must write to dedicated actions file, not impingements.jsonl"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_fortress_actions_file.py -v`
Expected: FAIL (fortress still writes to impingements.jsonl)

- [ ] **Step 3: Update fortress to write to dedicated file**

In `agents/fortress/__main__.py`, change the action_taken impingement write path from `/dev/shm/hapax-dmn/impingements.jsonl` to `/dev/shm/hapax-dmn/fortress-actions.jsonl`.

Find the line that opens the impingements file for append with source="fortress.action_taken" and change the path.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_fortress_actions_file.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/fortress/__main__.py tests/test_fortress_actions_file.py
git commit -m "refactor(fortress): write action feedback to dedicated JSONL file"
```

---

### Task 9: Integration Test — Full Stigmergic Chain

**Files:**
- Test: `tests/test_stigmergic_chain.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_stigmergic_chain.py
"""Integration test: DMN → /dev/shm → Imagination → /dev/shm → Resolver chain."""

import json
import time
from pathlib import Path


def test_observations_flow_through_shm(tmp_path):
    """Verify observations published by DMN can be read by imagination daemon."""
    from agents.dmn.buffer import DMNBuffer
    from agents.imagination_daemon.__main__ import read_observations

    # DMN publishes observations
    buf = DMNBuffer()
    buf.add_observation("Operator is scratching vinyl records", [], raw_sensor="")
    obs_path = tmp_path / "observations.json"
    buf.publish_observations(5, path=obs_path)

    # Imagination daemon reads them
    observations = read_observations(path=obs_path, stale_s=30.0)
    assert observations is not None
    assert "scratching" in observations[0]


def test_snapshot_flow_through_shm(tmp_path):
    """Verify sensor snapshot published by DMN can be read by imagination daemon."""
    from agents.dmn.sensor import publish_snapshot
    from agents.imagination_daemon.__main__ import read_snapshot

    # DMN publishes snapshot
    snapshot = {"stimmung": {"stance": "nominal"}, "perception": {"vad_confidence": 0.9}}
    snap_path = tmp_path / "snapshot.json"
    publish_snapshot(snapshot, path=snap_path)

    # Imagination daemon reads it
    result = read_snapshot(path=snap_path, stale_s=30.0)
    assert result is not None
    assert result["stimmung"]["stance"] == "nominal"


def test_fragment_flow_through_shm(tmp_path):
    """Verify fragment published by imagination can be detected by resolver."""
    from agents.content_resolver.__main__ import check_for_new_fragment

    # Imagination publishes fragment
    current = tmp_path / "current.json"
    current.write_text(json.dumps({
        "id": "test_frag_001",
        "content_references": [{"kind": "text", "value": "test content"}],
        "timestamp": time.time(),
    }))

    # Resolver detects it
    frag_id, data = check_for_new_fragment(last_id="", path=current)
    assert frag_id == "test_frag_001"
    assert len(data["content_references"]) == 1
```

- [ ] **Step 2: Run integration test**

Run: `uv run pytest tests/test_stigmergic_chain.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_stigmergic_chain.py
git commit -m "test: integration test for DMN → imagination → resolver stigmergic chain"
```
