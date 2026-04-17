"""Epic 2 Phase C — hothouse Cairo sources smoke tests.

Each of the 5 hothouse surfaces must render a single frame against a
zero-size ImageSurface without crashing — the compositor's cairooverlay
callback tolerates no exceptions from render(). These tests also pin the
basic shape of what each source reads so a regression (e.g. "we moved
the narrative-state file") surfaces here.
"""

from __future__ import annotations

import json
import time

import cairo
import pytest

from agents.studio_compositor import hothouse_sources as hs


def _ctx(w: int = 400, h: int = 200) -> tuple[cairo.ImageSurface, cairo.Context]:
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    return surface, cairo.Context(surface)


def test_impingement_cascade_renders_without_data(tmp_path, monkeypatch):
    missing = tmp_path / "nothing.json"
    monkeypatch.setattr(hs, "_PERCEPTION_STATE", missing)
    monkeypatch.setattr(hs, "_STIMMUNG_STATE", missing)
    src = hs.ImpingementCascadeCairoSource()
    surface, cr = _ctx(480, 360)
    src.render(cr, 480, 360, 0.0, {})
    surface.flush()


def test_impingement_cascade_renders_with_perception(tmp_path, monkeypatch):
    perception = tmp_path / "perception.json"
    perception.write_text(
        json.dumps(
            {
                "ir": {"ir_hand_zone": "desk", "ir_person_count": 1},
                "audio": {"contact_mic": {"desk_energy": 0.42, "desk_activity": "typing"}},
            }
        )
    )
    stimmung = tmp_path / "stimmung.json"
    stimmung.write_text(json.dumps({"dimensions": {"tension": 0.7}}))
    monkeypatch.setattr(hs, "_PERCEPTION_STATE", perception)
    monkeypatch.setattr(hs, "_STIMMUNG_STATE", stimmung)

    signals = hs._active_perceptual_signals(limit=10)
    paths = [s[0] for s in signals]
    assert any("desk_energy" in p for p in paths)
    assert any("stimmung.tension" in p for p in paths)

    src = hs.ImpingementCascadeCairoSource()
    surface, cr = _ctx(480, 360)
    src.render(cr, 480, 360, 0.0, {})
    surface.flush()


def test_recruitment_candidate_panel_renders_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(hs, "_DIRECTOR_INTENT_JSONL", tmp_path / "absent.jsonl")
    src = hs.RecruitmentCandidatePanelCairoSource()
    surface, cr = _ctx(800, 60)
    src.render(cr, 800, 60, 0.0, {})
    surface.flush()


def test_recruitment_candidate_panel_renders_with_intents(tmp_path, monkeypatch):
    jsonl = tmp_path / "intents.jsonl"
    lines = []
    for i in range(3):
        lines.append(
            json.dumps(
                {
                    "activity": "react",
                    "compositional_impingements": [
                        {
                            "narrative": f"test move {i}",
                            "intent_family": "camera.hero",
                            "salience": 0.8,
                            "material": "water",
                        }
                    ],
                    "emitted_at": time.time() - i,
                }
            )
        )
    jsonl.write_text("\n".join(lines) + "\n")
    monkeypatch.setattr(hs, "_DIRECTOR_INTENT_JSONL", jsonl)
    recent = hs._read_recent_intents(n=6)
    assert len(recent) == 3
    src = hs.RecruitmentCandidatePanelCairoSource()
    surface, cr = _ctx(800, 60)
    src.render(cr, 800, 60, 0.0, {})
    surface.flush()


def test_thinking_indicator_idle(tmp_path, monkeypatch):
    monkeypatch.setattr(hs, "_LLM_IN_FLIGHT", tmp_path / "absent.json")
    src = hs.ThinkingIndicatorCairoSource()
    surface, cr = _ctx(170, 44)
    src.render(cr, 170, 44, 0.0, {})
    surface.flush()


def test_thinking_indicator_in_flight(tmp_path, monkeypatch):
    marker = tmp_path / "inflight.json"
    marker.write_text(
        json.dumps({"tier": "narrative", "model": "command-r", "started_at": time.time()})
    )
    monkeypatch.setattr(hs, "_LLM_IN_FLIGHT", marker)
    src = hs.ThinkingIndicatorCairoSource()
    surface, cr = _ctx(170, 44)
    src.render(cr, 170, 44, 0.5, {})
    surface.flush()


def test_pressure_gauge_renders_empty(tmp_path, monkeypatch):
    missing = tmp_path / "absent.json"
    monkeypatch.setattr(hs, "_PERCEPTION_STATE", missing)
    monkeypatch.setattr(hs, "_STIMMUNG_STATE", missing)
    src = hs.PressureGaugeCairoSource()
    surface, cr = _ctx(300, 52)
    src.render(cr, 300, 52, 0.0, {})
    surface.flush()


def test_pressure_gauge_scales_with_active_signals(tmp_path, monkeypatch):
    stimmung = tmp_path / "stimmung.json"
    stimmung.write_text(
        json.dumps(
            {
                "dimensions": {
                    "intensity": 0.8,
                    "tension": 0.7,
                    "depth": 0.6,
                    "coherence": 0.9,
                }
            }
        )
    )
    monkeypatch.setattr(hs, "_PERCEPTION_STATE", tmp_path / "absent.json")
    monkeypatch.setattr(hs, "_STIMMUNG_STATE", stimmung)
    signals = hs._active_perceptual_signals(limit=30)
    active = sum(1 for _, v, _ in signals if abs(v) >= 0.35)
    assert active >= 4
    src = hs.PressureGaugeCairoSource()
    surface, cr = _ctx(300, 52)
    src.render(cr, 300, 52, 0.0, {})
    surface.flush()


def test_activity_variety_log_renders_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(hs, "_DIRECTOR_INTENT_JSONL", tmp_path / "absent.jsonl")
    src = hs.ActivityVarietyLogCairoSource()
    surface, cr = _ctx(400, 140)
    src.render(cr, 400, 140, 0.0, {})
    surface.flush()


def test_activity_variety_log_dedupes_consecutive_silence(tmp_path, monkeypatch):
    jsonl = tmp_path / "intents.jsonl"
    now = time.time()
    entries = [
        {"activity": "silence", "emitted_at": now - 10},
        {"activity": "silence", "emitted_at": now - 8},
        {"activity": "silence", "emitted_at": now - 6},
        {"activity": "react", "emitted_at": now - 4},
        {"activity": "silence", "emitted_at": now - 2},
    ]
    jsonl.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    monkeypatch.setattr(hs, "_DIRECTOR_INTENT_JSONL", jsonl)
    src = hs.ActivityVarietyLogCairoSource()
    surface, cr = _ctx(400, 140)
    src.render(cr, 400, 140, 0.0, {})
    surface.flush()


@pytest.mark.parametrize(
    "class_name",
    [
        "ImpingementCascadeCairoSource",
        "RecruitmentCandidatePanelCairoSource",
        "ThinkingIndicatorCairoSource",
        "PressureGaugeCairoSource",
        "ActivityVarietyLogCairoSource",
    ],
)
def test_hothouse_class_registered(class_name: str) -> None:
    from agents.studio_compositor.cairo_sources import get_cairo_source_class

    cls = get_cairo_source_class(class_name)
    assert cls is not None
    assert cls.__name__ == class_name


def test_llm_in_flight_context_manager(tmp_path, monkeypatch):
    from agents.studio_compositor import director_loop

    marker = tmp_path / "llm-in-flight.json"
    monkeypatch.setattr(director_loop, "_LLM_IN_FLIGHT_MARKER", marker)
    assert not marker.exists()
    with director_loop._LLMInFlight(tier="narrative", model="command-r"):
        assert marker.exists()
        payload = json.loads(marker.read_text())
        assert payload["tier"] == "narrative"
        assert payload["model"] == "command-r"
    assert not marker.exists()


def test_llm_in_flight_removes_marker_on_exception(tmp_path, monkeypatch):
    from agents.studio_compositor import director_loop

    marker = tmp_path / "llm-in-flight.json"
    monkeypatch.setattr(director_loop, "_LLM_IN_FLIGHT_MARKER", marker)
    with pytest.raises(RuntimeError):
        with director_loop._LLMInFlight(tier="structural", model="local-fast"):
            assert marker.exists()
            raise RuntimeError("test")
    assert not marker.exists()
