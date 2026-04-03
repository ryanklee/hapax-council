"""Bluetooth presence backend — watch proximity via BLE scan.

Periodically scans for the Pixel 10 phone's BLE advertisement. If the
watch MAC is seen, the operator is within ~10m. No pairing required —
just passive BLE advertisement detection.

Provides:
  - bt_watch_connected: bool (watch BLE advertisement seen recently)
"""

from __future__ import annotations

import logging
import subprocess
import time

from agents.hapax_daimonion.perception import PerceptionTier
from agents.hapax_daimonion.primitives import Behavior

log = logging.getLogger(__name__)

_WATCH_MAC = "B0:D5:FB:A5:86:E8"
_SCAN_DURATION_S = 5  # how long to scan each poll
_STALE_THRESHOLD_S = 60  # consider watch gone if not seen for this long


class BTPresenceBackend:
    """PerceptionBackend that detects Pixel 10 phone via BLE scan (no pairing)."""

    def __init__(self, watch_mac: str = _WATCH_MAC) -> None:
        self._watch_mac = watch_mac.upper()
        self._b_connected: Behavior[bool] = Behavior(False)
        self._last_seen: float = 0.0

    @property
    def name(self) -> str:
        return "bt_presence"

    @property
    def provides(self) -> frozenset[str]:
        return frozenset({"bt_watch_connected"})

    @property
    def tier(self) -> PerceptionTier:
        return PerceptionTier.SLOW  # BLE scan takes a few seconds

    def available(self) -> bool:
        try:
            result = subprocess.run(
                ["bluetoothctl", "show"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            return "Powered: yes" in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def contribute(self, behaviors: dict[str, Behavior]) -> None:
        now = time.monotonic()

        # Check actual connection state (not just paired list).
        # "Connected: yes" in bluetoothctl info means active link = proximity.
        # Paired-but-disconnected is NOT evidence of presence.
        connected = False
        try:
            result = subprocess.run(
                ["bluetoothctl", "info", self._watch_mac],
                capture_output=True,
                text=True,
                timeout=3,
            )
            connected = "Connected: yes" in result.stdout
        except Exception:
            pass

        self._b_connected.update(connected, now)
        behaviors["bt_watch_connected"] = self._b_connected

    def start(self) -> None:
        # Do an initial scan to populate the device list
        try:
            subprocess.Popen(
                ["bluetoothctl", "scan", "on"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Let it run — bluetoothctl scan persists in background
            time.sleep(_SCAN_DURATION_S)
            subprocess.run(
                ["bluetoothctl", "scan", "off"],
                capture_output=True,
                timeout=3,
            )
        except Exception:
            pass
        log.info("BT presence backend started (watch=%s)", self._watch_mac)

    def stop(self) -> None:
        try:
            subprocess.run(
                ["bluetoothctl", "scan", "off"],
                capture_output=True,
                timeout=3,
            )
        except Exception:
            pass
        log.info("BT presence backend stopped")
