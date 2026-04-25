"""Perception-state → OperatorActivityEngine signal adapter.

Phase 6a-i.B partial wire-in for the activity-claim engine that #1375
shipped as engine math + signal contract without a live consumer.

Activity signals live in the daimonion-side ``perception-state.json``
(written by ``agents.hapax_daimonion._perception_state_writer``):

- ``keyboard_active``: bool, derived from evdev raw HID input
- ``desk_activity``: enum, contact-mic DSP gesture classifier
  (``idle`` / ``typing`` / ``tapping`` / ``drumming`` / ``active``)
- ``desktop_active``: bool, derived from Hyprland focus events
- ``desk_energy``: float, contact-mic RMS energy

This adapter exposes a ``operator_activity_observation`` builder that
takes any ``_PerceptionStateSource`` and returns a single-tick
observation dict for ``OperatorActivityEngine.contribute()``.

Wired so far:
- Part 1 (#1389): ``keyboard_active``
- Part 2 (this PR): ``desk_active``

Remaining 3 signals (``midi_clock_active``,
``desktop_focus_changed_recent``, ``watch_movement``) wire in
subsequent PRs as their production sources land — same additive
pattern beta uses in #1379 + #1377 + #1382 for SystemDegradedEngine.

Reference doc: ``docs/superpowers/research/2026-04-23-bayesian-claims-research.md``
§Phase 6a + the OperatorActivityEngine module docstring.
"""

from __future__ import annotations

from typing import Protocol


class _PerceptionStateSource(Protocol):
    """Anything exposing the activity signal accessors.

    The bridge in ``logos/api/app.py`` (``LogosPerceptionStateBridge``)
    matches this protocol; tests use a stub object with the same shape.
    Returning ``None`` from any accessor signals "perception state
    unavailable for this signal" — the Bayesian engine then skips that
    signal for the tick (no contribution rather than negative evidence;
    positional ``None`` semantics are documented in
    ``shared/claim.py::ClaimEngine.tick``).
    """

    def keyboard_active(self) -> bool | None: ...
    def desk_active(self) -> bool | None: ...


def operator_activity_observation(
    source: _PerceptionStateSource,
) -> dict[str, bool | None]:
    """Build a single-tick observation dict for OperatorActivityEngine.

    Currently emits ``keyboard_active`` (Part 1, #1389) +
    ``desk_active`` (Part 2, this PR). Each signal's contract is
    registered in ``shared/lr_registry.yaml::operator_activity_signals``:

    - ``keyboard_active``: bidirectional, idle keyboard → real negative
      evidence (no recent keystrokes in the perception window).
    - ``desk_active``: bidirectional, idle contact mic → mild negative
      evidence (LR weights 0.75/0.10 — operator may be reading without
      typing or tapping, but sustained silence is informative).

    Designed for callers like::

        from agents.hapax_daimonion.operator_activity_engine import OperatorActivityEngine
        from agents.hapax_daimonion.backends.operator_activity_observation import (
            operator_activity_observation,
        )

        engine = OperatorActivityEngine()
        engine.contribute(operator_activity_observation(perception_bridge))
    """
    return {
        "keyboard_active": source.keyboard_active(),
        "desk_active": source.desk_active(),
    }


__all__ = ["operator_activity_observation"]
