"""Tests for Continuous-Loop Research Cadence §3.6 — emphasis timer driver."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def tick_mod():
    if "environmental_emphasis_tick" in sys.modules:
        return sys.modules["environmental_emphasis_tick"]
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "environmental_emphasis_tick.py"
    spec = importlib.util.spec_from_file_location("environmental_emphasis_tick", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["environmental_emphasis_tick"] = module
    spec.loader.exec_module(module)
    return module


class TestReadLastEmphasisAt:
    def test_missing_file_returns_zero(self, tick_mod, tmp_path: Path):
        assert tick_mod._read_last_emphasis_at(tmp_path / "absent.json") == 0.0

    def test_malformed_file_returns_zero(self, tick_mod, tmp_path: Path):
        p = tmp_path / "bad.json"
        p.write_text("not json", encoding="utf-8")
        assert tick_mod._read_last_emphasis_at(p) == 0.0

    def test_valid_file_returns_stored_value(self, tick_mod, tmp_path: Path):
        p = tmp_path / "state.json"
        p.write_text(json.dumps({"last_emphasis_at": 1234.5}), encoding="utf-8")
        assert tick_mod._read_last_emphasis_at(p) == 1234.5

    def test_non_float_value_returns_zero(self, tick_mod, tmp_path: Path):
        p = tmp_path / "state.json"
        p.write_text(json.dumps({"last_emphasis_at": "not a number"}), encoding="utf-8")
        assert tick_mod._read_last_emphasis_at(p) == 0.0


class TestWriteLastEmphasisAt:
    def test_writes_atomic(self, tick_mod, tmp_path: Path):
        p = tmp_path / "state.json"
        tick_mod._write_last_emphasis_at(p, 999.0)
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data == {"last_emphasis_at": 999.0}

    def test_creates_parent_dir(self, tick_mod, tmp_path: Path):
        nested = tmp_path / "a" / "b" / "state.json"
        tick_mod._write_last_emphasis_at(nested, 1.0)
        assert nested.exists()


class TestWriteHeroOverride:
    def test_writes_all_fields(self, tick_mod, tmp_path: Path):
        p = tmp_path / "hero.json"
        tick_mod._write_hero_override(p, "hardware", "ir_hand=1.0", 1.0, 100.0)
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data == {
            "hero_role": "hardware",
            "reason": "ir_hand=1.0",
            "salience_score": 1.0,
            "ts": 100.0,
        }


class TestTick:
    def test_no_recommendation_no_override_written(
        self, tick_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        state = tmp_path / "state.json"
        hero = tmp_path / "hero.json"
        monkeypatch.setenv("HAPAX_ENV_EMPHASIS_STATE_FILE", str(state))
        monkeypatch.setenv("HAPAX_ENV_EMPHASIS_HERO_FILE", str(hero))

        # Patch recommend_emphasis on the module path the script imports
        from agents.studio_compositor import environmental_salience_emphasis as mod

        monkeypatch.setattr(mod, "recommend_emphasis", lambda **_kw: None)

        rc = tick_mod.tick(now_monotonic=100.0, now_epoch=1700_000_000.0)
        assert rc == 0
        assert not hero.exists()
        assert not state.exists()

    def test_recommendation_writes_hero_and_state(
        self, tick_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        from agents.studio_compositor import environmental_salience_emphasis as mod
        from agents.studio_compositor.environmental_salience_emphasis import (
            EmphasisRecommendation,
        )

        state = tmp_path / "state.json"
        hero = tmp_path / "hero.json"
        monkeypatch.setenv("HAPAX_ENV_EMPHASIS_STATE_FILE", str(state))
        monkeypatch.setenv("HAPAX_ENV_EMPHASIS_HERO_FILE", str(hero))

        fake_rec = EmphasisRecommendation(
            camera_role="hardware",
            reason="ir_hand=1.00 + objective_activity=react",
            salience_score=1.0,
        )
        monkeypatch.setattr(mod, "recommend_emphasis", lambda **_kw: fake_rec)

        rc = tick_mod.tick(now_monotonic=200.0, now_epoch=1700_000_000.0)
        assert rc == 0

        hero_data = json.loads(hero.read_text(encoding="utf-8"))
        assert hero_data["hero_role"] == "hardware"
        assert hero_data["salience_score"] == 1.0
        assert hero_data["ts"] == 1700_000_000.0
        assert "react" in hero_data["reason"]

        state_data = json.loads(state.read_text(encoding="utf-8"))
        assert state_data["last_emphasis_at"] == 200.0


class TestSystemdUnits:
    def test_service_unit_present(self):
        path = (
            Path(__file__).resolve().parents[2]
            / "systemd"
            / "units"
            / "hapax-environmental-emphasis.service"
        )
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "environmental_emphasis_tick.py" in content
        assert "Type=oneshot" in content

    def test_timer_unit_present(self):
        path = (
            Path(__file__).resolve().parents[2]
            / "systemd"
            / "units"
            / "hapax-environmental-emphasis.timer"
        )
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "OnUnitActiveSec=30s" in content
        assert "hapax-environmental-emphasis.service" in content
