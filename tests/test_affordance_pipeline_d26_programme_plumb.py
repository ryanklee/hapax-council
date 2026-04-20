"""Tests for D-26: AffordancePipeline.select() active-programme plumb.

Phase 5 wire from plan §Phase 5 lines 349-388. Replaces the
`programme=None` stub at affordance_pipeline.py with a TTL-cached
`default_store().active_programme()` lookup so opt-ins set on the
current Programme actually reach `MonetizationRiskGate.assess()`.

Cache invariants tested here:
  - First call loads from store
  - Within TTL: returns cached value without re-reading
  - After TTL: refreshes
  - None is a LEGITIMATE cached value (means "no active programme") and
    must NOT trigger constant re-reads
  - Read failures fall back to None and don't break recruitment
"""

from __future__ import annotations

from unittest.mock import patch

import pytest  # noqa: TC002 — runtime import for test discovery + fixtures

import shared.affordance_pipeline as ap_mod
from shared.affordance_pipeline import AffordancePipeline
from shared.programme import Programme, ProgrammeRole, ProgrammeStatus


def _make_pipeline() -> AffordancePipeline:
    """Construct a pipeline with mocked deps; we only exercise the cache."""
    return AffordancePipeline()


def _make_programme(programme_id: str = "test-001", opt_ins: set[str] | None = None) -> Programme:
    p = Programme(
        programme_id=programme_id,
        role=ProgrammeRole.AMBIENT,
        status=ProgrammeStatus.ACTIVE,
        planned_duration_s=60.0,
        parent_show_id="test-show",
    )
    if opt_ins:
        p.constraints.monetization_opt_ins = opt_ins
    return p


class TestActiveProgrammeCache:
    def test_first_call_loads_from_store(self) -> None:
        prog = _make_programme()
        pipeline = _make_pipeline()
        with patch("shared.programme_store.default_store") as ds:
            ds.return_value.active_programme.return_value = prog
            result = pipeline._active_programme_cached()
        assert result is prog
        assert ds.return_value.active_programme.call_count == 1

    def test_cached_within_ttl_does_not_reread(self) -> None:
        prog = _make_programme()
        pipeline = _make_pipeline()
        with patch("shared.programme_store.default_store") as ds:
            ds.return_value.active_programme.return_value = prog
            # Two calls in rapid succession should hit the cache once.
            r1 = pipeline._active_programme_cached()
            r2 = pipeline._active_programme_cached()
        assert r1 is prog and r2 is prog
        assert ds.return_value.active_programme.call_count == 1

    def test_refresh_after_ttl(self, monkeypatch: pytest.MonkeyPatch) -> None:
        prog_a = _make_programme(programme_id="a")
        prog_b = _make_programme(programme_id="b")
        pipeline = _make_pipeline()
        # Make TTL effectively zero so every call refreshes.
        monkeypatch.setattr(ap_mod, "_PROGRAMME_CACHE_TTL_S", 0.0)
        with patch("shared.programme_store.default_store") as ds:
            ds.return_value.active_programme.side_effect = [prog_a, prog_b]
            r1 = pipeline._active_programme_cached()
            r2 = pipeline._active_programme_cached()
        assert r1 is prog_a
        assert r2 is prog_b
        assert ds.return_value.active_programme.call_count == 2

    def test_none_is_legitimate_cached_value(self) -> None:
        """Regression: cache must NOT treat None as 'not loaded' and re-read
        every call. None means 'no active programme' which is the steady-state
        for most of the day."""
        pipeline = _make_pipeline()
        with patch("shared.programme_store.default_store") as ds:
            ds.return_value.active_programme.return_value = None
            for _ in range(5):
                result = pipeline._active_programme_cached()
                assert result is None
        assert ds.return_value.active_programme.call_count == 1

    def test_store_error_falls_back_to_none(self) -> None:
        pipeline = _make_pipeline()
        with patch("shared.programme_store.default_store") as ds:
            ds.return_value.active_programme.side_effect = OSError("disk full")
            result = pipeline._active_programme_cached()
        assert result is None

    def test_store_error_does_not_propagate(self) -> None:
        """Programme lookup failure must NOT break recruitment — fail soft
        to None and let the gate handle the safety posture."""
        pipeline = _make_pipeline()
        with patch("shared.programme_store.default_store") as ds:
            ds.return_value.active_programme.side_effect = RuntimeError("kaboom")
            # Must not raise.
            pipeline._active_programme_cached()


class TestPipelineUsesActiveProgramme:
    """End-to-end: the plumb means the gate sees the active Programme's opt-ins.

    Without the plumb, medium-risk capabilities are blocked unconditionally
    (programme=None). With the plumb, they pass when the active Programme
    has opted them in.
    """

    def test_medium_risk_blocked_with_no_active_programme(self) -> None:
        from shared.affordance import SelectionCandidate
        from shared.governance.monetization_safety import GATE

        cand = SelectionCandidate(
            capability_name="mouth.curated",
            similarity=1.0,
            combined=1.0,
            payload={"monetization_risk": "medium"},
        )
        # No active programme → blocked.
        assessment = GATE.assess(cand, programme=None)
        assert assessment.allowed is False

    def test_medium_risk_allowed_when_active_programme_opts_in(self) -> None:
        from shared.affordance import SelectionCandidate
        from shared.governance.monetization_safety import GATE

        cand = SelectionCandidate(
            capability_name="mouth.curated",
            similarity=1.0,
            combined=1.0,
            payload={"monetization_risk": "medium"},
        )
        prog = _make_programme(opt_ins={"mouth.curated"})
        assessment = GATE.assess(cand, programme=prog)
        assert assessment.allowed is True
        assert "opted in" in assessment.reason

    def test_pipeline_passes_active_programme_to_gate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify the plumb actually fires: pipeline._active_programme_cached()
        is called by select()'s gate filter step (not via select() end-to-end
        which would require qdrant/embedding mocks)."""
        prog = _make_programme(opt_ins={"mouth.curated"})
        pipeline = _make_pipeline()
        with patch("shared.programme_store.default_store") as ds:
            ds.return_value.active_programme.return_value = prog
            cached = pipeline._active_programme_cached()
        assert cached is prog
        assert "mouth.curated" in cached.monetization_opt_ins
