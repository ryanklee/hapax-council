# Perceptual Agreement Invariants — Research Notes

> **Status:** Research (pre-design)
> **Date:** 2026-03-12
> **Scope:** New primitive in the detective layer — cross-system consistency checking
> **Builds on:** Perception primitives, governance chains, multi-source wiring

## Core Concept

Multiple perceptual systems observe a shared reality. There exist **invariants** — propositions that all competent perceptual systems must agree on. Disagreement on these invariants indicates system malfunction (broken sensor, wrong model, stale cache, spoofed input, wiring error), not genuine ambiguity.

This is distinct from sensor fusion (which blends noisy signals into a better estimate). Agreement checking asks whether the perceptual systems are **talking about the same reality** before any blending occurs.

## Three Structural Questions

### Q1: Competence Declaration

**Problem:** How does a perceptual system declare which invariants it can speak to? Not every system has an opinion on every fact. The overhead cam has no competence to assert operator presence (it sees hands, not faces).

**Current state:** Backends declare `provides` (Behavior names they write) and nothing more. No mechanism to say "I can attest to facts beyond the signals I produce." No mechanism to know that two backends are making claims about the same underlying fact.

**Answer: Propositions + Entailment Registry**

Two mechanisms, combined:

1. **Propositions as a special class of Behavior.** Certain Behaviors are designated as propositional — they represent factual claims, not continuous signals. Backends that write propositional Behaviors are implicitly declaring competence. Propositional Behaviors compose via agreement checking, not aggregation.

2. **Entailment rules** that derive propositional agreement obligations from non-propositional signals. These encode domain knowledge:
   - `emotion_arousal:face_cam` watermark advancing → entails `operator_present = True` (can't read a face that isn't there)
   - `activity_level:overhead_gear` > 0 → entails `operator_active = True`
   - `audio_energy_rms:monitor_mix` > 0 with onset → entails `studio_active = True`

   Entailment rules are declared once in the registry and apply across all sources. This keeps the backend protocol unchanged.

**Design principle:** Direct competence (backend produces the proposition) and derived competence (backend's signal logically entails the proposition) are both valid. The registry captures both.

### Q2: Compatibility Semantics

**Problem:** Agreement isn't always `==`. "In the office" and "at the workstation" are compatible (hierarchical). "In the office" and "in transit" are contradictory.

**Current factual claim types in the system:**

| Type | Examples | Agreement Semantics |
|------|----------|-------------------|
| Boolean | `operator_present`, `speech_detected`, `midi_active` | Identity (same truth value) |
| Ordinal enum | `presence_score` (4-level), `circadian_alignment` (4-level), `system_health_status` (4-level) | Proximity (within N steps on scale) |
| Categorical enum | `activity_mode` (7 values), `emotion_dominant` (8 values) | Declared compatibility matrix |
| Entailed | "face-cam emotion is fresh" → "operator present" | Logical implication check |

**Compatibility relation per invariant type:**

1. **Identity** — same value. For booleans.
2. **Proximity** — within distance threshold on ordinal scale. Threshold is a parameter of the invariant definition, not the type. `definitely_present` vs `likely_present` = compatible (distance 1). `definitely_present` vs `likely_absent` = violation (distance 3).
3. **Declared compatibility matrix** — explicit for categoricals. `coding` ↔ `research` = compatible (desk-focused knowledge work). `coding` ↔ `away` = contradictory. Matrix maintained in the registry.
4. **Entailment check** — signal S being active (watermark fresh, value non-default) implies proposition P must hold. If P is asserted False by another system while S is active, that's a violation.

### Q3: Violation Response

**Problem:** When an invariant is violated, what should the system do?

**Answer: VetoChain integration + Event emission**

Agreement violations feed into the system at two points:

1. **Event emission** (observability) — `AgreementViolation` events on a dedicated channel. Subscribers (notification system, logs, dashboards) react independently. Events carry full provenance: which invariant, which systems disagreed, what values they held.

2. **VetoChain integration** (enforcement) — each governance chain gets an `agreement_valid` veto. If any relevant invariant is violated, the veto fires and blocks downstream action. This leverages existing VetoChain properties:
   - Deny-wins semantics: if ANY invariant is violated, block
   - Audit trail: `denied_by` and `axiom_ids` show exactly why
   - Composability: different governance chains can have different agreement requirements
   - Commutativity: agreement veto composes correctly regardless of position in chain

**Why not poison watermarks:** Mutating Behavior state creates invisible fights between the producing backend and the agreement checker. The backend keeps writing "fresh" values, the checker keeps poisoning them. VetoChain integration is cleaner — the signal stays faithful to its source, the governance layer decides whether to trust it.

**Recovery:** Violations auto-clear when agreement is restored. No manual intervention for transient disagreements. Persistent disagreements (sustained > threshold duration) escalate via notification.

**Key insight:** Agreement violation has the same deny-wins semantics as VetoChain. You don't want to average disagreeing perceptions and act on the average — you want to stop acting until the disagreement resolves.

## Proposed Architecture

```
Layer 1: Invariant Registry (static config, like MCConfig/WiringConfig)
  ├─ Proposition declarations (name, type, compatibility relation)
  ├─ Competence mappings (which backends/signals → which propositions)
  └─ Entailment rules (signal S active → proposition P)

Layer 2: Agreement Checker (Tier 3 deterministic, no LLM)
  ├─ Subscribes to tick_event (same trigger as governance)
  ├─ On each tick: sample all competent signals per invariant
  ├─ Evaluate compatibility across sources
  ├─ Emit AgreementViolation events on disagreement
  └─ Maintain AgreementStatus behaviors (one per invariant)

Layer 3: Governance Integration (existing VetoChain)
  ├─ Each governance chain gets an agreement_valid veto
  ├─ Veto fires if any relevant invariant is violated
  └─ Full provenance in VetoResult

Layer 4: Recovery & Escalation
  ├─ Auto-clear when agreement restored
  ├─ Transient disagreements: log + brief action pause
  └─ Persistent disagreements: notification escalation
```

## Position in the Type System

Agreement checking is a **new primitive in the detective layer**, alongside:
- `FreshnessGuard` — "is the signal recent enough?"
- `AgreementGuard` — "are the signals consistent with each other?"
- `VetoChain` — "should we act given all constraints?"

Both FreshnessGuard and AgreementGuard are prerequisites for trusting perception before governance acts on it. They answer different failure modes:
- Stale signal → FreshnessGuard rejects
- Contradictory signals → AgreementGuard rejects
- Both fresh and consistent but violates a constraint → VetoChain rejects

## Algebraic Properties (for Hypothesis testing)

AgreementGuard should satisfy:
- **Monotonicity:** Adding a new perceptual source can only create new agreement obligations, never remove existing ones. More sources = stricter checking.
- **Symmetry:** If system A disagrees with system B, then system B disagrees with system A. (Unlike VetoChain which is order-independent but asymmetric in that vetoes only deny.)
- **Transitivity of compatibility:** If A is compatible with B, and B is compatible with C, then A must be compatible with C. (If this doesn't hold, the compatibility matrix is inconsistent and should be rejected at registry validation time.)
- **Entailment chain validity:** If S₁ entails P, and P entails Q, then S₁ entails Q. (Registry should validate no circular entailments.)

## Open Questions

1. **Granularity of invariant checking.** Should agreement be checked per-tick (on the fast cadence) or on a slower cadence? Per-tick is most responsive but adds computation. A dedicated slow-cadence group might be sufficient since disagreements are structural, not transient.

2. **Soft vs hard invariants.** Are all invariants hard (violation = full stop)? Or are some advisory (log a warning but don't block)? The design should probably support both via a severity level on the invariant definition.

3. **Quorum semantics.** When 3+ systems have competence on a proposition and 2 agree while 1 disagrees — is that a violation? Majority-wins is tempting but dangerous (2 broken sensors outvote 1 working one). Strict unanimity is safer for a single-operator system where false negatives (unnecessary action pause) are much cheaper than false positives (acting on contradictory perception).

4. **LLM agents as perceptual surfaces.** The workspace analyzer is LLM-driven. Its `activity_mode` claim is non-deterministic. Should LLM-derived propositions have lower "credibility weight" than sensor-derived ones? Or should they be held to the same agreement standard? (Credibility weighting starts to look like sensor fusion, which is explicitly not what this system is.)

5. **Entailment directionality.** "Face-cam emotion reading fresh → operator present" is a forward entailment. Should the system also support contrapositive checking? "Operator absent (from another source) → face-cam emotion should NOT be fresh." If it is fresh, either the absence claim or the emotion reading is wrong.

---

## Invariant Ontology: What Qualifies, What Doesn't, and Why

### The Inclusion Criterion

The sharpest test for whether something is an invariant: **Can the disagreement be explained by anything other than system malfunction?**

If legitimate real-world scenarios exist where the signals would diverge while everything is working correctly, it's not an invariant — it's a correlation, a soft expectation, or a design heuristic. If the only possible explanation for disagreement is that something is broken (sensor failure, model hallucination, stale cache, wiring error), then it IS an invariant.

This criterion has three corollaries:

1. **Invariants check agreement on facts, not correlation between signals.** Two signals that measure *different* physical quantities can diverge legitimately even when both are correct. Arousal and audio energy measure different things. Activity level (optical flow) and activity mode (inferred category) measure different things. Only signals that claim to observe the *same underlying fact* can form invariants.

2. **Invariants require freshness preconditions.** Most observer pairs can legitimately disagree during the gap between their respective update cycles. Face detection updates every 8s, LLM workspace analysis every 12s. During the stale window, disagreement is expected. An invariant must specify: "Given that both sources have updated within their freshness windows, they must agree." The precondition is as much a part of the invariant as the proposition.

3. **Invariants must be load-bearing.** If governance chains don't consume the signals involved, disagreement is operationally irrelevant. The registry guards governance decisions, not general-purpose consistency. An invariant earns its place by protecting a downstream action from acting on a contradictory world model.

### Identification Procedure

**Step 1: Enumerate physical facts, not signals.** The system has ~20 signals but they observe a smaller set of physical facts:

| Physical Fact | Observing Signals |
|---|---|
| Operator physically at desk | `presence_score`, `face_count`, `operator_present` (face detector), `operator_present` (LLM), `emotion_*` freshness as entailment |
| Current application in focus | `active_window_class` (Hyprland IPC), `WorkspaceAnalysis.app` (LLM screenshot) |
| Audio present in environment | `audio_energy_rms`, `vad_confidence`, `speech_detected` |
| Transport playback state | `timeline_mapping.transport`, `midi_active` (weak entailment) |

**Step 2: For each fact with 2+ observers, apply the inclusion criterion.** Ask: "If both are fresh, can they legitimately disagree?" Most candidates fall here.

**Step 3: Define the compatibility relation and preconditions.** Shape the invariant precisely.

**Step 4: Check load-bearing status.** Does governance consume these signals? If not, defer.

This procedure yields **5-8 invariants** for the current system.

### Scope of an Individual Invariant

An invariant declaration needs exactly these fields:

| Field | Purpose |
|---|---|
| **Proposition** | The factual claim, in natural language for audit logs |
| **Competent sources** | Which signals participate, with roles (direct observer, entailment source, authoritative source) |
| **Compatibility relation** | How to determine agreement (identity, proximity, implication, declared matrix) |
| **Preconditions** | When the invariant applies (freshness requirements, system state like "only when emotion backend running") |
| **Severity** | Hard (governance veto) vs advisory (log + notify) |
| **Min violation duration** | Debounce: how long disagreement must persist before firing (default: 2× slowest source's update cadence) |
| **Diagnostic hint** | What to investigate on violation |

The `min_violation_duration` field is important. A single-tick violation could be a race condition (one system updated, the other hasn't yet on this cycle). Sustained disagreement — e.g., 3 consecutive violations across 2× the slowest cadence — is a much stronger signal. Without debouncing, invariants fire spuriously during normal update interleaving.

### Scope of the Registry

The registry is bounded by: **propositions about the observable physical world that are load-bearing for governance decisions.**

**Includes:**
- Physical state of the operator (presence, broad activity category)
- Physical state of the environment (audio presence, studio gear state)
- System-level entailments (signal freshness implies physical preconditions)

**Excludes:**
- **Internal implementation consistency** — enforced by type system, unit tests, `Behavior.update()` raising on watermark regression. Not runtime invariants.
- **Historical consistency** — "the system was healthy yesterday." Audit concern, not perception agreement.
- **Predictive consistency** — "based on circadian profile, operator should be productive now." Predictions can be wrong; that's not a malfunction.
- **Correlations** — "high arousal should mean high energy." Different physical quantities that sometimes co-vary but have no obligation to agree.
- **Cross-domain invariants** — the health monitor and cockpit API also make claims about reality, but they're outside the perception engine boundary. Including them blurs architectural boundaries. (Future extension, not v1.)
- **Design-time checks** — "the overhead cam should not be wired as an emotion source." Validate this at registration/wiring time, not as a runtime invariant.

### Invariant Explosion Analysis

The criteria produce a registry that grows **linearly with the number of physical facts observed**, not quadratically with the number of signals:

- Each new backend either observes a **new** fact (adds 0 invariants — no other observer exists) or an **existing** fact (adds 1-2 invariants against existing observers).
- The competence matrix is sparse: most signals are NOT competent on most propositions.
- Most propositions have 2-3 competent observers, not N. Pairwise checks are O(1) per proposition.
- Preconditions further reduce active checks per tick (dormant when backends aren't running).

The main explosion risk is **liberal entailment**. If "signal X being fresh" can entail claims about everything, entailments multiply. Mitigation: entailments must be **logically necessary**, not statistically correlated. "Emotion fresh → face present" is logically necessary. "High audio energy → operator active" is merely common. Only necessary entailments qualify.

Estimated registry size: **8-12 invariants** for the current system, growing by 1-2 per new physical fact added.

### Taxonomy of Invariant Types

Five distinct types, each with different compatibility semantics, failure modes, and diagnostic value:

#### Type 1: Observational Agreement

Two or more sensors directly observe the same physical fact and must agree when both are fresh.

*Structure:* `source_A(fact) ↔ source_B(fact)` under freshness precondition.

*Example:* `presence_score ∈ {likely_present, definitely_present}` ↔ `LLM operator_present = True` when both updated within 15s.

*Compatibility:* Defined per-invariant (identity for booleans, proximity for ordinals, declared matrix for categoricals).

*Failure mode:* One sensor is wrong — camera occluded, LLM hallucinating, stale data slipped past watermark.

*Diagnostic value:* HIGH — localizes the disagreeing pair.

#### Type 2: Logical Entailment

One signal being in a certain state logically necessitates a fact that another signal observes.

*Structure:* `signal_A in state_X` → `proposition_P must hold`. Violation: `signal_A in state_X ∧ ¬P`.

*Example:* `emotion_valence:face_cam` watermark advancing (fresh face reading) → `face_count > 0`. Cannot read face emotion without a face.

*Compatibility:* Logical implication. Includes contrapositive: `¬P` → `signal_A should NOT be in state_X`.

*Failure mode:* The entailing system is producing data it shouldn't be able to produce (hallucination, stale cache, wiring error), or the entailed system is failing to detect what's there.

*Diagnostic value:* VERY HIGH — entailment violations indicate deep structural problems.

#### Type 3: Authoritative Override

One source is definitionally correct for a fact; other sources must defer when they claim to observe the same fact.

*Structure:* `authoritative_source(fact)` always wins. If `other_source(fact) ≠ authoritative_source(fact)`, the other source is wrong.

*Example:* Hyprland IPC for `active_window_class` is ground truth. `WorkspaceAnalysis.app` from LLM screenshot must agree. If not, the LLM is wrong.

*Compatibility:* Asymmetric — not "they disagree" but "the non-authoritative source is wrong."

*Failure mode:* LLM misclassification, screenshot lag, OCR errors.

*Diagnostic value:* MODERATE — usually means the LLM is having a bad inference.

*Note:* These might function better as **calibration checks** on the non-authoritative source rather than governance-level vetoes. The response isn't "stop trusting both" — it's "stop trusting the one that's definitely wrong."

#### Type 4: Mutual Exclusion

A combination of states that cannot co-exist in physical reality.

*Structure:* State tuple `(A, B, C)` where certain combinations are declared impossible.

*Example:* `activity_mode = "away" ∧ speech_detected = True ∧ presence_score = "definitely_present"`. If away, can't be speaking and visually present simultaneously.

*Compatibility:* Set-theoretic — membership in the set of possible state-tuples.

*Failure mode:* At least one signal is wrong, but can't immediately localize which.

*Diagnostic value:* MODERATE — identifies impossible state, doesn't localize fault.

*Explosion risk:* State-tuple space grows combinatorially. Must be limited to a small set of known-impossible configurations discovered through operational experience, not exhaustive enumeration.

#### Type 5: Temporal Continuity

A signal can't change faster than physical reality allows.

*Structure:* `|state(t) - state(t-dt)| ≤ max_rate × dt` or `transition(state_A → state_B) requires ≥ min_duration`.

*Example:* `presence_score` can't go from `definitely_present` to `likely_absent` in under 3s.

*Compatibility:* Rate-of-change bound.

*Failure mode:* Sensor glitch (brief dropout and recovery), intermittent hardware.

*Diagnostic value:* LOW for single glitches, HIGH for repeated rapid transitions (sensor instability).

**Design decision:** Type 5 is conceptually an invariant (the rate bound is a truth about physical reality), but mechanically it's different — it checks a system against its own past, not against another system. It requires state history, not cross-system comparison. **Recommend: acknowledge as related but defer to a separate `TemporalGuard` primitive.** The agreement framework is already novel enough. Type 5 could be a future extension or handled by temporal smoothing in the signal pipeline.

### The Negative Space: What Is NOT an Invariant

Equally important as what qualifies:

| Looks Like an Invariant | Why It Isn't |
|---|---|
| "High arousal should mean high energy" | Different physical quantities. A calm cellist has low arousal, high audio energy. |
| "Coding mode should have low audio" | Legitimate: music while coding, pair programming, video tutorial. |
| "Activity level should match activity mode" | Different observations: raw motion vs. inferred work category. Cat on desk = high motion, no human activity. |
| "Two emotion models should agree on arousal" | Model calibration concern, not perceptual agreement. Different models have different scales. |
| "If present 5 minutes ago, probably still present" | Probabilistic prediction, not invariant. People leave. |
| "Overhead cam shouldn't produce face-quality data" | Configuration/wiring check. Validate at registration time, not runtime. |
| "System health should be consistent over time" | Historical audit concern, not cross-system agreement. |

### LLM Agents as Perceptual Surfaces — Specific Considerations

The workspace analyzer is an LLM interpreting screenshots. Its failure modes are qualitatively different from sensors:

- **Hallucination** — seeing something that isn't there
- **Misclassification** — calling Bitwig an "IDE"
- **Non-determinism** — same input, different output on retry
- **Anchoring** — fixating on irrelevant visual details

These failure modes mean LLM-derived claims should participate in invariants but with two constraints:

1. **LLM claims should be the dependent side, not the authoritative side.** When an LLM claim disagrees with a deterministic sensor (Hyprland IPC, face detector, PipeWire), the sensor wins. This is Type 3 (Authoritative Override) — the LLM defers.

2. **LLM-vs-LLM disagreement is not an invariant violation** — it's expected non-determinism. Two LLM runs on the same screenshot might produce different `activity_mode` classifications. This isn't a system malfunction; it's the nature of the inference method. Don't register invariants between two LLM-derived signals.

### Candidate Invariants for Current System

Applying all criteria to the actual signal inventory:

| # | Type | Proposition | Sources | Compatibility | Load-Bearing? |
|---|---|---|---|---|---|
| 1 | Entailment | Face emotion fresh → face present | `emotion_*:face_cam` watermark, `face_count` | implication | Yes (governance uses both) |
| 2 | Observational | Presence signals agree on operator at desk | `presence_score`, `operator_present` (LLM) | ordinal proximity (within 1 step) | Yes (interruptibility) |
| 3 | Auth Override | App identification matches desktop manager | `active_window_class` (Hyprland), `WorkspaceAnalysis.app` | Hyprland authoritative | Indirect (activity_mode) |
| 4 | Entailment | Audio energy fresh → PipeWire operational | `audio_energy_rms:*` watermark, `pw-record` process alive | implication | Yes (MC governance) |
| 5 | Mutual Excl | Away + speaking + present is impossible | `activity_mode`, `speech_detected`, `presence_score` | state-tuple exclusion | Yes (activity classification) |
| 6 | Entailment | MIDI clock fresh → transport PLAYING | `midi_clock` watermark, `timeline_mapping.transport` | implication | Yes (MC governance) |
| 7 | Observational | Face detector and LLM agree on face count | `face_count`, `WorkspaceAnalysis.operator_present` | boolean identity | Yes (presence) |

Seven candidates. Some may be consolidated or dropped during design. This is the right order of magnitude.
