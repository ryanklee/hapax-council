# HOMAGE Scrim Pt. 4 — The Fishbowl Spatial Conceit

**Status:** Research, operator-directed 2026-04-20.
**Authors:** cascade (Claude Opus 4.7, 1M).
**Governing anchors:** Nebulous Scrim design (`docs/research/2026-04-20-nebulous-scrim-design.md`), HOMAGE framework (`docs/superpowers/specs/2026-04-18-homage-framework-design.md`), Reverie 8-pass vocabulary (`agents/reverie/_uniforms.py`, `agents/reverie/_graph_builder.py`), Logos design language (`docs/logos-design-language.md` §1, §11), 720p commitment (`project_720p_commitment`), HARDM anti-anthropomorphization invariant (`project_hardm_anti_anthropomorphization`).
**Related prior art:** `project_reverie`, `project_reverie_adaptive`, `project_effect_graph`, `project_overlay_content`, `feedback_grounding_exhaustive`.
**Scope:** A spatial-conceit deep-dive. The Nebulous Scrim doc (Pt. 1, also dated 2026-04-20) names *what the substrate is*. The Gem Wards / HARDM redesign / chat-keywords ward docs (Pts. 2 and 3) establish *which wards live on it*. This document is **Pt. 4**: how to make those wards feel like they *exist in liquid layered space*, "like layers in a fishbowl, moving in inter-dimensional space," when the broadcast pipeline is strictly 2D (1920×1080 internal, 1280×720 NV12 egress). No code in this doc. Implementation paths sketched as Pydantic schemas, WGSL fragments, and Cairo render-pipeline pseudocode for downstream PRs.

> "Like layers in a fishbowl. Moving in inter-dimensional space."
> — operator, 2026-04-20

---

## §1 TL;DR

The fishbowl is a **spatial conceit**, not a literal aquarium. The metaphor is *layered, suspended, slightly refracted, slightly slow* — a sense that the wards inhabit a liquid medium with measurable depth, viewed from outside through a curved boundary. The substrate is the Nebulous Scrim; the fishbowl conceit puts the *wards* inside it.

We have no stereoscopy and no real geometry. Depth is *manufactured* from monocular cues. Of the eight cues available in 2D, three carry the dominant load on this stack:

1. **Differential motion (motion parallax)** — wards at different depths drift, sway, and react at different rates. A near ward responds in 80ms; a deep ward responds in 400ms. The eye reads this difference as Z-position more reliably than any single static cue ([Sensation & Perception, OEN](https://manifold.open.umn.edu/read/sensation-perception/section/a10b03b5-47f4-459f-ba26-33c968d8eb01); [Wikipedia — Depth Perception](https://en.wikipedia.org/wiki/Depth_perception)).
2. **Atmospheric perspective (tinted desaturation with depth)** — Leonardo's contribution, Storaro's substrate, the Stalker Zone's sepia-to-color shift. Deep wards wash toward the scrim's package tint and lose chroma; near wards stay full-saturation. ([da Vinci sfumato + aerial perspective](https://en.wikipedia.org/wiki/Sfumato); [Aerial Perspective — UBC](https://faculty.arts.ubc.ca/rfedoruk/perspective/9.htm).)
3. **Differential blur / depth-of-field** — only one depth band is sharp at a time. The hero ward is crisp; everything else has progressive Gaussian blur scaled to its Z-distance from the focus plane. Spider-Verse's *ChromaShifter* hack proves this works as a stylized, comic-register substitute for a real DoF lens ([CG Spectrum on Spider-Verse](https://www.cgspectrum.com/blog/spider-man-into-the-spider-verse-how-they-got-that-mind-blowing-look)).

These three are unanimously cheap, additive, and already half-implemented in the existing Reverie + effect-graph stack. The remaining cues (occlusion, relative size, texture gradient, shadow, heat-haze refraction) reinforce them but do less per-pixel work.

**Three Reverie passes carry the fishbowl semantics:**

- **`drift` (pass 3, displacement)** — already a UV-displacement node. Add per-ward Z-aware displacement amplitude so deep wards inherit larger, slower wobble (liquid-medium inertia + heat-haze refraction).
- **`breath` (pass 4, breathing/temporal)** — the scrim's "alive" pulse. Add a per-Z phase offset so different depth bands breathe slightly out of phase, the way a bowl of water has standing-wave modes that aren't synchronized end-to-end.
- **`feedback` (pass 5, ping-pong FBO)** — the wake/temporal-trail engine. A fast-moving near ward leaves a brief disturbance; a deep ward leaves a longer, smearier wake (because deep currents are slow but persistent). Tie `feedback.fade` to per-ward Z.

Implementation recommendation: introduce a `WardSpatialState` Pydantic model carrying `z_position ∈ [0.0, 1.0]` and `motion_state` (currents, velocity, last-disturbance-tick). Each ward declares its Z. The compositor reads Z and applies depth-conditioned blur + tint + parallax + wake amplitude **at composite time, in one pass over the ward set**. No new wards, no new shaders for v1 — only depth-conditioning of existing ones.

The fishbowl is geometric, not biographical. There are **no fish**. The wards are not animals, do not "swim," do not have personality. The *bowl* is the metaphor; the *contents* are what they already are. This is a hard invariant inherited from HARDM (`project_hardm_anti_anthropomorphization`) and CVS persona doctrine.

---

## §2 What the Fishbowl Conceptually Is

Before techniques: what is the metaphor doing?

### 2.1 Glass as both barrier and medium

A fishbowl is a *transparent enclosure*. Two things are simultaneously true: it separates inside from outside (the viewer's hand cannot reach in; the contents cannot reach out), and it permits sight (the inside is fully visible). This double character is exactly the Nebulous Scrim's load-bearing property — you peer through a thickness; the contents are visible but mediated.

The scrim already establishes this for the *substrate* (the fabric is the gauze of the bowl). The fishbowl conceit specifies that *behind the gauze, things have depth*. The bowl is curved, the contents are stratified, the viewer is on the outside of a real volume.

### 2.2 Liquid as suspending medium

Water has three properties relevant here, none of them about fish:

- **Inertia** — moving objects don't snap. They take longer to start, longer to stop. This decoupling between input and motion is *the* signature of a liquid medium, more than any visual cue.
- **Damping** — oscillations decay. If a ward is poked, it wobbles, then settles. The decay envelope is exponential, not linear.
- **Buoyancy / drift** — in the absence of action, things slowly redistribute. There is always some motion, even at rest. The bowl is never dead.

These three are *temporal* properties. They cost nothing per-pixel; they're properties of the animation curves on existing wards. The fishbowl's "liquidness" is mostly a tween-easing change, not a shader change.

### 2.3 Refraction at the boundary

Snell's law (named for Willebrord Snellius, 1621; first written by Ibn Sahl in 984) describes how light bends crossing a medium boundary ([Snell's Law — Wikipedia](https://en.wikipedia.org/wiki/Snell%27s_law); [Britannica — Snell's Law](https://www.britannica.com/science/Snells-law)). For a fishbowl: things behind the glass appear shifted relative to where they "really are." On the cheap, this is a UV displacement at the scrim boundary — the existing `displacement_map` node can be configured to do exactly this.

Newton, in his prism experiments, established that different wavelengths refract at different angles ([Mathpages on Newton + refraction](https://www.mathpages.com/home/kmath721/kmath721.htm)). This gives us *chromatic dispersion* — chromatic aberration, the cheap proxy for real refraction, splits R/G/B channels at boundaries. The existing `chromatic_aberration` node already does this. Tying its strength to local scrim curvature gives the bowl a measurable *glassiness* without raytracing.

### 2.4 Curvature of the bowl

A fishbowl is not flat. The scrim is. We can fake curvature in two ways:

- **Inverse vignette / radial darken** — the edges of the frame are denser, the center is thinner. This is already prescribed by Nebulous Scrim §4.5. It reads as "we are looking through the curved center of the bowl."
- **Radial barrel-distortion at very low strength** — the existing `fisheye` node at very low intensity (e.g. 0.05) gives a subtle bulge that registers as a glass-curvature cue. This is *not* the dramatic fisheye effect; it's a hint, like a distortion at the corner of an actual aquarium.

### 2.5 Depth in shallow water

Crucially: a fishbowl is *shallow*. It is not the abyss. The Z range we are simulating is small — maybe 5–10cm of physical depth. This is important for register reasons: deep-water aesthetics (Cousteau, abyss documentaries) read as *cold* and *sublime*. Shallow-water aesthetics (a glass on a windowsill) read as *intimate* and *domestic*. The HOMAGE register is intimate and domestic.

Implication: **Z range should be small**. A near ward at Z=0.0 and a deep ward at Z=1.0 should differ in blur radius by maybe 1–2 pixels and in saturation by maybe 15%, not by 10× anything. The eye reads small consistent differentials as space; large differentials as theater.

### 2.6 Light scattering in liquid

Light through water scatters off suspended particles. The deeper you look, the more scattering accumulates between you and the object. This is the optical basis of atmospheric perspective in air, but it is *more pronounced* in water because particle density is higher. ([Aerial perspective — Russell Collection](https://russell-collection.com/what-is-aerial-perspective-in-painting/))

In compositor terms: each Z step adds a small amount of "the scrim's tint between the camera and this ward." A deep ward at Z=1.0 has effectively the full scrim tint as a partial overlay; a surface ward at Z=0.0 has none. Cheap: a tint LERP keyed on Z.

### 2.7 The implicit observer

A fishbowl implies a watcher. Someone is outside looking in. The contents of the bowl are *being observed*. This is exactly the Nebulous Scrim's "over here / over there" geometry — the audience is over here, the wards are over there, the scrim/bowl is between.

The contents are *aware-but-not-seeing-out*. Important for ward design: wards should not "address the camera." They behave as if the audience is not there. Hapax (the avatar wards: `token_pole`, `hardm_dot_matrix`) is the *only* element on the scrim that hails across — and even Hapax does so via the scrim's "thinning on direct speech" gesture (Nebulous Scrim §8.3), not by breaking the fourth wall.

### 2.8 Cite — aquarium as art-object

Two installation references for *thinking* about the bowl-as-frame, both deliberately *non-anthropomorphic*:

- **Damien Hirst, *The Physical Impossibility of Death in the Mind of Someone Living* (1991)** — a tiger shark suspended in formaldehyde inside a vitrine. The Tate's Luke White on the work: it is "simultaneously life and death incarnate in a way you don't quite grasp until you see it, suspended and silent, in its tank." The relevant move for HOMAGE is: *the vitrine is the artwork*. Not the shark. The framing apparatus is what the audience encounters first ([DailyArt Magazine — Hirst's Shark](https://www.dailyartmagazine.com/story-damien-hirst-shark/); [Wikipedia](https://en.wikipedia.org/wiki/The_Physical_Impossibility_of_Death_in_the_Mind_of_Someone_Living); [Tate — Luke White on Hirst's Shark](https://www.tate.org.uk/art/research-publications/the-sublime/luke-white-damien-hirsts-shark-nature-capitalism-and-the-sublime-r1136828)).
- **Mark Dion, *Oceanomania* (Musée Océanographique de Monaco, 2011)** — a curiosity cabinet of ocean specimens, taxidermy, glassware, archive material. Dion's whole practice is about how *the cabinet* (the vitrine, the archive, the shelf) turns its contents into a question: "how do we tell stories about the natural world?" ([Atlas Obscura — Dion's Marine Curiosity Cabinet](https://www.atlasobscura.com/articles/mark-dion-s-marine-curiosity-cabinet); [V&A — A Field Guide to Curiosity](https://www.vam.ac.uk/articles/a-field-guide-to-curiosity-a-mark-dion-project)).

These two references are about the *frame*, not the *fish*. They are the right precedent for a scrim-fishbowl that is the structuring device for the wards inside.

### 2.9 Cite — historical scrying / divination

Scrying — gazing into a reflective or translucent surface to perceive something on "the other side" — is the deep cultural ancestor of the fishbowl conceit. A scryer looks *into* a crystal ball, an obsidian mirror, a bowl of water, *not at* it. The bowl is the medium; what is seen is on the other side of the medium. This is pre-modern UX for "peering across a thickness," the same gesture the Nebulous Scrim is naming. We need not cite scrying directly in shaders, but it grounds the metaphor: a fishbowl of wards is a scrying surface for Hapax's interior life.

### 2.10 Cite — historical optics

- **Snell (1621), Ibn Sahl (984)** — refraction law. Establishes that crossing a boundary *bends* light measurably. ([Snell's Law — Britannica](https://www.britannica.com/science/Snells-law).)
- **Newton (Opticks, 1704)** — chromatic dispersion through a prism; first scientific explanation of the rainbow. Establishes that *different wavelengths bend differently*, the foundation of chromatic aberration. ([History of Geometric Optics — Univ. Texas](https://farside.ph.utexas.edu/teaching/316/lectures/node125.html); [Mathpages — Refraction Revisited](https://www.mathpages.com/home/kmath721/kmath721.htm).)
- **da Vinci, *Treatise on Painting*** — first systematic written explanation of aerial perspective: "distant objects are paler, less detailed, bluer, and hazier than nearer ones." ([Sfumato — Wikipedia](https://en.wikipedia.org/wiki/Sfumato); [da Vinci & Aerial Perspective — Art Secrets Studio](https://www.artsecretsstudio.com/post/leonardo-davinci-aerial-perspective-with-sfumato-softening-edges-by-getting-darker-farther-away).)

These three together — Snell, Newton, da Vinci — give us the entire physical and pictorial grammar we need: bend the light, split the colors, fade the distance.

---

## §3 Inventory of Depth Cues Available in 2D

Depth perception research distinguishes binocular cues (require two eyes / stereo disparity / convergence) from monocular cues (work in a single 2D image). For broadcast video, we have only monocular cues. The literature canonical list is well-summarized in the OEN *Sensation & Perception* textbook, Piter Pasma's depth-cues article, and the UC Irvine perception notes. ([Chapter 9: Depth Perception — OEN](https://manifold.open.umn.edu/read/sensation-perception/section/a10b03b5-47f4-459f-ba26-33c968d8eb01); [Visual Depth Cues — Piter Pasma](https://piterpasma.nl/articles/depth-cues); [UCI — Perceiving Depth and Size](https://ics.uci.edu/~majumder/vispercep/chap8notes.pdf); [PointOptics — Monocular Cues](https://www.pointoptics.com/monocular-cues/).)

The eight cues that apply to wards in a 2D composite, ranked by strength on a typical viewing distance for a 1080p TV or phone:

### 3.1 Occlusion (overlap) — strongest

If A is drawn over B, A is unambiguously in front of B. This is the most reliable depth cue in any rendering medium and the cheapest to honor. The compositor's `z_order` already does this. The scrim's depth bands inherit from this.

**For wards:** the depth-band sort order in `OverlayZones` IS the occlusion cue. Surface wards draw last (on top); near-surface beneath; beyond-scrim camera PiPs at the bottom. This is already correctly implemented. The fishbowl just *names* what's already happening.

### 3.2 Atmospheric perspective — second strongest at distance

Distant objects desaturate, blue-shift (or in our case, scrim-tint-shift), and lose contrast. This is the cue the Nebulous Scrim §4.3 already prescribes. For HOMAGE Phase A6 (BitchX active), the tint is cyan; for other packages, it is package-specific.

**Implementation:** per-ward color-grade pass biased toward the active package's scrim tint, strength scaled by ward Z. A ward at Z=0.0 has no tint shift; a ward at Z=1.0 has up to ~30% tint blend.

### 3.3 Defocus blur (depth of field) — strong at near range

Only the focal plane is sharp. Objects in front of and behind the focal plane have progressive Gaussian blur scaled by distance from focus.

**Implementation:** the cairo source has a `Pango.context_set_font_options()` and post-render Gaussian blur path. Add a `blur_radius` parameter scaled by `|ward.z - focus_plane.z|`. Approximate cost: a single small-kernel blur per ward is sub-millisecond at 1280×720 if pre-rendered to a cached surface (the existing `CairoSourceRunner` model already caches between cadences).

**Spider-Verse precedent:** the production used misaligned color channels (chromatic offset) as a depth-of-field substitute, because the comic-book register made true Gaussian blur read wrong. Their *ChromaShifter* tool repurposed motion-vector pipelines for depth offset. The lesson for HOMAGE: depth-of-field blur is a stylistic choice, not a physical requirement; pick the variant that matches the package register. ([CG Spectrum — Spider-Verse Animation](https://www.cgspectrum.com/blog/spider-man-into-the-spider-verse-how-they-got-that-mind-blowing-look); [80.lv — Spider-Verse 2D VFX](https://80.lv/articles/2d-vfx-behind-spot-from-spider-man-across-the-spider-verse); [AWN — Rewriting the Visual Rule Book](https://www.awn.com/animationworld/rewriting-visual-rule-book-spider-man-spider-verse).)

### 3.4 Motion parallax — strong if there is any motion

When the viewpoint moves OR scene elements move, near things move farther across the visual field per unit time than distant things. Even with a static virtual camera, *internal element motion* at differential rates reads as parallax. ([Motion Parallax — ScienceDirect](https://www.sciencedirect.com/topics/computer-science/motion-parallax); [Neural Basis of Motion Parallax — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4901450/); [What is Motion Parallax — Lens.com](https://www.lens.com/what-is/what-is-motion-parallax/).)

**Implementation:** every ward's intrinsic micro-motion (drift, jitter, breath, oscillation) is *amplitude-scaled by 1/(1+Z)* — near wards move more, deep wards move less. This is a single uniform multiply at compose time. It has no per-pixel cost.

### 3.5 Relative size — moderate, mostly already-occluded by ward sizing

If two ostensibly identical objects are at different sizes on screen, the smaller is perceived as more distant. For HOMAGE wards, the surface ward set is already designed at fixed sizes appropriate to legibility, not depth. We do not want to *shrink* deep wards (it makes them illegible); we *might* want to grow surface wards by ~5% as a hero-cue. Subtle.

**Implementation:** a small uniform scale on hero-ward when the structural director marks it as the focus. ~1.05× for hero, baseline for everyone else. Not a Z-conditioned scale — a Z-marker for "this ward is at the very front."

### 3.6 Texture gradient — present on the scrim itself

The scrim's gauze texture (from the `weave` / `noise` nodes) becomes the texture gradient: the weave is denser-and-finer at depth, coarser-and-bigger at the surface. This is already given by the scrim being composited over the deep wards (so its weave is between camera and them) and below the surface wards (so the surface wards are over it). No additional work needed; the layering does the cue automatically.

### 3.7 Shadow / lighting cues — costly, low payoff in our register

Cast shadows are a strong depth cue in 3D rendering but expensive and aesthetically off-register for HOMAGE (the BitchX/CRT/raster lineage is *flat*, not modeled). Skip.

There is a partial use case: a ward could carry a faint cast-shadow or *glow* on the scrim immediately behind it, indicating its slight stand-off from the fabric. This is the `bloom` node with asymmetric falloff, applied per ward at low intensity. Optional, register-bound.

### 3.8 Linear perspective — mostly inapplicable

Wards are not architectural; there are no vanishing-point lines to converge. Skip for ward composition. (Linear perspective applies to the studio camera feeds, but those are real-camera content; the lens already does this work.)

### 3.9 NOT available — stereoscopic disparity, convergence

Both require two viewpoints. Single-viewpoint broadcast cannot use these. Documented for completeness; do not pursue.

### 3.10 Per-cue priority for HOMAGE Scrim Pt. 4

| Cue | Cost | Strength at typical viewing | Already in stack | Recommend |
|---|---|---|---|---|
| Occlusion | 0 | strongest | yes (`z_order`) | already done |
| Atmospheric perspective | low | very strong | partial (`color` pass tints once) | extend to per-ward Z |
| Defocus blur | low-medium | strong | partial (cairo blur) | per-ward Z |
| Motion parallax | 0 | strong | no | wire per-ward velocity scaling |
| Texture gradient | 0 | weak (always present) | yes (scrim layering) | already done |
| Relative size | 0 | weak | no | hero-only flag |
| Shadow / glow | medium | weak in register | partial (`bloom`) | optional, hero-only |
| Linear perspective | n/a | n/a for wards | n/a | skip |
| Stereoscopic / convergence | n/a | n/a in 2D | n/a | skip |

**The three big movers** — atmospheric perspective, defocus blur, motion parallax — together carry maybe 80–90% of the perceived depth. All three are cheap. All three integrate cleanly with existing nodes. This is the implementation core.

---

## §4 Compositional Layering — Animation Industry References

Before shaders, the relevant lineage is the *compositional* one: how 2D animators have, for nearly a century, manufactured depth in flat media without geometry. The fishbowl has rich precedent.

### 4.1 The multiplane camera (Disney, 1937)

Disney's multiplane camera, designed by William Garity for the studio in early 1937 and debuted in the Silly Symphony *The Old Mill* (Academy Award, 1937 Animated Short), used **up to seven layers of artwork painted on glass**, photographed with a vertical camera at varying physical separations. The further from the camera, the slower the layer's lateral motion when the camera or scene panned. *Snow White and the Seven Dwarfs* (1937) was the first feature to use it; the Evil Queen's potion scene shows the surroundings spinning around her, with foreground glass moving at one rate and background glass at another. ([Multiplane Camera — Wikipedia](https://en.wikipedia.org/wiki/Multiplane_camera); [Walt Disney + the Multiplane Camera — NIHF](https://www.invent.org/inductees/walt-disney); [PetaPixel — How Disney's Multiplane Achieved Depth](https://petapixel.com/2025/04/04/how-disneys-multiplane-camera-achieved-the-illusion-of-depth/); [Collider — The Technology that Made Disney Animated Classics Magical](https://collider.com/disney-snow-white-and-the-seven-dwarfs-multiplane-camera/).)

**Direct lesson:** physical separation of layers + differential motion = depth. The scrim's depth bands ARE the multiplane glass plates. The ward's per-Z parallax IS the multiplane camera move.

### 4.2 Studio Ghibli "book layout" (Takahata, Miyazaki)

The 1,300+ Ghibli layouts (compiled in *Studio Ghibli Layout Designs: Understanding the Secrets of Takahata-Miyazaki Animation*, exhibited at Hong Kong Heritage Museum 2014, Tokyo 2008) document the studio's exhaustive use of one-, two-, three-point, isometric, and fish-eye perspectives, plus distortion-in-water studies, as the spatial scaffold for every shot. Crucially: most Ghibli depth is *already on the page*; the multiplane camera is doing relatively little. The depth is *drawn*. ([Goodreads — Studio Ghibli Layout Designs](https://www.goodreads.com/book/show/17187165-studio-ghibli-layout-designs); [Halcyon Realms — Layout Designs Review](https://halcyonrealms.com/anime/studio-ghibli-layout-designs-exhibition-art-book-review/); [Through the Looking Glass — HK Heritage Museum review](https://rachttlg.com/2014/07/09/studio-ghibli-hong-kong-heritage-museum/).)

**Direct lesson:** a static composite can read as deep if the *internal compositional logic* of each ward acknowledges depth. The Cairo render of a deep-band ward should already carry "deepness" in its line weight, color saturation, and detail density. The scrim cues *enhance* what the ward already declares.

### 4.3 Spider-Verse 2.5D (Sony Imageworks, 2018)

*Spider-Man: Into the Spider-Verse* used overlaid 2D drawings on top of 3D models — "2.5D" — to get the depth of 3D with the artistic control of 2D. Several techniques relevant to fishbowl-depth:

- **ChromaShifter for depth-of-field substitution.** Misaligned RGB channels mimicking comic-book misregistration replaced the lens-blur DoF, both because it matched the comic register *and* because pushing the chromatic offset to extreme values gave a unique motion-trail look on rapidly moving objects. ([CG Spectrum on Spider-Verse](https://www.cgspectrum.com/blog/spider-man-into-the-spider-verse-how-they-got-that-mind-blowing-look); [80.lv — 2D VFX in Spider-Verse](https://80.lv/articles/2d-vfx-behind-spot-from-spider-man-across-the-spider-verse).)
- **Animation on ones AND twos within a single shot** — Miles animated on twos (12fps) for inexperience; Peter on ones (24fps) for smoothness. The two characters in the same scene exist at different *temporal granularities*. ([Wikipedia — Spider-Man: Into the Spider-Verse](https://en.wikipedia.org/wiki/Spider-Man:_Into_the_Spider-Verse).)
- **Procedurally-generated halftones and hatching done in compositing**, not in rendering. The compositor (Nuke at Imageworks) carried significant depth-shading work. ([Imageworks — Spider-Man Spider-Verse production](https://www.imageworks.com/our-craft/feature-animation/movies/spider-man-spider-verse); [Foundry — Across the Spider-Verse with Nuke, Mari & Katana](https://www.foundry.com/insights/film-tv/across-the-spider-verse-nuke-mari-katana).)

**Direct lessons for HOMAGE:**
- *Animate at different cadences per depth.* Surface wards refresh every frame; deep wards may refresh every other frame or every third. The eye reads "frame-quantization" as temporal distance.
- *Use chromatic offset as depth proxy.* Already in stack (`chromatic_aberration` node). Tie its strength to ward Z.
- *Compositor does the depth work, not the renderer.* HOMAGE's `studio_compositor` is the right place; do not push depth into the cairo source generators themselves.

### 4.4 Klaus (Sergio Pablos / SPA Studios, 2019)

*Klaus* (Netflix, dir. Sergio Pablos) is the modern proof that 2D can read as volumetric. The pipeline used a custom in-house tool — *Klaus Light and Shadow* — to derive light-and-shadow tracking from drawn lines (vector AND bitmap), then layered light into four channels: **ambient, direct + shadow, bounce, rim**. Toon Boom Harmony was the foundation. ([before & afters — What Made Klaus 2D Animation Look 3D](https://beforesandafters.com/2019/11/14/heres-what-made-the-2d-animation-in-klaus-look-3d/); [AWN — How Klaus Combines CG Lighting with 2D](https://www.awn.com/animationworld/how-klaus-uniquely-combines-cg-lighting-techniques-traditional-2d-animation); [Toon Boom — Sergio Pablos on Klaus](https://www.toonboom.com/sergio-pablos-klaus); [Deadline — Pablos Elevates 2D with Klaus](https://deadline.com/2019/12/klaus-director-sergio-pablos-netflix-animation-interview-1202807202/); [SIGGRAPH Blog — Behind the Magic of Klaus](https://blog.siggraph.org/2019/12/behind-the-magic-of-netflixs-klaus.html/).)

**Direct lesson:** four light channels per element gives volumetric reading. For HOMAGE wards, this maps cleanly onto: (1) scrim ambient tint, (2) ward intrinsic color, (3) *bounce* — light from neighboring wards (we don't compute this; it's a constant fudge factor), and (4) *rim* — a slight backlighting glow indicating the ward sits in front of the scrim. The rim cue is the cheapest and the most volumetric per pixel.

### 4.5 Wolfwalkers (Cartoon Saloon, 2020)

*Wolfwalkers* (dir. Tomm Moore, Ross Stewart) uses **two contrasting 2D styles in the same film** — woodblock for the town of Kilkenny, sketchy expressive line work for the forest — as a depth/world-state cue. As Robyn identifies more with the wolfwalkers, her own design transitions from woodblock to forest-sketch. The "Wolfvision" sequences flatten to a limited palette with heightened expressive forms. ([Animation Magazine — Wolfwalkers Inspirations](https://www.animationmagazine.net/2020/06/annecy-tomm-moore-reveals-inspirations-behind-cartoon-saloons-wolfwalkers/); [Animation Obsessive — Inside the Look of Wolfwalkers](https://animationobsessive.substack.com/p/inside-the-look-of-wolfwalkers-with); [Cartoon Saloon — Wolfwalkers](https://www.cartoonsaloon.ie/wolfwalkers/).)

**Direct lesson:** *style itself* can be a depth/state cue. For HOMAGE, this is the inverse of the Wolfwalkers move: wards on the same depth band should share a style; cross-band differences should be felt. Surface wards are sharp + full-chroma + crisp typography; near-surface wards are slightly washed; beyond-scrim camera PiPs are blurred + tinted + lower-contrast. The audience reads "this set of wards is a category" partly via style continuity.

### 4.6 After Effects 3D layer compositing

Modern compositing software (After Effects, Nuke, Fusion) has had "3D layers" for two decades — flat 2D layers placed at Z positions in a 3D scene, with a virtual camera that produces real parallax + perspective. This is the same concept the multiplane camera invented physically; compositors now do it in software, at a per-element grain. The Spider-Verse and Klaus pipelines both rely on this as their compositor substrate.

**For HOMAGE:** the Cairo + GStreamer pipeline does NOT have native 3D-layer compositing. We're not adding a virtual camera. But the *concept* — each layer carries Z, the compositor honors Z — is exactly the WardSpatialState model proposed in §12.

### 4.7 Game engine UI sorting (Unity sortingLayer, Unreal Slate)

Game UI systems implement strict 2D layering with named depth bands and per-element Z-offsets. Unity's `sortingLayer` + `orderInLayer` and Unreal's Slate ZOrder are the canonical implementations. The lesson is taxonomic: have a small number of *named* depth bands ("Background", "Midground", "Foreground", "Overlay") rather than a continuous Z range, because human reasoning about layering is categorical. ([Unity sortingLayer documentation, Unreal Slate ZOrder, Game Programming Patterns chapter on update method ordering — for the categorical-layer pattern; not citing inline since the pattern is the lesson.])

**For HOMAGE:** the four scrim depth bands from Nebulous Scrim §6 (surface / near-surface / hero-presence / beyond-scrim) ARE the sorting layers. Continuous Z within a band; categorical between bands. This is well-formed.

### 4.8 The synthesis

The animation industry has converged on a small set of moves over 87 years:

1. **Layer separation with differential motion** (multiplane camera, 1937; AE 3D layers, 2000s).
2. **Drawn / authored depth that the lighting then enhances** (Ghibli, 1980s; Klaus, 2019).
3. **Stylized substitutes for physical depth-of-field** (Spider-Verse chromatic offset, 2018).
4. **Style-as-depth cue** (Wolfwalkers, 2020).
5. **Categorical sorting bands** (game UI engines, ongoing).

All five are available to HOMAGE. None require new shaders. Most require depth-tagging + a single compositor-pass enhancement.

---

## §5 Refraction Simulation Techniques

Real refraction is expensive (raytraced caustics, full Snell-law sampling). Real-time approximations cost almost nothing. The fishbowl needs *just enough* refraction to feel like glass + water; not photorealism.

### 5.1 Normal-map displacement (cheapest)

Sample a scrolling noise map; treat its values as a 2D normal direction; offset the UV by `noise_normal * strength` when sampling the underlying texture. The *displacement_map* node already does this. Inigo Quilez's *Simple Water* article lays out the canonical version: distort the surface normal with the normal map as a first step, then offset the sampling point based on the angle between surface normal and eye direction. ([iquilezles.org — Simple Water](https://iquilezles.org/articles/simplewater/); [iquilezles.org — Articles index](https://iquilezles.org/articles/); [Stevan Dedovic — Refraction Shader](https://www.dedovic.com/writings/warping-refraction-shader).)

**For HOMAGE:** the existing `drift` node (UV displacement on slow noise) is structurally this. Re-purpose it as the scrim's "looking through gauze and water" refraction. The strength uniform is the obvious knob: low (~0.02) for "slight refraction"; higher (~0.08) for "actively looking through water."

### 5.2 UV distortion in fragment shader (cheap, very effective for glass)

A fragment shader sampling the texture behind the scrim can apply an arbitrary 2D distortion (sine wobble, noise, radial bulge) to the sample coordinate. This is the universal "behind glass" trick. The `displacement_map` node + a noise input give exactly this; the output reads as "rippled glass surface" without computing any optics. ([Maxime Heckel — Refraction, Dispersion, and Other Shader Light Effects](https://blog.maximeheckel.com/posts/refraction-dispersion-and-other-shader-light-effects/); [Allan Bishop — Interactive Water in Unity](https://www.allanbishop.com/2022/08/17/interactive-water-simulation-in-unity/); [DEV.to — WebGL Liquid Glass Library](https://dev.to/maxgeris/webgl-based-javascript-library-for-pixel-perfect-ios-liquid-glass-effect-with-refractions-and-3p8m).)

**For HOMAGE:** apply at the *scrim boundary* between camera-PiP layers and surface wards. The behind-scrim camera content gets sampled through a noisy UV offset; the surface wards do not. This makes the wards feel *on the glass* and the cameras feel *behind it*.

### 5.3 Chromatic aberration as refraction proxy

Sample R, G, B at slightly different offsets — Newton's wavelength-dependent refraction in software. Existing `chromatic_aberration` node. ([3D Game Shaders for Beginners — Chromatic Aberration](https://lettier.github.io/3d-game-shaders-for-beginners/chromatic-aberration.html); [Harry Alisavakis — Chromatic Aberration](https://halisavakis.com/my-take-on-shaders-chromatic-aberration-introduction-to-image-effects-part-iv/); [GM Shaders — Chromatic Aberration](https://mini.gmshaders.com/p/gm-shaders-mini-chromatic-aberration); [ReShade — YACA](https://reshade.me/forum/shader-presentation/1133-yaca-yet-another-chromatic-aberration).)

**For HOMAGE:** the Nebulous Scrim §3 tech inventory tags this as a "+ register" move at low strength. For fishbowl: *only* at the edges of the frame (radial mask + chromatic aberration), simulating where the bowl curves and disperses light most. Costs ~0.1ms.

### 5.4 Caustics overlay

The web of bright lines on a pool floor from light passing through a wavy water surface. NVIDIA's *GPU Gems* Chapter 2 (Carlos Frias) is the canonical real-time technique: trace rays from light through a refractive surface, accumulate where they land. Modern variants use cascaded caustic maps for performance. ([NVIDIA Developer — Rendering Water Caustics, GPU Gems Ch. 2](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-2-rendering-water-caustics); [Martin Renou — Real-Time Water Caustics](https://medium.com/@martinRenou/real-time-rendering-of-water-caustics-59cda1d74aa); [Evan Wallace — Realtime Caustics in WebGL](https://medium.com/@evanwallace/rendering-realtime-caustics-in-webgl-2a99a29a0b2c); [Alexander Ameye — Realtime Caustics](https://ameye.dev/notes/realtime-caustics/).)

**For HOMAGE:** **register-questionable**. Caustics are a visually loud "look I'm rendering water" cue. They risk pushing the scrim from "fishbowl" to "swimming pool documentary." Recommend skipping in v1; consider as an *interlude / programme-scoped* node only.

### 5.5 Heat-haze / atmospheric refraction

Slow, low-amplitude UV displacement *only on a hero element*. Reads as "the bowl is warming up" or "this thing is special." The existing `displacement_map` masked by a hero bounding box gives this; Nebulous Scrim §4.7 already prescribes it. ([Quilez — Simple Water](https://iquilezles.org/articles/simplewater/) covers the displacement primitive.)

**For HOMAGE:** keep as the "hero attention" cue. Couple it with a slight `bloom` falloff for the heat-shimmer signature.

### 5.6 Procedural noise for the underlying displacement

The displacement map needs a source. The Book of Shaders Ch. 11–13 (Patricio Gonzalez Vivo) is the canonical primer on noise primitives — value noise, gradient noise, Worley/cellular noise (Steven Worley, *A Cellular Texture Basis Function*, 1996), fractal Brownian motion (fBm) for landscape-like detail at multiple frequencies. ([Book of Shaders — Noise](https://thebookofshaders.com/11/); [More Noise](https://thebookofshaders.com/12/); [Fractal Brownian Motion](https://thebookofshaders.com/13/); [Procedural Textures in GLSL — DiVA](https://www.diva-portal.org/smash/get/diva2:618262/FULLTEXT02.pdf).)

**For HOMAGE:** the existing `noise` node and `noise_overlay` already produce these. fBm at 3–4 octaves is the right basis for the displacement map driving `drift`. Cellular/Worley noise at low density is the right basis for the "smudge" / "aquarium-glass" Nebulous Scrim technique #8.

### 5.7 The synthesis

For HOMAGE Pt. 4 fishbowl refraction:

- **Always-on, cheap:** `drift` (UV displacement from fBm noise) at low strength. This IS the bowl's water.
- **Edge-only, cheap:** `chromatic_aberration` masked by radial vignette. This IS the bowl's curvature.
- **Hero-only, cheap:** localized `displacement_map` + `bloom` halo around the focused ward. This IS the heat-haze attention signal.
- **Skip:** caustics (register loud), full-water normal-map sampling (we have no light source to refract).

Total cost: ≤0.5ms additional GPU per frame. Comfortably inside the Nebulous Scrim §9 1.5ms budget.

---

## §6 Liquid-Medium Motion Grammar

The fishbowl is not visually loud. It is *kinematically* distinct. The wards' motion is the strongest fishbowl cue, and it costs nothing per pixel.

### 6.1 Inertia

A liquid-suspended object has measurable mass-against-medium-viscosity. Motion does not snap; it ramps and decays. Translated to ward animation: *no instant transitions*. Every position change is interpolated with an ease-in-out curve that has a longer tail than typical UI animation conventions.

**Concrete:** standard UI animation runs ~150–300ms with cubic ease-out. Fishbowl wards run ~400–700ms with critically-damped spring (ζ ≈ 0.7). The spring overshoots slightly, then settles — the "wobble after a poke" signature.

### 6.2 Damping

Oscillations decay exponentially with time. A ward that wobbles when it appears should reach <5% of initial amplitude within ~1.5s. The damping coefficient is the medium's viscosity made numerical.

**Concrete:** `velocity *= 0.92` per frame at 30fps gives ~1.5s decay-to-5%. Apply in the ward's animation update.

### 6.3 Buoyancy (ambient drift)

In the absence of explicit motion, wards drift slightly. Up-and-leftward (for western reading-eye baseline) at <1px/frame. This is the "alive" signal — the bowl is never dead even when nothing is happening.

**Concrete:** add a per-ward 2D drift vector sampled from very-low-frequency Perlin noise per Z-band. Surface wards drift least; deep wards drift most (currents are stronger at depth).

### 6.4 Currents

A global ambient flow that all wards inherit, with magnitude scaled by Z. The current is itself slowly time-evolving — its direction shifts over ~30s cycles. This gives the bowl a *mood*: a leftward current for 30s, then rightward, then a slow turn.

**Concrete:** a single `Current` Pydantic struct in shared state, written by the structural director or the reactive engine, read by every ward's animation tick. Direction changes over 20–40s windows.

### 6.5 Wake

A moving ward leaves a brief temporal disturbance behind it that other wards can react to. This is where the existing `feedback` node (ping-pong FBO temporal accumulation, Bachelard Amendment 2) earns its keep: the moving ward's bright pixels persist briefly in the feedback buffer; other wards rendered shortly after sample that buffer to wobble or tint slightly.

**Concrete:** every ward has a `wake_strength` that increments on motion. The `feedback` pass's `fade` parameter is reduced (longer trail) where wake_strength is high.

### 6.6 Boundary interaction

A ward hitting the edge of the bowl (the frame edge, or a parent overlay zone boundary) bounces *softly*. The bounce is critically damped: not elastic (no rubber-ball recoil), not absorbed (no thud). The ward arrives at the boundary, compresses slightly along its motion vector for ~150ms, then settles.

**Concrete:** boundary detection in the ward animation tick; on boundary, decompose velocity into `v_normal` and `v_tangent`; set `v_normal *= -0.3` (lossy bounce); apply a brief 150ms scale modulation along the motion axis (~1.05× → 0.97× → 1.0×) for the "compression" feel.

### 6.7 Cluster behavior — Reynolds boids, but for wards

Craig Reynolds' 1987 SIGGRAPH paper *Flocks, Herds, and Schools: A Distributed Behavioral Model* defines three steering behaviors per agent: **separation** (avoid crowding nearby boids), **alignment** (steer toward average heading of nearby boids), **cohesion** (move toward average position of nearby boids). The first animated use was *Stanley and Stella in: Breaking the Ice* (1987); first feature use, *Batman Returns* (1992). ([Reynolds 1987 SIGGRAPH paper](https://www.red3d.com/cwr/papers/1987/SIGGRAPH87.pdf); [Reynolds — Flocks, Herds, Schools](https://www.red3d.com/cwr/papers/1987/boids.html); [Boids — Wikipedia](https://en.wikipedia.org/wiki/Boids); [Befores & Afters — A History of CG Bird Flocking](https://beforesandafters.com/2022/04/07/a-history-of-cg-bird-flocking/).)

**For HOMAGE:** wards within a depth band exhibit *weak* boid behavior — they prefer not to overlap (separation), they share a slow drift heading (alignment), they cluster loosely toward their assigned overlay zone (cohesion). The strengths are very low: this is for *coherence* of the depth band, not for visible flocking.

**HARD INVARIANT (HARDM lineage):** apply boids to **wards-as-points-in-space**, not to wards-as-creatures. No "schooling" gestures. No directional V-formations. No ward should ever read as "swimming in a school." The boid math is doing local-neighborhood layout adjustment, nothing more. If a tester ever describes wards as "schooling" or "swimming together," the boid weights are too high — back them off until the behavior is invisible-but-felt.

### 6.8 The synthesis

Liquid motion is *temporal*, not visual. It costs nothing per pixel. It is implemented as per-ward animation parameters (spring-damper coefficients, drift vectors, current inheritance, wake strength, boundary bounce) tuned to "fishbowl" defaults. The visible behavior is a *register* — the bowl FEELS slow because the timings are deliberately past UI-typical.

Tuning sheet for v1:

| Parameter | Surface ward (Z=0.0) | Deep ward (Z=1.0) |
|---|---|---|
| Transition duration | 250ms | 600ms |
| Damping coefficient | 0.88 | 0.94 |
| Ambient drift magnitude | <0.2px/frame | <1.0px/frame |
| Current inheritance | 0.2× | 1.0× |
| Wake strength on motion | 0.3 | 0.8 |
| Boundary bounce loss | 0.5 (less compression) | 0.3 (more compression) |
| Boid weights (sep/align/coh) | 0.05 / 0.02 / 0.03 | 0.08 / 0.05 / 0.05 |

---

## §7 Lighting + Atmospheric Perspective

Already prescribed by Nebulous Scrim §4.3, §4.4. This section makes it programmable per-Z.

### 7.1 Distance fog tinted by package palette

Each HOMAGE package declares its scrim tint (BitchX → cyan; other packages TBD per their HOMAGE-spec entries). The scrim's color pass already tints the substrate; for fishbowl depth, *the same tint is applied to each ward proportional to its Z*.

**Concrete:** at composite time, for each ward, `ward.color = lerp(ward.color, package.scrim_tint, ward.z * 0.3)`. The 0.3 cap prevents deep wards from fully dissolving into the scrim (legibility constraint, Nebulous Scrim §9.2).

### 7.2 Per-ward color cast

Beyond the simple LERP toward scrim tint: deep wards lose *contrast* (gamma flatten), lose *saturation* (HSV S-channel reduce), and gain *fog* (additive scrim tint at low alpha). The combination is sfumato — Leonardo's "without lines or borders, in the manner of smoke" — applied at the scale of an individual ward. ([Sfumato — Wikipedia](https://en.wikipedia.org/wiki/Sfumato); [Russell Collection — Aerial Perspective](https://russell-collection.com/what-is-aerial-perspective-in-painting/); [DanteSisofo — Renaissance Art Techniques](https://dantesisofo.com/renaissance-art-techniques-mastering-perspective-light-and-form/); [Jerry Poon — Sfumato](https://www.jerrypoon.com/post/sfumato-leonardo-da-vinci-painting-technique).)

**Concrete:** a tiny `colorgrade` configuration per ward, conditioned on Z:

```
saturation_scale = 1.0 - (z * 0.3)     # 30% desaturation at deepest
contrast_scale   = 1.0 - (z * 0.2)     # 20% contrast loss at deepest
fog_alpha        = z * 0.25             # 25% fog at deepest
fog_color        = package.scrim_tint
```

Existing `colorgrade` node accepts these parameters today. Per-ward instantiation is the new piece.

### 7.3 Edge softening at depth

Deep wards have a sub-pixel edge softening — the high-frequency content of their text/lines damps with Z. Implementation: a 1-pixel Gaussian blur applied only on the deep band, only on the edges. Cheap, very effective.

**Concrete:** post-render, after the ward's cairo surface is generated, apply a Z-conditioned Gaussian. For Z=0.0: no blur. For Z=1.0: 1.5px Gaussian. The cairo cached surface model already supports this; the blur runs once at re-render time, not per frame.

### 7.4 Storaro on atmospheric substrate

Vittorio Storaro on *Apocalypse Now* (1979): when parachute flares failed in humid air, Storaro and the crew leaned into the dark areas, using arc lights and photofloods as highlights — turning the *absence* of atmospheric light into composition. Smoke as substrate, not effect. ([ASC — Apocalypse Now: A Clash of Titans](https://theasc.com/articles/flashback-apocalypse-now); [Nebulous Scrim doc §2.2 cites Storaro directly].)

**Direct lesson:** the scrim tint isn't *applied to* the wards; the wards *exist in* the scrim's atmospheric medium. Plan around the tint as a constant; the wards' colors are a *deviation from* the tint, brighter and more saturated near the surface, settling toward the tint at depth.

### 7.5 Programme-tunable strength

The seven scrim profiles named in Nebulous Scrim §7 (listening, hothouse, vinyl-showcase, wind-down, research, interlude, ritual) each declare their own atmospheric-perspective strength. The hothouse profile keeps deep wards at near-full saturation (active, alive); the wind-down profile pushes them deep into the tint (dissolving into substrate). Encode as `scrim_profile.atmospheric_strength` ∈ [0.0, 1.0]; multiply against the per-Z bias.

### 7.6 The HARDM-rim trick

For Hapax's avatar wards (`token_pole`, `hardm_dot_matrix`) at Z=0.5 (hero-presence band, straddling the scrim): apply Klaus's *rim light* technique. A faint glow around the avatar's silhouette, color-shifted toward the scrim's complementary hue, signals "this object stands in front of the fabric." Cost: a single small-kernel bloom with asymmetric falloff. ([Klaus four-channel lighting — AWN](https://www.awn.com/animationworld/how-klaus-uniquely-combines-cg-lighting-techniques-traditional-2d-animation).)

This is the only place lighting "drama" is appropriate. Everywhere else, atmospheric perspective is enough.

---

## §8 Time-Distortion in Liquid Space

Time is a depth cue. Deep things move slower, refresh slower, persist longer. This is independent of the spatial cues and adds a separate channel.

### 8.1 Slow motion as depth cue

Surface wards animate at 30fps; near-surface at 24fps; hero-presence at 30fps (they straddle and read crisp); beyond-scrim at 15fps. The lower the Z, the lower the temporal sample rate. ([Spider-Verse used this: Miles on twos, Peter on ones, in the same shot — Wikipedia](https://en.wikipedia.org/wiki/Spider-Man:_Into_the_Spider-Verse); [80.lv — Spider-Verse 2D VFX](https://80.lv/articles/2d-vfx-behind-spot-from-spider-man-across-the-spider-verse).)

The cost saving (some wards rendering less often) is a side benefit; the primary purpose is *temporal depth*.

**Concrete:** `CairoSourceRunner` already has a `target_fps` parameter per-source. Set it per ward depth band: surface=30, near-surface=24, hero=30, beyond-scrim=15. No new code needed.

### 8.2 Frame-blending / motion blur on far wards

Far wards' motion is slightly blurred. Implementation: render the ward to a small offscreen buffer; on motion, blend with the prior frame at 30% alpha. This is cheap (per-ward, only on motion) and reads as "deep things are smeary because the medium is thick."

This is the same intuition as Klaus's bounce-light channel applied temporally: a deep ward's previous-frame ghost is its "bounce" through the medium.

### 8.3 Inkblot dispersal on entry

When a new ward appears at depth, its appearance is a brief expansion-then-settle: the ward's bounding box grows to ~120% over 200ms, then contracts to 100% over 400ms (critically damped). The visual is "a drop of ink hitting water and dispersing." Cost: per-ward scale modulation on entry; trivial.

For surface wards: skip the inkblot. They appear instantly. This itself is a depth cue (instant = on-the-surface; dispersing = deep-in-the-medium).

### 8.4 Echo / phantom wards

A delayed copy of a recent ward state, drifting behind the live ward at lower opacity, makes the liquid feel dragged-through. Implementation: ring-buffer of (position, time) per ward; render a ghost at `t - 250ms` with alpha 0.2 if the ward has moved. Couple alpha to motion magnitude (only on actively moving wards).

This is the `echo` shader node already in stack, applied per-ward.

### 8.5 The synthesis

Time-distortion is a *parallel channel* to spatial depth. A ward at high Z gets:

- lower frame rate
- motion-blur ghost on movement
- inkblot dispersal on entry
- phantom echo on motion
- (and all the spatial cues from §3 / §7)

These together make a deep ward *feel slow*. Slowness is the bowl's most precise signature.

---

## §9 Hapax Shader Integration Paths

Working through how each cue lands in the existing Reverie + effect-graph stack.

### 9.1 Reverie 8-pass, what each pass already does

From `agents/reverie/_graph_builder.py` and `agents/reverie/_uniforms.py`:

| Pass | Order | Node | Purpose | Per-ward Z extension |
|---|---|---|---|---|
| 0 | noise | base noise generation | source for downstream | n/a (substrate) |
| 1 | rd | reaction-diffusion (temporal) | textural pattern evolution | n/a (substrate) |
| 2 | color | color grading | substrate tint | **per-ward extension via colorgrade params** |
| 3 | drift | UV displacement | gauzy fog motion | **add per-ward Z amplitude** |
| 4 | breath | breathing/oscillation (temporal) | "alive" pulse | **add per-Z phase offset** |
| 5 | feedback | ping-pong FBO accum (temporal) | trails / wake | **tie fade to per-ward Z + wake_strength** |
| 6 | content_layer | content composite | wards composite into substrate | **honor ward.z metadata for sort + tint** |
| 7 | postprocess | final tone / chroma / vignette | atmospheric tint, vignette | **chromatic aberration radial mask** |

### 9.2 The three passes most-modified by fishbowl

**`drift` (pass 3, displacement)** — already a UV-displacement on slow noise. Add a uniform `per_ward_z_amplitude` that the compositor sets per ward. Deep wards get larger, slower wobble (heat-haze + liquid-medium inertia). Surface wards get none. Cost: trivial; one extra uniform.

**`breath` (pass 4, temporal breathing)** — already pulses uniformly across the surface. Add a uniform `per_ward_phase_offset` so deep wards breathe slightly out of phase with surface wards. The bowl's standing-wave modes are not synchronized end-to-end. Cost: trivial.

**`feedback` (pass 5, ping-pong FBO)** — already the temporal-trail engine. Add per-ward `wake_strength` input; the `feedback.fade` parameter is reduced (longer trail) where the ward has moved recently. Per-ward implementation requires the feedback pass to either accept a per-region fade mask (medium effort) or for the compositor to drive a single global fade based on the *most-active* deep ward (cheap, lossy approximation). Recommend the cheap approximation for v1.

### 9.3 Other passes touched

**`content_layer` (pass 6)** — the ward composite. This is where ward Z is read and used for: (a) sort order (already done via `z_order`), (b) per-ward color-grade with Z-conditioned saturation/contrast/fog, (c) per-ward Gaussian blur radius. New work: extend `content_layer` to honor `ward.z` metadata as a per-element parameter, not just a sort key.

**`postprocess` (pass 7)** — the final tone pass. Add a radial-masked chromatic aberration (only at frame edges) to simulate bowl curvature. The existing `chromatic_aberration` node + a vignette mask gives this. Cost: ~0.1ms.

### 9.4 Cairo-side per-ward Z-aware rendering

The cairo source layer is where most of the per-ward depth conditioning actually happens, because the cairo pass owns each ward's surface generation. New work in `agents/studio_compositor/cairo_source.py::CairoSourceRunner`:

- Accept `WardSpatialState` from the ward's metadata.
- Apply per-Z Gaussian blur radius post-cairo-render (one-time per cache regeneration).
- Apply per-Z color-grade (saturation, contrast, fog) at composite time.
- Drive per-Z animation parameters (spring damping, drift, current, wake) into the ward's animation tick.

This is a localized change in `cairo_source.py` plus a new field on the Ward model. No new shader nodes needed.

### 9.5 Cost budget

Pulling together expected per-frame costs at 1280×720, layered onto Nebulous Scrim's 1.5ms budget:

| Cue | Where | Cost |
|---|---|---|
| Per-ward Z-conditioned tint/contrast/fog | content_layer | ~0.1ms |
| Per-ward Z-conditioned Gaussian blur | cairo cache | amortized; ~0ms per frame |
| Per-ward Z-amplitude drift modulation | drift pass uniform | ~0ms (uniform set only) |
| Per-Z breath phase offset | breath pass uniform | ~0ms |
| Per-ward wake feedback fade | feedback pass | already in budget |
| Radial chromatic aberration | postprocess | ~0.1ms |
| Spring-damper / drift / current / boids / wake | CPU per-ward animation | ~0.05ms total CPU |
| Inkblot / echo phantom / motion blur | per-ward, on event | amortized |
| **Total additional** | | **~0.2ms GPU + ~0.05ms CPU** |

Comfortably inside Nebulous Scrim §9 budget. Most of the depth illusion is *cheap* because it's per-ward parameter conditioning, not per-pixel work.

### 9.6 No new shader nodes for v1

This is the strongest implementation argument: every fishbowl cue lands on an existing Reverie pass or an existing shader node:

- `drift` ← liquid medium motion, heat haze
- `breath` ← standing-wave depth offset
- `feedback` ← wake / temporal trails
- `displacement_map` ← refraction (already an `effect_graph` node)
- `chromatic_aberration` ← bowl-curvature dispersion (already an `effect_graph` node)
- `colorgrade` ← per-ward atmospheric perspective (already an `effect_graph` node)
- `bloom` ← Hapax avatar rim glow (already an `effect_graph` node)
- `echo` ← phantom drift trails (already an `effect_graph` node)

Caustics and the dedicated water-normal-map sampler are *deferred*. v1 is a parameter-extension and compositor-pass change, not a shader-set expansion.

---

## §10 Inter-Dimensional Aesthetic References

The operator framing is "inter-dimensional," not "underwater." The bowl is a *liminal space* — a perceived adjacent dimension visible through the scrim. Five cinematic precedents that ground this register without resorting to literal aquaria.

### 10.1 Twin Peaks: The Return — Lodge sequences (Lynch, 2017)

The Red Room and the White Lodge are spatial impossibilities staged through repeating chevron floors, undulating red curtains, color-isolated palette (pure red, off-white, dark-brown), reverse-played dialogue, and overhead shots of cascading water that *parts and rejoins*. The cinematography establishes a stable visual grammar for the Lodge that signals "this is not normal space" without making the geometry impossible. ([Idyllopus Press — Analysis of Twin Peaks: The Return Pt. 1](https://idyllopuspress.com/idyllopus/film/tpr1.htm); [Far Out Magazine — The Strange Dialogue Effect](https://faroutmagazine.co.uk/strange-dialogue-twin-peaks-red-room/); [Twin Peaks Gazette — Iconography of the Red Room](https://twinpeaksgazette.com/2017/07/22/iconography-of-the-red-room/); [25 Years Later — Black Lodge, White Lodge](https://25yearslatersite.com/2017/09/26/black-lodge-white-lodge-time-for-a-rethink/); [Slashfilm — Red Room's Practical Purpose](https://www.slashfilm.com/836610/twin-peaks-red-room-was-created-to-serve-a-surprisingly-practical-purpose/).)

**For HOMAGE:** the Lodge's lesson is *consistency-of-strangeness*. The fishbowl-ness should be a *grammar* every ward shares, not a per-ward gimmick. The audience reads "this is the bowl space" once, then never has to re-read it.

### 10.2 2001: A Space Odyssey — the Stargate (Kubrick / Trumbull, 1968)

Douglas Trumbull's slit-scan apparatus produced the Stargate's infinite-corridor-of-lights by photographing high-contrast art (optical paintings, architectural drawings, electrical-circuit prints) through a moving slit, with each frame a 45-second double exposure on 30+ feet of camera track. The technique lifted from 1800s still-photography slit-scan; six months of production. ([Doug Trumbull on 2001 SFX — Media+Art+Innovation](https://mediartinnovation.com/2014/08/05/doug-trumbull-special-effects-on-2001-a-space-odyssey/); [Indie Film Hustle — Kubrick Slit Scan](https://indiefilmhustle.com/stanley-kubrick-slit-scan-2001/); [Film School Rejects — Stargate Sequence](https://filmschoolrejects.com/2001-a-space-odyssey-stargate/); [Air & Space — Making of the Stargate](https://airandspace.si.edu/stories/editorial/making-2001s-star-gate-sequence); [Neil Oseman — Slit-Scan and the Legacy of Trumbull](https://neiloseman.com/slit-scan-and-the-legacy-of-douglas-trumbull/); [BFI — Trumbull Obit](https://www.bfi.org.uk/news/douglas-trumbull-1942-2022); [Red Shark — Trumbull and Slit-Scan](https://www.redsharknews.com/douglas-trumbull-and-how-slit-scan-changed-sfx).)

**For HOMAGE:** the Stargate's lesson is *time-smeared layers as inter-dimensional grammar*. The existing `slitscan` node in `agents/shaders/nodes/slitscan.wgsl` is exactly this primitive. For *moments* — programme transitions, scrim.pierce, ritual openings — slitscan can be applied to deep-band content as a brief "passing-through" gesture. Not always-on; episodic.

### 10.3 Annihilation — the Shimmer (Garland, 2018)

DP Rob Hardy and the VFX team built the Shimmer's prismatic boundary using practical materials: prisms, crystal balls, weird old lenses, theatrical lights firing through glass. The deliberate visual choice was "petrol slick + paint job giving rainbow at glancing angles." The colorist Jim Passon added diffusion to most shots, giving "a feeling of condensation in the air." Garland's design intent: a continuous arc tracking Lena's emotional state, no hard divide between real-world and Area X. ([ASC — Annihilation: Expedition Unknown](https://theasc.com/articles/annihilation-expedition-unknown); [VFX Blog — Mandelbulbs and the VFX of Annihilation](https://vfxblog.com/2018/03/12/mandelbulbs-mutations-and-motion-capture-the-visual-effects-of-annihilation/); [We Are the Mutants — Reflection, Refraction, Mutation](https://wearethemutants.com/2018/04/17/reflection-refraction-mutation-alex-garlands-annihilation/); [The Quietus — A Shimmer in their Eyes](https://thequietus.com/culture/film/annihilation-review/); [Film Comment — Deep Focus: Annihilation](https://www.filmcomment.com/blog/deep-focus-annihilation/).)

**For HOMAGE:** the Shimmer's lesson is *the boundary IS the effect*. Don't render an "inside" the bowl that's drastically different from "outside" — render the *boundary* as the locus of refraction, color split, condensation. The scrim's outer surface (where wards live) is where the most refraction lands; the deep-band content is conventional, just tinted and blurred.

### 10.4 Last Year at Marienbad (Resnais / Robbe-Grillet, 1961)

Sacha Vierny's Dyaliscope (2.35:1) cinematography of the baroque hotel: gliding camera, low-angle tracking, cinema's "greatest hymn to stasis." Robbe-Grillet's intent: "an attempt to construct a purely mental space and time — those of dreams, perhaps, or of memory." Scenes paired with eerie organ and breathy narration unfold without distinguishing dreams from memories. ([The Criterion Collection — Last Year at Marienbad](https://www.criterion.com/films/1517-last-year-at-marienbad); [Wikipedia — Last Year at Marienbad](https://en.wikipedia.org/wiki/Last_Year_at_Marienbad); [Slant — Last Year at Marienbad Review](https://www.slantmagazine.com/film/last-year-at-marienbad-5981/); [BFI Big Screen Classics — Last Year in Marienbad](https://bfidatadigipres.github.io/big%20screen%20classics/2022/09/26/last-year-in-marienbad/); [Automachination — The Murmur of Memory](https://www.automachination.com/murmur-memory-alain-resnais-last-year-at-marienbad-1961/).)

**For HOMAGE:** Marienbad's lesson is that *static-feeling space with internal motion = dream*. The fishbowl is precisely this register: the *frame* is stable, the *contents* drift. This is the inverse of action cinema (stable contents, moving camera). It is the correct register for the Nebulous Scrim's intimate "hailing across" voice.

### 10.5 Tarkovsky, Stalker — the Zone (1979)

The Zone is shot in color while the outer world is sepia. The transition between is the cue. Inside the Zone, lush mist-veiled landscapes, long takes (the opening 7-minute continuous shot), deep focus, sound design that becomes "increasingly disorienting, with eerie soundscapes and distorted voices." The Zone is "a world of lush landscapes veiled in an ethereal mist that becomes a character itself." ([Senses of Cinema / Velvet Eyes / Wikipedia — Stalker (1979)](https://en.wikipedia.org/wiki/Stalker_(1979_film)); [Velvet Eyes — Stalker](https://velveteyes.net/movie-stills/stalker/); [Soviet Movie Posters — Stalker Cinematography](https://sovietmovieposters.com/movies-shape-stories/stalker/); [The New Republic — Why Stalker Is the Film We Need Now](https://newrepublic.com/article/143045/stalker-film-need-now); [Off-Screen — Temporal Defamiliarization in Stalker](https://offscreen.com/view/temporal_defamiliarization); [Peliplat — Crossing the Threshold: Liminal Spaces](https://www.peliplat.com/en/article/10004002/chapter-2-crossing-the-threshold-a-cinematic-exploration-of-liminal-spaces).)

**For HOMAGE:** the Zone's lesson is *crossing-the-boundary as a one-time event with permanent visual register-shift*. The audience enters the bowl-space when the stream begins; they don't leave until it ends. The visual register is consistent for the duration. There is no "reset to normal frame" within a stream. The bowl is the unit of viewing.

### 10.6 Tropical Malady — the forest (Apichatpong Weerasethakul, 2004)

The second half of the film: a soldier alone in the night jungle, "barely illuminated by moonlight, surrounded by thick vines and trees... practically enveloped by the singing of insects, birds, wind in the trees, and otherworldly electronic chatter." Almost wordless. Locked-off compositions. Weerasethakul: "Emotions are revealed by the jungle; it becomes a kind of mindscape." ([Senses of Cinema — The Strange Beast: Tropical Malady](https://www.sensesofcinema.com/2021/cteq/the-strange-beast-tropical-malady-apichatpong-weerasethakul-2004/); [BFI — Tropical Malady](https://www.bfi.org.uk/film/b6fed05e-eca5-5924-a201-efe4f3b86d6d/tropical-malady); [Senses of Cinema — Tropical Malady (2006)](https://www.sensesofcinema.com/2006/cteq/tropical_malady/); [Wikipedia — Tropical Malady](https://en.wikipedia.org/wiki/Tropical_Malady); [Film Comment — Queer & Now & Then: 2004](https://www.filmcomment.com/blog/queer-now-then-2004-tropical-malady-apichatpong-weerasethakul/).)

**For HOMAGE:** Tropical Malady's lesson is *enveloping ambient*. The deep band of the bowl should feel like Weerasethakul's jungle — full of unspecified depth and motion, slightly threatening only because it is *more than the eye can resolve*. Not literal threat. Just more-than-eye-can-resolve. The deep camera-PiP layer + the gauzy weave + the slow currents add up to this register.

### 10.7 The "color of magic" tradition

Oil-on-water rainbows as portal markers. The chromatic aberration at the bowl's curved edge IS this trope — the rainbow is the *signature* of the boundary. Newton's rainbow physics turned into Sterling Macer's (Twin Peaks lighting designer) palette, into the Shimmer's iridescent edge, into the Stargate's spectrum-bleed, into the Bachelard amendment's ROYGBIV reaction-diffusion accumulation. The HOMAGE chromatic-aberration radial-mask move is a direct citation of this tradition. ([Newton's Opticks → Mathpages](https://www.mathpages.com/home/kmath721/kmath721.htm); [Annihilation Shimmer petrol-slick design — VFX Blog](https://vfxblog.com/2018/03/12/mandelbulbs-mutations-and-motion-capture-the-visual-effects-of-annihilation/).)

### 10.8 The synthesis

The fishbowl is *Twin Peaks consistency* + *Stalker boundary-crossing* + *Marienbad static-with-internal-motion* + *Tropical Malady enveloping ambient* + *Annihilation boundary-as-effect* + *Stargate time-smeared moments* + *Lynch's commitment to a stable strange grammar*. None of these are about water. All of them are about *adjacent dimensional space* viewed through a thin barrier. The HOMAGE scrim is exactly that barrier; the fishbowl conceit is the *grammar inside it*.

---

## §11 Anti-Anthropomorphization Invariants

The operator's HARDM principle (`project_hardm_anti_anthropomorphization`): "no eyes / mouths / expressions. Raw signal-density on a grid." This applies to every ward and every effect. The fishbowl conceit is dangerously close to anthropomorphic territory because *bowls have fish*. The invariant must be unambiguous.

### 11.1 No fish

There are no fish-iconography elements anywhere in the system. No fish-shaped wards. No fish-icon overlays. No "schooling" animation patterns visible to the eye. No "swimming" gestures. The word "fishbowl" describes the *spatial conceit* — layered, suspended, slightly refracted, slightly slow — not the *contents*.

### 11.2 No personality projection on layered wards

Wards do not "react to each other" with personality. They share local-neighborhood layout adjustments via low-weight boids math (§6.7), but the visible behavior must remain *invisible-but-felt*. If a tester ever describes wards as having "preferences" about each other, the boid weights are too high.

### 11.3 No biographical depth

The Z-position of a ward is a *geometric* property, not a *character* property. Surface wards are not "more important" or "more present" than deep wards in a personality sense; they are *closer to the audience* in a geometric sense. The depth bands map to *information-architectural roles* (chrome / state / hero / context), not to character traits.

### 11.4 Contents-aware-but-not-seeing-out

Wards do not address the camera. They behave as if the audience is not there. Hapax's avatar wards are the ONLY elements on the scrim that hail across — and even those do so via the structural-intent `scrim.pierce` (Nebulous Scrim §8.3), not by breaking the geometric fourth wall.

### 11.5 The bowl, not the contents, is the metaphor

Every reference in §10 — Hirst's vitrine, Dion's cabinet, the Lodge, the Stargate, the Shimmer, the Zone, the jungle, Marienbad — is about *the framing apparatus*, not *the things inside it*. The HOMAGE scrim follows this lineage. The wards are simply the wards; the bowl is the conceit.

### 11.6 Test for invariant violations

If at any point during implementation:

- a ward acquires a face, eyes, mouth, or facial-feature analog,
- a ward animation reads as "expression,"
- a ward flocking reads visibly as "schooling,"
- the depth bands acquire personality narratives,
- the bowl acquires literal aquarium ornamentation (plants, gravel, bubbles-as-decoration),
- any documentation describes wards as "fish," "creatures," "swimmers," "inhabitants" (in the biological sense),

then the fishbowl conceit has slipped into anthropomorphization and must be rolled back. This is a hard line.

### 11.7 Permitted "biological" vocabulary

For internal documentation (specs, ADRs, this doc), the following metaphor-vocabulary is fine because it describes *physical media*, not living beings:

- "currents" (water motion, not creature motion)
- "drift" (passive medium motion)
- "wake" (physical disturbance behind a moving object)
- "buoyancy" (medium force)
- "breath" (the scrim's pulse, already in stack)
- "settling" (damping)
- "suspended" (held in medium)

Vocabulary to AVOID even in internal docs:

- "swim," "school," "creature," "fish," "alive" (in biological sense), "lurking," "darting," "aware" (of audience), "watching" (audience back)

### 11.8 The HARDM persona connection

HARDM is the visual twin of CVS #16 (persona anti-personification). The fishbowl conceit must be the visual twin of the same restraint. The *bowl* is the persona-frame; the *wards* are the persona-content; neither pretends to be a being. The metaphor is *spatial geometry of intimacy across distance*, not *creatures observed*.

---

## §12 Concrete Code-Shapes

Pydantic models, WGSL fragments, and Cairo pipeline pseudocode. Implementation sketches for downstream PRs; not verbatim PR-ready code.

### 12.1 WardSpatialState Pydantic model

```python
# shared/ward_spatial.py (proposed)
from pydantic import BaseModel, Field
from typing import Literal

class WardSpatialState(BaseModel):
    """Per-ward spatial conditioning for fishbowl depth.

    Z-position maps to scrim depth bands per Nebulous Scrim §6:
      Z=0.00..0.20  surface (chrome, captions)
      Z=0.20..0.40  near-surface (Hapax internal-state wards)
      Z=0.40..0.60  hero-presence (token_pole, hardm)
      Z=0.60..1.00  beyond-scrim (camera PiPs, vinyl, sierpinski)
    """
    z_position: float = Field(0.0, ge=0.0, le=1.0)
    depth_band: Literal["surface", "near_surface", "hero", "beyond"] = "surface"

    # Liquid-medium motion state
    velocity: tuple[float, float] = (0.0, 0.0)
    drift_vector: tuple[float, float] = (0.0, 0.0)
    last_motion_tick: float = 0.0
    wake_strength: float = 0.0

    # Composition tags
    is_hero: bool = False  # marks the focused ward; gets size 1.05 + heat-shimmer

    # Cached per-Z derived constants (recomputed when z_position changes)
    blur_radius_px: float = 0.0
    saturation_scale: float = 1.0
    contrast_scale: float = 1.0
    fog_alpha: float = 0.0
    transition_ms: int = 250
    damping: float = 0.88
    target_fps: int = 30

    def recompute_derived(self, package_scrim_tint: tuple[float, float, float]) -> None:
        z = self.z_position
        self.blur_radius_px = z * 1.5
        self.saturation_scale = 1.0 - (z * 0.3)
        self.contrast_scale = 1.0 - (z * 0.2)
        self.fog_alpha = z * 0.25
        self.transition_ms = int(250 + z * 350)
        self.damping = 0.88 + z * 0.06
        # Z=0 → 30fps; Z=1 → 15fps. Per §8.1.
        self.target_fps = int(30 - z * 15)
```

### 12.2 WGSL fragment — atmospheric perspective

```wgsl
// agents/shaders/nodes/atmospheric_perspective.wgsl (proposed; or fold into colorgrade)
// Inputs:
//   in_color : vec4<f32>     // ward's intrinsic color (after cairo render)
//   uniforms.ward_z : f32    // 0..1 depth
//   uniforms.scrim_tint : vec3<f32>  // package-declared scrim color
// Output:
//   final color with atmospheric perspective applied

fn apply_atmospheric_perspective(in_color: vec4<f32>) -> vec4<f32> {
    let z = uniforms.ward_z;

    // Saturation reduce (HSV approach via luminance lerp)
    let lum = dot(in_color.rgb, vec3<f32>(0.299, 0.587, 0.114));
    let desat_strength = z * 0.3;
    var rgb = mix(in_color.rgb, vec3<f32>(lum), desat_strength);

    // Contrast reduce (lerp toward midgray)
    let contrast_strength = z * 0.2;
    rgb = mix(rgb, vec3<f32>(0.5), contrast_strength);

    // Fog (additive scrim tint)
    let fog_alpha = z * 0.25;
    rgb = mix(rgb, uniforms.scrim_tint, fog_alpha);

    return vec4<f32>(rgb, in_color.a);
}
```

### 12.3 Cairo render pipeline — depth-conditioned blur

```python
# agents/studio_compositor/cairo_source.py (proposed extension)

def _apply_depth_conditioned_blur(
    surface: cairo.ImageSurface,
    spatial: WardSpatialState,
) -> cairo.ImageSurface:
    """Apply Z-conditioned Gaussian blur to a cached cairo surface.

    Called once when the cached surface is regenerated, not per frame.
    For Z=0.0 (surface), no-op. For Z=1.0 (deep), 1.5px Gaussian.
    """
    if spatial.blur_radius_px < 0.1:
        return surface  # no-op for surface wards

    # Use Pillow for the blur step (cheaper than per-pixel cairo math)
    # Convert ImageSurface → PIL → blur → back to ImageSurface
    import numpy as np
    from PIL import Image, ImageFilter

    width = surface.get_width()
    height = surface.get_height()
    buf = surface.get_data()
    arr = np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 4)
    # cairo BGRA → PIL RGBA
    pil = Image.fromarray(arr[:, :, [2, 1, 0, 3]], mode="RGBA")
    blurred = pil.filter(ImageFilter.GaussianBlur(radius=spatial.blur_radius_px))
    out_arr = np.array(blurred)
    # PIL RGBA → cairo BGRA
    out_arr = out_arr[:, :, [2, 1, 0, 3]].copy()
    out_surface = cairo.ImageSurface.create_for_data(
        out_arr.tobytes(), cairo.FORMAT_ARGB32, width, height
    )
    return out_surface
```

### 12.4 Animation tick — spring-damper + drift + boundary bounce

```python
# Per-frame ward animation update (CPU-side; ~0.05ms for ~20 wards)

def update_ward_animation(
    ward: Ward,
    spatial: WardSpatialState,
    current: Current,  # global ambient flow
    dt_seconds: float,
) -> None:
    # 1. Inherit current (scaled by Z)
    current_force = (current.dx * spatial.z_position, current.dy * spatial.z_position)

    # 2. Spring force toward target position
    dx_to_target = ward.target_x - ward.position_x
    dy_to_target = ward.target_y - ward.position_y
    spring_k = 1.0 / (spatial.transition_ms / 1000.0) ** 2
    spring_force = (dx_to_target * spring_k, dy_to_target * spring_k)

    # 3. Sum forces, integrate velocity
    fx = current_force[0] + spring_force[0] + spatial.drift_vector[0]
    fy = current_force[1] + spring_force[1] + spatial.drift_vector[1]
    new_vx = (spatial.velocity[0] + fx * dt_seconds) * spatial.damping
    new_vy = (spatial.velocity[1] + fy * dt_seconds) * spatial.damping

    # 4. Integrate position
    new_x = ward.position_x + new_vx * dt_seconds
    new_y = ward.position_y + new_vy * dt_seconds

    # 5. Boundary bounce (soft; per §6.6)
    if new_x < ward.bounds.x_min or new_x > ward.bounds.x_max:
        new_vx *= -0.3
        new_x = max(ward.bounds.x_min, min(ward.bounds.x_max, new_x))
    if new_y < ward.bounds.y_min or new_y > ward.bounds.y_max:
        new_vy *= -0.3
        new_y = max(ward.bounds.y_min, min(ward.bounds.y_max, new_y))

    # 6. Update wake_strength based on motion magnitude
    motion_mag = (new_vx ** 2 + new_vy ** 2) ** 0.5
    spatial.wake_strength = max(spatial.wake_strength * 0.9, motion_mag * 0.05)

    # 7. Persist
    spatial.velocity = (new_vx, new_vy)
    ward.position_x = new_x
    ward.position_y = new_y
    spatial.last_motion_tick = time.monotonic()
```

### 12.5 Programme YAML — fishbowl depth grammar

```yaml
# config/scrim_profiles/listening.yaml (proposed)
name: listening
package: bitchx
scrim:
  density: 0.65
  weave_amplitude: 0.25
  breath_hz: 0.18
fishbowl:
  atmospheric_strength: 1.0       # full atmospheric perspective
  depth_blur_max_px: 1.5
  motion_inertia_scale: 1.2       # extra slow on listening
  current_dx: -0.08               # gentle leftward drift
  current_dy: -0.02
  current_period_s: 35
  per_z_breath_phase_max_rad: 0.6
  wake_fade_floor: 0.92           # long persistent wakes
  edge_chromatic_strength: 0.04   # subtle bowl curvature

ward_z_overrides:
  # Per-programme Z assignment; defaults from ward.metadata.depth_band
  vinyl_pip: 0.85         # listening pushes vinyl deep
  token_pole: 0.45        # hero
  captions_source: 0.05   # surface
  album_overlay: 0.55     # near-hero
```

```yaml
# config/scrim_profiles/hothouse.yaml (proposed)
name: hothouse
package: bitchx
scrim:
  density: 0.85
  weave_amplitude: 0.55
  breath_hz: 0.32
fishbowl:
  atmospheric_strength: 0.5       # less wash; wards stay punchy
  depth_blur_max_px: 0.8
  motion_inertia_scale: 0.7       # snappier on hothouse
  current_dx: 0.04
  current_dy: -0.06
  current_period_s: 12            # faster shifts
  per_z_breath_phase_max_rad: 0.3
  wake_fade_floor: 0.78           # shorter wakes
  edge_chromatic_strength: 0.08
```

### 12.6 Compositor integration point

The composite-time depth conditioning lives in `agents/studio_compositor/compositional_consumer.py` (the place that already hands cairo surfaces to the GStreamer pipeline). The proposed extension:

```python
# Pseudocode (agents/studio_compositor/compositional_consumer.py extension)

def composite_with_fishbowl_depth(
    self,
    ward_set: list[Ward],
    scrim_profile: ScrimProfile,
) -> CompositorOutput:
    # 1. Sort wards by Z descending (deepest first; occlusion)
    sorted_wards = sorted(ward_set, key=lambda w: w.spatial.z_position, reverse=True)

    # 2. Per-ward conditioning
    for ward in sorted_wards:
        ward.spatial.recompute_derived(scrim_profile.package_scrim_tint)
        # Update animation
        update_ward_animation(ward, ward.spatial, scrim_profile.current, dt)
        # Apply Z-conditioned tint at composite time (cheap)
        ward.composite_color_grade = build_atmospheric_grade(ward.spatial)
        # Per-Z FPS gating (cairo source already supports this)
        if not should_render_this_tick(ward.spatial.target_fps):
            continue
        # Cached cairo surface includes Z-conditioned blur (one-time)
        ward.surface = self.cairo_runner.get_or_render(ward, ward.spatial)

    # 3. Compose into Reverie's content_layer with per-ward params
    return self.compose_content_layer(sorted_wards, scrim_profile)
```

### 12.7 Telemetry

Add Prometheus metrics for fishbowl conditioning:

- `hapax_scrim_ward_z{ward_id}` — current Z position (gauge)
- `hapax_scrim_ward_velocity_mag{ward_id}` — current velocity magnitude
- `hapax_scrim_ward_wake_strength{ward_id}` — current wake strength
- `hapax_scrim_current_dx`, `hapax_scrim_current_dy` — global current vector
- `hapax_scrim_atmospheric_strength` — currently-active programme value

So we can visualize the bowl's kinematic state and verify the conceit is doing what it should. This piggybacks on the existing `agents/studio_compositor/budget.py::publish_costs` mechanism.

---

## §13 Open Questions

These need either operator decision or empirical testing on a livestream session before v1 lands.

1. **Z assignment per ward — manual or automatic?** Proposal: each ward's `WardSpatialState.z_position` is declared in its metadata file (manual, deterministic, programme-overridable). Alternative: derive Z from the depth band that the ward already declares (semi-auto). Recommend manual + programme overrides for v1; full auto only if we get tired of the manual maintenance.

2. **Per-ward feedback fade — implement the exact version or the cheap approximation?** §9.2 suggests cheap approximation (single global fade tied to most-active deep ward). Question: does the eye actually notice the difference at 1.5px blur? Empirical test required.

3. **Boundary bounce — at the frame edge, or at the overlay-zone edge?** §6.6 doesn't specify. Recommend overlay-zone edge (so wards bounce within their assigned region), but this needs operator confirmation against the visual register.

4. **Inkblot dispersal on entry — for which depth bands?** §8.3 says skip for surface wards. Should hero-presence wards (Hapax avatars) also skip (instant materialization to reinforce hailing-across)? Or get a tiny inkblot to feel-alive?

5. **Echo / phantom wards — opt-in or default?** §8.4 specifies the technique; not whether every moving ward gets echoes by default. Recommend opt-in via `ward.spatial.echo_enabled` to avoid frame clutter.

6. **Boid neighborhood radius — local zone, or full frame?** §6.7 specifies very low weights. The neighborhood query cost is `O(n²)` if computed naively. Recommend per-overlay-zone neighborhood (cap the search radius to the ward's parent zone). Cheap, and matches the "local layout adjustment" intent.

7. **Programme-based Z overrides — should they animate the transition?** §12.5 shows `ward_z_overrides`; on programme change, the ward's Z should presumably animate to the new value, not snap. The transition duration could be the *deeper* of the two states' transition_ms. Operator confirm.

8. **Hero-mode size scaling — 1.05× or smaller?** §3.5 proposed 1.05×. Could be 1.03× or 1.08×. Empirical test, depends on register.

9. **Chromatic aberration radial mask — how aggressive?** §5.3 says low. Specifically: linear from 0.0 at center to ~0.04 at edges? Or `r²` bias toward outermost 20% of the frame only? Recommend `r²` mask for "only at the bowl curve" feel; needs visual A/B.

10. **Caustics — defer entirely, or queue for v2?** §5.4 recommends defer. v2 might be: caustics overlay only during interlude/chat programme, low intensity, register-bound. Operator decision.

11. **Time-cadence (target_fps per Z) — does GStreamer compositor honor per-element cadences cleanly?** The CairoSourceRunner does, per `cairo_source.py`. But the downstream effect-graph chain may not. Verify experimentally.

12. **`target_fps` LOD ladder — linear in Z, or stepped?** §12.1 sketch is linear (`30 - z*15`). Alternative: stepped (Z<0.4 → 30, Z 0.4..0.7 → 24, Z>0.7 → 15). Stepped is easier to reason about. Recommend stepped for v1.

---

## §14 Sources

### Animation industry — multiplane and 2.5D depth

- [Multiplane camera — Wikipedia](https://en.wikipedia.org/wiki/Multiplane_camera)
- [NIHF — Walt Disney and the Multiplane Camera](https://www.invent.org/inductees/walt-disney)
- [PetaPixel — How Disney's Multiplane Camera Achieved the Illusion of Depth (2025)](https://petapixel.com/2025/04/04/how-disneys-multiplane-camera-achieved-the-illusion-of-depth/)
- [Collider — The Technology That Made Disney's Animated Classics More Magical](https://collider.com/disney-snow-white-and-the-seven-dwarfs-multiplane-camera/)
- [Walt Disney Family Museum — Multiplane Classroom Kit](https://www.waltdisney.org/multiplane-classroom-kit)
- [Sony Pictures Imageworks — Spider-Man: Into the Spider-Verse Production](https://www.imageworks.com/our-craft/feature-animation/movies/spider-man-spider-verse)
- [80.lv — 2D VFX Behind Spot from Spider-Man: Across the Spider-Verse](https://80.lv/articles/2d-vfx-behind-spot-from-spider-man-across-the-spider-verse)
- [VFX Voice — Imageworks Artists 'Break the Mold' to Create Alternate Spider-Verse](https://vfxvoice.com/imageworks-artists-break-the-mold-to-create-an-alternate-spider-verse/)
- [SideFX — Spider-Man Into the Spider-Verse / SPI](https://www.sidefx.com/community/spider-man-into-the-spider-verse/)
- [CG Spectrum — The Animation Secrets of Spider-Man: Into the Spider-Verse](https://www.cgspectrum.com/blog/spider-man-into-the-spider-verse-how-they-got-that-mind-blowing-look)
- [Foundry — Across the Spider-Verse with Nuke, Mari & Katana](https://www.foundry.com/insights/film-tv/across-the-spider-verse-nuke-mari-katana)
- [Animation World Network — Rewriting the Visual Rule Book on Spider-Man: Into the Spider-Verse](https://www.awn.com/animationworld/rewriting-visual-rule-book-spider-man-spider-verse)
- [Wikipedia — Spider-Man: Into the Spider-Verse](https://en.wikipedia.org/wiki/Spider-Man:_Into_the_Spider-Verse)
- [Studio Ghibli Layout Designs — Goodreads](https://www.goodreads.com/book/show/17187165-studio-ghibli-layout-designs)
- [Halcyon Realms — Studio Ghibli Layout Designs Exhibition Art Book Review](https://halcyonrealms.com/anime/studio-ghibli-layout-designs-exhibition-art-book-review/)
- [Through the Looking Glass — Ghibli Layout Designs at HK Heritage Museum](https://rachttlg.com/2014/07/09/studio-ghibli-hong-kong-heritage-museum/)
- [befores & afters — What Made the 2D Animation in Klaus Look 3D](https://beforesandafters.com/2019/11/14/heres-what-made-the-2d-animation-in-klaus-look-3d/)
- [AWN — How Klaus Uniquely Combines CG Lighting Techniques with Traditional 2D Animation](https://www.awn.com/animationworld/how-klaus-uniquely-combines-cg-lighting-techniques-traditional-2d-animation)
- [Toon Boom — Sergio Pablos on the Creative Process Behind Klaus](https://www.toonboom.com/sergio-pablos-klaus)
- [Deadline — Sergio Pablos Elevates 2D Animation with Klaus](https://deadline.com/2019/12/klaus-director-sergio-pablos-netflix-animation-interview-1202807202/)
- [SIGGRAPH Blog — Behind the Magic of Netflix's Klaus](https://blog.siggraph.org/2019/12/behind-the-magic-of-netflixs-klaus.html/)
- [Animation Magazine — Annecy: Tomm Moore on Wolfwalkers](https://www.animationmagazine.net/2020/06/annecy-tomm-moore-reveals-inspirations-behind-cartoon-saloons-wolfwalkers/)
- [Animation Obsessive — Inside the Look of Wolfwalkers with Sandra Andersen](https://animationobsessive.substack.com/p/inside-the-look-of-wolfwalkers-with)
- [Cartoon Saloon — Wolfwalkers](https://www.cartoonsaloon.ie/wolfwalkers/)

### Shader and real-time graphics

- [Inigo Quilez — Simple Water article](https://iquilezles.org/articles/simplewater/)
- [Inigo Quilez — Articles index](https://iquilezles.org/articles/)
- [Stevan Dedovic — Warping / Refraction Shader](https://www.dedovic.com/writings/warping-refraction-shader)
- [Maxime Heckel — Refraction, Dispersion, and Other Shader Light Effects](https://blog.maximeheckel.com/posts/refraction-dispersion-and-other-shader-light-effects/)
- [DEV.to — WebGL-Based JS Library for iOS Liquid Glass Effect](https://dev.to/maxgeris/webgl-based-javascript-library-for-pixel-perfect-ios-liquid-glass-effect-with-refractions-and-3p8m)
- [Lettier — Chromatic Aberration / 3D Game Shaders for Beginners](https://lettier.github.io/3d-game-shaders-for-beginners/chromatic-aberration.html)
- [Harry Alisavakis — Chromatic Aberration (Image Effects IV)](https://halisavakis.com/my-take-on-shaders-chromatic-aberration-introduction-to-image-effects-part-iv/)
- [GM Shaders Mini — Chromatic Aberration](https://mini.gmshaders.com/p/gm-shaders-mini-chromatic-aberration)
- [ReShade Forum — YACA (Yet Another Chromatic Aberration)](https://reshade.me/forum/shader-presentation/1133-yaca-yet-another-chromatic-aberration)
- [The Book of Shaders — Noise (Ch. 11)](https://thebookofshaders.com/11/)
- [The Book of Shaders — More Noise (Ch. 12)](https://thebookofshaders.com/12/)
- [The Book of Shaders — Fractal Brownian Motion (Ch. 13)](https://thebookofshaders.com/13/)
- [Procedural Textures in GLSL — DiVA Linköping](https://www.diva-portal.org/smash/get/diva2:618262/FULLTEXT02.pdf)
- [NVIDIA Developer — Rendering Water Caustics (GPU Gems Ch. 2)](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-2-rendering-water-caustics)
- [Martin Renou — Real-Time Rendering of Water Caustics](https://medium.com/@martinRenou/real-time-rendering-of-water-caustics-59cda1d74aa)
- [Evan Wallace — Rendering Realtime Caustics in WebGL](https://medium.com/@evanwallace/rendering-realtime-caustics-in-webgl-2a99a29a0b2c)
- [Alexander Ameye — Realtime Caustics](https://ameye.dev/notes/realtime-caustics/)
- [Allan Bishop — Interactive Water Simulation in Unity](https://www.allanbishop.com/2022/08/17/interactive-water-simulation-in-unity/)

### Perception science

- [OEN Manifold — Sensation & Perception, Ch. 9: Depth Perception](https://manifold.open.umn.edu/read/sensation-perception/section/a10b03b5-47f4-459f-ba26-33c968d8eb01)
- [Piter Pasma — Visual Depth Cues](https://piterpasma.nl/articles/depth-cues)
- [Wikipedia — Depth Perception](https://en.wikipedia.org/wiki/Depth_perception)
- [PointOptics — A Guide to Monocular Cues](https://www.pointoptics.com/monocular-cues/)
- [PMC — The Neural Basis of Depth Perception from Motion Parallax](https://pmc.ncbi.nlm.nih.gov/articles/PMC4901450/)
- [ScienceDirect — Motion Parallax overview](https://www.sciencedirect.com/topics/computer-science/motion-parallax)
- [Lens.com — What Is Motion Parallax?](https://www.lens.com/what-is/what-is-motion-parallax/)
- [UC Irvine — Chapter 7: Perceiving Depth and Size (PDF)](https://ics.uci.edu/~majumder/vispercep/chap8notes.pdf)

### Optics history

- [Snell's Law — Wikipedia](https://en.wikipedia.org/wiki/Snell%27s_law)
- [Britannica — Snell's Law](https://www.britannica.com/science/Snells-law)
- [Britannica — Willebrord Snell biography](https://www.britannica.com/biography/Willebrord-Snell)
- [Mathpages — Refraction Revisited and Newton's Gespensterfeld](https://www.mathpages.com/home/kmath721/kmath721.htm)
- [Univ. Texas — History of Geometric Optics](https://farside.ph.utexas.edu/teaching/316/lectures/node125.html)
- [Wikipedia — Rainbow](https://en.wikipedia.org/wiki/Rainbow)
- [AMS Feature Column — The Mathematics of Rainbows](https://www.ams.org/publicoutreach/feature-column/fcarc-rainbows)
- [Sfumato — Wikipedia](https://en.wikipedia.org/wiki/Sfumato)
- [Russell Collection — What Is Aerial Perspective in Painting?](https://russell-collection.com/what-is-aerial-perspective-in-painting/)
- [Aerial Perspective — UBC Faculty of Arts](https://faculty.arts.ubc.ca/rfedoruk/perspective/9.htm)
- [Art Secrets Studio — Leonardo da Vinci & Aerial Perspective with Sfumato](https://www.artsecretsstudio.com/post/leonardo-davinci-aerial-perspective-with-sfumato-softening-edges-by-getting-darker-farther-away)

### Boids / flocking

- [Reynolds 1987 SIGGRAPH paper — Flocks, Herds, and Schools (PDF)](https://www.red3d.com/cwr/papers/1987/SIGGRAPH87.pdf)
- [Reynolds — Flocks, Herds, and Schools (HTML)](https://www.red3d.com/cwr/papers/1987/boids.html)
- [Reynolds — Boids landing page](https://www.red3d.com/cwr/boids/)
- [Wikipedia — Boids](https://en.wikipedia.org/wiki/Boids)
- [befores & afters — A History of CG Bird Flocking](https://beforesandafters.com/2022/04/07/a-history-of-cg-bird-flocking/)

### Inter-dimensional film / liminal space

- [Idyllopus Press — Analysis of Twin Peaks: The Return Pt. 1](https://idyllopuspress.com/idyllopus/film/tpr1.htm)
- [Far Out Magazine — How Twin Peaks Created the Red Room Dialogue Effect](https://faroutmagazine.co.uk/strange-dialogue-twin-peaks-red-room/)
- [Twin Peaks Gazette — Iconography of the Red Room](https://twinpeaksgazette.com/2017/07/22/iconography-of-the-red-room/)
- [25 Years Later — Black Lodge, White Lodge: Time for a Rethink?](https://25yearslatersite.com/2017/09/26/black-lodge-white-lodge-time-for-a-rethink/)
- [Slashfilm — Twin Peaks' Red Room Was Created to Serve a Surprisingly Practical Purpose](https://www.slashfilm.com/836610/twin-peaks-red-room-was-created-to-serve-a-surprisingly-practical-purpose/)
- [Media + Art + Innovation — Doug Trumbull: Special Effects on 2001](https://mediartinnovation.com/2014/08/05/doug-trumbull-special-effects-on-2001-a-space-odyssey/)
- [Indie Film Hustle — Stanley Kubrick's Slit Scan Effect in 2001](https://indiefilmhustle.com/stanley-kubrick-slit-scan-2001/)
- [Film School Rejects — How They Shot the Stargate Sequence in 2001](https://filmschoolrejects.com/2001-a-space-odyssey-stargate/)
- [Air & Space — The Making of 2001's Star Gate Sequence](https://airandspace.si.edu/stories/editorial/making-2001s-star-gate-sequence)
- [Neil Oseman — Slit-Scan and the Legacy of Douglas Trumbull](https://neiloseman.com/slit-scan-and-the-legacy-of-douglas-trumbull/)
- [BFI — Douglas Trumbull obituary](https://www.bfi.org.uk/news/douglas-trumbull-1942-2022)
- [Red Shark News — Douglas Trumbull and How Slit-Scan Changed SFX](https://www.redsharknews.com/douglas-trumbull-and-how-slit-scan-changed-sfx)
- [ASC — Annihilation: Expedition Unknown](https://theasc.com/articles/annihilation-expedition-unknown)
- [VFX Blog — Mandelbulbs, Mutations and Motion Capture: The VFX of Annihilation](https://vfxblog.com/2018/03/12/mandelbulbs-mutations-and-motion-capture-the-visual-effects-of-annihilation/)
- [We Are the Mutants — Reflection, Refraction, Mutation: Alex Garland's Annihilation](https://wearethemutants.com/2018/04/17/reflection-refraction-mutation-alex-garlands-annihilation/)
- [The Quietus — A Shimmer in their Eyes: On Alex Garland's Annihilation](https://thequietus.com/culture/film/annihilation-review/)
- [Film Comment — Deep Focus: Annihilation](https://www.filmcomment.com/blog/deep-focus-annihilation/)
- [The Criterion Collection — Last Year at Marienbad](https://www.criterion.com/films/1517-last-year-at-marienbad)
- [Wikipedia — Last Year at Marienbad](https://en.wikipedia.org/wiki/Last_Year_at_Marienbad)
- [BFI Big Screen Classics — Last Year in Marienbad](https://bfidatadigipres.github.io/big%20screen%20classics/2022/09/26/last-year-in-marienbad/)
- [Slant Magazine — Last Year at Marienbad Review](https://www.slantmagazine.com/film/last-year-at-marienbad-5981/)
- [Automachination — The Murmur of Memory: Resnais's Last Year at Marienbad](https://www.automachination.com/murmur-memory-alain-resnais-last-year-at-marienbad-1961/)
- [Wikipedia — Stalker (1979 film)](https://en.wikipedia.org/wiki/Stalker_(1979_film))
- [Velvet Eyes — A Dive into the Enigmatic Stalker](https://velveteyes.net/movie-stills/stalker/)
- [Soviet Movie Posters — Stalker (1979) Cinematography](https://sovietmovieposters.com/movies-shape-stories/stalker/)
- [Off-Screen — Temporal Defamiliarization and Mise-en-Scène in Tarkovsky's Stalker](https://offscreen.com/view/temporal_defamiliarization)
- [Peliplat — Crossing the Threshold: Cinematic Liminal Spaces](https://www.peliplat.com/en/article/10004002/chapter-2-crossing-the-threshold-a-cinematic-exploration-of-liminal-spaces)
- [Senses of Cinema — The Strange Beast: Tropical Malady (Apichatpong Weerasethakul, 2004)](https://www.sensesofcinema.com/2021/cteq/the-strange-beast-tropical-malady-apichatpong-weerasethakul-2004/)
- [BFI — Tropical Malady](https://www.bfi.org.uk/film/b6fed05e-eca5-5924-a201-efe4f3b86d6d/tropical-malady)
- [Senses of Cinema — Tropical Malady (2006)](https://www.sensesofcinema.com/2006/cteq/tropical_malady/)
- [Wikipedia — Tropical Malady](https://en.wikipedia.org/wiki/Tropical_Malady)
- [BFI — Where to Begin with Apichatpong Weerasethakul](https://www.bfi.org.uk/features/where-begin-with-apichatpong-weerasethakul)

### Aquarium / vitrine installation art

- [DailyArt Magazine — The Story of Damien Hirst's Famous Shark](https://www.dailyartmagazine.com/story-damien-hirst-shark/)
- [Wikipedia — The Physical Impossibility of Death in the Mind of Someone Living](https://en.wikipedia.org/wiki/The_Physical_Impossibility_of_Death_in_the_Mind_of_Someone_Living)
- [Tate — Luke White: Damien Hirst's Shark — Nature, Capitalism and the Sublime](https://www.tate.org.uk/art/research-publications/the-sublime/luke-white-damien-hirsts-shark-nature-capitalism-and-the-sublime-r1136828)
- [Atlas Obscura — The Most Beautiful Marine Curiosity Cabinet, Created by Mark Dion](https://www.atlasobscura.com/articles/mark-dion-s-marine-curiosity-cabinet)
- [V&A — A Field Guide to Curiosity: A Mark Dion Project](https://www.vam.ac.uk/articles/a-field-guide-to-curiosity-a-mark-dion-project)
- [Whitewall — Mark Dion Explores Sea Life](https://whitewall.art/art/mark-dion-explores-sea-life/)
- [Tate — Digging the Thames with Mark Dion](https://www.tate.org.uk/art/artworks/dion-tate-thames-dig-t07669/digging-thames-mark-dion)

### Cinematography (atmospheric substrate)

- [American Society of Cinematographers — Apocalypse Now: A Clash of Titans (Storaro)](https://theasc.com/articles/flashback-apocalypse-now)

### Internal cross-references (Hapax Council)

- `docs/research/2026-04-20-nebulous-scrim-design.md` — Pt. 1, the substrate doc
- `docs/research/2026-04-19-gem-ward-design.md` — Pt. 2 (gem-ward depth roles)
- `docs/research/2026-04-19-hardm-redesign.md` — anti-anthropomorphization invariant lineage
- `docs/research/2026-04-20-chat-keywords-ward-design.md` — Pt. 3 (chat-driven scrim density modulation)
- `docs/superpowers/specs/2026-04-18-homage-framework-design.md` — HOMAGE master spec
- `agents/reverie/_uniforms.py`, `agents/reverie/_graph_builder.py` — 8-pass vocabulary canonical
- `agents/shaders/nodes/{drift,breathing,feedback,postprocess,displacement_map,chromatic_aberration,colorgrade,bloom,echo}.wgsl` — node set referenced throughout
- `agents/studio_compositor/cairo_source.py` — `CairoSourceRunner` extension point
- `agents/studio_compositor/compositional_consumer.py` — composite-time integration point
- `shared/compositor_model.py` — `Source`/`Surface`/`Assignment`/`Layout` data model

---

End of Pt. 4. Pt. 5 (if commissioned) would be: programme→scrim_profile state machine specification + structural-director intent vocabulary for `scrim.pierce` / `scrim.deepen` / `scrim.thin`.
