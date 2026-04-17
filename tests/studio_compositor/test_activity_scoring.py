"""Tests for LRR Phase 9 §3.2 — stimmung-modulated activity scoring."""

from __future__ import annotations

import json
from pathlib import Path


class TestEngagementFromChatSignals:
    def test_none_returns_zero(self):
        from agents.studio_compositor.activity_scoring import engagement_from_chat_signals

        assert engagement_from_chat_signals(None) == 0.0

    def test_missing_fields_return_zero(self):
        from agents.studio_compositor.activity_scoring import engagement_from_chat_signals

        assert engagement_from_chat_signals({}) == 0.0

    def test_all_max_yields_one(self):
        from agents.studio_compositor.activity_scoring import engagement_from_chat_signals

        signals = {
            "participant_diversity": 1.0,
            "semantic_coherence": 1.0,
            "thread_count": 3,
        }
        assert engagement_from_chat_signals(signals) == 1.0

    def test_thread_count_over_three_caps(self):
        from agents.studio_compositor.activity_scoring import engagement_from_chat_signals

        signals = {
            "participant_diversity": 1.0,
            "semantic_coherence": 1.0,
            "thread_count": 10,
        }
        assert engagement_from_chat_signals(signals) == 1.0

    def test_malformed_values_returns_zero(self):
        from agents.studio_compositor.activity_scoring import engagement_from_chat_signals

        assert (
            engagement_from_chat_signals(
                {"participant_diversity": "not a number", "thread_count": None}
            )
            == 0.0
        )

    def test_mixed_values_average(self):
        from agents.studio_compositor.activity_scoring import engagement_from_chat_signals

        signals = {
            "participant_diversity": 0.6,
            "semantic_coherence": 0.3,
            "thread_count": 3,
        }
        # (0.6 + 0.3 + 1.0) / 3 ≈ 0.633
        assert abs(engagement_from_chat_signals(signals) - 0.633) < 0.01


class TestStimmungTermForActivity:
    def test_chat_lifted_by_high_engagement_with_activity(self):
        from agents.studio_compositor.activity_scoring import stimmung_term_for_activity

        t = stimmung_term_for_activity("chat", engagement=0.9, active_chat_messages=5)
        assert t == 1.0

    def test_chat_not_lifted_without_active_messages(self):
        from agents.studio_compositor.activity_scoring import stimmung_term_for_activity

        t = stimmung_term_for_activity("chat", engagement=0.9, active_chat_messages=0)
        assert t == 0.0

    def test_chat_dropped_by_low_engagement(self):
        from agents.studio_compositor.activity_scoring import stimmung_term_for_activity

        t = stimmung_term_for_activity("chat", engagement=0.1)
        assert t == -0.5

    def test_study_lifted_by_low_engagement(self):
        from agents.studio_compositor.activity_scoring import stimmung_term_for_activity

        t = stimmung_term_for_activity("study", engagement=0.1)
        assert t == 1.0

    def test_silence_lifted_by_low_engagement(self):
        from agents.studio_compositor.activity_scoring import stimmung_term_for_activity

        t = stimmung_term_for_activity("silence", engagement=0.1)
        assert t == 0.5

    def test_react_modulates_softer_than_chat(self):
        from agents.studio_compositor.activity_scoring import stimmung_term_for_activity

        high = stimmung_term_for_activity("react", engagement=0.9, active_chat_messages=5)
        low = stimmung_term_for_activity("react", engagement=0.1)
        assert high == 0.5
        assert low == -0.25

    def test_observe_and_vinyl_are_neutral(self):
        from agents.studio_compositor.activity_scoring import stimmung_term_for_activity

        for a in ("observe", "vinyl"):
            assert stimmung_term_for_activity(a, engagement=0.9, active_chat_messages=10) == 0.0
            assert stimmung_term_for_activity(a, engagement=0.1) == 0.0

    def test_unknown_activity_neutral(self):
        from agents.studio_compositor.activity_scoring import stimmung_term_for_activity

        assert stimmung_term_for_activity("mystery", engagement=0.9) == 0.0

    def test_mid_range_engagement_is_zero_for_all(self):
        from agents.studio_compositor.activity_scoring import stimmung_term_for_activity

        for activity in ("chat", "react", "study", "silence"):
            assert (
                stimmung_term_for_activity(activity, engagement=0.45, active_chat_messages=5) == 0.0
            )


class TestScoreActivity:
    def test_default_weights_sum_one(self):
        from agents.studio_compositor.activity_scoring import (
            DEFAULT_MOMENTARY_WEIGHT,
            DEFAULT_OBJECTIVE_WEIGHT,
            DEFAULT_STIMMUNG_WEIGHT,
        )

        assert DEFAULT_MOMENTARY_WEIGHT + DEFAULT_OBJECTIVE_WEIGHT + DEFAULT_STIMMUNG_WEIGHT == 1.0

    def test_momentary_only_gives_weighted_value(self):
        from agents.studio_compositor.activity_scoring import score_activity

        assert score_activity("chat", momentary=1.0, objective_alignment=0.0) == 0.70

    def test_objective_only_gives_weighted_value(self):
        from agents.studio_compositor.activity_scoring import score_activity

        assert score_activity("chat", momentary=0.0, objective_alignment=1.0) == 0.25

    def test_stimmung_term_contributes_five_percent(self):
        from agents.studio_compositor.activity_scoring import score_activity

        base = score_activity("chat", momentary=0.5, objective_alignment=0.5)
        lifted = score_activity("chat", momentary=0.5, objective_alignment=0.5, stimmung_term=1.0)
        assert abs((lifted - base) - 0.05) < 1e-9

    def test_stimmung_clamped_to_plus_minus_one(self):
        from agents.studio_compositor.activity_scoring import score_activity

        clamped = score_activity("chat", momentary=0.5, objective_alignment=0.5, stimmung_term=5.0)
        one = score_activity("chat", momentary=0.5, objective_alignment=0.5, stimmung_term=1.0)
        assert clamped == one

    def test_inputs_clamped_to_unit_interval(self):
        from agents.studio_compositor.activity_scoring import score_activity

        low = score_activity("chat", momentary=-5.0, objective_alignment=-5.0)
        assert low == 0.0

        high = score_activity("chat", momentary=5.0, objective_alignment=5.0)
        assert abs(high - (0.70 + 0.25)) < 1e-9


class TestShmIntegration:
    def test_term_from_shm_round_trip(self, tmp_path: Path):
        from agents.studio_compositor.activity_scoring import stimmung_term_for_activity_from_shm

        path = tmp_path / "chat-signals.json"
        path.write_text(
            json.dumps(
                {
                    "participant_diversity": 1.0,
                    "novelty_rate": 0.8,
                    "thread_count": 3,
                    "semantic_coherence": 0.9,
                    "window_size": 20,
                    "ts": 1000.0,
                }
            ),
            encoding="utf-8",
        )

        term = stimmung_term_for_activity_from_shm("chat", active_chat_messages=5, path=path)
        assert term == 1.0

    def test_term_from_shm_missing_yields_zero(self, tmp_path: Path):
        from agents.studio_compositor.activity_scoring import stimmung_term_for_activity_from_shm

        term = stimmung_term_for_activity_from_shm(
            "chat", active_chat_messages=5, path=tmp_path / "nope.json"
        )
        # No signals → engagement 0.0 → low-path for chat → -0.5
        assert term == -0.5

    def test_term_from_shm_study_lifted_on_silence(self, tmp_path: Path):
        from agents.studio_compositor.activity_scoring import stimmung_term_for_activity_from_shm

        path = tmp_path / "chat-signals.json"
        path.write_text(
            json.dumps(
                {
                    "participant_diversity": 0.0,
                    "novelty_rate": 0.0,
                    "thread_count": 0,
                    "semantic_coherence": 0.0,
                    "window_size": 0,
                    "ts": 1.0,
                }
            ),
            encoding="utf-8",
        )

        assert stimmung_term_for_activity_from_shm("study", path=path) == 1.0
