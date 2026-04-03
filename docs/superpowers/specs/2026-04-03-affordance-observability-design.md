# Affordance Field Observability — Dashboard Design Specification

**Date:** 2026-04-03
**Status:** Draft
**Scope:** Two Grafana dashboards + expanded Prometheus metrics endpoint
**Depends on:** Total Affordance Field epic (2026-04-03), SCM Formalization, PCT Control Laws

---

## 1. Architecture

One expanded Prometheus metrics endpoint (`/api/predictions/metrics`) scrapes all available `/dev/shm` state files on each request. Two Grafana dashboards consume from the same Prometheus data source at `:9090`.

**No daemon changes required.** All metrics are derived from existing SHM files written by running daemons. The metrics endpoint is a pure reader — it opens, parses, and emits. Each SHM file is stat'd for freshness; stale files (>120s) emit `NaN` rather than stale values.

**Dashboard 1:** `hapax-operational-health` — "Is everything running?"
**Dashboard 2:** `hapax-behavioral-predictions` — "Is the architecture doing what theory predicts?"

---

## 2. Metrics Endpoint Expansion

The existing `/api/predictions/metrics` route in `logos/api/routes/predictions.py` currently emits ~25 metrics. Expand to ~180 metrics organized in 10 scrape sections, each reading one or more SHM files.

### Scrape sections

| Section | SHM source(s) | Metrics emitted | Scrape cost |
|---|---|---|---|
| Predictions (existing) | `/dev/shm/hapax-reverie/predictions.json` | 14 | <1ms |
| Uniforms (expand) | `/dev/shm/hapax-imagination/uniforms.json` | 72 (36 value + 36 deviation) | <1ms |
| Stimmung | `/dev/shm/hapax-stimmung/state.json` | 33 (11 value + 11 freshness + 11 trend) | <1ms |
| Mesh health | `/dev/shm/hapax-*/health.json` (14 files) | 42 (14×3: reference, perception, error) | ~5ms |
| Exploration | `/dev/shm/hapax-exploration/*.json` (14 files) | 70 (14×5: boredom, curiosity, error, stagnation, coherence) | ~5ms |
| Imagination | `/dev/shm/hapax-imagination/current.json` | 11 (9 dims + salience + continuation) | <1ms |
| DMN status | `/dev/shm/hapax-dmn/status.json` + `visual-salience.json` | 6 | <1ms |
| CPAL | `/dev/shm/hapax-conversation/state.json` | 6 (gain + 4 errors + tier) | <1ms |
| Presence (existing) | `perception-state.json` | 6 | <1ms |
| Activation state | `~/.cache/hapax/affordance-activation-state.json` | ~30 (top-30 capabilities by use_count) | ~2ms |

Total scrape time: ~15ms. Prometheus scrape interval: 30s.

---

## 3. Dashboard 1: Operational Health

### 3.1 SCM Mesh Health

**14 panels (one per S1 component), unified row**

Each panel shows three lines: `reference` (green, flat at 1.0), `perception` (yellow, varies), `error` (red, |reference - perception|).

#### Metric: `hapax_mesh_error{component="..."}`

**What it measures:** The absolute difference between a component's reference signal (its nominal operating point) and its perceived state. Each of the 14 S1 components publishes a `ControlSignal(reference, perception, error)` to `/dev/shm/hapax-{component}/health.json`. The error is the PCT control loop's deviation from setpoint.

**Theoretical import:** Perceptual Control Theory (Powers, 1973) posits that behavior is the control of perception — organisms act to reduce the discrepancy between perceived state and reference state. Each S1 component is a PCT control loop. The mesh error is the aggregate `E_mesh = sum(w_i * |perception_i - reference_i|)` from the SCM concrete formalizations (§4.1). A healthy mesh has transient errors that resolve within the slowest reader's cadence; persistent errors indicate a control loop that cannot correct.

**Research references:**
- Powers, W.T. (1973). *Behavior: The Control of Perception*. Aldine.
- SCM spec §4.1: "The aggregate mesh error is the sum of weighted per-component errors."
- Control law specifications (2026-03-31): 14 components with 3-level corrective action.

**Predictive import:**
- `error < 0.1` for all components: nominal operation
- `error > 0.3` sustained: component has entered Level 1 corrective action (mild)
- `error > 0.6` sustained: component at Level 2 (moderate degradation)
- `error = 1.0`: component has failed or is not running
- Correlated errors across multiple components: cascading failure (the most dangerous pattern; monotonic degradation should prevent this)
- Expected: conversation and voice_pipeline show error=1.0 when no voice session is active (this is nominal, not a failure)

---

### 3.2 Stimmung Dimensions

**11 gauges + 1 stance indicator**

#### Metric: `hapax_stimmung_value{dimension="..."}`

**What it measures:** Each of the 11 stimmung dimensions is a 0.0 (healthy) to 1.0 (stressed) continuous reading. `SystemStimmung` aggregates inputs from multiple backends: `health` from service availability, `resource_pressure` from GPU/CPU, `operator_stress` from HRV+EDA+frustration, `exploration_deficit` from the 15th control law, etc.

**Theoretical import:** Stimmung (Heidegger, 1927) is not emotion — it is attunement, the pre-reflective disclosure of the world's significance. In Heidegger's ontology, Befindlichkeit (disposedness/attunement) is co-constitutive with understanding and discourse; it determines which affordances show up as salient. The system's Stimmung modulates every subsystem: imagination cadence, CPAL gain ceiling, affordance recruitment threshold (SEEKING halves it), VLA tick interval, model tier selection. It is the system-wide gain scheduling mechanism.

**Research references:**
- Heidegger, M. (1927). *Sein und Zeit*, §29: Befindlichkeit.
- SCM spec §3.3: "Stimmung provides gain scheduling, not synchronization."
- Stimmung Pipeline Coherence spec (2026-03-31).
- PCT coupled model (Powers, 1973): stimmung as gain multiplier on the S-loop.

**Predictive import:**
- All dimensions < 0.3: NOMINAL stance, full system capacity
- Any infrastructure dimension > 0.6: DEGRADED stance, subsystems slow by 2x
- `exploration_deficit` > 0.35 with all else nominal: SEEKING stance, recruitment aperture widens
- `operator_stress` > 0.5: biometric stress detection (HRV drop + EDA); system should reduce interruptions
- Rapid `error_rate` rise: indicates cascading service failures

#### Metric: `hapax_stimmung_stance`

**What it measures:** The discrete stance derived from worst-case dimension analysis. Encoded as float: nominal=0.0, seeking=0.1, cautious=0.25, degraded=0.5, critical=1.0.

**Predictive import:**
- Stance transitions should be rare (hysteresis: 3 readings to degrade, 5 to recover)
- Frequent stance oscillation indicates threshold tuning issues
- SEEKING entering and exiting cleanly indicates healthy exploration dynamics

---

### 3.3 Exploration Signals

**14 panels (one per SCM component)**

#### Metric: `hapax_exploration_boredom{component="..."}`

**What it measures:** The 4-layer boredom index (0.0-1.0) per S1 component. Computed as `0.30 * mean_habituation + 0.30 * (1 - mean_trace_interest) + 0.20 * stagnation/t_patience + 0.20 * dwell_in_coherence/t_patience`. High values mean the component's inputs are predictable and unchanging.

**Theoretical import:** Boredom is PCT reorganization signal (Powers, 1973, Chapter 16). When a control loop's error is chronically low but its trace interest has evaporated, the loop has habituated — it is controlling successfully but the reference is stale. The 15th control law (boredom/exploration) implements Heidegger's Tiefe Langeweile (profound boredom): the system has resolved all immediate concerns but finds nothing compelling. This triggers the SEEKING stance via `exploration_deficit` stimmung dimension.

**Research references:**
- Powers, W.T. (1973). *Behavior: The Control of Perception*, Ch. 16: Reorganization.
- Heidegger, M. (1929/30). *The Fundamental Concepts of Metaphysics*, §§29-38: Three forms of boredom.
- Boredom and Exploration Signal spec (2026-04-01).
- Carandini, M. & Heeger, D.J. (2012). Normalization as a canonical neural computation. *Nature Reviews Neuroscience*.

**Predictive import:**
- Boredom > 0.7 in multiple components simultaneously: system is in a rut, SEEKING should activate
- Boredom near 0 everywhere: high novelty state (new deployment, environment change)
- Single component at high boredom while others are low: that component's inputs are stagnant (sensor failure or monotonous environment)
- `affordance_pipeline` boredom rising: recruitment is settling into repetitive patterns — Thompson sampling may be over-exploiting

#### Metric: `hapax_exploration_curiosity{component="..."}`

**What it measures:** `max(chronic_error * (1.0 if improvement <= 0 else 0.5), max_novelty_score, 1.0 - local_coherence)`. High values indicate genuine novel stimulus detected.

**Theoretical import:** Curiosity is the complement of boredom. In PCT terms, it is the detection of a prediction error that resists correction — the system encounters something it cannot yet control. Berlyne (1960) distinguishes diversive curiosity (boredom-driven) from specific curiosity (novelty-driven). The curiosity index captures specific curiosity via `max_novelty_score` and the learning progress component (`chronic_error` with non-improving trajectory).

**Research references:**
- Berlyne, D.E. (1960). *Conflict, Arousal, and Curiosity*. McGraw-Hill.
- Schmidhuber, J. (2010). Formal Theory of Creativity, Fun, and Intrinsic Motivation. *IEEE TAMD*.
- Oudeyer, P.Y. & Kaplan, F. (2007). What is intrinsic motivation? *Frontiers in Neurorobotics*.

**Predictive import:**
- Curiosity > 0.6 in `dmn_imagination`: imagination has encountered something it cannot predict — reverberation loop may be active
- Curiosity spike in `salience_router`: novel utterance pattern detected
- Sustained curiosity > 0.4 across many components: productive exploration phase

---

### 3.4 Service Freshness

**Single heatmap: component × time, color = seconds since last update**

#### Metric: `hapax_shm_freshness_s{component="..."}`

**What it measures:** Seconds since the last modification of each component's primary SHM file. Computed via `stat().st_mtime` delta. Components with active daemons update continuously; timer-driven components update on their schedule.

**Theoretical import:** SCM Property 2 (heterogeneous temporal scales) guarantees that components operate at independent cadences. Staleness is not inherently pathological — a 1-hour weather sync is expected to be stale for most of each hour. But unexpected staleness (a 1-second perception loop going dark for 30s) indicates a stuck process. The sheaf health computation (SCM §4.2) uses staleness to determine which H^1 generators are transient vs persistent.

**Predictive import:**
- perception-state > 5s: voice daemon may have crashed
- stimmung > 60s: VLA tick is stuck
- imagination/current > 30s: imagination daemon cadence has paused (stimmung may be critical)
- exploration files > 600s: that component's ExplorationTrackerBundle is not ticking

---

### 3.5 Content Resolution

#### Metric: `hapax_content_sources_active`

**What it measures:** Count of subdirectories in `/dev/shm/hapax-imagination/sources/` that have both `frame.rgba` and `manifest.json`. Each represents an active content source on the visual surface.

**Theoretical import:** Content sources are the material expression of recruited affordances. A camera feed, a text render, a Qdrant recall result — each becomes a source. If the pipeline recruits content affordances but the source count stays at zero, the content resolution layer is broken. This is the Bachelardian test: does imagination produce visible material?

**Predictive import:**
- 0 sources for extended periods: content resolution is failing (check content_resolver health.json)
- 1-2 sources sustained: healthy, one content actively displayed
- >4 sources: Rust ContentSourceManager caps at 16 but visual clutter begins at 4

#### Metric: `hapax_content_source_tags{tag="recruited|fallback|perception|recall"}`

**What it measures:** Count of active sources by their manifest `tags` array. "recruited" means the AffordancePipeline selected this content. "fallback" means Qdrant was unavailable and the query text was rendered directly. "perception" means a camera feed. "recall" means a knowledge/episodic/profile recall result.

**Predictive import:**
- "fallback" > 0: Qdrant is down or embedding is failing — content degraded to text fallback
- "recruited" growing: pipeline is successfully activating content
- "recall" present: knowledge affordances are producing output

---

### 3.6 CPAL Conversation State

#### Metric: `hapax_cpal_gain`

**What it measures:** The CPAL control loop gain (0.0-1.0). Represents the system's conversational engagement intensity. 0.0 = silence/ambient. 1.0 = fully engaged conversation.

**Theoretical import:** CPAL implements conversation as the 15th S1 control loop (spec 2026-04-01). Gain replaces the binary session model. The controlled variable is Grounding Quality Index (GQI). Gain is driven upward by operator speech and presence, driven downward by silence and stimmung ceiling. The stimmung ceiling table (nominal=1.0, cautious=0.7, degraded=0.5, critical=0.3) ensures the system does not over-engage when infrastructure is stressed.

**Research references:**
- Clark, H.H. & Brennan, S.E. (1991). Grounding in Communication. *Perspectives on Socially Shared Cognition*.
- CPAL spec (2026-04-01): Conversation as the 15th S1 control loop.
- Traum, D.R. (1994). A Computational Theory of Grounding in Natural Language Conversation.

**Predictive import:**
- gain > 0 rising: operator is engaging, system is responding
- gain = 0 sustained: no active conversation (normal during solo work)
- gain oscillating rapidly: engagement detection instability
- gain hitting stimmung ceiling repeatedly: infrastructure stress is limiting conversational capacity

#### Metric: `hapax_cpal_error{domain="comprehension|affective|temporal"}`

**What it measures:** The CPAL error decomposition. Comprehension error: ungrounded discourse units. Affective error: 1.0 - GQI - 0.15. Temporal error: silence_s / 30s. These sum to the total CPAL error driving corrective action.

**Predictive import:**
- High comprehension error: the system is saying things the operator doesn't acknowledge — grounding is failing
- High affective error: low GQI, conversation quality is poor
- High temporal error: long silences, system may need to re-engage or accept ambient mode

---

### 3.7 Feature Flags

#### Metric: `hapax_feature_flag{flag="world_routing"}`

**What it measures:** 0/1 existence of `~/.cache/hapax/world-routing-enabled`.

**Predictive import:** When 0, world domain routing is disabled — no `env.*`, `body.*`, etc. affordances are routed in the daimonion consumer loop. Useful for correlating behavioral changes with flag toggles.

---

## 4. Dashboard 2: Behavioral Predictions

### 4.1 Realtime Section (seconds)

#### 4.1.1 Shader Uniform State

**36 gauges as a heatmap or multi-line chart**

##### Metric: `hapax_uniform_value{param="noise.amplitude|rd.feed_rate|color.saturation|..."}`

**What it measures:** The current value of each of the 36 shader parameters written to `uniforms.json` every mixer tick (~1s). These are the base plan defaults modified by visual chain dimension activations, imagination dimensions, and stimmung signals.

**Theoretical import:** The shader graph is the Bachelardian generative substrate — the material imagination rendered. The 8-pass vocabulary graph (noise → rd → color → drift → breath → feedback → content → postprocess) always runs; these parameters modulate its character. When uniform values deviate from vocabulary defaults, imagination is actively shaping the visual field. When they return to defaults, the visual surface is in its resting state.

The deviation from defaults is the most direct measure of whether imagination → visual expression is working. Zero deviation means the visual chain is inactive (no impingements, or impingements failing to recruit).

**Research references:**
- Bachelard, G. (1943). *L'Air et les Songes*. Imagination of movement.
- Bachelard, G. (1942). *L'Eau et les Reves*. Material imagination.
- Reverie Adaptive Compositor spec (2026-03-31): "The vocabulary graph always runs... recruitment modulates it."

##### Metric: `hapax_uniform_deviation{param="..."}`

**What it measures:** `|current_value - vocabulary_default|` per param.

**Predictive import:**
- Mean deviation near 0 for extended periods: imagination is not reaching the visual chain (check render_impingement_text, check impingement rate, check pipeline selection)
- Mean deviation > 0.5: strong imagination modulation, visually rich output
- Specific params at extreme deviation: a single dimension is dominating (check for Thompson exploitation collapse)
- `signal.stance` deviation: stimmung is in a non-nominal state
- `content.salience` > 0: active content recruitment on the visual surface

#### 4.1.2 Imagination Dimensions

**9 gauges in a polar/radar layout**

##### Metric: `hapax_imagination_dimension{dim="intensity|tension|depth|coherence|spectral_color|temporal_distortion|degradation|pitch_displacement|diffusion"}`

**What it measures:** The 9 canonical expressive dimensions from the current `ImaginationFragment`. These are set by the imagination LLM and represent the qualitative character of the current thought.

**Theoretical import:** The 9 dimensions are the system's phenomenal vocabulary — they describe not what is imagined (that's the narrative) but how it feels. They map to both visual expression (via `VisualChainCapability`) and vocal expression (via `VocalChainCapability`). The same dimension vector simultaneously drives GPU shader params and MIDI CC values on physical hardware.

The dimensions are the bridge between cognitive content and physical expression. Their variance over time indicates whether the imagination is producing diverse phenomenal qualities or is stuck in a narrow range.

**Research references:**
- Visual Chain Capability spec (2026-03-27): 9 dimensions mapped to shader node uniforms.
- Vocal Chain Capability spec (2026-03-27): same 9 dimensions mapped to MIDI CCs.
- Bachelard's 5 materials provide the qualitative framing; the 9 dimensions provide the quantitative axis.

**Predictive import:**
- All 9 near 0.0: imagination is producing low-salience fragments (normal during idle)
- Intensity + tension high together: urgent/transformative imagination (fire material likely)
- Depth + coherence high together: contemplative/structured imagination (water/earth likely)
- Single dimension spiking while others near 0: dimensional imbalance (may indicate a stale prompt template or LLM fixation)

##### Metric: `hapax_imagination_salience`

**What it measures:** The imagination LLM's self-assessed salience (0.0-1.0) of the current fragment. Salience > 0.55 triggers probabilistic escalation to the impingement trail.

**Theoretical import:** Salience is the DMN's self-assessment of whether a thought is worth broadcasting. Most fragments are 0.1-0.3 (background cognition, not escalated). Fragments > 0.6 almost certainly escalate. The sigmoid escalation curve (steepness=8, midpoint=0.55) is calibrated to suppress routine imagination while surfacing genuine insights.

**Predictive import:**
- Sustained salience < 0.2: imagination is idling, DMN in maintenance mode
- Salience spikes > 0.6: imagination has produced something it considers important — should see corresponding impingement and recruitment activity within seconds
- Mean salience rising over hours: the expanded context (weather, time, goals) may be giving the DMN more to work with

#### 4.1.3 Technique Confidence

##### Metric: `hapax_technique_confidence{technique="..."}`

**What it measures:** The AffordancePipeline combined score for the most recently recruited affordance of each type, from chronicle `technique.activated` events in the last 60s.

**Theoretical import:** This is Cisek's affordance competition (2007) made visible. Multiple affordances compete via `0.50*similarity + 0.20*base_level + 0.10*context_boost + 0.20*thompson`. The winning confidence score indicates how strongly the impingement narrative matched the affordance description. Low confidence wins (0.05-0.15) mean nothing strongly matched — the system is guessing. High confidence wins (0.5+) mean a clear semantic match.

**Research references:**
- Cisek, P. (2007). Cortical mechanisms of action selection: the affordance competition hypothesis. *Phil Trans R Soc B*.
- Desimone, R. & Duncan, J. (1995). Neural mechanisms of selective visual attention. *Annual Rev Neurosci*.
- Thompson, W.R. (1933). On the likelihood that one unknown probability exceeds another. *Biometrika*.

**Predictive import:**
- Diverse techniques recruited at moderate confidence (0.2-0.5): healthy competition, multiple affordances relevant
- Single technique dominating at high confidence: exploitation phase (may be appropriate or may indicate Thompson collapse)
- All techniques at very low confidence (<0.1): impingement narratives don't match any affordance descriptions well — check `render_impingement_text` narrative inclusion

---

### 4.2 Fast Section (minutes)

#### 4.2.1 Recruitment by Domain

##### Metric: `hapax_recruitment_count{domain="env|body|studio|space|digital|knowledge|social|system|world|node|content"}`

**What it measures:** Count of affordance recruitments per domain over a rolling 5-minute window, derived from chronicle `technique.activated` events.

**Theoretical import:** Gibson's ecological psychology predicts that affordances are context-dependent — the same environment affords different actions to different organisms in different states. If the system is in a music production session, `studio.*` affordances should dominate. If the operator is away, `space.*` presence affordances should dominate. Domain recruitment patterns should correlate with the operator's activity mode.

The Roschian basic-level categorization predicts that domain boundaries are pragmatic, not ontological — the embedding space should produce some cross-domain recruitment naturally. If recruitment is strictly domain-siloed (only `node.*` ever recruited, never `studio.*`), the embedding space may not be diverse enough.

**Research references:**
- Gibson, J.J. (1979). *The Ecological Approach to Visual Perception*, Ch. 8.
- Rosch, E. (1978). Principles of Categorization. In *Cognition and Categorization*.
- Total Affordance Field spec §6: "Domains organize registration and dispatch; the embedding space organizes recruitment."

**Predictive import:**
- 3+ domains recruited per 5-minute window: healthy cross-domain competition
- Single domain monopolizing: either appropriate (deep work in studio) or pathological (Thompson collapse)
- `world.*` recruitment while discovery stub returns []: aspirational affordance recruited but not resolved (expected until more external APIs are wired)
- `knowledge.*` recruitment: Qdrant recall affordances are being activated — content should appear on visual surface

#### 4.2.2 Content Resolution Success Rate

##### Metric: `hapax_content_resolution_success{type="narrative_text|episodic_recall|knowledge_recall|profile_recall|waveform_viz"}`

**What it measures:** Boolean (0/1) indicating whether the most recent activation of each content resolver produced a source in `/dev/shm/hapax-imagination/sources/`. Derived from comparing chronicle activations against source directory contents.

**Predictive import:**
- `narrative_text` success = 1: Pillow text rendering is working
- `knowledge_recall` success = 0: Qdrant query failed, fell back to text (check Qdrant health)
- `waveform_viz` success = 0: perception-state.json may not have `audio_energy_rms`

#### 4.2.3 Cross-Modal Dispatch

##### Metric: `hapax_expression_dispatch{modality="auditory|visual|textual|notification"}`

**What it measures:** Count of ExpressionCoordinator dispatch events by modality in the last 5 minutes. Incremented when `run_loops_aux.py` iterates coordinator activations and calls `cap.activate()`.

**Theoretical import:** The ExpressionCoordinator implements the cross-modal expression principle: a single impingement can recruit both visual (Reverie) and auditory (vocal chain) capabilities simultaneously. This is the system's version of multi-modal perception — the same thought expressed through multiple channels. Merleau-Ponty's sensorimotor contingencies predict that expression modality should match the character of the content: spatial/visual thoughts → visual expression, temporal/sequential thoughts → vocal expression.

**Research references:**
- Capability Parity spec (2026-03-29), Phase 5: Cross-modal recruitment.
- Merleau-Ponty, M. (1945). *Phenomenology of Perception*: Sensorimotor contingencies.

**Predictive import:**
- Multi-modal events (auditory + visual for same impingement): the architecture is producing genuine cross-modal expression
- Only visual, never auditory: voice session may not be active (expected during solo work)
- Notification events: system.notify_operator is being recruited and firing

---

### 4.3 Slow Section (hours)

#### 4.3.1 Thompson Convergence (expanded P1)

##### Metric: `hapax_thompson_mean{capability="..."}`

**What it measures:** `alpha / (alpha + beta)` for the Thompson Beta distribution of each registered affordance. Starts at `2/(2+1) = 0.67` (optimistic prior). Converges toward the true success rate as the affordance is recruited and outcomes recorded.

**Theoretical import:** Thompson sampling (Thompson, 1933) balances exploration (trying uncertain options) with exploitation (using known-good options). The optimistic prior (Beta(2,1)) ensures cold-start affordances get recruited — they start with a 67% assumed success rate and must fail repeatedly to be suppressed. The geometric decay (gamma=0.99) prevents unbounded growth, so old successes fade over ~100 uses.

Convergence means the system has learned which affordances work for which impingement types. Divergence (mean drifting away from prior) means the system is still exploring. Collapse (all affordances converging to the same mean) means Thompson sampling has lost its discriminatory power.

**Research references:**
- Thompson, W.R. (1933). On the likelihood that one unknown probability exceeds another. *Biometrika*.
- Chapelle, O. & Li, L. (2011). An empirical evaluation of Thompson sampling. *NIPS*.
- Total Affordance Field spec §2.2: "Thompson sampling with optimistic prior Beta(2,1)."

**Predictive import:**
- Mean > 0.7 for most affordances after 2h: healthy convergence, system is learning
- Mean < 0.5 for an affordance: that affordance has been failing — check if it has a handler
- All means clustered near 0.67 (prior): system hasn't recruited enough to learn — check impingement rate
- A few affordances at 0.9+ while most are at 0.67: exploitation bias — SEEKING should activate to widen aperture

#### 4.3.2 Hebbian Association Count (expanded P3)

##### Metric: `hapax_hebbian_association_count`

**What it measures:** Total number of `(cue_value, capability_name)` pairs in the context association dict. Each pair represents a learned relationship between an impingement source/metric and a recruited capability.

**Theoretical import:** Hebbian learning ("neurons that fire together wire together," Hebb 1949) is implemented as context associations in the AffordancePipeline. When `record_outcome()` is called with a context dict, each key-value pair becomes a cue that boosts future recruitment of that capability. The association strength is clamped [-1.0, 4.0] with passive decay (0.995 per tick). This is the system's long-term memory of what affordances are relevant to what situations.

**Research references:**
- Hebb, D.O. (1949). *The Organization of Behavior*. Wiley.
- Total Affordance Field spec: "Hebbian associations learn from outcomes across sessions."

**Predictive import:**
- Count growing over hours: system is learning new associations
- Count plateauing: exploration has settled, associations are stable
- Count very high (>100) with low diversity: many associations formed but most between the same few cues and capabilities
- Target: >=10 after 12h, >=20 after 24h (from P3 prediction)

#### 4.3.3 Recruitment Diversity (expanded P4)

##### Metric: `hapax_recruitment_diversity`

**What it measures:** Standard deviation of recruitment confidence scores across all affordances that were recruited in the last 10 minutes. Low std_dev = all affordances recruited at similar confidence (uniform, healthy competition). Very low std_dev with high mean = winner-take-all collapse.

**Theoretical import:** Biased competition (Desimone & Duncan, 1995) predicts that attention mechanisms should produce a winner while suppressing competitors. But healthy competition requires that the suppression is contextual — different impingements should recruit different winners. If the same affordance wins every competition regardless of context, the system has collapsed into exploitation.

The lateral suppression in the pipeline (`SUPPRESSION_FACTOR = 0.3`) ensures runners-up are penalized, but not eliminated. Diversity measures whether this suppression is producing contextual variation or monotonic dominance.

**Predictive import:**
- std_dev > 0.03: healthy variation (from P4 prediction)
- std_dev < 0.01 sustained: winner-take-all collapse — one affordance dominates all recruitment
- std_dev > 0.15: extreme variation — pipeline may be unstable (poor embedding quality)

#### 4.3.4 Imagination Narrative Diversity

##### Metric: `hapax_imagination_narrative_diversity`

**What it measures:** Rolling embedding variance of the last 20 imagination fragment narratives. Each narrative is embedded via nomic-embed-text-v2-moe (768-dim). The mean pairwise cosine distance indicates how diverse the imagination's output has been.

**Theoretical import:** With the expanded DMN context (weather, time, music, goals, fortress), imagination should produce more diverse narratives than when it only saw activity/stress/heart_rate. This metric directly tests the Bachelardian hypothesis: more material → richer imagination. If the expanded context does not increase narrative diversity, either the context isn't reaching the LLM (check assemble_context), or the LLM is ignoring it (check system prompt effectiveness).

**Research references:**
- Bachelard, G. (1943). Material imagination requires material.
- Total Affordance Field spec §2.3: "Expanding the DMN's sensor layer completes the Bachelardian commitment."

**Predictive import:**
- Mean cosine distance > 0.3: diverse imagination (healthy)
- Mean cosine distance < 0.15: imagination is repeating itself (convergence detection should be firing)
- Increase after world perception deployment: confirms Bachelard hypothesis
- Sudden drop: context assembly may have broken (check sensor promotion)

---

### 4.4 Structural Section (days)

#### 4.4.1 Cross-Domain Co-Recruitment

##### Metric: `hapax_cross_domain_cooccurrence{domain_a="...", domain_b="..."}`

**What it measures:** Count of impingements where affordances from domain_a and domain_b were both in the top-10 candidates within the same selection event. Derived from chronicle data aggregated hourly.

**Theoretical import:** Gibson's affordance theory predicts that affordances are relational — a music production session affords both `studio.mixer_energy` (sensing the sound) and `node.colorgrade` (transforming the visual palette to match the mood). Cross-domain co-recruitment is evidence that the embedding space captures these relational affordances. If domains never co-occur, the Gibson-verb descriptions may be too domain-specific (they describe the domain rather than the relation).

The Roschian analysis (spec §6) predicts domain boundaries are "prototypical centers of a radial category system, not exhaustive containers." Cross-domain recruitment is the architectural manifestation of this: the embedding space doesn't respect domain boundaries.

**Research references:**
- Gibson, J.J. (1979). *The Ecological Approach to Visual Perception*.
- Rosch, E. (1978). Principles of Categorization.
- Total Affordance Field spec §6: "Domains organize registration and dispatch; the embedding space organizes recruitment."

**Predictive import:**
- `studio` × `node` co-occurrence: music activity recruits both perception and visual expression (expected)
- `body` × `system` co-occurrence: biometric signals recruit system awareness (expected for stress detection)
- No co-occurrence between any pair: domains are semantically isolated — embedding descriptions may need revision
- `world` × anything: open-world affordances are being discovered alongside local ones

#### 4.4.2 SEEKING Dynamics

##### Metric: `hapax_seeking_active`

**What it measures:** 0/1 indicating whether the system is in SEEKING stance. Derived from stimmung state.

##### Metric: `hapax_seeking_duration_s`

**What it measures:** Cumulative seconds in SEEKING stance over the last 24 hours.

**Theoretical import:** SEEKING enters when exploration_deficit > 0.35 with all infrastructure healthy. It represents Heidegger's Tiefe Langeweile (profound boredom) resolved into action — the system has nothing urgent but is actively looking for something interesting. The recruitment threshold halves (0.05 → 0.025), widening the semantic aperture. More distant associations are recruited.

**Predictive import:**
- SEEKING activating 2-4 times per day for 10-30 minutes each: healthy exploration rhythm
- SEEKING never activating: system is always busy or always stressed — no idle exploration
- SEEKING sustained for hours: nothing is resolving the boredom — capability_discovery may need to actually search

#### 4.4.3 Capability Discovery Events

##### Metric: `hapax_discovery_search_count`

**What it measures:** Number of times `capability_discovery` was recruited and `search()` returned non-empty results.

**Predictive import:**
- Count > 0: the meta-affordance is firing and DuckDuckGo is returning results
- Count = 0 for days: either exploration_deficit never triggers SEEKING, or the capability_discovery affordance description doesn't match any impingement narratives
- High count with no new affordances registered: discovery is searching but propose() is not acting on results (expected — consent gate)

#### 4.4.4 Eigenform Convergence

##### Metric: `hapax_eigenform_entries`

**What it measures:** Line count of `/dev/shm/hapax-eigenform/state-log.jsonl`. Each entry is a snapshot of the coupled operator-system state vector.

**Theoretical import:** Eigenforms (Kauffman, 2005) are the stable fixed points of the coupled operator-system loop: `T(x*) = x*` where T is one complete perception → cognition → expression → operator response cycle. The eigenform infrastructure logs state vectors to eventually detect convergence (deep work arrival → flow eigenform) or divergence (IR miscalibration → phantom operator).

**Research references:**
- Kauffman, L.H. (2005). Eigenform. *Kybernetes*.
- SCM concrete formalizations §4.3: Eigenform analysis.
- Observer-system circularity (Property 6).

**Predictive import:**
- Entry count growing steadily: data accumulating for future eigenform analysis
- Entry count stagnant: logger may have stopped
- This is a data accumulation metric, not yet an analysis metric — eigenform detection requires post-hoc analysis

---

## 5. Implementation Approach

### Metrics endpoint

Expand `logos/api/routes/predictions.py` `predictions_metrics()` function with additional SHM scrape sections. Each section:
1. Stat the SHM file for freshness
2. If fresh (< 120s), parse JSON and emit metrics
3. If stale, emit `NaN` or skip

For activation state metrics, read `~/.cache/hapax/affordance-activation-state.json` and emit top-30 capabilities by use_count.

For chronicle-derived metrics (recruitment count, co-occurrence, technique confidence), maintain a small in-memory rolling window (last 300s) of chronicle events, updated on each scrape.

### Dashboard provisioning

Create two Grafana dashboard JSON files in `config/grafana/dashboards/`. Provision via Grafana's file-based provisioning (`/etc/grafana/provisioning/dashboards/`).

Each dashboard uses the Prometheus data source at `:9090` with 30s scrape interval.

### Testing

- Unit tests for each SHM scrape function (mock file contents, verify Prometheus text output)
- Integration test: start logos-api, scrape `/api/predictions/metrics`, verify all metric families present
