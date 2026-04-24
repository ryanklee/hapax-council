"""Tests for ``agents.youtube_telemetry.baseline``."""

from __future__ import annotations

import pytest

from agents.youtube_telemetry.baseline import RollingMedianBaseline


class TestRollingMedianBaseline:
    def test_empty_returns_none_until_min_samples(self):
        baseline = RollingMedianBaseline(min_samples=3)
        assert baseline.median() is None
        baseline.record(1.0)
        baseline.record(2.0)
        assert baseline.median() is None
        baseline.record(3.0)
        assert baseline.median() == pytest.approx(2.0)

    def test_evicts_oldest_at_cap(self):
        baseline = RollingMedianBaseline(cap=3, min_samples=1)
        baseline.extend([10.0, 20.0, 30.0])
        # Adding a 4th evicts the 10. Median of {20,30,40} = 30.
        baseline.record(40.0)
        assert len(baseline) == 3
        assert baseline.median() == pytest.approx(30.0)

    def test_negative_value_is_ignored(self):
        baseline = RollingMedianBaseline(min_samples=1)
        baseline.record(-5.0)
        assert baseline.median() is None
        baseline.record(10.0)
        assert baseline.median() == pytest.approx(10.0)

    def test_deviation_returns_none_until_baseline_warm(self):
        baseline = RollingMedianBaseline(min_samples=5)
        baseline.extend([10.0, 12.0])
        assert baseline.deviation(20.0) is None

    def test_deviation_returns_none_when_median_zero(self):
        baseline = RollingMedianBaseline(min_samples=1)
        baseline.extend([0.0, 0.0, 0.0])
        # median is 0; can't divide.
        assert baseline.deviation(5.0) is None

    def test_deviation_returns_none_for_negative_current(self):
        baseline = RollingMedianBaseline(min_samples=1)
        baseline.extend([10.0, 20.0])
        assert baseline.deviation(-1.0) is None

    def test_deviation_ratio_correct(self):
        baseline = RollingMedianBaseline(min_samples=1)
        baseline.extend([10.0, 10.0, 10.0])
        assert baseline.deviation(20.0) == pytest.approx(2.0)
        assert baseline.deviation(5.0) == pytest.approx(0.5)

    def test_rejects_invalid_construction(self):
        for bad in (0, -1):
            with pytest.raises(ValueError):
                RollingMedianBaseline(cap=bad)
            with pytest.raises(ValueError):
                RollingMedianBaseline(min_samples=bad)

    def test_extend_iterable(self):
        baseline = RollingMedianBaseline(min_samples=1)
        baseline.extend(range(1, 6))  # 1..5
        assert baseline.median() == pytest.approx(3.0)
