"""Tests for ``agents.youtube_telemetry.salience``."""

from __future__ import annotations

import pytest

from agents.youtube_telemetry.salience import (
    AMBIENT_SALIENCE,
    DROP_SALIENCE,
    DROP_THRESHOLD,
    SPIKE_SALIENCE,
    SPIKE_THRESHOLD,
    STALE_SALIENCE,
    classify,
    stale_verdict,
)


class TestClassify:
    def test_none_deviation_is_ambient(self):
        v = classify(None)
        assert v.kind == "ambient"
        assert v.salience == AMBIENT_SALIENCE

    def test_at_baseline_is_ambient(self):
        v = classify(1.0)
        assert v.kind == "ambient"

    def test_just_below_spike_is_ambient(self):
        v = classify(SPIKE_THRESHOLD - 0.01)
        assert v.kind == "ambient"

    def test_at_spike_threshold_is_spike(self):
        v = classify(SPIKE_THRESHOLD)
        assert v.kind == "spike"
        assert v.salience == SPIKE_SALIENCE

    def test_above_spike_is_spike(self):
        v = classify(5.0)
        assert v.kind == "spike"

    def test_at_drop_threshold_is_drop(self):
        v = classify(DROP_THRESHOLD)
        assert v.kind == "drop"
        assert v.salience == DROP_SALIENCE

    def test_below_drop_is_drop(self):
        v = classify(0.1)
        assert v.kind == "drop"

    def test_just_above_drop_is_ambient(self):
        v = classify(DROP_THRESHOLD + 0.01)
        assert v.kind == "ambient"


class TestStaleVerdict:
    def test_kind_stale_zero_salience(self):
        v = stale_verdict()
        assert v.kind == "stale"
        assert v.salience == STALE_SALIENCE

    def test_stale_constants_consistent(self):
        # Sanity: stale must have lower salience than the ambient
        # baseline; otherwise the bus consumer can't distinguish a
        # missed read from an uneventful tick by salience alone.
        assert STALE_SALIENCE < AMBIENT_SALIENCE


class TestSalienceTable:
    """Pin the decision table from the cc-task §Design ‘salience mapping’."""

    @pytest.mark.parametrize(
        ("deviation", "expected_kind", "expected_salience"),
        [
            (None, "ambient", 0.2),
            (1.0, "ambient", 0.2),
            (1.5, "ambient", 0.2),
            (2.0, "spike", 0.7),
            (3.0, "spike", 0.7),
            (0.5, "drop", 0.5),
            (0.25, "drop", 0.5),
        ],
    )
    def test_table(self, deviation, expected_kind, expected_salience):
        v = classify(deviation)
        assert v.kind == expected_kind
        assert v.salience == pytest.approx(expected_salience)
