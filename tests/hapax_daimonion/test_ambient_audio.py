"""Tests for AmbientAudioBackend — Blue Yeti room-level noise floor."""

from __future__ import annotations

import numpy as np

from agents.hapax_daimonion.primitives import Behavior


def test_backend_protocol():
    from agents.hapax_daimonion.backends.ambient_audio import AmbientAudioBackend

    backend = AmbientAudioBackend(source_name="Test Source")
    assert backend.name == "ambient_audio"
    assert "ambient_energy" in backend.provides


def test_rms_computation():
    from agents.hapax_daimonion.backends.ambient_audio import _compute_rms

    silence = np.zeros(480, dtype=np.int16).tobytes()
    assert _compute_rms(silence) == 0.0

    t = np.arange(480) / 16000.0
    loud = (0.5 * 32767 * np.sin(2 * np.pi * 440 * t)).astype(np.int16).tobytes()
    rms = _compute_rms(loud)
    assert 0.3 < rms < 0.4


def test_contribute_defaults():
    from agents.hapax_daimonion.backends.ambient_audio import AmbientAudioBackend

    backend = AmbientAudioBackend(source_name="Test Source")
    behaviors: dict[str, Behavior] = {}
    backend.contribute(behaviors)
    assert behaviors["ambient_energy"].value == 0.0
