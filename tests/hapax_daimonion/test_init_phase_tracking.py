"""Tests for daemon init phase tracking."""

from __future__ import annotations

from agents.hapax_daimonion.init_phase import InitPhase


class TestInitPhase:
    def test_phase_enum_values(self):
        assert InitPhase.CORE.value == "core"
        assert InitPhase.PERCEPTION.value == "perception"
        assert InitPhase.STATE.value == "state"
        assert InitPhase.VOICE.value == "voice"
        assert InitPhase.ACTUATION.value == "actuation"

    def test_all_phases_covered(self):
        assert len(InitPhase) == 5

    def test_phase_tracking_simulation(self):
        """Simulate init tracking without constructing a full daemon."""
        completed: set[InitPhase] = set()
        failed: dict[InitPhase, str] = {}

        for phase in InitPhase:
            completed.add(phase)

        assert len(completed) == 5
        assert len(failed) == 0

    def test_partial_failure_simulation(self):
        completed: set[InitPhase] = set()
        failed: dict[InitPhase, str] = {}

        completed.add(InitPhase.CORE)
        failed[InitPhase.PERCEPTION] = "No backends available"

        assert InitPhase.CORE in completed
        assert InitPhase.PERCEPTION not in completed
        assert InitPhase.PERCEPTION in failed
