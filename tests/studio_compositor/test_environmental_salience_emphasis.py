"""Tests for LRR Phase 8 item 11 — environmental salience emphasis."""

from __future__ import annotations

from pathlib import Path


class TestScoreIrHandSalience:
    def test_none_scores_zero(self):
        from agents.studio_compositor.environmental_salience_emphasis import _score_ir_hand_salience

        assert (
            _score_ir_hand_salience(
                {"overhead": {"ir_hand_activity": "none"}, "desk": {"ir_hand_activity": "none"}}
            )
            == 0.0
        )

    def test_takes_max_across_pis(self):
        from agents.studio_compositor.environmental_salience_emphasis import _score_ir_hand_salience

        assert (
            _score_ir_hand_salience(
                {"overhead": {"ir_hand_activity": "none"}, "desk": {"ir_hand_activity": "light"}}
            )
            == 0.5
        )

    def test_active_promotes_to_one(self):
        from agents.studio_compositor.environmental_salience_emphasis import _score_ir_hand_salience

        assert _score_ir_hand_salience({"overhead": {"ir_hand_activity": "active"}}) == 1.0

    def test_accepts_legacy_hand_activity_key(self):
        from agents.studio_compositor.environmental_salience_emphasis import _score_ir_hand_salience

        assert _score_ir_hand_salience({"overhead": {"hand_activity": "active"}}) == 1.0

    def test_unknown_label_scores_zero(self):
        from agents.studio_compositor.environmental_salience_emphasis import _score_ir_hand_salience

        assert _score_ir_hand_salience({"overhead": {"ir_hand_activity": "mystery"}}) == 0.0

    def test_non_dict_payload_ignored(self):
        from agents.studio_compositor.environmental_salience_emphasis import _score_ir_hand_salience

        assert _score_ir_hand_salience({"overhead": "not a dict"}) == 0.0


class TestObjectivePrefersEmphasis:
    def test_empty_returns_none(self):
        from agents.studio_compositor.environmental_salience_emphasis import (
            _objective_prefers_emphasis,
        )

        assert _objective_prefers_emphasis([]) is None

    def test_react_wins_over_observe(self):
        from agents.studio_compositor.environmental_salience_emphasis import (
            _objective_prefers_emphasis,
        )

        assert (
            _objective_prefers_emphasis(
                [
                    {"activities_that_advance": ["observe"]},
                    {"activities_that_advance": ["react"]},
                ]
            )
            == "react"
        )

    def test_observe_when_no_react(self):
        from agents.studio_compositor.environmental_salience_emphasis import (
            _objective_prefers_emphasis,
        )

        assert (
            _objective_prefers_emphasis([{"activities_that_advance": ["observe", "study"]}])
            == "observe"
        )

    def test_none_matches(self):
        from agents.studio_compositor.environmental_salience_emphasis import (
            _objective_prefers_emphasis,
        )

        assert _objective_prefers_emphasis([{"activities_that_advance": ["study", "chat"]}]) is None

    def test_non_list_activities_skipped(self):
        from agents.studio_compositor.environmental_salience_emphasis import (
            _objective_prefers_emphasis,
        )

        assert _objective_prefers_emphasis([{"activities_that_advance": "react"}]) is None


class TestRecommendEmphasis:
    def test_hysteresis_suppresses(self):
        from agents.studio_compositor.environmental_salience_emphasis import recommend_emphasis

        rec = recommend_emphasis(
            now_monotonic=100.0,
            last_emphasis_at=90.0,
            ir_reader=lambda: {"overhead": {"ir_hand_activity": "active"}},
            objectives_reader=lambda: [{"activities_that_advance": ["react"]}],
        )
        assert rec is None

    def test_no_matching_objective_returns_none(self):
        from agents.studio_compositor.environmental_salience_emphasis import recommend_emphasis

        rec = recommend_emphasis(
            now_monotonic=200.0,
            last_emphasis_at=0.0,
            ir_reader=lambda: {"overhead": {"ir_hand_activity": "active"}},
            objectives_reader=lambda: [{"activities_that_advance": ["study"]}],
        )
        assert rec is None

    def test_no_salience_returns_none(self):
        from agents.studio_compositor.environmental_salience_emphasis import recommend_emphasis

        rec = recommend_emphasis(
            now_monotonic=200.0,
            last_emphasis_at=0.0,
            ir_reader=lambda: {"overhead": {"ir_hand_activity": "none"}},
            objectives_reader=lambda: [{"activities_that_advance": ["react"]}],
        )
        assert rec is None

    def test_react_matches_any_salience(self):
        from agents.studio_compositor.environmental_salience_emphasis import recommend_emphasis

        rec = recommend_emphasis(
            now_monotonic=200.0,
            last_emphasis_at=0.0,
            ir_reader=lambda: {"overhead": {"ir_hand_activity": "light"}},
            objectives_reader=lambda: [{"activities_that_advance": ["react"]}],
        )
        assert rec is not None
        assert rec.camera_role == "hardware"
        assert rec.salience_score == 0.5
        assert "react" in rec.reason

    def test_observe_requires_high_salience(self):
        from agents.studio_compositor.environmental_salience_emphasis import recommend_emphasis

        light = recommend_emphasis(
            now_monotonic=200.0,
            last_emphasis_at=0.0,
            ir_reader=lambda: {"overhead": {"ir_hand_activity": "light"}},
            objectives_reader=lambda: [{"activities_that_advance": ["observe"]}],
        )
        assert light is None

        active = recommend_emphasis(
            now_monotonic=200.0,
            last_emphasis_at=0.0,
            ir_reader=lambda: {"overhead": {"ir_hand_activity": "active"}},
            objectives_reader=lambda: [{"activities_that_advance": ["observe"]}],
        )
        assert active is not None
        assert active.camera_role == "hardware"
        assert active.salience_score == 1.0

    def test_ttl_present_on_recommendation(self):
        from agents.studio_compositor.environmental_salience_emphasis import recommend_emphasis

        rec = recommend_emphasis(
            now_monotonic=200.0,
            last_emphasis_at=0.0,
            ir_reader=lambda: {"overhead": {"ir_hand_activity": "active"}},
            objectives_reader=lambda: [{"activities_that_advance": ["react"]}],
        )
        assert rec is not None and rec.ttl_seconds > 0

    def test_reader_defaults_are_filesystem(self, tmp_path: Path, monkeypatch):
        from agents.studio_compositor import environmental_salience_emphasis as mod

        ir_dir = tmp_path / "pi-noir"
        ir_dir.mkdir()
        (ir_dir / "overhead.json").write_text('{"ir_hand_activity": "active"}', encoding="utf-8")

        obj_dir = tmp_path / "objectives"
        obj_dir.mkdir()
        (obj_dir / "o.md").write_text(
            "---\nstatus: active\nactivities_that_advance: [react]\n---\n", encoding="utf-8"
        )

        monkeypatch.setattr(mod, "IR_STATE_DIR", ir_dir)
        monkeypatch.setattr(mod, "DEFAULT_OBJECTIVES_DIR", obj_dir)

        rec = mod.recommend_emphasis(now_monotonic=200.0, last_emphasis_at=0.0)
        assert rec is not None
        assert rec.camera_role == "hardware"
