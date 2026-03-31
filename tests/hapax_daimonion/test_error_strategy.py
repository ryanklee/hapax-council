"""Tests for the degradation registry."""

from __future__ import annotations

import pytest

from agents.hapax_daimonion.error_strategy import DegradationEvent, DegradationRegistry


class TestDegradationEvent:
    def test_fields(self):
        e = DegradationEvent(
            subsystem="backends",
            component="PipeWireBackend",
            severity="warning",
            message="not available",
            timestamp=1.0,
        )
        assert e.subsystem == "backends"
        assert e.component == "PipeWireBackend"
        assert e.severity == "warning"

    def test_frozen(self):
        e = DegradationEvent(
            subsystem="a", component="b", severity="info", message="c", timestamp=0.0
        )
        with pytest.raises(AttributeError):
            e.subsystem = "x"  # type: ignore[misc]


class TestDegradationRegistry:
    def test_record_and_retrieve(self):
        reg = DegradationRegistry()
        reg.record("backends", "Vision", "warning", "fdlite unavailable")
        assert len(reg.active()) == 1
        assert reg.active()[0].component == "Vision"

    def test_count_by_severity(self):
        reg = DegradationRegistry()
        reg.record("backends", "A", "warning", "msg")
        reg.record("backends", "B", "info", "msg")
        reg.record("audio", "C", "warning", "msg")
        counts = reg.count_by_severity()
        assert counts["warning"] == 2
        assert counts["info"] == 1

    def test_summary_format(self):
        reg = DegradationRegistry()
        reg.record("backends", "A", "warning", "msg")
        summary = reg.summary()
        assert "A" in summary
        assert "warning" in summary

    def test_empty_registry(self):
        reg = DegradationRegistry()
        assert reg.active() == []
        assert reg.count_by_severity() == {}
        assert "no degradations" in reg.summary().lower() or "No degradations" in reg.summary()
