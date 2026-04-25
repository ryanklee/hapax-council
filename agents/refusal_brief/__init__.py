"""Refusal-event log writer (`awareness-refusal-brief-writer` Phase 1).

Single canonical append-only log of every refusal event. Materializes
the refusal-as-data axiom per ``feedback_full_automation_or_no_engagement``
into a concrete data structure that any surface can subscribe to
without aggregation.

Usage from a refusal source (axiom guard, consent trace, content
resolver, refusal gate, publication bus)::

    from agents.refusal_brief import RefusalEvent, append
    from datetime import datetime, UTC

    append(RefusalEvent(
        timestamp=datetime.now(UTC),
        axiom="full_auto_or_nothing",
        surface="publication-bus:bandcamp-upload",
        reason="Bandcamp 'Keeping Bandcamp Human' — explicit AI ban",
    ))

Append is thread-safe and best-effort (failures log without raising
so the calling refusal-gate path is unaffected). The log lives at
``/dev/shm/hapax-refusals/log.jsonl`` (operator-overridable via
``HAPAX_REFUSALS_LOG_PATH``).
"""

from agents.refusal_brief.writer import (
    DEFAULT_LOG_PATH,
    RefusalEvent,
    append,
)

__all__ = ["DEFAULT_LOG_PATH", "RefusalEvent", "append"]
