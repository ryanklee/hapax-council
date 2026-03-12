"""Stream health perception backend — OBS streaming statistics.

SLOW-cadence backend polling OBS stats via obs-websocket. Provides stream
bitrate, dropped frames percentage, and encoding lag as Behaviors.

Stub backend: reserves behavior names and proves the protocol.
Actual implementation requires obs-websocket connection.
"""

from __future__ import annotations

import logging

from agents.hapax_voice.perception import PerceptionTier
from agents.hapax_voice.primitives import Behavior

log = logging.getLogger(__name__)


class StreamHealthBackend:
    """PerceptionBackend for OBS stream health statistics.

    Provides:
      - stream_bitrate: float (kbps)
      - stream_dropped_frames: float (percentage 0-100)
      - stream_encoding_lag: float (ms)
    """

    @property
    def name(self) -> str:
        return "stream_health"

    @property
    def provides(self) -> frozenset[str]:
        return frozenset({"stream_bitrate", "stream_dropped_frames", "stream_encoding_lag"})

    @property
    def tier(self) -> PerceptionTier:
        return PerceptionTier.SLOW

    def available(self) -> bool:
        return False

    def contribute(self, behaviors: dict[str, Behavior]) -> None:
        pass

    def start(self) -> None:
        log.info("StreamHealth backend started (stub)")

    def stop(self) -> None:
        log.info("StreamHealth backend stopped (stub)")
