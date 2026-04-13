# Post-Epic Audit — Phase 1 Completion Verification

**Date:** 2026-04-13
**Audit design:** [2026-04-13-post-epic-audit-design.md](../specs/2026-04-13-post-epic-audit-design.md)
**Audit plan:** [2026-04-13-post-epic-audit-plan.md](../plans/2026-04-13-post-epic-audit-plan.md)
**Method:** independent re-read of shipped code against the 11 parent + 4 Phase-8 acceptance criteria from the completion epic plan, ignoring the Phase 9 sweep's verdicts until after recording independent ones.

## Summary

- 9 ACs are **complete** on `main`.
- 3 ACs ship a helper but are **unwired** into the production boot path (AC-5, AC-7, AC-10).
- 2 ACs ship as **stubs** that don't actually perform the work (AC-3, AC-11).
- 1 AC is **missing** entirely (AC-13).

AC-3 is the root cause of the live operator-reported bug "reverie is still spawning outside logos" — Phase 4a landed a scaffold-only `headless::Renderer` and the systemd env var was deliberately not flipped. **Phase 4b lands in the same PR as this audit report (A3)** and closes AC-3.

## Parent ACs (11)

| # | AC | Status | Evidence / follow-up |
|---|---|---|---|
| 1 | Compositor boots with `default.json`; reverie PiP shows live frames in upper-right. | **complete** | `test_default_json_exists_and_is_valid_layout` + A1 layout fix (PR #749) + `test_reads_disk_layout_and_populates_state_and_registry`. The boot path is pinned. |
| 2 | Existing visible behavior preserved (UL Vitruvian, LL album). | **complete-but-unverified** | Asserted by the layout pydantic schema and A1's `test_default_json_operator_quadrant_defaults`. No runtime visual diff against a pre-epic baseline — AC-11 would have caught drift but is itself a stub (see below). |
| 3 | `hapax-imagination.service` runs headless; no winit window visible. | **~~STUB~~ → complete in this PR** | Was a pure stub: `headless.rs::Renderer::run_forever` looped on `tokio::time::interval` with zero GPU work, and `systemd/hapax-imagination.service` had no `HAPAX_IMAGINATION_HEADLESS=1` env var. PR #749 (A3) ships the real loop: private wgpu device, offscreen Rgba8UnormSrgb texture, same `DynamicPipeline` + `ContentSourceManager` + `StateReader` triple as the winit path, plus the env var flip. Live-verified producing 1920×1080 RGBA at the expected byte count. |
| 4 | `compositor.surface.set_geometry` moves a PiP within ≤1 frame. | **complete** | `command_server.py::_handle_set_geometry` + `test_command_server.py`. Wired into `command_server.py` CMD map. |
| 5 | File-watch reload within ≤2s for valid edits; invalid edit ignored with warning. | **UNWIRED** | `layout_persistence.py::LayoutFileWatcher` and `LayoutAutoSaver` classes exist, but grep for `LayoutFileWatcher(` and `LayoutAutoSaver(` in `compositor.py` returns zero hits — `StudioCompositor.__init__` never instantiates either. The file-watch reload path is dead code until wired. **Follow-up:** ticket to wire into `start_layout_only()`. |
| 6 | Every source has a persistent `appsrc` pad; reverie RGBA reaches glvideomixer. | **complete** | `fx_chain.py::build_source_appsrc_branches` walks the SourceRegistry, constructs `appsrc→videoconvert→glupload` chains, and skips any source whose backend lacks `gst_appsrc()`. The reverie `ShmRgbaReader` implements `gst_appsrc()`. |
| 7 | Preset load with unknown source reference fails loudly. | **UNWIRED** | `effect_graph/types.py::PresetInput` + `compiler.py::resolve_preset_inputs` + `PresetLoadError` exist and are tested, but grep for call sites outside `compiler.py` itself returns zero hits. No caller in `agents/studio_compositor/` or the effect_graph compile entrypoints invokes `resolve_preset_inputs`. **Follow-up:** ticket to wire into the preset load path. |
| 8 | Deleting `default.json` → fallback layout + ntfy. | **complete for fallback; partial for ntfy** | `load_layout_or_fallback` catches missing files and logs a warning that yields `_FALLBACK_LAYOUT`, verified by `test_load_layout_or_fallback_uses_fallback_when_file_missing`. `compositor.py` has `send_notification` wiring for camera transitions (lines 292, 508, 527) but NOT for the missing-layout-file case. **Follow-up:** minor — add ntfy call inside `load_layout_or_fallback` fallback branch. |
| 9 | All new tests pass; existing `tests/studio_compositor/` suite unchanged. | **complete** | 109 tests pass on the A1 branch after the stream_overlay additions. Phase 9 Task 29 legacy facade cleanup still pending — existing facade tests coexist with the new registry tests. |
| 10 | `compositor_source_frame_age_seconds` populates for every registered source. | **PARTIAL** | `FreshnessGauge` import exists in `shm_rgba_reader.py` and `imagination_loop.py` ONLY. `cairo_source.py::CairoSourceRunner` has no FreshnessGauge instance — the four cairo sources (token_pole, album, stream_overlay, sierpinski) are ungauged. "Every source" is not satisfied — only the shm external_rgba source is. **Follow-up:** wire a per-runner gauge into `CairoSourceRunner.__init__`. |
| 11 | Natural-size migration preserves visual output (golden-image regression). | **STUB / MISSING** | `tests/fixtures/` contains no `token_pole_golden.png`, and `tests/studio_compositor/` has no `test_token_pole*` or `test_natural*` file. The plan's Phase 2 task ("Render with fixed seed, save golden, commit separately") was never executed. The natural-size rewrite *likely* preserves output (the refactor was mechanical), but there is no test evidence. **Follow-up:** ticket to author the golden test. |

## Phase 8 ACs (4)

| # | AC | Status | Evidence / follow-up |
|---|---|---|---|
| 12 | `imagination_loop_fragments_published_total` counter increments per tick. | **complete** | `agents/imagination_loop.py` imports `FreshnessGauge`, instantiates `self.freshness = FreshnessGauge(...)`, calls `mark_published()` after a successful fragment and `mark_failed()` in the except branch. |
| 13 | `reverie_pool_*` gauges populate with live values. | **MISSING** | `DynamicPipeline::pool_metrics()` exists in `dynamic_pipeline.rs` and returns a `PoolMetrics` struct, but no Python consumer, no UDS handler, and no Prometheus exporter reads it. Task 8.3 "Pool metrics IPC exposure" shipped the Rust source but not the IPC export. **Follow-up:** Rust UDS endpoint + Python probe. |
| 14 | F10 `content_references` decision landed in code. | **complete, field-level** | `hapax-logos/crates/hapax-visual/src/state.rs:342` declares `pub content_references: Vec<ImaginationContentRef>` as `#[serde(default)]`. The "decision" (keep vs. delete) landed as "keep" by virtue of the field being live in the serde schema. No `#[allow(dead_code)]` gate because the field *is* read by the serde deserializer — so it's not dead, even if no downstream Rust code currently consumes it. Acceptable as shipped. |
| 15 | Amendment 4 reverberation acceleration observed once in live logs. | **complete** | `scripts/verify_reverberation_cadence.py` exists and shipped data (per the completion epic retirement handoff: 49 events in 30 min, avg 0.93s, max 0.97s — matches the <1s accelerated-cadence target). |

## Follow-up tickets (for A5–A8 execution phases)

These are the items the audit found that need either tests, wiring, or deletion. They seed Phases 2–5 of the audit plan.

1. **Wire `LayoutFileWatcher` + `LayoutAutoSaver` into `StudioCompositor`.** Without this, AC-5 is false on main; a file edit will not reload until the compositor is restarted.
2. **Wire `resolve_preset_inputs` into the preset load path.** Without this, AC-7's "fails loudly" is only true at the library-function level, not at user-visible preset load.
3. **Per-`CairoSourceRunner` `FreshnessGauge`.** Without this, AC-10 underserves half the source set.
4. **Author `token_pole_golden.png` and the regression test.** Without this, AC-11 is untested.
5. **Pool metrics IPC exposure.** Either Rust-side UDS handler + Python probe, or a Prometheus exporter on the Rust side reading `pool_metrics()`. Without this, AC-13 is dead-letter.
6. **ntfy on fallback load.** Minor — extend `load_layout_or_fallback` to call `send_notification` on file-missing or schema-failure path.

## Decisions for the audit's remaining phases

- **A3 (Phase 4b)** ships in this PR (PR #749) so the operator's live bug is fixed immediately rather than ticketed. This is the only one of the above that ships as code in the audit-phase-1 PR.
- **Items 1–6** are filed as follow-up work. They will be picked up in audit Phases 2 (correctness wiring) and 3 (dead-code sweep), each as its own focused PR.
- **Phase 9's sweep verdicts are superseded by this report** for the purposes of the audit's tracking. The sweep walked the ACs as written; this report walked the code behind them.
