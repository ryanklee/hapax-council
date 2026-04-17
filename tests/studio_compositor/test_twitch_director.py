"""Phase-5 tests for TwitchDirector."""

from __future__ import annotations

import json

import pytest

from agents.studio_compositor import compositional_consumer as cc
from agents.studio_compositor import twitch_director as td
from shared import perceptual_field as pf


@pytest.fixture(autouse=True)
def _redirect(monkeypatch, tmp_path):
    """Isolate every SHM + state file used by twitch + consumer."""
    # perceptual_field source files
    monkeypatch.setattr(pf, "_PERCEPTION_STATE", tmp_path / "perception-state.json")
    monkeypatch.setattr(pf, "_STIMMUNG_STATE", tmp_path / "stimmung-state.json")
    monkeypatch.setattr(pf, "_ALBUM_STATE", tmp_path / "album-state.json")
    monkeypatch.setattr(pf, "_CHAT_STATE", tmp_path / "chat-state.json")
    monkeypatch.setattr(pf, "_CHAT_RECENT", tmp_path / "chat-recent.json")
    monkeypatch.setattr(pf, "_STREAM_LIVE", tmp_path / "stream-live")
    monkeypatch.setattr(pf, "_PRESENCE_STATE", tmp_path / "presence-state.json")
    monkeypatch.setattr(pf, "_WORKING_MODE", tmp_path / "working-mode")
    monkeypatch.setattr(pf, "_CONSENT_CONTRACTS_DIR", tmp_path / "contracts")
    monkeypatch.setattr(pf, "_OBJECTIVES_DIR", tmp_path / "objectives")
    monkeypatch.setattr(pf, "_read_stream_mode", lambda: None)

    # twitch narrative-state path
    monkeypatch.setattr(td, "_NARRATIVE_STATE", tmp_path / "narrative-state.json")

    # consumer SHM paths — keep writes isolated
    monkeypatch.setattr(cc, "_HERO_CAMERA_OVERRIDE", tmp_path / "hero-camera-override.json")
    monkeypatch.setattr(cc, "_OVERLAY_ALPHA_OVERRIDES", tmp_path / "overlay-alpha-overrides.json")
    monkeypatch.setattr(cc, "_RECENT_RECRUITMENT", tmp_path / "recent-recruitment.json")
    monkeypatch.setattr(cc, "_YOUTUBE_DIRECTION", tmp_path / "youtube-direction.json")
    monkeypatch.setattr(cc, "_STREAM_MODE_INTENT", tmp_path / "stream-mode-intent.json")

    return tmp_path


def _write_narrative(tmp_path, stance="nominal"):
    (tmp_path / "narrative-state.json").write_text(
        json.dumps({"stance": stance, "activity": "react", "condition_id": "cond-x"})
    )


def _write_perception(tmp_path, **kwargs):
    (tmp_path / "perception-state.json").write_text(json.dumps(kwargs))


class TestStanceCadenceGate:
    def test_nominal_returns_4s(self, tmp_path):
        _write_narrative(tmp_path, stance="nominal")
        t = td.TwitchDirector()
        assert t._cadence_or_none() == 4.0

    def test_seeking_returns_3s(self, tmp_path):
        _write_narrative(tmp_path, stance="seeking")
        t = td.TwitchDirector()
        assert t._cadence_or_none() == 3.0

    def test_cautious_returns_none(self, tmp_path):
        _write_narrative(tmp_path, stance="cautious")
        t = td.TwitchDirector()
        assert t._cadence_or_none() is None

    def test_critical_returns_none(self, tmp_path):
        _write_narrative(tmp_path, stance="critical")
        t = td.TwitchDirector()
        assert t._cadence_or_none() is None


class TestBeatSyncedAlbumPulse:
    def test_beat_increment_emits_album_foreground(self, tmp_path):
        _write_narrative(tmp_path, stance="nominal")
        _write_perception(
            tmp_path,
            beat_position=1.0,
            transport_state="PLAYING",
        )
        t = td.TwitchDirector()
        emitted = t.tick_once()
        assert "overlay.foreground.album" in emitted

    def test_same_beat_does_not_emit_twice(self, tmp_path):
        _write_narrative(tmp_path, stance="nominal")
        _write_perception(
            tmp_path,
            beat_position=1.0,
            transport_state="PLAYING",
        )
        t = td.TwitchDirector()
        first = t.tick_once()
        assert "overlay.foreground.album" in first
        # Second tick with same beat — min_dwell debounce should prevent
        # immediate re-emission even though beat unchanged.
        second = t.tick_once()
        assert "overlay.foreground.album" not in second


class TestHandZonePulse:
    def test_turntable_hand_zone_emits_album(self, tmp_path):
        _write_narrative(tmp_path, stance="nominal")
        _write_perception(tmp_path, ir_hand_zone="turntable")
        t = td.TwitchDirector()
        emitted = t.tick_once()
        assert "overlay.foreground.album" in emitted


class TestDrummingBiasesAudioReactive:
    def test_drumming_with_high_energy_biases_audio_reactive(self, tmp_path):
        _write_narrative(tmp_path, stance="nominal")
        _write_perception(
            tmp_path,
            desk_activity="drumming",
            desk_energy=0.5,
        )
        t = td.TwitchDirector()
        emitted = t.tick_once()
        assert "fx.family.audio-reactive" in emitted

    def test_drumming_low_energy_does_not_bias(self, tmp_path):
        _write_narrative(tmp_path, stance="nominal")
        _write_perception(
            tmp_path,
            desk_activity="drumming",
            desk_energy=0.1,  # below threshold
        )
        t = td.TwitchDirector()
        emitted = t.tick_once()
        assert "fx.family.audio-reactive" not in emitted


class TestNoEmissionsWhenStanceUnsafe:
    def test_cautious_stance_quiescent(self, tmp_path):
        """Cadence gate should return None; the loop would idle.
        tick_once may still emit, but the loop wouldn't call it — that's
        tested via the cadence gate separately."""
        _write_narrative(tmp_path, stance="cautious")
        t = td.TwitchDirector()
        assert t._cadence_or_none() is None
