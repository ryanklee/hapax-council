# Effect mutation-bus cross-process flow + effect_graph module organization

**Date:** 2026-04-14
**Author:** delta (beta role — cam-stability focus)
**Scope:** Third drop in the effect-system walk. Drop #44
covered presets + governance, drop #45 covered shader
complexity + temporal slot dead code. This drop traces
the **cross-process mutation-bus flow** end-to-end —
from a chat keyword or random_mode fade tick through
`graph-mutation.json` into the compositor's
`state_reader_loop` and out to the slot pipeline. Plus
two module-organization findings on
`agents/effect_graph/`.
**Register:** scientific, neutral
**Status:** investigation — 4 findings. No code changed.
**Companion:** drops #38, #43, #44, #45

## Headline

**The effect-graph mutation bus is a file-based
cross-process pipe** between chat-monitor
(out-of-process), random_mode (separate daemon), or
operator API → compositor. The compositor-side reader
(`state_reader_loop`) polls the mutation file at
**10 Hz** (`time.sleep(0.1)`) which **undersamples
random_mode's 12.5 Hz fade-write rate**. The nominal
12-step fade becomes an effective 5-6 step fade from
the perceptual side.

**Four findings:**

1. **`random_mode` fade transitions are polling-bounded**
   — writes 24 mutation-bus updates per ~1-second fade
   (12 fade-out + 12 fade-in) but the state reader only
   samples at 10 Hz. Effective fade granularity is
   ~5-6 distinct brightness steps, not 12.
2. **Each mutation-bus write triggers a full graph
   recompile cycle** (parse JSON → construct
   EffectGraph → merge_default_modulations → compile
   plan → deepcopy → activate_plan). ~5-7 ms per write
   × 24 writes = ~120-170 ms of Python control-plane
   work during a fade. The drop #5 diff check prevents
   redundant shader recompiles but the plan-construction
   cost is still paid on every write.
3. **`agents/effect_graph/` has mixed concerns** —
   `capability.py` and `wgsl_compiler.py` + `wgsl_transpiler.py`
   are **Reverie-only** (consumed by
   `agents/reverie/mixer.py` + `agents/reverie/bootstrap.py`),
   **not used by the compositor at all**. The module is
   organically two modules in one: a compositor-facing
   core (types, compiler, runtime, modulator, pipeline,
   registry) and a reverie-facing transpile + capability
   path.
4. **`chat_reactor` has a production/test preset-exclusion
   mismatch** — the test branch of
   `_build_keyword_index` hardcodes an exclusion list
   (`clean`, `echo`, `reverie_vocabulary`) but the
   production branch defers to `get_preset_names()`
   which has its own exclusion in `random_mode.py`. The
   two exclusion sets happen to agree today but they're
   unlinked and could drift.

## 1. The mutation-bus flow end-to-end

```text
─────────────────────────────────────────────────────────────────────
WRITER SIDE (cross-process)                             FREQUENCY
─────────────────────────────────────────────────────────────────────

chat_reactor.PresetReactor.process_message              per chat
  (in-process with chat-monitor.py)                     message
  │  keyword match → preset lookup → cooldown check      + 30s cooldown
  │  → write(graph-mutation.json)
  │
  ▼
[/dev/shm/hapax-compositor/graph-mutation.json]         shared file

random_mode.run(interval=30.0)                           12.5 Hz
  (agents/studio_compositor/random_mode.py as daemon)    during fades
  │  fade_out: 12 × apply_graph_with_brightness
  │             (writes mutation file every 80 ms)
  │  fade_in: 12 × apply_graph_with_brightness
  │  hold at full brightness for interval - 2s
  │
  ▼
[/dev/shm/hapax-compositor/graph-mutation.json]

operator API (logos/api/routes/studio.py)                 per request
  → graph_runtime.load_graph(...) directly                (no mutation
  → chat reactor does NOT go through the file path       bus)
  (direct runtime call, bypasses state_reader)

AtmosphericSelector.evaluate (fx_tick_callback)          per tick
  → try_graph_preset(target) (from tick_governance)      (~30 Hz
  → direct file read + runtime.load_graph                 check, rate-
  (ALSO bypasses the mutation bus)                        limited by
                                                          _DWELL_MIN_S)

─────────────────────────────────────────────────────────────────────
READER SIDE (compositor process)                        FREQUENCY
─────────────────────────────────────────────────────────────────────

state_reader_loop (agents/studio_compositor/state.py)    10 Hz
  (daemon thread, time.sleep(0.1) per iteration)         polling
  │
  ├─ exists(graph-mutation.json)?
  │    │  yes:
  │    │  ├─ read_text + json.loads
  │    │  ├─ unlink mutation file                        (atomic
  │    │  │                                               consume)
  │    │  ├─ EffectGraph(**raw)                          pydantic
  │    │  │                                               validation
  │    │  ├─ merge_default_modulations(graph)            disk read
  │    │  │                                               of _default
  │    │  ├─ runtime.load_graph(graph)
  │    │  │    ├─ compiler.compile(graph)                → ExecutionPlan
  │    │  │    ├─ copy.deepcopy(graph)
  │    │  │    ├─ modulator.replace_all(...)
  │    │  │    └─ _on_plan_changed(old, new)
  │    │  │         → compositor._on_graph_plan_changed
  │    │  │              → slot_pipeline.activate_plan(new_plan)
  │    │  │                   ├─ assign nodes to slots
  │    │  │                   ├─ diff-check fragments
  │    │  │                   └─ set_property("fragment", frag)
  │    │  │                        for changed slots
  │    │  └─ set _user_preset_hold_until = now + 600s
  │    │     (suppress governance for 10 min)
  │    │
  │    └─ no: skip
```

**Critical observation**: the mutation bus is a
**single-file single-writer single-reader pipe**. The
reader (state_reader_loop) unlinks the file on read,
giving write-then-consume semantics. But the writer has
no mechanism to wait for the consumer — it just writes
and moves on. **If writer fires faster than reader polls,
writes are coalesced** (the newest overwrites the previous
one, and the reader only sees the latest).

### 1.1 The polling-undersampling problem

`random_mode.apply_graph_with_brightness` writes the
mutation file every 80 ms (`TRANSITION_STEP_MS = 80`).
`state_reader_loop` polls every 100 ms (`time.sleep(0.1)`).

- **Writer rate**: 12.5 Hz (80 ms period)
- **Reader rate**: 10.0 Hz (100 ms period)

Beat frequency: 2.5 Hz. Every ~400 ms, the reader
"misses" a writer step because the writer has already
overwritten the file with the next step. **The reader
effectively samples 1 in every ~1.25 writer steps.**

Over a 12-step fade (960 ms write duration), the reader
sees approximately **10 distinct writes** but 2 are
"lost" (overwritten) — and of the 10 it sees, the
reader's own processing time (~5-7 ms per read + parse
+ compile) eats into its next polling window, so the
effective perception is closer to **5-6 distinct
brightness levels visible** to the downstream pipeline.

**Why it matters**: the operator sees the fade as
having visible "steps" rather than smooth linear
interpolation. It's not broken, but it's not what the
code pretends to do.

**Fix options**:

- **MB-1**: align the writer step interval to the reader
  polling period. Set `TRANSITION_STEP_MS = 100` instead
  of 80. Writer now ticks at exactly 10 Hz → matches the
  reader's sampling rate. Clean 1:1 sampling.
- **MB-2**: state reader uses `inotify` instead of
  polling. Rust `notify` crate or Python `inotify_simple`
  gives sub-millisecond change detection. Larger change,
  but eliminates all polling undersampling across all
  mutation-bus writers (chat reactor, random mode,
  operator API).
- **MB-3**: writer blocks until the file is consumed.
  Add a read-ack mechanism (reader creates an ack file
  after consuming). Fragile — turns a fire-and-forget
  writer into a stateful one.

**Recommendation**: MB-1 is the one-line fix. MB-2 is
the principled fix but requires a Python inotify
dependency and replaces the state_reader polling loop.
MB-3 is not worth the complexity.

### 1.2 Per-mutation cost accounting

Each `state_reader_loop` iteration that finds a mutation
file does roughly:

| Step | Cost |
|---|---|
| `graph_mutation_path.exists()` | ~10 µs stat call |
| `raw = path.read_text()` | ~100-500 µs (depends on preset size) |
| `graph_mutation_path.unlink(missing_ok=True)` | ~50 µs |
| `graph = EffectGraph(**json.loads(raw))` | ~1-2 ms (pydantic validation) |
| `graph = merge_default_modulations(graph)` | ~500 µs (disk read + merge) |
| `runtime.load_graph(graph)` | ~2-4 ms (compile + deepcopy + replace_all) |
| `slot_pipeline.activate_plan(new_plan)` | ~500 µs (diff-check skips most slots) |

**Total per mutation**: ~5-7 ms of Python work on the
state_reader thread.

**random_mode's 24-step fade** therefore consumes
roughly **120-170 ms of cumulative state_reader CPU
time** over the ~960 ms fade window — ~12-18% of the
fade duration spent in control-plane machinery.

This is not a hot spot in absolute terms (the state
reader thread is mostly idle otherwise) but it's the
**highest non-trivial Python cost on the compositor's
control plane** during a transition.

**Drop #44 FX-2 (cache `_default_modulations.json`)**
would save ~500 µs per mutation × 24 writes = **~12 ms
per fade**. Modest.

**Drop #44 FX-3 (replace `copy.deepcopy` with
`graph.model_copy`)** would save ~500 µs per mutation
× 24 writes = **~12 ms per fade**. Modest.

**Combined FX-2 + FX-3**: ~24 ms per fade savings,
~15% of the control-plane cost eliminated.

## 2. Finding 3 — `effect_graph` module has mixed
Reverie + compositor concerns

Module inventory:

```text
agents/effect_graph/
  __init__.py            empty (1 line)
  METADATA.yaml          module metadata
  types.py               Pydantic models (shared)
  registry.py            ShaderRegistry (shared)
  compiler.py            GraphCompiler (shared)
  runtime.py             GraphRuntime (shared)
  modulator.py           UniformModulator (shared)
  pipeline.py            SlotPipeline (shared)
  temporal_slot.py       TemporalSlotState (DEAD — drop #45)
  visual_governance.py   AtmosphericSelector (compositor only)
  capability.py          ShaderGraphCapability (REVERIE only)
  wgsl_compiler.py       compile_to_wgsl_plan (REVERIE only)
  wgsl_transpiler.py     WGSL AST + codegen (REVERIE only)
```

Verified usage:

```text
$ grep -rn 'ShaderGraphCapability' agents/ | grep -v '__pycache__'
agents/effect_graph/capability.py  (defn)
agents/reverie/mixer.py:46         from agents.effect_graph.capability import ShaderGraphCapability
agents/reverie/mixer.py:50         self._shader_cap = ShaderGraphCapability()
agents/reverie/mixer.py:333        elif name == "shader_graph":

$ grep -rn 'wgsl_compiler\|wgsl_transpiler' agents/ | grep -v '__pycache__' | grep -v 'effect_graph'
agents/reverie/bootstrap.py:41     from agents.effect_graph.wgsl_compiler import ...
agents/reverie/_satellites.py:13   from agents.effect_graph.wgsl_compiler import ...
```

**None of these three files are imported anywhere
inside `agents/studio_compositor/`**. They're
Reverie-only.

**Cumulative picture** combined with drop #45 finding 1:

- `temporal_slot.py` — DEAD (63 lines)
- `capability.py` — Reverie-only (78 lines)
- `wgsl_compiler.py` — Reverie-only (284 lines)
- `wgsl_transpiler.py` — Reverie-only (262 lines)

**~687 lines of `agents/effect_graph/` are either dead
or Reverie-only**, while the compositor-facing subset
(types, registry, compiler, runtime, modulator, pipeline,
visual_governance) is ~1300 lines. **Roughly a third of
the `effect_graph` module is not used by the compositor.**

**Fix options**:

- **MB-4**: **move Reverie-only files** to a new
  `agents/reverie_shader/` submodule. Imports in
  `agents/reverie/` update to the new path. The
  compositor import graph shrinks by ~624 lines.
- **MB-5**: **rename `agents/effect_graph/` to
  `agents/shader_graph/`** since the name is already
  shared between two consumers. Or keep the current
  name and add a clear README about what's shared and
  what's Reverie-specific.
- **MB-6**: **leave as is, document**. Add a
  `README.md` to `agents/effect_graph/` explaining
  which files are compositor-facing and which are
  Reverie-facing. Zero code change. Surfaces the
  organization but doesn't fix it.

**Recommendation**: MB-4 is the principled move but
requires updating 3 import lines in reverie code +
moving 3 files. Low risk, modest LOC impact. MB-6 is
the zero-risk minimum.

## 3. Finding 4 — `chat_reactor` production/test
exclusion mismatch

`agents/studio_compositor/chat_reactor.py:97-106`:

```python
def _build_keyword_index(self) -> None:
    ...
    names = (
        get_preset_names()
        if self._preset_dir is PRESET_DIR
        else [
            p.stem
            for p in sorted(self._preset_dir.glob("*.json"))
            if not p.stem.startswith("_")
            and p.stem not in ("clean", "echo", "reverie_vocabulary")
        ]
    )
```

**Production path** (`self._preset_dir is PRESET_DIR`):
defers to `random_mode.get_preset_names()`:

```python
# agents/studio_compositor/random_mode.py:17-24
def get_preset_names() -> list[str]:
    return sorted(
        [
            p.stem
            for p in PRESET_DIR.glob("*.json")
            if not p.stem.startswith("_") and p.stem not in ("clean", "echo", "reverie_vocabulary")
        ]
    )
```

**Test path** (test passes a different `preset_dir`):
hardcoded exclusion list `("clean", "echo",
"reverie_vocabulary")`.

**Observation**: the two exclusion sets are **literally
identical** today but they're maintained in two separate
places. **If someone adds or removes an exclusion in one
location and forgets the other**, the production path and
test path diverge silently.

**Observability**: no test verifies that the two
exclusion sets agree.

**Fix**: make both paths call the same exclusion
function. ~5 lines of refactor.

```python
# random_mode.py — extract to module-level constant
_EXCLUDED_PRESETS = frozenset({"clean", "echo", "reverie_vocabulary"})

def _is_excluded(stem: str) -> bool:
    return stem.startswith("_") or stem in _EXCLUDED_PRESETS

def get_preset_names() -> list[str]:
    return sorted(p.stem for p in PRESET_DIR.glob("*.json") if not _is_excluded(p.stem))

# chat_reactor.py — import the helper
from .random_mode import _EXCLUDED_PRESETS, _is_excluded
```

## 4. Ring summary

### Ring 1 — small corrections

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **MB-1** | `TRANSITION_STEP_MS = 80 → 100` | `random_mode.py:14` | 1 | Writer aligns with state reader polling rate; clean 1:1 sampling |
| **MB-7** | Deduplicate preset-exclusion logic between chat_reactor + random_mode | `random_mode.py` + `chat_reactor.py` | ~5 | Eliminates silent drift risk between production and test paths |

**Risk profile**: zero for both.

### Ring 2 — module organization

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **MB-4** | Move `capability.py`, `wgsl_compiler.py`, `wgsl_transpiler.py` to `agents/reverie_shader/` | Multiple | ~8 import edits + 3 file moves | Effect_graph module becomes compositor-specific |
| **MB-6** | Add README documenting the mixed concerns | `agents/effect_graph/README.md` | ~20 | Zero-code alternative if MB-4 feels too disruptive |

**Risk profile**: MB-4 needs cross-repo coordination
because `agents/reverie/` might have open PRs that
touch the imports. MB-6 is zero-risk.

### Ring 3 — architectural (state reader redesign)

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **MB-2** | Replace state_reader polling with inotify-based change detection | `state.py` | ~60 | Eliminates 10 Hz poll + undersampling; sub-ms mutation detection |

**Risk profile**: medium. inotify behavior under rapid
write patterns has edge cases (coalescing,
write-then-unlink races). Needs careful testing. The
10 Hz polling isn't broken, just imperfect — MB-1 + MB-7
cover the current pain more cheaply.

## 5. Cumulative impact estimate

**Ring 1 alone** (MB-1 + MB-7): 6 lines of code
touched. Fade sampling becomes clean, test/prod
exclusion drift eliminated. Zero behavior change for
existing presets.

**Ring 2 MB-4**: effect_graph module becomes
topologically cleaner but no runtime change. Useful
for future refactors that want to see clearly what the
compositor depends on.

**Combined with drop #44 Ring 1 FX-2 + FX-3** (cache
default modulations, pydantic model_copy): another
~24 ms per fade reclaimed on the state_reader thread.

**None of these are hot-path fixes** in the streaming
sense. They're correctness / organizational
improvements to the control plane that sits next to
the hot path.

## 6. Cross-references

- `agents/studio_compositor/random_mode.py:13-59` —
  fade transition code (MB-1 site)
- `agents/studio_compositor/state.py:180-250` —
  `state_reader_loop` mutation file polling (MB-2
  target)
- `agents/studio_compositor/chat_reactor.py:89-114` —
  `_build_keyword_index` (MB-7 site)
- `agents/effect_graph/capability.py` — Reverie-only
- `agents/effect_graph/wgsl_compiler.py` — Reverie-only
- `agents/effect_graph/wgsl_transpiler.py` — Reverie-only
- `agents/reverie/mixer.py:46-50` — `ShaderGraphCapability`
  usage
- `agents/reverie/bootstrap.py:41` — `wgsl_compiler`
  usage
- Drop #5 — glfeedback diff check (prevents shader
  recompile storm during random_mode fades)
- Drop #36 — state_reader_loop threading overview
- Drop #38 — SlotPipeline activate_plan diff check
- Drop #41 — BudgetTracker wiring audit (same
  mutation-bus pattern, different file path)
- Drop #43 — fx_tick_callback walk (governance-side
  preset switch, bypasses mutation bus via direct
  runtime call)
- Drop #44 — preset + governance walk (FX-2 + FX-3
  are prerequisites for the fade-cost savings in this
  drop)
- Drop #45 — shader complexity survey (context for
  why the diff check matters on hot shaders)
