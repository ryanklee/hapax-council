"""Fortress episode system — episode boundary detection and storage.

Extends the base EpisodeBuilder with fortress-specific trigger logic.
Episode boundaries: season change, siege start/end, migrant wave, death,
mood event, milestone (era transition).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from agents.fortress.schema import (
    DeathEvent,
    FastFortressState,
    FortressEvent,
    MigrantEvent,
    MoodEvent,
    SiegeEvent,
)

log = logging.getLogger(__name__)


@dataclass
class FortressEpisode:
    """A bounded period of fortress activity."""

    session_id: str = ""
    fortress_name: str = ""
    game_tick_start: int = 0
    game_tick_end: int = 0
    season: int = 0
    year: int = 0
    trigger: str = ""  # what caused this episode boundary
    population_start: int = 0
    population_end: int = 0
    food_start: int = 0
    food_end: int = 0
    wealth_start: int = 0
    wealth_end: int = 0
    events: list[FortressEvent] = field(default_factory=list)
    narrative: str = ""
    commands_by_chain: dict[str, int] = field(default_factory=dict)
    timestamp_start: float = 0.0
    timestamp_end: float = 0.0

    @property
    def population_delta(self) -> int:
        return self.population_end - self.population_start

    @property
    def food_delta(self) -> int:
        return self.food_end - self.food_start

    @property
    def duration_ticks(self) -> int:
        return self.game_tick_end - self.game_tick_start

    def summary_text(self) -> str:
        """Generate text for embedding/search."""
        parts = [
            f"{self.fortress_name} Year {self.year} Season {self.season}:",
            f"{self.trigger}.",
            f"Pop {self.population_delta:+d},",
            f"food {self.food_delta:+d}.",
        ]
        if self.narrative:
            parts.append(self.narrative)
        return " ".join(parts)


class FortressEpisodeBuilder:
    """Detects episode boundaries from fortress state changes."""

    def __init__(self, session_id: str = "") -> None:
        self._session_id = session_id
        self._current: FortressEpisode | None = None
        self._last_state: FastFortressState | None = None
        self._closed_episodes: list[FortressEpisode] = []

    @property
    def closed_episodes(self) -> list[FortressEpisode]:
        """Drain closed episodes (returns and clears)."""
        episodes = list(self._closed_episodes)
        self._closed_episodes.clear()
        return episodes

    def observe(self, state: FastFortressState) -> FortressEpisode | None:
        """Process a new state snapshot. Returns closed episode if boundary detected."""
        if self._current is None:
            self._start_episode(state, "start")
            self._last_state = state
            return None

        trigger = self._check_boundary(state)
        if trigger:
            closed = self._close_episode(state, trigger)
            self._start_episode(state, trigger)
            self._last_state = state
            return closed

        # Accumulate events
        for event in state.pending_events:
            self._current.events.append(event)

        self._last_state = state
        return None

    def flush(self) -> FortressEpisode | None:
        """Close current episode (e.g., on shutdown)."""
        if self._current is not None and self._last_state is not None:
            return self._close_episode(self._last_state, "flush")
        return None

    def _check_boundary(self, state: FastFortressState) -> str | None:
        """Check if a new episode should start. Returns trigger name or None."""
        if self._last_state is None:
            return None

        # Season change
        if state.season != self._last_state.season or state.year != self._last_state.year:
            return "season_change"

        # Check pending events for significant triggers
        for event in state.pending_events:
            if isinstance(event, SiegeEvent):
                return "siege"
            if isinstance(event, MigrantEvent):
                return "migrant"
            if isinstance(event, DeathEvent):
                return "death"
            if isinstance(event, MoodEvent):
                return "mood"

        # Large population change (migrant wave without event)
        if abs(state.population - self._last_state.population) >= 5:
            return "population_shift"

        return None

    def _start_episode(self, state: FastFortressState, trigger: str) -> None:
        self._current = FortressEpisode(
            session_id=self._session_id,
            fortress_name=state.fortress_name,
            game_tick_start=state.game_tick,
            season=state.season,
            year=state.year,
            trigger=trigger,
            population_start=state.population,
            food_start=state.food_count,
            wealth_start=0,
            timestamp_start=time.time(),
        )

    def _close_episode(self, state: FastFortressState, trigger: str) -> FortressEpisode:
        ep = self._current
        assert ep is not None
        ep.trigger = trigger
        ep.game_tick_end = state.game_tick
        ep.population_end = state.population
        ep.food_end = state.food_count
        ep.timestamp_end = time.time()
        self._closed_episodes.append(ep)
        self._current = None
        return ep
