"""Tests for AudioExecutor — pw-cat playback, daemon thread, Executor protocol."""

from __future__ import annotations

import struct
import unittest
import wave
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from agents.hapax_daimonion.audio_executor import AudioExecutor
from agents.hapax_daimonion.commands import Command
from agents.hapax_daimonion.executor import Executor
from agents.hapax_daimonion.sample_bank import SampleBank


def _write_wav(path: Path, rate: int = 44100, channels: int = 1, n_frames: int = 100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(struct.pack(f"<{n_frames}h", *([1000] * n_frames)))


class TestAudioExecutor(unittest.TestCase):
    def _make_executor(self, tmpdir: str):
        base = Path(tmpdir)
        _write_wav(base / "vocal_throw" / "high_001.wav")
        _write_wav(base / "ad_lib" / "medium_001.wav")

        bank = SampleBank(base)
        bank.load()

        executor = AudioExecutor(sample_bank=bank)
        return executor

    def test_satisfies_executor_protocol(self):
        with TemporaryDirectory() as tmpdir:
            executor = self._make_executor(tmpdir)
            self.assertIsInstance(executor, Executor)

    @patch("agents.hapax_daimonion.audio_executor.threading.Thread")
    def test_execute_spawns_daemon_thread(self, mock_thread_cls):
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        with TemporaryDirectory() as tmpdir:
            executor = self._make_executor(tmpdir)
            cmd = Command(action="vocal_throw", params={"energy_rms": 0.8})
            executor.execute(cmd)

            mock_thread_cls.assert_called_once()
            _, kwargs = mock_thread_cls.call_args
            self.assertTrue(kwargs["daemon"])
            mock_thread.start.assert_called_once()

    @patch("agents.hapax_daimonion.pw_audio_output.play_pcm")
    def test_play_pcm_calls_pw_cat(self, mock_play):
        with TemporaryDirectory() as tmpdir:
            executor = self._make_executor(tmpdir)
            executor._play_pcm(b"\x00\x00", 44100, 1, "test")
            mock_play.assert_called_once_with(b"\x00\x00", rate=44100, channels=1)

    def test_available_with_samples(self):
        with TemporaryDirectory() as tmpdir:
            executor = self._make_executor(tmpdir)
            self.assertTrue(executor.available())

    def test_unavailable_without_samples(self):
        executor = AudioExecutor(sample_bank=None)
        self.assertFalse(executor.available())

    def test_handles(self):
        with TemporaryDirectory() as tmpdir:
            executor = self._make_executor(tmpdir)
            self.assertEqual(executor.handles, frozenset({"vocal_throw", "ad_lib"}))

    def test_execute_no_matching_sample(self):
        """execute with unknown action does not spawn thread."""
        with TemporaryDirectory() as tmpdir:
            executor = self._make_executor(tmpdir)
            with patch("agents.hapax_daimonion.audio_executor.threading.Thread") as mock_thread_cls:
                executor.execute(Command(action="nonexistent"))
                mock_thread_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
