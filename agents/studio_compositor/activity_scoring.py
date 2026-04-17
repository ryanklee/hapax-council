"""LRR Phase 9 §3.2 — stimmung-modulated activity selection.

Pure scoring helpers for the director-loop activity selector. Given a
candidate activity (``react`` / ``chat`` / ``vinyl`` / ``study`` /
``observe`` / ``silence``) plus three terms, returns a single number:

    score(a) = momentary_weight · momentary
             + objective_weight · objective_alignment
             + stimmung_weight  · stimmung_term

The weights default to ``0.70 / 0.25 / 0.05`` per spec §3.2 — conservative
start per the §6 oscillation-risk note. The stimmung term is derived
from the published chat-signals SHM (see ``agents/chat_monitor/sink.py``
and PR #998), mapped to a per-activity modulation: high engagement +
many threads lifts ``chat``, low engagement lifts ``study`` / ``silence``.

The module is side-effect-free and injection-friendly. The caller
passes ``momentary`` and ``objective_alignment`` from whatever upstream
logic already has them; ``stimmung_term`` is either supplied directly
or read via ``stimmung_term_for_activity``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_MOMENTARY_WEIGHT: float = 0.70
DEFAULT_OBJECTIVE_WEIGHT: float = 0.25
DEFAULT_STIMMUNG_WEIGHT: float = 0.05

# Chat-signal thresholds for high / low engagement (derived from
# participant_diversity + thread_count + semantic_coherence).
HIGH_ENGAGEMENT_SCORE: float = 0.65
LOW_ENGAGEMENT_SCORE: float = 0.30


# ── Engagement score from chat signals ──────────────────────────────────────


def engagement_from_chat_signals(chat_signals: dict[str, Any] | None) -> float:
    """Compute a single 0..1 engagement score from the published signals.

    Combines participant diversity (broad engagement), thread count
    (conversational liveliness, capped / normalised), and semantic
    coherence (audience focus) — each 0..1 — into a mean.
    Returns 0.0 when the signals dict is missing or malformed.
    """
    if not isinstance(chat_signals, dict):
        return 0.0

    try:
        diversity = max(0.0, min(1.0, float(chat_signals.get("participant_diversity", 0.0))))
        coherence = max(0.0, min(1.0, float(chat_signals.get("semantic_coherence", 0.0))))
        threads = max(0, int(chat_signals.get("thread_count", 0)))
    except (TypeError, ValueError):
        return 0.0

    # Thread count normalized so 3+ threads ≥ 1.0 (studio-lively upper bound).
    thread_signal = min(1.0, threads / 3.0)
    return (diversity + coherence + thread_signal) / 3.0


# ── Per-activity stimmung term ──────────────────────────────────────────────


def stimmung_term_for_activity(
    activity: str,
    *,
    engagement: float,
    active_chat_messages: int = 0,
) -> float:
    """Return a signed modulation term for ``activity`` in [-1, 1].

    * High engagement + active chat threads → raise ``chat`` / ``react``.
    * Low engagement → raise ``study`` / ``silence``.
    * ``observe`` / ``vinyl`` neutral (0.0) — they're operator-facing,
      not audience-facing.

    The caller multiplies by the stimmung weight (0.05 default) so the
    effective push is small; we keep the raw value in [-1, 1] for
    introspection.
    """
    engagement = max(0.0, min(1.0, engagement))
    high = engagement >= HIGH_ENGAGEMENT_SCORE and active_chat_messages > 0
    low = engagement < LOW_ENGAGEMENT_SCORE

    if activity == "chat":
        if high:
            return 1.0
        if low:
            return -0.5
        return 0.0
    if activity == "react":
        if high:
            return 0.5
        if low:
            return -0.25
        return 0.0
    if activity in ("study", "silence"):
        if low:
            return 1.0 if activity == "study" else 0.5
        if high:
            return -0.5
        return 0.0
    # observe / vinyl / unknown → neutral.
    return 0.0


# ── Top-level score ─────────────────────────────────────────────────────────


def score_activity(
    activity: str,
    *,
    momentary: float,
    objective_alignment: float,
    stimmung_term: float = 0.0,
    momentary_weight: float = DEFAULT_MOMENTARY_WEIGHT,
    objective_weight: float = DEFAULT_OBJECTIVE_WEIGHT,
    stimmung_weight: float = DEFAULT_STIMMUNG_WEIGHT,
) -> float:
    """Weighted sum per spec §3.2. Inputs are clamped to [0, 1] / [-1, 1]."""
    m = max(0.0, min(1.0, momentary))
    o = max(0.0, min(1.0, objective_alignment))
    s = max(-1.0, min(1.0, stimmung_term))
    del activity  # name retained for caller-clarity + trace tagging
    return momentary_weight * m + objective_weight * o + stimmung_weight * s


# ── Convenience: SHM-backed stimmung term ───────────────────────────────────


def _read_chat_signals_from_shm(path: Path | None = None) -> dict[str, Any] | None:
    """Read the published chat signals JSON; return the dict or ``None``."""
    from agents.chat_monitor.sink import read_latest

    return read_latest(path)


def stimmung_term_for_activity_from_shm(
    activity: str,
    *,
    active_chat_messages: int = 0,
    path: Path | None = None,
) -> float:
    """Convenience wrapper: read signals, derive engagement, return the term."""
    signals = _read_chat_signals_from_shm(path)
    engagement = engagement_from_chat_signals(signals)
    return stimmung_term_for_activity(
        activity, engagement=engagement, active_chat_messages=active_chat_messages
    )
