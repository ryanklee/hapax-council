"""Tests for narrative gating logic in the orientation collector."""

from __future__ import annotations

from logos.data.orientation import _should_generate_narrative
from logos.data.session_inference import SessionContext


def _session(
    absence: float = 0.5,
    boundary: bool = False,
) -> SessionContext:
    return SessionContext(
        last_active_domain="research",
        absence_hours=absence,
        session_boundary=boundary,
    )


class TestNarrativeGating:
    def test_triggers_on_session_boundary(self):
        assert _should_generate_narrative(
            _session(absence=3.0, boundary=True),
            "nominal",
            last_narrative_age_s=7200.0,
        )

    def test_suppressed_during_degraded(self):
        assert not _should_generate_narrative(
            _session(absence=3.0, boundary=True),
            "degraded",
            last_narrative_age_s=7200.0,
        )

    def test_suppressed_during_critical(self):
        assert not _should_generate_narrative(
            _session(absence=3.0, boundary=True),
            "critical",
            last_narrative_age_s=7200.0,
        )

    def test_suppressed_when_recent_narrative(self):
        assert not _should_generate_narrative(
            _session(absence=3.0, boundary=True),
            "nominal",
            last_narrative_age_s=600.0,  # 10 min < 30 min
        )

    def test_triggers_on_morning(self):
        assert _should_generate_narrative(
            _session(absence=10.0, boundary=False),
            "nominal",
            last_narrative_age_s=36000.0,  # 10h
        )

    def test_no_trigger_steady_state(self):
        assert not _should_generate_narrative(
            _session(absence=0.5, boundary=False),
            "nominal",
            last_narrative_age_s=7200.0,
        )
