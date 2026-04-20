"""Pipecat frame processor that publishes TTS-active state transitions.

Audio normalization PR-1 (plan
``docs/superpowers/plans/2026-04-21-audio-normalization-ducking-plan.md``).
Mirror of ``agents.hapax_daimonion.vad_state_publisher.VadStatePublisher``;
subscribes to pipecat ``TTSStartedFrame`` / ``TTSStoppedFrame`` and
publishes the boolean ``tts_active`` key into
``/dev/shm/hapax-compositor/voice-state.json`` via
``agents.studio_compositor.vad_ducking.publish_tts_state``.

The publish helper is read-modify-write so the existing
``operator_speech_active`` key (set by VadStatePublisher) is preserved
when only the TTS key flips.

Privacy posture matches the VAD publisher:
- TTS state is ephemeral (/dev/shm only, not persisted).
- No TTS payload (audio bytes, text) leaves this processor.
- The boolean is the only signal the compositor-side ducker reads.
"""

from __future__ import annotations

import logging

from pipecat.frames.frames import (
    Frame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from agents.studio_compositor.vad_ducking import publish_tts_state

log = logging.getLogger(__name__)


class TtsStatePublisher(FrameProcessor):
    """Publish TTS-active transitions to the compositor-side ducker.

    Pipecat frame flow: ... → LLM → TTS → TtsStatePublisher → output.
    The processor is placed AFTER the TTS stage so it observes the
    real start/stop of TTS playback (vs the upstream LLM-emitted
    speech intent).

    Pure side-effect node: frames pass through unmodified via
    ``push_frame`` after the boolean publish.
    """

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        # Upstream FrameProcessor.process_frame does bookkeeping (metrics,
        # interrupt handling). Call it when available; skip gracefully
        # under the stubbed test conftest that swaps pipecat out.
        if hasattr(super(), "process_frame"):
            await super().process_frame(frame, direction)

        if isinstance(frame, TTSStartedFrame):
            try:
                publish_tts_state(True)
            except Exception as exc:  # noqa: BLE001 — never block pipeline
                log.warning("tts_state publish (start) failed: %s", exc)
        elif isinstance(frame, TTSStoppedFrame):
            try:
                publish_tts_state(False)
            except Exception as exc:  # noqa: BLE001 — never block pipeline
                log.warning("tts_state publish (stop) failed: %s", exc)

        await self.push_frame(frame, direction)


__all__ = ["TtsStatePublisher"]
