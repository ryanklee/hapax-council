---
date: 2026-04-21
author: alpha
audience: alpha (execution), delta (umbrella governance), operator (review)
register: scientific, neutral
status: plan — ready to execute
scope: activate GEM (Graffiti Emphasis Mural) as the 15th HOMAGE ward; retire captions in same geometry
related:
  - docs/research/2026-04-19-gem-ward-design.md (canonical design)
  - docs/superpowers/specs/2026-04-20-homage-ward-umbrella-design.md (umbrella governance + §4.1bis)
  - config/ward_enhancement_profiles.yaml (`gem` profile, this PR)
  - agents/studio_compositor/homage/transitional_source.py (FSM base class)
  - agents/studio_compositor/captions_source.py (surface being retired)
  - agents/studio_compositor/hardm_source.py (reference emissive Cairo ward)
  - shared/homage_package.py (BitchX mIRC-16 grammar + AntiPatternKind enforcement)
governing-axioms:
  - single_user (constitutional)
  - executive_function (constitutional)
locked decisions (operator 2026-04-21):
  - GEM = ward #15
  - chat_keywords = ward #16
  - GEM activation PR ships first; profile-sweep second
  - Captions retires at GEM cutover (lower-band geometry collision)
---

# GEM Ward Activation Plan

GEM (Graffiti Emphasis Mural) is the operator-directed 15th HOMAGE ward (commit `b6ec4a723`, 2026-04-19). Design at `docs/research/2026-04-19-gem-ward-design.md`. This plan ships the activation: render code, layout binding, producer wiring, captions retirement, governance gate.

## §1 Phases

### Phase 1 — Render class (alpha, ~1 day)

Build `agents/studio_compositor/gem_source.py::GemCairoSource` inheriting from `HomageTransitionalSource`. Pattern after `HardmDotMatrix` (single most architecturally adjacent ward):

- BitchX palette enforcement via `shared/homage_package.HomagePackage`
- CP437-only raster (Px437 IBM VGA 8x16 font, no anti-aliasing)
- Frame-by-frame keyframe composition: read `/dev/shm/hapax-compositor/gem-frames.json`
- AntiPatternKind enforcement: emoji REJECTED at render time (ValueError → fallback frame)
- HARDM gate: composition rejected if Pearson face-correlation ≥0.6 (`shared.hardm_validator.is_face_like`)
- Render cadence: 4–8 fps (matches GEM design §3.2 keyframe cadence; not 30 fps)

**Tests:** `tests/studio_compositor/test_gem_source.py` covering palette purity, CP437 enforcement, anti-emoji rejection, HARDM gate, cadence.

### Phase 2 — Layout binding (alpha, ~1 hour)

Edit `config/compositor-layouts/default.json`:

- Add source `gem` (Cairo) → surface `gem-mural-bottom` at `{x: 40, y: 820, w: 1840, h: 240, z_order: 30}` (matches GEM design §2.1: lower-band geometry, replaces removed captions strip).
- **Mark `captions` source `enabled: false`** (retire). Surface `captions_strip` removed.
- Update assignment: `gem` → `gem-mural-bottom`.

### Phase 3 — Producer wiring (alpha, ~1 day)

Hapax must AUTHOR gem frames; this is not a passive surface.

- New module `agents/hapax_daimonion/gem_producer.py`:
  - Subscribes to impingement bus (`/dev/shm/hapax-dmn/impingements.jsonl`)
  - On `intent_family ∈ {"gem.emphasis.*", "gem.composition.*"}`, generates a 1–N keyframe sequence via LLM call (capable tier, ~200 token budget)
  - Validates output against AntiPatternKind taxonomy (no emoji, no proportional, no humanoid)
  - Writes atomic-rename to `/dev/shm/hapax-compositor/gem-frames.json`
- Spawn from `agents/hapax_daimonion/run_loops_aux.py` (mirror `impingement_consumer_loop` pattern).
- Affordance registration: 2 capabilities in `shared/affordance_pipeline.py`:
  - `gem.emphasis` — Gibson verb: "highlight a fragment with mural-style emphasis"
  - `gem.composition` — Gibson verb: "compose abstract glyph animation"

### Phase 4 — Choreographer integration (alpha, ~half day)

Wire GEM into the homage choreographer FSM:

- `agents/studio_compositor/homage/choreographer.py`: add `gem` to ward-rotation candidate set
- `agents/studio_compositor/homage/transitional_source.py`: confirm GEM enters `ABSENT → ENTERING → HOLD` cycle (Phase B3 hotfix doesn't bypass new wards)
- Visual entry: `ticker-scroll-in` (per HOMAGE framework default)

### Phase 5 — Captions retirement (alpha, ~1 hour)

- Mark `agents/studio_compositor/captions_source.py` deprecated (module-level docstring + import warning).
- Drop `captions_source.py` instantiation from `agents/studio_compositor/compositor.py`.
- Remove `captions` profile from `config/ward_enhancement_profiles.yaml` (only after GEM lands in production).
- Update `tests/studio_compositor/test_captions_acceptance.py` → skip with deprecation message.

### Phase 6 — Governance + observability (alpha + delta, ~half day)

- WardEnhancementProfile gate: GEM profile already shipped in YAML; CI runs schema validation.
- OQ-02 three-bound test extension: `tests/studio_compositor/homage/test_oq02_bounds_per_ward.py` includes `gem`.
- Prometheus metrics: `hapax_homage_render_cadence_hz{ward="gem"}`, `hapax_homage_transition_total{ward="gem",...}`.
- Grafana panel: add `gem` to homage-wards dashboard (mirror `hardm_dot_matrix` panel structure).

### Phase 7 — Smoke + ship

- Live smoke: trigger synthetic `gem.emphasis` impingement; observe lower-band ward render.
- E2E: 10-minute observation that GEM cycles through HOLD/ENTERING transitions.
- Ship PR.

## §2 Owner / coordination

- **Alpha** owns Phases 1–5, 7.
- **Delta** owns Phase 6 governance integration (B7 HOMAGE umbrella hardening; this becomes the GEM-shaped instance of B7 work).

## §3 Risks

- **HARDM Pearson gate may reject valid Hapax-authored compositions** if the LLM occasionally drifts toward humanoid layouts. Mitigation: aggressive AntiPatternKind taxonomy in the producer's prompt + retry-with-alternate-seed up to 3 times before falling back to a known-safe template.
- **Lower-band collision during cutover**: if captions producer continues writing while GEM source is added, layout gets two surfaces in same geometry. Mitigation: Phase 2 explicitly disables captions source before adding GEM source.
- **Frame-rate mismatch**: GEM at 4–8 fps in a 30 fps compositor pipeline could cause judder. Mitigation: cache last-frame and re-blit on render-thread tick.

## §4 Out of scope (deferred to follow-on)

- Chat-keywords ward (#16) — separate PR.
- GEM<->reverie scrim coupling (depth-conditioned tint of GEM raster) — deferred to umbrella hardening.
- Per-keyframe Ring-2 monetization gate — deferred until first live broadcast risk.
