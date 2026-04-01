"""Tests for TTSExecutor — pw-cat playback, pre-synthesized PCM."""

from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock, patch

from agents.hapax_daimonion.commands import Command, Schedule
from agents.hapax_daimonion.executor import Executor, ScheduleQueue
from agents.hapax_daimonion.tts_executor import TTSExecutor


class TestTTSExecutor(unittest.TestCase):
    def _make_executor(self):
        return TTSExecutor()

    def test_satisfies_executor_protocol(self):
        ex = self._make_executor()
        self.assertIsInstance(ex, Executor)

    def test_handles(self):
        ex = self._make_executor()
        self.assertEqual(ex.handles, frozenset({"tts_announce"}))

    @patch("agents.hapax_daimonion.pw_audio_output.play_pcm")
    @patch("agents.hapax_daimonion.tts_executor.write_acoustic_impulse", create=True)
    def test_play_pcm_calls_pw_cat(self, _mock_impulse, mock_play):
        ex = self._make_executor()
        pcm = b"\x00\x01" * 100
        ex._play_pcm(pcm, 24000, 1)
        mock_play.assert_called_once_with(pcm, rate=24000, channels=1)

    @patch("agents.hapax_daimonion.tts_executor.threading.Thread")
    def test_execute_spawns_daemon_thread(self, mock_thread_cls):
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread
        ex = self._make_executor()

        pcm = b"\x00\x01" * 100
        cmd = Command(action="tts_announce", params={"pcm_data": pcm, "sample_rate": 24000})
        ex.execute(cmd)

        mock_thread_cls.assert_called_once()
        _, kwargs = mock_thread_cls.call_args
        self.assertTrue(kwargs["daemon"])
        mock_thread.start.assert_called_once()

    def test_missing_pcm_data_handled(self):
        ex = self._make_executor()
        cmd = Command(action="tts_announce", params={})
        ex.execute(cmd)

    def test_non_bytes_pcm_handled(self):
        ex = self._make_executor()
        cmd = Command(action="tts_announce", params={"pcm_data": "not bytes"})
        ex.execute(cmd)

    def test_available(self):
        ex = self._make_executor()
        self.assertTrue(ex.available())

    @patch("agents.hapax_daimonion.pw_audio_output.play_pcm")
    def test_integration_synthesize_enqueue_drain_play(self, mock_play):
        """Simulates: synthesize → Command.params → ScheduleQueue → drain → TTSExecutor."""
        ex = self._make_executor()

        pcm = b"\x00\x01" * 500
        cmd = Command(
            action="tts_announce",
            params={"pcm_data": pcm, "sample_rate": 24000},
            trigger_source="tts_governance",
        )

        now = time.monotonic()
        schedule = Schedule(
            command=cmd,
            domain="beat",
            target_time=4.0,
            wall_time=now + 0.001,
            tolerance_ms=100.0,
        )

        queue = ScheduleQueue()
        queue.enqueue(schedule)

        ready = queue.drain(now + 0.002)
        self.assertEqual(len(ready), 1)

        ex._play_pcm(ready[0].command.params["pcm_data"], 24000, 1)
        mock_play.assert_called_once_with(pcm, rate=24000, channels=1)


if __name__ == "__main__":
    unittest.main()
