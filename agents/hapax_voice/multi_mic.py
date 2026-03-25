"""Multi-microphone noise reference subtraction.

Uses C920 webcam mics as ambient noise reference channels. The Yeti
captures operator voice + room noise. The C920s capture mostly room
noise (they're farther from the operator). Subtracting the C920 signal
from the Yeti reduces echo, ambient, and speaker bleed-through.

Optionally uses a contact microphone (e.g. Cortado MkII) for
structure-borne noise reference — desk vibrations, keyboard impacts,
mechanical rumble. Structure-borne subtraction runs first (alpha=1.0,
conservative) then airborne subtraction (alpha=1.5, aggressive).

This is spectral subtraction, not beamforming — no array geometry
needed. Works with arbitrary mic placement.

Usage:
    ref = NoiseReference(
        room_sources=["HD Pro Webcam C920"],
        structure_sources=["Contact Microphone"],
    )
    ref.start()
    # ... in audio loop:
    cleaned = ref.subtract(yeti_frame)
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque

import numpy as np

log = logging.getLogger(__name__)

# Spectral subtraction parameters
_FFT_SIZE = 512
_HOP_SIZE = 256
_SMOOTHING = 0.7  # noise estimate smoothing (0=no smoothing, 1=never update)

# Airborne subtraction (room mics — aggressive, removes ambient + echo)
_AIRBORNE_ALPHA = 1.5  # oversubtraction factor
_AIRBORNE_BETA = 0.01  # spectral floor

# Structure-borne subtraction (contact mic — conservative, removes desk/keyboard rumble)
_STRUCTURE_ALPHA = 1.0  # less aggressive (contact mic signal is already clean)
_STRUCTURE_BETA = 0.02  # slightly higher floor (preserve transient detail)


class NoiseReference:
    """Captures room noise from reference mics and subtracts from primary mic.

    The reference signal estimates what the room sounds like WITHOUT the
    operator's voice. Spectral subtraction removes this estimate from the
    Yeti signal, leaving mostly the operator's voice.
    """

    def __init__(
        self,
        room_sources: list[str] | None = None,
        structure_sources: list[str] | None = None,
        sample_rate: int = 16000,
    ) -> None:
        self._room_sources = room_sources or []
        self._structure_sources = structure_sources or []
        self._sample_rate = sample_rate
        self._running = False
        self._threads: list[threading.Thread] = []

        # Airborne noise estimate (room mics)
        self._noise_estimate: np.ndarray | None = None
        self._lock = threading.Lock()

        # Structure-borne noise estimate (contact mic)
        self._structure_noise_estimate: np.ndarray | None = None
        self._structure_lock = threading.Lock()

        # Ring buffer of recent reference frames for averaging
        self._ref_frames: deque[np.ndarray] = deque(maxlen=20)  # ~600ms at 30ms/frame

    def start(self) -> None:
        """Start capturing from reference microphones."""
        if not self._room_sources and not self._structure_sources:
            log.info("No reference sources configured — noise subtraction disabled")
            return

        self._running = True
        for source in self._room_sources:
            t = threading.Thread(
                target=self._capture_loop,
                args=(source,),
                kwargs={"is_structure": False},
                daemon=True,
                name=f"noise-ref-{source[:20]}",
            )
            t.start()
            self._threads.append(t)
        for source in self._structure_sources:
            t = threading.Thread(
                target=self._capture_loop,
                args=(source,),
                kwargs={"is_structure": True},
                daemon=True,
                name=f"struct-ref-{source[:20]}",
            )
            t.start()
            self._threads.append(t)
        log.info(
            "Noise reference started with %d room + %d structure source(s)",
            len(self._room_sources),
            len(self._structure_sources),
        )

    def stop(self) -> None:
        self._running = False
        for t in self._threads:
            t.join(timeout=2)
        self._threads.clear()

    @staticmethod
    def _apply_subtraction(
        mag: np.ndarray,
        noise_mag: np.ndarray | None,
        alpha: float,
        beta: float,
    ) -> np.ndarray:
        """Spectral subtraction: mag - alpha*noise, floored at beta*mag."""
        if noise_mag is not None and len(noise_mag) == len(mag):
            return np.maximum(mag - alpha * noise_mag, beta * mag)
        return mag

    def subtract(self, frame: bytes) -> bytes:
        """Apply spectral subtraction to a primary mic frame.

        Structure-borne subtraction runs first (conservative), then airborne
        subtraction (aggressive). This order prevents structure rumble from
        being misattributed to airborne noise.

        Args:
            frame: Raw PCM int16 mono audio frame from the Yeti.

        Returns:
            Cleaned PCM int16 mono audio frame.
        """
        if self._noise_estimate is None and self._structure_noise_estimate is None:
            return frame  # no reference data yet — pass through

        # Convert to float
        samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
        if len(samples) < _FFT_SIZE:
            return frame

        # STFT of input
        window = np.hanning(_FFT_SIZE)
        spec = np.fft.rfft(samples[:_FFT_SIZE] * window)
        mag = np.abs(spec)
        phase = np.angle(spec)

        # 1. Structure-borne subtraction (contact mic — conservative)
        with self._structure_lock:
            structure_mag = self._structure_noise_estimate
        mag = self._apply_subtraction(mag, structure_mag, _STRUCTURE_ALPHA, _STRUCTURE_BETA)

        # 2. Airborne subtraction (room mics — aggressive)
        with self._lock:
            noise_mag = self._noise_estimate
        mag = self._apply_subtraction(mag, noise_mag, _AIRBORNE_ALPHA, _AIRBORNE_BETA)

        # Reconstruct
        clean_spec = mag * np.exp(1j * phase)
        clean_samples = np.fft.irfft(clean_spec)[: len(samples)]

        # Convert back to int16
        clean_int16 = np.clip(clean_samples, -32768, 32767).astype(np.int16)
        return clean_int16.tobytes()

    def _capture_loop(self, source: str, *, is_structure: bool = False) -> None:
        """Continuously capture from a reference mic and update noise estimate.

        Args:
            source: Device name substring to match.
            is_structure: If True, updates structure-borne estimate instead of airborne.
        """
        lock = self._structure_lock if is_structure else self._lock
        kind = "structure" if is_structure else "room"

        try:
            import pyaudio

            pa = pyaudio.PyAudio()

            # Structure sources (PipeWire virtual) need pactl default-source;
            # room sources (hardware ALSA) use PyAudio device name matching.
            device_idx = None
            if is_structure:
                import subprocess

                try:
                    subprocess.run(
                        ["pactl", "set-default-source", "contact_mic"],
                        capture_output=True,
                        timeout=5,
                    )
                except Exception:
                    log.warning("Failed to set contact_mic as default source for %s ref", kind)
                # Use default device (now routed to contact_mic)
                device_idx = None  # None = default
            else:
                for i in range(pa.get_device_count()):
                    info = pa.get_device_info_by_index(i)
                    if source in str(info.get("name", "")):
                        device_idx = i
                        break
                if device_idx is None:
                    log.warning("Noise reference source not found (%s): %s", kind, source)
                    pa.terminate()
                    return

            open_kwargs: dict = {
                "format": pyaudio.paInt16,
                "channels": 1,
                "rate": self._sample_rate,
                "input": True,
                "frames_per_buffer": _FFT_SIZE,
            }
            if device_idx is not None:
                open_kwargs["input_device_index"] = device_idx

            stream = pa.open(**open_kwargs)

            log.info(
                "Noise reference capturing from %s source: %s (device %s)",
                kind,
                source,
                device_idx if device_idx is not None else "default",
            )

            while self._running:
                try:
                    data = stream.read(_FFT_SIZE, exception_on_overflow=False)
                    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)

                    # Compute magnitude spectrum
                    window = np.hanning(_FFT_SIZE)
                    spec = np.fft.rfft(samples * window)
                    mag = np.abs(spec)

                    # Update noise estimate with exponential smoothing
                    with lock:
                        if is_structure:
                            if self._structure_noise_estimate is None:
                                self._structure_noise_estimate = mag
                            else:
                                self._structure_noise_estimate = (
                                    _SMOOTHING * self._structure_noise_estimate
                                    + (1 - _SMOOTHING) * mag
                                )
                        else:
                            if self._noise_estimate is None:
                                self._noise_estimate = mag
                            else:
                                self._noise_estimate = (
                                    _SMOOTHING * self._noise_estimate + (1 - _SMOOTHING) * mag
                                )

                except Exception:
                    time.sleep(0.1)

            stream.stop_stream()
            stream.close()
            pa.terminate()

        except Exception:
            log.debug("Noise reference capture failed for %s (%s)", source, kind, exc_info=True)
