# CPAL Phase 1: Foundation — Core Types, Loop Gain, ControlSignal

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the core type system and loop gain model for the Conversational Perception-Action Loop, replacing the binary session model with continuous conversational intensity.

**Architecture:** New module `agents/hapax_daimonion/cpal/` containing the control loop foundation. The existing system continues to function — Phase 1 runs alongside it, publishing signals to `/dev/shm`. Subsequent phases incrementally replace old components with CPAL equivalents.

**Tech Stack:** Python 3.12, Pydantic, shared/control_signal.py (ControlSignal, publish_health), existing grounding_ledger.py (DUState, DiscourseUnit, GQI)

**Spec:** `docs/superpowers/specs/2026-04-01-conversational-perception-action-loop-design.md`

**Phasing:** This is Phase 1 of 4. Phase 2 (Streams), Phase 3 (Signal Repertoire), Phase 4 (Grounding Control) depend on this foundation.

---

### File Structure

| File | Responsibility |
|---|---|
| `agents/hapax_daimonion/cpal/__init__.py` | Package marker, public re-exports |
| `agents/hapax_daimonion/cpal/types.py` | Core enums, dataclasses: ConversationalRegion, ErrorSignal, CorrectionTier |
| `agents/hapax_daimonion/cpal/loop_gain.py` | LoopGainController: continuous 0.0–1.0 with drivers, dampers, stimmung ceiling, hysteresis |
| `agents/hapax_daimonion/cpal/control_law.py` | ConversationControlLaw: S1-compatible control law (reference, perception, error, action selection) |
| `agents/hapax_daimonion/cpal/shm_publisher.py` | Publishes CPAL state to /dev/shm/hapax-conversation/ for SCM integration |
| `tests/hapax_daimonion/test_cpal_types.py` | Type construction, enum membership, invariants |
| `tests/hapax_daimonion/test_loop_gain.py` | Gain dynamics: drivers, dampers, decay, ceiling, hysteresis, region mapping |
| `tests/hapax_daimonion/test_control_law.py` | Control law: error computation, action selection, ControlSignal emission |
| `tests/hapax_daimonion/test_shm_publisher.py` | SHM publication format, atomicity |

---

### Task 1: Core Types

**Files:**
- Create: `agents/hapax_daimonion/cpal/__init__.py`
- Create: `agents/hapax_daimonion/cpal/types.py`
- Create: `tests/hapax_daimonion/test_cpal_types.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/hapax_daimonion/test_cpal_types.py
"""Tests for CPAL core types."""

from agents.hapax_daimonion.cpal.types import (
    ConversationalRegion,
    CorrectionTier,
    ErrorDimension,
    ErrorSignal,
    GainUpdate,
)


class TestConversationalRegion:
    def test_all_regions_defined(self):
        assert len(ConversationalRegion) == 5

    def test_region_ordering(self):
        """Regions have increasing gain thresholds."""
        assert ConversationalRegion.AMBIENT.threshold < ConversationalRegion.PERIPHERAL.threshold
        assert ConversationalRegion.PERIPHERAL.threshold < ConversationalRegion.ATTENTIVE.threshold
        assert ConversationalRegion.ATTENTIVE.threshold < ConversationalRegion.CONVERSATIONAL.threshold
        assert ConversationalRegion.CONVERSATIONAL.threshold < ConversationalRegion.INTENSIVE.threshold

    def test_region_from_gain(self):
        assert ConversationalRegion.from_gain(0.0) == ConversationalRegion.AMBIENT
        assert ConversationalRegion.from_gain(0.05) == ConversationalRegion.AMBIENT
        assert ConversationalRegion.from_gain(0.15) == ConversationalRegion.PERIPHERAL
        assert ConversationalRegion.from_gain(0.35) == ConversationalRegion.ATTENTIVE
        assert ConversationalRegion.from_gain(0.55) == ConversationalRegion.CONVERSATIONAL
        assert ConversationalRegion.from_gain(0.85) == ConversationalRegion.INTENSIVE
        assert ConversationalRegion.from_gain(1.0) == ConversationalRegion.INTENSIVE


class TestCorrectionTier:
    def test_all_tiers_defined(self):
        assert len(CorrectionTier) == 4

    def test_tier_ordering(self):
        """Tiers have increasing cost."""
        tiers = list(CorrectionTier)
        assert tiers == [
            CorrectionTier.T0_VISUAL,
            CorrectionTier.T1_PRESYNTHESIZED,
            CorrectionTier.T2_LIGHTWEIGHT,
            CorrectionTier.T3_FULL_FORMULATION,
        ]


class TestErrorSignal:
    def test_construction(self):
        err = ErrorSignal(
            comprehension=0.3,
            affective=0.1,
            temporal=0.5,
        )
        assert err.comprehension == 0.3
        assert err.affective == 0.1
        assert err.temporal == 0.5

    def test_magnitude(self):
        """Magnitude is the max of all dimensions."""
        err = ErrorSignal(comprehension=0.3, affective=0.1, temporal=0.5)
        assert err.magnitude == 0.5

    def test_dominant_dimension(self):
        err = ErrorSignal(comprehension=0.3, affective=0.1, temporal=0.5)
        assert err.dominant == ErrorDimension.TEMPORAL

    def test_zero_error(self):
        err = ErrorSignal(comprehension=0.0, affective=0.0, temporal=0.0)
        assert err.magnitude == 0.0

    def test_suggested_tier(self):
        """Error magnitude maps to correction tier."""
        assert ErrorSignal(0.05, 0.0, 0.0).suggested_tier == CorrectionTier.T0_VISUAL
        assert ErrorSignal(0.2, 0.0, 0.0).suggested_tier == CorrectionTier.T1_PRESYNTHESIZED
        assert ErrorSignal(0.5, 0.0, 0.0).suggested_tier == CorrectionTier.T3_FULL_FORMULATION
        assert ErrorSignal(0.8, 0.0, 0.0).suggested_tier == CorrectionTier.T3_FULL_FORMULATION


class TestGainUpdate:
    def test_construction(self):
        gu = GainUpdate(delta=0.05, source="operator_speech")
        assert gu.delta == 0.05
        assert gu.source == "operator_speech"

    def test_driver_is_positive(self):
        gu = GainUpdate(delta=0.1, source="grounding_success")
        assert gu.is_driver

    def test_damper_is_negative(self):
        gu = GainUpdate(delta=-0.05, source="silence_decay")
        assert gu.is_damper
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/hapax_daimonion/test_cpal_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.hapax_daimonion.cpal'`

- [ ] **Step 3: Write the implementation**

```python
# agents/hapax_daimonion/cpal/__init__.py
"""Conversational Perception-Action Loop (CPAL).

The 15th S1 component in the Stigmergic Cognitive Mesh.
Models conversation as a perceptual control loop with continuous
intensity (loop gain) replacing the binary session model.
"""

from agents.hapax_daimonion.cpal.types import (
    ConversationalRegion,
    CorrectionTier,
    ErrorDimension,
    ErrorSignal,
    GainUpdate,
)

__all__ = [
    "ConversationalRegion",
    "CorrectionTier",
    "ErrorDimension",
    "ErrorSignal",
    "GainUpdate",
]
```

```python
# agents/hapax_daimonion/cpal/types.py
"""Core types for the Conversational Perception-Action Loop."""

from __future__ import annotations

import enum
from dataclasses import dataclass


class ConversationalRegion(enum.Enum):
    """Behavioral regions defined by loop gain thresholds.

    Each region activates different capabilities in the signal repertoire.
    Transitions are continuous drift, not discrete events.
    """

    AMBIENT = "ambient"  # 0.0-0.1
    PERIPHERAL = "peripheral"  # 0.1-0.3
    ATTENTIVE = "attentive"  # 0.3-0.5
    CONVERSATIONAL = "conversational"  # 0.5-0.7
    INTENSIVE = "intensive"  # 0.7-1.0

    @property
    def threshold(self) -> float:
        """Lower bound of this region."""
        return _REGION_THRESHOLDS[self]

    @classmethod
    def from_gain(cls, gain: float) -> ConversationalRegion:
        """Map a gain value to its behavioral region."""
        if gain >= 0.7:
            return cls.INTENSIVE
        if gain >= 0.5:
            return cls.CONVERSATIONAL
        if gain >= 0.3:
            return cls.ATTENTIVE
        if gain >= 0.1:
            return cls.PERIPHERAL
        return cls.AMBIENT


_REGION_THRESHOLDS: dict[ConversationalRegion, float] = {
    ConversationalRegion.AMBIENT: 0.0,
    ConversationalRegion.PERIPHERAL: 0.1,
    ConversationalRegion.ATTENTIVE: 0.3,
    ConversationalRegion.CONVERSATIONAL: 0.5,
    ConversationalRegion.INTENSIVE: 0.7,
}


class CorrectionTier(enum.Enum):
    """Tiered corrective actions, ordered by cost and latency.

    T0: <50ms, zero computation (visual state changes)
    T1: <200ms, presynthesized audio (backchannels, acknowledgments)
    T2: <500ms, lightweight computation (echo/rephrase, discourse markers)
    T3: 3-6s, full LLM formulation (substantive response)
    """

    T0_VISUAL = "t0_visual"
    T1_PRESYNTHESIZED = "t1_presynthesized"
    T2_LIGHTWEIGHT = "t2_lightweight"
    T3_FULL_FORMULATION = "t3_full_formulation"


class ErrorDimension(enum.Enum):
    """Dimensions of conversational error."""

    COMPREHENSION = "comprehension"  # ungrounded DUs, repair frequency
    AFFECTIVE = "affective"  # declining GQI, disengagement cues
    TEMPORAL = "temporal"  # growing gap between expected and actual timing


@dataclass(frozen=True)
class ErrorSignal:
    """Multi-dimensional conversational error.

    Each dimension is 0.0 (no error) to 1.0 (maximum error).
    The control law selects corrective action based on magnitude
    and dominant dimension.
    """

    comprehension: float
    affective: float
    temporal: float

    @property
    def magnitude(self) -> float:
        """Overall error magnitude -- max of all dimensions."""
        return max(self.comprehension, self.affective, self.temporal)

    @property
    def dominant(self) -> ErrorDimension:
        """Which dimension contributes most to error."""
        vals = {
            ErrorDimension.COMPREHENSION: self.comprehension,
            ErrorDimension.AFFECTIVE: self.affective,
            ErrorDimension.TEMPORAL: self.temporal,
        }
        return max(vals, key=vals.get)  # type: ignore[arg-type]

    @property
    def suggested_tier(self) -> CorrectionTier:
        """Map error magnitude to minimum correction tier."""
        mag = self.magnitude
        if mag < 0.1:
            return CorrectionTier.T0_VISUAL
        if mag < 0.3:
            return CorrectionTier.T1_PRESYNTHESIZED
        if mag < 0.45:
            return CorrectionTier.T2_LIGHTWEIGHT
        return CorrectionTier.T3_FULL_FORMULATION


@dataclass(frozen=True)
class GainUpdate:
    """A single adjustment to loop gain with provenance."""

    delta: float  # positive = driver, negative = damper
    source: str  # e.g. "operator_speech", "silence_decay", "grounding_failure"

    @property
    def is_driver(self) -> bool:
        return self.delta > 0

    @property
    def is_damper(self) -> bool:
        return self.delta < 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_daimonion/test_cpal_types.py -v`
Expected: PASS — all 13 tests

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_daimonion/cpal/__init__.py agents/hapax_daimonion/cpal/types.py tests/hapax_daimonion/test_cpal_types.py
git commit -m "feat(cpal): core types -- ConversationalRegion, ErrorSignal, CorrectionTier"
```

---

### Task 2: Loop Gain Controller

**Files:**
- Create: `agents/hapax_daimonion/cpal/loop_gain.py`
- Create: `tests/hapax_daimonion/test_loop_gain.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/hapax_daimonion/test_loop_gain.py
"""Tests for CPAL loop gain controller."""

import math

from agents.hapax_daimonion.cpal.loop_gain import LoopGainController
from agents.hapax_daimonion.cpal.types import ConversationalRegion, GainUpdate


class TestLoopGainBasics:
    def test_initial_gain_is_zero(self):
        ctrl = LoopGainController()
        assert ctrl.gain == 0.0

    def test_initial_region_is_ambient(self):
        ctrl = LoopGainController()
        assert ctrl.region == ConversationalRegion.AMBIENT

    def test_gain_clamped_to_unit_interval(self):
        ctrl = LoopGainController()
        ctrl.apply(GainUpdate(delta=5.0, source="test"))
        assert ctrl.gain == 1.0
        ctrl.apply(GainUpdate(delta=-10.0, source="test"))
        assert ctrl.gain == 0.0


class TestGainDrivers:
    def test_operator_speech_raises_gain(self):
        ctrl = LoopGainController()
        ctrl.apply(GainUpdate(delta=0.15, source="operator_speech"))
        assert ctrl.gain == 0.15

    def test_multiple_drivers_accumulate(self):
        ctrl = LoopGainController()
        ctrl.apply(GainUpdate(delta=0.15, source="operator_speech"))
        ctrl.apply(GainUpdate(delta=0.10, source="grounding_success"))
        assert ctrl.gain == 0.25

    def test_region_transitions_with_gain(self):
        ctrl = LoopGainController()
        assert ctrl.region == ConversationalRegion.AMBIENT
        ctrl.apply(GainUpdate(delta=0.15, source="operator_speech"))
        assert ctrl.region == ConversationalRegion.PERIPHERAL
        ctrl.apply(GainUpdate(delta=0.20, source="operator_speech"))
        assert ctrl.region == ConversationalRegion.ATTENTIVE
        ctrl.apply(GainUpdate(delta=0.20, source="grounding_success"))
        assert ctrl.region == ConversationalRegion.CONVERSATIONAL
        ctrl.apply(GainUpdate(delta=0.30, source="engagement"))
        assert ctrl.region == ConversationalRegion.INTENSIVE


class TestGainDampers:
    def test_damper_reduces_gain(self):
        ctrl = LoopGainController()
        ctrl.apply(GainUpdate(delta=0.5, source="test"))
        ctrl.apply(GainUpdate(delta=-0.2, source="silence_decay"))
        assert ctrl.gain == 0.3

    def test_silence_decay(self):
        """Exponential decay with ~15s time constant."""
        ctrl = LoopGainController()
        ctrl.apply(GainUpdate(delta=0.6, source="test"))
        ctrl.decay(dt=15.0)
        expected = 0.6 * math.exp(-15.0 / 15.0)
        assert abs(ctrl.gain - expected) < 0.01

    def test_decay_clamps_near_zero(self):
        ctrl = LoopGainController()
        ctrl.apply(GainUpdate(delta=0.01, source="test"))
        ctrl.decay(dt=60.0)
        assert ctrl.gain == 0.0


class TestStimmungCeiling:
    def test_nominal_no_ceiling(self):
        ctrl = LoopGainController()
        ctrl.set_stimmung_ceiling("nominal")
        ctrl.apply(GainUpdate(delta=1.0, source="test"))
        assert ctrl.gain == 1.0

    def test_cautious_caps_at_0_7(self):
        ctrl = LoopGainController()
        ctrl.set_stimmung_ceiling("cautious")
        ctrl.apply(GainUpdate(delta=1.0, source="test"))
        assert ctrl.gain == 0.7

    def test_degraded_caps_at_0_5(self):
        ctrl = LoopGainController()
        ctrl.set_stimmung_ceiling("degraded")
        ctrl.apply(GainUpdate(delta=1.0, source="test"))
        assert ctrl.gain == 0.5

    def test_critical_caps_at_0_3(self):
        ctrl = LoopGainController()
        ctrl.set_stimmung_ceiling("critical")
        ctrl.apply(GainUpdate(delta=1.0, source="test"))
        assert ctrl.gain == 0.3

    def test_ceiling_enforced_retroactively(self):
        ctrl = LoopGainController()
        ctrl.apply(GainUpdate(delta=0.8, source="test"))
        assert ctrl.gain == 0.8
        ctrl.set_stimmung_ceiling("degraded")
        assert ctrl.gain == 0.5


class TestHysteresis:
    def test_consecutive_failures_reduce_gain(self):
        """3 consecutive grounding failures -> reduce gain."""
        ctrl = LoopGainController()
        ctrl.apply(GainUpdate(delta=0.6, source="test"))
        ctrl.record_grounding_outcome(success=False)
        ctrl.record_grounding_outcome(success=False)
        assert ctrl.gain == 0.6
        ctrl.record_grounding_outcome(success=False)
        assert ctrl.gain < 0.6

    def test_consecutive_successes_raise_gain(self):
        """5 consecutive successes -> raise gain."""
        ctrl = LoopGainController()
        ctrl.apply(GainUpdate(delta=0.4, source="test"))
        for _ in range(4):
            ctrl.record_grounding_outcome(success=True)
        gain_before = ctrl.gain
        ctrl.record_grounding_outcome(success=True)
        assert ctrl.gain > gain_before

    def test_asymmetric_hysteresis(self):
        """Degrade is faster (3) than recover (5)."""
        ctrl = LoopGainController()
        ctrl.apply(GainUpdate(delta=0.5, source="test"))

        for _ in range(3):
            ctrl.record_grounding_outcome(success=False)
        degraded_gain = ctrl.gain
        assert degraded_gain < 0.5

        for _ in range(3):
            ctrl.record_grounding_outcome(success=True)
        assert ctrl.gain == degraded_gain

        ctrl.record_grounding_outcome(success=True)
        ctrl.record_grounding_outcome(success=True)
        assert ctrl.gain > degraded_gain

    def test_success_resets_failure_counter(self):
        ctrl = LoopGainController()
        ctrl.apply(GainUpdate(delta=0.5, source="test"))
        ctrl.record_grounding_outcome(success=False)
        ctrl.record_grounding_outcome(success=False)
        ctrl.record_grounding_outcome(success=True)
        ctrl.record_grounding_outcome(success=False)
        ctrl.record_grounding_outcome(success=False)
        assert ctrl.gain == 0.5


class TestGainHistory:
    def test_update_history_tracked(self):
        ctrl = LoopGainController()
        ctrl.apply(GainUpdate(delta=0.1, source="speech"))
        ctrl.apply(GainUpdate(delta=0.05, source="gaze"))
        assert len(ctrl.recent_updates) == 2
        assert ctrl.recent_updates[0].source == "speech"
        assert ctrl.recent_updates[1].source == "gaze"

    def test_history_bounded(self):
        ctrl = LoopGainController()
        for i in range(100):
            ctrl.apply(GainUpdate(delta=0.001, source=f"test_{i}"))
        assert len(ctrl.recent_updates) <= 50
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/hapax_daimonion/test_loop_gain.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# agents/hapax_daimonion/cpal/loop_gain.py
"""Loop gain controller -- continuous conversational intensity.

Replaces the binary session model (open/close) with a continuous
scalar 0.0 (ambient) to 1.0 (fully engaged). Gain emerges from
perception signals and modulates all conversational behavior.

Follows the same asymmetric hysteresis as all S1 components:
3 consecutive failures -> degrade, 5 consecutive successes -> recover.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from agents.hapax_daimonion.cpal.types import ConversationalRegion, GainUpdate

_DECAY_TAU = 15.0  # exponential decay time constant (seconds)
_DEGRADE_THRESHOLD = 3  # consecutive failures before gain reduction
_RECOVER_THRESHOLD = 5  # consecutive successes before gain boost
_DEGRADE_AMOUNT = 0.1  # gain reduction on degrade
_RECOVER_AMOUNT = 0.05  # gain boost on recover
_NEAR_ZERO = 0.005  # below this, clamp to 0.0
_HISTORY_MAXLEN = 50

_STIMMUNG_CEILINGS: dict[str, float] = {
    "nominal": 1.0,
    "cautious": 0.7,
    "degraded": 0.5,
    "critical": 0.3,
}


@dataclass
class LoopGainController:
    """Manages continuous conversational intensity.

    Gain is driven up by engagement signals and damped by silence,
    disengagement, and grounding failure. Stimmung acts as a ceiling.
    Hysteresis prevents oscillation.
    """

    _gain: float = 0.0
    _ceiling: float = 1.0
    _consecutive_failures: int = 0
    _consecutive_successes: int = 0
    _recent_updates: deque[GainUpdate] = field(
        default_factory=lambda: deque(maxlen=_HISTORY_MAXLEN)
    )

    @property
    def gain(self) -> float:
        return self._gain

    @property
    def region(self) -> ConversationalRegion:
        return ConversationalRegion.from_gain(self._gain)

    @property
    def recent_updates(self) -> list[GainUpdate]:
        return list(self._recent_updates)

    def apply(self, update: GainUpdate) -> None:
        """Apply a gain adjustment (driver or damper)."""
        self._gain = max(0.0, min(self._ceiling, self._gain + update.delta))
        self._recent_updates.append(update)

    def decay(self, dt: float) -> None:
        """Apply exponential silence decay over dt seconds."""
        self._gain *= math.exp(-dt / _DECAY_TAU)
        if self._gain < _NEAR_ZERO:
            self._gain = 0.0
        self._gain = min(self._gain, self._ceiling)

    def set_stimmung_ceiling(self, stance: str) -> None:
        """Set gain ceiling from stimmung stance. Enforced immediately."""
        self._ceiling = _STIMMUNG_CEILINGS.get(stance, 1.0)
        if self._gain > self._ceiling:
            self._gain = self._ceiling

    def record_grounding_outcome(self, *, success: bool) -> None:
        """Record a grounding success or failure for hysteresis.

        3 consecutive failures -> reduce gain (fast degrade).
        5 consecutive successes -> raise gain (slow recover).
        """
        if success:
            self._consecutive_failures = 0
            self._consecutive_successes += 1
            if self._consecutive_successes >= _RECOVER_THRESHOLD:
                self._gain = min(self._ceiling, self._gain + _RECOVER_AMOUNT)
                self._consecutive_successes = 0
        else:
            self._consecutive_successes = 0
            self._consecutive_failures += 1
            if self._consecutive_failures >= _DEGRADE_THRESHOLD:
                self._gain = max(0.0, self._gain - _DEGRADE_AMOUNT)
                self._consecutive_failures = 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_daimonion/test_loop_gain.py -v`
Expected: PASS — all 17 tests

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_daimonion/cpal/loop_gain.py tests/hapax_daimonion/test_loop_gain.py
git commit -m "feat(cpal): loop gain controller -- continuous intensity with hysteresis"
```

---

### Task 3: Conversation Control Law

**Files:**
- Create: `agents/hapax_daimonion/cpal/control_law.py`
- Create: `tests/hapax_daimonion/test_control_law.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/hapax_daimonion/test_control_law.py
"""Tests for CPAL conversation control law."""

from agents.hapax_daimonion.cpal.control_law import ConversationControlLaw
from agents.hapax_daimonion.cpal.types import (
    ConversationalRegion,
    CorrectionTier,
    ErrorDimension,
)


class TestControlLawEvaluation:
    def test_zero_error_ambient_no_action(self):
        """At ambient gain with no error, no correction needed."""
        law = ConversationControlLaw()
        result = law.evaluate(
            gain=0.05, ungrounded_du_count=0, repair_rate=0.0, gqi=0.8, silence_s=0.0,
        )
        assert result.error.magnitude < 0.1
        assert result.action_tier == CorrectionTier.T0_VISUAL

    def test_ungrounded_dus_raise_comprehension_error(self):
        law = ConversationControlLaw()
        result = law.evaluate(
            gain=0.6, ungrounded_du_count=3, repair_rate=0.0, gqi=0.5, silence_s=0.0,
        )
        assert result.error.comprehension > 0.3
        assert result.error.dominant == ErrorDimension.COMPREHENSION

    def test_declining_gqi_raises_affective_error(self):
        law = ConversationControlLaw()
        result = law.evaluate(
            gain=0.6, ungrounded_du_count=0, repair_rate=0.3, gqi=0.2, silence_s=0.0,
        )
        assert result.error.affective > 0.3
        assert result.error.dominant == ErrorDimension.AFFECTIVE

    def test_long_silence_raises_temporal_error(self):
        law = ConversationControlLaw()
        result = law.evaluate(
            gain=0.6, ungrounded_du_count=0, repair_rate=0.0, gqi=0.8, silence_s=20.0,
        )
        assert result.error.temporal > 0.3
        assert result.error.dominant == ErrorDimension.TEMPORAL

    def test_action_tier_scales_with_error(self):
        law = ConversationControlLaw()
        low = law.evaluate(gain=0.6, ungrounded_du_count=0, repair_rate=0.0, gqi=0.9, silence_s=0.0)
        high = law.evaluate(gain=0.6, ungrounded_du_count=5, repair_rate=0.5, gqi=0.2, silence_s=15.0)
        assert low.action_tier.value < high.action_tier.value

    def test_gain_modulates_action_tier(self):
        """Same error at low gain should produce lower-tier action."""
        law = ConversationControlLaw()
        low_gain = law.evaluate(gain=0.1, ungrounded_du_count=2, repair_rate=0.1, gqi=0.5, silence_s=5.0)
        high_gain = law.evaluate(gain=0.8, ungrounded_du_count=2, repair_rate=0.1, gqi=0.5, silence_s=5.0)
        assert low_gain.action_tier.value <= high_gain.action_tier.value


class TestControlSignalEmission:
    def test_emits_control_signal(self):
        law = ConversationControlLaw()
        result = law.evaluate(gain=0.5, ungrounded_du_count=1, repair_rate=0.1, gqi=0.6, silence_s=2.0)
        cs = result.control_signal
        assert cs.component == "conversation"
        assert 0.0 <= cs.reference <= 1.0
        assert 0.0 <= cs.perception <= 1.0
        assert cs.error >= 0.0

    def test_high_gqi_means_low_error(self):
        law = ConversationControlLaw()
        result = law.evaluate(gain=0.6, ungrounded_du_count=0, repair_rate=0.0, gqi=0.95, silence_s=0.0)
        assert result.control_signal.error < 0.15

    def test_low_gqi_means_high_error(self):
        law = ConversationControlLaw()
        result = law.evaluate(gain=0.6, ungrounded_du_count=3, repair_rate=0.3, gqi=0.1, silence_s=10.0)
        assert result.control_signal.error > 0.3


class TestRegionGating:
    def test_ambient_never_produces_vocal(self):
        law = ConversationControlLaw()
        result = law.evaluate(gain=0.05, ungrounded_du_count=5, repair_rate=0.5, gqi=0.1, silence_s=30.0)
        assert result.action_tier == CorrectionTier.T0_VISUAL

    def test_peripheral_max_t1(self):
        law = ConversationControlLaw()
        result = law.evaluate(gain=0.2, ungrounded_du_count=5, repair_rate=0.5, gqi=0.1, silence_s=30.0)
        assert result.action_tier in (CorrectionTier.T0_VISUAL, CorrectionTier.T1_PRESYNTHESIZED)

    def test_conversational_allows_t3(self):
        law = ConversationControlLaw()
        result = law.evaluate(gain=0.6, ungrounded_du_count=5, repair_rate=0.5, gqi=0.1, silence_s=30.0)
        assert result.action_tier == CorrectionTier.T3_FULL_FORMULATION
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/hapax_daimonion/test_control_law.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# agents/hapax_daimonion/cpal/control_law.py
"""Conversation control law -- the 15th S1 component.

Evaluates conversational state against the grounding reference and
selects a corrective action tier. Emits a ControlSignal for SCM
mesh-wide observability.

Reference: mutual understanding (GQI = 1.0 ideal).
Perception: current grounding state (GQI, ungrounded DUs, repair rate).
Error: gap between reference and perception.
Action: tiered correction proportional to error x gain.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.control_signal import ControlSignal

from agents.hapax_daimonion.cpal.types import (
    ConversationalRegion,
    CorrectionTier,
    ErrorSignal,
)

_REGION_MAX_TIER: dict[ConversationalRegion, CorrectionTier] = {
    ConversationalRegion.AMBIENT: CorrectionTier.T0_VISUAL,
    ConversationalRegion.PERIPHERAL: CorrectionTier.T1_PRESYNTHESIZED,
    ConversationalRegion.ATTENTIVE: CorrectionTier.T2_LIGHTWEIGHT,
    ConversationalRegion.CONVERSATIONAL: CorrectionTier.T3_FULL_FORMULATION,
    ConversationalRegion.INTENSIVE: CorrectionTier.T3_FULL_FORMULATION,
}

_TIER_ORDER = [
    CorrectionTier.T0_VISUAL,
    CorrectionTier.T1_PRESYNTHESIZED,
    CorrectionTier.T2_LIGHTWEIGHT,
    CorrectionTier.T3_FULL_FORMULATION,
]


@dataclass(frozen=True)
class ControlLawResult:
    """Result of a single control law evaluation."""

    error: ErrorSignal
    action_tier: CorrectionTier
    control_signal: ControlSignal
    region: ConversationalRegion


class ConversationControlLaw:
    """Evaluates conversational state and selects corrective action.

    Called on each tick. Reads grounding state, computes multi-dimensional
    error, selects the appropriate correction tier gated by current
    conversational region (loop gain).
    """

    def evaluate(
        self,
        *,
        gain: float,
        ungrounded_du_count: int,
        repair_rate: float,
        gqi: float,
        silence_s: float,
    ) -> ControlLawResult:
        comprehension = min(1.0, ungrounded_du_count * 0.15 + repair_rate)
        affective = max(0.0, 1.0 - gqi)
        temporal = min(1.0, silence_s / 30.0)

        error = ErrorSignal(
            comprehension=comprehension,
            affective=affective,
            temporal=temporal,
        )

        region = ConversationalRegion.from_gain(gain)

        suggested = error.suggested_tier
        max_allowed = _REGION_MAX_TIER[region]
        suggested_idx = _TIER_ORDER.index(suggested)
        max_idx = _TIER_ORDER.index(max_allowed)
        action_tier = _TIER_ORDER[min(suggested_idx, max_idx)]

        cs = ControlSignal(
            component="conversation",
            reference=1.0,
            perception=gqi,
        )

        return ControlLawResult(
            error=error,
            action_tier=action_tier,
            control_signal=cs,
            region=region,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_daimonion/test_control_law.py -v`
Expected: PASS — all 11 tests

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_daimonion/cpal/control_law.py tests/hapax_daimonion/test_control_law.py
git commit -m "feat(cpal): conversation control law -- error computation + region-gated action selection"
```

---

### Task 4: SHM Publisher

**Files:**
- Create: `agents/hapax_daimonion/cpal/shm_publisher.py`
- Create: `tests/hapax_daimonion/test_shm_publisher.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/hapax_daimonion/test_shm_publisher.py
"""Tests for CPAL /dev/shm publisher."""

import json

from agents.hapax_daimonion.cpal.loop_gain import LoopGainController
from agents.hapax_daimonion.cpal.shm_publisher import publish_cpal_state
from agents.hapax_daimonion.cpal.types import CorrectionTier, ErrorSignal, GainUpdate


class TestShmPublisher:
    def test_publishes_json(self, tmp_path):
        ctrl = LoopGainController()
        ctrl.apply(GainUpdate(delta=0.5, source="test"))
        error = ErrorSignal(comprehension=0.2, affective=0.1, temporal=0.0)

        publish_cpal_state(
            gain_controller=ctrl,
            error=error,
            action_tier=CorrectionTier.T1_PRESYNTHESIZED,
            path=tmp_path / "state.json",
        )

        data = json.loads((tmp_path / "state.json").read_text())
        assert data["gain"] == 0.5
        assert data["region"] == "conversational"
        assert data["error"]["comprehension"] == 0.2
        assert data["error"]["magnitude"] == 0.2
        assert data["action_tier"] == "t1_presynthesized"
        assert "timestamp" in data

    def test_atomic_write(self, tmp_path):
        ctrl = LoopGainController()
        error = ErrorSignal(0.0, 0.0, 0.0)

        publish_cpal_state(
            gain_controller=ctrl,
            error=error,
            action_tier=CorrectionTier.T0_VISUAL,
            path=tmp_path / "state.json",
        )

        data = json.loads((tmp_path / "state.json").read_text())
        assert data["gain"] == 0.0
        assert data["region"] == "ambient"

    def test_publishes_control_signal(self, tmp_path):
        ctrl = LoopGainController()
        ctrl.apply(GainUpdate(delta=0.6, source="test"))
        error = ErrorSignal(0.3, 0.1, 0.0)

        publish_cpal_state(
            gain_controller=ctrl,
            error=error,
            action_tier=CorrectionTier.T3_FULL_FORMULATION,
            health_path=tmp_path / "health.json",
            path=tmp_path / "state.json",
        )

        health = json.loads((tmp_path / "health.json").read_text())
        assert health["component"] == "conversation"
        assert 0.0 <= health["error"] <= 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/hapax_daimonion/test_shm_publisher.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# agents/hapax_daimonion/cpal/shm_publisher.py
"""Publish CPAL state to /dev/shm for SCM integration.

Writes two files atomically:
- /dev/shm/hapax-conversation/state.json -- full CPAL state
- /dev/shm/hapax-conversation/health.json -- ControlSignal for mesh health
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from shared.control_signal import ControlSignal, publish_health

from agents.hapax_daimonion.cpal.loop_gain import LoopGainController
from agents.hapax_daimonion.cpal.types import CorrectionTier, ErrorSignal

_DEFAULT_STATE_PATH = Path("/dev/shm/hapax-conversation/state.json")
_DEFAULT_HEALTH_PATH = Path("/dev/shm/hapax-conversation/health.json")


def publish_cpal_state(
    *,
    gain_controller: LoopGainController,
    error: ErrorSignal,
    action_tier: CorrectionTier,
    path: Path = _DEFAULT_STATE_PATH,
    health_path: Path = _DEFAULT_HEALTH_PATH,
) -> None:
    """Publish CPAL state atomically to /dev/shm."""
    state = {
        "gain": gain_controller.gain,
        "region": gain_controller.region.value,
        "error": {
            "comprehension": error.comprehension,
            "affective": error.affective,
            "temporal": error.temporal,
            "magnitude": error.magnitude,
            "dominant": error.dominant.value,
        },
        "action_tier": action_tier.value,
        "timestamp": time.time(),
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    tmp.rename(path)

    cs = ControlSignal(
        component="conversation",
        reference=1.0,
        perception=1.0 - error.magnitude,
    )
    publish_health(cs, path=health_path)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_daimonion/test_shm_publisher.py -v`
Expected: PASS — all 3 tests

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_daimonion/cpal/shm_publisher.py tests/hapax_daimonion/test_shm_publisher.py
git commit -m "feat(cpal): SHM publisher -- conversation state + health for SCM mesh"
```

---

### Task 5: Update Package Exports and Final Verification

**Files:**
- Modify: `agents/hapax_daimonion/cpal/__init__.py`

- [ ] **Step 1: Update package exports**

```python
# agents/hapax_daimonion/cpal/__init__.py
"""Conversational Perception-Action Loop (CPAL).

The 15th S1 component in the Stigmergic Cognitive Mesh.
Models conversation as a perceptual control loop with continuous
intensity (loop gain) replacing the binary session model.
"""

from agents.hapax_daimonion.cpal.control_law import ConversationControlLaw, ControlLawResult
from agents.hapax_daimonion.cpal.loop_gain import LoopGainController
from agents.hapax_daimonion.cpal.shm_publisher import publish_cpal_state
from agents.hapax_daimonion.cpal.types import (
    ConversationalRegion,
    CorrectionTier,
    ErrorDimension,
    ErrorSignal,
    GainUpdate,
)

__all__ = [
    "ConversationalRegion",
    "ConversationControlLaw",
    "ControlLawResult",
    "CorrectionTier",
    "ErrorDimension",
    "ErrorSignal",
    "GainUpdate",
    "LoopGainController",
    "publish_cpal_state",
]
```

- [ ] **Step 2: Run all CPAL tests**

Run: `uv run pytest tests/hapax_daimonion/test_cpal_types.py tests/hapax_daimonion/test_loop_gain.py tests/hapax_daimonion/test_control_law.py tests/hapax_daimonion/test_shm_publisher.py -v`
Expected: PASS — all 44 tests

- [ ] **Step 3: Run lint and format**

Run: `uv run ruff check agents/hapax_daimonion/cpal/ tests/hapax_daimonion/test_cpal_*.py && uv run ruff format --check agents/hapax_daimonion/cpal/ tests/hapax_daimonion/test_cpal_*.py`
Expected: All checks passed, all files already formatted

- [ ] **Step 4: Commit and push**

```bash
git add agents/hapax_daimonion/cpal/__init__.py
git commit -m "feat(cpal): complete Phase 1 -- package exports for control law, loop gain, SHM publisher"
git push origin main
```
