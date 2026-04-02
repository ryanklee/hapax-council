import struct
import time
from unittest.mock import patch

from agents.hapax_daimonion.energy_classifier import TtsEnergyTracker


def _make_pcm(amplitude: int = 10000, n_samples: int = 480) -> bytes:
    """Generate a mono int16 PCM frame at given amplitude."""
    return struct.pack(f"<{n_samples}h", *([amplitude] * n_samples))


def _silence(n_samples: int = 480) -> bytes:
    return b"\x00\x00" * n_samples


class TestTtsEnergyTracker:
    def test_inactive_when_no_tts(self):
        t = TtsEnergyTracker()
        assert not t.is_active()

    def test_active_after_record(self):
        t = TtsEnergyTracker()
        t.record(_make_pcm())
        assert t.is_active()

    def test_inactive_after_decay(self):
        t = TtsEnergyTracker(decay_s=0.1)
        t.record(_make_pcm())
        with patch("agents.hapax_daimonion.energy_classifier.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 0.2
            assert not t.is_active()

    def test_expected_energy_tracks_tts(self):
        t = TtsEnergyTracker()
        t.record(_make_pcm(amplitude=10000))
        energy = t.expected_energy()
        assert energy > 5000

    def test_expected_energy_zero_when_inactive(self):
        t = TtsEnergyTracker()
        assert t.expected_energy() == 0.0

    def test_ring_buffer_bounded(self):
        t = TtsEnergyTracker(buffer_size=5)
        for _ in range(20):
            t.record(_make_pcm())
        assert len(t._energy_ring) <= 5
