# Impingement-Driven Activation Cascade — Unified Component/Tool Interface

**Status:** Design (architectural specification)
**Date:** 2026-03-25
**Builds on:** DMN Architecture, DMN-Phenomenology-Context Mapping, Impingement-Driven Activation Cascades Research, Unified Activation Interface Architectures Research
**Research base:** 5 touch points researched, 8 loose ends resolved, 14 architectural patterns evaluated

---

## 1. Problem Statement

Hapax operates as a collection of independently-triggered systems: voice daemon, fortress governor, content scheduler, sync agents, health monitor. Each has its own activation logic, its own event loop, its own context assembly. There is no unified model of what should be active, why, and at what intensity. Components are either fully on (systemd service running) or fully off (service stopped). Tools are either available (registered in MCP/function schema) or unavailable.

This specification replaces the collection model with a unified activation model where:
- The DMN is the always-on base state
- Components and tools share one interface (capabilities)
- Activation is driven by impingement (stimulus-driven, not request-driven)
- Composition is arbitrary, determined by contextual need at runtime
- Activation is graduated, not binary

## 2. The Two Poles

**DMN (base state):** Always on. Continuous background processing. Situation model maintenance, value estimation, relevance filtering. No tools active. No components demanding attention. The system is aware but not doing.

**Full activation (peak):** Everything online. Voice processing speech. Fortress deliberating. Cameras classifying. Every tool available. The system is fully engaged.

The specification defines the graduated path between them.

## 3. Capability Interface

Every capability — internal component or external tool — registers with one interface:

```python
@dataclass
class Capability:
    name: str
    affordance_signature: set[str]    # impingement types this can resolve
    activation_cost: float            # resource cost (0.0 = free, 1.0 = full GPU)
    activation_level: float = 0.0     # current: 0.0 (dormant) → 1.0 (fully active)
    consent_required: bool = False    # needs consent gate before activation
    priority_floor: bool = False      # bypasses competition (safety-critical)

    def can_resolve(self, impingement: Impingement) -> float:
        """Return activation strength (0.0 = irrelevant, 1.0 = perfect match)."""
        ...

    def activate(self, impingement: Impingement, level: float) -> Resolution:
        """Attempt to resolve the impingement at the given activation level."""
        ...

    def deactivate(self) -> None:
        """Return to dormant state. Update residual activation."""
        ...
```

There is no distinction between "component" and "tool." Speech production, camera classification, fortress governance, a Qdrant query, and a DFHack command are all capabilities with the same interface. This follows from:
- Gibson's affordance theory: tools are extensions of the perceptual-motor system
- Clark & Chalmers' parity principle: internal and external resources are functionally equivalent
- Heidegger's ready-to-hand: tools are invisible extensions until breakdown

## 4. The Five-Phase Cycle

### Phase 1: DMN Base State (Always Running)

The DMN maintains five structures continuously:

| Structure | Implementation | Update Rate |
|-----------|---------------|-------------|
| Situation model | DMN sensory tick → buffer position 0 | 5s |
| Predictive model | DMN evaluative tick → expected next state | 30s |
| Attentional set | Concern graph weights + stimmung dimensions | Per-turn |
| Affordance landscape | Registered capabilities × current context | On capability change |
| Interrupt token registry | Axiom violation patterns, operator voice timbre, safety signals | Static + learned |

The DMN is never off. During TPN-active periods, it slows (anti-correlation) but does not stop.

### Phase 2: Impingement Detection (Salience Gate)

Impingement occurs when incoming signals deviate from the DMN's predictive model. Three detection mechanisms operate in parallel:

**2a. Statistical deviation (MMN-equivalent):**
Sensor reading differs from the running average by more than a threshold. Fast, automatic, preattentive. Implemented by the DMN sensory tick's delta detection.

**2b. Pattern match (interrupt tokens):**
Signal matches a hardcoded or learned interrupt pattern. Fast, automatic, bypasses salience threshold. Examples: operator voice timbre detected, axiom T0 violation pattern, fortress population drop, stimmung stance shift to "critical."

**2c. Salience integration (salience network equivalent):**
Multi-modal signal evaluation. Combines the activation equation:

```
A_i = B_i + Σ(W_j × S_ji) + ε
```

Where:
- `B_i` = concern anchor base-level activation (power-law temporal decay)
- `W_j` = attentional weight of source j (modulated by stimmung)
- `S_ji` = associative strength (cosine similarity between signal and concern)
- `ε` = noise term (prevents deterministic habituation)

**Resolve vs. escalate:** If `A_i` < escalation threshold AND no interrupt token matched, the DMN absorbs the signal internally (updates situation model, adjusts predictions, no escalation). If `A_i` ≥ threshold OR interrupt token matched, escalate to Phase 3.

**Anti-habituation safeguard:** Alongside delta detection, absolute threshold checks run at every evaluative tick:
- `drink < population × 2` → flag regardless of delta
- `population < 3` → flag regardless of delta
- `stimmung.stance == "critical"` → flag regardless of delta
- `operator_stress > 0.8` → flag regardless of delta

These prevent vigilance decrement during extended stable-but-bad periods.

### Phase 3: Recruitment Cascade (Arbitrary Composition)

Escalation broadcasts the impingement signal to all registered capabilities. Recruitment proceeds through three concurrent mechanisms:

**3a. Broadcast self-selection (GWT):**
All capabilities receive the signal via the existing perception subscriber pattern. Each evaluates `can_resolve(impingement)` against its affordance signature. Capabilities with non-zero match enter the competition.

**3b. Biased competition (Desimone-Duncan):**
Multiple matching capabilities compete. The winner is determined by:
- `can_resolve()` score × (1 - activation_cost) × concern_weight
- Mutual suppression: activating one capability reduces the effective score of competing capabilities in the same category
- Priority floor: capabilities marked `priority_floor=True` bypass competition entirely

**3c. Cascade sequencing:**
Each activated capability's output can recruit further capabilities. The resolution of one step defines the impingement for the next:
- Audio classifier detects directed speech → recruits STT
- STT produces transcription → recruits language understanding
- Language understanding identifies operator intent → recruits appropriate response tool (speech, visual, governance action)

The composition is not pre-planned. It emerges from the signal content, available capabilities, and current context.

### Phase 4: Graduated Activation (Depth Control)

Each recruited capability activates at a graduated level:

| Level | Meaning | Example |
|-------|---------|---------|
| 0.0 | Dormant | Camera classification when no visual impingement |
| 0.1-0.3 | Primed | STT loaded but not transcribing (name-in-the-din scenario: brief activation, immediate deactivation) |
| 0.4-0.6 | Partially active | Fortress governance checking state but not deliberating |
| 0.7-0.9 | Fully engaged | Voice pipeline processing active conversation |
| 1.0 | Emergency | All capabilities at maximum, preempting lower-priority work |

The activation level is determined by:
- Signal strength (impingement magnitude)
- Task complexity (Yerkes-Dodson: moderate activation optimal for complex tasks)
- Activation cost (expensive capabilities need stronger justification)

Spreading activation primes related capabilities: when STT activates, TTS and language understanding receive elevated priming (faster re-activation if needed).

### Phase 5: Deactivation and Return to DMN

Resolution triggers deactivation through three mechanisms:

**5a. Habituation:** Repeated successful resolution of the same signal type decreases response intensity. Third time the neighbor's voice triggers the audio classifier: activation drops from 0.3 to 0.1 to 0.0.

**5b. Inhibition of return:** Resolved impingements receive an inhibitory tag. The same signal cannot re-trigger escalation for a refractory period (configurable per capability, default 30s).

**5c. Allostatic return:** The baseline shifts. The DMN's situation model now includes what was learned during activation. Residual activation persists: recently-used capabilities are primed for faster re-activation (benefit) but may interfere with unrelated processing (cost).

## 5. Speech as a Tool

Speech production (`hapax-daimonion` TTS) is a capability with the same interface as any other:

```python
speech_production = Capability(
    name="speech_production",
    affordance_signature={"verbal_response_needed", "operator_greeting", "alert_verbal"},
    activation_cost=0.3,  # GPU for TTS
    consent_required=False,
    priority_floor=False,
)
```

It gets recruited when the cascade reaches a point where the resolution requires verbal output. It does NOT activate on every impingement — only when the resolution demands speech. A visual acknowledgment, a governance action, or silence may be equally valid resolutions.

## 6. Wake Words as Impingement

Wake words are not eliminated — they are subsumed. The system detects directed speech through multimodal fusion:

| Signal | Source | Weight |
|--------|--------|--------|
| Speech detected (VAD) | Silero VAD, 30ms frames | Required |
| Operator voice (speaker ID) | Speaker embedding match | High |
| Operator present (face) | Camera face detection | High |
| Operator facing system (gaze) | Gaze direction estimate | Medium (currently unavailable) |
| Name/keyword detected | Audio pattern match | Interrupt token (highest) |

The system is always listening (DMN sensory tick reads audio classification). It detects impingement through the combination of these signals, not through a single keyword. A wake word is one signal among many — a pattern match interrupt token — not the sole gatekeeper.

## 7. Consent as Stage-Gated Inhibitor

Consent gates integrate naturally as stage-gated inhibitors in the cascade:

1. Capability receives broadcast signal
2. Capability evaluates affordance match (`can_resolve()`)
3. If `consent_required=True`: check `ConsentGatedWriter.check()` (<1ms, synchronous)
4. If consent denied: capability does not activate, signal continues to other capabilities
5. If consent granted: capability activates normally

Axiom T0 violations are checked at the signal level (salience router forces CAPABLE tier) and at the output level (axiom enforcement validates before persistence). Both are synchronous and non-blocking to the cascade.

## 8. Competing Impingements

When multiple impingement signals compete simultaneously:

1. **Normal competition:** Biased competition resolves through mutual suppression. The stronger signal wins; the weaker remains in the DMN buffer with elevated activation for subsequent processing.

2. **Priority floor signals:** Axiom violations, safety-critical events, and operator direct address bypass competition entirely. These are interrupt-level signals that preempt any current processing (analogous to hardware NMI).

3. **Capacity sharing:** When two non-conflicting signals activate non-overlapping capabilities, both proceed in parallel. Voice processing and fortress governance can coexist — they use different resources.

## 9. Integration with Existing Infrastructure

| Existing System | Role in Cascade | Changes Needed |
|-----------------|----------------|----------------|
| DMN daemon (agents/dmn/) | Phase 1: base state | Add absolute threshold checks (anti-habituation) |
| Perception subscriber (perception.py) | Phase 2-3: broadcast mechanism | Formalize capability registration interface |
| Salience router (salience_router.py) | Phase 2: activation equation | Add temporal decay, stimmung modulation, noise |
| Concern graph (concern_graph.py) | Phase 2: B_i and S_ji values | Add power-law temporal decay |
| GPU semaphore (gpu_semaphore.py) | Phase 4: resource contention | Extend to cost-weighted activation |
| Consent gate (consent_gate.py) | Phase 3: stage inhibitor | Already compatible, no changes |
| VRAM watchdog (vram-watchdog.sh) | Phase 5: deactivation | Already handles idle model unloading |
| Barge-in (cognitive_loop.py) | Phase 3: preemption | Already handles operator interrupts |
| Stimmung (stimmung.py) | Phase 2: W_j modulation | Wire stimmung dimensions as attentional weights |

## 10. What This Specification Does NOT Do

- Does not replace the voice daemon's real-time audio/cognitive loops. Those operate at 30ms/150ms for latency-critical voice interaction. The cascade operates at 5s+ for cognitive monitoring.
- Does not require a central router or orchestrator. Composition emerges from broadcast + self-selection + competition.
- Does not require new hardware. The RTX 3090 has 16GB free with the current always-on stack.
- Does not modify any existing capability's internal logic. It provides a unified ACTIVATION interface, not a unified EXECUTION interface.
- Does not implement the activation equation changes or anti-habituation safeguards. Those are implementation tasks that follow from this design.

## 11. Forcing Function

The impingement cascade is tested through the DF fortress governance scenario:

**Test:** Run fortress with the cascade active. Create a state where drink=0, no still exists, and the situation persists for 5+ game-days. Measure:
1. Does the DMN's absolute threshold check fire on drink=0? (anti-habituation)
2. Does the impingement escalate to recruit fortress governance? (broadcast + self-selection)
3. Does the governance cascade recruit the resource chain? (cascade sequencing)
4. Does the resource chain recruit the planner for workshop construction? (further recruitment)
5. Does the resolution propagate back through the cascade? (deactivation)

**Success:** The cascade detects, escalates, recruits, resolves, and deactivates within 2 game-days.
**Failure:** The system habituates to drink=0 (vigilance decrement) or activates everything simultaneously (runaway).
