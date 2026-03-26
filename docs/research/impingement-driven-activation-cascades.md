# Impingement-Driven Activation Cascades

**Date:** 2026-03-25
**Status:** Research synthesis — five touch points mapped to DMN-as-base-state architecture
**Purpose:** Design foundations for an AI system where a continuously-running DMN serves as base state, components/tools are activated by impingement signals with arbitrary composition determined by contextual need

---

## Architecture Being Designed

```
DMN (always running, monitoring)
  │
  ▼ impingement signal
SALIENCE GATE (relevance resolution)
  │
  ├─ resolve internally → DMN absorbs, no escalation
  │
  ▼ escalate
RECRUITMENT CASCADE (arbitrary component composition)
  │
  ├─ components selected by contextual need
  ├─ activation level graduated, not binary
  │
  ▼ resolution
DEACTIVATION → return to DMN
  (with residual activation / altered baseline)
```

---

# TOUCH POINT 1: DMN as First Responder — Relevance Resolution Without Escalation

## 1.1 Preattentive Processing and Relevance Filtering

**Mechanism:** The brain processes all available environmental information in parallel within 50-500ms, before conscious attention engages. Visual analysis is functionally divided between an early preattentive stage (spatially parallel feature coding) and a later stage requiring focused attention for feature conjunction. The basal ganglia can intercept visual information almost immediately if irrelevant, activating the thalamic reticular nucleus (TRN) to screen out extraneous stimuli per prefrontal cortex directives (Treisman & Gelade, 1980; Desimone & Duncan, 1995).

**Resolve vs. escalate:** The "contingent-capture" model (Folk et al., 1992) establishes that current intentions/goals modulate preattentive speed — stimuli matching goal-relevant features are processed faster, others are filtered. The decision is not made by a central executive but by the match between stimulus features and an active attentional set. No match = resolved by filtering. Match = escalated to attentive processing.

**Threshold:** Salience (bottom-up pop-out) interacts with relevance (top-down attentional set). A stimulus must exceed either the salience threshold OR match the relevance template to survive filtering.

**Design mapping:** The DMN maintains an active "attentional set" — a specification of what kinds of signals matter right now. Incoming signals are matched against this set in parallel, at the preattentive layer. Most signals are absorbed (filtered) without escalation. Only signals that match the attentional set or exceed a raw salience threshold propagate to the salience gate.

Sources: [Pre-attentive processing (Wikipedia)](https://en.wikipedia.org/wiki/Pre-attentive_processing), [Brain Uses Filters Not Spotlight (Quanta)](https://www.quantamagazine.org/to-pay-attention-the-brain-uses-filters-not-a-spotlight-20190924/), [Preattentive Processing in Vision (Treisman)](https://www.sciencedirect.com/science/article/abs/pii/S0734189X85800049)

---

## 1.2 Mismatch Negativity (MMN) — Automatic Change Detection

**Mechanism:** The MMN is an event-related potential (ERP) that fires 100-250ms after a deviant stimulus breaks an established auditory pattern, without requiring attention. It is generated in temporal and frontal cortex, peaks at ~5 microV, and operates on a memory trace of the preceding standard pattern (Naatanen et al., 1978; Garrido et al., 2009).

**Two competing accounts:**
1. **Neural adaptation hypothesis:** Repeated standards fatigue feature-selective neurons; deviants activate fresh neurons, producing a differential response. This is a passive mechanism — the "detection" is a side effect of adaptation.
2. **Sensory memory / comparator hypothesis:** The brain actively maintains a memory trace of the standard pattern and generates MMN when incoming input mismatches the trace. This is an active, model-based mechanism.

Modern consensus: MMN is a compound of both — an early sensorial non-comparator component and a later cognitive comparator component, separable in time.

**Resolve vs. escalate:** Small deviations produce MMN but do not capture attention (resolved at the preattentive level). Large deviations or deviations in multiple features trigger an involuntary attention switch — the P3a component follows MMN and marks attentional capture (escalation).

**Threshold:** The magnitude of the prediction error (deviance from the standard) determines escalation. Subthreshold deviations are logged but not escalated.

**Design mapping:** This is the core impingement mechanism. The DMN maintains a predictive model of "what should be happening." When incoming signals deviate from the model, the deviation magnitude determines the response: small deviations update the model internally (resolve), large deviations trigger the salience gate (escalate). The compound mechanism (adaptation + comparator) maps to having both a fast statistical detector and a slower model-based comparator.

Sources: [MMN underlying mechanisms (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2671031/), [Making Sense of MMN (Frontiers)](https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2020.00468/full), [MMN (Wikipedia)](https://en.wikipedia.org/wiki/Mismatch_negativity)

---

## 1.3 Cocktail Party Effect — Automatic Name Detection

**Mechanism:** During selective listening, the unattended channel is processed to a semantic level sufficient to detect one's own name — a well-documented behavioral and neural phenomenon (Moray, 1959; Wood & Cowan, 1995). The detection occurs in the left superior temporal gyrus (non-primary auditory cortex) with involvement of a fronto-parietal network (inferior frontal gyrus, superior parietal sulcus, intraparietal sulcus) for attention shifting.

Detection of semantic violations in unattended speech produces a late positive component (LPC), indicating that structure-building processing operates automatically even outside the primary focus of attention (Niemczak & Bhatt, 2023 — JNeurosci).

**Resolve vs. escalate:** Most unattended speech is filtered (resolved). Self-relevant tokens (own name, emotionally charged words) automatically capture attention (escalate). The mechanism is not a general semantic monitor but a specific detector for high-priority tokens — an interrupt handler for self-relevant signals.

**Threshold:** The threshold is categorical, not graded — the own-name advantage survives experimental manipulation and does not extend to merely "unexpected" words (Roer et al., 2022 — preregistered replication). This suggests a hardwired interrupt vector for self-reference, not a general novelty detector.

**Design mapping:** The DMN should maintain a set of "interrupt tokens" — high-priority patterns that always capture attention regardless of current task focus. These are not configurable in the moment; they represent constitutional-level concerns (axiom violations, safety signals, operator direct address). Everything else in the unattended channel is filtered.

Sources: [Neurophysiological Evidence (JNeurosci)](https://www.jneurosci.org/content/43/27/5045), [Preregistered Replication (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8908911/), [Cocktail Party Effect (Wikipedia)](https://en.wikipedia.org/wiki/Cocktail_party_effect)

---

## 1.4 Salience Network — The Impingement Detector

**Mechanism:** The salience network (SN), composed of the anterior insula (AI) and dorsal anterior cingulate cortex (dACC), connected via the uncinate fasciculus, serves as the brain's central impingement detector. It performs bottom-up detection of salient events AND mediates switching between the DMN and the central executive network (CEN) (Menon & Uddin, 2010; Seeley et al., 2007).

The right anterior insula is the "causal outflow hub" — it plays a critical and causal role in activating the CEN and deactivating the DMN. Granger causality analysis and TMS studies confirm the causal direction: SN drives the switch, it does not merely correlate with it (Sridharan et al., 2008).

**How it works:**
1. AI integrates threat-value and salience information from interoceptive and exteroceptive sources
2. Depending on threat level, AI connects with midcingulate cortex BEFORE stimulus encounter to tune sensitivity
3. The interaction between anterior and posterior insula moderates autonomic reactions and generates a signal to the ACC
4. ACC selectively intensifies salient stimuli requiring further cortical analysis
5. If threshold is exceeded, SN activates CEN and deactivates DMN — the system switches from monitoring to engagement

**Resolve vs. escalate:** The SN is the explicit resolve/escalate gate. Sub-threshold salience is absorbed by the SN itself (the AI adjusts sensitivity but does not trigger a network switch). Supra-threshold salience triggers the DMN→CEN switch.

**Design mapping:** The salience network maps directly to the salience gate in our architecture. It is not a simple threshold comparator but an integrative hub that:
- Receives signals from multiple modalities
- Considers current context (pre-tunes sensitivity)
- Has a nonlinear switching dynamic (not gradual — the DMN→CEN transition is a phase change)
- Is the ONLY path from DMN to active engagement

Sources: [Saliency, switching, attention and control (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2899886/), [Salience Network (Wikipedia)](https://en.wikipedia.org/wiki/Salience_network), [Anterior insula as gatekeeper (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S0149763422002251), [SN responsible for DMN-CEN switching (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S1053811914004170)

---

## 1.5 Interrupt-Driven vs. Polling — CS Parallels

**Mechanism:** In polling, the CPU continuously checks device status registers, consuming cycles whether or not anything has changed. In interrupt-driven I/O, devices signal the CPU only when they need attention; the CPU is free to do other work (or idle) between interrupts.

**Key insight for design:** Interrupt-driven systems are more efficient but require:
1. An interrupt controller (maps to salience network)
2. Priority levels (maps to graduated activation)
3. Interrupt service routines (maps to recruited components)
4. The ability to mask/disable interrupts during critical sections (maps to attentional suppression during deep engagement)

The hybrid approach is most relevant: high-frequency, low-priority signals are polled (batched); high-priority signals are interrupt-driven. This matches the biological system — the DMN does low-frequency environmental polling while maintaining interrupt sensitivity for high-priority signals.

**Design mapping:** The DMN operates in a hybrid mode: continuous low-rate polling of environmental state (situation model maintenance), with interrupt sensitivity for high-priority signals. This is not pure interrupt-driven (the DMN is never truly idle) and not pure polling (it doesn't waste cycles checking every signal at full rate).

Sources: [Polling vs Interrupts (Total Phase)](https://www.totalphase.com/blog/2023/10/polling-interrupts-exploring-differences-applications/), [Interrupt vs Polling in OS (GeeksforGeeks)](https://www.geeksforgeeks.org/operating-systems/difference-between-interrupt-and-polling/)

---

## 1.6 Sentinel Hypothesis — DMN as Background Monitor

**Mechanism:** The sentinel hypothesis (Buckner et al., 2008; Hahn et al., 2007) proposes that DMN activity at rest reflects broad monitoring of the peripheral and internal environment, preparing the organism to react to upcoming stimuli or significant unpredictable events. Even at rest, the brain actively processes environmental information and maintains readiness to respond.

When presented with a task requiring focused attention, the brain directs resources to the task while temporarily suspending environmental monitoring (DMN deactivation). The DMN and task-positive network (TPN) are anticorrelated — their activity is moment-to-moment negatively correlated even at rest, and DMN deactivation scales linearly with task difficulty.

**However:** Recent work (Moerel et al., 2024 — Imaging Neuroscience) shows that DMN activation at task switches does NOT correlate with enhanced processing of the surrounding scene, suggesting the sentinel hypothesis alone doesn't explain all DMN activity. The DMN likely serves multiple functions: environmental monitoring (sentinel), self-referential processing, and situation model maintenance.

**Design mapping:** The DMN is not a single-function module. It is the base state that:
1. Monitors the environment (sentinel function)
2. Maintains the situation model (who, what, where, when)
3. Runs self-referential processing (introspection, goal maintenance)
4. Is partially suppressed — not eliminated — during active engagement

The anticorrelation with TPN is the key architectural constraint: you cannot fully monitor AND fully engage simultaneously. The salience network mediates the tradeoff.

Sources: [Sentinel role of DMN (ResearchGate)](https://www.researchgate.net/publication/50350635_The_brain's_default_mode_network_A_mind_sentinel_role), [20 years of DMN (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10524518/), [External task switches and DMN (MIT Press)](https://direct.mit.edu/imag/article/doi/10.1162/imag_a_00185/121098/External-task-switches-activate-default-mode), [DMN (Wikipedia)](https://en.wikipedia.org/wiki/Default_mode_network)

---

# TOUCH POINT 2: Recruitment Cascades — Arbitrary Component Composition

## 2.1 Biased Competition Model (Desimone & Duncan, 1995)

**Mechanism:** Multiple stimuli in the visual field compete for neural representation. Attention does not select stimuli directly — it biases the ongoing competition. Top-down signals from prefrontal and parietal cortex are fed back to extrastriate visual areas, where they bias the competition such that neurons representing the attended stimulus suppress neurons representing distractors. Both bottom-up (stimulus-driven salience) and top-down (goal-driven relevance) factors bias the competition.

**What triggers recruitment:** The competition is always running — stimuli are always competing for representation. What changes is the bias: top-down attention signals bias the competition toward task-relevant stimuli, recruiting the neural populations that represent them while suppressing others.

**Component selection:** Selection is not a discrete "pick one" operation. It is a continuous biasing process where the strongest activation pattern wins. Multiple stimuli can partially win (parallel processing) until the competition resolves into a dominant representation.

**Sequential or parallel:** Parallel at early stages (feature detection), competitive at intermediate stages (object recognition), sequential at late stages (response selection). The architecture supports parallel recruitment that converges to serial execution.

**Design mapping:** Components in our system should not be discretely selected by a central controller. Instead, all potentially relevant components should be activated in parallel with varying degrees of bias. The context (current goals, salience of the signal) provides the bias. Components that receive the strongest combined bias win the competition and get full activation. This is fundamentally different from a router that picks one tool — it is a competitive activation landscape.

Sources: [Biased Competition Theory (Wikipedia)](https://en.wikipedia.org/wiki/Biased_Competition_Theory), [Top-down and bottom-up biasing (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2740806/), [Neural mechanisms of selective attention (Desimone & Duncan)](https://pubmed.ncbi.nlm.nih.gov/7605061/)

---

## 2.2 Global Workspace Theory (Baars, 1988) — Ignition and Broadcast

**Mechanism:** The Global Neuronal Workspace (GNW) proposes two dynamic states for any incoming stimulus:
1. **Subliminal processing:** Activity propagates upward but decays progressively in higher regions — no ignition, no conscious access, no broadcast.
2. **Conscious access (ignition):** Activity cascades upward in a self-amplified manner via NMDA-mediated recurrent loops, ultimately igniting the entire workspace. Once ignited, information is broadcast to all local processors via long-range excitatory tracts connecting prefrontal and parietal cortices.

The transition between subliminal and conscious is NONLINEAR — it is all-or-none ignition, not a gradual increase. This is a phase transition.

**What triggers recruitment:** Ignition triggers broadcast. Once information enters the global workspace, it becomes available to ALL local processors — this is the recruitment mechanism. Processors do not need to be explicitly called; they receive the broadcast and self-select based on relevance.

**Component selection:** Self-selection. Each local processor receives the broadcast and determines whether the content is relevant to its function. Relevant processors engage; irrelevant ones do not. The composition is emergent, not planned.

**Design mapping:** This is the most important mechanism for arbitrary composition. After the salience gate fires:
1. The signal undergoes ignition (amplification into the workspace)
2. The amplified signal is broadcast to all available components
3. Each component self-selects based on relevance to the broadcast content
4. The composition of responding components is determined by the signal content, not by a pre-planned routing table

The ignition threshold is the key parameter — it determines what gets broadcast vs. what stays subliminal. Too low = everything gets broadcast (attentional flooding). Too high = important signals fail to ignite (attentional neglect).

Sources: [GNW Hypothesis (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8770991/), [GWT (Wikipedia)](https://en.wikipedia.org/wiki/Global_workspace_theory), [GNW from neuronal architectures to clinical applications](https://www.antoniocasella.eu/dnlaw/Dehaene_Changeaux_Naccache_2011.pdf), [Global Workspace Dynamics (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3664777/)

---

## 2.3 Neural Cascade — Hierarchical Sequential Activation

**Mechanism:** Perceptual and cognitive processing unfolds as a hierarchical cascade across cortical regions with distinct temporal dynamics. In conflict processing: ACC signals emerge first, then dlPFC (~200ms later), then mFC, then OFC. Decision-making involves at least two stages: evidence representation (early sensory areas) and evidence accumulation to decision threshold (decision-related regions). Recurrent processes generate cascades of hierarchical decisions over extended time periods (Marti et al., 2015; VanRullen & Koch, 2003).

**What triggers recruitment:** Each stage recruits the next based on output — the cascade is driven by the content flowing through it, not by a central scheduler. Higher regions are recruited only when lower regions produce output that requires further processing.

**Component selection:** Determined by the nature of the processed content. Visual content recruits V1→V2→V4→IT. Conflict content recruits ACC→dlPFC. The cascade follows established anatomical pathways but the depth of processing (how far the cascade goes) is determined by task demands.

**Design mapping:** After broadcast, components may activate sequentially in cascades: one component's output becomes the input that recruits the next. The architecture should support both parallel (broadcast-based) and sequential (cascade-based) recruitment. The depth of the cascade — how many components are activated in sequence — is determined by the complexity of the impinging signal.

Sources: [Neural cascade of conflict processing (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5365079/), [Cascade of neural processing in frontal cortex (eLife)](https://elifesciences.org/articles/12352), [Recurrent processes cascade (eLife)](https://elifesciences.org/articles/56603)

---

## 2.4 Affordance Competition Hypothesis (Cisek, 2007)

**Mechanism:** The brain does not first perceive, then decide, then act in sequence. Instead, perception continuously specifies multiple potential actions (affordances) in parallel, and these affordances compete in fronto-parietal cortex through mutual inhibition. Biasing influences from prefrontal cortex and basal ganglia resolve the competition. The strength of each affordance's representation reflects the probability it will be selected, influenced by salience, expected reward, and probability estimates.

**Key insight:** Action specification and action selection occur simultaneously and continue even during overt performance. The system is always preparing multiple possible responses.

**Design mapping:** The DMN should continuously maintain a set of "potential responses" to the current situation — not waiting for a signal to start planning, but always having partial plans ready. When impingement occurs, the competition between pre-prepared responses resolves quickly because the groundwork is already laid. This reduces latency: the system does not cold-start on impingement, it resolves a competition that was already running.

Sources: [Affordance competition hypothesis (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2440773/), [Cisek, Cortical mechanisms of action selection (Royal Society)](https://royalsocietypublishing.org/doi/abs/10.1098/rstb.2007.2054)

---

## 2.5 Predictive Processing / Active Inference — Prediction Error as Recruitment Signal

**Mechanism:** Under the predictive processing framework, the brain continuously generates predictions about incoming sensory input. Prediction errors (mismatches between predicted and actual input) drive processing: the system recruits whatever mechanisms are needed to minimize expected future prediction error. Recruitment of more complex mechanisms is licensed by necessity — a harder problem requires more sophisticated processing (Friston, 2010; Clark, 2013).

An active inference system recruits whatever mix of internal and external operations (recall from memory, accessing external tools, sensory sampling) that best minimizes expected future prediction error. This is the recruitment principle: the system uses what it needs, from wherever it can get it.

**Design mapping:** Prediction error is the universal currency of impingement. The DMN generates predictions; deviations produce prediction error; the magnitude and type of prediction error determines what gets recruited. Small prediction errors are absorbed by updating the model (internal resolution). Large prediction errors recruit additional components to resolve the discrepancy. The composition of recruited components is determined by what kind of prediction error it is — not by a routing table, but by what would reduce the error.

Sources: [Predictive Processing (ScienceDirect)](https://www.sciencedirect.com/topics/psychology/predictive-processing), [Active Predictive Coding (MIT Press)](https://direct.mit.edu/neco/article/36/1/1/118264/Active-Predictive-Coding-A-Unifying-Neural-Model), [Predictive Coding (Wikipedia)](https://en.wikipedia.org/wiki/Predictive_coding), [Reconciling predictive coding and biased competition (Frontiers)](https://www.frontiersin.org/journals/computational-neuroscience/articles/10.3389/neuro.10.004.2008/full)

---

# TOUCH POINT 3: Unified Component/Tool Interface

## 3.1 Affordance Theory (Gibson) — Tools as Perceptual Extensions

**Mechanism:** Gibson's affordance theory treats tools as extensions of the perceptual-motor system. A hammer's affordance is not an abstract property of the hammer — it is a relationship between the agent's capabilities and the tool's properties. When an agent picks up a tool, the space of perceived affordances changes: new actions become possible, and the agent directly perceives these new possibilities. Neural regions temporarily assemble to enable perception and utilization of affordances, with the dorsal visual pathway constraining motor parameters (e.g., grip shape) based on perceived object properties.

**Component vs. tool distinction:** There is no principled distinction. An affordance is a relationship between an agent and any resource (internal or external) that enables action. The brain's dorsal stream treats a hand and a hammer the same way — both are action-enabling resources with affordance signatures.

**Design mapping:** Components and tools should present the same interface: an affordance signature (what actions they enable). The system discovers what's available by perceiving affordances, not by consulting a registry. This means the interface is not "what can you do?" (capability description) but "what does this let me do?" (affordance specification relative to current context).

Sources: [Affordance (Wikipedia)](https://en.wikipedia.org/wiki/Affordance), [Affordances and neuroscience (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0149763417301276), [Mind in action (Taylor & Francis)](https://www.tandfonline.com/doi/full/10.1080/09515089.2024.2365554)

---

## 3.2 Extended Cognition (Clark & Chalmers, 1998) — Parity Principle

**Mechanism:** The parity principle states: "If, as we confront some task, a part of the world functions as a process which, were it done in the head, we would have no hesitation in recognizing as part of the cognitive process, then that part of the world IS part of the cognitive process." Otto's notebook IS his memory — it functions identically to biological memory in the relevant respects. The mind and environment form a "coupled system" that constitutes a complete cognitive system.

**Component vs. tool distinction:** The parity principle explicitly dissolves this distinction. If an external process functions like an internal one, it IS cognitive — not a "tool used by" the cognitive system, but a constituent part OF the cognitive system. The boundary between agent and tool is functional, not physical.

**Design mapping:** In our architecture, there should be no architectural distinction between "internal components" (e.g., the situation model, the salience gate) and "external tools" (e.g., Qdrant search, web search, file operations). They should share the same interface, the same activation dynamics, and the same deactivation dynamics. The system should not know or care whether a capability is "internal" or "external" — only whether it is currently coupled and available.

Sources: [Extended Mind Thesis (Wikipedia)](https://en.wikipedia.org/wiki/Extended_mind_thesis), [Parity Argument (Cornell)](http://www.philosophy-online.de/pdf/cogextension.pdf), [What is extension of extended mind (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5686289/)

---

## 3.3 Ready-to-Hand (Heidegger) — Tool Transparency and Breakdown

**Mechanism:** Heidegger's analysis of equipment use identifies two modes:
1. **Ready-to-hand (Zuhandenheit):** When a tool functions smoothly, it withdraws from consciousness. The skilled carpenter does not experience the hammer as an object — it is phenomenologically transparent, an invisible extension of agency. The tool's being IS its functioning; it is most itself when it disappears.
2. **Present-at-hand (Vorhandenheit):** When the tool breaks, goes missing, or gets in the way, it becomes conspicuous — it shifts from transparent extension to opaque object requiring theoretical attention.

The critical insight: breakdown discloses the background whole — the task, the workshop, the practices — that normally recede from attention. The network of equipment relations becomes visible only when something goes wrong.

**Design mapping:** This provides the deactivation criterion for successfully integrated tools. A well-functioning component should be invisible to the system's reflective processes — it operates transparently in the background. It only becomes a focus of attention when it breaks down (errors, timeouts, unexpected output). The monitoring system should track component health not by constantly checking each component (polling) but by detecting breakdowns (interrupt-driven). A breakdown triggers the component's shift from ready-to-hand to present-at-hand — it becomes a focus of diagnostic attention.

Sources: [Ready-to-hand and present-at-hand (Eternalised)](https://eternalisedofficial.com/2021/02/02/ready-to-hand-and-present-at-hand-heidegger/), [Transition from ready-to-hand to unready-to-hand (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2834739/), [Heidegger (Stanford Encyclopedia)](https://plato.stanford.edu/entries/heidegger/)

---

## 3.4 LLM Function Calling — Protocol-Agnostic Tool Interface

**Mechanism:** Recent work on ToolRegistry (2025) demonstrates a protocol-agnostic architecture for LLM tool integration built around three principles: protocol agnosticism, developer simplicity, and execution efficiency. Tools from different sources (Python functions, MCP tools, OpenAPI services, LangChain tools) are normalized into a unified ToolCall representation through automated schema generation. A three-layer architecture handles tool invocations from API request to formatted response. Experimental results show 60-80% code reduction and up to 3.1x performance improvement over per-protocol integration.

**Design mapping:** The unified tool interface already exists in LLM engineering. The insight from biology is that the interface should go further: tools should not just share a calling convention (JSON schema) but should share an affordance representation — what they enable in context. The ToolRegistry approach is necessary infrastructure but insufficient for impingement-driven activation. Tools need to be discoverable by the recruitment cascade, not just callable by a planner.

Sources: [Unified Tool Integration for LLMs (arXiv)](https://arxiv.org/abs/2508.02979), [ToolRegistry (arXiv)](https://arxiv.org/html/2507.10593v1)

---

## 3.5 Service Mesh — Dynamic Capability Discovery

**Mechanism:** In microservices architecture, service discovery is the mechanism by which a service finds another service at runtime. Services register themselves in a service registry; clients discover services either directly (client-side discovery) or through a load balancer/router (server-side discovery). Service meshes add a sidecar proxy pattern that abstracts network infrastructure, providing standardized service-to-service communication. New instances join the system without manual intervention; removed instances are automatically deregistered.

**Design mapping:** Service mesh provides the infrastructure model. Components register their affordances (not just their endpoints). The recruitment cascade discovers components by affordance match, not by name lookup. Components can be dynamically added or removed without architecture changes. The sidecar pattern maps to a thin activation wrapper around each component that handles registration, health reporting, and graceful deactivation.

Sources: [Service Discovery Patterns (Solo.io)](https://www.solo.io/topics/microservices/microservices-service-discovery), [Service Discovery in Microservices (Baeldung)](https://www.baeldung.com/cs/service-discovery-microservices)

---

## 3.6 Object-Capability Model — Capability as Unforgeable Token

**Mechanism:** In capability-based security, a capability is a communicable, unforgeable token of authority that references an object along with its access rights. Capabilities are created at activation time from two sources: capabilities already in the procedure and actual parameters provided by the caller. The principle of least privilege governs: each process receives only the capabilities it needs.

**Design mapping:** When the recruitment cascade activates a component, it passes capabilities as unforgeable tokens — the component can only access what the cascade explicitly grants. This provides consent-aware activation: components cannot self-activate or access resources beyond what the impingement context authorizes. This maps directly to the consent architecture (axiom: interpersonal_transparency) — activation carries an explicit scope of authority.

Sources: [Capability-based security (Wikipedia)](https://en.wikipedia.org/wiki/Capability-based_security), [Object-capability model (Wikipedia)](https://en.wikipedia.org/wiki/Object-capability_model)

---

# TOUCH POINT 4: Graduated Activation — The Middle Ground

## 4.1 Yerkes-Dodson Law — Arousal-Performance Curve

**Mechanism:** Performance increases with arousal up to an optimum, then decreases — the inverted U. Critically, the optimal arousal level depends on task complexity: simple/well-learned tasks benefit from high arousal (monotonic relationship); complex/novel tasks have a lower optimum and degrade faster under high arousal. The upward portion reflects the energizing effect of arousal; the downward portion reflects narrowing of attention ("tunnel vision"), memory impairment, and degraded problem-solving under excessive arousal (Yerkes & Dodson, 1908).

**What determines activation level:** Task complexity interacts with arousal to determine the optimal activation level. The system must match activation intensity to task demands — not just "activate" but "activate to the right degree."

**Design mapping:** Component activation should be graduated by task complexity. Simple, well-practiced operations (template responses, cached lookups) can run at high activation (fast, narrow). Complex, novel operations (reasoning, creative composition) require moderate activation (slower, broader). Over-activation of complex operations degrades performance — the system should resist the impulse to throw maximum resources at every problem.

Sources: [Yerkes-Dodson law (Wikipedia)](https://en.wikipedia.org/wiki/Yerkes%E2%80%93Dodson_law), [Arousal and performance (Trends in Cognitive Sciences)](https://www.cell.com/trends/cognitive-sciences/fulltext/S1364-6613(24)00078-0)

---

## 4.2 Allostatic Load — Graduated Stress Response

**Mechanism:** The stress response is a graduated cascade: first the sympathetic-adrenal-medullary (SAM) axis releases catecholamines (fast, ~seconds), then the hypothalamic-pituitary-adrenal (HPA) axis produces glucocorticoids (slower, ~minutes). Both hormones are protective in the short run (adaptation, homeostasis maintenance) but damaging over extended duration (allostatic load). McEwen and Wingfield distinguish Type 1 overload (energy demand exceeds supply — triggers emergency response) from Type 2 overload (chronic psychosocial stressor — no emergency but persistent wear).

**What determines activation level:** The duration and nature of the stressor. Acute stressors get a fast, intense response that resolves quickly. Chronic stressors produce sustained, moderate activation that accumulates wear (allostatic load). The system has no mechanism for "chronic moderate stress is fine" — it always pays a cost for sustained activation.

**Design mapping:** The system should track activation duration, not just activation level. Components that have been active for extended periods accumulate "allostatic load" — a metric that triggers concern about sustained resource consumption, model context exhaustion, or cognitive drift. The return-to-DMN imperative is not just about efficiency; it is about preventing cumulative degradation from sustained activation.

Sources: [Allostatic load (Wikipedia)](https://en.wikipedia.org/wiki/Allostatic_load), [Allostasis and allostatic load (Nature)](https://www.nature.com/articles/1395453), [Stressed or stressed out (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC1197275/)

---

## 4.3 Levels of Automation (Parasuraman, Sheridan & Wickens, 2000)

**Mechanism:** Automation applies to four functions: information acquisition, information analysis, decision/action selection, and action implementation. Within each function, automation ranges from fully manual (human does everything) to fully automatic (system does everything with no human involvement). The framework is a matrix: 4 function types x N levels of automation per function. Higher automation can be achieved either by automating later stages (action implementation vs. information acquisition) or by increasing the level within a stage (suggesting options vs. executing without approval).

**What determines activation level:** The level should be set independently for each function based on the specific demands of the situation. A system might be fully automated for information acquisition but fully manual for action implementation.

**Design mapping:** Each component in the recruitment cascade should have an adjustable activation level along the Parasuraman-Sheridan-Wickens dimensions. A component can be activated at the "suggest" level (information analysis only), the "recommend" level (decision support), or the "execute" level (autonomous action). The activation level is set by the impingement context: routine signals get high-autonomy activation; novel or high-stakes signals get low-autonomy activation requiring operator confirmation.

Sources: [Parasuraman, Sheridan & Wickens model (ResearchGate)](https://www.researchgate.net/publication/11596569_A_model_for_types_and_levels_of_human_interaction_with_automation), [Levels of automation (ScienceDirect)](https://www.sciencedirect.com/topics/psychology/level-of-automation)

---

## 4.4 Interrupt Priority Levels — Hardware Activation Gradient

**Mechanism:** Hardware interrupt systems implement a strict priority gradient. The VAX system, for example, supports 32 priority levels (0-31): levels 16+ for hardware interrupts, levels 0-15 for software interrupts. Higher-priority interrupts preempt lower-priority ones automatically (nested vectored interrupt control — NVIC in ARM Cortex). An interrupt at level N masks all interrupts at level <= N during its handler execution.

Three priority models exist: equal single-level (latest wins), static multilevel (priority encoder assigns fixed priorities), and dynamic multilevel (priorities reassigned per context).

**What determines activation level:** The priority level is a function of the interrupt source's inherent importance AND the current system state. Critical hardware failures get the highest priority; routine I/O gets lower priority. The priority is not just "how important is this signal" but "how important is this signal RIGHT NOW given what else is happening."

**Design mapping:** The impingement system should implement a priority scheme:
- Level 0-3: Background maintenance (polling-equivalent, runs in DMN idle cycles)
- Level 4-7: Routine signals (scheduled agent outputs, timer events)
- Level 8-11: Significant signals (operator input, environmental changes)
- Level 12-15: Critical signals (axiom violations, safety events, system failures)

Higher-priority impingements preempt lower-priority ones. An active level-10 response is interrupted by a level-12 signal but not by a level-8 signal.

Sources: [Interrupt priority level (Wikipedia)](https://en.wikipedia.org/wiki/Interrupt_priority_level), [Priority Interrupts (GeeksforGeeks)](https://www.geeksforgeeks.org/computer-organization-architecture/priority-interrupts-sw-polling-daisy-chaining/), [Linux kernel interrupts](https://linux-kernel-labs.github.io/refs/heads/master/lectures/interrupts.html)

---

## 4.5 Spreading Activation (Collins & Loftus, 1975)

**Mechanism:** Semantic concepts are represented as nodes in a network connected by bidirectional associative links of varying strength. When a node is activated (e.g., by perceiving the word "nurse"), activation spreads automatically along the links to related nodes ("doctor," "hospital," "medicine"), with the amount of spreading activation decreasing with distance and link weakness. This produces semantic priming — related words are recognized faster because their nodes are already partially activated.

**What determines activation level:** Activation level at any node is determined by: (1) the strength of the initial activation, (2) the strength of the associative link from the source, (3) the distance from the source, and (4) the decay rate. Activation is graded, not binary — a node can be slightly activated (primed), moderately activated (accessible), or fully activated (retrieved).

**Design mapping:** Components in the system exist in a semantic network connected by associative links. When an impingement signal activates one component, related components receive spreading activation — they are primed, not fully activated. This produces a readiness gradient: closely related components are nearly ready to activate; distantly related ones are slightly warmed. This reduces latency for cascade activation: when the first component's output recruits the next, that next component is already primed and activates faster.

Sources: [Spreading activation (Wikipedia)](https://en.wikipedia.org/wiki/Spreading_activation), [Collins & Loftus 1975 (APA PsycNet)](https://psycnet.apa.org/record/1976-03421-001), [Spreading activation in attractor network (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3490422/)

---

## 4.6 Graded Autonomy in Human-Robot Interaction

**Mechanism:** Robot autonomy is modeled along a 10-point taxonomy from teleoperation to full autonomy (Beer et al., 2014). Key variables that modulate the appropriate level include: acceptance, situational awareness, trust, robot intelligence, reliability, transparency, and methods of control. Adjustable autonomy frameworks use reinforcement learning to automatically adjust the robot's autonomy level based on human operator feedback, represented as a Markov Decision Process. Mixed-initiative interaction allows each agent (human and robot) to contribute what it is best suited for at the most appropriate time.

**Design mapping:** Components should have adjustable autonomy that adapts based on operator trust and past performance. A newly deployed component starts at low autonomy (report-only). As it demonstrates reliability, its autonomy increases (suggest, then act-and-report, then act-silently). Breakdowns reduce autonomy (shift to present-at-hand). This maps directly to the Parasuraman levels but adds a dynamic trust-based adjustment mechanism.

Sources: [Framework for levels of robot autonomy (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5656240/), [Levels of Autonomy for AI Agents (Knight First Amendment)](https://knightcolumbia.org/content/levels-of-autonomy-for-ai-agents-1)

---

# TOUCH POINT 5: Deactivation and Return to DMN

## 5.1 Habituation — Stimulus Repetition Reduces Response

**Mechanism:** Habituation is a decrease in behavioral response to a repeated stimulus, mediated by decreased neurotransmitter release in the activated pathways. At the neural level, this is repetition suppression — neurons responding to a repeated stimulus show progressively decreased firing. Two timescales: fast adaptation (within hundreds of milliseconds — immediate sensory adaptation) and slow adaptation (minutes to days — learned habituation).

The fatigue model proposes that the stronger a neuron's initial response, the more it decreases with repetition — proportional fatigue. This is not sensory fatigue (the sensors still detect the stimulus) but central habituation (the response system stops caring).

**Active or passive:** Primarily passive — the system stops responding due to adaptation, not due to active suppression. However, dishabituation (restoration of response to a habituated stimulus when a novel stimulus intervenes) shows that the habituated state can be overridden, implying that the adapted state is maintained by an active process that can be released.

**What persists:** The adapted state itself persists — the system does not return to its pre-habituation sensitivity immediately. Slow habituation can persist for days. This means the system's baseline shifts after habituation: the "resting state" after exposure to a repeated stimulus is different from the resting state before exposure.

**Design mapping:** Components that have been activated repeatedly for the same type of signal should habituate — decrease their response intensity and eventually stop responding, unless the signal changes. This prevents the system from endlessly reacting to a persistent but unchanging condition. The habituation state persists: after returning to DMN, the system remembers what it habituated to and does not re-activate for the same signal without a novel element (dishabituation).

Sources: [Habituation (Wikipedia)](https://en.wikipedia.org/wiki/Habituation), [Habituation revisited (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2754195/), [Neural adaptation (Wikipedia)](https://en.wikipedia.org/wiki/Neural_adaptation)

---

## 5.2 Inhibition of Return (Posner) — Don't Re-Attend the Resolved

**Mechanism:** After attention is withdrawn from a cued location, the system is inhibited from returning to that location for 500-3000ms (Posner, Rafal, Choate & Vaughan, 1985). The mechanism: after attention captures to a salient cue and finds nothing important, an "inhibitory tag" is placed on that location. Subsequent search processes avoid tagged locations, making search more efficient.

The effect is: brief enhancement (100-300ms of faster detection at the cued location) followed by prolonged impairment (500-3000ms of slower detection — the inhibition of return proper).

**Active or passive:** Active inhibition — the system actively suppresses reorienting to previously attended locations. This is not decay of activation but application of inhibitory tags.

**What persists:** The inhibitory tag persists for up to 3 seconds. Multiple tags can be maintained simultaneously (the system remembers several recently-attended locations). Tags decay over time, eventually allowing re-attending.

**Design mapping:** After the system resolves an impingement signal, an inhibitory tag is placed on that signal class. Subsequent occurrences of the same signal are suppressed (not re-processed) for a configurable refractory period. This prevents oscillation: without IOR, a resolved signal could immediately re-trigger the salience gate and cause an activation loop. The tag decays over time, allowing the signal to re-enter if it persists beyond the refractory period (indicating it wasn't actually resolved).

Sources: [Inhibition of return (Wikipedia)](https://en.wikipedia.org/wiki/Inhibition_of_return), [IOR (Scholarpedia)](http://www.scholarpedia.org/article/Inhibition_of_return), [IOR information processing theory (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0010945220304238)

---

## 5.3 Refractory Period — Recovery Time After Activation

**Mechanism:** Two kinds:
1. **Neural refractory period:** After an action potential, the neuron enters an absolute refractory period (~2ms, sodium channel inactivation — physically cannot fire) followed by a relative refractory period (~2-5ms, requires stronger stimulus to fire). This limits maximum firing rate and prevents retrograde propagation.
2. **Psychological refractory period (PRP):** After processing one stimulus, the response to a second stimulus is significantly slowed. Caused by a bottleneck in central processing — only one response selection operation can proceed at a time.

**Active or passive:** The neural refractory period is passive (ion channel physics). The PRP is structural (processing bottleneck). Neither involves active suppression; both are constraints of the processing substrate.

**What persists:** The refractory period is transient — once recovery completes, the system returns to full readiness. Unlike habituation, the refractory period does not alter the baseline; it is a temporary constraint on re-activation speed.

**Design mapping:** After a component completes processing, it enters a brief refractory period during which it cannot be re-activated. This prevents rapid re-triggering and ensures the component's output has time to propagate through the system before the component is asked to process again. The PRP maps to a system-level constraint: only N recruitment cascades can proceed simultaneously (the "semaphore" in the reactive engine is a PRP implementation).

Sources: [Refractory period (ScienceDirect)](https://www.sciencedirect.com/topics/neuroscience/refractory-period), [Psychological refractory period (Wikipedia)](https://en.wikipedia.org/wiki/Psychological_refractory_period), [Refractory periods (Kenhub)](https://www.kenhub.com/en/library/physiology/refractory-periods)

---

## 5.4 Homeostasis vs. Allostasis — Return to (Which?) Baseline

**Mechanism:** Homeostasis maintains a fixed set point through negative feedback — perturbation triggers a corrective response that restores the original value. Allostasis achieves stability through change — the set point itself moves based on anticipated demands, using feed-forward (predictive) mechanisms rather than purely reactive feedback.

Key distinction: homeostasis RETURNS to baseline; allostasis MOVES the baseline. The body elevates blood pressure during stress and returns to normal when the stressor is removed (homeostasis). But under chronic stress, the set point itself shifts — "normal" blood pressure is now higher (allostasis).

**Design mapping:** Return to DMN should be allostatic, not homeostatic. After resolving an impingement, the system should not snap back to its exact pre-impingement state. The DMN's situation model, attentional set, and prediction models should be updated by what was learned during the active phase. The "resting state" after activation is different from the resting state before activation — the system has adapted. This is critical: a purely homeostatic return would discard everything learned during activation. An allostatic return preserves the adaptation while releasing the active resources.

Sources: [Allostasis (Wikipedia)](https://en.wikipedia.org/wiki/Allostasis), [Clarifying homeostasis and allostasis (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4166604/), [Homeostasis (Wikipedia)](https://en.wikipedia.org/wiki/Homeostasis)

---

## 5.5 Task-Switching Cost — Residual Activation Persists

**Mechanism:** When switching from Task A to Task B, performance on Task B is impaired even with unlimited preparation time — "residual switch costs." Two accounts:
1. **Task-set inertia (Allport et al., 1994):** Persisting activation of the previous task set interferes with the new task set. The old task set does not fully deactivate; its residual activation competes with the new one.
2. **Failure to engage:** The new task set fails to fully activate despite preparation.

Backward inhibition: when switching A→B→A, the return to Task A is slower than switching A→B→C, because Task A was actively inhibited when switching away from it and must now overcome that inhibition (deinhibition cost).

**Active or passive:** Both. Residual activation is passive (the old task set decays slowly). Backward inhibition is active (the old task set was deliberately suppressed). The combination means that deactivation is never instantaneous or complete — there is always a residual trace of recent activation.

**What persists:** Task-set activation persists beyond voluntary control. The system cannot fully purge a recently active task set. This residual activation can be both helpful (facilitating return to a recently abandoned task) and harmful (interfering with the current task).

**Design mapping:** When the system deactivates a component and returns to DMN, residual activation from the deactivated component persists. This has two implications:
1. **Positive:** If the same signal class re-impinges shortly after, the component re-activates faster (residual priming).
2. **Negative:** The residual activation can interfere with processing of a different signal class (task-set interference). The system should account for this: when rapidly switching between different impingement types, expect degraded performance on the second type due to residual activation from the first.

The system should also implement backward inhibition: when leaving a component, actively suppress it to prevent it from interfering. But recognize that this suppression has a cost — re-activating that same component later will be slower (deinhibition cost).

Sources: [Task switching (Wikipedia)](https://en.wikipedia.org/wiki/Task_switching_(psychology)), [Residual switch costs (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0010945209002263), [Backward inhibition and deinhibition (Frontiers)](https://www.frontiersin.org/journals/behavioral-neuroscience/articles/10.3389/fnbeh.2022.846369/full)

---

# SYNTHESIS: The Complete Cycle

## Phase 1: DMN Base State (Always Running)

The DMN maintains:
- **Situation model** (who, what, where, when — continuously updated)
- **Predictive model** (what should happen next — generates expectations)
- **Attentional set** (what kinds of signals matter — configured by current goals)
- **Affordance landscape** (what actions are currently possible — pre-computed)
- **Interrupt token registry** (what always captures attention — constitutional concerns)

The DMN operates in hybrid polling/interrupt mode: low-frequency polling of environmental state with high-priority interrupt sensitivity. It is never idle; it is always monitoring, maintaining, and predicting.

## Phase 2: Impingement Detection (Salience Gate)

Impingement occurs when incoming signals deviate from the predictive model. Three detection mechanisms operate in parallel:

1. **Statistical deviation** (MMN-equivalent): Signal differs from the running average. Fast, automatic, preattentive.
2. **Pattern match** (cocktail party equivalent): Signal matches an interrupt token. Fast, automatic, bypasses salience threshold.
3. **Salience integration** (salience network equivalent): Signal properties are integrated across modalities and evaluated against current context. Slower, integrative, determines escalation threshold.

Resolve vs. escalate: Small deviations and non-matching signals are absorbed by the DMN (the predictive model is updated, the situation model is adjusted, no escalation). Signals exceeding the salience threshold or matching interrupt tokens trigger escalation.

## Phase 3: Recruitment Cascade (Arbitrary Composition)

Escalation triggers a nonlinear ignition event (GNW-equivalent). The amplified signal is broadcast to all available components. Recruitment proceeds through three concurrent mechanisms:

1. **Broadcast self-selection** (GWT): All components receive the signal; relevant ones self-activate based on affordance match.
2. **Biased competition** (Desimone-Duncan): Multiple potentially relevant components compete; context-provided bias resolves the competition.
3. **Cascade sequencing** (neural cascade): Components activate sequentially as each stage's output recruits the next.

The composition is not pre-planned — it emerges from the signal content, the available components, and the current context. Different impingement signals produce different component compositions, even from the same set of available components.

## Phase 4: Graduated Activation (Depth Control)

Each recruited component activates at a graduated level determined by:
- **Signal priority** (interrupt priority level)
- **Task complexity** (Yerkes-Dodson: simple tasks get high activation, complex tasks get moderate)
- **Component trust** (graded autonomy: reliable components get higher autonomy)
- **Automation level** (Parasuraman: information → analysis → decision → action)

Spreading activation primes related components: the activation landscape has a gradient from fully active (recruited) through primed (ready but not active) to dormant.

## Phase 5: Deactivation and Return to DMN

Resolution triggers deactivation through multiple mechanisms:
1. **Habituation**: Repeated successful resolution of the same signal type decreases response intensity
2. **Inhibition of return**: Resolved signals receive inhibitory tags preventing re-processing for a refractory period
3. **Refractory period**: Components enter a brief recovery period after processing

The return is **allostatic, not homeostatic**: the DMN's situation model, predictive model, and attentional set are updated by what was learned during activation. The baseline has shifted. Residual activation from recently active components persists, producing both positive (faster re-activation) and negative (task-set interference) effects.

---

## Key Design Principles Extracted

1. **No central router.** Composition is emergent from broadcast + self-selection + competition, not from a routing table.
2. **No binary activation.** Every component exists on a gradient from dormant → primed → partially active → fully active.
3. **Prediction error is the universal currency.** All impingement signals are prediction errors of different magnitudes and types.
4. **The DMN is never off.** It is partially suppressed during active engagement but never fully deactivated. The anticorrelation with active processing is a tradeoff, not a switch.
5. **Tools and components are the same thing.** The parity principle dissolves the distinction. Same interface, same activation dynamics, same deactivation dynamics.
6. **Return to baseline shifts the baseline.** The system after activation is not the same system as before activation. This is adaptation, not restoration.
7. **Deactivation is active, not passive.** Inhibitory tags, backward inhibition, and habituation are active processes that prevent oscillation and interference.
8. **Latency is reduced by pre-computation.** The affordance competition hypothesis means the DMN is always preparing potential responses. Impingement resolves a competition that was already running, rather than starting one.
