---
date: 2026-04-21
author: delta
audience: alpha + delta (follow-on work), operator (disposition)
register: scientific, neutral
status: research — audit output; follow-on plan in `docs/superpowers/plans/2026-04-21-livestream-surface-shepherd-plan.md`
scope: Complete inventory of every visual entity on the livestream broadcast surface — ward / overlay / shader / camera — cross-referenced against specs and plans, with live-state verification and identification of missing or broken items.
related:
  - docs/research/2026-04-20-nebulous-scrim-design.md
  - docs/superpowers/specs/2026-04-21-ward-stimmung-modulator-design.md
  - docs/superpowers/specs/2026-04-20-homage-ward-umbrella-design.md
  - docs/research/2026-04-19-gem-ward-design.md
  - docs/research/2026-04-19-expert-system-blinding-audit.md
  - docs/research/2026-04-21-per-ward-opacity-audit.md
  - docs/superpowers/plans/2026-04-21-gem-ward-activation-plan.md
---

# Livestream Surface Audit — Comprehensive Visual Inventory

**Capture time:** 2026-04-21 ~17:16 UTC (live state snapshot)
**Method:** read-only inspection of compositor modules, layout config, affordance registry, `/dev/shm` producer files, director intent JSONL, and systemd service state. Cross-referenced against HOMAGE umbrella spec + GEM activation plan + per-ward opacity audit + expert-system blinding audit.

## Executive summary

The broadcast surface composites **19 active Cairo wards + 1 dormant producer (GEM) + the reverie substrate + 6 camera PiP slots + 1 shader effect chain**. Findings:

- 19 wards ALIVE and producing Cairo surfaces on schedule.
- 4 wards registered in `ward-properties.json` but NOT in any layout (orphan metadata — never rendered).
- 1 ward declared in layout but producer starved of recruitment signal (GEM).
- 1 overlay-zone triplet infrastructure ready but no producer writing — valuable canvas real-estate unused.
- 1 captions strip dormant (scheduled retirement when GEM takes the slot).
- Ward stimmung modulator is live (z-plane + opacity attenuation flowing to ward-properties.json every ~200 ms) but **director `placement_bias` field is not observed in emitted intent records** — modulator falls back to hard-coded defaults.
- Hardcoded variety / dwell / recency gates in `compositional_consumer` override affordance recruitment outcomes at a non-trivial rate (~14% of compositional recruitments per prior audit).

See §3 for the full actionable list; §4 for five key findings ranked by operator visibility.

## 1. Frame inventory by z-plane

Measurements at **1920×1080 @ 30 fps GStreamer output**. Z-plane taxonomy per `docs/research/2026-04-20-nebulous-scrim-design.md` §4 and ward-stimmung-modulator spec §4.

### Base layer: reverie substrate (beyond-scrim attenuation)

| Field | Value |
|---|---|
| Producer | `hapax-imagination.service` (Rust wgpu) |
| Output | `/dev/shm/hapax-sources/reverie.rgba` at ~30 fps |
| Consumer | studio-compositor GStreamer pipeline |
| Director coupling | Stimmung 9-dim → `uniforms.json` → Rust per-node overrides |
| Live status | ALIVE (`current.json` <1 s stale at capture) |
| Z-plane | beyond-scrim base (depth 0.2) |

Vocabulary pipeline: `noise → rd → color → drift → breath → feedback → content_layer → postprocess`. Permanent generative process; wards composite **through** the scrim, not on top of it.

### Camera PiP tiles (beyond-scrim)

Six cameras positioned per default layout:

| Slot | Geometry (x, y, w, h) |
|---|---|
| pip-ul | 20, 20, 300, 300 |
| pip-ur | 1260, 20, 640, 360 |
| pip-ll | 20, 540, 400, 520 |
| pip-lr | 1500, 860, 400, 200 |

Producer: compositor camera pipeline (pyudev monitor + fallback on disconnect). Director coupling absent (`follow_mode.py` suggests hero camera via dispatcher, does not modulate per-tile on-screen presence).

### Content layer: album (beyond-scrim)

| Field | Value |
|---|---|
| Source | `album_overlay.py::AlbumOverlayCairoSource` |
| State files | `/dev/shm/hapax-compositor/album-cover.png`, `album-state.json` |
| Cadence | "always" (redraws only on state change) |
| Coupling | Indirect (state-file driven) |
| Live | ALIVE (17:14 capture) |

Album recognizability invariant (OCR ≥80%, dominant-contour IoU ≥0.65) enforced by pre-merge harness.

### Hothouse wards (mid-scrim primary, some promoted to surface-scrim per PR #1167)

| Name | Geometry | Producer reads | Rate | Director coupling | Live status |
|---|---|---|---|---|---|
| impingement_cascade | 480×360 | `/dev/shm/hapax-dmn/impingements.jsonl` (own cursor) | 2 Hz | indirect (stream) | ALIVE |
| recruitment_candidate_panel | 800×60 | `/dev/shm/hapax-compositor/recent-recruitment.json` | 2 Hz | affordance pipeline | ALIVE |
| thinking_indicator | 170×44 | `unified-reactivity.json` | 6 Hz | `dimension.intensity` → breath freq | ALIVE |
| pressure_gauge | 300×52 | `unified-reactivity.json` | 2 Hz | stimmung dimensions | ALIVE |
| activity_variety_log | 400×140 | director activity history | 2 Hz | director activity field | ALIVE |
| whos_here | 230×46 | `person-detection.json` + YT viewer count | 2 Hz | none | ALIVE |

stance_indicator (4,000 px²) and thinking_indicator (7,480 px²) are the two smallest wards on the surface; both were promoted to `surface-scrim` in PR #1167 to survive shader overwrite. Per-ward opacity audit (2026-04-21) flagged both as highest-risk for halftone/chromatic shader domination.

### Chrome / legibility layer (on-scrim, some surface-scrim)

| Name | Geometry | Producer | Cadence | Director coupling | Live |
|---|---|---|---|---|---|
| token_pole | 300×300 | `token-ledger.json` | "always" | token-spend events | ALIVE |
| activity_header | 800×56 | director state | 2 Hz | activity + `homage_rotation_mode` | ALIVE |
| stance_indicator | 100×40 | unified-reactivity | 2 Hz | stimmung stance FSM | ALIVE |
| grounding_provenance_ticker | 480×40 | director-intent.jsonl `grounding_provenance` | 2 Hz | direct field | ALIVE |
| chat_ambient | 320×96 | `/dev/shm/hapax-dmn/chat-state.json` | 2 Hz | chat classifier | ALIVE |
| stream_overlay | 400×200 | `fx-current.txt`, `youtube-viewer-count.txt`, `stream-mode-intent.json` | 2 Hz | none | ALIVE |
| captions | 1840×110 | no active STT ingestion wired | 4 Hz (declared) | none | DORMANT (deprecating) |
| chat_keyword_legend | 480×40 | chat classifier keyword stream | 2 Hz | indirect | ALIVE |
| research_marker_overlay | conditional | `~/.cache/hapax/working-mode` | 2 Hz | none | ALIVE (mode-gated) |

### Geometric expression layer (HOMAGE)

| Name | What | Producer | Rate | Coupling | Live |
|---|---|---|---|---|---|
| hardm_dot_matrix | 16×16 CP437 half-block grid | `hardm-cell-signals.json` (family recruitment) | 15 Hz | affordance `expression.hardm_*` | ALIVE |
| sierpinski | fractal scaffold + 3 YT frame slots | `yt-frame-{0,1,2}.jpg` | "always" | `content.sierpinski_content` | ALIVE |

Invariants: Pearson face-correlation <0.6 on both (anti-anthropomorphization).

### Lower-band expression (GEM) — LATENT

| Field | Value |
|---|---|
| Geometry | 40, 820, 1840, 240 (lower-band, post PR #1171) |
| Producer | `agents/hapax_daimonion/gem_producer.py` |
| Output | `/dev/shm/hapax-compositor/gem-frames.json` |
| CairoSource | `agents/studio_compositor/gem_source.py::GemCairoSource` |
| Director coupling | **BROKEN** — affordance pipeline not recruiting `expression.gem_mural` |
| Live status | LATENT — frames.json last update 16:48 (27 min stale at capture) |

GEM is wired end-to-end (layout declares source, CairoSource renders, producer code exists, SHM path valid, `IntentFamily` Literal opened in PR #1171) but **no recruitment path emits `gem.*` intents into the director**. PR #1175 (delta, open) removed `gem.emphasis` from the director's fallback micromove cycle after diagnosing meta-instruction leakage into mural content. The fallback removal is correct; what's missing is a grounded entry point so the director's LLM (not the fallback) emits `gem.*` when appropriate.

Until wired, GEM renders its static `» hapax «` fallback frame.

### Legibility overlays

| Name | Geometry | Producer | Status |
|---|---|---|---|
| overlay_zones (main / research / lyrics) | 3 named zones | none active | **DORMANT** |

Zones registered in `overlay_zones.ZONES` + SHM consumers ready, but no active writer. Mid-canvas real-estate unused. Research breakthroughs + emergent insights + research-domain knowledge outputs have no surface.

## 2. Ward / overlay matrix

| Ward | Spec | Layout | Producer | Rendering | Director coupling | Live |
|---|---|---|---|---|---|---|
| token_pole | ✓ | ✓ | ✓ | ✓ | ✓ token events | ✓ |
| album | ✓ | ✓ | ✓ | ✓ | ~ indirect | ✓ |
| stream_overlay | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| sierpinski | ✓ | ✓ | ✓ | ✓ | ✓ content | ✓ |
| reverie | ✓ (substrate) | ✓ | ✓ | ✓ | ✓ 9 dims | ✓ |
| activity_header | ✓ | ✓ | ✓ | ✓ | ✓ activity + rotation | ✓ |
| stance_indicator | ✓ | ✓ | ✓ | ✓ (surface-scrim) | ✓ stance FSM | ✓ |
| chat_ambient | ✓ | ✓ | ✓ | ✓ | ~ classifier | ✓ |
| captions | ✓ | ✓ | ✗ idle | ✗ empty | ✗ | DORMANT |
| gem | ✓ | ✓ | ⚠ waiting on recruitment | ✓ ready | **✗ BROKEN** | LATENT |
| grounding_provenance_ticker | ✓ | ✓ | ✓ | ✓ | ✓ grounding | ✓ |
| impingement_cascade | ✓ | ✓ | ✓ | ✓ | ✓ stream | ✓ |
| recruitment_candidate_panel | ✓ | ✓ | ✓ | ✓ | ✓ pipeline | ✓ |
| thinking_indicator | ✓ | ✓ | ✓ | ✓ (promoted) | ✓ intensity | ✓ |
| pressure_gauge | ✓ | ✓ | ✓ | ✓ | ✓ dimensions | ✓ |
| activity_variety_log | ✓ | ✓ | ✓ | ✓ | ✓ activity | ✓ |
| whos_here | ✓ | ✓ | ✓ | ✓ (promoted) | ✓ IR + viewer | ✓ |
| hardm_dot_matrix | ✓ | ✓ | ✓ | ✓ | ✓ family recruitment | ✓ |
| chat_keyword_legend | ✓ | ✓ | ✓ | ✓ | ~ classifier | ✓ |
| research_marker_overlay | ✓ | ✓ | ✓ | ✓ | ✗ (system state) | ✓ |
| overlay_zones | ~ partial | ✓ | ✗ no writer | ✗ empty | ✗ | DORMANT |
| vinyl_platter | ✗ | ✗ | ⚠ class only | ✗ | ✗ | orphan |
| objectives_overlay | ✗ | ✗ | ⚠ class only | ✗ | ✗ | orphan |
| music_candidate_surfacer | ✗ | ✗ | ⚠ class only | ✗ | ✗ | orphan |
| scene_director | ✗ | ✗ | ⚠ SHM entry only | ✗ | ✗ | orphan |
| structural_director | ✗ | ✗ | ⚠ SHM entry stale >1h | ✗ | ✗ unused | orphan |

## 3. Missing or broken — actionable list

### A1. GEM recruitment pipeline (wiring gap)

**Spec:** `docs/research/2026-04-19-gem-ward-design.md` §2.1–2.2; HOMAGE umbrella §4.1bis.
**Expected:** affordance pipeline recruits `expression.gem_mural` on impingement narratives → producer emits `GemComposition` JSON → CairoSource renders at 12 Hz.
**Current:** Literal open (PR #1171), producer wired, SHM path live, fallback de-risked (PR #1175 open). No grounded entry point wired.
**Impact:** 1840×240 lower-band geometry reserved but rendering static fallback.
**Disposition:** NEW WORK — director prompt extension + affordance catalog seeding + recruitment path verification.

### A2. GEM rendering is a ticker-tape failure state (operator-surfaced)

**Source:** operator 2026-04-21 — *"looks like chiron or ticker tape not a cool fucking digital graffiti mural… If it's not as cool as the sierpinski triangle without cribbing the look it's not cool enough."*
**Current:** `render_emphasis_template` produces a three-frame banner (`┌───┐` / `│ text │` / `└───┘`) + `» text «` fade. One font, one rectangle, one line of text. Zero multi-layer composition, zero depth, zero algorithmic process visible.
**Why it fails:** Sierpinski-caliber means multi-layer algorithmic composition with process visible. Current GEM has none of that. Renders as news-crawl chrome, not mural.
**Aesthetic bar:** Sierpinski-caliber visual interest WITHOUT cribbing Sierpinski's literal look. Use CP437 + Px437 + BitchX punctuation + box-draw + Braille density to create depth and multi-region composition in the 1840×240 canvas. Frame-by-frame animation (already schema-supported) severely underused.
**Governance constraints (still hold):** CP437 only, no faces / humanoid shapes, emoji rejected, Pearson face-correlation < 0.6.
**Disposition:** NEW WORK — design spike before coding. Brainstorming required on: layered box-draw scaffolding, Braille-density shadows, animated "spray" letter-by-letter emergence, multi-region zones doing different things, depth cues via overdraw/occlusion. Operator input on preferred directions before commitment. Cross-ref `feedback_gem_aesthetic_bar.md`.

### B. Overlay-zones producer (dormancy)

**Spec:** none formal; zones registered in `overlay_zones.ZONES` with consumers ready.
**Expected:** affordance pipeline selects `communication.overlay_zone_{main,research,lyrics}` → producer writes Pango markdown JSON to SHM → CairoSource renders.
**Current:** infrastructure ready; no producer writer active.
**Impact:** mid-canvas surface unused; research/reasoning output has no visual home.
**Disposition:** NEW WORK — scope-define via brainstorming skill (content source per zone is an open design question).

### C. StructuralIntent `placement_bias` field emission (architectural)

**Spec:** volitional-grounded-director §3.2; homage-framework §3.3.1.
**Expected:** director emits `StructuralIntent.placement_bias` per tick → choreographer / ward-stimmung-modulator reads and applies z-plane / spatial-dynamism adjustments.
**Current:** field declared in schema + consumers ready; **not observed in director-intent.jsonl** per audit 2026-04-19. Modulator falls back to `WARD_Z_PLANE_DEFAULTS`.
**Impact:** operator-invisible on surface; z-plane dynamism infrastructure-ready but not narrative-driven.
**Disposition:** INVESTIGATE — trace schema parser + LLM prompt; likely either (a) prompt doesn't elicit `placement_bias`, or (b) parser silently drops it.

### D. Smallest wards vulnerable to shader overwrite

**Spec:** per-ward-opacity-audit 2026-04-21; PR #1167 mitigation.
**Evidence:** stance_indicator 4,000 px², thinking_indicator 7,480 px² — smallest wards, highest shader-domination risk. Surface-scrim promotion applied but effective opacity still ~0.6–0.8 against bright halftone/chromatic presets.
**Disposition:** DESIGN follow-up — audit `non_destructive` flag on small chrome wards, consider outline contrast + size bumps as secondary mitigation. Test against worst-case shader.

### E. Fallback micromove cycle masks recruitment failures (Category A expert system)

**Spec:** expert-system-blinding-audit 2026-04-19 §1.
**Evidence:** `_narrative_too_similar` + `_emit_micromove_fallback` fired 40+ times in 12 h audit window. Hardcoded 7-step cycle (silence / music / chat / research / ...) substitutes deterministic dispatch for recruitment outcomes.
**Impact:** director agency limited — correct silence-holds get rotated, narrative similarity treated as failure.
**Disposition:** retire per audit — move similarity-gating into affordance-pipeline impingement-family deduplication. Multi-step plan required.

### F. Ward-highlight recruitment family (partial)

**Spec:** expert-system-blinding-audit 2026-04-19 §1.3; `shared/affordance_pipeline.py` family catalog.
**Evidence:** `family-restricted retrieval returned no candidates` — 10 events in 12 h audit window for `ward.highlight.<ward_id>` queries.
**Cause:** catalog missing per-ward capabilities OR cosine threshold too narrow.
**Impact:** director intents to emphasize specific wards silently fail.
**Disposition:** INVESTIGATE — enumerate ward-highlight-* capabilities with proper Gibson-verb descriptions; tune threshold.

### G. Camera-hero variety / dwell gates (expert-system masking)

**Spec:** expert-system-blinding-audit §1 (Category A).
**Evidence:** `compositional_consumer.dispatch_camera_hero` hardcoded variety-gate (reject if used last 4 ticks) + dwell-gate (reject if dwell <8 frames) — overrides ~6,358 recruitment outcomes in 12 h (~14.1% of compositional recruitments).
**Disposition:** retire per audit — migrate recency signal into affordance pipeline.

### H. Orphan ward entries in ward-properties.json

**Evidence:** vinyl_platter, objectives_overlay, music_candidate_surfacer registered but never instantiated in layout. scene_director, structural_director exist as metadata-only entries (not CairoSources).
**Impact:** none on surface; state bloat complicates debugging.
**Disposition:** CLEANUP — audit ward-properties.json production path to include only layout-declared + overlay-zone + camera-PiP + YT-slot wards. Remove orphans on startup.

### I. Captions strip retirement

**Current:** 1840×110 lower-band geometry declared in layout, producer idle, no STT ingestion wired. Operator-visible as empty frame.
**Coupled to:** GEM activation (item A). Captions retire when GEM takes the lower-band slot.
**Disposition:** sequence AFTER GEM activation lands.

### K. HAPAX_TTS_TARGET bypassed — voice skips voice-fx-chain entirely

**Source:** live PipeWire introspection 2026-04-21 after operator "hapax voice still coming into l12 from pc super hot."
**Symptom:** voice reaches Ryzen → L-12 CH 11/12 without any of the designed voice-specific processing (biquad EQ, voice-fx-chain presence/air boost, voice-fx-loudnorm SC4 + limiter). Ends up 15–20 dB hotter than designed on broadcast.
**Evidence:**
- sink 102 (`hapax-voice-fx-capture`) = IDLE; nothing writes to it.
- sink 517 (`input.loopback.sink.role.assistant`) = RUNNING; `pw-cat` with `media.role=Assistant` writes here.
- SI516 (`output.loopback.sink.role.assistant`) forwards to Ryzen (sink 482) at 100% — no loudnorm in between.
- daimonion systemd env declares `HAPAX_TTS_TARGET=hapax-voice-fx-capture` but the flag isn't honored.
**Root cause hypothesis:** `pw-cat` subprocess (spawned by daimonion TTS) tags streams with `media.role=Assistant`. WirePlumber's role-based policy steers any assistant-role stream into the role.assistant loopback, overriding the explicit `--target` / `target.object` hint. Net effect: `HAPAX_TTS_TARGET` is a no-op for any stream that carries a role.
**Live band-aid (2026-04-21):** SI516 sink-input volume dropped to 35% (-27 dB). Non-persistent — resets on PipeWire restart.
**Disposition:** NEW WORK — two candidate fixes:
1. **Daimonion-side:** make pw-cat invocation not tag `media.role=Assistant` (drop the role, or set to an explicit "no-policy" role). Then `--target hapax-voice-fx-capture` will stick.
2. **WirePlumber-side:** add a node rule that retargets `output.loopback.sink.role.assistant` to `hapax-voice-fx-capture` instead of default sink.
Option 1 is cleaner (keeps policy layer honest). Option 2 is more resilient (per-role routing becomes explicit infrastructure).
Cross-ref `reference_default_sink_elevation_breaks_roles.md` (related class of role-loopback routing failures).

### J. HOMAGE ward blinking — operator-reported watchability violation

**Source:** operator feedback, 2026-04-21 session — *"way too much BLINKING for the homage wards. it's not even an interesting behavior and it is extremely hard to look at."*
**Scope:** affects the entire HOMAGE ward family on the broadcast surface.
**Candidate sources of blink behavior** (audit-level enumeration; requires per-ward measurement to confirm which are actually firing):

1. `activity_header` — audit-reported "200 ms inverse-flash" on activity change.
2. `stance_indicator` — "pulses at stance-Hz" may be high-frequency with square-ish amplitude envelope.
3. `thinking_indicator` — "breathing dot" at 6 Hz render rate may be producing hard on/off rather than smooth breath.
4. `token_pole` — sparkle-burst effects on token events.
5. HOMAGE choreographer rotation-mode selection — may snap wards on/off when `ward_emphasis` set changes tick-to-tick.
6. ward-stimmung-modulator opacity dynamics — if opacity envelopes are step-functioned (not smooth) between z-plane changes, will read as blink.

**Disposition:** NEW WORK — per-ward blink-behavior audit (measure luminance delta-per-frame on each ward across 10 s of broadcast output), identify the blink sources, replace hard on/off with smooth envelopes. Governance invariant: no visual element should change luminance by > 40% faster than once every 500 ms, except for intentional token-reward flashes with operator consent. Cross-ref `feedback_no_blinking_homage_wards.md`.

**Priority:** operator-surfaced; most-operator-visible issue alongside GEM latency. Sequenced in §4 as Finding 1.

## 4. Key findings (ranked by operator-visibility)

1. **HOMAGE blinking** — operator-reported, watchability-blocking. Hard on/off flashes across multiple wards. Item J.
2. **GEM rendering is ticker-tape** — operator-reported. Current template produces chyron-aesthetic, not graffiti mural. Item A2.
3. **GEM recruitment absent** — director doesn't emit gem.* via grounded path; static fallback only. Item A1.
4. **placement_bias silence** — z-plane dynamism stuck on defaults despite modulator being live. Invisible but caps HOMAGE expressiveness. Item C.
5. **Small ward shader domination** — stance + thinking indicators lose against bright shader presets despite z-plane promotion. Item D.
6. **Micromove + camera-hero expert systems override recruitment** — invisible on surface but masks ~14% of affordance decisions. Items E + G.
7. **Overlay zones + orphan wards** — unused real-estate and state bloat. Lower-priority cleanup. Items B + H.

## 5. Scope boundaries

Out of scope of this audit (as declared at dispatch):
- daimonion voice / TTS internals
- stimmung dimension calculation (consumption only)
- Logos desktop app UI
- IR perception backend (consumption via `person-detection.json` only)
- affordance pipeline internal scoring (only recruitment outcomes observed)

## 6. Shepherd note

Follow-on sequencing, per-item owners, and cc-task filings live in the companion plan:
`docs/superpowers/plans/2026-04-21-livestream-surface-shepherd-plan.md`.
