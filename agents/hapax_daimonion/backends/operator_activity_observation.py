"""Perception-state → OperatorActivityEngine signal adapter.

Phase 6a-i.B partial wire-in for the activity-claim engine that #1375
shipped as engine math + signal contract without a live consumer.

Activity signals live in the daimonion-side ``perception-state.json``
(written by ``agents.hapax_daimonion._perception_state_writer``):

- ``keyboard_active``: bool, derived from evdev raw HID input
- ``desktop_active``: bool, derived from Hyprland focus events
- ``desk_activity`` / ``desk_energy``: contact-mic DSP

This adapter exposes a ``operator_activity_observation`` builder that
takes any ``_PerceptionStateSource`` (anything implementing
``keyboard_active() -> bool | None``) and returns a single-tick
observation dict for ``OperatorActivityEngine.contribute()``.

Phase 6a-i.B Part 1 wires only ``keyboard_active``. The other 4
signals (``midi_clock_active``, ``desk_active``,
``desktop_focus_changed_recent``, ``watch_movement``) wire in
subsequent PRs as their production sources land — same additive
pattern beta used in #1379 + #1377 for SystemDegradedEngine.

Reference doc: ``docs/superpowers/research/2026-04-23-bayesian-claims-research.md``
§Phase 6a + the OperatorActivityEngine module docstring.
"""

from __future__ import annotations

from typing import Protocol


class _PerceptionStateSource(Protocol):
    """Anything exposing ``keyboard_active() -> bool | None``.

    The bridge in ``logos/api/app.py`` (``LogosPerceptionStateBridge``)
    matches this protocol; tests use a stub object with the same shape.
    Returning ``None`` signals "perception state unavailable" — the
    Bayesian engine then skips this signal for the tick (no contribution
    rather than negative evidence; positional ``None`` semantics are
    documented in ``shared/claim.py::ClaimEngine.tick``).
    """

    def keyboard_active(self) -> bool | None: ...


def operator_activity_observation(
    source: _PerceptionStateSource,
) -> dict[str, bool | None]:
    """Build a single-tick observation dict for OperatorActivityEngine.

    Returns ``{"keyboard_active": True | False | None}`` per
    ``shared/lr_registry.yaml::operator_activity_signals.keyboard_active``
    (bidirectional ``positive_only=False``: idle keyboard is real
    negative evidence for activity — no recent keystrokes within the
    perception window).

    Designed for callers like::

        from agents.hapax_daimonion.operator_activity_engine import OperatorActivityEngine
        from agents.hapax_daimonion.backends.operator_activity_observation import (
            operator_activity_observation,
        )

        engine = OperatorActivityEngine()
        engine.contribute(operator_activity_observation(perception_bridge))
    """
    return {"keyboard_active": source.keyboard_active()}


__all__ = ["operator_activity_observation"]
