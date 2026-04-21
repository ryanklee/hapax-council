---
date: 2026-04-21
author: alpha
audience: delta (B10 owner), operator (review)
register: scientific, neutral
status: spec — ready for plan + execution
scope: CBIP Phase 1 — first two enhancement families (Palette Lineage + Poster Print) + 3 new effect-graph nodes + recognizability test harness + Ring-2 pre-render gate + operator-override surface
related:
  - docs/research/2026-04-20-cbip-1-name-cultural-lineage.md (CBIP concept + 4-step hermeneutic)
  - docs/research/2026-04-20-cbip-vinyl-enhancement-research.md (5 enhancement families + test harness)
  - docs/superpowers/specs/2026-04-20-homage-ward-umbrella-design.md (CBIP annex)
  - scripts/album-identifier.py (Phase 0 deterministic tint, PR #1112)
  - agents/studio_compositor/album_overlay.py (current AlbumOverlayCairoSource — host for CBIP enhancements)
  - agents/effect_graph/ (WGSL compiler + node registry — destination for new nodes)
governing-axioms:
  - single_user (constitutional)
  - executive_function (constitutional)
locked decisions (operator 2026-04-21):
  - PR #1112 deterministic tint = Phase 0 foundation (kept)
  - Phase 1 ships Palette Lineage + Poster Print families
  - Recognizability bar: 80% human ID
  - Round structure (chess/boxing) deferred to Phase 2 (after Phase 1 lands)
  - Operator overrides: stimmung-coupled by default + manual intensity slider
---

# CBIP Phase 1 — Two Enhancement Families + Test Harness + Override Surface

CBIP (Chess Boxing Interpretive Plane) is a HOMAGE ward in `album` slot. Phase 0 (PR #1112, commit `a9573c93b`) shipped deterministic per-album tint as the recognition foundation. Operator directive (2026-04-20 relay): *"Result should be interesting **but still indicative** of an album cover."* Phase 0 is "indicative" but not "interesting." Phase 1 ships the first two enhancement families per `docs/research/2026-04-20-cbip-vinyl-enhancement-research.md`, with the recognizability test harness gating every enhancement before it reaches broadcast.

## §1 Decisions (locked)

| Decision | Choice | Rationale |
|---|---|---|
| Phase 0 disposition | Keep PR #1112 as foundation | Deterministic tint is the identification primitive (hermeneutic step 1) |
| First enhancement families | Palette Lineage + Poster Print | Lowest recognizability risk; highest Wu-Tang fidelity (research §7.1) |
| Recognizability bar | 80% human ID rate | Pragmatic; matches operator's "indicative" framing |
| Round structure timing | Phase 2 (after Phase 1 ships) | Single skinny vertical slice first; round timing defines render cadence for ALL families |
| Operator override surface | Both stimmung-coupled default + manual slider | Default is intelligent; operator can always override |
| Cross-modal scope | Albums only (Phase 1) | Books/figures/instruments deferred to Phase 3+ |
| Sacrifice primitive | Deferred to Phase 4 | Requires programme-layer integration |
| Spec location | Stays under `/homage/` | CBIP is one ward in the umbrella, not a parallel system |

## §2 New effect-graph nodes (3)

All three land in `agents/effect_graph/nodes/` as Python pass spec + corresponding WGSL shader in `agents/reverie/shaders/` (or Python/Cairo equivalent — TBD per node). Each registered in `agents/effect_graph/wgsl_compiler.py` node registry.

### §2.1 `posterize` (palette collapse via ordered Bayer dither)

- **Inputs:** RGBA texture, `palette_size: int (4..16)`, `dither_strength: float (0..1)`
- **Output:** RGBA texture
- **Algorithm:** Quantize each pixel to nearest palette entry; apply 8×8 Bayer dither matrix at strength `dither_strength` to break banding.
- **Recognizability risk:** Low if `palette_size ≥ 6` and `dither_strength ≥ 0.5`.
- **Implementation:** WGSL fragment shader (single-pass).
- **Tests:** golden-image pin against `tests/studio_compositor/golden_images/cbip/posterize/`.

### §2.2 `kuwahara` (edge-preserving smoothing)

- **Inputs:** RGBA texture, `radius: int (3..9)`
- **Output:** RGBA texture
- **Algorithm:** For each pixel, partition `radius × radius` window into 4 quadrants; output = mean of quadrant with lowest variance.
- **Recognizability risk:** Medium — preserves edges but flattens interior detail. Approved at `radius ≤ 5`.
- **Implementation:** WGSL compute shader (multi-pass for radius > 5; single-pass at radius ≤ 5).
- **Tests:** edge-IoU ≥ 0.65 against original (Sobel edges before/after).

### §2.3 `palette_extract` (K-means dominant-color extraction → swatch grid overlay)

- **Inputs:** RGBA texture, `k: int (4..12)`, `grid_layout: "row" | "column" | "grid"`
- **Output:** RGBA texture (original + swatch overlay positioned per `grid_layout`)
- **Algorithm:** K-means cluster pixels in CIELAB space; render top-K colors as swatch grid with frequency-weighted size.
- **Recognizability risk:** Low — non-destructive overlay, original preserved underneath.
- **Implementation:** Python (scikit-learn KMeans) + Cairo overlay (compute on CPU, blit at compositor rate).
- **Tests:** swatch palette delta-E ≤ 5 vs. canonical K-means reference.

## §3 Enhancement families

### §3.1 Family 1 — Palette Lineage (contextualization move)

- **Compose:** `palette_extract(k=8, layout="grid")` → blit alongside original cover
- **Optional:** add producer/artist attribution text under each swatch (sourced from album metadata)
- **Round affinity:** deliberative (chess) — long dwell, deep metadata
- **Recognizability profile:** original cover preserved unmodified; swatch grid is additive
- **Acceptance test:** `tests/studio_compositor/cbip/test_palette_lineage_acceptance.py` — confirms original ≥99% pixel-identical, swatch grid present with K=8 colors

### §3.2 Family 2 — Poster Print (argument move)

- **Compose:** `kuwahara(radius=5)` → `posterize(palette_size=8, dither_strength=0.6)`
- **Round affinity:** either (high static visual interest)
- **Recognizability profile:** edge IoU ≥ 0.65; OCR ≥ 90%; palette delta-E ≤ 40
- **Acceptance test:** `tests/studio_compositor/cbip/test_poster_print_acceptance.py` — full recognizability harness (see §4)

## §4 Recognizability test harness

Lives at `tests/studio_compositor/cbip/recognizability_harness.py`. Every CBIP enhancement family MUST pass before reaching broadcast.

| Metric | Method | Threshold | Severity |
|---|---|---|---|
| OCR title round-trip | Tesseract on title region | ≥90% character accuracy | INVARIANT (block ship) |
| Perceptual hash distance | imagehash 64-bit Hamming | ≤8 bits | INVARIANT |
| Palette delta-E (CIELAB) | K-means K=8, CIE2000 | ≤40 units mean per color | QUALITY (warn, don't block) |
| Edge IoU (Sobel σ=1) | Jaccard | ≥0.65 geometric, ≥0.50 abstract | QUALITY |
| CLIP-score | OpenAI CLIP cosine vs original | ≥0.75 | QUALITY |
| Human ID rate | Canonical 20-cover panel × 3 intensity (`tests/fixtures/cbip-canonical-covers/`) | ≥80% | INVARIANT (operator-run) |

Canonical panel: 20 covers spanning typography-heavy (Madvillainy, The Low End Theory), abstract (My Bloody Valentine — Loveless, Aphex Twin — Selected Ambient Works), figurative (Liquid Swords, Marquee Moon), monochrome (Joy Division — Unknown Pleasures), color-field (Black on Black). Operator runs Human-ID test once per family at first ship + on every threshold change.

INVARIANT failures block PR merge via CI gate `tests/studio_compositor/cbip/test_recognizability_invariants.py`.

## §5 Ring-2 WARD pre-render gate

CBIP renders at `SurfaceKind.WARD`. Per Ring 2 monetization governance, every enhancement output MUST pass three gates before reaching broadcast:

| Gate | Check | Action on fail |
|---|---|---|
| Content-ID matchability | Audio fingerprint of associated track present in copyright-clear set | Block render; substitute Phase 0 output |
| Copyright freshness | Album metadata age <90 days from last copyright check | Re-check via copyright-status API; cache 24h |
| Demonetization risk | Vision-classifier risk score on rendered output ≤0.4 | Block render; substitute Phase 0 output |

Implementation: `agents/studio_compositor/cbip/ring2_gate.py::Ring2PreRenderGate.evaluate(rendered_output, album_metadata) -> GateResult`. Wired between enhancement-family render and final compositor blit.

## §6 Operator override surface

Two override channels:

### §6.1 Stimmung-coupled default

`agents/studio_compositor/cbip/intensity_router.py` reads stimmung dimensions:
- `intensity` ≥ 0.7 → enhancement intensity 1.0 (full Family 2 stack)
- `intensity` 0.4–0.7 → enhancement intensity 0.5 (Family 1 only, mid-strength)
- `intensity` < 0.4 → enhancement intensity 0.0 (Phase 0 deterministic tint only)
- `coherence` < 0.3 → force Phase 0 fallback (degraded mode, prefer recognizability)

### §6.2 Manual override slider

Logos UI exposes `cbip.intensity_override` (0–100% or "auto"). Persists to `~/.cache/hapax/cbip/intensity-override.json` (atomic-write). When non-auto, overrides §6.1 entirely. Surfaces in Logos right-sidebar under Studio panel.

## §7 Phasing

| Phase | Scope | Owner | Estimated |
|---|---|---|---|
| 1.1 | `posterize` node + WGSL shader + tests | delta | 1 day |
| 1.2 | `kuwahara` node + WGSL compute shader + tests | delta | 2 days |
| 1.3 | `palette_extract` node + Cairo overlay + tests | delta | 1 day |
| 1.4 | Recognizability test harness + canonical 20-cover fixture set | delta + operator | 1 day + operator panel-run |
| 1.5 | Family 1 (Palette Lineage) compose + acceptance test | delta | 1 day |
| 1.6 | Family 2 (Poster Print) compose + acceptance test | delta | 1 day |
| 1.7 | Ring-2 pre-render gate | delta | 1 day |
| 1.8 | Stimmung intensity router | delta | half day |
| 1.9 | Logos manual override slider | alpha | half day |
| 1.10 | E2E smoke + ship | delta | half day |

**Phase 2 preview (next spec):** Round structure (chess deliberative ↔ boxing reactive) wired into programme manager + AlbumOverlayCairoSource render cadence.

## §8 Out of scope (Phase 1)

- Round structure (Phase 2)
- Family 3 (Contour Forward / Sobel edges) — Phase 2
- Family 4 (Dither & Degradation) — Phase 2
- Family 5 (Glitch Burst) — Phase 3 (requires reactive round to exist)
- Cross-modal objects (books, instruments, figures) — Phase 3
- Sacrifice primitive — Phase 4
- Lineage-chain attribution propagation — Phase 4
- Spec relocation `/homage/` → `/cbip/` — not happening (CBIP stays under HOMAGE umbrella)

## §9 References (source of truth)

- Operator directive: `~/.cache/hapax/relay/delta-queue-cbip-vinyl-enhancement-20260420.md`
- CBIP concept: `docs/research/2026-04-20-cbip-1-name-cultural-lineage.md`
- Enhancement families research: `docs/research/2026-04-20-cbip-vinyl-enhancement-research.md`
- Phase 0 commit: `a9573c93b` (PR #1112)
- Delta audit: `~/.cache/hapax/relay/audit/oq3-cbip-history-delta-2026-04-21.md`
