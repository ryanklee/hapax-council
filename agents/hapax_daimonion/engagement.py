# agents/hapax_daimonion/engagement.py
"""Engagement classifier — replaces wake word detection.

Three-stage pipeline:
  Stage 1: VAD gate (speech detected, operator present)
  Stage 2: Directed-speech classifier (context window, gaze, exclusions)
  Stage 3: Semantic confirmation (speculative STT + salience, only when ambiguous)
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.hapax_daimonion.perception import Behavior

log = logging.getLogger("engagement")

CONTEXT_WINDOW_S = 45.0
GAZE_STALE_S = 5.0
ACTIVATE_THRESHOLD = 0.4
SUPPRESS_THRESHOLD = 0.2
FOLLOW_UP_THRESHOLD = 0.1
FOLLOW_UP_WINDOW_S = 30.0
MEETING_ACTIVITIES = frozenset({"meeting", "phone_call"})
DESK_GAZE_ZONES = frozenset({"desk", "screen", "monitor"})


class EngagementClassifier:
    """Determines whether operator speech is directed at the system."""

    def __init__(self, on_engaged: Callable[[], None]) -> None:
        self._on_engaged = on_engaged
        self._last_system_speech: float = 0.0
        self._follow_up_until: float = 0.0
        self._last_activation: float = 0.0
        self._debounce_s: float = 2.0

    def notify_system_spoke(self) -> None:
        """Called when TTS playback finishes."""
        self._last_system_speech = time.monotonic()

    def notify_session_closed(self) -> None:
        """Called when a session closes — opens follow-up window."""
        self._follow_up_until = time.monotonic() + FOLLOW_UP_WINDOW_S

    def on_speech_detected(self, behaviors: dict[str, Behavior]) -> None:
        """Called from audio loop when VAD detects speech and operator is present.

        Runs Stage 2 evaluation. If ambiguous, Stage 3 would run async
        (deferred to v2 — for now, ambiguous = suppress).
        """
        now = time.monotonic()
        if now - self._last_activation < self._debounce_s:
            return

        score = self.evaluate(behaviors)
        threshold = FOLLOW_UP_THRESHOLD if self._in_follow_up_window() else ACTIVATE_THRESHOLD

        if score >= threshold:
            self._last_activation = now
            log.info(
                "Engagement detected: score=%.2f threshold=%.2f",
                score,
                threshold,
            )
            self._on_engaged()

    def evaluate(self, behaviors: dict[str, Behavior]) -> float:
        """Stage 2: compute engagement score from available signals."""
        context = self._check_context_window()
        gaze = self._check_gaze(behaviors)
        exclusion = self._check_exclusions(behaviors)

        # Weighted OR: best positive signal, gated by exclusions
        positive = max(context, gaze)
        return positive * exclusion

    def _check_context_window(self) -> float:
        """Stage 2a: recent system speech implies follow-up.

        Hot zone (0-15s): linearly decays from 1.0 to 0.9.
        Tail zone (15-45s): linearly decays from 0.9 to 0.0.
        Beyond 45s: 0.0.
        """
        if self._last_system_speech == 0.0:
            return 0.0
        age = time.monotonic() - self._last_system_speech
        if age < 0.0:
            return 1.0
        if age <= 15.0:
            return 1.0 - (age / 15.0) * 0.1  # 1.0 → 0.9
        if age <= CONTEXT_WINDOW_S:
            return 0.9 * (1.0 - (age - 15.0) / (CONTEXT_WINDOW_S - 15.0))  # 0.9 → 0.0
        return 0.0

    def _check_gaze(self, behaviors: dict[str, Behavior]) -> float:
        """Stage 2c: head orientation from IR presence."""
        gaze_b = behaviors.get("ir_gaze_zone")
        if gaze_b is None:
            return 0.5  # neutral — no data, don't block

        age = time.monotonic() - getattr(gaze_b, "timestamp", 0.0)
        if age > GAZE_STALE_S:
            return 0.5  # stale — neutral

        zone = getattr(gaze_b, "value", "")
        if zone in DESK_GAZE_ZONES:
            return 0.8
        return 0.2

    def _check_exclusions(self, behaviors: dict[str, Behavior]) -> float:
        """Stage 2b/2d: phone call and meeting activity suppress."""
        phone = behaviors.get("phone_call_active")
        if phone is not None and getattr(phone, "value", False):
            return 0.0

        activity = behaviors.get("activity_mode")
        if activity is not None and getattr(activity, "value", "") in MEETING_ACTIVITIES:
            return 0.0

        return 1.0

    def _in_follow_up_window(self) -> bool:
        """Check if we're in the post-session follow-up window."""
        return time.monotonic() < self._follow_up_until
