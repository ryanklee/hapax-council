---
date: 2026-04-21
status: amendment — integrates into existing HOMAGE + preset-variety work
amends:
  - docs/superpowers/specs/2026-04-20-homage-ward-umbrella-design.md
  - docs/superpowers/plans/2026-04-20-preset-variety-plan.md (task #166)
  - docs/superpowers/specs/2026-04-21-ward-stimmung-modulator-design.md
related_tasks:
  - "#112 HOMAGE Phase 6 — Ward↔shader bidirectional coupling"
  - "#166 Preset + chain variety"
  - "#179 FINDING-W fix — post-FX cairooverlay for chrome wards"
evidence: docs/research/evidence/2026-04-21-pixel-sort-dominance.png
---

# Amendment — Shader-intensity caps (pixel-sort first)

## Finding

Live stream inspection 2026-04-21 (evidence image: `docs/research/evidence/2026-04-21-pixel-sort-dominance.png`) shows the pixel-sorting shader effect running at an intensity level where it occupies the majority of the frame as oversaturated horizontal streaking. At that intensity it reads as **chromatic noise rather than texture** — it drowns the underlying camera content and overlay wards, inverting the "scrim is a translucent presence" spatial contract from `docs/research/2026-04-20-nebulous-scrim-design.md` §4 ("composite/effects ARE the nebulous scrim through which the studio is viewed").

The encoder-side softness (previously reported as "blurry stream") is a separate concern and was resolved independently by tuning NVENC Tune=High Quality + Psycho Visual Tuning + B-frames=2+. Text edges read crisply in the evidence image. **The remaining failure is compositional: shader intensity, not bitrate.**

## Governing principle

Every shader family (pixel-sort, glfeedback, colorgrade, drift, feedback, rd, noise, breath) must ship with an explicit **maximum compositional intensity** — a bound above which the shader ceases to read as scrim-texture and starts reading as foreground-dominant noise. This is the same class of governance as OQ-02 brightness bounds (homage-ward-umbrella §482) and OQ-01 ward-count bounds, but applied to shader activation strength instead of ward render brightness.

The cap is **not** a global brightness gate. Brightness can legitimately spike under high-tension stimmung. The cap governs how much screen area a single shader family may spatially dominate regardless of raw brightness. Pixel-sort's failure mode is particularly acute because its visual weight scales non-linearly with the `pixel_sort_strength` parameter: doubling the parameter more than doubles the perceptual dominance because the streak length scales with both intensity and frame persistence (feedback mixing amplifies it further).

## Cap specification (per shader family)

Per-shader-family soft cap authored in `presets/shader_intensity_bounds.json` (new file), read by `SatelliteManager` and `DynamicPipeline` at preset-compile time:

```json
{
  "pixel_sort": {
    "max_strength": 0.55,
    "spatial_coverage_max_pct": 0.40,
    "recovery_timeout_ms": 400
  },
  "glfeedback": { "max_strength": 0.70, "spatial_coverage_max_pct": 0.60 },
  "colorgrade":  { "max_strength": 1.00, "spatial_coverage_max_pct": 1.00 },
  "drift":       { "max_strength": 0.80, "spatial_coverage_max_pct": 1.00 },
  "feedback":    { "max_strength": 0.75, "spatial_coverage_max_pct": 0.80 },
  "rd":          { "max_strength": 0.85, "spatial_coverage_max_pct": 1.00 },
  "noise":       { "max_strength": 0.60, "spatial_coverage_max_pct": 0.70 },
  "breath":      { "max_strength": 0.90, "spatial_coverage_max_pct": 1.00 }
}
```

Values are starting-point priors derived from the 2026-04-21 evidence image. Live tuning is expected; add operator-signed amendments as they're refined.

### Enforcement paths

1. **Preset-compile clamp** — `agents/effect_graph/wgsl_compiler.py` clamps any preset's per-shader `strength` / `intensity` parameter to `max_strength` at compile time. Logs a WARNING when clamping fires. Preset files are NOT mutated; the clamp is applied to the compiled plan only.

2. **Stimmung-modulator clamp** — `ward_stimmung_modulator` (spec `2026-04-21-ward-stimmung-modulator-design.md`) may write `drift_amplitude_px`, `glow_radius_px`, etc. per ward. Modulator reads `shader_intensity_bounds.json` and refuses to push any per-shader parameter above its cap. This is enforced in `_apply_dims()` via a terminal `min(computed, cap)` on every numeric write.

3. **Runtime spatial-coverage gate (Phase 2, deferred)** — a GPU-side check at `postprocess` stage measures per-shader-family pixel coverage; if any single family exceeds its `spatial_coverage_max_pct` for >`recovery_timeout_ms`, the pipeline forces a crossfade to the next preset via the existing affordance-recruitment path. Ships after Phase 1 caps land and we have live data on whether compile-time clamps are sufficient.

## Integration contracts

### HOMAGE Phase 6 (ward↔shader bidirectional coupling) — task #112

Phase 6 wires ward state → shader uniforms (e.g. high-salience ward → elevated shader bias). The cap constrains the ceiling of that bias. Phase 6 must read the bounds file when computing its ward→shader uniform writes. If Phase 6 is already merged by the time this amendment lands, the cap integration ships as a Phase 6.1 follow-on PR.

### Preset variety (task #166)

Plan `2026-04-20-preset-variety-plan.md` already addresses repetition via scoring (affordance-pipeline recency prior, programme palette bias). The cap is orthogonal — it bounds *individual preset intensity* rather than repetition. Both must land; neither solves the other. The preset-variety plan's Phase 2 catalog audit is the natural place to surface presets whose authored `strength` values exceed the new caps and flag them for operator review (most likely: the `calm-textural` family plus any `pixel_sort_dominant` preset).

### Ward stimmung modulator (spec 2026-04-21)

The modulator's §6.2 `tension` mapping scales `drift_amplitude_px` by `(1.0 + tension × 2.0)` for `surface-scrim` wards. This can legitimately produce `drift_amplitude_px = 24` at maximum tension — which is above the `drift.max_strength` proxy of 0.80 when renormalized. The modulator must apply the cap **after** its own scaling, not before, so tension-driven peaks are bounded but not uniformly squashed.

### FINDING-W (task #179) post-FX chrome cairooverlay

The finding (chrome wards currently render pre-FX, so they get smeared by the shader chain) is adjacent: chrome wards rendered post-FX would be immune to shader intensity. That's a separate fix. But chrome-specific caps may still be useful because reverie content RENDERED UNDER THE CHROME still needs scrim-intensity governance.

## Non-goals

- This amendment does **not** replace the nebulous scrim design. Scrim is substrate; the cap is the ceiling on substrate-perturbing shaders within the scrim.
- It does **not** hardcode "no pixel-sort" or "never dominant effects". High-energy moments are permitted; the cap ensures they're punctual rather than persistent.
- It does **not** introduce expert-system gates (per `feedback_no_expert_system_rules`). The cap is a per-parameter bound, not a conditional rule over stimmung dims. Stimmung chooses where within `[0, max_strength]` to operate; the cap only clips the top.

## Phased shippable shape

| Phase | LOC | What |
|---|---|---|
| 1a | ~30 | `presets/shader_intensity_bounds.json` file + `shared/shader_bounds.py` loader |
| 1b | ~60 | `wgsl_compiler.py` clamp-at-compile path + WARNING log + test |
| 1c | ~40 | `ward_stimmung_modulator` read-and-apply after its own scaling + test |
| 1d | ~20 | Preset-variety Phase 2 audit cross-refs this amendment + flags presets above cap |
| 2 (deferred) | ~200 | GPU-side spatial-coverage gate + forced crossfade path |

Total Phase 1: ~150 LOC. One PR. Test: render each of the 30 presets under max stimmung and assert no shader family exceeds its cap.

## Acceptance

- [ ] `presets/shader_intensity_bounds.json` authored + reviewed
- [ ] `shared/shader_bounds.py` with `load_bounds()` + typed dataclass
- [ ] `wgsl_compiler.py` clamps + logs
- [ ] `ward_stimmung_modulator.py` clamps after scaling
- [ ] Test `tests/effect_graph/test_shader_intensity_bounds.py` — render each preset, assert bounds respected
- [ ] Preset-variety Phase 2 audit updated with cap flags
- [ ] Operator verifies live: pixel-sort no longer dominates; scrim feels like scrim
