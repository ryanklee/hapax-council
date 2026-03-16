"""Visual communication layer — data models and display state machine.

Pure-logic module: no I/O, no threading, no network. Takes signal inputs
and produces display state + zone opacities. Fully testable in isolation.

Architecture:
  Signal Aggregator (polls API) → VisualLayerState (this module's output)
  → Studio Compositor (reads JSON, renders Cairo overlay)

Five display states, six signal categories, opacity-driven transitions.
Designed for ADHD/autism operator: muted palette, ≥500ms transitions,
max 5 simultaneous info chunks, flow-state-gated escalation.
"""

from __future__ import annotations

import time
from enum import StrEnum

from pydantic import BaseModel, Field

# ── Display States ───────────────────────────────────────────────────────────


class DisplayState(StrEnum):
    """Visual layer operating mode."""

    AMBIENT = "ambient"  # Generative shader only, no data (80% of time)
    PERIPHERAL = "peripheral"  # 1-2 subtle indicators at ~40% opacity (15%)
    INFORMATIONAL = "informational"  # Structured layout, readable (4%)
    ALERT = "alert"  # Critical signal breaks through (1%)
    PERFORMATIVE = "performative"  # Audio-reactive, rules suspended (<1%)


# ── Signal Categories ────────────────────────────────────────────────────────


class SignalCategory(StrEnum):
    """Visual zone categories. Each maps to a fixed spatial zone."""

    CONTEXT_TIME = "context_time"  # Top-left: calendar, briefing, copilot
    GOVERNANCE = "governance"  # Top-right: consent, axioms, drift
    WORK_TASKS = "work_tasks"  # Left edge: nudges, open loops, goals
    HEALTH_INFRA = "health_infra"  # Bottom-right: system health, GPU, containers
    PROFILE_STATE = "profile_state"  # Center-top: flow state, activity mode
    AMBIENT_SENSOR = "ambient_sensor"  # Bottom strip: audio energy, genre


# ── Zone Layout ──────────────────────────────────────────────────────────────


class ZoneSpec(BaseModel, frozen=True):
    """Zone position as fractions of canvas dimensions."""

    x: float  # Left edge (0.0-1.0)
    y: float  # Top edge (0.0-1.0)
    w: float  # Width fraction
    h: float  # Height fraction


ZONE_LAYOUT: dict[str, ZoneSpec] = {
    SignalCategory.CONTEXT_TIME: ZoneSpec(x=0.01, y=0.03, w=0.25, h=0.12),
    SignalCategory.GOVERNANCE: ZoneSpec(x=0.74, y=0.03, w=0.25, h=0.12),
    SignalCategory.WORK_TASKS: ZoneSpec(x=0.01, y=0.20, w=0.18, h=0.45),
    SignalCategory.HEALTH_INFRA: ZoneSpec(x=0.78, y=0.78, w=0.21, h=0.18),
    SignalCategory.PROFILE_STATE: ZoneSpec(x=0.35, y=0.01, w=0.30, h=0.06),
    SignalCategory.AMBIENT_SENSOR: ZoneSpec(x=0.01, y=0.92, w=0.75, h=0.06),
}


# ── Signal Entry ─────────────────────────────────────────────────────────────


class SignalEntry(BaseModel, frozen=True):
    """A single signal to potentially surface in the visual layer."""

    category: SignalCategory
    severity: float  # 0.0 (info) to 1.0 (critical)
    title: str
    detail: str = ""
    source_id: str = ""  # For dedup and dismissal tracking


# ── Ambient Parameters ───────────────────────────────────────────────────────


class AmbientParams(BaseModel):
    """Parameters for the generative ambient shader."""

    speed: float = 0.08  # Animation speed (0.0-1.0)
    turbulence: float = 0.1  # Noise complexity (0.0-1.0)
    color_warmth: float = 0.0  # 0.0 = cool teal, 1.0 = warm red
    brightness: float = 0.25  # Overall brightness


# ── Visual Layer State (output model) ────────────────────────────────────────


class VisualLayerState(BaseModel):
    """Complete state for the visual communication layer.

    Written atomically to /dev/shm/hapax-compositor/visual-layer-state.json
    by the signal aggregator. Read by the studio compositor for rendering.
    """

    display_state: DisplayState = DisplayState.AMBIENT
    zone_opacities: dict[str, float] = Field(default_factory=dict)
    signals: dict[str, list[SignalEntry]] = Field(default_factory=dict)
    ambient_params: AmbientParams = Field(default_factory=AmbientParams)
    timestamp: float = 0.0


# ── Opacity Targets per State ────────────────────────────────────────────────

# Each state defines target opacity for each zone category.
# The renderer interpolates toward these targets at ≥500ms rate.

_OPACITY_TARGETS: dict[DisplayState, dict[str, float]] = {
    DisplayState.AMBIENT: {
        SignalCategory.CONTEXT_TIME: 0.0,
        SignalCategory.GOVERNANCE: 0.0,
        SignalCategory.WORK_TASKS: 0.0,
        SignalCategory.HEALTH_INFRA: 0.0,
        SignalCategory.PROFILE_STATE: 0.0,
        SignalCategory.AMBIENT_SENSOR: 0.0,
    },
    DisplayState.PERIPHERAL: {
        SignalCategory.CONTEXT_TIME: 0.4,
        SignalCategory.GOVERNANCE: 0.4,
        SignalCategory.WORK_TASKS: 0.3,
        SignalCategory.HEALTH_INFRA: 0.3,
        SignalCategory.PROFILE_STATE: 0.2,
        SignalCategory.AMBIENT_SENSOR: 0.15,
    },
    DisplayState.INFORMATIONAL: {
        SignalCategory.CONTEXT_TIME: 0.75,
        SignalCategory.GOVERNANCE: 0.75,
        SignalCategory.WORK_TASKS: 0.7,
        SignalCategory.HEALTH_INFRA: 0.7,
        SignalCategory.PROFILE_STATE: 0.6,
        SignalCategory.AMBIENT_SENSOR: 0.5,
    },
    DisplayState.ALERT: {
        SignalCategory.CONTEXT_TIME: 0.5,
        SignalCategory.GOVERNANCE: 0.5,
        SignalCategory.WORK_TASKS: 0.4,
        SignalCategory.HEALTH_INFRA: 0.9,  # Health alerts are the primary alert source
        SignalCategory.PROFILE_STATE: 0.3,
        SignalCategory.AMBIENT_SENSOR: 0.3,
    },
    DisplayState.PERFORMATIVE: {
        SignalCategory.CONTEXT_TIME: 0.0,
        SignalCategory.GOVERNANCE: 0.0,
        SignalCategory.WORK_TASKS: 0.0,
        SignalCategory.HEALTH_INFRA: 0.0,  # Even health fades — only critical survives via alert
        SignalCategory.PROFILE_STATE: 0.0,
        SignalCategory.AMBIENT_SENSOR: 0.0,
    },
}

# ── Severity Thresholds ──────────────────────────────────────────────────────

SEVERITY_CRITICAL = 0.85  # Triggers ALERT state
SEVERITY_HIGH = 0.70  # Nudge priority "critical" or "high"
SEVERITY_MEDIUM = 0.40  # Visible in INFORMATIONAL
SEVERITY_LOW = 0.20  # Visible in PERIPHERAL only if space

# Max signals per zone (attention budget — ADHD research: 3-5 chunks)
MAX_SIGNALS_PER_ZONE = 3
MAX_TOTAL_VISIBLE_SIGNALS = 5

# ── De-escalation Cooldowns (seconds) ────────────────────────────────────────

_DEESCALATION_COOLDOWN: dict[tuple[DisplayState, DisplayState], float] = {
    (DisplayState.ALERT, DisplayState.INFORMATIONAL): 5.0,
    (DisplayState.ALERT, DisplayState.PERIPHERAL): 10.0,
    (DisplayState.ALERT, DisplayState.AMBIENT): 15.0,
    (DisplayState.INFORMATIONAL, DisplayState.PERIPHERAL): 8.0,
    (DisplayState.INFORMATIONAL, DisplayState.AMBIENT): 12.0,
    (DisplayState.PERIPHERAL, DisplayState.AMBIENT): 10.0,
}

# Performative transitions are smoother
_PERFORMATIVE_ENTER_S = 2.0
_PERFORMATIVE_EXIT_S = 5.0


# ── Display State Machine ────────────────────────────────────────────────────


class DisplayStateMachine:
    """Pure-logic state machine for the visual layer display mode.

    No I/O. Takes signal summaries and perception state, produces
    the next display state and zone opacities.

    Escalation is immediate — critical signals appear within one tick.
    De-escalation requires sustained quiet (cooldown timers).
    """

    def __init__(self) -> None:
        self.state = DisplayState.AMBIENT
        self._last_escalation_time: float = 0.0
        self._deescalation_timer: float = 0.0

    def tick(
        self,
        signals: list[SignalEntry],
        flow_score: float = 0.0,
        audio_energy: float = 0.0,
        production_active: bool = False,
        now: float | None = None,
    ) -> VisualLayerState:
        """Compute next state from current signals and perception.

        Args:
            signals: All active signals from the aggregator.
            flow_score: 0.0-1.0 from perception (flow_state_score behavior).
            audio_energy: 0.0-1.0 RMS audio energy.
            production_active: True if production_activity != "idle".
            now: Monotonic timestamp (defaults to time.monotonic()).

        Returns:
            Complete VisualLayerState for rendering.
        """
        if now is None:
            now = time.monotonic()

        max_severity = max((s.severity for s in signals), default=0.0)
        signal_count = len(signals)
        deep_flow = flow_score >= 0.6

        # Determine target state
        target = self._compute_target_state(
            max_severity=max_severity,
            signal_count=signal_count,
            deep_flow=deep_flow,
            production_active=production_active,
            audio_energy=audio_energy,
        )

        # Apply transition rules
        new_state = self._apply_transition(target, now)
        self.state = new_state

        # Categorize signals into zones
        categorized = self._categorize_signals(signals)

        # Compute zone opacities
        zone_opacities = self._compute_opacities(new_state, categorized)

        # Compute ambient shader parameters
        ambient = self._compute_ambient_params(max_severity, flow_score, audio_energy)

        return VisualLayerState(
            display_state=new_state,
            zone_opacities=zone_opacities,
            signals={cat: entries for cat, entries in categorized.items() if entries},
            ambient_params=ambient,
            timestamp=now,
        )

    def _compute_target_state(
        self,
        *,
        max_severity: float,
        signal_count: int,
        deep_flow: bool,
        production_active: bool,
        audio_energy: float,
    ) -> DisplayState:
        """Determine what state we WANT to be in based on current conditions."""
        # Performative: production + music + flow
        if production_active and audio_energy > 0.05 and deep_flow:
            return DisplayState.PERFORMATIVE

        # Alert: critical signal, even during flow
        if max_severity >= SEVERITY_CRITICAL:
            return DisplayState.ALERT

        # Deep flow: suppress everything below critical
        if deep_flow:
            return DisplayState.AMBIENT

        # Alert: high severity when not in flow
        if max_severity >= SEVERITY_HIGH:
            return DisplayState.ALERT

        # Informational: multiple signals or medium severity
        if signal_count >= 3 or max_severity >= SEVERITY_MEDIUM:
            return DisplayState.INFORMATIONAL

        # Peripheral: some signals
        if signal_count > 0:
            return DisplayState.PERIPHERAL

        # Nothing to show
        return DisplayState.AMBIENT

    def _apply_transition(self, target: DisplayState, now: float) -> DisplayState:
        """Apply hysteresis rules to state transitions.

        Escalation (toward higher urgency) is immediate.
        De-escalation requires sustained quiet for a cooldown period.
        """
        if target == self.state:
            self._deescalation_timer = now
            return self.state

        # Escalation order: AMBIENT < PERIPHERAL < INFORMATIONAL < ALERT
        # PERFORMATIVE is orthogonal
        escalation_order = {
            DisplayState.AMBIENT: 0,
            DisplayState.PERIPHERAL: 1,
            DisplayState.INFORMATIONAL: 2,
            DisplayState.ALERT: 3,
            DisplayState.PERFORMATIVE: -1,  # Special
        }

        current_level = escalation_order[self.state]
        target_level = escalation_order[target]

        # Performative transitions: always allowed (with smooth crossfade handled by renderer)
        if target == DisplayState.PERFORMATIVE or self.state == DisplayState.PERFORMATIVE:
            self._deescalation_timer = now
            return target

        # Escalation: immediate
        if target_level > current_level:
            self._last_escalation_time = now
            self._deescalation_timer = now
            return target

        # De-escalation: requires cooldown
        cooldown = _DEESCALATION_COOLDOWN.get((self.state, target), 10.0)
        elapsed = now - self._deescalation_timer
        if elapsed >= cooldown:
            return target

        # Not enough time has passed — stay in current state
        return self.state

    def _categorize_signals(self, signals: list[SignalEntry]) -> dict[str, list[SignalEntry]]:
        """Group signals by category, sorted by severity, capped per zone."""
        categorized: dict[str, list[SignalEntry]] = {cat.value: [] for cat in SignalCategory}

        for signal in sorted(signals, key=lambda s: s.severity, reverse=True):
            cat = signal.category.value
            if len(categorized[cat]) < MAX_SIGNALS_PER_ZONE:
                categorized[cat].append(signal)

        # Global attention budget: trim total visible signals
        all_signals = []
        for entries in categorized.values():
            all_signals.extend(entries)
        all_signals.sort(key=lambda s: s.severity, reverse=True)

        if len(all_signals) > MAX_TOTAL_VISIBLE_SIGNALS:
            keep = set(id(s) for s in all_signals[:MAX_TOTAL_VISIBLE_SIGNALS])
            for cat in categorized:
                categorized[cat] = [s for s in categorized[cat] if id(s) in keep]

        return categorized

    def _compute_opacities(
        self,
        state: DisplayState,
        categorized: dict[str, list[SignalEntry]],
    ) -> dict[str, float]:
        """Compute target opacity per zone based on state and signal presence."""
        base = dict(_OPACITY_TARGETS[state])

        # In ALERT state, boost the zone that contains the highest-severity signal
        if state == DisplayState.ALERT:
            max_cat = ""
            max_sev = 0.0
            for cat, entries in categorized.items():
                if entries and entries[0].severity > max_sev:
                    max_sev = entries[0].severity
                    max_cat = cat
            if max_cat:
                base[max_cat] = 0.95

        # Zero out zones with no signals (don't show empty zone chrome)
        for cat in base:
            if not categorized.get(cat):
                base[cat] = min(base[cat], 0.0)

        return base

    def _compute_ambient_params(
        self,
        max_severity: float,
        flow_score: float,
        audio_energy: float,
    ) -> AmbientParams:
        """Map system state to generative shader parameters.

        Healthy/calm = slow, cool, dim.
        Degraded = faster, warmer, brighter.
        Flow = minimal movement.
        """
        # Base: slow, cool, dim
        speed = 0.08
        turbulence = 0.1
        warmth = 0.0
        brightness = 0.25

        # Severity drives warmth and speed
        if max_severity > 0.0:
            warmth = min(1.0, max_severity)
            speed = 0.08 + 0.3 * max_severity
            turbulence = 0.1 + 0.3 * max_severity

        # Flow reduces movement (stability supports flow)
        if flow_score > 0.3:
            speed *= max(0.3, 1.0 - flow_score)
            turbulence *= max(0.3, 1.0 - flow_score)

        # Audio energy adds subtle life
        brightness = max(0.15, 0.25 + 0.1 * audio_energy)

        return AmbientParams(
            speed=round(speed, 3),
            turbulence=round(turbulence, 3),
            color_warmth=round(warmth, 3),
            brightness=round(brightness, 3),
        )
