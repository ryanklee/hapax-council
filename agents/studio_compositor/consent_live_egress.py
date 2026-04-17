"""Consent live-egress gate — extends recording-valve enforcement to the
live video output path.

Phase 6 of the volitional-director epic (PR #1017, spec §5 Phase 6).
Hardened to fail-closed in Epic 2 Phase A2 after audit flagged fail-open
edge cases.

Per axiom `interpersonal_transparency` + `it-irreversible-broadcast`
(T0, ratified 2026-04-15), any identifiable non-operator broadcast
without active contract is a T0 violation. Predicate defaults to
compose-safe on ANY ambiguity.
"""

from __future__ import annotations

import logging
import os
from typing import Protocol

log = logging.getLogger(__name__)


class _OverlayDataLike(Protocol):
    """Minimal shape the predicate needs from OverlayData."""

    consent_phase: str | None
    guest_present: bool | None
    persistence_allowed: bool | None


# Whitelist of consent phases under which broadcast is permitted.
# The only explicitly-safe phase is `consent_granted` (active contract
# for a present non-operator). A solo-operator state is represented by
# `consent_phase = None` with `guest_present in (None, False)`; that's
# handled separately.
_SAFE_CONSENT_PHASES: frozenset[str] = frozenset({"consent_granted"})

# Phases that must fire compose-safe immediately.
_UNSAFE_CONSENT_PHASES: frozenset[str] = frozenset(
    {
        "guest_detected",
        "consent_pending",
        "consent_refused",
    }
)


def should_egress_compose_safe(
    overlay_data: _OverlayDataLike | None,
    *,
    state_is_stale: bool = False,
) -> bool:
    """Return True if the current overlay state requires compose-safe egress.

    Axiom it-irreversible-broadcast T0 — fail-closed on ambiguity. Broadcast
    is only permitted when all of these hold:

    - ``overlay_data is not None``
    - ``not state_is_stale``
    - ``HAPAX_CONSENT_EGRESS_GATE != 0``
    - EITHER ``consent_phase == "consent_granted"`` (active contract) OR
      solo-operator state (``consent_phase is None`` and
      ``guest_present in (None, False)``)
    - ``guest_present`` is not True without persistence_allowed
    - ``consent_phase`` is not a known-unsafe value
    - ``consent_phase`` is not an unknown string (future phases fail closed)

    Returns True (compose-safe) if any condition is violated.
    """
    # Disable-flag escape hatch — logged at module load.
    if _gate_disabled:
        return False

    if overlay_data is None:
        return True
    if state_is_stale:
        return True

    phase = getattr(overlay_data, "consent_phase", None)
    guest_present = getattr(overlay_data, "guest_present", None)
    persistence_allowed = getattr(overlay_data, "persistence_allowed", None)

    # Known unsafe phases.
    if isinstance(phase, str) and phase in _UNSAFE_CONSENT_PHASES:
        return True

    # Unknown future phases fail closed.
    if isinstance(phase, str) and phase not in _SAFE_CONSENT_PHASES:
        return True

    # Solo-operator is OK: no guest observed, phase unset.
    solo_operator = phase is None and guest_present in (None, False)
    if solo_operator:
        return False

    # Active-contract state: must also have persistence allowance + no
    # flagged guest without allowance.
    if guest_present is True and persistence_allowed is not True:
        return True

    # Phase == "consent_granted" and guest accounted for — broadcast OK.
    # Any other state (phase None but guest_present True, etc.) fails closed.
    return phase != "consent_granted"


def _is_gate_disabled() -> bool:
    value = os.environ.get("HAPAX_CONSENT_EGRESS_GATE", "").strip().lower()
    return value in {"0", "false", "off", "disabled"}


_gate_disabled = _is_gate_disabled()
if _gate_disabled:
    log.warning(
        "HAPAX_CONSENT_EGRESS_GATE disabled at module load — "
        "live-egress compose-safe predicate will return False unconditionally. "
        "This is an axiom-violating override; expect an audit event."
    )


# Location of the consent-safe fallback layout.
CONSENT_SAFE_LAYOUT_NAME: str = "consent-safe.json"


__all__ = [
    "should_egress_compose_safe",
    "CONSENT_SAFE_LAYOUT_NAME",
]
