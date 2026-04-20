# HOMAGE × Scrim — Dispatch 1: Algorithmic Intelligence for Ward Placement

**Status:** Research / design, operator-directed 2026-04-20.
**Author:** alpha (Claude Opus 4.7, 1M).
**Governing anchors:**
- HOMAGE framework (`docs/superpowers/specs/2026-04-18-homage-framework-design.md`)
- Nebulous Scrim design (`docs/research/2026-04-20-nebulous-scrim-design.md`)
- Programme primitive (`shared/programme.py`)
- Affordance pipeline (`shared/affordance_pipeline.py`, `shared/affordance.py`)
- Logos design language (`docs/logos-design-language.md`)
**Memory anchors:** `feedback_no_expert_system_rules`, `project_programmes_enable_grounding`, `project_hardm_anti_anthropomorphization`, `feedback_grounding_exhaustive`, `feedback_director_grounding`, `reference_wards_taxonomy`.
**Scope:** Architectural research and a sequenced design proposal for the **algorithmic intelligence** that places non-substrate wards (token-pole, album, sierpinski, HARDM, all pango overlays, PiPs) inside the compositor frame and times their interactions with the Nebulous Scrim. No code merged here — this is the substrate that subsequent dispatches (visual taxonomy, Programme catalog, integration epic) build on.

> "Wards 'play' in that scrim like layers in a fishbowl."
> — operator brief, 2026-04-20

---

## §1. TL;DR

**Frame.** Ward placement should not be an authored grammar (a rule book) and not an unconstrained optimization (a global utility). It is the **emergent side-effect of unified semantic recruitment running under a Programme-supplied soft-prior envelope**, with a thin **composition-feasibility filter** sitting between the choreographer's planning slice and the compositor's render slice. Programmes give the *flavor* of the fishbowl. The affordance pipeline still picks *which* wards activate. A small placement post-pass picks *where* on the surface they go and *how they animate*. No expert-system rules about cadence. No central planner that names a placement. The intelligence is in the layered product of soft priors, scoring, and per-ward affordance-bound spatial affinities — exactly the same architecture by which the daimonion already speaks.

**Substrate.** Extend the Programme `ConstraintEnvelope` with a **`scrim_mode_priors`** sub-model that names a `fishbowl_mode` plus four spatial soft-prior fields (`composition_priors`, `motion_priors`, `attention_zones`, `depth_grammar`). Each ward declares a **`WardSpatialAffordance`** describing where on the scrim it likes to live, how fast it likes to drift, what its depth band is, and which other wards it pushes/pulls. The choreographer's existing `reconcile()` slice gains a **placement post-pass** that resolves the planned moves into `(x, y, scale, opacity, drift_velocity, depth_band)` tuples by composing these inputs.

**Four fishbowl modes** (the operator-facing names; soft priors only, never hard gates):

1. **`deep-water`** — slow drift, deep depth bands, low attention demand, high negative space, breath-paced cadence. The default at calm stretches and during operator-deep-focus stimmung.
2. **`shallows`** — frequent transit, shallow depth bands, multiple wards entering / exiting, moderate emphasis rate. The "active conversation" mode.
3. **`current`** — beat-locked motion, rhythmic ward phrasing aligned to vinyl phase, cross-ward coordination as percussion ensemble. The vinyl / music mode.
4. **`still-pool`** — minimal motion, single hero ward held long, deep negative space, almost-static surface. The contemplative / wind-down mode.

These four are a starting taxonomy, not a closed set; Programmes may name new modes by composing the four spatial priors directly.

**Three operator next-actions** (head of §12):

- Land the `WardSpatialAffordance` Pydantic model and a registry mapping every existing ward source_id to its declared affordance, before any algorithm changes.
- Extend `ProgrammeConstraintEnvelope` with `scrim_mode_priors` + a strict-positive validator (matches the existing soft-prior axiom).
- Add a `placement_postpass` to `Choreographer.reconcile()` that emits a `WardPlacementPlan` to a new SHM file, with the compositor's animation engine consuming it. Behind a default-off feature flag for one livestream cycle of empirical observation.

---

## §2. What "intelligent placement" means — paradigms and chosen frame

Four frames are live in the literature; this section catalogs each, explains why each alone is insufficient, and then states the chosen hybrid.

### 2.1 Constraint-satisfaction view

Ward placement as a Cassowary-style linear constraint problem ([Badros et al. 2001](https://constraints.cs.washington.edu/solvers/cassowary-tochi.pdf)). Composition rules are encoded as required and preferred constraints; the solver finds a layout satisfying them. iOS Auto Layout, Apple's interface layout system, and a handful of Servo-internal styling passes use this approach ([Cassowary — Wikipedia](https://en.wikipedia.org/wiki/Cassowary_(software)); [Servo Layout Overview](https://github.com/servo/servo/wiki/Layout-Overview)).

**Strengths:** Deterministic, testable, declarative. Composition rules become *the* model.

**Weaknesses:** Requires the rules to be authored. Hapax's architectural axiom (`feedback_no_expert_system_rules`) explicitly forbids this. Hardcoded composition gates would be the visual twin of the cadence/threshold gates we already refuse for cognition.

### 2.2 Optimization view

Ward placement as a global utility function over (ward, x, y, scale, opacity, depth) tuples; solved by gradient descent or simulated annealing ([Davidson & Harel 1996](https://dl.acm.org/doi/pdf/10.1145/234535.234538) on graph drawing via SA; [UCLA siggraph11 furniture](https://web.cs.ucla.edu/~dt/papers/siggraph11/siggraph11.pdf) on furniture arrangement via Metropolis-Hastings). The utility function aggregates rule-of-thirds proximity, attention-budget conformance, depth-band balance, motion smoothness, etc.

**Strengths:** Smooth gradient over a large continuous space; can produce visually balanced layouts.

**Weaknesses:** The utility function is itself an authored rule set. A naive utility produces a *consensus* layout — every ward equally well-placed — which reads as visual mush. Worse, optimization-as-rendered runs every frame and would interact badly with the compositor's per-frame budget tracker (`agents/studio_compositor/budget.py`).

### 2.3 Affordance-pipeline view

Each ward placement is itself an affordance, recruited under a Programme. The affordance carries spatial-affinity metadata; recruitment scores against impingement; the winner activates with its declared spatial behavior. No central placement planner. This is the **architecture-pure** answer and it matches every other behavioral surface in Hapax — voice, perception, capability invocation.

**Strengths:** Architecturally consistent. Soft priors via Programme. No expert-system rules. Already-built scoring/learning machinery (Thompson sampling, Hebbian context boosts, exploration noise) applies.

**Weaknesses:** Two wards both winning recruitment can collide spatially. Recruitment doesn't know about the Choreographer's max-simultaneous-entries cap, and the Choreographer doesn't know about ward-to-ward push/pull. These need a coordination layer.

### 2.4 Hybrid (chosen)

**Composition rules act as soft priors carried by Programmes.** Each Programme declares spatial preferences via its `scrim_mode_priors`. **Recruitment is the recruiter** — the affordance pipeline still does its job, scoring, picking, learning. **The Choreographer enforces composition-feasibility** in a thin post-pass that takes the *planned* set of recruited wards plus their declared `WardSpatialAffordance`s plus the active Programme's `scrim_mode_priors` and resolves them into final `(x, y, scale, opacity, drift_velocity, depth_band)` tuples. The post-pass is local (composes already-recruited wards), small (no global utility), and fast (one tick of solver work bounded by max-simultaneous-entries).

This is the same shape the cognitive stack already uses: a soft-prior envelope (Programme), a scoring stage (AffordancePipeline.select), a feasibility filter (consent gate, monetization gate, choreographer concurrency cap), and a render-side actuator (compositor). Adding a placement post-pass extends the pattern; it does not break it.

**Reference-frame analogy.** The placement post-pass is to ward layout what the **monetization gate** ([`shared/governance/monetization_safety.py`](file:///home/hapax/projects/hapax-council/shared/governance/monetization_safety.py)) is to capability availability: a thin filter between recruitment and execution that respects soft-prior intent without becoming a hard rule book.

---

## §3. Composition rules — cinematography and UI design literature

Composition rules in the chosen frame are **inputs to soft priors**, never gates. This section catalogs the literature so that Programme authors (Hapax, not the operator — see `feedback_hapax_authors_programmes`) can compose plausible priors. Eight families:

### 3.1 Rule of thirds and the F-pattern

The 3×3 grid placement rule is the most widely-cited compositional heuristic in both photography and UI design ([Interaction Design Foundation — Rule of Thirds](https://ixdf.org/literature/topics/rule-of-thirds); [UX Design Institute guide to rule of thirds](https://www.uxdesigninstitute.com/blog/guide-to-the-rule-of-thirds-in-ux/)). Eyes scan an image roughly in an F-shape, with the top-left "sweet spot" receiving the most attention. For broadcast surfaces specifically (`docs/research/2026-04-20-nebulous-scrim-design.md` §4), placing wards on the four 1/3 intersections produces felt-balanced compositions.

**Hapax mapping.** A `composition_priors` field with attractor weights at the four 1/3 intersections and reduced weight near the geometric center (which collides with the hero camera position).

### 3.2 Golden ratio (1.618:1)

Used historically for visual hierarchy and proportion ([Figma — Golden Ratio](https://www.figma.com/resource-library/golden-ratio/); [LogRocket — golden ratio in UX](https://blog.logrocket.com/ux-design/using-the-golden-ratio-in-ux-design/)). For 1920×1080, the golden-section vertical line sits at x ≈ 1186, the horizontal at y ≈ 668. Placing the dominant ward near a golden-section line and the secondary near a 1/3 line produces a felt-richer composition than pure rule-of-thirds alone ([iMark Infotech comparison](https://www.imarkinfotech.com/rule-of-thirds-vs-golden-ratio-in-ux-ui-design-a-comparison/)).

### 3.3 Visual weight and balance (Bruce Block)

Bruce Block, *The Visual Story* ([Routledge edition](https://www.routledge.com/The-Visual-Story-Creating-the-Visual-Structure-of-Film-TV-and-Digital-Media/Block/p/book/9781138014152); [Internet Archive copy](https://archive.org/details/visualstorycreat0000bloc)), develops the **Principle of Contrast & Affinity** across seven visual components: space, line, shape, tone, color, movement, rhythm. The most intense lines are diagonals, then verticals, then horizontals. Visual progression — gradually intensifying contrast — is how musical-style buildup translates to image. Block's work was developed at USC's Sergei Eisenstein Endowed Chair and codifies what Pixar, Disney, ILM and Dreamworks teach.

**Hapax mapping.** A ward's `motion_priors` describe its movement intensity (drift velocity range, vibration amplitude). A Programme's `scrim_mode_priors` can bias toward high-contrast (active wards on diagonals, fast drift) or affinity (low-contrast, parallel verticals, slow drift). HOMAGE-mode `current` would lean toward contrast; `still-pool` toward affinity.

### 3.4 Negative space (cinematography)

Negative space carries visual weight and balances complex subjects ([Filmmakers Academy — Negative Space](https://www.filmmakersacademy.com/blog-negative-space-film/); [Chaplin Film Festival glossary — Negative Space](https://chaplinfilmfestival.com/cinematography-glossary/negative-space/)). A symmetrical composition feels stable; asymmetric negative space creates tension and dynamism. Inverse vignette (densest at edges, thinnest at center) is the single most cinematographic move available — Hollywood portraiture diffusion exploits it (see scrim §4.5).

**Hapax mapping.** `attention_zones` on the Programme envelope can declare regions to *keep clear*. The placement post-pass treats these as repulsion fields. A `still-pool` Programme would have very large attention_zone clearings; `shallows` smaller ones.

### 3.5 Gestalt principles (perception)

Six principles — proximity, similarity, continuation, closure, figure/ground, prägnanz ([UserTesting — 7 Gestalt principles](https://www.usertesting.com/blog/gestalt-principles); [Toptal — Gestalt for UI](https://www.toptal.com/designers/ui/gestalt-principles-of-design); [IxDF — Gestalt principles](https://ixdf.org/literature/topics/gestalt-principles)). Proximity groups; similarity links; continuation guides the eye along a curve; closure fills implied shapes.

**Hapax mapping.** Wards of the same `domain` (per `agents/studio_compositor/ward_fx_mapping.py`) read as a group when placed proximally. Programme priors can encode "hothouse wards cluster lower-left" as a soft attractor field for that domain class. Gestalt continuation argues for ward arrangements along an implicit S-curve through the frame, which the operator's eye then follows.

### 3.6 Z-order and depth grammar (animation)

Layered animation has a long lineage from cel animation through digital compositing ([Painter's Algorithm — Wikipedia](https://en.wikipedia.org/wiki/Painter's_algorithm); [Local Layering paper](https://www.researchgate.net/publication/220183661_Local_layering); [Adobe Animate parallax via layer depth](https://helpx.adobe.com/animate/using/layer-depth.html); [3DArtist — Compositing Layers](https://3dartist.substack.com/p/basic-compositing-layers-explained)). Z-order is grammar — *which layers can sit in front of which* is a constraint on legibility.

**Hapax mapping.** A `depth_grammar` field on the Programme envelope declares allowable depth-band orderings: `["substrate", "deep", "mid", "near", "surface"]`. Each ward's `WardSpatialAffordance` declares which bands it lives in. Placement post-pass enforces the grammar. The current `default.json` z_order numbers (10 / 24 / 26 / 28 / 30 / 35) implicitly encode this; we are formalizing it.

### 3.7 Animetism / multiplanar depth (Lamarre)

Thomas Lamarre's *The Anime Machine* ([Wikipedia — The Anime Machine](https://en.wikipedia.org/wiki/The_Anime_Machine); [Lamarre — Multiplanar Image PDF](http://www.lamarre-mediaken.com/Site/Film_279_0_files/Lamarre_Multiplanar_Image.pdf); [Animétudes — On Animetism](https://animetudes.com/2020/04/08/on-animetism-or-the-importance-of-sakuga-to-theory/)) distinguishes **cinematism** (depth via Cartesian perspective, ballistic into-the-frame motion) from **animetism** (depth via differential motion of *parallel planes* — multiple flat layers moving at different rates, with depth manufactured by the rate ratio rather than by perspective convergence).

This is the load-bearing precedent for the scrim's spatial work. Hapax has no real geometry; depth must be *felt* not *computed*. Animetism is exactly this practice.

**Hapax mapping.** Wards in different depth bands drift at different rates. The placement post-pass writes per-ward `drift_velocity` proportional to depth-band ordinal: substrate ≈ 0.05px/s, deep ≈ 0.15px/s, mid ≈ 0.4px/s, near ≈ 1.0px/s, surface ≈ 2.5px/s (numbers are starting points). This is the simplest implementation of multiplanar parallax that the existing animation engine supports.

### 3.8 Differential blur and atmospheric perspective

Hero subject crisp; context fuzzy; far-side washes toward the dominant tint ([Filmmakers Academy — Balance](https://www.filmmakersacademy.com/glossary/balance/); [Pixel Valley Studio — beyond the 1/3 rule](https://pixelvalleystudio.com/pmf-articles/framing-and-composition-cinematography-going-beyond-the-13-rule)). Storaro on *Apocalypse Now* used colored smoke as compositional substrate ([ASC — Apocalypse Now: A Clash of Titans](https://theasc.com/articles/flashback-apocalypse-now)); same logic applies here: depth = blur + tint, both encoded per-ward via the depth-band assignment.

**Hapax mapping.** Each depth band has a `blur_radius_px` and a `tint_strength` field. The placement post-pass writes these to the per-ward effect chain so the compositor's existing `effect_chain` (per-assignment) renders them. Phase A6 substrate-invariant work already does this for Reverie + cyan tinting; we generalize it.

---

## §4. Computational layout algorithm options

Survey of the candidate algorithms from the literature, with trade-offs against the chosen hybrid frame.

### 4.1 Force-directed placement

Spring-electrical model: each ward is a node, attractive springs connect related wards (same domain), repulsive forces push all wards apart. Solved iteratively per frame ([Kobourov — Force-Directed Drawing Algorithms](https://cs.brown.edu/people/rtamassi/gdhandbook/chapters/force-directed.pdf); [yWorks — Force-Directed Graph Layout](https://www.yworks.com/pages/force-directed-graph-layout); [User-Guided Force-Directed Graph Layout — arxiv 2506.15860](https://arxiv.org/html/2506.15860); [PMC — User-Guided Force-Directed Graph Layout](https://pmc.ncbi.nlm.nih.gov/articles/PMC12306815/)).

**Pro:** Smooth animation as forces shift. No hard rule book — emergent layout from local pairwise forces. Composition_priors can be encoded as fixed attractor anchors; scrim_mode_priors as global force-magnitude scalars.

**Con:** Can be unstable under rapid ward churn (entry / exit cause whole-system jitter). Mitigation: dampening and per-ward inertia.

**Verdict:** Strong candidate for the placement post-pass. Especially under `current` mode where rhythmic ward arrival/departure benefits from spring-like settle dynamics.

### 4.2 Constrained force-directed (Adaptagrams cola)

Force-directed layout extended with linear inequality constraints ([Adaptagrams cola::ConstrainedFDLayout](https://www.adaptagrams.org/documentation/classcola_1_1ConstrainedFDLayout.html); [MDPI — Multivariate Network Layout with Attribute Constraints](https://www.mdpi.com/2076-3417/12/9/4561)). Lets the system declare e.g. "ward X must stay above ward Y" or "ward X must stay within rect R" alongside the springs.

**Pro:** Combines the emergence of force-directed with declarative constraints — exactly the soft-prior + filter shape we want.

**Con:** More complex; the cola library is C++. We'd write a small Python equivalent for the bounded problem size (max ~10 wards).

**Verdict:** The right shape for v2. v1 starts simpler.

### 4.3 Simulated annealing

Davidson & Harel's classic graph drawing application ([Davidson & Harel 1996 — Drawing Graphs Nicely](https://dl.acm.org/doi/pdf/10.1145/234535.234538); [Wikipedia — Simulated Annealing](https://en.wikipedia.org/wiki/Simulated_annealing); [GeeksforGeeks — Simulated Annealing](https://www.geeksforgeeks.org/artificial-intelligence/what-is-simulated-annealing/); also applied to architectural layout in [CAADRIA 2020 paper 024](https://papers.cumincad.org/cgi-bin/works/paper/caadria2020_024)). Cost function aggregates composition heuristics; SA finds a near-optimum by stochastically accepting worse states early.

**Pro:** Provably escapes local minima. Aesthetically pleasing layouts. Used in furniture-arrangement (UCLA siggraph11 — already cited) which is structurally close to ward placement.

**Con:** Per-frame cost is high if run online. Better fit: **annealing-on-Programme-change**. Each Programme transition triggers one SA pass; result is then animated to via interpolation.

**Verdict:** Good for mode-transition planning; bad for per-frame placement. Use as the **transition planner** layer.

### 4.4 Markov decision process

Macro placement in chip design has been recast as MDP ([Mirhoseini et al. — Delving into Macro Placement with RL — arxiv 2109.02587](https://ar5iv.labs.arxiv.org/html/2109.02587); [IEEE — same paper](https://ieeexplore.ieee.org/abstract/document/9531313); foundations in [Wikipedia — Markov Decision Process](https://en.wikipedia.org/wiki/Markov_decision_process); textbook treatment by [Wiering & van Otterlo](https://www.ai.rug.nl/~mwiering/Intro_RLBOOK.pdf)) with RL agents producing superhuman placements.

**Pro:** Learnable from operator feedback. Hebbian-style learning could promote layouts that tend to retain attention.

**Con:** Heavy machinery for a 10-ward problem with a soft-prior architecture. The affordance pipeline already does Thompson-sampling learning at the *which-ward* level; pushing learning down to *where-the-ward-goes* invites combinatorial explosion (state space = product of ward positions, scales, opacities).

**Verdict:** Defer. Revisit if v1 placements feel un-learnable from operator pinning behavior.

### 4.5 Boids / flocking

Reynolds' 1987 model: separation, alignment, cohesion ([Reynolds — Boids paper](https://www.red3d.com/cwr/papers/1987/boids.html); [Wikipedia — Boids](https://en.wikipedia.org/wiki/Boids); [Reynolds — red3d.com/cwr/boids](https://www.red3d.com/cwr/boids/); historical context in [Ohio State Pressbooks 19.2 Flocking Systems](https://ohiostate.pressbooks.pub/graphicshistory/chapter/19-2-flocking-systems/); recent emergent-swarm work in [arxiv 2309.11408](https://arxiv.org/html/2309.11408v2) and [Nature — Swarm intelligence collection](https://www.nature.com/collections/cgbgjbahac)).

**Pro:** Cheap, emergent, beautiful. Wards as boids drift naturally. Neighbors influence neighbors without a central conductor.

**Con:** Boids assume the swarm is homogeneous; wards are not. Each ward's "kind" (token-pole vs HARDM vs album) has different spatial obligations.

**Verdict:** Use the *idea* — local pairwise rules — within the force-directed framework. Don't literally implement boids.

### 4.6 Reservoir sampling

Vitter's algorithms for k-of-n streaming sampling ([Wikipedia — Reservoir Sampling](https://en.wikipedia.org/wiki/Reservoir_sampling); [Vitter — algorithms K, L, M](https://dl.acm.org/doi/10.1145/198429.198435); [pythonspeed — Timesliced Reservoir Sampling](https://pythonspeed.com/articles/reservoir-sampling-profilers/); [Florian — Reservoir Sampling](https://florian.github.io/reservoir-sampling/)).

**Pro:** Right tool for "given N pending wards and M emphasis slots, pick M with bounded memory". Already implicit in the choreographer's `weighted_by_salience` rotation mode.

**Verdict:** Direct fit. Use Vitter algorithm K (efficient time complexity) for the emphasis-slot selection within a tick. Timesliced variant: divide the rotation cycle into K windows and emit one emphasized ward per window — matches the operator's "rotation cadence" intuition.

### 4.7 Cassowary linear constraint solver

Apple Auto Layout's underlying engine ([Cassowary TOCHI 2001 PDF](https://constraints.cs.washington.edu/solvers/cassowary-tochi.pdf); [Wikipedia — Cassowary software](https://en.wikipedia.org/wiki/Cassowary_(software)); [UW Cassowary toolkit](https://constraints.cs.washington.edu/cassowary/); [Cassowary docs — solving theory](https://cassowary.readthedocs.io/en/latest/topics/theory.html)).

**Pro:** Mature, well-understood, perfect for hard geometric constraints (e.g. "two wards must not overlap > 5px").

**Con:** Linear-only; it can't model the smooth "drift toward this attractor" behavior we want for animetism-style depth. Best used for the hard-constraint *post*-pass on top of force-directed positioning.

**Verdict:** v2 layer for hard non-overlap and non-egress constraints. v1 just clips at frame edges.

### 4.8 Servo / Figma comparison points

Browser layout engines and design tools provide useful contrast. Servo runs styling and layout as separate parallel passes ([Servo Layout Overview](https://github.com/servo/servo/wiki/Layout-Overview); [Wikipedia — Servo](https://en.wikipedia.org/wiki/Servo_(software)); [Mozilla Hacks — Quantum CSS / Stylo](https://hacks.mozilla.org/2017/08/inside-a-super-fast-css-engine-quantum-css-aka-stylo/)). Figma's auto-layout vs constraints distinction ([Figma Help — Guide to auto layout](https://help.figma.com/hc/en-us/articles/360040451373-Guide-to-auto-layout); [Figma Help — Apply constraints](https://help.figma.com/hc/en-us/articles/360039957734-Apply-constraints-to-define-how-layers-resize); [UIPrep — When to use](https://www.uiprep.com/blog/when-to-use-constraints-vs-auto-layout)) — auto-layout is "frame responds to children", constraints are "children respond to frame" — these are two sides of the same coin we need.

**Hapax mapping.** Programme priors are auto-layout-style (the fishbowl mode dictates how wards arrange themselves). WardSpatialAffordances are constraint-style (each ward's hard-bounded preferences). Both run, both modulate the placement post-pass.

### 4.9 OBS / broadcast scene-switcher comparison

OBS Studio's Advanced Scene Switcher uses a macro / condition / action model ([Streamgeeks — Automatic Scene Switching in OBS](https://streamgeeks.us/automatic-scene-switching-in-obs/); [OBS Forums — Advanced Scene Switcher](https://obsproject.com/forum/resources/advanced-scene-switcher.395/)). Rule-of-thumb in motion-graphics-for-broadcast literature ([Envato Tuts+ — How to Add Motion Graphics to Live Stream Video](https://photography.tutsplus.com/articles/howto-motion-graphics-live-stream-video--cms-35221); [Ross XPression Real-Time Motion Graphics](https://www.rossvideo.com/live-production/graphics/xpression/); [Unreal — Broadcast Cinematics](https://www.unrealengine.com/en-US/explainers/broadcast-and-live-events/what-are-broadcast-cinematics); [Zero Density — Real-Time Motion Graphics](https://www.zerodensity.io/); [Fiveable — Motion Graphics Class Notes](https://fiveable.me/tv-studio-production/unit-7/motion-graphics/study-guide/mKj0uIJNJaMsJUTH); [Blackmagic Fusion — Broadcast Graphics](https://www.blackmagicdesign.com/products/fusion/broadcastgraphics)) emphasizes consistency, hierarchy, and "motion guides the eye". Sports broadcast deeply uses templated motion ([School of Motion — Sports MoGraph](https://www.schoolofmotion.com/blog/how-to-design-show-stopping-sports-mograph)).

**Negative lesson.** Macro/condition systems are exactly the expert-system rules Hapax forbids. We are not building Advanced Scene Switcher. We are building affordance-recruited placement.

**Positive lesson.** The motion-graphics literature's emphasis on *consistency* maps directly to depth_grammar; on *motion-guides-eye* to attention_zones; on *templated motion* to per-Programme `motion_priors`.

### 4.10 Decision

**v1: force-directed placement post-pass with declarative WardSpatialAffordance attractors and Programme-supplied attention_zone repulsors.** Cheap, smooth, emergent, no central rule book.

**v2: add Cassowary-style hard-constraint pass** for non-overlap and non-egress.

**v3: add simulated-annealing transition planner** for Programme mode-changes.

**v4 (optional): MDP / RL learning** if operator-pin telemetry shows learnable patterns.

---

## §5. Programme primitive integration — concrete YAML and Pydantic

### 5.1 Pydantic extension

Add to `shared/programme.py`. Strict-positive validators preserve the soft-prior axiom.

```python
class CompositionPriorAttractor(BaseModel):
    """A single soft-attractor anchor in normalized [0,1] frame coords."""
    x_norm: float = Field(..., ge=0.0, le=1.0)
    y_norm: float = Field(..., ge=0.0, le=1.0)
    weight: float = Field(..., gt=0.0, le=10.0)
    label: str = ""  # operator-legible: "rule-of-thirds-tl"

class AttentionZone(BaseModel):
    """A region the placement post-pass should keep clearer (soft repulsor)."""
    x_norm: float = Field(..., ge=0.0, le=1.0)
    y_norm: float = Field(..., ge=0.0, le=1.0)
    radius_norm: float = Field(..., gt=0.0, le=1.0)
    clearance_strength: float = Field(..., gt=0.0, le=10.0)

class MotionPriors(BaseModel):
    """Drift / cadence biases applied to all wards under this Programme."""
    drift_velocity_scalar: float = Field(default=1.0, gt=0.0, le=5.0)
    vibration_amplitude_scalar: float = Field(default=1.0, gt=0.0, le=5.0)
    cadence_phrase_bars: int = Field(default=4, ge=1, le=32)
    beat_lock_strength: float = Field(default=0.0, ge=0.0, le=1.0)

class DepthGrammar(BaseModel):
    """Allowable z-band orderings + per-band drift/blur/tint."""
    band_order: list[str] = Field(default_factory=lambda: [
        "substrate", "deep", "mid", "near", "surface"
    ])
    band_drift_velocity_px_s: dict[str, float] = Field(default_factory=lambda: {
        "substrate": 0.05, "deep": 0.15, "mid": 0.4,
        "near": 1.0, "surface": 2.5,
    })
    band_blur_radius_px: dict[str, float] = Field(default_factory=lambda: {
        "substrate": 0.0, "deep": 1.5, "mid": 0.5, "near": 0.0, "surface": 0.0,
    })
    band_tint_strength: dict[str, float] = Field(default_factory=lambda: {
        "substrate": 0.0, "deep": 0.7, "mid": 0.3, "near": 0.0, "surface": 0.0,
    })

class ScrimModePriors(BaseModel):
    """Programme-level fishbowl mode envelope. Soft priors only."""
    fishbowl_mode: Literal[
        "deep-water", "shallows", "current", "still-pool"
    ] = "shallows"
    composition_priors: list[CompositionPriorAttractor] = Field(default_factory=list)
    attention_zones: list[AttentionZone] = Field(default_factory=list)
    motion_priors: MotionPriors = Field(default_factory=MotionPriors)
    depth_grammar: DepthGrammar = Field(default_factory=DepthGrammar)
    max_concurrent_active_wards: int = Field(default=3, ge=1, le=8)
    cross_ward_coupling_strength: float = Field(default=0.5, ge=0.0, le=1.0)
```

Then extend `ProgrammeConstraintEnvelope`:

```python
class ProgrammeConstraintEnvelope(BaseModel):
    # ... existing fields ...
    scrim_mode_priors: ScrimModePriors | None = None
```

`None` means "no scrim-mode opinion; placement post-pass uses defaults" — which makes the addition fully backward-compatible with every existing Programme.

### 5.2 The four canonical fishbowl-mode YAML examples

#### `deep-water` (calm, contemplative)

```yaml
fishbowl_mode: deep-water
composition_priors:
  - {x_norm: 0.333, y_norm: 0.333, weight: 1.5, label: rule-of-thirds-tl}
  - {x_norm: 0.667, y_norm: 0.667, weight: 1.5, label: rule-of-thirds-br}
  - {x_norm: 0.500, y_norm: 0.500, weight: 0.3, label: center-weak}
attention_zones:
  - {x_norm: 0.5, y_norm: 0.5, radius_norm: 0.30, clearance_strength: 4.0}
motion_priors:
  drift_velocity_scalar: 0.3
  vibration_amplitude_scalar: 0.2
  cadence_phrase_bars: 16
  beat_lock_strength: 0.0
depth_grammar:
  band_order: [substrate, deep, mid, surface]
  band_drift_velocity_px_s: {substrate: 0.02, deep: 0.05, mid: 0.15, surface: 0.4}
max_concurrent_active_wards: 2
cross_ward_coupling_strength: 0.2
```

#### `shallows` (active, present, the default)

```yaml
fishbowl_mode: shallows
composition_priors:
  - {x_norm: 0.333, y_norm: 0.333, weight: 1.5, label: rule-of-thirds-tl}
  - {x_norm: 0.667, y_norm: 0.333, weight: 1.5, label: rule-of-thirds-tr}
  - {x_norm: 0.333, y_norm: 0.667, weight: 1.5, label: rule-of-thirds-bl}
  - {x_norm: 0.667, y_norm: 0.667, weight: 1.5, label: rule-of-thirds-br}
attention_zones:
  - {x_norm: 0.5, y_norm: 0.5, radius_norm: 0.20, clearance_strength: 2.5}
motion_priors:
  drift_velocity_scalar: 1.0
  vibration_amplitude_scalar: 1.0
  cadence_phrase_bars: 8
  beat_lock_strength: 0.2
max_concurrent_active_wards: 4
cross_ward_coupling_strength: 0.5
```

#### `current` (vinyl, beat-locked)

```yaml
fishbowl_mode: current
composition_priors:
  - {x_norm: 0.382, y_norm: 0.382, weight: 1.8, label: golden-tl}
  - {x_norm: 0.618, y_norm: 0.618, weight: 1.8, label: golden-br}
  - {x_norm: 0.382, y_norm: 0.618, weight: 1.0, label: golden-bl}
  - {x_norm: 0.618, y_norm: 0.382, weight: 1.0, label: golden-tr}
attention_zones:
  - {x_norm: 0.5, y_norm: 0.5, radius_norm: 0.18, clearance_strength: 2.0}
motion_priors:
  drift_velocity_scalar: 1.5
  vibration_amplitude_scalar: 2.0
  cadence_phrase_bars: 4
  beat_lock_strength: 0.85
depth_grammar:
  band_order: [substrate, deep, mid, near, surface]
max_concurrent_active_wards: 5
cross_ward_coupling_strength: 0.75
```

#### `still-pool` (wind-down, deep negative space)

```yaml
fishbowl_mode: still-pool
composition_priors:
  - {x_norm: 0.500, y_norm: 0.382, weight: 2.0, label: center-golden-upper}
attention_zones:
  - {x_norm: 0.5, y_norm: 0.5, radius_norm: 0.45, clearance_strength: 6.0}
  - {x_norm: 0.0, y_norm: 0.0, radius_norm: 0.30, clearance_strength: 3.0}
  - {x_norm: 1.0, y_norm: 1.0, radius_norm: 0.30, clearance_strength: 3.0}
motion_priors:
  drift_velocity_scalar: 0.15
  vibration_amplitude_scalar: 0.1
  cadence_phrase_bars: 32
  beat_lock_strength: 0.0
depth_grammar:
  band_order: [substrate, deep, surface]
max_concurrent_active_wards: 1
cross_ward_coupling_strength: 0.05
```

### 5.3 Soft-prior axiom check

Every numeric field above passes through a `gt=0.0` validator. Zero would be a hard gate. Reusing the architectural enforcement already shipped in `shared/programme.py:115-160` keeps this consistent with the rest of the Programme primitive.

---

## §6. Affordance-pipeline integration

### 6.1 Where in the chain

The placement post-pass sits **between** the choreographer's planning slice and the compositor's animation engine:

```
impingement → AffordancePipeline.select() → recruited capability set
                                               │
                                               ▼
                          choreographer.reconcile()
                          (planning + concurrency cap)
                                               │
                                               ▼
                          PlacementPostPass.resolve()  ◄── ScrimModePriors
                          (force-directed in normalized coords)
                                               │
                                               ▼
                          WardPlacementPlan → /dev/shm/hapax-compositor/ward-placement.json
                                               │
                                               ▼
                          AnimationEngine consumes plan → updates
                          ward-properties.json + ward-animation-state.json
                                               │
                                               ▼
                          GStreamer pipeline renders
```

This preserves unified semantic recruitment intact (no bypass paths). The placement post-pass receives an *already-recruited* set; it never overrides recruitment, only resolves placement of what recruitment has already chosen.

### 6.2 Scoring inputs that matter for ward placement

The post-pass reads, but does not modify, these signals:

- **Stimmung** (`shared/stimmung.py`): `overall_stance` biases the global `motion_priors.drift_velocity_scalar`. CRITICAL stance halves drift; SEEKING doubles it.
- **Exploration deficit** (`/dev/shm/hapax-exploration/`, aggregated as in `shared/affordance_pipeline.py:144`): high deficit → relax attention_zone clearance to allow more activity.
- **Recent attention distribution** (a small ring buffer maintained by the post-pass): Hebbian-style "this ward has been on-screen too long" repulsion, preventing visual lock-in.
- **Ward cooldown** (per-ward `last_emphasized_at`): standard refractory-period suppression matched to the existing `record_success/failure` cadence.
- **Audio beat phase** (`shared/beat_tracker.py`, `agents/studio_compositor/audio_processor`): under `current` mode, the post-pass snaps animation phases to the nearest beat boundary.
- **Ward-FX bus** (`shared/ward_fx_bus.py`): subscribes to `WardEvent` for cross-ward coupling — when ward X enters EMPHASIZED, neighboring wards' attractor weights shift slightly to make room.

### 6.3 Where the choreographer sits relative to AffordancePipeline.select()

**Pre-recruitment.** Programme `bias_multiplier(capability_name)` already biases the pipeline's `combined` score before retrieval (`shared/programme.py:162`). The Programme's *capability* biases stay where they are — purely soft, multiplicative.

**Post-recruitment, pre-render.** The placement post-pass receives the recruited set. This is the new layer.

**Composition-feasibility filter.** Implemented inside the post-pass: if max_concurrent_active_wards is N and N+1 are recruited this tick, the post-pass demotes the lowest-scoring recruit to a quieter `surface` band rather than deferring it. *Demoting, not refusing*, preserves the soft-prior axiom — every recruited ward still appears, just possibly quieter.

### 6.4 The HARDM anchoring case

The choreographer already does a HARDM-anchoring pass (`agents/studio_compositor/homage/choreographer.py:519-559`) when bias > UNSKIPPABLE_BIAS. The placement post-pass treats HARDM with elevated attractor weight under any mode where HARDM is anchoring — ensuring the ward visibly takes its bound spatial slot when communicatively anchored. This is a worked example of how anti-anthropomorphization invariants (`project_hardm_anti_anthropomorphization`) translate to spatial decisions: HARDM gets a deterministic anchored position when bias is high, without a narrative explanation in the system.

---

## §7. Temporal rhythm and phrasing intelligence

### 7.1 Wards as a percussion ensemble

Each ward has a "default cadence" (its Cairo render rate, ranging 2 Hz to 30 Hz in `default.json`). The Choreographer can syncopate, accent, or rest these cadences via `motion_priors`. This is direct mapping of musical phrasing onto visual rhythm.

Reference: musical phrasing literature on tension-release and four/eight/sixteen-bar phrase structure ([School of Composition — Tension and Release](https://www.schoolofcomposition.com/what-is-tension-and-release-in-music/); [Wikipedia — Musical phrasing](https://en.wikipedia.org/wiki/Musical_phrasing); [Pat Pattison — The Art of Phrasing](https://www.patpattison.com/art-of-phrasing); [Musical-U — Tension and Release in Music](https://www.musical-u.com/learn/tension-in-music/); [MasterClass — 6 Ways to Create Tension and Release](https://www.masterclass.com/articles/ways-to-create-tension-and-release-in-music); [Point Blank — Creating Tension and Release in EDM](https://www.pointblankmusicschool.com/blog/creating-tension-and-release-in-electronic-dance-music/); [EDMProd — Advanced Guide to Tension and Energy](https://www.edmprod.com/tension/)). The four/eight/sixteen-bar phrase-arc is the most-cited unit; tension built through harmonic/rhythmic complexity, released through resolution.

### 7.2 Beat-locked vs free-flow

`current` mode's `beat_lock_strength: 0.85` snaps ward animation phases to the nearest beat boundary; `deep-water`'s `beat_lock_strength: 0.0` lets wards drift on their own clocks. The compositor already has beat tracking (`shared/beat_tracker.py`); wiring `beat_lock_strength` is one more uniform read.

**Visual-beat literature.** Davis & Agrawala's *Visual Rhythm and Beat* ([Davis Stanford 2018 PDF](https://www.abedavis.com/files/papers/VisualRhythm_Davis18.pdf); [ACM TOG abstract](https://dl.acm.org/doi/10.1145/3197517.3201371); [author site](https://abedavis.com/visualbeat/); Springer companion [Dance to the beat](https://link.springer.com/article/10.1007/s41095-018-0115-y)) formalizes the alignment of motion patterns to musical beats. VJ practice ([Beatflo — How VJs Sync Visuals with Music](https://beatflo.net/resources/blog/how-vjs-sync-visuals-music-exploring-art-visual-synchronization); [ArKaos VJ/DJ — Live Video Performance](https://vj.arkaos.com/grandvj/about); [Synesthesia — Live Music Visualizer](https://synesthesia.live/); [Visualz Studio](https://www.visualzstudio.com/)) gives the operator-vocabulary of "beat-locked", "phrase-locked", "free-flow".

### 7.3 Phrase-level intelligence

A *phrase* is a 4 / 8 / 16-bar arc with the structure: arrival → development → release. The placement post-pass can encode this as a state machine over the cadence_phrase_bars period:

- **Arrival** (first ¼ of phrase): one new ward enters.
- **Development** (middle ½): attractor weights drift, depth bands shift slightly.
- **Release** (last ¼): no new entries; existing wards settle to their attractors.

This produces *felt* musical phrasing in the visual layer without any expert-system rule about "after 3 seconds, do X". The phrase length is operator-mode-dependent (cadence_phrase_bars), and the tempo source is whatever `beat_tracker.py` is producing.

### 7.4 Cross-pollination with Hapax cognitive cadence

The cognitive substrate (DMN pulse, imagination loop) already runs on a roughly 0.15–0.25 Hz "breath" rhythm (per scrim §4.6 and existing shader's `breathing` node). Aligning ward phrase boundaries to multiples of this period — `cadence_phrase_bars` × beat-period ≈ N × breath-period — creates *conceptual rhyme* between the cognitive pulse and the visual pulse. Operator can perceive this without hearing it explained.

---

## §8. Cross-ward coordination protocols

### 8.1 Local pairwise rules (boids-derived)

The placement post-pass implements three boid-style local rules for ward-to-ward coordination ([Reynolds — Boids paper](https://www.red3d.com/cwr/papers/1987/boids.html); [Wikipedia — Boids](https://en.wikipedia.org/wiki/Boids)):

- **Separation:** wards in the same depth band repel each other proportionally to inverse-square distance.
- **Alignment:** wards in the same `domain` (per ward_fx_mapping) align drift directions.
- **Cohesion:** wards with the same `programme_role` tag mildly attract each other.

Strengths scale by `cross_ward_coupling_strength` from the active mode's ScrimModePriors.

### 8.2 Composite emergence — phrase formation

When 2-3 wards coordinate they form a **visual phrase**. Examples:

- Token-pole accent → album-cover lean → HARDM cell-density spike. This is a phrase about *attention* ("the system is paying close attention to this beat").
- Sierpinski rotation → Reverie palette shift. (Reverie is substrate, but the palette signals participation.) This is a phrase about *atmospheric mood-change*.
- Pressure-gauge surge → impingement-cascade scrolling-faster → activity-variety-log dim. This is a phrase about *cognitive load*.

These phrases are not authored. They emerge from the interaction of local pairwise rules, Programme priors, and recruitment outcomes. Operator perceives them as moments of compositional rhyme.

### 8.3 Composition cap

`max_concurrent_active_wards` enforces the "noise cap". This is a **soft cap via demotion**, not a hard cap via refusal — overflow wards drop to lower-attention bands rather than disappearing. This preserves recruitment intent while preventing visual mush. Mirrors the existing choreographer's max_simultaneous_entries enforcement (which is a hard cap on FSM transitions, *not* on ward presence; the two caps complement each other).

### 8.4 Attractor / repulsor field literature

Swarm-aggregation theory provides the mathematical basis for the attraction/repulsion mix ([Researchgate — Stable swarm aggregations](https://www.researchgate.net/publication/4006489_A_class_of_attractionrepulsion_functions_for_stable_swarm_aggregations); [PMC — Cognitive swarming with attractor dynamics](https://pmc.ncbi.nlm.nih.gov/articles/PMC7183509/); [Thomy Phan — Emergence in Multi-Agent Systems](https://thomyphan.github.io/research/emergence/); [JHU APL — Neuro-Inspired Dynamic Replanning in Swarms](https://www.jhuapl.edu/sites/default/files/2024-09/35-04-Hwang.pdf)). The standard force law — Lennard-Jones-style attractive-at-distance, repulsive-at-close — gives stable aggregation without lock-in. We borrow it directly.

---

## §9. Operator override mechanics

### 9.1 Per axiom-bound operator authority

The `single_user` constitutional axiom and the `executive_function` axiom together mean the operator's spatial preference always wins. Per-ward operator pinning operates at three levels:

- **Hard pin.** Operator pins ward X to position (x, y) via the command registry (`hapax-logos/src/lib/commands/`). This becomes a hard constraint in the placement post-pass; the ward stays put until unpinned.
- **Soft pin.** Operator marks "ward X prefers upper-left for this session". This becomes a high-weight attractor in `composition_priors` for the active Programme.
- **Programme override.** Operator names a specific Programme; that Programme's `scrim_mode_priors` take precedence over autonomous priors. Programmes are fully Hapax-authored (`feedback_hapax_authors_programmes`), but the operator can *select* among them.

### 9.2 UX for indicating override

This is a livestream-visible question — the audience sees the surface. Two principles:

- **Subtle, not viewer-distracting.** Following the design language's anti-personification stance, override-indicators should not be face-iconography, not anthropomorphic widgets. A small chrome ring around the pinned ward, or a faint geometric tag in the bottom-right corner of its surface.
- **Opaque to the audience, legible to the operator.** Override status is a Hapax internal state. The audience sees the layout effect, not the cause. The operator sees a small token in the Logos panel saying "ward X pinned: y=540".

### 9.3 Restoring autonomy

A `unpin all` command via the command registry returns full placement authority to the post-pass. This matches the existing pattern of explicit recovery from emergency states (consent-safe fallback, etc.).

---

## §10. Anti-anthropomorphization invariants for ward intelligence

### 10.1 No narration of decisions

The system must NEVER produce text like:

> "Hapax thinks the album cover wants to swim left."

The intelligence is in the *aggregate behavior*, not in any single decision. This matches the binding HARDM-class invariant from `project_hardm_anti_anthropomorphization`: no eyes, no mouths, no expressions, no anthropomorphic narration.

### 10.2 Decisions are emergent, not authored

Each ward placement is the resolution of forces, not the execution of an intent. There is no "decision" to narrate; there is a **state** (positions, velocities, opacities) that the post-pass converged to. Even when operator behavior would let us reconstruct a story ("the system shifted everything left because chat was loud"), the system itself does not produce that story.

### 10.3 Aggregation, not individuation

The four fishbowl modes describe aggregate fishbowl behavior. They do not name individual ward "personalities". Wards are *capabilities*, not characters. This preserves the architectural separation already enforced for cognitive surfaces ("Hapax does not have feelings about wards"; HARDM is not a face, etc.).

### 10.4 Heider-Simmel temptation

Heider & Simmel (1944) showed that humans impose narrative on simple geometric motion — even two triangles and a circle become "characters" in a story ([Nature Scientific Reports — Heider and Simmel revisited in VR](https://www.nature.com/articles/s41598-024-65532-0); [PMC — Heider capacity in dynamic scenes](https://pmc.ncbi.nlm.nih.gov/articles/PMC6396302/); [Sage — Judging social interaction in Heider and Simmel](https://journals.sagepub.com/doi/abs/10.1177/1747021819838764); [Researchgate — Heider and Simmel revisited PDF](https://www.researchgate.net/publication/284514443_Heider_and_simmel_1944_revisited_Causal_attribution_and_the_animated_film_technique); [movieperception WordPress — perception and attribution of causality](https://movieperception.wordpress.com/2013/10/29/perception-attribution-of-causality/); [Frontiers in Psychology — review article PDF](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1168739/pdf)). The audience *will* read social meaning into our ward motion. We cannot stop them. What we can do — and must — is not collude. The system does not produce, store, or surface narratives about ward decisions. The operator's eye and the audience's eye build whatever story they will. The system stays silent.

This is the **same architectural commitment** as the daimonion's refusal to narrate its model selection: the system performs the work, it does not perform the meaning of the work.

---

## §11. Concrete code-shapes

### 11.1 `WardSpatialAffordance` Pydantic model

```python
# shared/ward_spatial_affordance.py (new file)

from typing import Literal
from pydantic import BaseModel, Field, field_validator

DepthBand = Literal["substrate", "deep", "mid", "near", "surface"]

class SpatialAttractor(BaseModel):
    """Where on the scrim this ward likes to live (normalized coords)."""
    x_norm: float = Field(..., ge=0.0, le=1.0)
    y_norm: float = Field(..., ge=0.0, le=1.0)
    weight: float = Field(default=1.0, gt=0.0, le=10.0)

class WardSpatialAffordance(BaseModel):
    """Per-ward declaration of spatial behavior preferences.

    All fields are soft priors. The placement post-pass composes them
    with Programme-supplied ScrimModePriors and active recruitment to
    produce final positions. Zero-magnitude weights are forbidden by
    validator; use small positive values for strong-but-not-absolute
    bias-against (matches `shared/programme.py` axiom).
    """
    ward_id: str
    depth_bands: list[DepthBand] = Field(..., min_length=1)
    natural_attractors: list[SpatialAttractor] = Field(default_factory=list)
    natural_drift_px_s: float = Field(default=0.4, gt=0.0, le=10.0)
    natural_vibration_amplitude_px: float = Field(default=0.0, ge=0.0, le=20.0)
    natural_scale: float = Field(default=1.0, gt=0.0, le=4.0)
    domain: str  # for boid-style alignment grouping
    coupled_wards: dict[str, float] = Field(default_factory=dict)
    # Mapping ward_id → coupling sign × strength.
    # Positive = attractor (cohesion); negative = repulsor (separation).
    # Magnitude in (0, 1].

    @field_validator("coupled_wards")
    @classmethod
    def _coupling_in_range(cls, v: dict[str, float]) -> dict[str, float]:
        for k, mag in v.items():
            if not (-1.0 <= mag <= 1.0) or mag == 0.0:
                raise ValueError(
                    f"coupled_wards[{k!r}]={mag!r} — must be in "
                    "[-1, 0) ∪ (0, 1]; zero is architecturally forbidden."
                )
        return v
```

### 11.2 `compute_ward_position` algorithm sketch

```python
# agents/studio_compositor/placement_postpass.py (new file)

import math
import time

def compute_ward_positions(
    planned_wards: list[PlannedTransition],
    ward_affordances: dict[str, WardSpatialAffordance],
    programme_priors: ScrimModePriors,
    stimmung: SystemStimmung,
    beat_phase: float,  # [0, 1) within current beat
    prev_positions: dict[str, tuple[float, float]],
    frame_w: int = 1920,
    frame_h: int = 1080,
    n_iters: int = 16,
    dt: float = 1/30,
) -> WardPlacementPlan:
    """Force-directed placement post-pass.

    Each ward starts at its previous position (or its primary natural
    attractor for fresh entries). We then run n_iters of force-integration:

        F_total = F_natural_attractor   (per-ward declared)
                + F_programme_attractor (Programme composition_priors)
                - F_attention_zone_repulsor (Programme attention_zones)
                + sum_neighbours F_coupling (boid-style separation/alignment/cohesion)
                - F_frame_edge_clip       (soft clip near frame edges)

    Velocity update:  v += F * dt;  v *= damping(stimmung)
    Position update:  p += v * dt
    Beat-lock under `current` mode: snap velocity phase to beat boundary.

    Returns a WardPlacementPlan that the animation engine consumes.
    """
    positions: dict[str, tuple[float, float]] = {}
    velocities: dict[str, tuple[float, float]] = {}

    # Stimmung damping: CRITICAL stance freezes; SEEKING accelerates
    base_damping = 0.85
    stimmung_factor = {
        Stance.NOMINAL: 1.0,
        Stance.SEEKING: 1.4,
        Stance.CAUTIOUS: 0.7,
        Stance.DEGRADED: 0.5,
        Stance.CRITICAL: 0.2,
    }[stimmung.overall_stance]
    damping = base_damping * stimmung_factor

    # Initialize positions for fresh entries; preserve for ongoing.
    for plan in planned_wards:
        wid = plan.source_id
        affordance = ward_affordances.get(wid)
        if affordance is None:
            continue
        if wid in prev_positions:
            positions[wid] = prev_positions[wid]
        else:
            primary = affordance.natural_attractors[0] if affordance.natural_attractors \
                      else SpatialAttractor(x_norm=0.5, y_norm=0.5, weight=1.0)
            positions[wid] = (primary.x_norm * frame_w, primary.y_norm * frame_h)
        velocities[wid] = (0.0, 0.0)

    # Force-integration loop
    for _ in range(n_iters):
        forces: dict[str, tuple[float, float]] = {wid: (0.0, 0.0) for wid in positions}

        # Per-ward natural attractors
        for wid, (px, py) in positions.items():
            affordance = ward_affordances[wid]
            for attr in affordance.natural_attractors:
                ax = attr.x_norm * frame_w
                ay = attr.y_norm * frame_h
                fx, fy = (ax - px) * attr.weight * 0.05, (ay - py) * attr.weight * 0.05
                forces[wid] = (forces[wid][0] + fx, forces[wid][1] + fy)

        # Programme composition_priors as global attractors
        for prior in programme_priors.composition_priors:
            ax = prior.x_norm * frame_w
            ay = prior.y_norm * frame_h
            for wid, (px, py) in positions.items():
                fx, fy = (ax - px) * prior.weight * 0.02, (ay - py) * prior.weight * 0.02
                forces[wid] = (forces[wid][0] + fx, forces[wid][1] + fy)

        # Programme attention_zones as repulsors
        for zone in programme_priors.attention_zones:
            zx = zone.x_norm * frame_w
            zy = zone.y_norm * frame_h
            zr = zone.radius_norm * min(frame_w, frame_h)
            for wid, (px, py) in positions.items():
                dx, dy = px - zx, py - zy
                d = math.hypot(dx, dy) or 0.001
                if d < zr:
                    push = (zr - d) / zr * zone.clearance_strength * 5.0
                    forces[wid] = (
                        forces[wid][0] + dx / d * push,
                        forces[wid][1] + dy / d * push,
                    )

        # Boid-style pairwise coupling (separation, alignment, cohesion)
        coupling = programme_priors.cross_ward_coupling_strength
        for wid, (px, py) in positions.items():
            affordance = ward_affordances[wid]
            for other_wid, (ox, oy) in positions.items():
                if other_wid == wid:
                    continue
                # Explicit per-ward coupling overrides domain default
                explicit = affordance.coupled_wards.get(other_wid)
                other_affordance = ward_affordances[other_wid]
                if explicit is not None:
                    sign_strength = explicit
                elif affordance.domain == other_affordance.domain:
                    sign_strength = 0.3  # cohesion within domain
                else:
                    sign_strength = -0.2  # mild separation across domains
                dx, dy = ox - px, oy - py
                d = math.hypot(dx, dy) or 0.001
                # Lennard-Jones style: attractive at distance, repulsive close
                lj = sign_strength * coupling * (1.0 - (40.0 / d) ** 2) * 2.0
                forces[wid] = (
                    forces[wid][0] + dx / d * lj,
                    forces[wid][1] + dy / d * lj,
                )

        # Velocity + position integration
        motion_scalar = programme_priors.motion_priors.drift_velocity_scalar
        for wid in positions:
            vx, vy = velocities[wid]
            fx, fy = forces[wid]
            vx = (vx + fx * dt) * damping
            vy = (vy + fy * dt) * damping
            # Beat-lock under high beat_lock_strength
            bls = programme_priors.motion_priors.beat_lock_strength
            if bls > 0.5:
                # Snap velocity magnitude to beat-aligned envelope
                envelope = 0.5 + 0.5 * math.cos(2 * math.pi * beat_phase)
                v_mag = math.hypot(vx, vy)
                if v_mag > 0.001:
                    target_mag = v_mag * (1 - bls + bls * envelope)
                    vx = vx * target_mag / v_mag
                    vy = vy * target_mag / v_mag
            velocities[wid] = (vx * motion_scalar, vy * motion_scalar)
            px, py = positions[wid]
            positions[wid] = (
                max(0, min(frame_w, px + vx * dt)),
                max(0, min(frame_h, py + vy * dt)),
            )

    # Resolve final depth bands based on programme.depth_grammar order
    resolved = []
    for plan in planned_wards:
        wid = plan.source_id
        affordance = ward_affordances.get(wid)
        if affordance is None:
            continue
        # Pick the band the ward is allowed AND that the programme orders
        allowed = [b for b in affordance.depth_bands
                   if b in programme_priors.depth_grammar.band_order]
        depth_band = allowed[0] if allowed else "mid"
        x, y = positions[wid]
        drift = programme_priors.depth_grammar.band_drift_velocity_px_s.get(depth_band, 0.4)
        blur = programme_priors.depth_grammar.band_blur_radius_px.get(depth_band, 0.0)
        tint = programme_priors.depth_grammar.band_tint_strength.get(depth_band, 0.0)
        resolved.append(WardPlacement(
            ward_id=wid,
            x_px=x, y_px=y,
            scale=affordance.natural_scale,
            opacity=1.0,  # opacity stays out of post-pass; choreographer FSM owns it
            drift_velocity_px_s=drift,
            depth_band=depth_band,
            blur_radius_px=blur,
            tint_strength=tint,
        ))
    return WardPlacementPlan(placements=resolved, ts=time.monotonic())
```

This is a sketch. Real implementation will live in `agents/studio_compositor/placement_postpass.py`, will have unit tests with deterministic seeds, and will hold a small fixed iteration budget per tick. Cost analysis: 16 iterations × ~10 wards × ~10 wards (pairwise) ≈ 1600 force computations per tick; at 30 fps that's ~50k ops/s, well under the budget tracker's frame ceiling.

### 11.3 Extended Choreographer state diagram

The existing FSM (ABSENT → ENTERING → HOLD → EMPHASIZED → EXITING) is preserved unchanged. The placement post-pass is additive:

```
                  ┌─────────────────────────────────────────────────┐
                  │  Choreographer.reconcile()                      │
                  │                                                 │
   pending  ───►  │  read pending  →  partition (entry/exit/modify) │
                  │                  ↓                              │
                  │         apply max-simultaneous caps             │
                  │                  ↓                              │
                  │            planned: list[PlannedTransition]     │
                  │                  ↓                              │
                  │  ┌──── NEW: placement_postpass.resolve() ────┐  │
                  │  │  read ScrimModePriors from active         │  │
                  │  │  Programme, read WardSpatialAffordances,  │  │
                  │  │  read prev positions from SHM,            │  │
                  │  │  read stimmung + beat_phase,              │  │
                  │  │  run force-directed iterations,           │  │
                  │  │  emit WardPlacementPlan to SHM            │  │
                  │  └──────────────────────────────────────────┘  │
                  │                  ↓                              │
                  │      publish payload + ward events             │
                  └─────────────────────────────────────────────────┘
                                     ↓
                  AnimationEngine consumes WardPlacementPlan
                  → updates ward-properties.json
                  → updates ward-animation-state.json
                                     ↓
                          GStreamer pipeline renders
```

### 11.4 SHM contract

Adding one new file: `/dev/shm/hapax-compositor/ward-placement.json`. Schema:

```json
{
  "ts": 12345.678,
  "fishbowl_mode": "shallows",
  "placements": [
    {
      "ward_id": "token_pole",
      "x_px": 533.2, "y_px": 312.4,
      "scale": 1.0,
      "opacity": 1.0,
      "drift_velocity_px_s": 0.4,
      "depth_band": "mid",
      "blur_radius_px": 0.5,
      "tint_strength": 0.3
    }
  ]
}
```

Atomic tmp+rename, matching every other HOMAGE compositor SHM file pattern (per `agents/studio_compositor/homage/choreographer.py:903-921`).

---

## §12. Open questions

### 12.1 What is the right cadence for the placement post-pass?

Choreographer.reconcile() runs at the structural director's cadence (typically 30s narrative tier, 90s structural tier). But ward animation needs frame-rate updates. **Resolution:** the post-pass *plans* at reconcile cadence; the animation engine *interpolates* between plans at frame rate. This matches OBS Advanced Scene Switcher's pattern of macro-condition checks at slow rate, animation at fast rate.

### 12.2 How does the post-pass interact with operator pinning when a ward is mid-animation?

If operator pins a ward at t=0 and that ward was mid-flight to a new position, the pin should snap the ward to the pin location (smooth interpolation, ~0.5s ease-out). The interpolation is owned by AnimationEngine, not the post-pass.

### 12.3 What happens when no Programme is active?

Default `ScrimModePriors` (the `shallows` mode YAML, encoded as the default in the Pydantic model). Always-active: there is never a state where the post-pass receives no envelope.

### 12.4 How do we handle hothouse-pressure mode?

Hothouse wards (`tags: ["hothouse", ...]` in `default.json`) declare a high-coupling-strength affordance with each other. Under high cognitive-load stimmung, the Programme planner should select a `current`-or-`shallows` Programme variant whose `cross_ward_coupling_strength` is high — letting hothouse wards visually swarm. This emerges from the existing tag taxonomy without new mechanism.

### 12.5 What is the empirical loop?

After a livestream cycle with the post-pass active, manually review the recordings for:

- Visual mush moments (too many simultaneous wards) → tune max_concurrent_active_wards down.
- Visual deadness (one ward dominating too long) → tune cohesion strength up, or add ward-cooldown repulsion.
- Beat-lock false-positives (wards snapping when they shouldn't) → tune beat_lock_strength threshold.
- Operator pin frequency → if high, the autonomous priors disagree with operator taste; revisit Programme catalog.

### 12.6 Three concrete operator next-actions (recap)

1. **Land `WardSpatialAffordance` and a per-ward registry** — pure data, no algorithm changes. Each existing ward source_id in `default.json` gets one declared affordance. This is committable in one PR with no behavioral change.
2. **Extend `ProgrammeConstraintEnvelope` with `scrim_mode_priors`** — Pydantic-only addition with backward-compatible `None` default. The four canonical fishbowl-mode YAMLs ship as Programme-template fixtures.
3. **Add `placement_postpass` to `Choreographer.reconcile()` behind a default-off feature flag** — actually wires the algorithm. One livestream cycle of empirical observation under flag-on, then default-on with rollback escape hatch (matches the `HAPAX_HOMAGE_ACTIVE` rollback pattern in `agents/studio_compositor/homage/choreographer.py:92-106`).

### 12.7 What about MotionCanvas and AI-driven motion design?

A 2025 line of work — MotionCanvas, generative motion-design models — produces ward-like motion from intent prompts ([MotionCanvas — arxiv 2502.04299](https://arxiv.org/html/2502.04299v1); [Pixflow — How AI Is Redefining Motion Design in 2025](https://pixflow.net/blog/how-ai-is-redefining-motion-design-in-2025/); [GenMotion — arxiv 2112.06060](https://arxiv.org/abs/2112.06060); [Springer — Motion Matching: Data-Driven Character Animation](https://link.springer.com/rwe/10.1007/978-3-031-23161-2_511); [Sage — Biomechanical analysis of cinematic motion AI 2025](https://journals.sagepub.com/doi/10.1177/14727978251348639); [DearDeer — Enhancing Static Charts with Data-driven Animations TVCG 21](https://deardeer.github.io/pub/TVCG21_Ant.pdf); [Games-105 — Data-driven Animation lecture notes](https://games-105.github.io/ppt/05%20-%20Data-driven%20Animation.pdf); [tkh44 — data-driven-motion React lib](https://github.com/tkh44/data-driven-motion); [Datalabs — Animated Data Videos](https://www.datalabsagency.com/animated-data-videos/)). These are interesting *generators of new ward motion vocabularies*, but not replacements for the placement post-pass — they produce per-ward motion patterns, while the post-pass coordinates *across* wards. Long-term: a MotionCanvas-style component could *populate* per-ward `natural_drift_*` and `natural_vibration_*` fields automatically from a designer prompt; the post-pass still does coordination. Defer.

### 12.8 What about Manovich-style spatial montage?

Manovich's "spatial montage" — multiple temporal events composited into a single frame — is what Hapax already does; the wards are exactly this ([Manovich — Soft Cinema](https://manovich.net/index.php/projects/soft-cinema); [Manovich — What is Digital Cinema PDF](https://manovich.net/content/04-projects/009-what-is-digital-cinema/07_article_1995.pdf); [TUe Alice — The Language of New Media PDF](https://www.alice.id.tue.nl/references/manovich-2001.pdf); [Tiffany's Window — Montage according to Manovich](https://tiffanyswindow.wordpress.com/2014/10/21/montage-according-to-lev-manovich/); [Wikipedia — Database cinema](https://en.wikipedia.org/wiki/Database_cinema); [Communication Chaos — Layers and Manovich](https://communicationchaos.wordpress.com/2014/06/09/its-all-about-the-layers-and-manovich/); [MIT Press — The Language of New Media](https://mitpress.mit.edu/9780262632553/the-language-of-new-media/)). The placement post-pass is one Hapax-specific instance of Manovich's general claim about how digital media produces meaning. Worth re-reading periodically for vocabulary.

---

## §13. Sources

### Hapax codebase

- `shared/programme.py` (Programme primitive — strict-positive soft-prior validators)
- `shared/affordance_pipeline.py` (AffordancePipeline.select, scoring, recruitment, consent + monetization gates)
- `shared/affordance.py` (CapabilityRecord, ActivationState, SelectionCandidate)
- `shared/governance/monetization_safety.py` (model for the placement post-pass's filter shape)
- `shared/director_intent.py` (NarrativeStructuralIntent, IntentFamily including ward.* families)
- `shared/stimmung.py` (Stance, SystemStimmung dimensions)
- `shared/homage_package.py` (HomagePackage, palette, transition vocabulary)
- `shared/homage_coupling.py` (shader↔ward reverse-path for hold pacing)
- `shared/ward_fx_bus.py` (WardEvent pubsub; cross-ward coupling carrier)
- `shared/beat_tracker.py` (audio beat phase for `current` mode)
- `agents/studio_compositor/homage/choreographer.py` (reconcile, placement post-pass insertion point)
- `agents/studio_compositor/homage/substrate_source.py` (HomageSubstrateSource protocol; substrate registry)
- `agents/studio_compositor/animation_engine.py` (consumes WardPlacementPlan downstream)
- `agents/studio_compositor/compositional_consumer.py` (dispatch_ward_* writes; existing ward-properties.json schema)
- `agents/studio_compositor/ward_fx_mapping.py` (domain_for_ward; boid-alignment grouping)
- `config/compositor-layouts/default.json` (current 16-source layout; baseline for affordance-registry seeding)
- `docs/research/2026-04-20-nebulous-scrim-design.md` (governing scrim design — 7 commitments, 15 techniques, 7 spatial moves)
- `docs/superpowers/specs/2026-04-18-homage-framework-design.md` (HOMAGE framework spec)
- `docs/superpowers/specs/2026-04-02-unified-semantic-recruitment-design.md` (recruitment architectural axiom)

### Composition theory and cinematography

- Bruce Block, *The Visual Story* — [Routledge edition](https://www.routledge.com/The-Visual-Story-Creating-the-Visual-Structure-of-Film-TV-and-Digital-Media/Block/p/book/9781138014152) | [Internet Archive](https://archive.org/details/visualstorycreat0000bloc) | [Google Books](https://books.google.com/books/about/The_Visual_Story.html?id=YaxtjmZaHz8C) | [Arthur Tasquin notes — 7 visual components](https://arthurtasquin.com/blog/visualjourney1)
- Thomas Lamarre, *The Anime Machine: A Media Theory of Animation* — [Wikipedia](https://en.wikipedia.org/wiki/The_Anime_Machine) | [Multiplanar Image PDF](http://www.lamarre-mediaken.com/Site/Film_279_0_files/Lamarre_Multiplanar_Image.pdf) | [UMN Press](https://www.upress.umn.edu/9780816651559/the-anime-machine/) | [Animétudes — On Animetism](https://animetudes.com/2020/04/08/on-animetism-or-the-importance-of-sakuga-to-theory/) | [Rhizomes review](https://rhizomes.net/issue20/reviews/dunlap.html)
- Edward Tufte, *The Visual Display of Quantitative Information* — [Tufte's site](https://www.edwardtufte.com/) | [Wikipedia](https://en.wikipedia.org/wiki/Edward_Tufte) | [Geeks for Geeks — Mastering Tufte's Principles](https://www.geeksforgeeks.org/data-visualization/mastering-tuftes-data-visualization-principles/) | [Guy Pursey notes](https://guypursey.com/blog/202001041530-tufte-principles-visual-display-quantitative-information) | [Comm Spot — Tufte's Principles](https://thecommspot.com/comm-subjects/visual-communication/data-visualization/principles-of-data-visualization/edward-tuftes-principles-for-data-visualization/) | [Doublethink — Tufte's Principles](https://thedoublethink.com/tuftes-principles-for-visualizing-quantitative-information/) | [GA Tech CS 7450 lecture notes PDF](https://faculty.cc.gatech.edu/~stasko/7450/16/Notes/tufte.pdf)
- Negative space and balance — [Filmmakers Academy — Negative Space](https://www.filmmakersacademy.com/blog-negative-space-film/) | [Chaplin Film Festival Cinematography Glossary](https://chaplinfilmfestival.com/cinematography-glossary/negative-space/) | [FilmLifestyle — Negative Space](https://filmlifestyle.com/what-is-negative-space/) | [Filmmakers Academy — Balance](https://www.filmmakersacademy.com/glossary/balance/) | [Wolfcrow — Three Composition Conventions](https://wolfcrow.com/the-three-important-composition-and-framing-conventions-in-cinematography/) | [LTX Studio — Film Composition](https://ltx.studio/glossary/film-composition) | [Brad Dailey — Balance: Composition + Values](https://www.braddailey.com/balance-composition-values) | [Fiveable — Principles of Visual Composition](https://fiveable.me/cinematography/unit-4/principles-visual-composition/study-guide/Dc66oJG3NVxqTt26) | [Number Analytics — Rule of Space](https://www.numberanalytics.com/blog/the-art-of-rule-of-space-in-cinematography)
- Rule of thirds and golden ratio — [IxDF — What is the Rule of Thirds?](https://ixdf.org/literature/topics/rule-of-thirds) | [UX Design Institute — Guide to Rule of Thirds](https://www.uxdesigninstitute.com/blog/guide-to-the-rule-of-thirds-in-ux/) | [Loop11 — Rule of Thirds in Mobile UX](https://www.loop11.com/what-is-the-rule-of-thirds-in-the-ux-mobile-design-process/) | [Figma — Golden Ratio](https://www.figma.com/resource-library/golden-ratio/) | [LogRocket — Golden Ratio in UX](https://blog.logrocket.com/ux-design/using-the-golden-ratio-in-ux-design/) | [iMark Infotech comparison](https://www.imarkinfotech.com/rule-of-thirds-vs-golden-ratio-in-ux-ui-design-a-comparison/) | [Bootcamp Medium — Golden Ratio in UI](https://bootcamp.uxdesign.cc/golden-ratio-in-user-interface-d70f4d652872) | [IxDF — Rule of Thirds layout sweet spots](https://ixdf.org/literature/article/the-rule-of-thirds-know-your-layout-sweet-spots) | [AND Academy — Meaning of Rule of Thirds in Design](https://www.andacademy.com/resources/glossary/ui-ux-design/rule-of-thirds/) | [Fiveable — Rule of Thirds and Golden Ratio in Visual Storytelling](https://fiveable.me/visual-storytelling/unit-3/rule-thirds-golden-ratio/study-guide/AmfclEisN7GWFEaa)
- Gestalt principles — [UserTesting — 7 Gestalt principles](https://www.usertesting.com/blog/gestalt-principles) | [Toptal — Gestalt for UI](https://www.toptal.com/designers/ui/gestalt-principles-of-design) | [IxDF — Gestalt principles](https://ixdf.org/literature/topics/gestalt-principles) | [Lyssna — How Gestalt Principles Enhance Web Design](https://www.lyssna.com/blog/gestalt-design-principles/) | [Bejamas — Practical Application of Gestalt](https://bejamas.com/blog/gestalt-principles-of-design) | [Optimal Workshop — Gestalt in UX](https://www.optimalworkshop.com/blog/understanding-the-gestalt-principles-of-perception-for-ux) | [UX Tigers — Gestalt for Visual UI Design](https://www.uxtigers.com/post/gestalt-principles) | [Figma — What Are The Gestalt Principles?](https://www.figma.com/resource-library/gestalt-principles/) | [Aela — Gestalt in UX/UI Projects](https://www.aela.io/en/blog/all/gestalt-principles-apply-them-uxui-design-projects) | [SVGator — Guide to Gestalt Principles](https://www.svgator.com/blog/gestalt-principles-of-design/)
- Cinematography composition rules — [StudioBinder — Rules of Shot Composition](https://www.studiobinder.com/blog/rules-of-shot-composition-in-film/) | [Artlist — Shot Composition Framing](https://artlist.io/blog/shot-composition-framing/) | [Motion Array — 7 Rules](https://motionarray.com/learn/filmmaking/shot-composition-framing-rules/) | [Freewell Gear — Composition Rules](https://freewellgear.com/blogs/news/photography-composition-rules) | [SolveigMM — Shot Composition](https://www.solveigmm.com/blog/en/shot-composition-framing-your-videos-like-a-pro/) | [DIY Video Editor — Shot Composition](https://diyvideoeditor.com/shot-composition-how-to-frame-your-scenes-like-a-pro/) | [Pixel Valley Studio — Beyond the 1/3 Rule](https://pixelvalleystudio.com/pmf-articles/framing-and-composition-cinematography-going-beyond-the-13-rule) | [SLR Lounge — Video Composition](https://www.slrlounge.com/rules-of-composition-video/) | [Venture Videos — Shot Composition](https://www.venturevideos.com/insight/learning-the-basics-of-shot-composition) | [EditMate — 9 Rules of Video Composition](https://www.editmate.com/video-composition/)
- Storaro / *Apocalypse Now* — [ASC — Apocalypse Now: A Clash of Titans](https://theasc.com/articles/flashback-apocalypse-now)
- Mise-en-scène and blocking — [NIPAI — Mise-en-scène and Blocking](https://www.nipai.org/post/miseenscene-and-blocking) | [StudioBinder — 20 Mise en Scène Elements](https://www.studiobinder.com/blog/mise-en-scene-elements/) | [Fiveable — Blocking and Actor Placement](https://fiveable.me/film-aesthetics/unit-3/blocking-actor-placement/study-guide/SeaXJpxJmQnYtYIe) | [Wikipedia — Mise-en-scène](https://en.wikipedia.org/wiki/Mise-en-sc%C3%A8ne) | [Senses of Cinema — John Cassavetes](https://www.sensesofcinema.com/2016/great-directors/john-cassavetes/) | [MasterClass — How to Block a Scene](https://www.masterclass.com/articles/how-to-block-a-scene) | [SPS Academy — Mastering Blocking](https://www.southsideperformancestudio.co.uk/blog/mastering-blocking-a-guide-to-understanding-scene-movement-in-acting) | [Mark Murphy — Blocking 101](https://markmurphydirector.co.uk/blocking-101-choreographing-actor-movements/) | [Screening Shakespeare — Blocking](https://screenshakespeare.org/mise-en-scene/blocking/) | [Saturation — What is Mise En Scene](https://saturation.io/blog/mise-en-scene)

### Algorithm and computational layout

- Force-directed: [Kobourov — Force-Directed Drawing Algorithms PDF](https://cs.brown.edu/people/rtamassi/gdhandbook/chapters/force-directed.pdf) | [yWorks — Force-Directed Graph Layout](https://www.yworks.com/pages/force-directed-graph-layout) | [User-Guided Force-Directed Graph Layout — arxiv 2506.15860](https://arxiv.org/html/2506.15860) | [PMC — User-Guided Force-Directed Graph Layout](https://pmc.ncbi.nlm.nih.gov/articles/PMC12306815/) | [Telerik — Force-Directed Diagram Layout](https://www.telerik.com/products/aspnet-ajax/documentation/controls/diagram/structure/layout/force-directed) | [ESRI ArcGIS Pro — Force Directed Layout reference](https://pro.arcgis.com/en/pro-app/latest/help/data/network-diagrams/force-directed-layout-reference.htm) | [Nevron — Force Directed Layouts](https://helpdotnetvision.nevron.com/UsersGuide_Layouts_Force_Directed_Layouts.html) | [MDPI — Multivariate Network Layout with Attribute Constraints](https://www.mdpi.com/2076-3417/12/9/4561)
- Constrained force-directed: [Adaptagrams cola::ConstrainedFDLayout](https://www.adaptagrams.org/documentation/classcola_1_1ConstrainedFDLayout.html)
- Cassowary: [Cassowary TOCHI 2001 PDF](https://constraints.cs.washington.edu/solvers/cassowary-tochi.pdf) | [Wikipedia — Cassowary software](https://en.wikipedia.org/wiki/Cassowary_(software)) | [UW Cassowary toolkit](https://constraints.cs.washington.edu/cassowary/) | [Cassowary docs theory](https://cassowary.readthedocs.io/en/latest/topics/theory.html) | [ACM TOCHI abstract](https://dl.acm.org/doi/abs/10.1145/504704.504705) | [GitHub — Cassowary in Swift](https://github.com/inamiy/Cassowary) | [Researchgate — Cassowary Algorithm](https://www.researchgate.net/publication/2615412_The_Cassowary_Linear_Arithmetic_Constraint_Solving_Algorithm) | [Hacker News discussion](https://news.ycombinator.com/item?id=43362528) | [croisant.net — Understanding UI Layout Constraints](https://croisant.net/blog/2016-02-24-ui-layout-constraints-part-1/)
- Simulated annealing: [Davidson & Harel — Drawing Graphs Nicely PDF](https://dl.acm.org/doi/pdf/10.1145/234535.234538) | [Wikipedia — Simulated Annealing](https://en.wikipedia.org/wiki/Simulated_annealing) | [GeeksforGeeks — Simulated Annealing](https://www.geeksforgeeks.org/artificial-intelligence/what-is-simulated-annealing/) | [Inglo Games — Optimization and Simulated Annealing](https://inglo-games.github.io/2019/09/21/sim-annealing.html) | [UCLA siggraph11 — Furniture arrangement](https://web.cs.ucla.edu/~dt/papers/siggraph11/siggraph11.pdf) | [Springer — SA and GA for Facility Layout](https://link.springer.com/article/10.1023/A:1008623913524) | [CAADRIA 2020 — Architectural Layout via SA](https://papers.cumincad.org/cgi-bin/works/paper/caadria2020_024) | [GitHub — fogleman/GraphLayout SA-based](https://github.com/fogleman/GraphLayout) | [Researchgate — Drawing Graphs Nicely with SA](https://www.researchgate.net/publication/2545070_Drawing_Graphs_Nicely_Using_Simulated_Annealing)
- MDP / RL placement: [Mirhoseini et al. — Macro Placement with RL arxiv 2109.02587](https://ar5iv.labs.arxiv.org/html/2109.02587) | [IEEE — same paper](https://ieeexplore.ieee.org/abstract/document/9531313) | [Wikipedia — Markov Decision Process](https://en.wikipedia.org/wiki/Markov_decision_process) | [Wiering & van Otterlo — Intro to RL textbook](https://www.ai.rug.nl/~mwiering/Intro_RLBOOK.pdf) | [Springer — RL and MDPs chapter](https://link.springer.com/chapter/10.1007/978-3-642-27645-3_1) | [Neptune — MDP in RL](https://neptune.ai/blog/markov-decision-process-in-reinforcement-learning) | [Gibberblot — MDPs notes](https://gibberblot.github.io/rl-notes/single-agent/MDPs.html) | [CMU 10-601 MDP+RL slides](https://www.cs.cmu.edu/~10601b/slides/MDP_RL.pdf) | [IEEE — MDP for RL paper](https://ieeexplore.ieee.org/document/9678310/) | [ADS — Macro Placement with RL](https://ui.adsabs.harvard.edu/abs/2021arXiv210902587J/abstract)
- Boids and emergent swarms: [Reynolds — Boids paper 1987](https://www.red3d.com/cwr/papers/1987/boids.html) | [Wikipedia — Boids](https://en.wikipedia.org/wiki/Boids) | [Reynolds — red3d.com/cwr/boids](https://www.red3d.com/cwr/boids/) | [Reynolds — siggraph97 course PDF](https://www.cs.toronto.edu/~dt/siggraph97-course/cwr87/) | [Ohio State Pressbooks — Flocking Systems](https://ohiostate.pressbooks.pub/graphicshistory/chapter/19-2-flocking-systems/) | [befores & afters — History of CG bird flocking](https://beforesandafters.com/2022/04/07/a-history-of-cg-bird-flocking/) | [Medium — Simulating Flocking with Boids](https://medium.com/fragmentblog/simulating-flocking-with-the-boids-algorithm-92aef51b9e00) | [GitHub — rystrauss/boids](https://github.com/rystrauss/boids) | [GitHub — Naguib BoidsSimulation](https://github.com/Michael-Naguib/BoidsSimulation) | [agentpy — Flocking behavior tutorial](https://agentpy.readthedocs.io/en/latest/agentpy_flocking.html)
- Swarm attractor/repulsor theory: [Researchgate — Stable swarm aggregations](https://www.researchgate.net/publication/4006489_A_class_of_attractionrepulsion_functions_for_stable_swarm_aggregations) | [PMC — Cognitive swarming with attractor dynamics](https://pmc.ncbi.nlm.nih.gov/articles/PMC7183509/) | [Nature — Swarm Intelligence collection](https://www.nature.com/collections/cgbgjbahac) | [arxiv 2309.11408 — Indirect Swarm Control](https://arxiv.org/html/2309.11408v2) | [Thomy Phan — Emergence in Multi-Agent Systems](https://thomyphan.github.io/research/emergence/) | [arxiv 2502.15937 — Emergent Robot Swarm Behaviors](https://arxiv.org/html/2502.15937v1) | [Emergent Mind — Agent Swarm Dynamics](https://www.emergentmind.com/topics/agent-swarm) | [JHU APL — Neuro-Inspired Dynamic Replanning](https://www.jhuapl.edu/sites/default/files/2024-09/35-04-Hwang.pdf) | [Sciencedirect — Swarm manipulation in VR](https://www.sciencedirect.com/science/article/pii/S0097849324002486) | [HAL — Emergent Complex Behaviors for Swarm Robotic Systems](https://hal.science/hal-00955949/document)
- Reservoir sampling: [Wikipedia — Reservoir Sampling](https://en.wikipedia.org/wiki/Reservoir_sampling) | [Vitter — algorithms K, L, M paper](https://dl.acm.org/doi/10.1145/198429.198435) | [pythonspeed — Timesliced Reservoir Sampling](https://pythonspeed.com/articles/reservoir-sampling-profilers/) | [QuestDB — Reservoir Sampling](https://questdb.com/glossary/reservoir-sampling/) | [GeeksforGeeks — Reservoir Sampling](https://www.geeksforgeeks.org/dsa/reservoir-sampling/) | [Florian — Reservoir Sampling](https://florian.github.io/reservoir-sampling/) | [App Metrics — Reservoir Sampling](https://alhardy.github.io/app-metrics-docs/getting-started/sampling/index.html) | [Taylor & Francis — Reservoir Sampling overview](https://taylorandfrancis.com/knowledge/Engineering_and_technology/Computer_science/Reservoir_sampling/) | [Austin Rochford — Reservoir Sampling for Streaming Data](https://austinrochford.com/posts/2014-11-30-reservoir-sampling.html) | [Rice COMP 480 — Stream Computing scribe notes](https://www.cs.rice.edu/~as143/COMP480_580_Spring19/scribe/S8.pdf)

### Layout engines and design tools

- Browser layout: [Servo Layout Overview](https://github.com/servo/servo/wiki/Layout-Overview) | [Wikipedia — Servo](https://en.wikipedia.org/wiki/Servo_(software)) | [Mozilla Hacks — Quantum CSS / Stylo](https://hacks.mozilla.org/2017/08/inside-a-super-fast-css-engine-quantum-css-aka-stylo/) | [Servo's official site](https://servo.org/) | [Servo About page](https://servo.org/about/) | [Servo browser engine research wiki](https://github.com/servo/servo/wiki/Browser-Engine-Research) | [HiPC 2016 — parallel browser energy modeling](https://hpcforge.eng.uci.edu/publication/hipc16-browser/hipc16-browser.pdf) | [Phoronix — Servo 0.0.1 release](https://www.phoronix.com/news/Servo-0.0.1-Released)
- Figma: [Figma Help — Guide to auto layout](https://help.figma.com/hc/en-us/articles/360040451373-Guide-to-auto-layout) | [Figma Help — Apply constraints](https://help.figma.com/hc/en-us/articles/360039957734-Apply-constraints-to-define-how-layers-resize) | [UIPrep — When to use Constraints vs Auto Layout](https://www.uiprep.com/blog/when-to-use-constraints-vs-auto-layout) | [Joey Banks — Techniques for Auto Layout in Figma](https://medium.com/@joeyabanks/techniques-for-using-auto-layout-in-figma-fb2c874940ae) | [NALS Engineering — Constraints and Auto-Layout in Figma](https://medium.com/@NALSengineering/understand-constrain-and-auto-layout-in-figma-5aca5c762988) | [Riya Chatterjee — Figma guide for auto layout](https://medium.com/design-bootcamp/figma-guide-for-auto-layout-and-constraints-f570626c74ca) | [Moon Learning — Responsive Figma deep dive](https://www.moonlearning.io/responsive-figma) | [Zeplin Gazette — When (and when not) to use Auto Layout](https://blog.zeplin.io/collaboration/when-and-when-not-to-use-auto-layout-in-figma/) | [Figma Forum — Auto layout vs Constraints](https://forum.figma.com/ask-the-community-7/difference-between-auto-layout-align-and-constraints-5824) | [Figma Auto Constraints plugin](https://www.figma.com/community/plugin/1155285435916019216/auto-constraints)
- OBS / broadcast: [Streamgeeks — Automatic Scene Switching in OBS](https://streamgeeks.us/automatic-scene-switching-in-obs/) | [OBS Forums — Advanced Scene Switcher](https://obsproject.com/forum/resources/advanced-scene-switcher.395/) | [OBS Forums — Auto Scene Switcher](https://obsproject.com/forum/threads/auto-scene-switcher.153195/) | [OBS Forums — Timed Automatic Scene Switching](https://obsproject.com/forum/threads/timed-automatic-scene-switching.156214/) | [OBS Forums — Automatic scene transitions](https://obsproject.com/forum/threads/automatic-scene-transitions.120003/) | [OBS Forums — Scene Switching tag](https://obsproject.com/forum/tags/scene-switching/) | [OBS Forums — Advanced Scene Switcher page 156](https://obsproject.com/forum/threads/advanced-scene-switcher.48264/page-156) | [eCampus Ontario Pressbooks — Automatic Scene Switcher](https://ecampusontario.pressbooks.pub/osdigcomm/chapter/automatic-window-switcher/) | [Streamer Magazine — OBS transition settings guide](https://alive-project.com/en/streamer-magazine/article/2091/) | [ReelMind — OBS Transitions with Transparency](https://reelmind.ai/blog/obs-transitions-with-transparency-advanced-scene-switching-for-live-streaming) | [Envato Tuts+ — Motion Graphics for Live Stream](https://photography.tutsplus.com/articles/howto-motion-graphics-live-stream-video--cms-35221) | [Ross XPression — Real-Time Motion Graphics](https://www.rossvideo.com/live-production/graphics/xpression/) | [Unreal — Broadcast Cinematics explainer](https://www.unrealengine.com/en-US/explainers/broadcast-and-live-events/what-are-broadcast-cinematics) | [Zero Density — Real-Time Motion Graphics](https://www.zerodensity.io/) | [Fiveable — Motion Graphics study guide](https://fiveable.me/tv-studio-production/unit-7/motion-graphics/study-guide/mKj0uIJNJaMsJUTH) | [Blackmagic Fusion 21 — Broadcast Graphics](https://www.blackmagicdesign.com/products/fusion/broadcastgraphics) | [School of Motion — Sports MoGraph](https://www.schoolofmotion.com/blog/how-to-design-show-stopping-sports-mograph) | [Udemy — TV Broadcast Design with After Effects](https://www.udemy.com/course/tv-broadcast-design-with-adobe-after-effects/) | [Nightwolves Studio — Broadcast Cinematic Design](https://nightwolves.studio/broadcast-design-services) | [FlexClip — Create Broadcast Graphic in AE](https://www.flexclip.com/learn/broadcast-graphic.html)

### Compositing, depth, animation history

- Z-order and Painter's Algorithm: [Grokipedia — Z-order](https://grokipedia.com/page/Z-order) | [Webperf Tips — Layers and Compositing](https://webperf.tips/tip/layers-and-compositing/) | [Painter's algorithm — Wikipedia](https://en.wikipedia.org/wiki/Painter's_algorithm) | [BCALabs — Painter Algorithm in Computer Graphics](https://bcalabs.org/subject/painter-algorithm-in-computer-graphics) | [Researchgate — Local Layering paper](https://www.researchgate.net/publication/220183661_Local_layering)
- Layered animation and compositing: [3DArtist — Compositing Layers Explained](https://3dartist.substack.com/p/basic-compositing-layers-explained) | [Blender Projects — Layered Animation in Digital Art](https://projects.blender.org/yg4-yelis/NEWBlogs/projects/1273) | [fxguide — The Art of Deep Compositing](https://www.fxguide.com/fxfeatured/the-art-of-deep-compositing/) | [Adobe Animate — Parallax via Layer Depth](https://helpx.adobe.com/animate/using/layer-depth.html) | [ReelMind — After Effects Compositing Tutorial](https://reelmind.ai/blog/after-effects-compositing-tutorial-layering-effects-for-cinematic-depth)
- Generative motion design / AI motion: [MotionCanvas — arxiv 2502.04299](https://arxiv.org/html/2502.04299v1) | [Pixflow — How AI Is Redefining Motion Design in 2025](https://pixflow.net/blog/how-ai-is-redefining-motion-design-in-2025/) | [GenMotion — arxiv 2112.06060](https://arxiv.org/abs/2112.06060) | [Springer — Motion Matching: Data-Driven Character Animation](https://link.springer.com/rwe/10.1007/978-3-031-23161-2_511) | [Sage — Biomechanical AI motion 2025](https://journals.sagepub.com/doi/10.1177/14727978251348639) | [DearDeer — Enhancing Static Charts with Data-driven Animations TVCG21](https://deardeer.github.io/pub/TVCG21_Ant.pdf) | [Games-105 — Data-driven Animation lecture notes](https://games-105.github.io/ppt/05%20-%20Data-driven%20Animation.pdf) | [tkh44 — data-driven-motion React](https://github.com/tkh44/data-driven-motion) | [Datalabs — Animated Data Videos](https://www.datalabsagency.com/animated-data-videos/) | [Researchgate — Data-driven animation with mocap](https://www.researchgate.net/publication/234798010_Introduction_to_data-driven_animation_Programming_with_motion_capture)
- Casey Reas / Memo Akten / generative art: [Casey Reas portfolio](https://reas.com/) | [bitforms gallery — Casey Reas artist page](https://www.bitforms.art/artist/casey-reas) | [Wikipedia — Casey Reas](https://en.wikipedia.org/wiki/Casey_Reas) | [bitforms — Process/Drawing exhibition](https://www.bitforms.art/exhibition/casey-reas-process-drawing) | [LANDMARKS UT Austin — A Mathematical Theory Of Communication](https://landmarks.utexas.edu/artwork/mathematical-theory-communication) | [Le Random — Reas on history of generative art Pt 1](https://www.lerandom.art/editorial/reas-history-1) | [Anteism — Casey Reas online resources](https://www.anteism.com/casey-reas-resources) | [Photobook Journal — Reas GAN book review](https://photobookjournal.com/2025/08/21/casey-reas-making-pictures-with-generative-adversarial-networks/) | [Artforum — Reas portfolio feature](https://www.artforum.com/features/casey-reas-portfolio-1234737006/) | [Visual Alchemist — generative art tools comparison](https://visualalchemyx.wordpress.com/2024/08/31/comparing-top-generative-art-tools-processing-openframeworks-p5-js-and-more/)

### Music phrasing and visual rhythm

- Tension and release / phrasing: [School of Composition — Tension and Release](https://www.schoolofcomposition.com/what-is-tension-and-release-in-music/) | [Wikipedia — Musical phrasing](https://en.wikipedia.org/wiki/Musical_phrasing) | [Pat Pattison — The Art of Phrasing](https://www.patpattison.com/art-of-phrasing) | [Musical-U — Tension and Release in Music](https://www.musical-u.com/learn/tension-in-music/) | [MasterClass — 6 Ways to Create Tension and Release](https://www.masterclass.com/articles/ways-to-create-tension-and-release-in-music) | [Point Blank — Tension and Release in EDM](https://www.pointblankmusicschool.com/blog/creating-tension-and-release-in-electronic-dance-music/) | [EDMProd — Advanced Guide to Tension](https://www.edmprod.com/tension/) | [Medium — Tension and Release fundamental listening](https://medium.com/@jgoncalonogueira/tension-and-release-the-fundamental-way-we-listen-to-music-46406dce5fd3) | [My Music Theory — Phrase, Patterns and Sequences](https://mymusictheory.com/keyboard-reconstruction-abrsm-grade-8/phrase-patterns-and-sequences-keyboard-reconstruction/) | [Quora — What is phrasing in rhythm](https://www.quora.com/What-is-phrasing-in-rhythm)
- Visual beat / VJ practice: [Davis & Agrawala — Visual Rhythm and Beat PDF](https://www.abedavis.com/files/papers/VisualRhythm_Davis18.pdf) | [Davis — visualbeat](https://abedavis.com/visualbeat/) | [ACM TOG — Visual rhythm and beat](https://dl.acm.org/doi/10.1145/3197517.3201371) | [Springer — Dance to the beat](https://link.springer.com/article/10.1007/s41095-018-0115-y) | [Beatflo — How VJs Sync Visuals with Music](https://beatflo.net/resources/blog/how-vjs-sync-visuals-music-exploring-art-visual-synchronization) | [Beatflo — NUCLYR Beat Sync Visuals Set](https://beatflo.net/products/nuclyr-beat-sync-visuals-set) | [ArKaos VJ/DJ — Live Video Performance](https://vj.arkaos.com/grandvj/about) | [DjMirror — DJ/VJ visualization features](https://djmirror.com/features/) | [Synesthesia — Live Music Visualizer](https://synesthesia.live/) | [Visualz Studio — VJ tools](https://www.visualzstudio.com/)

### Affordance theory and perception

- Gibson and affordance: [Wikipedia — Affordance](https://en.wikipedia.org/wiki/Affordance) | [Gibson — Ecological Approach Ch.8 PDF](https://cs.brown.edu/courses/cs137/2017/readings/Gibson-AFF.pdf) | [Arch Psych — Gibson's Affordance in Architecture](https://www.archpsych.co.uk/post/gibson-affordance-theory-in-architecture-understanding-the-design-of-possibility) | [Learning Theories — Affordance Theory](https://learning-theories.com/affordance-theory-gibson.html) | [IxDF — Affordances Encyclopedia of HCI](https://www.interaction-design.org/literature/book/the-encyclopedia-of-human-computer-interaction-2nd-ed/affordances) | [Tandfonline — Mind in action: expanding affordance](https://www.tandfonline.com/doi/full/10.1080/09515089.2024.2365554) | [IxDF — Affordances in Glossary of HCI](https://ixdf.org/literature/book/the-glossary-of-human-computer-interaction/affordances) | [Affordance Theory Medium — ontological no-man's land](https://affordancetheory.medium.com/gibsons-affordances-a-journey-to-the-ontological-no-man-s-land-bfd88d07e9a7) | [MedEdMentor — Affordance theory database](https://mededmentor.org/theory-database/theory-index/affordance/) | [IJIP — Gibson's Ecological Theory of Development PDF](https://ijip.in/wp-content/uploads/2020/05/B00351V2I42015.pdf)
- Heider-Simmel attribution: [Nature Sci Reports — Heider Simmel revisited in VR](https://www.nature.com/articles/s41598-024-65532-0) | [PMC — Heider capacity in dynamic scenes](https://pmc.ncbi.nlm.nih.gov/articles/PMC6396302/) | [Sage — Judging social interaction in Heider Simmel](https://journals.sagepub.com/doi/abs/10.1177/1747021819838764) | [movieperception WordPress — perception attribution causality](https://movieperception.wordpress.com/2013/10/29/perception-attribution-of-causality/) | [Researchgate — Heider Simmel revisited PDF](https://www.researchgate.net/publication/284514443_Heider_and_simmel_1944_revisited_Causal_attribution_and_the_animated_film_technique) | [PMC — Heider Simmel in VR PMC11269668](https://pmc.ncbi.nlm.nih.gov/articles/PMC11269668/) | [All About Psychology — Fritz Heider](https://www.all-about-psychology.com/fritz-heider.html) | [Frontiers Psychology — review article PDF](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1168739/pdf) | [Researchgate — Heider Simmel revisited Kassin profile](https://www.researchgate.net/profile/Saul-Kassin/publication/324832066_Heider_and_Simmel_1944_revisited_Causal_attribution_and_the_animated-film_technique/links/5ae656100f7e9b9793c7a47f/Heider-and-Simmel-1944-revisited-Causal-attribution-and-the-animated-film-technique.pdf) | [BWH Heider Cartoon Database](https://search.bwh.harvard.edu/new/HeiderCartoonDatabase.html)

### Software studies / cinematic compositing

- Lev Manovich: [Manovich — Soft Cinema project](https://manovich.net/index.php/projects/soft-cinema) | [Manovich — What is Digital Cinema 1995 PDF](https://manovich.net/content/04-projects/009-what-is-digital-cinema/07_article_1995.pdf) | [TUe Alice — The Language of New Media PDF](https://www.alice.id.tue.nl/references/manovich-2001.pdf) | [MIT Press — The Language of New Media](https://mitpress.mit.edu/9780262632553/the-language-of-new-media/) | [Tiffany's Window — Montage according to Manovich](https://tiffanyswindow.wordpress.com/2014/10/21/montage-according-to-lev-manovich/) | [Wikipedia — Database cinema](https://en.wikipedia.org/wiki/Database_cinema) | [Communication Chaos — Layers and Manovich](https://communicationchaos.wordpress.com/2014/06/09/its-all-about-the-layers-and-manovich/) | [Fotokiji — Manovich Five Core Principles explained](https://fotokiji.com/120) | [EUP Film-Philosophy — Birth of Software Studies](https://www.euppublishing.com/doi/full/10.3366/film.2003.0055) | [Academia — Manovich, Movies and Montage](https://www.academia.edu/9790068/Manovich_Movies_and_Montage_New_Media_New_Narrative)

---

**End of dispatch 1.** The next dispatches in the series will cover (a) the visual taxonomy / per-Programme aesthetic catalog, (b) the empirical loop and metric harness, and (c) the integration epic that lands the post-pass behind a feature flag and steps it to default-on across one livestream cycle.
