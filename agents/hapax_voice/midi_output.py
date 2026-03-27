"""MidiOutput — thin mido wrapper for sending MIDI CC messages.

Lazy-initializes the MIDI output port on first send. Fails gracefully
if no MIDI hardware is available (logs warning, becomes a no-op).
"""

from __future__ import annotations

import logging

import mido

log = logging.getLogger(__name__)


class MidiOutput:
    """Send MIDI CC messages to external hardware."""

    def __init__(self, port_name: str = "") -> None:
        self._port_name = port_name
        self._port: mido.ports.BaseOutput | None = None
        self._init_failed = False

    def send_cc(self, channel: int, cc: int, value: int) -> None:
        """Send a MIDI Control Change message.

        Args:
            channel: MIDI channel (0-indexed, 0-15).
            cc: CC number (0-127).
            value: CC value (0-127, clamped).
        """
        if self._init_failed:
            return
        if self._port is None:
            self._open_port()
            if self._port is None:
                return

        value = max(0, min(127, value))
        msg = mido.Message("control_change", channel=channel, control=cc, value=value)
        self._port.send(msg)

    def _open_port(self) -> None:
        """Lazy-open the MIDI output port."""
        try:
            name = self._port_name or None  # None = mido picks first available
            self._port = mido.open_output(name)
            log.info("MIDI output opened: %s", self._port.name)
        except OSError as exc:
            log.warning("No MIDI output available (%s) — vocal chain disabled", exc)
            self._init_failed = True

    def close(self) -> None:
        """Close the MIDI output port."""
        if self._port is not None:
            self._port.close()
            self._port = None
