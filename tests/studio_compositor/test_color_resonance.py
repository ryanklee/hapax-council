"""Epic 2 Phase F2 — color resonance smoothing + publish/read cycle."""

from __future__ import annotations

import json

import pytest

from agents.studio_compositor import color_resonance


class TestResonanceSmoothing:
    def test_neutral_when_no_cover(self, tmp_path, monkeypatch):
        monkeypatch.setattr(color_resonance, "_ALBUM_COVER", tmp_path / "missing.png")
        r = color_resonance.ColorResonance()
        state = r.tick()
        assert state["warmth"] == pytest.approx(0.0, abs=1e-6)
        assert 0.0 <= state["mean_v"] <= 1.0

    def test_warm_cover_drives_positive_warmth(self, tmp_path, monkeypatch):
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("PIL not installed")
        cover = tmp_path / "warm.png"
        Image.new("RGB", (32, 32), (220, 80, 40)).save(cover)
        monkeypatch.setattr(color_resonance, "_ALBUM_COVER", cover)
        # Advance simulated time so the low-pass actually converges.
        import time

        clock = [1_000_000.0]

        def _fake_time() -> float:
            clock[0] += 1.0
            return clock[0]

        monkeypatch.setattr(time, "time", _fake_time)
        r = color_resonance.ColorResonance()
        for _ in range(30):
            state = r.tick()
        assert state["warmth"] > 0.3

    def test_cool_cover_drives_negative_warmth(self, tmp_path, monkeypatch):
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("PIL not installed")
        cover = tmp_path / "cool.png"
        Image.new("RGB", (32, 32), (40, 120, 220)).save(cover)
        monkeypatch.setattr(color_resonance, "_ALBUM_COVER", cover)
        import time

        clock = [1_000_000.0]

        def _fake_time() -> float:
            clock[0] += 1.0
            return clock[0]

        monkeypatch.setattr(time, "time", _fake_time)
        r = color_resonance.ColorResonance()
        for _ in range(30):
            state = r.tick()
        assert state["warmth"] < -0.3


class TestPublishRead:
    def test_publish_read_round_trip(self, tmp_path, monkeypatch):
        target = tmp_path / "color-resonance.json"
        monkeypatch.setattr(color_resonance, "_RESONANCE_OUT", target)
        color_resonance.publish(
            {"warmth": 0.42, "mean_h": 35.0, "mean_s": 0.8, "mean_v": 0.65, "updated_at": 0.0}
        )
        assert target.exists()
        got = color_resonance.read_current()
        assert got["warmth"] == pytest.approx(0.42)
        assert got["mean_s"] == pytest.approx(0.8)

    def test_read_missing_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(color_resonance, "_RESONANCE_OUT", tmp_path / "absent.json")
        assert color_resonance.read_current() == {}

    def test_publish_is_atomic(self, tmp_path, monkeypatch):
        target = tmp_path / "color.json"
        monkeypatch.setattr(color_resonance, "_RESONANCE_OUT", target)
        # Write then read back — ensure tmp was renamed, not left behind.
        color_resonance.publish({"warmth": 0.1})
        assert target.exists()
        assert not (tmp_path / "color.json.tmp").exists()
        assert json.loads(target.read_text())["warmth"] == 0.1


class TestStreamModeBorder:
    def test_accent_for_known_modes(self, monkeypatch):
        from agents.studio_compositor.legibility_sources import _stream_mode_accent

        for mode in ("private", "public", "public_research", "fortress", "off"):
            monkeypatch.setattr("shared.stream_mode.get_stream_mode", lambda m=mode: m)
            accent = _stream_mode_accent()
            assert accent is not None, f"mode {mode!r} returned None"
            assert len(accent) == 4
            assert 0.0 <= accent[3] <= 1.0

    def test_accent_for_unknown_returns_none(self, monkeypatch):
        from agents.studio_compositor.legibility_sources import _stream_mode_accent

        monkeypatch.setattr("shared.stream_mode.get_stream_mode", lambda: "unknown-mode")
        assert _stream_mode_accent() is None
