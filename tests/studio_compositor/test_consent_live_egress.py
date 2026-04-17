"""Phase-6 + Epic-2-A2 tests for consent live-egress predicate — fail-closed."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agents.studio_compositor import consent_live_egress as cle
from agents.studio_compositor.consent_live_egress import (
    CONSENT_SAFE_LAYOUT_NAME,
    should_egress_compose_safe,
)


def _od(**kwargs):
    defaults = {
        "consent_phase": None,
        "guest_present": False,
        "persistence_allowed": True,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.fixture(autouse=True)
def _no_disable(monkeypatch):
    monkeypatch.setattr(cle, "_gate_disabled", False)


class TestFailClosedTriggers:
    def test_none_overlay_data_is_unsafe(self):
        assert should_egress_compose_safe(None) is True

    def test_state_stale_is_unsafe(self):
        assert should_egress_compose_safe(_od(), state_is_stale=True) is True

    def test_guest_detected_is_unsafe(self):
        assert should_egress_compose_safe(_od(consent_phase="guest_detected")) is True

    def test_consent_pending_is_unsafe(self):
        assert should_egress_compose_safe(_od(consent_phase="consent_pending")) is True

    def test_consent_refused_is_unsafe(self):
        assert should_egress_compose_safe(_od(consent_phase="consent_refused")) is True

    def test_unknown_phase_is_unsafe(self):
        assert should_egress_compose_safe(_od(consent_phase="contract_expiring")) is True

    def test_guest_present_without_persistence_is_unsafe(self):
        assert (
            should_egress_compose_safe(_od(guest_present=True, persistence_allowed=False)) is True
        )

    def test_guest_present_without_phase_is_unsafe(self):
        assert should_egress_compose_safe(_od(guest_present=True)) is True


class TestSafeTriggers:
    def test_solo_operator_is_safe(self):
        assert should_egress_compose_safe(_od()) is False

    def test_consent_granted_is_safe(self):
        assert (
            should_egress_compose_safe(
                _od(
                    consent_phase="consent_granted",
                    guest_present=True,
                    persistence_allowed=True,
                )
            )
            is False
        )


class TestDisableFlag:
    def test_disable_flag_bypasses_all(self, monkeypatch):
        monkeypatch.setattr(cle, "_gate_disabled", True)
        assert (
            should_egress_compose_safe(_od(consent_phase="guest_detected", guest_present=True))
            is False
        )

    def test_disable_flag_values(self, monkeypatch):
        for val in ("0", "false", "off", "disabled"):
            monkeypatch.setenv("HAPAX_CONSENT_EGRESS_GATE", val)
            assert cle._is_gate_disabled() is True
        for val in ("1", "true", "", "on"):
            monkeypatch.setenv("HAPAX_CONSENT_EGRESS_GATE", val)
            assert cle._is_gate_disabled() is False


class TestRegression:
    def test_layout_name_is_stable(self):
        assert CONSENT_SAFE_LAYOUT_NAME == "consent-safe.json"
