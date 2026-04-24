"""Tests for ``agents.youtube_telemetry.client``."""

from __future__ import annotations

from unittest import mock

import pytest

from agents.youtube_telemetry.client import AnalyticsClient


def _fake_response(rows: list[list]) -> dict:
    return {"rows": rows}


class TestAnalyticsClient:
    def test_rejects_empty_channel_id(self):
        with pytest.raises(ValueError):
            AnalyticsClient(channel_id="")

    def test_realtime_returns_zero_when_no_rows(self):
        api = mock.Mock(return_value=_fake_response([]))
        client = AnalyticsClient(channel_id="UC-test", api_call=api)
        reading = client.read_realtime(now=1.0)
        assert reading.concurrent_viewers == 0.0
        assert reading.engagement_score is None
        assert reading.sampled_at == 1.0

    def test_realtime_returns_zero_when_value_unparseable(self):
        api = mock.Mock(return_value=_fake_response([["not-a-number"]]))
        client = AnalyticsClient(channel_id="UC-test", api_call=api)
        reading = client.read_realtime(now=1.0)
        assert reading.concurrent_viewers == 0.0

    def test_realtime_parses_numeric_row(self):
        responses = [
            _fake_response([[42.0]]),  # concurrentViewers
            _fake_response([[100.0]]),  # estimatedMinutesWatched
        ]
        api = mock.Mock(side_effect=responses)
        client = AnalyticsClient(channel_id="UC-test", api_call=api)
        reading = client.read_realtime(now=1.0)
        assert reading.concurrent_viewers == pytest.approx(42.0)
        assert reading.engagement_score == pytest.approx(100.0)

    def test_engagement_returns_none_on_empty(self):
        responses = [
            _fake_response([[10.0]]),
            _fake_response([]),  # no engagement available
        ]
        api = mock.Mock(side_effect=responses)
        client = AnalyticsClient(channel_id="UC-test", api_call=api)
        reading = client.read_realtime(now=1.0)
        assert reading.engagement_score is None

    def test_realtime_swallows_api_exception(self):
        api = mock.Mock(side_effect=RuntimeError("API outage"))
        client = AnalyticsClient(channel_id="UC-test", api_call=api)
        # Required metric defaults to zero; optional defaults to None.
        reading = client.read_realtime(now=1.0)
        assert reading.concurrent_viewers == 0.0
        assert reading.engagement_score is None

    def test_filter_uses_channel_id(self):
        captured = {}

        def _capture(**kwargs):
            captured.update(kwargs)
            return _fake_response([[1.0]])

        client = AnalyticsClient(channel_id="UC-special", api_call=_capture)
        client.read_realtime(now=1.0)
        assert captured["ids"] == "channel==UC-special"
