# tests/hapax_daimonion/test_engagement.py
"""Tests for the engagement-based activation classifier."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

from agents.hapax_daimonion.engagement import EngagementClassifier


class TestStage2ContextWindow:
    def test_recent_system_speech_activates(self):
        ec = EngagementClassifier(on_engaged=MagicMock())
        ec._last_system_speech = time.monotonic() - 10.0
        assert ec._check_context_window() >= 0.9

    def test_old_system_speech_does_not_activate(self):
        ec = EngagementClassifier(on_engaged=MagicMock())
        ec._last_system_speech = time.monotonic() - 60.0
        assert ec._check_context_window() < 0.1

    def test_no_system_speech_returns_zero(self):
        ec = EngagementClassifier(on_engaged=MagicMock())
        ec._last_system_speech = 0.0
        assert ec._check_context_window() == 0.0


class TestStage2Exclusions:
    def test_phone_call_suppresses(self):
        ec = EngagementClassifier(on_engaged=MagicMock())
        behaviors = {"phone_call_active": MagicMock(value=True)}
        assert ec._check_exclusions(behaviors) < 0.1

    def test_no_phone_call_allows(self):
        ec = EngagementClassifier(on_engaged=MagicMock())
        behaviors = {"phone_call_active": MagicMock(value=False)}
        assert ec._check_exclusions(behaviors) >= 0.9

    def test_meeting_activity_suppresses(self):
        ec = EngagementClassifier(on_engaged=MagicMock())
        behaviors = {
            "phone_call_active": MagicMock(value=False),
            "activity_mode": MagicMock(value="meeting"),
        }
        assert ec._check_exclusions(behaviors) < 0.1


class TestStage2Gaze:
    def test_desk_gaze_activates(self):
        ec = EngagementClassifier(on_engaged=MagicMock())
        behaviors = {
            "ir_gaze_zone": MagicMock(value="desk", timestamp=time.monotonic()),
        }
        assert ec._check_gaze(behaviors) >= 0.7

    def test_away_gaze_does_not_activate(self):
        ec = EngagementClassifier(on_engaged=MagicMock())
        behaviors = {
            "ir_gaze_zone": MagicMock(value="away", timestamp=time.monotonic()),
        }
        assert ec._check_gaze(behaviors) < 0.3

    def test_stale_gaze_returns_neutral(self):
        ec = EngagementClassifier(on_engaged=MagicMock())
        behaviors = {
            "ir_gaze_zone": MagicMock(value="desk", timestamp=time.monotonic() - 10.0),
        }
        assert ec._check_gaze(behaviors) == 0.5


class TestStage2Fusion:
    def test_context_window_alone_activates(self):
        ec = EngagementClassifier(on_engaged=MagicMock())
        ec._last_system_speech = time.monotonic() - 5.0
        behaviors = {"phone_call_active": MagicMock(value=False)}
        score = ec.evaluate(behaviors)
        assert score >= 0.4

    def test_phone_call_blocks_even_with_context(self):
        ec = EngagementClassifier(on_engaged=MagicMock())
        ec._last_system_speech = time.monotonic() - 5.0
        behaviors = {"phone_call_active": MagicMock(value=True)}
        score = ec.evaluate(behaviors)
        assert score < 0.2


class TestFollowUpWindow:
    def test_follow_up_lowers_threshold(self):
        ec = EngagementClassifier(on_engaged=MagicMock())
        ec._follow_up_until = time.monotonic() + 30.0
        assert ec._in_follow_up_window()

    def test_expired_follow_up(self):
        ec = EngagementClassifier(on_engaged=MagicMock())
        ec._follow_up_until = time.monotonic() - 5.0
        assert not ec._in_follow_up_window()
