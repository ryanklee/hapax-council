"""Tests for CPAL runner."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.hapax_daimonion.cpal.runner import CpalRunner


class TestCpalRunnerLifecycle:
    def _make_runner(self):
        buffer = MagicMock()
        buffer.speech_active = False
        buffer.speech_duration_s = 0.0
        buffer.is_speaking = False
        buffer.get_utterance.return_value = None
        buffer.speech_frames_snapshot = []

        stt = MagicMock()
        stt.transcribe = AsyncMock(return_value="")

        router = MagicMock()
        router.route.return_value = MagicMock(tier="CAPABLE")

        return CpalRunner(
            buffer=buffer,
            stt=stt,
            salience_router=router,
        )

    def test_initial_state(self):
        runner = self._make_runner()
        assert not runner.is_running
        assert runner.tick_count == 0

    @pytest.mark.asyncio
    async def test_run_and_stop(self):
        runner = self._make_runner()

        async def stop_after_ticks():
            while runner.tick_count < 3:
                await asyncio.sleep(0.05)
            runner.stop()

        await asyncio.gather(runner.run(), stop_after_ticks())
        assert not runner.is_running
        assert runner.tick_count >= 3

    @pytest.mark.asyncio
    async def test_gain_rises_during_speech(self):
        runner = self._make_runner()
        # Simulate operator speaking
        runner._buffer.speech_active = True

        async def stop_after():
            while runner.tick_count < 5:
                await asyncio.sleep(0.05)
            runner.stop()

        await asyncio.gather(runner.run(), stop_after())
        assert runner.evaluator.gain_controller.gain > 0.0

    @pytest.mark.asyncio
    async def test_utterance_detected(self):
        runner = self._make_runner()
        runner._buffer.get_utterance.return_value = b"\x00\x01" * 500

        async def stop_after():
            while runner.tick_count < 2:
                await asyncio.sleep(0.05)
            runner.stop()

        await asyncio.gather(runner.run(), stop_after())
        # Utterance was consumed (get_utterance called)
        runner._buffer.get_utterance.assert_called()

    @pytest.mark.asyncio
    async def test_process_impingement(self):
        runner = self._make_runner()
        imp = MagicMock()
        imp.source = "stimmung"
        imp.strength = 0.9
        imp.content = {"metric": "stimmung_critical", "narrative": "System critical"}
        imp.interrupt_token = None

        await runner.process_impingement(imp)
        assert runner.evaluator.gain_controller.gain > 0.0

    def test_presynthesize_signals(self):
        runner = self._make_runner()
        tts = MagicMock()
        tts.synthesize.return_value = b"\x00\x01" * 100
        runner._tts_manager = tts
        runner.presynthesize_signals()
        assert runner.signal_cache.is_ready


class TestCpalRunnerTelemetry:
    """Queue #225: CPAL loop Prometheus telemetry."""

    def _make_runner(self):
        buffer = MagicMock()
        buffer.speech_active = False
        buffer.speech_duration_s = 0.0
        buffer.is_speaking = False
        buffer.get_utterance.return_value = None
        buffer.speech_frames_snapshot = []

        stt = MagicMock()
        stt.transcribe = AsyncMock(return_value="")

        router = MagicMock()
        router.route.return_value = MagicMock(tier="CAPABLE")

        return CpalRunner(buffer=buffer, stt=stt, salience_router=router)

    def test_classify_tick_idle(self):
        runner = self._make_runner()
        assert runner._classify_tick() == "idle"

    def test_classify_tick_utterance(self):
        runner = self._make_runner()
        runner._processing_utterance = True
        assert runner._classify_tick() == "utterance"

    def test_classify_tick_producing(self):
        runner = self._make_runner()
        # ProductionStream.is_producing is a read-only property; swap the
        # production stream for a mock with a writable attribute.
        prod = MagicMock()
        prod.is_producing = True
        runner._production = prod
        assert runner._classify_tick() == "producing"

    def test_classify_tick_impingement_dominates(self):
        runner = self._make_runner()
        # Impingement takes priority over utterance/producing; it's the most
        # information-dense signal the loop handles this tick.
        prod = MagicMock()
        prod.is_producing = True
        runner._production = prod
        runner._processing_utterance = True
        runner._impingement_since_last_tick = True
        assert runner._classify_tick() == "impingement"

    @pytest.mark.asyncio
    async def test_process_impingement_marks_tick(self):
        runner = self._make_runner()
        imp = MagicMock()
        imp.source = "stimmung"
        imp.strength = 0.9
        imp.content = {"metric": "stimmung_critical", "narrative": "System critical"}
        imp.interrupt_token = None

        assert runner._impingement_since_last_tick is False
        await runner.process_impingement(imp)
        assert runner._impingement_since_last_tick is True

    @pytest.mark.asyncio
    async def test_impingement_flag_resets_after_tick(self):
        runner = self._make_runner()
        runner._impingement_since_last_tick = True

        async def stop_after():
            while runner.tick_count < 1:
                await asyncio.sleep(0.01)
            runner.stop()

        await asyncio.gather(runner.run(), stop_after())
        # First full tick reclassifies as impingement, then clears the flag.
        assert runner._impingement_since_last_tick is False
