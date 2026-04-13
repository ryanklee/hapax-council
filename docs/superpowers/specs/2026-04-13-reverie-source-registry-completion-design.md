# Reverie + Source Registry Completion Epic — Design

**Status:** draft
**Date:** 2026-04-13
**Author:** alpha session (autonomous epic execution)
**Parent spec:** `docs/superpowers/specs/2026-04-12-compositor-source-registry-foundation-design.md`
**Parent plan:** `docs/superpowers/plans/2026-04-12-compositor-source-registry-foundation-plan.md` (4049 lines, 29 TDD tasks)
**Relationship:** this doc is the umbrella design for finishing the parent plan + absorbing adjacent reverie/observability work discovered after the parent spec was frozen. Where the parent spec is authoritative, this doc references it and does not duplicate.

## Summary

Complete the compositor source-registry epic (parent plan) so reverie, the three cairo overlays, and — via persistent `appsrc` pads — every compositor source becomes a first-class, layout-declared, runtime-mutable, preset-routable visual producer. In the same epic, close three adjacent observability gaps discovered during the 2026-04-13 discovery sweeps (`BETA-FINDING-2026-04-13-C` freshness masking, pool metrics IPC exposure, dormant reverie override paths) so the rendering pipeline gains both the PiP/control machinery the operator asked for AND the freshness contracts that prevent silent masked failures in the always-on producers the new machinery creates.

This is **one epic in nine phases**, owned by a single session running to completion without intervention. Each phase ships as its own PR with a green test suite. Phases are ordered by hard dependency; parallelism is avoided because the compositor service reads Python directly from the alpha worktree and split-worktree work has repeatedly produced silent regressions in this repo (cf. PR #555 / PR #710, PR #696 / PR #700, PR #731 OOM cascade).

## Scope

### In scope

**Parent-plan tasks still open (18 of 29):**

- Phase C tasks 8–11 — TokenPole/Album/Sierpinski natural-size migration + final shim sweep
- Phase E tasks 15–16 — `blit_scaled` helper + `_pip_draw` refactor to walk `LayoutState`
- Phase F tasks 18–19 — `headless::Renderer` in `src-imagination/` + `HAPAX_IMAGINATION_HEADLESS=1` systemd env
- Phase G tasks 20–22 — `command_server.py` UDS handler + Tauri pass-through + file-watch with debounced auto-save
- Phase H tasks 23–25 — `gst_appsrc()` on runner + reader + `fx_chain.py` persistent appsrc branches + main-layer integration test
- Phase I tasks 26–27 — `Preset.inputs` schema + loader resolution against `SourceRegistry`
- Phase J tasks 28–29 — acceptance criteria sweep + final push

**Parent-plan task 14** (D14 — `StudioCompositor.start()` wiring) is done in PR #735, merged first as Phase 1 of this epic.

**Adjacent observability work (new, not in parent plan):**

- **Imagination freshness gauge** — generalized fix for `BETA-FINDING-2026-04-13-C`. Every always-on producer with a `try/except + log.warning + return` pattern publishes an `*_age_seconds` gauge + `*_published_total` counter, and health-monitor flags stale producers. Seeded with `imagination_loop`; generalized into a tiny helper module.
- **Pool metrics IPC exposure** — `DynamicPipeline::pool_metrics()` (shipped in PR #697) has no external consumer. Adds a Rust shm-writer tick + a Python reader + four `reverie_pool_*` Prometheus gauges.
- **F7 decision** — the dormant `signal.{9dim}` override path in `dynamic_pipeline.rs` (lines 812–828) reads keys no Python side writes. Decide: wire `visual_chain` to write them, or delete the Rust arms. Documented in PR #718, decision pending.
- **F10 verification** — `ImaginationState.content_references` field, suspected orphaned from pre-affordance-pipeline era. Grep + delete if unused.
- **Amendment 4 verification** — reverie reverberation cadence acceleration on surprise. Pathway wired, never observed post-imagination-recovery. Observational.

### Out of scope (deferred, with rationale)

- **`BETA-FINDING-2026-04-13-B` gmail-sync inotify flood** — crosses reactive engine + sync-agent boundaries, needs operator routing decision on fix surface (diff-before-write vs. reactive-engine debounce vs. exclude from watch vs. logos-api process split). Flagged separately in the relay, not bundled here.
- **Sierpinski wgpu integration** — the Apr-11 plan (`docs/superpowers/plans/2026-04-11-sierpinski-visual-layout.md`) predates the source-registry and assumes the old reverie vocabulary structure. Needs rebase onto the new source-registry + `sat_sierpinski_*` satellite path before it can ship. Separate follow-up epic.
- **Vinyl shader / vinyl visual plugin** — no shader file exists, no spec exists. Net-new creative work; specify in a separate design doc once the source-registry surface is stable so a new backend slots in trivially via `class_name` dispatch.
- **Affordance recruitment hook for layouts** — explicit non-goal of parent PR 1. The mechanism (`compositor.assignment.add` / `remove` commands) is listed as a PR 2 candidate in the parent spec. Defer until the source-registry machinery is in production use for at least a week.
- **Runtime source registration / deregistration** — non-goal of parent PR 1. Adding/removing sources at runtime requires rebuilding the GStreamer pipeline mid-stream; the correct vehicle is a preset chain switch on pre-existing appsrc pads (Phase H + I enable this), not on-the-fly source creation.
- **Animation tweens on geometry changes** — non-goal of parent PR 1. Snap-only. Operator can build tweens on top of `compositor.surface.set_geometry` in a frontend module if desired.
- **Main-layer assignments promoting non-camera sources** — non-goal of parent PR 1. Mechanism ships (Phase H); the default layout stays current behavior to avoid silent visible-output changes under an operator who has not explicitly opted in.
- **Sprint 0 G3 gate state mismatch** — carried from beta-3 / beta-4 handoffs. Outside reverie / compositor scope entirely.

## Dependency order and parallelism decision

Every phase ships serially on a fresh branch off the latest main. No parallel worktrees; no branch stacking beyond one level. The parent plan's delta session retired mid-epic precisely because split worktrees produced false-positive merge complexity. Serializing is strictly faster in this repo because:

1. The compositor reads `agents/studio_compositor/*.py` directly from alpha's primary worktree. Any feature-branch work under alpha is "dormant in production" until the branch merges to main AND `rebuild-services.timer` fires (or the worktree cycles through main). Two concurrent feature branches multiply this tension.
2. Tests are per-phase cumulative — earlier phases ship machinery later phases build on. A parallel branch would have to rebase after each merge.
3. CI takes ~5 min per PR. At 9 phases × ~5 min CI + ~5 min review = ~90 min serial, vs. unbounded rebase loops if parallel.

```
Phase 1: merge PR #735 (no new code)
    ↓
Phase 2: Phase C tasks 8-11 (natural-size migration)
    ↓
Phase 3: Phase E tasks 15-16 (render refactor — reverie appears UR)
    ↓
Phase 4: Phase F tasks 18-19 (reverie headless mode — winit window retires)
    ↓
Phase 5: Phase G tasks 20-22 (command server — runtime mutation)
    ↓
Phase 6: Phase H tasks 23-25 (appsrc pads — railroad proof)
    ↓
Phase 7: Phase I tasks 26-27 (preset schema extension)
    ↓
Phase 8: Adjacent observability (freshness gauge, pool metrics IPC, F7/F10/Amendment-4)
    ↓
Phase 9: Phase J tasks 28-29 (AC sweep, final push, retirement handoff)
```

Phase 8 is scheduled between Phase 7 and Phase 9 rather than earlier because:
(a) the freshness-gauge generalization should cover every producer the epic creates, and Phases 2–7 create several of them (LayoutState, SourceRegistry, appsrc push threads, UDS command server, file watcher);
(b) the pool-metrics IPC exposure depends on the appsrc push path's observability conventions set by Phase 6;
(c) the F7 decision depends on whether any Phase 3 / Phase 5 work ends up writing `signal.*` keys anyway (eliminating the dead-code question).

Within a phase, tasks run in the order the parent plan specifies. Parent-plan task instructions are authoritative; this doc adds no task-level changes to the parent plan for Phases 2–7 and 9.

## Phase details

### Phase 1 — Merge PR #735 (Task 14)

**Scope:** merge the existing open PR without changes. The branch is `feat/phase-d-task-14-layout-wiring` at `cc6d07005`, tests pass locally, CI was running at the time this design was frozen. Wait for CI green, squash-merge, delete branch, pull.

**Exit criteria:**

- PR #735 merged
- Local branch deleted
- `git log --oneline -1 origin/main` shows the merge commit
- `/dev/shm/hapax-imagination/uniforms.json` behavior unchanged (task 14 is render-path inert — the `LayoutState` it builds has no reader yet)

### Phase 2 — Cairo natural-size migration (parent tasks 8–11)

**Scope:** per parent plan tasks 8–11. The key delta-handoff note is that Task 8 is the only nontrivial migration — `token_pole.py` has `OVERLAY_X=20`, `OVERLAY_Y=20`, `OVERLAY_SIZE=300` constants referenced throughout the render method at 17 sites (lines 148–358 per grep). Task 9 (Album) and Task 10 (Sierpinski) have no `OVERLAY_*` constants and likely only need a signature audit + a test asserting natural-size rendering. Task 11 is the final shim sweep: confirm the legacy facades (`TokenPole`, `AlbumOverlay`, `SierpinskiRenderer`) still work for `fx_chain._pip_draw`'s legacy path (it still uses `compositor._album_overlay.draw(cr)` etc.), because Phase 3 flips that path — until then the legacy facades must keep working.

**Design delta from parent plan:** none. The parent plan's tasks are complete as written.

**Risk:** TokenPole refactor. The spiral rendering coordinates, corner radius arcs, scaled pixbuf blit, gravity center, text positioning — all reference `OVERLAY_X + SOMETHING` and `OVERLAY_Y + SOMETHING`. The refactor is a find-replace of `OVERLAY_X` → `0` and `OVERLAY_Y` → `0` in the render method, plus deleting the constants and updating tests. Visual regression test required; delta deferred precisely this task because the test fixture path was unclear. Approach: write a golden-image test that renders the natural-size output, hash the pixels, and compare against a pre-committed golden for regression.

**Exit criteria:**

- `tests/test_token_pole.py` / `tests/test_album_overlay.py` / `tests/test_sierpinski_renderer.py` all pass at natural size
- `compositor.py` and `fx_chain.py` unchanged — legacy facade path still routes through `compositor._token_pole.draw(cr)` because Phase 3 hasn't flipped the render path yet
- `uv run pytest tests/studio_compositor/ tests/test_studio_compositor.py -q` green

### Phase 3 — Render path flip (parent tasks 15–16)

**Scope:** per parent plan tasks 15 (`blit_scaled` helper) and 16 (`_pip_draw` refactor). This is the phase where the compositor's visible output changes. After merge, on next `rebuild-services.timer` firing or compositor restart, the render loop walks `LayoutState.get().assignments` instead of `_album_overlay.draw(cr)` / `_token_pole.draw(cr)` / `_sierpinski_renderer.draw(cr)`. The four PiPs declared in `config/compositor-layouts/default.json` — Vitruvian UL, reverie UR (placeholder until Phase 4 headless), album LL, sierpinski LR (unassigned) — become the source of truth.

**Design delta from parent plan:** none critical, but add two invariants the parent plan implies but does not state explicitly:

1. **Backward-compat shim for the legacy `_pip_draw` during transition.** Until Phase 3 merges, `_pip_draw` uses the legacy path. After Phase 3 merges, the legacy facades (`compositor._token_pole`, `_album_overlay`, `_sierpinski_renderer`) are still initialized in `compositor.py` but their `draw(cr)` methods are only called by deprecated code paths. Mark the legacy `TokenPole.draw()` / `AlbumOverlay.draw()` / `SierpinskiRenderer.draw()` methods `@deprecated` with a pointer to Phase 3 removal. Full deletion is deferred to Phase 9's AC sweep, after production verification.

2. **One-frame-old source cache.** When `_pip_draw` walks LayoutState and a source's `get_current_surface()` returns None (source hasn't rendered yet), blit nothing and increment a `compositor_source_frame_skip_total{source_id}` counter — do NOT fall back to the legacy path. The legacy path must die for Phase 3 to be honest.

**Risk:** highest-visibility change in the epic. Live compositor output may transiently flicker during rebuild-services restart. Test the refactor against a fixture LayoutState before deploy.

**Exit criteria:**

- After merge + restart, `jq '.sources[].id' /tmp/compositor-layout.json` (or equivalent introspection) lists the declared sources
- The compositor frame visually matches the default layout at UL/UR/LL quadrants (reverie UR is still the SHM fallback from PR #723, not yet headless)
- Existing tests pass
- New `test_pip_draw_refactor.py` covers LayoutState walking + scale-on-blit math

### Phase 4 — Reverie headless mode (parent tasks 18–19)

**Scope:** per parent plan tasks 18 (`headless::Renderer` in `src-imagination/src/headless.rs` + branch in `src-imagination/src/main.rs`) and 19 (systemd unit `Environment=HAPAX_IMAGINATION_HEADLESS=1`). PR #723 already ships the producer-side second SHM output (`/dev/shm/hapax-sources/reverie.rgba` + sidecar). Phase 4 is the consumer-side: `hapax-imagination` runs without a winit window when the env var is set, using an offscreen wgpu texture for `DynamicPipeline::render`.

**Design delta from parent plan:** none. The parent plan's task instructions are sufficient.

**Risk:** the existing `GpuContext` uses `wgpu::Surface::get_current_texture()` which requires a swapchain. Headless mode skips that entirely and calls render into an owned texture. Preserve `HAPAX_IMAGINATION_HEADLESS=0` as a debug opt-out.

**Exit criteria:**

- `HAPAX_IMAGINATION_HEADLESS=1 hapax-imagination` runs without a Wayland surface
- `/dev/shm/hapax-sources/reverie.rgba` mtime advances every ~16ms at 60fps (sidecar `frame_id` increments)
- `/dev/shm/hapax-visual/frame.{jpg,rgba}` continues to populate (the existing HTTP :8053 frame server must keep working)
- Systemd unit update lands but is NOT deployed until compositor Phase 3 has been running cleanly for one `rebuild-services.timer` cycle (safety: don't retire the debug window while the replacement is unproven)

### Phase 5 — Command server + control path (parent tasks 20–22)

**Scope:** per parent plan tasks 20 (`command_server.py` UDS handler), 21 (Tauri Rust pass-through + frontend command registry), 22 (file-watch + debounced auto-save). This is the "move/resize PiPs mid-stream" half of the operator's original ask.

**Design delta from parent plan:** none critical. Implementation note: use `inotify_simple` or mtime polling — the parent plan leaves the choice open; delta's deferred guidance is mtime polling because `inotify_simple` adds a runtime dependency and the layout file is tiny (debounce cadence dominates staleness).

**Risk:** UDS socket at `$XDG_RUNTIME_DIR/hapax-compositor.sock` adds a new IPC surface. Restart semantics must not leak socket files; `command_server` registers `atexit` cleanup.

**Exit criteria:**

- From `window.__logos.execute("compositor.surface.set_geometry", {...})`, a PiP moves within ≤1 frame
- File-watch reload picks up hand-edits to `~/.config/hapax-compositor/layouts/default.json` within ≤2s
- Self-write detection prevents reload loops
- Error responses match the parent spec's error table (unknown_surface, invalid_geometry, etc.)

### Phase 6 — Persistent appsrc pads (parent tasks 23–25)

**Scope:** per parent plan tasks 23 (`gst_appsrc()` on runner + reader), 24 (`fx_chain.py` constructs persistent appsrc branches), 25 (main-layer integration test). The "railroad tracks" proof: reverie's RGBA bytes reach `glvideomixer`'s output pad via an augmented test layout fixture, even though `default.json` does not make it visible.

**Design delta from parent plan:** none.

**Risk:** GStreamer pipeline topology change. The parent spec commits to `alpha=0` on inactive pads — this lets preset switches be alpha-snap decisions rather than pipeline rewiring. Verify with `gst-inspect-1.0 glvideomixer` that the sink pad has an `alpha` property (it does per the spec, re-confirm during implementation).

**Exit criteria:**

- `test_main_layer_path.py` passes: reverie RGBA bytes appear in the glvideomixer output buffer with ≤5% tolerance via golden-image comparison
- `ps -C gst-launch-1.0` (or whatever the compositor invokes) shows no new processes vs. pre-Phase-6 baseline — pads are in-process, not separate pipelines
- `default.json` runtime output unchanged — no visible main-layer promotion

### Phase 7 — Preset schema extension (parent tasks 26–27)

**Scope:** per parent plan tasks 26 (`Preset.inputs: list[PresetInput] | None = None`) and 27 (preset loader resolves inputs against `SourceRegistry` with loud-fail on unknown pad). Enables preset chains to declare which sources feed `layer0`/`layer1`/`layer2` at load time.

**Design delta from parent plan:** none. Task 26 resolves the parent spec's open question 3 (load-time vs. tick-time resolution) to **load-time** — delta's recommendation and the one this epic honors.

**Exit criteria:**

- `Preset(inputs=[PresetInput(pad="reverie", as_="layer0")])` validates
- Loading a preset with an unknown pad raises `UnknownPresetInputError` with a structured message including the preset name and the unknown pad
- Existing presets that do not declare `inputs` continue to load unchanged

### Phase 8 — Adjacent observability hardening (new)

**Scope:** the five items enumerated in § Scope → In scope → Adjacent observability work.

This phase does not have a parent-plan counterpart. The task breakdown is inline in this doc and in the plan file (`docs/superpowers/plans/2026-04-13-reverie-source-registry-completion-plan.md`).

**Sub-design: Imagination freshness gauge + generalization**

Fix `BETA-FINDING-2026-04-13-C` via a reusable pattern. New module `shared/freshness_gauge.py`:

```python
class FreshnessGauge:
    """Per-producer freshness contract for always-on loops.

    Every always-on producer with a `try/except + log.warning + return` shape
    MUST own a FreshnessGauge instance. The gauge publishes:

    - `{name}_published_total` counter — incremented on every successful tick
    - `{name}_age_seconds` gauge — seconds since the last successful tick
    - An optional `{name}_last_error` Prometheus info metric for diagnosis

    The health monitor's check_{name}_freshness() helper reads the age gauge
    and flags stale producers. Subclasses of FreshnessGauge publish under
    different namespaces; the default is `prometheus_client.REGISTRY`.
    """

    def __init__(self, name: str, expected_cadence_s: float) -> None: ...
    def mark_published(self) -> None: ...  # increments counter, resets age
    def mark_failed(self, exc: BaseException | None = None) -> None: ...
    def age_seconds(self) -> float: ...
    def is_stale(self, tolerance_mult: float = 10.0) -> bool: ...
```

Seed with `imagination_loop`: instantiate `FreshnessGauge("imagination_loop_fragments", expected_cadence_s=30)` in `agents/imagination_loop.py:__init__`, call `mark_published()` on successful `_process_fragment` and `mark_failed(exc)` in the `except Exception` block. Health monitor's existing periodic check gets a `check_imagination_freshness()` helper that calls `gauge.is_stale(tolerance_mult=10)`.

Generalize by grepping the repo for `log.warning("... failed"` near `except Exception` and adding freshness gauges to the three worst offenders (imagination_loop is one; the other two are scouted during Phase 8 implementation and named inline in the plan). Also instrument `CairoSourceRunner._render_one_frame`'s try/except with the same pattern — `compositor_source_frame_published_total{source_id}`.

**Sub-design: Pool metrics IPC exposure**

`DynamicPipeline::pool_metrics()` in `crates/hapax-visual/` returns `PoolMetrics { bucket_count, total_textures, acquires, allocations, reuse_ratio }`. The accessor exists; no one reads it outside the Rust crate.

Add a periodic shm writer on the imagination tick loop:

```rust
// crates/hapax-visual/src/output.rs
fn write_pool_metrics(&self, metrics: &PoolMetrics) -> Result<()> {
    let path = Path::new("/dev/shm/hapax-imagination/pool_metrics.json");
    let payload = serde_json::json!({
        "bucket_count": metrics.bucket_count,
        "total_textures": metrics.total_textures,
        "acquires": metrics.acquires,
        "allocations": metrics.allocations,
        "reuse_ratio": metrics.reuse_ratio,
        "written_at": time::OffsetDateTime::now_utc().unix_timestamp(),
    });
    atomic_write_json(path, &payload)
}
```

Python-side reader in `agents/reverie_prediction_monitor.py` adds four new gauges:

- `reverie_pool_bucket_count` — distinct size buckets currently in the pool
- `reverie_pool_total_textures` — live textures held
- `reverie_pool_acquires_total` — monotonic
- `reverie_pool_reuse_ratio` — acquires / allocations (target ≥ 0.8)

Alert when `reuse_ratio < 0.5` for > 60s or `total_textures > 200` (suggests an allocation leak similar to the PR #731 OOM cascade).

**Sub-design: F7 dormant signal override decision**

`dynamic_pipeline.rs` lines 812–828 have a `match key.strip_prefix("signal.")` arm reading 9 override keys (`intensity`, `tension`, `depth`, `coherence`, `spectral_color`, `temporal_distortion`, `degradation`, `pitch_displacement`, `diffusion`). The Python `visual_chain.compute_param_deltas()` writes only `signal.color_warmth` and `signal.stance`. The 9 dimension overrides have no writer.

Decision: **keep the Rust arms, explicitly document them as a reserved override surface for future `visual_chain` extensions**. Rationale: the override path is O(1) per key per frame (trivial cost) and preserving it allows `visual_chain` to grow into per-frame dimension biasing without a Rust change. The PR #718 doc-comment is sufficient as-is; add a `#[allow(dead_code)]` annotation on the arms if Clippy complains.

This is a documentation change only, no code delta.

**Sub-design: F10 verification**

`ImaginationState.content_references` — grep repository for all usages, determine if orphaned. If unused, delete the field + its construction sites + any Pydantic migration fallbacks + update the `ImaginationState` docstring. If used, document the user and close F10.

Expected LoC: 0–30.

**Sub-design: Amendment 4 reverberation cadence**

Observational only. The `ImaginationLoop._check_reverberation()` path is wired (`reverberation_check(last_narrative, perceived)` returns a float; when > `REVERBERATION_THRESHOLD` the cadence accelerates). With imagination now producing fragments again (TabbyAPI fix shipped), verify that reverberation acceleration fires at least once under normal operation.

Task: add a tiny one-off script `scripts/verify_reverberation_cadence.py` that tails imagination logs for `Reverberation %.2f` log messages and asserts at least one acceleration event within a 5-minute window. Run it as part of Phase 9's AC sweep.

### Phase 9 — Final acceptance sweep (parent tasks 28–29)

**Scope:** per parent plan tasks 28 (AC validation sweep against all 11 parent-spec ACs) and 29 (final push). Add to the sweep the four new ACs introduced by Phase 8:

| AC# | Criterion | Verified by |
|---|---|---|
| 12 | `imagination_loop_fragments_published_total` counter increments at every published fragment | `curl /api/predictions/metrics` over 2 tick cycles |
| 13 | `reverie_pool_*` gauges populate with live values | `curl /api/predictions/metrics` after Phase 8 Rust shm writer lands |
| 14 | `F10` content_references decision landed (deleted or documented) | code grep |
| 15 | Amendment 4 reverberation acceleration observed once in live logs | `scripts/verify_reverberation_cadence.py` run output |

Final push: retire the legacy `_pip_draw` code paths marked `@deprecated` in Phase 3, delete any unused legacy-facade classes (`TokenPole.draw()` etc. if call-site count is zero), run full test suite + ruff + pyright, write retirement handoff doc, close.

## Composition with other sessions

**Alpha (this session):** executes the entire epic. No delegations.

**Beta:** inflection posted at epic start to avoid overlapping imagination-loop observability work. Beta's BETA-FINDING-2026-04-13-C is adopted into Phase 8; beta is notified via convergence.log.

**Delta:** no delta session active; the source-registry-epic delta has already retired.

**Cross-session edits:** none required. All changes are in files alpha owns at the top level. The Rust `hapax-visual` crate edits (Phase 4, Phase 8 pool metrics) are in alpha's territory per the camera-24/7-epic retirement handoff.

## Rollback

Each phase is a squash-merge of a single PR. Per-phase rollback via `git revert <merge SHA>`. Specific rollback notes:

- **Phase 3 (render refactor):** if the new `_pip_draw` produces wrong output, revert + the legacy facades immediately resume on the next compositor restart. Legacy code remains present (deleted only in Phase 9).
- **Phase 4 (headless mode):** if reverie renders blank in headless mode, set `HAPAX_IMAGINATION_HEADLESS=0` on the systemd unit (manual override, no code revert needed). Debug the headless path at leisure.
- **Phase 6 (appsrc pads):** if GStreamer pipeline fails to build, revert + the pipeline returns to the pre-Phase-6 topology. Cairo PiPs unaffected because they use the `cairooverlay` post-FX draw path, not glvideomixer input pads.
- **Phase 8 (observability):** additive only. Reverts are clean.

No phase modifies schema in a way that requires a data migration.

## Risks and footguns

1. **TokenPole refactor (Phase 2 Task 8)** is the biggest visual regression risk. Golden-image test mandatory before push.
2. **Phase 3 render-refactor flicker** during `rebuild-services.timer` restart window. Document restart timing in the PR description.
3. **Phase 5 UDS socket** must clean up on restart. Use `atexit` + a pre-start `rm -f` in the systemd unit ExecStartPre if the socket file leaks.
4. **Phase 8 freshness gauge shared library** — if `shared/freshness_gauge.py` API is not right the first time, every call-site needs updating. Start with imagination-loop only; generalize to two more call-sites only after the API has survived imagination-loop integration for one commit.
5. **Alpha worktree as deploy target** (carried tension). All phases go green on main; compositor sees them only after `rebuild-services.timer` or on next alpha-worktree refresh to main. Plan PR descriptions accordingly — every phase describes expected live-behavior change post-rebuild.

## Acceptance criteria (epic-level)

1. All 11 parent-spec ACs hold post-Phase 9.
2. The four new Phase 8 ACs hold.
3. `BETA-FINDING-2026-04-13-C` is closed: no always-on producer in `agents/` can fail silently for > 10× expected cadence without the health monitor catching it.
4. `BETA-FINDING-2026-04-13-A` stays closed (the TabbyAPI fix shipped in a local clone; verify post-epic that the fix is still live).
5. `F7` / `F10` decisions landed in code or in docs, no open follow-ups.
6. Reverie visibly appears in the upper-right quadrant of the compositor frame (Phase 3 + Phase 4 + Phase 6 interaction).
7. `window.__logos.execute("compositor.surface.set_geometry", {...})` moves a PiP mid-stream.
8. Zero visible regressions in existing stream output (golden-image comparison in Phase 9 sweep).

## Open questions

None. All four parent-spec open questions have been resolved (see parent spec's § Open questions), and the four new adjacent items have explicit decision paragraphs above.

## Next action

Merge PR #735 (Phase 1), then proceed to Phase 2 immediately.
