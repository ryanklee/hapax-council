"""Tests for destination recruitment — medium declared, not inferred from names."""

from shared.affordance import OperationalProperties


def test_operational_properties_has_medium():
    ops = OperationalProperties(medium="auditory")
    assert ops.medium == "auditory"


def test_medium_defaults_to_none():
    ops = OperationalProperties()
    assert ops.medium is None


def test_medium_accepts_known_values():
    for medium in ("auditory", "visual", "textual", "notification", None):
        ops = OperationalProperties(medium=medium)
        assert ops.medium == medium


def test_visual_chain_has_visual_medium():
    from agents.visual_chain import VISUAL_CHAIN_RECORDS

    for rec in VISUAL_CHAIN_RECORDS:
        assert rec.operational.medium == "visual", f"{rec.name} missing visual medium"


def test_vocal_chain_has_auditory_medium():
    from agents.hapax_daimonion.vocal_chain import VOCAL_CHAIN_RECORDS

    for rec in VOCAL_CHAIN_RECORDS:
        assert rec.operational.medium == "auditory", f"{rec.name} missing auditory medium"


def test_expression_coordinator_uses_medium_not_name():
    from pathlib import Path

    source = Path("shared/expression.py").read_text()
    assert '"speech" in name' not in source, "Still uses name substring for speech"
    assert '"voice" in name' not in source, "Still uses name substring for voice"
    assert '"shader" in name' not in source, "Still uses name substring for shader"
    assert '"visual" in name' not in source, "Still uses name substring for visual"
