"""Local Langfuse trace reader — durable consumer-side store.

`agents.langfuse_sync` polls Langfuse every 6 hours and persists daily
trace records to ``~/documents/rag-sources/langfuse/traces-YYYY-MM-DD.jsonl``
alongside the human-readable markdown summaries.

This module reads from those JSONL files, giving consumers a durable trace
store that survives MinIO blob retention rotation (queue #242: dropped
from 14 days → 3 days). Consumers that previously polled the Langfuse API
with multi-day lookback windows should switch to this reader so they keep
working when the API stops returning >3-day-old data.

Caveat — granularity: this store is **trace-level**, not observation-level.
``langfuse_sync`` extracts ``TraceSummary`` records (one per Langfuse trace,
which can contain multiple LLM calls). For per-call analysis (token
distribution within a trace, fine-grained latency), continue to query the
Langfuse API directly with a ≤3-day window.

Example:

    from datetime import UTC, datetime, timedelta
    from agents import _langfuse_local

    since = datetime.now(UTC) - timedelta(days=14)
    for trace in _langfuse_local.query_traces(since):
        ...

    cost_per_model = _langfuse_local.cost_by_model(since)
    daily = _langfuse_local.daily_cost_trend(days=30)
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

log = logging.getLogger("agents._langfuse_local")

LANGFUSE_DIR: Path = Path.home() / "documents" / "rag-sources" / "langfuse"


def is_available() -> bool:
    """Return True if at least one daily trace JSONL file exists locally."""
    if not LANGFUSE_DIR.exists():
        return False
    return any(LANGFUSE_DIR.glob("traces-*.jsonl"))


def query_traces(since: datetime, until: datetime | None = None) -> Iterator[dict]:
    """Yield trace summary dicts within [since, until].

    Each dict matches ``agents.langfuse_sync.TraceSummary`` schema:
    ``trace_id``, ``name``, ``timestamp``, ``model``, ``input_preview``,
    ``output_preview``, ``total_cost``, ``latency_ms``, ``status``,
    ``tags``, ``metadata``.

    Iteration order: ascending by ``timestamp`` within each daily file,
    then by file date.
    """
    if until is None:
        until = datetime.now(UTC)
    if not LANGFUSE_DIR.exists():
        return

    since_str = since.isoformat()
    until_str = until.isoformat()
    since_day = since.strftime("%Y-%m-%d")
    until_day = until.strftime("%Y-%m-%d")

    for jsonl_path in sorted(LANGFUSE_DIR.glob("traces-*.jsonl")):
        date_part = jsonl_path.stem.replace("traces-", "")
        if date_part < since_day or date_part > until_day:
            continue
        try:
            with jsonl_path.open() as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError as exc:
                        log.warning("skipping malformed line in %s: %s", jsonl_path, exc)
                        continue
                    ts = rec.get("timestamp", "")
                    if since_str <= ts <= until_str:
                        yield rec
        except OSError as exc:
            log.warning("failed to read %s: %s", jsonl_path, exc)
            continue


def trace_count(since: datetime, until: datetime | None = None) -> int:
    """Total trace count in window."""
    return sum(1 for _ in query_traces(since, until))


def cost_by_model(since: datetime, until: datetime | None = None) -> dict[str, float]:
    """Aggregate ``total_cost`` by model name within window."""
    totals: dict[str, float] = {}
    for trace in query_traces(since, until):
        model = trace.get("model") or "unknown"
        cost = float(trace.get("total_cost", 0.0) or 0.0)
        totals[model] = totals.get(model, 0.0) + cost
    return totals


def count_by_model(since: datetime, until: datetime | None = None) -> dict[str, int]:
    """Trace count by model name within window."""
    counts: dict[str, int] = {}
    for trace in query_traces(since, until):
        model = trace.get("model") or "unknown"
        counts[model] = counts.get(model, 0) + 1
    return counts


def daily_cost_trend(days: int) -> dict[str, float]:
    """Daily cost rollup for the last N days. Returns {YYYY-MM-DD: cost}."""
    until = datetime.now(UTC)
    since = until - timedelta(days=days)
    daily: dict[str, float] = {}
    for trace in query_traces(since, until):
        ts = trace.get("timestamp", "")
        day = ts[:10]
        if not day:
            continue
        daily[day] = daily.get(day, 0.0) + float(trace.get("total_cost", 0.0) or 0.0)
    return daily


def filter_by_name(
    name_substring: str,
    since: datetime,
    until: datetime | None = None,
    *,
    case_sensitive: bool = False,
) -> Iterator[dict]:
    """Yield traces whose ``name`` contains the given substring.

    Useful for governance accounting (e.g. ``axiom_gate``, ``consent_check``).
    """
    needle = name_substring if case_sensitive else name_substring.lower()
    for trace in query_traces(since, until):
        name = trace.get("name", "")
        haystack = name if case_sensitive else name.lower()
        if needle in haystack:
            yield trace
