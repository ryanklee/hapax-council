# Ward Stimmung Modulator + Z-Axis — Build Plan

**Spec:** `docs/superpowers/specs/2026-04-21-ward-stimmung-modulator-design.md`
**CC-task:** `ward-modulator-z-axis-spec-plan-implement.md` (claimed by alpha 2026-04-21)

## Phase 1 — Schema + static depth opacity (~45 LOC, behavior-neutral)

One PR, no visual change at default `z_plane="on-scrim"` (depth_opacity ≈ 0.96).

- [ ] `agents/studio_compositor/z_plane_constants.py` (new) — `_Z_INDEX_BASE` dict + `Z_PLANES` literal type alias
- [ ] `agents/studio_compositor/ward_properties.py` — add `z_plane: str = "on-scrim"` and `z_index_float: float = 0.5` to `WardProperties`; `_dict_to_properties` already tolerant of new keys (no change needed)
- [ ] `agents/studio_compositor/fx_chain.py` — add `blit_with_depth(cr, src, geom, opacity, blend_mode, z_plane, z_index_float)`; update `pip_draw_from_layout` to resolve `WardProperties` per-assignment and call `blit_with_depth` instead of `blit_scaled`
- [ ] `tests/studio_compositor/test_blit_with_depth.py` (new) — three tests: default `on-scrim` ≈ no opacity change; `beyond-scrim` reduces; `surface-scrim` passes through
- [ ] `uv run pytest tests/studio_compositor/ -q -x -k "not slow"` green

## Phase 2 — Modulator + z_index_float writes (~110 LOC)

One PR, depends on Phase 1 merge.

- [ ] `agents/studio_compositor/ward_stimmung_modulator.py` (new) — `WardStimmungModulator` dataclass; `maybe_tick`, `_run`, `_read_dims`, `_apply_dims` per spec §5.1
- [ ] `agents/studio_compositor/metrics.py` — register `HAPAX_WARD_MODULATOR_TICK_TOTAL`, `HAPAX_WARD_MODULATOR_STALE_TOTAL`, `HAPAX_WARD_Z_PLANE_COUNT`, `HAPAX_WARD_DEPTH_ATTENUATION` per spec §9
- [ ] `agents/studio_compositor/compositor.py` — instantiate modulator on `StudioCompositor.__init__`
- [ ] `agents/studio_compositor/fx_chain.py` — call `compositor._ward_stimmung_modulator.maybe_tick()` in `fx_tick_callback` (after existing `tick_modulator` invocation)
- [ ] `tests/studio_compositor/test_ward_stimmung_modulator.py` (new) — 7 tests per spec §11.testing
- [ ] `uv run pytest tests/studio_compositor/ -q -x` green

## Phase 3 — Reverie drift per-plane + colorgrade tint (deferred)

Depends on Scrim Phase 2 (Reverie drift per-plane wired). Deferred to its own PR after scrim work lands. Out of scope for this cc-task's immediate ship.

## Acceptance gates

- Phase 1 PR merged, default behavior unchanged, all existing studio_compositor tests pass
- Phase 2 PR merged, modulator metrics visible in Prometheus, `HAPAX_WARD_MODULATOR_ACTIVE=0` default (modulator instantiated but `maybe_tick` returns early)
- Operator flips `HAPAX_WARD_MODULATOR_ACTIVE=1`, observes ward continuous motion on stream, no regressions

## Out of scope

- Ward continuous-motion direction-driven by stimmung beyond the §6 mappings (future work)
- Cairo blur in the hot path (Phase 3 routes through Reverie colorgrade GPU node)
- z-plane override in `OperationalProperties` capability metadata (precedence §7.2 deferred)
