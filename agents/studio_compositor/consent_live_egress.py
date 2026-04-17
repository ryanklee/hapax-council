"""Consent live-egress gate — extends recording-valve enforcement to the
live video output path.

Phase 6 of the volitional-director epic (PR #1017, spec §5 Phase 6).

Gap that motivated this module (Agent 2 finding, 2026-04-17):
    "The recording valve (`agents/studio_compositor/recording.py:28`) and
    Qdrant gate (`shared/governance/qdrant_gate.py`) fail-close when a
    non-operator face is detected without an active consent contract.
    Live video egress to /dev/video42 + RTMP + HLS does NOT — it keeps
    broadcasting the frame."

Per axiom `interpersonal_transparency` + `it-irreversible-broadcast`
(T0, ratified 2026-04-15), any identifiable non-operator broadcast
without active contract is a T0 violation.

This module exposes a predicate the state reader can call on each tick
to decide whether to hot-swap into the consent-safe fallback layout
(`config/compositor-layouts/consent-safe.json`).
"""

from __future__ import annotations

import logging
from typing import Protocol

log = logging.getLogger(__name__)


class _OverlayDataLike(Protocol):
    """Minimal shape the predicate needs from OverlayData.

    Real shape is `agents/studio_compositor/models.OverlayData`; using a
    Protocol lets us test without constructing the whole model.
    """

    consent_phase: str | None
    guest_present: bool | None
    persistence_allowed: bool | None


# Consent phases treated as unsafe for live video egress. `guest_detected`
# (a face was found but contract not yet checked) and `consent_pending`
# (awaiting operator resolution) fail-closed: the axiom says a broadcast
# cannot proceed without an active contract, so any hesitation becomes
# compose-safe.
_UNSAFE_CONSENT_PHASES: frozenset[str] = frozenset(
    {
        "guest_detected",
        "consent_pending",
        "consent_refused",
    }
)


def should_egress_compose_safe(overlay_data: _OverlayDataLike) -> bool:
    """Return True if the current overlay state requires compose-safe egress.

    Rule:
      consent_phase in {guest_detected, consent_pending, consent_refused}
      OR (guest_present == True AND persistence_allowed != True)

    The second clause fires when guest_present has been set positively
    (vision-backend observed a non-operator face/body) even before a
    consent_phase transition has been recorded by the governance layer.
    It's a belt-and-suspenders check: the axiom demands fail-closed, so
    we prefer a false-positive compose-safe over a false-negative
    broadcast.
    """
    phase = getattr(overlay_data, "consent_phase", None)
    if isinstance(phase, str) and phase in _UNSAFE_CONSENT_PHASES:
        return True
    guest_present = getattr(overlay_data, "guest_present", None) is True
    persistence_allowed = getattr(overlay_data, "persistence_allowed", None) is True
    return bool(guest_present and not persistence_allowed)


# Location of the consent-safe fallback layout. The compositor's layout
# hot-swap reads this when the state reader signals egress-unsafe.
CONSENT_SAFE_LAYOUT_NAME: str = "consent-safe.json"


__all__ = [
    "should_egress_compose_safe",
    "CONSENT_SAFE_LAYOUT_NAME",
]
