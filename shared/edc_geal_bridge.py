"""EDC → GEAL animation envelope bridge.

Converts an Enlightenment EDC ``signal`` / ``action: STATE_SET`` /
``transition`` triplet into a GEAL :class:`shared.geal_curves.Envelope`.
Lets GEAL inherit Rasterman's interaction-timing decisions (the same
decisions the Enlightenment WM has been refining since the late 90s)
rather than hand-tuning every primitive's three-phase parameters.

This module deliberately operates on **already-parsed triplets**, not
on raw ``.edc`` text. EDC text-parsing belongs to a sibling module
(``shared/aesthetic_library_loader.py`` per ytb-AUTH-PALETTE umbrella);
keeping the bridge text-format-agnostic means it can also bridge other
"signal + action + transition" sources (Qt animations, CSS transitions,
GTK CSS keyframes) without code duplication.

## Heuristic (per ytb-AUTH-GEAL spec)

The bridge maps EDC transition durations to GEAL three-phase segment
sizes by *what the operator perceives* — not by literal timing match,
because GEAL's animation grammar (§7) is anchored to a ~200 ms blink
floor that's strictly slower than EDC's ``transition: 0.0;`` instant
swaps.

| EDC transition (ms) | Mapping                            | Notes |
|---------------------|------------------------------------|-------|
| ``< 50``            | None (treat as instant; no curve)  | Below perceptual lift; caller should set state directly |
| ``50–100``          | near-instant 3-phase (clamped)     | Hits blink-floor; GEAL refuses faster |
| ``100–300``         | easeOut-shaped 3-phase             | Most common EDC range |
| ``> 300``           | full 3-phase, segment ratios       | Rasterman's "full transition" |

In every case where an envelope is returned, the commit (rise) segment
is clamped to ``>= GEAL_BLINK_FLOOR_MS`` (200 ms by default) so the
resulting curve always honours the §7 blink-floor invariant — the
GEAL test ``|dv/dt| < 1/0.2 s`` passes for any envelope this bridge
emits.

## Anti-personification

This module does NOT introduce eye / face / mouth / breath terminology
(GEAL anti-personification linter rejects those keywords in
``geal_*.py``). It speaks in segments, transitions, and commits —
purely mechanical.

Spec: ytb-AUTH-GEAL; depends on ytb-AUTH-HOMAGE (#1288).
GEAL spec: ``docs/superpowers/specs/2026-04-23-geal-spec.md`` §7.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from shared.geal_curves import Envelope

# GEAL §2 invariant 5: no step-functions faster than 200 ms.
# §6 mechanical test samples curves at 1 ms and asserts |dv/dt| < 1/0.2s.
# Bridge-emitted envelopes must respect this floor on every commit phase.
GEAL_BLINK_FLOOR_MS: float = 200.0

# Below this, treat EDC's "transition: <tiny>" as an explicit signal
# that the author wanted no animation at all — return None and let the
# caller set state directly. Above this and below the floor, we still
# emit a curve but clamp it to floor.
INSTANT_THRESHOLD_MS: float = 50.0

# Boundary between "easeOut shape" and "full three-phase" mappings.
THREE_PHASE_FLOOR_MS: float = 300.0

# Three-phase segment ratios for the >= 300 ms branch (sum to 1.0).
# Lifted from spec §7.5 cadence (e.g. S1 depth crossfade 120/90/600
# ≈ 0.15/0.11/0.74) — using the cleaner 0.15/0.25/0.60 split that the
# cc-task spec calls out as the default Rasterman-inherited shape.
ANTICIPATE_RATIO: float = 0.15
COMMIT_RATIO: float = 0.25
SETTLE_RATIO: float = 0.60


# Rough ms cost of the EDC "transition: 0.2;" syntax. EDC times are in
# seconds; one decimal of precision is what most EDC files carry.
_EDC_TRANSITION_RE = re.compile(r"transition\s*:\s*([0-9]*\.?[0-9]+)\s*;?")
_EDC_STATE_SET_RE = re.compile(r'STATE_SET\s+"([^"]+)"')


@dataclass(frozen=True)
class EdcTriplet:
    """The minimal information the bridge needs from a parsed EDC program.

    A real EDC program also names the source part, has scope rules, and
    references a target part — none of those affect the envelope shape,
    so they're out of scope for the bridge.
    """

    signal_name: str  # e.g. "mouse,in" — kept for callers that key by signal
    action: str  # e.g. 'STATE_SET "hover" 0.0' — bridge reads target state
    transition_time_ms: float  # converted from EDC's seconds-decimal


def parse_edc_transition_seconds(s: str) -> float | None:
    """Pull the ``transition: 0.2;`` value out of a fragment of EDC text.

    Returns the duration in milliseconds. Returns None if no transition
    directive is present (an EDC ``program`` without a transition is
    instant and should not animate).
    """
    match = _EDC_TRANSITION_RE.search(s)
    if match is None:
        return None
    return float(match.group(1)) * 1000.0


def parse_edc_state_set_target(action: str) -> str | None:
    """Extract the target state name from an EDC ``STATE_SET`` action.

    Returns None for non-STATE_SET actions (signal sends, callbacks,
    embryo program calls — out of scope for the bridge).
    """
    match = _EDC_STATE_SET_RE.search(action)
    if match is None:
        return None
    return match.group(1)


class EdcProgramAnalyzer:
    """Heuristic mapper from EDC ``signal/action/transition`` → GEAL Envelope.

    Stateless — every call resolves entirely from its arguments. Callers
    typically hold onto the returned :class:`Envelope` and tick it from
    the GEAL render loop.
    """

    @classmethod
    def envelope_for_transition(
        cls,
        transition_time_ms: float,
        *,
        fire_at_s: float = 0.0,
        peak_amp: float = 1.0,
        anticipate_amp: float = -0.10,
    ) -> Envelope | None:
        """Build a three-phase Envelope from an EDC transition duration.

        Args:
            transition_time_ms: EDC ``transition`` value, converted to ms.
                Negative values are treated as 0; sub-INSTANT_THRESHOLD_MS
                values return None.
            fire_at_s: When the resulting envelope should fire. Bridge
                callers usually pass the wall-clock time of the EDC
                signal trigger; defaults to 0 for unit-test ergonomics.
            peak_amp: Peak amplitude for the commit phase. Default 1.0
                matches GEAL's normalized primitive convention.
            anticipate_amp: Anticipate-segment counter-direction
                amplitude. Default -0.10 is GEAL's spec value (§7.1).

        Returns:
            None if ``transition_time_ms`` is below INSTANT_THRESHOLD_MS
            — caller should set state without animating.

            Otherwise an :class:`Envelope` whose commit segment is at
            least GEAL_BLINK_FLOOR_MS so the §6 mechanical
            ``|dv/dt| < 1/0.2 s`` test passes.
        """
        t = max(0.0, float(transition_time_ms))
        if t < INSTANT_THRESHOLD_MS:
            return None

        if t < THREE_PHASE_FLOOR_MS:
            # Mid-range: weighted shorter anticipate, longer commit
            # (easeOut character). Spec heuristic suggests
            # anticipate=50, commit=100, settle=t-150 — but commit=100
            # would violate blink-floor; clamp commit to the floor and
            # let settle absorb the remainder.
            anticipate_ms = 50.0
            commit_ms = max(GEAL_BLINK_FLOOR_MS, 100.0)
            settle_ms = max(0.0, t - anticipate_ms - commit_ms)
        else:
            # Long: spec ratios.
            anticipate_ms = ANTICIPATE_RATIO * t
            commit_ms = max(GEAL_BLINK_FLOOR_MS, COMMIT_RATIO * t)
            settle_ms = SETTLE_RATIO * t

        # Pick the settle tau from the same heuristic family GEAL §7.5
        # uses — log-decay tail roughly matches the visible commit
        # length so the "grace" segment doesn't overshoot the EDC
        # transition by more than ~2x.
        settle_tau_ms = max(150.0, commit_ms * 1.5)

        return Envelope.three_phase(
            fire_at_s=fire_at_s,
            anticipate_ms=anticipate_ms,
            commit_ms=commit_ms,
            settle_ms=settle_ms,
            anticipate_amp=anticipate_amp,
            peak_amp=peak_amp,
            settle_tau_ms=settle_tau_ms,
        )

    @classmethod
    def envelope_for_triplet(
        cls,
        triplet: EdcTriplet,
        *,
        fire_at_s: float = 0.0,
        peak_amp: float = 1.0,
        anticipate_amp: float = -0.10,
    ) -> Envelope | None:
        """Convenience wrapper — same as :meth:`envelope_for_transition`
        but takes the parsed triplet directly. ``signal_name`` and
        ``action`` are advisory metadata for the caller, not consumed
        by the envelope shape (an EDC ``mouse,in`` and ``mouse,out``
        with the same transition produce identical curves — direction
        of motion lives in the caller's state machine, not in GEAL)."""
        return cls.envelope_for_transition(
            triplet.transition_time_ms,
            fire_at_s=fire_at_s,
            peak_amp=peak_amp,
            anticipate_amp=anticipate_amp,
        )


__all__ = [
    "ANTICIPATE_RATIO",
    "COMMIT_RATIO",
    "EdcProgramAnalyzer",
    "EdcTriplet",
    "GEAL_BLINK_FLOOR_MS",
    "INSTANT_THRESHOLD_MS",
    "SETTLE_RATIO",
    "THREE_PHASE_FLOOR_MS",
    "parse_edc_state_set_target",
    "parse_edc_transition_seconds",
]
