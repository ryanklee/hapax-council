"""Phase-4 smoke tests for legibility Cairo sources."""

from __future__ import annotations

import json

import cairo
import pytest

from agents.studio_compositor import legibility_sources as ls


def _render(src_cls, w=400, h=60):
    """Render into a fresh surface and return (surface, cr) for inspection."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    cr = cairo.Context(surface)
    src = src_cls()
    src.render(cr, w, h, t=0.0, state={})
    return surface


@pytest.fixture(autouse=True)
def _redirect_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(ls, "_NARRATIVE_STATE", tmp_path / "narrative-state.json")
    monkeypatch.setattr(ls, "_DIRECTOR_INTENT_JSONL", tmp_path / "director-intent.jsonl")
    monkeypatch.setattr(ls, "_WORKING_MODE_FILE", tmp_path / "working-mode")
    return tmp_path


def _write_narrative_state(tmp_path, stance="nominal", activity="react"):
    (tmp_path / "narrative-state.json").write_text(
        json.dumps({"stance": stance, "activity": activity, "last_tick_ts": 0, "condition_id": "c"})
    )


def _write_intent(tmp_path, prov=None, impingements=None):
    payload = {
        "activity": "vinyl",
        "stance": "nominal",
        "narrative_text": "",
        "grounding_provenance": prov or [],
        "compositional_impingements": impingements or [],
    }
    (tmp_path / "director-intent.jsonl").write_text(json.dumps(payload) + "\n")


class TestActivityHeader:
    def test_renders_without_state(self, tmp_path):
        surf = _render(ls.ActivityHeaderCairoSource, 800, 60)
        data = surf.get_data()
        # Non-empty render
        assert any(b != 0 for b in bytes(data[:1000]))

    def test_reads_narrative_and_intent(self, tmp_path):
        _write_narrative_state(tmp_path, activity="vinyl")
        _write_intent(
            tmp_path,
            impingements=[
                {"narrative": "turntable focus", "intent_family": "camera.hero", "salience": 0.9}
            ],
        )
        surf = _render(ls.ActivityHeaderCairoSource, 800, 60)
        assert surf.get_width() == 800


class TestStanceIndicator:
    def test_nominal_default(self, tmp_path):
        surf = _render(ls.StanceIndicatorCairoSource, 120, 40)
        assert surf.get_width() == 120

    def test_seeking_stance_from_file(self, tmp_path):
        _write_narrative_state(tmp_path, stance="seeking")
        surf = _render(ls.StanceIndicatorCairoSource, 120, 40)
        data = bytes(surf.get_data()[:4000])
        # Verify some content rendered
        assert any(b != 0 for b in data)

    def test_unknown_stance_fallback(self, tmp_path):
        _write_narrative_state(tmp_path, stance="bogus")
        # Should still render without crashing (dot uses fallback color)
        surf = _render(ls.StanceIndicatorCairoSource, 120, 40)
        assert surf is not None


class TestChatLegend:
    def test_renders_keywords(self, tmp_path):
        surf = _render(ls.ChatKeywordLegendCairoSource, 180, 200)
        assert surf.get_width() == 180


class TestGroundingTicker:
    def test_empty_provenance(self, tmp_path):
        surf = _render(ls.GroundingProvenanceTickerCairoSource, 500, 30)
        # No intent file — should render "(ungrounded)"
        assert surf.get_width() == 500

    def test_with_provenance(self, tmp_path):
        _write_intent(
            tmp_path,
            prov=[
                "audio.contact_mic.desk_activity.drumming",
                "visual.overhead_hand_zones.turntable",
            ],
        )
        surf = _render(ls.GroundingProvenanceTickerCairoSource, 500, 30)
        data = bytes(surf.get_data()[:2000])
        assert any(b != 0 for b in data)


class TestWorkingModePalette:
    def test_research_mode_default(self, tmp_path):
        assert ls._read_working_mode() == "research"
        pal = ls._palette()
        assert "fg_primary" in pal

    def test_rnd_mode_from_file(self, tmp_path):
        (tmp_path / "working-mode").write_text("rnd")
        assert ls._read_working_mode() == "rnd"


class TestRegistry:
    def test_all_four_registered(self, tmp_path):
        # Force re-import to trigger registration
        from agents.studio_compositor.cairo_sources import (
            get_cairo_source_class,
            list_classes,
        )

        classes = set(list_classes())
        assert "ActivityHeaderCairoSource" in classes
        assert "StanceIndicatorCairoSource" in classes
        assert "ChatKeywordLegendCairoSource" in classes
        assert "GroundingProvenanceTickerCairoSource" in classes
        # Fetchable
        assert get_cairo_source_class("ActivityHeaderCairoSource") is ls.ActivityHeaderCairoSource
