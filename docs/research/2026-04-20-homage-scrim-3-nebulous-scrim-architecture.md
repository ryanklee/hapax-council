# HOMAGE / Scrim Cluster 3 — Nebulous Scrim Architecture: What the Scrim IS, How Wards Swim In It

**Status:** Research / design, operator-directed 2026-04-20.
**Authors:** alpha-research dispatch (Claude Opus 4.7, 1M).
**Governing anchors:** the existing scrim design (`docs/research/2026-04-20-nebulous-scrim-design.md`), HOMAGE framework spec (`docs/superpowers/specs/2026-04-18-homage-framework-design.md`), Reverie vocabulary integrity (council CLAUDE.md § Reverie Vocabulary Integrity, `agents/reverie/_uniforms.py`), Logos design language (`docs/logos-design-language.md`), HARDM anti-anthropomorphization invariant (memory `project_hardm_anti_anthropomorphization`).
**Related prior art:** `project_effect_graph`, `project_reverie`, `project_reverie_adaptive`, `feedback_director_grounding`, `feedback_no_expert_system_rules`, `feedback_grounding_exhaustive`, `project_720p_commitment`.
**Scope:** Conceptual deepening + architectural sequencing of the *scrim itself*, with explicit attention to how wards "swim" in it and how the asymmetry of perception (broadcast tee vs studio inhabitant) is honored. Extends — does not duplicate — the existing scrim design.
**Non-scope:** Per-ward behavior beyond depth-positioning and lifecycle; new HOMAGE packages beyond BitchX (deferred to Cluster 4); audio-DSP beyond the §8 coupling matrix.

---

## §1 TL;DR

The Nebulous Scrim is the compositor's **output substrate**, not a layer. Cluster 2 (the existing `2026-04-20-nebulous-scrim-design.md`) named the scrim, gave it seven precedent commitments, sketched eight-phase integration, and proposed seven scrim-profile families. This doc deepens *what the scrim IS* media-theoretically (theatrical scrim + maya + McLuhan + Lacanian gaze + Steyerl/Paglen), gives a **wards-swim grammar** the existing design does not have, formalises the **broadcast-vs-studio asymmetry** as an architectural invariant, and lands a recommended implementation path with concrete code-shapes.

**Recommended implementation path: Option A + Option D hybrid.** A new dedicated `scrim` pass in the Reverie wgpu graph (Option A — between `feedback` and `content_layer`, before `postprocess`) drives the scrim's *visual* properties (density / refraction / color cast / particulate). A `ScrimSourceRegistry` entry (Option D — substrate-protocol-tagged like Reverie itself) exposes the scrim's *parameters* to the compositor so cairo wards can read `scrim_depth` + `ward_permeability` and adjust their own composite blend. Justification: Reverie already owns the always-on generative substrate (per `agents/studio_compositor/homage/substrate_source.py`'s `HomageSubstrateSource` protocol with `SUBSTRATE_SOURCE_REGISTRY = ("reverie_external_rgba", "reverie", "album")`); adding the scrim as an in-graph pass keeps the substrate invariant intact (no FSM dispatch required), reuses the existing per-frame uniform bridge (`agents/reverie/_uniforms.py:_BITCHX_COLOR_*` damping pattern), and the parallel SourceRegistry tag lets cairo wards opt into refraction/blur without each ward shipping its own per-instance shader (which would multiply maintenance cost across the ~13 cairo source modules under `agents/studio_compositor/`).

**Three scrim-Programme mode names** (the wards-permeability axis, orthogonal to the seven scrim-profile families in Cluster 2):

1. **`semipermeable_membrane`** (default) — wards transit gradually; `behind`→`surface` takes ~600ms with refraction falloff. The "good night" baseline.
2. **`solute_suspension`** — wards diffuse into the scrim and remain trapped, oscillating in place; high `density`, refraction wobble at ~0.3 Hz. For interludes and listening passages.
3. **`ionised_glow`** — wards punch through cleanly and sit *in front of* the scrim with crisp edges and a back-glow halo. For research markers, hero callouts, and ritual openings.

These three are *permeability profiles*; they govern ward-swim behavior. The seven Cluster-2 profiles (`gauzy_quiet`, `warm_haze`, `moire_crackle`, `clarity_peak`, `dissolving`, `ritual_open`, `rain_streak`) govern scrim-fabric character. Both are soft priors per `feedback_no_expert_system_rules`; they compose, they don't gate.

---

## §2 What the Scrim IS — Media-Theoretic Framing

Cluster 2 §2 already gives the theatrical-scrim mechanics, the film/photography touchstones, and the BitchX-as-fabric lineage. This section adds *philosophical* grounding the existing design under-specifies.

### 2.1 Theatrical scrim — the load-bearing physics, restated

A theatrical scrim (sharkstooth gauze, cotton open-weave) "appears transparent or solid depending on how it's lit. It is a piece of fabric that mostly has an open weave pattern, which gives it its transparency and opacity" (Theatrecrafts). The mechanism is *differential lighting*: front-lit + dark-behind = opaque; dark-front + lit-behind = transparent; both lit = ghost layering. "Sharkstooth scrim is one of the most useful materials in the gauze family, most often employed for conceals, reveals, and creating the illusion of depth and distance" ([Sew What Inc](https://sewwhatinc.com/blog/2015/08/20/the-magic-of-sharkstooth-scrim/)).

The implication for our compositor: **scrim density and ward emission are differentially-lit equivalents.** A bright surface ward (Hapax's `token_pole` glyph at full glow) is "front light"; a dim camera PiP behind the scrim is "back light absent." The scrim's apparent opacity isn't a single uniform — it's the *ratio* of ward emission to camera transmission at every screen-space sample.

### 2.2 Maya — the veil of phenomenal-vs-real

Hindu Advaita Vedānta names *māyā* as "the powerful force that creates the cosmic illusion that the phenomenal world is real" ([Wikipedia — Maya (religion)](https://en.wikipedia.org/wiki/Maya_(religion))). Vivekananda's clarification is critical: "to say the world is maya does not mean that it is an illusion, or there is no external world. Māyā is a fact in that it is the appearance of phenomena" ([Maya in Hindu Philosophy](https://www.hinduwebsite.com/hinduism/essays/maya.asp)). In Buddhism, māyā "is one of twenty subsidiary unwholesome mental factors, responsible for deceit or concealment about the illusionary nature of things."

Why this matters: the scrim is *not pretending* the studio doesn't exist. It is *showing* the studio under the condition that the showing is itself a thing. The audience sees-through-something, and the something is part of what they're seeing. This is why Cluster 2 §9.1's "scrim is always present" is non-negotiable: a scrim-off state would betray the metaphor by pretending to a clarity that the medium cannot deliver.

### 2.3 McLuhan — the medium IS the message

"The medium is the message" ([McLuhan 1964](https://web.mit.edu/allanmc/www/mcluhan.mediummessage.pdf)) reframes our scrim: the *fabric* is the broadcast's content as much as the camera feeds are. McLuhan: "the 'content' of any medium is always another medium … The content of writing is speech, just as the written word is the content of print, and print is the content of the telegraph" ([Wikipedia](https://en.wikipedia.org/wiki/The_medium_is_the_message)).

Translating: the scrim is the *medium*; the camera feeds + Reverie + cairo wards are the *content* the scrim carries. Operators who think of the scrim as decorative are reading it as content; the scrim is in fact carrying the content but *also being its own message* about the relationship between studio and broadcast. The "hallloo over there from over here across the way" register is the scrim *speaking as itself*, not a label slapped on top.

### 2.4 Lacanian gaze — the screen as objet petit a

Lacan's gaze is "not what one sees, but that which structures one's position as being seen — a point from which the subject is seen without being able to locate the source. It is tied intimately to Lacan's concept of the object a (objet petit a), the lost object-cause of desire, and serves as a rupture in the field of visibility that marks the Real" ([DS Project](https://thedsproject.com/portfolio/deciphering-the-gaze-in-lacans-of-the-gaze-as-objet-petit-a/)). And: "Man isolates the function of the screen and plays with it, knowing how to play with the mask as that beyond which there is the gaze."

Implication for our scrim: the scrim is exactly what the *viewer's gaze passes through*. The studio inhabitants do not see the scrim; only the viewer sees it. The viewer's gaze is *structured by* the scrim — it *cannot* directly access what's behind. The studio inhabitants are the unseen seers; the broadcast viewer is the seen-through-a-veil seer. (This is also why the scrim must NEVER be anthropomorphized — see §10. A scrim with a face would be the gaze gazing back, which collapses the asymmetry.)

### 2.5 Steyerl, Paglen — the screen as ontological boundary

Hito Steyerl's *How Not to Be Seen: A Fucking Didactic Educational .MOV File* (2013) treats the screen as an ontological boundary: "Birds transverse the boundary of the screen to emerge on the desert platform, heightening the friction between the 'real' and simulated realms" ([Frames Cinema Journal](https://framescinemajournal.com/article/facing-off-from-abstraction-to-diffraction-in-hito-steyerls-abstract-2012/)). Trevor Paglen's *Invisible Images* names the screen as where "machine-readable images that function primarily for algorithms" live, "uncoupled from human perception" ([Wiley/Architectural Design](https://onlinelibrary.wiley.com/doi/abs/10.1002/ad.2383)).

Implication: the scrim is doing *active boundary work*. It is not neutral. YouTube's content classifier sees through the scrim (per Cluster 2 §9.3 — demonetization safety unaffected); humans see *the scrim*. This is the demonetization-vs-aesthetic split the Cluster 2 design already names; the Steyerl/Paglen lens makes its philosophical weight legible.

### 2.6 Brechtian alienation — making the medium visible

Brecht's *Verfremdungseffekt* "made the mechanics of performance visible, urging the audience to think critically rather than passively absorb" ([Wikipedia — Distancing effect](https://en.wikipedia.org/wiki/Distancing_effect)). The scrim is not a Brechtian-alienation device per se (it is warm, intimate, hailing — not cold-distancing), but it *shares* Brecht's commitment to keeping the medium honest. The scrim does not dissolve into immersion. It says: "this is broadcast; I am the broadcast's surface; I am here, and I am between us."

### 2.7 Shoji — the load-bearing architectural analog

A shoji "is a door, window or room divider used in traditional Japanese architecture, consisting of translucent (or transparent) sheets on a lattice frame … They act like curtains, shielding and protecting dwellers from outside elements, yet letting in light and sound to a degree" ([Wikipedia — Shoji](https://en.wikipedia.org/wiki/Shoji)). The kumiko lattice is "literally 'woven'" — two structural commitments that map directly onto our scrim:

- **Lattice + paper = structure + diffusion.** The cairo ward layer is the lattice (load-bearing legibility); the Reverie scrim pass is the washi (the diffusing medium).
- **Light AND sound, both partially transmitted.** The §8 audio-coupling matrix below treats sound as scrim-permeable too: Hapax's voice is *cloth-filtered* through the scrim per Cluster 2 §8.1, not magically present in the broadcast.

### 2.8 Synthesis — what these commitments imply for design

The seven Cluster-2 commitments (translucent medium, differential lighting, fabric weave, tinted, subtle motion, atmospheric perspective, always-present) are extended by the media-theoretic frame to:

8. **The scrim is its own message** (McLuhan) — its *appearance* is non-decorative content the audience reads.
9. **The scrim is asymmetrically perceived** (Lacan) — it is for the viewer's gaze; studio inhabitants see through their own physical eyes onto the room.
10. **The scrim does ontological work** (Steyerl/Paglen) — it marks the broadcast/studio boundary as a *kind of thing*, not a transparent membrane.
11. **The scrim is honest about being a medium** (Brecht-adjacent) — it does not pretend to disappear.
12. **The scrim is structured fabric over diffusing material** (shoji) — the cairo lattice (load-bearing) + the wgpu diffuser (atmospheric) are formally distinct contributions.

These five additional commitments harden into the §10 anti-anthropomorphization invariants and the §7 asymmetry architecture below.

---

## §3 Existing Design Audit

The existing `docs/research/2026-04-20-nebulous-scrim-design.md` is *thorough* on what the scrim is and how to install it as substrate. This audit identifies what it specifies, what it under-specifies, and where the operator's "wards swim in the scrim" directive demands extension.

### 3.1 What Cluster 2 already commits to

- **Conceptual anchor (§§1–2).** Theatrical/film/photographic/visual-art precedent. Seven commitment list (§2.7).
- **Vocabulary inventory (§3).** 15 scrim-producing techniques tabulated against existing nodes + estimated GPU cost.
- **Spatial-semantics toolkit (§4).** Differential blur, parallax, atmospheric perspective, contrast reduction, inverse vignette, soft pulsation, heat-shimmer-on-hero. Seven techniques.
- **Substrate-not-layer architecture (§5).** Four conceptual layers (scrim pass / behind-scrim / on-scrim / in-front-of-scrim).
- **Ward-depth assignments (§6).** Four-band classification of *which* wards sit at *which* depth.
- **Programme-scrim coupling (§7).** Seven programmes × scrim character table (Listening, Hothouse, Vinyl showcase, Wind-down, Research, Interlude, Ritual).
- **Hapax-voice cross-scrim treatment (§8).** Cloth-filtered TTS preset, scrim-pierce intent for direct address.
- **Non-negotiables (§9).** Always-present, studio-readable, demonetization-independent, consent-gate-respecting, BitchX register, performance ceiling, consent-safe layout exemption, 720p commitment, palette coherence.
- **Eight-phase implementation (§11).** Phase 1 = `scrim_baseline` preset; Phase 2 = `scrim_depth` tag; Phase 3 = atmospheric tint; Phase 4 = differential blur; Phase 5 = programme-density wiring; Phase 6 = preset reorganization; Phase 7 = voice filter; Phase 8 = `scrim.pierce` intent; Phase 9 = new shader nodes.
- **Profile taxonomy (§13).** Six canonical scrim-profile families + one context-bound (`rain_streak`).

### 3.2 Gaps and under-specified areas

The Cluster 2 doc is excellent on *substrate framing* but under-specifies the following six areas, which this dispatch fills:

| Gap | Cluster 2 status | This doc § |
|-----|------------------|-----------|
| **Wards-swim grammar** | implicit in §6 (depth bands) but no lifecycle / state machine | §6 |
| **Broadcast/studio asymmetry as architectural invariant** | implied by §1.3 spatial semantics, no explicit operator-monitor model | §7 |
| **Audio coupling beyond voice** | §8 is voice-only; stimmung / vinyl_chain / MIDI couplings absent | §8 |
| **Scrim as Programme primitive** | §7 implies it via the programme→scrim table; no schema or YAML | §9 |
| **Anti-anthropomorphization invariant for the scrim itself** | not addressed (Cluster 2 inherits HARDM doctrine implicitly) | §10 |
| **Concrete code-shapes (WGSL, Pydantic, YAML)** | sketched in §11 prose; no source-form artifacts | §11 |

### 3.3 Where Cluster 2 conflicts with "wards swim in the scrim"

Cluster 2 §5.2 places wards at *fixed depth bands* (`surface`, `near-surface`, `hero-presence`, `beyond`). The operator's directive — wards *swim in* the scrim — implies wards have **time-varying** depth, not static depth. A ward should be able to:

- enter the scrim from "beyond" (the camera-side),
- traverse the scrim's thickness over hundreds of milliseconds,
- emerge on the "surface" at full crispness,
- get *trapped* in the scrim and oscillate,
- dissolve back into the scrim.

This is not a contradiction — it's a *promotion* of Cluster 2's static depth-tag to a dynamic depth-position field. §6 below resolves this by formalising the swim grammar.

### 3.4 Where Cluster 2 aligns and accelerates

- The substrate framing (§5) is exactly right and this doc inherits it wholesale.
- The four-conceptual-layer model (scrim pass / behind / on / in-front) is the structural skeleton this doc's §6 swim grammar attaches to.
- The eight-phase sequencing is sound; this doc's §11 code-shapes slot into Phases 1, 2, 3, 8.
- Cluster 2's seven scrim-profiles (gauzy_quiet etc.) are *fabric-character* knobs; this doc's three permeability modes (semipermeable_membrane / solute_suspension / ionised_glow) are *ward-behavior* knobs. They are orthogonal axes that compose.

### 3.5 Implementation-hook map (Cluster 2 → existing code)

| Cluster 2 Phase | Code site | This doc relevance |
|----------------|-----------|--------------------|
| Phase 1 — `scrim_baseline` preset | `presets/` (e.g. `presets/reverie_vocabulary.json`) | §11.3 YAML |
| Phase 2 — `scrim_depth` tag on Source | `shared/compositor_model.py:44` `SourceKind` literal; `SurfaceSchema` at line 177 | §11.2 Pydantic |
| Phase 3 — atmospheric-perspective tint | `agents/shaders/nodes/colorgrade.wgsl` (per-source uniforms) | inherits |
| Phase 4 — differential blur | new node or reuse `agents/shaders/nodes/bloom.wgsl` mask | §11.1 WGSL |
| Phase 5 — programme→scrim envelope | `agents/studio_compositor/structural_director.py:86` `StructuralIntent` | §11.2 |
| Phase 7 — voice filter | `config/pipewire/voice-fx-*.conf` (per CLAUDE.md § Voice FX Chain) | inherits |
| Phase 8 — `scrim.pierce` intent | `agents/studio_compositor/homage/choreographer.py` (1027 lines), structural director | §6.4 |
| Phase 9 — new nodes | `agents/shaders/nodes/*.wgsl` (currently 56 nodes) | §11.1 |

The substrate-protocol pattern at `agents/studio_compositor/homage/substrate_source.py:36` (`HomageSubstrateSource` `Protocol` with `is_substrate: Literal[True]`) is the template for the recommended Option D registration.

---

## §4 Implementation Path Options

Four options, evaluated against latency, compositional flexibility, coupling to existing pipeline, and GPU budget.

### 4.1 Option A — New `scrim` pass in the Reverie wgpu graph

**Sketch.** Insert a new pass between `feedback` and `content_layer` (or between `content_layer` and `postprocess`) in the 8-pass vocabulary graph. The pass is a fragment shader sampling `tex` (the upstream composite) and a procedurally-generated fbm-noise field, applying refraction-coupled UV displacement, density modulation, color cast, and particulate noise.

**WGSL sketch:** see §11.1.

**Pros.**
- Fits the substrate invariant cleanly — Reverie is already the always-on substrate per `agents/studio_compositor/homage/substrate_source.py`'s `SUBSTRATE_SOURCE_REGISTRY = ("reverie_external_rgba", "reverie", "album")`. Adding a pass to its graph keeps it inside the FSM-bypass envelope (the choreographer skips substrate sources, per `substrate_source.py:14-17` rationale).
- Reuses the existing per-frame uniform bridge (`agents/reverie/_uniforms.py:_BITCHX_COLOR_*` HOMAGE A6 damping pattern is the template for `_SCRIM_*` damping).
- One GPU cost; one place to tune; one place to test.
- Per-node `params_buffer` infrastructure already exists (council CLAUDE.md § Reverie Vocabulary Integrity describes the path: `visual_chain.compute_param_deltas() → uniforms.json → dynamic_pipeline.rs`).

**Cons.**
- Couples scrim semantics tightly to Reverie's render pipeline — if Reverie ever needs to be replaced (e.g. a future non-wgpu surface), the scrim moves with it.
- Cairo wards composite *after* the scrim pass (cairo lives in the GStreamer compositor, not in Reverie); they can be drawn *over* the scrim but cannot be *swum through it* by the WGSL shader directly. (This is the reason the recommendation pairs A with D.)

**GPU cost estimate.** ~0.5–0.8ms at 1280×720 for fbm + refraction sample + color cast + particulate. Fits inside Cluster 2 §9.6's 1.5ms ceiling.

### 4.2 Option B — Compositor cairo overlay

**Sketch.** The scrim is a full-canvas Cairo source rendered on a background thread (per the `CairoSource` protocol at `agents/studio_compositor/cairo_source.py`), composited via blend modes onto the final frame.

**Pros.**
- Sits in the same layer as wards; trivial to make wards composite with scrim via cairo blend operators.
- Reusable rendering paradigm operators already understand.

**Cons.**
- Cairo cannot do real refraction (no per-fragment displacement); the scrim becomes a *texture* not a *medium*.
- Scrim becomes a layer applied OVER the substrate, not part of the substrate — directly contradicts Cluster 2 §5.4 ("substrate, not skin").
- 1280×720 cairo full-canvas updates are CPU-expensive; the budget tracker (`agents/studio_compositor/budget.py`) would have to absorb new full-canvas cost.

**Verdict.** Not recommended. Cluster 2 §5.4 already commits to "the composite *exists in* the scrim from the start"; Option B violates this.

### 4.3 Option C — Per-ward shader effect

**Sketch.** Each ward gets its own per-instance shader (refraction, blur, depth-of-field) parameterized by a `scrim_position` uniform.

**Pros.**
- Maximum per-ward expressivity. A ward can have unique scrim physics.

**Cons.**
- Explodes the maintenance surface across ~13 cairo source modules under `agents/studio_compositor/`. Each ward shipping its own shader is the opposite of consolidation.
- No single source of truth for scrim parameters — the scrim's apparent character would drift between wards.
- Violates the Cluster 2 §5.4 substrate commitment.

**Verdict.** Not recommended as the primary mechanism. Per-ward tuning *can* exist (`ward_permeability` per-ward override in §11.2), but the scrim itself stays single-sourced.

### 4.4 Option D — `ScrimSourceRegistry` substrate-protocol entry

**Sketch.** Register the scrim alongside Reverie in the substrate protocol (`HomageSubstrateSource` at `agents/studio_compositor/homage/substrate_source.py:36`). The scrim's *parameters* (density, refraction strength, hue shift, particulate amount, ward permeability) are exposed via `/dev/shm/hapax-compositor/scrim-state.json` (atomic write pattern matching `_publish` at `structural_director.py:123`). Cairo wards consume this state when computing their own composite blend.

**Pros.**
- Cairo wards can read the live scrim state without cross-process coupling.
- Substrate protocol pattern is proven (`SUBSTRATE_SOURCE_REGISTRY` in `substrate_source.py:53`).
- Adds the scrim as a *first-class governance surface* — a future spec amendment to add new substrate sources is the same pattern.

**Cons.**
- On its own, Option D doesn't render the scrim. It's an information bus, not a renderer.

**Verdict.** Recommended *as a complement to Option A*. Option A renders the scrim's pixels; Option D exposes the scrim's parameters so cairo wards know how to draw themselves with respect to the scrim's current state.

### 4.5 Recommendation

**Option A + Option D hybrid.**

- **Option A** delivers the visual scrim via a new wgpu pass in Reverie's vocabulary graph. WGSL fragment shader (§11.1) does fbm-warp + refraction + density + color cast + particulate.
- **Option D** delivers the scrim's *state vector* via `/dev/shm/hapax-compositor/scrim-state.json`. Cairo wards (which composite outside Reverie) read this state to align their own blend behavior to the scrim's current condition.

This split honors the §7 asymmetry: Reverie writes scrim *appearance* for the broadcast tee; the state vector lets cairo wards (which the operator monitor *also* sees) participate without forcing the operator to look at the broadcast scrim during studio work.

**Trade-off summary.**

| Option | Latency add | Compositional flexibility | Coupling | GPU budget | Recommended |
|--------|-------------|--------------------------|----------|------------|-------------|
| A — wgpu pass | ~0.5–0.8ms | High (per-pass uniforms) | Medium (Reverie) | Inside ceiling | **Yes** |
| B — cairo overlay | ~3–5ms (CPU) | Medium | Low | Doesn't apply (CPU) | No |
| C — per-ward shader | ~0.1ms × 13 wards | Very high | Very high | Marginal | Auxiliary only |
| D — state-bus registry | ~0ms (file I/O) | N/A (it's a bus) | Very low | None | **Yes** |

---

## §5 Visual Properties of the Scrim

These are the *axes the WGSL shader exposes* via the per-node Params struct. Each axis maps to a uniform field in §11.1.

### 5.1 Density

Opacity of the scrim in the Z direction. Range `0.0` (gone — disallowed in default state per Cluster 2 §9.1) to `1.0` (maximum opacity allowed by HOMAGE substrate invariant). Modulation sources: stimmung tension (high → denser), Programme mode (Listening = ~0.45, Hothouse = ~0.65, Wind-down = ~0.85), `scrim.pierce` intent (radial dip). All *soft priors* per `feedback_no_expert_system_rules`. Default baseline ~0.50.

### 5.2 Refraction strength

How much the scrim displaces UV samples of the upstream composite. Implementation: scale on the fbm-noise displacement applied to the underlying texture sample. Range `0.0` (no refraction) to `0.05` (extreme, distorts faces noticeably). Default ~0.012. Modulated by vinyl_chain.spray (granular wash → wavier scrim, +0.005 nudge per active spray channel) and ambient stimmung.

### 5.3 Color cast (hue shift)

Subtle hue rotation applied to upstream samples passing through the scrim. Implementation: HSV rotate after sampling. Range ±15° around the active HOMAGE package accent (Cluster 2 §9.9 — palette coherence). Default 0° (no extra cast beyond the existing colorgrade damping at `_BITCHX_COLOR_HUE_ROTATE = 180.0°` in `agents/reverie/_uniforms.py:37`).

### 5.4 Particulate noise

Dust, static, grain in the membrane itself. Implementation: high-frequency hash noise added to the alpha channel of the scrim layer. Range `0.0` (clean) to `0.3` (visible static). Default ~0.05. Programme-coupled: `moire_crackle` profile pushes to ~0.20.

### 5.5 Depth (apparent thickness)

Does the scrim itself read as 2D plane or as having depth? Implementation: parallax — the fbm domain-warp coordinate uses two octaves at slightly different time offsets, producing the felt "this medium has thickness" sensation. Range: `0.0` (single-octave, flat) to `1.0` (multi-octave with parallax). Default ~0.4. Inigo Quilez's domain-warping fbm ([iquilezles.org/articles/warp/](https://iquilezles.org/articles/warp/)) is the algorithmic template.

### 5.6 Permeability (per-ward override hook)

How easily a ward at `scrim_position = z` punches through the scrim. Range `0.0` (sealed — wards in the scrim cannot reach the surface) to `1.0` (porous — wards transit instantly). Default `0.5`. Per-ward overrides exposed in §11.2; programme-mode defaults in §1.

### 5.7 Self-motion

The scrim moves *independently* of wards and cameras. Implementation: time-driven advection of the fbm domain-warp coordinate. Speed `0.0` (frozen — disallowed; violates Cluster 2 §2.7.5) to `~0.3` (visibly drifting). Default ~0.08. Audio-coupled (§8) to MIDI clock for slow tempo-locked drift.

---

## §6 How Wards Swim in the Scrim — The Z-Axis Grammar

The operator's "wards swim in the scrim" directive is the heart of this dispatch. Cluster 2 §6's static depth bands become time-varying *positions* on a Z axis, with a state machine governing transitions.

### 6.1 The Z-axis

Every ward carries a `scrim_position` field — a real number in `[-1.0, +1.0]`:

- `scrim_position = -1.0` — **deep beyond.** Camera-side; behind the studio inhabitants' floor. Heavy refraction, atmospheric tint, contrast reduction.
- `scrim_position = -0.3` — **behind the scrim.** Cluster 2 "behind" depth band. Soft blur, light atmospheric tint.
- `scrim_position =  0.0` — **embedded in the scrim.** Maximum refraction wobble, maximum scrim-color cast. The "trapped" state.
- `scrim_position = +0.3` — **on-scrim surface.** Cluster 2 "surface" depth band. Crisp, full chroma.
- `scrim_position = +1.0` — **piercing through the scrim toward audience.** Cluster 2 "in-front-of-scrim". Glow halo on the audience side; reserved.

Default position per ward type (set in §11.2 schema):

| Ward type | Default scrim_position |
|-----------|----------------------|
| Camera PiPs | `-0.5` |
| `album_overlay` | `-0.5` |
| `sierpinski_renderer` | `-0.3` |
| Internal-state wards (`impingement_cascade`, etc.) | `-0.1` |
| Surface chrome (`captions_source`, `activity_header`, `chat_ambient`) | `+0.3` |
| `token_pole`, `hardm_dot_matrix` (avatars) | `+0.2` (straddles) |
| `research_marker_overlay` (when active) | `+0.5` |

### 6.2 Per-position visual transform

The scrim pass uses the ward's `scrim_position` to compute four derived values per fragment:

- **Refraction strength.** Bell curve peaking at `z=0` (embedded state has maximum wobble); falls to ~0 at `|z|=1`.
- **Opacity (toward the audience).** Sigmoidal: `z=-1` → 0.55 (heavily tinted), `z=0` → 0.75 (medium translucent), `z=+1` → 1.0 (fully opaque/crisp).
- **Motion-blur radius.** Coupled to `|dz/dt|` — wards in motion through the scrim acquire motion blur proportional to transit velocity. Static wards have zero motion blur regardless of position.
- **Color cast strength.** Linear in `|z|`; surface (`z=+0.3`) and beyond (`z=-1`) both lean into the scrim's color, but in opposite directions (surface = full chroma toward Hapax accent; beyond = desaturated toward atmospheric tint).

### 6.3 Lifecycle states

A ward has six lifecycle states with respect to the scrim:

```
   ┌─────────┐
   │ DORMANT │ ← scrim_position is None; ward not rendered
   └────┬────┘
        │ recruitment fires
        ▼
   ┌─────────┐
   │ ENTERING│ ← scrim_position interpolates from default deep-beyond toward target
   └────┬────┘
        │ position reaches target ± epsilon
        ▼
   ┌─────────┐
   │ HOLD    │ ← steady state at target position (default operating depth)
   └────┬────┘
        │ Programme mode change OR scrim.pierce intent OR explicit transit
        ▼
   ┌──────────┐         ┌──────────┐
   │ TRANSIT  │ ←────→  │ TRAPPED  │ ← oscillates around z=0 with slow wobble (~0.3 Hz)
   └────┬─────┘         └──────────┘
        │ position reaches new target
        ▼
   ┌─────────┐
   │ HOLD    │ (at new target)
   └────┬────┘
        │ retirement fires
        ▼
   ┌─────────┐
   │ EXITING │ ← scrim_position interpolates back toward dormant boundary
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │ DORMANT │
   └─────────┘
```

This maps onto the existing HOMAGE FSM (`agents/studio_compositor/homage/transitional_source.py` per CLAUDE.md HOMAGE Phase context: `ABSENT → ENTERING → HOLD → EXITING`) — extending it with `TRANSIT` and `TRAPPED` as scrim-specific states. ENTERING/HOLD/EXITING preserve their existing semantics; only TRANSIT and TRAPPED are new and only apply to scrim-aware sources (cameras, sierpinski, album, internal-state wards).

### 6.4 `scrim.pierce` — the explicit transit verb

Cluster 2 §8.3 defines `scrim.pierce` as a radial alpha modulation around Hapax's avatar. This dispatch generalises: `scrim.pierce` is the **transit-trigger intent**. It accepts:

- `target: WardId` — which ward to transit
- `from: float` — starting `scrim_position`
- `to: float` — ending `scrim_position`
- `duration_ms: int` — transit time
- `envelope: Literal["cosine", "ease_in_out", "linear", "spring"]` — interpolation curve

Default Hapax-greeting pierce: `target=token_pole, from=+0.2, to=+0.9, duration_ms=1500, envelope=cosine` then return; matches Cluster 2 §10.2.

### 6.5 Permeability profiles (the three Programme modes from §1)

The three permeability profiles named in §1 are *priors on `scrim_position` distribution* across all wards in the scene:

| Profile | Default-target distribution | Transit speed | Trapped-state probability |
|---------|----------------------------|---------------|--------------------------|
| `semipermeable_membrane` | Bimodal (`-0.5` cameras / `+0.3` chrome) | Medium (~600ms) | Low (~5%) |
| `solute_suspension` | Centered at `0.0` (everything embedded) | Slow (~1200ms) | High (~40%) |
| `ionised_glow` | Bimodal (`-0.5` cameras / `+0.7` chrome) | Fast (~250ms) | Zero |

These are not gates — the structural director still chooses per-ward target positions per Programme; the profile *biases* default behavior. Per `feedback_no_expert_system_rules`, deviation is allowed; the profile is the prior.

### 6.6 Edge dissolve

A ward whose `scrim_position` is near `0.0` (inside the scrim) acquires a soft edge — its alpha falls off radially from the bounding-box centroid. Implementation: cairo wards check `scrim_position` from the §11.2 state file and apply a per-render edge softening; wgpu wards (the satellite-shader ones) handle this via mask uniform.

### 6.7 The "swim" verb is metaphor-load-bearing

Wards do not literally swim. They **occupy time-varying positions on a Z axis whose physics is the scrim's permeability profile**. Per the maya/Lacanian framing of §2, the swimming is what the *viewer* perceives — the depth is in the seeing, not in the rendered geometry. The scrim is not a 3D fluid sim; it is a perceptual device whose motion grammar happens to read as fluid.

---

## §7 Asymmetry of Perception — The Broadcast Tee

This is the architectural invariant the Cluster 2 design implies but does not formalise. **The scrim exists for the broadcast viewer, not for the studio inhabitant.**

### 7.1 The two viewers

| Viewer | Sees |
|--------|------|
| **Broadcast viewer (YouTube)** | scrim + wards-through-scrim + Reverie-substrate behind |
| **Studio inhabitant (operator + collaborators)** | physical environment of the room; not the broadcast |
| **Operator monitor** | (decision below) |

The broadcast viewer's gaze passes *through* the scrim per the §2.4 Lacanian framing. The studio inhabitant's gaze does *not* — they see the room with their physical eyes, and the cameras/MPC/turntable/vinyl are physical objects in their visual field, not flat textures.

### 7.2 Why this matters architecturally

The scrim is *not part of the studio*. The compositor's output goes to `/dev/video42` (OBS V4L2 source) and HLS (per CLAUDE.md § Studio Compositor) — both consumed by the broadcast pipeline. The studio inhabitant interacts with the room. **The scrim must not be on a surface the operator looks at while doing studio work** (typing on the Keychron, manipulating the MPC, cueing the vinyl).

### 7.3 Operator-monitor decision

Three viable configurations:

- **A. Operator monitor = clean view (no scrim).** The operator sees what the studio looks like. The broadcast view (with scrim) lives on a separate surface (e.g. a small status panel in waybar, a secondary monitor, or the Logos preview pane).
- **B. Operator monitor = broadcast view (with scrim).** The operator sees what the audience sees. Stream Deck status / cue indicators must be on a non-scrim surface.
- **C. Hybrid.** Operator monitor shows clean view by default; can toggle to broadcast view via keybind for spot-checking.

**Recommendation: C, with default = clean.** The scrim is for the audience; the operator should not be looking at refracted wards when reading the stream-deck cue. Toggle is for the moments when the operator wants to see what the audience sees (e.g. before going live, or during ritual openings).

### 7.4 Implication for ward placement

Wards the operator wants studio-visible (Stream Deck status, audio cue indicators, MIDI clock readout, Hapax's spoken-text scrolling) must NOT depend on scrim transit to be visible. Two patterns:

- **Pattern 1: Render twice.** A ward registers two `Source` entries — one scrim-aware (for the broadcast), one non-scrim (for the operator monitor's clean view). Higher cost but cleanest semantics.
- **Pattern 2: Operator-only wards.** Some wards (Stream Deck status etc.) are *never* in the broadcast pipeline; they live only in the operator-monitor compositing tree. The operator monitor's compositor consumes a different `Layout` than the broadcast compositor.

**Recommendation: Pattern 2 for studio-control wards** (Stream Deck, MIDI clock, raw audio meters). **Pattern 1 for content wards** that legitimately appear on both surfaces (`activity_header`, `captions_source`).

### 7.5 The asymmetry is the design conceit

The system is *building a perceptual layer the studio doesn't see*. This is not a bug — it is the precise semantic of the scrim. The scrim is the audience's experience of the room; it is *not* the room. Per the Lacanian framing, the scrim is what the audience's gaze passes through to find a studio that the studio itself sees differently.

This is the design conceit. Honor it: don't leak the scrim into the studio; don't leak the studio's clean surfaces into the broadcast.

---

## §8 Audio Coupling

Cluster 2 §8 covers Hapax's voice cross-scrim. This dispatch extends to *all* audio→scrim couplings. All couplings are **soft priors** per `feedback_no_expert_system_rules` — no single audio signal deterministically drives a scrim parameter.

### 8.1 Coupling matrix

| Audio source | Scrim parameter | Coupling | Rationale |
|--------------|----------------|----------|-----------|
| **Stimmung tension** | `density` | `+0.20 × tension` (range +0..0.20) | High tension → denser scrim per §5.1 default |
| **Vinyl spray (vinyl_chain)** | `refraction_strength` | `+0.005 × spray_amount` per channel | Granular wash → wavier scrim per §5.2 |
| **MIDI clock (bar boundaries)** | `transit_trigger` (allows new pierce intents to fire on bar) | event-edge | Beat-locked transit per `project_vocal_chain` |
| **Active HOMAGE package palette** | `hue_shift` | replaces baseline color cast | Per §5.3 palette coherence |
| **Contact mic energy (Cortado MKIII)** | `particulate_amount` | `+0.05 × ema(energy, 2s)` | Tactile activity → scrim crackle |
| **DMN voice activity (vad_speech)** | `density` (radial dip near Hapax) | `-0.30 in 240px radius around token_pole` | Hapax addresses → fabric thins (Cluster 2 §8.3) |
| **Boredom signal** (per `project_exploration_signal`) | `self_motion` (slows) | `-0.02 × boredom_normalized` | Boredom → scrim decelerates (visible but quiet) |
| **Operator face-detected presence** | overall scrim envelope active | gating | Scrim only renders when operator present (consent-safe per Cluster 2 §9.7) |

### 8.2 Cross-modal soft priors, not chains

No audio signal deterministically sets any scrim value. Each is one input to a weighted sum that the structural director's per-tick mixing computes. The mixing weights default to those above; the structural director's LLM tick can override (within bounds) per `feedback_no_expert_system_rules`.

### 8.3 Rate-of-change limits

To prevent perceptible flicker, all scrim parameters are smoothed via a 250ms exponential moving average before reaching the WGSL pass. Hard-edge audio events (MIDI bar, vad_speech onset) are converted to *intent triggers* (which fire transit envelopes) rather than direct uniform writes.

### 8.4 No cycle_mode coupling

Per `feedback_no_cycle_mode`, scrim parameters never read `cycle_mode`. Working mode (`research`/`rnd`) per CLAUDE.md § Council-Specific Conventions is the only mode coupling and only governs palette per Cluster 2 §9.9.

---

## §9 Programme Primitive Integration

The scrim has its own Programme variants — the three modes from §1 (`semipermeable_membrane`, `solute_suspension`, `ionised_glow`) — that compose with the seven Cluster-2 fabric profiles.

### 9.1 The orthogonal axes

```
                 fabric profile (Cluster 2 §13)
                 gauzy_quiet   warm_haze   moire_crackle
permeability     ─────────────┼─────────────┼─────────────
mode             ▲           │            │
(this doc §1)    │ Listening │ Vinyl     │ Hothouse
semipermeable    │           │ showcase  │
─────────────────┼───────────┼───────────┼─────────────
solute_          │ Wind-down │ Interlude │ -
suspension       │           │           │
─────────────────┼───────────┼───────────┼─────────────
ionised_glow     │ Research  │ Ritual    │ -
                 │           │ open      │
```

7 fabric profiles × 3 permeability modes = 21 named scene operating points. Not all combinations are sensible; the structural director picks combinations bounded by the Cluster 2 §7 programme→scrim table.

### 9.2 Operator override: `panic_clear`

A new structural intent `scrim.panic_clear` immediately drops `density` to 0.0 for 2 seconds, then ramps back to baseline over 4 seconds. Use cases: technical failure clarity, demonetization risk callout, urgent safety information. Triggered via Stream Deck or keybind — operator-only, never director-initiated. The `density=0.0` exception to Cluster 2 §9.1's always-present rule is operator-authoritative; the director cannot exercise it.

### 9.3 Programme schema

Per §11.3 below, scrim Programmes are YAML files at `presets/scrim_programmes/{name}.yaml`. The structural director selects one per programme tick (90s cadence per `agents/studio_compositor/structural_director.py:177`).

### 9.4 Composition with fabric profiles

`StructuralIntent` (at `structural_director.py:86`) gains a new field `scrim_permeability: Literal["semipermeable_membrane", "solute_suspension", "ionised_glow"]`. The existing `preset_family_hint` field continues to govern the Cluster 2 fabric profile.

### 9.5 Coordination with the four fishbowl modes (Cluster 1 sibling research)

Cluster 1 (sibling research drop) describes four fishbowl modes. The scrim Programmes coordinate as follows (provisional pending Cluster 1 finalisation):

| Fishbowl mode | Scrim permeability prior |
|---------------|-------------------------|
| Listening | `semipermeable_membrane` |
| Inviting | `ionised_glow` |
| Working | `semipermeable_membrane` |
| Reverie | `solute_suspension` |

This is a **soft mapping**, not a hard binding. The fishbowl mode informs but does not gate the scrim Programme.

---

## §10 Anti-Anthropomorphization Invariants for the Scrim

Per `project_hardm_anti_anthropomorphization`: HARDM refuses face-iconography (no eyes, mouths, expressions). The scrim inherits this principle and extends it.

### 10.1 The scrim has no face

No fbm-noise pattern allowed to read as facial features. No symmetry axes that could be perceived as eye-pairs. No "expressions" — the scrim does not "smile" or "frown" via density patterning. This is enforced at WGSL review: any pattern term containing radial symmetry around two points within 30% of frame width must be regenerated or rejected.

### 10.2 The scrim is not a character

Operator language must NOT personify the scrim:

- **Bad:** "Hapax is feeling cloudy today" / "the scrim is moody" / "she's denser than usual."
- **Good:** "scrim density is 0.65" / "the BitchX package raises baseline density" / "the scrim is in `solute_suspension` mode."

The scrim's variation is *factual*: high stimmung → dense fog *because* the coupling matrix says so. NOT *narrative*. (This is the same discipline `feedback_scientific_register` applies to research docs.)

### 10.3 The scrim is not a container of faces

Cluster 2 §6 places `token_pole` and `hardm_dot_matrix` as "hero-presence wards" straddling the scrim. The scrim must not aggregate these into a single perceived face-locus. Per CLAUDE.md face-obscure pipeline (`agents/studio_compositor/face_obscure_integration.py`), camera-side faces are pixelated *before* the scrim; the scrim does not re-introduce face-iconography by aggregation.

### 10.4 The scrim does not gaze back

Per the §2.4 Lacanian framing, the gaze is *the viewer's*, structured by but not originating from the scrim. The scrim does not have a "viewing position." No shader effect should suggest the scrim is looking at the audience. (No "eye in the fog" effects, no centered radial pupil-like patterns.)

### 10.5 Asymmetry-without-character

The §7 broadcast/studio asymmetry is the scrim's *only* "perspective." It is structural, not characterial. The scrim does not "prefer" the broadcast viewer over the studio; it is *for* the broadcast viewer because of how the rendering pipeline is wired.

### 10.6 Enforcement at code review

Any PR adding a scrim shader pattern must pass a face-detection check: render 5 frames at default parameters, run InsightFace SCRFD face detection (already in the repo per CLAUDE.md § Bayesian Presence Detection — `operator_face` signal source). If any detection fires with confidence > 0.4, the pattern is rejected.

---

## §11 Concrete Code-Shapes

### 11.1 WGSL fragment for the scrim pass (Option A)

Path: `agents/shaders/nodes/scrim.wgsl` (new node).

```wgsl
struct Params {
    u_density: f32,            // 0.0 .. 1.0; per §5.1
    u_refraction: f32,         // 0.0 .. 0.05; per §5.2
    u_hue_shift: f32,          // -15.0 .. +15.0 degrees; per §5.3
    u_particulate: f32,        // 0.0 .. 0.3; per §5.4
    u_depth: f32,              // 0.0 .. 1.0; per §5.5 (parallax)
    u_self_motion: f32,        // 0.0 .. 0.3; per §5.7
    u_pierce_x: f32,           // pierce center x in [0,1]; per §6.4
    u_pierce_y: f32,           // pierce center y in [0,1]; per §6.4
    u_pierce_radius: f32,      // pierce radius in [0,0.5]; 0 = no pierce
    u_pierce_strength: f32,    // pierce density-dip in [0,1]
}

struct FragmentOutput { @location(0) fragColor: vec4<f32>, }

var<private> fragColor: vec4<f32>;
var<private> v_texcoord_1: vec2<f32>;

@group(1) @binding(0) var tex: texture_2d<f32>;        // upstream composite
@group(1) @binding(1) var tex_sampler: sampler;
@group(2) @binding(0) var<uniform> global: Params;

// Hash + value noise — see drift.wgsl for the canonical pattern.
fn hash(p: vec2<f32>) -> f32 {
    return fract(sin(dot(p, vec2<f32>(127.1, 311.7))) * 43758.547);
}

fn noise(p: vec2<f32>) -> f32 {
    let i = floor(p);
    let f = fract(p);
    let u = f * f * (vec2<f32>(3.0) - 2.0 * f);
    let a = hash(i);
    let b = hash(i + vec2<f32>(1.0, 0.0));
    let c = hash(i + vec2<f32>(0.0, 1.0));
    let d = hash(i + vec2<f32>(1.0, 1.0));
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

// fBm — Inigo Quilez fbm article + Book of Shaders ch.13 template.
// 4 octaves; gain 0.5; lacunarity 2.0.
fn fbm(p: vec2<f32>) -> f32 {
    var v = 0.0;
    var a = 0.5;
    var q = p;
    for (var i = 0; i < 4; i = i + 1) {
        v = v + a * noise(q);
        q = q * 2.0;
        a = a * 0.5;
    }
    return v;
}

fn main_1() {
    let uv = v_texcoord_1;
    let t = uniforms.time * global.u_self_motion;

    // Domain-warped fbm — Inigo Quilez warp pattern.
    // q is a low-frequency offset that drives r (the actual scrim density field).
    let q = vec2<f32>(
        fbm(uv * 3.0 + vec2<f32>(t, 0.0)),
        fbm(uv * 3.0 + vec2<f32>(0.0, t * 1.2)),
    );
    let scrim_field = fbm(uv * 5.0 + q * global.u_depth + vec2<f32>(t * 0.3));

    // Refraction — sample upstream composite at displaced UV.
    let disp = (q - vec2<f32>(0.5)) * global.u_refraction;
    let upstream = textureSample(tex, tex_sampler, uv + disp);

    // Pierce — radial alpha modulation around pierce center.
    let pierce_dist = length(uv - vec2<f32>(global.u_pierce_x, global.u_pierce_y));
    let pierce_mask = select(
        0.0,
        smoothstep(global.u_pierce_radius, 0.0, pierce_dist) * global.u_pierce_strength,
        global.u_pierce_radius > 0.0,
    );
    let effective_density = global.u_density * (1.0 - pierce_mask);

    // Particulate noise — add high-frequency static.
    let particulate = (hash(uv * 1024.0 + vec2<f32>(t * 7.0)) - 0.5) * global.u_particulate;

    // Hue shift — rotate upstream sample's hue by u_hue_shift degrees.
    // Cheap channel rotation; full HSV would cost more.
    let hue_rad = radians(global.u_hue_shift);
    let cos_h = cos(hue_rad);
    let sin_h = sin(hue_rad);
    let shifted = vec3<f32>(
        upstream.r * cos_h - upstream.g * sin_h,
        upstream.r * sin_h + upstream.g * cos_h,
        upstream.b,
    );

    // Composite — scrim density mixes upstream toward scrim_field gray + particulate.
    let scrim_color = vec3<f32>(scrim_field) + vec3<f32>(particulate);
    let composited = mix(shifted, scrim_color, effective_density * 0.4);

    fragColor = vec4<f32>(composited, 1.0);
}

@fragment
fn main(@location(0) v_texcoord: vec2<f32>) -> FragmentOutput {
    v_texcoord_1 = v_texcoord;
    main_1();
    return FragmentOutput(fragColor);
}
```

This is a sketch — the actual WGSL transpiler emits a slightly different form (see `agents/shaders/nodes/drift.wgsl` line 21 for the canonical hash/noise pattern after transpiler emission). The Params struct field order matches the transpiler's positional binding (per CLAUDE.md § Reverie Vocabulary Integrity: "param_name must match WGSL Params struct field order").

### 11.2 Pydantic schema for `ScrimState`

Path: `shared/scrim_model.py` (new module).

```python
"""Scrim state — the per-tick parameter vector consumed by the scrim WGSL pass
and read by cairo wards (Option D state-bus per scrim research §4.4).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PermeabilityProfile = Literal[
    "semipermeable_membrane",  # default; bimodal swim
    "solute_suspension",       # everything embedded; oscillating
    "ionised_glow",            # crisp transit; back-glow halo
]


FabricProfile = Literal[
    "gauzy_quiet",
    "warm_haze",
    "moire_crackle",
    "clarity_peak",
    "dissolving",
    "ritual_open",
    "rain_streak",
]


class WardScrimPosition(BaseModel):
    """Per-ward Z position + permeability override."""
    model_config = ConfigDict(extra="forbid")

    ward_id: str
    scrim_position: float = Field(0.0, ge=-1.0, le=1.0)
    permeability_override: float | None = Field(None, ge=0.0, le=1.0)
    lifecycle: Literal[
        "DORMANT", "ENTERING", "HOLD", "TRANSIT", "TRAPPED", "EXITING"
    ] = "HOLD"


class ScrimPierce(BaseModel):
    """Active pierce intent — radial density-dip around a target ward."""
    model_config = ConfigDict(extra="forbid")

    target_ward_id: str
    center_x: float = Field(..., ge=0.0, le=1.0)
    center_y: float = Field(..., ge=0.0, le=1.0)
    radius: float = Field(..., ge=0.0, le=0.5)
    strength: float = Field(..., ge=0.0, le=1.0)
    started_at: float
    duration_ms: int = Field(..., gt=0, le=8000)
    envelope: Literal["cosine", "ease_in_out", "linear", "spring"] = "cosine"


class ScrimState(BaseModel):
    """Per-tick scrim state. Atomically published to
    /dev/shm/hapax-compositor/scrim-state.json; consumed by WGSL pass
    (uniform mapping in agents/reverie/_uniforms.py) and cairo wards.

    All fields are SOFT priors per feedback_no_expert_system_rules — the
    structural director can override within bounds; nothing is gated.
    """
    model_config = ConfigDict(extra="forbid")

    # Core visual properties — per §5
    density: float = Field(0.50, ge=0.0, le=1.0)
    refraction_strength: float = Field(0.012, ge=0.0, le=0.05)
    hue_shift_degrees: float = Field(0.0, ge=-15.0, le=15.0)
    particulate_amount: float = Field(0.05, ge=0.0, le=0.30)
    depth_parallax: float = Field(0.4, ge=0.0, le=1.0)
    self_motion: float = Field(0.08, ge=0.0, le=0.30)

    # Programme axes
    fabric_profile: FabricProfile = "gauzy_quiet"
    permeability_profile: PermeabilityProfile = "semipermeable_membrane"

    # Ward positions (Z axis per §6.1)
    ward_positions: list[WardScrimPosition] = Field(default_factory=list)

    # Active pierces (per §6.4)
    active_pierces: list[ScrimPierce] = Field(default_factory=list)

    # Provenance
    emitted_at: float
    structural_intent_id: str | None = None
    operator_panic_clear: bool = False  # §9.2 panic_clear override
```

### 11.3 Programme YAML for the three scrim variants

Path: `presets/scrim_programmes/`.

```yaml
# presets/scrim_programmes/semipermeable_membrane.yaml
name: semipermeable_membrane
description: |
  Default permeability profile. Wards transit gradually; behind→surface
  takes ~600ms with refraction falloff. Bimodal default-target distribution:
  cameras at -0.5, chrome wards at +0.3.

defaults:
  density: 0.50
  refraction_strength: 0.012
  hue_shift_degrees: 0.0
  particulate_amount: 0.05
  depth_parallax: 0.4
  self_motion: 0.08

ward_position_priors:
  cameras: -0.5
  album_overlay: -0.5
  sierpinski_renderer: -0.3
  internal_state_wards: -0.1
  surface_chrome: +0.3
  hapax_avatars: +0.2
  research_marker: +0.5

transit_speed_ms: 600
trapped_state_probability: 0.05

permitted_pierces:
  hapax_greeting: { radius: 0.20, strength: 0.7, duration_ms: 1500 }
  programme_change: { radius: 0.15, strength: 0.5, duration_ms: 800 }
  research_marker_callout: { radius: 0.18, strength: 0.6, duration_ms: 1200 }
```

```yaml
# presets/scrim_programmes/solute_suspension.yaml
name: solute_suspension
description: |
  Wards diffuse into the scrim and remain trapped, oscillating in place.
  High density, refraction wobble at ~0.3 Hz. For interludes and
  listening passages.

defaults:
  density: 0.70
  refraction_strength: 0.025
  hue_shift_degrees: 0.0
  particulate_amount: 0.15
  depth_parallax: 0.7
  self_motion: 0.04

ward_position_priors:
  cameras: -0.1
  album_overlay: 0.0
  sierpinski_renderer: 0.0
  internal_state_wards: -0.05
  surface_chrome: +0.1
  hapax_avatars: 0.0
  research_marker: +0.3

transit_speed_ms: 1200
trapped_state_probability: 0.40
trapped_oscillation_hz: 0.3

permitted_pierces:
  hapax_greeting: { radius: 0.30, strength: 0.5, duration_ms: 2200 }
  programme_change: { radius: 0.20, strength: 0.4, duration_ms: 1500 }
```

```yaml
# presets/scrim_programmes/ionised_glow.yaml
name: ionised_glow
description: |
  Wards punch through cleanly and sit in front of the scrim with crisp
  edges and a back-glow halo. For research markers, hero callouts, and
  ritual openings.

defaults:
  density: 0.60
  refraction_strength: 0.008
  hue_shift_degrees: 0.0
  particulate_amount: 0.02
  depth_parallax: 0.3
  self_motion: 0.05

ward_position_priors:
  cameras: -0.5
  album_overlay: -0.3
  sierpinski_renderer: -0.2
  internal_state_wards: 0.0
  surface_chrome: +0.7
  hapax_avatars: +0.5
  research_marker: +0.8

transit_speed_ms: 250
trapped_state_probability: 0.0

# Ionised_glow wards get a back-glow halo (handled by bloom node parameterised
# off scrim_position; bloom radius scales with abs(scrim_position - target)).
back_glow_enabled: true

permitted_pierces:
  hapax_greeting: { radius: 0.15, strength: 0.85, duration_ms: 1000 }
  programme_change: { radius: 0.10, strength: 0.6, duration_ms: 600 }
  research_marker_callout: { radius: 0.20, strength: 0.9, duration_ms: 1500 }
  ritual_open: { radius: 0.40, strength: 0.95, duration_ms: 3500 }
```

### 11.4 State diagram for "ward swims through scrim" lifecycle

See §6.3 above — the 6-state FSM (`DORMANT → ENTERING → HOLD → (TRANSIT|TRAPPED) → HOLD → EXITING → DORMANT`). Implementation extends the existing `agents/studio_compositor/homage/transitional_source.py` 4-state FSM by adding `TRANSIT` and `TRAPPED` as scrim-specific extensions. Existing wards (per Cluster 2 §6 ward inventory) inherit ENTERING/HOLD/EXITING semantics; only scrim-aware wards opt into TRANSIT/TRAPPED via a new `scrim_aware: bool = False` field on the cairo source registration.

---

## §12 Open Questions

1. **Operator-monitor view default.** §7.3 recommends C (clean, toggle to broadcast). Does the operator concur, or prefer A or B?
2. **Pierce-cadence rate.** §6.4 gives Hapax-greeting pierce parameters; §8.1 lists vad_speech as the trigger. Cadence could be per-utterance (frequent) or rate-limited to once per ~90s (Cluster 2 §8.3 default). Cluster 2 recommended rare-ritual; this dispatch concurs but flags for confirmation.
3. **Scrim-state schema versioning.** §11.2's `ScrimState` will evolve as fabric profiles and permeability profiles get added. Migration strategy needed (soft-add fields with defaults? hard schema bump with handoff?).
4. **Per-ward `scrim_aware` migration path.** §11.4 introduces `scrim_aware: bool = False` on cairo sources. Default-False preserves current behavior, but the eventual goal is most content-bearing wards (`album_overlay`, `sierpinski_renderer`, internal-state wards) opt in. What's the migration sequencing — by ward, by Programme, all-at-once?
5. **Anti-anthropomorphization enforcement at PR-time.** §10.6 proposes InsightFace check on rendered scrim frames. Should this be a CI gate, a pre-merge advisory, or both?
6. **Cluster 1 fishbowl-mode binding.** §9.5 gives provisional mappings. Need Cluster 1 finalisation to confirm.
7. **Programme YAML location.** §11.3 puts the three Programmes at `presets/scrim_programmes/`. Should this directory live under `presets/` (alongside reverie presets) or under `agents/studio_compositor/scrim/` (alongside structural director)? Probably `presets/` — keeps the artist-editable concerns in one place.
8. **5-channel mixer integration.** Per `project_reverie_adaptive`, operator's adaptive direction work has 5 channels (RD/Physarum/Voronoi/feedback/noise). How does the scrim fabric profile compose with the mixer's channel selection? Cluster 2 §12.6 raised this; this dispatch defers.

---

## §13 Sources

### Internal — codebase

- `docs/research/2026-04-20-nebulous-scrim-design.md` — Cluster 2 design (extended, not duplicated, by this dispatch)
- `docs/superpowers/specs/2026-04-18-homage-framework-design.md` — HOMAGE framework, Phase A6 substrate invariant
- `docs/logos-design-language.md` — visual surface authority document
- `agents/reverie/_uniforms.py:36-38` — `_BITCHX_COLOR_*` damping pattern (template for scrim damping)
- `agents/reverie/_uniforms.py:44-58` — `_iter_passes` v1/v2 plan schema handler
- `agents/studio_compositor/homage/substrate_source.py:36` — `HomageSubstrateSource` Protocol; `:53` `SUBSTRATE_SOURCE_REGISTRY`
- `agents/studio_compositor/homage/choreographer.py` (1027 lines) — HOMAGE FSM ABSENT/ENTERING/HOLD/EXITING dispatcher
- `agents/studio_compositor/structural_director.py:86` — `StructuralIntent` Pydantic model; `:177` cadence
- `agents/studio_compositor/cairo_source.py` — `CairoSource` protocol + `CairoSourceRunner`
- `agents/studio_compositor/face_obscure_integration.py` — pre-scrim face-obscure pipeline (Cluster 2 §9.4)
- `shared/compositor_model.py:44-54` `SourceKind`; `:71-85` `SurfaceKind`; `:177` `SurfaceSchema`; `:195` `Assignment`; `:223` `Layout`
- `agents/shaders/nodes/drift.wgsl:21-67` — canonical hash/noise WGSL pattern (template for §11.1 scrim shader)
- `agents/shaders/nodes/displacement_map.wgsl` — UV displacement template
- `agents/shaders/nodes/breathing.wgsl` — temporal pulsation template
- `agents/effect_graph/wgsl_compiler.py` — WGSL plan compiler, v2 target schema
- `gst-plugin-glfeedback/src/glfeedback/imp.rs` — GL temporal feedback filter
- `presets/reverie_vocabulary.json` — vocabulary preset (anchor for scrim_baseline preset)
- Council CLAUDE.md § Reverie Vocabulary Integrity — per-node `params_buffer` bridge
- Council CLAUDE.md § Voice FX Chain — `config/pipewire/voice-fx-*.conf` (Cluster 2 §8.1 voice-fx-scrim)
- Council CLAUDE.md § Studio Compositor — pipeline architecture, `/dev/video42` egress
- Memory `project_hardm_anti_anthropomorphization` — face-iconography invariant
- Memory `feedback_no_expert_system_rules` — soft priors not hard gates
- Memory `feedback_grounding_exhaustive` — every move grounded
- Memory `feedback_no_cycle_mode` — only working_mode, no cycle_mode
- Memory `project_720p_commitment` — never propose resolution changes

### External — theatrical scrim

- [Theatrecrafts — Lighting with a Gauze / Scrim](https://theatrecrafts.com/pages/home/topics/lighting/lighting-gauze-scrim/)
- [Charles H. Stewart — How to Light a Scrim](https://charleshstewart.com/blog/how-to-light-a-scrim/)
- [Georgia Stage — Sharkstooth Scrim Special Effects](https://gastage.com/149-sharkstooth-scrim-special-effects)
- [Sew What Inc — The Magic of Sharkstooth Scrim](https://sewwhatinc.com/blog/2015/08/20/the-magic-of-sharkstooth-scrim/)
- [Wikipedia — Scrim (material)](https://en.wikipedia.org/wiki/Scrim_(material))
- [ShowTex — Making Magic with Scrim Projections](https://www.showtex.com/en/blog/buyers-guide-fabrics/making-magic-scrim-projections)
- [Salon Privé — Sharkstooth Scrim, A Dramatic Stage Element](https://www.salonprivemag.com/sharkstooth-scrim-a-dramatic-stage-element/)

### External — media theory & philosophy

- [Marshall McLuhan — Understanding Media (1964) — The Medium is the Message (PDF)](https://web.mit.edu/allanmc/www/mcluhan.mediummessage.pdf)
- [Wikipedia — The medium is the message](https://en.wikipedia.org/wiki/The_medium_is_the_message)
- [Wikipedia — Understanding Media](https://en.wikipedia.org/wiki/Understanding_Media)
- [Lacan, "Of the Gaze as Objet Petit a" — DS Project deciphering](https://thedsproject.com/portfolio/deciphering-the-gaze-in-lacans-of-the-gaze-as-objet-petit-a/)
- [Lacan on Gaze (IJHSS PDF)](https://ijhss.thebrpi.org/journals/Vol_5_No_10_1_October_2015/15.pdf)
- [Hito Steyerl — abstract & diffraction (Frames Cinema Journal)](https://framescinemajournal.com/article/facing-off-from-abstraction-to-diffraction-in-hito-steyerls-abstract-2012/)
- [Hito Steyerl — Wikipedia](https://en.wikipedia.org/wiki/Hito_Steyerl)
- [Trevor Paglen — Invisible Images: Your Pictures Are Looking at You (Wiley AD)](https://onlinelibrary.wiley.com/doi/abs/10.1002/ad.2383)
- [Trevor Paglen — A Study of Invisible Images (Brooklyn Rail)](https://brooklynrail.org/2017/10/artseen/TREVOR-PAGLEN-A-Study-of-Invisible-Things/)
- [Wikipedia — Distancing effect (Verfremdungseffekt)](https://en.wikipedia.org/wiki/Distancing_effect)
- [Wikipedia — Maya (religion)](https://en.wikipedia.org/wiki/Maya_(religion))
- [Hindu Website — Understanding Maya in Hindu Philosophy](https://www.hinduwebsite.com/hinduism/essays/maya.asp)
- [Britannica — Maya (Vedic, Upanishads, Yoga)](https://www.britannica.com/topic/maya-Indian-philosophy)
- [Wikipedia — Shoji](https://en.wikipedia.org/wiki/Shoji)
- [Japan Objects — Complete Guide to Japanese Paper Screens](https://japanobjects.com/features/shoji)
- [Stan Brakhage — Mothlight (Wikipedia)](https://en.wikipedia.org/wiki/Mothlight)
- [Artforum — J. Hoberman on Brakhage's Mothlight](https://www.artforum.com/features/j-hoberman-on-stan-brakhages-mothlight-200839/)

### External — shader graphics references

- [The Book of Shaders ch.13 — Fractal Brownian Motion](https://thebookofshaders.com/13/)
- [The Book of Shaders ch.11 — Noise](https://thebookofshaders.com/11/)
- [Inigo Quilez — fBm article](https://iquilezles.org/articles/fbm/)
- [Inigo Quilez — Domain Warping](https://iquilezles.org/articles/warp/)
- [Cogs and Levers — Volumetric Fog in Shaders](https://tuttlem.github.io/2025/02/03/volumetric-fog-in-shaders.html)
- [NVIDIA Developer — Volumetric Light Scattering as a Post-Process](https://developer.nvidia.com/gpugems/gpugems3/part-ii-light-and-shadows/chapter-13-volumetric-light-scattering-post-process)
- [NVIDIA Developer — Generic Refraction Simulation (GPU Gems 2 ch.19)](https://developer.nvidia.com/gpugems/gpugems2/part-ii-shading-lighting-and-shadows/chapter-19-generic-refraction-simulation)
- [Maxime Heckel — Refraction, dispersion, and other shader light effects](https://blog.maximeheckel.com/posts/refraction-dispersion-and-other-shader-light-effects/)
- [Maxime Heckel — Real-time dreamy Cloudscapes with Volumetric Raymarching](https://blog.maximeheckel.com/posts/real-time-cloudscapes-with-volumetric-raymarching/)
- [80.lv — Unity Shader Guide for Glass Refraction & Distortion](https://80.lv/articles/making-stunning-glass-refraction-effects-in-unity)
- [Codrops — Real-time Multiside Refraction in Three Steps](https://tympanus.net/codrops/2019/10/29/real-time-multiside-refraction-in-three-steps/)
- [Linden Reid — Heat Distortion Shader Tutorial](https://lindenreidblog.com/2018/03/05/heat-distortion-shader-tutorial/)
- [Game Dev Bill — Heat Haze Shader Graph How-To](https://gamedevbill.com/heat-haze-shader-graph/)
- [Wolfire Games Blog — Screen-space distortion](http://blog.wolfire.com/2006/03/screen-space-distortion/)
- [WebGPU Fundamentals — WGSL](https://webgpufundamentals.org/webgpu/lessons/webgpu-wgsl.html)
- [W3C — WebGPU Shading Language (WGSL)](https://www.w3.org/TR/WGSL/)
- [Catlike Coding — Depth of Field (Unity)](https://catlikecoding.com/unity/tutorials/advanced-rendering/depth-of-field/)
- [Lettier — Depth of Field (3D Game Shaders for Beginners)](https://lettier.github.io/3d-game-shaders-for-beginners/depth-of-field.html)
- [Wikipedia — Parallax scrolling](https://en.wikipedia.org/wiki/Parallax_scrolling)
- [Pixelnest — Parallax scrolling tutorial](https://pixelnest.io/tutorials/2d-game-unity/parallax-scrolling/)
- [Webflow Blog — Parallax scrolling: 10 examples](https://webflow.com/blog/parallax-scrolling)

---
