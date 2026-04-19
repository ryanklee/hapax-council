---
date: 2026-04-19
author: alpha (Claude Opus 4.7, 1M context, cascade worktree)
audience: delta (execution dispatcher) + operator
register: scientific, neutral
status: dispatchable plan — multi-phase, parallel-safe
related:
  - docs/superpowers/specs/2026-04-18-homage-framework-design.md
  - docs/superpowers/specs/2026-04-18-token-pole-homage-migration-design.md
  - docs/superpowers/specs/2026-04-18-vinyl-image-homage-ward-design.md
  - docs/superpowers/specs/2026-04-18-chat-ambient-ward-design.md
  - docs/superpowers/specs/2026-04-18-hardm-dot-matrix-design.md
  - docs/governance/reverie-substrate-invariant.md
  - docs/runbooks/homage-phase-10-rehearsal.md
  - 20-projects/hapax-research/2026-04-19-homage-aesthetic-reckoning.md (vault, source-of-truth diagnosis)
  - agents/studio_compositor/hardm_source.py (exemplar emissive rework)
branch: hotfix/fallback-layout-assignment
operator-directive-load-bearing: |
  "Option A and research every coherent set of granular touch points using
  a dedicated agent to devise a multi-phase plan to make every correction
  needed to bring us back into perfect alignment with our original
  intentions ... we are doing the whole fucking thing tonight and going
  live like planned."
---

# HOMAGE — Completion Plan (Option A + reckoning-gap closure)

## §0. Scope, intent, and what this plan IS

This plan ships, in one branch (`hotfix/fallback-layout-assignment`) under
delta orchestration tonight, the union of:

1. **Option A** from the reckoning (§6.1): every ward's render layer
   reconceived as an emissive / particle / shader-modulated surface using
   the HARDM `hardm_source.py` rework as the exemplar template. Every
   `cairo.rectangle + cairo.show_text` paint-and-hold pattern is retired
   in favour of radial gradients, per-cell shimmer, breathing pulse,
   stance-indexed phase modulation, and emissive halos against a near-
   black ground.
2. **The reckoning's §3 gap closures** that Option A does NOT solve on
   its own: the choreographer FSM un-bypass, director->ward signal-flow
   wiring, the `chat_ambient` layout-binding fix, Pango/Px437 typography
   foundation, Reverie substrate alpha damping, `hapax_homage_*` metrics
   pipeline, the HOMAGE research condition `cond-phase-a-homage-active-001`
   actually being opened, and the Phase 10 rehearsal walked end-to-end
   as the acceptance gate.
3. **Go-live audio/presence polish** the operator flagged adjacent (vinyl
   on stream, YT turn-taking, TTS cadence verification, music
   anti-repetition) — already partially shipped, this plan verifies and
   completes.

This plan is NOT code. Each phase below is a discrete subagent dispatch
that delta will fan out (parallel where the DAG permits, serial where it
does not). The plan's grain is "one phase = one execution subagent =
one commit (or tight commit set) on `hotfix/fallback-layout-assignment` =
one squash-merged PR".

This plan is also NOT silent about scope. Operator override of the
reckoning's Option B recommendation means this plan ships ~40-60 hours
of nominal engineering work in a compressed window via parallel
subagents. Critical-path estimate is in §3.

---

## §1. Success definition — what "done" pixel-by-pixel looks like

The acceptance test is operator visual-read of a 30-second `/dev/video42`
capture. The capture, with audio off, must read as ONE programmed
instrument — a coupled, breathing, choreographed surface in BitchX
register, with director decisions visibly steering ward emphasis on
human timescales. Below, four paragraphs describing the end-state
surface against which every phase below must be measured.

### 1.1 The substrate (Reverie)

The Reverie wgpu pipeline continues to render its 8-pass graph
(noise -> rd -> color -> drift -> breath -> feedback -> content_layer ->
postprocess). Under the active BitchX package its colorgrade hue rotates
toward palette accent (180-deg cyan) AND its saturation is damped by
`colorgrade.saturation` in [0.35, 0.55] so the substrate reads as a
*tinted ground*, not as a saturation explosion. A viewer's first read
of the surface area is no longer "kaleidoscopic screensaver" but
"breathing dim cyan-magenta tinted plane that moves slowly under the
wards". Reverie's `custom[4].x` channel is fed by the choreographer's
transition energy — when a ward netsplit-bursts, Reverie briefly lifts
saturation by ~10%, then damps back; otherwise Reverie holds the quiet.

### 1.2 The wards (16 surfaces, all emissive)

Every ward is a small emissive generative engine. No flat-fill
rectangles. No raw `cairo.show_text`. No JetBrains Mono or DejaVu
fallback typography. Every text path goes through Pango with Px437 IBM
VGA 8x16 explicitly verified at startup. Every ward inherits from a
shared `EmissiveWardBase` (Phase A1) that provides radial-gradient,
shimmer, breathing-pulse, and phase-offset helpers generalised from
`hardm_source.py:621-739`. Concretely:

- **token_pole (300x300, pip-ul):** an emissive Vitruvian Man — the
  PNG is multiplied with `palette.terminal_default x shimmer` at
  alpha=0.55 so the figure is a grey engraving, not a sepia ink. Limbs
  are 16-color mIRC strokes pulsing at stance-indexed Hz (nominal
  1.0 Hz, seeking 1.6 Hz, cautious 0.7 Hz). The token glyph at the
  navel is a centre dot (`accent_yellow`) + soft halo (`accent_magenta`
  alpha=0.45) + outer bloom (`accent_yellow` alpha=0.12) — reads as a
  point of light, not a candy face. The status row at top
  reads `>>> [TOKEN | <pole>:<value>/<threshold>]` in Px437. Token
  ticks fire a 200 ms inverse-flash on the status row (mIRC
  `topic-change` vocab); explosions fire a `mode-change` flash on
  the whole ward + a 2 s `[+k pole crested]` kick-reason row drawn
  from `signature_artefacts`.
- **HARDM (256x256, hardm-dot-matrix-ur):** already shipped at the
  source-code level (`hardm_source.py:621-739`); this plan ensures
  the deploy gap closes (Phase E1) and adds the missing wires:
  emphasis brightness when CPAL is mid-utterance (already in source
  via `_read_emphasis_state`), FX-chain bias toward "neon" preset
  family during HARDM emphasis windows (Phase B6), and rotation-mode-
  driven brightness ceiling (when `homage_rotation_mode=burst` HARDM
  cells momentarily inflate halo radius by 1.5x).
- **Album overlay (300x450, pip-ll):** the five-PiP-FX dictionary
  (`_pip_fx_vintage`/`cold`/`neon`/`film`/`phosphor`) is DELETED. A
  single `_pip_fx_package(cr, w, h, pkg)` quantises the cover to
  the active package's palette via `Image.quantize(palette=mIRC16,
  dither=Bayer4)`, draws horizontal CP437 scanlines at raster
  cadence in `package.muted` (every 3 px), and applies an ordered-
  dither shadow in `package.accent_magenta`. Splattribution above
  the cover renders in Px437 14 via `text_render.render_text` with
  the BitchX header. On track-change the cover swaps via a
  `ticker-scroll-in` (slide right-to-left over 400 ms).
- **Captions strip (1840x110, captions_strip):** Pango-rendered
  Px437 IBM VGA 8x16 at 22 px (scientific) / 36 px (public) on a
  semi-transparent dark band. STT-line crossfades over 200 ms
  rather than instant-swapping.
- **HARDM, activity_header, stance_indicator, grounding_provenance_ticker:**
  all four converted to emissive base — text glyphs as point-of-light
  centre dots + halo, breathing alpha at 0.32 Hz with per-glyph phase
  offset. The line-start chevron marker becomes a small triangle of
  three emissive dots, not a typeset character.
- **Hothouse family (impingement_cascade, recruitment_candidate_panel,
  thinking_indicator, pressure_gauge, activity_variety_log,
  whos_here):** rewritten as emissive panels. Pressure gauge is no
  longer a flat red bar — it is a row of 32 CP437 half-block cells
  where each cell is rendered as a centre dot + halo, fill level
  driven by pressure value, hue interpolated from
  `accent_green` -> `accent_yellow` -> `accent_red`. Impingement
  cascade entries enter via `join-message` (slide in from left with
  ghost trail) and decay alpha over their lifetime.
- **Chat ambient (560x40, chat-legend-right):** REBOUND in
  `default.json` from the legacy `ChatKeywordLegendCairoSource` to
  `ChatAmbientWard`. The CP437 rate gauge cells render as emissive
  point-of-light blocks; `[Users(#hapax:1/N)]` and `[Mode +v +H]`
  cells in Px437.

### 1.3 The director->ward signal flow (visible, every tick)

The director's `compositional_impingements.intent_family` set to
`ward.highlight`, `ward.emphasis`, or `overlay.emphasis` results within
<=100 ms in: (a) the named ward's `glow_radius_px` rising from 0.0 to
14.0, (b) `border_pulse_hz` set to 2.0 (so the border visibly pulses
at 2 Hz), (c) `border_color_rgba` set to the impingement's domain
accent role, (d) `expires_at = now + impingement.salience * 5.0`. The
14 wards that currently never get emphasis (everything except album +
HARDM) start receiving emphasis values driven by every director tick.

The structural director writes `homage_rotation_mode` taking values
`steady|deliberate|rapid|burst` (replacing the unrecognised
`sequential` placeholder) and the choreographer rotates wards every N
seconds per strategy. `burst` triggers a netsplit-burst that briefly
clears 8 wards and re-populates them via `join-message` transitions
within 600 ms.

The choreographer FSM hotfix at `transitional_source.py:90-110` is
REMOVED. The default `initial_state` reverts to `TransitionState.ABSENT`.
The choreographer dispatches a `ticker-scroll-in` to every registered
`HomageTransitionalSource` at startup so wards advance ABSENT -> ENTERING
-> HOLD properly. After the startup dispatch, the choreographer continues
to drive ENTERING/EXITING transitions on its own cadence — a viewer's
first 10 seconds shows at least 3 visible ward transitions.

### 1.4 The signature, the artefacts, the observability

Every 30/90/180 s (per rotation_mode) a signature artefact rotates onto
the surface (quit-quip, MOTD-block, kick-reason, join-banner). Each
carries `by Hapax/bitchx@cond-phase-a-homage-active-001` inline.
Research condition `cond-phase-a-homage-active-001` is OPEN (Phase C2);
director-intent records carry it; the Bayesian validation pipeline can
slice pre/post-HOMAGE.

`hapax_homage_*` Prometheus counters/gauges emit on every FSM
transition, every emphasis application, every render-cadence beat,
every rotation choice. A Grafana dashboard at
`localhost:3001/d/homage-transitions/` shows `hapax_homage_transition_total`
strictly increasing during a normal session.

Phase 10 rehearsal runbook is walked end-to-end after deploy; every
checkbox ticked by direct observation against `/dev/video42`. The
checklist becomes the go-live acceptance gate (§6).

---

## §2. Phase list

Phases are grouped into five families (A through E). Family A is the
Option A render-layer rewrite. Family B is the director->ward signal
flow. Family C is observability + governance. Family D is audio /
presence polish (already partially shipped, completion pass). Family E
is the deploy + acceptance walkthrough.

Each phase has: scope (file paths bounded), blocking dependencies,
parallel-safe siblings, success criteria (pixel-level where possible),
test strategy, LOC range + size (S=<=200, M=200-500, L=500-1500),
commit-message template.

**All phases:** commit directly to `hotfix/fallback-layout-assignment`.
Do NOT switch branches. Do NOT use `isolation: "worktree"` (operator-
mandated subagent git safety per workspace CLAUDE.md). Each commit is
self-contained and ends with the standard
`Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
trailer.

### Family A — Ward render-layer rewrite (Option A core)

#### Phase A1: `EmissiveWardBase` shared base class

**Scope:**
- New file: `agents/studio_compositor/homage/emissive_base.py`
- Tests: `tests/studio_compositor/test_emissive_base.py`

**Description:** Generalise the `hardm_source.py:621-739` rendering
pattern (radial-gradient centre-dot + halo + outer-glow + per-cell
shimmer + scanline overlay) into a reusable base mixin or helper module
that ALL ward rewrites in A2/A3/A4 can compose with. Provide:

- `paint_emissive_point(cr, cx, cy, role_rgba, *, t, phase, baseline_alpha,
  centre_radius_px=2.5, halo_radius_px=6.5, outer_glow_radius_px=9.0)`
- `paint_emissive_glyph(cr, x, y, glyph, font_size, role_rgba, *, t,
  phase)` — renders a CP437 glyph as a centre-dot grid sample + halo;
  used for the chevron line-start marker and bracket characters
- `paint_emissive_stroke(cr, x0, y0, x1, y1, role_rgba, *, t, phase,
  width_px=2.0)` — emissive line stroke for token-pole limbs and
  pressure-gauge bars
- `paint_breathing_alpha(t, *, hz, baseline=0.85, amplitude=0.15,
  phase=0.0) -> float` — shared alpha modulator
- `paint_scanlines(cr, w, h, *, role_rgba, every_n_rows=4, alpha=0.10)` —
  CRT raster hint, generalised from HARDM
- Constants: `STANCE_HZ` mapping (nominal=1.0, seeking=1.6,
  cautious=0.7, degraded=0.5, critical=2.4) used by all wards
  for stance-indexed pulse rates
- `paint_emissive_bg(cr, w, h, *, ground_rgba=GRUVBOX_BG0)` — Gruvbox
  bg0 ground (matches HARDM's `_GRUVBOX_BG0`)

**Blocking dependencies:** None. This is a leaf module.

**Parallel-safe siblings:** A5 (typography foundation), A6, B1, B2,
B5, B6, C1, C2, C3, C4, D1, D2, D3 can all run alongside.

**Success criteria:**
- `uv run pytest tests/studio_compositor/test_emissive_base.py -q`
  passes (>=10 unit tests covering each helper)
- `uv run ruff check agents/studio_compositor/homage/emissive_base.py`
  clean
- Module imports successfully; `from agents.studio_compositor.homage.emissive_base
  import paint_emissive_point` succeeds at REPL
- A demo Cairo ImageSurface render of `paint_emissive_point` saved as
  `tests/studio_compositor/golden/emissive_point.png` matches a
  golden ref to within +/-4 per channel

**Test strategy:** Unit tests for each helper (alpha bounds, shimmer
phase symmetry, gradient stop ordering). One golden-image regression
for `paint_emissive_point` and `paint_emissive_stroke` rendered at
deterministic `t=0.0`, `t=pi/SHIMMER_ANGULAR_FREQ` (mid-shimmer).

**Estimated LOC:** 250-400 module + 200-300 tests. Size: M.

**Commit message template:**

```
feat(homage): EmissiveWardBase — shared HARDM-style emissive primitives

Generalise the pointillism / shimmer / halo rendering pattern from
`hardm_source.py:621-739` into a reusable helper module. Phase A1 of
the homage-completion plan; consumed by Phase A2/A3/A4 rewrites.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phase A2: Hothouse family emissive rewrite

**Scope:**
- `agents/studio_compositor/hothouse_sources.py` — full rewrite of
  six `render_content` methods:
  - `ImpingementCascadeCairoSource` (lines 164-218)
  - `RecruitmentCandidatePanelCairoSource` (lines 220-308)
  - `ThinkingIndicatorCairoSource` (lines 310-358)
  - `PressureGaugeCairoSource` (lines 360-435)
  - `ActivityVarietyLogCairoSource` (lines 437-496)
  - `WhosHereCairoSource` (lines 498-567)
- Tests: `tests/studio_compositor/test_hothouse_sources_emissive.py`
  (or expand existing test file in same dir)
- Goldens: 6 new images under `tests/studio_compositor/golden/hothouse/`

**Description:** Each ward's `render_content` is reimplemented to use
`EmissiveWardBase` helpers from A1. Concrete pixel targets per ward:

- **impingement_cascade (480x360):** drop the colon-separated
  `signal_name : value` rows. Render each top-N signal as one row
  consisting of `* <id> [salience|<bar>|family|<accent>]` where:
  the `*` is a 4-px emissive centre dot in `palette.muted`; `<id>`
  is Px437 in `palette.bright`; the `<bar>` is 8 emissive cells
  filled by salience using `paint_emissive_point` with hue
  interpolated from family role; `<accent>` is the family role
  itself. New rows enter via `join-message` (slide in from left
  over 200 ms with ghost trail of decreasing alpha). Old rows
  decay alpha at 1/lifetime over 5 s before being culled.
- **recruitment_candidate_panel (800x60):** show the last 3 recruited
  capabilities as three emissive cells in a row, each with: capability
  name in Px437 + emissive halo in family accent; salience as a
  width-modulated bar of emissive points; entry transition is
  `ticker-scroll-in`.
- **thinking_indicator (170x44):** the pulsing dot becomes a
  point-of-light at the left edge with breathing alpha at
  stance-indexed Hz; when LLM in flight, alpha modulation
  amplifies and a `[thinking...]` Px437 label fades in beside it.
- **pressure_gauge (300x52):** the flat red bar is REPLACED with a
  row of 32 CP437 half-block cells. Each cell is a centre dot +
  halo via `paint_emissive_point`, fill level driven by pressure
  value (0..1), hue interpolated cell-by-cell from `accent_green`
  -> `accent_yellow` -> `accent_red`. The label
  `>>> [PRESSURE | <count>/<saturation%>]` is Px437 above the cells.
- **activity_variety_log (400x140):** the recent-moves ribbon
  becomes a horizontal stack of 6 cells (oldest leftmost),
  each cell an emissive name+intensity rendered as point-of-light
  glyphs. New entries enter via `ticker-scroll-in` from the right;
  oldest exits via `ticker-scroll-out` to the left.
- **whos_here (230x46):** `[hapax:1/N]` rendered as Px437 with the
  `1` and `N` as point-of-light glyphs (stance-coloured for `1`,
  audience-colour for `N`).

**Blocking dependencies:** A1 (EmissiveWardBase), A5 (Pango/Px437
foundation, so the typography lands correctly).

**Parallel-safe siblings:** A3, A4 (ward-render rewrites in
non-overlapping files). B1-B6, C1-C4, D1-D3 also parallel-safe.

**Success criteria:**
- All 6 wards visibly render as emissive surfaces (no flat-fill
  rectangles, no `cairo.show_text` raw calls — text goes through
  Pango via A5)
- Per-ward golden-image regressions pass with +/-4 channel tolerance
  at `t=0.0` and `t=pi`
- `uv run pytest tests/studio_compositor/test_hothouse_sources_emissive.py -q`
  passes (>=18 tests, 3 per ward)
- `uv run ruff check agents/studio_compositor/hothouse_sources.py` clean
- After deploy + restart of `studio-compositor.service`, `mpv
  v4l2:///dev/video42` shows pressure-gauge as a row of 32 emissive
  cells (NOT a flat red bar), impingement-cascade rows entering with
  visible slide-in motion

**Test strategy:** 18+ unit tests + 6 golden images. Visual smoketest
(operator) post-deploy.

**Estimated LOC:** 900-1300 (rewriting six render methods). Size: L.

**Commit message template:**

```
feat(homage): hothouse family emissive rewrite (Option A)

Reconceives the six hothouse wards (impingement_cascade,
recruitment_candidate_panel, thinking_indicator, pressure_gauge,
activity_variety_log, whos_here) as emissive surfaces using the
EmissiveWardBase primitives from Phase A1. Pressure gauge becomes
a row of 32 CP437 half-block emissive cells; impingement cascade
rows enter via join-message slide-in; etc.

Phase A2 of homage-completion-plan. Per operator-directed Option A
rewrite of the cairo-rectangle-as-text-box pattern.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phase A3: Legibility family emissive rewrite

**Scope:**
- `agents/studio_compositor/legibility_sources.py` — full rewrite of
  four `render_content` methods (existing classes; the chat-legend
  legacy class becomes a back-compat thin shim that delegates to
  ChatAmbientWard once B5 lands):
  - `ActivityHeaderCairoSource` (lines 188-263)
  - `StanceIndicatorCairoSource` (lines 269-313)
  - `GroundingProvenanceTickerCairoSource` (lines 389-447)
  - `ChatKeywordLegendCairoSource` (lines 329-383) — keep instantiable
    as legacy alias per Phase 10 rehearsal §2.3 expectation, but
    convert its render to emissive-style for visual consistency until
    B5 swaps the layout binding to `ChatAmbientWard`
- Tests: `tests/studio_compositor/test_legibility_sources_emissive.py`
- Goldens: 4 new images under `tests/studio_compositor/golden/legibility/`

**Description:** Per ward concretes:

- **activity_header (800x56):** `>>> [ACTIVITY | gloss]` rendered as
  emissive Px437 — every glyph in the marker chevron sequence and
  brackets is a `paint_emissive_glyph` call. The gloss text uses
  `text_render.render_text` (Pango) with Px437 14. On activity
  change, the entire header inverse-flashes for 200 ms (mode-change
  vocab). Optionally append `:: [ROTATION:<mode>]` when
  `homage_rotation_mode` is non-default; rotation token coloured
  by mode (steady=muted, deliberate=accent_cyan, rapid=accent_yellow,
  burst=accent_red).
- **stance_indicator (100x40):** `[+H STANCE]` rendered emissively —
  brackets and `+H` as point-of-light glyphs in `palette.muted`,
  stance label as point-of-light glyphs in stance role colour.
  Stance-indexed pulse on the label glyphs (1.0 Hz nominal, 1.6 Hz
  seeking, etc.). On stance change, a 200 ms inverse-flash on the
  whole ward.
- **grounding_provenance_ticker (480x40):** `* <signal>` rows
  rendered emissively, with the `*` as a 3-px centre dot in
  `palette.muted` and signal names in `palette.bright`. Each entry
  enters via `join-message` slide-in. When `prov` is empty, render
  `*  (ungrounded)` in muted with breathing alpha at 0.3 Hz so even
  the empty state shows life.
- **chat_keyword_legend (560x40):** keep registered, render the
  static keywords emissively for the Phase 10 backwards-compat
  surface (B5 swaps the layout binding so `ChatAmbientWard` becomes
  the production renderer; this class stays as the legacy alias).

**Blocking dependencies:** A1, A5.

**Parallel-safe siblings:** A2, A4. B1-B6, C1-C4, D1-D3.

**Success criteria:**
- Four wards visibly emissive, no flat-fill backgrounds (the
  `paint_bitchx_bg` + `paint_emissive_bg` composite reads as
  tinted-on-near-black with side-bar accent)
- Stance indicator visibly pulses at stance-indexed Hz post-deploy
- Activity header visibly inverse-flashes on activity change
- Goldens pass; ruff clean; pytest green

**Estimated LOC:** 600-900. Size: L.

**Commit message template:**

```
feat(homage): legibility family emissive rewrite (Option A)

ActivityHeader, StanceIndicator, GroundingProvenanceTicker, and
ChatKeywordLegend render their content via EmissiveWardBase point-of-
light glyphs + halos rather than cairo.show_text. Stance indicator
pulses at stance-indexed Hz; activity header inverse-flashes on
activity change.

Phase A3 of homage-completion-plan.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phase A4: Content-ward emissive rewrite

**Scope:**
- `agents/studio_compositor/token_pole.py` — rewrite `render_content`
  in `TokenPoleCairoSource` (lines 289-end). Drop the candy face
  (eyes + smile + cheeks); replace with emissive token-as-point-of-
  light. Convert spiral guide to emissive stroke. Add Px437 status row.
- `agents/studio_compositor/album_overlay.py` — DELETE
  `_pip_fx_vintage`, `_pip_fx_cold`, `_pip_fx_neon`, `_pip_fx_film`,
  `_pip_fx_phosphor`, and the `PIP_EFFECTS` dict (lines 34-170). ADD
  `_pip_fx_package(cr, w, h, package)` per spec
  `2026-04-18-vinyl-image-homage-ward-design.md` §5.2. Switch
  splattribution from `JetBrains Mono Bold 10` to
  `package.typography.primary_font_family` via Pango.
- `agents/studio_compositor/captions_source.py` — switch
  `STYLE_SCIENTIFIC.font_description` from `"JetBrains Mono 18"` to
  `"Px437 IBM VGA 8x16 22"` and `STYLE_PUBLIC.font_description` from
  `"Noto Sans Display Bold 32"` to `"Px437 IBM VGA 8x16 36"`. Add
  startup font-availability check that emits a loud WARN if Px437
  doesn't resolve via Pango.
- `agents/studio_compositor/stream_overlay.py` — convert FX/viewers/
  chat-status three-line panel to emissive Px437; each line
  `>>> [<field>|<value>]`.
- `agents/studio_compositor/research_marker_overlay.py` — convert
  marker render to emissive (point-of-light per character of the
  marker label).
- `agents/studio_compositor/vinyl_platter.py` — convert (if a Cairo
  source) to emissive style or confirm it's gst-only and skip.
- Tests: `tests/studio_compositor/test_token_pole_emissive.py`,
  `test_album_overlay_emissive.py`, `test_captions_pango.py`,
  `test_stream_overlay_emissive.py`, `test_research_marker_emissive.py`
- Goldens: 6 new images under `tests/studio_compositor/golden/content/`

**Description:** Concrete per-ward:

- **token_pole (300x300):** Vitruvian PNG painted at alpha=0.55
  multiplied with `palette.terminal_default x shimmer(t, hz=stance_hz,
  phase=0)`. Spiral guide reimplemented as 32 emissive points along
  the spiral path with phase offsets. Token glyph at navel: centre
  dot (`accent_yellow`), halo (`accent_magenta` alpha=0.45), outer
  bloom (`accent_yellow` alpha=0.12). Particles on explosions
  reimplemented as emissive points with role-resolved colour. Status
  row at top in Px437 via `text_render.render_text`. Smiley face
  DELETED. Cascade-marker text on emoji spew also via Pango Px437
  (drop the hardcoded `JetBrains Mono Bold 12` at line 622).
- **album_overlay (300x450):** new `_pip_fx_package(cr, w, h, pkg)`
  that:
  1. Loads the cover via existing `image_loader.get_image_loader().load`
  2. Quantises to mIRC-16 palette via PIL `Image.quantize(palette=
     mIRC16_palette_image, dither=Image.Dither.ORDERED, dither_levels=4)`
     where `mIRC16_palette_image` is built from `pkg`'s 16 colour roles
  3. Draws horizontal scanlines every 3 px in `pkg.resolve_colour("muted")`
     at alpha=0.18
  4. Applies an ordered-dither shadow mask in
     `pkg.resolve_colour("accent_magenta")` at alpha=0.22 along bottom 25%
  5. Draws a 2 px sharp border in `pkg.resolve_colour(domain_accent)`
  Splattribution above cover via `text_render.render_text` with
  `font_description=f"{pkg.typography.primary_font_family} 14"`.
  ALBUM header via `paint_bitchx_header` (already present at
  line 342, just confirm it uses Pango path).
- **captions:** font swap + startup check. The startup check lives in
  `agents/studio_compositor/captions_source.py` module-level (or in
  `compositor.py` startup) — calls `text_render._has_font(
  "Px437 IBM VGA 8x16")` (new helper in `text_render.py` or inline
  Pango font resolution check); WARN-loud if missing.
- **stream_overlay (400x200):** three rows `>>> [FX|<chain>]`,
  `>>> [VIEWERS|<count>]`, `>>> [CHAT|<status>]` in emissive Px437.
- **research_marker_overlay:** marker label rendered as point-of-light
  glyphs over a `>>> [RESEARCH MARKER] <HH:MM:SS>` Px437 line.

**Blocking dependencies:** A1, A5.

**Parallel-safe siblings:** A2, A3. B1-B6, C1-C4, D1-D3.

**Success criteria:**
- `agents/studio_compositor/album_overlay.py` no longer contains
  `_pip_fx_vintage`, `_pip_fx_cold`, `_pip_fx_neon`, `_pip_fx_film`,
  `_pip_fx_phosphor`, or `PIP_EFFECTS` (grep returns empty)
- Captions render in Px437 post-deploy (visible via `mpv
  v4l2:///dev/video42`); startup WARN absent
- Token pole: smiley face NOT visible; token glyph reads as a
  point-of-light; status row in Px437
- Goldens pass; ruff clean; pytest green

**Estimated LOC:** 1100-1500 (token_pole rewrite is the largest).
Size: L.

**Commit message template:**

```
feat(homage): content-ward emissive rewrite + PiP-FX dict deletion

Token pole drops candy face for point-of-light token glyph; album
overlay's five-PiP-FX dict (_pip_fx_vintage/cold/neon/film/phosphor)
DELETED, replaced with single _pip_fx_package(pkg) that mIRC-16-
quantises the cover; captions / stream_overlay / research_marker
re-rendered emissively in Px437 via Pango.

Phase A4 of homage-completion-plan. Closes reckoning §3.2 (album
PiP) and §3.3 (Px437 typography) for the four loudest wards.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phase A5: Pango / Px437 typography foundation

**Scope:**
- `agents/studio_compositor/text_render.py` — add a startup font-
  availability helper:
  - `def has_font(family: str) -> bool` (uses `Pango.FontMap` /
    `pangocairo.FontMap.get_default()` to enumerate available
    families and return True/False)
  - `def warn_if_missing_homage_fonts() -> None` (called once at
    compositor startup; logs a loud WARN if `"Px437 IBM VGA 8x16"`
    is not resolvable)
- `agents/studio_compositor/homage/rendering.py` — replace
  `select_bitchx_font` (lines 36-51) which uses Cairo's toy
  `select_font_face` API with a Pango-backed equivalent:
  - `def select_bitchx_font_pango(cr, size, *, bold=False) -> str`
    returns a Pango-compatible `font_description` string
    (`f"{pkg.typography.primary_font_family} {' Bold' if bold else ''}
    {size}"`) for callers to pass to `text_render`. Keep the old
    `select_bitchx_font` as a deprecated shim (no callers should use
    it after A2/A3/A4 land).
- `agents/studio_compositor/legibility_sources.py` — replace the
  module-private `_select_bitchx_font` (lines 113-128) with calls
  through `text_render.render_text` (i.e., wards stop calling
  `cr.show_text` directly; they construct a `TextStyle` and call
  `render_text(cr, style, x, y)`).
- `agents/studio_compositor/chat_ambient_ward.py` — same swap (the
  `_select_font` helper at lines 92-101).
- `agents/studio_compositor/compositor.py` — call
  `text_render.warn_if_missing_homage_fonts()` once at startup.
- Tests: `tests/studio_compositor/test_text_render_pango.py` (extend
  existing if present) — add tests for `has_font` (mock Pango
  FontMap), `warn_if_missing_homage_fonts` (assert WARN log emitted
  when font absent).

**Description:** This phase converts every text path in the compositor
from Cairo's toy API (which doesn't consult fontconfig the same way
Pango does and silently falls back to DejaVu Sans for unknown family
names) to Pango via the existing `text_render.render_text` /
`render_text_to_surface` plumbing. The Px437 TTF
`/usr/share/fonts/TTF/Px437_IBM_VGA_8x16.ttf` exists fontconfig-side;
Pango resolves it; Cairo toy doesn't.

**Blocking dependencies:** None for the helper additions; A1
implicitly because A2/A3/A4 must depend on the Pango helpers being in
place.

**Parallel-safe siblings:** A1 (independent). B1-B6, C1-C4, D1-D3.

**Note:** A2/A3/A4 depend on A5 — delta should land A5 before
dispatching A2/A3/A4 (or dispatch A5 alongside A1 in a tight first
batch, then A2/A3/A4 as the second batch).

**Success criteria:**
- `uv run python -c "from agents.studio_compositor.text_render import
  has_font; assert has_font('Px437 IBM VGA 8x16')"` succeeds
- Compositor startup log contains no "Px437 not found" WARN
- All text on `/dev/video42` post-deploy renders in Px437 (visual
  spot-check via `mpv v4l2:///dev/video42` — letters must show CP437
  raster character of Px437, not the smooth anti-aliased curves of
  DejaVu)

**Test strategy:** Mock-based unit tests (Pango FontMap mocked) for
the helpers; visual smoketest for live verification.

**Estimated LOC:** 200-350 module changes + 150-200 tests. Size: M.

**Commit message template:**

```
feat(homage): Pango/Px437 typography foundation

Adds text_render.has_font + warn_if_missing_homage_fonts; replaces
Cairo toy select_font_face calls with Pango via text_render across
legibility_sources, chat_ambient_ward, and homage/rendering. Px437
IBM VGA 8x16 now resolves correctly through fontconfig; the surface
stops falling back to DejaVu Sans Mono.

Phase A5 of homage-completion-plan. Closes reckoning §3.3.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phase A6: Reverie substrate alpha damping

**Scope:**
- `agents/studio_compositor/homage/choreographer.py` — the
  `broadcast_package_to_substrates` method writes the palette
  hint; verify it sets `colorgrade.saturation` to a damped value
  (~0.40) when the active package is BitchX, not the default 1.0
- `agents/effect_graph/wgsl_compiler.py` (or wherever `colorgrade`
  pass param defaults live) — confirm the per-pass `saturation`
  field accepts a per-tick override
- `agents/visual_layer_aggregator/*` (the writer of `uniforms.json`) —
  confirm package palette broadcasts flow through to `uniforms.json`
  `colorgrade.saturation` and `colorgrade.brightness`
- `presets/reverie_vocabulary.json` — confirm `colorgrade` pass
  exists and exposes `saturation`/`brightness`/`hue_rotate` params

**Description:** Per the reckoning §3.7 and the substrate-invariant
governance doc, when BitchX is the active package the Reverie
`colorgrade` pass should damp saturation toward 0.4 (range 0.35-0.55)
and rotate hue toward the package accent (180-deg cyan). Currently the
substrate is amplifying saturation rather than damping it. Trace the
exact write path:

1. `Choreographer.broadcast_package_to_substrates(pkg)` — writes
   palette hue hint to `/dev/shm/hapax-compositor/homage-substrate-package.json`
2. The substrate-package consumer (lives in
   `agents/visual_layer_aggregator/` or `agents/studio_compositor/homage/substrate_source.py`)
   reads that file and SHOULD write
   `{"colorgrade.saturation": 0.40, "colorgrade.hue_rotate": 180.0,
   "colorgrade.brightness": 0.85}` into the `uniforms.json` per-node
   override file
3. The Rust `dynamic_pipeline.rs` per-frame override bridge picks up
   those values and applies them

This phase: AUDIT the path end-to-end, fix whichever step is dropping
the saturation damping, ship a unit test that asserts the
broadcast-to-uniforms write produces `colorgrade.saturation <= 0.55`
when BitchX is active.

**Blocking dependencies:** None.

**Parallel-safe siblings:** All other phases.

**Success criteria:**
- Live `jq '."colorgrade.saturation"' /dev/shm/hapax-imagination/uniforms.json`
  returns <= 0.55 when BitchX is active
- Visual: post-deploy, Reverie reads as a tinted-cyan ground (NOT a
  high-saturation kaleidoscope); the wards become the visually-
  loudest elements, Reverie becomes the substrate
- Unit test pinning the broadcast -> uniforms write

**Test strategy:** One unit test in
`tests/studio_compositor/test_homage_substrate_damping.py` (mock
SHM I/O, assert the writer produces damped saturation).

**Estimated LOC:** 100-250. Size: S.

**Commit message template:**

```
fix(homage): damp Reverie saturation under BitchX (substrate invariant)

When the active homage package is BitchX, the colorgrade pass receives
saturation=0.40 + hue_rotate=180 so Reverie reads as a tinted ground
rather than a kaleidoscopic competitor for visual attention. Audit
of the broadcast-to-uniforms path identified the dropped write at
<location>; fix flows palette hint into colorgrade.saturation per
the substrate-invariant governance doc.

Phase A6 of homage-completion-plan. Closes reckoning §3.7.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

### Family B — Director->ward signal-flow wiring

#### Phase B0: Narrative structural_intent write-path verification (BLOCKER)

**Scope:**
- AUDIT the path `StructuralDirectorLLM → NarrativeStructuralIntent →
  director-intent.jsonl serializer → /dev/shm/hapax-compositor/narrative-
  structural-intent.json → compositional_consumer.dispatch_structural_intent`.
  Per `docs/research/2026-04-19-blinding-defaults-audit.md` §ceremonial-
  defaults-2 and `docs/research/2026-04-19-expert-system-blinding-audit.md`:
  **994/994 of the last director-intent.jsonl records carry no
  `structural_intent` key at all**, and `narrative-structural-intent.json`
  writes are hours-stale. B1 and B2 below write into a consumer that
  never fires unless this path is restored.
- `shared/director_intent.py:381-390` — verify the serializer (likely
  `model_dump` / `DirectorIntent.to_jsonl` path) does NOT drop empty
  containers. If `structural_intent` is emitted as `None` or `{}` and
  the serializer uses `exclude_defaults=True` or `exclude_none=True`,
  the field silently disappears.
- `agents/studio_compositor/narrative_director.py` (or wherever the
  structural LLM call lives) — confirm the LLM is actually asked to
  emit `structural_intent` on every tick AND the emitted value is
  non-empty (populates `homage_rotation_mode`, `ward_emphasis`,
  `ward_dispatch`, `ward_retire`, or `placement_bias`).
- `/dev/shm/hapax-compositor/narrative-structural-intent.json` —
  confirm the file is being written every N seconds (matches the
  narrative-director cadence). Fix the staleness bug if not.
- Tests: `tests/studio_compositor/test_structural_intent_emission.py`
  — pin that a director tick produces a JSONL record with a
  non-empty `structural_intent` object AND that
  `narrative-structural-intent.json` is updated.

**Description:** This is a reconnaissance + repair phase. Without
this, every B-family phase ships into a dead consumer. Execution
sequence for the subagent: (1) grep + trace the write path, (2) run
one director tick in isolation, (3) observe what's emitted at each
stage, (4) identify the drop, (5) fix it, (6) pin with tests.

Potential drop sites (most to least likely):
- Pydantic `model_dump(exclude_none=True)` or `exclude_defaults=True`
  dropping empty container fields
- Serializer writing `structural_intent` but consumer reading the
  wrong key path
- Narrative director LLM not being invoked on the structural prompt
- LLM invoked but returning empty JSON in the `structural_intent` field
- Field populated in memory but not persisted to JSONL (race condition)

**Blocking dependencies:** None (diagnostic).

**Parallel-safe siblings:** All A-family, B1, B2, B4 (which read the
intent), C-family, D-family. B3 does not depend on this path.

**Blocks:** B1, B2, B4 cannot be declared functionally complete until
B0 lands. If B0 finds the path is sound (i.e., structural_intent IS
being written but was mis-observed in the audit), document and close
B0 as a no-op.

**Success criteria:**
- `tail -5 ~/hapax-state/stream-experiment/director-intent.jsonl |
  jq '.structural_intent' ` returns non-null objects with at least
  one populated field across the last 5 records
- `stat --format=%Y /dev/shm/hapax-compositor/narrative-structural-intent.json`
  returns a timestamp within the last 60 seconds during an active
  director session
- Unit tests pin the emission behaviour (end-to-end mock: LLM returns
  a populated `structural_intent`, serializer preserves it, JSONL
  contains the key)

**Estimated LOC:** 150-400 (audit + likely 1-3 file fixes). Size: M.

**Commit message template:**

```
fix(homage): restore narrative structural_intent write path

Per docs/research/2026-04-19-blinding-defaults-audit.md + expert-
system-blinding-audit.md, 994/994 of the last director-intent.jsonl
records carried no structural_intent key, and narrative-structural-
intent.json writes were hours-stale. B1/B2 ward-properties writes
depend on this consumer firing.

Root cause: <pydantic exclude_none drop | LLM call gap | serializer
race — fill in from audit>. Fix: <describe>.

Tests pin end-to-end emission (LLM → JSONL → /dev/shm).

Phase B0 of homage-completion-plan. Closes blinding-defaults §2 and
expert-system-blinding §recruitment-gap-1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phase B1: Ward-property manager driven aggressively by structural intent

**Scope:**
- `agents/studio_compositor/compositional_consumer.py` — the
  `dispatch_structural_intent` function (lines 1100-1176) and the
  `_apply_emphasis` / `_apply_placement` helpers (lines ~1020-1067).
  Currently `_apply_emphasis(ward_id, salience=1.0)` produces only
  mild modulation; this phase aggressively maps:
  - `ward_emphasis: [<ward_id>]` -> `set_ward_properties(ward_id,
    WardProperties(glow_radius_px=14.0, border_pulse_hz=2.0,
    border_color_rgba=domain_accent_rgba(ward_id), alpha=1.0,
    scale_bump_pct=0.06), ttl_s=salience * 5.0)`
  - `placement_bias: {ward_id: hint}` -> modulate `position_offset_x/y`
    per hint (e.g., `"foreground"` -> no offset; `"left-edge"` ->
    position_offset_x=-50; `"recede"` -> alpha=0.55)
- New helper: `domain_accent_rgba(ward_id) -> tuple[float,...]` —
  resolves through the active package's role for the ward's domain
  (cribbing from `homage/rendering.py:_DOMAIN_ACCENT_ROLE`)
- Tests: extend `tests/studio_compositor/test_compositional_consumer.py`
  with assertions that emphasis writes produce `glow_radius_px >= 12.0`
  for nominated wards

**Blocking dependencies:** None (independent of A-family).

**Parallel-safe siblings:** All other phases (writes one file, tests
one file).

**Success criteria:**
- Live: `jq '.wards | map_values(.glow_radius_px) | to_entries[] |
  select(.value >= 12.0)' /dev/shm/hapax-compositor/ward-properties.json`
  returns >= 4 entries during a normal session (rather than current
  2: HARDM + album)
- Border pulse visible on emphasized wards in v4l2 output
- Unit tests pinning the aggressive values pass

**Test strategy:** Unit tests with monkeypatched `set_ward_properties`
+ assertions on the dataclass values.

**Estimated LOC:** 150-300. Size: S.

**Commit message template:**

```
feat(homage): ward-property emphasis values driven aggressively

dispatch_structural_intent now maps ward_emphasis nominations to
glow_radius_px=14, border_pulse_hz=2.0, scale_bump_pct=0.06 (per the
operator's "deeply felt and in-your-face impact" directive) rather
than the prior near-no-op modulations. Closes reckoning §3.4.

Phase B1 of homage-completion-plan.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phase B2: compositional_impingement.intent_family -> ward-properties dispatch

**Scope:**
- `agents/studio_compositor/compositional_consumer.py` — the
  `dispatch` function and the `_ward_dispatch_common` helper. The
  narrative director's `compositional_impingements` list contains
  records with `intent_family` like `ward.highlight`, `overlay.emphasis`,
  `preset.bias`, `camera.hero`. This phase ensures that when an
  impingement carries `intent_family=ward.highlight.<ward_id>` OR
  `overlay.emphasis.<ward_id>`, the ward-properties writer fires
  with aggressive values.
- Specifically: trace the path
  `narrative-director writes director-intent.jsonl with
  compositional_impingements[*].intent_family` -> `compositional_consumer.dispatch`
  reads -> `dispatch_ward_highlight` / `dispatch_overlay_emphasis`
  invoked -> `_apply_emphasis` writes ward-properties.
- The current path exists (per grep `intent_family|ward.highlight|
  overlay.emphasis`), but the values are mild. Confirm the dispatch
  reads `salience` and uses it to set TTL aggressively (TTL >= 5 *
  salience seconds; minimum TTL 1.5 s so brief emphases are visible).
- Tests: extend `tests/studio_compositor/test_compositional_consumer.py`

**Blocking dependencies:** B1 (shares `_apply_emphasis` updates).

**Parallel-safe siblings:** A-family, B3-B6, C, D.

**Success criteria:**
- During normal director ticks, `ward-properties.json` shows
  emphasis values rotating across multiple wards over a 60s window
  (not stuck on HARDM + album)
- Director-intent records with `intent_family=ward.highlight.<ward>`
  produce visible emphasis on the named ward within <=200 ms
- Tests pin the value mapping

**Test strategy:** Unit + integration test (mock director-intent.jsonl
record, run dispatch, assert ward-properties.json contents).

**Estimated LOC:** 100-250. Size: S.

**Commit message template:**

```
feat(homage): wire compositional_impingement.intent_family to ward-props

Narrative director's compositional_impingements with intent_family
ward.highlight.<id> / overlay.emphasis.<id> now produce aggressive
ward-properties writes (glow_radius_px=14, pulse_hz=2.0, ttl scaled
by salience). Closes the second half of reckoning §3.4 (the wire was
present; signal was silent).

Phase B2 of homage-completion-plan.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phase B3: Choreographer FSM un-bypass (drop HOLD-default hotfix)

**Scope:**
- `agents/studio_compositor/homage/transitional_source.py` — REMOVE
  the 2026-04-18 hotfix (`initial_state: TransitionState = TransitionState.HOLD`
  default at line 86). Revert to `initial_state: TransitionState =
  TransitionState.ABSENT`.
- `agents/studio_compositor/homage/choreographer.py` — add a new
  method `Choreographer.dispatch_startup_entries(registry)` that, at
  compositor startup, enumerates every registered `HomageTransitionalSource`
  via the source registry and synthesises a `ticker-scroll-in`
  pending transition for each. This guarantees that when
  `HAPAX_HOMAGE_ACTIVE=1` becomes the default, no ward is left
  permanently in ABSENT.
- `agents/studio_compositor/compositor.py` — call
  `choreographer.dispatch_startup_entries(source_registry)` once
  during `StudioCompositor.start_pipeline` after wards are registered.
- Tests: `tests/studio_compositor/test_choreographer_startup_dispatch.py`
  — assert that after `dispatch_startup_entries` + one `reconcile`,
  every ward's FSM has advanced past ABSENT.
- Regression test: `tests/studio_compositor/test_transitional_source_default_state.py`
  — pin the default `initial_state=TransitionState.ABSENT` so a future
  triage commit doesn't silently re-introduce the HOLD-default.

**Description:** This is the single largest change toward "wards
visibly transition" per reckoning §3.1. The hotfix at line 90-110 is
the comment-block describing the gap. This phase REPLACES the hotfix
with the reckoning §7.2 step 3's prescribed fix: choreographer
dispatches entries at startup so wards advance ABSENT -> ENTERING ->
HOLD properly, and the FSM continues to drive transitions thereafter.

**CRITICAL:** This phase MUST NOT land before A2+A3+A4 + A5 are
complete. If it lands first, the surface goes black for any ward
whose Cairo source's render path depends on the HOLD-default
behaviour. Delta sequences this phase AFTER the family-A rewrites
have landed.

**Blocking dependencies:** A2, A3, A4, A5 (every ward must have
been re-verified to render correctly under proper FSM dispatch).

**Parallel-safe siblings:** B1, B2, B4, B5, B6, C, D.

**Success criteria:**
- After deploy + restart, every ward's first paint is preceded by a
  `ticker-scroll-in` transition (visible as a slide-in in v4l2 output)
- Live `jq 'length' /dev/shm/hapax-compositor/homage-pending-transitions.json`
  shows the queue is being drained (size <= 50 typically, not 444)
- Pinned regression test: default `initial_state=ABSENT` cannot be
  silently changed
- 30-second v4l2 capture: viewer sees >= 3 ward transitions
  (entries/exits/modifies)

**Test strategy:** Choreographer integration test + per-ward FSM-
state regression.

**Estimated LOC:** 200-400. Size: M.

**Commit message template:**

```
fix(homage): drop transitional_source HOLD-default; restore choreographer dispatch

Replace the 2026-04-18 paint-and-hold hotfix with proper choreographer-
driven entry dispatch. transitional_source default initial_state reverts
to ABSENT; Choreographer.dispatch_startup_entries enumerates registered
wards and queues ticker-scroll-in for each at compositor start. Wards
now advance ABSENT -> ENTERING -> HOLD via the FSM as the spec intends.

Phase B3 of homage-completion-plan. Closes reckoning §3.1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phase B4: HOMAGE rotation_mode activation (steady|deliberate|rapid|burst)

**Scope:**
- `shared/director_intent.py` — confirm `NarrativeStructuralIntent`
  has `homage_rotation_mode: Literal["sequential","random",
  "weighted_by_salience","paused"]`. This phase adds the four
  semantic modes from spec §4.13 (`steady|deliberate|rapid|burst`) as
  ALIASES that map to the existing four (or extend the Literal set).
  Recommended: extend the Literal: `Literal["sequential", "random",
  "weighted_by_salience", "paused", "steady", "deliberate", "rapid",
  "burst"]` and have the choreographer read the new modes.
- `agents/studio_compositor/homage/choreographer.py` — extend
  `_read_rotation_mode` and the rotation-mode switch logic to handle
  `steady|deliberate|rapid|burst`. Concrete cadences (per spec §4.13):
  - `steady` (default): rotate one ward every 30 s
  - `deliberate`: rotate one ward every 15 s, single transition at a
    time, no concurrent entries
  - `rapid`: rotate one ward every 4 s, allow 2 concurrent entries
  - `burst`: every 60 s, fire a netsplit-burst that exits 8 wards in
    parallel and re-enters them via join-message over 600 ms
- New method: `Choreographer.maybe_rotate(now, rotation_mode, registry)`
  — called every reconcile tick; checks `_last_rotation_ts` against
  the per-mode cadence; if elapsed, picks a ward (round-robin or
  by-salience per mode) and synthesises `ticker-scroll-out` ->
  `ticker-scroll-in` pair.
- `agents/studio_compositor/director_loop.py` — narrative director's
  prompt update at lines 2007, 2036, 2137 (already reference
  rotation_mode) — extend the prompt vocabulary to include the four
  semantic modes so the LLM produces them.
- `agents/studio_compositor/structural_director.py` — extend
  `StructuralIntent.homage_rotation_mode` field type + the prompt
  schema string at line 267.
- Tests: `tests/studio_compositor/test_choreographer_rotation_modes.py`
  — assert per-mode cadence behaviour with mocked time.

**Description:** Currently `homage_rotation_mode=sequential` produces
no visible rotation; the choreographer reads it but `sequential` is
just FIFO ordering of producer-supplied entries — when producers are
silent, no rotation happens. The four semantic modes (steady,
deliberate, rapid, burst) make the choreographer ITSELF a producer of
rotations on a clock cadence, which is what the spec §4.13 prescribes.

**Blocking dependencies:** B3 (rotations only work when wards can
actually advance through ENTERING/EXITING).

**Parallel-safe siblings:** A-family (independent file), B1, B2, B5,
B6, C, D.

**Success criteria:**
- Live: `jq '.homage_rotation_mode' /dev/shm/hapax-structural/intent.json`
  returns one of `steady|deliberate|rapid|burst` (NOT `sequential` as
  the unrecognised default)
- 60-second v4l2 capture under `steady` shows >= 2 ward rotations
- Under `burst`, a netsplit visibly clears 8 wards and re-fills them
- Pinned tests for per-mode cadence

**Test strategy:** Time-mocked choreographer integration tests.

**Estimated LOC:** 350-600. Size: M-L.

**Commit message template:**

```
feat(homage): rotation-mode activation — steady/deliberate/rapid/burst

Extends NarrativeStructuralIntent.homage_rotation_mode to the four
semantic modes from framework spec §4.13. Choreographer.maybe_rotate
synthesises ticker-scroll-out/in pairs on per-mode cadences (30s/15s/
4s/60s+netsplit). The choreographer becomes its own producer of
rotations rather than relying on producer-supplied entries.

Phase B4 of homage-completion-plan. Closes the rotation-mode gap from
reckoning §2.6.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phase B5: Layout JSON: chat_ambient -> ChatAmbientWard

**Scope:**
- `config/compositor-layouts/default.json` — change line 107 from
  `"class_name": "ChatKeywordLegendCairoSource"` to
  `"class_name": "ChatAmbientWard"` for the `chat_ambient` source
  entry (lines 102-117).
- `config/compositor-layouts/consent-safe.json` — same change if the
  consent-safe layout has the same binding (verify; else skip).
- `agents/studio_compositor/cairo_sources/__init__.py` — confirm
  `ChatAmbientWard` is registered in the source-class registry
  (it should be per Phase 10 rehearsal §2.3 expectation that lists
  it). If not, register.
- Tests: `tests/studio_compositor/test_chat_ambient_layout_binding.py`
  — load default.json, assert `chat_ambient` source class resolves
  to `ChatAmbientWard`.

**Description:** Single-line layout fix per reckoning §7.2 step 1.
The new ward is fully implemented; just unbound.

**Blocking dependencies:** None.

**Parallel-safe siblings:** All.

**Success criteria:**
- Post-deploy, the chat-legend-right region renders the
  `[Users(#hapax:1/N)]` `[Mode +v +H]` `[blocks]` cells (NOT the
  static six-keyword legend)
- Layout-binding test passes
- Phase 10 rehearsal §3.5 (chat_ambient) checkboxes tick

**Test strategy:** Layout JSON load + class resolution test.

**Estimated LOC:** 30-80. Size: S.

**Commit message template:**

```
fix(homage): bind chat_ambient layout slot to ChatAmbientWard

Layout default.json had chat_ambient bound to legacy
ChatKeywordLegendCairoSource; the new aggregate-only BitchX-grammar
ChatAmbientWard was implemented but unbound. Single-line JSON edit.

Phase B5 of homage-completion-plan. Closes reckoning §3.5 and §7.2
step 1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phase B6: HARDM emphasis -> FX-chain bias

**Scope:**
- `agents/studio_compositor/fx_chain_ward_reactor.py` (or
  `fx_chain.py` reactor portion) — extend the ward<->FX bus consumer
  so when `WardEvent(ward_id="hardm_dot_matrix",
  transition="HOLD_TO_EMPHASIZED")` fires, the FX chain biases its
  next preset selection toward the "neon" preset family for ~30 s
  (cooldown enforced).
- `agents/studio_compositor/chat_reactor.py` (PresetReactor) — confirm
  the preset-family selection mechanism supports a "bias" input.
- Tests: `tests/studio_compositor/test_fx_chain_hardm_bias.py`

**Description:** Per the success-definition §1.2, when Hapax speaks
and HARDM is emphasised the FX chain should shift toward the "neon"
preset family — this is the cross-modal coupling the operator wants
visible.

**Blocking dependencies:** B3 (so emphasis events actually fire).

**Parallel-safe siblings:** A-family, B1, B2, B4, B5, C, D.

**Success criteria:**
- During a TTS utterance, the FX chain's selected preset family
  visibly shifts toward neon for the duration of the emphasis window
- Cooldown prevents preset-thrash
- Unit tests for the reactor

**Estimated LOC:** 150-300. Size: S-M.

**Commit message template:**

```
feat(homage): HARDM emphasis biases FX-chain preset family toward "neon"

Cross-modal coupling per reckoning §1.2 success-def: when HARDM
WardEvent transition is HOLD_TO_EMPHASIZED, fx_chain biases next
preset family selection toward neon for 30s with cooldown.

Phase B6 of homage-completion-plan.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

### Family C — Observability + governance

#### Phase C1: `hapax_homage_*` Prometheus metrics pipeline

**Scope:**
- `shared/director_observability.py` — extend with the metric
  registrations the framework spec §6 prescribes:
  - `hapax_homage_transition_total{ward, transition_name, phase}` —
    counter, increments on every choreographer-emitted transition
  - `hapax_homage_emphasis_applied_total{ward, intent_family}` —
    counter, increments on every ward-properties write driven by an
    intent_family
  - `hapax_homage_render_cadence_hz{ward}` — gauge, current per-ward
    render rate
  - `hapax_homage_rotation_mode` — labeled gauge (mode value as
    label), 1.0 for active mode, 0.0 for others
  - `hapax_homage_active_package` — labeled gauge (package name as
    label)
  - `hapax_homage_substrate_saturation_target` — gauge, the target
    saturation the choreographer broadcasts
- Wire emit calls into:
  - `agents/studio_compositor/homage/choreographer.py::_emit_metrics`
    (already exists; extend) — emit `hapax_homage_transition_total`
    + `hapax_homage_rotation_mode` + `hapax_homage_active_package` +
    `hapax_homage_substrate_saturation_target`
  - `agents/studio_compositor/compositional_consumer.py::_apply_emphasis`
    + `dispatch_*` — emit `hapax_homage_emphasis_applied_total`
  - `agents/studio_compositor/cairo_source.py::CairoSourceRunner` —
    emit `hapax_homage_render_cadence_hz` per render tick
- Confirm the compositor's Prometheus endpoint at
  `127.0.0.1:9482/metrics` actually exposes these (per reckoning §3.9
  the endpoint may be owned by camera-resilience scrape; if so, add
  the homage metrics to the same registry).
- Tests: `tests/shared/test_director_observability_homage.py`

**Blocking dependencies:** None.

**Parallel-safe siblings:** All.

**Success criteria:**
- `curl -s http://localhost:9482/metrics | grep hapax_homage_` returns
  >= 6 metric lines
- `hapax_homage_transition_total` strictly increases over a 60s
  window
- Tests pin the metric registrations

**Test strategy:** Unit tests with `prometheus_client` test fixtures.

**Estimated LOC:** 250-400. Size: M.

**Commit message template:**

```
feat(homage): hapax_homage_* Prometheus metrics pipeline

Adds the metrics framework spec §6 prescribes (transition_total,
emphasis_applied_total, render_cadence_hz, rotation_mode,
active_package, substrate_saturation_target). Wires emit calls into
choreographer, compositional_consumer, and CairoSourceRunner.

Phase C1 of homage-completion-plan. Closes reckoning §3.9. Provides
the Prometheus alert (rate(transition_total[5m]) < 0.05) the §7.3
verification protocol prescribes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phase C2: Open `cond-phase-a-homage-active-001` research condition

**Scope:**
- Run `scripts/research-registry.py open cond-phase-a-homage-active-001
  --parent cond-phase-a-volitional-director-001` (one-time imperative).
  This creates `~/hapax-state/research-registry/cond-phase-a-homage-
  active-001/condition.yaml`.
- Commit the condition YAML if the registry script doesn't auto-commit.
- `agents/studio_compositor/director_loop.py` — ensure director-intent
  records carry `condition_id = "cond-phase-a-homage-active-001"`
  while the condition is active. There's likely a condition-resolver
  helper in `shared/research_condition.py` or similar; wire the
  director loop to call it and stamp the condition_id on every
  emitted record.
- Tests: `tests/studio_compositor/test_director_intent_condition_id.py`

**Blocking dependencies:** None.

**Parallel-safe siblings:** All.

**Success criteria:**
- `cat ~/hapax-state/research-registry/cond-phase-a-homage-active-001/condition.yaml`
  exists, status `open`
- `tail -1 ~/hapax-state/stream-experiment/director-intent.jsonl |
  jq .condition_id` returns `"cond-phase-a-homage-active-001"`
- Tests pin the condition-stamping behaviour

**Test strategy:** Integration test (mock condition-resolver,
assert dirctor loop writes the id).

**Estimated LOC:** 100-250 (mostly wiring). Size: S.

**Commit message template:**

```
docs(lrr): open cond-phase-a-homage-active-001 + stamp director-intent

Opens the research condition the framework spec §7 prescribed but was
never opened (per reckoning §3.8). Director loop stamps the condition
id on every emitted intent record so Bayesian validation can slice
pre/post-HOMAGE.

Phase C2 of homage-completion-plan.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phase C3: Visual-regression golden suite

**Scope:**
- `tests/studio_compositor/golden/` — directory holding one golden
  image per ward x emphasis state (off + on). Total ~32 images.
- `tests/studio_compositor/test_visual_regression_homage.py` — runner
  that loads each ward, renders to a Cairo ImageSurface at known
  `t=0.0`, compares against the golden with +/-4 channel tolerance,
  emits a side-by-side diff PNG on failure.
- `scripts/regenerate-homage-goldens.sh` — operator-runnable script
  that regenerates all goldens after a deliberate change.
- CI workflow integration: `.github/workflows/ci.yml` (or whichever
  is the primary test workflow) — add a step that runs the visual-
  regression test, uploads diff PNGs as artifacts on failure.

**Description:** Per reckoning §3.10 the existing test suite pins
SHAPE not BEHAVIOUR. This phase doesn't fix the temporal-dynamics
gap (that's E1's rehearsal walkthrough), but it DOES add a visual
regression gate that would catch a future silent fall-back to flat-
fill rendering or a typography regression.

**Blocking dependencies:** A2, A3, A4 (need the new emissive renders
to generate goldens against).

**Parallel-safe siblings:** B1-B6, C1, C2, C4, D1-D3.

**Success criteria:**
- 16 wards x 2 emphasis states = 32 goldens checked in
- CI runs the visual-regression test on every PR
- A deliberate render change (e.g., shimmer amplitude bumped) fails
  the test loudly with a diff PNG

**Test strategy:** Pytest + cairo-image-diff utility.

**Estimated LOC:** 400-700. Size: M.

**Commit message template:**

```
test(homage): visual-regression golden suite (32 images)

Per-ward x emphasis-on/off golden image regressions covering all
16 HOMAGE wards. CI runs the diff on every PR; failures upload
side-by-side diff PNGs as artifacts.

Phase C3 of homage-completion-plan. Provides a continuous gate
against the rendering regressions reckoning §3.10 flagged.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phase C4: Phase 10 rehearsal runbook automation

**Scope:**
- `scripts/run-phase-10-rehearsal.sh` — bash script that walks the
  `docs/runbooks/homage-phase-10-rehearsal.md` checklist programmatically
  for the items that CAN be automated (service status, layout JSON
  validity, source registry contents, font availability, /dev/shm file
  presence + freshness, Prometheus metric scrape, condition.yaml status).
  Items that REQUIRE operator visual observation are listed but
  print as "OPERATOR VERIFY: <description>" rather than auto-passing.
- Output: a pass/fail report at `~/hapax-state/rehearsal/phase-10-
  <timestamp>.txt` with per-checkbox status.
- The script's exit code is non-zero if any auto-checkable item fails.
- Tests: `tests/scripts/test_run_phase_10_rehearsal.py` (mock the
  filesystem + curl calls).

**Description:** Reckoning §4.4 / §7.3 prescribes a script-driven
rehearsal walk so the acceptance gate isn't operator-eyeball-driven
across 60+ checkboxes. This phase ships that script.

**Blocking dependencies:** C1 (so the metrics endpoint actually has
data), C2 (so the condition.yaml exists).

**Parallel-safe siblings:** A-family (independent), B1-B6, C3, D1-D3.

**Success criteria:**
- `bash scripts/run-phase-10-rehearsal.sh` produces a per-checkbox
  pass/fail report; auto-checkable items pass; OPERATOR VERIFY items
  are printed for the operator to walk in <5 min
- The script is idempotent (re-runnable)
- Tests pin the per-section checks

**Test strategy:** Mock-based unit tests + manual smoketest on the
delta worktree.

**Estimated LOC:** 350-600. Size: M.

**Commit message template:**

```
test(homage): scripts/run-phase-10-rehearsal.sh — runbook automation

Walks the auto-checkable items from docs/runbooks/homage-phase-10-
rehearsal.md (service status, layout validity, registry, fonts,
/dev/shm freshness, Prometheus, condition.yaml). Prints OPERATOR
VERIFY items for visual checks. Output: ~/hapax-state/rehearsal/
phase-10-<ts>.txt.

Phase C4 of homage-completion-plan. Implements the §7.3 verification
protocol.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

### Family D — Audio / presence polish (go-live adjacent)

These phases are completion passes on work mostly already shipped per
recent commit log (anti-repetition, vinyl, sidechat CPAL routing).

#### Phase D1: Vinyl-on-stream filter-chain verification

**Scope:**
- AUDIT `config/pipewire/voice-fx-*.conf` — confirm vinyl audio is
  reaching the broadcast sink (PipeWire filter-chain bug per recent
  operator note).
- `agents/studio_compositor/audio_capture.py` (or wherever the audio
  routing lives) — verify the vinyl source is captured.
- Smoketest: produce a `gst-launch-1.0` snippet that plays a known
  audio file through the broadcast pipeline and confirms it reaches
  the output sink.
- If a bug is found: fix the filter-chain config; document in
  `config/pipewire/README.md`.

**Blocking dependencies:** None.

**Parallel-safe siblings:** All.

**Success criteria:**
- Operator can play a vinyl record and hear it on the live stream
- Smoketest documented
- README updated

**Estimated LOC:** 50-200 (config + docs). Size: S.

---

#### Phase D2: YouTube turn-taking gate

**Scope:**
- Identify the YouTube-content surface in the compositor (sierpinski
  may carry it per `docs/research/youtube-content-visibility-...md`
  or there may be a dedicated `youtube_*` source).
- `agents/studio_compositor/<youtube_source>.py` — add a director-
  driven gate so only one YouTube video plays at a time. The gate
  reads `director-intent.jsonl` for `intent_family=youtube.direction`
  records and only enables the video when the director nominates it.
- Tests: `tests/studio_compositor/test_youtube_turn_taking.py`

**Blocking dependencies:** None (independent file).

**Parallel-safe siblings:** All.

**Success criteria:**
- At most one YouTube video visible / audible on the surface at a
  time
- The director can switch videos via `intent_family=youtube.direction`
- Tests pin the gate behaviour

**Estimated LOC:** 200-400. Size: M.

---

#### Phase D3: Hapax TTS presence verification (post-deploy)

**Scope:**
- POST-DEPLOY check: confirm the 20s TTS cadence is holding (per
  the continuous-cognitive-loop axiom).
- `agents/hapax_daimonion/cpal/*` — verify the cognitive loop is
  still firing utterances on the expected cadence after all the
  surface changes land.
- `tests/hapax_daimonion/test_cpal_cadence.py` — ensure regression
  tests pass.
- Confirm `agents/director_loop.py` music-anti-repetition (recent
  commit b87be6d48) actually reduces music narrative duplication in
  director-intent.jsonl.

**Blocking dependencies:** None.

**Parallel-safe siblings:** All.

**Success criteria:**
- 20s TTS cadence holding post-deploy (operator verifies)
- Music narrative duplication rate < 1 per 60s window
- Tests pass

**Estimated LOC:** 100-250 (mostly verification). Size: S.

---

### Family F — Expert-system rule + default retirement (parallel with main wave)

Three delete-only phases shipped alongside A/B/C/D. The full retirement
scope from the two audits (`docs/research/2026-04-19-expert-system-
blinding-audit.md` + `2026-04-19-blinding-defaults-audit.md`) is LARGER
— 14 Category A rules + 18 Category A defaults — but most retirement
work requires new recruitment capability before the rule can safely
come out. This family carves out the ZERO-BLOCKER retirements: rules
that can be deleted immediately because the pipeline is already
scoring them correctly and the rule is only discarding the answer.

F3-F5 below are documented but DEFERRED POST-LIVE because they need
new capability registration (silence, micromove) or architectural work
(speech_production recruitment path restoration) before the gate can
come out safely.

#### Phase F1: Retire `camera.hero` variety-gate

**Scope:**
- `agents/studio_compositor/compositional_consumer.py:198-206` — delete
  the variety-gate block that checks "c920-desk in recent [...], skipping"
  and silently drops the dispatch.
- Evidence from `docs/research/2026-04-19-expert-system-blinding-audit.md`:
  **6,358 / 45,178 (14%) of all compositional dispatches in the last
  12h** were silently dropped by this gate, after the recruitment
  pipeline had already produced a score. The pipeline's answer was
  "use this camera"; the gate overrode it.
- Tests: `tests/studio_compositor/test_compositional_consumer.py` — add
  regression test asserting that an impingement producing a camera.hero
  recruitment score above threshold produces a hero-camera write even
  when the same camera was recently hero'd.
- Pin: `hapax_compositor_variety_gate_skips_total` (if it exists as a
  metric) should trend to zero post-retirement.

**Description:** Smallest possible rule retirement. The pipeline
already recruits `camera.hero.<id>` capabilities correctly; this gate
throws away the answer because of a hardcoded "don't-repeat" bias. If
the operator wants varied hero cameras, the impingement-generation
side should emit diverse `camera.hero.*` impingements (which it
already does via the director's intent_family emissions); the
consumer should not second-guess the pipeline.

**Blocking dependencies:** None (delete-only).

**Parallel-safe siblings:** All.

**Success criteria:**
- `rg 'variety-gate' agents/studio_compositor/compositional_consumer.py`
  returns empty
- Pipeline produces hero-camera dispatches at the pipeline's actual
  recruitment rate (post-retirement baseline: expect ~14% bump in
  camera-hero write frequency)
- Regression test pins the retirement (an artificial "just-used" input
  still produces the dispatch)

**Estimated LOC:** -20 / +40 (delete + test). Size: S.

**Commit message template:**

```
refactor(compositor): retire camera.hero variety-gate (expert-system rule)

Per docs/research/2026-04-19-expert-system-blinding-audit.md §A1:
variety-gate at compositional_consumer.py:198-206 silently dropped
6,358/45,178 (14%) of camera.hero dispatches over 12h — the pipeline
scored them, the gate threw the answer away. Delete-only retirement;
no replacement impingement shape needed (pipeline already recruits
diverse camera.hero.* capabilities via director intent_family).

Phase F1 of homage-completion-plan.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phase F2: Retire `narrative-too-similar` + `activity-rotation` rules

**Scope:**
- `agents/studio_compositor/director_loop.py:1210-1264` — delete the
  `narrative-too-similar` check that rejects a narrative emission if
  it resembles recent ones and falls back to a 7-step hardcoded
  `_emit_micromove_fallback` cycle.
- `agents/studio_compositor/director_loop.py:1293-1335` — delete the
  activity-rotation enforcer that fires `music → music after 3
  consecutive` (evidence: fired 11+ times/12h with the absurd
  self-rotation, per blinding audit §A6).
- Evidence: the micromove fallback fired **40+ times / 12h**; the
  activity rotation fired **11+ times / 12h** including the pathological
  `music→music after 3 consecutive` case. The micromove cycle is
  7 hardcoded tuples at `director_loop.py:1337-1464` — this phase does
  NOT delete that block (F4 post-live deletes it once capabilities are
  registered); it only removes the CALL SITES that trigger the fallback.
- The `_emit_micromove_fallback` method body stays (F4 post-live
  retirement). The triggers are what die.
- Tests: `tests/studio_compositor/test_director_loop_rules_retired.py`
  — assert that a director tick producing a similar narrative no
  longer routes through `_emit_micromove_fallback`; the narrative
  either ships as-is or the LLM is re-prompted (preferred: ship
  as-is — repetition is a recruitment choice the pipeline made).

**Description:** Two delete-only rule retirements in the same file.
The narrative-too-similar rule is the operator's loudest complaint
("Hapax says the same stupid thing over and over"); it's masking the
director-LLM's repetition tendency, which is a prompt-engineering
problem not a post-hoc filter problem. The activity-rotation rule is
mechanically nonsensical at best (rotating music to music).

Per the audit:
> Suggested first-pass retirement: A1 variety-gate, A11 hardcoded
> structural emphasis envelope, A6 narrative-too-similar + micromove
> cycle.

F1 retires A1. F2 retires A6 (call site). A11 is addressed by B1
(aggressive emphasis values replace the envelope).

**Blocking dependencies:** None.

**Parallel-safe siblings:** All.

**Success criteria:**
- `rg 'narrative-too-similar|activity-rotation' agents/studio_compositor/director_loop.py`
  returns 0 live call sites (grep should return only the doc/comment
  references about why they were removed)
- `_emit_micromove_fallback` is no longer called from the director
  tick path
- Regression test pinning the retirement: similar-narrative input does
  NOT fall through to micromove emission

**Estimated LOC:** -120 / +50 (delete + test). Size: S-M.

**Commit message template:**

```
refactor(director): retire narrative-too-similar + activity-rotation rules

Per docs/research/2026-04-19-expert-system-blinding-audit.md §A6:
narrative-too-similar triggered micromove-fallback 40+ times/12h;
activity-rotation fired 11+ times/12h including absurd music→music
self-rotation. Both are expert-system filters second-guessing the
director LLM. Repetition is a prompt problem, not a post-hoc filter
problem.

This phase removes the CALL SITES only. The _emit_micromove_fallback
method body is preserved for F4 post-live retirement (requires
capability registration).

Phase F2 of homage-completion-plan.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

#### Phases F3, F4, F5 (POST-LIVE — not dispatched in this wave)

Not dispatched with the tonight wave. Documented here so the
retirement work is visible and reachable.

- **F3: `silence.*` capability family registration + retire
  `_silence_hold_impingement`.** Requires registering a new capability
  domain in `shared/compositional_affordances.py` so the parser-failure
  path's emitted impingement can recruit against `silence.hold`,
  `silence.surrender`, `silence.wait`. Until then the silence-hold
  fallback stays so the surface doesn't go void on parse failure.
- **F4: Director-micromove capability registry + retire the 7 hardcoded
  micromove tuples.** Registers the 7 tuples in
  `director_loop.py:1337-1464` as 7 named capabilities in
  `affordances/micromove/*.json` so the AffordancePipeline can recruit
  one per `director.micromove_request` impingement. F2 removed the call
  sites; F4 deletes the dead body.
- **F5: Restore `speech_production` recruitment path + retire
  `should_surface` hardcoded thresholds.** `run_loops_aux.py:445-449`
  scores speech via the pipeline then discards the score ("CPAL owns
  it"); CPAL's `should_surface` at `impingement_adapter.py:101-105`
  uses hardcoded thresholds. Post-live work: route pipeline-scored
  speech directly into CPAL's `should_surface`, retire the thresholds.

F3/F4/F5 are tracked as follow-up issues (#163 companion; open as
needed). Operator's governance directive ("no expert-system rules")
implies these DO eventually retire; this plan ships the non-blocker
subset tonight.

---

### Family E — Deploy + acceptance

#### Phase E1: Deploy to running compositor + Phase 10 rehearsal walkthrough

**Scope (operator + delta-coordinated):**
- After all preceding phases land on `hotfix/fallback-layout-assignment`
  AND PRs are squash-merged to main, deploy via the normal
  `rebuild-services.timer` cascade (5-min cadence) OR an explicit
  `scripts/rebuild-service.sh studio-compositor` if waiting is
  intolerable.
- After `studio-compositor.service` restarts, the operator runs
  `bash scripts/run-phase-10-rehearsal.sh` (Phase C4) and observes
  the OPERATOR VERIFY items by direct viewing of `mpv
  v4l2:///dev/video42`.
- Sign-off requires:
  - Auto-checkable items: 100% pass
  - OPERATOR VERIFY items: >= 95% pass (operator may flag 1-2
    cosmetic issues for follow-up without blocking go-live)
- If any blocking item fails: triage immediately; do NOT go live.

**Blocking dependencies:** ALL preceding phases.

**Parallel-safe siblings:** None (this is the terminal phase).

**Success criteria:**
- Full rehearsal pass-or-flagged-cosmetic
- 30-second v4l2 capture saved to
  `~/hapax-state/rehearsal/<timestamp>-acceptance-capture.mp4`
- Operator declares: "we are live"

**Estimated LOC:** 0 (this is execution). Time: 30-60 min for
deploy + walkthrough.

---

## §3. Rollout ordering — DAG and critical path

### Dependency DAG

```
                  PARALLEL BATCH 1 (no deps)
                  A1, A5, A6, B0, B5, B6,
                  C1, C2, D1, D2, D3,
                  F1, F2
                                |
                                v
                  PARALLEL BATCH 2
                  (need A1+A5; B1+B2 need B0)
                  A2, A3, A4, B1, B2
                                |
                                v
                  PARALLEL BATCH 3
                  (need A2+A3+A4)
                  B3 — choreographer FSM unblock
                  C3 — visual-regression goldens
                  (B4 needs B3; B6 needs B3)
                  B4 — rotation modes
                                |
                                v
                  SEQUENTIAL
                  C4 — runbook automation script
                       (needs C1+C2)
                                |
                                v
                  TERMINAL
                  E1 — deploy + rehearsal
```

**Audit-reconciled dependency notes (added post-plan-v1):**
- **B0 is a blocker for B1 and B2.** Per `docs/research/2026-04-19-
  blinding-defaults-audit.md`, 994/994 director-intent records carry
  no `structural_intent` field; B1/B2 write into a consumer that
  never fires without B0's fix. B0 ships in batch 1 alongside B5/B6
  and promotes B1/B2 to batch 2.
- **F1 and F2 are delete-only retirements.** Per the expert-system
  blinding audit, the variety-gate discards 14% of camera-hero
  recruitments and the narrative-too-similar rule triggers the
  hardcoded micromove fallback 40+ times/12h. Both ship in batch 1.
- **F3/F4/F5 are post-live.** They require new capability
  registration (silence, micromove) or an architectural change
  (speech_production recruitment path), which does not fit the
  tonight window.

### Critical path

The longest serial chain is:

`A1 -> A2 (or A3 or A4) -> B3 -> B4 -> C4 -> E1`

- A1: 250-400 LOC, M ~ 1.5 h subagent
- A2 (longest of A2/A3/A4): 900-1300 LOC, L ~ 3 h
- B3: 200-400 LOC, M ~ 1.5 h
- B4: 350-600 LOC, M-L ~ 2 h
- C4: 350-600 LOC, M ~ 1.5 h
- E1: 30-60 min execution

**Critical path floor: ~10-12 h wall-clock if serial.** With ~4
concurrent execution subagents in batch 1 (A1, A5, A6, B1+B2, C1+C2)
and ~3 concurrent in batch 2 (A2, A3, A4), the floor compresses to
~6-8 h wall-clock. With operator awake to merge PRs as they land and
to run Phase 10 rehearsal at the end, **realistic completion is 8-10
h from delta-dispatch start.**

If the operator wants to compress further: reduce A2/A3/A4 scope
(skip the most-cosmetic wards in this pass, defer to a follow-up;
e.g., `vinyl_platter`, `research_marker_overlay`, `whos_here`,
`activity_variety_log` could fall off the critical path with minimal
visual impact).

### Concurrency steady-state

Aim for 3-4 concurrent execution subagents at any given moment.
Delta orchestrates by:

1. Dispatch all batch-1 phases at once (12 phases)
2. As batch-1 phases land + merge, hold A2/A3/A4 (need A1+A5 merged)
3. Dispatch A2/A3/A4 in parallel once A1+A5 are merged
4. Dispatch B3 once A2/A3/A4 merge; B4 follows B3
5. Dispatch C3 once A2/A3/A4 merge (parallel with B3)
6. Dispatch C4 once C1+C2 merge
7. Operator + delta walk E1

---

## §4. Per-phase risk table

| Phase | Failure at 80% | Rollback | Detection |
|-------|---------------|----------|-----------|
| A1 | Helper has subtle alpha bug, all downstream wards over-bright | Revert one commit; helpers haven't been adopted yet | Goldens fail loud |
| A2 | One of 6 wards renders garbled (e.g., pressure_gauge cells overflow) | Revert one commit; wards re-paint with prior code | Visual smoketest + per-ward goldens |
| A3 | Stance-indexed pulse hz wrong, ward strobes uncomfortably | Revert; reduce `STANCE_HZ` constants | Operator visual flag |
| A4 | Album PiP-FX dict deletion loses some viewers' aesthetic preference | NOT a bug; intentional per reckoning §3.2 | n/a |
| A5 | Px437 doesn't actually load via Pango | A5 includes startup WARN; visible immediately in journal | WARN log + visual fallback |
| A6 | Reverie damping misses; substrate still loud | Tunable via JSON; revert is one commit | Visual + `jq` check |
| B1 | Aggressive emphasis values too loud; viewer fatigues | Knob-tunable in compositional_consumer.py; ship a JSON-driven multiplier | Operator visual flag |
| B2 | intent_family dispatch produces emphasis on wrong ward (id mismatch) | Revert; per-id assertions in tests catch this pre-merge | Tests + visual |
| B3 | Choreographer fails to dispatch entries; some wards stay ABSENT (= invisible) | RE-APPLY the hotfix; the line revert is a 2-line change | Visual smoketest immediately reveals |
| B4 | Rotation mode misfires; wards thrash | Revert; mode falls back to `weighted_by_salience` which is the current default | Operator visual flag |
| B5 | ChatAmbientWard render exception; chat-legend region goes black | Revert one JSON line; back to legacy keyword legend | Visual immediately |
| B6 | FX-chain bias too sticky; preset stays on neon | Cooldown is in code; revert reduces stickiness | Visual + Grafana FX-preset histogram |
| C1 | Metrics endpoint conflict with camera-resilience scrape | Use a separate port `:9483` for HOMAGE metrics if needed | `curl /metrics` empty result |
| C2 | research-registry script fails to open condition | Manual `~/hapax-state/research-registry/...` directory creation; commit YAML by hand | Script exit code |
| C3 | Goldens fail spuriously due to font hinting differences | Tolerance is +/-4 per channel; bump if needed | CI red |
| C4 | Rehearsal script reports false-positive failures | Iterate the script; not blocking deploy | Operator runs and reads |
| D1 | Vinyl audio still not reaching stream | Operator-flagged; not deploy-blocking but go-live-blocking | Operator listens |
| D2 | YouTube gate too strict, no videos play | Loosen the gate; revert one file | Operator flags |
| D3 | TTS cadence broke (regression from D-family changes) | Tests pin; CI catches before merge | Tests + operator |
| E1 | Rehearsal fails > 5% checkboxes | Triage per failed item; do NOT go live | Script + operator |

---

## §5. Branch / PR strategy

- **Branch:** `hotfix/fallback-layout-assignment` (already current).
  All phases commit directly. Do NOT create new branches per phase.
- **Per phase:** one execution subagent -> one commit (or tight set:
  module + tests + goldens) -> push -> delta opens one PR with
  squash-merge. The PR body is the phase's success criteria.
- **PR template (per phase):**

  ```
  ## Phase <N>: <name>

  Per docs/superpowers/plans/2026-04-19-homage-completion-plan.md §<N>.

  ## Changes
  - <bullet list of file changes>

  ## Visual evidence
  - Pre-deploy: tests pass (`uv run pytest <paths> -q`)
  - Post-deploy: <visual check from success criteria>

  ## Test plan
  - [ ] `uv run pytest <paths> -q`
  - [ ] `uv run ruff check <paths>`
  - [ ] visual smoketest: <description>

  Closes #<issue> (if any).
  ```

- **CI gate:** every phase's PR must pass CI (ruff, pytest,
  visual-regression once C3 lands). Delta does NOT merge until CI
  green.
- **Merge order:** batch-1 phases merge as ready; A2/A3/A4 merge
  AFTER A1+A5 merge; B3 merges AFTER A2+A3+A4 merge; etc. per
  the DAG in §3.
- **Operator owns:** PR review (light-touch — alpha + delta have
  done the heavy lifting), merge button, deploy command, rehearsal
  walkthrough.
- **DO NOT:** force-push to main; rebase merged commits; skip CI;
  skip the rehearsal gate before declaring live.

---

## §6. Go-live acceptance checklist

A 15-25 item checklist the operator walks in <10 min after E1.
Designed so the operator can mark "PASS" / "FLAG" / "BLOCK" per item.

### Visual checks (by `mpv v4l2:///dev/video42`)

1. [ ] Reverie reads as a tinted ground (NOT a kaleidoscopic
       saturation explosion)
2. [ ] Captions strip in Px437 IBM VGA 8x16 (NOT JetBrains Mono / DejaVu)
3. [ ] Album cover renders with mIRC-16 quantize + scanlines (NOT
       random PiP filter)
4. [ ] Token pole shows token-as-point-of-light at navel (NOT smiley face)
5. [ ] Pressure gauge is a row of CP437 half-block cells (NOT flat red bar)
6. [ ] HARDM renders as synthwave point cloud with shimmer (NOT flat-fill grid)
7. [ ] Chat-legend-right shows `[Users(#hapax:1/N)]` `[Mode +v +H]`
       cells (NOT static six-keyword legend)
8. [ ] Stance indicator pulses at stance-indexed Hz (visible breathing)
9. [ ] Activity header inverse-flashes on activity change (observe
       for 60s)
10. [ ] At least 3 ward transitions visible in a 30-second window
        (entries / exits / netsplit)
11. [ ] At least 2 wards show emphasis border pulse simultaneously
        during normal director ticks (NOT just HARDM + album)

### Metric / state checks

12. [ ] `curl -s http://localhost:9482/metrics | grep hapax_homage_`
        returns >= 6 metric lines
13. [ ] `hapax_homage_transition_total` increases over 60s
14. [ ] `jq '.homage_rotation_mode' /dev/shm/hapax-structural/intent.json`
        returns one of `steady|deliberate|rapid|burst`
15. [ ] `jq '."colorgrade.saturation"' /dev/shm/hapax-imagination/uniforms.json`
        returns <= 0.55
16. [ ] `tail -1 ~/hapax-state/stream-experiment/director-intent.jsonl
        | jq .condition_id` returns `"cond-phase-a-homage-active-001"`
17. [ ] `cat ~/hapax-state/research-registry/cond-phase-a-homage-active-001/condition.yaml`
        exists, status `open`
18. [ ] `bash scripts/run-phase-10-rehearsal.sh` exits 0 (auto-checks
        pass)

### Audio + cadence

19. [ ] Hapax TTS firing on ~20s cadence
20. [ ] Vinyl audible on stream
21. [ ] At most one YouTube video active at any moment
22. [ ] No music-narrative repeats in latest 5 director-intent records

### Governance

23. [ ] Face-obscure pipeline active (no un-obscured faces in v4l2)
24. [ ] No personification violations in compositor journal
        (`journalctl --user -u studio-compositor.service -n 200 |
        grep -i personif` empty)

### Audit-reconciled rule retirement

25a. [ ] `tail -5 ~/hapax-state/stream-experiment/director-intent.jsonl
         | jq '.structural_intent'` returns non-null objects with at
         least one populated field (B0 verification)
25b. [ ] `rg 'variety-gate' agents/studio_compositor/compositional_consumer.py`
         returns 0 live call sites (F1 verification)
25c. [ ] `rg 'narrative-too-similar|activity-rotation' agents/studio_compositor/director_loop.py`
         returns 0 live call sites (F2 verification)

### Operator declaration

25. [ ] Operator: "this looks like one programmed instrument" -> GO LIVE

---

## §7. Notes for delta

### Subagent dispatch hygiene

- Per workspace CLAUDE.md "Subagent Git Safety — MANDATORY": dispatch
  WITHOUT `isolation: "worktree"`. Include verbatim in every dispatch
  prompt:

  > You are working in the cascade worktree
  > (`~/projects/hapax-council--cascade-2026-04-18`).
  > Branch is `hotfix/fallback-layout-assignment`. Commit directly to
  > this branch. Do NOT create branches. Do NOT run `git checkout`
  > or `git switch`. Do NOT switch branches under any circumstances.

- After EVERY subagent that writes code, immediately verify:
  `ls <expected_files> && git log --oneline -3 origin/hotfix/fallback-layout-assignment..`.
  If files are missing, rewrite directly — the code is in conversation
  context. Do not re-dispatch.

### Spec ambiguities flagged for delta

The plan is concrete enough to dispatch all 23 phases. The following
items the plan flags as needing resolution BEFORE dispatching the
indicated phase, OR can be resolved at execution-subagent discretion
with the documented default:

- **Phase A4 — vinyl_platter classification:** the plan does not have
  certainty whether `vinyl_platter.py` is a Cairo source or a gst-only
  surface. Default: execution subagent inspects, classifies, and
  either rewrites emissively (if Cairo) or skips with a one-line
  commit comment (if gst-only).
- **Phase A6 — exact saturation target value:** the substrate-invariant
  doc prescribes "damped" without a number. Default: 0.40 (mid-range
  of 0.35-0.55). Operator can tune post-deploy via the broadcast
  writer constant.
- **Phase B4 — rotation cadences:** the framework spec §4.13 lists
  `steady|deliberate|rapid|burst` as enum values without prescribed
  cadence numbers. Defaults proposed: steady=30s, deliberate=15s,
  rapid=4s, burst=60s+netsplit. Operator can tune at runtime via the
  structural intent.
- **Phase B6 — FX-chain bias mechanism:** depends on whether
  `PresetReactor` already supports a "bias" input. If not, the
  execution subagent extends `PresetReactor` to accept one. Add this
  to the subagent's scope explicitly in dispatch prompt.
- **Phase C1 — metrics port conflict:** if `:9482` is exclusively the
  camera-resilience scrape, fall back to `:9483` for HOMAGE metrics.
  Subagent decides at dispatch time based on `lsof -i :9482` output.

### Phases that are "as ambiguous as the plan can make them" but still dispatchable

None. Every phase has concrete file paths, function names, and
success criteria. If a subagent encounters ambiguity, it should
ask delta in conversation rather than guess.

### Dependencies to resolve BEFORE dispatching

Before dispatching ANY phase, delta confirms:

1. The cascade worktree (cwd of this plan) is on branch
   `hotfix/fallback-layout-assignment` with no uncommitted changes.
2. `uv sync --all-extras` is current (so subagents can run pytest
   without dependency-resolution delays).
3. The Px437 TTF is installed at
   `/usr/share/fonts/TTF/Px437_IBM_VGA_8x16.ttf` (per reckoning
   Appendix A — should already be present, verify with `ls` on that
   path).
4. The compositor service is currently running so post-deploy visual
   smoketests can happen (`systemctl --user is-active
   studio-compositor.service`).

If any of these is false: resolve before dispatching.

---

## §8. Coda

The reckoning document recommended Option B (wire the existing
correct-shape rendering scaffolding without rewriting it). Operator
chose Option A (top-down rewrite of every ward's render layer) AND
demanded the gap-closure work that Option B would have done anyway.
This plan ships both, in one branch, in one night, via parallel
execution subagents.

The plan's grain is concrete enough that delta can dispatch the 23
phases without reading any other document. The plan's ordering is
strict enough that the critical path is ~6-8 h with parallelism and
the surface lands in a state the operator can sign off on by
walking §6.

The acceptance test remains the operator's read of a 30-second v4l2
capture: "this is a designed thing, made by one person, with its own
dialect, that is responding to something happening underneath."
That is the spec, paraphrased. That is the test.

---

## Appendix A — file:line targets index

For execution subagents to cross-reference quickly:

- HARDM exemplar render method: `agents/studio_compositor/hardm_source.py:621-739`
- Choreographer FSM hotfix to remove: `agents/studio_compositor/homage/transitional_source.py:90-110`
- Default `initial_state` to revert: `agents/studio_compositor/homage/transitional_source.py:86`
- Album PiP-FX dict to delete: `agents/studio_compositor/album_overlay.py:34-170`
- Album splattribution typography: `agents/studio_compositor/album_overlay.py:325-326`
- Captions typography to swap: `agents/studio_compositor/captions_source.py:53-65`
- Token-pole cascade-marker font to swap: `agents/studio_compositor/token_pole.py:622`
- Layout `chat_ambient` binding to fix: `config/compositor-layouts/default.json:107`
- Cairo toy-API font selection to retire: `agents/studio_compositor/legibility_sources.py:113-128`
- Cairo toy-API font selection (homage rendering): `agents/studio_compositor/homage/rendering.py:36-51`
- Cairo toy-API font selection (chat ambient): `agents/studio_compositor/chat_ambient_ward.py:92-101`
- Choreographer `_emit_metrics` extension point: `agents/studio_compositor/homage/choreographer.py` (search `_emit_metrics`)
- `dispatch_structural_intent` to make aggressive: `agents/studio_compositor/compositional_consumer.py:1100-1176`
- `_apply_emphasis` / `_apply_placement`: `agents/studio_compositor/compositional_consumer.py:~1020-1067`
- `ward_properties.set_ward_properties`: `agents/studio_compositor/ward_properties.py:172-208`
- `paint_emphasis_border` (already wired, just needs aggressive values): `agents/studio_compositor/homage/rendering.py:203-270`
- Phase 10 rehearsal: `docs/runbooks/homage-phase-10-rehearsal.md` (845 lines)
- Live state inspection paths:
  - `/dev/shm/hapax-compositor/ward-properties.json`
  - `/dev/shm/hapax-compositor/homage-pending-transitions.json`
  - `/dev/shm/hapax-compositor/homage-substrate-package.json`
  - `/dev/shm/hapax-compositor/narrative-structural-intent.json`
  - `/dev/shm/hapax-structural/intent.json`
  - `/dev/shm/hapax-imagination/uniforms.json`
  - `~/hapax-state/stream-experiment/director-intent.jsonl`

End of plan.
