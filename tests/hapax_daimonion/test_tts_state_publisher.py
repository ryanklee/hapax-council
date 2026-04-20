"""Tests for TtsStatePublisher — audio-normalization PR-1.

Spec: docs/research/2026-04-21-audio-normalization-ducking-integration.md.
Plan: docs/superpowers/plans/2026-04-21-audio-normalization-ducking-plan.md PR-1.

Verifies:
  - publish_tts_state writes tts_active=true to voice-state.json
  - publish_tts_state preserves any existing operator_speech_active key
    (atomic read-modify-write, mirrors vad_ducking lines 45-51)
  - publish_vad_state preserves any existing tts_active key (symmetric
    invariant — both publishers must merge, not overwrite)
  - Corrupt voice-state.json is treated as empty (degraded posture)
  - Missing voice-state.json bootstraps cleanly with just the new key
"""

from __future__ import annotations

import json
from pathlib import Path

from agents.studio_compositor import vad_ducking


def test_publish_tts_state_writes_tts_active_true(tmp_path: Path, monkeypatch) -> None:
    state_file = tmp_path / "voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)

    vad_ducking.publish_tts_state(True)

    payload = json.loads(state_file.read_text())
    assert payload == {"tts_active": True}


def test_publish_tts_state_writes_tts_active_false(tmp_path: Path, monkeypatch) -> None:
    state_file = tmp_path / "voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)

    vad_ducking.publish_tts_state(False)

    payload = json.loads(state_file.read_text())
    assert payload == {"tts_active": False}


def test_publish_tts_state_preserves_operator_speech_active(tmp_path: Path, monkeypatch) -> None:
    """RMW invariant: publishing tts_active must not clobber an existing
    operator_speech_active key written by VadStatePublisher.
    """
    state_file = tmp_path / "voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)

    # VadStatePublisher fired first
    vad_ducking.publish_vad_state(True)
    # Then TTS started
    vad_ducking.publish_tts_state(True)

    payload = json.loads(state_file.read_text())
    assert payload == {"operator_speech_active": True, "tts_active": True}


def test_publish_vad_state_preserves_tts_active(tmp_path: Path, monkeypatch) -> None:
    """Symmetric RMW invariant: VAD publisher must not clobber tts_active."""
    state_file = tmp_path / "voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)

    vad_ducking.publish_tts_state(True)
    vad_ducking.publish_vad_state(False)

    payload = json.loads(state_file.read_text())
    assert payload == {"tts_active": True, "operator_speech_active": False}


def test_publish_tts_state_handles_missing_file(tmp_path: Path, monkeypatch) -> None:
    """Bootstrap path: file missing → write a single-key payload."""
    state_file = tmp_path / "subdir" / "voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)

    vad_ducking.publish_tts_state(True)

    assert state_file.exists()
    payload = json.loads(state_file.read_text())
    assert payload == {"tts_active": True}


def test_publish_tts_state_handles_corrupt_file(tmp_path: Path, monkeypatch) -> None:
    """Degraded posture: corrupt JSON treated as empty; new key wins."""
    state_file = tmp_path / "voice-state.json"
    state_file.write_text("{not valid json")
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)

    vad_ducking.publish_tts_state(True)

    payload = json.loads(state_file.read_text())
    assert payload == {"tts_active": True}


def test_publish_tts_state_handles_non_dict_file(tmp_path: Path, monkeypatch) -> None:
    """A non-dict payload (e.g. a JSON list) is treated as empty."""
    state_file = tmp_path / "voice-state.json"
    state_file.write_text(json.dumps([1, 2, 3]))
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)

    vad_ducking.publish_tts_state(True)

    payload = json.loads(state_file.read_text())
    assert payload == {"tts_active": True}


def test_consecutive_state_changes_track_correctly(tmp_path: Path, monkeypatch) -> None:
    """Multiple flips of both keys preserve the latest value of each."""
    state_file = tmp_path / "voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)

    vad_ducking.publish_tts_state(True)
    vad_ducking.publish_vad_state(True)
    vad_ducking.publish_tts_state(False)
    vad_ducking.publish_vad_state(False)

    payload = json.loads(state_file.read_text())
    assert payload == {"tts_active": False, "operator_speech_active": False}


def test_publish_tts_state_atomic_via_tmp_rename(tmp_path: Path, monkeypatch) -> None:
    """Pin: writes go through the .tmp + rename pattern, never directly."""
    state_file = tmp_path / "voice-state.json"
    monkeypatch.setattr(vad_ducking, "VOICE_STATE_FILE", state_file)

    vad_ducking.publish_tts_state(True)

    # Final file exists; tmp file does not (rename consumed it).
    assert state_file.exists()
    assert not state_file.with_suffix(".tmp").exists()
