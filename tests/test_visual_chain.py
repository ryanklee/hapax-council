"""Tests for the visual chain capability — semantic visual expression."""

from agents.visual_chain import ParameterMapping, param_value_from_level


def test_param_value_at_zero():
    mapping = ParameterMapping(
        technique="gradient",
        param="brightness",
        breakpoints=[(0.0, 0.0), (0.5, 0.15), (1.0, 0.40)],
    )
    assert param_value_from_level(0.0, mapping.breakpoints) == 0.0


def test_param_value_at_midpoint():
    mapping = ParameterMapping(
        technique="gradient",
        param="brightness",
        breakpoints=[(0.0, 0.0), (0.5, 0.15), (1.0, 0.40)],
    )
    result = param_value_from_level(0.5, mapping.breakpoints)
    assert abs(result - 0.15) < 0.001


def test_param_value_interpolates():
    mapping = ParameterMapping(
        technique="gradient",
        param="brightness",
        breakpoints=[(0.0, 0.0), (1.0, 1.0)],
    )
    result = param_value_from_level(0.25, mapping.breakpoints)
    assert abs(result - 0.25) < 0.001


def test_param_value_clamps_below():
    mapping = ParameterMapping(
        technique="gradient",
        param="brightness",
        breakpoints=[(0.0, 0.0), (1.0, 1.0)],
    )
    assert param_value_from_level(-0.5, mapping.breakpoints) == 0.0


def test_param_value_clamps_above():
    mapping = ParameterMapping(
        technique="gradient",
        param="brightness",
        breakpoints=[(0.0, 0.0), (1.0, 1.0)],
    )
    assert param_value_from_level(1.5, mapping.breakpoints) == 1.0
