"""Tests for TtsDuckController — audio normalization PR-3.

Spec: docs/superpowers/plans/2026-04-21-audio-normalization-ducking-plan.md PR-3.

Verifies:
  - tts_active=true → set_gain(duck_gain) called once
  - tts_active=false → set_gain(default_gain) called once
  - State unchanged across polls → no spam (transition-only emission)
  - Missing voice-state.json → fail-open to default_gain
  - Stale voice-state.json (mtime > 2s old) → fail-open to default_gain
  - Corrupt voice-state.json → fail-open to default_gain
  - set_gain exception does not propagate / break the loop
  - Default thresholds match plan: poll 30ms, duck 0.316, default 1.0
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from agents.studio_compositor import vad_ducking
from agents.studio_compositor.vad_ducking import (
    DEFAULT_STALE_THRESHOLD_S,
    TtsDuckController,
)


class _MockGain:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def set_gain(self, gain: float) -> None:
        self.calls.append(gain)


def _write_state(path: Path, *, tts_active: bool, age_s: float = 0.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tts_active": tts_active}))
    if age_s > 0:
        past = time.time() - age_s
        os.utime(path, (past, past))


# ── Transition emission ────────────────────────────────────────────────


def test_tts_active_true_emits_duck_gain(tmp_path: Path, monkeypatch) -> None:
    state_file = tmp_path / "voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)
    _write_state(state_file, tts_active=True)

    mock = _MockGain()
    controller = TtsDuckController(mock)
    controller.tick_once()
    assert mock.calls == [0.316]


def test_tts_active_false_emits_default_gain(tmp_path: Path, monkeypatch) -> None:
    state_file = tmp_path / "voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)
    _write_state(state_file, tts_active=False)

    mock = _MockGain()
    controller = TtsDuckController(mock)
    controller.tick_once()
    # First tick from None → False does emit default_gain (fail-open posture).
    assert mock.calls == [1.0]


def test_state_unchanged_no_spam(tmp_path: Path, monkeypatch) -> None:
    state_file = tmp_path / "voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)
    _write_state(state_file, tts_active=True)

    mock = _MockGain()
    controller = TtsDuckController(mock)
    controller.tick_once()
    controller.tick_once()
    controller.tick_once()
    # Only one call — transition-only emission
    assert mock.calls == [0.316]


def test_transitions_emit_each_change(tmp_path: Path, monkeypatch) -> None:
    state_file = tmp_path / "voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)

    mock = _MockGain()
    controller = TtsDuckController(mock)

    _write_state(state_file, tts_active=True)
    controller.tick_once()
    _write_state(state_file, tts_active=False)
    controller.tick_once()
    _write_state(state_file, tts_active=True)
    controller.tick_once()

    assert mock.calls == [0.316, 1.0, 0.316]


# ── Fail-open ──────────────────────────────────────────────────────────


def test_missing_file_fail_open_to_default(tmp_path: Path, monkeypatch) -> None:
    state_file = tmp_path / "missing-voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)

    mock = _MockGain()
    controller = TtsDuckController(mock)
    controller.tick_once()
    assert mock.calls == [1.0]


def test_stale_file_fail_open_to_default(tmp_path: Path, monkeypatch) -> None:
    state_file = tmp_path / "voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)
    # Write tts_active=True but with an old mtime — stale > 2s threshold
    _write_state(state_file, tts_active=True, age_s=10.0)

    mock = _MockGain()
    controller = TtsDuckController(mock)
    controller.tick_once()
    # Fail-open: ignore the (stale) duck signal, force default gain
    assert mock.calls == [1.0]


def test_corrupt_file_fail_open_to_default(tmp_path: Path, monkeypatch) -> None:
    state_file = tmp_path / "voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)
    state_file.write_text("{not valid json")

    mock = _MockGain()
    controller = TtsDuckController(mock)
    controller.tick_once()
    assert mock.calls == [1.0]


def test_recovery_from_stale_when_fresh_signal_arrives(tmp_path: Path, monkeypatch) -> None:
    """After fail-open default, a fresh tts_active=true must emit duck_gain."""
    state_file = tmp_path / "voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)
    _write_state(state_file, tts_active=True, age_s=10.0)  # stale

    mock = _MockGain()
    controller = TtsDuckController(mock)
    controller.tick_once()  # fail-open default
    assert mock.calls == [1.0]

    _write_state(state_file, tts_active=True)  # fresh
    controller.tick_once()
    assert mock.calls == [1.0, 0.316]


# ── Defensive ──────────────────────────────────────────────────────────


class _BoomGain:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def set_gain(self, gain: float) -> None:
        self.calls.append(gain)
        raise RuntimeError("gain socket broken")


def test_set_gain_exception_does_not_break_loop(tmp_path: Path, monkeypatch) -> None:
    state_file = tmp_path / "voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)
    _write_state(state_file, tts_active=True)

    boom = _BoomGain()
    controller = TtsDuckController(boom)
    # Must not raise
    controller.tick_once()
    assert boom.calls == [0.316]


# ── Defaults ───────────────────────────────────────────────────────────


def test_default_thresholds_match_plan() -> None:
    """Plan §lines 79-80: 30ms poll. Strategy doc §4.2: -10 dB ≈ 0.316."""
    mock = _MockGain()
    controller = TtsDuckController(mock)
    assert controller._poll_interval == 0.03
    assert controller._duck_gain == 0.316
    assert controller._default_gain == 1.0
    assert DEFAULT_STALE_THRESHOLD_S == 2.0
