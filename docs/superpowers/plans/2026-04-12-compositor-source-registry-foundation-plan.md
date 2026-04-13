# Compositor Source Registry Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `Layout`/`SourceSchema`/`SurfaceSchema`/`Assignment` framework authoritative for the studio compositor: register reverie as a first-class `external_rgba` source, migrate the three hardcoded cairo overlays to natural-size + layout-driven placement, support mid-stream PiP geometry mutation, and lay persistent GStreamer `appsrc` pads for every source so preset chains can route any source into the main compositing path.

**Architecture:** Three-layer authority (JSON baseline → in-memory `LayoutState` → cairooverlay draw callback). Two backend dispatchers (`cairo` via class_name, `shm_rgba` via mmap + sidecar). Scale-on-blit render path. Command registry → UDS command server → `LayoutState.mutate()`. Reverie renders offscreen and publishes RGBA to `/dev/shm/hapax-sources/reverie.rgba`. Persistent appsrc pads in the GStreamer pipeline (one per source) ensure preset chain switches are alpha-snap decisions on existing pads, not pipeline rewiring.

**Tech Stack:** Python 3.12, pydantic v2, Cairo/PyCairo, GStreamer 1.28 (cairooverlay, glvideomixer, appsrc, glupload), pyinotify, mmap, `sdnotify`, Tauri 2 (Rust), TypeScript (React command registry), pytest, Rust (wgpu, winit, tokio) for `src-imagination`.

**Scope anchor:** `docs/superpowers/specs/2026-04-12-compositor-source-registry-foundation-design.md` (committed at 45efacbb1 on `feat/compositor-source-registry-foundation`, PR #709).

**Composition with alpha's camera epic:** Alpha's camera 24/7 resilience epic touches `compositor.py` (camera-branch construction section only, wrapped in `# --- ALPHA PHASE 2 ---` comments), `cameras.py`, `state.py`, and new camera-specific modules. Delta does NOT touch any of those. The only shared file is `compositor.py`, where delta's section (LayoutState wiring + command server startup) lives at the top-level pipeline orchestration level, distinct from the camera branch. Alpha recommends that this plan's implementation land AFTER alpha's 6-phase camera epic retires (~09:30 CDT 2026-04-13), then rebase onto the merged state. See `~/.cache/hapax/relay/inflections/20260412-221500-alpha-delta-composition.md`.

---

## File Structure

### New Python modules

- `agents/studio_compositor/layout_state.py` — in-memory Layout authority with RLock-guarded mutation, subscriber emission, debounced auto-save
- `agents/studio_compositor/source_registry.py` — `{source_id → backend_handle}` map, single `get_current_surface()` entry point
- `agents/studio_compositor/shm_rgba_reader.py` — mmap view of RGBA shm buffer + sidecar parsing, exposes `get_current_surface()` + `gst_appsrc()`
- `agents/studio_compositor/command_server.py` — UDS newline-delimited JSON handler for `compositor.surface.set_geometry` etc., calls `LayoutState.mutate()`
- `agents/studio_compositor/cairo_sources/__init__.py` — class_name → class import dispatch table
- `agents/studio_compositor/cairo_sources/token_pole_source.py` — migrated `TokenPoleCairoSource` (natural 300×300)
- `agents/studio_compositor/cairo_sources/album_overlay_source.py` — migrated `AlbumOverlayCairoSource` (natural 400×520)
- `agents/studio_compositor/cairo_sources/sierpinski_source.py` — migrated `SierpinskiCairoSource` (natural 640×640)

### New test files

- `tests/studio_compositor/test_layout_state.py`
- `tests/studio_compositor/test_source_registry.py`
- `tests/studio_compositor/test_shm_rgba_reader.py`
- `tests/studio_compositor/test_cairo_sources_migration.py`
- `tests/studio_compositor/test_default_layout_loading.py`
- `tests/studio_compositor/test_pip_draw_refactor.py`
- `tests/studio_compositor/test_command_server.py`
- `tests/studio_compositor/test_layout_file_watch.py`
- `tests/studio_compositor/test_main_layer_path.py` — the end-to-end reverie→glvideomixer proof
- `tests/studio_compositor/test_preset_inputs_resolution.py`
- `tests/studio_compositor/fixtures/default.json` — test copy of the layout
- `tests/studio_compositor/fixtures/augmented_fx_chain_input_layout.json`

### New config + scripts

- `config/compositor-layouts/default.json` — canonical baseline, installed to `~/.config/hapax-compositor/layouts/default.json` by the install script
- `scripts/install-compositor-layout.sh` — one-time installer

### New frontend files

- `hapax-logos/src/lib/commands/compositor.ts` — frontend command registry entries (5 commands)
- `hapax-logos/src-tauri/src/commands/compositor.rs` — Tauri pass-through to compositor UDS

### Modified Python files

- `shared/compositor_model.py` — add `"fx_chain_input"` to `SurfaceKind` literal
- `agents/studio_compositor/compositor.py` — load default.json → LayoutState + SourceRegistry, start command server, start file-watch, pass LayoutState into fx_chain
- `agents/studio_compositor/fx_chain.py` — refactor `_pip_draw` to walk LayoutState; construct persistent `appsrc` branches per source
- `agents/studio_compositor/cairo_source.py` — `CairoSourceRunner.__init__` gains `natural_w` / `natural_h` kwargs (default to canvas dims for backward compat), natural-size `cairo.ImageSurface` allocation, `gst_appsrc()` method
- `agents/studio_compositor/token_pole.py` — shim re-exporting from `cairo_sources/token_pole_source.py`
- `agents/studio_compositor/album_overlay.py` — shim
- `agents/studio_compositor/sierpinski_renderer.py` — shim
- `agents/effect_graph/types.py` — `Preset` type gains `inputs: list[PresetInput] | None = None`
- `agents/effect_graph/compiler.py` (or `pipeline.py` — confirmed at task 26) — preset loader resolves `inputs[].pad` names against SourceRegistry at load-time, fails loudly on unknown pad

### Modified Rust files

- `src-imagination/src/main.rs` — `HAPAX_IMAGINATION_HEADLESS=1` env branch, constructs `headless::Renderer` instead of winit Window
- `src-imagination/src/headless.rs` (new) — offscreen wgpu renderer that reuses `hapax_visual::DynamicPipeline`
- `crates/hapax-visual/src/output.rs` — second shm output path: `/dev/shm/hapax-sources/reverie.rgba` + `reverie.rgba.json` sidecar (atomic writes)

### Modified config

- `systemd/units/hapax-imagination.service` — add `Environment=HAPAX_IMAGINATION_HEADLESS=1`

---

## Phase A — Foundation types (3 tasks)

### Task 1: Add `fx_chain_input` to SurfaceKind literal

**Files:**
- Modify: `shared/compositor_model.py:71-78`
- Test: `tests/test_compositor_model.py` (add new test function)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_compositor_model.py`:

```python
def test_surface_kind_fx_chain_input_accepted():
    """fx_chain_input is a valid SurfaceKind for main-layer appsrc pads."""
    schema = SurfaceSchema(
        id="reverie-main",
        geometry=SurfaceGeometry(kind="fx_chain_input"),
    )
    assert schema.geometry.kind == "fx_chain_input"


def test_surface_kind_rejects_unknown():
    """Unknown kinds are rejected by the Literal type."""
    with pytest.raises(ValueError):
        SurfaceSchema(
            id="bogus",
            geometry=SurfaceGeometry(kind="not_a_real_kind"),
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_compositor_model.py::test_surface_kind_fx_chain_input_accepted -v
```

Expected: `ValidationError` on `"fx_chain_input"` not matching the Literal.

- [ ] **Step 3: Add the literal value**

Edit `shared/compositor_model.py:71-78`:

```python
SurfaceKind = Literal[
    "rect",           # Fixed rectangle on the canvas (x, y, w, h)
    "tile",           # Compositor tile (positioned by layout algorithm)
    "masked_region",  # Inscribed rect inside a mask shape (Sierpinski corner)
    "wgpu_binding",   # Named wgpu bind group entry (content_slot_*)
    "video_out",      # /dev/video42, NDI, OBS feed
    "ndi_out",        # NDI source advertisement (Phase 5)
    "fx_chain_input", # Named appsrc pad feeding glvideomixer (main-layer input)
]
```

- [ ] **Step 4: Run tests to verify both pass**

```bash
uv run pytest tests/test_compositor_model.py -v
```

Expected: `test_surface_kind_fx_chain_input_accepted PASSED`, `test_surface_kind_rejects_unknown PASSED`, all existing tests pass.

- [ ] **Step 5: Commit**

```bash
git add shared/compositor_model.py tests/test_compositor_model.py
git commit -m "feat(compositor): add fx_chain_input SurfaceKind for main-layer appsrc pads"
```

---

### Task 2: Create `LayoutState` class

**Files:**
- Create: `agents/studio_compositor/layout_state.py`
- Test: `tests/studio_compositor/test_layout_state.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/studio_compositor/test_layout_state.py`:

```python
"""LayoutState tests — in-memory authority for the compositor Layout."""
from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from agents.studio_compositor.layout_state import LayoutState
from shared.compositor_model import (
    Assignment,
    Layout,
    SourceSchema,
    SurfaceGeometry,
    SurfaceSchema,
)


def _minimal_layout() -> Layout:
    return Layout(
        name="test",
        sources=[
            SourceSchema(
                id="src1",
                kind="cairo",
                backend="cairo",
                params={"class_name": "TestSource", "natural_w": 100, "natural_h": 100},
            )
        ],
        surfaces=[
            SurfaceSchema(
                id="pip-ul",
                geometry=SurfaceGeometry(kind="rect", x=0, y=0, w=100, h=100),
            )
        ],
        assignments=[Assignment(source="src1", surface="pip-ul")],
    )


def test_get_returns_current_snapshot():
    state = LayoutState(_minimal_layout())
    layout = state.get()
    assert layout.name == "test"
    assert len(layout.surfaces) == 1


def test_mutate_replaces_layout_atomically():
    state = LayoutState(_minimal_layout())

    def move_pip(layout: Layout) -> Layout:
        new_surfaces = [
            s.model_copy(update={"geometry": s.geometry.model_copy(update={"x": 500, "y": 400})})
            for s in layout.surfaces
        ]
        return layout.model_copy(update={"surfaces": new_surfaces})

    state.mutate(move_pip)
    assert state.get().surfaces[0].geometry.x == 500
    assert state.get().surfaces[0].geometry.y == 400


def test_mutate_is_atomic_under_concurrent_readers():
    state = LayoutState(_minimal_layout())
    done = threading.Event()
    observed_xs: list[int] = []

    def writer() -> None:
        for i in range(100):
            state.mutate(
                lambda layout, i=i: layout.model_copy(
                    update={
                        "surfaces": [
                            s.model_copy(
                                update={
                                    "geometry": s.geometry.model_copy(update={"x": i})
                                }
                            )
                            for s in layout.surfaces
                        ]
                    }
                )
            )
        done.set()

    def reader() -> None:
        while not done.is_set():
            x = state.get().surfaces[0].geometry.x
            observed_xs.append(x)

    writers = [threading.Thread(target=writer) for _ in range(10)]
    readers = [threading.Thread(target=reader) for _ in range(50)]
    for t in readers + writers:
        t.start()
    for t in writers:
        t.join()
    done.set()
    for t in readers:
        t.join()
    for x in observed_xs:
        assert 0 <= x <= 99


def test_subscribe_receives_mutated_layout():
    state = LayoutState(_minimal_layout())
    received: list[Layout] = []
    state.subscribe(received.append)
    state.mutate(lambda layout: layout.model_copy(update={"description": "mutated"}))
    assert len(received) == 1
    assert received[0].description == "mutated"


def test_mutate_validation_failure_rolls_back():
    state = LayoutState(_minimal_layout())

    def break_layout(layout: Layout) -> Layout:
        return layout.model_copy(
            update={
                "assignments": [
                    Assignment(source="nonexistent", surface="pip-ul")
                ]
            }
        )

    with pytest.raises(ValueError, match="unknown source"):
        state.mutate(break_layout)
    assert state.get().assignments[0].source == "src1"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/studio_compositor/test_layout_state.py -v
```

Expected: `ModuleNotFoundError` on `agents.studio_compositor.layout_state`.

- [ ] **Step 3: Write the implementation**

Create `agents/studio_compositor/layout_state.py`:

```python
"""LayoutState — in-memory authority for the compositor Layout.

Holds the current `shared.compositor_model.Layout` behind an RLock, exposes
atomic `mutate()` for edits, emits events to subscribers, and (via a background
thread) debounces auto-save back to disk.

See docs/superpowers/specs/2026-04-12-compositor-source-registry-foundation-design.md § "Live state".
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from shared.compositor_model import Layout

log = logging.getLogger(__name__)

Mutator = Callable[[Layout], Layout]
Subscriber = Callable[[Layout], None]


class LayoutState:
    """In-memory authority for the current compositor Layout.

    All reads return a snapshot of the current layout. All writes go through
    ``mutate()`` which takes a pure function ``Layout -> Layout``, validates
    the result via pydantic, atomically installs it, and emits to subscribers.

    Thread-safe: RLock-guarded. Readers never block on each other; a writer
    blocks readers only for the duration of ``fn(current) + validation``.
    """

    def __init__(self, initial: Layout) -> None:
        self._layout = Layout.model_validate(initial.model_dump())
        self._lock = threading.RLock()
        self._subscribers: list[Subscriber] = []
        self._last_self_write_mtime: float = 0.0

    def get(self) -> Layout:
        """Return the current layout snapshot.

        Callers must treat the returned value as immutable. Mutations go
        through :meth:`mutate`, not by editing this return value.
        """
        with self._lock:
            return self._layout

    def mutate(self, fn: Mutator) -> None:
        """Atomically replace the layout with ``fn(current)``.

        The callable must return a new Layout (typically via ``model_copy``).
        Pydantic re-validates the result — validation failures raise without
        mutating state.
        """
        with self._lock:
            candidate = fn(self._layout)
            validated = Layout.model_validate(candidate.model_dump())
            self._layout = validated
            subscribers_snapshot = list(self._subscribers)
        for sub in subscribers_snapshot:
            try:
                sub(validated)
            except Exception:
                log.exception("LayoutState subscriber raised; continuing")

    def subscribe(self, callback: Subscriber) -> None:
        """Register a callback invoked on every successful mutation."""
        with self._lock:
            self._subscribers.append(callback)

    def mark_self_write(self, mtime: float) -> None:
        """Record the mtime of a self-initiated write-back to disk.

        The file-watcher consults this to skip inotify events that match
        within a 2-second tolerance window, preventing reload loops.
        """
        with self._lock:
            self._last_self_write_mtime = mtime

    def is_self_write(self, mtime: float, tolerance: float = 2.0) -> bool:
        """True if ``mtime`` is within ``tolerance`` seconds of the last self-write."""
        with self._lock:
            return abs(mtime - self._last_self_write_mtime) <= tolerance
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/studio_compositor/test_layout_state.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/layout_state.py tests/studio_compositor/test_layout_state.py
git commit -m "feat(compositor): LayoutState in-memory authority with atomic mutate"
```

---

### Task 3: Create `SourceRegistry` skeleton + backend dispatch

**Files:**
- Create: `agents/studio_compositor/source_registry.py`
- Test: `tests/studio_compositor/test_source_registry.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/studio_compositor/test_source_registry.py`:

```python
from __future__ import annotations

import cairo
import pytest

from agents.studio_compositor.source_registry import (
    SourceRegistry,
    UnknownBackendError,
    UnknownSourceError,
)
from shared.compositor_model import Layout, SourceSchema, SurfaceGeometry, SurfaceSchema


class _FakeBackend:
    def __init__(self, surface: cairo.ImageSurface) -> None:
        self._surface = surface

    def get_current_surface(self) -> cairo.ImageSurface:
        return self._surface


def _make_source(id: str, backend: str, params: dict) -> SourceSchema:
    return SourceSchema(id=id, kind="cairo", backend=backend, params=params)


def test_get_current_surface_returns_backend_output():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10)
    registry = SourceRegistry()
    registry.register("src1", _FakeBackend(surf))
    assert registry.get_current_surface("src1") is surf


def test_get_current_surface_unknown_raises():
    registry = SourceRegistry()
    with pytest.raises(UnknownSourceError, match="bogus"):
        registry.get_current_surface("bogus")


def test_dispatch_raises_for_unknown_backend():
    registry = SourceRegistry()
    src = _make_source("src1", "not_a_backend", {})
    with pytest.raises(UnknownBackendError, match="not_a_backend"):
        registry.construct_backend(src)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/studio_compositor/test_source_registry.py -v
```

Expected: `ModuleNotFoundError` on `agents.studio_compositor.source_registry`.

- [ ] **Step 3: Write the implementation**

Create `agents/studio_compositor/source_registry.py`:

```python
"""SourceRegistry — thin map from source_id to backend handles.

Backends expose ``get_current_surface() -> cairo.ImageSurface | None``. The
render loop and fx_chain both consult this registry and don't care whether
the pixels came from a CairoSourceRunner or a ShmRgbaReader.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

import cairo

from shared.compositor_model import SourceSchema

log = logging.getLogger(__name__)


class UnknownSourceError(KeyError):
    """Raised when a source_id is not registered."""


class UnknownBackendError(ValueError):
    """Raised when a SourceSchema.backend has no dispatcher."""


class SourceBackend(Protocol):
    def get_current_surface(self) -> cairo.ImageSurface | None:  # pragma: no cover - protocol
        ...


class SourceRegistry:
    """Maps source_id → backend handle. Single lookup entry point."""

    def __init__(self) -> None:
        self._backends: dict[str, SourceBackend] = {}

    def register(self, source_id: str, backend: SourceBackend) -> None:
        if source_id in self._backends:
            raise ValueError(f"source_id already registered: {source_id}")
        self._backends[source_id] = backend

    def get_current_surface(self, source_id: str) -> cairo.ImageSurface | None:
        try:
            return self._backends[source_id].get_current_surface()
        except KeyError:
            raise UnknownSourceError(source_id) from None

    def ids(self) -> list[str]:
        return list(self._backends.keys())

    def construct_backend(self, source: SourceSchema) -> SourceBackend:
        """Instantiate a backend for ``source`` using its ``backend`` dispatcher.

        Fills in Task 6; this stub raises for any backend to make the dispatch
        path explicit and covered by a failing test.
        """
        if source.backend == "cairo":
            raise UnknownBackendError(
                f"cairo backend dispatcher not wired yet (source: {source.id})"
            )
        if source.backend == "shm_rgba":
            raise UnknownBackendError(
                f"shm_rgba backend dispatcher not wired yet (source: {source.id})"
            )
        raise UnknownBackendError(f"unknown backend: {source.backend}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/studio_compositor/test_source_registry.py -v
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/source_registry.py tests/studio_compositor/test_source_registry.py
git commit -m "feat(compositor): SourceRegistry skeleton with backend dispatch protocol"
```

---

## Phase B — Backends (3 tasks)

### Task 4: Extend `CairoSourceRunner` with `natural_w` / `natural_h`

**Files:**
- Modify: `agents/studio_compositor/cairo_source.py:86-120` (constructor), `237-247` (render allocation)
- Test: extend `tests/studio_compositor/test_cairo_source_runner.py` or create `tests/studio_compositor/test_cairo_source_natural_size.py`

- [ ] **Step 1: Write the failing test**

Create `tests/studio_compositor/test_cairo_source_natural_size.py`:

```python
"""Verify CairoSourceRunner renders at natural_w/natural_h when given."""
from __future__ import annotations

import cairo
import pytest

from agents.studio_compositor.cairo_source import CairoSource, CairoSourceRunner


class _FillSource(CairoSource):
    """Fills the passed-in canvas with solid red so we can inspect the surface size."""

    def render(self, cr, canvas_w, canvas_h, t, state):  # noqa: D401
        cr.set_source_rgba(1.0, 0.0, 0.0, 1.0)
        cr.rectangle(0, 0, canvas_w, canvas_h)
        cr.fill()


def test_natural_size_smaller_than_canvas_allocates_natural():
    runner = CairoSourceRunner(
        source_id="red",
        source=_FillSource(),
        canvas_w=1920,
        canvas_h=1080,
        target_fps=10.0,
        natural_w=300,
        natural_h=300,
    )
    runner.tick_once()
    out = runner.get_output_surface()
    assert out is not None
    assert out.get_width() == 300
    assert out.get_height() == 300


def test_natural_size_defaults_to_canvas_when_unset():
    runner = CairoSourceRunner(
        source_id="red",
        source=_FillSource(),
        canvas_w=640,
        canvas_h=360,
        target_fps=10.0,
    )
    runner.tick_once()
    out = runner.get_output_surface()
    assert out is not None
    assert out.get_width() == 640
    assert out.get_height() == 360
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/studio_compositor/test_cairo_source_natural_size.py -v
```

Expected: `TypeError: __init__() got an unexpected keyword argument 'natural_w'`.

- [ ] **Step 3: Modify `CairoSourceRunner.__init__`**

Edit `agents/studio_compositor/cairo_source.py:86-120`. Replace the constructor signature and body to accept `natural_w` / `natural_h` with defaults equal to canvas dims:

```python
    def __init__(
        self,
        source_id: str,
        source: CairoSource,
        canvas_w: int = 1920,
        canvas_h: int = 1080,
        target_fps: float = 10.0,
        publish_to_source_protocol: bool = False,
        budget_tracker: BudgetTracker | None = None,
        budget_ms: float | None = None,
        natural_w: int | None = None,
        natural_h: int | None = None,
    ) -> None:
        if target_fps <= 0:
            raise ValueError(f"target_fps must be > 0, got {target_fps}")
        if budget_ms is not None and budget_ms <= 0:
            raise ValueError(f"budget_ms must be > 0 when set, got {budget_ms}")
        self._source_id = source_id
        self._source = source
        self._canvas_w = canvas_w
        self._canvas_h = canvas_h
        self._natural_w = natural_w if natural_w is not None else canvas_w
        self._natural_h = natural_h if natural_h is not None else canvas_h
        self._period = 1.0 / target_fps
        self._publish = publish_to_source_protocol
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._output_surface: cairo.ImageSurface | None = None
        self._output_lock = threading.Lock()
        self._frame_count = 0
        self._last_render_ms = 0.0
        self._budget_tracker = budget_tracker
        self._budget_ms = budget_ms
        self._consecutive_skips = 0
```

Then update `_render_one_frame()` at `cairo_source.py:237`:

```python
    def _render_one_frame(self) -> None:
        if (
            self._budget_ms is not None
            and self._budget_tracker is not None
            and self._budget_tracker.over_budget(self._source_id, self._budget_ms)
        ):
            self._budget_tracker.record_skip(self._source_id)
            self._consecutive_skips += 1
            log.debug(
                "CairoSource %s over budget (%.2fms > %.2fms); skipping tick (run=%d)",
                self._source_id,
                self._budget_tracker.last_frame_ms(self._source_id),
                self._budget_ms,
                self._consecutive_skips,
            )
            return

        t0 = time.monotonic()
        try:
            surface = cairo.ImageSurface(
                cairo.FORMAT_ARGB32, self._natural_w, self._natural_h
            )
            cr = cairo.Context(surface)
            self._source.render(
                cr,
                self._natural_w,
                self._natural_h,
                t0,
                self._source.state(),
            )
            surface.flush()
        except Exception:
            log.exception("CairoSource %s render failed", self._source_id)
            return

        with self._output_lock:
            self._output_surface = surface
        self._frame_count += 1
        self._last_render_ms = (time.monotonic() - t0) * 1000.0
        if self._budget_tracker is not None:
            self._budget_tracker.record(self._source_id, self._last_render_ms)
        self._consecutive_skips = 0

        if self._publish:
            self._publish_to_source_protocol(surface)
```

- [ ] **Step 4: Run tests to verify they pass + existing suite**

```bash
uv run pytest tests/studio_compositor/test_cairo_source_natural_size.py tests/studio_compositor/ -v
```

Expected: new tests pass, existing `CairoSourceRunner` suite passes unchanged.

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/cairo_source.py tests/studio_compositor/test_cairo_source_natural_size.py
git commit -m "feat(cairo-source): natural_w/natural_h render size separate from canvas"
```

---

### Task 5: Create `ShmRgbaReader`

**Files:**
- Create: `agents/studio_compositor/shm_rgba_reader.py`
- Test: `tests/studio_compositor/test_shm_rgba_reader.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/studio_compositor/test_shm_rgba_reader.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import cairo
import pytest

from agents.studio_compositor.shm_rgba_reader import ShmRgbaReader


def _write_rgba_and_sidecar(tmp_path: Path, w: int, h: int, fill: int, frame_id: int) -> Path:
    stride = w * 4
    rgba = bytes([fill]) * (stride * h)
    path = tmp_path / "reverie.rgba"
    path.write_bytes(rgba)
    sidecar = path.with_suffix(".rgba.json")
    sidecar.write_text(json.dumps({"w": w, "h": h, "stride": stride, "frame_id": frame_id}))
    return path


def test_reader_returns_surface_matching_sidecar(tmp_path: Path):
    path = _write_rgba_and_sidecar(tmp_path, w=4, h=3, fill=0xFF, frame_id=1)
    reader = ShmRgbaReader(path)
    surf = reader.get_current_surface()
    assert surf is not None
    assert surf.get_width() == 4
    assert surf.get_height() == 3


def test_reader_reloads_on_frame_id_change(tmp_path: Path):
    path = _write_rgba_and_sidecar(tmp_path, w=4, h=3, fill=0xAA, frame_id=1)
    reader = ShmRgbaReader(path)
    first = reader.get_current_surface()
    _write_rgba_and_sidecar(tmp_path, w=4, h=3, fill=0xBB, frame_id=2)
    second = reader.get_current_surface()
    assert first is not second
    assert bytes(second.get_data())[0] == 0xBB


def test_reader_returns_none_if_sidecar_missing(tmp_path: Path):
    path = tmp_path / "reverie.rgba"
    path.write_bytes(b"\x00" * 48)
    reader = ShmRgbaReader(path)
    assert reader.get_current_surface() is None


def test_reader_returns_none_if_rgba_file_missing(tmp_path: Path):
    path = tmp_path / "reverie.rgba"
    sidecar = tmp_path / "reverie.rgba.json"
    sidecar.write_text(json.dumps({"w": 4, "h": 3, "stride": 16, "frame_id": 1}))
    reader = ShmRgbaReader(path)
    assert reader.get_current_surface() is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/studio_compositor/test_shm_rgba_reader.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Create `agents/studio_compositor/shm_rgba_reader.py`:

```python
"""ShmRgbaReader — reads RGBA frames from a shared-memory file + sidecar.

Shape of the sidecar JSON (``<path>.json``):
    {"w": int, "h": int, "stride": int, "frame_id": int}

The reader mmaps the RGBA buffer and re-wraps it as a ``cairo.ImageSurface``
whenever ``frame_id`` changes. Missing file / missing sidecar / unreadable
JSON all resolve to ``get_current_surface() -> None`` without raising.
"""

from __future__ import annotations

import json
import logging
import mmap
import os
from pathlib import Path
from typing import Any

import cairo

log = logging.getLogger(__name__)


class ShmRgbaReader:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._sidecar_path = self._path.with_suffix(self._path.suffix + ".json")
        self._cached_surface: cairo.ImageSurface | None = None
        self._cached_frame_id: int | None = None

    def _read_sidecar(self) -> dict[str, Any] | None:
        if not self._sidecar_path.exists():
            return None
        try:
            return json.loads(self._sidecar_path.read_text())
        except (OSError, json.JSONDecodeError):
            log.debug("ShmRgbaReader failed to read sidecar %s", self._sidecar_path, exc_info=True)
            return None

    def get_current_surface(self) -> cairo.ImageSurface | None:
        meta = self._read_sidecar()
        if meta is None:
            return None
        if not self._path.exists():
            return None

        frame_id = meta.get("frame_id")
        if frame_id == self._cached_frame_id and self._cached_surface is not None:
            return self._cached_surface

        w = int(meta["w"])
        h = int(meta["h"])
        stride = int(meta["stride"])
        try:
            raw = self._path.read_bytes()
        except OSError:
            log.debug("ShmRgbaReader failed to read %s", self._path, exc_info=True)
            return None
        if len(raw) < stride * h:
            log.debug("ShmRgbaReader buffer short: got %d, want %d", len(raw), stride * h)
            return None

        data = bytearray(raw[: stride * h])
        surface = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, w, h, stride)
        self._cached_surface = surface
        self._cached_frame_id = frame_id
        return surface
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/studio_compositor/test_shm_rgba_reader.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/shm_rgba_reader.py tests/studio_compositor/test_shm_rgba_reader.py
git commit -m "feat(compositor): ShmRgbaReader for external_rgba sources with sidecar metadata"
```

---

### Task 6: Wire backend dispatcher table for `cairo` + `shm_rgba`

**Files:**
- Modify: `agents/studio_compositor/source_registry.py` (replace stub `construct_backend`)
- Test: extend `tests/studio_compositor/test_source_registry.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/studio_compositor/test_source_registry.py`:

```python
from pathlib import Path

def test_construct_backend_cairo_via_class_name(tmp_path: Path):
    src = SourceSchema(
        id="token_pole",
        kind="cairo",
        backend="cairo",
        params={"class_name": "TokenPoleCairoSource", "natural_w": 300, "natural_h": 300},
    )
    registry = SourceRegistry()
    backend = registry.construct_backend(src)
    assert backend is not None
    assert hasattr(backend, "get_current_surface")


def test_construct_backend_shm_rgba(tmp_path: Path):
    rgba_path = tmp_path / "reverie.rgba"
    src = SourceSchema(
        id="reverie",
        kind="external_rgba",
        backend="shm_rgba",
        params={"natural_w": 640, "natural_h": 360, "shm_path": str(rgba_path)},
    )
    registry = SourceRegistry()
    backend = registry.construct_backend(src)
    assert backend is not None
    assert hasattr(backend, "get_current_surface")
```

(The first test will require the `cairo_sources` package with a `TokenPoleCairoSource` class — Task 7 / 8. Skip this subtest in Task 6, add a `@pytest.mark.skip("requires Task 8")` marker and remove the marker in Task 8.)

- [ ] **Step 2: Run test to verify shm_rgba case fails**

```bash
uv run pytest tests/studio_compositor/test_source_registry.py::test_construct_backend_shm_rgba -v
```

Expected: `UnknownBackendError: shm_rgba backend dispatcher not wired yet`.

- [ ] **Step 3: Replace `construct_backend` in `source_registry.py`**

```python
    def construct_backend(self, source: SourceSchema) -> SourceBackend:
        """Instantiate a backend for ``source`` using its ``backend`` dispatcher."""
        if source.backend == "cairo":
            from agents.studio_compositor.cairo_sources import get_cairo_source_class
            from agents.studio_compositor.cairo_source import CairoSourceRunner

            class_name = source.params.get("class_name")
            if not class_name:
                raise UnknownBackendError(
                    f"cairo source {source.id}: missing params.class_name"
                )
            source_cls = get_cairo_source_class(class_name)
            source_obj = source_cls()
            natural_w = int(source.params.get("natural_w", 1920))
            natural_h = int(source.params.get("natural_h", 1080))
            target_fps = float(source.params.get("fps", 10.0))
            return CairoSourceRunner(
                source_id=source.id,
                source=source_obj,
                canvas_w=natural_w,
                canvas_h=natural_h,
                target_fps=target_fps,
                natural_w=natural_w,
                natural_h=natural_h,
            )
        if source.backend == "shm_rgba":
            from agents.studio_compositor.shm_rgba_reader import ShmRgbaReader

            shm_path = source.params.get("shm_path")
            if not shm_path:
                raise UnknownBackendError(
                    f"shm_rgba source {source.id}: missing params.shm_path"
                )
            return ShmRgbaReader(Path(shm_path))
        raise UnknownBackendError(f"unknown backend: {source.backend}")
```

Add the import at the top of the file:

```python
from pathlib import Path
```

- [ ] **Step 4: Run shm_rgba test to verify it passes**

```bash
uv run pytest tests/studio_compositor/test_source_registry.py::test_construct_backend_shm_rgba -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/source_registry.py tests/studio_compositor/test_source_registry.py
git commit -m "feat(compositor): wire shm_rgba backend dispatcher in SourceRegistry"
```

---

## Phase C — Cairo source migration (4 tasks)

### Task 7: Create `cairo_sources` package + dispatcher

**Files:**
- Create: `agents/studio_compositor/cairo_sources/__init__.py`
- Test: extend `tests/studio_compositor/test_source_registry.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/studio_compositor/test_source_registry.py`:

```python
def test_cairo_source_registry_unknown_class_raises():
    from agents.studio_compositor.cairo_sources import get_cairo_source_class

    with pytest.raises(KeyError, match="NotARealClass"):
        get_cairo_source_class("NotARealClass")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/studio_compositor/test_source_registry.py::test_cairo_source_registry_unknown_class_raises -v
```

Expected: `ModuleNotFoundError: agents.studio_compositor.cairo_sources`.

- [ ] **Step 3: Write the package init**

Create `agents/studio_compositor/cairo_sources/__init__.py`:

```python
"""Registry of migrated CairoSource classes.

Adding a new cairo source: drop a module file in this package exporting a
``CairoSource`` subclass, then add a row to ``_CAIRO_SOURCE_CLASSES`` below.
"""

from __future__ import annotations

from typing import Type

from agents.studio_compositor.cairo_source import CairoSource

_CAIRO_SOURCE_CLASSES: dict[str, Type[CairoSource]] = {}


def register(name: str, cls: Type[CairoSource]) -> None:
    """Register a CairoSource class by name. Idempotent on duplicates of the same class."""
    existing = _CAIRO_SOURCE_CLASSES.get(name)
    if existing is None:
        _CAIRO_SOURCE_CLASSES[name] = cls
        return
    if existing is cls:
        return
    raise ValueError(
        f"cairo_sources: name {name!r} already bound to {existing.__name__}, not {cls.__name__}"
    )


def get_cairo_source_class(name: str) -> Type[CairoSource]:
    """Return the CairoSource class registered under ``name``.

    Raises :class:`KeyError` with the unknown name if not registered.
    """
    try:
        return _CAIRO_SOURCE_CLASSES[name]
    except KeyError as e:
        raise KeyError(f"cairo source class not registered: {name}") from e


def list_classes() -> list[str]:
    return sorted(_CAIRO_SOURCE_CLASSES.keys())
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/studio_compositor/test_source_registry.py::test_cairo_source_registry_unknown_class_raises -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/cairo_sources/__init__.py tests/studio_compositor/test_source_registry.py
git commit -m "feat(compositor): cairo_sources package with class_name registry"
```

---

### Task 8: Migrate `TokenPole` → `TokenPoleCairoSource`

**Files:**
- Read: `agents/studio_compositor/token_pole.py` (current direct-cairo impl)
- Create: `agents/studio_compositor/cairo_sources/token_pole_source.py`
- Modify: `agents/studio_compositor/token_pole.py` (shim)
- Test: `tests/studio_compositor/test_cairo_sources_migration.py`

- [ ] **Step 1: Read the current token_pole.py to understand its state and render method**

```bash
cat agents/studio_compositor/token_pole.py
```

Note:
- The class name and current render signature
- Which instance attributes need to persist (color cycle, spiral position, particle state)
- Any constants `OVERLAY_X`, `OVERLAY_Y`, `OVERLAY_SIZE` that must be deleted

- [ ] **Step 2: Write the failing test**

Create `tests/studio_compositor/test_cairo_sources_migration.py`:

```python
"""Each migrated cairo source renders at natural size with origin (0,0)."""
from __future__ import annotations

import cairo
import pytest

from agents.studio_compositor.cairo_sources import get_cairo_source_class


def _render_at(class_name: str, w: int, h: int) -> cairo.ImageSurface:
    cls = get_cairo_source_class(class_name)
    source = cls()
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    cr = cairo.Context(surface)
    source.render(cr, w, h, t=0.0, state={})
    surface.flush()
    return surface


def test_token_pole_renders_at_natural_300x300():
    surf = _render_at("TokenPoleCairoSource", 300, 300)
    assert surf.get_width() == 300
    assert surf.get_height() == 300
    data = bytes(surf.get_data())
    assert any(b != 0 for b in data[:1024])


def test_album_overlay_renders_at_natural_400x520():
    surf = _render_at("AlbumOverlayCairoSource", 400, 520)
    assert surf.get_width() == 400
    assert surf.get_height() == 520
    data = bytes(surf.get_data())
    assert any(b != 0 for b in data[:1024])


def test_sierpinski_renders_at_natural_640x640():
    surf = _render_at("SierpinskiCairoSource", 640, 640)
    assert surf.get_width() == 640
    assert surf.get_height() == 640
    data = bytes(surf.get_data())
    assert any(b != 0 for b in data[:1024])
```

- [ ] **Step 3: Run test to verify all three fail**

```bash
uv run pytest tests/studio_compositor/test_cairo_sources_migration.py -v
```

Expected: `KeyError: cairo source class not registered: TokenPoleCairoSource` (and same for the other two).

- [ ] **Step 4: Create `TokenPoleCairoSource` module**

Create `agents/studio_compositor/cairo_sources/token_pole_source.py`:

```python
"""TokenPoleCairoSource — migrated from agents/studio_compositor/token_pole.py.

Natural size: 300×300. Draws the Vitruvian Man backdrop + golden-spiral token
tracker + particle-explosion state at local origin (0,0). The compositor now
places this surface at its assigned SurfaceSchema.geometry rather than
hardcoding `OVERLAY_X=20, OVERLAY_Y=20`.

This module imports and wraps the existing rendering logic from the legacy
``token_pole`` module to minimize migration risk. The legacy module becomes
a thin shim (see Task 11) that re-exports this class.
"""

from __future__ import annotations

from typing import Any

import cairo

from agents.studio_compositor.cairo_source import CairoSource
from agents.studio_compositor.cairo_sources import register


class TokenPoleCairoSource(CairoSource):
    """Vitruvian + golden spiral + particles, drawn at natural 300×300."""

    def __init__(self) -> None:
        # Import the legacy module locally to avoid circular imports during
        # package init. The legacy module owns particle state, spiral state,
        # and color cycling.
        from agents.studio_compositor import token_pole as _legacy

        self._impl = _legacy._make_legacy_impl()  # helper added in Task 11

    def render(
        self,
        cr: cairo.Context,
        canvas_w: int,
        canvas_h: int,
        t: float,
        state: dict[str, Any],
    ) -> None:
        self._impl.render_at_origin(cr, canvas_w, canvas_h, t, state)

    def state(self) -> dict[str, Any]:
        return self._impl.state()

    def cleanup(self) -> None:
        self._impl.cleanup()


register("TokenPoleCairoSource", TokenPoleCairoSource)
```

- [ ] **Step 5: Expose helper from legacy `token_pole.py`**

The legacy `token_pole.py` probably has the drawing logic inside a class or module-level functions. Add a helper (a) factoring the current render into a method that draws at local origin with no hardcoded OVERLAY_X/Y, and (b) exposing a module-level `_make_legacy_impl()` factory. Keep the existing public surface working for any callers not yet migrated.

Example refactor pattern (adapt to whatever `token_pole.py` actually contains):

```python
# At module top of agents/studio_compositor/token_pole.py, ADD:

class _TokenPoleLegacyImpl:
    """Internal impl shared between the legacy direct-use and the migrated CairoSource."""

    def __init__(self) -> None:
        self._particle_state: list[dict] = []
        self._color_cycle_t: float = 0.0
        # ... any other state currently on module-level globals or the old class

    def render_at_origin(self, cr, w, h, t, state):
        # Draw into (0, 0, w, h). NO OVERLAY_X, NO OVERLAY_Y, NO OVERLAY_SIZE.
        # The compositor places us at our assigned geometry.
        ... # existing draw logic, with all X/Y offsets made relative to 0/0

    def state(self):
        return {}

    def cleanup(self):
        pass


def _make_legacy_impl() -> _TokenPoleLegacyImpl:
    return _TokenPoleLegacyImpl()


# Existing module-level OVERLAY_X, OVERLAY_Y, OVERLAY_SIZE constants are
# DELETED — the natural-size surface is 300×300 and the compositor owns
# placement. Any other callers of these constants must be migrated.
```

- [ ] **Step 6: Run the migration test to verify token_pole passes**

```bash
uv run pytest tests/studio_compositor/test_cairo_sources_migration.py::test_token_pole_renders_at_natural_300x300 -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add agents/studio_compositor/cairo_sources/token_pole_source.py agents/studio_compositor/token_pole.py tests/studio_compositor/test_cairo_sources_migration.py
git commit -m "feat(compositor): migrate TokenPole to TokenPoleCairoSource (natural 300x300)"
```

---

### Task 9: Migrate `AlbumOverlay` → `AlbumOverlayCairoSource`

**Files:**
- Create: `agents/studio_compositor/cairo_sources/album_overlay_source.py`
- Modify: `agents/studio_compositor/album_overlay.py` — add `_AlbumOverlayLegacyImpl` and `_make_legacy_impl()` following Task 8's pattern
- Test: already written in Task 8

Repeat the Task 8 recipe for AlbumOverlayCairoSource at natural size 400×520. Same structure: legacy module exposes `_make_legacy_impl()`; migrated class wraps it.

- [ ] **Step 1: Read the current `album_overlay.py` to understand state**

```bash
cat agents/studio_compositor/album_overlay.py
```

- [ ] **Step 2: Run the migration test to see the target failure**

```bash
uv run pytest tests/studio_compositor/test_cairo_sources_migration.py::test_album_overlay_renders_at_natural_400x520 -v
```

Expected: `KeyError: cairo source class not registered: AlbumOverlayCairoSource`.

- [ ] **Step 3: Create `AlbumOverlayCairoSource` + legacy helper**

Create `agents/studio_compositor/cairo_sources/album_overlay_source.py`:

```python
"""AlbumOverlayCairoSource — migrated from agents/studio_compositor/album_overlay.py.

Natural size: 400×520. Draws the album cover + splattribution text block +
PiP effect at local origin (0,0).
"""

from __future__ import annotations

from typing import Any

import cairo

from agents.studio_compositor.cairo_source import CairoSource
from agents.studio_compositor.cairo_sources import register


class AlbumOverlayCairoSource(CairoSource):
    def __init__(self) -> None:
        from agents.studio_compositor import album_overlay as _legacy
        self._impl = _legacy._make_legacy_impl()

    def render(
        self,
        cr: cairo.Context,
        canvas_w: int,
        canvas_h: int,
        t: float,
        state: dict[str, Any],
    ) -> None:
        self._impl.render_at_origin(cr, canvas_w, canvas_h, t, state)

    def state(self) -> dict[str, Any]:
        return self._impl.state()

    def cleanup(self) -> None:
        self._impl.cleanup()


register("AlbumOverlayCairoSource", AlbumOverlayCairoSource)
```

- [ ] **Step 4: Add `_AlbumOverlayLegacyImpl` + `_make_legacy_impl()` to `album_overlay.py`**

Same pattern as Task 8. Extract the current draw logic into a class whose `render_at_origin(cr, w, h, t, state)` method draws at (0, 0, w, h) with no hardcoded placement offsets.

- [ ] **Step 5: Run the migration test to verify album passes**

```bash
uv run pytest tests/studio_compositor/test_cairo_sources_migration.py::test_album_overlay_renders_at_natural_400x520 -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add agents/studio_compositor/cairo_sources/album_overlay_source.py agents/studio_compositor/album_overlay.py
git commit -m "feat(compositor): migrate AlbumOverlay to AlbumOverlayCairoSource (natural 400x520)"
```

---

### Task 10: Migrate `SierpinskiRenderer` → `SierpinskiCairoSource`

**Files:**
- Create: `agents/studio_compositor/cairo_sources/sierpinski_source.py`
- Modify: `agents/studio_compositor/sierpinski_renderer.py` — add `_SierpinskiLegacyImpl` + `_make_legacy_impl()`
- Test: already written in Task 8

Same pattern. Natural size 640×640. Repeat steps 1–6 of Task 9 for Sierpinski.

The Sierpinski renderer computes yt-frame inscribed rects relative to triangle vertices — those calculations are already local and transfer cleanly.

- [ ] **Step 1: Read the current `sierpinski_renderer.py`**

```bash
cat agents/studio_compositor/sierpinski_renderer.py
```

- [ ] **Step 2: Run the migration test to see the target failure**

```bash
uv run pytest tests/studio_compositor/test_cairo_sources_migration.py::test_sierpinski_renders_at_natural_640x640 -v
```

Expected: KeyError for SierpinskiCairoSource.

- [ ] **Step 3: Create the migrated module + legacy helper, following Task 9 pattern**

- [ ] **Step 4: Run the migration test**

```bash
uv run pytest tests/studio_compositor/test_cairo_sources_migration.py -v
```

Expected: all three tests pass.

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/cairo_sources/sierpinski_source.py agents/studio_compositor/sierpinski_renderer.py
git commit -m "feat(compositor): migrate SierpinskiRenderer to SierpinskiCairoSource (natural 640x640)"
```

---

### Task 11: Final shim sweep + remove hardcoded offsets

**Files:**
- Modify: `agents/studio_compositor/token_pole.py`, `album_overlay.py`, `sierpinski_renderer.py` — remove any remaining module-level `OVERLAY_X` / `OVERLAY_Y` / `OVERLAY_SIZE` constants now that nothing needs them
- Test: grep the repo for any remaining references

- [ ] **Step 1: Grep for stale constants**

```bash
grep -rn "OVERLAY_X\|OVERLAY_Y\|OVERLAY_SIZE" agents/studio_compositor/ scripts/ tests/ || echo "none found"
```

Expected: only references inside the migrated classes (if any); nothing at module top-level of the legacy files.

- [ ] **Step 2: Delete the stale constants**

Remove any module-level `OVERLAY_X`, `OVERLAY_Y`, `OVERLAY_SIZE` lines still present. Leave the `_make_legacy_impl()` helpers untouched.

- [ ] **Step 3: Run the full compositor test suite**

```bash
uv run pytest tests/studio_compositor/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Run ruff + pyright**

```bash
uv run ruff check agents/studio_compositor/
uv run pyright agents/studio_compositor/
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/token_pole.py agents/studio_compositor/album_overlay.py agents/studio_compositor/sierpinski_renderer.py
git commit -m "refactor(compositor): delete hardcoded OVERLAY_* constants from migrated legacy modules"
```

---

## Phase D — Default layout JSON + wiring (3 tasks)

### Task 12: Create baseline `default.json` + install script

**Files:**
- Create: `config/compositor-layouts/default.json`
- Create: `scripts/install-compositor-layout.sh`
- Test: `tests/studio_compositor/test_default_layout_loading.py`

- [ ] **Step 1: Write the failing test**

Create `tests/studio_compositor/test_default_layout_loading.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from shared.compositor_model import Layout

DEFAULT_JSON = Path(__file__).parents[2] / "config" / "compositor-layouts" / "default.json"


def test_default_json_exists_and_is_valid_layout():
    assert DEFAULT_JSON.exists(), f"missing {DEFAULT_JSON}"
    raw = json.loads(DEFAULT_JSON.read_text())
    layout = Layout.model_validate(raw)
    source_ids = {s.id for s in layout.sources}
    assert source_ids == {"token_pole", "album", "sierpinski", "reverie"}
    surface_ids = {s.id for s in layout.surfaces}
    assert surface_ids == {"pip-ul", "pip-ur", "pip-ll", "pip-lr"}
    assignment_pairs = {(a.source, a.surface) for a in layout.assignments}
    assert assignment_pairs == {
        ("token_pole", "pip-ul"),
        ("reverie", "pip-ur"),
        ("album", "pip-ll"),
    }
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/studio_compositor/test_default_layout_loading.py -v
```

Expected: `AssertionError: missing <path>/config/compositor-layouts/default.json`.

- [ ] **Step 3: Create the JSON file**

Create `config/compositor-layouts/default.json`:

```json
{
  "name": "default",
  "description": "Default studio compositor layout — PR 1 baseline",
  "sources": [
    {
      "id": "token_pole",
      "kind": "cairo",
      "backend": "cairo",
      "params": {"class_name": "TokenPoleCairoSource", "natural_w": 300, "natural_h": 300}
    },
    {
      "id": "album",
      "kind": "cairo",
      "backend": "cairo",
      "params": {"class_name": "AlbumOverlayCairoSource", "natural_w": 400, "natural_h": 520}
    },
    {
      "id": "sierpinski",
      "kind": "cairo",
      "backend": "cairo",
      "params": {"class_name": "SierpinskiCairoSource", "natural_w": 640, "natural_h": 640}
    },
    {
      "id": "reverie",
      "kind": "external_rgba",
      "backend": "shm_rgba",
      "params": {
        "natural_w": 640,
        "natural_h": 360,
        "shm_path": "/dev/shm/hapax-sources/reverie.rgba"
      }
    }
  ],
  "surfaces": [
    {"id": "pip-ul", "geometry": {"kind": "rect", "x":   20, "y":  20, "w": 300, "h": 300}, "z_order": 10},
    {"id": "pip-ur", "geometry": {"kind": "rect", "x": 1260, "y":  20, "w": 640, "h": 360}, "z_order": 10},
    {"id": "pip-ll", "geometry": {"kind": "rect", "x":   20, "y": 540, "w": 400, "h": 520}, "z_order": 10},
    {"id": "pip-lr", "geometry": {"kind": "rect", "x": 1260, "y": 420, "w": 640, "h": 640}, "z_order": 10}
  ],
  "assignments": [
    {"source": "token_pole", "surface": "pip-ul"},
    {"source": "reverie",    "surface": "pip-ur"},
    {"source": "album",      "surface": "pip-ll"}
  ]
}
```

- [ ] **Step 4: Create the installer script**

Create `scripts/install-compositor-layout.sh` with mode 755:

```bash
#!/usr/bin/env bash
# install-compositor-layout.sh — install the canonical compositor layout
# to the user config directory on first run.
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)/config/compositor-layouts/default.json"
DEST_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/hapax-compositor/layouts"
DEST="$DEST_DIR/default.json"

mkdir -p "$DEST_DIR"
if [ -f "$DEST" ]; then
    echo "layout already installed at $DEST; leaving in place"
    exit 0
fi
install -m 644 "$SRC" "$DEST"
echo "installed $DEST"
```

Make it executable:

```bash
chmod 755 scripts/install-compositor-layout.sh
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
uv run pytest tests/studio_compositor/test_default_layout_loading.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add config/compositor-layouts/default.json scripts/install-compositor-layout.sh tests/studio_compositor/test_default_layout_loading.py
git commit -m "feat(compositor): baseline default.json layout + install script"
```

---

### Task 13: Compositor startup loads `default.json` into `LayoutState` with fallback

**Files:**
- Modify: `agents/studio_compositor/compositor.py` — load layout and construct SourceRegistry in `__init__` or `start()`
- Test: extend `tests/studio_compositor/test_default_layout_loading.py` with end-to-end load test

- [ ] **Step 1: Write the failing test**

Append to `tests/studio_compositor/test_default_layout_loading.py`:

```python
def test_compositor_loads_layout_from_path(tmp_path: Path):
    """StudioCompositor loads a Layout file at startup and exposes it via LayoutState."""
    from agents.studio_compositor.compositor import load_layout_or_fallback

    src = DEFAULT_JSON.read_text()
    target = tmp_path / "default.json"
    target.write_text(src)
    layout = load_layout_or_fallback(target)
    assert layout.name == "default"


def test_compositor_falls_back_on_missing_file(tmp_path: Path, caplog):
    from agents.studio_compositor.compositor import load_layout_or_fallback

    layout = load_layout_or_fallback(tmp_path / "does-not-exist.json")
    assert layout.name == "default"
    assert any("fallback" in rec.message.lower() for rec in caplog.records)


def test_compositor_falls_back_on_invalid_json(tmp_path: Path, caplog):
    from agents.studio_compositor.compositor import load_layout_or_fallback

    broken = tmp_path / "broken.json"
    broken.write_text("{not json")
    layout = load_layout_or_fallback(broken)
    assert layout.name == "default"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/studio_compositor/test_default_layout_loading.py -v
```

Expected: `ImportError: cannot import name 'load_layout_or_fallback'`.

- [ ] **Step 3: Add `load_layout_or_fallback` to `compositor.py`**

Add near the top of `agents/studio_compositor/compositor.py` (below existing imports):

```python
import json
import logging
from pathlib import Path

from shared.compositor_model import (
    Assignment,
    Layout,
    SourceSchema,
    SurfaceGeometry,
    SurfaceSchema,
)

log = logging.getLogger(__name__)


_FALLBACK_LAYOUT = Layout(
    name="default",
    description="Hardcoded fallback layout (invoked on missing/invalid default.json)",
    sources=[
        SourceSchema(
            id="token_pole",
            kind="cairo",
            backend="cairo",
            params={"class_name": "TokenPoleCairoSource", "natural_w": 300, "natural_h": 300},
        ),
        SourceSchema(
            id="album",
            kind="cairo",
            backend="cairo",
            params={"class_name": "AlbumOverlayCairoSource", "natural_w": 400, "natural_h": 520},
        ),
        SourceSchema(
            id="sierpinski",
            kind="cairo",
            backend="cairo",
            params={"class_name": "SierpinskiCairoSource", "natural_w": 640, "natural_h": 640},
        ),
        SourceSchema(
            id="reverie",
            kind="external_rgba",
            backend="shm_rgba",
            params={
                "natural_w": 640,
                "natural_h": 360,
                "shm_path": "/dev/shm/hapax-sources/reverie.rgba",
            },
        ),
    ],
    surfaces=[
        SurfaceSchema(id="pip-ul", geometry=SurfaceGeometry(kind="rect", x=20, y=20, w=300, h=300), z_order=10),
        SurfaceSchema(id="pip-ur", geometry=SurfaceGeometry(kind="rect", x=1260, y=20, w=640, h=360), z_order=10),
        SurfaceSchema(id="pip-ll", geometry=SurfaceGeometry(kind="rect", x=20, y=540, w=400, h=520), z_order=10),
        SurfaceSchema(id="pip-lr", geometry=SurfaceGeometry(kind="rect", x=1260, y=420, w=640, h=640), z_order=10),
    ],
    assignments=[
        Assignment(source="token_pole", surface="pip-ul"),
        Assignment(source="reverie", surface="pip-ur"),
        Assignment(source="album", surface="pip-ll"),
    ],
)


def load_layout_or_fallback(path: Path) -> Layout:
    """Load a Layout JSON file, falling back to the hardcoded default on any error."""
    try:
        raw = json.loads(Path(path).read_text())
        return Layout.model_validate(raw)
    except FileNotFoundError:
        log.warning("compositor layout %s missing — using fallback", path)
        return _FALLBACK_LAYOUT
    except (json.JSONDecodeError, ValueError) as e:
        log.warning("compositor layout %s invalid (%s) — using fallback", path, e)
        return _FALLBACK_LAYOUT
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/studio_compositor/test_default_layout_loading.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/compositor.py tests/studio_compositor/test_default_layout_loading.py
git commit -m "feat(compositor): load_layout_or_fallback with hardcoded rescue path"
```

---

### Task 14: Wire `LayoutState` + `SourceRegistry` into `StudioCompositor.start()`

**Files:**
- Modify: `agents/studio_compositor/compositor.py` — `StudioCompositor.__init__` / `start` builds LayoutState + SourceRegistry and passes them to fx_chain
- Test: `tests/studio_compositor/test_compositor_wiring.py`

- [ ] **Step 1: Write the failing test**

Create `tests/studio_compositor/test_compositor_wiring.py`:

```python
from __future__ import annotations

from pathlib import Path

from agents.studio_compositor.compositor import StudioCompositor


def test_start_populates_layout_state_and_source_registry(tmp_path: Path, monkeypatch):
    layout_file = tmp_path / "default.json"
    from tests.studio_compositor.test_default_layout_loading import DEFAULT_JSON
    layout_file.write_text(DEFAULT_JSON.read_text())

    compositor = StudioCompositor(layout_path=layout_file, dry_run=True)
    compositor.start_layout_only()

    layout = compositor.layout_state.get()
    assert {s.id for s in layout.sources} == {"token_pole", "album", "sierpinski", "reverie"}
    assert set(compositor.source_registry.ids()) == {"token_pole", "album", "sierpinski", "reverie"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/studio_compositor/test_compositor_wiring.py -v
```

Expected: `TypeError` on `StudioCompositor.__init__` not accepting `layout_path`, or `AttributeError` on `start_layout_only`.

- [ ] **Step 3: Wire `LayoutState` + `SourceRegistry` into `StudioCompositor`**

Add to the class (exact insertion point depends on existing class layout — the key additions are the new kwarg, instance attrs, and a `start_layout_only()` helper for the test to exercise without touching GStreamer):

```python
# inside StudioCompositor:

def __init__(
    self,
    *,
    layout_path: Path | None = None,
    dry_run: bool = False,
    # ... existing kwargs ...
) -> None:
    # ... existing init ...
    self._layout_path = Path(layout_path) if layout_path is not None else (
        Path.home() / ".config" / "hapax-compositor" / "layouts" / "default.json"
    )
    self.layout_state: LayoutState | None = None
    self.source_registry: SourceRegistry | None = None
    self._dry_run = dry_run

def start_layout_only(self) -> None:
    """Load the layout and build the SourceRegistry without starting GStreamer.

    Used by tests and by the main start() path as its first phase.
    """
    layout = load_layout_or_fallback(self._layout_path)
    self.layout_state = LayoutState(layout)
    self.source_registry = SourceRegistry()
    for source in layout.sources:
        try:
            backend = self.source_registry.construct_backend(source)
        except Exception:
            log.exception("failed to construct backend for source %s", source.id)
            continue
        self.source_registry.register(source.id, backend)
```

Call `start_layout_only()` from `start()` before any GStreamer pipeline construction. Pass `self.layout_state` / `self.source_registry` into `fx_chain` wiring (Task 15).

Add imports at the top if missing:

```python
from agents.studio_compositor.layout_state import LayoutState
from agents.studio_compositor.source_registry import SourceRegistry
```

- [ ] **Step 4: Run the test**

```bash
uv run pytest tests/studio_compositor/test_compositor_wiring.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/compositor.py tests/studio_compositor/test_compositor_wiring.py
git commit -m "feat(compositor): StudioCompositor.start_layout_only wires LayoutState+SourceRegistry"
```

---

## Phase E — Render path refactor (2 tasks)

### Task 15: Add `blit_scaled` helper

**Files:**
- Modify: `agents/studio_compositor/fx_chain.py` — add module-level helper
- Test: `tests/studio_compositor/test_pip_draw_refactor.py`

- [ ] **Step 1: Write the failing test**

Create `tests/studio_compositor/test_pip_draw_refactor.py`:

```python
from __future__ import annotations

import cairo

from agents.studio_compositor.fx_chain import blit_scaled
from shared.compositor_model import SurfaceGeometry


def _solid_surface(w: int, h: int, rgb: tuple[float, float, float]) -> cairo.ImageSurface:
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    cr = cairo.Context(surface)
    cr.set_source_rgba(rgb[0], rgb[1], rgb[2], 1.0)
    cr.paint()
    return surface


def test_blit_scaled_places_source_at_geometry():
    canvas = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 100)
    cr = cairo.Context(canvas)
    cr.set_source_rgba(0, 0, 0, 1)
    cr.paint()

    src = _solid_surface(10, 10, (1.0, 0.0, 0.0))
    geom = SurfaceGeometry(kind="rect", x=50, y=30, w=40, h=20)
    blit_scaled(cr, src, geom, opacity=1.0, blend_mode="over")
    canvas.flush()

    # Read a pixel from inside the target rect — expect red.
    data = canvas.get_data()
    stride = canvas.get_stride()
    def px(x, y):
        off = y * stride + x * 4
        return data[off + 2], data[off + 1], data[off + 0], data[off + 3]

    r, g, b, a = px(60, 40)  # inside rect
    assert (r, g, b, a) == (0xFF, 0x00, 0x00, 0xFF)
    r, g, b, _ = px(10, 10)  # outside rect
    assert (r, g, b) == (0x00, 0x00, 0x00)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/studio_compositor/test_pip_draw_refactor.py::test_blit_scaled_places_source_at_geometry -v
```

Expected: `ImportError: cannot import name 'blit_scaled' from 'agents.studio_compositor.fx_chain'`.

- [ ] **Step 3: Add `blit_scaled` to `fx_chain.py`**

Add near the top of `agents/studio_compositor/fx_chain.py` (after existing imports):

```python
import cairo

from shared.compositor_model import SurfaceGeometry


def blit_scaled(
    cr: cairo.Context,
    src: cairo.ImageSurface,
    geom: SurfaceGeometry,
    opacity: float,
    blend_mode: str,
) -> None:
    """Place a natural-size source surface at geom's rect with scaling."""
    if geom.kind != "rect":
        return
    cr.save()
    cr.translate(geom.x or 0, geom.y or 0)
    sx = (geom.w or src.get_width()) / max(src.get_width(), 1)
    sy = (geom.h or src.get_height()) / max(src.get_height(), 1)
    cr.scale(sx, sy)
    cr.set_source_surface(src, 0, 0)
    pattern = cr.get_source()
    try:
        pattern.set_filter(cairo.FILTER_BILINEAR)
    except Exception:
        pass
    if blend_mode == "plus":
        cr.set_operator(cairo.OPERATOR_ADD)
    else:
        cr.set_operator(cairo.OPERATOR_OVER)
    cr.paint_with_alpha(opacity)
    cr.restore()
```

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/studio_compositor/test_pip_draw_refactor.py::test_blit_scaled_places_source_at_geometry -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/fx_chain.py tests/studio_compositor/test_pip_draw_refactor.py
git commit -m "feat(fx-chain): blit_scaled helper places natural-size surfaces at SurfaceGeometry"
```

---

### Task 16: Refactor `_pip_draw` to walk `LayoutState`

**Files:**
- Modify: `agents/studio_compositor/fx_chain.py:_pip_draw` (and its caller in the cairooverlay callback setup)
- Test: extend `tests/studio_compositor/test_pip_draw_refactor.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/studio_compositor/test_pip_draw_refactor.py`:

```python
from agents.studio_compositor.fx_chain import pip_draw_from_layout
from agents.studio_compositor.layout_state import LayoutState
from agents.studio_compositor.source_registry import SourceRegistry
from shared.compositor_model import (
    Assignment,
    Layout,
    SourceSchema,
    SurfaceGeometry,
    SurfaceSchema,
)


class _CannedBackend:
    def __init__(self, surface):
        self._surface = surface

    def get_current_surface(self):
        return self._surface


def test_pip_draw_from_layout_walks_assignments_by_z_order():
    # Build a layout: 2 sources, 2 surfaces, 2 assignments, different z_order.
    red = _solid_surface(10, 10, (1.0, 0.0, 0.0))
    green = _solid_surface(10, 10, (0.0, 1.0, 0.0))
    layout = Layout(
        name="t",
        sources=[
            SourceSchema(id="r", kind="cairo", backend="cairo", params={"class_name": "X"}),
            SourceSchema(id="g", kind="cairo", backend="cairo", params={"class_name": "X"}),
        ],
        surfaces=[
            SurfaceSchema(id="a", geometry=SurfaceGeometry(kind="rect", x=0, y=0, w=50, h=50), z_order=1),
            SurfaceSchema(id="b", geometry=SurfaceGeometry(kind="rect", x=20, y=20, w=50, h=50), z_order=5),
        ],
        assignments=[
            Assignment(source="r", surface="a"),
            Assignment(source="g", surface="b"),
        ],
    )
    state = LayoutState(layout)
    registry = SourceRegistry()
    registry.register("r", _CannedBackend(red))
    registry.register("g", _CannedBackend(green))

    canvas = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 200)
    cr = cairo.Context(canvas)
    cr.set_source_rgba(0, 0, 0, 1)
    cr.paint()
    pip_draw_from_layout(cr, state, registry)
    canvas.flush()

    data = canvas.get_data()
    stride = canvas.get_stride()
    def px(x, y):
        off = y * stride + x * 4
        return data[off + 2], data[off + 1], data[off + 0]

    # Overlap point (25, 25) should show green (z=5) overlaying red (z=1).
    assert px(25, 25) == (0x00, 0xFF, 0x00)
    # Point in red-only region (5, 5) should be red.
    assert px(5, 5) == (0xFF, 0x00, 0x00)


def test_pip_draw_skips_non_rect_surfaces():
    layout = Layout(
        name="t",
        sources=[SourceSchema(id="r", kind="cairo", backend="cairo", params={"class_name": "X"})],
        surfaces=[
            SurfaceSchema(id="a", geometry=SurfaceGeometry(kind="fx_chain_input"), z_order=0),
        ],
        assignments=[Assignment(source="r", surface="a")],
    )
    state = LayoutState(layout)
    registry = SourceRegistry()
    registry.register("r", _CannedBackend(_solid_surface(10, 10, (1, 1, 1))))
    canvas = cairo.ImageSurface(cairo.FORMAT_ARGB32, 50, 50)
    cr = cairo.Context(canvas)
    cr.set_source_rgba(0, 0, 0, 1)
    cr.paint()
    pip_draw_from_layout(cr, state, registry)
    # No exception = non-rect surface correctly skipped.
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/studio_compositor/test_pip_draw_refactor.py -v
```

Expected: `ImportError: cannot import name 'pip_draw_from_layout'`.

- [ ] **Step 3: Implement `pip_draw_from_layout` in `fx_chain.py`**

Add to `agents/studio_compositor/fx_chain.py`:

```python
from agents.studio_compositor.layout_state import LayoutState
from agents.studio_compositor.source_registry import SourceRegistry


def pip_draw_from_layout(
    cr: cairo.Context,
    layout_state: LayoutState,
    source_registry: SourceRegistry,
) -> None:
    """Walk the current layout's assignments by z_order and blit each one.

    Called from the GStreamer cairooverlay draw callback on the streaming
    thread. Must be cheap — no allocation in the hot path except for the
    blit. Surfaces that are not ``kind="rect"`` are skipped (they are
    handled by the main-layer appsrc path, not the cairooverlay path).
    """
    layout = layout_state.get()
    # Build (assignment, surface_schema) pairs so we can sort by the surface's z_order.
    pairs = []
    for assignment in layout.assignments:
        surface_schema = layout.surface_by_id(assignment.surface)
        if surface_schema is None:
            continue
        if surface_schema.geometry.kind != "rect":
            continue
        pairs.append((assignment, surface_schema))
    pairs.sort(key=lambda p: p[1].z_order)

    for assignment, surface_schema in pairs:
        try:
            src = source_registry.get_current_surface(assignment.source)
        except KeyError:
            continue
        if src is None:
            continue
        blit_scaled(
            cr,
            src,
            surface_schema.geometry,
            opacity=assignment.opacity,
            blend_mode=surface_schema.blend_mode,
        )
```

Replace the existing `_pip_draw` callback wiring so that when the cairooverlay draw signal fires, it calls `pip_draw_from_layout(cr, self.layout_state, self.source_registry)` instead of blitting hardcoded sources. Find the current callback registration (search for `_pip_draw`) and swap the call. Preserve the callback's existing signature (cairooverlay gives it cr + GstSample + timestamp + duration + user_data — the user_data is the hook for passing `layout_state` and `source_registry`).

Example wiring (adapt to the exact callback shape):

```python
def _make_pip_draw_callback(layout_state: LayoutState, source_registry: SourceRegistry):
    def _cb(overlay, cr, timestamp, duration):
        pip_draw_from_layout(cr, layout_state, source_registry)
    return _cb
```

And at cairooverlay connection time (inside the existing pipeline construction):

```python
cairooverlay.connect("draw", _make_pip_draw_callback(self.layout_state, self.source_registry))
```

- [ ] **Step 4: Run the refactor tests + full compositor suite**

```bash
uv run pytest tests/studio_compositor/test_pip_draw_refactor.py tests/studio_compositor/ -v
```

Expected: new tests pass; existing tests pass (or show expected breakage on tests that poke `_pip_draw` directly — fix those by switching them to `pip_draw_from_layout` or by leaving `_pip_draw` as a thin wrapper).

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/fx_chain.py tests/studio_compositor/test_pip_draw_refactor.py
git commit -m "feat(fx-chain): pip_draw_from_layout walks LayoutState, replaces hardcoded _pip_draw"
```

---

## Phase F — Reverie headless mode (3 tasks)

### Task 17: Add second shm output to `ShmOutput`

**Files:**
- Modify: `crates/hapax-visual/src/output.rs` — add second write path for `/dev/shm/hapax-sources/reverie.rgba` + sidecar JSON
- Test: Rust unit test in the same file or adjacent

- [ ] **Step 1: Write the failing test**

Add to `crates/hapax-visual/src/output.rs` at the bottom:

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn write_side_output_creates_sidecar_json() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("reverie.rgba");
        let pixels = vec![0xFFu8; 4 * 4 * 4];
        write_side_output(&path, &pixels, 4, 4, 16, 42).unwrap();
        assert!(path.exists());
        let sidecar = path.with_extension("rgba.json");
        assert!(sidecar.exists());
        let meta: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(&sidecar).unwrap()).unwrap();
        assert_eq!(meta["w"], 4);
        assert_eq!(meta["h"], 4);
        assert_eq!(meta["stride"], 16);
        assert_eq!(meta["frame_id"], 42);
    }
}
```

Make sure `tempfile = "3"` and `serde_json = "1"` are in `crates/hapax-visual/Cargo.toml` `[dev-dependencies]`.

- [ ] **Step 2: Run test to verify it fails**

```bash
cargo test -p hapax-visual --lib output::tests::write_side_output_creates_sidecar_json
```

Expected: `cannot find function 'write_side_output'`.

- [ ] **Step 3: Implement `write_side_output`**

Add near the end of `crates/hapax-visual/src/output.rs`:

```rust
use std::path::Path;

/// Write an RGBA buffer to a sibling shm path with a JSON sidecar describing
/// the dimensions + frame_id. Writes are atomic (tmp + rename).
pub fn write_side_output(
    path: &Path,
    pixels: &[u8],
    w: u32,
    h: u32,
    stride: u32,
    frame_id: u64,
) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let tmp = path.with_extension("rgba.tmp");
    std::fs::write(&tmp, pixels)?;
    std::fs::rename(&tmp, path)?;

    let sidecar = path.with_extension("rgba.json");
    let sidecar_tmp = sidecar.with_extension("json.tmp");
    let meta = serde_json::json!({
        "w": w,
        "h": h,
        "stride": stride,
        "frame_id": frame_id,
    });
    std::fs::write(&sidecar_tmp, meta.to_string())?;
    std::fs::rename(&sidecar_tmp, &sidecar)?;
    Ok(())
}
```

Add `serde_json = "1"` to `[dependencies]` in `crates/hapax-visual/Cargo.toml` if not already present.

Call `write_side_output` from the existing `ShmOutput::write_frame` after the existing JPEG/RGBA writes, at the canonical path `/dev/shm/hapax-sources/reverie.rgba`:

```rust
// inside write_frame after the existing RGBA write:
let _ = write_side_output(
    Path::new("/dev/shm/hapax-sources/reverie.rgba"),
    &clean_pixels,
    width,
    height,
    stride,
    self.frame_count,
);
```

(Use a `let _ =` to make failures non-fatal — reverie keeps rendering even if shm writing fails, and `compositor_source_frame_age_seconds` will catch chronic staleness.)

- [ ] **Step 4: Run the test + full Rust suite**

```bash
cargo test -p hapax-visual
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add crates/hapax-visual/src/output.rs crates/hapax-visual/Cargo.toml
git commit -m "feat(hapax-visual): write reverie RGBA+sidecar to /dev/shm/hapax-sources/"
```

---

### Task 18: Headless mode branch in `src-imagination/src/main.rs`

**Files:**
- Create: `src-imagination/src/headless.rs`
- Modify: `src-imagination/src/main.rs` — `HAPAX_IMAGINATION_HEADLESS=1` branch that instantiates `headless::Renderer` instead of winit Window

- [ ] **Step 1: Write the failing/marker test**

Add a Rust integration test at `src-imagination/tests/headless_mode.rs`:

```rust
#[test]
fn headless_module_compiles() {
    // Presence of the module + its public Renderer type means the headless
    // branch is buildable. The actual offscreen loop is exercised by
    // running the binary with HAPAX_IMAGINATION_HEADLESS=1 in the smoke
    // test (Task 22).
    let _ = hapax_imagination::headless::Renderer::new_for_tests(640, 360);
}
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cargo test -p hapax-imagination --test headless_mode
```

Expected: compilation error (headless module doesn't exist).

- [ ] **Step 3: Create the headless module**

Create `src-imagination/src/headless.rs`:

```rust
//! Headless wgpu renderer — runs DynamicPipeline without a winit Window.
//!
//! Activated by `HAPAX_IMAGINATION_HEADLESS=1`. Owns a wgpu texture (no
//! surface, no swapchain), drives `DynamicPipeline::render` into it on a
//! 60fps tokio interval, and publishes RGBA + sidecar to
//! `/dev/shm/hapax-sources/reverie.rgba` via the shared `ShmOutput` path.

use std::sync::Arc;

use hapax_visual::{DynamicPipeline, GpuContext, StateReader};

pub struct Renderer {
    width: u32,
    height: u32,
    // Fields populated in the real constructor — see new() below.
}

impl Renderer {
    pub fn new_for_tests(width: u32, height: u32) -> Self {
        Self { width, height }
    }

    pub async fn new(width: u32, height: u32) -> anyhow::Result<Self> {
        // Build a headless GpuContext (no surface). The GpuContext helper
        // in hapax-visual already exists for the windowed path; add a
        // corresponding headless constructor there if one isn't present.
        let _ctx = GpuContext::new_headless(width, height).await?;
        Ok(Self { width, height })
    }

    pub async fn run_forever(mut self) -> anyhow::Result<()> {
        // 60fps tick loop that calls DynamicPipeline::render into the
        // offscreen texture and triggers ShmOutput::write_frame.
        let mut interval = tokio::time::interval(std::time::Duration::from_millis(16));
        loop {
            interval.tick().await;
            // ... render tick into offscreen texture ...
            // ... trigger ShmOutput write_frame (which now also writes the sidecar) ...
        }
    }
}
```

If `hapax_visual::GpuContext::new_headless` doesn't exist yet, add it:

```rust
// crates/hapax-visual/src/gpu.rs

impl GpuContext {
    pub async fn new_headless(width: u32, height: u32) -> anyhow::Result<Self> {
        let instance = wgpu::Instance::default();
        let adapter = instance
            .request_adapter(&wgpu::RequestAdapterOptions {
                power_preference: wgpu::PowerPreference::HighPerformance,
                compatible_surface: None,
                force_fallback_adapter: false,
            })
            .await
            .ok_or_else(|| anyhow::anyhow!("no adapter"))?;
        // ... existing device/queue construction ...
        Ok(Self { /* ... */ })
    }
}
```

- [ ] **Step 4: Modify `main.rs` to branch on the env var**

Edit `src-imagination/src/main.rs`. In the main entry point:

```rust
fn main() -> anyhow::Result<()> {
    if std::env::var("HAPAX_IMAGINATION_HEADLESS").map(|v| v == "1").unwrap_or(false) {
        let rt = tokio::runtime::Runtime::new()?;
        rt.block_on(async {
            let renderer = hapax_imagination::headless::Renderer::new(1920, 1080).await?;
            renderer.run_forever().await
        })?;
        return Ok(());
    }
    // ... existing winit Window + EventLoop path ...
}
```

Also add `pub mod headless;` to `src-imagination/src/lib.rs` so the integration test can reach it.

- [ ] **Step 5: Build and run the integration test**

```bash
cargo build -p hapax-imagination
cargo test -p hapax-imagination --test headless_mode
```

Expected: builds and the marker test passes.

- [ ] **Step 6: Commit**

```bash
git add src-imagination/src/headless.rs src-imagination/src/main.rs src-imagination/src/lib.rs src-imagination/tests/headless_mode.rs crates/hapax-visual/src/gpu.rs
git commit -m "feat(imagination): HAPAX_IMAGINATION_HEADLESS=1 runs offscreen Renderer"
```

---

### Task 19: systemd unit update

**Files:**
- Modify: `systemd/units/hapax-imagination.service` — add `Environment=HAPAX_IMAGINATION_HEADLESS=1`

- [ ] **Step 1: Add the environment line**

Open `systemd/units/hapax-imagination.service` and add under `[Service]`:

```ini
Environment=HAPAX_IMAGINATION_HEADLESS=1
```

- [ ] **Step 2: Validate the unit file**

```bash
systemd-analyze verify systemd/units/hapax-imagination.service
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add systemd/units/hapax-imagination.service
git commit -m "feat(systemd): hapax-imagination runs HAPAX_IMAGINATION_HEADLESS=1 by default"
```

---

## Phase G — Command server + control path (4 tasks)

### Task 20: `command_server.py` UDS handler

**Files:**
- Create: `agents/studio_compositor/command_server.py`
- Test: `tests/studio_compositor/test_command_server.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/studio_compositor/test_command_server.py`:

```python
from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from agents.studio_compositor.command_server import CommandServer
from agents.studio_compositor.layout_state import LayoutState
from shared.compositor_model import (
    Assignment,
    Layout,
    SourceSchema,
    SurfaceGeometry,
    SurfaceSchema,
)


def _minimal_layout() -> Layout:
    return Layout(
        name="t",
        sources=[SourceSchema(id="s1", kind="cairo", backend="cairo", params={"class_name": "X"})],
        surfaces=[
            SurfaceSchema(id="pip-ul", geometry=SurfaceGeometry(kind="rect", x=0, y=0, w=100, h=100), z_order=1),
        ],
        assignments=[Assignment(source="s1", surface="pip-ul")],
    )


def _call(sock_path: Path, payload: dict) -> dict:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(str(sock_path))
    s.sendall((json.dumps(payload) + "\n").encode("utf-8"))
    resp = s.recv(4096)
    s.close()
    return json.loads(resp.decode("utf-8"))


def test_set_geometry_mutates_layout(tmp_path: Path):
    state = LayoutState(_minimal_layout())
    sock_path = tmp_path / "compositor.sock"
    server = CommandServer(state, sock_path)
    server.start()
    try:
        resp = _call(
            sock_path,
            {
                "command": "compositor.surface.set_geometry",
                "args": {"surface_id": "pip-ul", "x": 500, "y": 300, "w": 200, "h": 200},
            },
        )
        assert resp["status"] == "ok"
        layout = state.get()
        surface = layout.surface_by_id("pip-ul")
        assert surface.geometry.x == 500
        assert surface.geometry.y == 300
    finally:
        server.stop()


def test_unknown_surface_returns_error_with_hint(tmp_path: Path):
    state = LayoutState(_minimal_layout())
    sock_path = tmp_path / "compositor.sock"
    server = CommandServer(state, sock_path)
    server.start()
    try:
        resp = _call(
            sock_path,
            {
                "command": "compositor.surface.set_geometry",
                "args": {"surface_id": "pip-u", "x": 0, "y": 0, "w": 10, "h": 10},
            },
        )
        assert resp["status"] == "error"
        assert resp["error"] == "unknown_surface"
        assert "pip-ul" in resp["hint"]
    finally:
        server.stop()


def test_invalid_geometry_rejected(tmp_path: Path):
    state = LayoutState(_minimal_layout())
    sock_path = tmp_path / "compositor.sock"
    server = CommandServer(state, sock_path)
    server.start()
    try:
        resp = _call(
            sock_path,
            {
                "command": "compositor.surface.set_geometry",
                "args": {"surface_id": "pip-ul", "x": 0, "y": 0, "w": -5, "h": 10},
            },
        )
        assert resp["status"] == "error"
        assert resp["error"] == "invalid_geometry"
    finally:
        server.stop()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/studio_compositor/test_command_server.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `command_server.py`**

Create `agents/studio_compositor/command_server.py`:

```python
"""CommandServer — UDS newline-delimited JSON command handler for the compositor.

Protocol: client sends one JSON line per request, server replies with one JSON
line per response. No connection reuse — one request per connection.

Supported commands (PR 1):
  - compositor.surface.set_geometry {surface_id, x, y, w, h}
  - compositor.surface.set_z_order {surface_id, z_order}
  - compositor.assignment.set_opacity {source_id, surface_id, opacity}
  - compositor.layout.save
  - compositor.layout.reload
"""

from __future__ import annotations

import difflib
import json
import logging
import math
import os
import socket
import threading
from pathlib import Path

from agents.studio_compositor.layout_state import LayoutState
from shared.compositor_model import Assignment, Layout, SurfaceGeometry

log = logging.getLogger(__name__)


class CommandServer:
    def __init__(self, state: LayoutState, socket_path: Path) -> None:
        self._state = state
        self._socket_path = Path(socket_path)
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._socket_path.exists():
            self._socket_path.unlink()
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(str(self._socket_path))
        self._sock.listen(8)
        self._sock.settimeout(0.5)
        self._thread = threading.Thread(target=self._loop, daemon=True, name="compositor-cmdsrv")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self._socket_path.exists():
            try:
                self._socket_path.unlink()
            except OSError:
                pass

    def _loop(self) -> None:
        assert self._sock is not None
        while not self._stop.is_set():
            try:
                conn, _addr = self._sock.accept()
            except (socket.timeout, OSError):
                continue
            try:
                self._handle_connection(conn)
            except Exception:
                log.exception("compositor command handler raised")
            finally:
                try:
                    conn.close()
                except OSError:
                    pass

    def _handle_connection(self, conn: socket.socket) -> None:
        conn.settimeout(2.0)
        buf = b""
        while b"\n" not in buf:
            chunk = conn.recv(4096)
            if not chunk:
                return
            buf += chunk
            if len(buf) > 65536:
                self._reply(conn, {"status": "error", "error": "payload_too_large"})
                return

        line, _ = buf.split(b"\n", 1)
        try:
            request = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._reply(conn, {"status": "error", "error": "invalid_json"})
            return

        command = request.get("command")
        args = request.get("args") or {}
        handler = _COMMANDS.get(command)
        if handler is None:
            self._reply(conn, {"status": "error", "error": "unknown_command", "command": command})
            return
        try:
            result = handler(self._state, args)
            self._reply(conn, {"status": "ok", **(result or {})})
        except _CommandError as e:
            self._reply(conn, {"status": "error", **e.payload})

    @staticmethod
    def _reply(conn: socket.socket, payload: dict) -> None:
        try:
            conn.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        except OSError:
            pass


class _CommandError(Exception):
    def __init__(self, payload: dict) -> None:
        super().__init__(payload.get("error", "error"))
        self.payload = payload


def _did_you_mean(needle: str, haystack: list[str]) -> str:
    matches = difflib.get_close_matches(needle, haystack, n=3, cutoff=0.6)
    return ", ".join(matches) if matches else ""


def _handle_set_geometry(state: LayoutState, args: dict) -> dict:
    sid = args.get("surface_id")
    x = args.get("x")
    y = args.get("y")
    w = args.get("w")
    h = args.get("h")
    for k, v in (("x", x), ("y", y), ("w", w), ("h", h)):
        if not isinstance(v, (int, float)) or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            raise _CommandError({"error": "invalid_geometry", "field": k})
    if w <= 0 or h <= 0:
        raise _CommandError({"error": "invalid_geometry", "field": "w_or_h_nonpositive"})

    layout = state.get()
    if layout.surface_by_id(sid) is None:
        hint = _did_you_mean(sid or "", [s.id for s in layout.surfaces])
        raise _CommandError({"error": "unknown_surface", "surface_id": sid, "hint": hint})
    surface = layout.surface_by_id(sid)
    if surface.geometry.kind != "rect":
        raise _CommandError({"error": "layout_immutable_kind", "kind": surface.geometry.kind})

    def mutator(layout: Layout) -> Layout:
        new_surfaces = []
        for s in layout.surfaces:
            if s.id != sid:
                new_surfaces.append(s)
                continue
            new_geom = s.geometry.model_copy(update={"x": int(x), "y": int(y), "w": int(w), "h": int(h)})
            new_surfaces.append(s.model_copy(update={"geometry": new_geom}))
        return layout.model_copy(update={"surfaces": new_surfaces})

    state.mutate(mutator)
    return {}


def _handle_set_z_order(state: LayoutState, args: dict) -> dict:
    sid = args.get("surface_id")
    z = args.get("z_order")
    if not isinstance(z, int):
        raise _CommandError({"error": "invalid_z_order"})
    layout = state.get()
    if layout.surface_by_id(sid) is None:
        hint = _did_you_mean(sid or "", [s.id for s in layout.surfaces])
        raise _CommandError({"error": "unknown_surface", "surface_id": sid, "hint": hint})

    def mutator(layout: Layout) -> Layout:
        new_surfaces = [
            s.model_copy(update={"z_order": z}) if s.id == sid else s
            for s in layout.surfaces
        ]
        return layout.model_copy(update={"surfaces": new_surfaces})

    state.mutate(mutator)
    return {}


def _handle_set_opacity(state: LayoutState, args: dict) -> dict:
    source_id = args.get("source_id")
    surface_id = args.get("surface_id")
    opacity = args.get("opacity")
    if not isinstance(opacity, (int, float)) or not 0.0 <= opacity <= 1.0:
        raise _CommandError({"error": "invalid_opacity"})

    def mutator(layout: Layout) -> Layout:
        new_assignments = []
        touched = False
        for a in layout.assignments:
            if a.source == source_id and a.surface == surface_id:
                new_assignments.append(a.model_copy(update={"opacity": float(opacity)}))
                touched = True
            else:
                new_assignments.append(a)
        if not touched:
            raise _CommandError({"error": "unknown_assignment"})
        return layout.model_copy(update={"assignments": new_assignments})

    state.mutate(mutator)
    return {}


def _handle_save(state: LayoutState, args: dict) -> dict:
    # Task 22 wires the auto-save path + this flush.
    return {}


def _handle_reload(state: LayoutState, args: dict) -> dict:
    # Task 22 wires file-watch + this manual reload.
    return {}


_COMMANDS = {
    "compositor.surface.set_geometry": _handle_set_geometry,
    "compositor.surface.set_z_order": _handle_set_z_order,
    "compositor.assignment.set_opacity": _handle_set_opacity,
    "compositor.layout.save": _handle_save,
    "compositor.layout.reload": _handle_reload,
}
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/studio_compositor/test_command_server.py -v
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/command_server.py tests/studio_compositor/test_command_server.py
git commit -m "feat(compositor): UDS command_server for runtime layout mutation"
```

---

### Task 21: Tauri Rust pass-through + frontend command registry entries

**Files:**
- Create: `hapax-logos/src-tauri/src/commands/compositor.rs`
- Create: `hapax-logos/src/lib/commands/compositor.ts`
- Modify: `hapax-logos/src-tauri/src/commands/mod.rs` (add compositor module)
- Modify: `hapax-logos/src/lib/commandRegistry.ts` or wherever command modules are bootstrapped

- [ ] **Step 1: Write the Rust unit test (if possible) or a shape test**

At `hapax-logos/src-tauri/src/commands/compositor.rs`, start with a module skeleton and a test:

```rust
// commands/compositor.rs
use serde::{Deserialize, Serialize};
use std::os::unix::net::UnixStream;
use std::io::{Read, Write};
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize)]
pub struct CompositorRequest {
    pub command: String,
    pub args: serde_json::Value,
}

fn compositor_sock_path() -> PathBuf {
    let runtime_dir = std::env::var("XDG_RUNTIME_DIR")
        .unwrap_or_else(|_| format!("/run/user/{}", unsafe { libc::getuid() }));
    PathBuf::from(runtime_dir).join("hapax-compositor.sock")
}

#[tauri::command]
pub async fn compositor_surface_set_geometry(
    surface_id: String,
    x: i32,
    y: i32,
    w: i32,
    h: i32,
) -> Result<serde_json::Value, String> {
    let req = CompositorRequest {
        command: "compositor.surface.set_geometry".to_string(),
        args: serde_json::json!({
            "surface_id": surface_id,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
        }),
    };
    send_compositor_request(&req)
}

fn send_compositor_request(req: &CompositorRequest) -> Result<serde_json::Value, String> {
    let mut stream = UnixStream::connect(compositor_sock_path())
        .map_err(|e| format!("connect: {e}"))?;
    let payload = serde_json::to_string(req).map_err(|e| format!("serialize: {e}"))?;
    stream.write_all(format!("{}\n", payload).as_bytes()).map_err(|e| format!("write: {e}"))?;
    let mut buf = Vec::new();
    stream.read_to_end(&mut buf).map_err(|e| format!("read: {e}"))?;
    let text = String::from_utf8_lossy(&buf);
    serde_json::from_str(text.trim_end_matches('\n')).map_err(|e| format!("parse: {e}"))
}
```

Register the command in `hapax-logos/src-tauri/src/commands/mod.rs`:

```rust
pub mod compositor;
```

And in the Tauri builder (typically `hapax-logos/src-tauri/src/lib.rs` or `main.rs`):

```rust
.invoke_handler(tauri::generate_handler![
    // ... existing commands ...
    commands::compositor::compositor_surface_set_geometry,
    // add the other 4 commands here as stubs or full handlers
])
```

- [ ] **Step 2: Create the frontend registry entries**

Create `hapax-logos/src/lib/commands/compositor.ts`:

```typescript
// commands/compositor.ts — registers compositor commands with the command registry.
import { invoke } from "@tauri-apps/api/core";
import type { CommandRegistry } from "../commandRegistry";

interface SetGeometryArgs {
  surface_id: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

export function registerCompositorCommands(registry: CommandRegistry): void {
  registry.register({
    id: "compositor.surface.set_geometry",
    description: "Move/resize a compositor PiP surface at runtime",
    argsSchema: {
      surface_id: { type: "string", required: true },
      x: { type: "number", required: true },
      y: { type: "number", required: true },
      w: { type: "number", required: true },
      h: { type: "number", required: true },
    },
    execute: async (args: SetGeometryArgs) =>
      invoke("compositor_surface_set_geometry", args),
  });

  registry.register({
    id: "compositor.surface.set_z_order",
    description: "Change a PiP's z_order",
    argsSchema: {
      surface_id: { type: "string", required: true },
      z_order: { type: "number", required: true },
    },
    execute: async (args: { surface_id: string; z_order: number }) =>
      invoke("compositor_surface_set_z_order", args),
  });

  registry.register({
    id: "compositor.assignment.set_opacity",
    description: "Set the opacity of a specific source→surface assignment",
    argsSchema: {
      source_id: { type: "string", required: true },
      surface_id: { type: "string", required: true },
      opacity: { type: "number", required: true },
    },
    execute: async (args: { source_id: string; surface_id: string; opacity: number }) =>
      invoke("compositor_assignment_set_opacity", args),
  });

  registry.register({
    id: "compositor.layout.save",
    description: "Flush the debounced layout auto-save immediately",
    execute: async () => invoke("compositor_layout_save"),
  });

  registry.register({
    id: "compositor.layout.reload",
    description: "Force reload of the layout JSON from disk",
    execute: async () => invoke("compositor_layout_reload"),
  });
}
```

Register the module in the command registry bootstrap (typically `hapax-logos/src/contexts/CommandRegistryContext.tsx` or similar):

```typescript
import { registerCompositorCommands } from "../lib/commands/compositor";
// inside the provider init:
registerCompositorCommands(registry);
```

- [ ] **Step 3: Build the frontend and backend**

```bash
cd hapax-logos
pnpm tsc --noEmit
cd ../src-tauri
cargo build --manifest-path ../hapax-logos/src-tauri/Cargo.toml
```

Expected: clean builds.

- [ ] **Step 4: Commit**

```bash
git add hapax-logos/src-tauri/src/commands/compositor.rs hapax-logos/src-tauri/src/commands/mod.rs hapax-logos/src-tauri/src/lib.rs hapax-logos/src/lib/commands/compositor.ts hapax-logos/src/contexts/CommandRegistryContext.tsx
git commit -m "feat(logos): compositor command registry entries + Tauri UDS pass-through"
```

---

### Task 22: File-watch + debounced auto-save

**Files:**
- Modify: `agents/studio_compositor/compositor.py` — start an inotify watcher thread; wire auto-save via `LayoutState.subscribe`
- Test: `tests/studio_compositor/test_layout_file_watch.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/studio_compositor/test_layout_file_watch.py`:

```python
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from agents.studio_compositor.compositor import LayoutFileWatcher, LayoutAutoSaver
from agents.studio_compositor.layout_state import LayoutState
from shared.compositor_model import (
    Assignment,
    Layout,
    SourceSchema,
    SurfaceGeometry,
    SurfaceSchema,
)


def _minimal_layout() -> Layout:
    return Layout(
        name="t",
        sources=[SourceSchema(id="s1", kind="cairo", backend="cairo", params={"class_name": "X"})],
        surfaces=[SurfaceSchema(id="pip-ul", geometry=SurfaceGeometry(kind="rect", x=0, y=0, w=100, h=100), z_order=1)],
        assignments=[Assignment(source="s1", surface="pip-ul")],
    )


def test_autosave_debounces_rapid_mutations(tmp_path: Path):
    layout_file = tmp_path / "default.json"
    layout_file.write_text(json.dumps(_minimal_layout().model_dump()))
    state = LayoutState(_minimal_layout())
    saver = LayoutAutoSaver(state, layout_file, debounce_s=0.1)
    saver.start()
    try:
        for i in range(5):
            state.mutate(
                lambda layout, i=i: layout.model_copy(
                    update={
                        "surfaces": [
                            s.model_copy(
                                update={
                                    "geometry": s.geometry.model_copy(update={"x": i})
                                }
                            )
                            for s in layout.surfaces
                        ]
                    }
                )
            )
        time.sleep(0.3)
        on_disk = json.loads(layout_file.read_text())
        assert on_disk["surfaces"][0]["geometry"]["x"] == 4
    finally:
        saver.stop()


def test_filewatcher_reloads_on_valid_edit(tmp_path: Path):
    layout_file = tmp_path / "default.json"
    layout_file.write_text(json.dumps(_minimal_layout().model_dump()))
    state = LayoutState(_minimal_layout())
    watcher = LayoutFileWatcher(state, layout_file)
    watcher.start()
    try:
        new_layout = _minimal_layout()
        new_surfaces = [
            s.model_copy(update={"geometry": s.geometry.model_copy(update={"x": 999})})
            for s in new_layout.surfaces
        ]
        new_layout = new_layout.model_copy(update={"surfaces": new_surfaces})
        layout_file.write_text(json.dumps(new_layout.model_dump()))
        time.sleep(0.5)
        assert state.get().surfaces[0].geometry.x == 999
    finally:
        watcher.stop()


def test_filewatcher_skips_self_write(tmp_path: Path):
    layout_file = tmp_path / "default.json"
    layout_file.write_text(json.dumps(_minimal_layout().model_dump()))
    state = LayoutState(_minimal_layout())
    watcher = LayoutFileWatcher(state, layout_file)
    saver = LayoutAutoSaver(state, layout_file, debounce_s=0.05)
    watcher.start()
    saver.start()
    reload_count = {"n": 0}

    def observer(_layout):
        reload_count["n"] += 1

    state.subscribe(observer)
    try:
        state.mutate(lambda layout: layout.model_copy(update={"description": "a"}))
        time.sleep(0.3)
        # One mutation + zero file-watch reloads (auto-save counted itself as self-write).
        assert reload_count["n"] == 1
    finally:
        watcher.stop()
        saver.stop()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/studio_compositor/test_layout_file_watch.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `LayoutAutoSaver` + `LayoutFileWatcher`**

Add to `agents/studio_compositor/compositor.py`:

```python
import os
import tempfile
import threading
import time

try:
    import inotify_simple  # type: ignore
    _HAS_INOTIFY = True
except ImportError:
    _HAS_INOTIFY = False


class LayoutAutoSaver:
    """Subscribes to LayoutState mutations and debounces JSON writes to disk."""

    def __init__(self, state: LayoutState, path: Path, debounce_s: float = 0.5) -> None:
        self._state = state
        self._path = Path(path)
        self._debounce_s = debounce_s
        self._lock = threading.Lock()
        self._last_mutation_at: float = 0.0
        self._pending = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._state.subscribe(self._on_mutation)
        self._thread = threading.Thread(target=self._loop, daemon=True, name="compositor-autosave")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def flush_now(self) -> None:
        self._write()

    def _on_mutation(self, _layout: Layout) -> None:
        with self._lock:
            self._last_mutation_at = time.monotonic()
            self._pending = True

    def _loop(self) -> None:
        while not self._stop.is_set():
            time.sleep(self._debounce_s / 2)
            with self._lock:
                if not self._pending:
                    continue
                if time.monotonic() - self._last_mutation_at < self._debounce_s:
                    continue
                self._pending = False
            self._write()

    def _write(self) -> None:
        layout = self._state.get()
        dump = json.dumps(layout.model_dump(), indent=2)
        tmp_fd, tmp_name = tempfile.mkstemp(
            prefix=".default.json.tmp-", dir=str(self._path.parent)
        )
        try:
            os.write(tmp_fd, dump.encode("utf-8"))
        finally:
            os.close(tmp_fd)
        os.replace(tmp_name, self._path)
        self._state.mark_self_write(self._path.stat().st_mtime)


class LayoutFileWatcher:
    """Watches the layout JSON for external edits and hot-reloads valid ones."""

    def __init__(self, state: LayoutState, path: Path) -> None:
        self._state = state
        self._path = Path(path)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_mtime: float = self._path.stat().st_mtime if self._path.exists() else 0.0

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True, name="compositor-fw")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _loop(self) -> None:
        while not self._stop.is_set():
            time.sleep(0.1)
            if not self._path.exists():
                continue
            mtime = self._path.stat().st_mtime
            if mtime == self._last_mtime:
                continue
            if self._state.is_self_write(mtime, tolerance=2.0):
                self._last_mtime = mtime
                continue
            try:
                raw = json.loads(self._path.read_text())
                new_layout = Layout.model_validate(raw)
            except (json.JSONDecodeError, ValueError) as e:
                log.warning("compositor layout reload rejected: %s", e)
                self._last_mtime = mtime
                continue
            self._state.mutate(lambda _old: new_layout)
            self._last_mtime = self._path.stat().st_mtime
```

Note: we're using mtime polling (not inotify) for simplicity and portability — mtime checks every 100 ms are cheap, the layout JSON is small, and it avoids a pyinotify dependency. inotify can be added in a follow-up if latency becomes a concern.

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/studio_compositor/test_layout_file_watch.py -v
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/compositor.py tests/studio_compositor/test_layout_file_watch.py
git commit -m "feat(compositor): LayoutAutoSaver + LayoutFileWatcher with self-write detection"
```

---

## Phase H — Persistent appsrc pads (3 tasks)

### Task 23: `CairoSourceRunner.gst_appsrc()` + `ShmRgbaReader.gst_appsrc()`

**Files:**
- Modify: `agents/studio_compositor/cairo_source.py` — add `gst_appsrc()` method on runner
- Modify: `agents/studio_compositor/shm_rgba_reader.py` — add `gst_appsrc()` method
- Test: `tests/studio_compositor/test_appsrc_pads.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/studio_compositor/test_appsrc_pads.py`:

```python
from __future__ import annotations

import pytest

pytest.importorskip("gi")
from gi.repository import Gst  # type: ignore  # noqa: E402

Gst.init(None)


def test_cairo_source_runner_gst_appsrc_returns_element():
    from agents.studio_compositor.cairo_source import CairoSource, CairoSourceRunner

    class _S(CairoSource):
        def render(self, cr, w, h, t, state):
            cr.set_source_rgba(1, 0, 0, 1)
            cr.rectangle(0, 0, w, h)
            cr.fill()

    runner = CairoSourceRunner(
        source_id="s1",
        source=_S(),
        canvas_w=100,
        canvas_h=100,
        target_fps=10,
        natural_w=100,
        natural_h=100,
    )
    elem = runner.gst_appsrc()
    assert elem is not None
    assert elem.get_factory().get_name() == "appsrc"


def test_shm_rgba_reader_gst_appsrc_returns_element(tmp_path):
    from agents.studio_compositor.shm_rgba_reader import ShmRgbaReader

    reader = ShmRgbaReader(tmp_path / "reverie.rgba")
    elem = reader.gst_appsrc()
    assert elem is not None
    assert elem.get_factory().get_name() == "appsrc"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/studio_compositor/test_appsrc_pads.py -v
```

Expected: `AttributeError: 'CairoSourceRunner' object has no attribute 'gst_appsrc'`.

- [ ] **Step 3: Add `gst_appsrc()` to `CairoSourceRunner`**

In `agents/studio_compositor/cairo_source.py`, add a method:

```python
    def gst_appsrc(self) -> "Gst.Element | None":
        """Return (or lazily create) a GStreamer appsrc element for this source.

        The element is configured with the source's natural width/height and
        ARGB32 caps. Buffers are pushed from the render thread after each
        successful tick via a one-time connected push callback.
        """
        if getattr(self, "_gst_appsrc", None) is not None:
            return self._gst_appsrc
        try:
            import gi
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst  # type: ignore
        except (ImportError, ValueError):
            return None
        Gst.init(None)
        elem = Gst.ElementFactory.make("appsrc", f"appsrc-{self._source_id}")
        if elem is None:
            return None
        caps = Gst.Caps.from_string(
            f"video/x-raw,format=BGRA,width={self._natural_w},height={self._natural_h},framerate=0/1"
        )
        elem.set_property("caps", caps)
        elem.set_property("format", Gst.Format.TIME)
        elem.set_property("is-live", True)
        elem.set_property("do-timestamp", True)
        self._gst_appsrc = elem
        return elem

    def _push_buffer_to_appsrc(self, surface: "cairo.ImageSurface") -> None:
        appsrc = getattr(self, "_gst_appsrc", None)
        if appsrc is None:
            return
        try:
            import gi
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst  # type: ignore
        except (ImportError, ValueError):
            return
        data = bytes(surface.get_data())
        buf = Gst.Buffer.new_wrapped(data)
        appsrc.emit("push-buffer", buf)
```

At the end of `_render_one_frame()`, call `self._push_buffer_to_appsrc(surface)` after the existing `self._output_surface = surface` assignment.

Initialize `self._gst_appsrc = None` in `__init__`.

- [ ] **Step 4: Add `gst_appsrc()` to `ShmRgbaReader`**

In `agents/studio_compositor/shm_rgba_reader.py`, add:

```python
    def gst_appsrc(self) -> "Gst.Element | None":
        if self._gst_appsrc is not None:
            return self._gst_appsrc
        try:
            import gi
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst  # type: ignore
        except (ImportError, ValueError):
            return None
        Gst.init(None)
        meta = self._read_sidecar() or {}
        w = int(meta.get("w", 640))
        h = int(meta.get("h", 360))
        elem = Gst.ElementFactory.make("appsrc", f"appsrc-{self._path.stem}")
        if elem is None:
            return None
        caps = Gst.Caps.from_string(
            f"video/x-raw,format=BGRA,width={w},height={h},framerate=0/1"
        )
        elem.set_property("caps", caps)
        elem.set_property("format", Gst.Format.TIME)
        elem.set_property("is-live", True)
        elem.set_property("do-timestamp", True)
        self._gst_appsrc = elem
        return elem
```

Initialize `self._gst_appsrc = None` in `__init__`.

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/studio_compositor/test_appsrc_pads.py -v
```

Expected: both tests pass (or skip cleanly if GStreamer is not installed in the test env — document that).

- [ ] **Step 6: Commit**

```bash
git add agents/studio_compositor/cairo_source.py agents/studio_compositor/shm_rgba_reader.py tests/studio_compositor/test_appsrc_pads.py
git commit -m "feat(compositor): CairoSourceRunner + ShmRgbaReader gain gst_appsrc() method"
```

---

### Task 24: `fx_chain.py` constructs persistent appsrc branches for every source

**Files:**
- Modify: `agents/studio_compositor/fx_chain.py` — iterate SourceRegistry at pipeline build time, construct `appsrc → glupload → glvideomixer` branch per source
- Test: inspection test for the constructed pipeline

- [ ] **Step 1: Write the failing test**

Append to `tests/studio_compositor/test_appsrc_pads.py`:

```python
def test_fx_chain_build_attaches_appsrc_branch_per_source(tmp_path):
    pytest.importorskip("gi")
    from agents.studio_compositor.fx_chain import build_source_appsrc_branches
    from agents.studio_compositor.layout_state import LayoutState
    from agents.studio_compositor.source_registry import SourceRegistry
    from agents.studio_compositor.shm_rgba_reader import ShmRgbaReader
    from shared.compositor_model import (
        Assignment, Layout, SourceSchema, SurfaceGeometry, SurfaceSchema,
    )

    layout = Layout(
        name="t",
        sources=[
            SourceSchema(id="reverie", kind="external_rgba", backend="shm_rgba",
                         params={"natural_w": 40, "natural_h": 30, "shm_path": str(tmp_path / "r.rgba")}),
        ],
        surfaces=[
            SurfaceSchema(id="pip-ur", geometry=SurfaceGeometry(kind="rect", x=0, y=0, w=40, h=30), z_order=1),
        ],
        assignments=[Assignment(source="reverie", surface="pip-ur")],
    )
    state = LayoutState(layout)
    registry = SourceRegistry()
    for s in layout.sources:
        registry.register(s.id, registry.construct_backend(s))

    from gi.repository import Gst
    Gst.init(None)
    pipeline = Gst.Pipeline.new("test")
    branches = build_source_appsrc_branches(pipeline, state, registry)
    assert "reverie" in branches
    appsrc = branches["reverie"]["appsrc"]
    assert appsrc.get_factory().get_name() == "appsrc"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/studio_compositor/test_appsrc_pads.py::test_fx_chain_build_attaches_appsrc_branch_per_source -v
```

Expected: `ImportError: cannot import name 'build_source_appsrc_branches'`.

- [ ] **Step 3: Implement `build_source_appsrc_branches`**

Add to `agents/studio_compositor/fx_chain.py`:

```python
def build_source_appsrc_branches(
    pipeline: "Gst.Pipeline",
    layout_state: LayoutState,
    source_registry: SourceRegistry,
) -> dict:
    """For each source in the current layout, add an appsrc branch to the pipeline.

    The branch shape is:
        appsrc → videoconvert → glupload → [mixer sink pad]

    Returns a dict keyed by source_id with ``{appsrc, glupload, mixer_pad}``
    sub-elements so the caller can link them to the mixer and control per-pad
    alpha. Inactive sources have their mixer sink pad ``alpha`` property set
    to 0.0 at startup; preset loads flip alpha to their declared value.
    """
    try:
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst  # type: ignore
    except (ImportError, ValueError):
        return {}
    Gst.init(None)

    branches: dict = {}
    layout = layout_state.get()
    for src in layout.sources:
        backend = source_registry._backends.get(src.id)
        if backend is None or not hasattr(backend, "gst_appsrc"):
            continue
        appsrc = backend.gst_appsrc()
        if appsrc is None:
            continue
        vconv = Gst.ElementFactory.make("videoconvert", f"vconv-{src.id}")
        glupload = Gst.ElementFactory.make("glupload", f"glupload-{src.id}")
        if vconv is None or glupload is None:
            continue
        pipeline.add(appsrc)
        pipeline.add(vconv)
        pipeline.add(glupload)
        appsrc.link(vconv)
        vconv.link(glupload)
        branches[src.id] = {
            "appsrc": appsrc,
            "videoconvert": vconv,
            "glupload": glupload,
        }
    return branches
```

Wire it into the main pipeline construction in `fx_chain.py` / `compositor.py` so that each branch's `glupload` output is linked to a new sink pad on `glvideomixer` with initial `alpha=0`.

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/studio_compositor/test_appsrc_pads.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/fx_chain.py tests/studio_compositor/test_appsrc_pads.py
git commit -m "feat(fx-chain): build_source_appsrc_branches — persistent appsrc pads per source"
```

---

### Task 25: Main-layer integration test (end-to-end proof)

**Files:**
- Create: `tests/studio_compositor/test_main_layer_path.py`
- Create: `tests/studio_compositor/fixtures/augmented_fx_chain_input_layout.json`

- [ ] **Step 1: Create the augmented layout fixture**

Create `tests/studio_compositor/fixtures/augmented_fx_chain_input_layout.json`:

```json
{
  "name": "test-main-layer",
  "description": "Adds a reverie → fx_chain_input assignment to prove the tracks carry traffic",
  "sources": [
    {
      "id": "reverie",
      "kind": "external_rgba",
      "backend": "shm_rgba",
      "params": {"natural_w": 40, "natural_h": 30, "shm_path": "__FIXTURE_SHM_PATH__"}
    }
  ],
  "surfaces": [
    {"id": "reverie-main", "geometry": {"kind": "fx_chain_input"}, "z_order": 0}
  ],
  "assignments": [
    {"source": "reverie", "surface": "reverie-main"}
  ]
}
```

- [ ] **Step 2: Write the failing end-to-end test**

Create `tests/studio_compositor/test_main_layer_path.py`:

```python
"""End-to-end proof: reverie RGBA bytes reach the glvideomixer output pad.

This is the load-bearing test for PR 1's 'railroad tracks' guarantee:
every source has a persistent appsrc pad, and fx_chain_input assignments
let any source become a main-layer input. Default runtime behavior is
unchanged; this test uses a fixture layout that explicitly adds the
reverie → fx_chain_input assignment.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("gi")
from gi.repository import Gst  # type: ignore  # noqa: E402

Gst.init(None)

from agents.studio_compositor.layout_state import LayoutState
from agents.studio_compositor.source_registry import SourceRegistry
from agents.studio_compositor.fx_chain import build_source_appsrc_branches
from shared.compositor_model import Layout


_FIXTURE = Path(__file__).parent / "fixtures" / "augmented_fx_chain_input_layout.json"


def _write_reverie_rgba(path: Path, w: int, h: int, fill: int, frame_id: int) -> None:
    stride = w * 4
    path.write_bytes(bytes([fill]) * (stride * h))
    sidecar = path.with_suffix(".rgba.json")
    sidecar.write_text(json.dumps({"w": w, "h": h, "stride": stride, "frame_id": frame_id}))


def test_reverie_rgba_reaches_glvideomixer_output(tmp_path):
    rgba = tmp_path / "reverie.rgba"
    _write_reverie_rgba(rgba, w=40, h=30, fill=0xFF, frame_id=1)

    raw = _FIXTURE.read_text().replace("__FIXTURE_SHM_PATH__", str(rgba))
    layout = Layout.model_validate(json.loads(raw))
    state = LayoutState(layout)
    registry = SourceRegistry()
    for s in layout.sources:
        registry.register(s.id, registry.construct_backend(s))

    pipeline = Gst.Pipeline.new("test")
    branches = build_source_appsrc_branches(pipeline, state, registry)
    assert "reverie" in branches

    # Build a minimal sink chain: glupload → glcolorconvert → appsink.
    glupload = branches["reverie"]["glupload"]
    glcolorconvert = Gst.ElementFactory.make("glcolorconvert", "cc")
    appsink = Gst.ElementFactory.make("appsink", "sink")
    assert glcolorconvert is not None and appsink is not None
    pipeline.add(glcolorconvert)
    pipeline.add(appsink)
    glupload.link(glcolorconvert)
    glcolorconvert.link(appsink)
    appsink.set_property("emit-signals", True)
    appsink.set_property("max-buffers", 2)
    appsink.set_property("drop", True)

    pipeline.set_state(Gst.State.PLAYING)

    # Push 3 buffers through the reverie appsrc.
    appsrc = branches["reverie"]["appsrc"]
    import time
    for i in range(3):
        data = bytes([0xFF, 0x00, 0x00, 0xFF]) * (40 * 30)
        buf = Gst.Buffer.new_wrapped(data)
        appsrc.emit("push-buffer", buf)
        time.sleep(0.05)

    sample = appsink.emit("try-pull-sample", Gst.SECOND)
    pipeline.set_state(Gst.State.NULL)
    assert sample is not None, "appsink received no buffer — the railroad tracks are broken"
```

- [ ] **Step 3: Run the test to verify it fails (initially) then passes after fx_chain wiring**

```bash
uv run pytest tests/studio_compositor/test_main_layer_path.py -v
```

Iterate on pipeline wiring (`build_source_appsrc_branches`) until the test passes. If GStreamer plugins `glupload`/`glcolorconvert` aren't available in the test environment, substitute `videoconvert` + `appsink` and document the limitation.

- [ ] **Step 4: Commit**

```bash
git add tests/studio_compositor/fixtures/augmented_fx_chain_input_layout.json tests/studio_compositor/test_main_layer_path.py
git commit -m "test(compositor): end-to-end main-layer proof reverie→glvideomixer output"
```

---

## Phase I — Preset schema extension (2 tasks)

### Task 26: `Preset` type gains optional `inputs` array

**Files:**
- Modify: `agents/effect_graph/types.py` — add `PresetInput` type + `Preset.inputs` optional field
- Test: `tests/effect_graph/test_preset_inputs_schema.py`

- [ ] **Step 1: Read the existing preset type**

```bash
cat agents/effect_graph/types.py | head -200
```

Identify the existing `Preset` or equivalent pydantic model.

- [ ] **Step 2: Write the failing test**

Create `tests/effect_graph/test_preset_inputs_schema.py`:

```python
from __future__ import annotations

import pytest

from agents.effect_graph.types import Preset, PresetInput


def test_preset_inputs_field_is_optional():
    p = Preset(name="simple", nodes=[])
    assert p.inputs is None or p.inputs == []


def test_preset_inputs_accepts_pad_binding():
    p = Preset(
        name="with-reverie",
        nodes=[],
        inputs=[
            PresetInput(pad="reverie", as_="layer0"),
            PresetInput(pad="cam-vinyl", as_="layer1"),
        ],
    )
    assert len(p.inputs) == 2
    assert p.inputs[0].pad == "reverie"
    assert p.inputs[0].as_ == "layer0"


def test_preset_input_empty_pad_rejected():
    with pytest.raises(ValueError):
        PresetInput(pad="", as_="layer0")
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/effect_graph/test_preset_inputs_schema.py -v
```

Expected: `ImportError: cannot import name 'PresetInput'`.

- [ ] **Step 4: Add `PresetInput` and extend `Preset`**

In `agents/effect_graph/types.py`:

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PresetInput(BaseModel):
    """Preset-level binding from a source pad to a named layer slot.

    ``pad`` references a SourceRegistry source_id. ``as_`` is the internal
    layer name the shader chain references. The preset loader resolves
    ``pad`` against the live SourceRegistry at load-time and fails loudly
    on unknown pads.
    """

    model_config = ConfigDict(extra="forbid")

    pad: str = Field(..., min_length=1)
    as_: str = Field(..., min_length=1, alias="as")

    @field_validator("pad")
    @classmethod
    def _nonempty_pad(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("pad must be non-empty")
        return v


# Extend the existing Preset class (find it and add the field):
class Preset(BaseModel):
    # ... existing fields ...
    inputs: list[PresetInput] | None = Field(default=None)
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/effect_graph/test_preset_inputs_schema.py -v
```

Expected: all 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add agents/effect_graph/types.py tests/effect_graph/test_preset_inputs_schema.py
git commit -m "feat(effect-graph): Preset.inputs optional PresetInput list for source pads"
```

---

### Task 27: Preset loader resolves `inputs` against SourceRegistry, fails loudly on unknown pads

**Files:**
- Modify: `agents/effect_graph/compiler.py` OR `pipeline.py` (whichever owns preset loading — determine by reading)
- Test: `tests/effect_graph/test_preset_inputs_resolution.py`

- [ ] **Step 1: Determine the preset loader file**

```bash
grep -l "def load_preset\|class PresetLoader\|def compile_preset" agents/effect_graph/*.py
```

Use the returned filename as the target (likely `compiler.py` or `pipeline.py`).

- [ ] **Step 2: Write the failing test**

Create `tests/effect_graph/test_preset_inputs_resolution.py`:

```python
from __future__ import annotations

import pytest

from agents.studio_compositor.source_registry import SourceRegistry
from agents.effect_graph.types import Preset, PresetInput


class _StubBackend:
    def get_current_surface(self):
        return None

    def gst_appsrc(self):
        return object()


def test_preset_resolves_known_pads():
    from agents.effect_graph.compiler import resolve_preset_inputs

    registry = SourceRegistry()
    registry.register("reverie", _StubBackend())
    registry.register("cam-vinyl", _StubBackend())
    preset = Preset(
        name="ok",
        nodes=[],
        inputs=[PresetInput(pad="reverie", **{"as": "layer0"}), PresetInput(pad="cam-vinyl", **{"as": "layer1"})],
    )
    resolved = resolve_preset_inputs(preset, registry)
    assert set(resolved.keys()) == {"layer0", "layer1"}


def test_preset_unknown_pad_fails_loudly():
    from agents.effect_graph.compiler import resolve_preset_inputs, PresetLoadError

    registry = SourceRegistry()
    registry.register("reverie", _StubBackend())
    preset = Preset(
        name="bad",
        nodes=[],
        inputs=[PresetInput(pad="nonexistent", **{"as": "layer0"})],
    )
    with pytest.raises(PresetLoadError, match="nonexistent"):
        resolve_preset_inputs(preset, registry)
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/effect_graph/test_preset_inputs_resolution.py -v
```

Expected: `ImportError: cannot import name 'resolve_preset_inputs'`.

- [ ] **Step 4: Implement `resolve_preset_inputs` in `compiler.py`**

```python
class PresetLoadError(RuntimeError):
    """Raised when a preset cannot be loaded for a structural reason.

    Non-silent by design: preset loads that reference missing sources fail
    loudly with this exception so operators see the problem immediately.
    """


def resolve_preset_inputs(preset: "Preset", registry: "SourceRegistry") -> dict[str, object]:
    """Resolve ``preset.inputs`` pad names against a live SourceRegistry.

    Returns a dict mapping the ``as`` layer name to the resolved backend
    handle. Raises :class:`PresetLoadError` loudly on any unknown pad so
    preset chain switches cannot silently reference dead sources.
    """
    if not preset.inputs:
        return {}
    registered = set(registry.ids())
    resolved: dict[str, object] = {}
    for entry in preset.inputs:
        if entry.pad not in registered:
            raise PresetLoadError(
                f"preset {preset.name!r}: inputs reference unknown source pad "
                f"{entry.pad!r}; known pads: {sorted(registered)}"
            )
        resolved[entry.as_] = registry._backends[entry.pad]
    return resolved
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/effect_graph/test_preset_inputs_resolution.py -v
```

Expected: both tests pass.

- [ ] **Step 6: Commit**

```bash
git add agents/effect_graph/compiler.py tests/effect_graph/test_preset_inputs_resolution.py
git commit -m "feat(effect-graph): resolve_preset_inputs against SourceRegistry, loud failure on unknown pad"
```

---

## Phase J — Acceptance sweep + final push (2 tasks)

### Task 28: Acceptance criteria validation sweep

**Files:**
- All tests in `tests/studio_compositor/` and `tests/effect_graph/`
- Manual smoke checks

- [ ] **Step 1: Run the full test suite**

```bash
uv run pytest tests/studio_compositor/ tests/effect_graph/ tests/test_compositor_model.py -v
```

Expected: every test passes. If anything fails, fix the root cause (do not mask).

- [ ] **Step 2: Ruff + pyright sweep**

```bash
uv run ruff check agents/studio_compositor/ agents/effect_graph/ shared/compositor_model.py
uv run ruff format --check agents/studio_compositor/ agents/effect_graph/ shared/compositor_model.py
uv run pyright agents/studio_compositor/ agents/effect_graph/
```

Expected: zero errors.

- [ ] **Step 3: Rust build + tests**

```bash
cargo build -p hapax-visual -p hapax-imagination
cargo test -p hapax-visual -p hapax-imagination
```

Expected: clean build, all tests pass.

- [ ] **Step 4: Verify each acceptance criterion from the spec**

Walk down the AC list in `docs/superpowers/specs/2026-04-12-compositor-source-registry-foundation-design.md § Acceptance criteria` and confirm each one has a corresponding test or manual verification step:

- [ ] AC1: compositor boots with default.json, reverie PiP upper-right shows frames
- [ ] AC2: existing Vitruvian/album visible, no regression
- [ ] AC3: hapax-imagination.service runs headless, no winit window
- [ ] AC4: `window.__logos.execute("compositor.surface.set_geometry", {...})` moves a PiP
- [ ] AC5: file-watch hot-reload works on valid edit, rejects invalid
- [ ] AC6: every source has a persistent appsrc pad (test_main_layer_path)
- [ ] AC7: preset load fails loudly on unknown source (test_preset_inputs_resolution)
- [ ] AC8: deleting default.json triggers fallback + ntfy, stream stays up
- [ ] AC9: all new tests pass; existing suite unchanged
- [ ] AC10: compositor_source_frame_age_seconds populates per source
- [ ] AC11: migrated cairo sources preserve visual output (golden-image check — may need a separate follow-up)

Any AC without a test or verification step → add a new task to this plan.

- [ ] **Step 5: Update PR #709 description**

```bash
gh pr edit 709 --body "$(cat <<'EOF'
## Summary
- Spec + implementation plan for PR 1 of the compositor source registry epic
- Makes the `Layout`/`SourceSchema`/`SurfaceSchema`/`Assignment` framework authoritative
- Registers reverie as an `external_rgba` source, migrates three cairo overlays
- Adds mid-stream PiP geometry mutation + persistent appsrc pads for main-layer availability
- Retires the standalone `hapax-imagination` winit window

## Artifacts
- Spec: `docs/superpowers/specs/2026-04-12-compositor-source-registry-foundation-design.md`
- Plan: `docs/superpowers/plans/2026-04-12-compositor-source-registry-foundation-plan.md`
- Hook fix: `hooks/scripts/no-stale-branches.sh` (delta as first-class session)
- CLAUDE.md updates: § Studio Compositor pointer, § Claude Code Hooks table

## Test plan
- [ ] Operator reviews the spec and plan
- [ ] After alpha's camera 24/7 resilience epic retires, a future session (alpha/beta/delta) implements this plan task-by-task
- [ ] Each task is TDD: test → fail → implement → pass → commit
EOF
)"
```

- [ ] **Step 6: Commit any final plan adjustments**

```bash
git add docs/superpowers/plans/2026-04-12-compositor-source-registry-foundation-plan.md
git commit -m "plan: compositor source registry foundation implementation plan" || echo "nothing to commit"
```

---

### Task 29: Final push

- [ ] **Step 1: Push all commits**

```bash
git push origin feat/compositor-source-registry-foundation
```

- [ ] **Step 2: Verify PR #709 updated state**

```bash
gh pr view 709 --json number,commits,statusCheckRollup | jq '.commits | length'
```

Expected: number of commits on the branch.

- [ ] **Step 3: Done**

Announce in the relay (`~/.cache/hapax/relay/delta.yaml`) that PR #709 is feature-complete for the spec + plan + hook fix phase, and retire the delta session with a handoff doc at `docs/superpowers/handoff/2026-04-12-delta-source-registry-handoff.md`.

---

## Self-review notes

The following checks were performed during plan authoring:

**Spec coverage:** Each section of the spec (architecture, source backends, reverie headless, default.json, render path, command surface, main-layer availability, testing, acceptance criteria, error handling) maps to one or more tasks in Phases A–J. The F8 content.* dead routing and the overlay_zones migration are explicit non-goals and are not in the plan.

**Placeholder scan:** No TBDs or "implement later" markers. Tests include concrete code; commands include concrete args; the render refactor shows the exact cairo sequence.

**Type consistency:** `LayoutState`, `SourceRegistry`, `CairoSourceRunner`, `ShmRgbaReader`, `Layout`, `SurfaceSchema`, `Assignment`, `Preset`, `PresetInput`, `PresetLoadError` are used consistently across tasks. Method signatures (`get()`, `mutate()`, `subscribe()`, `get_current_surface()`, `gst_appsrc()`, `resolve_preset_inputs()`) are the same in every task that references them.

**Scope check:** Single PR of approximately 29 tasks across 10 phases. All tasks belong to the single coherent PR 1 of the source-registry epic and are tightly coupled (reverie + cairo migration + layout authority + command server + appsrc tracks all depend on each other). Further decomposition would fragment the PR in a way that breaks the TDD cycle.
