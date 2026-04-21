"""Tests for cbip.ring2_gate (CBIP Phase 1 §5)."""

from __future__ import annotations

import time

from agents.studio_compositor.cbip.ring2_gate import (
    COPYRIGHT_FRESHNESS_MAX_AGE_S,
    GateName,
    GateOutcome,
    GateResult,
    Ring2PreRenderGate,
    _interpret_demonet_risk,
)


def _gate(
    *,
    in_clear_set: bool = True,
    last_check_age_s: float = 0.0,
    risk: float | str = 0.0,
    fixed_now: float = 1_700_000_000.0,
) -> Ring2PreRenderGate:
    last_check = (fixed_now - last_check_age_s) if last_check_age_s is not None else None
    return Ring2PreRenderGate(
        content_id_lookup=lambda track_id: in_clear_set,
        copyright_freshness_clock=lambda album_id: last_check,
        demonet_risk_scorer=lambda rendered: risk,
        now_fn=lambda: fixed_now,
    )


# ── Risk interpretation ─────────────────────────────────────────────────


def test_interpret_numeric_risk_below_threshold_allows() -> None:
    blocked, _ = _interpret_demonet_risk(0.39)
    assert blocked is False


def test_interpret_numeric_risk_at_threshold_blocks() -> None:
    blocked, _ = _interpret_demonet_risk(0.40)
    assert blocked is True


def test_interpret_numeric_risk_above_threshold_blocks() -> None:
    blocked, _ = _interpret_demonet_risk(0.85)
    assert blocked is True


def test_interpret_label_risk_low_allows() -> None:
    blocked, _ = _interpret_demonet_risk("low")
    assert blocked is False


def test_interpret_label_risk_none_allows() -> None:
    blocked, _ = _interpret_demonet_risk("none")
    assert blocked is False


def test_interpret_label_risk_medium_blocks() -> None:
    blocked, _ = _interpret_demonet_risk("medium")
    assert blocked is True


def test_interpret_label_risk_high_blocks() -> None:
    blocked, _ = _interpret_demonet_risk("HIGH")  # case-insensitive
    assert blocked is True


def test_interpret_out_of_range_numeric_fails_closed() -> None:
    blocked, reason = _interpret_demonet_risk(1.5)
    assert blocked is True
    assert "out of [0, 1]" in reason


def test_interpret_unknown_type_fails_closed() -> None:
    blocked, _ = _interpret_demonet_risk(None)  # type: ignore[arg-type]
    assert blocked is True


# ── Gate outcomes ───────────────────────────────────────────────────────


def test_all_three_pass_substitutes_nothing() -> None:
    gate = _gate(in_clear_set=True, last_check_age_s=10_000.0, risk=0.1)
    result = gate.evaluate(rendered=object(), track_id="t1", album_id="a1")
    assert result.passed
    assert result.substitute_phase_0 is False


def test_content_id_miss_blocks_and_substitutes() -> None:
    gate = _gate(in_clear_set=False, last_check_age_s=10_000.0, risk=0.1)
    result = gate.evaluate(rendered=object(), track_id="t1", album_id="a1")
    assert not result.passed
    assert result.substitute_phase_0 is True
    failures = [o.name for o in result.failures]
    assert GateName.CONTENT_ID in failures


def test_stale_copyright_blocks() -> None:
    gate = _gate(
        in_clear_set=True,
        last_check_age_s=COPYRIGHT_FRESHNESS_MAX_AGE_S + 1.0,
        risk=0.1,
    )
    result = gate.evaluate(rendered=object(), track_id="t1", album_id="a1")
    assert not result.passed
    failures = [o.name for o in result.failures]
    assert GateName.COPYRIGHT_FRESHNESS in failures


def test_no_copyright_check_record_blocks() -> None:
    gate = _gate(in_clear_set=True, risk=0.1)
    # Override the freshness clock to return None.
    gate.copyright_freshness_clock = lambda album_id: None
    result = gate.evaluate(rendered=object(), track_id="t1", album_id="a1")
    failures = [o.name for o in result.failures]
    assert GateName.COPYRIGHT_FRESHNESS in failures


def test_high_demonet_risk_blocks() -> None:
    gate = _gate(in_clear_set=True, last_check_age_s=10_000.0, risk=0.9)
    result = gate.evaluate(rendered=object(), track_id="t1", album_id="a1")
    failures = [o.name for o in result.failures]
    assert GateName.DEMONET_RISK in failures
    assert result.substitute_phase_0 is True


def test_label_risk_low_passes() -> None:
    gate = _gate(in_clear_set=True, last_check_age_s=10_000.0, risk="low")
    result = gate.evaluate(rendered=object(), track_id="t1", album_id="a1")
    assert result.passed


def test_label_risk_high_blocks() -> None:
    gate = _gate(in_clear_set=True, last_check_age_s=10_000.0, risk="high")
    result = gate.evaluate(rendered=object(), track_id="t1", album_id="a1")
    assert not result.passed


# ── Fail-closed on injected exceptions ─────────────────────────────────


def test_content_id_lookup_exception_fails_closed() -> None:
    def boom(track_id: str) -> bool:
        raise RuntimeError("fingerprint store offline")

    gate = Ring2PreRenderGate(
        content_id_lookup=boom,
        copyright_freshness_clock=lambda a: time.time(),
        demonet_risk_scorer=lambda r: 0.0,
    )
    result = gate.evaluate(rendered=object(), track_id="t1", album_id="a1")
    assert result.substitute_phase_0 is True
    content_id_outcome = next(o for o in result.outcomes if o.name == GateName.CONTENT_ID)
    assert "RuntimeError" in content_id_outcome.reason


def test_copyright_clock_exception_fails_closed() -> None:
    def boom(album_id: str) -> float:
        raise FileNotFoundError("metadata store missing")

    gate = Ring2PreRenderGate(
        content_id_lookup=lambda t: True,
        copyright_freshness_clock=boom,
        demonet_risk_scorer=lambda r: 0.0,
    )
    result = gate.evaluate(rendered=object(), track_id="t1", album_id="a1")
    assert result.substitute_phase_0 is True


def test_demonet_scorer_exception_fails_closed() -> None:
    def boom(rendered: object) -> float:
        raise TimeoutError("LLM gateway down")

    gate = Ring2PreRenderGate(
        content_id_lookup=lambda t: True,
        copyright_freshness_clock=lambda a: time.time(),
        demonet_risk_scorer=boom,
    )
    result = gate.evaluate(rendered=object(), track_id="t1", album_id="a1")
    assert result.substitute_phase_0 is True


# ── Reason strings ──────────────────────────────────────────────────────


def test_passing_outcome_has_human_reason() -> None:
    gate = _gate(in_clear_set=True, last_check_age_s=10_000.0, risk=0.0)
    result = gate.evaluate(rendered=object(), track_id="t1", album_id="a1")
    for o in result.outcomes:
        assert o.reason  # non-empty


def test_freshness_reason_includes_age() -> None:
    gate = _gate(in_clear_set=True, last_check_age_s=86400.0 * 30, risk=0.0)
    result = gate.evaluate(rendered=object(), track_id="t1", album_id="a1")
    freshness = next(o for o in result.outcomes if o.name == GateName.COPYRIGHT_FRESHNESS)
    assert "30.0d ago" in freshness.reason


# ── GateResult invariants ───────────────────────────────────────────────


def test_gate_result_failures_subset_of_outcomes() -> None:
    result = GateResult(
        outcomes=(
            GateOutcome(name=GateName.CONTENT_ID, passed=True),
            GateOutcome(name=GateName.COPYRIGHT_FRESHNESS, passed=False, reason="stale"),
            GateOutcome(name=GateName.DEMONET_RISK, passed=True),
        ),
        substitute_phase_0=True,
    )
    assert result.failures == (
        GateOutcome(name=GateName.COPYRIGHT_FRESHNESS, passed=False, reason="stale"),
    )
    assert result.passed is False


def test_gate_result_passed_when_all_outcomes_passed() -> None:
    result = GateResult(
        outcomes=tuple(GateOutcome(name=n, passed=True) for n in GateName),
        substitute_phase_0=False,
    )
    assert result.passed
    assert result.failures == ()
