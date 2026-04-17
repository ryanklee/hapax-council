"""Environmental snapshot aggregator.

Pure function that reads the various environmental signal sources
(time-of-day clock, weather sensor state at ``/dev/shm/hapax-sensors/
weather.json`` when available, ambient audio/presence indicators from
stimmung) and returns a single ``EnvironmentalSnapshot``.

The compositor consumes this at whatever cadence it chooses (30-60s
cadence is sensible; the time-of-day banding doesn't change faster).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Weather sensor state path (written by agents.weather_sync).
WEATHER_STATE_PATH = Path("/dev/shm/hapax-sensors/weather.json")

# Stimmung snapshot (ambient-energy + operator-energy live here).
STIMMUNG_STATE_PATH = Path("/dev/shm/hapax-stimmung/state.json")


@dataclass(frozen=True)
class EnvironmentalSnapshot:
    """Aggregated environmental state at a point in time."""

    time_of_day: str  # "morning" | "midday" | "afternoon" | "evening" | "night" | "late-night"
    local_hour_24: int
    weather_summary: str | None = None  # short human summary like "47°F, partly cloudy"
    weather_fresh: bool = False  # True iff weather was updated in the last 30 min
    ambient_energy_band: str | None = None  # "low" | "medium" | "high" (from stimmung)
    captured_at: str = ""
    extras: dict[str, Any] = field(default_factory=dict)


# ── Time-of-day banding ─────────────────────────────────────────────────────


def band_time_of_day(hour: int) -> str:
    """Map a 0-23 local hour to a time-of-day label.

    Bands chosen to match the operator's studio rhythm:
      00-04 late-night (deep studio hours)
      05-08 morning
      09-11 midday
      12-16 afternoon
      17-20 evening
      21-23 night
    """
    if 0 <= hour < 5:
        return "late-night"
    if 5 <= hour < 9:
        return "morning"
    if 9 <= hour < 12:
        return "midday"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


# ── Weather helpers ─────────────────────────────────────────────────────────


def _read_weather_state(path: Path = WEATHER_STATE_PATH) -> dict[str, Any] | None:
    """Return the parsed weather sensor state, or None on any failure."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        log.debug("weather state read failed", exc_info=True)
        return None


def _weather_summary(state: dict[str, Any]) -> str | None:
    """Render a weather-state dict into a terse human summary.

    Accepts the common shapes observed from the weather_sync agent:
      {"temp_f": 47, "condition": "partly cloudy"}
      {"temperature": 47.0, "description": "partly cloudy"}
    Unknown shapes return None.
    """
    temp = state.get("temp_f") or state.get("temperature")
    cond = state.get("condition") or state.get("description")
    if temp is None and not cond:
        return None
    parts: list[str] = []
    if temp is not None:
        try:
            parts.append(f"{int(round(float(temp)))}°F")
        except (TypeError, ValueError):
            pass
    if cond:
        parts.append(str(cond))
    return ", ".join(parts) or None


def _weather_fresh(state: dict[str, Any], *, stale_after_minutes: int = 30) -> bool:
    """True iff the weather state's updated-at timestamp is within the
    fresh window."""
    ts = state.get("updated_at") or state.get("timestamp")
    if ts is None:
        return False
    try:
        # Accept either ISO8601 strings or epoch seconds
        if isinstance(ts, (int, float)):
            age_s = datetime.now().timestamp() - float(ts)
        else:
            s = str(ts).replace("Z", "+00:00")
            age_s = (
                datetime.now(datetime.fromisoformat(s).tzinfo) - datetime.fromisoformat(s)
            ).total_seconds()
    except (ValueError, TypeError):
        return False
    return 0 <= age_s <= stale_after_minutes * 60


# ── Stimmung helpers ────────────────────────────────────────────────────────


def _read_stimmung_state(path: Path = STIMMUNG_STATE_PATH) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _band_value_low_med_high(value: float) -> str:
    if value < 0.33:
        return "low"
    if value < 0.66:
        return "medium"
    return "high"


def _ambient_energy_band(stimmung: dict[str, Any]) -> str | None:
    """Extract an ambient-energy band from the stimmung snapshot.

    Uses ``operator_energy`` if present (the 0-1 dimension in the live
    stimmung). This is a sensible proxy for ambient / engagement level in
    the room during an active stream segment.
    """
    block = stimmung.get("operator_energy")
    if block is None:
        return None
    if not isinstance(block, dict):
        return None
    try:
        value = float(block.get("value", 0.0))
    except (TypeError, ValueError):
        return None
    return _band_value_low_med_high(value)


# ── Top-level aggregator ────────────────────────────────────────────────────


def read_environmental_snapshot(
    now: datetime | None = None,
    *,
    weather_reader=None,
    stimmung_reader=None,
) -> EnvironmentalSnapshot:
    """Pull the latest environmental state.

    Args:
        now: Inject a specific time (for tests). Defaults to
            ``datetime.now()`` (local).
        weather_reader / stimmung_reader: Injection points for tests.

    Returns:
        EnvironmentalSnapshot. Fields missing their source are None.
        The snapshot is always returned; errors in individual sources
        degrade their fields only.
    """
    now = now or datetime.now()
    hour = now.hour
    tod = band_time_of_day(hour)

    weather_state = (weather_reader or _read_weather_state)()
    weather_summary = None
    weather_fresh = False
    if weather_state is not None:
        weather_summary = _weather_summary(weather_state)
        weather_fresh = _weather_fresh(weather_state)

    stimmung_state = (stimmung_reader or _read_stimmung_state)()
    ambient_energy_band = None
    if stimmung_state is not None:
        ambient_energy_band = _ambient_energy_band(stimmung_state)

    return EnvironmentalSnapshot(
        time_of_day=tod,
        local_hour_24=hour,
        weather_summary=weather_summary,
        weather_fresh=weather_fresh,
        ambient_energy_band=ambient_energy_band,
        captured_at=now.isoformat(),
    )
