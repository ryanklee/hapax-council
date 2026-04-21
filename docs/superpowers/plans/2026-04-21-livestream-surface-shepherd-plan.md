---
date: 2026-04-21
author: delta
audience: alpha (primary owner for most items), delta (co-owner on diagnostics + cleanup), operator (disposition + priority)
status: plan — shepherding the livestream surface inventory audit
scope: sequence 10 findings from the 2026-04-21 livestream surface audit into bounded workstreams with owners + priorities + dependencies
source: docs/research/2026-04-21-livestream-surface-inventory-audit.md
---

# Livestream Surface Shepherd Plan

Ten findings from the 2026-04-21 audit, sequenced for execution. Priority ranking follows operator-visibility (Finding 4.1–4.6) with operator-surfaced blinking issue at P0.

## Priority order

| # | Finding | Priority | Owner | Depends on | cc-task slug |
|---|---|---|---|---|---|
| J | HOMAGE ward blinking | P0 | alpha | none | ls-shepherd-blink-audit |
| A2 | GEM rendering redesign (ticker-tape → mural) | P0 | alpha | brainstorming + operator input | ls-shepherd-gem-rendering-redesign |
| A1 | GEM recruitment pipeline | P1 | alpha | #1175 merged | ls-shepherd-gem-recruitment |
| C | `placement_bias` emission | P2 | alpha | none | ls-shepherd-placement-bias-investigate |
| D | Small ward shader domination | P2 | alpha | item J (blink audit) produces luminance harness | ls-shepherd-small-ward-shader |
| E | Micromove fallback retirement | P3 | alpha | expert-system-blinding audit | ls-shepherd-micromove-retirement |
| G | Camera-hero variety/dwell retirement | P3 | alpha | expert-system-blinding audit | ls-shepherd-camera-hero-retirement |
| F | Ward-highlight recruitment catalog | P3 | delta | none | ls-shepherd-ward-highlight-catalog |
| B | Overlay-zones producer | P4 | alpha | brainstorming first | ls-shepherd-overlay-zones-producer |
| H | Orphan ward entries cleanup | P4 | delta | none | ls-shepherd-orphan-ward-cleanup |
| I | Captions strip retirement | P5 | alpha | item A1 + A2 (GEM lands first) | ls-shepherd-captions-retirement |

## Item J — HOMAGE blinking audit + remediation (P0)

**Outcome:** no visual element changes luminance by > 40% faster than once every 500 ms on the broadcast surface, except explicit consented token-reward flashes.

**Deliverables:**
1. Luminance delta harness — script that records 10 s of `/dev/shm/hapax-compositor/frames/*.jpg` (or samples the RTMP output) and computes per-ward per-frame luminance deltas with threshold alerts.
2. Audit report identifying every ward that exceeds the threshold.
3. Remediation PRs — one per identified offender. Replace step-functions with smooth envelopes (ease-in-out / sine / log decay / crossfade 200–600 ms).
4. Regression test: harness runs in CI on a rendered-frame fixture; fails if threshold exceeded.

**Candidate offenders (enumeration from audit §3.J; measurement required to confirm):**
- `activity_header` 200 ms inverse-flash
- `stance_indicator` stance-Hz pulse amplitude envelope
- `thinking_indicator` 6 Hz breath
- `token_pole` sparkle-burst timing
- HOMAGE choreographer rotation snap
- ward-stimmung-modulator opacity step changes

**Risk:** softening pulses may read as "less alive" — watch for over-damping. Cross-ref `feedback_show_dont_tell_director.md`: the goal is embodied state, not announced state.

## Item A2 — GEM rendering redesign (P0)

**Outcome:** GEM renders at Sierpinski-caliber visual interest. No longer reads as chyron / ticker-tape.

**Source:** operator feedback 2026-04-21: *"looks like chiron or ticker tape not a cool fucking digital graffiti mural… If it's not as cool as the sierpinski triangle without cribbing the look it's not cool enough."* Cross-ref `feedback_gem_aesthetic_bar.md`.

**Current state:** `render_emphasis_template` produces 3-frame box-banner + `» text «` fade. One font, one line, no depth, no process.

**Bar to clear:** multi-layer composition, algorithmic process visible, depth in the 1840×240 canvas, frame-by-frame animation actually used. Grammar primitives: CP437 + Px437 + BitchX punctuation + box-draw + Braille density. Governance invariants still hold (CP437 only, no faces / humanoid, emoji refused, Pearson face-correlation < 0.6).

**Deliverables:**
1. Brainstorming session (`superpowers:brainstorming` skill) with operator to pick 2–3 candidate directions from the solution space:
   - Layered box-draw scaffolding with content drifting through
   - Braille-density shadows casting behind foreground glyphs
   - Animated "spray" letter-by-letter emergence
   - Multi-region zones each doing different things simultaneously
   - Depth cues via overdraw / occlusion / variable-weight rasters
2. Spec doc per selected direction.
3. Implementation plan + execution PR.
4. Recognizability / aesthetic harness: snapshot 20 frames against the new renderer, operator sign-off before merge.
5. Sequence AFTER item A1 lands so recruitment signal is already flowing when the new renderer activates (no empty-slot risk).

**Risk:** over-investment in rendering before content pipeline is mature. Mitigation: brainstorm first with time-box, converge on smallest-viable direction that clears the bar, iterate.

## Item A1 — GEM recruitment pipeline (P1)

**Outcome:** director's LLM emits `gem.emphasis` / `gem.composition` intents via grounded narrative path; producer authors mural frames; ward shows real content (still template-rendered until A2 ships).

**Deliverables:**
1. Director prompt extension: add `gem.emphasis` / `gem.composition` to the set of families the LLM is encouraged to emit when narrative emphasis is appropriate.
2. Affordance catalog seeding: verify `expression.gem_mural` is in the Qdrant `affordances` collection with proper Gibson-verb description (already seeded in `shared/affordance_registry.py::GEM_AFFORDANCES`; verify live state).
3. Optional — opt-in `HAPAX_GEM_LLM_AUTHORING=1` env flag on daimonion systemd unit so Kokoro-level authoring runs instead of template fallback.
4. Live verification: director-intent.jsonl contains gem.* entries; producer writes to gem-frames.json; CairoSource renders non-fallback text.

**Depends on:** PR #1175 merged (removes fallback micromove leakage). Currently open, CI red.

**Note:** item A1 without A2 still renders in the current ticker-tape aesthetic. That's acceptable as an intermediate state — at least real content flows — but A2 is the real fix.

## Item C — `placement_bias` emission investigation (P2)

**Outcome:** `StructuralIntent.placement_bias` field appears in director-intent.jsonl on every tick; ward-stimmung-modulator applies it.

**Diagnostic steps:**
1. `grep placement_bias` on 1000 most-recent director-intent.jsonl entries — confirm absence at scale.
2. Inspect director prompt — does it elicit `placement_bias`?
3. Inspect `_parse_intent_from_llm` — is the field silently dropped on parse?
4. Confirm Pydantic schema accepts it.
5. Fix per root cause.

## Item D — Small ward shader domination mitigation (P2)

**Outcome:** stance_indicator + thinking_indicator remain legible against worst-case shader preset.

**Deliverables:**
1. Reuse item J's luminance harness to measure stance/thinking contrast against halftone + chromatic presets.
2. If still insufficient post-blink-smoothing: audit `non_destructive` flag, consider outline contrast bump, evaluate geometric size bump.

**Depends on:** item J (harness).

## Item E — Micromove fallback retirement (P3)

**Outcome:** `_narrative_too_similar` + `_emit_micromove_fallback` paths retired; narrative similarity gating lives in affordance-pipeline impingement-family deduplication.

**Spec:** `docs/research/2026-04-19-expert-system-blinding-audit.md` §1 Category A.
**Deliverables:** multi-phase plan (separate from this shepherd) because retirement needs recruitment-pipeline signal migration; scope it once item A lands and recruitment signal path is clearer.

## Item G — Camera-hero variety / dwell retirement (P3)

**Outcome:** `compositional_consumer.dispatch_camera_hero` no longer overrides recruitment outcomes via hardcoded gates.

**Spec:** expert-system-blinding-audit §1 Category A.
**Deliverables:** migrate recency / dwell signals into affordance-pipeline context so recruitment can natively weight them.

## Item F — Ward-highlight recruitment catalog (P3)

**Outcome:** `family-restricted retrieval returned no candidates` stops firing for `ward.highlight.<ward_id>` queries.

**Deliverables:**
1. Enumerate all ward-highlight-* capabilities with Gibson-verb descriptions.
2. Seed Qdrant.
3. Tune cosine threshold if needed (prior audit flagged ≥0.50 may be narrow).
4. Regression test against 10 known-good narrative samples.

## Item B — Overlay-zones producer (P4)

**Outcome:** main / research / lyrics zones have an active producer populating Pango-markdown content.

**Scope-define via brainstorming first** — content source per zone is an open design question:
- `main`: operator-authored ephemeral announcements? DMN-authored observations? Research-domain LLM output?
- `research`: grounding citations from director? research-measure snapshots? sprint-tracker state?
- `lyrics`: vinyl metadata + track-position timecodes? SoundCloud bed text?

Do NOT ship a producer before the content-source decision. Operator input required.

## Item H — Orphan ward cleanup (P4)

**Outcome:** `ward-properties.json` contains only layout-declared + overlay-zone + camera-PiP + YT-slot wards.

**Deliverables:**
1. Audit ward-properties.json production path in `ward_property_manager.py` (or equivalent).
2. Filter out orphans: `vinyl_platter`, `objectives_overlay`, `music_candidate_surfacer`, `scene_director`, `structural_director`.
3. Regression test: orphan entries absent on fresh startup.

## Item I — Captions strip retirement (P5)

**Outcome:** captions strip removed from layout; lower-band 1840×110 geometry claimed by GEM.

**Depends on:** item A (GEM must be live before captions retire — invariant from existing captions-deprecating memo).

## Execution notes

- This plan is a shepherd for the audit, NOT a spec. Each item above still needs its own spec + plan per standard SDLC before execution, except item H (trivial cleanup) and item F (small enough to brainstorm → ship in one cycle).
- Items J + A are the two P0/P1 items with operator-visibility consequences. Sequence J first (blink is actively watchability-breaking; GEM latency is less painful because the fallback frame isn't *bad*, just static).
- Items E, G, F touch the affordance pipeline and should be sequenced together after item A lands so the recruitment signal path is proven.
- Item B (overlay-zones) needs brainstorming before scoping; filing the cc-task to surface the design question to the operator.

## Related

- Source: `docs/research/2026-04-21-livestream-surface-inventory-audit.md`
- HOMAGE umbrella: `docs/superpowers/specs/2026-04-20-homage-ward-umbrella-design.md`
- Per-ward opacity audit: `docs/research/2026-04-21-per-ward-opacity-audit.md`
- Expert-system blinding audit: `docs/research/2026-04-19-expert-system-blinding-audit.md`
- GEM activation plan: `docs/superpowers/plans/2026-04-21-gem-ward-activation-plan.md`
- Operator feedback memory: `feedback_no_blinking_homage_wards.md`
