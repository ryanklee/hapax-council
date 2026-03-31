# Real-Time Flow Events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an in-process event bus that captures agent-to-agent and agent-to-external-service communication, streams it to the frontend via SSE + Tauri bridge, and renders transient directional dots on flow graph edges.

**Architecture:** Python EventBus (asyncio, in-process ring buffer) receives events from 6 sources (SHM writes, engine rules/actions, LLM calls, Qdrant ops, Pi POSTs). SSE endpoint streams to Tauri Rust bridge, which re-emits as Tauri events. React FlowPage listens and spawns one-shot SVG dot animations along edge bezier paths.

**Tech Stack:** Python 3.12+ / FastAPI / asyncio / Rust / Tauri 2 / React / @xyflow/react / SVG animateMotion

**Spec:** `docs/superpowers/specs/2026-03-31-realtime-flow-events-design.md`

---

### Task 1: EventBus core + FlowEvent dataclass

**Files:**
- Create: `logos/event_bus.py`
- Test: `tests/test_event_bus.py`

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_event_bus.py"""
import asyncio
from logos.event_bus import EventBus, FlowEvent


class TestEventBus:
    def test_emit_and_recent(self):
        bus = EventBus(maxlen=10)
        ev = FlowEvent(
            kind="shm.write",
            source="stimmung_sync",
            target="apperception",
            label="state.json",
        )
        bus.emit(ev)
        recent = bus.recent()
        assert len(recent) == 1
        assert recent[0].source == "stimmung_sync"
        assert recent[0].ts > 0

    def test_ring_buffer_overflow(self):
        bus = EventBus(maxlen=3)
        for i in range(5):
            bus.emit(FlowEvent(kind="shm.write", source=f"a{i}", target="b", label=""))
        recent = bus.recent()
        assert len(recent) == 3
        assert recent[0].source == "a2"  # oldest surviving

    def test_recent_since_filters(self):
        import time
        bus = EventBus(maxlen=100)
        bus.emit(FlowEvent(kind="shm.write", source="old", target="b", label=""))
        cutoff = time.time() + 0.01
        time.sleep(0.02)
        bus.emit(FlowEvent(kind="shm.write", source="new", target="b", label=""))
        filtered = bus.recent(since=cutoff)
        assert len(filtered) == 1
        assert filtered[0].source == "new"

    def test_subscribe_receives_events(self):
        bus = EventBus(maxlen=10)

        async def run():
            received = []
            sub = bus.subscribe()

            async def collect():
                async for ev in sub:
                    received.append(ev)
                    if len(received) >= 2:
                        break

            task = asyncio.create_task(collect())
            await asyncio.sleep(0.01)
            bus.emit(FlowEvent(kind="engine.rule", source="a", target="b", label="r1"))
            bus.emit(FlowEvent(kind="engine.action", source="b", target="c", label="a1"))
            await asyncio.wait_for(task, timeout=1.0)
            assert len(received) == 2
            assert received[0].kind == "engine.rule"
            assert received[1].kind == "engine.action"

        asyncio.run(run())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_event_bus.py -v`
Expected: FAIL with ImportError (logos.event_bus does not exist)

- [ ] **Step 3: Write the implementation**

```python
"""logos/event_bus.py — In-process async event bus for flow visualization."""
from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field

__all__ = ["EventBus", "FlowEvent"]


@dataclass
class FlowEvent:
    """A single observable system event for flow visualization."""

    kind: str  # shm.write | engine.rule | engine.action | llm.call | qdrant.op | pi.detection
    source: str  # source agent/node ID
    target: str  # target agent/node ID
    label: str  # human-readable description
    duration_ms: float | None = None
    ts: float = field(default_factory=time.time)


class EventBus:
    """Bounded ring buffer with async fan-out to SSE subscribers."""

    def __init__(self, maxlen: int = 500) -> None:
        self._ring: deque[FlowEvent] = deque(maxlen=maxlen)
        self._subscribers: list[asyncio.Queue[FlowEvent]] = []

    def emit(self, event: FlowEvent) -> None:
        """Non-blocking emit. Drops subscriber messages if queue full."""
        self._ring.append(event)
        dead: list[int] = []
        for i, q in enumerate(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # drop — subscriber is slow
        # Clean up dead subscribers (removed via unsubscribe)
        # No-op here; cleanup happens in subscribe's finally block

    def recent(self, since: float | None = None) -> list[FlowEvent]:
        """Return recent events, optionally filtered by timestamp."""
        if since is None:
            return list(self._ring)
        return [e for e in self._ring if e.ts >= since]

    def subscribe(self) -> _Subscription:
        """Create an async iterator that yields events as they arrive."""
        q: asyncio.Queue[FlowEvent] = asyncio.Queue(maxsize=50)
        self._subscribers.append(q)
        return _Subscription(q, self._subscribers)


class _Subscription:
    """Async iterator over event bus. Cleans up on exit."""

    def __init__(
        self,
        queue: asyncio.Queue[FlowEvent],
        subscribers: list[asyncio.Queue[FlowEvent]],
    ) -> None:
        self._queue = queue
        self._subscribers = subscribers

    def __aiter__(self):
        return self

    async def __anext__(self) -> FlowEvent:
        try:
            return await self._queue.get()
        except asyncio.CancelledError:
            self._cleanup()
            raise

    def _cleanup(self) -> None:
        try:
            self._subscribers.remove(self._queue)
        except ValueError:
            pass

    async def aclose(self) -> None:
        self._cleanup()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_event_bus.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add logos/event_bus.py tests/test_event_bus.py
git commit -m "feat: add EventBus core with ring buffer and async subscriptions"
```

---

### Task 2: SSE endpoint + wire EventBus into app startup

**Files:**
- Create: `logos/api/routes/events.py`
- Modify: `logos/api/app.py:27-92` (lifespan — add EventBus creation)
- Modify: `logos/api/app.py:100+` (router registration)
- Test: `tests/test_event_bus.py` (add SSE endpoint test)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_bus.py`:

```python
import httpx
from starlette.testclient import TestClient

from logos.event_bus import EventBus, FlowEvent


class TestSSEEndpoint:
    def test_sse_streams_events(self):
        """SSE endpoint yields events as server-sent events."""
        from fastapi import FastAPI
        from logos.api.routes.events import router, get_event_bus

        bus = EventBus(maxlen=10)
        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")
        test_app.dependency_overrides[get_event_bus] = lambda: bus

        with TestClient(test_app) as client:
            # Emit before connecting — should be in initial burst
            bus.emit(FlowEvent(kind="shm.write", source="a", target="b", label="test"))

            with client.stream("GET", "/api/events/stream") as resp:
                assert resp.status_code == 200
                # Read the first SSE line (data: ...)
                for line in resp.iter_lines():
                    if line.startswith("data:"):
                        import json
                        data = json.loads(line[5:].strip())
                        assert data["kind"] == "shm.write"
                        assert data["source"] == "a"
                        break
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_event_bus.py::TestSSEEndpoint -v`
Expected: FAIL with ImportError (logos.api.routes.events does not exist)

- [ ] **Step 3: Create the SSE endpoint**

```python
"""logos/api/routes/events.py — SSE stream of real-time flow events."""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import AsyncIterator

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from logos.event_bus import EventBus, FlowEvent

router = APIRouter(tags=["events"])

# Dependency — overridden in tests, set from app.state in production
_bus: EventBus | None = None


def set_event_bus(bus: EventBus) -> None:
    global _bus
    _bus = bus


def get_event_bus() -> EventBus:
    if _bus is None:
        raise RuntimeError("EventBus not initialized")
    return _bus


async def _event_generator(bus: EventBus, request: Request) -> AsyncIterator[str]:
    """Yield FlowEvents as JSON strings for SSE."""
    sub = bus.subscribe()
    try:
        async for event in sub:
            if await request.is_disconnected():
                break
            yield json.dumps(asdict(event))
    finally:
        await sub.aclose()


@router.get("/events/stream")
async def event_stream(request: Request) -> EventSourceResponse:
    """SSE endpoint streaming real-time flow events."""
    bus = get_event_bus()
    return EventSourceResponse(_event_generator(bus, request))
```

- [ ] **Step 4: Wire EventBus into app startup**

In `logos/api/app.py`, add to the lifespan function after the engine startup block (after line 86):

```python
    # Start event bus
    from logos.event_bus import EventBus
    from logos.api.routes.events import set_event_bus

    event_bus = EventBus(maxlen=500)
    app.state.event_bus = event_bus
    set_event_bus(event_bus)
```

Register the router after the existing router registrations (near line 100+):

```python
from logos.api.routes.events import router as events_router
app.include_router(events_router, prefix="/api")
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_event_bus.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add logos/api/routes/events.py logos/api/app.py tests/test_event_bus.py
git commit -m "feat: add SSE endpoint for flow events, wire EventBus into app startup"
```

---

### Task 3: SHM write event emission in FlowObserver

**Files:**
- Modify: `logos/api/flow_observer.py:36-61` (scan method)
- Test: `tests/test_event_bus.py` (add SHM write test)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_bus.py`:

```python
class TestSHMWriteEvents:
    def test_observer_emits_on_mtime_change(self, tmp_path):
        """FlowObserver emits shm.write events when file mtimes change."""
        import time
        from logos.event_bus import EventBus
        from logos.api.flow_observer import FlowObserver

        bus = EventBus(maxlen=100)

        # Create fake SHM directory structure
        shm_dir = tmp_path / "hapax-stimmung"
        shm_dir.mkdir()
        state_file = shm_dir / "state.json"
        state_file.write_text("{}")

        observer = FlowObserver(
            shm_root=tmp_path,
            event_bus=bus,
        )
        # Register a reader for this path
        observer.register_reader("apperception", str(shm_dir / "state.json"))

        # First scan — establishes baseline mtimes
        observer.scan()
        initial_events = bus.recent()

        # Touch the file to change mtime
        time.sleep(0.05)
        state_file.write_text('{"updated": true}')

        # Second scan — should detect mtime change and emit
        observer.scan()
        new_events = bus.recent(since=time.time() - 1)
        shm_events = [e for e in new_events if e.kind == "shm.write"]
        assert len(shm_events) >= 1
        assert shm_events[0].source == "stimmung"
        assert shm_events[0].target == "apperception"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_event_bus.py::TestSHMWriteEvents -v`
Expected: FAIL (FlowObserver doesn't accept event_bus parameter)

- [ ] **Step 3: Modify FlowObserver**

In `logos/api/flow_observer.py`, update `__init__` to accept an optional event bus:

```python
from __future__ import annotations
from logos.event_bus import EventBus, FlowEvent

class FlowObserver:
    def __init__(
        self,
        shm_root: Path | None = None,
        decay_seconds: float = 60.0,
        event_bus: EventBus | None = None,
    ) -> None:
        self._shm_root = shm_root or Path("/dev/shm")
        self._decay_seconds = decay_seconds
        self._event_bus = event_bus
        self._writers: dict[str, dict[str, float]] = {}
        self._readers: dict[str, str] = {}
        self._observed: dict[tuple[str, str], float] = {}
        self._prev_mtimes: dict[str, float] = {}  # NEW: track previous mtimes for change detection
```

In the `scan()` method, after reading each file's mtime, compare with previous and emit if changed:

```python
def scan(self) -> None:
    now = time.time()
    # ... existing directory scanning logic ...
    for shm_dir in self._shm_root.iterdir():
        if not shm_dir.is_dir() or not shm_dir.name.startswith("hapax-"):
            continue
        writer_name = shm_dir.name.removeprefix("hapax-")
        current_mtimes: dict[str, float] = {}
        for f in shm_dir.iterdir():
            if not f.is_file():
                continue
            try:
                mtime = f.stat().st_mtime
            except OSError:
                continue
            current_mtimes[str(f)] = mtime

            # Emit event if mtime changed since last scan
            prev = self._prev_mtimes.get(str(f))
            if self._event_bus and prev is not None and mtime != prev:
                # Find all readers of this writer's files
                for reader_id, reader_path in self._readers.items():
                    if reader_path.startswith(str(shm_dir)):
                        self._event_bus.emit(FlowEvent(
                            kind="shm.write",
                            source=writer_name,
                            target=reader_id,
                            label=f.name,
                        ))

            # ... existing writer/reader correlation logic ...

        # Update previous mtimes
        for path, mt in current_mtimes.items():
            self._prev_mtimes[path] = mt
    # ... existing edge decay logic ...
```

- [ ] **Step 4: Wire event bus into FlowObserver creation**

In `logos/api/routes/flow.py`, where FlowObserver is instantiated, pass the event bus:

Find the FlowObserver instantiation and add `event_bus=request.app.state.event_bus` (or however the observer is created — it may be a module-level singleton that needs the bus injected after app startup).

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_event_bus.py -v`
Expected: All passed

- [ ] **Step 6: Commit**

```bash
git add logos/api/flow_observer.py logos/api/routes/flow.py tests/test_event_bus.py
git commit -m "feat: emit shm.write events from FlowObserver on mtime changes"
```

---

### Task 4: Engine rule and action event emission

**Files:**
- Modify: `logos/engine/__init__.py:537-549` (after action execution, where history is recorded)
- Test: `tests/test_event_bus.py` (add engine event test)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_bus.py`:

```python
class TestEngineEvents:
    def test_engine_emits_action_events(self):
        """Engine emits engine.action events after executing actions."""
        import asyncio
        from logos.event_bus import EventBus

        bus = EventBus(maxlen=100)

        async def run():
            from logos.engine import ReactiveEngine

            engine = ReactiveEngine(event_bus=bus)
            # We can't easily test full engine dispatch without rules,
            # so test the emit helper directly
            engine._emit_action_event(
                event_path="/dev/shm/hapax-stimmung/state.json",
                action_name="update_apperception",
                duration_ms=42.0,
            )
            events = bus.recent()
            assert len(events) == 1
            assert events[0].kind == "engine.action"
            assert events[0].source == "stimmung"
            assert events[0].label == "update_apperception"

        asyncio.run(run())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_event_bus.py::TestEngineEvents -v`
Expected: FAIL (ReactiveEngine doesn't accept event_bus parameter)

- [ ] **Step 3: Add event bus to ReactiveEngine**

In `logos/engine/__init__.py`, update `__init__` to accept an optional event bus:

```python
from logos.event_bus import EventBus, FlowEvent

class ReactiveEngine:
    def __init__(self, ..., event_bus: EventBus | None = None) -> None:
        # ... existing init ...
        self._event_bus = event_bus
```

Add a helper method to extract agent ID from a file path:

```python
def _agent_from_path(self, path: str) -> str:
    """Extract agent name from SHM path like /dev/shm/hapax-stimmung/state.json."""
    from pathlib import PurePosixPath
    parts = PurePosixPath(path).parts
    for p in parts:
        if p.startswith("hapax-"):
            return p.removeprefix("hapax-")
    return "unknown"

def _emit_action_event(
    self, event_path: str, action_name: str, duration_ms: float | None = None,
) -> None:
    """Emit an engine.action event if event bus is available."""
    if not self._event_bus:
        return
    self._event_bus.emit(FlowEvent(
        kind="engine.action",
        source=self._agent_from_path(event_path),
        target=action_name,
        label=action_name,
        duration_ms=duration_ms,
    ))
```

In `_handle_change`, after the action execution block (after line 527), emit events for each completed action:

```python
            # After: await self._executor.execute(plan)
            self._actions_executed += len(plan.results)
            self._error_count += len(plan.errors)

            # Emit flow events for executed actions
            if self._event_bus:
                for action_name in plan.results:
                    self._emit_action_event(
                        event_path=str(event.path),
                        action_name=action_name,
                    )
```

- [ ] **Step 4: Wire event bus when creating engine in app.py**

In `logos/api/app.py`, pass the event bus to the engine (after the event bus is created, modify the engine creation):

```python
    engine = ReactiveEngine(event_bus=event_bus)
```

Note: the event bus creation must be moved BEFORE the engine creation in the lifespan function.

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_event_bus.py -v`
Expected: All passed

- [ ] **Step 6: Commit**

```bash
git add logos/engine/__init__.py logos/api/app.py tests/test_event_bus.py
git commit -m "feat: emit engine.action events from ReactiveEngine after execution"
```

---

### Task 5: Pi fleet event emission

**Files:**
- Modify: `logos/api/routes/pi.py:27-53` (IR detection POST handler)
- Test: `tests/test_event_bus.py` (add Pi event test)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_bus.py`:

```python
class TestPiEvents:
    def test_ir_detection_emits_event(self):
        """Pi IR detection POST emits pi.detection event."""
        from fastapi import FastAPI, Request
        from starlette.testclient import TestClient
        from logos.event_bus import EventBus
        from logos.api.routes.pi import router

        bus = EventBus(maxlen=10)
        test_app = FastAPI()
        test_app.include_router(router, prefix="/api/pi")

        @test_app.on_event("startup")
        async def setup():
            test_app.state.event_bus = bus

        with TestClient(test_app) as client:
            resp = client.post("/api/pi/desk/ir", json={
                "timestamp": 1234567890.0,
                "role": "desk",
                "detections": [],
                "frame_width": 640,
                "frame_height": 480,
            })
            # May get 200 or 422 depending on full schema — either way check bus
            events = bus.recent()
            pi_events = [e for e in events if e.kind == "pi.detection"]
            if resp.status_code == 200:
                assert len(pi_events) == 1
                assert pi_events[0].source == "pi-desk"
                assert pi_events[0].target == "perception"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_event_bus.py::TestPiEvents -v`
Expected: FAIL (pi.py doesn't emit events)

- [ ] **Step 3: Add event emission to Pi IR handler**

In `logos/api/routes/pi.py`, in the `receive_ir_detection` function, after successful processing, add:

```python
    # Emit flow event
    bus: EventBus | None = getattr(request.app.state, "event_bus", None)
    if bus:
        from logos.event_bus import FlowEvent
        bus.emit(FlowEvent(
            kind="pi.detection",
            source=f"pi-{role}",
            target="perception",
            label=f"ir/{role}",
        ))
```

Note: the handler needs `request: Request` in its signature if not already present, to access `request.app.state`.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_event_bus.py -v`
Expected: All passed

- [ ] **Step 5: Commit**

```bash
git add logos/api/routes/pi.py tests/test_event_bus.py
git commit -m "feat: emit pi.detection events from Pi fleet POST handlers"
```

---

### Task 6: Qdrant operation event emission

**Files:**
- Modify: `shared/config.py:179-182` (wrap get_qdrant)
- Test: `tests/test_event_bus.py` (add Qdrant event test)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_bus.py`:

```python
class TestQdrantEvents:
    def test_instrumented_qdrant_emits_on_search(self):
        """Instrumented Qdrant client emits qdrant.op events on search."""
        from unittest.mock import MagicMock, AsyncMock
        from logos.event_bus import EventBus
        from shared.config import InstrumentedQdrantClient

        bus = EventBus(maxlen=10)
        mock_client = MagicMock()
        mock_client.search = MagicMock(return_value=[])

        instrumented = InstrumentedQdrantClient(mock_client, bus, agent_name="test_agent")
        instrumented.search(collection_name="documents", query_vector=[0.1, 0.2])

        events = bus.recent()
        assert len(events) == 1
        assert events[0].kind == "qdrant.op"
        assert events[0].source == "test_agent"
        assert events[0].target == "qdrant"
        assert events[0].label == "search/documents"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_event_bus.py::TestQdrantEvents -v`
Expected: FAIL (InstrumentedQdrantClient does not exist)

- [ ] **Step 3: Create InstrumentedQdrantClient**

In `shared/config.py`, add after the existing `get_qdrant()`:

```python
from logos.event_bus import EventBus, FlowEvent


class InstrumentedQdrantClient:
    """Wrapper that emits flow events on Qdrant operations."""

    def __init__(
        self,
        client: QdrantClient,
        event_bus: EventBus,
        agent_name: str = "unknown",
    ) -> None:
        self._client = client
        self._bus = event_bus
        self._agent = agent_name

    def __getattr__(self, name: str):
        """Proxy all attributes to the underlying client."""
        return getattr(self._client, name)

    def search(self, collection_name: str, **kwargs):
        self._bus.emit(FlowEvent(
            kind="qdrant.op",
            source=self._agent,
            target="qdrant",
            label=f"search/{collection_name}",
        ))
        return self._client.search(collection_name=collection_name, **kwargs)

    def upsert(self, collection_name: str, **kwargs):
        self._bus.emit(FlowEvent(
            kind="qdrant.op",
            source=self._agent,
            target="qdrant",
            label=f"upsert/{collection_name}",
        ))
        return self._client.upsert(collection_name=collection_name, **kwargs)
```

Note: This is a lightweight proxy — only `search` and `upsert` are instrumented since those are the primary operations. All other methods pass through via `__getattr__`.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_event_bus.py::TestQdrantEvents -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add shared/config.py tests/test_event_bus.py
git commit -m "feat: add InstrumentedQdrantClient that emits qdrant.op events"
```

---

### Task 7: LLM call event emission

**Files:**
- Modify: Identify the LiteLLM call path and add event emission
- Test: `tests/test_event_bus.py`

The LiteLLM proxy is an external Docker container, so we can't instrument it directly. Instead, instrument the Python client-side call point. Agents call LLMs via pydantic-ai which goes through LiteLLM.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_bus.py`:

```python
class TestLLMEvents:
    def test_llm_event_emission(self):
        """LLM call helper emits llm.call event."""
        from logos.event_bus import EventBus, FlowEvent

        bus = EventBus(maxlen=10)

        # Direct emission test — the actual instrumentation wraps pydantic-ai
        bus.emit(FlowEvent(
            kind="llm.call",
            source="stimmung_sync",
            target="llm",
            label="claude-sonnet-4-20250514",
            duration_ms=1200.0,
        ))
        events = bus.recent()
        assert len(events) == 1
        assert events[0].kind == "llm.call"
        assert events[0].target == "llm"
```

- [ ] **Step 2: Identify the LLM call instrumentation point**

LLM calls go through pydantic-ai agents, which are configured with a model that routes through LiteLLM. The Langfuse telemetry (`logos/_telemetry.py`) already wraps these calls. The simplest approach: emit an event in the `hapax_span` wrapper when span name indicates an LLM call.

In `logos/_telemetry.py`, add a hook that emits to the event bus when a generation span completes:

```python
def emit_llm_event(
    agent_name: str, model: str, duration_ms: float, event_bus: EventBus | None
) -> None:
    """Emit an llm.call flow event if bus is available."""
    if event_bus is None:
        return
    event_bus.emit(FlowEvent(
        kind="llm.call",
        source=agent_name,
        target="llm",
        label=model,
        duration_ms=duration_ms,
    ))
```

The bus reference can be set as a module-level variable (same pattern as event routes):

```python
_event_bus: EventBus | None = None

def set_telemetry_event_bus(bus: EventBus) -> None:
    global _event_bus
    _event_bus = bus
```

Wire this in `app.py` lifespan alongside the other `set_event_bus` call.

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_event_bus.py -v`
Expected: All passed

- [ ] **Step 4: Commit**

```bash
git add logos/_telemetry.py logos/api/app.py tests/test_event_bus.py
git commit -m "feat: emit llm.call events from telemetry span completions"
```

---

### Task 8: External nodes and event-driven edges in flow state

**Files:**
- Modify: `logos/api/routes/flow.py` (enrich flow state with external nodes and event-based edges)
- Test: `tests/test_event_bus.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_bus.py`:

```python
class TestExternalNodes:
    def test_recent_llm_events_create_external_node(self):
        """Flow state includes llm node when recent llm.call events exist."""
        import time
        from logos.event_bus import EventBus, FlowEvent
        from logos.api.routes.flow import build_external_nodes

        bus = EventBus(maxlen=100)
        bus.emit(FlowEvent(
            kind="llm.call", source="stimmung_sync", target="llm",
            label="claude-sonnet", duration_ms=500,
        ))

        nodes, edges = build_external_nodes(bus, since=time.time() - 60)
        assert any(n["id"] == "llm" for n in nodes)
        assert any(e["source"] == "stimmung_sync" and e["target"] == "llm" for e in edges)

    def test_no_events_no_external_nodes(self):
        """Flow state has no external nodes when no recent events."""
        import time
        from logos.event_bus import EventBus
        from logos.api.routes.flow import build_external_nodes

        bus = EventBus(maxlen=100)
        nodes, edges = build_external_nodes(bus, since=time.time() - 60)
        assert len(nodes) == 0
        assert len(edges) == 0

    def test_qdrant_events_create_qdrant_node(self):
        """Flow state includes qdrant node when recent qdrant.op events exist."""
        import time
        from logos.event_bus import EventBus, FlowEvent
        from logos.api.routes.flow import build_external_nodes

        bus = EventBus(maxlen=100)
        bus.emit(FlowEvent(
            kind="qdrant.op", source="briefing_agent", target="qdrant",
            label="search/documents",
        ))

        nodes, edges = build_external_nodes(bus, since=time.time() - 60)
        assert any(n["id"] == "qdrant" for n in nodes)
        assert any(e["source"] == "briefing_agent" and e["target"] == "qdrant" for e in edges)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_event_bus.py::TestExternalNodes -v`
Expected: FAIL (build_external_nodes does not exist)

- [ ] **Step 3: Implement build_external_nodes**

In `logos/api/routes/flow.py`, add:

```python
from logos.event_bus import EventBus

# External node definitions
_EXTERNAL_NODES = {
    "llm": {"label": "LLM Gateway", "pipeline_layer": "external"},
    "qdrant": {"label": "Vector DB", "pipeline_layer": "external"},
    "pi_fleet": {"label": "Pi Fleet", "pipeline_layer": "external"},
}

# Map event kinds to external node IDs
_KIND_TO_NODE = {
    "llm.call": "llm",
    "qdrant.op": "qdrant",
    "pi.detection": "pi_fleet",
}


def build_external_nodes(
    bus: EventBus, since: float,
) -> tuple[list[dict], list[dict]]:
    """Build synthetic external nodes and edges from recent events."""
    events = bus.recent(since=since)
    active_kinds: set[str] = set()
    edge_pairs: dict[tuple[str, str], str] = {}  # (source, target) -> label

    for ev in events:
        node_id = _KIND_TO_NODE.get(ev.kind)
        if node_id:
            active_kinds.add(ev.kind)
            key = (ev.source, ev.target)
            edge_pairs[key] = ev.label

    nodes = []
    for kind, node_id in _KIND_TO_NODE.items():
        if kind in active_kinds:
            defn = _EXTERNAL_NODES[node_id]
            # Count recent events for this node
            count = sum(1 for e in events if _KIND_TO_NODE.get(e.kind) == node_id)
            last_label = ""
            for e in reversed(events):
                if _KIND_TO_NODE.get(e.kind) == node_id:
                    last_label = e.label
                    break
            nodes.append({
                "id": node_id,
                "label": defn["label"],
                "status": "active",
                "age_s": 0,
                "pipeline_layer": defn["pipeline_layer"],
                "metrics": {"recent_count": count, "last_label": last_label},
            })

    edges = []
    for (source, target), label in edge_pairs.items():
        edges.append({
            "source": source,
            "target": target,
            "active": True,
            "label": label,
            "edge_type": "emergent",
        })

    return nodes, edges
```

Then in the main flow state endpoint handler, after building the normal nodes/edges, append the external ones:

```python
    # At end of flow state handler, before returning:
    bus: EventBus | None = getattr(request.app.state, "event_bus", None)
    if bus:
        ext_nodes, ext_edges = build_external_nodes(bus, since=time.time() - 60)
        result["nodes"].extend(ext_nodes)
        result["edges"].extend(ext_edges)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_event_bus.py -v`
Expected: All passed

- [ ] **Step 5: Commit**

```bash
git add logos/api/routes/flow.py tests/test_event_bus.py
git commit -m "feat: build external nodes (LLM, Qdrant, Pi) from recent flow events"
```

---

### Task 9: Tauri SSE bridge for flow events

**Files:**
- Modify: `hapax-logos/src-tauri/src/commands/streaming.rs` (or create `flow_events.rs`)
- Modify: `hapax-logos/src-tauri/src/main.rs` (register command)

This task adds a Tauri command that subscribes to `/api/events/stream` and re-emits events as Tauri `flow-event` events. It reuses the existing SSE client pattern from `streaming.rs`.

- [ ] **Step 1: Add the flow events command**

In `hapax-logos/src-tauri/src/commands/streaming.rs` (or a new file `flow_events.rs`), add:

```rust
#[tauri::command]
pub async fn subscribe_flow_events(app: AppHandle) -> Result<(), String> {
    let base = crate::api_base_url();
    let url = format!("{}/api/events/stream", base);

    tauri::async_runtime::spawn(async move {
        let client = reqwest::Client::new();
        let resp = match client.get(&url).send().await {
            Ok(r) => r,
            Err(e) => {
                let _ = app.emit("flow-event-error", format!("Connect failed: {e}"));
                return;
            }
        };

        let mut stream = resp.bytes_stream();
        let mut buffer = String::new();

        use futures_util::StreamExt;
        while let Some(chunk) = stream.next().await {
            let chunk = match chunk {
                Ok(c) => c,
                Err(_) => break,
            };
            let text = String::from_utf8_lossy(&chunk);
            buffer.push_str(&text);

            // Parse SSE: lines starting with "data:" followed by empty line
            while let Some(pos) = buffer.find("\n\n") {
                let block = buffer[..pos].to_string();
                buffer = buffer[pos + 2..].to_string();

                for line in block.lines() {
                    if let Some(data) = line.strip_prefix("data:") {
                        let data = data.trim();
                        if !data.is_empty() {
                            let _ = app.emit("flow-event", data);
                        }
                    }
                }
            }
        }
    });

    Ok(())
}
```

- [ ] **Step 2: Register the command in main.rs**

Find the `.invoke_handler(tauri::generate_handler![...])` call and add `subscribe_flow_events`:

```rust
commands::streaming::subscribe_flow_events,
```

- [ ] **Step 3: Build to verify Rust compiles**

Run: `cd hapax-logos && cargo check 2>&1 | tail -5`
Expected: Clean compile

- [ ] **Step 4: Commit**

```bash
git add hapax-logos/src-tauri/src/commands/streaming.rs hapax-logos/src-tauri/src/main.rs
git commit -m "feat: Tauri SSE bridge for flow-event emission"
```

---

### Task 10: Frontend — transient dot animation on edges

**Files:**
- Modify: `hapax-logos/src/pages/FlowPage.tsx` (add event listener, dot rendering in FlowingEdge)

- [ ] **Step 1: Add FlowEvent type and event listener hook**

At the top of `FlowPage.tsx`, add the type and a hook:

```typescript
interface FlowEventData {
  ts: number;
  kind: string;
  source: string;
  target: string;
  label: string;
  duration_ms: number | null;
}

function useFlowEvents(onEvent: (ev: FlowEventData) => void) {
  useEffect(() => {
    let unlisten: (() => void) | null = null;

    // Subscribe to flow events via Tauri
    invoke("subscribe_flow_events").catch(() => {
      // Not in Tauri — ignore
    });

    import("@tauri-apps/api/event").then(({ listen }) => {
      listen<string>("flow-event", (event) => {
        try {
          const data: FlowEventData = JSON.parse(event.payload);
          onEvent(data);
        } catch {
          // Malformed event — drop
        }
      }).then((fn) => { unlisten = fn; });
    }).catch(() => {
      // Not in Tauri environment
    });

    return () => { unlisten?.(); };
  }, [onEvent]);
}
```

- [ ] **Step 2: Add transient dot state and rendering to FlowingEdge**

Update the `FlowingEdge` component to accept and render transient dots:

```typescript
// Module-level: active dots keyed by edge ID
const activeDots: Map<string, { id: number; color: string; ts: number }[]> = new Map();
let dotCounter = 0;

function addDot(edgeId: string, color: string) {
  const id = ++dotCounter;
  const dots = activeDots.get(edgeId) || [];
  dots.push({ id, color, ts: Date.now() });
  activeDots.set(edgeId, dots);
  // Clean up old dots after animation completes (800ms + buffer)
  setTimeout(() => {
    const current = activeDots.get(edgeId);
    if (current) {
      const filtered = current.filter(d => d.id !== id);
      if (filtered.length === 0) activeDots.delete(edgeId);
      else activeDots.set(edgeId, filtered);
    }
  }, 1000);
}
```

In `FlowingEdge`, render dots from the `activeDots` map:

```typescript
function FlowingEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data }: EdgeProps) {
  const [path] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition });
  // ... existing edge rendering ...
  const [, forceUpdate] = useState(0);
  const dots = activeDots.get(id) || [];

  return (
    <g className="flow-edge-group">
      <BaseEdge id={id} path={path} style={{ stroke: color, strokeWidth: width, opacity, strokeDasharray: strokeDash, transition: "stroke 1s ease, opacity 1s ease" }} />
      {dots.map(dot => (
        <circle key={dot.id} r="3" fill={dot.color} opacity="1">
          <animateMotion dur="0.8s" path={path} fill="freeze" begin="0s" />
          <animate attributeName="opacity" from="1" to="0" begin="0.6s" dur="0.2s" fill="freeze" />
        </circle>
      ))}
      {lbl && <text className="flow-edge-label">...</text>}
    </g>
  );
}
```

- [ ] **Step 3: Wire event listener to dot spawning in FlowPage**

In `FlowPage`, add the event handler that maps events to edge IDs and spawns dots:

```typescript
const handleFlowEvent = useCallback((ev: FlowEventData) => {
  // Find the edge that matches source→target
  const edgeId = edges.find(e =>
    e.source === ev.source && e.target === ev.target
  )?.id;
  if (!edgeId) return;

  // Get source node status color
  const sourceNode = flowState?.nodes.find(n => n.id === ev.source);
  const sourceStatus = sourceNode?.status || "offline";
  const dotColor = sourceStatus === "active" ? p["green-400"]
    : sourceStatus === "stale" ? p["yellow-400"]
    : p["zinc-600"];

  addDot(edgeId, dotColor);
  // Force re-render of edges
  setEdges(prev => [...prev]);
}, [edges, flowState, p, setEdges]);

useFlowEvents(handleFlowEvent);
```

- [ ] **Step 4: Build to verify TypeScript compiles**

Run: `cd hapax-logos && npx tsc --noEmit`
Expected: Clean

- [ ] **Step 5: Commit**

```bash
git add hapax-logos/src/pages/FlowPage.tsx
git commit -m "feat: render transient directional dots on edges from flow events

Dots traverse edge bezier paths in 800ms, fade in last 200ms,
then remove. Each real system event produces one dot. No event = no motion."
```

---

### Task 11: Integration verification

**Files:** None — verification only.

- [ ] **Step 1: Run all Python tests**

Run: `uv run pytest tests/test_event_bus.py -v`
Expected: All passed

- [ ] **Step 2: Run TypeScript type check**

Run: `cd hapax-logos && npx tsc --noEmit`
Expected: Clean

- [ ] **Step 3: Run ruff**

Run: `uv run ruff check logos/event_bus.py logos/api/routes/events.py shared/config.py`
Expected: Clean

- [ ] **Step 4: Manual smoke test**

Start logos-api and check:
1. `curl -N http://localhost:8051/api/events/stream` — should receive SSE events as system operates
2. `curl http://localhost:8051/api/flow/state | python3 -m json.tool` — should include external nodes (llm, qdrant, pi_fleet) if there are recent events of those types
3. Build Tauri app, navigate to system anatomy — dots should appear on edges when agents run

- [ ] **Step 5: Final commit if any fixups needed**
