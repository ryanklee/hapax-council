"""Ambient audio backend — room-level noise floor via Blue Yeti.

Captures from the Blue Yeti USB microphone via pw-cat. Computes
smoothed RMS energy as a room occupancy proxy.

Provides:
  - ambient_energy: float (smoothed RMS, 0.0-1.0)
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time

import numpy as np

from agents.hapax_daimonion.perception import PerceptionTier
from agents.hapax_daimonion.primitives import Behavior

log = logging.getLogger(__name__)

_SAMPLE_RATE = 16000
_FRAME_MS = 30
_FRAME_SAMPLES = _SAMPLE_RATE * _FRAME_MS // 1000
_FRAME_BYTES = _FRAME_SAMPLES * 2
_SMOOTHING_ALPHA = 0.05


def _compute_rms(frame: bytes) -> float:
    samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(samples**2)))


class AmbientAudioBackend:
    def __init__(self, source_name: str = "Yeti Stereo Microphone") -> None:
        self._source_name = source_name
        self._smoothed_energy: float = 0.0
        self._b_energy: Behavior[float] = Behavior(0.0)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def name(self) -> str:
        return "ambient_audio"

    @property
    def provides(self) -> frozenset[str]:
        return frozenset({"ambient_energy"})

    @property
    def tier(self) -> PerceptionTier:
        return PerceptionTier.FAST

    def available(self) -> bool:
        try:
            result = subprocess.run(
                ["pw-cli", "ls", "Node"], capture_output=True, text=True, timeout=3
            )
            return self._source_name in result.stdout
        except Exception:
            return False

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="ambient-audio"
        )
        self._thread.start()
        log.info("AmbientAudioBackend started (source=%s)", self._source_name)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        log.info("AmbientAudioBackend stopped")

    def contribute(self, behaviors: dict[str, Behavior]) -> None:
        now = time.monotonic()
        self._b_energy.update(self._smoothed_energy, now)
        behaviors["ambient_energy"] = self._b_energy

    def _capture_loop(self) -> None:
        retry_delay = 2.0
        while not self._stop_event.is_set():
            proc = None
            try:
                cmd = [
                    "pw-cat",
                    "--record",
                    "--target",
                    self._source_name,
                    "--format",
                    "s16",
                    "--rate",
                    str(_SAMPLE_RATE),
                    "--channels",
                    "1",
                    "-",
                ]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                log.info("Ambient audio capturing via pw-cat (target=%s)", self._source_name)
                retry_delay = 2.0

                while not self._stop_event.is_set():
                    assert proc.stdout is not None
                    data = proc.stdout.read(_FRAME_BYTES)
                    if not data or len(data) < _FRAME_BYTES:
                        break
                    rms = _compute_rms(data)
                    self._smoothed_energy = (
                        _SMOOTHING_ALPHA * rms + (1 - _SMOOTHING_ALPHA) * self._smoothed_energy
                    )
            except Exception:
                if self._stop_event.is_set():
                    break
                log.warning(
                    "Ambient audio pw-cat failed — retrying in %.0fs",
                    retry_delay,
                    exc_info=True,
                )
            finally:
                if proc is not None:
                    try:
                        proc.terminate()
                        proc.wait(timeout=2)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
            if not self._stop_event.is_set():
                self._stop_event.wait(timeout=retry_delay)
                retry_delay = min(retry_delay * 2, 30.0)
