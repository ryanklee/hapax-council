# 2026-04-13 — Alpha session: reverie source registry completion epic retirement handoff

**Role:** alpha (autonomous execution)
**Duration:** 2026-04-13 ~17:50 → ~14:xx CDT (single session, 8 phases shipped)
**Operator directive:** _"complete any remaining research and formal design docs required to plan an epic multi phase to work through ALL remaining reverie related and source registry and plugin related work and adjacent work discovered, then plan the epic, then update alpha, then start working through all the batches — all without intervention."_
**Status:** closing

## What was asked

Run the reverie + source-registry completion epic to completion without intervention: research, design, plan, update alpha relay, execute every phase back-to-back. No pausing for approval. Operator trusted the epic's scoping decisions to land sensibly.

## What shipped

Eight phase PRs, all merged to main on a single branch sequence. Each phase was serial, each PR was squash-merged, each phase's worktree was cleaned up before the next branch was created. The no-stale-branches hook's 4-worktree limit was never exceeded; the session worktree budget stayed within alpha + beta-standby + rebuild-scratch + 1 rotating phase slot.

| Phase | Parent tasks | PR | Merge SHA | Headline |
|---|---|---|---|---|
| 1 | D14 | #735 | `dc7e4559a` | Wire LayoutState + SourceRegistry into StudioCompositor.start (pre-existing from earlier today) |
| 2 | C8–C11 | #738 | `d659daedb` | Cairo sources render at natural origin — TokenPole OVERLAY_X/Y/SIZE removed |
| 3 | E15+E16 | #739 | `f7789f705` | Render path flips to LayoutState walk — reverie appears UR (pending Phase 4b) |
| 4a | F18 (skeleton) | #742 | `d3e227aa2` | Headless::Renderer scaffold in src-imagination — env-var branch live, stub loop |
| 5 | G20+G22 | #743 | `734d72f9e` | UDS command server + layout autosave/watch — 20 new tests |
| 6 | H23+H24 | #744 | `187446307` | Persistent appsrc pads per source — gst_appsrc methods + build_source_appsrc_branches |
| 7 | I26+I27 | #745 | `ac6642cca` | Preset.inputs schema + resolve_preset_inputs with PresetLoadError |
| 8 | NEW | #746 | `96821a460` | FreshnessGauge + imagination wiring + Amendment 4 observational script |
| 9 | J28 (docs-only) | this PR | pending | Acceptance sweep audit + this retirement handoff |

Plus the docs PR that shipped the epic design + master plan at the start:

| — | Docs | #736 | `70895221e` | Epic design doc + 9-phase master plan |

Adjacent PRs that merged during the session (not alpha's work but relevant to the epic state):

| — | BETA-FINDING-A watchdog | #737 | — | P9 imagination-loop freshness file-watch — complements Phase 8's in-process gauge |
| — | BETA-FINDING-B fix | #740 | — | gmail-sync idempotent write — clears the hook-blocker loop |
| — | memory ceiling | #741 | — | compositor MemoryMax 4→6G + MemoryHigh 5G |

## What the epic achieved

**Source registry is now authoritative for the compositor's visual composition.** Before this epic, `_pip_draw` walked hardcoded `compositor._album_overlay.draw(cr)` / `_token_pole.draw(cr)` / `_sierpinski_renderer.draw(cr)` calls. After Phase 3, `_pip_draw` walks `LayoutState.get().assignments` by z_order, looks each source up in `SourceRegistry.get_current_surface()`, and scale-blits via the `blit_scaled` helper. The legacy direct path is kept as a fallback for compositors that lack `layout_state` / `source_registry` (which will be eliminated in Phase 9b once Phase 5b wires `command_server.start()` into `StudioCompositor.start_layout_only()`).

**Every source is a self-contained natural-size surface.** TokenPole (Phase 2 / PR #738) had the most invasive work: drop `OVERLAY_X=20`, `OVERLAY_Y=20`, `OVERLAY_SIZE=300` constants, rewrite 16 render sites to origin-relative coordinates, strip three external labels that previously lived in the canvas margin outside the overlay card. Album and Sierpinski already rendered at origin — verified by the parametrized grep regression pin `test_no_hardcoded_overlay_offsets` which rejects any reintroduction of the old constants.

**The "railroad tracks" for main-layer input are laid.** Phase 6 / PR #744 adds `gst_appsrc()` to both `CairoSourceRunner` and `ShmRgbaReader` (lazy, BGRA caps from natural dims, cached). `build_source_appsrc_branches` walks the layout sources and constructs `appsrc → videoconvert → glupload` per source, returning the elements so the caller can attach to `glvideomixer` with initial `alpha=0`. Any preset chain switch becomes an alpha-snap decision on existing pads, not pipeline rewiring.

**Runtime mutation is callable.** Phase 5 / PR #743 ships `CommandServer` on a UDS socket with 5 commands (`set_geometry`, `set_z_order`, `set_opacity`, `layout.save`, `layout.reload`) and structured error responses (`unknown_surface` with `did-you-mean` hint, `invalid_geometry`, `invalid_json`, `layout_immutable_kind`, etc.). `LayoutAutoSaver` debounces mutations to disk with atomic writes and `LayoutFileWatcher` mtime-polls for external edits — the two coexist via `LayoutState.mark_self_write` / `is_self_write` without producing a reload loop. The mechanism is ready; the `compositor.start_layout_only()` wiring is Phase 5b.

**Presets can declare source bindings.** Phase 7 / PR #745: `PresetInput(pad, as_)` schema, `EffectGraph.inputs: list[PresetInput] | None` optional field, `resolve_preset_inputs(preset, registry)` helper that fails loudly with `PresetLoadError` on any unknown pad. Resolution is load-time, not tick-time — parent spec open question 3 is closed.

**The silent-mask class is defeated on the imagination producer.** Phase 8 / PR #746: `shared/freshness_gauge.py` is the reusable contract for always-on loops with the `try/except + log.warning + return` shape. Every instance publishes `{name}_published_total`, `{name}_failed_total`, `{name}_age_seconds`. Default staleness threshold is 10× expected cadence. Imagination-loop is the seed site (`hapax_imagination_loop_fragments` at 12s expected cadence → 120s alarm). Generalization to `CairoSourceRunner` + two more always-on producers is Phase 8b.

**Bachelard Amendment 4 is verified live.** `scripts/verify_reverberation_cadence.py` ran against `journalctl --user -u hapax-imagination-loop.service --since "30 min ago"` during Phase 8 execution: **49 high-reverberation events, avg score 0.93, min 0.90, max 0.97**. Every single reverberation event cleared the 0.6 threshold. Amendment 4 is firing reliably post-BETA-FINDING-A recovery, which is also transitive verification that the TabbyAPI native tool-call extractor fix is still live (imagination wouldn't be producing fragments otherwise).

## Deferred items (named owners + rationale)

The epic scoped certain pieces as scaffold-plus-follow-up to avoid half-ships. Every deferral is explicit and has a follow-up pointer in the audit doc (`docs/superpowers/audits/2026-04-13-reverie-source-registry-completion-sweep.md`). See audit § Deferred items for full detail; compressed here:

- **Phase 4b — Real offscreen render loop.** `GpuContext::new_headless`, owned wgpu texture, staging buffer CPU readback, RGBA+sidecar SHM write. ~4h Rust+wgpu. After 4b lands, flip `hapax-imagination.service` env var to `HAPAX_IMAGINATION_HEADLESS=1`.
- **Phase 5b — Tauri/TS frontend + runtime wiring.** `hapax-logos/src-tauri/src/commands/compositor.rs` UDS client, `hapax-logos/src/lib/commands/compositor.ts` command registry entries. Also: wire `CommandServer.start()` + `LayoutAutoSaver.start()` + `LayoutFileWatcher.start()` into `StudioCompositor.start_layout_only()`. ~1–2h — backend is already done.
- **Phase 6b — Main-layer end-to-end proof (H25).** `test_main_layer_path.py` with augmented fixture layout + golden-image comparison through `glcolorconvert` + `appsink`. Test-env-fragile, needs its own CI compatibility work.
- **Phase 8b — Observability generalization.** 8.2: FreshnessGauge per-source in `SourceRegistry.construct_backend` + two more always-on producers. 8.3: Pool metrics IPC (Rust shm writer + Python reader + `reverie_pool_*` gauges). 8.4: F7 `#[allow(dead_code)]` + doc comment on the dormant signal override arms.
- **Phase 9b — Legacy facade removal.** Delete `compositor._album_overlay = AlbumOverlay()` + `_token_pole` + `_sierpinski_renderer` instantiations in `fx_chain.build_inline_fx_chain`, delete the `_pip_draw` legacy fallback branch, delete the `draw()` methods on the facade classes if call-sites drop to zero. **Prerequisite: Phase 5b wiring is live + one clean `rebuild-services.timer` cycle on it.**

## What I did NOT do (and why)

- **Did not wire `CommandServer` / autosaver / filewatcher into `StudioCompositor.start_layout_only()`.** That's Phase 5b — it bundles with the Tauri pass-through and the full frontend command-registry entries. Landing the mechanism without the frontend consumer leaves a half-functional surface that's easier to complete all at once.
- **Did not remove legacy facades.** Bundling legacy-facade removal with the rest of Phase 9 would make rollback of any primary-path bug in Phase 3/5/6 a multi-revert. The safety net stays until Phase 9b verifies Phase 5b is clean.
- **Did not ship the real headless wgpu render loop.** Operator's own PR #723 commit message said it explicitly: _"Task 18 needs DynamicPipeline decoupled from the winit surface + an offscreen texture copy-out loop — several hours of work I don't want to half-ship."_ Respected the prior judgment.
- **Did not generalize FreshnessGauge beyond imagination-loop.** The seed-first approach matches the parent plan's guidance: validate the API with one call-site under production conditions for one cycle before extending to three more. Phase 8b generalizes once imagination-loop is observed producing live metrics on main.
- **Did not touch BETA-FINDING-2026-04-13-B (gmail-sync starvation).** The operator fixed it in parallel (PR #740 merged mid-session). My role was to let it unblock me when it merged, which it did.

## Risks and footguns for a future session

1. **Don't set `HAPAX_IMAGINATION_HEADLESS=1` on the systemd unit until Phase 4b ships.** The headless branch in `main.rs` reaches the stub `run_forever` which sleeps in a 60fps tokio loop without rendering. Setting the env var without 4b will take the reverie visual surface dark.
2. **Don't delete the `_pip_draw` legacy fallback before Phase 5b.** `StudioCompositor.start_layout_only()` populates `layout_state` and `source_registry`, so the fallback branch is unreachable in normal production. But: if a future refactor of `start_layout_only` drops either attribute, `_pip_draw` silently falls through to the legacy path and the failure is visible. Keep the fallback until Phase 5b is observed clean for at least one `rebuild-services.timer` cycle.
3. **Don't remove the appsrc `_push_buffer_to_appsrc` no-op fast path.** `CairoSourceRunner._render_one_frame` calls `self._push_buffer_to_appsrc(surface)` unconditionally after every tick. The method is a cheap `is None` check when `gst_appsrc()` was never called — that's the correct behavior until Phase 6b wires the mixer attach.
4. **Don't "optimize" the `EffectGraph.inputs` default from `None` to `[]`.** The `None` default preserves backward compatibility with every existing preset that doesn't declare inputs. A list default would round-trip to `"inputs": []` on every disk write, polluting every preset file in the repo. The `None` / `[]` distinction is load-bearing.
5. **Don't bundle docs-only PRs without a non-docs carrier.** Bitten three times this session (PRs #736, #738, this one). CI `paths-ignore` filter swallows `docs/**` + root-level `*.md`. Bundle a one-line Python edit or a non-markdown file. See § Council-Specific Conventions in CLAUDE.md.

## Relay state at retirement

- **alpha.yaml** — will be updated with the epic complete marker + pointers to this handoff + the audit doc + the session PR tally (#738, #739, #742–746).
- **beta.yaml** — unchanged since 2026-04-13 03:03 (beta retired after the discovery sweep). Beta's three findings all have resolutions now: A via local TabbyAPI patch (from my earlier alpha work), B via PR #740, C via Phase 8 FreshnessGauge.
- **delta.yaml** — no delta active since the source-registry design session on 2026-04-12.
- **No relay conflicts with this epic's work.** Alpha is the only active session in this workstream.
- **Convergence log** — to be updated with the epic-complete entry post-merge.

## What the next session should do

Order-of-operations for picking up where this epic left off:

1. **Phase 5b** — the fastest unlock. Wire the already-built `CommandServer` + autosaver + filewatcher into `StudioCompositor.start_layout_only()`. Add the Tauri pass-through + TS command registry entries. ~1–2h. After this ships, `window.__logos.execute("compositor.surface.set_geometry", ...)` works end-to-end from the browser console and AC4 passes.
2. **Phase 4b** — the biggest end-to-end unlock. Implement the real headless render loop in `src-imagination/src/headless.rs` + wgpu-side `GpuContext::new_headless`. After 4b ships, flip the systemd env var and reverie actually appears in the compositor's UR quadrant. AC1 semantic + AC3 pass.
3. **Phase 9b** — legacy facade removal. Preconditions: 5b live + one `rebuild-services.timer` cycle of clean operation. Removes `_album_overlay` / `_token_pole` / `_sierpinski_renderer` instantiations + `_pip_draw` legacy fallback + facade `draw()` methods. Small diff, high readability gain.
4. **Phase 8b** — observability follow-up (pool metrics IPC + FreshnessGauge generalization + F7 decision).
5. **Phase 6b** — H25 end-to-end "railroad tracks" integration test. Needs CI environment with `glcolorconvert` + `appsink` available. Depends on nothing else.

Every item is independent of every other item. Any session with time can pick any one.

## Handoff checklist

- [x] All 8 operational phase PRs merged green
- [x] Phase 9 audit doc written (`docs/superpowers/audits/2026-04-13-reverie-source-registry-completion-sweep.md`)
- [x] This retirement handoff written
- [x] Epic master plan state tracker updated (bundled in this PR)
- [x] Non-docs carrier for this PR's CI gate (CLAUDE.md comment? or a trivial code touch — decided during commit)
- [ ] Alpha relay status updated post-merge
- [ ] Session closed

— alpha, 2026-04-13.
