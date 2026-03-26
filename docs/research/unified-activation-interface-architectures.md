# Unified Activation Interface Architectures

**Date:** 2026-03-25
**Type:** Research survey
**Purpose:** Identify architectures where components, tools, sensors, and capabilities share one recruitment protocol — no distinction between "internal component" and "external tool"

---

## 1. Actor Model (Hewitt, Bishop, & Steiger, 1973)

**Activation interface:** Asynchronous message. Every actor receives messages through the same mechanism regardless of whether it represents a sensor, a computation, a storage system, or an external service. There is no type distinction at the protocol level.

**Propagation:** Point-to-point message sending. An actor, upon receiving a message, can create new actors, send messages to known actors, and determine its behavior for the next message. No broadcast — propagation is explicit and directed.

**Internal/external distinction:** None. This is the model's foundational contribution. An actor is an actor. Whether it wraps a hardware sensor or a pure computation, the interface is identical: receive message, respond.

**Activation level:** Binary. An actor either receives a message or does not. There is no graded activation — no concept of "partially activated." The actor processes one message at a time (mailbox semantics provide ordering but not prioritization in the base model).

**Runaway prevention:** Mailbox backpressure (messages queue but actor processes one at a time). No inherent mechanism to prevent cascading message storms across actor networks. Erlang/OTP adds supervisors with restart intensity limits (max N restarts in M seconds before the supervisor itself terminates), providing hierarchical circuit-breakers.

**Return to quiescence:** Actors waiting on empty mailboxes are quiescent by default. No explicit quiescence detection mechanism in the base model. Erlang supervisors can detect idle processes.

**DMN mapping:** Weak. Actors are reactive (wait for messages), which maps to TPN-style on-demand processing. No continuous background activity unless an actor sends messages to itself on a timer — which is the Hapax DMN pulse implementation pattern. The actor model provides the *protocol* for unified activation but not the *dynamics* of impingement-driven recruitment.

**Citation:** Hewitt, C., Bishop, P., & Steiger, R. (1973). A universal modular ACTOR formalism for artificial intelligence. *IJCAI*, 235-245.

---

## 2. ROS (Robot Operating System)

**Activation interface:** Publish-subscribe over named topics. Every capability — sensor, actuator, planner, SLAM module, external tool — publishes and subscribes to typed message topics. The interface is: declare what you produce, declare what you consume.

**Propagation:** Subscription-driven fan-out. A published message is delivered to all subscribers of that topic. This is implicit broadcast within a topic scope. Propagation is data-driven: a sensor publishes, and all downstream consumers activate.

**Internal/external distinction:** Effectively none at the topic level. A camera node, a planning node, and a remote web service all publish/subscribe identically. ROS2 adds QoS profiles (reliability, latency tolerance) that implicitly distinguish real-time sensors from batch processors, but the interface remains uniform.

**Activation level:** Binary per message, but *frequency-modulated*. A high-rate sensor (100Hz LiDAR) activates downstream consumers more frequently than a low-rate sensor (1Hz GPS). Activation level is encoded as publication rate, not as a scalar on individual messages. ROS2 adds message priorities and deadline QoS, providing coarse activation levels.

**Runaway prevention:** Subscriber queue depth limits. If a subscriber cannot keep up, messages are dropped (best-effort QoS) or the publisher blocks (reliable QoS). No global mechanism to prevent topic storms — a misconfigured node can flood the system.

**Return to quiescence:** Nodes spin on their subscription callbacks. Quiescence is not a system-level concept — nodes are always listening. A node with no incoming messages simply idles on its event loop.

**DMN mapping:** Moderate. The pub-sub model maps well to the DMN's multi-rate pulse: sensory ticks publish observations, evaluative ticks subscribe to accumulated observations. The lack of internal/external distinction is directly relevant. However, ROS has no concept of competitive activation — all subscribers get all messages, with no biased competition for attention.

**Citation:** Quigley, M., et al. (2009). ROS: an open-source Robot Operating System. *ICRA Workshop on Open Source Software*.

---

## 3. SOAR Cognitive Architecture (Laird, Newell, & Rosenbloom, 1987)

**Activation interface:** Production rules firing against working memory. All knowledge — perceptual, procedural, declarative — is encoded as production rules (condition-action pairs) that match against the current state of working memory. The interface is uniform: if your conditions match, you fire.

**Propagation:** Elaboration cycles. Rules fire in parallel during an elaboration phase, modifying working memory, which triggers further rule matches. This continues until *quiescence* — no more rules can fire. Then a decision procedure selects an operator from the proposed candidates.

**Internal/external distinction:** Partially collapsed. Perception, motor, and memory modules use the same buffer interface to communicate with the central production system. However, the modules themselves are structurally distinct (procedural memory, semantic memory, episodic memory, spatial-visual system). The interface is uniform; the implementations are not.

**Activation level:** Operator preferences provide graded selection. Operators are proposed with "acceptable," "better," "best," "worst," "reject," and "indifferent" preferences. The decision procedure resolves these into a single selection. This is competitive activation with explicit preference ordering.

**Runaway prevention:** Quiescence detection. The elaboration cycle terminates when no new rules fire. This is a natural fixed-point — the system converges. Impasses (no operator selectable, or tie between operators) trigger subgoaling, which creates a new problem space to resolve the impasse. This prevents infinite loops by making unresolvable states productive (they generate learning via chunking).

**Return to quiescence:** Explicitly defined. A decision cycle = elaboration until quiescence + operator selection + operator application. Quiescence is the steady-state between decisions. The system is designed to reach quiescence rapidly (millisecond elaboration cycles in practice).

**DMN mapping:** Strong. The elaboration-quiescence-decision cycle maps to the impingement-recruitment-resolution cycle. Elaboration = impingement spreading across working memory. Quiescence = the system settling before committing to action. Operator selection = recruitment of the winning capability. Chunking = learning from resolved impasses, which reduces future impasse frequency (the system gets faster at handling familiar situations). The key gap: SOAR has no continuous background process — it only runs when there is a goal to pursue.

**Citation:** Laird, J. E., Newell, A., & Rosenbloom, P. S. (1987). SOAR: An architecture for general intelligence. *Artificial Intelligence*, 33(1), 1-64. Laird, J. E. (2012). *The Soar Cognitive Architecture*. MIT Press.

---

## 4. ACT-R (Anderson, 1993; Anderson et al., 2004)

**Activation interface:** Buffer-mediated production matching. Modules (visual, aural, motor, declarative memory, goal, imaginal) communicate through buffers. Production rules match against buffer contents. The interface is: place a chunk in a buffer, and any matching production rule fires.

**Propagation:** Single production per cycle (conflict resolution selects one). But activation *spreads* through declarative memory continuously: chunks have numerical activation values determined by base-level learning (frequency + recency of access) and spreading activation from currently attended chunks. This is graded, continuous, parallel activation.

**Internal/external distinction:** None at the buffer level. The visual buffer and the declarative memory retrieval buffer have the same interface — both hold chunks, both are matched by the same production system. A perceptual module and a memory module are structurally identical from the production system's perspective.

**Activation level:** Continuous, real-valued. Every chunk has an activation value: `A_i = B_i + sum(W_j * S_ji) + noise`, where B_i is base-level activation (log of weighted recency), W_j is attentional weight of source j, and S_ji is associative strength between source j and chunk i. Higher activation = faster retrieval = more likely to be recruited. This is the most sophisticated graded activation mechanism in any cognitive architecture.

**Runaway prevention:** Activation decay. Base-level activation decays as a power law of time since last access (B_i = ln(sum(t_j^{-d}))). Without reinforcement, chunks fade. The single-production-per-cycle bottleneck prevents parallel runaway. Retrieval has a latency proportional to exp(-A_i) — low-activation chunks take longer to retrieve, providing natural throttling.

**Decay and return to quiescence:** Activation decays continuously via the power law. The system naturally returns to quiescence as unreinforced chunks fall below retrieval threshold. This is the closest analog to biological neural decay.

**DMN mapping:** Very strong. ACT-R's spreading activation is the computational equivalent of DMN-style background processing — activation spreads through associative memory even when no production is actively using a chunk. The base-level learning equation (recency + frequency) is a formal model for the DMN's "what's been relevant recently" computation. The retrieval threshold acts as a natural impingement filter — only chunks with sufficient activation break through into processing, which is exactly the impingement model. The key insight: ACT-R's activation equation is the mathematical core of what "impingement signal strength" means.

**Citation:** Anderson, J. R. (1993). *Rules of the Mind*. Lawrence Erlbaum. Anderson, J. R., et al. (2004). An integrated theory of the mind. *Psychological Review*, 111(4), 1036-1060.

---

## 5. Blackboard Architecture (Erman et al., 1980; Hayes-Roth, 1985)

**Activation interface:** Shared workspace (the blackboard). Knowledge sources (KS) monitor the blackboard and self-activate when they can contribute. The interface is: read the blackboard, decide if you can contribute, write your contribution.

**Propagation:** Opportunistic. No fixed execution order. A KS activates when the blackboard state matches its preconditions. Each KS contribution modifies the blackboard, potentially triggering other KSs. This is cascading activation driven by shared state.

**Internal/external distinction:** None by design. Any knowledge source — whether a speech recognizer, a syntactic parser, a semantic analyzer, or an external database query — registers with the same blackboard interface. The blackboard neither knows nor cares about the implementation of its KSs.

**Activation level:** In basic blackboard systems, binary (a KS either triggers or not). Hayes-Roth's BB1 architecture added meta-level control: a separate control blackboard where KSs bid for execution priority, providing graded activation through scheduling. HEARSAY-II used confidence scores on hypotheses, providing graded belief but not graded activation.

**Runaway prevention:** Scheduling. A scheduler selects which triggered KS to execute based on priority, estimated contribution, and resource constraints. Without a scheduler, multiple KSs could fire simultaneously and corrupt the blackboard. BB1's meta-control blackboard provides second-order regulation — control KSs can change the scheduling strategy when the system is stalled or thrashing.

**Return to quiescence:** When no KS preconditions match the current blackboard state, the system is quiescent. This is a natural fixed-point. However, oscillation is possible (KS-A writes X, which triggers KS-B to write Y, which triggers KS-A to write X...). No built-in oscillation detection.

**DMN mapping:** Strong. The blackboard IS the DMN buffer — a shared workspace where observations accumulate and trigger downstream processing. The self-activation of KSs maps directly to impingement-driven recruitment: capabilities activate when the situation demands them, not when explicitly called. The scheduling layer maps to the salience network's role as arbiter. BB1's meta-control (control KSs monitoring whether problem-solving is stalled) maps to the system's ability to detect and break out of ruminative loops.

**Citation:** Erman, L. D., Hayes-Roth, F., Lesser, V. R., & Reddy, D. R. (1980). The Hearsay-II speech-understanding system. *Computing Surveys*, 12(2), 213-253. Hayes-Roth, B. (1985). A blackboard architecture for control. *Artificial Intelligence*, 26(3), 251-321.

---

## 6. Subsumption Architecture (Brooks, 1986)

**Activation interface:** Continuous sensor-to-actuator wiring through augmented finite state machines (AFSMs). Each behavior layer receives raw sensor data and produces actuator commands. The interface is: read sensors, emit commands. All layers run continuously and in parallel.

**Propagation:** Layered inhibition/suppression. Higher layers can suppress lower layers' outputs or inhibit their inputs. There is no message passing between layers — only suppression of signal lines. Propagation is through the physical wiring, not through data structures.

**Internal/external distinction:** Eliminated by design. Brooks' explicit goal was to remove the boundary between perception and action. There are no internal representations — behavior emerges from direct sensor-actuator coupling. Every "component" is a behavior that couples to the world.

**Activation level:** All layers are always active (continuous parallel execution). The "activation level" is determined by which layer's output survives suppression. Higher layers subsume (override) lower layers when their conditions are met, but lower layers continue running and take over immediately when higher layers disengage.

**Runaway prevention:** Layered priority. Each layer has a fixed priority. Suppression is unidirectional (higher suppresses lower). This prevents oscillation — there is always a deterministic winner. The fixed priority ordering is both the strength (simplicity, reliability) and the weakness (no dynamic reprioritization).

**Return to quiescence:** Never. All layers run continuously. There is no quiescence — only shifting dominance between layers. The lowest layer (e.g., "avoid obstacles") is always producing output; higher layers either override it or let it through.

**DMN mapping:** Moderate but important. The always-on lowest layers map to the DMN — they run continuously, providing baseline behavior (obstacle avoidance = baseline situational awareness). Higher layers map to TPN engagement — they activate when specific conditions are met and override the baseline. The suppression mechanism maps to the DMN/TPN anti-correlation: when the TPN is active, it suppresses DMN-like baseline processing. The key insight from Brooks: **the baseline must never stop.** Hapax's DMN pulse ticks match this — they slow during TPN engagement but never cease.

**Citation:** Brooks, R. A. (1986). A robust layered control system for a mobile robot. *IEEE Journal on Robotics and Automation*, 2(1), 14-23.

---

## 7. Reactive Planning / Situated Action (Agre & Chapman, 1987)

**Activation interface:** Indexical-functional (deictic) representations. Actions are triggered by environmental affordances, not by internal goals or plans. The interface is: perceive an affordance, act on it. The representation is always relational ("the-thing-I'm-running-from") rather than absolute ("object-47").

**Propagation:** Direct environmental coupling. There is no internal propagation between components — the environment IS the medium. Action modifies the environment, which changes the affordances perceived, which triggers new actions. The propagation loop goes through the world.

**Internal/external distinction:** Deliberately abolished. Agre and Chapman's central argument is that the internal/external distinction is the source of the frame problem. By coupling action directly to perception through deictic reference, the agent never maintains an internal world model that could diverge from reality.

**Activation level:** Binary — an affordance is either perceived or not. However, the effective field of view provides implicit prioritization: affordances in the current attentional field are acted upon; others are not perceived.

**Runaway prevention:** Environmental grounding. The agent cannot hallucinate affordances — they must exist in the environment. This provides a natural constraint on activation. The agent acts only on what is actually there.

**Return to quiescence:** The agent is always active (continuous perception-action loop). There is no quiescence, only varying levels of environmental demand. In a calm environment, the agent performs low-level maintenance behaviors.

**DMN mapping:** Strong for the coupling mechanism, weak for the architecture. The deictic reference model maps directly to the impingement concept: capabilities are activated by what is *actually present* in the situation, not by internal scheduling. The "no world model" stance is too extreme for Hapax (the DMN buffer IS a world model), but the principle that activation should be driven by environmental impingement rather than internal polling is foundational.

**Citation:** Agre, P. E., & Chapman, D. (1987). Pengi: An implementation of a theory of activity. *AAAI*, 268-272.

---

## 8. Society of Mind (Minsky, 1986)

**Activation interface:** K-lines (knowledge-lines) and agent-to-agent activation. Agents are simple processes that activate or suppress other agents. The interface is: receive activation, produce activation/suppression signals to connected agents. A K-line, when activated, re-activates the constellation of agents that were active when the K-line was formed — a memory recall mechanism.

**Propagation:** Network activation spreading. An agent activates its connected agents, who activate theirs. This is parallel, distributed, and associative. Propagation is through the connection topology, not through a shared workspace.

**Internal/external distinction:** None. Agents that process sensory data and agents that perform motor actions use the same activation interface. Minsky explicitly argues that higher cognition emerges from the same mechanisms as perception and action — there is no qualitative distinction, only structural complexity.

**Activation level:** Graded through voting and inhibition. Supportive agents amplify, opposing agents suppress. The net activation of an agent is the sum of its excitatory and inhibitory inputs. This is a neural-network-like activation model.

**Runaway prevention:** Mutual inhibition and censors. Competing agents suppress each other. Minsky introduces "censors" — agents whose job is to suppress harmful or unproductive activation patterns. These are learned through experience (analogous to immune memory).

**Return to quiescence:** Not well-defined. The society is always active at some level. Minsky's model is more descriptive than computational — he does not specify a formal quiescence criterion.

**DMN mapping:** Moderate. The K-line mechanism maps to the DMN's associative memory retrieval: a cue (impingement signal) reactivates a constellation of previously-co-active agents. The graded activation through voting maps to biased competition. The lack of formal dynamics is a limitation — Minsky provides the conceptual vocabulary but not the equations.

**Citation:** Minsky, M. (1986). *The Society of Mind*. Simon & Schuster.

---

## 9. Event-Driven Architecture / Choreography

**Activation interface:** Event publication. Services emit events when state changes occur. Other services subscribe to event types they care about. The interface is: produce events, consume events. No distinction between "internal" microservice and "external" API — all communicate through the event bus.

**Propagation:** Fan-out via subscription. An event is delivered to all subscribers. Subscribers may emit new events, creating cascading activation. No central orchestrator — the event flow is determined by subscription topology.

**Internal/external distinction:** Minimized. A local microservice and a remote third-party API both publish and subscribe through the same event bus. Protocol adapters may be needed, but the logical interface is identical.

**Activation level:** Binary (event received or not). However, events can carry priority metadata, and consumers can implement priority queues. This is application-level, not architectural.

**Runaway prevention:** Dead letter queues, circuit breakers, idempotency. If a service fails repeatedly, its events go to a dead letter queue. Circuit breakers stop calling failing services. Idempotency ensures duplicate events don't cause duplicate effects. However, event storms (cascading events amplifying each other) are a known failure mode with no built-in architectural solution.

**Return to quiescence:** Services idle on their event loops when no events arrive. The system is quiescent when no events are in transit and no services are processing.

**DMN mapping:** Weak for the cognitive model, strong for the implementation pattern. Event-driven choreography is how Hapax already works (inotify-reactive engine, filesystem-as-bus). The pattern provides the *plumbing* for impingement signals but not the *dynamics* (no activation levels, no decay, no competition).

**Citation:** Hohpe, G., & Woolf, B. (2003). *Enterprise Integration Patterns*. Addison-Wesley.

---

## 10. Capability Discovery / Service Registry

**Activation interface:** Registration + discovery. Services register their capabilities (name, interface, health) in a registry. Consumers discover services at runtime by querying the registry for capabilities matching their needs. The interface is: register what you can do, discover what others can do.

**Propagation:** Pull-based. Consumers query the registry; the registry does not push. No cascading activation — a service must be explicitly discovered and invoked.

**Internal/external distinction:** The registry intentionally abstracts this away. A local service and a remote cloud API have the same registry entry format. Dynamic binding means the consumer doesn't know (or care) where the capability lives.

**Activation level:** Binary (service available or unavailable). Health checks provide a third state (degraded). No graded activation.

**Runaway prevention:** Rate limiting, health checks, circuit breakers at the consumer level.

**Return to quiescence:** Services deregister on shutdown. The registry reflects the current live population.

**DMN mapping:** Weak for cognitive dynamics. Strong for the capability registration aspect of the impingement model: every capability (internal component, external tool, sensor) registers itself through one protocol, and activation decisions can discover all available capabilities uniformly. This is the "how do you know what can be recruited?" question, not the "what triggers recruitment?" question.

**Citation:** Richardson, C. (2018). *Microservices Patterns*. Manning.

---

## 11. MCP (Model Context Protocol, Anthropic, 2024)

**Activation interface:** Tool registration via JSON-RPC. MCP servers register tools (name, description, JSON Schema parameters). MCP clients (LLM hosts) present these tools to the model, which selects and invokes them. The interface is: register a capability as a typed function, let the model decide when to call it.

**Propagation:** Model-mediated selection. The LLM evaluates which tool to invoke based on the conversation context. No cascading — each tool call is a discrete decision. However, tool results feed back into the context, potentially triggering further tool calls (agentic loops).

**Internal/external distinction:** Fully collapsed. A local file reader, a remote API, a database query, and a code execution sandbox all register identically as MCP tools. The model cannot distinguish their implementation — it sees only the schema.

**Activation level:** Implicit in the model's selection probability. The model assigns an unobservable confidence to each tool, but this is not exposed or controllable. No explicit activation levels.

**Runaway prevention:** Client-side tool call limits, human-in-the-loop confirmation, context window limits. The model can theoretically loop on tool calls indefinitely; the client enforces bounds.

**Return to quiescence:** The model stops calling tools when it determines the task is complete. This is a learned/prompted behavior, not an architectural constraint.

**DMN mapping:** Weak for dynamics, strong for the unified interface aspiration. MCP proves that erasing the internal/external tool boundary is practical and productive. But MCP is fundamentally on-demand (the model calls tools when prompted) — there is no background activation, no impingement, no continuous readiness. MCP solves the registration problem but not the recruitment problem.

**Citation:** Anthropic. (2024). Model Context Protocol Specification. https://modelcontextprotocol.io

---

## 12. OpenAI Function Calling (2023)

**Activation interface:** JSON Schema function definitions submitted with the prompt. The model selects functions to call based on conversation context. Identical in structure to MCP tools but without the server/client protocol layer.

**Propagation:** Same as MCP — model-mediated, discrete, non-cascading except through agentic loops.

**Internal/external distinction:** Fully collapsed at the schema level.

**Activation level:** Implicit in model probabilities. The `tool_choice` parameter provides coarse control (auto, required, specific function).

**Runaway prevention:** `max_tokens`, iteration limits, parallel function call limits.

**Return to quiescence:** Model's judgment.

**DMN mapping:** Same as MCP. Unified interface, no activation dynamics.

**Citation:** OpenAI. (2023). Function calling and other API updates. https://openai.com/index/function-calling-and-other-api-updates/

---

## 13. Biological Immune System — Innate/Adaptive Activation

**Activation interface:** Pattern recognition receptors (PRRs). The innate immune system uses germline-encoded receptors (TLRs, NLRs, RIG-I) that recognize pathogen-associated molecular patterns (PAMPs) and damage-associated molecular patterns (DAMPs). The adaptive immune system uses somatically recombined receptors (TCRs, BCRs) that recognize specific antigens. Both use the same downstream signaling cascades (NF-kB, interferons, cytokines).

**Propagation:** Graduated cascade. Innate recognition → cytokine release → dendritic cell activation → antigen presentation → T cell priming → B cell activation → antibody production. Each step amplifies and specializes the response. This is a recruitment cascade: each activated component recruits the next level.

**Internal/external distinction:** Profoundly absent. The immune system does not distinguish between "internal" defenses (complement, phagocytes) and "recruited external" defenses (adaptive lymphocytes). All operate through the same cytokine signaling and receptor-ligand interactions. A macrophage and a T cell use the same activation language (cytokines, MHC presentation) despite being fundamentally different cell types with different developmental histories.

**Activation level:** Continuously graded. Cytokine concentrations determine activation thresholds. A low-level infection triggers innate responses only; a high-level infection recruits adaptive immunity. The threshold is not binary — it is a concentration gradient that determines which response tiers engage.

**Runaway prevention:** Regulatory T cells (Tregs), anti-inflammatory cytokines (IL-10, TGF-beta), activation-induced cell death (AICD), complement regulators (Factor H, DAF/CD55, CD59). The immune system has an entire regulatory apparatus dedicated to preventing runaway activation (autoimmunity). DAF specifically accelerates the decay of complement convertases, preventing the complement cascade from self-amplifying indefinitely. This is decay-based quiescence: the activation signal must be continuously reinforced or it decays.

**Return to quiescence:** Active resolution. Anti-inflammatory mediators (resolvins, lipoxins) actively terminate the immune response. Memory cells persist at low activation for rapid re-recruitment. The system does not simply stop — it actively resolves, leaving a trace (memory) that enables faster future activation for the same threat.

**DMN mapping:** Very strong. This is the most complete model for impingement-driven recruitment:
- **PAMPs/DAMPs = impingement signals** (environmental perturbations that break through the baseline)
- **Innate = always-on DMN-like baseline** (fast, generic, low-cost, catches common patterns)
- **Adaptive = TPN-like recruited capability** (slow, specific, high-cost, handles novel situations)
- **Cytokine concentration = activation level** (graded, determines which tier of response engages)
- **Tregs + anti-inflammatory cytokines = suppression fields** (actively prevent runaway, enforce resolution)
- **Memory cells = learned patterns** (enable faster re-recruitment, like SOAR's chunking)
- **Active resolution (resolvins) = explicit return to quiescence** (not just cessation — active wind-down)

**Citation:** Janeway, C. A., & Medzhitov, R. (2002). Innate immune recognition. *Annual Review of Immunology*, 20, 197-216. Medzhitov, R. (2007). Recognition of microorganisms and activation of the immune response. *Nature*, 449, 819-826.

---

## 14. Complement Cascade

**Activation interface:** Sequential protease activation. Each complement component is a zymogen (inactive enzyme precursor) that is cleaved (activated) by the preceding component in the cascade. The interface is: be cleaved → cleave the next component. All 30+ complement proteins share this same activation interface.

**Propagation:** Strictly sequential cascade with amplification at each step. C1 → C4 → C2 → C3 → C5 → C6-C9 (membrane attack complex). Each activated component cleaves many copies of the next, providing exponential amplification. The cascade fans out: one C1 complex generates many C3b molecules, each of which generates many C5b molecules.

**Internal/external distinction:** None. Early components (C1, C4, C2) and late components (C5-C9) use the same protease-substrate interface. The cascade does not distinguish between "recognition components" and "effector components" — they are all zymogens activated by the same mechanism.

**Activation level:** Concentration-dependent. The number of activated molecules at each step determines whether the next step's threshold is reached. A weak initial signal may activate C1 and C4 but fail to generate enough C3b to trigger the terminal pathway. This is *analog amplification with digital thresholds at each stage*.

**Runaway prevention:** Decay accelerating factor (DAF/CD55) accelerates the dissociation of C3 convertases. Factor H competes with Factor B for C3b binding. C1 inhibitor (C1-INH) deactivates C1. CD59 prevents MAC assembly on self-cells. Each stage of the cascade has a specific inhibitor. This is *stage-gated regulation*: inhibitors at each step prevent the cascade from proceeding unless the activation signal overwhelms the inhibitor concentration.

**Return to quiescence:** Spontaneous decay. Activated complement components (especially C3b) have short half-lives and spontaneously deactivate (hydrolysis) if they don't bind a target surface. This is *inherent temporal decay*: activation is self-limiting by chemistry.

**DMN mapping:** Very strong and mechanistically precise. The complement cascade is the best model for the impingement → recruitment cascade:
- **Recognition (C1 binding) = impingement signal detection**
- **Early cascade (C1-C4-C2-C3) = progressive recruitment of assessment capability**
- **Amplification at each stage = each recruited component provides evidence that recruits the next tier**
- **Stage-gated inhibitors = each stage must overcome its own suppression threshold**
- **Threshold non-linearity = the cascade either fizzles (sub-threshold) or commits (supra-threshold)**
- **Spontaneous decay = activation is inherently temporary without continuous reinforcement**
- **MAC assembly = terminal commitment (full resource deployment, irreversible action)**

**Citation:** Merle, N. S., et al. (2015). Complement system part I — molecular mechanisms of activation and regulation. *Frontiers in Immunology*, 6, 262.

---

## 15. Global Workspace Theory (Baars, 1988) [Bonus]

**Activation interface:** Competition for broadcast. Specialized processors (modules) compete for access to a global workspace. The module that wins broadcasts its content to all other modules simultaneously.

**Propagation:** Winner-take-all broadcast. Once a module wins workspace access, its content is available to all modules. This is ignition: a non-linear transition from local processing to global availability.

**Internal/external distinction:** None at the workspace level. Perceptual modules, memory modules, motor modules, and executive modules all compete for the same workspace.

**Activation level:** Sub-threshold (local processing only, not broadcast) vs. supra-threshold (global broadcast, conscious access). The transition is non-linear: a stimulus either ignites the workspace or decays. This is the "ignition threshold" model confirmed by Dehaene et al. (2003).

**Runaway prevention:** Competition. Only one coalition of modules can occupy the workspace at a time. Broadcast is exclusive — winning the workspace suppresses competing coalitions.

**Return to quiescence:** Workspace contents decay unless reinforced. New stimuli compete for workspace access, displacing old contents.

**DMN mapping:** Strong. The ignition threshold maps directly to the impingement model: signals must reach sufficient activation to "break through" from local processing to global broadcast. The DMN's role is to maintain sub-threshold processing (local module activity) that feeds into the workspace competition. The salience network acts as the gatekeeper (which signal ignites the workspace). The TPN is what happens after ignition — focused processing on the broadcast content.

**Citation:** Baars, B. J. (1988). *A Cognitive Theory of Consciousness*. Cambridge University Press. Dehaene, S., & Naccache, L. (2001). Towards a cognitive neuroscience of consciousness. *Cognition*, 79, 1-37.

---

## 16. Biased Competition (Desimone & Duncan, 1995) [Bonus]

**Activation interface:** Competitive neural activation. Multiple stimuli activate overlapping neural populations. The representations compete through mutual suppression. Top-down bias (attention) and bottom-up salience (stimulus strength) modulate the competition.

**Propagation:** Mutual suppression + bias signal. Competing representations suppress each other. The winner suppresses losers and captures the processing resources. Top-down attention biases the competition toward task-relevant stimuli.

**Activation level:** Continuously graded. Each representation has a real-valued activation strength. Competition is proportional — a strong competitor suppresses weak ones, but two equally strong competitors can sustain prolonged competition (attentional oscillation).

**Runaway prevention:** Mutual suppression IS the prevention mechanism. Activation of one representation suppresses competing representations. The system is self-regulating: more activation in one channel means less in others (zero-sum competition).

**Return to quiescence:** When stimuli are removed, activation decays. In the absence of input, all representations decay toward baseline.

**DMN mapping:** Very strong. Biased competition is the mechanism by which impingement signals compete for recruitment. The salience router in the Hapax voice daemon is already a biased competition system. The key insight: activation is not scheduled or orchestrated — it emerges from competition between simultaneously-present signals, biased by top-down concerns (goals) and bottom-up salience (surprise/change). This is the activation DYNAMICS that the actor model, ROS, and MCP lack.

**Citation:** Desimone, R., & Duncan, J. (1995). Neural mechanisms of selective visual attention. *Annual Review of Neuroscience*, 18, 193-222.

---

## Comparative Analysis

### Activation Interface Taxonomy

| Architecture | Interface Type | Graded? | Background? | Self-Activating? |
|-------------|---------------|---------|-------------|-----------------|
| Actor Model | Message | No | No | No |
| ROS | Pub-sub topic | Frequency-modulated | Yes (continuous publish) | Yes (on subscription) |
| SOAR | Production rule match | Yes (preferences) | No | Yes (rule matching) |
| ACT-R | Buffer + activation equation | Yes (continuous) | Yes (spreading activation) | Yes (threshold retrieval) |
| Blackboard | Shared workspace match | No (BB1: yes) | No | Yes (precondition match) |
| Subsumption | Sensor-actuator wire | Suppression-modulated | Yes (all layers run) | Yes (continuous) |
| Situated Action | Affordance perception | No | Yes (continuous coupling) | Yes (environmental) |
| Society of Mind | K-line activation | Yes (voting) | Yes (parallel agents) | Yes (associative) |
| Event-Driven | Event subscription | No | No | Yes (on event) |
| Service Registry | Query-discover-invoke | No | No | No |
| MCP | Schema registration + model selection | Implicit only | No | No (model decides) |
| OpenAI Functions | Schema + model selection | Implicit only | No | No (model decides) |
| Immune System | Receptor-ligand + cytokine | Yes (concentration) | Yes (innate patrol) | Yes (pattern match) |
| Complement | Protease-substrate | Yes (concentration) | Yes (spontaneous hydrolysis) | Yes (cascade) |
| Global Workspace | Competition for broadcast | Yes (ignition threshold) | Yes (local processing) | Yes (competition) |
| Biased Competition | Mutual suppression + bias | Yes (continuous) | Yes (parallel activation) | Yes (competition) |

### Which Architecture Best Matches the Impingement-Driven Recruitment Cascade?

**Requirements of the model:**
1. Unified activation interface (no internal/external distinction)
2. Graded activation levels (not just on/off)
3. Background processing (DMN-like continuous readiness)
4. Self-activation (capabilities activate by impingement, not invocation)
5. Competitive selection (multiple capabilities compete, one wins)
6. Cascading recruitment (initial detection recruits assessment, which recruits action)
7. Active suppression of non-selected capabilities
8. Decay-based return to quiescence
9. Stage-gated regulation (runaway prevention)

**Scoring (0-2 per requirement):**

| Architecture | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | Total |
|-------------|---|---|---|---|---|---|---|---|---|-------|
| Actor Model | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 3 |
| ROS | 2 | 1 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 6 |
| SOAR | 1 | 1 | 0 | 2 | 2 | 1 | 0 | 0 | 2 | 9 |
| ACT-R | 2 | 2 | 2 | 2 | 1 | 1 | 0 | 2 | 0 | 12 |
| Blackboard | 2 | 1 | 0 | 2 | 1 | 1 | 0 | 0 | 1 | 8 |
| Subsumption | 2 | 1 | 2 | 2 | 1 | 0 | 2 | 0 | 1 | 11 |
| Situated Action | 2 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 6 |
| Society of Mind | 2 | 1 | 2 | 2 | 1 | 0 | 1 | 0 | 0 | 9 |
| Event-Driven | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 2 |
| Service Registry | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| MCP | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| Immune System | 2 | 2 | 2 | 2 | 1 | 2 | 1 | 2 | 2 | 16 |
| Complement | 2 | 2 | 1 | 2 | 0 | 2 | 0 | 2 | 2 | 13 |
| Global Workspace | 2 | 2 | 1 | 2 | 2 | 0 | 2 | 1 | 1 | 13 |
| Biased Competition | 2 | 2 | 2 | 2 | 2 | 0 | 2 | 2 | 0 | 14 |

### Winner: Biological Immune System (16/18)

The immune system is the only architecture that satisfies all nine requirements of the impingement-driven recruitment cascade model. Its specific advantages:

1. **No internal/external distinction**: Innate and adaptive effectors use the same cytokine/receptor language.
2. **Continuously graded activation**: Cytokine concentration determines response tier.
3. **Always-on background**: Innate immune cells patrol continuously (= DMN).
4. **Self-activating**: PRRs activate on pattern match, not on command (= impingement).
5. **Competitive selection**: T cells compete for antigen (affinity maturation, clonal selection).
6. **Cascading recruitment**: Innate → bridge → adaptive, each tier recruiting the next.
7. **Active suppression**: Tregs and anti-inflammatory cytokines suppress activated responses.
8. **Decay-based quiescence**: Activated cells undergo AICD, complement decays spontaneously.
9. **Stage-gated regulation**: Each cascade stage has specific inhibitors (DAF, Factor H, C1-INH).

### Synthesis: The Impingement Cascade Protocol

Drawing from the top-scoring architectures, the unified activation interface for Hapax should combine:

**From ACT-R:** The activation equation `A_i = B_i + sum(W_j * S_ji)` as the core impingement signal computation. Base-level activation (recency + frequency) plus spreading activation from currently-active concerns.

**From the immune system:** The graduated recruitment cascade with stage-gated inhibitors. Each stage must overcome its own suppression threshold before recruiting the next. The DMN is the innate system; TPN capabilities are the adaptive system.

**From biased competition:** The mutual suppression dynamics for selecting among competing capabilities. Multiple impingement signals compete; the winner suppresses the losers and captures processing resources.

**From the complement cascade:** The amplification-with-decay model. Each stage amplifies the signal but the signal decays spontaneously without reinforcement. This prevents runaway while allowing genuine threats to propagate through the full cascade.

**From SOAR:** Quiescence as the natural termination criterion. Processing continues until no new rules fire (no new capabilities are being recruited), then commits to the selected action.

**From Global Workspace Theory:** The ignition threshold. Sub-threshold impingement signals remain in local/DMN processing. Supra-threshold signals ignite global broadcast and recruit the full TPN.

**From subsumption:** The baseline never stops. Lower layers (DMN) run continuously; higher layers (TPN capabilities) activate and suppress lower layers when engaged, but lower layers resume immediately when higher layers disengage.

---

## Mapping to DMN → Impingement → Recruitment → Resolution

| Phase | Mechanism | Source Architecture |
|-------|-----------|-------------------|
| **DMN (quiescent background)** | Continuous multi-rate pulse, sensory ticks, spreading activation across memory | Subsumption (always-on layers), ACT-R (spreading activation), Immune (innate patrol) |
| **Impingement (signal detection)** | Delta detection in sensory ticks, activation exceeding retrieval threshold, PAMP-like pattern matching | ACT-R (retrieval threshold), Immune (PRR pattern recognition), Situated Action (affordance perception) |
| **Recruitment (capability activation)** | Graduated cascade: impingement → assessment capability → action capability, each stage gated by suppression threshold | Complement (sequential protease cascade), Immune (innate → adaptive recruitment), SOAR (impasse → subgoaling) |
| **Competition (selection)** | Mutual suppression among recruited capabilities, biased by top-down concerns and bottom-up salience | Biased Competition (mutual suppression + bias), GWT (workspace competition), SOAR (operator preferences) |
| **Resolution (action + quiescence)** | Selected capability executes, activation decays via power law, anti-inflammatory suppression actively terminates response | ACT-R (activation decay), Immune (resolvins, AICD, Tregs), Complement (DAF, spontaneous hydrolysis), SOAR (quiescence detection) |

---

## Sources

- [Actor model - Wikipedia](https://en.wikipedia.org/wiki/Actor_model)
- [Actor Model of Computation (Hewitt, 2010)](https://arxiv.org/vc/arxiv/papers/1008/1008.1459v8.pdf)
- [Robot Operating System - Wikipedia](https://en.wikipedia.org/wiki/Robot_Operating_System)
- [Soar Cognitive Architecture - Wikipedia](https://en.wikipedia.org/wiki/Soar_(cognitive_architecture))
- [Introduction to the Soar Cognitive Architecture (Laird, 2022)](https://arxiv.org/pdf/2205.03854)
- [The Soar Architecture Manual](https://soar.eecs.umich.edu/soar_manual/02_TheSoarArchitecture/)
- [ACT-R - Wikipedia](https://en.wikipedia.org/wiki/ACT-R)
- [ACT-R About (CMU)](https://act-r.psy.cmu.edu/about/)
- [Unit 4: Activation of Chunks and Base-Level Learning](http://act-r.psy.cmu.edu/wordpress/wp-content/themes/ACT-R/tutorials/unit4.htm)
- [Blackboard systems (Springer)](https://link.springer.com/article/10.1007/BF00140399)
- [A blackboard architecture for control (Hayes-Roth, 1985)](https://www.sciencedirect.com/science/article/abs/pii/0004370285900633)
- [Blackboard system - Wikipedia](https://en.wikipedia.org/wiki/Blackboard_system)
- [Subsumption architecture - Wikipedia](https://en.wikipedia.org/wiki/Subsumption_architecture)
- [A Robust Layered Control System for a Mobile Robot (Brooks, 1986)](https://people.csail.mit.edu/brooks/papers/AIM-864.pdf)
- [Pengi: An Implementation of a Theory of Activity (Agre & Chapman)](https://www.semanticscholar.org/paper/Pengi:-An-Implementation-of-a-Theory-of-Activity-Agre-Chapman/df7c6065060953361535afde2511725aac5cee7d)
- [Society of Mind - Wikipedia](https://en.wikipedia.org/wiki/Society_of_Mind)
- [Choreography pattern - Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/patterns/choreography)
- [Service Registry pattern](https://microservices.io/patterns/service-registry.html)
- [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Innate Immune Pattern Recognition (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5146691/)
- [Physiology, Immune Response (NCBI)](https://www.ncbi.nlm.nih.gov/books/NBK539801/)
- [Regulation of adaptive immunity by the innate immune system (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3645875/)
- [Physiology, Complement Cascade (NCBI)](https://www.ncbi.nlm.nih.gov/books/NBK551511/)
- [Complement system - Wikipedia](https://en.wikipedia.org/wiki/Complement_system)
- [Decay-accelerating factor - Wikipedia](https://en.wikipedia.org/wiki/Decay-accelerating_factor)
- [Conscious Processing and the Global Neuronal Workspace Hypothesis (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8770991/)
- [Global workspace theory - Wikipedia](https://en.wikipedia.org/wiki/Global_workspace_theory)
- [Biased competition theory - Wikipedia](https://en.wikipedia.org/wiki/Biased_competition_theory)
- [Default mode network - Wikipedia](https://en.wikipedia.org/wiki/Default_mode_network)
- [Salience network integrity predicts DMN function (PNAS)](https://www.pnas.org/doi/10.1073/pnas.1113455109)
- [Erlang Supervisor Behaviour](https://www.erlang.org/doc/system/sup_princ.html)
