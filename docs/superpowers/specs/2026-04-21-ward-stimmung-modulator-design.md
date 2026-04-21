# Ward Stimmung Modulator + Z-Axis Parallax Integration

**Status:** Design, operator-directed 2026-04-21.
**Governing anchors:** HOMAGE framework (`docs/superpowers/specs/2026-04-18-homage-framework-design.md` §6), Nebulous Scrim System (`docs/research/2026-04-20-nebulous-scrim-design.md`), Ward↔FX bidirectional coupling (Phase 6 Layer 5), `agents/studio_compositor/ward_properties.py`, `agents/studio_compositor/fx_chain_ward_reactor.py`.
**Scope:** Co-designs two features that share schema fields and shader-node writes: (1) a continuous imagination-dimension → WardProperties modulator, and (2) a z-axis parallax stratification system. Both touch `WardProperties`, `fx_chain.py`'s blit path, and the same Prometheus counters. They cannot be designed independently.

---

## 1. Problem

**Gap 1 — No continuous dimension→ward path.** The imagination pipeline produces 9 expressive dimensions (intensity, tension, depth, coherence, spectral_color, temporal_distortion, degradation, pitch_displacement, diffusion) at every tick. None propagate continuously to `WardProperties`. Ward emphasis is event-driven (FSM transitions via `WardFxReactor`) but not dimension-driven. Rising `depth` cannot deepen the scrim. High `tension` cannot amplify parallax wobble.

**Gap 2 — No z-axis stratification.** All wards composite at the same conceptual depth. The nebulous scrim design (`docs/research/2026-04-20-nebulous-scrim-design.md` §4) establishes five z-planes with distinct blur, tint, and parallax semantics. No schema field, no blit logic, no per-plane drift modulation.

Both gaps share the same solution surface: `WardProperties` gains `z_plane` + `z_index_float`; the modulator writes continuously; the blit path honors them.

---

## 2. Terminology

- **Imagination dimensions** — 9 canonical floats at `/dev/shm/hapax-imagination/current.json` as `ImaginationFragment.dimensions`. NOT `SystemStimmung`. The modulator reads imagination dims.
- **z-plane** — semantic depth category on a ward. Five values: `beyond-scrim`, `mid-scrim`, `on-scrim`, `surface-scrim`, and implicit `reverie_base`. Default `"on-scrim"`.
- **z_index_float** — sub-plane position, [0.0 far, 1.0 near]. Modulator-continuous.
- **modulator** — `WardStimmungModulator` in `agents/studio_compositor/ward_stimmung_modulator.py`. ~5 Hz (every 6th 30 Hz fx tick).
- **blit_with_depth** — replaces `blit_scaled` in `pip_draw_from_layout`. Reads `z_plane` + `z_index_float`, applies plane-conditioned opacity (+ Phase 3 drift/tint).

---

## 3. WardProperties Schema Additions

**File:** `agents/studio_compositor/ward_properties.py`.

```python
z_plane: Literal["beyond-scrim","mid-scrim","on-scrim","surface-scrim"] = "on-scrim"
z_index_float: float = 0.5  # 0.0 (far) to 1.0 (near)
```

**Default `"on-scrim"` mandatory.** Existing wards land on the legibility plane with no visual change. Opt-in per ward via director `placement_bias` or modulator nudges.

`_dict_to_properties` tolerance: skips unknown keys — no change. `_dataclass_to_jsonable` tuple-handling: both fields are plain primitives. `z_order_override` (existing) is compositor sort key; `z_plane` is depth semantic — orthogonal.

---

## 4. Z-Plane Taxonomy

| Plane | `z_plane` value | Wards | Blur (Phase 3) | Tint (Phase 3) | Parallax |
|-------|----------------|-------|----------------|----------------|----------|
| Surface-scrim | `"surface-scrim"` | stream_overlay, research_marker_overlay | 0.0 px | 0% | none |
| On-scrim (default) | `"on-scrim"` | token_pole, captions, activity_header, stance_indicator | 0.2 px | ~0% | minimal |
| Mid-scrim | `"mid-scrim"` | chat_ambient, impingement_cascade, thinking_indicator, grounding_provenance_ticker | +0.5 px | +8% scrim tint | mid |
| Beyond-scrim | `"beyond-scrim"` | camera PiPs, album_overlay | +2.0 px | +15% scrim tint | full |

```python
_Z_INDEX_BASE: dict[str, float] = {
    "beyond-scrim": 0.2,
    "mid-scrim":    0.5,
    "on-scrim":     0.9,
    "surface-scrim": 1.0,
}
```

---

## 5. New Files

### 5.1 `agents/studio_compositor/ward_stimmung_modulator.py` (new)

**Class:** `WardStimmungModulator`

```python
@dataclass
class WardStimmungModulator:
    current_path: Path = Path("/dev/shm/hapax-imagination/current.json")
    ward_properties_ttl_s: float = 0.4   # 2 modulator ticks ≈ 400 ms
    tick_every_n: int = 6                # ~5 Hz at 30 Hz fx cadence
    _tick_counter: int = 0

    def maybe_tick(self) -> None:
        self._tick_counter += 1
        if self._tick_counter < self.tick_every_n:
            return
        self._tick_counter = 0
        self._run()

    def _run(self) -> None:
        dims = self._read_dims()
        if dims is None:
            return
        for ward_id in _all_known_ward_ids():
            base = get_specific_ward_properties(ward_id) or WardProperties()
            updated = self._apply_dims(ward_id, base, dims)
            if updated is not base:
                set_ward_properties(ward_id, updated, ttl_s=self.ward_properties_ttl_s)
        _emit_modulator_tick_total()
```

`_read_dims()`: JSON parse of `current.json`, returns `None` on missing/parse error. Staleness: `timestamp` older than 10s → skip + increment `HAPAX_MODULATOR_STALE_TOTAL`.

`_apply_dims()`: per-ward property computation (§6). Returns new `WardProperties` if any field changed, else `base`.

`_all_known_ward_ids()`: `ward_fx_mapping.WARD_DOMAIN.keys()` — same registry as reactor.

### 5.2 `agents/studio_compositor/fx_chain.py` additions

```python
def blit_with_depth(
    cr: cairo.Context,
    src: cairo.ImageSurface,
    geom: SurfaceGeometry,
    opacity: float,
    blend_mode: str,
    z_plane: str,
    z_index_float: float,
    scrim_tint_hue: float = 180.0,
) -> None:
    z_base = _Z_INDEX_BASE.get(z_plane, 0.9)
    effective_z = max(0.0, min(1.0, z_base + (z_index_float - 0.5) * 0.2))
    depth_opacity = 0.6 + 0.4 * effective_z  # beyond=0.68, on-scrim=0.96
    blit_scaled(cr, src, geom, opacity * depth_opacity, blend_mode)
```

Phase 1: static opacity modulation only. Differential blur + tint deferred to Phase 3 (routed through Reverie's colorgrade node, not in the Cairo hot path).

`pip_draw_from_layout` integration:

```python
props = resolve_ward_properties(assignment.source)
blit_with_depth(
    cr, src, surface_schema.geometry,
    opacity=effective_alpha,
    blend_mode=surface_schema.blend_mode,
    z_plane=props.z_plane,
    z_index_float=props.z_index_float,
)
```

`_Z_INDEX_BASE` moves to `agents/studio_compositor/z_plane_constants.py` (new, 15 LOC) to avoid circular imports.

---

## 6. Imagination Dim → WardProperty Mapping

All mappings continuous soft functions, not threshold gates (per `feedback_no_expert_system_rules`).

### 6.1 `depth` → beyond/mid-plane attenuation

```python
# Only for "beyond-scrim" and "mid-scrim"
depth_val = dims.get("depth", 0.5)
attenuation = 0.5 + 0.5 * (1.0 - depth_val)      # 0.5@depth=1, 1.0@depth=0
z_nudge     = (0.5 - depth_val) * 0.3             # -0.15..+0.15
```

### 6.2 `tension` → per-plane drift amplitude

```python
tension_val = dims.get("tension", 0.0)
_TENSION_DRIFT_SCALE = {
    "surface-scrim": 1.0 + tension_val * 2.0,
    "on-scrim":      1.0 + tension_val * 1.5,
    "mid-scrim":     1.0 + tension_val * 0.3,
    "beyond-scrim":  1.0,
}
# props.drift_amplitude_px *= _TENSION_DRIFT_SCALE[z_plane]
```

Foreground-anxious / background-calm reading. `drift_amplitude_px` already exists on `WardProperties`; the modulator scales an existing field.

### 6.3 `coherence` → z-plane convergence/divergence

```python
coherence_val = dims.get("coherence", 0.5)
convergence = (coherence_val - 0.5) * 0.2   # ±0.1 range
# beyond-scrim: z_index_float = base - convergence (pull forward at high coherence)
# on-scrim stays near 0.9 regardless
```

### 6.4 `diffusion` → cross-plane blur convergence (Phase 1 proxy only)

Phase 1: `diffusion` maps to `glow_radius_px` on `beyond-scrim` wards as a proxy for "softened boundary." Phase 3: real per-plane blur radii via colorgrade.

### 6.5 `intensity` → transient forward displacement

```python
intensity_val = dims.get("intensity", 0.0)
if intensity_val >= 0.7 and ward_was_recently_recruited(ward_id):
    forward_nudge = (intensity_val - 0.7) / 0.3 * 0.15  # 0..+0.15
    z_index_float_override = min(1.0, base_z + forward_nudge)
```

"Recently recruited" = `ward_id` in `recent-recruitment.json` (written by `WardFxReactor._bias_preset_family`) within last 2s. TTL 0.8s, then decays.

---

## 7. Precedence

Three authorities, decreasing priority:

1. **Director explicit placement** — `placement_bias` in `StructuralIntent` (or new `IntentFamily.scrim_placement`) sets `z_plane` directly. Modulator MUST NOT override `z_plane` while active.
2. **Explicit recruitment** — affordance pipeline can include `z_plane` in capability metadata.
3. **Modulator** — ONLY writes `z_index_float` (sub-plane float), never `z_plane` category.

**Implementation:** modulator checks `get_specific_ward_properties(ward_id)` before writing. If entry's `z_plane` differs from `"on-scrim"` and its `expires_at` has not lapsed, modulator skips `z_plane` and writes only `z_index_float`.

---

## 8. Phased Rollout

### Phase 1 — Schema + static depth opacity

Deliverable: `z_plane` + `z_index_float` on `WardProperties`. `blit_with_depth` in `fx_chain.py` with static per-plane opacity. `pip_draw_from_layout` updated. `z_plane_constants.py`. No visual change for existing wards (default `"on-scrim"`, depth_opacity ≈ 0.96). **Depth is semantic, not yet visually apparent.**

~45 LOC. No new Prometheus metrics yet. No modulator instance. **No dependency on scrim work.**

Files:
- `agents/studio_compositor/ward_properties.py` — add two fields
- `agents/studio_compositor/fx_chain.py` — add `blit_with_depth`, update `pip_draw_from_layout`
- `agents/studio_compositor/z_plane_constants.py` — new

### Phase 2 — Modulator + z_index_float writes

Deliverable: `WardStimmungModulator` as a new file. Wired into `fx_tick_callback` after `tick_modulator`. Reads `current.json`. Writes `z_index_float` + `drift_amplitude_px` + `alpha` deltas (§6). Does NOT yet write colorgrade/blur. Prometheus counters + histogram (§9).

~110 LOC incl. tests. Modulator instance in `StudioCompositor.__init__`.

Files:
- `agents/studio_compositor/ward_stimmung_modulator.py` — new
- `agents/studio_compositor/fx_chain.py` — `fx_tick_callback` calls `compositor._ward_stimmung_modulator.maybe_tick()`
- `agents/studio_compositor/compositor.py` — instantiate modulator
- `agents/studio_compositor/metrics.py` — metric registrations
- `tests/studio_compositor/test_ward_stimmung_modulator.py` — new

### Phase 3 — Reverie drift per-plane + colorgrade tint (visual parallax arrives)

Deliverable: wire Reverie's `drift` node amplitude per-plane; colorgrade tint (`saturation` + `hue_rotate` toward scrim dominant hue) written per-plane to `uniforms.json`. **Motion parallax and atmospheric tint become visually apparent.**

**Scrim dependency:** lands WITH scrim Phase 2 (Reverie drift per-plane must be live).

~80 LOC. Files:
- `agents/studio_compositor/ward_stimmung_modulator.py` — add `_apply_colorgrade_tint`, `_apply_drift_per_plane`
- `agents/studio_compositor/fx_chain_ward_reactor.py` — teach reactor about `z_plane` when computing per-ward domain hints

### Phase 4 — Scrim Phase 3 (DoF shader) compatibility

When scrim Phase 3's DoF WGSL node ships, Phase 3's colorgrade approximation downgrades to a soft prior. No new modulator code required. Orthogonal.

---

## 9. Observability

```python
HAPAX_MODULATOR_TICK_TOTAL = Counter(
    "hapax_ward_modulator_tick_total",
    "Ward stimmung modulator ticks (successful dim reads + ward writes).",
    registry=REGISTRY,
)
HAPAX_MODULATOR_STALE_TOTAL = Counter(
    "hapax_ward_modulator_stale_total",
    "Modulator ticks skipped because current.json was stale or missing.",
    registry=REGISTRY,
)
HAPAX_WARD_Z_PLANE_COUNT = Gauge(
    "hapax_ward_z_plane_count",
    "Number of wards currently assigned to each z-plane.",
    ["z_plane"],
    registry=REGISTRY,
)
HAPAX_WARD_DEPTH_ATTENUATION = Histogram(
    "hapax_ward_depth_attenuation",
    "z_index_float values written by the modulator, labeled by z_plane and driving_dim.",
    ["z_plane", "driving_dim"],
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    registry=REGISTRY,
)
```

**Grafana queries:**
- `rate(hapax_ward_modulator_stale_total[5m]) > 0` → imagination loop dead or very slow
- `hapax_ward_z_plane_count{z_plane="beyond-scrim"}` → how many wards deep at any moment
- `histogram_quantile(0.95, hapax_ward_depth_attenuation{driving_dim="depth"})` → depth dim effect on far wards

---

## 10. Data Flow

```
/dev/shm/hapax-imagination/current.json
    ↓  (~5 Hz: WardStimmungModulator._read_dims)
    dims: {intensity, tension, depth, coherence, diffusion, ...}
    ↓  (_apply_dims per ward_id)
    WardProperties delta: {alpha, z_index_float, drift_amplitude_px, glow_radius_px}
    ↓  (set_ward_properties atomic SHM write)
    /dev/shm/hapax-compositor/ward-properties.json
    ↓  (resolve_ward_properties in pip_draw_from_layout, 200ms cache)
    WardProperties {z_plane, z_index_float, alpha, drift_amplitude_px, ...}
    ↓  (blit_with_depth)
    depth-conditioned opacity on Cairo surface blit
```

Phase 3 parallel flow:

```
dims.tension → drift_amplitude_px per ward → ward_properties.json
    → ward_render_scope reads drift_amplitude_px
    → CairoSourceRunner applies drift offset on render thread
    → per-plane visual parallax on Cairo surfaces
```

---

## 11. Critical Details

### Error handling
- `_read_dims` returns `None` on any I/O or parse error. Modulator increments `HAPAX_MODULATOR_STALE_TOTAL`, exits cleanly. No exception to `fx_tick_callback`.
- `set_ward_properties` already handles write failures with `log.warning` + cache invalidation.
- `blit_with_depth` preserves the `geom.kind != "rect"` early-return path.

### Performance
- ~5 Hz × ~17 wards = ~85 atomic `/dev/shm` file replaces/s, each ~200 bytes. RAM-backed, acceptable.
- `blit_with_depth` adds one dict lookup + two floats per blit. Zero new allocations beyond existing `resolve_ward_properties`.
- 200 ms cache unchanged; modulator writes visible within 200 ms worst case.
- DEGRADED mode: modulator checks `_degraded_active()` and no-ops (matches `tick_governance` / `tick_slot_pipeline` patterns).

### Testing
`tests/studio_compositor/test_ward_stimmung_modulator.py`. `unittest.mock` only, self-contained, no shared conftest:

- `test_dims_read_fail_returns_none` — missing `current.json` → no-op
- `test_stale_dims_skipped` — timestamp 15s ago → skip
- `test_depth_dim_attenuates_beyond_ward` — `depth=1.0` → `beyond-scrim` `alpha` and `z_index_float` decrease
- `test_tension_scales_near_drift_not_far` — `tension=1.0` → `on-scrim` `drift_amplitude_px` up, `beyond-scrim` unchanged
- `test_modulator_does_not_override_director_z_plane` — ward entry with non-default `z_plane` + unexpired TTL → modulator only updates `z_index_float`
- `test_blit_with_depth_beyond_reduces_opacity` — `z_plane="beyond-scrim"` → combined opacity < input
- `test_blit_with_depth_surface_passes_through` — `z_plane="surface-scrim"` → opacity ~= 1.0 × depth_opacity

### Governance
No new capabilities, no consent surfaces, no LLM calls. Deterministic signal transform. Continuous soft functions, no threshold gates.

---

## 12. Upstream Dependencies

- **`presets/scrim_baseline.json`** — required for full scrim context but NOT a blocker for Phase 1/2. Phase 1 is fully independent.
- **Scrim Phase 2 (drift per-plane in Reverie)** — required before modulator Phase 3.
- **Imagination loop liveness** — modulator degrades gracefully (stale counter + no-op) when dead.

---

## 13. Build Sequence

**Phase 1 (one PR):**
- [ ] Add `z_plane` + `z_index_float` to `WardProperties`
- [ ] Create `agents/studio_compositor/z_plane_constants.py`
- [ ] Add `blit_with_depth` to `fx_chain.py`
- [ ] Update `pip_draw_from_layout` to call `blit_with_depth`
- [ ] `uv run pytest tests/studio_compositor/ -q` — all existing tests pass (default `"on-scrim"` is behavior-neutral)

**Phase 2 (one PR):**
- [ ] Create `agents/studio_compositor/ward_stimmung_modulator.py`
- [ ] Instantiate in `StudioCompositor.__init__`
- [ ] Wire `maybe_tick()` into `fx_tick_callback` after `tick_modulator`
- [ ] Add 4 Prometheus metrics
- [ ] Create `tests/studio_compositor/test_ward_stimmung_modulator.py`
- [ ] `uv run pytest tests/studio_compositor/ -q`

**Phase 3 (one PR, depends on scrim Phase 2):**
- [ ] `_apply_colorgrade_tint` + `_apply_drift_per_plane`
- [ ] Teach `fx_chain_ward_reactor.py` about `z_plane`

---

## 14. Key Decisions

1. **`z_plane` goes on `WardProperties`** (not `Source`/`Assignment`) — consistent with modulator + reactor both writing to `WardProperties` SHM; blit path reads it there.
2. **Modulator at 5 Hz, not 30 Hz** — 85 atomic SHM writes/s is acceptable; 510/s (30 Hz × 17 wards) is not.
3. **Modulator writes `z_index_float` only, never `z_plane`** — precedence clean. Director + recruitment own category; modulator owns sub-plane float.
4. **`blit_with_depth` is NOT Cairo blur in Phase 1** — pure opacity math. Real Gaussian blur at 30 fps per ward would bust frame budget. Phase 3 routes blur through the Reverie colorgrade node (GPU, ~0.3ms total regardless of ward count).
5. **Phase 1 ships before any scrim work** — schema + blit function are behavior-neutral (default `"on-scrim"`, opacity ≈ 0.96). No visual regression risk.

---

## 15. References

- `agents/studio_compositor/ward_properties.py` — `WardProperties` dataclass, SHM write/read path
- `agents/studio_compositor/fx_chain.py` — `blit_scaled`, `pip_draw_from_layout`, `fx_tick_callback`
- `agents/studio_compositor/fx_chain_ward_reactor.py` — existing reactor pattern
- `agents/studio_compositor/fx_tick.py` — `tick_modulator`, `tick_governance` patterns
- `agents/studio_compositor/metrics.py` — Prometheus registration pattern
- `agents/studio_compositor/ward_fx_mapping.py` — `WARD_DOMAIN` registry
- `agents/imagination.py` — `ImaginationFragment`, `CANONICAL_DIMENSIONS`, `CURRENT_PATH`
- `docs/research/2026-04-20-nebulous-scrim-design.md` — scrim spatial semantics §4, §6, §11
- `docs/superpowers/specs/2026-04-18-homage-framework-design.md` — HOMAGE framework
