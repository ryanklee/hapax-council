"""Tests for novel capability discovery meta-affordance."""

from agents.hapax_daimonion.discovery_affordance import (
    DISCOVERY_AFFORDANCE,
    CapabilityDiscoveryHandler,
)


def test_discovery_affordance_exists():
    name, desc = DISCOVERY_AFFORDANCE
    assert name == "capability_discovery"
    assert "discover" in desc.lower() or "find" in desc.lower()


def test_discovery_handler_extracts_unresolved_intent():
    from shared.impingement import Impingement, ImpingementType

    imp = Impingement(
        source="exploration.boredom",
        type=ImpingementType.BOREDOM,
        timestamp=0.0,
        strength=0.8,
        content={"narrative": "I wonder what that song sounds like"},
    )
    handler = CapabilityDiscoveryHandler()
    intent = handler.extract_intent(imp)
    assert "song" in intent.lower()


def test_discovery_handler_consent_required():
    handler = CapabilityDiscoveryHandler()
    assert handler.consent_required is True
