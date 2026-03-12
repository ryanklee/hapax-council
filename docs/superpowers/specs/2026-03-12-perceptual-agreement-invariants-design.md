# Perceptual Agreement Invariants — Design Spec

> **Status:** Proposed
> **Date:** 2026-03-12
> **Scope:** `agents/hapax_voice/agreement.py` — new detective-layer primitive
> **Builds on:** [Perception Primitives](2026-03-11-perception-primitives-design.md), [Governance Chains](2026-03-11-governance-design.md), [Multi-Source Wiring](2026-03-12-multi-source-wiring-design.md)

## Problem

The perception system fuses signals from multiple backends (cameras, audio, LLM workspace analysis, desktop IPC, physiological sensors) into a shared world model that governance chains act on. Currently, the only trust checks are:

- **FreshnessGuard** — rejects stale signals (watermark too old)
- **VetoChain** — rejects actions that violate domain constraints

Neither checks whether the perception systems **agree with each other about basic facts**. A Behavior can be fresh, within range, and *wrong* — contradicted by another system that also looks healthy. The governance chain would act on a contradictory world model without knowing it.

Concrete failure scenario already latent in the system: the face detector updates `face_count` on an 8s cycle, the LLM workspace analyzer updates `operator_present` on a 12s cycle. During the stale gap, `presence_score` can read "likely_absent" (from fresh VAD data) while `WorkspaceAnalysis.operator_present` reads True (from a 12s-old screenshot showing the operator). The emotion backend's freshness (it can only produce data when a face is present) entails operator presence — but nothing checks that entailment against the face detector's count. Three systems with opinions about the same physical fact, no mechanism to detect when they contradict.

## Goal

Add an **AgreementGuard** to the detective layer that:

1. Maintains a registry of **perceptual invariants** — propositions about shared reality that multiple systems must agree on
2. On each governance tick, evaluates all active invariants against current Behavior values
3. Produces an `AgreementResult` (analogous to `FreshnessResult`) that governance chains consume as a veto
4. Emits `AgreementViolation` events for observability and escalation
5. Auto-clears when agreement is restored; escalates persistent violations via notification

This is a **new primitive alongside FreshnessGuard**, not a replacement. The AgreementChecker operates at the perception engine level (subscribing to `tick_event`, reading from the full engine behaviors dict) and publishes a `Behavior[bool]` that governance chains consume through the existing alias mechanism:

```
                                    ┌─────────────────────────┐
                                    │   AgreementChecker      │
  tick_event ──────────────────────►│  reads engine.behaviors  │
                                    │  publishes agreement_ok  │──► engine.behaviors["agreement_ok"]
                                    │  emits violation events  │
                                    └─────────────────────────┘

  trigger → with_latest_from(alias) → FreshnessGuard → VetoChain(includes agreement_ok check) → FallbackChain → Schedule
```

## Design Decisions

### D1: Four invariant types, not five

**Decision:** Implement Types 1-4 (Observational Agreement, Logical Entailment, Authoritative Override, Mutual Exclusion). Defer Type 5 (Temporal Continuity) to a separate `TemporalGuard` primitive.

**Rationale:**
- Types 1-4 all share the same fundamental structure: "given freshness preconditions, these N sources must satisfy a compatibility relation at this point in time." They differ only in the compatibility function.
- Type 5 (temporal continuity) checks a system against its own past, not against another system. It requires state history, ring buffers, and rate-of-change math — a different mechanical concern. Jamming it into the agreement framework would distort the abstraction.
- Type 5's failure mode is different: sensor glitches (brief dropout and recovery) vs. the structural malfunction that Types 1-4 catch. Different responses are appropriate.
- Future `TemporalGuard` is explicitly contemplated. The invariant registry could later include temporal constraints if the two primitives prove to share enough structure.

### D2: Invariants are conditional — preconditions are first-class

**Decision:** Every invariant includes explicit preconditions that must hold before the compatibility check runs. The precondition is as much a part of the invariant as the proposition.

**Rationale:**
- Without preconditions, invariants fire spuriously during startup (not all backends initialized), shutdown (backends stopping at different times), sensor transitions (camera reconnecting), and normal update interleaving (one source updated this tick, the other hasn't yet).
- The most common precondition is freshness: "both participating signals have updated within their respective watermarks." This reuses the existing FreshnessRequirement type.
- Additional preconditions include backend availability: "only check emotion↔face agreement when the emotion backend is registered and running."
- Preconditions make invariants self-documenting: reading the precondition tells you when the check applies.

### D3: Debounced violation, not single-tick

**Decision:** An invariant fires only after sustained disagreement exceeding `min_violation_ticks` consecutive failed checks (default: 3). A single tick of disagreement is logged as a transient but does not trigger the governance veto or violation event.

**Rationale:**
- Multiple perception sources update at different cadences (VAD: 30ms, face detector: 8s, LLM workspace: 12s, emotion inference: 333ms). During the window where one source has updated and another hasn't, a single-tick disagreement is expected — it's a race condition in update scheduling, not a real contradiction.
- Requiring sustained disagreement (3 consecutive ticks at the checking cadence) filters out interleaving races while catching genuine malfunction. At a 2.5s fast tick, 3 ticks = 7.5s of sustained disagreement — well beyond any single update interleave.
- The debounce counter resets to 0 when the invariant passes, providing automatic recovery.

### D4: Strict unanimity, not quorum

**Decision:** When an invariant has 3+ competent sources, ALL must agree. No majority-wins semantics.

**Rationale:**
- This is a single-operator system where false negatives (unnecessary action pause) are dramatically cheaper than false positives (acting on contradictory perception). A vocal throw during a live recording is irreversible; pausing for 10 seconds while sensors re-converge is harmless.
- Majority-wins is dangerous: 2 broken sensors can outvote 1 working one. In a system with 3-5 perception sources, a single-point hardware failure (USB hub brownout affecting two cameras) could corrupt the majority.
- Strict unanimity means the system is maximally conservative. It stops acting when ANY source disagrees, forcing either automatic recovery (the stale source updates and agreement restores) or operator attention (persistent notification).
- This aligns with the existing VetoChain semantics: any single veto blocks. AgreementGuard adds "disagreement among sources" as another denial reason with the same deny-wins character.

### D5: LLM-derived claims participate but never as authority

**Decision:** LLM-derived signals (WorkspaceAnalysis fields) participate in invariants as the dependent side. When an LLM claim disagrees with a deterministic sensor, the sensor is authoritative. No invariants are registered between two LLM-derived signals.

**Rationale:**
- LLM vision analysis has qualitatively different failure modes from sensors: hallucination, misclassification, non-determinism, anchoring. Two runs on the same input can produce different outputs. This is expected behavior, not malfunction.
- Deterministic sensors (Hyprland IPC, face detector, PipeWire, MIDI) produce bit-identical output for the same physical state. They are the ground truth for facts they directly observe.
- Registering invariants between two LLM outputs would produce false violation events from normal inference variance. This undermines trust in the invariant system.
- Type 3 (Authoritative Override) captures this asymmetry: the sensor is the authority, the LLM is the dependent. Violation means "the LLM is probably wrong," not "something is structurally broken."

### D6: AgreementChecker at engine level, not inside governance pipeline

**Decision:** The AgreementChecker subscribes to `tick_event` at the perception engine level, reads from the full `engine.behaviors` dict, and publishes an `agreement_ok: Behavior[bool]` that governance chains consume as a standard veto.

**Rationale:**
- **Signal access problem.** The governance FusedContext is built from the alias dict (`build_behavior_alias()`), which only contains source-qualified audio/emotion signals plus a few unqualified pass-throughs (`vad_confidence`, `timeline_mapping`). It does NOT contain `face_count`, `operator_present`, `presence_score`, or `active_window_class` — all of which are needed by candidate invariants. The full `engine.behaviors` dict has `face_count` and `operator_present` directly.
- **Clean separation of concerns.** The agreement checker asks "is the world model self-consistent?" — a perception-level question. The governance chains ask "given a consistent world model, should we act?" These are different concerns at different architectural layers. The agreement checker belongs with the perception engine, not inside the governance pipeline.
- **Minimal coupling.** Governance chains add a single veto: `Veto(name="agreement_ok", predicate=lambda ctx: ctx.get_sample("agreement_ok").value)`. They don't need to know about invariant registries, compatibility functions, or debounce logic. The agreement checker's complexity is fully encapsulated.
- **Backward compatible.** If no agreement checker is wired, `agreement_ok` is simply absent from the behaviors dict. Governance chains that don't include the veto work exactly as before.
- **Prerequisite: promote `presence_score` to a Behavior.** Currently `presence_score` is a computed field on `EnvironmentState`, not a Behavior in the engine's dict. Invariants #2, #4, and #7 need to read it. The implementation must add `self._b_presence_score: Behavior[str]` to the engine and update it in `tick()`, same pattern as the existing `_b_operator_present`.

### D7: Registry is static config, not dynamic

**Decision:** The invariant registry is a frozen dataclass (like `MCConfig` or `WiringConfig`), constructed at startup from a declarative configuration. Invariants cannot be added or removed at runtime.

**Rationale:**
- Invariants represent truths about physical reality that don't change during a session. "Face emotion requires face presence" is always true. "Presence sensors should agree" is always true. There's no scenario where you'd want to add or remove an invariant while the daemon is running.
- Static configuration enables validation at construction time: check that all referenced signals exist, compatibility matrices are internally consistent (transitive), entailment graphs are acyclic.
- Matches the existing pattern: `MCConfig`, `WiringConfig`, `GovernanceBinding` are all frozen dataclasses.

### D8: Checking cadence matches governance cadence

**Decision:** Agreement checks run on the same tick that governance chains consume — the perception engine's fast tick (~2.5s). No separate cadence.

**Rationale:**
- The agreement check is a predicate evaluation, not a heavy computation. Evaluating 7-12 invariants (each a few comparisons and a freshness check) takes microseconds. No need to rate-limit.
- Checking on the governance tick ensures the agreement status is exactly current when governance acts. A separate slower cadence would introduce a window where governance sees stale agreement status.
- The debounce mechanism (D3) already prevents single-tick false positives. No additional rate-limiting needed.

## Architecture

### Type System

```python
@dataclass(frozen=True)
class InvariantSpec:
    """Declaration of a single perceptual agreement invariant."""
    name: str                          # unique identifier, e.g., "face_emotion_entails_presence"
    proposition: str                   # human-readable for audit logs
    invariant_type: InvariantType      # OBSERVATIONAL | ENTAILMENT | AUTHORITATIVE | MUTUAL_EXCLUSION
    sources: tuple[SourceRole, ...]    # participating signals with roles
    compatibility: CompatibilityFn     # how to check agreement
    preconditions: tuple[FreshnessRequirement, ...] = ()  # when the check applies
    severity: Severity = Severity.HARD # HARD (veto) or ADVISORY (log only)
    min_violation_ticks: int = 3       # debounce threshold
    diagnostic_hint: str = ""          # what to investigate on violation

class InvariantType(Enum):
    OBSERVATIONAL = "observational"    # same fact, multiple sensors
    ENTAILMENT = "entailment"          # signal A fresh → proposition P
    AUTHORITATIVE = "authoritative"    # one source is ground truth
    MUTUAL_EXCLUSION = "mutual_exclusion"  # impossible state combination

class Severity(Enum):
    HARD = "hard"          # governance veto on violation
    ADVISORY = "advisory"  # log + notify, don't block

@dataclass(frozen=True)
class SourceRole:
    """A signal's participation in an invariant, with its role."""
    behavior_name: str
    role: Role  # OBSERVER | ENTAILING | AUTHORITATIVE | DEPENDENT

class Role(Enum):
    OBSERVER = "observer"              # direct observer (Type 1)
    ENTAILING = "entailing"            # signal whose freshness entails a fact (Type 2)
    AUTHORITATIVE = "authoritative"    # definitionally correct source (Type 3)
    DEPENDENT = "dependent"            # must agree with authority (Type 3)
    PARTICIPANT = "participant"        # member of mutual exclusion set (Type 4)
```

### Compatibility Functions

```python
# Type alias — takes behaviors dict + now timestamp, returns (satisfied, diagnostic_str)
CompatibilityFn = Callable[[dict[str, Behavior], float], tuple[bool, str]]
```

Compatibility functions are plain callables that read directly from the engine's behaviors dict. Constructed from factory helpers:

```python
def identity_agreement(a: str, b: str) -> CompatibilityFn:
    """Both signals must have the same value."""

def proximity_agreement(a: str, b: str, max_distance: int, ordinal: tuple[str, ...]) -> CompatibilityFn:
    """Ordinal values must be within max_distance steps of each other."""

def freshness_entailment(signal: str, proposition: str, expected_value: object,
                         max_staleness_s: float) -> CompatibilityFn:
    """If signal's watermark is fresh (within max_staleness_s), proposition must equal expected_value."""

def authority_match(authority: str, dependent: str) -> CompatibilityFn:
    """Dependent's value must match authority's value."""

def state_exclusion(signals: tuple[str, ...],
                    impossible: frozenset[tuple[object, ...]]) -> CompatibilityFn:
    """State tuple across signals must not be in the impossible set."""
```

Note: compatibility functions receive the raw `behaviors` dict, not a FusedContext. This gives them access to all engine signals including `face_count`, `operator_present`, and `presence_score` — signals that are absent from the governance alias dict. See D6 for why this is necessary.

### AgreementChecker

```python
class AgreementChecker:
    """Evaluates perceptual agreement invariants at the perception engine level.

    Subscribes to tick_event, reads from the full engine.behaviors dict,
    maintains per-invariant debounce counters, and publishes agreement_ok
    as a Behavior for governance chains to consume.

    Operates at the engine level, not inside the governance pipeline (see D6).
    """

    def __init__(self, registry: AgreementRegistry, behaviors: dict[str, Behavior]) -> None
    def check(self, now: float) -> AgreementResult   # evaluates all invariants
    def subscribe_to_tick(self, tick_event: Event[float]) -> None  # wiring
    @property
    def agreement_ok(self) -> Behavior[bool]          # for engine.behaviors dict
    @property
    def violation_event(self) -> Event[AgreementViolation]  # for observability

@dataclass(frozen=True)
class AgreementRegistry:
    """Static registry of all perceptual agreement invariants."""
    invariants: tuple[InvariantSpec, ...]
    def __post_init__(self) -> None:  # validation: unique names, transitive compat, acyclic entailment

@dataclass(frozen=True)
class AgreementResult:
    """Outcome of checking all invariants."""
    satisfied: bool
    violations: tuple[InvariantViolation, ...] = ()

@dataclass(frozen=True)
class InvariantViolation:
    """A single invariant that is currently in sustained violation."""
    invariant_name: str
    proposition: str
    severity: Severity
    observed_values: dict[str, object]  # signal_name → current value
    consecutive_ticks: int
    diagnostic_hint: str

@dataclass(frozen=True)
class AgreementViolation:
    """Event payload emitted when a violation first reaches sustained threshold."""
    violation: InvariantViolation
    timestamp: float
```

### Governance Integration

The AgreementChecker publishes `agreement_ok: Behavior[bool]` into the engine's behaviors dict. Governance chains read it through the normal alias mechanism by adding `"agreement_ok"` to `GovernanceBinding.unqualified`:

**Engine-level wiring (in daemon startup):**
```python
# Create checker with full engine behaviors access
checker = AgreementChecker(registry=build_default_registry(), behaviors=engine.behaviors)
checker.subscribe_to_tick(engine.tick_event)

# Register the agreement_ok Behavior in the engine
engine.behaviors["agreement_ok"] = checker.agreement_ok
```

**Governance-level consumption (in VetoChain):**
```python
# Add agreement_ok to the unqualified signals that pass through to governance
binding = GovernanceBinding(
    energy_source="monitor_mix",
    emotion_source="face_cam",
    unqualified=("vad_confidence", "timeline_mapping", "agreement_ok"),
)

# Add a veto that checks the agreement_ok Behavior
Veto(
    name="agreement_ok",
    predicate=lambda ctx: ctx.get_sample("agreement_ok").value,
    description="perceptual agreement across sources",
)
```

Only HARD-severity invariants contribute to the `agreement_ok` Behavior. ADVISORY invariants are checked and emit violation events but don't set `agreement_ok` to False.

**Backward compatible:** If no AgreementChecker is wired, `agreement_ok` is absent from the behaviors dict. Governance chains that don't include the veto work exactly as before.

### Prerequisite: Promote `presence_score` to a Behavior

Currently `presence_score` is a computed field on `EnvironmentState`, not a Behavior in the engine's dict. Invariants #2, #4, and #7 need it. The implementation must:

1. Add `self._b_presence_score: Behavior[str] = Behavior("likely_absent")` to `PerceptionEngine.__init__`
2. Add `"presence_score": self._b_presence_score` to `self.behaviors`
3. Update `tick()` to call `self._b_presence_score.update(presence_score, now)` alongside existing Behavior updates

This is a 3-line change to `perception.py` that makes presence_score available to the agreement checker and any future consumer.

### Event-Driven Escalation

```python
checker.violation_event.subscribe(lambda ts, v: send_notification(
    f"Perceptual disagreement: {v.violation.proposition}\n"
    f"Signals: {v.violation.observed_values}\n"
    f"Sustained for {v.violation.consecutive_ticks} ticks",
    topic="hapax-alerts",
))
```

### Lifecycle

1. **Construction** — `AgreementRegistry` validated (unique names, transitive compat matrices, acyclic entailments)
2. **Wiring** — `AgreementChecker` created with registry + engine.behaviors, subscribed to tick_event, `agreement_ok` Behavior added to engine.behaviors dict
3. **Per-tick** — on tick_event, checker evaluates all invariants against engine.behaviors, updates debounce counters, publishes `agreement_ok` Behavior, emits violations
4. **Recovery** — debounce counter resets when invariant passes; violation auto-clears; `agreement_ok` returns to True
5. **Escalation** — persistent violations (configurable `escalation_ticks` threshold, default: 12 = ~30s) emit notification via `send_notification()`

## Candidate Invariants for Current System

| # | Name | Type | Proposition | Sources | Compatibility | Severity |
|---|---|---|---|---|---|---|
| 1 | `face_emotion_entails_presence` | Entailment | Face emotion backend producing fresh data entails operator face is visible | `emotion_valence:face_cam` (entailing), `face_count` (observer) | `face_count > 0` when emotion watermark < 5s old | HARD |
| 2 | `presence_sensors_agree` | Observational | Face detector and LLM workspace agree on operator presence | `operator_present` via face_count (observer), `operator_present` via WorkspaceAnalysis (observer) | Boolean identity when both fresh within 15s | HARD |
| 3 | `app_matches_desktop_manager` | Authoritative | LLM app identification consistent with Hyprland ground truth | `active_window_class` (authoritative), `WorkspaceAnalysis.app` (dependent) | Authority match when both fresh | ADVISORY |
| 4 | `away_presence_exclusion` | Mutual Exclusion | Cannot be simultaneously "away" and actively speaking while visually present | `activity_mode`, `speech_detected`, `presence_score` (participants) | State tuple `("away", True, "definitely_present")` excluded | HARD |
| 5 | `transport_midi_agreement` | Entailment | MIDI clock producing fresh data entails transport is PLAYING | `midi_clock` watermark (entailing), `timeline_mapping.transport` (observer) | Transport == PLAYING when MIDI watermark < 2s old | HARD |
| 6 | `audio_energy_entails_pipewire` | Entailment | Audio energy backend producing fresh data entails PipeWire capture is operational | `audio_energy_rms:*` watermark (entailing) | Watermark advancing (checked implicitly by FreshnessGuard — may be redundant) | ADVISORY |
| 7 | `emotion_arousal_entails_presence` | Entailment | Emotion arousal fresh from face cam entails presence score is not "likely_absent" | `emotion_arousal:face_cam` (entailing), `presence_score` (observer) | `presence_score ≠ "likely_absent"` when emotion watermark < 5s old | HARD |

Invariant #6 may be redundant with FreshnessGuard (which already rejects when audio_energy_rms watermark is stale). Included as ADVISORY for defense-in-depth; may be dropped during implementation if it adds no diagnostic value.

## Failure Modes

| Failure | Invariant That Catches It | Response |
|---|---|---|
| Face-cam disconnected but emotion backend serving stale cached values | #1 face_emotion_entails_presence | Governance veto until emotion watermark goes stale (then FreshnessGuard catches it) |
| LLM hallucinates operator present from old screenshot | #2 presence_sensors_agree | Governance veto until LLM updates with fresh screenshot |
| LLM misidentifies application from screenshot | #3 app_matches_desktop_manager | Advisory log (Hyprland is ground truth) |
| activity_mode classifier stuck on "away" while operator is speaking on camera | #4 away_presence_exclusion | Governance veto — impossible state indicates classifier error |
| MIDI clock backend running but transport actually stopped | #5 transport_midi_agreement | Governance veto — prevents MC from scheduling beat-aligned throws to a stopped transport |
| USB hub brownout drops face detection but emotion backend keeps running from last-good frame | #1, #7 (two invariants catch this from different angles) | Governance veto — defense in depth |
| Workspace analyzer returns non-deterministic results between runs | No invariant (by design, D5) | Not a malfunction — expected LLM behavior |

## Algebraic Properties

AgreementGuard preserves the governance primitive algebra:

- **Monotonicity (of VetoChain):** Adding an agreement veto to a VetoChain can only make it more restrictive. Removing an invariant from the registry can only make it less restrictive. Consistent with VetoChain's "adding a veto can only restrict" property.
- **Commutativity (of VetoChain):** The agreement veto's position in the chain doesn't affect outcomes. It evaluates independently and contributes denials to the same deny-wins set.
- **Symmetry (of agreement):** If source A disagrees with source B, then source B disagrees with source A. The invariant violation is attributed to the invariant, not to a specific source. (Exception: Type 3 Authoritative Override, which is asymmetric by design — the dependent is wrong, not the authority.)
- **Transitivity (of compatibility):** If value A is compatible with B, and B is compatible with C, then A must be compatible with C. Registry validation rejects compatibility matrices that violate transitivity.
- **Entailment acyclicity:** If signal A entails proposition P, and P entails Q, the entailment chain must be acyclic. Registry validation rejects circular entailments.
- **Debounce idempotence:** Evaluating the same state N times produces the same violation set (after debounce settles). No hysteresis beyond the debounce counter.

These properties are testable via Hypothesis, matching the existing governance test pattern.

## Testing Strategy

### Layer 1: Unit Tests — AgreementChecker mechanics

```
TestAgreementChecker:
    test_empty_registry_always_satisfied
    test_single_invariant_pass
    test_single_invariant_fail_under_debounce
    test_single_invariant_fail_after_debounce
    test_recovery_resets_debounce_counter
    test_advisory_violations_dont_block_veto
    test_hard_violations_block_veto
    test_multiple_invariants_all_must_pass
    test_precondition_not_met_skips_check
    test_violation_event_emitted_on_sustained_failure
    test_violation_event_not_emitted_on_transient_failure
```

### Layer 2: Compatibility Function Tests

```
TestIdentityAgreement:
    test_same_value_passes
    test_different_value_fails
    test_both_none_passes

TestProximityAgreement:
    test_adjacent_values_pass
    test_distant_values_fail
    test_boundary_at_max_distance

TestEntailment:
    test_fresh_signal_with_matching_proposition_passes
    test_fresh_signal_with_contradicting_proposition_fails
    test_stale_signal_skips_check (precondition handles this)

TestAuthorityMatch:
    test_dependent_matches_authority_passes
    test_dependent_contradicts_authority_fails

TestExclusion:
    test_possible_state_tuple_passes
    test_impossible_state_tuple_fails
```

### Layer 3: Registry Validation Tests

```
TestAgreementRegistryValidation:
    test_duplicate_invariant_names_rejected
    test_non_transitive_compatibility_matrix_rejected
    test_cyclic_entailment_rejected
    test_valid_registry_constructs
    test_unknown_behavior_name_warned (not rejected — backend may not be registered yet)
```

### Layer 4: Integration with Governance

```
TestGovernanceIntegration:
    test_agreement_veto_blocks_when_violated
    test_agreement_veto_allows_when_satisfied
    test_agreement_veto_composes_with_existing_vetoes
    test_backward_compat_no_checker (no agreement_checker → old behavior)
    test_mc_pipeline_with_agreement_checker
```

### Layer 5: Hypothesis Property Tests

```
TestAgreementProperties:
    test_symmetry — disagreement is symmetric across source pairs
    test_monotonicity — adding invariant only restricts
    test_debounce_idempotence — same state repeated produces same result after settling
    test_recovery_always_possible — if all sources agree, violations clear
```

### Layer 6: Candidate Invariant Tests

One test per candidate invariant from the registry, using concrete scenarios:

```
TestCandidateInvariants:
    test_face_emotion_entails_presence_catches_disconnected_camera
    test_presence_sensors_agree_catches_stale_llm
    test_app_matches_desktop_advisory_only
    test_away_presence_exclusion_catches_classifier_error
    test_transport_midi_catches_stale_clock
```

## Dependencies

None. All types are pure Python dataclasses, enums, and callables. No new third-party packages.

## Files

| File | Change |
|---|---|
| `agents/hapax_voice/agreement.py` | **New.** AgreementChecker, AgreementRegistry, InvariantSpec, compatibility functions, result types, `build_default_registry()` factory |
| `agents/hapax_voice/perception.py` | **+3 lines.** Promote `presence_score` to a Behavior in engine.behaviors dict |
| `agents/hapax_voice/governance.py` | **Unchanged.** Agreement integrates via existing Veto protocol |
| `agents/hapax_voice/mc_governance.py` | **+2 lines.** Add `agreement_ok` veto to `build_mc_veto_chain()` |
| `agents/hapax_voice/obs_governance.py` | **+2 lines.** Same pattern as MC |
| `agents/hapax_voice/wiring.py` | **+1 line.** Add `"agreement_ok"` to default `GovernanceBinding.unqualified` tuple |
| `tests/test_agreement.py` | **New.** ~40 tests across 6 layers |
| `tests/test_mc_governance.py` | **+5 tests.** Integration tests with agreement veto |

## Resolved Design Choices

1. **Where does the candidate invariant registry live?** A `build_default_registry()` factory function in `agreement.py`. It's code, not config, because the compatibility functions are Python callables. The factory returns an `AgreementRegistry` frozen dataclass.

2. **Should `AgreementChecker.check()` receive the raw behaviors dict or FusedContext?** **Resolved: raw behaviors dict.** The governance FusedContext is built from the alias dict which excludes `face_count`, `operator_present`, `presence_score`, and other signals needed by invariants. The checker receives the full engine behaviors dict at construction and reads from it on each tick. See D6 rationale.

3. **Notification threshold for persistent violations.** Configurable `escalation_ticks` on `AgreementCheckerConfig` (default: 12, = ~30s at 2.5s tick). Separate from `min_violation_ticks` (debounce for governance veto, default: 3).
