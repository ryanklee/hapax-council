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
