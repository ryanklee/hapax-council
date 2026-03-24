"""Fortress query dispatch — routes operator questions to knowledge sources.

Supports temporal ("what happened since X"), causal ("why did X die"),
and strategic ("should I breach the cavern?") queries.
"""

from __future__ import annotations

import json
import logging

from shared.config import PROFILES_DIR

log = logging.getLogger(__name__)

CHRONICLE_PATH = PROFILES_DIR / "fortress-chronicle.jsonl"
SESSIONS_PATH = PROFILES_DIR / "fortress-sessions.jsonl"


def load_chronicle(limit: int = 50) -> list[dict]:
    """Load recent chronicle entries."""
    if not CHRONICLE_PATH.exists():
        return []
    entries = []
    for line in CHRONICLE_PATH.read_text().strip().split("\n"):
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries[-limit:]


def load_sessions(limit: int = 20) -> list[dict]:
    """Load historical session records."""
    if not SESSIONS_PATH.exists():
        return []
    entries = []
    for line in SESSIONS_PATH.read_text().strip().split("\n"):
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries[-limit:]


def build_query_context(
    query: str,
    chronicle: list[dict] | None = None,
    sessions: list[dict] | None = None,
) -> str:
    """Build context string for advisor LLM from available data sources."""
    parts = [f"Operator query: {query}", ""]

    chron = load_chronicle(20) if chronicle is None else chronicle
    if chron:
        parts.append("Recent chronicle entries:")
        for entry in chron[-10:]:
            parts.append(
                f"  [{entry.get('year', '?')}/{entry.get('season', '?')}] "
                f"{entry.get('narrative', entry.get('trigger', 'unknown'))}"
            )
        parts.append("")

    sess = load_sessions(5) if sessions is None else sessions
    if sess:
        parts.append("Historical sessions:")
        for s in sess[-3:]:
            parts.append(
                f"  {s.get('fortress_name', '?')}: "
                f"{s.get('survival_days', '?')} days, "
                f"cause={s.get('cause_of_death', '?')}"
            )
        parts.append("")

    return "\n".join(parts)
