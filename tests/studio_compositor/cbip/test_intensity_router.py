"""Tests for cbip.intensity_router.

Spec §6.1.
"""

from __future__ import annotations

from agents.studio_compositor.cbip.intensity_router import (
    CbipIntensity,
    intensity_for_stimmung,
    resolve_effective_intensity,
)


def _stimmung(stance: str = "nominal", coherence: float = 1.0) -> dict:
    return {
        "overall_stance": {"value": stance},
        "physiological_coherence": {"value": coherence},
    }


# ── intensity_for_stimmung ───────────────────────────────────────────────


def test_nominal_stance_yields_full() -> None:
    assert intensity_for_stimmung(_stimmung("nominal")) is CbipIntensity.FULL


def test_seeking_stance_yields_full() -> None:
    assert intensity_for_stimmung(_stimmung("seeking")) is CbipIntensity.FULL


def test_cautious_stance_yields_mid() -> None:
    assert intensity_for_stimmung(_stimmung("cautious")) is CbipIntensity.MID


def test_degraded_stance_yields_off() -> None:
    assert intensity_for_stimmung(_stimmung("degraded")) is CbipIntensity.OFF


def test_critical_stance_yields_off() -> None:
    assert intensity_for_stimmung(_stimmung("critical")) is CbipIntensity.OFF


def test_unknown_stance_falls_back_to_mid() -> None:
    assert intensity_for_stimmung(_stimmung("contemplative")) is CbipIntensity.MID


def test_low_coherence_forces_off_regardless_of_stance() -> None:
    """Coherence trumps stance — recognizability over interesting-ness."""
    assert intensity_for_stimmung(_stimmung("nominal", coherence=0.1)) is CbipIntensity.OFF
    assert intensity_for_stimmung(_stimmung("seeking", coherence=0.2)) is CbipIntensity.OFF


def test_coherence_just_above_threshold_keeps_stance() -> None:
    assert intensity_for_stimmung(_stimmung("nominal", coherence=0.31)) is CbipIntensity.FULL


def test_missing_dimensions_default_to_mid() -> None:
    """Empty stimmung → conservative middle (no degradation, no stance)."""
    assert intensity_for_stimmung({}) is CbipIntensity.MID


def test_accepts_flat_dimension_values() -> None:
    """Some callers may pass flat scalars instead of {value: ...} dicts."""
    flat = {"overall_stance": "cautious", "physiological_coherence": 0.5}
    assert intensity_for_stimmung(flat) is CbipIntensity.MID


# ── resolve_effective_intensity (override surface) ───────────────────────


def test_no_override_uses_stimmung() -> None:
    assert resolve_effective_intensity(_stimmung("nominal"), override=None) is CbipIntensity.FULL
    assert resolve_effective_intensity(_stimmung("degraded"), override=None) is CbipIntensity.OFF


def test_override_zero_yields_off() -> None:
    assert resolve_effective_intensity(_stimmung("nominal"), override=0.0) is CbipIntensity.OFF


def test_override_full_yields_full() -> None:
    """Operator can override degraded stimmung to FULL if they want it."""
    assert resolve_effective_intensity(_stimmung("critical"), override=1.0) is CbipIntensity.FULL


def test_override_midpoint_yields_mid() -> None:
    assert resolve_effective_intensity(_stimmung("nominal"), override=0.5) is CbipIntensity.MID


def test_override_below_quarter_yields_off() -> None:
    assert resolve_effective_intensity(_stimmung("nominal"), override=0.20) is CbipIntensity.OFF


def test_override_just_below_full_threshold_yields_mid() -> None:
    assert resolve_effective_intensity(_stimmung("nominal"), override=0.74) is CbipIntensity.MID


def test_override_above_three_quarters_yields_full() -> None:
    assert resolve_effective_intensity(_stimmung("nominal"), override=0.75) is CbipIntensity.FULL


def test_override_negative_clamps_to_off() -> None:
    assert resolve_effective_intensity(_stimmung("nominal"), override=-0.5) is CbipIntensity.OFF


def test_override_above_one_clamps_to_full() -> None:
    assert resolve_effective_intensity(_stimmung("nominal"), override=1.5) is CbipIntensity.FULL
