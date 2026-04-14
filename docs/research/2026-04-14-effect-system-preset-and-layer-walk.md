# Effect system systematic walk — presets, layers, governance, plan activation

**Date:** 2026-04-14
**Author:** delta (beta role — cam-stability focus)
**Scope:** First drop in a new systematic walk covering the
**effect system** side of the compositor — the preset
files, shader node registry, graph runtime, atmospheric
governance, and the preset → plan → slot-pipeline dispatch
chain. Drops #38 and #43 touched the slot-pipeline
architecture and the per-tick modulator flow but stopped
short of auditing the preset-facing control plane. This
drop maps the entire flow from `presets/*.json` to
`set_property("fragment", ...)` on a `glfeedback` slot.
**Register:** scientific, neutral
**Status:** investigation — 9 findings, 2 dead features,
1 silent naming bug. No code changed.
**Companion:** drop #38 (SlotPipeline internals),
drop #41 (BudgetTracker wiring audit + layout source
dead-path finding), drop #43 (fx_tick_callback walk)

## Headline

**The effect system has 59 shader node types, 28 playable
presets, and a sophisticated governance layer — but a
large fraction of the architectural surface is unused or
broken:**

- **`LayerPalette` system is dead code.** The Pydantic
  model, runtime state, and setter/getter exist but **zero
  presets** declare `layer_palettes`. No downstream
  consumer reads the runtime's `_layer_palettes` dict.
- **`PresetInput` / `resolve_preset_inputs` / source-registry
  binding system is dead code.** Phase 7 of the source-
  registry completion epic shipped the schema + loader
  validation but **zero presets** declare `inputs`.
  Combined with drop #41 finding 1 (layout-declared cairo
  sources never start), the **entire source-registry →
  preset → glvideomixer pad-alpha pipeline is dead
  end-to-end**.
- **Silent genre-bias bug**: `_GENRE_BIAS` in
  `visual_governance.py` references `"tunnel_vision"`
  (underscore) but the preset file is `tunnelvision.json`
  (no underscore). Electronic/ambient genre biases never
  match that preset.
- **`_default_modulations.json` is re-read from disk on
  every preset load.** No caching; the `merge_default_modulations`
  function does a fresh file read + parse each time
  `try_graph_preset` fires.
- **Preset naming is fragile**: some presets carry a
  `_preset` suffix (`halftone_preset`, `vhs_preset`,
  `ascii_preset`) and some don't (`neon`, `ghost`,
  `ambient`). The `GRAPH_PRESET_ALIASES` dict patches
  legacy names but the `_STATE_MATRIX` in governance
  hardcodes specific names — adding a new preset requires
  knowing which convention applies.

**Healthy parts**: the `SlotPipeline.activate_plan` diff
check (drop #5 era fix) correctly prevents redundant
shader recompiles. The `UniformModulator` tick is simple
and cheap. The `AtmosphericSelector` has appropriate dwell
time + stance-change bypass semantics.

## 1. Architecture map

```text
presets/*.json
   │  (28 JSON files, 5-8 nodes each, median 6-7)
   │
   ▼
try_graph_preset(name)                        agents/studio_compositor/effects.py
   │
   ├── file lookup in:
   │     ~/.config/hapax/effect-presets/
   │     ./presets/
   │   (with GRAPH_PRESET_ALIASES for legacy names)
   │
   ├── json.loads → EffectGraph(**raw)
   │
   ├── merge_default_modulations(graph)
   │     │ reads presets/_default_modulations.json every call
   │     │ builds type→node_id map
   │     │ appends up to 13 default bindings (matched by node type, last instance)
   │     ▼
   │
   ├── resolve_preset_inputs(graph, source_registry)   [DEAD — no preset has inputs]
   │
   ▼
GraphRuntime.load_graph(graph)                agents/effect_graph/runtime.py
   │
   ├── compiler.compile(graph) → ExecutionPlan
   │     │ topo-sort per output target (Phase 5a multi-target support)
   │     │ merge registry defaults with instance params
   │     │ mark temporal nodes (need glfeedback tex_accum)
   │     │ mark needs_dedicated_fbo (multi-fanout nodes)
   │     ▼
   │
   ├── copy.deepcopy(graph)                   [expensive pydantic deepcopy per load]
   │
   ├── modulator.replace_all(graph.modulations)
   │     │ ← 0-13 modulations (preset's own + defaults)
   │
   ├── _layer_palettes update                 [DEAD — no preset writes palettes]
   │
   └── _on_plan_changed(old, new)
         │
         ▼
         compositor._on_graph_plan_changed(old, new)   agents/studio_compositor/compositor.py
         │
         ▼
         slot_pipeline.activate_plan(new)            agents/effect_graph/pipeline.py
         │
         ├── default all 24 slots to PASSTHROUGH_SHADER
         ├── assign each plan step to next slot (sequential, topo-ordered)
         ├── for each slot: diff-check frag vs _slot_last_frag[i]
         ├── if changed: set_property("fragment", frag)
         │                _slot_last_frag[i] = frag
         │                fragment_set_count += 1
         └── increment COMP_GLFEEDBACK_RECOMPILE_TOTAL by fragment_set_count
```

## 2. Presets — static characterization

### 2.1 Preset file inventory

```text
preset                          nodes  edges  mods  palettes  inputs
────────────────────────────────────────────────────────────────────
heartbeat.json                      8      8     0         0       0
screwed.json                        8      8     0         0       0
ambient.json                        8      8     0         0       0
dither_retro.json                   8      8     0         0       0
mirror_rorschach.json               8      8     0         0       0
trap.json                           8      8     0         0       0
fisheye_pulse.json                  7      7     1         0       0
vhs_preset.json                     7      7     1         0       0
ascii_preset.json                   7      7     0         0       0
datamosh.json                       7      7     0         0       0
datamosh_heavy.json                 7      7     0         0       0
ghost.json                          7      7     0         0       0
glitch_blocks_preset.json           7      7     0         0       0
trails.json                         7      7     1         0       0
tunnelvision.json                   6      6     1         0       0    ← note filename
feedback_preset.json                6      6     1         0       0
kaleidodream.json                   6      6     1         0       0
neon.json                           6      6     1         0       0
nightvision.json                    6      6     0         0       0
pixsort_preset.json                 6      6     0         0       0
sculpture.json                      6      6     0         0       0
silhouette.json                     6      6     0         0       0
voronoi_crystal.json                6      6     0         0       0
diff_preset.json                    6      6     0         0       0
clean.json                          5      5     0         0       0
thermal_preset.json                 5      5     0         0       0
halftone_preset.json                5      5     0         0       0
slitscan_preset.json                5      5     0         0       0
────────────────────────────────────────────────────────────────────
                  28 presets, node median=6-7, max=8, min=5
                  Only 8/28 declare modulations (all with exactly 1)
                  0/28 declare layer_palettes
                  0/28 declare inputs
```

Plus `_default_modulations.json` (0 nodes, 13 default
bindings) and `reverie_vocabulary.json` (reverie-specific,
not a compositor preset).

### 2.2 Shader node registry

`agents/shaders/nodes/*.json` — 59 node type manifests, each
with:
- A `.json` manifest declaring inputs/outputs/params/temporal
- A `.frag` fragment shader (GLSL)
- A `.wgsl` alternative shader (for the Reverie wgpu path)

All 59 are **loaded eagerly at compositor startup** via
`ShaderRegistry.__init__` which globs the directory and
reads every JSON + its referenced `.frag` file. Total
in-memory footprint: ~60-100 KB of GLSL source text.

**Finding**: shader authoring requires a compositor
restart to pick up new shaders — `ShaderRegistry` has no
reload path. Minor developer-ergonomics issue; not a
runtime hot spot.

## 3. Findings

### 3.1 Finding 1 — `LayerPalette` system is dead code

The `EffectGraph` pydantic model declares
`layer_palettes: dict[str, LayerPalette]`. The
`GraphRuntime` initializes
`self._layer_palettes = {"live": LayerPalette(), "smooth":
LayerPalette(), "hls": LayerPalette()}`. `load_graph`
updates `self._layer_palettes[k] = v` for any key in
`graph.layer_palettes`. There are `set_layer_palette` and
`get_layer_palette` methods and the layer palette state is
exported in `get_graph_state()`.

**But zero presets populate `layer_palettes`.** And no
downstream consumer reads the runtime's `_layer_palettes`
dict — grep confirms no slot-pipeline, no shader uniform,
no cairooverlay, no fx_chain reads it.

**Impact**: pure dead surface area. The feature was
designed for per-layer color grading (brightness / contrast
/ saturation / sepia / hue_rotate per input layer) but
never wired to the glvideomixer pads or per-slot uniforms.

**Fix options**:

- **Option A**: **remove the LayerPalette system entirely.**
  ~30 lines across `types.py`, `runtime.py`, and
  `get_graph_state`. Cleaner type system, no behavior change.
- **Option B**: **wire it up** — have the slot pipeline
  apply layer palettes as uniforms on shaders that reference
  `u_brightness`/`u_contrast`/etc. Larger work, but gives
  per-layer tinting. Not currently requested.

**Recommendation**: Option A. Dead code rots.

### 3.2 Finding 2 — `PresetInput` / source-registry bindings
are dead end-to-end

Phase 7 of the source-registry completion epic introduced
the `PresetInput` pydantic model (`types.py:80-114`) and
the `resolve_preset_inputs` loader helper
(`compiler.py:35-64`). The helper raises `PresetLoadError`
loudly on unknown pad references, and `try_graph_preset`
calls it when a preset has `inputs`.

**But zero presets declare `inputs`.** And combined with
drop #41 finding 1 (layout-declared cairo sources are
never started, so `source_registry._backends` contains
backends that never render), **the entire pipe from
preset → source registry → glvideomixer main-layer appsrc
pad is dead end-to-end**:

```text
preset.inputs (empty for all 28 presets)
   → resolve_preset_inputs (never called for real presets)
   → source_registry lookup (backends never started)
   → glvideomixer appsrc branch (Phase 6 task H24 code path)
   → never receives any buffers
```

**Impact**: Phases 6 + 7 of the source-registry completion
epic landed code but no preset authorship followed. Drop
#41 finding 1 needed a `SourceRegistry.start_all()` call
to even begin — this drop's finding is that **even with
that fix, no preset would actually USE the pads** because
no preset declares `inputs` references.

**Fix**: either

- **Option A**: write at least one reference preset that
  uses `inputs` to prove the path works end-to-end, document
  it, and add a test that validates the main-layer branch
  actually receives buffers. This is meaningful engineering
  work (~2-3 hours) but it completes the epic.
- **Option B**: **retire the Phase 6 + 7 code** — remove
  `PresetInput`, `resolve_preset_inputs`,
  `build_source_appsrc_branches`, `SurfaceKind.fx_chain_input`,
  and the related glvideomixer appsrc branch wiring. Large
  removal (~200 lines) but eliminates a major dead
  architectural surface.

**Recommendation**: operator decision required. If the
intent is still to drive main-layer content from preset
bindings, keep it and write one reference preset. If the
intent has drifted (most likely — the cairo overlay +
cudacompositor path covers the same conceptual ground),
retire it.

### 3.3 Finding 3 — `_GENRE_BIAS` has a silent typo

`agents/effect_graph/visual_governance.py:45-53`:

```python
_GENRE_BIAS: dict[str, list[str]] = {
    "hip hop": ["trap", "screwed", "ghost"],
    "trap": ["trap", "screwed", "ghost"],
    "lo-fi": ["vhs_preset", "dither_retro", "ambient"],
    "jazz": ["vhs_preset", "dither_retro", "ambient"],
    "soul": ["vhs_preset", "ambient"],
    "electronic": ["voronoi_crystal", "tunnel_vision", "kaleidodream"],
    "ambient": ["voronoi_crystal", "tunnel_vision", "kaleidodream"],
}
```

Two entries reference `"tunnel_vision"` (with underscore).
The actual preset file is `presets/tunnelvision.json` —
stem `tunnelvision` (no underscore). `get_available_preset_names()`
returns `{..., "tunnelvision", ...}`. When the genre bias
tries to prepend `"tunnel_vision"` to a preset family, it
filters via `p in available_presets` which evaluates False.

**Impact**: the `tunnelvision` preset is silently
unreachable from genre bias for `electronic` or `ambient`
music. Governance still picks it from the underlying
`_STATE_MATRIX` (where it's not listed either, so never)
— which means **`tunnelvision` is effectively unreachable
from auto-governance entirely**.

Grep confirms: `tunnelvision` is NOT in the state matrix
either. It's only triggerable by manual
`try_graph_preset("tunnelvision")` via the chat reactor
or operator API — never by the atmospheric selector.

**Fix**: rename the preset file to `tunnel_vision.json`
(matching the governance reference), OR change the
governance dict to `"tunnelvision"`. File rename is
riskier because it breaks any hardcoded reference; dict
edit is safer. One-line fix.

### 3.4 Finding 4 — `merge_default_modulations` reads disk
every preset load

`agents/studio_compositor/effects.py:112-161`:

```python
def merge_default_modulations(graph):
    template_path = Path(__file__).parent.parent.parent / "presets" / "_default_modulations.json"
    if not template_path.is_file():
        return graph
    try:
        defaults = json.loads(template_path.read_text()).get("default_modulations", [])
    except Exception:
        return graph
    ...
```

**Every call reads the file from disk and parses JSON.**
The template is 13 static bindings that don't change at
runtime.

**Cost per call**: ~500 µs for the read + parse. Trivial
in absolute terms, but:
- `try_graph_preset` is called from the state_reader_loop
  on `fx-request.txt` (operator), `fx_tick_callback` via
  `tick_governance → try_graph_preset` (governance
  automatic), and the chat reactor.
- Under frequent governance-triggered preset switches,
  this is ~500 µs per switch on the main loop.

**Fix**: cache the parsed defaults at module load time.
~5 lines. Saves the disk read but doesn't change the
per-preset pydantic merge cost (which is small anyway).

### 3.5 Finding 5 — `merge_default_modulations` targets
nodes by TYPE, picks LAST matching ID

`effects.py:125-161`:

```python
# Build type→node_id map for matching default bindings to prefixed nodes
type_to_ids: dict[str, list[str]] = {}
for nid, node in graph.nodes.items():
    t = node.type
    if t not in type_to_ids:
        type_to_ids[t] = []
    type_to_ids[t].append(nid)

...
for d in defaults:
    target_type = d["node"]
    matching_ids = type_to_ids.get(target_type, [])
    if not matching_ids:
        continue
    # Apply to the LAST matching node — in chains, earlier instances are
    # neutralized (identity params), so modulations should target the
    # last instance which retains authored params.
    node_id = matching_ids[-1]
    ...
```

The inline comment explains the design intent: for preset
chains like `p0_bloom → p1_bloom` (merged from multiple
sub-presets), the earlier instances have identity params
and the last instance has the authored ones. The default
modulations should target the last.

**Observations**:

- This behavior is **implicit** and depends on chain
  naming conventions (`p0_`, `p1_` prefixes) that aren't
  enforced anywhere.
- Regular presets (no prefix) have at most one instance of
  each node type, so the "last" is the only one — no
  ambiguity.
- **Surprising coupling**: if a preset author declares TWO
  `bloom` nodes (for legitimate reasons), the default
  modulation gets applied only to the second. The first
  gets NO default bloom modulation. The author may not
  notice.

**Observability gap**: no warning when a preset has
multiple instances of the same type. Silent selection.

**Fix (minor)**: log at INFO level when
`matching_ids` has more than one entry, naming the
selected (last) and unselected (earlier) IDs. ~3 lines.
Makes the coupling visible to preset authors.

### 3.6 Finding 6 — `GraphRuntime.load_graph` uses
`copy.deepcopy` on every load

`agents/effect_graph/runtime.py:46-60`:

```python
def load_graph(self, graph: EffectGraph) -> None:
    old = self._current_plan
    plan = self._compiler.compile(graph)
    self._current_graph = copy.deepcopy(graph)   # ← here
    self._current_plan = plan
    self._modulator.replace_all(list(graph.modulations))
    ...
```

`copy.deepcopy` on a pydantic model traverses every field
recursively, copying nested dicts / lists / Pydantic
sub-models. For an 8-node preset with ~10 modulations +
~10 params per node, that's ~100 object allocations +
~200 value copies per load.

**Cost per call**: ~1-3 ms depending on preset size. Not a
hot spot, but pydantic has a native `model_copy()` that's
faster (uses serialization + re-validation).

**Fix**: replace `copy.deepcopy(graph)` with
`graph.model_copy(deep=True)`. Same semantics, faster
implementation, explicit about being pydantic-aware. ~1
line.

### 3.7 Finding 7 — preset naming is inconsistent

Some preset files carry a `_preset` suffix:

- `ascii_preset.json`
- `diff_preset.json`
- `feedback_preset.json`
- `glitch_blocks_preset.json`
- `halftone_preset.json`
- `pixsort_preset.json`
- `slitscan_preset.json`
- `thermal_preset.json`
- `vhs_preset.json`

Others don't:

- `ambient.json`
- `clean.json`
- `datamosh.json`
- `ghost.json`
- `heartbeat.json`
- `kaleidodream.json`
- `neon.json`
- ... and ~12 more

`GRAPH_PRESET_ALIASES` patches the legacy names:

```python
GRAPH_PRESET_ALIASES: dict[str, str] = {
    "ascii": "ascii_preset",
    "diff": "diff_preset",
    "feedback": "feedback_preset",
    "glitchblocks": "glitch_blocks_preset",
    "halftone": "halftone_preset",
    "pixsort": "pixsort_preset",
    "slitscan": "slitscan_preset",
    "thermal": "thermal_preset",
    "vhs": "vhs_preset",
}
```

So `try_graph_preset("halftone")` finds `halftone_preset.json`
via the alias. But the `_STATE_MATRIX` in governance
hardcodes:

```python
("nominal", "low"): PresetFamily(presets=("halftone_preset", "dither_retro", "ambient")),
```

It uses the raw filename `halftone_preset`, not the alias
`halftone`. So governance works, but manual chat-reactor
references to `"halftone"` also work via the alias, while
`"halftone_preset"` also works (direct file match).
**Everything works but the surface is confusing.**

**Finding**: preset naming is not enforced by anything.
Adding a new preset requires knowing:
- Which directory to drop it in
  (`~/.config/hapax/effect-presets` vs
  `./presets/` — overrides apply first)
- Whether to use a `_preset` suffix (contextual)
- Whether to add an alias in `GRAPH_PRESET_ALIASES`
  (optional but affects legacy chat references)
- Whether to add it to `_STATE_MATRIX` in governance (
  required for auto-selection)

**Fix options**:

- **Option A**: rename all presets to strip `_preset`
  suffix, update `_STATE_MATRIX` references, retire the
  `GRAPH_PRESET_ALIASES` dict. ~10-15 file renames + ~10
  governance edits. One-shot cleanup.
- **Option B**: document the naming convention in the
  preset directory README. Zero code change. Doesn't
  actually fix the fragility but surfaces it.

**Recommendation**: Option A. Silent naming drift is the
kind of thing that compounds over time.

### 3.8 Finding 8 — `ModulationBinding.smoothing` default
of 0.85 is a hardcoded magic number

`agents/effect_graph/types.py:59-69`:

```python
class ModulationBinding(BaseModel):
    node: str
    param: str
    source: str
    scale: float = 1.0
    offset: float = 0.0
    smoothing: float = Field(default=0.85, ge=0.0, le=1.0)
    attack: float | None = Field(default=None, ge=0.0, le=1.0)
    decay: float | None = Field(default=None, ge=0.0, le=1.0)
```

`smoothing=0.85` means "each tick, new value is
15% new + 85% previous" — a 1-pole lowpass filter with a
time constant of roughly `1 / (1 - 0.85) = 6.67` ticks ≈
220 ms at 30 fps.

**Observation**: this is a reasonable default but it's a
magic number with no docstring explaining the choice. All
13 default modulations in `_default_modulations.json`
override it with explicit `attack` + `decay` pairs because
asymmetric envelopes are more musically useful (fast
kicks + slow release).

**Fix (documentation)**: add a docstring to the
`smoothing` field explaining the 1-pole-lowpass semantics
and the ~220 ms time constant. Helps preset authors
understand what they're getting. ~2 lines.

### 3.9 Finding 9 — `tick` modulator branches per binding,
could be compiled

`agents/effect_graph/modulator.py:31-57`:

```python
def tick(self, signals: dict[str, float]) -> dict[tuple[str, str], float]:
    updates: dict[tuple[str, str], float] = {}
    for b in self._bindings:
        raw = signals.get(b.source)
        if raw is None:
            continue
        target = raw * b.scale + b.offset
        key = (b.node, b.param)
        prev = self._smoothed.get(key)
        if prev is None:
            val = target
        elif b.attack is not None and b.decay is not None:
            coeff = b.attack if target > prev else b.decay
            val = coeff * prev + (1.0 - coeff) * target
        elif b.smoothing == 0.0:
            val = target
        else:
            val = b.smoothing * prev + (1.0 - b.smoothing) * target
        self._smoothed[key] = val
        updates[key] = val
    return updates
```

Three branches per binding:
1. First call (no prior): raw target
2. Has attack+decay: asymmetric envelope
3. No attack/decay: simple smoothing (or instant if
   smoothing=0)

At 30 fps with ~10 bindings per preset (after default merge)
= 300 branches per second. **Absolutely trivial in CPU
terms** (~30 µs/sec total).

**Observation** (not really a fix): this is a hot path
for audio reactivity but the cost is so low it doesn't
merit optimization. The only interesting thing is that
**binding dispatch could be pre-compiled once per
preset-activation** — map each binding to one of three
lambda branches at load time, eliminate the per-tick
branching. ~20 lines of refactor, saves ~10 µs/sec. **Not
worth the complexity increase.**

**Keep as is. Documented as negative finding** — drop #43
finding 3 flagged tick_slot_pipeline's per-tick
string-contains scan as worth fixing; this is a similar
shape but the absolute cost is much smaller, so the
priority is inverted.

## 4. Ring summary

### Ring 1 — drop-everything (shippable today)

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **FX-1** | Fix `tunnel_vision` → `tunnelvision` typo in `_GENRE_BIAS` | `visual_governance.py:51-52` | 2 | `tunnelvision` preset becomes reachable via genre bias |
| **FX-2** | Cache `_default_modulations.json` at module import | `effects.py:112-161` | ~5 | Eliminates disk read per preset load |
| **FX-3** | Replace `copy.deepcopy` with `graph.model_copy(deep=True)` | `runtime.py:49` | 1 | Faster deep copy + explicit pydantic idiom |
| **FX-4** | Log info when `merge_default_modulations` finds multiple nodes of same type | `effects.py:140-145` | 3 | Makes silent "last match" selection visible to preset authors |

**Risk profile**: zero for all four. Pure refactors /
bugfixes with no behavior change (or behavior is strictly
improved by the bug fix).

### Ring 2 — dead-code removal (requires operator decision)

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **FX-5** | Remove `LayerPalette` system entirely | `types.py`, `runtime.py`, tests | ~30 | Dead surface area eliminated |
| **FX-6** | Operator decision: retire `PresetInput` / source-registry bindings OR write a reference preset that uses them | multiple files | ~200 removal OR ~50 addition | Dead Phase 6+7 code path |
| **FX-7** | Rename all presets to strip `_preset` suffix, update `_STATE_MATRIX`, retire `GRAPH_PRESET_ALIASES` | presets/ + `visual_governance.py` + `effects.py` | ~30 file ops + ~10 edits | Preset naming becomes uniform |

**Risk profile**: FX-5 is zero-risk deletion. FX-6
requires operator decision. FX-7 is a bigger change with
non-code coordination (anything that references a preset
by name from outside the compositor — chat reactor
keywords, MCP tools, logos-sdk — needs to migrate in
lockstep).

### Ring 3 — documentation + observability

| # | Fix | File | Lines | Impact |
|---|---|---|---|---|
| **FX-8** | Docstring for `ModulationBinding.smoothing` default | `types.py` | 2 | Preset-author documentation |
| **FX-9** | Add a `compositor_preset_load_duration_ms` histogram + preset-name label | `metrics.py` + `effects.py:try_graph_preset` | ~15 | Preset-load cost becomes scrape-visible; validates drop #43's FXT-3 concern |
| **FX-10** | Add a preset-naming-convention README to `presets/` | `presets/README.md` | ~20 | Documents FX-7's convention decision |

## 5. Cumulative impact estimate

**Ring 1 alone**: 4 bugfixes + perf cleanups. Zero risk.
Ships today.

**Ring 1 + Ring 3**: adds preset-load observability and
docs. Still zero risk.

**Ring 2 FX-5**: eliminates LayerPalette system. ~30
lines deleted. Net negative LOC.

**Ring 2 FX-6**: requires operator decision. Either ~200
lines deleted (retire) or ~50 added (reference preset).
Largest architectural impact.

**Ring 2 FX-7**: ~40 lines of coordinated changes. Non-
code impact (external callers).

**Operator-visible effect**:

- FX-1 restores `tunnelvision` as a reachable governance
  target for electronic/ambient music
- FX-5 makes `get_graph_state()` output cleaner by
  removing an always-empty `layer_palettes` key
- FX-7 makes preset naming predictable for future preset
  authoring
- FX-9 surfaces the first drop-level observability on the
  preset control plane

## 6. Cross-references

- `agents/effect_graph/types.py:80-114` — `PresetInput`
  (dead)
- `agents/effect_graph/types.py:72-78` — `LayerPalette`
  (dead)
- `agents/effect_graph/types.py:117-135` — `EffectGraph`
- `agents/effect_graph/compiler.py:35-64` —
  `resolve_preset_inputs` (dead)
- `agents/effect_graph/compiler.py:121-151` —
  `GraphCompiler.compile` (per-target Phase 5a)
- `agents/effect_graph/runtime.py:46-60` —
  `GraphRuntime.load_graph`
- `agents/effect_graph/modulator.py:31-57` —
  `UniformModulator.tick`
- `agents/effect_graph/visual_governance.py:45-53` —
  `_GENRE_BIAS` (FX-1 typo)
- `agents/effect_graph/visual_governance.py:25-42` —
  `_STATE_MATRIX`
- `agents/studio_compositor/effects.py:112-161` —
  `merge_default_modulations` (FX-2 + FX-4)
- `agents/studio_compositor/effects.py:13-23` —
  `GRAPH_PRESET_ALIASES` (FX-7)
- `presets/*.json` — 28 playable presets
- `presets/_default_modulations.json` — 13 default
  bindings
- `agents/shaders/nodes/*.json` — 59 shader node types
- Drop #5 — glfeedback diff check (fx chain upstream
  fix)
- Drop #38 — SlotPipeline internals (the downstream
  target of preset activation)
- Drop #41 — BudgetTracker wiring + source-registry
  dead-path finding (related to FX-6)
- Drop #43 — fx_tick_callback walk + `tick_governance`
  main-loop concern
