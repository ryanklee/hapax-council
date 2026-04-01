"""AudioExecutor — plays samples via PipeWire in a daemon thread.

Implements the Executor protocol. Uses pw-cat for playback instead
of PyAudio (which triggers assertion failures under PipeWire).
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from agents.hapax_daimonion.commands import Command
from agents.hapax_daimonion.sample_bank import SampleBank

log = logging.getLogger(__name__)


class AudioExecutor:
    """Executor playing MC samples via PipeWire.

    handles = {"vocal_throw", "ad_lib"}
    """

    def __init__(self, pa: Any = None, sample_bank: SampleBank | None = None) -> None:
        self._sample_bank = sample_bank

    @property
    def name(self) -> str:
        return "audio"

    @property
    def handles(self) -> frozenset[str]:
        return frozenset({"vocal_throw", "ad_lib"})

    def execute(self, command: Command) -> None:
        """Play a sample matching the command action. Non-blocking."""
        if self._sample_bank is None:
            return
        energy_rms = command.params.get("energy_rms", 0.5)
        entry = self._sample_bank.select(command.action, energy_rms)
        if entry is None:
            log.debug("No sample for action=%s energy=%.2f", command.action, energy_rms)
            return
        thread = threading.Thread(
            target=self._play_pcm,
            args=(entry.pcm_data, entry.sample_rate, entry.channels, command.action),
            daemon=True,
        )
        thread.start()

    def _play_pcm(self, pcm_data: bytes, rate: int, channels: int, action: str) -> None:
        """Play PCM buffer via PipeWire. Runs in a background thread."""
        try:
            from agents.hapax_daimonion.pw_audio_output import play_pcm

            play_pcm(pcm_data, rate=rate, channels=channels)
        except Exception as exc:
            log.warning("AudioExecutor playback failed for %s: %s", action, exc)

    def available(self) -> bool:
        return self._sample_bank is not None and self._sample_bank.sample_count > 0

    def close(self) -> None:
        pass
