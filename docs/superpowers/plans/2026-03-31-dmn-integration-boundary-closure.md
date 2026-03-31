# DMN Integration Boundary Closure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all DMN integration boundary gaps — shared impingement consumer, degradation signal wiring (stimmung + capability), Reverie dead code cleanup.

**Architecture:** Extract duplicated JSONL consumer into `shared/impingement_consumer.py`, migrate Fortress and Daimonion consumers, wire DMN health into stimmung via VLA, register `system_awareness` capability in Daimonion for active degradation response, delete dead `fortress_visual_response` routing.

**Tech Stack:** Python 3.12+, pydantic, asyncio, /dev/shm JSON/JSONL, pytest (unittest.mock only, self-contained tests, asyncio_mode=auto)

**Spec:** `docs/superpowers/specs/2026-03-31-dmn-integration-boundary-closure-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `shared/impingement_consumer.py` | Cursor-tracked JSONL reader for cross-daemon impingement transport |
| Create | `tests/test_impingement_consumer.py` | Unit tests for consumer utility |
| Create | `agents/hapax_daimonion/system_awareness.py` | SystemAwarenessCapability class |
| Create | `tests/test_system_awareness.py` | Unit tests for system awareness capability |
| Create | `tests/test_stimmung_dmn_health.py` | Unit tests for VLA DMN health reader |
| Modify | `agents/fortress/__main__.py:245-277` | Replace hand-rolled JSONL consumer with shared utility |
| Modify | `agents/hapax_daimonion/run_loops_aux.py:113-185` | Replace hand-rolled JSONL consumer with shared utility |
| Modify | `agents/hapax_daimonion/init_pipeline.py:105-149` | Register system_awareness capability |
| Modify | `agents/visual_layer_aggregator/stimmung_methods.py:25-98` | Add DMN health reader |
| Modify | `agents/dmn/__main__.py:219-234` | Delete fortress_visual_response routing |
| Modify | `agents/reverie/actuation.py:67-78` | Deregister fortress_visual_response capability |

---

## Stage 1: Shared ImpingementConsumer

### Task 1: Create ImpingementConsumer with tests

**Files:**
- Create: `shared/impingement_consumer.py`
- Create: `tests/test_impingement_consumer.py`

- [ ] **Step 1: Write failing tests**

```python
"""tests/test_impingement_consumer.py — ImpingementConsumer unit tests."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from shared.impingement import Impingement, ImpingementType
from shared.impingement_consumer import ImpingementConsumer


def _make_imp(source: str = "dmn.test", strength: float = 0.5) -> Impingement:
    return Impingement(
        timestamp=time.time(),
        source=source,
        type=ImpingementType.ABSOLUTE_THRESHOLD,
        strength=strength,
        content={"metric": "test"},
    )


def _write_jsonl(path: Path, imps: list[Impingement]) -> None:
    with path.open("a", encoding="utf-8") as f:
        for imp in imps:
            f.write(imp.model_dump_json() + "\n")


class TestImpingementConsumer:
    def test_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "imp.jsonl"
        path.write_text("", encoding="utf-8")
        consumer = ImpingementConsumer(path)
        assert consumer.read_new() == []
        assert consumer.cursor == 0

    def test_missing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.jsonl"
        consumer = ImpingementConsumer(path)
        assert consumer.read_new() == []

    def test_reads_new_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "imp.jsonl"
        imp1 = _make_imp("source.a")
        imp2 = _make_imp("source.b")
        _write_jsonl(path, [imp1, imp2])

        consumer = ImpingementConsumer(path)
        result = consumer.read_new()
        assert len(result) == 2
        assert result[0].source == "source.a"
        assert result[1].source == "source.b"
        assert consumer.cursor == 2

    def test_cursor_advances(self, tmp_path: Path) -> None:
        path = tmp_path / "imp.jsonl"
        _write_jsonl(path, [_make_imp("first")])

        consumer = ImpingementConsumer(path)
        first = consumer.read_new()
        assert len(first) == 1

        # Append more lines
        _write_jsonl(path, [_make_imp("second"), _make_imp("third")])
        second = consumer.read_new()
        assert len(second) == 2
        assert second[0].source == "second"
        assert consumer.cursor == 3

    def test_no_new_lines_returns_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "imp.jsonl"
        _write_jsonl(path, [_make_imp()])

        consumer = ImpingementConsumer(path)
        consumer.read_new()  # consume first
        assert consumer.read_new() == []

    def test_malformed_lines_skipped(self, tmp_path: Path) -> None:
        path = tmp_path / "imp.jsonl"
        imp = _make_imp("valid")
        with path.open("w", encoding="utf-8") as f:
            f.write("not json at all\n")
            f.write(imp.model_dump_json() + "\n")
            f.write("{bad json\n")

        consumer = ImpingementConsumer(path)
        result = consumer.read_new()
        assert len(result) == 1
        assert result[0].source == "valid"
        assert consumer.cursor == 3  # all 3 lines consumed (cursor advanced past bad ones)

    def test_blank_lines_skipped(self, tmp_path: Path) -> None:
        path = tmp_path / "imp.jsonl"
        imp = _make_imp()
        with path.open("w", encoding="utf-8") as f:
            f.write("\n")
            f.write(imp.model_dump_json() + "\n")
            f.write("\n")

        consumer = ImpingementConsumer(path)
        result = consumer.read_new()
        assert len(result) == 1

    def test_oserror_returns_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "imp.jsonl"
        _write_jsonl(path, [_make_imp()])
        consumer = ImpingementConsumer(path)
        with patch.object(Path, "read_text", side_effect=OSError("disk")):
            assert consumer.read_new() == []
        # cursor unchanged after error
        assert consumer.cursor == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_impingement_consumer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shared.impingement_consumer'`

- [ ] **Step 3: Write ImpingementConsumer**

```python
"""shared/impingement_consumer.py — Cursor-tracked JSONL impingement reader.

Extracts the duplicated consumer pattern used by Fortress, Daimonion,
and DMN-side Reverie routing into a single reusable utility.

Usage:
    consumer = ImpingementConsumer(Path("/dev/shm/hapax-dmn/impingements.jsonl"))
    for imp in consumer.read_new():
        candidates = pipeline.select(imp)
        # daemon-specific routing
"""

from __future__ import annotations

import logging
from pathlib import Path

from shared.impingement import Impingement

log = logging.getLogger(__name__)


class ImpingementConsumer:
    """Cursor-tracked reader for JSONL impingement files.

    Reads new lines since the last call to read_new(), parses them as
    Impingement models, and advances the cursor. Malformed lines are
    skipped with a debug log. OSErrors return empty results without
    advancing the cursor.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._cursor: int = 0

    def read_new(self) -> list[Impingement]:
        """Return new impingements since last read. Non-blocking."""
        if not self._path.exists():
            return []
        try:
            text = self._path.read_text(encoding="utf-8")
            lines = text.strip().split("\n") if text.strip() else []
            new_lines = lines[self._cursor :]
            if not new_lines:
                return []
            self._cursor = len(lines)
            result: list[Impingement] = []
            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    result.append(Impingement.model_validate_json(line))
                except Exception:
                    log.debug("Malformed impingement line skipped: %s", line[:80])
            return result
        except OSError:
            log.debug("Failed to read %s", self._path, exc_info=True)
            return []

    @property
    def cursor(self) -> int:
        """Current line-based offset into the JSONL file."""
        return self._cursor
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_impingement_consumer.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add shared/impingement_consumer.py tests/test_impingement_consumer.py
git commit -m "feat: shared ImpingementConsumer utility for cross-daemon JSONL transport"
```

### Task 2: Migrate Fortress consumer

**Files:**
- Modify: `agents/fortress/__main__.py:245-277`

- [ ] **Step 1: Run existing fortress tests to confirm baseline**

Run: `uv run pytest tests/ -k fortress -v --timeout=30`
Expected: All pass (note count for regression check)

- [ ] **Step 2: Replace hand-rolled consumer in Fortress**

In `agents/fortress/__main__.py`, add import near the top (with other shared imports):

```python
from shared.impingement_consumer import ImpingementConsumer
```

In `__init__`, replace `self._dmn_impingement_cursor = 0` with:

```python
self._impingement_consumer = ImpingementConsumer(
    Path("/dev/shm/hapax-dmn/impingements.jsonl")
)
```

Replace the `_impingement_consumer_loop` method (lines 245-277) with:

```python
    async def _impingement_consumer_loop(self) -> None:
        """Poll DMN impingements and route through affordance pipeline."""
        while self._running:
            try:
                for imp in self._impingement_consumer.read_new():
                    try:
                        candidates = self._affordance_pipeline.select(imp)
                        for c in candidates:
                            if c.capability_name == "fortress_governance":
                                self._fortress_capability.activate(imp, c.combined)
                        if candidates:
                            self._affordance_pipeline.add_inhibition(imp, duration_s=60.0)
                    except Exception:
                        pass
            except Exception:
                log.debug("Impingement consumer error (non-fatal)", exc_info=True)

            await asyncio.sleep(1.0)
```

- [ ] **Step 3: Run fortress tests**

Run: `uv run pytest tests/ -k fortress -v --timeout=30`
Expected: Same count passing as Step 1

- [ ] **Step 4: Commit**

```bash
git add agents/fortress/__main__.py
git commit -m "refactor: migrate Fortress impingement consumer to shared utility"
```

### Task 3: Migrate Daimonion consumer

**Files:**
- Modify: `agents/hapax_daimonion/run_loops_aux.py:113-185`
- Modify: `agents/hapax_daimonion/init_pipeline.py:109`

- [ ] **Step 1: Run existing daimonion tests to confirm baseline**

Run: `uv run pytest tests/ -k "daimonion or vocal_chain" -v --timeout=30`
Expected: All pass (note count)

- [ ] **Step 2: Replace hand-rolled consumer in Daimonion**

In `agents/hapax_daimonion/run_loops_aux.py`, add import:

```python
from shared.impingement_consumer import ImpingementConsumer
```

Replace the `impingement_consumer_loop` function (lines 113-185) with:

```python
async def impingement_consumer_loop(daemon: VoiceDaemon) -> None:
    """Poll DMN impingements and route through affordance pipeline."""
    consumer = ImpingementConsumer(Path("/dev/shm/hapax-dmn/impingements.jsonl"))

    while daemon._running:
        try:
            for imp in consumer.read_new():
                try:
                    candidates = await asyncio.to_thread(
                        daemon._affordance_pipeline.select, imp
                    )
                    for c in candidates:
                        if c.capability_name == "speech_production":
                            daemon._speech_capability.activate(imp, c.combined)
                            log.info(
                                "Speech recruited via affordance: %s (score=%.2f)",
                                imp.content.get("metric", imp.source),
                                c.combined,
                            )
                        elif c.capability_name == "system_awareness":
                            if hasattr(daemon, "_system_awareness"):
                                score = daemon._system_awareness.can_resolve(imp)
                                if score > 0:
                                    daemon._system_awareness.activate(imp, score)
                    # Vocal chain: modulate voice character via MIDI
                    if hasattr(daemon, "_vocal_chain") and daemon._vocal_chain is not None:
                        vc_score = daemon._vocal_chain.can_resolve(imp)
                        if vc_score > 0.0:
                            daemon._vocal_chain.activate_from_impingement(imp)
                            log.debug(
                                "Vocal chain activated: %s (score=%.2f)",
                                imp.content.get("metric", imp.source),
                                vc_score,
                            )
                    # Cross-modal coordination
                    if len(candidates) > 1 and hasattr(daemon, "_expression_coordinator"):
                        recruited_pairs = [
                            (
                                c.capability_name,
                                getattr(daemon, f"_{c.capability_name}", None),
                            )
                            for c in candidates
                        ]
                        recruited_pairs = [
                            (n, cap) for n, cap in recruited_pairs if cap is not None
                        ]
                        if len(recruited_pairs) > 1:
                            activations = daemon._expression_coordinator.coordinate(
                                imp.content, recruited_pairs
                            )
                            if activations:
                                log.info(
                                    "Cross-modal coordination: %d modalities for %s",
                                    len(activations),
                                    imp.content.get("narrative", "")[:40],
                                )
                    # Proactive utterance
                    if imp.source == "imagination" and imp.strength >= 0.65:
                        _handle_proactive_impingement(daemon, imp)
                except Exception:
                    pass
        except Exception:
            log.debug("Impingement consumer error (non-fatal)", exc_info=True)

        await asyncio.sleep(0.5)
```

Note: The `system_awareness` routing is added here but won't activate until Task 6 registers the capability. The `hasattr` guard ensures no crash.

- [ ] **Step 3: Remove stale cursor init**

In `agents/hapax_daimonion/init_pipeline.py`, line 109, delete:

```python
    daemon._dmn_impingement_cursor = 0
```

The cursor is now inside the `ImpingementConsumer` local to the loop function.

- [ ] **Step 4: Run daimonion tests**

Run: `uv run pytest tests/ -k "daimonion or vocal_chain" -v --timeout=30`
Expected: Same count passing as Step 1

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_daimonion/run_loops_aux.py agents/hapax_daimonion/init_pipeline.py
git commit -m "refactor: migrate Daimonion impingement consumer to shared utility"
```

---

## Stage 2: Integration Boundary Closure

### Task 4: Delete fortress_visual_response dead code

**Files:**
- Modify: `agents/dmn/__main__.py:219-234`
- Modify: `agents/reverie/actuation.py:67-78`

- [ ] **Step 1: Delete dead routing in DMN __main__.py**

In `agents/dmn/__main__.py`, replace the Reverie routing block (lines 219-234):

Delete the `fortress_visual_response` branch only. The block becomes:

```python
            # Feed impingements to Reverie via affordance pipeline
            if self._reverie is not None:
                for imp in impingements:
                    candidates = self._reverie.pipeline.select(imp)
                    for c in candidates:
                        if c.capability_name == "shader_graph":
                            self._reverie.shader_capability.activate(imp, imp.strength)
                        elif c.capability_name == "visual_chain":
                            score = self._reverie.visual_chain.can_resolve(imp)
                            if score > 0:
                                self._reverie.visual_chain.activate(imp, score)
```

- [ ] **Step 2: Deregister capability in Reverie actuation**

In `agents/reverie/actuation.py`, replace the pipeline init (lines 72-78):

```python
        p = AffordancePipeline()
        for n, d in [
            ("shader_graph", "Activate shader graph effects from imagination"),
            ("visual_chain", "Modulate visual chain from stimmung/evaluative"),
        ]:
            p.index_capability(CapabilityRecord(name=n, description=d, daemon="reverie"))
        return p
```

- [ ] **Step 3: Run DMN + Reverie tests**

Run: `uv run pytest tests/ -k "dmn or reverie or visual" -v --timeout=30`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add agents/dmn/__main__.py agents/reverie/actuation.py
git commit -m "fix: remove unreachable fortress_visual_response routing and capability"
```

### Task 5: Wire DMN health into stimmung (passive path)

**Files:**
- Modify: `agents/visual_layer_aggregator/stimmung_methods.py`
- Create: `tests/test_stimmung_dmn_health.py`

- [ ] **Step 1: Write failing test**

```python
"""tests/test_stimmung_dmn_health.py — DMN health feeding into stimmung."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agents.visual_layer_aggregator.stimmung_methods import update_dmn_health


class TestDmnHealthStimmung:
    def test_stale_dmn_degrades_health(self, tmp_path: Path) -> None:
        """DMN not ticking for >30s degrades stimmung health."""
        status_path = tmp_path / "status.json"
        status_path.write_text(
            json.dumps({"timestamp": time.time() - 60, "buffer_entries": 5, "uptime_s": 120})
        )

        collector = MagicMock()
        update_dmn_health(collector, status_path)
        collector.update_health.assert_called_once()
        args = collector.update_health.call_args
        assert args[0] == (0, 1)
        assert args[1]["failed_checks"] == ["dmn_stale"]

    def test_fresh_dmn_no_degradation(self, tmp_path: Path) -> None:
        """Fresh DMN with entries does not degrade health."""
        status_path = tmp_path / "status.json"
        status_path.write_text(
            json.dumps({"timestamp": time.time(), "buffer_entries": 5, "uptime_s": 120})
        )

        collector = MagicMock()
        update_dmn_health(collector, status_path)
        collector.update_health.assert_not_called()

    def test_empty_buffer_after_startup_degrades(self, tmp_path: Path) -> None:
        """DMN running >60s with 0 buffer entries degrades health."""
        status_path = tmp_path / "status.json"
        status_path.write_text(
            json.dumps({"timestamp": time.time(), "buffer_entries": 0, "uptime_s": 120})
        )

        collector = MagicMock()
        update_dmn_health(collector, status_path)
        collector.update_health.assert_called_once()
        args = collector.update_health.call_args
        assert args[1]["failed_checks"] == ["dmn_empty_buffer"]

    def test_empty_buffer_during_startup_ok(self, tmp_path: Path) -> None:
        """DMN running <60s with 0 entries is normal startup — no degradation."""
        status_path = tmp_path / "status.json"
        status_path.write_text(
            json.dumps({"timestamp": time.time(), "buffer_entries": 0, "uptime_s": 30})
        )

        collector = MagicMock()
        update_dmn_health(collector, status_path)
        collector.update_health.assert_not_called()

    def test_missing_file_no_error(self, tmp_path: Path) -> None:
        """Missing status file is not an error (DMN may not be running)."""
        collector = MagicMock()
        update_dmn_health(collector, tmp_path / "nope.json")
        collector.update_health.assert_not_called()

    def test_malformed_json_no_error(self, tmp_path: Path) -> None:
        """Malformed JSON does not crash."""
        status_path = tmp_path / "status.json"
        status_path.write_text("not json")
        collector = MagicMock()
        update_dmn_health(collector, status_path)
        collector.update_health.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_stimmung_dmn_health.py -v`
Expected: FAIL — `ImportError: cannot import name 'update_dmn_health'`

- [ ] **Step 3: Implement DMN health reader**

Add to `agents/visual_layer_aggregator/stimmung_methods.py`, after `update_stimmung_sources` and before `update_biometrics`:

```python
def update_dmn_health(
    collector,
    status_path: Path | None = None,
) -> None:
    """Read DMN status and feed health signal into stimmung.

    Degrades health when:
    - DMN hasn't ticked in >30s (stale)
    - DMN has 0 buffer entries after >60s uptime (empty buffer)
    """
    if status_path is None:
        status_path = Path("/dev/shm/hapax-dmn/status.json")
    try:
        data = json.loads(status_path.read_text(encoding="utf-8"))
        age = time.time() - data.get("timestamp", 0)
        if age > 30:
            collector.update_health(0, 1, failed_checks=["dmn_stale"])
        elif data.get("buffer_entries", 0) == 0 and data.get("uptime_s", 0) > 60:
            collector.update_health(0, 1, failed_checks=["dmn_empty_buffer"])
    except (OSError, json.JSONDecodeError, KeyError):
        pass  # DMN not running — not an error
```

Wire the call inside `update_stimmung_sources`, after block 6 (grounding quality, line 98) and before block 7 (snapshot, line 100):

```python
    # 6b. DMN health
    update_dmn_health(agg._stimmung_collector)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_stimmung_dmn_health.py -v`
Expected: 6 passed

- [ ] **Step 5: Run full stimmung/VLA tests for regression**

Run: `uv run pytest tests/ -k "stimmung or visual_layer" -v --timeout=30`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add agents/visual_layer_aggregator/stimmung_methods.py tests/test_stimmung_dmn_health.py
git commit -m "feat: wire DMN health into stimmung via VLA (passive degradation path)"
```

### Task 6: SystemAwarenessCapability (active path)

**Files:**
- Create: `agents/hapax_daimonion/system_awareness.py`
- Create: `tests/test_system_awareness.py`
- Modify: `agents/hapax_daimonion/init_pipeline.py`

- [ ] **Step 1: Write failing tests**

```python
"""tests/test_system_awareness.py — SystemAwarenessCapability unit tests."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from shared.impingement import Impingement, ImpingementType
from agents.hapax_daimonion.system_awareness import SystemAwarenessCapability


def _make_degradation_imp(
    source: str = "dmn.ollama_degraded",
    strength: float = 0.7,
) -> Impingement:
    return Impingement(
        timestamp=time.time(),
        source=source,
        type=ImpingementType.ABSOLUTE_THRESHOLD,
        strength=strength,
        content={"metric": "ollama_degraded", "consecutive_failures": 5},
    )


class TestSystemAwareness:
    def test_blocks_when_nominal(self, tmp_path: Path) -> None:
        """Capability does not recruit when stimmung is nominal."""
        stimmung_path = tmp_path / "state.json"
        stimmung_path.write_text(json.dumps({"overall_stance": "nominal"}))

        cap = SystemAwarenessCapability(stimmung_path=stimmung_path)
        assert cap.can_resolve(_make_degradation_imp()) == 0.0

    def test_blocks_when_cautious(self, tmp_path: Path) -> None:
        """Capability does not recruit when stimmung is cautious."""
        stimmung_path = tmp_path / "state.json"
        stimmung_path.write_text(json.dumps({"overall_stance": "cautious"}))

        cap = SystemAwarenessCapability(stimmung_path=stimmung_path)
        assert cap.can_resolve(_make_degradation_imp()) == 0.0

    def test_allows_when_degraded(self, tmp_path: Path) -> None:
        """Capability recruits when stimmung is degraded."""
        stimmung_path = tmp_path / "state.json"
        stimmung_path.write_text(json.dumps({"overall_stance": "degraded"}))

        cap = SystemAwarenessCapability(stimmung_path=stimmung_path)
        imp = _make_degradation_imp(strength=0.8)
        assert cap.can_resolve(imp) == 0.8

    def test_allows_when_critical(self, tmp_path: Path) -> None:
        """Capability recruits when stimmung is critical."""
        stimmung_path = tmp_path / "state.json"
        stimmung_path.write_text(json.dumps({"overall_stance": "critical"}))

        cap = SystemAwarenessCapability(stimmung_path=stimmung_path)
        assert cap.can_resolve(_make_degradation_imp()) > 0.0

    def test_cooldown_suppresses(self, tmp_path: Path) -> None:
        """After activation, further calls within cooldown return 0."""
        stimmung_path = tmp_path / "state.json"
        stimmung_path.write_text(json.dumps({"overall_stance": "degraded"}))

        cap = SystemAwarenessCapability(stimmung_path=stimmung_path, cooldown_s=300.0)
        imp = _make_degradation_imp()

        assert cap.can_resolve(imp) > 0.0
        cap.activate(imp, 0.7)

        assert cap.can_resolve(_make_degradation_imp()) == 0.0

    def test_cooldown_expires(self, tmp_path: Path) -> None:
        """After cooldown expires, capability recruits again."""
        stimmung_path = tmp_path / "state.json"
        stimmung_path.write_text(json.dumps({"overall_stance": "degraded"}))

        cap = SystemAwarenessCapability(stimmung_path=stimmung_path, cooldown_s=300.0)
        cap.activate(_make_degradation_imp(), 0.7)

        # Simulate time passing beyond cooldown
        cap._last_activation = time.monotonic() - 301.0
        assert cap.can_resolve(_make_degradation_imp()) > 0.0

    def test_activate_queues_impingement(self, tmp_path: Path) -> None:
        """Activation queues impingement for consumption."""
        stimmung_path = tmp_path / "state.json"
        stimmung_path.write_text(json.dumps({"overall_stance": "degraded"}))

        cap = SystemAwarenessCapability(stimmung_path=stimmung_path)
        imp = _make_degradation_imp()
        cap.activate(imp, 0.7)

        assert cap.has_pending()
        consumed = cap.consume_pending()
        assert consumed is not None
        assert consumed.source == "dmn.ollama_degraded"
        assert not cap.has_pending()

    def test_missing_stimmung_blocks(self, tmp_path: Path) -> None:
        """Missing stimmung file is safe — returns 0."""
        cap = SystemAwarenessCapability(stimmung_path=tmp_path / "nope.json")
        assert cap.can_resolve(_make_degradation_imp()) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_system_awareness.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.hapax_daimonion.system_awareness'`

- [ ] **Step 3: Implement SystemAwarenessCapability**

```python
"""agents/hapax_daimonion/system_awareness.py — Surface DMN degradation to operator.

Recruited by the affordance pipeline when DMN health signals (sensor
starvation, Ollama failure, resolver degradation) reach the impingement
cascade. Gated on stimmung stance — only activates when the system is
genuinely degraded, not on transient blips.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from agents._impingement import Impingement

log = logging.getLogger("voice.system_awareness")

SYSTEM_AWARENESS_DESCRIPTION = (
    "Surface system health degradation to operator awareness. "
    "Recruitable when infrastructure, inference, or sensor subsystems "
    "are failing and stimmung stance is DEGRADED or CRITICAL."
)

_STIMMUNG_GATE = {"degraded", "critical"}
_DEFAULT_STIMMUNG_PATH = Path("/dev/shm/hapax-stimmung/state.json")


class SystemAwarenessCapability:
    """Surfaces DMN degradation signals to operator via voice daemon."""

    def __init__(
        self,
        stimmung_path: Path = _DEFAULT_STIMMUNG_PATH,
        cooldown_s: float = 300.0,
    ) -> None:
        self._stimmung_path = stimmung_path
        self._cooldown_s = cooldown_s
        self._last_activation: float = 0.0
        self._pending: list[Impingement] = []

    def can_resolve(self, impingement: Impingement) -> float:
        """Score: impingement.strength if gate passes, 0.0 otherwise."""
        # Cooldown gate
        if time.monotonic() - self._last_activation < self._cooldown_s:
            return 0.0

        # Stimmung gate — read stance from /dev/shm
        try:
            data = json.loads(self._stimmung_path.read_text(encoding="utf-8"))
            stance = data.get("overall_stance", "nominal")
        except (OSError, json.JSONDecodeError):
            return 0.0

        if stance not in _STIMMUNG_GATE:
            return 0.0

        return impingement.strength

    def activate(self, impingement: Impingement, level: float) -> None:
        """Queue awareness signal for voice pipeline consumption."""
        self._last_activation = time.monotonic()
        self._pending.append(impingement)
        log.info(
            "System awareness recruited: %s (strength=%.2f, level=%.2f)",
            impingement.content.get("metric", impingement.source),
            impingement.strength,
            level,
        )

    def has_pending(self) -> bool:
        return len(self._pending) > 0

    def consume_pending(self) -> Impingement | None:
        if self._pending:
            return self._pending.pop(0)
        return None
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_system_awareness.py -v`
Expected: 8 passed

- [ ] **Step 5: Register capability in Daimonion pipeline**

In `agents/hapax_daimonion/init_pipeline.py`, after the vocal chain block (after line 142), add:

```python
    # System awareness: surface DMN degradation to operator
    from agents.hapax_daimonion.system_awareness import (
        SYSTEM_AWARENESS_DESCRIPTION,
        SystemAwarenessCapability,
    )

    daemon._system_awareness = SystemAwarenessCapability()
    daemon._affordance_pipeline.index_capability(
        CapabilityRecord(
            name="system_awareness",
            description=SYSTEM_AWARENESS_DESCRIPTION,
            daemon="hapax_daimonion",
        )
    )
    daemon._affordance_pipeline.register_interrupt(
        "system_critical", "system_awareness", "hapax_daimonion"
    )
```

Update the final log line to reflect the new capability:

```python
    log.info("Pipeline dependencies precomputed (affordance pipeline: speech + 9 vocal chain dims + system_awareness)")
```

- [ ] **Step 6: Run full daimonion test suite**

Run: `uv run pytest tests/ -k "daimonion or vocal_chain or system_awareness" -v --timeout=30`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add agents/hapax_daimonion/system_awareness.py agents/hapax_daimonion/init_pipeline.py tests/test_system_awareness.py
git commit -m "feat: system_awareness capability — active DMN degradation escalation via voice"
```

---

## Stage 3: Verification + Follow-on

### Task 7: Lint, format, full test suite

**Files:** None (verification only)

- [ ] **Step 1: Lint all changed files**

Run: `uv run ruff check shared/impingement_consumer.py agents/hapax_daimonion/system_awareness.py agents/visual_layer_aggregator/stimmung_methods.py agents/dmn/__main__.py agents/reverie/actuation.py agents/fortress/__main__.py agents/hapax_daimonion/run_loops_aux.py agents/hapax_daimonion/init_pipeline.py`
Expected: No errors

- [ ] **Step 2: Format**

Run: `uv run ruff format shared/impingement_consumer.py agents/hapax_daimonion/system_awareness.py agents/visual_layer_aggregator/stimmung_methods.py`
Expected: No changes or auto-fixed

- [ ] **Step 3: Full test suite**

Run: `uv run pytest tests/ -v --timeout=60 -x`
Expected: All pass. If any fail, fix before proceeding.

- [ ] **Step 4: Fix any issues and commit**

If lint or tests required fixes:
```bash
git add -u && git commit -m "fix: lint and test fixes for DMN integration boundary closure"
```

### Task 8: Update relay context and memory

**Files:**
- Create: relay context artifact `context/dmn-integration-boundary.md`
- Update: relay status `alpha.yaml`
- Update: project memory

- [ ] **Step 1: Write relay context artifact for beta**

Write context artifact documenting:
- Shared ImpingementConsumer created — Fortress and Daimonion migrated
- DMN health wired into stimmung (passive path via VLA)
- system_awareness capability registered in Daimonion (active path, gated on stance)
- fortress_visual_response dead code deleted
- Phase 4/5 alignment: Reverie routing in DMN is cleaner, ImpingementConsumer ready for mixer adoption

- [ ] **Step 2: Update alpha relay status**

Update alpha.yaml with completed work and note that Reverie independent daemon (C) is queued for next brainstorm cycle.

- [ ] **Step 3: Update DMN project memory**

Update the DMN architecture memory with integration boundary closure work completed.
