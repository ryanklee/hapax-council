"""Phase-6 tests for consent live-egress predicate."""

from __future__ import annotations

from types import SimpleNamespace

from agents.studio_compositor.consent_live_egress import (
    CONSENT_SAFE_LAYOUT_NAME,
    should_egress_compose_safe,
)


def _od(**kwargs):
    """Build a duck-typed OverlayData for the predicate."""
    defaults = {"consent_phase": None, "guest_present": False, "persistence_allowed": True}
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestConsentPhases:
    def test_guest_detected_is_unsafe(self):
        assert should_egress_compose_safe(_od(consent_phase="guest_detected")) is True

    def test_consent_pending_is_unsafe(self):
        assert should_egress_compose_safe(_od(consent_phase="consent_pending")) is True

    def test_consent_refused_is_unsafe(self):
        assert should_egress_compose_safe(_od(consent_phase="consent_refused")) is True

    def test_consent_granted_is_safe(self):
        assert should_egress_compose_safe(_od(consent_phase="consent_granted")) is False

    def test_no_phase_is_safe(self):
        assert should_egress_compose_safe(_od(consent_phase=None)) is False


class TestGuestPresentBeltAndSuspenders:
    def test_guest_present_with_persistence_disallowed(self):
        """guest_present=True + persistence_allowed!=True → unsafe even without phase."""
        assert (
            should_egress_compose_safe(
                _od(
                    guest_present=True,
                    persistence_allowed=False,
                )
            )
            is True
        )

    def test_guest_present_with_persistence_allowed(self):
        """Consent-granted contract with guest_present=True + persistence True → safe."""
        assert (
            should_egress_compose_safe(_od(guest_present=True, persistence_allowed=True)) is False
        )


class TestRegression:
    def test_all_fields_none_is_safe(self):
        """Pre-any-signal state: no consent phase, guest field absent, persistence unknown. Safe."""
        assert should_egress_compose_safe(_od()) is False

    def test_layout_name_is_stable(self):
        assert CONSENT_SAFE_LAYOUT_NAME == "consent-safe.json"
