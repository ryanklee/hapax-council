# Nebulous Scrim Three-Bound Invariants — Research-to-Plan Triage

**Status:** RESEARCH-TO-PLAN TRIAGE CANDIDATE (promoted from `~/.cache/hapax/relay/alpha.yaml` OQ-02 per operator delegation 2026-04-20)
**Owner:** alpha (HOMAGE/scrim family)
**Promoted by:** alpha (operator-decision delegation 2026-04-20T17:30Z)
**Cross-link:** D-25 (OQ-01) is the smallest concrete bound-2 instance and ships the brightness-ceiling pattern this epic generalizes.

## 1. Origin

Operator queue-add 2026-04-20 in `~/.cache/hapax/relay/alpha.yaml` (`operator_queue_adds_20260420.OQ-02`). Three constraints stated by operator across three messages:

1. *"every effect and combination of effects used by Hapax in the Nebulous Scrim must be guaranteed to be face pseudo-anonymizing (facial features fine, recognize my face easily, not fine at all)"*
2. *"effects must never be so strong that the fact that there is a studio with inhabitants with interesting objects and content never disappears. The nebulous scrim should ALWAYS be that — a nebulous scrim."*
3. *"It must NEVER look like a simple audio visualizer. That is NOT the point. Although AUDIO reactivity remains key."*

## 2. The triple invariant

Three HARD bounds on every scrim effect AND every chain of effects:

| Bound | Semantics | Failure mode |
|---|---|---|
| **B1 — anti-recognition** | Face-recognition distance against operator's enrolled embedding > identifiability threshold | Effects too weak; identity leaks |
| **B2 — anti-opacity / scrim-translucency** | Scene-legibility metric > minimum threshold; audience can always perceive a studio with inhabitants, objects, content | Effects too strong; studio dissolves into abstract pattern |
| **B3 — anti-audio-visualizer** | Visualizer-register score < threshold; audio modulates but does not iconographically illustrate | Surface drifts into Winamp/MilkDrop register |

Audio reactivity is preserved (it's the right input); audio iconography is forbidden (no FFT-to-geometry, no beat-synced symmetric pulses, no waveform/spectrum wards).

## 3. Coverage today

### Bound 1 (anti-recognition)
- `nebulous-scrim-design` §7 invariants 2 + 4: face-obscure (#129) runs at camera producer layer BEFORE scrim compositor. Scrim does not count as obscuring for consent.
- §10 Q1 was OPEN; **DECIDED 2026-04-20: face-obscure BEFORE scrim** (matches existing pipeline architecture per CLAUDE.md § Unified Semantic Recruitment; matches design's own proposal).
- Covers raw camera-pixel feed only. Per-effect / per-combination preservation is NOT proven.

### Bound 2 (scrim-translucency)
- `nebulous-scrim-design` §7 invariant 2 states "Studio remains readable" but is presently a doc invariant only — no enforced metric, no test, no runtime check.
- HOMAGE-scrim-3 §10 anti-anthropomorph constraint is enforced in spirit; analogous legibility-preservation constraint is NOT.

### Bound 3 (anti-audio-visualizer)
- No coverage today. Audio reactivity is wired (impingement → uniform deltas, bloom glow_strength = f(audio_energy)) but no constraint prevents drift into Winamp-register patterns.

### What's NOT guaranteed today (all three bounds)
- Per-effect proof: each scrim effect / WGSL pass preserves all three bounds.
- Per-combination proof: pairwise / k-wise compositions don't violate any bound.
- Specific risk surfaces:
  - **B1:** temporal-feedback nodes (rd, feedback, drift) accumulate frames → effective super-resolution; sharpen / unsharp-mask invert blur; contrast + saturation push amplify residual identity-bearing chroma; color-quantize + temporal jitter produce face-shape silhouette.
  - **B2:** high scrim density + heavy bloom + max colorgrade.brightness saturate to white (verified instance: D-25 / OQ-01 neon — see §6); postprocess vignette + noise crush mid-tones to black; reverie temporal-feedback at extreme decay produces trail-only abstraction; material→color material_id swing converts scene to single-hue field.
  - **B3:** tight 1:1 BPM-locked geometric modulation; FFT-band → spatial direct mapping; symmetric radial bloom centered on screen middle pulsing on beats; waveform-shaped ward content; spectrum-bar overlays.

## 4. Phased plan stub (≥3 PR-sized phases — to be expanded into a full plan)

### Phase 1 — Metric selection and oracle authoring
- Pick one of three candidate metrics for each bound.
  - B1 candidate: face-recognition distance (e.g. InsightFace SCRFD embedding L2 against operator's enrolled embedding) > threshold.
  - B2 candidate: SSIM / MS-SSIM with floor; OR structural-content score (edge-density preservation + multi-scale luminance variance + color-channel entropy floor); OR learned classifier (studio-with-people vs abstract-pattern).
  - B3 candidate: FFT↔geometry cross-correlation; OR radial-symmetry-on-beat detector; OR BPM-periodicity detector; OR learned classifier (music-visualizer captures vs studio-with-effects).
- Each metric must be cheap enough for runtime per-frame / rolling-window check.
- Author oracle as a Python module under `agents/effect_graph/invariants/{anti_recognition,scrim_translucency,anti_visualizer}.py`.
- Acceptance: each metric returns a deterministic score on a fixed reference frame.

### Phase 2 — Test harness across all effects and chains
- Render N reference frames (with face-obscure ON) plus N studio-scene frames.
- Pipe through every scrim effect individually AND every shipped chain.
- Vary audio inputs: silence, broadband, periodic-beat, full-mix music.
- Assert all three bounds for every (effect, audio profile) and (chain, audio profile) combination.
- New tests under `tests/effect_graph/invariants/test_three_bound_*.py`.

### Phase 3 — Temporal-feedback integration tests
- 60-frame integration tests on rd / feedback / drift nodes:
  - B1: feedback decays below identifiability after N frames AND stays above legibility?
  - B1: integrates ABOVE identifiability if obscure pattern is stable?
  - B3: doesn't produce beat-synced trail-rings under periodic audio?

### Phase 4 — CI gate
- Block PRs that add new effects or chains without passing all three metrics under all four audio profiles.

### Phase 5 — Runtime checks (live, on-stream)
- B1: sentinel pixel pattern injected into obscure (or checksum on obscured-pixel statistics) — fail loudly on obscure-bypass bug.
- B2: per-frame scene-legibility on egress; if below threshold for >K consecutive frames, force scrim density toward minimum and emit degraded signal.
- B3: rolling-window visualizer-score on egress (5s window); if above threshold, dampen audio→geometry coupling gain (do NOT mute audio reactivity entirely; lower the slope).

### Phase 6 — Document promotion
- Promote `nebulous-scrim-design` §7 invariant 2 from prose-invariant to enforced-invariant with numeric threshold.
- Add new §7 invariant: *"Scrim is never a music visualizer. Audio modulates the scrim; the scrim does not illustrate the audio. No FFT-to-geometry mapping, no beat-synced symmetric pulses, no waveform/spectrum iconography."*

## 5. Acceptance for the planning epic itself

The planning epic is complete (and ready to enter implementation triage) when:

- (a) One of three candidate metrics is committed for each bound, with named test/oracle.
- (b) Phased plan stub at `docs/superpowers/plans/2026-04-2X-nebulous-scrim-invariants-plan.md` enumerating ≥3 PR-sized phases.
- (c) Cross-link to OQ-01 (D-25) fix as the bound-2 reference instance.
- (d) Decision recorded on §10 Q1 (face-obscure ordering) — DECIDED: BEFORE.
- (e) Operator review and explicit GO/NO-GO before any inline ship of enforced metrics.

## 6. Cross-link to OQ-01 / D-25

OQ-01 (white-edge neon) is the first verified bound-2 violation in production. The fix shipped 2026-04-20 establishes the brightness-ceiling pattern this epic generalizes:

- New `palette_remap` shader node injects synthwave palette before colorgrade so edges aren't grayscale-then-hue-rotated (a no-op).
- `colorgrade.brightness` capped 1.1 → 0.85 in `presets/neon.json` to prevent saturation-to-white when combined with bloom.
- Smoketest `tests/effect_graph/test_neon_palette_cycle.py::test_neon_preset_brightness_ceiling` explicitly cites OQ-02 bound-2 as the rationale.

Pattern: **every preset whose chain ends in `colorgrade + bloom` should be audited for the same brightness-ceiling.** This is a hand-applied bound-2 enforcement until the Phase 5 runtime check exists.

## 7. Sources

- `~/.cache/hapax/relay/alpha.yaml` `operator_queue_adds_20260420.OQ-02`
- `docs/research/2026-04-20-nebulous-scrim-design.md` §7, §10 Q1
- `docs/research/2026-04-20-homage-scrim-3-nebulous-scrim-architecture.md` §10 anti-anthropomorph
- `agents/studio_compositor/face_obscure_integration.py` (#129 pixelation pipeline)
- `presets/neon.json` (D-25 ship — bound-2 reference instance)
- `tests/effect_graph/test_neon_palette_cycle.py` (D-25 invariant assertions)
- Memory: `project_hardm_anti_anthropomorphization` (CVS #16 anti-personification — visual sibling of B3 anti-visualizer)
- Memory: `feedback_show_dont_tell_director` (B3 spirit: action IS the communication, not a rendered illustration)
