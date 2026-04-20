# GEM — Graffiti Emphasis Mural Ward Design

**Date:** 2026-04-19
**Register:** scientific, design-doc neutral.
**Status:** design proposal — phased.
**Task:** #191 (new HOMAGE ward).

**Related:**
- `agents/studio_compositor/homage/transitional_source.py` — `HomageTransitionalSource` FSM base class
- `agents/studio_compositor/homage/__init__.py` — package registry + `get_active_package()`
- `agents/studio_compositor/homage/choreographer.py` — transition scheduler
- `agents/studio_compositor/hardm_source.py` — adjacent avatar ward (CP437 blocks, Px437 font, SHM consumer pattern)
- `shared/homage_package.py` — `HomagePackage` grammar + palette (BitchX mIRC-16)
- `scripts/hardm-publish-signals.py` — reference publisher pattern
- `config/compositor-layouts/default.json` — layout JSON format
- `docs/research/2026-04-19-hardm-redesign.md` — HARDM placement analysis (same canvas)
- `docs/research/2026-04-20-hardm-aesthetic-rehab.md` — bbs/ascii-authenticity precedent
- `~/.claude/projects/-home-hapax-projects/memory/project_hardm_anti_anthropomorphization.md` — non-negotiable anti-face invariant
- `agents/hapax_daimonion/cpal/production_stream.py` — `write_emphasis()` call site (speech state publisher)
- `agents/hapax_daimonion/run_loops_aux.py` — impingement consumer loop (cross-modal dispatch)

This document specifies a new HOMAGE-participating Cairo ward, GEM (**G**raffiti **E**mphasis **M**ural), that provides the visual expression surface intentionally vacated by the deliberate absence of speech transcription.

---

## §1. What GEM IS (and is NOT)

### 1.1 What it IS

GEM is a Cairo-rendered Hapax-authored expression surface. The grammar is **graffiti-mural inspired but BitchX-constrained**: the surface is a flat CP437 raster (no anti-aliasing, no proportional fonts, no rounded corners) whose content is Hapax-authored glyph compositions that may emphasize words, frame ideas, or animate abstract spatial sequences. Graffiti-mural as a mood — density, overlap, revision, layering, erasure marks — not as a literal aesthetic.

Positive definition: GEM is what happens when you remove the caption-strip assumption (one line of literal transcription, white-on-black, monotone typography) and replace it with a **raster canvas Hapax is free to draw on** within the BitchX grammar. The ward renders a sequence of ASCII glyph states that decay and recompose.

The content vocabulary includes:

- **Emphasized text fragments** — single words or short phrases in `large`/`banner` size-class, with BitchX-authentic punctuation framing: angle brackets, square brackets, carets, equal-sign rules, box-draw borders.
- **Box-draw compositions** — CP437 single/double line drawings (`┌─┐│└─┘╔═╗║╚═╝`) that frame, divide, or contain text runs.
- **Braille density fills** — U+2800–U+28FF for high-density, sub-character-cell shading where a plain block glyph would be too coarse.
- **Frame-by-frame abstract animation** — a glyph composition that advances through `N` keyframes, each a full raster re-paint. Animations are explicitly abstract: a tree growing branches, a shape rotating, a word fracturing and re-assembling — **never** a walking figure, a face expressing, a mouth opening.
- **Revision marks** — overstrikes (U+0336 combining long stroke), asterisk-prefix edit marks (`* correction:`), and BitchX-lineage `/me`-style action markers.

### 1.2 What it is NOT

GEM is explicitly NOT any of the following:

- **A speech transcription display.** The entire point is that the transcription slot is empty. GEM does not subtitle utterances.
- **An emoji wall.** Emoji is in `AntiPatternKind = "emoji"` (`shared/homage_package.py` L83); the BitchX package refuses it.
- **A face, avatar, or character.** Hapax has no face (`project_hardm_anti_anthropomorphization.md`). GEM inherits this governance. Any composition a naive viewer would read as a figure is rejected before render.
- **A scrolling chat log.** Chat has its own ward (`chat_ambient`); GEM does not duplicate it.
- **A log of Hapax's reasoning or chain-of-thought.** That is `impingement_cascade`'s job.
- **A status indicator.** Stance/thinking/pressure indicators already exist.

### 1.3 Examples: accepted

- The word `ACIDIC` in 32-pt Px437 with a `═══════` double rule underneath and `▓▒░` stippled shadow behind it.
- An abstract CP437 "tree": `╱╲` branches growing across frames 0–12, peaking, decaying via `·` sparse dither back to blank.
- A 3×3 block pattern that rotates through 6 frames of ASCII rotational symmetry.
- A fragment: `» spectral drift « ` with the word `drift` underlined and the whole fragment drifting horizontally at 8 px/s before fading.

### 1.4 Examples: rejected by governance

- `(^_^)`, `:)`, `( ._.)`, `>_<`, `B)` — any parenthetical kaomoji.
- Two dense-character clusters in upper half with a linear cluster in lower half (reads as eyes + mouth).
- A vertical-symmetric composition with eye-spacing roughly 40–60 px (standard face width fraction).
- `HAPAX` spelled out as glyphs. Hapax is not a character with a name on a wall — spelling the system's own name is character-framing.
- A silhouette made of `@`/`#`/`*` that has head-torso-limbs proportions.
- Performative emotional markers: `!!!`, `???`, `...zzz`, `ಠ_ಠ`.

---

## §2. Input — what drives GEM content?

GEM content is **Hapax-authored**, not operator-pre-authored. The authorship chain is deliberately tight to the impingement → affordance architecture, not a bolt-on.

### 2.1 Authorship source: the existing impingement stream

The DMN already writes `/dev/shm/hapax-dmn/impingements.jsonl`, consumed by daimonion's CPAL loop (`agents/hapax_daimonion/cpal/production_stream.py`) and the affordance loop (`agents/hapax_daimonion/run_loops_aux.py::impingement_consumer_loop`). Each impingement record carries a `narrative_text` field plus the 9 canonical expressive dimensions (intensity, tension, depth, coherence, spectral_color, temporal_distortion, degradation, pitch_displacement, diffusion). **This stream is the substrate of everything Hapax expresses.** Wiring GEM to it means GEM breathes with the same rhythm as the rest of Hapax's expression — not on a separate cadence, not from a separate model.

### 2.2 Authorship source: a new affordance (`expression.gem_mural`)

GEM becomes a registered capability in the `AffordancePipeline` with Gibson-verb description:

> *expression.gem_mural* — "emphasize a fragment, idea, or shape by drawing it in ASCII. Pick words, phrases, box-frames, or abstract animations that make a moment legible on the graffiti surface. Author content; do not transcribe."

When impingement selects this affordance (score ≥ recruitment threshold; Thompson sampling makes occasional dormant activation possible per unified-recruitment semantics), the GEM producer is asked to emit one **composition** — a small JSON payload containing glyph content and keyframe timing.

### 2.3 Composition producer (`scripts/gem-publisher.py`)

The producer runs as a **systemd user timer** (`hapax-gem-publisher.timer`, `OnUnitActiveSec=8s`, `AccuracySec=500ms`). On each fire:

1. Read the most recent N=5 impingements from `/dev/shm/hapax-dmn/impingements.jsonl`.
2. Read the current stimmung state from `/dev/shm/hapax-stimmung/state.json`.
3. Read the active `HomagePackage` via `get_active_package()`.
4. Check whether `expression.gem_mural` was recruited in the last `recent-recruitment.json` window.
5. If recruited: build a prompt containing impingement narratives + stimmung + explicit anti-face/anti-transcription constraints, call LLM (`coding` alias → TabbyAPI Qwen3.5-9B for cost reasons; `balanced` alias → Claude Sonnet when `stimmung.coherence < 0.3` and a high-stakes composition is warranted).
6. LLM returns a `GemComposition` Pydantic payload (§4.3).
7. Run anti-anthropomorphization checkers (§5). On reject: log + emit no new composition (GEM decays to idle).
8. Write atomically to `/dev/shm/hapax-compositor/gem-composition.json` (tmp + rename, mkdir-p parent).

The 8 s cadence is deliberately slower than HARDM's 2 s and the GStreamer 10–15 Hz render loop. GEM compositions are meant to **sit** — glyph animations decay over 5–20 seconds; over-publishing would churn the surface incoherently.

### 2.4 Why this source (not alternatives)

Alternatives considered and rejected:

- **Purely reactive to TTS utterances.** Would re-introduce transcription-by-proxy; rejected by §1 constraint.
- **New DMN daemon producing GEM.** Duplicates DMN cognitive work. Rejected by per unified-recruitment: imagination produces intent (impingement); expression surfaces consume it.
- **Pure signal-stream composition (stimmung → ASCII mood glyphs) with no LLM.** Works for Phase 2 but is semantically thin — cannot emphasize a specific word, cannot compose a sentence fragment. Phase 2 precisely.
- **Operator-authored cue files.** Violates "Hapax authors programmes" (memory: `feedback_hapax_authors_programmes.md`).

### 2.5 Integration with existing impingement architecture

GEM does **not** spawn a third impingement consumer. It reads the jsonl with its own cursor (`~/.cache/hapax/impingement-cursor-gem-publisher.txt`) via the existing `shared.impingement_consumer.ImpingementConsumer` (`start_at_end=True`, because stale visual impingements should not drive current expression). This mirrors the reverie pattern: three independent consumers with three cursor files, no coordination required because each consumer has its own rate-limit and its own authorial role.

---

## §3. Rendering architecture

### 3.1 Layout placement

Canvas is 1920×1080. The transcription strip was historically `(40, 930, 1840, 110)` — a wide lower strip (see HARDM redesign §2 reference). **GEM claims this vacated geometry with one key modification: it is not a thin strip but a wider band designed for composition, not single-line text.**

Proposed geometry: **`(40, 820, 1840, 240)`** — lower-canvas band, 22 % of pixel area. This is large enough to host a multi-line composition (15 rows of 16 px = 240 px height; 115 cols of 16 px = 1840 px width; total ~1,725 cells of raster potential).

The lower band sits below the existing PiP pile, below the album (`pip-ll` ends at y=1060), and overlaps the `grounding-ticker-bl` surface at `(16, 900, 480, 40)`. The grounding ticker moves to `(16, 1060 - 40, 480, 40)` — immediately flush to bottom edge; negligible displacement. `stream_overlay` at `(1500, 860, 400, 200)` shifts up to `(1500, 620, 400, 200)` to clear the band.

Rationale for lower-band placement (vs. left-rail or centre):

- Eye-tracking on IRC-style layouts converges on the bottom third of screen for "current activity".
- Lower placement avoids visual conflict with the upper-right HARDM + reverie + thinking cluster.
- Width >> height rules out the vertical-symmetric face-silhouette risk (see §5).
- Displaces nothing that is simultaneously active in a typical composition tick.

**Open question deferred to operator (§10):** lower-band `(40,820,1840,240)` vs. left-rail `(0,200,400,780)` vs. centre `(760,440,400,200)`. Lower-band is the design's default.

### 3.2 Surface natural size

Source declared at `natural_w=1840, natural_h=240`. Cairo source runs at **`rate_hz=12.0`** (between HARDM's 4 Hz and the overlay zones' 30 Hz; a compromise respecting both BitchX "event rhythm as texture" and smooth keyframe animation).

### 3.3 Text rendering

Same engine as HARDM: `agents/studio_compositor/text_render.py::render_text()` with `TextStyle`. Font: **Px437 IBM VGA 8×16** (already installed for HARDM). Size classes drawn from `HomagePackage.typography.size_classes`:

- `compact` (8 pt) for background texture glyphs.
- `normal` (12 pt) for body text.
- `large` (24 pt) for emphasized words.
- `banner` (48 pt) for single hero words (one per composition max).

No font mixing within a size class. No italic (BitchX lineage refuses it implicitly — `weight = "single"`). Bold is a colour-brightness shift (muted → bright), not a font-weight change.

### 3.4 Frame-by-frame animation

Compositions carry an optional `keyframes: list[GemFrame]`. Each frame has a duration (ms) and a glyph layout. The renderer interpolates:

- `zero-cut` (BitchX grammar): instant swap to next keyframe; no tween.
- `scroll-h` / `scroll-v`: the current keyframe pixel-scrolls into place at the `ticker-scroll-in` transition rate.
- `overstrike`: new keyframe composited atop old with a 1-tick overlap.

There is **no fade, no dissolve, no alpha tween**. `AntiPatternKind = "fade-transition"` is in BitchX's `refuses_anti_patterns`; the ward inherits that refusal.

At 12 Hz render rate with per-frame durations in the 200 ms–2000 ms range, a composition with 5–8 keyframes runs 1–16 seconds before entering the decay state.

### 3.5 State machine

GEM inherits `HomageTransitionalSource`. The four-state FSM (`ABSENT`, `ENTERING`, `HOLD`, `EXITING`) is extended with GEM-specific sub-states inside `HOLD`:

| Sub-state | Trigger | Visual |
|---|---|---|
| `fill` | No composition published, no recent utterance | Ambient texture: slow RD-driven CP437 dither at `muted` colour role. Not empty; lightly alive. |
| `emerging` | New composition read, first 300 ms | Keyframe 0 rendered; if `ticker-scroll-in` is the active entry transition, the whole composition scrolls in. |
| `speaking` | `write_emphasis("speaking")` flag set (from CPAL) | Brightness multiplier `GEM_SPEAKING_BRIGHTNESS_MULT=1.22` (slightly above HARDM's 1.18 because GEM carries more semantic weight). |
| `resolving` | Post-animation hold | Current (last) keyframe held for `compose_hold_s` (composition-specified, default 3 s). |
| `decaying` | Past `compose_hold_s` | Glyphs overstrike with `░` dither, fading to `fill` over 1.5 s. |

Sub-state is internal to `GemGraffitiSource`; the outer FSM stays `HOLD` through all of the above. Only when the choreographer emits an exit transition does the outer FSM leave `HOLD`.

### 3.6 Integration with `HomageTransitionalSource`

GEM is a subclass: `class GemGraffitiSource(HomageTransitionalSource)`. It inherits the FSM, the `apply_transition` contract, the `_maybe_paint_emphasis` border polish, and the consent-safe fallback (active package `None` → transparent render, no signature-artefact leak). The subclass contract is `render_content()`; everything else is base.

---

## §4. Content vocabulary

### 4.1 ASCII + CP437 subrange

GEM's glyph palette, in priority order:

1. **Printable ASCII** (0x20–0x7E): primary for all text runs.
2. **CP437 box-drawing** (U+2500–U+257F mapped through Px437's CP437 glyph positions): `─│┌┐└┘├┤┬┴┼═║╔╗╚╝╠╣╦╩╬`.
3. **CP437 block elements** (U+2580–U+259F): `▀▁▂▃▄▅▆▇█▉▊▋▌▍▎▏▐░▒▓`.
4. **CP437 shaded/geometric** (U+25A0–U+25FF selected): `■□▣▤▥▦▧▨▩▲▼◆◇○●`.
5. **Braille patterns** (U+2800–U+28FF): `⠀⠁⠂⠃⠄⠅⠆⠇⠈⠉...⣿` — full 256-pattern range for sub-cell density.

**Excluded**: emoji (AntiPatternKind), decorative arrows beyond `→←↑↓`, general Unicode punctuation (`…‹›«»` are OK; `‰‱’‛` are refused as proportional-flavored).

### 4.2 Pango markup

Cairo/Pango with pango-markup enabled. Supported tags:

- `<span foreground="#rrggbb">...</span>` for per-run colour (mapped from HomagePackage palette roles; never hardcoded).
- `<span weight="bold">...</span>` — implemented as colour brightness shift per §3.3, not as a font weight.
- `<span size="larger">` / `size="smaller"` — mapped to size classes only (`compact`/`normal`/`large`/`banner`); raw point sizes refused.
- `<span strikethrough="true">` — for revision marks.
- `<span underline="single">` for emphasized words.

**Unsupported/refused** Pango tags: `<i>`, `<span style="italic">` (BitchX anti-italic), `<sub>`, `<sup>` (reads proportional), `<span letter_spacing="...">` (breaks raster).

### 4.3 Composition schema

```python
class GemFrame(BaseModel):
    glyphs: list[str]          # rows of the frame; each row is a Pango-markup string
    duration_ms: int = Field(ge=100, le=5000)
    transition_from_prev: Literal["zero-cut", "scroll-h", "scroll-v", "overstrike"] = "zero-cut"

class GemComposition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    composition_id: str               # uuid4 from producer
    narrative_seed_id: str | None     # impingement record id that seeded this
    keyframes: tuple[GemFrame, ...]   # 1–12 frames
    compose_hold_s: float = Field(ge=0.5, le=10.0, default=3.0)
    emphasis_words: tuple[str, ...] = ()  # words receiving size_class="large"
    banner_word: str | None = None        # optional single word at size_class="banner"
    anchor: Literal["tl", "tc", "tr", "cl", "cc", "cr", "bl", "bc", "br"] = "cc"
    created_at: float
```

Written as JSON to `/dev/shm/hapax-compositor/gem-composition.json`.

### 4.4 Palette — BitchX Gruvbox + bright-identity-accent

GEM resolves colour through `HomagePackage.resolve_colour(role)`. No hex literals. Role usage:

| Content class | Default role | Condition |
|---|---|---|
| Body text | `content_colour_role` (grammar-defined; BitchX: `terminal_default`) | Always |
| Emphasized words | `identity_colour_role` (BitchX: `bright`) | `emphasis_words` match |
| Banner word | `accent_cyan` or `accent_magenta` | Rotates per composition to avoid single-colour bias |
| Box-draw frames | `punctuation_colour_role` (BitchX: `accent_green`) | Always |
| Revision marks (strikethrough) | `accent_red` | When `<span strikethrough>` used |
| Ambient fill texture | `muted` | Sub-state `fill` |
| Background | `background` | Always cleared before draw |

Background is only cleared when the composition occupies the full band; partial-area compositions honour the compositor's expectation of transparent-outside-content.

Per HOMAGE spec §4.4 the palette swaps on working-mode (research vs rnd) transitions **without** recolour shock — the package instance changes, and the next render picks up the new roles.

---

## §5. Anti-anthropomorphization filters

A **runtime checker** runs between LLM output and SHM write. Reject causes the producer to skip publication (GEM decays to `fill`); it never renders a rejected composition.

File: `agents/studio_compositor/gem/anti_face.py`.

### 5.1 Invariants (analogous to HARDM's 10)

1. **I1 — No kaomoji / emoticon sequences.** Regex reject on `:-?[()Dp>O]`, `[:;]['`]?[)(]`, `\(\s*[._<>^-]\s*[._<>^-]\s*\)`, `[<>]\s*[._]\s*[<>]`, `\[[._]\s*[._]\]`, `XD`, `B)`, `ಠ_ಠ`, `(҂⌣̀_⌣́)`, and all structurally similar patterns. Regex list pinned in test.

2. **I2 — No vertical-symmetry eye+mouth layout.** Parse the glyph grid. For each pair of high-density glyphs (`█▇▆▅◆●■`) separated horizontally by 24–64 px in the upper half of the composition (top 40% rows), scan the lower half for a horizontally-extended glyph run (`─═▬▂▃`). If an eye-pair + mouth-run triplet fits within a 120×80 px bounding box, reject. **Tolerance:** purely symmetric text compositions pass because density-metric ignores text runs below a density threshold (count of high-density glyphs in each cluster < 3).

3. **I3 — No figure silhouette.** Binarise the composition (glyph present = 1, blank = 0). Compute the vertical profile (count per row). Reject if the profile has the `head(narrow) → shoulders(wide) → torso(medium) → legs(narrow-split)` signature: specifically a top ≤ 4 rows of width <= 40% of the widest row, followed by a row <= 8 rows down whose width is ≥ 80% of the max, tapering to a narrower bottom. Conservative — catches obvious human-silhouette renders.

4. **I4 — No spelling of `hapax` as banner or emphasis.** Case-insensitive check on `emphasis_words` and `banner_word`. Rejects `hapax`, `HAPAX`, `h a p a x`, leet (`h4p4x`), reversed (`xapah`). Hapax is not a character on a wall.

5. **I5 — No speaker-attribution glyph patterns.** Reject sequences like `hapax>`, `hapax:`, `<hapax>` — these read as chat-nickname syntax and re-introduce "Hapax as a person speaking" framing. (Note: GEM may still use angle-bracket container shape per BitchX `container_shape="angle-bracket"`, but never with `hapax` / `Hapax` inside.)

6. **I6 — Density budget.** A single keyframe may not exceed 45% filled glyph cells. Denser reads as "image" rather than "graffiti"; rejection protects against inadvertent pictorial renders.

7. **I7 — Frame-count budget.** A composition may not have more than 12 keyframes. Longer reads as animated character-cartoon.

8. **I8 — No performative emotion markers.** Reject standalone `!!!`, `???`, `...`, `zzz`, `!?!`, `!1!1`. One `!` or `?` inline in a fragment is fine; runs are refused.

9. **I9 — Anti-pattern cross-check.** Run the active `HomagePackage.refuses_anti_patterns` set against the composition: emoji → reject; fade-transition → reject (shouldn't be emittable anyway); swiss-grid alignment → reject (catches centred-paragraph multi-line bodies without ragged edges or line-start markers).

10. **I10 — Banner-word length.** `banner_word` must be a single word, length ≤ 12 characters. Long banner-words at 48 pt read as "signage" rather than emphasis and are a common failure mode of LLMs trying to "paint a message". Enforced by `GemComposition` field validator.

Each invariant emits a Prometheus counter on reject: `gem_anti_face_rejections_total{invariant="I1"}`.

### 5.2 Hypothesis property tests

`tests/studio_compositor/test_gem_anti_face_properties.py`:

- `test_no_kaomoji_ever_passes` — Hypothesis strategy generates compositions containing randomly-positioned kaomoji strings; all must reject.
- `test_vertical_symmetry_detected` — generates random 2-cluster + 1-bar compositions; I2 must reject with recall ≥ 0.98 on the positive set.
- `test_hapax_spelling_never_passes` — generates `emphasis_words` containing `hapax` in various forms; must always reject.
- `test_density_budget_enforced` — generates fills from 0.0–1.0; accept/reject at exactly 0.45.
- `test_text_compositions_pass` — generates plain multi-line ASCII fragments (no kaomoji, no symmetry cluster); must not reject for spurious reasons.

### 5.3 LLM-side prompt constraint

In addition to runtime filters, the composition-producer prompt includes explicit negatives:

> You are authoring a graffiti-style ASCII composition for Hapax's expression surface. Hapax has no face, no character, no avatar. NEVER: use emoticons, kaomoji, human silhouettes, speaker-attribution patterns (`name:`, `<name>`), the word "Hapax", exclamation/question-mark runs, or images that read as figures. ALWAYS: pick a fragment or shape worth emphasising, keep density below 45%, prefer box-draw frames and braille density over figurative glyphs. Refuse if no suitable composition exists — emit `null`.

The prompt's refusal path produces a `null` composition, which the producer writes as an empty `keyframes: []` (no-op at render).

---

## §6. State machine

### 6.1 Outer FSM (inherited from `HomageTransitionalSource`)

`ABSENT` → `ENTERING` → `HOLD` → `EXITING` → `ABSENT`. Default `initial_state=TransitionState.HOLD` (paint-and-hold semantics; see HARDM hotfix 2026-04-18). Entry/exit transitions driven by the choreographer. Default entry: `ticker-scroll-in`. Default exit: `ticker-scroll-out`.

### 6.2 Inner sub-state machine (GEM-specific)

While outer FSM is in `HOLD`, `GemGraffitiSource` runs its own sub-FSM tracking composition lifecycle:

```
fill ──(new composition published)──> emerging
emerging ──(300 ms elapsed)──> playing
playing ──(all keyframes consumed)──> resolving
resolving ──(compose_hold_s elapsed)──> decaying
decaying ──(1.5 s elapsed)──> fill
```

**Signal → state mapping:**

- `fill` is default when no composition has been read, OR when an impingement quiet period (no new impingements in the last 30 s) elapses. Fill renders ambient RD dither at `muted` role; visually low-key, not blank. Never empty — the surface always shows *something*.
- `emerging`/`playing`/`resolving`/`decaying` cycle through composition data.
- `speaking` emphasis is orthogonal to the sub-state machine: `write_emphasis("speaking")` from CPAL sets a brightness multiplier applied in any sub-state.
- `seeking`/impingement-spike is reflected via stimmung state. When `stimmung.overall_stance == "seeking"` or `stimmung.intensity > 0.8`, the producer lowers its recruitment threshold (half, per the unified-recruitment SEEKING clause) and publishes more frequently. The ward does not change visual vocabulary; the vocabulary is always the BitchX grammar. What changes is **rate** of composition turnover.

### 6.3 Idle state content

The `fill` state is itself content — per the `event_rhythm_as_texture` BitchX grammar rule (`GrammarRules.event_rhythm_as_texture=True`). It is a slow, sparse CP437 dither produced by a Gray-Scott-style 2D diffusion field (same technique as HARDM) at the `muted` palette role. The dither is **not** expressive; it is a texture showing the system is alive and the surface is present. No words, no shapes — just density waves.

---

## §7. Integration with speech-transcription-absence

The operator directive states explicitly: *Hapax will have no visible transcriptions for its speech.* GEM is designed as the **adjacent, honest, non-transcriptional response** to that absence.

### 7.1 Correlation vs. abstraction

The design choice is: **loose semantic correlation, not verbatim tracking.** GEM compositions seed from the *same impingements* that seed CPAL utterances, so they share semantic neighbourhood without ever being a transcription. The viewer sees that Hapax is emphasising a word or shape that is *related* to what it might be saying, but the ASCII mural is never a caption of the audio.

This achieves three things:

- Hapax retains authorship latitude (graffiti, shapes, frame-by-frame abstract animation all remain permissible).
- Audience has a semantic anchor without forcing a transcription contract.
- Operator's "Hapax will have no visible transcriptions" constraint is respected in letter and spirit.

### 7.2 How the audience knows Hapax is speaking

Three sources, none of which introduce transcription:

1. **Audio.** Hapax speaks aloud (Kokoro TTS → Studio 24c → stream audio). The stream carries the voice.
2. **HARDM emphasis** (existing). `write_emphasis("speaking")` brightens active HARDM cells 1.18×; the signal-grid visibly brightens on utterance onset.
3. **GEM `speaking` sub-state.** GEM's own brightness multiplier (1.22×) plus the RD texture's tempo doubling during utterance onset (implementation: reduce RD time-step to 0.5× so the dither visibly animates faster). This makes GEM *respond* to utterances without transcribing them.

Additionally, when `stimmung.coherence < 0.3` and the utterance is a high-stakes moment (`impingement.intensity > 0.85`), the producer is permitted to author a composition whose `emphasis_words` include the **single most salient word** from the impingement's narrative text (a word-level anchor, not a sentence). This is a rare, deliberate anchoring — the equivalent of an IRC user `/me`-emphasizing one word — not a caption.

### 7.3 Silence state

When Hapax is not speaking and impingement is quiet (intensity < 0.2 for > 30 s), GEM stays in `fill`. The viewer sees a slowly shimmering muted dither in the lower band. This is the visual equivalent of the silence CPAL is also producing — aligned, non-performative, texture-only.

---

## §8. Implementation phases

Each phase is independently shippable. Phase 1 is operator-visible confidence that the surface exists.

### Phase 1 — Static heartbeat ward (minimum)

**Scope:** Register the source, wire the layout, render a static CP437 box-draw placeholder with a slow 1 Hz pulse effect, ensure it appears in `/dev/video42` and `rtmp://127.0.0.1:1935/studio`.

**Deliverables:**
- `agents/studio_compositor/gem/__init__.py`
- `agents/studio_compositor/gem/graffiti_source.py` — `GemGraffitiSource(HomageTransitionalSource)` rendering a hardcoded `┌─ GEM ─┐ │ ... │ └───────┘` placeholder.
- `config/compositor-layouts/default.json` — new source entry + new surface at `(40, 820, 1840, 240)` + assignment (`gem_graffiti` → `gem-mural-bottom`, z_order=25, opacity=0.95).
- `agents/studio_compositor/cairo_source_registry.py` — `register("GemGraffitiSource", GemGraffitiSource)`.
- Smoke test: ward visible on livestream within one rebuild cycle.

Sub-task: displace `grounding-ticker-bl` to `(16, 1040, 480, 40)` and `stream_overlay` surface to free the band.

### Phase 2 — Signal-stream dynamic content

**Scope:** Replace the placeholder with a composition derived from stimmung + recent impingements, **without LLM calls**. Maps stimmung dimensions to glyph density, impingement narrative's most-frequent content word to an emphasis word, RD field to ambient fill.

**Deliverables:**
- `agents/studio_compositor/gem/stimmung_composer.py` — rule-based `GemComposition` producer from `/dev/shm/hapax-stimmung/state.json` and the impingement tail.
- `scripts/gem-publisher.py` — systemd-timer entry point using the Phase 2 composer.
- `systemd/units/hapax-gem-publisher.timer` + `.service` (2 s cadence at this phase).
- Integration into `gem/graffiti_source.py` to read `/dev/shm/hapax-compositor/gem-composition.json`.

Phase 2 stands alone as a working ward: no LLM cost, semantics honest to signals.

### Phase 3 — Frame-by-frame animation

**Scope:** Support `GemFrame.keyframes` with `zero-cut`, `scroll-h`, `scroll-v`, `overstrike` transitions.

**Deliverables:**
- `agents/studio_compositor/gem/animator.py` — keyframe clock + transition rendering.
- Phase 2 composer extended to emit 2–3 keyframe animations (e.g., a glyph "growing" or a box expanding).
- Sub-state machine from §6.2 fully implemented.

### Phase 4 — LLM-output-driven graffiti

**Scope:** Replace rule-based Phase 2 composer with LLM-backed composer.

**Deliverables:**
- `agents/studio_compositor/gem/llm_composer.py` — pydantic-ai agent with `output_type=GemComposition`, prompt scaffolded from §5.3.
- Affordance registration: `expression.gem_mural` in the affordance registry with Gibson-verb description and `OperationalProperties(medium="visual", consent_required=False)`.
- `scripts/gem-publisher.py` reads recruitment state + calls LLM composer when recruited.
- Cost envelope: 8 s cadence × 24 h × ~400 tokens/call @ TabbyAPI → operator-provides-the-GPU cost zero; fallback to `balanced` (Sonnet) gated by stimmung coherence (see §2.3).

### Phase 5 — Anti-face invariants + Hypothesis property tests

**Scope:** Full §5 checker enforcement, cross-phase regression tests.

**Deliverables:**
- `agents/studio_compositor/gem/anti_face.py` — all 10 invariants (I1–I10) runtime-enforceable.
- `tests/studio_compositor/test_gem_anti_face_properties.py` — Hypothesis-driven property tests per §5.2.
- `tests/studio_compositor/test_gem_anti_face_fixtures.py` — fixture-based regression: known-bad compositions always reject; known-good always pass.
- Prometheus counter wiring via `shared/director_observability.py` (new `emit_gem_anti_face_rejection(invariant: str)`).
- Alert rule: `gem_anti_face_rejections_total > 20/hour` triggers ntfy to operator (LLM is generating face-y content; likely a prompt-degradation signal).

### Phase 6 (optional, future) — Coupling to reverie

The HOMAGE coupling-rules slot allows GEM to feed a `gem_density` scalar into `uniforms.custom[coupling_slot_index]` so the reverie shader graph can modulate (e.g., increase diffusion when GEM density is high — "the mural is busy, visual drift is slow"). Deferred.

---

## §9. Files to create / modify

### 9.1 New files

| Path | Responsibility |
|---|---|
| `agents/studio_compositor/gem/__init__.py` | Module init, exports `GemGraffitiSource`, `GemComposition`, `GemFrame`. |
| `agents/studio_compositor/gem/graffiti_source.py` | `GemGraffitiSource(HomageTransitionalSource)` — Cairo render, sub-state machine, SHM consumer. |
| `agents/studio_compositor/gem/schema.py` | Pydantic `GemComposition`, `GemFrame` models + field validators (banner_word length, frame count). |
| `agents/studio_compositor/gem/stimmung_composer.py` | Phase 2 rule-based composer. |
| `agents/studio_compositor/gem/llm_composer.py` | Phase 4 pydantic-ai composer. |
| `agents/studio_compositor/gem/animator.py` | Phase 3 keyframe clock + transition rendering. |
| `agents/studio_compositor/gem/anti_face.py` | 10-invariant runtime checker. |
| `scripts/gem-publisher.py` | Systemd-timer producer; reads impingements, stimmung, package; writes composition SHM. |
| `systemd/units/hapax-gem-publisher.service` | Oneshot runner for the publisher. |
| `systemd/units/hapax-gem-publisher.timer` | 2 s (P2) / 8 s (P4) cadence. |
| `tests/studio_compositor/test_gem_graffiti_source.py` | Unit tests for FSM, sub-state, render contract. |
| `tests/studio_compositor/test_gem_composition_schema.py` | Pydantic validation tests. |
| `tests/studio_compositor/test_gem_anti_face_properties.py` | Hypothesis property tests. |
| `tests/studio_compositor/test_gem_anti_face_fixtures.py` | Known-bad / known-good fixture tests. |
| `tests/studio_compositor/test_gem_publisher.py` | Publisher integration test (mocked SHM paths). |

### 9.2 Modified files

| Path | Change |
|---|---|
| `config/compositor-layouts/default.json` | Add `gem_graffiti` source; add `gem-mural-bottom` surface at `(40,820,1840,240)`; move `grounding-ticker-bl` to `(16,1040,480,40)`; move `stream_overlay` surface to `(1500,620,400,200)`; add assignment. |
| `agents/studio_compositor/cairo_source_registry.py` | Register `GemGraffitiSource`. |
| `shared/director_observability.py` | Add `emit_gem_anti_face_rejection(invariant: str)` and `emit_gem_composition_published()`. |
| `scripts/rebuild-service.sh` | Watch path: add `agents/studio_compositor/gem/` and `scripts/gem-publisher.py` to rebuild triggers for `studio-compositor.service`. |
| `agents/studio_compositor/homage/choreographer.py` | Include `gem_graffiti` in the package's ward rotation; emit `ticker-scroll-in`/`ticker-scroll-out` at composition boundaries (optional — GEM can use its own inner sub-state). |
| `systemd/expected-timers.yaml` | Add `hapax-gem-publisher.timer`. |

### 9.3 SHM paths (complete list)

| Path | Writer | Reader | Purpose |
|---|---|---|---|
| `/dev/shm/hapax-compositor/gem-composition.json` | `scripts/gem-publisher.py` | `GemGraffitiSource` | Current composition payload (`GemComposition` as JSON). |
| `/dev/shm/hapax-dmn/impingements.jsonl` | DMN (existing) | `gem-publisher.py` | Impingement tail for semantic seeding. |
| `/dev/shm/hapax-stimmung/state.json` | stimmung (existing) | `gem-publisher.py`, `GemGraffitiSource` | Stimmung dimensions. |
| `/dev/shm/hapax-compositor/homage-active.json` | rotator (existing) | `get_active_package()` | HomagePackage selection. |
| `/dev/shm/hapax-compositor/recent-recruitment.json` | affordance pipeline (existing) | `gem-publisher.py` | Gate on `expression.gem_mural` recruitment. |
| `/dev/shm/hapax-compositor/hardm-emphasis.json` | CPAL (existing) | `GemGraffitiSource` | `speaking`/`quiescent` flag, shared with HARDM. |
| `~/.cache/hapax/impingement-cursor-gem-publisher.txt` | `gem-publisher.py` | `gem-publisher.py` | Independent cursor file. |

---

## §10. Open questions

1. **Where should GEM live on screen?** Design default is lower-band `(40,820,1840,240)`. Alternatives:
   - Left-rail `(0,200,400,780)` — more painterly "column", displaces token_pole.
   - Centre `(760,440,400,200)` — high prominence, displaces sierpinski centre.
   - Dual-band: a thin 60 px strip top + thin 60 px strip bottom.
   - **Operator call.** Lower-band is the proposal; a Phase-0 review of all four options live in a staging layout is cheap.

2. **Which signals drive content in Phase 2?** Design default is stimmung (10 dims) + impingement text tail (most-frequent content word). Alternatives:
   - Director's structural_intent → composition seed (tight coupling to narrative loop).
   - Reverie shader state → composition (visual-to-visual feedback).
   - DMN dreams channel (if/when a dedicated dream stream exists).
   - Delta decides, ideally signal-honest. Design recommends stimmung+impingement because those streams are mature and have clear semantics.

3. **LLM call frequency for Phase 4?** Design default is 8 s cadence with TabbyAPI Qwen3.5-9B (cost zero, operator-owned GPU). Fallback to `balanced`/Sonnet conditional on `stimmung.coherence < 0.3 AND impingement.intensity > 0.85` — rare, ~5–10 Sonnet calls/hour at peak, <$0.10/hr. If Phase 2 signal-driven content is good enough, Phase 4 LLM is defer-able indefinitely.

4. **Should GEM transmit an HOMAGE coupling payload?** Phase 6 proposes reverie receives `gem_density` via `uniforms.custom[coupling_slot_index]`. Defer — BitchX couples to HARDM only today; multi-ward coupling is a spec expansion.

5. **Braille density glyphs vs. CP437 blocks — priority?** Both are in the vocabulary; the composer should choose per density regime (<15 % density → CP437 blocks; 15–45 % → Braille; the 45 % ceiling is I6). Priority could be runtime-configurable. Default: composer picks, no runtime flag.

6. **Compositions crossing the `(emerging → playing → resolving → decaying)` boundary when a new composition arrives mid-playback.** Design default: hard interrupt — drop the in-flight composition, enter `emerging` for the new one, inherit the `transition_from_prev` of keyframe 0 as the inter-composition transition. Alternative: queue the new composition, let the current finish. Queue is kinder to slow-moving visuals; hard-interrupt is more honest to "Hapax expressed something new, here it is". Recommend hard-interrupt; validate with operator during Phase 2.

7. **Should Phase 2's rule-based composer emit animations (multiple keyframes) or only static compositions?** Static-only is cheaper; animations come in Phase 3. The phases could be merged if Phase 2's composer has a trivial animation generator (e.g. expand-then-hold box-draw frame). Design keeps them separate for shipping independence.

8. **Consent-safe behavior.** When the consent gate flips the active package to `None`, GEM receives a `None` from `get_active_package()`. Design: render a blank (transparent) surface. Alternative: render a single, neutral consent-safe indicator (e.g. a grey box-draw with `[—]`). The HARDM consent-safe behavior is blank render; GEM mirrors. Confirm with governance if a signal-of-presence is preferred.

9. **Do anti-face rejections count against the producer's budget?** If an LLM composition is rejected and the producer skips, the surface decays to `fill`. If rejection rate spikes (e.g. LLM degradation), the ntfy alert (§Phase 5) fires. A secondary response could be to automatically downgrade to the rule-based Phase 2 composer until the rejection rate recovers. Deferred — first observe real rates post-launch.

10. **Multi-composition layering.** Could GEM render two independent compositions (e.g. a background decay composition + a foreground fresh-impingement composition)? Adds expressivity but also anti-face risk (layering can create unintended symmetry). Deferred. Single composition per tick for Phase 1–5.

---

**End of design.**
