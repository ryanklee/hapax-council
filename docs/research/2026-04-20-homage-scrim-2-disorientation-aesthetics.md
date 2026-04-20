# HOMAGE / Scrim 2 — Disorientation as a Design Principle

**Status:** Research / aesthetic foundations, operator-directed 2026-04-20.
**Author:** cascade (Claude Opus 4.7, 1M).
**Governing anchors:** HOMAGE framework (`docs/superpowers/specs/2026-04-18-homage-framework-design.md`), Nebulous Scrim design (`docs/research/2026-04-20-nebulous-scrim-design.md`), Logos design language (`docs/logos-design-language.md`), Phase A6 substrate invariant.
**Related prior art / memory:** `project_hardm_anti_anthropomorphization`, `project_livestream_is_research`, `project_reverie`, `project_reverie_adaptive`, `feedback_grounding_exhaustive`, `project_720p_commitment`, `project_overlay_content`.
**Scope:** Theoretical foundation and concrete-technique catalogue for ward behaviour inside the Nebulous Scrim. No code. Inputs to downstream PRs in HOMAGE Wave B/C/D.

> "Somewhat disoriented, like everything else in this system."
> — operator, 2026-04-20

---

## 1. TL;DR

This document grounds a single design instinct: **HOMAGE wards inside the Nebulous Scrim must be somewhat disorienting, in the way that the rest of this system is somewhat disorienting** — not as ornament, not as transgression, but as the system's *characteristic relation to perception*. The aim is not unease; the aim is **defamiliarisation that re-recruits attention** so that the studio, the music, and Hapax's hailing voice are *more* present, not less.

### 1.1 Theoretical frame

Disorientation in this codebase is in the lineage of:

- **Russian Formalist *ostranenie*** (Shklovsky, 1917): art makes the stone *stony* by making it strange; habit deadens; estrangement is the *return* of perception, not its negation. ([Defamiliarization — literariness.org](https://literariness.org/2016/03/17/defamiliarization/); [Stanford — *Beyond Language: Viktor Shklovsky, Estrangement*](https://stacks.stanford.edu/file/druid:wk536ws4497/Beyond%20Language%20\(final\)-augmented.pdf).)
- **Brechtian *Verfremdungseffekt*** (Brecht, 1949 *Short Organum*): the audience is held *just outside* identification, so that what is shown can be *thought about* rather than disappeared into. ([*A Short Organum for the Theatre* — critical reading](https://media.neliti.com/media/publications/632827-brechts-theatre-for-the-scientific-age-a-f62b5223.pdf); [Distancing effect — Wikipedia](https://en.wikipedia.org/wiki/Distancing_effect).)
- **Surrealist *dépaysement*** (Breton): displacement of the object from its expected ground reveals it. ([Surrealism — TheArtStory](https://www.theartstory.org/movement/surrealism/).)
- **Hauntology** (Derrida via Mark Fisher, *Ghosts of My Life*, 2014): the present held by traces of futures that did not arrive — texture as memory, decay as content. ([*Ghosts of My Life* — Internet Archive](https://archive.org/details/ghostsofmylifewr0000fish); [Hauntology (music) — Wikipedia](https://en.wikipedia.org/wiki/Hauntology_\(music\)).)
- **The Lynchian uncanny**: the dream-logic that is almost-rational and slightly wrong; not horror, not safety, the *threshold*. (Twin Peaks: The Return Part 8 as the load-bearing reference. [Slate — Part 8 review](https://slate.com/culture/2017/06/twin-peaks-part-8-is-one-of-the-most-radical-hours-of-tv-ever.html); [Offscreen — Western, Sci-Fi and the BIG BOMB](https://offscreen.com/view/twin-peaks-the-return-part-8-the-western-science-fiction-and-big-bomb).)
- **Tarkovskian time-sculpting** (Tarkovsky, *Sculpting in Time*; Stalker's Zone): time as the medium of cinema; slowness as a perceptual instrument. ([Offscreen — Temporal Defamiliarization in Stalker](https://offscreen.com/view/temporal_defamiliarization).)
- **Predictive processing** (Friston, 2010): perception is prediction; well-calibrated *prediction-error* (surprise the system can metabolise) drives engagement; runaway error is anxiety. ([Friston — *The free-energy principle: a unified brain theory?* — Nature Reviews Neuroscience](https://www.nature.com/articles/nrn2787).)

### 1.2 The operator's distinctive position

The operator runs a livestream that is **a public research apparatus, not entertainment** (`project_livestream_is_research`). The aesthetic lineage is BitchX raster + Vitruvian Man + halftone shaders + granular sonic palette + glitch + hip-hop / jazz / soul / electronic / vaporwave / hauntology / lo-fi / beat-scene. Disorientation here is not adolescent transgression and not pastiche; it is a *grammar shared by the whole system* — voice latency, ground panel cycling, content rotation, Reverie's drift, the substrate-invariant cyan ground. The wards must speak that grammar, **in support of the studio**, never about themselves.

Crucially: the **anti-anthropomorphization HARD invariant** (`project_hardm_anti_anthropomorphization`) refuses face-iconography. A "disoriented face" is still a face. Therefore disorientation here works only on **patterns, time, surfaces, and substrates** — never on agents, characters, or expressions.

### 1.3 The five most-applicable techniques (out of §8's catalogue)

For ward authors who only have time to internalise five gestures:

1. **Sub-perceptual drift** — a ward is not exactly where it was a beat ago. Below the threshold of detection-on-arrival; only noticed on return-of-eye.
2. **Time displacement (the "memory" effect)** — a ward shows a delayed version of recent state. The scrim has lag; the lag is felt.
3. **Edge dissolve** — the ward's boundary is uncertain. A 6–12 px feathered alpha gradient with low-frequency noise modulation.
4. **Spectral skew** — small hue separation between content and frame, as if the scrim refracts colour by a few degrees.
5. **Inconsistent persistence** — most wards leave no trail, occasionally one does. The asymmetry is the message: "the rules are *almost* consistent."

These five do nearly everything required: they are cheap, they compose, they all defer to anti-anthropomorphization, and they all *deepen* the scrim metaphor rather than fight it.

---

## 2. Theoretical Paradigms

### 2.1 Russian Formalism — *ostranenie* / "art as device"

Shklovsky's 1917 essay *Art as Device* (or *Art as Technique* in the Lemon/Reis translation) set out the principle that defines almost the entire downstream tradition this document draws on. The argument is simple and severe:

> "Habituation devours objects, clothes, furniture, one's wife, and the fear of war. […] And so, in order to return sensation to our limbs, in order to make us feel objects, to make a stone feel stony, man has been given the tool of art. The purpose of art is to lead us to a knowledge of a thing through the organ of sight instead of recognition." ([Wikipedia — Defamiliarization](https://en.wikipedia.org/wiki/Defamiliarization); [literariness.org — Defamiliarization](https://literariness.org/2016/03/17/defamiliarization/).)

Three things to take from this:

- **Disorientation is a *return* of perception, not a removal of it.** The point is to recover the stone's stoniness. A ward that disorients should make the studio behind it *more* visible-as-itself, not less.
- **Estrangement is a *device*, not a mood.** It is constructed, applied, and removable. Wards must be authored with a specific disorienting move in mind, named, parameterisable, and decomposable — composability is already a system-wide constraint (`feedback_composites_as_sources`).
- **The frame of reference is the *automatised*.** What the audience already takes for granted — a label is a label, a counter counts up, a frame stays still — is the surface against which estrangement reads. A ward that violates a not-yet-established expectation does not read as estrangement; it reads as noise.

The OPOYAZ context (Shklovsky, Eikhenbaum, Tynyanov) further insists that the *device* is what literature studies, not the content. ([NYU — *The Politics of Estrangement*](https://as.nyu.edu/content/dam/nyu-as/faculty/documents/estrangement.pdf).) Translated to ward design: catalogue and govern the *devices* (drift, dissolve, displacement) — not the *contents* (album art, captions, gem ward) — because the devices are what carry the system's voice.

### 2.2 Brecht — the *Verfremdungseffekt*

Brecht's *Short Organum for the Theatre* (1949) crystallised a project that began in the 1920s: theatre that *prevents the spectator from disappearing into illusion*, so that the social conditions presented on stage remain available for *thought*. Devices include episodic dramaturgy, didactic song, the *Gestus*, the actor showing-the-character-rather-than-being-them, and the famous *Verfremdungseffekt* — variously translated alienation effect, distancing effect, "making strange." ([Britannica — alienation effect](https://www.britannica.com/art/alienation-effect); [*A Short Organum* — critical reading](https://media.neliti.com/media/publications/632827-brechts-theatre-for-the-scientific-age-a-f62b5223.pdf).)

Brecht is the right reference for the livestream's posture because:

- The livestream is **a research instrument that the audience is welcomed to witness**, not a fiction the audience is invited to dissolve into. The scrim metaphor (the audience is "over here," the studio "over there," with thickness between) is structurally Brechtian.
- Brecht's distancing is **anti-cathartic, not anti-affective**. Audiences feel; they just are not allowed to drown. The HOMAGE wards similarly should hold an *acknowledged distance* — colourful, alive, present — without inviting the viewer to mistake the scrim for a window into a fiction.
- Brecht insists on *exposing the apparatus*. Visible scaffolding, named devices, the show showing itself. Eliasson explicitly cites this lineage when describing The Weather Project: the structure and machinery of the installation are deliberately exposed to the viewer. ([Tate — How Eliasson is changing our perceptions](https://www.tate.org.uk/art/artists/olafur-eliasson-5239/yes-but-why-olafur-eliasson).) The wards should never *deceive* — disorientation that pretends to be invisible is propaganda, not art.

### 2.3 Surrealism — *dépaysement*

Breton's *dépaysement* — literally "un-countrying," removal-from-the-familiar — is the surrealist hinge. The object is taken out of its expected ground and placed into another, and the strangeness so produced is generative. ([TheArtStory — Surrealism](https://www.theartstory.org/movement/surrealism/); [InMaterial — Surrealism and the dream (José Jiménez)](http://www.inmaterial.com/jjimenez/sysen.htm).)

For wards: the *grounding* a ward arrives from is part of the disorientation. A counter that suddenly appears as a halftoned veil-fragment in the lower-third *re-grounds* the counting-act. The counting is no longer journalistic; it is *uncountrified*. This is structurally identical to the substrate-invariant cyan ground of Phase A6 — a ward that arrives onto the scrim is *already* dépaysé by virtue of arriving onto a fabric rather than onto the bare camera feed.

### 2.4 The uncanny — Jentsch and Freud

Jentsch (1906) located the uncanny in *intellectual uncertainty* — the most successful storytelling device for uncanny effect is to leave the reader unsure whether a figure is human or automaton, animate or not. Freud (1919) accepts the data and supplies a different mechanism: the uncanny is *the familiar* (heimlich) returning under a pressure that has rendered it strange (un-heimlich = "un-homely"). ([Freud — The Uncanny notes](https://courses.washington.edu/freudlit/Uncanny.Notes.html); [TheCollector — Unpacking Freud's Concept of "The Uncanny"](https://www.thecollector.com/uncanny-sigmund-freud/); [Freud and Jentsch read Hoffmann's Uncanny Automata — Academia.edu](https://www.academia.edu/110509279/Freud_and_Jentsch_read_Hoffmann_s_Uncanny_Automata).)

The Freud/Jentsch ground is *constitutive* of the anti-anthropomorphization invariant. The HARDM principle refuses face-iconography precisely because **the uncanny lives most powerfully in the human-shaped**, and the system's posture is *not* to mobilise that. Hapax-disorientation lives one step back from the face: in patterns, in time, in surfaces. The thing the audience can never quite be sure of is *the substrate*, not *the agent*.

### 2.5 Lynchian unease — dream-logic that is almost-rational

David Lynch's signature is not horror and not surrealism in the orthodox Breton sense; it is a *dream-logic that obeys most of waking-life's rules and breaks one or two*. Twin Peaks: The Return Part 8 — the Trinity-test sequence scored to Penderecki's *Threnody to the Victims of Hiroshima* — is the canonical demonstration. Black-and-white, thirty-minute origin-of-evil hallucination, almost-no-dialogue, the camera entering the mushroom cloud. Mark Frost on the original conception: "The idea, obviously — or, well, not obviously — was that we'd never done anything close to what you might describe as a Twin Peaks origin story… in David's hands, it could run as long as 10 or 12 minutes, and it would be riveting." ([Wikipedia — Part 8](https://en.wikipedia.org/wiki/Part_8_\(Twin_Peaks\)); [Slate — radical hours of TV](https://slate.com/culture/2017/06/twin-peaks-part-8-is-one-of-the-most-radical-hours-of-tv-ever.html); [Quod.lib — The Atomic Gambit of Twin Peaks: The Return](https://quod.lib.umich.edu/f/fc/13761232.0041.324/--atomic-gambit-of-twin-peaks-the-return?rgn=main%3Bview%3Dfulltext).)

What is takeable for the wards:

- **Almost-correct timing.** A ward that times itself to the bar will read as locked. A ward that times itself to the bar minus 30 ms will read as *almost-locked* — Lynchian. (Compare the contact-mic-driven beat-locked rotations in `project_contact_mic_wired`; the design choice is whether to lock to the grid or to the *almost*-grid.)
- **Almost-correct colour.** A ward whose hue is exactly the substrate cyan reads as part of the scrim. A ward whose hue is the substrate cyan rotated 8° reads as *visiting* the scrim from somewhere else. Spectral skew (§8.5) is exactly this device.
- **Almost-correct geometry.** A rectangle that is exactly axis-aligned reads as a panel. A rectangle that is 0.4° off-axis reads as a panel that *was hung*.

### 2.6 Tarkovsky — sculpting in time, the Zone as substrate

Tarkovsky defined the director's work as "sculpting in time" — removing from a lump of time everything that is not integral, just as a sculptor removes marble. ([TakeOne — Tarkovsky: Sculpting in Time](https://takeonecinema.net/2016/tarkovsky-sculpting-time/); [Senses of Cinema — Cinematic Genius](https://www.theculturium.com/andrei-tarkovsky-cinematic-genius/).) Stalker's Zone is the load-bearing example: a depersonalised space outside conventional spatio-temporality, a "time-image" in Deleuze's sense — non-chronological, no linear action-reaction, no definitive past/present/future. ([Offscreen — Temporal Defamiliarization in Stalker](https://offscreen.com/view/temporal_defamiliarization).)

The Tarkovskian instruction for ward design is:

- **Slowness is a perceptual instrument, not a pacing failure.** A ward that stays for 90 seconds at a sub-perceptual drift rate is *doing more perceptual work* than a ward that flashes in and out at the bar. The livestream is long-form; the wards should respect that scale.
- **The substrate has its own time.** Reverie's reaction-diffusion node and the glfeedback ping-pong FBO produce slow temporal evolution that already operates in the Tarkovskian register. Wards should *defer* to that timescale rather than fight it.

### 2.7 Hauntology — Mark Fisher

Mark Fisher's *Ghosts of My Life: Writings on Depression, Hauntology and Lost Futures* (Zero Books, 2014) is the load-bearing text for the operator's whole adjacent musical world. Fisher (and Simon Reynolds) named hauntology in music to refer to the work of Burial, the Caretaker, William Basinski, Philip Jeck, the Ghost Box label artists; key forerunners are Boards of Canada. The unifying figure is *the present haunted by traces of futures that did not arrive*. ([*Ghosts of My Life* — Internet Archive](https://archive.org/details/ghostsofmylifewr0000fish); [xenogothic — Introduction to Mark Fisher's *Ghosts of My Life*](https://xenogothic.com/2025/04/02/introduction-to-mark-fishers-ghosts-of-my-life/); [Hauntology (music) — Wikipedia](https://en.wikipedia.org/wiki/Hauntology_\(music\)).)

For the wards specifically, hauntology supplies a *vocabulary of texture-as-content*:

- Crackle, hiss, vinyl-pop as load-bearing meaning, not as artefact.
- Wow-and-flutter pitch wobble as *evidence of a medium*.
- The half-remembered as the right register: not amnesia, not memory, the threshold.

The scrim metaphor and hauntology converge: both insist that the medium is felt, that the medium has a *thickness*, that what comes through it has *passed through* something with its own properties. Wards should sit comfortably inside this register — as if printed onto the scrim, as if remembered through it.

---

## 3. Cinematic References — the watch list

Each entry below is selected for *one specific disorienting move* applicable to ward design. The watch-this-week shortlist (5) is at the end.

- **David Lynch, *Twin Peaks: The Return* (2017), esp. Part 8** — the Trinity hallucination as the gold standard for almost-rational image-time. Part 8's ten-minute slow zoom into the mushroom cloud is the strongest extant demonstration that *duration itself* can be a defamiliarising device. Penderecki's *Threnody* underscoring the sequence exemplifies the texture-as-content rule. ([Wikipedia](https://en.wikipedia.org/wiki/Part_8_\(Twin_Peaks\)); [Slate](https://slate.com/culture/2017/06/twin-peaks-part-8-is-one-of-the-most-radical-hours-of-tv-ever.html); [Offscreen](https://offscreen.com/view/twin-peaks-the-return-part-8-the-western-science-fiction-and-big-bomb).)
- **David Lynch, *Inland Empire* (2006)** — DV camera disorientation, recursive narrative, faces in the wrong rooms. The *threshold* aesthetic at film-length.
- **Andrei Tarkovsky, *Stalker* (1979)** — the Zone as substrate, slow lateral tracking, the dream-logic of place. Average shot length deliberately long; time is the protagonist. ([Offscreen](https://offscreen.com/view/temporal_defamiliarization); [Film Inquiry — Sculptures in Time Pt V: Tarkovsky's STALKER](https://www.filminquiry.com/sculptures-time-pt-v-tarkovskys-stalker/).)
- **Andrei Tarkovsky, *Solaris* (1972)** — the planet as a defamiliarising mirror; the long Bach-organ-and-Bruegel sequence as a perceptual reset.
- **Béla Tarr, *Werckmeister Harmonies* (2000)** — 39 shots in 145 minutes; the average shot length of nearly four minutes is itself the device. ([BFI — Béla Tarr on Sátántangó at 30](https://www.bfi.org.uk/interviews/bela-tarr-satantango-werckmeister-harmonies); [Wikipedia — Béla Tarr](https://en.wikipedia.org/wiki/B%C3%A9la_Tarr).)
- **Béla Tarr, *Sátántangó* (1994)** — 7.5 hours, ~172 shots, average shot length ~152 seconds. The most extended pure demonstration that *duration* is a perceptual instrument. ([Michigan Quarterly Review — Béla Tarr's *Sátántangó*](https://sites.lsa.umich.edu/mqr/2013/07/bela-tarrs-satantango/).)
- **Apichatpong Weerasethakul, *Uncle Boonmee Who Can Recall His Past Lives* (2010)** — slow cinema as a mode of *meditative* spectatorship, ghosts as natural occupants, animism as compositional logic. Palme d'Or 2010. ([Senses of Cinema](https://www.sensesofcinema.com/2020/cteq/uncle-boonmee-who-can-recall-his-past-lives-apichatpong-weerasethakul-2010/); [Wikipedia](https://en.wikipedia.org/wiki/Uncle_Boonmee_Who_Can_Recall_His_Past_Lives).)
- **Maya Deren, *Meshes of the Afternoon* (1943)** — the canonical "trance film." Multiple exposure, jump-cutting, slow-motion, point-of-view recursion. Disoriented timeline as *first-person interiority*. ([Wikipedia — Meshes of the Afternoon](https://en.wikipedia.org/wiki/Meshes_of_the_Afternoon); [MoMA collection record](https://www.moma.org/collection/works/299942).)
- **Stan Brakhage, *Mothlight* (1963)** — moth wings and plant matter pressed between Mylar tape, contact-printed; cameraless cinema. The *substrate-as-content* rule at its purest. ([Wikipedia — Mothlight](https://en.wikipedia.org/wiki/Mothlight); [Artforum — J. Hoberman on Brakhage's Mothlight](https://www.artforum.com/features/j-hoberman-on-stan-brakhages-mothlight-200839/).)
- **Stanley Kubrick & Douglas Trumbull, *2001: A Space Odyssey* (1968), Stargate sequence** — slit-scan as *time-smeared surface*; foreground and background are the same material at different time-offsets.
- **Vittorio Storaro / Francis Ford Coppola, *Apocalypse Now* (1979)** — coloured smoke as *substrate* not weather. Cited in `2026-04-20-nebulous-scrim-design.md` §2.2.

### 3.1 Watch-this-week (5)

In this order, for one operator week:

1. **Twin Peaks: The Return, Part 8** (~58 min). One sitting. Pay attention to how Lynch *holds* on the still image past comfort — that holding is the device.
2. **Stalker** (~163 min). One sitting if possible. Notice the camera's lateral tracks across walls and water; the Zone reading itself.
3. **Meshes of the Afternoon** (~14 min). Watch three times back-to-back. Each pass surfaces a different recursive logic.
4. **Mothlight** (~4 min). Watch five times. This is the operator's substrate-pedagogy in four minutes.
5. **Werckmeister Harmonies, opening sequence — the bar dance / cosmic demonstration** (~10 min). Single shot, choreographed; the rotation and slowness are the technique.

---

## 4. Musical References — already in the operator's DNA

The operator's adjacent musical world is the densest concentration of working disorientation-as-aesthetic in any medium. Each entry below is paired with the *device* it operationalises.

- **Burial, *Untrue* (2007, Hyperdub).** Pitch-bent vocals as architecture; rain, fire, vinyl crackle as *constitutive texture*; the "loneliest prayer in the world" as call-and-response with nowhere to go. Burial in interview: "a plethora of voices wrapped around nothing but itself, a kind of architecture and a schizophrenia at once, pitches shifting, layers in the mix held out like staircases that disappear as soon as you put a foot down." ([The Wire — Burial unedited transcript](https://www.thewire.co.uk/in-writing/interviews/burial_unedited-transcript); [Cyclic Defrost — Burial: "Tunes for the last party on earth"](https://www.cyclicdefrost.com/2007/11/burial-interview-by-emmy-hennings/); [newcritique.co.uk — Like a Ghost Touched Your Heart: Burial's Sonic Hauntology](https://newcritique.co.uk/2021/04/16/essay-like-a-ghost-touched-your-heart-burials-sonic-hauntology-edward-campbell-rowntree/).) **Device for wards: ambient texture as *substrate-of-substrate* — wards float on a fabric that itself rains, hisses, sighs.**
- **The Caretaker (Leyland Kirby), *Everywhere at the End of Time* (2016–19, six volumes).** Six albums, released six months apart, mapping the stages of dementia through degraded 1920s–30s ballroom samples. "I've given the whole project dementia." ([Wikipedia](https://en.wikipedia.org/wiki/Everywhere_at_the_End_of_Time); [The Believer — The Process: The Caretaker](https://www.thebeliever.net/logger/the-process-the-caretaker/).) **Device for wards: progressive degradation as a long-form arc; the substrate decays at human-perceptible scales.**
- **William Basinski, *The Disintegration Loops* (2002–03).** Magnetic-oxide flake-off captured in the act of digitisation. The recording *is the recording's death*. ([Wikipedia](https://en.wikipedia.org/wiki/The_Disintegration_Loops); [Crack Magazine — How Basinski's masterpiece captured a world crumbling around us in slow motion](https://crackmagazine.net/article/long-reads/how-william-basinskis-masterpiece-the-disintegration-loops-captured-a-world-crumbling-around-us-in-slow-motion/); [Median (NMC) — Archival Time, Absent Time](http://median.newmediacaucus.org/the_aesthetics_of_erasure/the-disintegration-loops/).) **Device: aesthetic value lives in the *process of failure*. A ward that decays gracefully is more honest than a ward that cuts.**
- **Boards of Canada, *Music Has the Right to Children* (1998, Warp).** Detuned vintage synths, deliberately failing tape recorders, "wavering off-pitch synths, redolent of the music on TV programs from my '70s childhood" (Simon Reynolds). ([PopMatters — *The Fragmented Quality of Boards of Canada's MHTRTC*](https://www.popmatters.com/boards-canada-music-children-atr); [Stereogum — *Music Has The Right To Children* Turns 20](https://www.stereogum.com/1992284/music-has-the-right-to-children-turns-20/reviews/the-anniversary/); [Treblezine 100, no. 60](https://www.treblezine.com/treble-100-no-60-boards-of-canada-music-has-the-right-to-children/).) **Device: micro-detune. A ward whose colour or geometry is 1–2% off-true is not an error — it is a *medium reveal*.**
- **DJ Screw — chopped & screwed (Houston, 1990s).** Pitch-down + tempo-down + chops. "By slowing down tracks and introducing irregular cuts, he altered the temporal structure of songs, creating a sense of space and weight that contrasted with the faster tempos dominating the genre." ([Wikipedia — Chopped and screwed](https://en.wikipedia.org/wiki/Chopped_and_screwed); [University of Houston — Keeping DJ Screw's Memory Alive](https://stories.uh.edu/dj-screw/index.html).) **Device: temporal dilation as the transformation. The wards' Mode-D / granular-wash mode should respect this lineage explicitly.**
- **Madlib / Quasimoto.** Lord Quas's high voice produced by *slowing the recorder, rapping slow, speeding back up* — analog pitch-shift as a method, not a digital effect. ([The Quietus — *The Strange World of… Madlib*](https://thequietus.com/articles/26665-madlib-madvillain-quasimoto-review).) **Device: micro-disorientation baked into the groove. A ward should be *of* the beat, not interrupting it.**
- **Oneohtrix Point Never, *Replica* (2011, Mexican Summer).** Sample-based; 1980s–90s TV ad sources reconstituted as glitchy ambient art-pop. A foundational text for hypnagogic pop and the precursor to vaporwave. ([Wikipedia](https://en.wikipedia.org/wiki/Replica_\(Oneohtrix_Point_Never_album\)); [Red Bull Music Academy — OPN lecture](https://www.redbullmusicacademy.com/lectures/oneohtrix-point-never-replication/).) **Device: granular reconstitution of *recognisable* sources as alien material.**
- **Vaporwave — *Floral Shoppe* (Macintosh Plus / Vektroid, 2011), *Eccojams Vol. 1* (Chuck Person / Lopatin, 2010), *Far Side Virtual* (James Ferraro, 2011).** Slowed corporate muzak, mall-air, Y2K detritus reframed as *the memory of a future that never arrived*. ([Wikipedia — Vaporwave](https://en.wikipedia.org/wiki/Vaporwave); [Wikipedia — Floral Shoppe](https://en.wikipedia.org/wiki/Floral_Shoppe); [CCCB Lab — Vaporwave: The Musical Wallpaper of Lost Futures](https://lab.cccb.org/en/vaporwave-the-musical-wallpaper-of-lost-futures/).) **Device: defamiliarisation of the over-familiar. The ground material is *known*; what's strange is its *condition*.**

### 4.1 Listen-this-week (5)

For one operator week, on the studio monitors, while working:

1. **Burial — *Untrue* (2007).** Whole album, in order. Listen *for the rain* — the rain is the substrate, the songs sit on top.
2. **The Caretaker — *Everywhere at the End of Time, Stage 1* (2016).** Just stage 1 first. Then, if the operator wants, stage 4 next week. (Stage 6 only after preparation.)
3. **William Basinski — *Disintegration Loop 1.1*** (~63 min). One sitting. Notice the moment the loop becomes *less* than itself.
4. **Boards of Canada — *Music Has the Right to Children* (1998).** Whole album. Pay attention to the wow-and-flutter; the medium is audible.
5. **Oneohtrix Point Never — *Replica* (2011).** Whole album. Notice how the source materials are *almost* recognisable.

---

## 5. Visual-Art References — the installation tradition

- **James Turrell — Ganzfeld pieces, Skyspaces, the Roden Crater.** Fills the entire visual field with a single colour; produces "prisoner's cinema" hallucinations after sustained viewing. Turrell's BA was in perceptual psychology (Pomona, 1965), specifically including the Ganzfeld effect. He aims at *seeing yourself see*. ([Design Is This — James Turrell: Ganzfeld](https://www.designisthis.com/us/blog/post/james-turrell-ganzfeld); [The Offing — The Ganzfeld Effect](https://theoffingmag.com/art/the-ganzfeld-effect/).) **Lesson for wards: a *single* uninterrupted surface is itself a perceptual instrument; the substrate-invariant cyan ground is already a low-Ganzfeld move.**
- **Olafur Eliasson — *The Weather Project* (Tate Modern Turbine Hall, 2003).** Semi-circular screen, mirrored ceiling, artificial mist, monochrome amber sun. Eliasson on the work: viewers experience *seeing yourself sensing*. The structure and machinery are deliberately exposed. ([Studio Olafur Eliasson — The weather project](https://olafureliasson.net/artwork/the-weather-project-2003/); [Tate Modern — Unilever Series](https://www.tate.org.uk/whats-on/tate-modern/unilever-series/unilever-series-olafur-eliasson-weather-project); [Tate — How Eliasson is changing our perceptions](https://www.tate.org.uk/art/artists/olafur-eliasson-5239/yes-but-why-olafur-eliasson).) **Lesson: monochrome at scale + visible apparatus + atmospheric mediation = phenomenological surface. The Hapax livestream's whole composite is structurally an Eliasson piece.**
- **Yayoi Kusama — *Infinity Mirror Rooms* (1965–present).** Mirror, light, polka-dot recursion; ego dissolution as constitutive aim. Kusama's *self-obliteration* philosophy. ([Hirshhorn — Infinity Mirror Rooms](https://hirshhorn.si.edu/kusama/infinity-rooms/); [Juxtapoz — Yayoi Kusama: Infinity Mirror Rooms](https://www.juxtapoz.com/news/magazine/yayoi-kusama-infinity-mirror-rooms/).) **Lesson: pattern recursion at the right scale dissolves figure/ground. Used badly, it is a selfie machine; used well, it is the most direct route to perceptual disorientation in any medium. (Note: Kusama is the limit-case for the anti-anthropomorphization invariant — her work *is* about the body in space. Hapax intentionally takes the *pattern* and refuses *the body*.)**
- **Bridget Riley / Victor Vasarely — Op Art (1960s–).** Geometric repetition tuned to the visual cortex's response to high-contrast spatial frequencies; produces apparent motion in static works. Riley's signature device is *perceptual colour* — colour generated by adjacency rather than pigment. ([TheCollector — Bridget Riley](https://www.thecollector.com/bridget-riley-op-art-optical-illusions/); [Britannica — Bridget Riley](https://www.britannica.com/biography/Bridget-Riley); [Art UK — Bridget Riley and Op Art](https://artuk.org/learn/learning-resources/bridget-riley-and-op-art).) **Lesson: pattern can produce motion that is not present. Useful for wards that want to seem *alive* without animating. Caution: Op-Art-grade contrast triggers vestibular disorientation in some viewers; calibrate (§9).**
- **Brion Gysin & William S. Burroughs — the cut-up technique (1959–).** Gysin discovers it slicing newspaper-mounts; Burroughs takes it as a tool to expose what he sees as the manipulative structure of language. *The Third Mind* (1977). ([Wikipedia — Cut-up technique](https://en.wikipedia.org/wiki/Cut-up_technique); [UbuWeb — The Cut-Up Method of Brion Gysin (Burroughs)](https://www.ubu.com/papers/burroughs_gysin.html); [Brion Gysin — Cut-ups](https://www.briongysin.com/cut-ups/).) **Lesson: juxtaposition of sources from incompatible registers reveals the *structure* of each. The HOMAGE wards' practice of placing album-art adjacent to a Vitruvian Man adjacent to a halftoned counter is a literal cut-up.**

---

## 6. Glitch-Aesthetic Precedents

- **Rosa Menkman — *The Glitch Studies Manifesto* (2010/11).** The manifesto's argument: "the dominant, continuing search for a noiseless channel has been — and will always be — no more than a regrettable, ill-fated dogma." Glitch = "disintegration" and is the flipside of synthesis; "there is no knowledge without nonsense, there is no familiarity without the uncanny and there is no order without chaos." ([Rhizome — Glitch Studies Manifesto](https://rhizome.org/editorial/2011/jul/28/glitch-studies-manifesto-rosa-menkman/); [Network Cultures — *The Glitch Moment(um)*](https://networkcultures.org/_uploads/NN%234_RosaMenkman.pdf); [beyondresolution.info — Glitch Studies Manifesto](https://beyondresolution.info/Glitch-Studies-Manifesto).)
- **JODI (Joan Heemskerk and Dirk Paesmans, 1995–).** Seminal net.art duo; intentional layout errors that expose underlying code; the precursor to databending and datamoshing. ([Lisson Gallery — Cory Arcangel and JODI's Feedback Loop](https://www.lissongallery.com/news/cory-arcangel-and-jodi-s-feedback-loop-independent).)
- **Cory Arcangel — *Data Diaries* (2003) and the dead-pixel work.** Technological obsolescence, dead pixels, screen artefacts as subjects. ([Glitch art — Wikipedia](https://en.wikipedia.org/wiki/Glitch_art).)
- **Datamoshing.** Removing I-frames so that a codec applies one scene's motion to another scene's pixels; "fluid, hallucinatory transitions where subjects bleed into each other." ([Glitch art — Wikipedia](https://en.wikipedia.org/wiki/Glitch_art).)
- **Vaporwave / Webcore / Frutiger Aero / Y2K aesthetic resurgence.** Memory of corporate optimism reprocessed as melancholy. ([Vaporwave — Wikipedia](https://en.wikipedia.org/wiki/Vaporwave).)
- **Memphis Group (Ettore Sottsass, Milan, 1980–87).** Productive ugliness as a postmodern programme. "Cheap plastics combined with hardwood, lacquer and brass… mixing high and low, precious and tacky." ([Wikipedia — Memphis Group](https://en.wikipedia.org/wiki/Memphis_Group); [Roseberys — Memphis Group: The Radicals of Post-Modern Design](https://www.roseberys.co.uk/news/memphis-group-the-radicals-of-post-modern-design); [Design Museum — Memphis Group: awful or awesome?](https://designmuseum.org/discover-design/all-stories/memphis-group-awful-or-awesome).)
- **Brutalist web design (revival, 2010s–).** Unstyled HTML, system fonts, default browser chrome embraced as honesty.

The throughline across all six is: **the medium's failure-modes are content-bearing, and refusing them is a form of dishonesty.** This is the right moral frame for the HOMAGE wards. The scrim's seams should be visible; the medium should be felt.

---

## 7. Cognitive Science of Disorientation — when it works, when it harms

### 7.1 Predictive processing — surprise as recruitment, surprise as anxiety

Karl Friston's free-energy principle holds that the brain is a *prediction machine* that constantly generates hypotheses about the causes of its sensory inputs and updates them via prediction error. Systems pursue *paths of least surprise* — minimising the difference between prediction and sensory data. ([Friston — *The free-energy principle: a unified brain theory?* — Nature Reviews Neuroscience](https://www.nature.com/articles/nrn2787); [PMC — Predictive coding under the free-energy principle](https://pmc.ncbi.nlm.nih.gov/articles/PMC2666703/); [OECS — The Free Energy Principle](https://oecs.mit.edu/pub/my8vpqih).)

Translated to ward design:

- **Useful disorientation = *metabolisable* prediction error.** The ward violates expectation in a way the visual system can resolve, which *recruits* attention onto the violating element. This is the Shklovskian "return of the stone's stoniness" rendered in computational terms.
- **Harmful disorientation = *un*-metabolisable prediction error.** The system cannot reduce the error within working-memory budget. The result is either active aversion (anxiety) or passive disengagement (the viewer looks away).
- **The threshold is not absolute; it is contextual.** A viewer in a meditative state can metabolise more than a viewer who has just opened the stream. The Stimmung-coupling already implemented elsewhere is therefore the right mechanism for ward intensity coupling (§11).

### 7.2 Cognitive load theory — Sweller

Sweller's cognitive load theory (1988–) divides load into *intrinsic* (the inherent difficulty of the material), *extraneous* (overhead from how it's presented), and *germane* (resources spent forming schemas). Working memory has a hard, small capacity. Extraneous load is *the load that should be minimised*. ([Wikipedia — Cognitive load](https://en.wikipedia.org/wiki/Cognitive_load); [Sweller — Cognitive Load Theory and Instructional Design](https://www.uky.edu/~gmswan3/544/Cognitive_Load_&_ID.pdf); [Springer — *Intrinsic and Extraneous Cognitive Load*](https://link.springer.com/chapter/10.1007/978-1-4419-8126-4_5).)

Translated:

- **A disorientation move that does not pay for itself in *what the viewer sees* is extraneous load.** Decorative weirdness is exactly this. It taxes working memory without returning meaning.
- **Stacking more than ~3 simultaneous disorientation moves on the same ward overloads any reasonable viewer.** The §11 calibration mechanism caps simultaneous moves per ward.
- **Disorientation should be *intrinsic* to the ward — i.e., *part of what the ward is*.** A counter that drifts is *a drifting counter*. A counter with a separately-applied glitch shader is two things being seen at once.

### 7.3 Csikszentmihalyi — flow and the skill–challenge balance

Csikszentmihalyi's flow is the engagement state when perceived challenge matches perceived skill, with clear goals and immediate feedback. Skill > challenge → boredom. Challenge > skill → anxiety. ([Wikipedia — Flow (psychology)](https://en.wikipedia.org/wiki/Flow_\(psychology\)); [Positive Psychology — Mihály Csíkszentmihályi: The Father of Flow](https://positivepsychology.com/mihaly-csikszentmihalyi-father-of-flow/); [Maverick Learning — Flow Theory](https://mlpp.pressbooks.pub/mavlearn/chapter/flow-theory/).)

The audience's "skill" in reading the livestream rises across a session — they learn the wards, they learn the scrim's behaviour, they learn the substrate. Therefore:

- **Disorientation budget should rise across a session**, not stay flat. Opening with peak weirdness is anxiety-producing; opening with low-disorientation that escalates as the audience learns the system is flow-producing.
- **Mode coupling (§11.4)** is the right mechanism: Selector mode (lower-skill demand on viewer; e.g. a new audience member arriving) → low disorientation; Granular-wash mode (higher-skill, audience has settled in) → higher disorientation.

### 7.4 Gibsonian affordance — what disorientation breaks and what it must not

J.J. Gibson's *The Ecological Approach to Visual Perception* (1979) defines an affordance as *what the environment offers the animal* — relational, not absolute. Perception is direct apprehension of actionable properties. ([Wikipedia — Affordance](https://en.wikipedia.org/wiki/Affordance); [Gibson — *The Ecological Approach to Visual Perception* Chapter 8 (Brown)](https://cs.brown.edu/courses/cs137/2017/readings/Gibson-AFF.pdf); [PMC — *The History and Philosophy of Ecological Psychology*](https://pmc.ncbi.nlm.nih.gov/articles/PMC6280920/).)

Translated:

- **Disorientation that disables affordance perception is harmful.** A ward that is so disoriented the viewer cannot tell *what kind of thing it is* (counter? album art? caption?) has destroyed an affordance.
- **Disorientation that *recombines* affordances is generative.** A counter that *also* affords reading-as-substrate-pattern — that is a new affordance, and the viewer's act of reading it is itself the perceptual gain.
- **The substrate (scrim) sets the *dominant* affordance: "look through me."** Wards must not break that. A ward that demands to be read *as* the surface (rather than *on* the surface) violates the metaphor. The five techniques in §1.3 all pass this test; some others in §8 (e.g. doubling, false gravity) need calibration.

---

## 8. Eleven-plus Concrete Techniques Applied to Wards

Each is named, described, paired with an estimated disorientation cost, and tagged with which §2 paradigm it most resembles. All are compatible with the substrate-invariant cyan ground and with the anti-anthropomorphization invariant (no faces, no characters).

### 8.1 Sub-perceptual drift — *Tarkovsky / Lynch*

Ward translates by 0.5–2 px/s along a slow-noise trajectory. Below detection-on-arrival; only noticed when the eye returns to the ward and finds it elsewhere. Cost: low. **Highest-leverage technique in the catalogue.** Compose with everything.

### 8.2 Aspect-ratio breath — *Op Art / Gibson*

Ward scales asymmetrically by 1–3% on a slow sinusoid (~0.05 Hz). Breaks the rectangular-grid expectation; the ward feels *alive without animating*. Cost: low. Avoid stacking with §8.3.

### 8.3 Z-stacking inversion — *Lynch / Surrealism*

A foreground ward briefly slips behind a background ward. Lasts 200–600 ms; resolves. Reads as a *medium fault*, not a glitch. Cost: medium (one viewer in a hundred will feel queasy; budget accordingly). Use sparingly — once or twice per minute at most.

### 8.4 Edge dissolve — *Hauntology / Brakhage*

Ward boundary is a 6–12 px feathered alpha gradient modulated by low-frequency value-noise. The ward is *of* the scrim, not stamped onto it. Cost: low. **Should be on by default for every ward; Wave B work.**

### 8.5 Spectral skew — *Lynch / Boards of Canada (micro-detune)*

The ward's hue rotates 4–10° from the substrate's hue. Reads as if the scrim refracts colour by a few degrees. Cost: low. Composes well with §8.4.

### 8.6 Refraction simulation — *Eliasson / Storaro*

Wards near the scrim's "thicker" regions appear to bend (chromatic aberration + small displacement field). Implementation: sample a low-frequency curl-noise displacement texture, use it to perturb the ward's UVs by 2–6 px before composite. Cost: medium. Couples to Reverie's RD field naturally.

### 8.7 Time-displacement — the "memory" effect — *hauntology / Tarkovsky*

The ward shows a delayed version of its recent state — a 200–800 ms lag, optionally fading. Implementation: ping-pong FBO ring. Cost: medium (memory). **Is the most direct expression of the scrim-as-medium-with-thickness metaphor.** Highest priority after §8.1 and §8.4.

### 8.8 Doubling — *Lynch (the doppelgänger), Deren (multiple exposure)*

A ward briefly appears twice, slightly offset (4–10 px), the duplicate at 30–60% alpha. Lasts 400–1200 ms. Reads as *medium echo*. Cost: medium. **Risk: in concert with the anti-anthropomorphization rule, doubling must never be applied to anything face-shaped or character-shaped.**

### 8.9 False gravity — *Op Art / Surrealism*

Wards drift sideways or upward, never down. Defeats the gravity-prior the visual system supplies for free. Cost: medium (some viewers will read it as broken UX). Mode-couple — only in Mode D / granular-wash.

### 8.10 Inconsistent persistence — *Burial / Caretaker*

Most wards leave no trail. Occasionally one does: a 1–3 second exponential decay echo. The asymmetry is the message — *the rules are almost consistent*. Cost: low. **Excellent low-budget hauntological move.**

### 8.11 Phantom wards — *Freud (the uncanny) / Burial ("voices wrapped around nothing")*

A ward reads as present (frame, edge dissolve, drift) but contains no actual content — only the substrate showing through where the ward "is." Reads as *expectation of meaning, withheld*. Cost: medium (overuse becomes nihilistic). One per programme at most.

### 8.12 — additional techniques

- **Wow-and-flutter pitch on motion** — animation curves that wobble around their nominal trajectory by 1–3% in time, modelled on tape transport. *Boards of Canada.*
- **Halftone breathing** — the halftone screen frequency drifts 5–10% over 30–60 s. *BitchX raster + medium-aware.*
- **Inter-ward temporal coupling** — when ward A appears, ward B in the opposite quadrant *barely* responds (2–3 px shift, 100 ms). Not causation; *resonance*. Reads as *the scrim itself responding*.
- **Substrate bleed** — for 100–300 ms after a ward leaves, the substrate at its former location holds a faint imprint (Reverie's RD already does this for free if wired correctly). *Basinski.*
- **Slow rotation past true** — a ward labelled "horizontal" sits at +0.4° to +0.8°; a ward labelled "vertical" at +0.2° to +0.5°. *Lynch.* Cost: nil.

---

## 9. Where Disorientation Becomes Alienation — red flags

- **Photosensitive seizure risk.** Hard floor: WCAG 2.3.1 — content must not flash more than three times in any one-second period unless flashes are below the general (≥20 cd/m² luminance, ≥3 Hz, ≥0.006 sr area) and red-flash thresholds. AAA stricter (2.3.2) bans any flashing >3 Hz regardless of area. Saturated red has its own special test. ([W3C — Understanding 2.3.1](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html); [MDN — Web accessibility for seizures](https://developer.mozilla.org/en-US/docs/Web/Accessibility/Guides/Seizure_disorders); [WCAG.dock.codes — 2.3.2](https://wcag.dock.codes/documentation/wcag232/).) **Already covered in HOMAGE Wave B's flashing-pattern detector. The detector is the floor; design above it.**
- **Cognitive load spike.** More than ~3 simultaneous disorientation moves on the same ward, or more than ~5 across the whole composite, exceeds working-memory budget for almost any viewer (§7.2). The §11 budget enforces this.
- **Anti-anthropomorphization invariant violation.** A "disoriented" face is still a face. Doubling (§8.8), refraction (§8.6), and time-displacement (§8.7) applied to anything face-shaped (or character-shaped, or eye-shaped, or mouth-shaped) violates the HARDM principle. The substrate is fair game; the anthropomorphic is not.
- **Operator-goal misalignment.** If the operator is using a ward to *communicate* (intro card, mode label, programme title), disorientation should *sharpen* that communication, not blur it. Default: communication-critical wards run on Selector profile (low disorientation, §11.4). Override: opt-in.
- **Audience onboarding fatigue.** A new audience member arriving 30 minutes into the stream needs *less* disorientation than the audience that has been present from the open. The §11 ramp solves this only partially; an open-grace period of low disorientation at the top of every hour is also a defensible move.
- **Selfie-machine drift.** Kusama's late-period reception cautions: any sufficiently spectacular perceptual installation becomes a backdrop for the audience's *own* image. The Hapax livestream is anti-anthropomorphic and so is intrinsically resistant — but a ward that becomes a viral GIF outside the stream's research context *has* slipped. Rare and acceptable; not the design target.
- **Op-Art vestibular induction.** High-contrast geometric patterns at certain spatial frequencies trigger nausea / dizziness in some viewers. Bridget Riley's own work has been documented to affect some viewers physiologically. Calibrate spatial frequencies to avoid the dangerous bands, or restrict to Mode D with explicit operator opt-in. ([Britannica — Bridget Riley](https://www.britannica.com/biography/Bridget-Riley).)

---

## 10. Hapax-Disorientation — the distinctive identity

Many systems are disoriented. Few are *characteristically* disoriented. The Hapax-disorientation profile has four constitutive marks. Wards that satisfy these four read as Hapax; wards that miss any one read as borrowed.

1. **Anti-anthropomorphic.** No characters disoriented; only patterns, time, surfaces. Disorientation operates one rung back from the human-shaped. (HARDM invariant; Freud's uncanny held at arm's length.)
2. **Substrate-grounded.** Disorientation has a *fabric*. The scrim is always present; the ward is always *of* the scrim, not stamped on it. (BitchX raster grammar; Brakhage substrate; Storaro coloured smoke.)
3. **Hip-hop-adjacent.** Disorientation is *of the groove*, not the interruption of it. The right register is Madlib's pitch-shifted Quasimoto, not the dropped-frame skip. Micro-disorientations that *integrate* into the time-feel beat the macro-disruptions.
4. **Research-apparatus posture.** The viewer is a *witness to a process*, not an audience expecting comfort. Brechtian distancing, *not* mystery-cinema illusion. The wards never apologise for being constructed; the apparatus is exposed (Eliasson).

Together these four also *exclude* a great deal of adjacent territory: jump-scare horror (rules out by 4); anime expressivity (rules out by 1); pure ambient prettiness (rules out by 4); hard-glitch transgression (rules out by 3). What remains is a narrow but rich aesthetic position.

---

## 11. Calibration Mechanisms

### 11.1 Disorientation budget per minute

Cap the *count of simultaneous disorientation moves* per composite frame (≤5 across all wards), and the *count of disorientation moves per ward* (≤3 simultaneous). Implementation: a disorientation accountant in the compositor, reading per-ward `disorient` flags and refusing additional moves once budget is exhausted (degrade gracefully — drop the *newest* request, since the in-progress effect is what the viewer is currently parsing).

### 11.2 Ramp-up and ramp-down

- **Stream open**: open the stream at ~30% of full disorientation budget; ramp to 100% over the first 15–25 minutes.
- **Stream close**: ramp down to ~20% over the last 10 minutes; the closing register is *low-disorientation*, so that whatever the operator is communicating at close is unambiguous.
- **Mid-stream re-anchor (e.g. a tracklist title-card)**: drop to ~40% for the duration of the title-card, return to ambient level after.

### 11.3 Operator override — the panic button

A keyboard shortcut (mapping into the existing command-registry, `project_command_registry`) sets disorientation budget to 10% for a configurable window (default 60 s). Use cases: a moment of operator-to-audience communication that must be unambiguous; a mid-stream guest entering the room; a technical issue the operator wants to acknowledge directly.

### 11.4 Programme-mode coupling

Coupling to the modes already specified in `2026-04-20-vinyl-broadcast-mode-b-turntablist-craft.md` and `…-mode-d-granular-instrument.md`:

| Mode | Disorientation profile | Rationale |
|------|------------------------|-----------|
| **Selector** (mode A) | Low (~30%) | The operator is in conversational selector mode; disorientation should not impede the audience's reading of which record / artist is on. |
| **Turntablist** (mode B) | Beat-locked medium (~60%) | The disorientation locks to the bar; matches the rhythmic intensity of the technique. |
| **Continuous mix** (mode C) | Medium (~50%), drifting | The mix has its own continuity; wards should not compete. |
| **Granular-wash** (mode D) | High (~85%) | The aesthetic is itself granular and dilated; wards should be the most disoriented here. |

### 11.5 Stimmung coupling

Reduce disorientation when stimmung activation is high (the system itself is "loud"); raise it when stimmung is low (the system has perceptual headroom to use). This couples ward intensity to the *system's* state, not just to the programme mode — and resolves a class of cases where two perfectly-budgeted moves still feel oppressive because the substrate is itself busy.

### 11.6 Audience-arrival grace

At the top of every wall-clock hour (a proxy for "new audience member likely to be arriving"), drop disorientation to ~50% for 90 seconds. The cost is small; the gain in onboarding is substantial.

---

## 12. Open Questions

- **Is *progressive* decay across a session (Caretaker model) appropriate, or does the livestream re-anchor too often for the arc to land?** Probably re-anchors too often, but a 6-hour DJ set might support a slow degradation ramp. Test in Wave C.
- **Should *some* wards be *exempt* from disorientation entirely?** The status / operational wards (e.g. "stream is recording") arguably should be — Brechtian apparatus-exposure says the *machinery* is named clearly. Default: exempt; explicit opt-in to disorient.
- **What is the right *time-scale* for sub-perceptual drift?** Below 0.5 px/s, viewers mistake it for monitor wobble. Above 2 px/s, they detect it on arrival. Probably 0.8–1.5 px/s, but A/B test on actual stream content in Wave B.
- **Can we *measure* whether disorientation is doing its perceptual work?** Possibly: chat reactions referring to "the visuals" are a positive signal; chat reactions saying "I can't read it" are negative. A simple lexicon-sweep across stream chat could yield a coarse quality signal.
- **Is anything in this document at risk of converting the livestream into an art-installation, away from its research-apparatus posture?** Possibly the Op Art / Kusama branches if pushed too far. Hold the line at *substrate-grounded* and *research-apparatus posture* (constraints 2 and 4 of §10).
- **How does disorientation interact with the consent-channel work?** A consent-critical moment must read as one. The §11.3 panic button is the floor; an automatic drop to ~10% on consent prompts is a further safeguard worth specifying in Wave D.

---

## 13. Sources

### 13.1 Primary theoretical texts and commentaries

1. Viktor Shklovsky, "Art as Device" / "Art as Technique" (1917, in *Theory of Prose*, 1925). [Defamiliarization — Wikipedia](https://en.wikipedia.org/wiki/Defamiliarization).
2. *Defamiliarization* — literariness.org. <https://literariness.org/2016/03/17/defamiliarization/>
3. *Beyond Language: Viktor Shklovsky, Estrangement, and the Politics of Form* — Stanford. <https://stacks.stanford.edu/file/druid:wk536ws4497/Beyond%20Language%20\(final\)-augmented.pdf>
4. *The Politics of Estrangement: Tracking Shklovsky's Device* — NYU. <https://as.nyu.edu/content/dam/nyu-as/faculty/documents/estrangement.pdf>
5. Bertolt Brecht, *A Short Organum for the Theatre* (1949). Critical reading: <https://media.neliti.com/media/publications/632827-brechts-theatre-for-the-scientific-age-a-f62b5223.pdf>
6. *Distancing effect* — Wikipedia. <https://en.wikipedia.org/wiki/Distancing_effect>
7. *Alienation effect* — Britannica. <https://www.britannica.com/art/alienation-effect>
8. *Surrealism* — TheArtStory. <https://www.theartstory.org/movement/surrealism/>
9. André Breton, *Manifestoes of Surrealism*. <https://monoskop.org/images/2/2f/Breton_Andre_Manifestoes_of_Surrealism.pdf>
10. *The Uncanny* notes (Freud), University of Washington. <https://courses.washington.edu/freudlit/Uncanny.Notes.html>
11. *Unpacking Freud's Concept of "The Uncanny"* — TheCollector. <https://www.thecollector.com/uncanny-sigmund-freud/>
12. *Freud and Jentsch read Hoffmann's Uncanny Automata* — Academia.edu. <https://www.academia.edu/110509279/Freud_and_Jentsch_read_Hoffmann_s_Uncanny_Automata>
13. Mark Fisher, *Ghosts of My Life: Writings on Depression, Hauntology and Lost Futures* (Zero Books, 2014). <https://archive.org/details/ghostsofmylifewr0000fish>
14. *Introduction to Mark Fisher's Ghosts of My Life* — xenogothic. <https://xenogothic.com/2025/04/02/introduction-to-mark-fishers-ghosts-of-my-life/>
15. *Hauntology (music)* — Wikipedia. <https://en.wikipedia.org/wiki/Hauntology_\(music\)>
16. Andrei Tarkovsky, *Sculpting in Time* — TakeOne. <https://takeonecinema.net/2016/tarkovsky-sculpting-time/>
17. *Temporal Defamiliarization and Mise-en-Scène in Tarkovsky's Stalker* — Offscreen. <https://offscreen.com/view/temporal_defamiliarization>

### 13.2 Cinematic primary references

18. *Twin Peaks: The Return* Part 8 — Wikipedia. <https://en.wikipedia.org/wiki/Part_8_\(Twin_Peaks\)>
19. *Twin Peaks' Part 8 is one of the most radical hours of TV ever* — Slate. <https://slate.com/culture/2017/06/twin-peaks-part-8-is-one-of-the-most-radical-hours-of-tv-ever.html>
20. *Twin Peaks: The Return, Part 8 — The Western, Science-Fiction and the BIG BOMB* — Offscreen. <https://offscreen.com/view/twin-peaks-the-return-part-8-the-western-science-fiction-and-big-bomb>
21. *The Atomic Gambit of Twin Peaks: The Return* — Quod.lib (Michigan). <https://quod.lib.umich.edu/f/fc/13761232.0041.324/--atomic-gambit-of-twin-peaks-the-return?rgn=main%3Bview%3Dfulltext>
22. Béla Tarr on *Sátántangó* at 30 — BFI interview. <https://www.bfi.org.uk/interviews/bela-tarr-satantango-werckmeister-harmonies>
23. *Béla Tarr's Sátántangó* — Michigan Quarterly Review. <https://sites.lsa.umich.edu/mqr/2013/07/bela-tarrs-satantango/>
24. *Sculptures in Time Pt V: Tarkovsky's STALKER* — Film Inquiry. <https://www.filminquiry.com/sculptures-time-pt-v-tarkovskys-stalker/>
25. *Uncle Boonmee Who Can Recall His Past Lives* — Senses of Cinema. <https://www.sensesofcinema.com/2020/cteq/uncle-boonmee-who-can-recall-his-past-lives-apichatpong-weerasethakul-2010/>
26. *Meshes of the Afternoon* — Wikipedia. <https://en.wikipedia.org/wiki/Meshes_of_the_Afternoon>
27. *Maya Deren, Alexander Hammid. Meshes of the Afternoon. 1943* — MoMA. <https://www.moma.org/collection/works/299942>
28. *Mothlight* — Wikipedia. <https://en.wikipedia.org/wiki/Mothlight>
29. J. Hoberman, "Close-Up: Direct Cinema" (on Brakhage's *Mothlight*) — Artforum. <https://www.artforum.com/features/j-hoberman-on-stan-brakhages-mothlight-200839/>

### 13.3 Musical primary references and criticism

30. *Burial: Unedited Transcript* — The Wire. <https://www.thewire.co.uk/in-writing/interviews/burial_unedited-transcript>
31. *Burial — "Tunes for the last party on earth"* (Emmy Hennings interview) — Cyclic Defrost. <https://www.cyclicdefrost.com/2007/11/burial-interview-by-emmy-hennings/>
32. *Like a Ghost Touched Your Heart: Burial's Sonic Hauntology* — Edward Campbell-Rowntree, NewCritique. <https://newcritique.co.uk/2021/04/16/essay-like-a-ghost-touched-your-heart-burials-sonic-hauntology-edward-campbell-rowntree/>
33. *Everywhere at the End of Time* — Wikipedia. <https://en.wikipedia.org/wiki/Everywhere_at_the_End_of_Time>
34. *The Process: The Caretaker* — The Believer. <https://www.thebeliever.net/logger/the-process-the-caretaker/>
35. *The Disintegration Loops* — Wikipedia. <https://en.wikipedia.org/wiki/The_Disintegration_Loops>
36. *How William Basinski's masterpiece, The Disintegration Loops, captured a world crumbling around us in slow motion* — Crack Magazine. <https://crackmagazine.net/article/long-reads/how-william-basinskis-masterpiece-the-disintegration-loops-captured-a-world-crumbling-around-us-in-slow-motion/>
37. *Archival Time, Absent Time: On William Basinski's The Disintegration Loops* — Median (NMC). <http://median.newmediacaucus.org/the_aesthetics_of_erasure/the-disintegration-loops/>
38. *The Fragmented Quality of Boards of Canada's Music Has the Right to Children* — PopMatters. <https://www.popmatters.com/boards-canada-music-children-atr>
39. *Music Has The Right To Children Turns 20* — Stereogum (Simon Reynolds reflection). <https://www.stereogum.com/1992284/music-has-the-right-to-children-turns-20/reviews/the-anniversary/>
40. *Chopped and screwed* — Wikipedia. <https://en.wikipedia.org/wiki/Chopped_and_screwed>
41. *Keeping DJ Screw's Memory Alive* — University of Houston stories. <https://stories.uh.edu/dj-screw/index.html>
42. *The Strange World of… Madlib* — The Quietus. <https://thequietus.com/articles/26665-madlib-madvillain-quasimoto-review>
43. *Replica (Oneohtrix Point Never album)* — Wikipedia. <https://en.wikipedia.org/wiki/Replica_\(Oneohtrix_Point_Never_album\)>
44. *Oneohtrix Point Never* — Red Bull Music Academy lecture. <https://www.redbullmusicacademy.com/lectures/oneohtrix-point-never-replication/>
45. *Vaporwave* — Wikipedia. <https://en.wikipedia.org/wiki/Vaporwave>
46. *Floral Shoppe* — Wikipedia. <https://en.wikipedia.org/wiki/Floral_Shoppe>
47. *Vaporwave: The Musical Wallpaper of Lost Futures* — CCCB Lab. <https://lab.cccb.org/en/vaporwave-the-musical-wallpaper-of-lost-futures/>

### 13.4 Visual-art primary references

48. *James Turrell: Ganzfeld* — Design Is This. <https://www.designisthis.com/us/blog/post/james-turrell-ganzfeld>
49. *The Ganzfeld Effect* — The Offing. <https://theoffingmag.com/art/the-ganzfeld-effect/>
50. *The weather project* — Studio Olafur Eliasson. <https://olafureliasson.net/artwork/the-weather-project-2003/>
51. *The Unilever Series: Olafur Eliasson: The Weather Project* — Tate Modern. <https://www.tate.org.uk/whats-on/tate-modern/unilever-series/unilever-series-olafur-eliasson-weather-project>
52. *How Eliasson is changing our perceptions* — Tate. <https://www.tate.org.uk/art/artists/olafur-eliasson-5239/yes-but-why-olafur-eliasson>
53. *Infinity Mirror Rooms* — Hirshhorn / Smithsonian. <https://hirshhorn.si.edu/kusama/infinity-rooms/>
54. *Yayoi Kusama: Infinity Mirror Rooms* — Juxtapoz. <https://www.juxtapoz.com/news/magazine/yayoi-kusama-infinity-mirror-rooms/>
55. *Bridget Riley: The Female Artist Who Creates Optical Illusions* — TheCollector. <https://www.thecollector.com/bridget-riley-op-art-optical-illusions/>
56. *Bridget Riley* — Britannica. <https://www.britannica.com/biography/Bridget-Riley>
57. *Bridget Riley and Op Art* — Art UK. <https://artuk.org/learn/learning-resources/bridget-riley-and-op-art>
58. *Cut-up technique* — Wikipedia. <https://en.wikipedia.org/wiki/Cut-up_technique>
59. *The Cut-Up Method of Brion Gysin* (William S. Burroughs) — UbuWeb. <https://www.ubu.com/papers/burroughs_gysin.html>
60. *Cut ups* — Brion Gysin official. <https://www.briongysin.com/cut-ups/>

### 13.5 Glitch and digital aesthetics

61. *Glitch Studies Manifesto* (Rosa Menkman) — Rhizome. <https://rhizome.org/editorial/2011/jul/28/glitch-studies-manifesto-rosa-menkman/>
62. *The Glitch Moment(um)* (Menkman) — Network Cultures. <https://networkcultures.org/_uploads/NN%234_RosaMenkman.pdf>
63. *Glitch Studies Manifesto* — beyondresolution.info. <https://beyondresolution.info/Glitch-Studies-Manifesto>
64. *Glitch art* — Wikipedia. <https://en.wikipedia.org/wiki/Glitch_art>
65. *Cory Arcangel and JODI's Feedback Loop* — Lisson Gallery / Independent. <https://www.lissongallery.com/news/cory-arcangel-and-jodi-s-feedback-loop-independent>
66. *Memphis Group* — Wikipedia. <https://en.wikipedia.org/wiki/Memphis_Group>
67. *Memphis Group: The Radicals of Post-Modern Design* — Roseberys London. <https://www.roseberys.co.uk/news/memphis-group-the-radicals-of-post-modern-design>
68. *Memphis Group: awful or awesome?* — Design Museum. <https://designmuseum.org/discover-design/all-stories/memphis-group-awful-or-awesome>

### 13.6 Cognitive science

69. Karl Friston, *The free-energy principle: a unified brain theory?* — Nature Reviews Neuroscience, 2010. <https://www.nature.com/articles/nrn2787>
70. *Predictive coding under the free-energy principle* — PMC. <https://pmc.ncbi.nlm.nih.gov/articles/PMC2666703/>
71. *The Free Energy Principle* — Open Encyclopedia of Cognitive Science (MIT). <https://oecs.mit.edu/pub/my8vpqih>
72. *Cognitive load* — Wikipedia. <https://en.wikipedia.org/wiki/Cognitive_load>
73. *Cognitive Load Theory and Instructional Design* — Sweller et al. (Univ. of Kentucky). <https://www.uky.edu/~gmswan3/544/Cognitive_Load_&_ID.pdf>
74. *Intrinsic and Extraneous Cognitive Load* — Springer. <https://link.springer.com/chapter/10.1007/978-1-4419-8126-4_5>
75. *Flow (psychology)* — Wikipedia. <https://en.wikipedia.org/wiki/Flow_\(psychology\)>
76. *Mihály Csíkszentmihályi: The Father of Flow* — Positive Psychology. <https://positivepsychology.com/mihaly-csikszentmihalyi-father-of-flow/>
77. *Flow Theory* — Maverick Learning. <https://mlpp.pressbooks.pub/mavlearn/chapter/flow-theory/>
78. *Affordance* — Wikipedia. <https://en.wikipedia.org/wiki/Affordance>
79. J. J. Gibson, *The Ecological Approach to Visual Perception* (1979), Chapter 8. <https://cs.brown.edu/courses/cs137/2017/readings/Gibson-AFF.pdf>
80. *The History and Philosophy of Ecological Psychology* — PMC. <https://pmc.ncbi.nlm.nih.gov/articles/PMC6280920/>

### 13.7 Accessibility and safety

81. *Understanding Success Criterion 2.3.1: Three Flashes or Below Threshold* — W3C / WAI. <https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html>
82. *Web accessibility for seizures and physical reactions* — MDN. <https://developer.mozilla.org/en-US/docs/Web/Accessibility/Guides/Seizure_disorders>
83. *WCAG 2.3.2: Limit flashing to safe thresholds* — wcag.dock.codes. <https://wcag.dock.codes/documentation/wcag232/>
84. *International Guidelines for Photosensitive Epilepsy: Gap Analysis and Recommendations* — PMC. <https://pmc.ncbi.nlm.nih.gov/articles/PMC11872230/>
