# Phase 5: Multi-Output Support — Design Spec

**Date:** 2026-04-12
**Status:** Approved (self-authored, alpha session)
**Epic:** `docs/superpowers/plans/2026-04-12-compositor-unification-epic.md`
**Phase:** 5 of 7
**Risk:** Medium-high (touches the graph compiler and Rust pipeline)
**Depends on:** Phase 2–4 complete

---

## Purpose

Relax the single-output constraint so one Layout (or one EffectGraph)
can produce multiple independent render targets — stream video out,
wgpu winit window, NDI source, thumbnail, HDR mirror — without
duplicating the graph or routing through brittle ad-hoc plumbing.

After Phase 5, **one frame description compiles to one execution plan
that fans out to multiple targets.** The host decides per target where
the output goes (`/dev/video42`, the wgpu window, an NDI socket).
Cameras decode once and feed every target. Effect chains run once per
target only when their outputs differ.

This is the unification point for the two parallel pipelines (GStreamer
+ wgpu). After Phase 5b ships, the GStreamer side becomes pure ingest
(cameras, v4l2 sources, audio) and the wgpu side becomes the only
compositing path.

---

## Scope

Two sub-phases. Phase 5a is mechanical and low-risk; Phase 5b is the
larger architectural rewire.

### Phase 5a — Relax single-output constraint (small, in this round)

1. The graph compiler accepts **>= 1** output nodes (not exactly one).
2. Each output node carries a `target` name. Default is `"main"` for
   backwards compatibility — existing graphs with one unnamed output
   become a single-target plan named `main`.
3. `ExecutionPlan` carries `targets: dict[str, list[ExecutionStep]]`
   instead of a flat `steps` list. A `steps` property is preserved
   for callers that want the union (concatenated in stable target
   name order).
4. `wgsl_compiler.py` emits `plan.json` v2 with `{"version": 2,
   "targets": {"main": {"passes": [...]}}}`. v1 plans (a flat
   `passes` list) are still parsed by the Rust side.
5. The Rust `DynamicPipeline` parses both v1 and v2; v1 plans are
   wrapped into a single-target `main` map at parse time. The render
   loop currently walks the `main` target only — additional targets
   land in Phase 5b.

**Effect for the live system in 5a:** zero. Today's vocabulary graph
has one output node, compiles to a single `main` target, and the
Rust executor renders exactly the same passes it did before.
Multi-output support exists in the data plane but no graph yet uses
it.

### Phase 5b — Unify GStreamer + wgpu under one model (large, deferred)

Add `Surface(kind=video_out, target="gstreamer_video")` and
`Surface(kind=video_out, target="wgpu_window")`. Each becomes a target
in the compile phase. The wgpu side renders both targets per frame;
the host wires the appropriate output buffer to each sink (v4l2sink
for `/dev/video42`, the winit swapchain for the on-screen window).

The GStreamer compositor reduces to pure ingest — cameras, v4l2
sources, audio — producing textures that feed the wgpu compositor.
The wgpu side produces the final composited frame for both outputs.

**This is the longest-running change in the epic.** It rewires the
live system and likely needs to ship as a series of smaller
migrations (one content type at a time moving from GStreamer
composition to wgpu composition). 5b is *not* in scope for this
round.

---

## Phase 5a: relax single-output constraint

### File structure

| Layer | Files | Change |
|---|---|---|
| Types | `agents/effect_graph/types.py` | New `OUTPUT_NODE_TYPE` constant; default target naming convention |
| Compiler | `agents/effect_graph/compiler.py` | Validate ≥1 output (not exactly one); build per-target ExecutionPlan |
| ExecutionPlan | `agents/effect_graph/compiler.py` | Add `targets: dict[str, list[ExecutionStep]]`; `steps` becomes a computed concatenation |
| Plan emit | `agents/effect_graph/wgsl_compiler.py` | Emit v2 format with `targets` dict |
| Rust parse | `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs` | `PlanFile` accepts both `passes` (v1) and `targets` (v2); internal storage is target-keyed |
| Tests | `tests/effect_graph/test_wgsl_compiler.py` | Multi-output graph compiles to multiple targets |
| Tests | `tests/effect_graph/test_all.py` | Compiler accepts multi-output; each target is independently topo-sorted |

### Target name resolution

Output nodes get their target name from the `params.target` key.
Default is `"main"` when unset:

```python
# Old (single output, no target):
{"output": {"type": "output"}}

# New (single output, default target "main" — same as old):
{"output": {"type": "output"}}

# New (single output, explicit target):
{"output": {"type": "output", "params": {"target": "preview"}}}

# New (multi output, two targets):
{
    "main_out": {"type": "output", "params": {"target": "main"}},
    "hud_out":  {"type": "output", "params": {"target": "hud"}},
}
```

Using `params.target` keeps the change additive — `NodeInstance.params`
is already a free dict, no schema migration needed for existing
presets.

### Per-target compilation

The compiler walks **backwards** from each output node, marking the
nodes reachable via the input dependency graph. Each output's
reachable set becomes one target's ExecutionStep list, topo-sorted
in the same way as today.

Shared subgraphs (a noise node feeding both `main_out` and `hud_out`)
appear in both targets' step lists today — Phase 5b will add
deduplication via shared intermediate textures. For Phase 5a, the
duplication is acceptable: the only graph in production has one
output, and the dedup pass needs the Phase 4c transient pool to land
in Rust first anyway.

### Compiler signature

```python
@dataclass
class ExecutionPlan:
    name: str
    targets: dict[str, list[ExecutionStep]] = field(default_factory=dict)
    layer_sources: set[str] = field(default_factory=set)
    transition_ms: int = 500

    @property
    def steps(self) -> list[ExecutionStep]:
        """Backwards-compat: union of all targets' steps in target name order."""
        out: list[ExecutionStep] = []
        for target_name in sorted(self.targets):
            out.extend(self.targets[target_name])
        return out

    @property
    def target_names(self) -> tuple[str, ...]:
        return tuple(sorted(self.targets))


class GraphCompiler:
    def compile(self, graph: EffectGraph) -> ExecutionPlan:
        edges = graph.parsed_edges
        self._validate(graph, edges)
        # Find all output nodes; each becomes a target.
        outputs = [
            (nid, n.params.get("target", "main"))
            for nid, n in graph.nodes.items()
            if n.type == "output"
        ]
        # Validate target names unique.
        target_names = [t for _, t in outputs]
        if len(target_names) != len(set(target_names)):
            raise GraphValidationError(
                f"Graph {graph.name!r}: duplicate target names: {target_names}"
            )
        targets: dict[str, list[ExecutionStep]] = {}
        for output_id, target_name in outputs:
            reachable = self._reachable_subgraph(graph, edges, output_id)
            order = self._topo_sort_subset(graph, edges, reachable)
            steps = self._build(graph, edges, order)
            targets[target_name] = steps
        return ExecutionPlan(
            name=graph.name,
            targets=targets,
            layer_sources={e.source_node for e in edges if e.is_layer_source},
            transition_ms=graph.transition_ms,
        )
```

The `_validate` method drops the `output_count != 1` check and
substitutes `output_count == 0` (a graph with no output is invalid).

`_reachable_subgraph` is a new helper: BFS from `output_id` along
incoming edges. The result is the set of nodes whose output the
target depends on.

### wgsl_compiler v2 format

```python
def compile_to_wgsl_plan(graph: EffectGraph) -> dict[str, object]:
    plan: ExecutionPlan = compiler.compile(graph)
    targets: dict[str, dict[str, object]] = {}
    for target_name, steps in plan.targets.items():
        passes = _build_passes(steps, ...)  # existing per-step logic
        targets[target_name] = {"passes": passes}
    return {"version": 2, "targets": targets}
```

The key change: instead of returning `{"version": 1, "passes": [...]}`,
return `{"version": 2, "targets": {name: {"passes": [...]}}}`. The
single-target case is the common one and produces a one-key targets
dict.

### Rust PlanFile

```rust
#[derive(Debug, Deserialize)]
struct PlanFile {
    #[serde(default)]
    version: u32,
    /// v1 format: flat list of passes, single implicit "main" target.
    #[serde(default)]
    passes: Vec<PlanPass>,
    /// v2 format: named targets, each with its own pass list.
    #[serde(default)]
    targets: HashMap<String, TargetPlan>,
}

#[derive(Debug, Deserialize)]
struct TargetPlan {
    #[serde(default)]
    passes: Vec<PlanPass>,
}
```

At load time, the v1 → v2 normalization is one helper:

```rust
fn normalize_targets(plan: &PlanFile) -> HashMap<String, Vec<PlanPass>> {
    if !plan.targets.is_empty() {
        plan.targets
            .iter()
            .map(|(k, v)| (k.clone(), v.passes.clone()))
            .collect()
    } else {
        // v1 fallback: wrap flat passes into a "main" target.
        let mut out = HashMap::new();
        out.insert("main".to_string(), plan.passes.clone());
        out
    }
}
```

`DynamicPipeline.passes` becomes `passes_by_target: HashMap<String,
Vec<DynamicPass>>`. The render loop currently walks `passes_by_target
.get("main")` only — additional targets are reserved for Phase 5b.
This means today's vocabulary graph (single output, one target)
renders byte-identically.

### Tests

`tests/effect_graph/test_wgsl_compiler.py`:

- `test_single_output_emits_v2_plan` — version is 2, targets has one key "main"
- `test_single_output_default_target_name_is_main` — explicit check
- `test_multi_output_emits_multi_target_plan` — two outputs → two targets
- `test_explicit_target_name` — `params: {"target": "hud"}` produces target "hud"
- `test_v2_plan_target_passes_match_v1_shape` — each target's passes have the same fields v1 produced

`tests/effect_graph/test_all.py`:

- `test_compile_accepts_two_output_nodes` — compiler doesn't raise
- `test_compile_rejects_zero_output_nodes` — compiler does raise
- `test_compile_rejects_duplicate_target_names` — two outputs both named "main" → raise
- `test_execution_plan_steps_property_is_union` — steps property returns concatenated targets in stable order
- `test_per_target_topo_sort_independent` — two targets each get their own topologically-correct ordering

### Rust integration

A small Rust unit test parses a v2 plan with one target named "main"
and verifies the resulting `passes_by_target` map has one entry. A
second test parses a v1 plan and verifies the same structure (v1 →
v2 normalization). These live in `dynamic_pipeline.rs` if a tests
module exists, or as a doc test on `normalize_targets`.

### Acceptance

- `EffectGraph` graphs with multiple `type=output` nodes compile
  successfully into per-target ExecutionPlans.
- `wgsl_compiler.py` emits v2 plan.json with `version: 2`.
- The Rust `DynamicPipeline` parses both v1 and v2 plans.
- The vocabulary graph (single output) renders byte-identically.
- All Phase 5a tests pass (~10 new tests).
- `cargo check` clean.

### PR shape

- ~120 lines of Python (compiler + ExecutionPlan + wgsl_compiler)
- ~80 lines of Rust (PlanFile + normalize_targets + storage rename)
- ~150 lines of tests
- Total: ~350 lines net change

### Risk

Medium. The compiler change is mechanical but the ExecutionPlan
shape change touches every consumer of `plan.steps`. The backwards-
compat `steps` property keeps the existing call sites working
without rewrites. The Rust storage rename touches every site that
references `self.passes` — those become `self.passes_by_target
.get("main").unwrap_or(&Vec::new())` until Phase 5b multi-target
support arrives.

### Mitigation

- The `steps` property on `ExecutionPlan` is the explicit backwards-
  compat hook. Every existing caller continues to work.
- The Rust render loop only renders the `main` target this round;
  other targets are stored but unrendered. No visual change.
- v1 plan.json files (legacy on-disk artifacts) are still accepted
  via the `passes` fallback in `PlanFile`.

---

## Phase 5b: unify GStreamer + wgpu (deferred to a future round)

### Scope (out of scope for this round)

- Add `Surface(kind=video_out)` instances for `gstreamer_video` and
  `wgpu_window` targets in the canonical garage-door layout.
- Wire the host so each target's output buffer feeds the appropriate
  sink: v4l2sink for `gstreamer_video`, the winit swapchain for
  `wgpu_window`.
- Move camera ingest from "GStreamer composes" to "GStreamer ingests
  → wgpu composes". This is the multi-week migration step.

### Why defer

Phase 5b is "the longest-running change in this phase" per the master
epic plan. It rewires the live streaming pipeline, which means:

- Risk of streaming downtime if anything goes wrong
- Multiple content types need migrating one by one
- Validation requires running the live stream end-to-end through
  the new path

This is too much for one round. Phase 5a lands the data plumbing so
when Phase 5b starts, the multi-target compile output already exists
and the Rust executor's storage already supports per-target render
plans. 5b only needs to:

1. Add a render loop that walks all targets (not just "main")
2. Add output texture binding per target
3. Add host-side sink wiring

That's a clean, self-contained PR once 5a is in place.

---

## Cross-sub-phase concerns

### Branch strategy

```
main
 └── feat/phase-5a-multi-target-plans   (PR A)
```

Phase 5b lands later as one or more separate PRs against main once
the data plumbing is proven.

### Coexistence with current rendering

Phase 5a is **purely additive in behavior**. The live vocabulary
graph has one output node and produces a single-target plan. The
Rust executor renders that single target via the same code path as
before. Future graphs can introduce additional targets, but no
existing graph needs to.

### Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| ExecutionPlan shape change breaks downstream callers | Medium | Low | Backwards-compat `steps` property |
| Rust passes_by_target rename breaks render loop | Medium | High | Render loop reads `main` target only — same passes as today |
| v1 plan.json files in /dev/shm break after Rust update | Low | Medium | PlanFile parses both `passes` and `targets` fields |
| Multi-output topo sort doesn't handle shared subgraphs | Medium | Low | 5a accepts duplication; 5b adds dedup with the Phase 4c pool |
| Target name collisions go unreported | Low | Low | Compiler validates target name uniqueness, raises GraphValidationError |

### Success metrics

Phase 5a is complete when:

- Multi-output graphs compile cleanly
- Single-output graphs (the entire current preset library) continue
  to compile and produce byte-identical render output
- v1 plan.json files load successfully on the Rust side
- v2 plan.json files load successfully on the Rust side
- All existing wgsl_compiler tests pass
- All new Phase 5a tests pass

---

## Not in scope

Phase 5a does not:
- Render any target other than `main` (Phase 5b)
- Add `video_out` Surfaces to the canonical layout (Phase 5b)
- Move GStreamer composition to wgpu composition (Phase 5b)
- Deduplicate shared subgraphs across targets (Phase 5b + Phase 4c-rust)
- Add per-target output texture pooling (Phase 4c-rust follow-up)

Phase 5a is the "land the data shape" sub-phase.
