"""Shared access to the active research registry condition ID.

LRR Phase 1 established the append-only research registry with a canonical
pointer file at ``~/hapax-state/research-registry/current.txt``. LRR Phase 10
requires per-condition slicing for Prometheus metrics + research analysis.

This module is the single read path for the active condition so downstream
metrics labels, telemetry tags, and observability surfaces stay consistent.
Writers (registry state transitions) live in the research registry's own
management path — NOT here.

Design choices:

- Caller pays for staleness: reads happen on demand. A Prometheus metric
  wrapper may want to cache for ≤1s to avoid filesystem thrash; that cache
  policy is the wrapper's responsibility, not this module's.
- Fails open to ``"unknown"`` label rather than dropping metrics: losing
  the time series entirely under a transient read error is worse than
  briefly mis-labeling. Callers that want strict handling can use
  ``get_current_condition_strict()`` and catch ``ConditionUnavailable``.
"""

from __future__ import annotations

from pathlib import Path

CONDITION_POINTER = Path.home() / "hapax-state" / "research-registry" / "current.txt"
UNKNOWN_CONDITION_LABEL = "unknown"


class ConditionUnavailable(RuntimeError):
    """The research registry has no active condition on record."""


def get_current_condition(pointer_path: Path = CONDITION_POINTER) -> str:
    """Return the active condition_id, or ``"unknown"`` if unavailable."""
    try:
        return get_current_condition_strict(pointer_path)
    except ConditionUnavailable:
        return UNKNOWN_CONDITION_LABEL


def get_current_condition_strict(pointer_path: Path = CONDITION_POINTER) -> str:
    """Return the active condition_id. Raises if unset or unreadable."""
    if not pointer_path.exists():
        raise ConditionUnavailable(f"pointer file {pointer_path} does not exist")
    try:
        value = pointer_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ConditionUnavailable(f"failed to read {pointer_path}: {exc}") from exc
    if not value:
        raise ConditionUnavailable(f"pointer file {pointer_path} is empty")
    return value
