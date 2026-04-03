"""Test that world context reaches the imagination."""

from agents.imagination import assemble_context


def test_weather_appears_in_context():
    snapshot = {
        "perception": {"activity": "idle", "flow_score": 0.3},
        "stimmung": {"stance": "nominal", "operator_stress": {"value": 0.2}},
        "watch": {"heart_rate": 72},
        "weather": {"temperature_f": 68, "humidity_pct": 45, "description": "Partly cloudy"},
    }
    ctx = assemble_context(["stable"], [], snapshot)
    assert "68" in ctx or "Partly cloudy" in ctx


def test_time_appears_in_context():
    snapshot = {
        "perception": {"activity": "coding", "flow_score": 0.7},
        "stimmung": {"stance": "nominal", "operator_stress": {"value": 0.1}},
        "watch": {"heart_rate": 65},
        "time": {
            "hour": 14,
            "period": "afternoon",
            "weekday": "Thursday",
            "date": "2026-04-03",
            "minute": 30,
        },
    }
    ctx = assemble_context(["active"], [], snapshot)
    assert "afternoon" in ctx


def test_music_appears_in_context():
    snapshot = {
        "perception": {"activity": "making_music", "flow_score": 0.9},
        "stimmung": {"stance": "nominal", "operator_stress": {"value": 0.1}},
        "watch": {"heart_rate": 80},
        "music": {"genre": "boom-bap", "mixer_energy": 0.7},
    }
    ctx = assemble_context(["active"], [], snapshot)
    assert "boom-bap" in ctx


def test_goals_appear_in_context():
    snapshot = {
        "perception": {"activity": "idle", "flow_score": 0.2},
        "stimmung": {"stance": "nominal", "operator_stress": {"value": 0.3}},
        "watch": {"heart_rate": 70},
        "goals": {"active_count": 3, "stale_count": 1, "top_domain": "research"},
    }
    ctx = assemble_context(["stable"], [], snapshot)
    assert "research" in ctx
