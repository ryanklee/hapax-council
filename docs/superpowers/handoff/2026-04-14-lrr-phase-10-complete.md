# LRR Phase 10 — Observability Polish — Complete

**Date:** 2026-04-14
**Session:** alpha (post-retirement reviver — operator: "continue with LRR, watch for beta/delta drops")
**Predecessor:** 2026-04-14 Alpha continuation retirement handoff (`2026-04-14-alpha-continuation-retirement.md`)
**Scope:** LRR Phase 10 — observability polish. Autonomously feasible work using delta's pre-staged research drops.

## Start state

Previous alpha session retired at 10:22Z after shipping PRs #797, #798, #799, #800 with `completed_phases=[0,1,2,9]`. Retirement handoff listed Phase 10 as the next autonomously-feasible pickup and pointed at 7 delta research drops.

Operator revived the session with: "continue with LRR, watch for beta/delta drops".

Between the retirement and the first Phase 10 commit, delta shipped 3 additional research drops to main:

- `f8d2b678f` — `perf-findings-rollup.md` — pre-ranked impact-per-effort picklist for the Phase 10 work
- `6bbb39535` — `prompt-cache-audit.md` — orthogonal (future LLM-cost phase)
- `86c0383e0` — `director-loop-llm-cost.md` — orthogonal (future LLM-cost phase)

Then during the phase, delta shipped 4 more:

- `2665c2218` — `audio-path-baseline-errata.md` — healthy baseline, no action
- `d71eb2385` — `logos-build-time-audit.md` — iteration-speed wins (operator-owned)
- `684ff7ca7` — `metric-coverage-gaps.md` — consolidated observability backlog (C1-C12, A1-A4, D1-D4)
- `79d4f53a5` — `hermes-3-70b-vram-sizing-preflight.md` — Phase 5 pre-flight

And 2 more toward the end:

- `cf7a9e877` — `lrr-phase-9-integration-preflight.md` — Phase 8 pre-flight
- `b3e540a42` — `tabbyapi-config-audit.md` — Phase 5 pre-flight

Beta also shipped one new context drop:

- `2026-04-14-beta-phase-3-supplement-verified-preconditions.md` — **important finding**: verified on-rig that Phase 3 is NOT fully hardware-gated. Only items 4 (PCIe link width), 10 (cable hygiene), and 11 (BRIO replacement) need the X670E. Hermes 3 download, sm_120 compute verification, and gpu_split ordering ([2.75, 23.5]) can ship now. Beta kicked off the Hermes 3 BF16 download in background at ~15:30Z.

## What shipped this phase (PR #801 — 5 logical commits)

### Phase 10 PR #1 — glfeedback diff check (R1, ★★★★★)

Delta drop `2026-04-14-glfeedback-shader-recompile-storm.md`: `SlotPipeline.activate_plan()` was unconditionally calling `set_property("fragment", ...)` on all 24 temporal slots per plan activation, and the Rust plugin's `set_property` handler was flipping `shader_dirty = true` without diffing. Result: ~336 GL recompiles/hour of which ~224 were byte-identical no-ops. Each triggered an accumulation-buffer clear, producing visible flicker on any feedback-using effect.

- `agents/effect_graph/pipeline.py` — `_slot_last_frag` memo; activate_plan skips `set_property` on no-op re-sets; activation log reports `fragment_set_count`
- `gst-plugin-glfeedback/src/glfeedback/imp.rs` — `set_property("fragment", ...)` diffs against `props.fragment` before flipping `shader_dirty`
- `tests/effect_graph/test_pipeline.py::TestGlfeedbackDiffCheck` — 3 tests: repeat plan skips; real change sets exactly once; `create_slots` resets memo

**Operator follow-up:** `cargo build --release -p gst-plugin-glfeedback` after merge. The `hapax-rebuild-logos.timer` does not touch the GStreamer plugin.

### Phase 10 PR #2 — BudgetTracker wiring (T1+T2+T3, ★★★★)

Delta drop `2026-04-14-compositor-frame-budget-forensics.md`: The Phase 7 `BudgetTracker` + `publish_costs` + `publish_degraded_signal` were all installed but had zero runtime callers. Every `CairoSourceRunner` was constructed with `budget_tracker=None`. Both FreshnessGauges sat at `age_seconds=+Inf` for the entire process lifetime.

- `agents/studio_compositor/compositor.py` — `StudioCompositor.__init__` instantiates shared `_budget_tracker`; forwarded into `OverlayZoneManager` and `start_layout_only()` cairo-backend construction
- `agents/studio_compositor/source_registry.py` — `construct_backend(source, *, budget_tracker=None)` forwards to `CairoSourceRunner`
- `agents/studio_compositor/overlay_zones.py`, `sierpinski_renderer.py` — facade classes accept `budget_tracker` kwarg
- `agents/studio_compositor/fx_chain.py` — passes compositor tracker into `SierpinskiRenderer`
- `agents/studio_compositor/lifecycle.py` — new 1-second `GLib.timeout_add` firing `publish_costs()` + `publish_degraded_signal()`
- Tests: 9 new regression pins across `test_source_registry.py` and `test_compositor_wiring.py`

### Phase 10 PR #3 — CUDA pin + studio_fx CPU-fallback warning (C2+C3+R4)

- `systemd/units/studio-compositor.service` — `Environment=CUDA_VISIBLE_DEVICES=0` durably pins the compositor to GPU index 0 across reboots (the pin was correct at runtime today but nothing in the unit file captured the intent)
- `agents/studio_fx/gpu.py` — replaced bare `except Exception: pass` with `log.warning(..., exc_info=True)` and added a zero-device branch warning so OpenCV-CUDA disable situations are loud from startup

### Phase 10 PR #4 — Phase 2 carry-overs (OutputRouter + ResearchMarkerOverlay registration)

- `agents/studio_compositor/compositor.py` — new `self.output_router: OutputRouter | None` populated in `start_layout_only()` via `OutputRouter.from_layout(layout)`. Logs every discovered binding. Pure data plumbing; does NOT replace legacy hardcoded sink construction (that's a larger refactor deferred to a future phase).
- `agents/studio_compositor/cairo_sources/__init__.py` — registers `ResearchMarkerOverlay` in the class-name registry so it is declarable from layout JSON (Phase 2 item 4 was implemented but never registered)
- Tests: 4 new pins in `TestStudioCompositorOutputRouterWiring` + `TestResearchMarkerOverlayRegistered`

**Deferred:** the third Phase 2 carry-over (HAPAX_AUDIO_ARCHIVE_ROOT env var reader) cannot land until an `agents/audio_recorder` Python module exists — the env var is declared in `systemd/units/.../archive-path.conf` drop-ins but there is no consumer code yet.

### Phase 10 PR #5 — overlay_zones diagnostic + glfeedback counters + feature-probe log (R2/D1 + C7/C8 + D3)

Delta's `2026-04-14-metric-coverage-gaps.md` validated my earlier PRs and added these small items that I bundled together.

- `agents/studio_compositor/text_render.py` — R2/D1 diagnostic: wraps the `cairo.ImageSurface(FORMAT_ARGB32, sw, sh)` construction at line 188 in a try/except that logs `sw`, `sh`, `text_w`, `text_h`, `padding_px`, `text_len`, `text_preview` on failure, then re-raises. Delta's drop enumerated three candidate causes of the 50-exception/4-second bursts; after one live capture the root cause will be directly visible in journald.
- `agents/studio_compositor/metrics.py` — two new Counters: `compositor_glfeedback_recompile_total` and `compositor_glfeedback_accum_clear_total`. Proof-of-fix metrics for Phase 10 PR #1 — before the diff check they would have read ~336/hour, after the fix they only advance on real fragment changes.
- `agents/effect_graph/pipeline.py` — increments both counters by `fragment_set_count` after the diff loop
- `agents/studio_compositor/lifecycle.py` — new `_log_feature_probes(compositor)` called from `start_compositor` before pipeline build. Stable grep format `feature-probe: NAME=BOOL` across `prometheus_client`, `budget_tracker_active`, `opencv_cuda`, `output_router`, `research_marker_overlay_registered`. Delta's drops #1 and #6 each spent investigation cycles on features installed but runtime-disabled — this log would have caught both on day 1.
- Tests: 3 new pins in `test_text_render.py`, `test_pipeline.py::TestGlfeedbackDiffCheck`, and `test_compositor_wiring.py::TestFeatureProbeLog`

## LRR state at retirement

| Field | Value |
|---|---|
| `completed_phases` | `[0, 1, 2, 9, 10]` |
| `last_completed_phase` | 10 |
| `current_phase` | null |
| `current_phase_owner` | null |

## Test stats this phase

- 508 tests pass across `tests/test_budget.py`, `tests/studio_compositor/`, `tests/test_source_registry.py`, `tests/effect_graph/`, `tests/test_text_render.py`
- 19 new regression pins added across 5 commits
- `ruff check` + `ruff format` + `pyright` — clean on every touched file

## Items intentionally deferred from Phase 10

From delta's perf-findings-rollup picklist and metric-coverage-gaps backlog:

- **T4 — 6 camera freshness gauges**: delta's errata says these don't go through the cairo source path that was hyphen-fixed; they need a different registration site. The per-camera `studio_camera_frame_interval_seconds_bucket` histogram already provides an overlapping signal.
- **T5 — `studio_camera_kernel_drops_total` false-zero**: observability correctness bug. The v4l2 sequence-gap detector doesn't fire for MJPG. Fix requires a replacement signal source.
- **T6 — `_PUBLISH_COSTS_FRESHNESS` log rate-limit**: ★-ranked, low priority. After PR #2's wiring the publish path fires once per second as intended; current log levels are already quiet.
- **R3 — studio_fx OpenCV CUDA rebuild**: operator-owned. Package diagnosis + reinstall.
- **R5 — per-effect GPU paths for classify/screwed/pixsort/vhs/slitscan**: sprint-scale work, not a single fix.
- **C1 — brio-operator 27.94 fps deficit**: beta's `beta-brio-operator-deep-research.md` has evolved this beyond "hardware fault moot". Requires a cable/port swap test + operator judgment; see the earlier handoff's divergence note.
- **C2-C6 — appsrc back-pressure, DTS jitter, interpipe swaps, NVENC latency, encoder queue depth**: delta's metric-coverage-gaps Ring 3. Sprint-sized instrumentation work; bundle under a dedicated "compositor pipeline health instrumentation" spec.
- **C9 — PipeWire xrun counter**: separate signal source (PipeWire internal, not GStreamer).
- **C10 + C11 + D4 — director_loop LLM cost metrics**: belong in a future LLM-cost phase.
- **A3 — kernel_drops false-zero**: prerequisite for a future brio-operator root-cause investigation.
- **A4 — legacy freshness gauge hygiene**: housekeeping; no operator-visible impact.
- **B1 — 6 camera freshness gauges completion**: same as T4 above.
- **Phase 2 carry-over 3 — HAPAX_AUDIO_ARCHIVE_ROOT reader**: no consumer code exists.
- **OutputRouter-driven sink construction**: larger refactor; this phase established the data plane only.
- **ResearchMarkerOverlay layout wiring**: requires adding a top-strip surface to the default layout, an operator-owned decision.

All deferred items are documented in delta's `metric-coverage-gaps.md` + `perf-findings-rollup.md` so the next Phase-10-class work has a canonical backlog.

## Known carry-overs from prior phases (unchanged)

1. Phase 0 item 3 — `/data` inode alerts cross-repo (llm-stack), operator-gated
2. Phase 0 item 4 Step 3 — FINDING-Q runtime rollback design-ready
3. Phase 1 item 10 sub-item 2 — dotfiles `workspace-CLAUDE.md` Qdrant 9 → 10 (beta drafted fix)
4. Phase 6 voice transcript rotation hook
5. Operator decision — operator-patterns writer retire vs reschedule
6. BRIO 5342C819 — hardware replacement coordinated with X670E install

## Hardware milestone pending

**X670E motherboard install:** ~2026-04-16. Per beta's Phase 3 supplement, most of Phase 3 is now unblockable on the current rig — only PCIe link width re-verification, cable hygiene, and BRIO replacement truly need the new mobo. Phase 5 Hermes 3 substrate swap can begin as soon as beta's background BF16 download completes and alpha executes the Hermes 3 config with the **corrected** `gpu_split=[2.75, 23.5]` (5060 Ti at process index 0, 3090 at index 1 under `CUDA_DEVICE_ORDER=PCI_BUS_ID`).

## Recommended next pickup

**Phase 5 Hermes 3 substrate swap** — beta's Phase 3 supplement proves the preconditions are verified on-rig. The critical correction is the gpu_split inversion: `[2.75, 23.5]` (not `[23.5, 2.75]`). Beta has pre-staged the full execution recipe + is running the BF16 download now. Alpha's next session can pick up as soon as the download finishes and execute the EXL3 quantization + TabbyAPI config update.

Alternative next pickups:
- **Phase 8 content programming** — delta's `lrr-phase-9-integration-preflight.md` pre-flights the work
- **Compositor pipeline health instrumentation** — the C2-C6 + C9 sprint bundle from delta's metric-coverage-gaps
- **Phase 6 governance + voice transcript rotation** — operator-in-loop, beta has axiom patches ready

## Final sanity checks

- `git worktree list` on alpha clean: alpha on main + rebuild scratch + Phase 10 worktree (to be removed post-merge)
- PR #801 merged with 5 logical commits (R1 + T1/T2/T3 + C2/C3/R4 + Phase-2-carryovers + R2/C7/C8/D3)
- `lrr-state.yaml` will reflect `completed_phases=[0,1,2,9,10]` after PR #6 merges
- `alpha.yaml` will be updated to `RETIRED` by PR #6

Retiring Phase 10 cleanly.
