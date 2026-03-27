# Visual Attention in Strategy/Management Games: Research for Constrained AI Perception

**Date:** 2026-03-24
**Purpose:** Inform the design of a constrained perception system for an AI fortress governor
by understanding how human eyes and attention actually work when playing games like Dwarf Fortress.

---

## 1. Eye Tracking in Strategy Games

### What the research shows

Eye tracking studies on strategy and competitive games reveal several consistent patterns:

**Fixation metrics.** Fixations in game contexts typically last 200-500ms depending on task
complexity. Any fixation exceeding 1.5 seconds is classified as a "zone out" -- the player has
stopped processing and is likely stuck or overwhelmed. In tile-based puzzle games, studies found
hundreds of fixations per session with distinct distributions between target tiles, distractor
tiles, and edge regions between them (JMIR, 2021).

**Expert vs. novice gaze in StarCraft.** A PLOS ONE study on StarCraft 2 found that expert
players exhibit fundamentally different gaze control than novices:
- Expert gaze covers a significantly larger horizontal area
- Experts have higher saccade percentage and lower fixation percentage (more scanning, less staring)
- Saccade velocity is faster in experts
- Crucially, there was *no significant difference in APM* between skill levels -- expertise is
  about *where you look*, not how fast you click

**Minimap as attention anchor.** In MOBAs and RTS games, the minimap region captures nearly 50%
of expert players' visual attention. Expert StarCraft players make 3.46 minimap interactions
per minute versus 1.22 for novices. The minimap functions as a compressed situational overview
that experts consult reflexively.

**Individually stable patterns.** Eye tracking research on two-player strategic games revealed
"individually heterogeneous-but-stable patterns of visual information acquisition" -- each player
develops their own consistent scanning strategy based on their level of strategic sophistication.

### Design implications for AI perception

- **Scan rate matters more than dwell time.** An expert-modeled AI should make frequent brief
  observations across many areas rather than long sustained reads of one area.
- **Compressed overviews are primary.** The equivalent of a "minimap glance" -- a fast, low-detail
  summary of fortress state -- should be the most frequent perception operation.
- **Stable scanpaths per context.** The AI should develop consistent observation routines for
  familiar fortress states, not random sampling.

---

## 2. Visual Chunking in Games

### Chase & Simon's chess chunks

Chase and Simon (1973) operationally defined chunks as groups of pieces placed with inter-piece
intervals under 2 seconds during reconstruction tasks. Their key findings:

- Chess masters reconstruct positions almost perfectly after 5 seconds of viewing
- This advantage vanishes for *randomly placed* pieces
- Masters don't have better memory -- they perceive larger *meaningful* chunks
- Estimated ~50,000 chunks in a Grandmaster's memory (order-of-magnitude estimate)

### Cowan's revision: 4 chunks, not 7

Nelson Cowan's research revised Miller's famous 7 plus/minus 2 down to approximately 4 chunks
as the true capacity of the focus of attention. This limit holds across:
- Visual and auditory modalities
- Spatial and temporal information
- Single and dual task conditions
- Attended and unattended stimuli

The 3-5 meaningful items limit applies to young adults regardless of information type (Cowan, 2001;
2010).

### What constitutes a "chunk" in Dwarf Fortress

By analogy with chess chunks, a DF chunk would be a *meaningful spatial-functional unit*:
- A complete workshop cluster (forge + smelter + stockpile = one chunk)
- A dining hall with its tables and chairs (one chunk, not N furniture items)
- A military squad on patrol (one chunk regardless of squad size)
- A stockpile zone with its fill level (one chunk: location + status)
- A farm plot with crop state (one chunk)

An expert player doesn't perceive "tile at (45,23) has a dwarf, tile at (45,24) has a table" --
they perceive "the dining hall is occupied." The AI perception system should chunk similarly.

### Design implications

- **Chunk, don't enumerate.** The perception system should report "workshop cluster: operational,
  output flowing" not a list of individual building states.
- **4 chunks per observation.** Each perception pass should return approximately 4 high-level
  chunks, matching the human focus-of-attention capacity.
- **Chunk boundaries follow function.** Rooms, zones, and functional areas are natural chunk
  boundaries -- not arbitrary grid regions.

---

## 3. Information Foraging Theory

### Pirolli & Card's framework

Information foraging theory (Pirolli & Card, 1999) applies optimal foraging theory from biology
to information seeking. Core concepts:

- **Information scent:** Cues in the environment that indicate the value/relevance of information
  at a location. "Trigger words" in navigation, color-coded status indicators, movement patterns.
- **Information patches:** Spatial and temporal clusters of related information. A DF analogy:
  the military screen is a "patch," the stocks screen is a different "patch."
- **Information diet:** The decision to pursue one information source over another based on
  expected value versus cost.
- **Patch-leaving decisions:** When does the forager decide the current patch is depleted and
  move to a new one? This maps to "when does the player stop checking military status and
  switch to checking food stocks?"

### How players decide where to look

Players follow information scent. In DF terms:
- A flashing red arrow on a dwarf is strong scent (unhappiness)
- Idle dwarves visible on the map are moderate scent (potential labor problem)
- A stockpile that appears full is moderate scent (potential production bottleneck)
- An empty area with no activity is low scent (nothing to forage)

Players do *not* follow rigid F-pattern or Z-pattern scanning across the game map. Those patterns
apply to text-heavy pages and structured documents. Game maps use *saliency-driven* scanning
(see section 5). However, F-patterns and Z-patterns *do* apply when players are reading menus,
stock lists, and status screens.

### Design implications

- **The AI should forage, not poll.** Instead of uniformly sampling all game state, the AI should
  follow information scent -- checking areas where signals indicate something has changed or
  needs attention.
- **Scent signals:** Notifications, alerts, visual changes on the map, time elapsed since last
  check, known pending events (caravan arrival, siege season).
- **Patch-leaving heuristic:** After N observations in one domain (e.g., military), switch to
  another unless active threat conditions persist.

---

## 4. Menu vs. Field Parsing

### Two distinct processing modes

Eye tracking and cognitive research distinguish sharply between how humans process:

**Spatial/map displays (the game field):**
- Processed via ambient vision first (short fixations, long saccades) for spatial orientation
- Followed by focal vision (long fixations, short saccades) for object identification
- Gestalt grouping happens automatically -- proximity groups rooms, similarity groups stockpiles
- Saliency-driven: motion, color contrast, and flicker capture attention bottom-up

**Structured menus and lists (status screens, stock lists):**
- Processed via reading patterns (F-pattern for dense text, Z-pattern for sparse layouts)
- Gestalt proximity creates visual groups in lists (related items clustered together)
- Recognition task, not recall -- items are visible, so working memory load is lower
- Visual hierarchy guides the eye: size > color > position > typography

### Gestalt principles in game UI

The key Gestalt principles active in game interfaces:
- **Proximity:** Nearby elements are perceived as grouped. Workshop + adjacent stockpile = unit.
- **Similarity:** Same-colored items (same material, same category) group perceptually.
- **Common fate:** Units moving together are perceived as a group (a squad).
- **Figure-ground:** The current z-level is figure; other levels are ground (not attended).
- **Closure:** An incomplete room outline is still perceived as "a room."

These groupings happen automatically and reduce cognitive load -- "the observer only needs to
track the group, rather than every individual element" (PMC, 2012).

### Design implications

- **Separate perception modes for map vs. menus.** Map perception should use spatial chunking
  and saliency. Menu/list perception should use structured sequential reading.
- **Gestalt grouping should be built into the perception model.** Don't report individual tiles;
  report Gestalt-grouped functional units.
- **Menu reads are cheaper than map reads.** A structured stock list can be processed as a
  recognition task with low cognitive load. Map scanning requires more expensive spatial processing.

---

## 5. Peripheral Vision and Pre-attentive Features

### Treisman's Feature Integration Theory

Anne Treisman (1980) established that certain visual features are processed pre-attentively --
automatically, in parallel, without focused attention:

**Pre-attentive features (pop-out in parallel):**
- Color (a red item among green items)
- Orientation (a tilted line among vertical lines)
- Size (a large item among small items)
- Motion/flicker (a moving item among static items)
- Intensity/contrast

**Conjunction features (require serial search with focused attention):**
- Red AND vertical (among red horizontal and green vertical)
- Large AND moving
- Any combination of two or more basic features

The pop-out effect means a single distinctive feature is detected instantly regardless of how
many distractors are present. Conjunction search scales linearly with the number of items.

### Peripheral vision in games

Research shows:
- Video game players distribute more attention to the visual periphery under low perceptual load
- As cognitive load increases, peripheral processing narrows and attention centralizes
- Peripheral vision primarily detects motion, contrast, and spatial layout (ambient vision)
- Central/focal vision handles identification and semantic processing

VR research confirms that peripheral flicker and motion reliably redirect attention even without
conscious awareness.

### The Itti-Koch saliency model

The computational saliency model (Itti & Koch, 1998) provides a formal framework:
- Multiscale features (color, intensity, orientation) computed at 8 spatial scales
- Center-surround contrast computed for each feature, producing 42 feature maps
- All maps combined into a single topographic saliency map
- Winner-take-all network selects the most salient location for attention

This is fundamentally a *contrast detector* -- what stands out from its surroundings.

### Design implications

- **The AI should detect contrast, not content.** The first-pass perception should identify
  *what changed* or *what stands out*, not read every tile.
- **Pre-attentive channels for the AI:**
  - Motion/activity: dwarves moving vs. idle, creatures appearing
  - Color-coded status: red stress indicators, flashing alerts
  - Spatial anomaly: empty area that should be occupied, crowded area that should be empty
  - Novel entity: new creature, new construction, collapsed structure
- **Saliency-first, detail-second.** First compute what's salient. Then read details only
  at salient locations. This mirrors the ambient-then-focal processing sequence in humans.

---

## 6. Attention Allocation: Expert vs. Novice

### Endsley's Situational Awareness Model

Endsley (1995) defines three levels of situational awareness (SA):

**Level 1 -- Perception:** Detecting elements in the environment. "There are dwarves in the
dining hall." "The food stockpile exists."

**Level 2 -- Comprehension:** Understanding meaning through pattern recognition and integration.
"The dining hall is operating normally." "Food stocks are declining toward shortage."

**Level 3 -- Projection:** Predicting future states. "At current consumption rate, food will
run out in 30 days." "The approaching goblin siege will arrive before the drawbridge is complete."

### Expert advantages

Experts develop:
- **Automatic Level 1 processing:** Perception requires fewer attentional resources, freeing
  capacity for comprehension and projection.
- **Schema-driven comprehension:** Mental models allow rapid pattern recognition -- an expert
  doesn't reason about each dwarf's happiness; they recognize "a tantrum spiral is forming."
- **Attention shedding under load:** Endsley & Rodgers (1998) showed that experts "shed attention
  to less important information as taskload increases." They don't try to monitor everything --
  they drop monitoring of low-priority subsystems when under pressure.

### The fighter pilot analogy

Endsley & Smith (1996) found that fighter pilots' attention to targets on a tactical display was
directly related to the *importance of those targets to their current task*. Unimportant targets
receive zero attention, not proportionally less attention.

### Design implications

- **Three-level perception pipeline:** The AI should have distinct perception, comprehension,
  and projection phases -- not collapse them into one "read the game state" operation.
- **Attention shedding is a feature.** Under crisis, the AI should *explicitly stop monitoring*
  low-priority systems (room quality, artifact production) and concentrate on the threat.
- **Importance-weighted observation.** The probability of observing a subsystem should be
  proportional to its current importance, not uniform.

---

## 7. Cognitive Load and Working Memory Constraints

### The real limits

- **Miller (1956):** 7 plus/minus 2 items in short-term memory (the classic number)
- **Cowan (2001):** Revised to ~4 chunks in the focus of attention
- **Gobet & Clarkson (2004):** Evidence for the "magical number four... or is it two?"
- **Key distinction:** These limits apply to *recall* tasks. Recognition tasks (scanning a visible
  display) have much higher capacity because items don't need to be held in memory.

### Cognitive load in game interfaces

Research on strategy games identifies a "cognitive threshold" beyond which forcing complex
decisions under time pressure stops being enjoyable (Quantic Foundry, 2016). Key findings:

- **Cognitive tunneling:** Under high load, operators fixate on a single information source and
  stop scanning. Peripheral vision utilization drops. In DF terms: a player managing a siege
  may completely stop monitoring food/drink/happiness.
- **Progressive disclosure:** Effective complex interfaces reveal information gradually as needed,
  not all at once.
- **Information overload markers:** Longer fixation durations, reduced scan areas, increased
  error rates, slower decision-making.

### Context switching costs

Each switch between information domains (military screen to stocks screen to individual dwarf)
incurs a cognitive cost:
- 23 minutes to fully regain deep focus after a context switch (UC Irvine research)
- Up to 40% of productive time consumed by chronic switching (APA)
- Each open "tab" or pending concern acts as a cognitive hook consuming background resources

### Design implications

- **Bound the observation buffer.** The AI should hold at most 4-5 high-level state summaries
  in its working context at any time, matching human chunk capacity.
- **Context switches are expensive.** The AI should batch observations by domain (check all
  military state together, then all food state together) rather than interleaving.
- **Tunneling is a real risk.** The system needs an explicit mechanism to break out of tunneling
  -- a timer or interrupt that forces domain-switching even during crisis management.
- **Progressive disclosure model.** Level 1 (everything): summary stats. Level 2 (some things):
  subsystem details for areas showing anomaly. Level 3 (one thing): full deep-read of a specific
  problem.

---

## 8. Scanpath Theory

### Noton & Stark's findings

Noton and Stark (1971) proposed that upon first viewing a stimulus, the sequence of fixations is
stored as a spatial model. On re-exposure:

- Participants repeated their initial scanpath in 65% of subsequent presentations
- Equivalent to the same scanpath occurring in 73.8% of all viewings
- The scanpath is a *top-down cognitive representation* that controls active looking

### Application to familiar game screens

This means:
- An experienced DF player develops a consistent scan order for familiar views
- When checking the main fortress view, they likely follow a habitual path: entrance region
  first, then workshop area, then living quarters, then farms, then military positions (or
  whatever their personal sequence is)
- When opening the stocks screen, they scan in a learned order: food, drink, materials, weapons
- These patterns are *individual* but *stable* -- each player has their own, and it persists

### Web and interface research confirms this

Josephson & Holmes tested scanpath theory on web pages and found that "some viewers' eye movements
may follow a habitually preferred path across the visual display" on repeated viewing. Recurrent
pattern detection methods have been developed to identify these stable sequences.

### Design implications

- **The AI should have explicit scan routines.** A defined, repeatable sequence of observations
  for each context (routine check, crisis response, post-event assessment).
- **Scan routines should be stable but context-dependent.** The "normal operations" scanpath
  differs from the "siege response" scanpath.
- **First-time exploration is different.** When the AI encounters a genuinely new situation, it
  should switch from scanpath mode to exploratory mode (ambient scanning).

---

## 9. Change Blindness

### What players miss

Change blindness research demonstrates:

- **Disruption-mediated:** Changes during saccades, blinks, or scene cuts are missed even when
  large. In DF terms: changes that happen while the player is looking at a different z-level or
  in a menu screen are effectively invisible.
- **Gradual changes:** Changes that occur slowly enough fall below motion-detection thresholds
  and go completely unnoticed. "When changes are sufficiently gradual, the visible change signal
  does not seem to draw attention" (Simons et al., 2000). In DF terms: a slowly declining food
  stockpile, gradual dwarf unhappiness increase, or a slowly encroaching aquifer.
- **Inattentional blindness:** When focused on one task, completely unexpected stimuli in plain
  sight are missed. The "Papers, Please" example is instructive -- focusing on one document
  field causes players to miss discrepancies in other fields.

### The DF-specific risk

DF is particularly vulnerable to change blindness because:
- The player frequently switches z-levels (disruption)
- The player frequently opens menus (disruption)
- Many critical changes are gradual (food depletion, stress accumulation, skill decay)
- The simulation runs continuously even while the player is focused elsewhere

### Design implications

- **Gradual change detection is a superpower.** The AI should explicitly track slow trends that
  humans reliably miss: declining stocks, rising stress averages, increasing idle time, growing
  miasma areas.
- **The AI should NOT assume omniscience.** To model realistic perception constraints, the AI
  should have limited visibility -- changes that happen "off-screen" (outside the current
  observation scope) should not be immediately known.
- **Change detection > state reading.** Comparing current state to previous state and reporting
  *deltas* is more valuable than reporting absolute state, because deltas are what change
  blindness causes humans to miss.
- **Interrupt on threshold.** Gradual changes should trigger alerts when they cross thresholds,
  even if no single tick-to-tick change is large enough to notice.

---

## 10. The Dwarf Fortress Player Experience

### How experienced players actually play

From Steam community discussions and wiki documentation:

**Systems over individuals.** Experienced DF players manage *systems*, not individual dwarves.
They monitor whether "output stockpiles are filling up without bottlenecking" -- a systems-level
observation. Individual dwarves are interchangeable parts of the logistics design. You don't
watch a dwarf; you watch whether the *workflow* is functioning.

**Visual tracking is limited.** A Steam community thread titled "do you really feel like you can
track what dwarves are doing visually?" reveals that experienced players acknowledge they
*cannot* effectively track individual dwarf behavior visually. The game's tile-based hopping
movement (versus smooth movement in Rimworld) makes visual tracking even harder. Players rely
on the game's information systems (announcements, screens, alerts) more than direct visual
observation.

**The notification system as attention driver.** DF's announcement system is the primary
attention-direction mechanism. Players customize `announcements.txt` to control which events
pause the game, recenter the camera, or display alerts. The key customizations most players
make: MIGRANT_ARRIVAL and CARAVAN_ARRIVAL. Some install the "Audible Alerts" mod to add
sound to notifications.

**Happiness monitoring via color coding.** The game uses color-coded thought indicators: blue/green
for positive, red/yellow for strong negative, brown for mild negative, purple/grey for neutral.
Stress becomes visible when dwarves flash a red downward arrow. This is a pre-attentive
feature -- color and flicker pop out without focused attention.

**The mental patrol routine.** An experienced player's routine appears to be:
1. Check announcements/alerts (interrupt-driven)
2. Scan the main view for obvious anomalies (saliency-driven)
3. Check food/drink stocks (periodic, information-foraging)
4. Review dwarf happiness summary (periodic)
5. Check military readiness (periodic, elevated during threat seasons)
6. Review work orders and labor allocation (periodic)
7. Inspect specific problems flagged by steps 1-6 (detail-on-demand)

This maps closely to the scanpath theory -- a stable, habitual sequence of observations that
the player runs through cyclically.

---

## Synthesis: Principles for a Constrained AI Perception System

The research across all 10 areas converges on a coherent set of design principles:

### Principle 1: Ambient-then-Focal Processing

The AI should have two perception modes operating in sequence:
- **Ambient pass:** Fast, broad, low-detail scan. Detects saliency (contrast, change, motion,
  anomaly). Produces a list of "interesting" locations/domains. Analogous to short-fixation,
  long-saccade initial scanning.
- **Focal pass:** Slow, narrow, high-detail read of items flagged by the ambient pass. Produces
  rich state descriptions. Analogous to long-fixation, short-saccade detailed inspection.

### Principle 2: Chunk-Based Representation

Perception output should be chunked into functional units, not raw tile data:
- Maximum ~4 chunks per focal observation (Cowan's limit)
- Chunks correspond to game-meaningful units: rooms, workshops, squads, stockpiles
- Chunk descriptions include functional status, not just physical inventory

### Principle 3: Information Foraging, Not Polling

The AI should follow information scent rather than polling uniformly:
- Areas with recent changes, alerts, or anomalies get more frequent observation
- Areas with no scent (stable, functioning systems) get infrequent background checks
- Domain switching follows a patch-leaving heuristic: move on when current domain yields
  diminishing returns

### Principle 4: Saliency-Driven Attention

Pre-attentive features should drive observation priority:
- Alerts/notifications (highest priority -- interrupt-driven)
- Status changes (color-coded state transitions)
- Motion anomalies (unusual activity patterns)
- Absence (something expected is missing)
- Gradual trends crossing thresholds

### Principle 5: Stable Scanpaths with Context Switching

The AI should maintain explicit observation routines:
- **Routine scanpath:** Cyclic check of all major subsystems at defined intervals
- **Crisis scanpath:** Compressed, threat-focused, with explicit shedding of non-critical domains
- **Exploratory mode:** For genuinely novel situations, drop the scanpath and scan broadly
- Scanpath transitions should be triggered by SA level changes

### Principle 6: Three-Level Situational Awareness

Map directly to Endsley's model:
- **Level 1 (Perception):** What exists? Raw observations chunked by functional area.
- **Level 2 (Comprehension):** What does it mean? Pattern recognition across observations.
  "Food is declining" + "dwarves are unhappy" = "morale crisis forming."
- **Level 3 (Projection):** What will happen? Extrapolation of trends. "At this rate, food
  runs out in 20 days; a tantrum spiral will begin in 15."

### Principle 7: Change Detection as Primary Signal

Deltas are more valuable than absolutes:
- Compare current observations to previous observations
- Explicitly track gradual trends that fall below per-tick detection thresholds
- Report what *changed* since last observation, not just what *is*

### Principle 8: Bounded Working Context

The AI's decision-making context should be capacity-limited:
- Maximum 4-5 active concerns (chunks in the focus of attention)
- Domain batching: complete one domain's observations before switching
- Context switch cost modeled explicitly: switching domains means losing some prior context
- Anti-tunneling timer: forced domain rotation even during crisis

### Principle 9: Attention Shedding Under Load

Under crisis, the AI should explicitly deprioritize:
- Room quality, artifact tracking, social relationships during siege
- Military readiness during peacetime resource optimization
- Individual dwarf preferences during mass-casualty events
- This mirrors expert operator behavior in all studied domains

### Principle 10: Intentional Blindness

The AI should *not see everything*:
- Off-screen areas have reduced observation fidelity (not zero, but degraded)
- Gradual changes must accumulate past a threshold to trigger awareness
- During focused tasks, peripheral information is available only as pre-attentive features
  (something moved, something changed color), not as detailed state
- This creates realistic perception constraints that make the AI's decision-making legible
  and bounded

---

## Sources

- [JMIR: Eye Tracking in Puzzle Games](https://games.jmir.org/2021/1/e24151)
- [Eye Tracking in Game UX (Gamedeveloper)](https://www.gamedeveloper.com/design/-read-player-s-mind-through-eyes-how-eye-tracking-works-in-game-user-research)
- [Strategic Sophistication and Attention (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S089982561500130X)
- [Eye Tracking and Video Games (Try Evidence)](https://tryevidence.com/blog/eye-tracking-and-video-games-research/)
- [Chase & Simon: Perception in Chess (CMU)](https://iiif.library.cmu.edu/file/Simon_box00005_fld00354_bdl0001_doc0001/Simon_box00005_fld00354_bdl0001_doc0001.pdf)
- [Cowan: Magical Number 4 (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2864034/)
- [Gobet: Expert Chess Memory Revisiting Chunking](https://www.academia.edu/82542304/Expert_Chess_Memory_Revisiting_the_Chunking_Hypothesis)
- [Pirolli & Card: Information Foraging (IxDF)](https://ixdf.org/literature/book/the-glossary-of-human-computer-interaction/information-foraging-theory)
- [Information Foraging (NN/g)](https://www.nngroup.com/articles/information-foraging/)
- [Gestalt Principles in Games (ThinkMind)](https://www.thinkmind.org/articles/icds_2022_2_40_10021.pdf)
- [Gestalt Principles (IxDF)](https://ixdf.org/literature/topics/gestalt-principles)
- [Gestalt Similarity Benefits WM (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3806891/)
- [A Century of Gestalt Psychology (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3482144/)
- [Action Video Game Modifies Visual Attention (Nature)](https://www.nature.com/articles/nature01647)
- [Video Games as Tool to Train Visual Skills (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2884279/)
- [Visuospatial Attention and Action Games (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2896828/)
- [Treisman Feature Integration Theory (Wikipedia)](https://en.wikipedia.org/wiki/Feature_integration_theory)
- [Preattentive Features (Wolfe & Utochkin)](https://search.bwh.harvard.edu/new/pubs/CurrOpPsych_PreattFeatWolfe_Utochkin2019.pdf)
- [Pre-Attentive Processing Survey (TU Graz)](https://courses.isds.tugraz.at/ivis/surveys/ss2010/g2-survey-preatt.pdf)
- [Perception in Visualization (Healey, NCSU)](https://www.csc2.ncsu.edu/faculty/healey/PP/)
- [Itti & Koch Saliency Model (1998)](https://hasler.ece.gatech.edu/Courses/MachineLearning/FoundationalPapers/Itti_Koch_Neiber1998.pdf)
- [Itti: Computational Modelling of Visual Attention (Nature)](https://www.nature.com/articles/35058500)
- [Endsley: Toward a Theory of Situation Awareness](https://www.researchgate.net/publication/210198492_Endsley_MR_Toward_a_Theory_of_Situation_Awareness_in_Dynamic_Systems_Human_Factors_Journal_371_32-64)
- [Endsley: SA Misconceptions (2015)](https://journals.sagepub.com/doi/10.1177/1555343415572631)
- [Expertise and Situation Awareness (Cambridge)](https://www.cambridge.org/core/books/abs/cambridge-handbook-of-expertise-and-expert-performance/expertise-and-situation-awareness/AC21B986A4DFE55AA740967469AAB888)
- [StarCraft Gaze Control (PLOS ONE)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0265526)
- [Expert StarCraft Gaze (PsyPost)](https://www.psypost.org/expert-starcraft-players-employ-more-efficient-gaze-control-abilities-than-low-skill-players-study-finds/)
- [Digit Eyes: Learning in StarCraft (Springer)](https://link.springer.com/article/10.3758/s13414-020-02019-w)
- [Miller's Law (Laws of UX)](https://lawsofux.com/millers-law/)
- [Cognitive Threshold in Strategy Games (Quantic Foundry)](https://quanticfoundry.com/2016/01/20/game-genre-map-the-cognitive-threshold-in-strategy-games/)
- [Cognitive Load in Game Interfaces (Medium)](https://medium.com/@zeynepbalibek.ux/cognitive-load-and-usability-in-game-interface-design-ad381ffc7651)
- [Noton & Stark Scanpath Theory (ResearchGate)](https://www.researchgate.net/publication/241250830_The_Scanpath_Theory_its_definition_and_later_developments_-_art_no_60570A)
- [Scanpath Theory on the Web (Josephson & Holmes)](https://www.semanticscholar.org/paper/Visual-attention-to-repeated-internet-images:-the-Josephson-Holmes/db1d5055438ea9cb5d983fff9dd7b88ebafb6f10)
- [Repeated Web Visits Scanpath (MDPI)](https://www.mdpi.com/1995-8892/3/4/21)
- [Change Blindness (NN/g)](https://www.nngroup.com/articles/change-blindness-definition/)
- [Inattentional Blindness and Video Games (Psychology Today)](https://www.psychologytoday.com/us/blog/mind-games/201307/inattentional-blindness-and-video-games)
- [Change Blindness Without Disruption (Simons et al.)](https://visionplus.psych.northwestern.edu/Papers_files/Simons_etal_gradual.pdf)
- [Gradual Change Blindness EEG (PubMed)](https://pubmed.ncbi.nlm.nih.gov/29364069/)
- [Ambient and Focal Processing (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10902451/)
- [Eye Movement Patterns Ambient/Focal (PLOS ONE)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0277099)
- [Two Modes of Visual Processing (NCBI)](https://www.ncbi.nlm.nih.gov/books/NBK219039/)
- [F-Pattern Z-Pattern Complex Systems (Medium)](https://medium.com/uxd-critical-software/understanding-the-f-shaped-and-z-shaped-reading-patterns-for-optimal-usability-in-complex-systems-e96668839abd)
- [Dashboard Layout Eye Tracking (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11435723/)
- [DF Steam: Tracking Dwarves Visually](https://steamcommunity.com/app/975370/discussions/0/3716062978747541116/)
- [DF Steam: Keep Track of What's Going On](https://steamcommunity.com/app/975370/discussions/0/4415298705117357295/)
- [DF Wiki: Announcements](https://dwarffortresswiki.org/index.php/Announcement)
- [DF Steam: Alert Options Guide](https://steamcommunity.com/sharedfiles/filedetails/?id=2898849198)
- [UI Strategy Game Design (Gamedeveloper)](https://www.gamedeveloper.com/design/ui-strategy-game-design-dos-and-don-ts)
