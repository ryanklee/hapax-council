# Phase 2: Shared Context Enrichment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a shared `EnrichmentContext` assembled from canonical sources so both daimonion and Reverie consume identical context at the same moment.

**Architecture:** New `shared/context.py` defines `EnrichmentContext` (frozen dataclass) and `ContextAssembler` (gathers from stimmung, goals, health, nudges, DMN, imagination, perception). Daimonion's existing `_*_fn` callables delegate to the assembler. Reverie reads from the same `EnrichmentContext`. Assembly uses snapshot isolation (all sources read once) with 2s TTL cache.

**Tech Stack:** Python 3.12, dataclasses, pathlib for `/dev/shm` reads

**Spec:** `docs/superpowers/specs/2026-03-29-capability-parity-design.md` (Phase 2)

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `shared/context.py` | EnrichmentContext, ContextAssembler |
| `tests/test_context_enrichment.py` | Assembly, caching, snapshot isolation |

### Modified Files

| File | Change |
|------|--------|
| `agents/hapax_daimonion/context_enrichment.py` | render_* functions delegate to ContextAssembler |
| `agents/hapax_daimonion/__main__.py` | Create ContextAssembler, pass to pipeline |

---

## Task 1: EnrichmentContext + ContextAssembler

**Files:**
- Create: `shared/context.py`
- Test: `tests/test_context_enrichment.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_context_enrichment.py
"""Tests for shared context enrichment."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from shared.context import ContextAssembler, EnrichmentContext


class TestEnrichmentContext(unittest.TestCase):
    def test_frozen(self):
        ctx = EnrichmentContext(timestamp=time.time())
        with self.assertRaises(AttributeError):
            ctx.timestamp = 0.0

    def test_defaults(self):
        ctx = EnrichmentContext(timestamp=1.0)
        assert ctx.stimmung_stance == "nominal"
        assert ctx.active_goals == []
        assert ctx.health_summary == {}
        assert ctx.pending_nudges == []
        assert ctx.dmn_observations == []
        assert ctx.imagination_fragments == []
        assert ctx.perception_snapshot == {}


class TestContextAssembler(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._stimmung_path = Path(self._tmpdir) / "stimmung" / "state.json"
        self._stimmung_path.parent.mkdir(parents=True, exist_ok=True)
        self._dmn_path = Path(self._tmpdir) / "dmn" / "buffer.txt"
        self._dmn_path.parent.mkdir(parents=True, exist_ok=True)
        self._imagination_path = Path(self._tmpdir) / "imagination" / "current.json"
        self._imagination_path.parent.mkdir(parents=True, exist_ok=True)

    def _write_stimmung(self, stance="nominal"):
        self._stimmung_path.write_text(json.dumps({
            "overall_stance": stance,
            "health": {"value": 0.1, "trend": "stable", "freshness_s": 0.0},
            "timestamp": time.time(),
        }))

    def _make_assembler(self, **overrides):
        defaults = {
            "stimmung_path": self._stimmung_path,
            "dmn_buffer_path": self._dmn_path,
            "imagination_path": self._imagination_path,
            "goals_fn": lambda: [],
            "health_fn": lambda: {},
            "nudges_fn": lambda: [],
            "perception_fn": lambda: {},
        }
        defaults.update(overrides)
        return ContextAssembler(**defaults)

    def test_assemble_returns_enrichment_context(self):
        self._write_stimmung("cautious")
        asm = self._make_assembler()
        ctx = asm.assemble()
        assert isinstance(ctx, EnrichmentContext)
        assert ctx.stimmung_stance == "cautious"

    def test_assemble_reads_goals(self):
        self._write_stimmung()
        asm = self._make_assembler(goals_fn=lambda: [{"title": "Ship feature"}])
        ctx = asm.assemble()
        assert len(ctx.active_goals) == 1
        assert ctx.active_goals[0]["title"] == "Ship feature"

    def test_assemble_reads_dmn_buffer(self):
        self._write_stimmung()
        self._dmn_path.write_text("Operator is typing actively.")
        asm = self._make_assembler()
        ctx = asm.assemble()
        assert "typing" in ctx.dmn_observations[0]

    def test_assemble_reads_imagination(self):
        self._write_stimmung()
        self._imagination_path.write_text(json.dumps({
            "narrative": "A field of stars",
            "salience": 0.7,
        }))
        asm = self._make_assembler()
        ctx = asm.assemble()
        assert len(ctx.imagination_fragments) == 1

    def test_assemble_caches_with_ttl(self):
        self._write_stimmung("nominal")
        asm = self._make_assembler()
        ctx1 = asm.assemble()
        # Modify stimmung
        self._write_stimmung("degraded")
        ctx2 = asm.assemble()
        # Should return cached (same object)
        assert ctx2 is ctx1
        assert ctx2.stimmung_stance == "nominal"

    def test_cache_expires(self):
        self._write_stimmung("nominal")
        asm = self._make_assembler()
        asm._cache_ttl = 0.0  # expire immediately
        ctx1 = asm.assemble()
        self._write_stimmung("degraded")
        ctx2 = asm.assemble()
        assert ctx2 is not ctx1
        assert ctx2.stimmung_stance == "degraded"

    def test_missing_stimmung_defaults_nominal(self):
        # Don't write stimmung file
        asm = self._make_assembler()
        ctx = asm.assemble()
        assert ctx.stimmung_stance == "nominal"

    def test_missing_dmn_returns_empty(self):
        self._write_stimmung()
        # Don't write DMN buffer
        asm = self._make_assembler()
        ctx = asm.assemble()
        assert ctx.dmn_observations == []

    def test_callable_failure_returns_empty(self):
        self._write_stimmung()

        def bad_goals():
            raise RuntimeError("broken")

        asm = self._make_assembler(goals_fn=bad_goals)
        ctx = asm.assemble()
        assert ctx.active_goals == []

    def test_perception_snapshot(self):
        self._write_stimmung()
        asm = self._make_assembler(
            perception_fn=lambda: {"desk_activity": "typing", "flow_score": 0.8}
        )
        ctx = asm.assemble()
        assert ctx.perception_snapshot["desk_activity"] == "typing"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_context_enrichment.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shared.context'`

- [ ] **Step 3: Implement shared/context.py**

```python
# shared/context.py
"""Shared context enrichment for all Hapax subsystems.

EnrichmentContext is assembled from canonical sources and consumed by both
daimonion (voice) and Reverie (visual). Both systems see identical context
at the same moment.

Phase 2 of capability parity (queue #018).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_STIMMUNG = Path("/dev/shm/hapax-stimmung/state.json")
_DEFAULT_DMN_BUFFER = Path("/dev/shm/hapax-dmn/buffer.txt")
_DEFAULT_IMAGINATION = Path("/dev/shm/hapax-imagination/current.json")


@dataclass(frozen=True)
class EnrichmentContext:
    """Snapshot of all context sources, consumed by voice and visual systems."""

    timestamp: float
    stimmung_stance: str = "nominal"
    stimmung_raw: dict = field(default_factory=dict)
    active_goals: list[dict] = field(default_factory=list)
    health_summary: dict = field(default_factory=dict)
    pending_nudges: list[dict] = field(default_factory=list)
    dmn_observations: list[str] = field(default_factory=list)
    imagination_fragments: list[dict] = field(default_factory=list)
    perception_snapshot: dict = field(default_factory=dict)


class ContextAssembler:
    """Gathers context from canonical sources with snapshot isolation and caching."""

    def __init__(
        self,
        stimmung_path: Path = _DEFAULT_STIMMUNG,
        dmn_buffer_path: Path = _DEFAULT_DMN_BUFFER,
        imagination_path: Path = _DEFAULT_IMAGINATION,
        goals_fn=None,
        health_fn=None,
        nudges_fn=None,
        perception_fn=None,
    ) -> None:
        self._stimmung_path = stimmung_path
        self._dmn_buffer_path = dmn_buffer_path
        self._imagination_path = imagination_path
        self._goals_fn = goals_fn or (lambda: [])
        self._health_fn = health_fn or (lambda: {})
        self._nudges_fn = nudges_fn or (lambda: [])
        self._perception_fn = perception_fn or (lambda: {})
        self._cache: EnrichmentContext | None = None
        self._cache_time: float = 0.0
        self._cache_ttl: float = 2.0

    def assemble(self) -> EnrichmentContext:
        """Assemble context from all sources. Cached for _cache_ttl seconds."""
        now = time.monotonic()
        if self._cache is not None and (now - self._cache_time) < self._cache_ttl:
            return self._cache

        ctx = EnrichmentContext(
            timestamp=time.time(),
            stimmung_stance=self._read_stimmung_stance(),
            stimmung_raw=self._read_stimmung_raw(),
            active_goals=self._safe_call(self._goals_fn, []),
            health_summary=self._safe_call(self._health_fn, {}),
            pending_nudges=self._safe_call(self._nudges_fn, []),
            dmn_observations=self._read_dmn_buffer(),
            imagination_fragments=self._read_imagination(),
            perception_snapshot=self._safe_call(self._perception_fn, {}),
        )
        self._cache = ctx
        self._cache_time = now
        return ctx

    def invalidate(self) -> None:
        """Force next assemble() to re-read all sources."""
        self._cache = None

    def _read_stimmung_stance(self) -> str:
        try:
            raw = json.loads(self._stimmung_path.read_text(encoding="utf-8"))
            return raw.get("overall_stance", "nominal")
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return "nominal"

    def _read_stimmung_raw(self) -> dict:
        try:
            return json.loads(self._stimmung_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _read_dmn_buffer(self) -> list[str]:
        try:
            text = self._dmn_buffer_path.read_text(encoding="utf-8").strip()
            return [text] if text else []
        except (FileNotFoundError, OSError):
            return []

    def _read_imagination(self) -> list[dict]:
        try:
            raw = json.loads(self._imagination_path.read_text(encoding="utf-8"))
            return [raw] if raw else []
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []

    @staticmethod
    def _safe_call(fn, default):
        try:
            return fn()
        except Exception:
            log.debug("Context source failed (non-fatal)", exc_info=True)
            return default
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_context_enrichment.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add shared/context.py tests/test_context_enrichment.py
git commit -m "feat: shared EnrichmentContext + ContextAssembler"
```

---

## Task 2: Wire ContextAssembler into Daimonion

**Files:**
- Modify: `agents/hapax_daimonion/context_enrichment.py`
- Modify: `agents/hapax_daimonion/__main__.py`

- [ ] **Step 1: Add assembler-backed render functions to context_enrichment.py**

Add at the bottom of `agents/hapax_daimonion/context_enrichment.py`:

```python
# ── Shared assembler integration ─────────────────────────────────────────

_assembler: ContextAssembler | None = None


def get_assembler() -> ContextAssembler:
    """Return the shared ContextAssembler, creating it lazily if needed."""
    global _assembler
    if _assembler is None:
        from shared.context import ContextAssembler

        _assembler = ContextAssembler(
            goals_fn=_collect_goals,
            health_fn=_collect_health,
            nudges_fn=_collect_nudges,
        )
    return _assembler


def set_assembler(asm: ContextAssembler) -> None:
    """Set the shared ContextAssembler (for dependency injection in daemon)."""
    global _assembler
    _assembler = asm


def _collect_goals() -> list[dict]:
    """Collect goals as dicts for EnrichmentContext."""
    try:
        from logos.data.goals import collect_goals

        goals = collect_goals()
        return [{"title": g.title, "status": g.status} for g in goals if g.status != "done"]
    except Exception:
        return []


def _collect_health() -> dict:
    """Collect health summary for EnrichmentContext."""
    try:
        from shared.config import PROFILES_DIR

        health_file = PROFILES_DIR / "health-history.jsonl"
        if not health_file.exists():
            return {}
        import json

        lines = health_file.read_text().strip().split("\n")
        if not lines:
            return {}
        latest = json.loads(lines[-1])
        return latest
    except Exception:
        return {}


def _collect_nudges() -> list[dict]:
    """Collect nudges as dicts for EnrichmentContext."""
    try:
        from logos.data.nudges import collect_nudges

        nudges = collect_nudges()
        return [{"title": n.title, "priority_label": n.priority_label} for n in nudges[:3]]
    except Exception:
        return []
```

Add import at top: `from shared.context import ContextAssembler`

- [ ] **Step 2: Wire assembler into daemon startup**

In `agents/hapax_daimonion/__main__.py`, in `_precompute_pipeline_deps()` (around line 955-966), after the existing render_* assignments, add:

```python
        # Shared context assembler
        from shared.context import ContextAssembler
        from agents.hapax_daimonion.context_enrichment import (
            set_assembler,
            _collect_goals,
            _collect_health,
            _collect_nudges,
        )

        self._context_assembler = ContextAssembler(
            goals_fn=_collect_goals,
            health_fn=_collect_health,
            nudges_fn=_collect_nudges,
            perception_fn=lambda: self.perception.latest if hasattr(self, "perception") and self.perception else {},
        )
        set_assembler(self._context_assembler)
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_context_enrichment.py tests/hapax_daimonion/ -q --ignore=tests/hapax_daimonion/test_tracing.py --ignore=tests/hapax_daimonion/test_tracing_flush_timeout.py --ignore=tests/hapax_daimonion/test_tracing_robustness.py -x`
Expected: No new failures

- [ ] **Step 4: Commit**

```bash
git add agents/hapax_daimonion/context_enrichment.py agents/hapax_daimonion/__main__.py
git commit -m "feat: wire ContextAssembler into daimonion daemon"
```

---

## Task 3: Full Test Suite + PR

- [ ] **Step 1: Run full tests**

Run: `uv run pytest tests/test_context_enrichment.py tests/test_capability_protocol.py -v`
Expected: All pass

- [ ] **Step 2: Lint**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: Clean

- [ ] **Step 3: Push and create PR**

```bash
git push -u origin HEAD
gh pr create --title "feat: shared context enrichment — both systems see identical context" --body "..."
```

- [ ] **Step 4: Monitor CI, merge when green**
