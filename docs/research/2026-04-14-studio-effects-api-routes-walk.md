# Studio effects API routes walk — double-apply bug + dead endpoint

**Date:** 2026-04-14
**Author:** delta (beta role — cam-stability focus)
**Scope:** Fifth drop in the effect-system walk. Audits
`logos/api/routes/studio_effects.py` — the FastAPI surface
for effect graph mutation. Drop #46 flagged this as a
parallel entry point that bypasses the state_reader
mutation bus; this drop walks all 11 routes and identifies
a double-apply bug, a dead endpoint for the LayerPalette
dead feature, and latent thread-safety issues on the
modulator state.
**Register:** scientific, neutral
**Status:** investigation — 4 findings, 1 positive (prior
art for observability). No code changed.
**Companion:** drops #44, #46, #47

## Headline

**`PUT /api/studio/effect/graph` loads the same graph
TWICE:**

1. First via direct in-process call:
   `rt.load_graph(graph)` from the FastAPI worker thread
2. Then via the mutation bus: writes
   `/dev/shm/hapax-compositor/graph-mutation.json` which
   `state_reader_loop` picks up ~50-100 ms later on its
   10 Hz poll and applies AGAIN via `try_graph_preset` →
   `runtime.load_graph`

**The graph is compiled, deep-copied, and slot-pipeline-
activated twice per PUT request.** The second application
is silently idempotent because drop #5's glfeedback diff
check prevents redundant shader recompiles — but the
Python-side control-plane work (~5-7 ms per drop #46
measurement) is duplicated.

**Three other findings:**

2. **`PATCH /api/studio/layer/{layer}/palette` is an API
   endpoint for a dead feature.** Drop #44 finding 1
   identified `LayerPalette` as dead code (0 presets use
   it, no downstream reader). This endpoint calls
   `rt.set_layer_palette(layer, LayerPalette(**palette))`
   which writes to `_layer_palettes` — a dict that
   nothing reads. **Clients calling the endpoint get
   HTTP 200 with no observable side effect.**
3. **`PUT /api/studio/effect/graph/modulations` races
   with `tick_modulator`** (drop #43): both touch
   `UniformModulator._bindings` without a lock. CPython
   GIL makes list assignment atomic but iteration
   semantics are fragile. Latent bug, not currently
   observed.
4. **Positive finding**: `studio_effects.py` has a
   per-command-per-stage latency histogram
   (`logos_command_latency_ms`) that **is actually
   populated**. This is rare — most of the compositor
   has defined-but-unpopulated metrics (drop #41 finding,
   drops #33 observability gaps). `studio_effects.py` is
   prior art for drop #43's FXT-4 fx_tick observability
   recommendation.

## 1. API surface inventory

`logos/api/routes/studio_effects.py` exposes 11 routes:

| Route | Verb | Action |
|---|---|---|
| `/api/studio/effect/graph` | GET | `rt.get_graph_state()` |
| `/api/studio/effect/graph` | PUT | **Double-apply**: `rt.load_graph(graph)` + writes mutation bus |
| `/api/studio/effect/graph` | PATCH | `rt.apply_patch(patch)` (mutation bus NOT written) |
| `/api/studio/effect/graph/node/{node_id}/params` | PATCH | `rt.patch_node_params(node_id, params)` |
| `/api/studio/effect/graph/node/{node_id}` | DELETE | `rt.remove_node(node_id)` |
| `/api/studio/layer/{layer}/palette` | PATCH | **Dead** — writes `_layer_palettes`; no downstream reader |
| `/api/studio/layer/status` | GET | Returns `_layer_palettes` (all defaults) |
| `/api/studio/effect/graph/modulations` | PUT | **Thread race**: `rt.modulator.replace_all(...)` |
| `/api/studio/effect/graph/modulations` | GET | Returns current bindings |
| `/api/studio/presets` | GET | List available presets |
| `/api/studio/presets/{name}` | GET | Return a preset's EffectGraph |
| `/api/studio/presets/{name}/activate` | POST | `rt.load_graph(preset)` (direct, no mutation bus) |

**Inconsistency**: `PUT /effect/graph` writes to the
mutation bus; `PATCH /effect/graph`, `PATCH /node/.../params`,
and `POST /presets/.../activate` do NOT. Either the PUT
path is over-doing it (redundant) or the others are
under-doing it (missing cross-process notification).

## 2. Finding 1 — `replace_effect_graph` double-applies

`logos/api/routes/studio_effects.py:123-154`:

```python
@router.put("/studio/effect/graph")
async def replace_effect_graph(request: dict[str, object]):
    from agents.effect_graph.types import EffectGraph

    t_start = time.perf_counter()
    rt = _get_runtime()
    if not rt:
        raise HTTPException(503, "Compositor not available")
    source = str(request.pop("fx_source", request.pop("_source", "live")))
    try:
        graph = EffectGraph(**request)
        t_validate = time.perf_counter()
        _observe_stage("replace_graph", "validate", ...)
        rt.load_graph(graph)                                    # ← first apply
        t_runtime = time.perf_counter()
        _observe_stage("replace_graph", "runtime_load", ...)
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    try:
        mutation_path = Path("/dev/shm/hapax-compositor/graph-mutation.json")
        mutation_path.parent.mkdir(parents=True, exist_ok=True)
        mutation_path.write_text(_json_mod.dumps(graph.model_dump()))    # ← second apply
        source_path = Path("/dev/shm/hapax-compositor/fx-source.txt")
        source_path.write_text(source)
        t_ipc = time.perf_counter()
        _observe_stage("replace_graph", "ipc_write", ...)
    except OSError:
        pass
    _observe_stage("replace_graph", "total", ...)
    return {"status": "ok"}
```

**Sequence of events**:

1. `rt.load_graph(graph)` runs on the FastAPI worker thread
   - Compiles ExecutionPlan
   - `copy.deepcopy(graph)`
   - `modulator.replace_all(...)`
   - Calls `_on_plan_changed(old, new)` → `compositor._on_graph_plan_changed`
   - → `slot_pipeline.activate_plan(new_plan)` → iterates slots → fragment property sets
2. `mutation_path.write_text(...)` writes the JSON to `/dev/shm`
3. FastAPI returns 200 to the client
4. `state_reader_loop` (running on its own thread at 10 Hz) eventually polls the file at ~50-100 ms latency
5. `state_reader_loop` reads the file, unlinks it, parses as EffectGraph, calls `merge_default_modulations`, calls `try_graph_preset` → `runtime.load_graph(graph)` AGAIN
6. Second apply: full compile + deepcopy + replace_all + activate_plan, but drop #5's glfeedback diff check skips all fragment property sets because the assignments are unchanged

**Cost**: ~5-7 ms of redundant Python work on the state_reader
thread per PUT. Negligible in absolute terms, but it's
pure waste.

**Correctness impact**: also subtle — between step 1 and
step 5, `_user_preset_hold_until` is NOT set by the direct
runtime call (that's set by `try_graph_preset`, not by
`rt.load_graph` directly). When the state_reader eventually
re-applies via `try_graph_preset`, it sets
`_user_preset_hold_until = time.monotonic() + 600.0`. So
the hold window starts **100 ms late** for a direct-API
preset switch.

**Fix options**:

- **API-1**: remove the mutation bus write from
  `replace_effect_graph`. The direct `rt.load_graph` call
  already updates everything. Adjust other paths to also
  set `_user_preset_hold_until` directly. ~5 lines.
- **API-2**: keep the mutation bus write, remove the direct
  `rt.load_graph` call. All cross-thread dispatch goes
  through the state_reader polling. Slightly higher
  latency per PUT (~50-100 ms) but cleaner thread model.
  ~5 lines.
- **API-3**: make `rt.load_graph` itself set
  `_user_preset_hold_until` via a callback. Unified path
  for direct calls and state_reader calls. ~10 lines.

**Recommendation**: API-2. Centralizes graph mutation on
the state_reader thread; eliminates the latent thread-
safety issue in finding 3; trades ~100 ms of client
latency for architectural cleanliness.

**Alternative recommendation**: API-1 is simpler if the
operator prefers fast PUT responses.

## 3. Finding 2 — `/studio/layer/{layer}/palette` is an
API endpoint for a dead feature

`logos/api/routes/studio_effects.py:200-218`:

```python
@router.patch("/studio/layer/{layer}/palette")
async def set_layer_palette(layer: str, palette: dict[str, object]):
    from agents.effect_graph.types import LayerPalette

    if layer not in ("live", "smooth", "hls"):
        raise HTTPException(400, f"Invalid layer: {layer}")
    rt = _get_runtime()
    if not rt:
        raise HTTPException(503, "Compositor not available")
    rt.set_layer_palette(layer, LayerPalette(**palette))
    return {"status": "ok"}


@router.get("/studio/layer/status")
async def get_layer_status():
    rt = _get_runtime()
    if not rt:
        return {"layers": {}}
    return {"layers": {l: rt.get_layer_palette(l).model_dump() for l in ("live", "smooth", "hls")}}
```

**The dead feature chain from drop #44 finding 1**:

- `EffectGraph.layer_palettes: dict[str, LayerPalette]`
  — declared in presets (0/28 use it)
- `GraphRuntime._layer_palettes` — runtime state
- `GraphRuntime.set_layer_palette` / `get_layer_palette`
- **`PATCH /api/studio/layer/{layer}/palette`** ← this
  endpoint
- **`GET /api/studio/layer/status`** ← and this one

The PATCH endpoint writes to `_layer_palettes` dict. The
GET endpoint reads back from the same dict. **But no
downstream consumer (shader, uniform setter, cairo
source, cudacompositor pad) reads the dict.** A client
could:

1. `PATCH /studio/layer/live/palette` with `{"brightness":
   1.5}` → HTTP 200
2. `GET /studio/layer/status` → returns `{"layers":
   {"live": {"brightness": 1.5, ...}, ...}}`
3. **The livestream output is unchanged.**

The API contract lies: it accepts the mutation, confirms
receipt, and returns the stored state — but the stored
state has no observable effect on the rendering pipeline.

**Fix options**:

- **API-4**: remove both endpoints along with the
  `LayerPalette` dead feature (drop #44 FX-5, drop #47
  DR-1). Net negative LOC.
- **API-5**: return HTTP 501 "Not Implemented" from the
  PATCH endpoint until someone wires the feature to the
  downstream renderer. Explicit surface of the gap.
- **API-6**: actually wire the feature — have slot_pipeline
  apply layer palettes as uniforms on shaders reading
  `u_brightness`/`u_contrast`/etc. Real feature work;
  bigger scope.

**Recommendation**: API-4 (remove). Same reasoning as
drop #44 FX-5 / drop #47 DR-1.

## 4. Finding 3 — `replace_modulations` races with
`tick_modulator`

`logos/api/routes/studio_effects.py:221-229`:

```python
@router.put("/studio/effect/graph/modulations")
async def replace_modulations(bindings: list[dict[str, object]]):
    from agents.effect_graph.types import ModulationBinding

    rt = _get_runtime()
    if not rt:
        raise HTTPException(503, "Compositor not available")
    rt.modulator.replace_all([ModulationBinding(**b) for b in bindings])
    return {"status": "ok"}
```

`UniformModulator.replace_all` (`modulator.py:27-29`):

```python
def replace_all(self, bindings: list[ModulationBinding]) -> None:
    self._bindings = list(bindings)
    self._smoothed.clear()
```

This runs on the FastAPI worker thread. Simultaneously,
`fx_tick_callback` (drop #43) runs on the GLib main loop
thread and calls `modulator.tick(signals)` which iterates
`self._bindings`:

```python
def tick(self, signals: dict[str, float]) -> dict[tuple[str, str], float]:
    updates = {}
    for b in self._bindings:
        ...
```

**Race condition**:

- Thread A (FastAPI): `self._bindings = list(bindings)` — assigns a new list atomically under the GIL
- Thread B (GLib main loop): iterating `for b in self._bindings` — holds a reference to the pre-replace list (Python for-loops snapshot the iterable at the start)

**In CPython**: this is **accidentally safe** because
`for b in self._bindings` binds the iteration variable to
the current value of `self._bindings` AT THE START of the
loop. If another thread replaces `self._bindings` mid-
iteration, the loop continues iterating the original list
until it completes.

**BUT**: `self._smoothed.clear()` runs after the list
replacement, and the tick loop writes to `self._smoothed`
on every binding. If the main loop is mid-tick when
`clear()` fires:

1. Main loop: iterates binding X, computes new value,
   writes `self._smoothed[key] = val`
2. FastAPI: `self._smoothed.clear()` — removes all
   entries
3. Main loop: continues to binding Y, reads
   `self._smoothed.get(key)` — returns None, uses target
   as first-call value

**Effect**: after a `replace_modulations` call, the first
tick may produce "first-call" values (no smoothing)
instead of properly-smoothed values, causing a one-tick
visual jump on the next render.

**Probability**: `replace_modulations` is rare (manual
operator action). The race window is ~30 µs (one tick's
worth of modulator work). Odds of hitting it per PUT
request: <1% typically.

**Visible effect**: a single frame of "uninterpolated
audio reactivity" values for modulated params. Barely
perceptible.

**Not urgent but latent.**

**Fix options**:

- **API-7**: dispatch `replace_all` via `GLib.idle_add`
  to run on the main loop thread. Standard pattern from
  `pipeline_manager._idle_swap_to_fallback`. ~3 lines.
- **API-8**: add a lock to `UniformModulator` and acquire
  it in both `replace_all` and `tick`. ~5 lines.

**Recommendation**: API-7. Consistent with the rest of
the codebase's cross-thread dispatch pattern.

## 5. Finding 4 — positive — prior art for observability

`studio_effects.py:28-90` implements a per-command-per-
stage Prometheus histogram (`logos_command_latency_ms`)
with labels `{command, stage}`. Stages are:

- `validate` — Pydantic parse + EffectGraph/GraphPatch
  construction
- `runtime_load` — direct runtime call cost
- `ipc_write` — mutation bus file write
- `total` — full handler duration

**Populated on every request** to the relevant endpoints
(`replace_graph`, `patch_graph`). Exposed via the
prometheus_fastapi_instrumentator middleware.

This is **rare** in the compositor codebase. Drop #41
identified widespread defined-but-unpopulated metrics
(`studio_rtmp_bytes_total`, `studio_rtmp_connected`, etc.
— all skeletons). Drop #33, #36, #39, #43 all flagged
per-subsystem observability gaps.

**`studio_effects.py` got it right**: lazy-init histogram,
labelled stages, per-stage `_observe_stage` helper, and
the histogram actually observes real timing data.

**Drop #43 FXT-4 ("per-timer latency histograms" for
fx_tick_callback)** should **model itself on this
pattern**. The code is ~30 lines and ready to be
templated.

## 6. Ring summary

### Ring 1 — bugfixes + dead endpoint removal

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **API-1 OR API-2** | Remove double-apply in `replace_effect_graph` | `studio_effects.py:123-154` | ~5 | Eliminates ~5-7 ms redundant control-plane work per PUT |
| **API-4** | Remove `/studio/layer/{layer}/palette` endpoints | `studio_effects.py:200-218` | ~20 | API contract stops lying; aligns with drop #44 FX-5 / drop #47 DR-1 |
| **API-7** | `GLib.idle_add` dispatch for `replace_modulations` | `studio_effects.py:221-229` | ~3 | Eliminates thread race on modulator state |

**Risk profile**: API-1/API-2 need alignment with whatever
calls `PUT /effect/graph` today (chain builder? operator
API?). API-4 requires the LayerPalette removal to ship
(drop #44 / drop #47). API-7 is zero risk.

### Ring 2 — observability templating

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **API-9** | Port the `_command_latency` pattern to drop #43 FXT-4 (fx_tick_callback) | `lifecycle.py`, `metrics.py`, `fx_tick.py` | ~30 | Per-timer latency histogram shipped |

## 7. Cross-references

- `logos/api/routes/studio_effects.py` — all routes + the
  `_command_latency` prior art
- `logos/api/routes/studio.py:26-37` — `_graph_runtime`
  and `_shader_registry` module globals (set by
  `effects.py:init_graph_runtime`, read via late-import
  by studio_effects)
- `agents/studio_compositor/effects.py:42-47` — exports
  the runtime to the API module
- `agents/studio_compositor/state.py:249-270` — state
  reader's `graph-mutation.json` consumer (the other
  side of the double-apply path)
- `agents/effect_graph/runtime.py:46-60` —
  `GraphRuntime.load_graph`
- `agents/effect_graph/modulator.py:27-58` —
  `replace_all` (thread race) and `tick`
- Drop #5 — glfeedback diff check (what neutralizes the
  double-apply's GPU cost)
- Drop #33 — live incident retro (example of
  unpopulated skeleton metrics)
- Drop #41 — BudgetTracker wiring audit (same theme of
  defined-but-unpopulated observability)
- Drop #43 — fx_tick_callback walk (FXT-4 observability
  gap that API-9 could close with prior art from this
  drop)
- Drop #44 — preset + governance walk (LayerPalette
  origin)
- Drop #46 — mutation bus flow (state_reader polling
  path that double-apply feeds)
- Drop #47 — dead feature inventory (DR-1 LayerPalette
  removal that API-4 is aligned with)
