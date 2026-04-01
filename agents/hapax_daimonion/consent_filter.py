"""Consent ingestion filter for the perception pipeline.

Suppresses person-adjacent perception behaviors when consent is
unresolved (guest detected but no active consent contract). Applied
in PerceptionEngine.tick() after backends contribute but before
EnvironmentState construction.

ir_person_detected flows unconditionally — the ConsentStateTracker
needs it to maintain its own state transitions.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# Behaviors that reveal non-operator persons — suppressed when consent unresolved
PERSON_ADJACENT_BEHAVIORS: frozenset[str] = frozenset(
    {
        "ir_person_count",
        "ir_gaze_zone",
        "ir_head_pose_yaw",
        "ir_posture",
        "ir_drowsiness_score",
        "ir_blink_rate",
        "ir_heart_rate_bpm",
        "ir_heart_rate_conf",
        "face_count",
        "guest_count",
        "top_emotion",
        "gaze_direction",
        "hand_gesture",
        "posture",
        "pose_summary",
    }
)

# Phases where person-adjacent data may flow
CONSENT_ALLOWED_PHASES = frozenset({"NO_GUEST", "CONSENT_GRANTED"})


def filter_behaviors(behaviors: dict, consent_phase: str) -> int:
    """Suppress person-adjacent behaviors when consent is unresolved.

    Args:
        behaviors: dict of behavior_name -> Behavior objects
        consent_phase: current ConsentStateTracker phase string

    Returns:
        Number of behaviors suppressed.
    """
    if consent_phase in CONSENT_ALLOWED_PHASES:
        return 0

    suppressed = 0
    for name in PERSON_ADJACENT_BEHAVIORS:
        if name in behaviors:
            behavior = behaviors[name]
            # Reset to safe default without advancing watermark
            if hasattr(behavior, "_value"):
                if isinstance(behavior._value, bool):
                    behavior._value = False
                elif isinstance(behavior._value, (int, float)):
                    behavior._value = 0
                elif isinstance(behavior._value, str):
                    behavior._value = "unknown"
                suppressed += 1

    if suppressed > 0:
        log.info(
            "Consent filter: suppressed %d person-adjacent behaviors (phase=%s)",
            suppressed,
            consent_phase,
        )
    return suppressed
