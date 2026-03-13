"""Perceptual agreement invariants — cross-system coherence checking.

Validates that perception systems agree about basic facts before governance
chains act on the world model. A Behavior can be fresh, within range, and
*wrong* — contradicted by another system. This module catches those cases.

Three layers:
  - InvariantSpec: declarative invariant definitions with compatibility functions
  - AgreementRegistry: validated collection of invariant specs
  - AgreementChecker: stateful evaluator with debounce counters and event emission
"""

from __future__ import annotations

import logging
import types
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from agents.hapax_voice.governance import FreshnessRequirement
from agents.hapax_voice.primitives import Behavior, Event

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

CompatibilityFn = Callable[[dict[str, Behavior], float], tuple[bool, str]]

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InvariantType(Enum):
    """Classification of perceptual agreement invariant."""

    OBSERVATIONAL = "observational"
    ENTAILMENT = "entailment"
    AUTHORITATIVE = "authoritative"
    MUTUAL_EXCLUSION = "mutual_exclusion"


class Severity(Enum):
    """Impact of invariant violation on governance."""

    HARD = "hard"  # governance veto
    ADVISORY = "advisory"  # log only


class Role(Enum):
    """Role of a behavior source within an invariant."""

    OBSERVER = "observer"
    ENTAILING = "entailing"
    AUTHORITATIVE = "authoritative"
    DEPENDENT = "dependent"
    PARTICIPANT = "participant"


# ---------------------------------------------------------------------------
# Frozen dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceRole:
    """A behavior and its role within an invariant."""

    behavior_name: str
    role: Role


@dataclass(frozen=True)
class InvariantViolation:
    """A single invariant violation with diagnostic context."""

    invariant_name: str
    proposition: str
    severity: Severity
    observed_values: dict[str, object] = field(default_factory=dict)
    consecutive_ticks: int = 0
    diagnostic_hint: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_values", types.MappingProxyType(self.observed_values))


@dataclass(frozen=True)
class AgreementViolation:
    """Event payload for a sustained invariant violation."""

    violation: InvariantViolation
    timestamp: float


@dataclass(frozen=True)
class AgreementResult:
    """Outcome of checking all invariants."""

    satisfied: bool
    violations: tuple[InvariantViolation, ...] = ()


@dataclass(frozen=True)
class InvariantSpec:
    """Declarative specification of a perceptual agreement invariant."""

    name: str
    proposition: str
    invariant_type: InvariantType
    sources: tuple[SourceRole, ...]
    check: CompatibilityFn
    preconditions: tuple[FreshnessRequirement, ...] = ()
    severity: Severity = Severity.HARD
    min_violation_ticks: int = 3
    diagnostic_hint: str = ""


# ---------------------------------------------------------------------------
# Compatibility function factories
# ---------------------------------------------------------------------------


def identity_agreement(a: str, b: str) -> CompatibilityFn:
    """Values of two behaviors must be equal."""

    def _check(behaviors: dict[str, Behavior], now: float) -> tuple[bool, str]:
        if a not in behaviors or b not in behaviors:
            return True, "signal not present"
        va, vb = behaviors[a].value, behaviors[b].value
        if va == vb:
            return True, ""
        return False, f"{a}={va!r} != {b}={vb!r}"

    return _check


def proximity_agreement(
    a: str,
    b: str,
    max_distance: float,
    ordinal: list[str] | None = None,
) -> CompatibilityFn:
    """Values must be within max_distance (numeric) or ordinal step distance."""

    def _check(behaviors: dict[str, Behavior], now: float) -> tuple[bool, str]:
        if a not in behaviors or b not in behaviors:
            return True, "signal not present"
        va, vb = behaviors[a].value, behaviors[b].value
        if ordinal is not None:
            try:
                ia, ib = ordinal.index(va), ordinal.index(vb)
                dist = abs(ia - ib)
            except ValueError:
                return True, "value not in ordinal scale"
        else:
            dist = abs(va - vb)
        if dist <= max_distance:
            return True, ""
        return False, f"distance({a}, {b}) = {dist} > {max_distance}"

    return _check


def freshness_entailment(
    signal: str,
    proposition_behavior: str,
    check_fn: Callable[[object], bool],
    max_staleness_s: float,
) -> CompatibilityFn:
    """If signal watermark is fresh, check_fn(proposition_behavior.value) must be True."""

    def _check(behaviors: dict[str, Behavior], now: float) -> tuple[bool, str]:
        if signal not in behaviors or proposition_behavior not in behaviors:
            return True, "signal not present"
        staleness = now - behaviors[signal].watermark
        if staleness > max_staleness_s:
            return True, f"{signal} stale ({staleness:.1f}s) — entailment vacuous"
        prop_val = behaviors[proposition_behavior].value
        if check_fn(prop_val):
            return True, ""
        return False, f"{signal} fresh but {proposition_behavior}={prop_val!r} fails check"

    return _check


def authority_match(authority: str, dependent: str) -> CompatibilityFn:
    """Dependent value must match authority value."""

    def _check(behaviors: dict[str, Behavior], now: float) -> tuple[bool, str]:
        if authority not in behaviors or dependent not in behaviors:
            return True, "signal not present"
        va, vd = behaviors[authority].value, behaviors[dependent].value
        if va == vd:
            return True, ""
        return False, f"authority {authority}={va!r} != dependent {dependent}={vd!r}"

    return _check


def state_exclusion(
    signals: tuple[str, ...],
    impossible: frozenset[tuple[object, ...]],
) -> CompatibilityFn:
    """Current value tuple must not be in the impossible set."""

    def _check(behaviors: dict[str, Behavior], now: float) -> tuple[bool, str]:
        for s in signals:
            if s not in behaviors:
                return True, "signal not present"
        current = tuple(behaviors[s].value for s in signals)
        if current in impossible:
            return False, f"impossible state: {dict(zip(signals, current, strict=True))}"
        return True, ""

    return _check


# ---------------------------------------------------------------------------
# AgreementRegistry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgreementRegistry:
    """Validated collection of invariant specs. Name uniqueness enforced."""

    invariants: tuple[InvariantSpec, ...] = ()

    def __post_init__(self) -> None:
        names = [spec.name for spec in self.invariants]
        dupes = [n for n in names if names.count(n) > 1]
        if dupes:
            raise ValueError(f"Duplicate invariant names: {set(dupes)}")


# ---------------------------------------------------------------------------
# AgreementChecker
# ---------------------------------------------------------------------------


class AgreementChecker:
    """Stateful evaluator of perceptual agreement invariants.

    Maintains debounce counters per invariant. Only reports violations after
    min_violation_ticks consecutive failures (transient disagreements are normal).
    """

    __slots__ = ("_registry", "_behaviors", "_counters", "_agreement_ok", "_violation_event")

    def __init__(
        self,
        registry: AgreementRegistry,
        behaviors: dict[str, Behavior],
    ) -> None:
        self._registry = registry
        self._behaviors = behaviors
        self._counters: dict[str, int] = {spec.name: 0 for spec in registry.invariants}
        self._agreement_ok: Behavior[bool] = Behavior(True, watermark=0.0)
        self._violation_event: Event[AgreementViolation] = Event()

    @property
    def agreement_ok(self) -> Behavior[bool]:
        return self._agreement_ok

    @property
    def violation_event(self) -> Event[AgreementViolation]:
        return self._violation_event

    def check(self, now: float) -> AgreementResult:
        """Evaluate all invariants against current behavior values."""
        violations: list[InvariantViolation] = []

        for spec in self._registry.invariants:
            # Check preconditions (freshness of required signals)
            precondition_met = True
            for req in spec.preconditions:
                b = self._behaviors.get(req.behavior_name)
                if b is None:
                    precondition_met = False
                    break
                if now - b.watermark > req.max_staleness_s:
                    precondition_met = False
                    break

            if not precondition_met:
                self._counters[spec.name] = 0
                continue

            # Run compatibility check
            compatible, diagnostic = spec.check(self._behaviors, now)

            if compatible:
                self._counters[spec.name] = 0
                continue

            # Increment debounce counter
            self._counters[spec.name] += 1
            count = self._counters[spec.name]

            if count >= spec.min_violation_ticks:
                # Collect observed values from sources
                observed = {}
                for src in spec.sources:
                    b = self._behaviors.get(src.behavior_name)
                    if b is not None:
                        observed[src.behavior_name] = b.value

                violation = InvariantViolation(
                    invariant_name=spec.name,
                    proposition=spec.proposition,
                    severity=spec.severity,
                    observed_values=observed,
                    consecutive_ticks=count,
                    diagnostic_hint=diagnostic or spec.diagnostic_hint,
                )
                violations.append(violation)

                self._violation_event.emit(
                    now, AgreementViolation(violation=violation, timestamp=now)
                )

        # agreement_ok = no HARD violations
        has_hard = any(v.severity is Severity.HARD for v in violations)
        self._agreement_ok.update(not has_hard, now)

        return AgreementResult(
            satisfied=len(violations) == 0,
            violations=tuple(violations),
        )


# ---------------------------------------------------------------------------
# Default registry factory
# ---------------------------------------------------------------------------


def build_default_registry() -> AgreementRegistry:
    """Build the 8 candidate invariants from the design spec."""
    return AgreementRegistry(
        invariants=(
            # 1. face_emotion_entails_presence (ENTAILMENT, HARD)
            InvariantSpec(
                name="face_emotion_entails_presence",
                proposition="Face emotion fresh entails face_count > 0",
                invariant_type=InvariantType.ENTAILMENT,
                sources=(
                    SourceRole("emotion_valence", Role.ENTAILING),
                    SourceRole("face_count", Role.OBSERVER),
                ),
                check=freshness_entailment(
                    signal="emotion_valence",
                    proposition_behavior="face_count",
                    check_fn=lambda v: int(v) > 0,  # type: ignore[arg-type]
                    max_staleness_s=5.0,
                ),
                severity=Severity.HARD,
                diagnostic_hint="Emotion backend producing data but no face visible",
            ),
            # 2. presence_sensors_agree (OBSERVATIONAL, HARD)
            InvariantSpec(
                name="presence_sensors_agree",
                proposition="Face detector and presence score agree on operator presence",
                invariant_type=InvariantType.OBSERVATIONAL,
                sources=(
                    SourceRole("operator_present", Role.OBSERVER),
                    SourceRole("presence_score", Role.OBSERVER),
                ),
                check=_presence_agreement(),
                preconditions=(
                    FreshnessRequirement("operator_present", 15.0),
                    FreshnessRequirement("presence_score", 15.0),
                ),
                severity=Severity.HARD,
                diagnostic_hint="Face detector and presence score disagree",
            ),
            # 3. app_matches_desktop_manager (AUTHORITATIVE, ADVISORY)
            InvariantSpec(
                name="app_matches_desktop_manager",
                proposition="LLM app identification matches Hyprland ground truth",
                invariant_type=InvariantType.AUTHORITATIVE,
                sources=(
                    SourceRole("active_window", Role.AUTHORITATIVE),
                    SourceRole("activity_mode", Role.DEPENDENT),
                ),
                check=_app_desktop_agreement(),
                severity=Severity.ADVISORY,
                diagnostic_hint="LLM app identification inconsistent with window manager",
            ),
            # 4. away_presence_exclusion (MUTUAL_EXCLUSION, HARD)
            InvariantSpec(
                name="away_presence_exclusion",
                proposition="Cannot be away + speaking + definitely present simultaneously",
                invariant_type=InvariantType.MUTUAL_EXCLUSION,
                sources=(
                    SourceRole("activity_mode", Role.PARTICIPANT),
                    SourceRole("vad_confidence", Role.PARTICIPANT),
                    SourceRole("presence_score", Role.PARTICIPANT),
                ),
                check=_away_exclusion_check(),
                severity=Severity.HARD,
                diagnostic_hint="Impossible state: classified away but speaking and present",
            ),
            # 5. transport_midi_agreement (ENTAILMENT, HARD)
            InvariantSpec(
                name="transport_midi_agreement",
                proposition="MIDI clock fresh entails transport is PLAYING",
                invariant_type=InvariantType.ENTAILMENT,
                sources=(
                    SourceRole("midi_clock", Role.ENTAILING),
                    SourceRole("timeline_mapping", Role.OBSERVER),
                ),
                check=freshness_entailment(
                    signal="midi_clock",
                    proposition_behavior="timeline_mapping",
                    check_fn=lambda v: (
                        getattr(v, "transport", None) is not None and v.transport.value == "playing"
                    ),
                    max_staleness_s=2.0,
                ),
                severity=Severity.HARD,
                diagnostic_hint="MIDI clock active but transport reports stopped",
            ),
            # 6. audio_energy_entails_pipewire (ENTAILMENT, ADVISORY)
            InvariantSpec(
                name="audio_energy_entails_pipewire",
                proposition="Audio energy fresh entails PipeWire capture is operational",
                invariant_type=InvariantType.ENTAILMENT,
                sources=(SourceRole("audio_energy_rms", Role.ENTAILING),),
                check=_pipewire_entailment(),
                severity=Severity.ADVISORY,
                diagnostic_hint="Audio energy stale — PipeWire capture may be down",
            ),
            # 7. emotion_arousal_entails_presence (ENTAILMENT, HARD)
            InvariantSpec(
                name="emotion_arousal_entails_presence",
                proposition="Emotion arousal fresh entails presence score is not likely_absent",
                invariant_type=InvariantType.ENTAILMENT,
                sources=(
                    SourceRole("emotion_arousal", Role.ENTAILING),
                    SourceRole("presence_score", Role.OBSERVER),
                ),
                check=freshness_entailment(
                    signal="emotion_arousal",
                    proposition_behavior="presence_score",
                    check_fn=lambda v: v != "likely_absent",
                    max_staleness_s=5.0,
                ),
                severity=Severity.HARD,
                diagnostic_hint="Emotion arousal fresh but operator appears absent",
            ),
            # 8. identity_emotion_coherence (ENTAILMENT, ADVISORY)
            InvariantSpec(
                name="identity_emotion_coherence",
                proposition="Emotion fresh entails operator identified",
                invariant_type=InvariantType.ENTAILMENT,
                sources=(
                    SourceRole("emotion_valence", Role.ENTAILING),
                    SourceRole("operator_identified", Role.OBSERVER),
                ),
                check=freshness_entailment(
                    signal="emotion_valence",
                    proposition_behavior="operator_identified",
                    check_fn=lambda v: v is True,
                    max_staleness_s=5.0,
                ),
                severity=Severity.ADVISORY,
                diagnostic_hint=(
                    "Emotion fresh but operator not identified — may be processing guest face"
                ),
            ),
        )
    )


# ---------------------------------------------------------------------------
# Internal compatibility functions for complex invariants
# ---------------------------------------------------------------------------


def _presence_agreement() -> CompatibilityFn:
    """Face detector (operator_present bool) must be consistent with presence_score string.

    Identity-aware: when operator_identified is available and fresh, uses it as
    ground truth. Guests-only (faces but not identified) + absent is acceptable.
    """

    def _check(behaviors: dict[str, Behavior], now: float) -> tuple[bool, str]:
        if "operator_present" not in behaviors or "presence_score" not in behaviors:
            return True, "signal not present"
        face_present = behaviors["operator_present"].value
        score = behaviors["presence_score"].value

        # When identity is available, use it for presence ground truth
        identity_b = behaviors.get("operator_identified")
        if identity_b is not None and identity_b.watermark > 0:
            identified = identity_b.value
            # operator_identified=True + absent → genuine contradiction
            if identified and score in ("likely_absent",):
                return False, f"operator identified but presence_score={score!r}"
            # Faces detected + not identified + absent → acceptable (guests only)
            if not identified and not face_present:
                return True, ""
            # operator_identified=True + present → fine
            if identified:
                return True, ""

        # Fallback: original logic
        absent_scores = ("likely_absent",)
        present_scores = ("definitely_present", "likely_present")
        if face_present and score in absent_scores:
            return False, f"face detected but presence_score={score!r}"
        if not face_present and score in present_scores:
            return False, f"no face but presence_score={score!r}"
        return True, ""

    return _check


def _app_desktop_agreement() -> CompatibilityFn:
    """Activity mode should not contradict active window class (advisory)."""

    def _check(behaviors: dict[str, Behavior], now: float) -> tuple[bool, str]:
        # Always pass — this invariant needs richer signals than currently available.
        # Placeholder that returns True to avoid false positives.
        if "active_window" not in behaviors or "activity_mode" not in behaviors:
            return True, "signal not present"
        return True, ""

    return _check


def _away_exclusion_check() -> CompatibilityFn:
    """Cannot be away + speaking + definitely_present simultaneously."""

    def _check(behaviors: dict[str, Behavior], now: float) -> tuple[bool, str]:
        for name in ("activity_mode", "vad_confidence", "presence_score"):
            if name not in behaviors:
                return True, "signal not present"
        mode = behaviors["activity_mode"].value
        vad = behaviors["vad_confidence"].value
        score = behaviors["presence_score"].value
        # Speech detected when VAD > 0.5
        speaking = vad > 0.5
        if mode == "away" and speaking and score == "definitely_present":
            return False, f"impossible: mode={mode}, speaking={speaking}, presence={score}"
        return True, ""

    return _check


def _pipewire_entailment() -> CompatibilityFn:
    """Audio energy watermark advancing implies PipeWire is operational.

    This is largely redundant with FreshnessGuard but provides defense-in-depth
    diagnostics. Always returns True — the freshness_entailment factory handles
    the real check for invariants that reference specific behaviors.
    """

    def _check(behaviors: dict[str, Behavior], now: float) -> tuple[bool, str]:
        if "audio_energy_rms" not in behaviors:
            return True, "signal not present"
        staleness = now - behaviors["audio_energy_rms"].watermark
        if staleness > 10.0:
            return False, f"audio_energy_rms watermark {staleness:.1f}s stale — PipeWire down?"
        return True, ""

    return _check
