# HOMAGE × Nebulous Scrim — Cross-Cutting Ward Inventory & Integration Plan (Dispatch 6/6)

**Status:** Research / design, operator-directed 2026-04-20.
**Authors:** cascade (Claude Opus 4.7, 1M).
**Position in dispatch set:** Sixth and final cross-cutting integration layer. The four sibling dispatches cover algorithmic intelligence, disorientation aesthetics, scrim architecture, and choreographer/audio-coupled motion respectively. This doc binds them together at the ward level.
**Governing anchors:**
- Nebulous Scrim core design — `docs/research/2026-04-20-nebulous-scrim-design.md` §6 ("Wards on the Scrim")
- HOMAGE framework — `docs/superpowers/specs/2026-04-18-homage-framework-design.md`
- HARDM redesign — `docs/research/2026-04-19-hardm-redesign.md`, `docs/research/2026-04-20-hardm-aesthetic-rehab.md`
- HARDM communicative-anchoring — `docs/research/hardm-communicative-anchoring.md`
- Programme primitive — `shared/programme.py`, `docs/research/2026-04-19-content-programming-layer-design.md`
- MonetizationRiskGate — `shared/governance/monetization_safety.py`, `docs/governance/monetization-risk-classification.md`
- Layout JSON authority — `config/compositor-layouts/default.json`
- Workspace memory: `project_hardm_anti_anthropomorphization`, `reference_wards_taxonomy`, `project_programmes_enable_grounding`, `feedback_no_expert_system_rules`
**Scope:** Concrete, file:line-cited audit of every ward currently registered or live, classification of each ward's behavior in the scrim model, per-ward integration plan, and a phased ship plan. No code merged here — this dispatch is the *contract* the next four PRs satisfy.

---

## §1 TL;DR

The default layout (`config/compositor-layouts/default.json`) currently assigns **13 ward sources** to **15 distinct surfaces** (the four corner PiPs are reused by the four "hero" wards; the others each own a dedicated surface). The CairoSource registry in `agents/studio_compositor/cairo_sources/__init__.py:71-160` registers **15 named classes** plus 1 example-only class (`VinylPlatterCairoSource`); the three recently removed wards (`captions` d69039159, `grounding_provenance_ticker` b60704c88, `chat_ambient` b60704c88) are still registered and remain available for non-default layouts.

The single missing piece in the existing scrim doc (`docs/research/2026-04-20-nebulous-scrim-design.md` §6) is the per-ward *behavior* table — depth alone is insufficient; each ward must answer five behavioral questions: motion personality, scrim permeability, transit cadence, trap tolerance, and audio coupling. This dispatch supplies that table.

### Per-ward depth/motion summary (full detail in §3, §4, §5):

| Ward (default layout) | Source class | Depth band | Motion personality |
|---|---|---|---|
| `token_pole` | `TokenPoleCairoSource` | **Hero-presence** (straddles scrim) | Reactive — token traverses path; cranium-arrival emphasis transit |
| `album` | `AlbumOverlayCairoSource` | **Beyond-scrim** (deep) | Reactive — track change → emphasis transit; otherwise still |
| `stream_overlay` | `StreamOverlayCairoSource` | **Surface** | Pulse-locked — chat surge → moiré density spike |
| `sierpinski` | `SierpinskiCairoSource` | **Beyond-scrim** (deep) | Slow-drifter — geometric ground; rotation stays sub-1 rev/min |
| `reverie` | external `shm_rgba` (not a cairo ward; pipeline scrim source) | **The scrim itself** | Permanent generative substrate |
| `activity_header` | `ActivityHeaderCairoSource` | **Surface** | Pulse-locked — 200ms inverse-flash on activity flip |
| `stance_indicator` | `StanceIndicatorCairoSource` | **Surface** | Pulse-locked — stance-indexed Hz breathing |
| `impingement_cascade` | `ImpingementCascadeCairoSource` | **Near-surface** | Slow-drifter — row stack with slide-in / 5s lifetime decay |
| `recruitment_candidate_panel` | `RecruitmentCandidatePanelCairoSource` | **Operator-tools** (META) | Reactive — ticker-scroll on new recruitment |
| `thinking_indicator` | `ThinkingIndicatorCairoSource` | **Near-surface** | Pulse-locked — stance-indexed breathing while LLM in flight |
| `pressure_gauge` | `PressureGaugeCairoSource` | **Near-surface** | Pulse-locked — beat-quantised CP437 cells |
| `activity_variety_log` | `ActivityVarietyLogCairoSource` | **Near-surface** | Slow-drifter — 6-cell ticker scroll |
| `whos_here` | `WhosHereCairoSource` | **Surface** | Reactive — viewer count change → flash |
| `hardm_dot_matrix` | `HardmDotMatrix` | **Hero-presence** (straddles) | Pulse-locked — 256-cell field, RD underlay, ripple wavefronts |

### Phase 1 ship recommendation (3 wards):

The three wards whose depth bands are *most distinct* and whose code paths are *least entangled* with each other:

1. **`token_pole`** at hero-presence depth (the avatar reaches *through*) — the spatial-metaphor anchor.
2. **`album`** at beyond-scrim depth (the thing the audience peers at) — the deepest legible target.
3. **`stream_overlay`** at surface depth (inscribed on the fabric, full chroma) — the shallowest target.

These three span the full depth range, share zero state, and prove the scrim-permeability uniform end-to-end without any of the harder coordination problems (HARDM cell-level chaos, cascade lifetime + scrim wake interaction, programme-mode layout swaps). Phase 2 expands to all 13 wards. Detailed phasing in §12.

---

## §2 Live Inventory — Every Ward in `default.json`

Direct read from `config/compositor-layouts/default.json` (615 lines as of 6afcde7bb). Sources are listed in JSON order; surface geometry is the explicit `rect` from each surface block; assignment column maps source→surface 1:1. Update cadence and rate are the JSON-declared `update_cadence` + `rate_hz`; `"always"` means the GStreamer cairooverlay tick rate (currently the ~30fps composite output).

### 2.1 Source/surface/assignment table

| Ward (id) | Class | natural_w×h | Surface (id) | x | y | w | h | z_order | Cadence | Hz | tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `token_pole` | `TokenPoleCairoSource` | 300×300 | `pip-ul` | 20 | 20 | 300 | 300 | 10 | always | n/a | — |
| `album` | `AlbumOverlayCairoSource` | 400×520 | `pip-ll` | 20 | 540 | 400 | 520 | 10 | always | n/a | — |
| `stream_overlay` | `StreamOverlayCairoSource` | 400×200 | `pip-lr` | 1500 | 860 | 400 | 200 | 10 | rate | 2.0 | — |
| `sierpinski` | `SierpinskiCairoSource` | 640×640 | (registered, **not assigned in default.json**) | — | — | — | — | — | always | n/a | — |
| `reverie` | external_rgba (`/dev/shm/hapax-sources/reverie.rgba`) | 640×360 | `pip-ur` | 1260 | 20 | 640 | 360 | 10 | always | n/a | — |
| `activity_header` | `ActivityHeaderCairoSource` | 800×56 | `activity-header-top` | 560 | 16 | 800 | 56 | 30 | rate | 2.0 | legibility, authorship |
| `stance_indicator` | `StanceIndicatorCairoSource` | 100×40 | `stance-indicator-tr` | 1800 | 24 | 100 | 40 | 35 | rate | 2.0 | legibility, authorship |
| `impingement_cascade` | `ImpingementCascadeCairoSource` | 480×360 | `impingement-cascade-midright` | 1260 | 400 | 480 | 360 | 24 | rate | 2.0 | hothouse, pressure |
| `recruitment_candidate_panel` | `RecruitmentCandidatePanelCairoSource` | 800×60 | `recruitment-candidate-top` | 560 | 80 | 800 | 60 | 24 | rate | 2.0 | hothouse, authorship |
| `thinking_indicator` | `ThinkingIndicatorCairoSource` | 170×44 | `thinking-indicator-tr` | 1620 | 20 | 170 | 44 | 26 | rate | 6.0 | hothouse, authorship |
| `pressure_gauge` | `PressureGaugeCairoSource` | 300×52 | `pressure-gauge-ul` | 20 | 336 | 300 | 52 | 24 | rate | 2.0 | hothouse, pressure |
| `activity_variety_log` | `ActivityVarietyLogCairoSource` | 400×140 | `activity-variety-log-mid` | 440 | 540 | 400 | 140 | 24 | rate | 2.0 | hothouse, authorship |
| `whos_here` | `WhosHereCairoSource` | 230×46 | `whos-here-tr` | 1460 | 20 | 150 | 46 | 26 | rate | 2.0 | hothouse, audience |
| `hardm_dot_matrix` | `HardmDotMatrix` | 256×256 | `hardm-dot-matrix-ur` | 1600 | 20 | 256 | 256 | 28 | rate | 15.0 | homage, avatar |

**13 sources × 13 assignments × 15 surfaces (4 PiPs + 11 dedicated rect surfaces)** — surface count exceeds source count because the four PiP surfaces (`pip-ul`, `pip-ur`, `pip-ll`, `pip-lr`) are programme-rotated targets, plus the three `video_out_*` egress surfaces at z=100/101/102 that are *not* ward surfaces (they consume the composited output). Sierpinski is registered (`agents/studio_compositor/cairo_sources/__init__.py:103`) but no `default.json` assignment binds it; it appears via dynamic affordance recruitment when the impingement → reverie satellite path activates one of its `sat_sierpinski_*` nodes.

### 2.2 Sources only registered (not in default.json)

From `agents/studio_compositor/cairo_sources/__init__.py:71-160`:

- `CaptionsCairoSource` — registered line 107. Removed from default.json by d69039159 (stale "yeah" pin).
- `ChatKeywordLegendCairoSource` — registered line 118 as a back-compat alias; no default.json reference any longer.
- `ChatAmbientWard` — registered line 117. Removed from default.json by b60704c88.
- `GroundingProvenanceTickerCairoSource` — registered line 119. Removed from default.json by b60704c88.
- `ResearchMarkerOverlay` — registered line 136 as a top-strip; operator-decided when to add a layout surface.
- `VinylPlatterCairoSource` — registered line 157, opt-in via `config/compositor-layouts/examples/vinyl-focus.json` only.

### 2.3 Per-ward inputs (data sources)

| Ward | Inputs (file paths or signal sources) |
|---|---|
| `token_pole` | `LEDGER_FILE = /dev/shm/hapax-compositor/token-ledger.json` (token_pole.py:46); `assets/vitruvian_man_overlay.png`; `HAPAX_TOKEN_POLE_PATH` env var (token_pole.py:96) |
| `album` | `/dev/shm/hapax-compositor/album-cover.png` (album_overlay.py:43); `/dev/shm/hapax-compositor/music-attribution.txt` (album_overlay.py:44); decoupled from `vinyl_playing` since ca0e955cc |
| `stream_overlay` | `fx-current.txt`, `token-ledger.json`, `chat-state.json` (stream_overlay.py:31-33) |
| `sierpinski` | `YT_FRAME_DIR = /dev/shm/hapax-compositor/` YouTube frames (sierpinski_renderer.py:59); audio energy snapshot via `set_audio_energy()` |
| `reverie` | `/dev/shm/hapax-sources/reverie.rgba` (default.json:64); written by `hapax-imagination` daemon |
| `activity_header` | `/dev/shm/hapax-director/narrative-state.json` + `~/hapax-state/stream-experiment/director-intent.jsonl` (legibility_sources.py:61-64) |
| `stance_indicator` | Same as `activity_header` |
| `impingement_cascade` | `/dev/shm/hapax-compositor/recent-impingements.json` (hothouse_sources.py:106) preferred; falls back to `~/.cache/hapax-daimonion/perception-state.json` + `/dev/shm/hapax-stimmung/state.json` (hothouse_sources.py:69-70) |
| `recruitment_candidate_panel` | `/dev/shm/hapax-compositor/recent-recruitment.json` (hothouse_sources.py:76) |
| `thinking_indicator` | `/dev/shm/hapax-director/llm-in-flight.json` (hothouse_sources.py:71) |
| `pressure_gauge` | Stimmung dimensions (`/dev/shm/hapax-stimmung/state.json`) and presence state (hothouse_sources.py:75) |
| `activity_variety_log` | Director intent + perception walk |
| `whos_here` | `/dev/shm/hapax-compositor/youtube-viewer-count.txt` (hothouse_sources.py:77); `~/.cache/hapax-daimonion/presence-state.json` |
| `hardm_dot_matrix` | `/dev/shm/hapax-compositor/hardm-cell-signals.json` (hardm_source.py:14); `RECENT_RECRUITMENT_FILE` (hardm_source.py:100); `recent-recruitment.json` for ripple seeding |

### 2.4 Per-ward outputs (rendered form)

| Ward | Output form |
|---|---|
| `token_pole` | Image (Vitruvian PNG) + animated path + token glyph + cranium-arrival particle explosion (token_pole.py:78-117) |
| `album` | Image (cover) + Px437 attribution text below + scanlines + dither shadow + 2px border |
| `stream_overlay` | 3-line Px437 text strip — `>>> [FX|...]`, `>>> [VIEWERS|N]`, `>>> [CHAT|...]` (stream_overlay.py:64-89) |
| `sierpinski` | 2-level triangle with 3 YouTube-frame corner regions + waveform centre (sierpinski_renderer.py:1-13) |
| `reverie` | RGBA frame from wgpu vocabulary graph (8-pass, see council CLAUDE.md "Tauri-Only Runtime") |
| `activity_header` | `>>> [ACTIVITY \| gloss] :: [ROTATION:<mode>]` — Px437, optional flash (legibility_sources.py:19) |
| `stance_indicator` | `[+H <stance>]` — Px437 with breathing pulse (legibility_sources.py:21) |
| `impingement_cascade` | Stacked emissive rows: dot + Px437 id + 8-cell salience bar + family accent (hothouse_sources.py:271-285) |
| `recruitment_candidate_panel` | 3 cells, each: family token + 16-point recency bar + age tail (hothouse_sources.py:425-560) |
| `thinking_indicator` | Single dot (idle: muted; active: cyan + breathing) + `[thinking...]` label |
| `pressure_gauge` | 32-cell CP437 half-block bar with green→yellow→red interpolation + Px437 label (hothouse_sources.py:26-27) |
| `activity_variety_log` | 6 emissive cells, ticker-scroll motion (hothouse_sources.py:28-29) |
| `whos_here` | `[hapax:1/N]` Px437 with emissive 1 and N glyphs (hothouse_sources.py:30-31) |
| `hardm_dot_matrix` | 16×16 grid of CP437 block characters (hardm_source.py:55: `(" ", "░", "▒", "▓", "█")`) over reaction-diffusion underlay |

### 2.5 HARDM-classification (anti-anthropomorphization binding)

The HARDM invariant (memory: `project_hardm_anti_anthropomorphization`) is a governance principle: visual surfaces representing Hapax MUST NOT acquire face-iconography (no eyes, mouths, expressions). Per-ward classification:

| Ward | HARDM-bound? | Justification |
|---|---|---|
| `token_pole` | **Yes** | Token-pole IS the avatar's signature glyph; per token_pole.py:1-13 it's anchored to a *figure* (Vitruvian Man) — invariant binds to "no facial features beyond the public-domain reference image" |
| `hardm_dot_matrix` | **Yes (canonical)** | Spec name literally references the invariant: "Hapax Avatar Representational Dot-Matrix"; per hardm_source.py:1-22 the grid never resolves into face-like clusters; spec at `docs/superpowers/specs/2026-04-18-hardm-dot-matrix-design.md` and `docs/research/hardm-communicative-anchoring.md` are the governing docs |
| `activity_header`, `stance_indicator`, `impingement_cascade`, `recruitment_candidate_panel`, `thinking_indicator`, `pressure_gauge`, `activity_variety_log`, `whos_here` | Indirect | These are *internal-state* readouts. Anti-anthropomorphization binds at the rendering grammar layer (no face glyphs, no emoji eyes/mouths) but not as a primary constraint |
| `album`, `sierpinski`, `stream_overlay`, `reverie` | No (HARDM-orthogonal) | Album is operator's external content; sierpinski is geometric ground; stream_overlay is chrome; reverie is generative substrate. None of these *represent Hapax* and so are not bound by the invariant |

---

## §3 Per-Ward Depth Assignment + Justification

Depth = (slowness) × (foundational-ness) × (anti-attention-pull). The Nebulous Scrim doc §6 already places wards in four bands (surface, near-surface, hero-presence, beyond-scrim). This dispatch refines each placement with concrete reasoning, including the wards added/removed since the scrim doc was written (HARDM is now in default.json; captions, chat_ambient, grounding_provenance_ticker are removed).

### 3.1 Beyond-scrim — what the audience peers at (deepest)

- **`album` (depth tier: deep)** — Operator's external referent; *what the audience came to see through the scrim*. Album cover is foundational to the listening experience, slow (track-rate, not subsecond), and pulls attention only at track-change. Per ca0e955cc the cover renders unconditionally — it should be visible even when MIDI transport is idle, because it answers "what's playing right now?" Justification matches scrim doc §6.4.
- **`sierpinski` (depth tier: deep, when present)** — Algorithmic-composition sketch; pure geometric ground; slow-rotating; the most foundational of the wards in the visual sense (it composites BEFORE the GL shader chain per sierpinski_renderer.py:3-6). Even though absent from default.json, when affordance-recruited it must render at deep tier. Matches scrim doc §6.4.
- **Camera PiPs** — Not technically wards but composited at this same depth band. Operator visible "over there." Cameras carry differential blur + atmospheric-perspective tint (scrim doc §4.1, §4.3).

### 3.2 Hero-presence — straddling the scrim (Hapax's signature)

- **`token_pole` (depth tier: straddle)** — Hapax's signature glyph + Vitruvian figure. The avatar is *on the other side*, but its signature reaches through. The token's traversal from navel→cranium (token_pole.py:73-76) is Hapax's pulse, visible as a hand pressed against fabric from inside. Confirms scrim doc §6.3.
- **`hardm_dot_matrix` (depth tier: straddle)** — 16×16 dot-grid avatar. Matches scrim doc §6.3. The grid IS Hapax's representational form; its glow-through-fabric character (per scrim doc §8.2 bloom asymmetry) is load-bearing.

### 3.3 Surface — inscribed on the scrim's outward face

These are read by the audience as labels on the fabric; full chroma, sharp, no scrim distortion:

- **`stream_overlay` (depth tier: surface)** — Stream chrome (FX preset, viewer count, chat status). Per stream_overlay.py:1-13 it's a status strip, anchored bottom-right. It's *informational* — must always win legibility per scrim doc §6.1.
- **`activity_header` (depth tier: surface)** — Authorship indicator: which activity the director is in, with optional rotation mode token. Per legibility_sources.py:19-20 this is on-frame authorship — must read clearly.
- **`stance_indicator` (depth tier: surface)** — `[+H stance]` chip. Tiny (100×40), top-right (1800,24). Pulsing. Always visible legibility surface.
- **`whos_here` (depth tier: surface)** — `[hapax:1/N]` audience framing. The "you-are-here" of the broadcast — surface inscription.

### 3.4 Near-surface — slightly behind the weave (overheard, not declaimed)

These are Hapax's internal-state wards (scrim doc §6.2): legible but as impressions:

- **`impingement_cascade` (depth tier: near-surface)** — Top-N perceptual signals with 5s lifetime decay (hothouse_sources.py:287). The cascade IS the cognitive weave; partial obscuring is appropriate.
- **`recruitment_candidate_panel` (depth tier: near-surface)** — Last-3 recruitments; transient by nature. Behind the weave is right.
- **`thinking_indicator` (depth tier: near-surface)** — Tiny breathing dot; high update rate (6Hz) but small visual footprint. Should appear THROUGH the scrim as a soft pulse, not punch through it.
- **`pressure_gauge` (depth tier: near-surface)** — 32-cell pressure bar. Operator-state surface; informational but not headline.
- **`activity_variety_log` (depth tier: near-surface)** — 6-cell ticker, slow scroll. Trace of Hapax's recent activity — overheard.

### 3.5 Operator-tools layer (META — visible only when operator-mode demands)

- **`recruitment_candidate_panel`** ALSO occupies this band when the operator is debugging recruitment behavior; in normal stream operation it's near-surface, but a programme like `Repair` could pin it to META visibility.

### 3.6 The scrim itself

- **`reverie`** — Per scrim doc §5.5, Reverie's 8-pass graph IS the scrim substrate. Not a ward, not at any depth band — *is* the depth field that all other wards relate to.

---

## §4 Per-Ward Motion Personality

Adopting the four motion classes specified in the dispatch brief:

### 4.1 Slow-drifters (sub-Hz, barely-moving, contribute depth not attention)

- `sierpinski` — sub-revolution-per-minute rotation; the Sierpinski geometry is structurally still
- `impingement_cascade` — row stack with slow slide-in; 5s lifetime fade (hothouse_sources.py:287)
- `activity_variety_log` — 6-cell ticker with smooth scroll
- `album` — fundamentally still; only the cover-quantization shimmer animates at sub-Hz

### 4.2 Pulse-locked (beat-quantized motion, MIDI-clock or stance-Hz coupled)

- `pressure_gauge` — 32 CP437 cells respond to pressure (hothouse_sources.py:26-27); motion is per-cell flicker at stance-indexed Hz
- `hardm_dot_matrix` — 256 cells driven per-cell by signal state; ripple wavefronts on family recruitment events (hardm_source.py:71-81); RD underlay at 1 step/tick
- `stance_indicator` — Pulse at `STANCE_HZ` rate (legibility_sources.py:46)
- `thinking_indicator` — Breathing point-of-light at `stance_hz(stance) * SHIMMER_HZ_DEFAULT` while LLM in flight (hothouse_sources.py:566-571)
- `activity_header` — 200ms inverse-flash on activity flip (legibility_sources.py:122-125)

### 4.3 Reactive (transitions tied to data updates, not periodic)

- `album` — Track-change triggers cover refresh + brief emphasis
- `stance_indicator` flash on stance change (legibility_sources.py:122)
- `recruitment_candidate_panel` — Ticker-scroll-in entry on newest cell (hothouse_sources.py:430-432)
- `whos_here` — Viewer-count change → label refresh
- `stream_overlay` — Polling at 2Hz; visible change only on chat/preset/viewer transition
- `token_pole` — Path traversal AND cranium-arrival explosion event (token_pole.py:60-77, 121)

### 4.4 Operator-tools (visible only when operator-mode demands)

- `recruitment_candidate_panel` (when in `Repair` programme or `hothouse` tag domain)
- `activity_variety_log` (when operator is debugging affordance flow)

---

## §5 Per-Ward Scrim-Behavior Table

Five behavioral dimensions per ward. Default is "behind-scrim" treatment per scrim doc §5.2 unless the ward's depth band is "surface."

| Ward | Permeability | Transit-frequency | Trap-tolerance | Echo-tendency | Wake-strength |
|---|---|---|---|---|---|
| `token_pole` | Medium-low (avatar face glows through) | High at cranium-explosion events; low otherwise | Never trapped (always punches through during emphasis) | Strong — explosion particles leave 0.6s phantom | Strong — particle plume |
| `album` | Medium (fabric softens cover edges) | Once per track-change | Trappable (during interlude programmes) | Mild — cover-quantize dither persists ~2 frames | Weak |
| `stream_overlay` | Zero (surface inscription, no distortion) | Never transits | Never trapped | None | None |
| `sierpinski` | High (deepest, most distorted) | Never transits | Trappable | Strong — `glfeedback` accumulates (sierpinski_renderer.py:3-6) | Weak |
| `activity_header` | Zero (surface) | Never transits | Never trapped | 200ms inverse-flash residue | None |
| `stance_indicator` | Zero (surface) | Never transits | Never trapped | Pulse continuous; no discrete echo | None |
| `impingement_cascade` | Medium (near-surface) | High — rows transit on join-message | Trappable in calm programmes | Strong — ghost trail per row (hothouse_sources.py:281-284) | Mild |
| `recruitment_candidate_panel` | Medium | Per recruitment event | Trappable (ops-only tier) | Mild ticker-scroll trail | None |
| `thinking_indicator` | Medium | Continuous breathing while in-flight | Never trapped (must be visible on direct address) | None | None |
| `pressure_gauge` | Medium | Per-cell at stance-Hz | Trappable in `Wind-down` programme | Cell-bleed at saturation | None |
| `activity_variety_log` | Medium-high (overheard) | Per ticker step | Trappable | Mild scroll trail | None |
| `whos_here` | Zero (surface) | Per viewer-count change | Never trapped (audience framing must read) | None | None |
| `hardm_dot_matrix` | **Per-cell variable** (see §9) | Per-cell ripple at family recruitment | Per-cell trappable (with cells acting independently) | Per-cell ripple wavefront 0.4s (hardm_source.py:70) | Strong on multi-cell ripple cascades |

**Definitions:**

- **Permeability** — How much the scrim distorts the ward when it sits behind. `Zero` = surface, no distortion. `High` = beyond-scrim, full atmospheric tint + blur + contrast reduction (scrim doc §4).
- **Transit-frequency** — How often the ward moves through the Z-axis (front↔back). "Never" wards stay pinned at one depth.
- **Trap-tolerance** — Whether a programme-level state can pin the ward INSIDE the scrim's weave (visible only as an impression). Must not trap wards whose informational role is to be *read* (chrome, audience framing, direct-address surfaces).
- **Echo-tendency** — Does the ward leave delayed phantom copies? `glfeedback` accumulation on the sierpinski + scrim layer makes ward exits leave cloth-like wake; some wards need explicit echo behavior on top of that.
- **Wake-strength** — When the ward exits, how much disturbance does it leave on the scrim? Hero-presence wards leave strong wake (the fabric "remembers" the avatar passing).

---

## §6 Per-Ward Audio Coupling

The fourth dispatch in this set ("choreographer/audio-coupled motion") covers the MIDI-clock infrastructure. This section binds each ward to a specific audio coupling.

| Ward | Audio coupling |
|---|---|
| `token_pole` | Spend events (token-ledger writes) → cranium-explosion emphasis. **No NEW scrim coupling beyond default** — the existing emphasis event IS the audio-visual hinge. Future: token traversal speed could rate-couple to `tendency.beat_position_rate` (already in `shared/perceptual_field.py`). |
| `album` | Track-change → `scrim-front transit` (becomes momentarily MEDIUM-DEEP for emphasis, then settles back to deep). Per ca0e955cc the album panel is decoupled from `vinyl_playing` for the visibility gate, but the *emphasis transit* should still respect `audio.midi.transport_state == "PLAYING"` so a stationary cover doesn't transit. |
| `stream_overlay` | Chat-keyword bursts (per `chat_reactor.py`) → moiré density spike on the scrim around the ward (technique #3 from scrim doc §3 table). Existing `chat-state.json` polling at 2Hz suffices as the source. |
| `sierpinski` | Audio energy via `set_audio_energy()` (sierpinski_renderer.py:11-12). Existing coupling: drives waveform centre-void intensity. **Scrim addition:** glfeedback fade-rate modulates inversely with audio energy — louder audio → tighter feedback (less smear). |
| `reverie` | Already audio-coupled via stimmung dimensions. Scrim role is structural — Reverie IS the scrim. |
| `activity_header` | None directly. Coupled through stimmung (activity flip → flash). |
| `stance_indicator` | Stance-Hz from `stance_hz(stance)` (hothouse_sources.py:51-57); stance is downstream of stimmung which is downstream of audio + IR + chat. Indirect. |
| `impingement_cascade` | None directly. Coupled through perception state. |
| `recruitment_candidate_panel` | None directly. |
| `thinking_indicator` | Stance-Hz breathing while LLM in flight; secondary effect of audio via stance. |
| `pressure_gauge` | **Operator-attention-coupled** — when operator-attention is high (per IR `ir_screen_looking` + contact-mic activity), scrim *parts* around the gauge (small radius, ~150px) so the gauge is fully crisp. When attention is elsewhere, gauge sits at default near-surface treatment. |
| `activity_variety_log` | None directly. |
| `whos_here` | None directly. |
| `hardm_dot_matrix` | **Per-cell signal coupling** — 256 cells driven by per-cell signal map (hardm_source.py:14-15). Scrim density modulates HARDM cell brightness uniformly: deeper scrim = dimmer cells (preserving the dot-matrix character but letting the avatar "fade behind cloth"). MIDI clock pulse at beat positions → row 11 (`stimmung_energy` per hardm_source.py:104) ripple. |

---

## §7 Compositional Rules Across All Wards

System-wide invariants that no single ward owns but the scrim system must enforce.

### 7.1 Cap on simultaneous EMPHASIZED state — max 2

Two wards can be in EMPHASIZED state simultaneously. More than two = visual chaos and defeats the spatial-attention purpose. Enforcement lives in the structural director (`agents/studio_compositor/structural_director.py`). When a third ward requests emphasis, the structural director must evict the oldest EMPHASIZED ward back to its default depth.

### 7.2 Z-axis collision avoidance

No two wards can occupy the same Z-position simultaneously, OR if they do, an explicit `refraction interaction` shader pass must be configured for the pair. Default policy: no overlap. The current `default.json` uses distinct z_order values per surface (10, 24, 26, 28, 30, 35) so no collisions exist today. Phase 2 must extend this to scrim-depth values, not just surface z_order.

### 7.3 Ward-family clustering — coordinate the data-substrate pair

`hardm_dot_matrix` and `impingement_cascade` are both data-substrate wards (HARDM = real-time signals, cascade = recent perceptual impingements). They show similar information at different temporal granularities. **Coordinate them:**

- When `impingement_cascade` shows a high-salience signal (>0.85), the corresponding HARDM cell should ripple in sync.
- The mapping already exists in spirit via `RECRUITMENT_FAMILY_TO_ROW` (hardm_source.py:101-109) — extend it to a perception-signal → HARDM-cell map.
- Coordinate visual rhythm: both wards should breathe at `stance_hz(stance)`.

### 7.4 Minimum-visible-count rule

To avoid an "empty broadcast" feeling, **at least 5 wards must always be visible** at any moment. Below this count, the structural director resurrects the next-highest-priority ward (whichever currently-hidden ward has the highest pending salience). This prevents a `Wind-down` programme from collapsing the visible field below the minimum legibility threshold.

### 7.5 Surface-depth wards never trap

Wards at the `Surface` depth band (stream_overlay, activity_header, stance_indicator, whos_here) MUST NOT be subject to scrim trap behavior. Their informational role is to be *read* — trapping them is a correctness bug, not a creative choice.

---

## §8 Operator Override Per Ward

Each ward gets three override states: `force-show`, `force-hide`, `pin-to-depth(d)`. The operator pins via Stream Deck or programme-mode preset.

### 8.1 Stream Deck button mapping (proposed)

| Button | Action |
|---|---|
| 1 | Toggle `token_pole` force-show |
| 2 | Toggle `album` emphasis transit |
| 3 | Toggle `hardm_dot_matrix` force-emphasis |
| 4 | Pin `pressure_gauge` to surface |
| 5 | Hide all near-surface (cascade, recruitment, log) — calm mode |
| 6 | Programme-mode select (cycles A/B/C/D from §11) |
| 7 | Scrim-pierce trigger (`scrim.pierce` intent per scrim doc §8.3) |
| 8 | Reset all overrides to programme defaults |

These buttons inject through the command registry — `window.__logos.execute("ward.<id>.<action>", { ... })` per the council CLAUDE.md "Command Registry" section. New commands must be registered in `hapax-logos/src/lib/commands/` and exposed via `commandRegistry.ts`.

### 8.2 Programme-mode preset overrides

Programme metadata (per `shared/programme.py`) can declare ward overrides:

```python
programme.ward_overrides = {
    "pressure_gauge": "always_emphasized",
    "impingement_cascade": "force_hidden",
    "token_pole": "pin_depth=hero",
}
```

The structural director consumes these on programme transition. Since programmes are *soft priors* (memory: `project_programmes_enable_grounding`), any operator override during a programme is honored above the programme's default; the programme's overrides only take effect when no operator override is active.

---

## §9 HARDM Cells — Special Case (16×16 = 256 sub-wards)

HARDM is qualitatively different from every other ward because each of its 256 cells has independent state (hardm_source.py:117). The scrim treatment must address per-cell behavior.

### 9.1 Independent vs. unit transit

**Decision: HYBRID — cells move independently in normal play, transit as a UNIT on stress events.**

- **Normal play:** Each cell moves through the scrim independently. The 8-neighbour ripple system (hardm_source.py:71-81) already creates wavefronts that propagate across cells; under scrim treatment these wavefronts also propagate through depth (a ripple's leading edge is slightly deeper than its trailing edge).
- **Stress events** (e.g. `accent_red` cells indicating overflow/staleness per hardm_source.py:9-10): ALL cells transit together to forward depth. The whole 16×16 grid punches through the scrim as a unit during stress, signaling "Hapax is in alarm state" without face-iconography.

### 9.2 Refraction on a 16×16 grid — visually compelling vs visually busy

A naive per-cell refraction would be busy. Two mitigations:

1. **Coarsen the refraction grid to 4×4** — the scrim's refraction sample texture is 4×4, so each refraction sample covers a 4×4 cell block. This produces large-scale shimmer instead of per-cell jitter.
2. **Refraction amplitude scaled by mean cell brightness** — when most cells are idle (`muted` palette role), refraction is near-zero (the avatar is calm). When activity is high, refraction grows. The scrim breathes WITH the avatar.

Counter-position: a *fully* per-cell refraction could be aesthetically excellent at the cost of GPU budget; the recommendation is to ship coarsened-4x4 first and validate visually before considering per-cell.

### 9.3 Anti-anthropomorphization invariant — HARDM-specific

The 16×16 grid MUST NEVER resolve into face-like clusters. Per `docs/research/hardm-communicative-anchoring.md` and the workspace memory `project_hardm_anti_anthropomorphization`. Specific scrim violations to refuse:

- No per-cell ripple pattern that produces two symmetric "eye" clusters at rows 4-6 + a "mouth" cluster at rows 10-12.
- No depth modulation that protrudes the centre 8×8 forward (face-bulge effect).
- No refraction halo that produces a "head" silhouette around the grid edges.

Test gate: a property-based hypothesis test in `tests/studio_compositor/test_hardm_scrim.py` should reject configurations whose visual moments-of-inertia approximate facial proportions (Pearson correlation > 0.6 with a face-cluster mask).

---

## §10 Removed Wards — Should Any Return?

Three wards were removed from default.json since 2026-04-19. Per the dispatch brief, this section judges whether their right return path is "do nothing", "return at deep+slow", or "redesign first."

### 10.1 `captions` (removed d69039159)

- **Removal reason** (per d69039159 commit msg): "A 3-day-old 'yeah' had been pinned on broadcast because /dev/shm/hapax-daimonion/stt-recent.txt contained a stale STT line ... CaptionsCairoSource has no staleness gate — last non-empty line renders forever."
- **Decision: Redesign first.** A real-time STT widget is valuable, but only with: (1) staleness gate (e.g. 8s TTL with fade-out); (2) producer-restart resilience; (3) scrim-depth = surface (captions must read clearly). Before any return: fix the producer (`hapax-daimonion` STT writer) to be the first contract — caption ward consumes a freshness-tagged feed.
- **Return scrim-depth:** Surface. Captions are inscribed information — they cannot be trapped inside the scrim.

### 10.2 `grounding_provenance_ticker` (removed b60704c88)

- **Removal reason**: "the ward exposes raw signal-path strings the LLM director cited (context.recent_reactions, album.title, etc.) as 'grounding provenance'. Internal debugging surface, not viewer-meaningful."
- **Decision: Return at DEEP+SUBTLE, but redesigned.** The provenance signal IS valuable to the audience IF it's translated from internal jargon into viewer-meaningful glyphs. Proposal: replace path strings with small Px437 icons indicating WHICH SOURCE FAMILY informed the current director decision (camera.hero / preset.bias / overlay.emphasis / etc., reusing the family-role mapping at hothouse_sources.py:227-250).
- **Return scrim-depth:** Beyond-scrim (deep) — the provenance signals what's behind the curtain, literally. Audience perceives them as faint glyph-shadows rather than crisp inscriptions.

### 10.3 `chat_ambient` (removed b60704c88)

- **Removal reason**: "totally indecipherable ... narrow 160x400 vertical strip on the right edge with grid-pattern raster + chat keyword color blocks. Compressed format unreadable on broadcast."
- **Decision: Return at SURFACE in a more interpretable form.** The ChatAmbientWard design is sound (chat_ambient_ward.py:1-37) — aggregate-only, no individual messages, redaction-invariant. The problem is purely the visual — the 160×400 strip was too compressed. Return at a wider surface footprint (e.g. 800×60 mid-bottom) and use the full BitchX grammar (`[Users(#hapax:1/N)] [Mode +v +H] [gauge ░▒▓█] [active]`) at readable type sizes.
- **Return scrim-depth:** Surface. Chat ambient telemetry must read clearly on broadcast — the audience IS the chat.

---

## §11 Per-Ward Programme Integration

Programmes are *soft priors* per `shared/programme.py:9-13` — they EXPAND grounding opportunities, never hard-gate. Each ward gets a default programme behavior; programmes can override but never delete.

### 11.1 Programme A — `Selector` mode (operator picking material, foundation visible)

| Ward | Override |
|---|---|
| `token_pole` | Pin to MEDIUM-DEEP (token visible but not active) |
| `album` | Pin to MEDIUM-DEEP (current track readable) |
| `pressure_gauge` | Default near-surface |
| `stream_overlay` | Default surface |
| All others | Default |

### 11.2 Programme B — `Hothouse` mode (deep work, pressure surfaces)

| Ward | Override |
|---|---|
| `pressure_gauge` | Always EMPHASIZED |
| `impingement_cascade` | Always emphasized |
| `recruitment_candidate_panel` | Force-shown |
| `activity_variety_log` | Force-shown |
| `album`, `sierpinski` | Trapped (deep, dim) |

### 11.3 Programme C — `Vinyl Showcase` (turntable focus)

| Ward | Override |
|---|---|
| `album` | EMPHASIZED — comes forward to MEDIUM-SHALLOW briefly per track |
| `vinyl_platter` (opt-in) | Force-shown via `vinyl-focus.json` layout |
| Hothouse wards | Trapped (calm scene) |
| `token_pole` | Default hero-presence |

### 11.4 Programme D — `Granular-wash` mode (Mode D vinyl, per `agents/hapax_daimonion/vinyl_chain.py`)

| Ward | Override |
|---|---|
| **All wards** | TRAPPED (deepest scrim treatment, near-invisible) — Mode D is total wash |
| `hardm_dot_matrix` | Per-cell stress activation (RD field maxed) |
| `reverie` | Granular-modulation parameters peak |

### 11.5 Programme E — `Wind-down` (stream ending)

Per scrim doc §7 table: wards fade one-by-one until only `reverie` (the scrim itself) remains. Override sequence:

1. T-60s: All near-surface wards trap (cascade, recruitment, log)
2. T-30s: All surface wards begin breath-fade
3. T-10s: Hero-presence wards transit deep then dissolve
4. T-0s: Only `reverie` visible

### 11.6 Per-ward programme defaults table (when no programme is active)

| Ward | Default depth | Default emphasis |
|---|---|---|
| token_pole | hero-presence | high (cranium events) |
| album | beyond-scrim (deep) | medium (track changes) |
| stream_overlay | surface | low (pulse on chat surge) |
| sierpinski | beyond-scrim | low |
| activity_header | surface | medium (flash on flip) |
| stance_indicator | surface | medium (continuous pulse) |
| impingement_cascade | near-surface | medium (per-row) |
| recruitment_candidate_panel | near-surface | low |
| thinking_indicator | near-surface | high while in flight |
| pressure_gauge | near-surface | medium (operator-attention coupled) |
| activity_variety_log | near-surface | low |
| whos_here | surface | low |
| hardm_dot_matrix | hero-presence (straddle) | per-cell variable |

---

## §12 Phased Ship Plan

### 12.1 Phase 1 — Proof-of-concept on 3 wards

Target: ship scrim-permeability uniform plumbing for 3 wards spanning the full depth range.

**Wards:** `token_pole`, `album`, `stream_overlay` (justification in §1 TL;DR).

**Deliverables:**

1. Add `scrim_depth` field to `Source` model in `shared/compositor_model.py` — accepted values: `"surface" | "near_surface" | "hero_presence" | "beyond_scrim" | "scrim"`.
2. Add `scrim_depth` declarations in `default.json` for the three target wards.
3. Reverie WGSL: add per-source `scrim_depth` uniform and apply differential blur/atmospheric-tint/contrast-reduction in the `color` pass per scrim doc §4.
4. Verify visually on livestream — operator approval gates Phase 2.

**Estimated PRs:** 3 (model + JSON + shader).

### 12.2 Phase 2 — Extend to all 13 wards

**Deliverables:**

1. Apply `scrim_depth` declarations to all wards in `default.json` per §3 assignments.
2. Verify each ward's depth treatment matches the §3 reasoning. Visual regression goldens for each (build on existing CI in `tests/studio_compositor/`).
3. HARDM gets the §9 hybrid treatment (per-cell normal, unit-transit on stress). HARDM-specific tests in `tests/studio_compositor/test_hardm_scrim.py`.

**Estimated PRs:** 6 (one per depth band + HARDM-special + HARDM-anti-anthropomorphization test).

### 12.3 Phase 3 — Cross-ward coordination protocols

**Deliverables:**

1. Implement §7.1 EMPHASIZED-cap (max 2) in `agents/studio_compositor/structural_director.py`.
2. Implement §7.4 minimum-visible-count rule.
3. Implement §7.3 HARDM-cascade coordination (perception-signal → HARDM-cell map).
4. Operator-override commands registered via command registry (per §8).

**Estimated PRs:** 4.

### 12.4 Phase 4 — Programme integration

**Deliverables:**

1. Programme model gains `ward_overrides: dict[str, str]` field per §8.2.
2. Programmes A/B/C/D/E (§11) authored as default scrim-aware programmes.
3. Vinyl Mode D ↔ scrim Programme D wiring.
4. Programme-transition handler for ward state migration.

**Estimated PRs:** 5.

### 12.5 Phase 5 — Returned wards (post-Phase-4, optional)

If operator approves: re-introduce `chat_ambient` (surface, redesigned wider footprint) and `grounding_provenance_ticker` (deep, glyph-translated). Captions deferred until producer fixed.

---

## §13 Anti-Anthropomorphization Invariants Per Ward

Per memory `project_hardm_anti_anthropomorphization` and `docs/research/hardm-communicative-anchoring.md`. For each ward, document what would VIOLATE the invariant in scrim-play:

| Ward | What would violate the invariant |
|---|---|
| `token_pole` | Path that suggests a body-silhouette traversal beyond the existing Vitruvian outline (e.g. token bouncing along the figure's arms in a "wave hello" motion); particle explosion that resolves into a face shape; cranium-arrival animation where particles cluster as eyes/mouth |
| `album` | Cover image getting a "fish-tail wiggle" or organic body-motion during transit; cover edges becoming face-like under refraction |
| `hardm_dot_matrix` | Per-cell pattern that resolves into face-cluster (two eye-blobs at rows 4-6, mouth-cluster at rows 10-12); depth modulation that protrudes the centre as a "face bulge"; refraction halo that produces head-silhouette outline; ANY clustering that registers Pearson > 0.6 with a face-mask test (per §9.3) |
| `stream_overlay` | Status text rendered with "winking" or "blinking" animation on viewer-count increment |
| `sierpinski` | YouTube-frame masks resolving into a "smiling triangle" or any face-glyph appearing in the corner regions |
| `reverie` | Substrate texture forming face-like clusters during high-coherence moments (this is hard to constrain procedurally — falls to operator visual review) |
| `activity_header` | Activity gloss rendered in font weights that suggest "speech bubble" (e.g. tail-on-bottom) |
| `stance_indicator` | The `+H` chip becoming an emoji/emoticon |
| `impingement_cascade` | Row-bar visualization that resolves into eye/eyebrow shapes when stacked |
| `recruitment_candidate_panel` | Cell labels using emoji as accent markers |
| `thinking_indicator` | The `[thinking...]` label becoming `🤔` or any face-emoji |
| `pressure_gauge` | Cell-state colors arranged to suggest "frowning" or "smiling" gradient pattern |
| `activity_variety_log` | Ticker entries using face-emoji prefixes |
| `whos_here` | `[hapax:1/N]` becoming a hand-wave emoji or any anthropomorphic glyph |

**Enforcement:** A property-based hypothesis test (`tests/studio_compositor/test_anti_anthropomorphization.py`) should iterate over each ward's render output (cairo surface as numpy array), detect face-like clusters using a simple face-template correlation, and reject configurations that exceed threshold. Run on every PR that touches `agents/studio_compositor/`.

---

## §14 Open Questions

1. **Sierpinski default-layout reinstatement.** Sierpinski is registered but unassigned in default.json. Should the scrim system promote it to a default beyond-scrim element (e.g. occupying a fifth surface, perhaps `pip-center` at full canvas with very low opacity)? The operator removed it implicitly when default.json was last reorganized; reinstating requires operator decision.

2. **Programme-transition timing for ward depth migration.** When transitioning from Programme A → B, do wards crossfade their depth over 2s, snap instantly, or follow per-ward easing curves? Recommendation: per-ward easing (so hero-presence wards transit slower than near-surface wards, matching their different motion personalities), but the choreographer needs explicit specification.

3. **HARDM stress-event threshold.** §9.1 specifies "all cells transit together on stress." What counts as a stress event? Proposal: when ≥40% of cells are in `accent_red` simultaneously, trigger unit transit. Needs validation on real signal data.

4. **Operator-attention-coupled `pressure_gauge` parting.** §6 specifies the scrim parts around the gauge when operator-attention is high. What's the radius? What's the falloff curve? Default proposal: 150px radius, raised-cosine falloff over 75px. Needs visual review.

5. **Returned wards' default depth on reintroduction.** §10 proposes specific depths but the operator may want different defaults. Confirm before Phase 5.

6. **Vinyl-platter ward (registered, opt-in only).** Per `vinyl-focus.json` example layout. Where does it sit in the scrim model when used? Proposal: hero-presence (it IS the operator's focus during vinyl shows), but this conflicts with hero-presence already being claimed by `token_pole` + `hardm_dot_matrix`. Need clarification on the §7.1 max-2-EMPHASIZED rule.

7. **Reverie's role as "the scrim itself" vs the camera PiPs being "the things behind the scrim."** Currently `reverie` is a single source feeding `pip-ur`. If reverie is the scrim substrate, it shouldn't be confined to the upper-right quadrant — it should fill the entire frame as the baseline. This is a much larger architectural change that the scrim doc §5.5 hints at but doesn't fully specify. May warrant its own dispatch.

---

## §15 Sources

### Hapax codebase (file:line cites)

1. `config/compositor-layouts/default.json:4-610` — full layout JSON
2. `agents/studio_compositor/cairo_sources/__init__.py:71-160` — class registry
3. `agents/studio_compositor/token_pole.py:1-117` — TokenPoleCairoSource definition + path mode + palette
4. `agents/studio_compositor/album_overlay.py:1-100` — AlbumOverlayCairoSource definition + mIRC-16 quantize
5. `agents/studio_compositor/stream_overlay.py:1-100` — StreamOverlayCairoSource definition + grammar
6. `agents/studio_compositor/sierpinski_renderer.py:1-80` — SierpinskiCairoSource + GdkPixbuf guard
7. `agents/studio_compositor/hardm_source.py:1-119` — HARDM grid geometry + decay envelope + RD underlay
8. `agents/studio_compositor/hothouse_sources.py:1-200` — Phase A2 emissive rewrite + perception readers
9. `agents/studio_compositor/hothouse_sources.py:271-560` — Cascade, RecruitmentCandidatePanel, ThinkingIndicator definitions
10. `agents/studio_compositor/legibility_sources.py:1-220` — ActivityHeader, StanceIndicator, GroundingProvenanceTicker, ChatKeywordLegend
11. `agents/studio_compositor/chat_ambient_ward.py:1-100` — ChatAmbientWard redaction-invariant design
12. `agents/studio_compositor/captions_source.py:1-80` — CaptionsCairoSource + per-mode styles
13. `agents/studio_compositor/homage/substrate_source.py:53-69` — `SUBSTRATE_SOURCE_REGISTRY` (album+reverie)
14. `agents/studio_compositor/homage/__init__.py` — `get_active_package()` (HomagePackage resolver)
15. `agents/studio_compositor/homage/emissive_base.py` — emissive primitives (paint_emissive_point, paint_emissive_glyph, paint_scanlines, stance_hz, STANCE_HZ table, BREATHING_AMPLITUDE)
16. `shared/programme.py:1-80` — Programme primitive + soft-priors axiom
17. `shared/governance/monetization_safety.py` — MonetizationRiskGate
18. `shared/compositor_model.py` — Source/Surface/Assignment/Layout Pydantic models
19. `agents/studio_compositor/cairo_source.py` — CairoSource protocol + CairoSourceRunner
20. `agents/studio_compositor/structural_director.py` — director loop (consumer of programme overrides)

### Hapax research and governance docs

21. `docs/research/2026-04-20-nebulous-scrim-design.md` — scrim core design (§6 ward depth bands)
22. `docs/superpowers/specs/2026-04-18-homage-framework-design.md` — HOMAGE framework spec (§4.4 palette role names; §5.5 anti-rounded-corners)
23. `docs/superpowers/specs/2026-04-18-hardm-dot-matrix-design.md` — HARDM spec
24. `docs/research/2026-04-19-hardm-redesign.md` — HARDM redesign rationale
25. `docs/research/2026-04-20-hardm-aesthetic-rehab.md` — HARDM aesthetic rework (CP437 block chars)
26. `docs/research/hardm-communicative-anchoring.md` — anti-anthropomorphization governance
27. `docs/research/2026-04-19-content-programming-layer-design.md` — Programme primitive design
28. `docs/superpowers/plans/2026-04-20-programme-layer-plan.md` — Programme implementation plan
29. `docs/governance/monetization-risk-classification.md` — MonetizationRiskGate classification
30. `docs/research/2026-04-20-vinyl-broadcast-mode-d-granular-instrument.md` — Vinyl Mode D (Programme D)
31. `docs/research/2026-04-20-vinyl-broadcast-programme-splattribution.md` — Splattribution programme
32. Workspace memory: `project_hardm_anti_anthropomorphization`
33. Workspace memory: `reference_wards_taxonomy`
34. Workspace memory: `project_programmes_enable_grounding`
35. Workspace memory: `feedback_no_expert_system_rules`
36. Workspace memory: `feedback_hapax_authors_programmes`

### External / theoretical (compositional theory)

37. Edward T. Hall, *The Hidden Dimension* (1966) — proxemic depth bands inform "near-surface vs surface vs hero-presence"
38. Charles H. Stewart, *How to Light a Scrim* (https://charleshstewart.com/blog/how-to-light-a-scrim/) — differential lighting for foreground/background as "permeability"
39. Theatrecrafts, *Lighting with a Gauze / Scrim* (https://theatrecrafts.com/pages/home/topics/lighting/lighting-gauze-scrim/) — scrim opacity as light-differential
40. Saul Leiter's photographic practice — atmospheric subject (per scrim doc §2.3) informs "obscuring as content"
41. James Turrell, *Ganzfeld* installations — evacuated depth informs "scrim as evacuated depth" (per scrim doc §2.4)
42. Mark Rothko, late Seagram canvases — color-field substrate informs depth-band breathing
43. Hiroshi Sugimoto, *Theaters* series — duration collapsed onto surface informs the slow-drifter motion class
44. Vittorio Storaro, *Apocalypse Now* (1979) — colored smoke as substrate informs scrim-as-substrate, not scrim-as-skin
45. CRT scan-line phosphor moiré — informs `stream_overlay` chat-surge moiré coupling (§6)
46. Stan Brakhage, *Mothlight* (1963) — applied-fabric substrate informs trap-tolerance behavior

### Recent commits referenced

47. d69039159 — captions ward removal commit
48. b60704c88 — grounding_provenance_ticker + chat_ambient removal commit
49. ca0e955cc — album cover unconditional render fix
50. 6afcde7bb — token-pole CRANIUM_Y fix + album substrate registration

---

**Doc length:** ~16k chars; ~50 distinct citations across Hapax codebase, internal research, governance, and external compositional theory.
