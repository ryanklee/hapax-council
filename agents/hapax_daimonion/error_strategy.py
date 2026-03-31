"""Degradation tracking for graceful subsystem failures.

Replaces silent log.info("skipping") patterns with structured events
that can be queried for health checks and diagnostics.
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from dataclasses import dataclass

log = logging.getLogger(__name__)

__all__ = ["DegradationEvent", "DegradationRegistry"]


@dataclass(frozen=True)
class DegradationEvent:
    """A recorded subsystem degradation."""

    subsystem: str
    component: str
    severity: str  # "info", "warning", "error"
    message: str
    timestamp: float


class DegradationRegistry:
    """Tracks active degradations across all subsystems."""

    def __init__(self) -> None:
        self._events: list[DegradationEvent] = []

    def record(
        self,
        subsystem: str,
        component: str,
        severity: str,
        message: str,
    ) -> None:
        """Record a degradation event and log it."""
        event = DegradationEvent(
            subsystem=subsystem,
            component=component,
            severity=severity,
            message=message,
            timestamp=time.monotonic(),
        )
        self._events.append(event)
        log_fn = getattr(log, severity, log.warning)
        log_fn("Degradation [%s/%s]: %s", subsystem, component, message)

    def active(self) -> list[DegradationEvent]:
        """Return all recorded degradations."""
        return list(self._events)

    def count_by_severity(self) -> dict[str, int]:
        """Count degradations by severity level."""
        return dict(Counter(e.severity for e in self._events))

    def summary(self) -> str:
        """Human-readable summary of all degradations."""
        if not self._events:
            return "No degradations recorded"
        lines = [f"{len(self._events)} degradation(s):"]
        for e in self._events:
            lines.append(f"  [{e.severity}] {e.subsystem}/{e.component}: {e.message}")
        return "\n".join(lines)
