"""Shared reader for the LRR Phase 1 research marker.

The research marker file at ``/dev/shm/hapax-compositor/research-marker.json``
carries the active research ``condition_id``. It is written by
``scripts/research-registry.py`` on every ``init`` / ``open`` / ``close``
invocation, and read by consumers that need to tag their telemetry with
the currently-active research condition.

The JSON shape is::

    {
        "condition_id": "cond-phase-a-baseline-qwen-001",
        "written_at": "2026-04-14T12:00:00+00:00"
    }

Consumers who stamp telemetry with the active condition_id:

- ``agents/studio_compositor/director_loop.py`` — livestream director
  reactions are stamped with ``condition_id`` on every JSONL + Qdrant +
  Langfuse write (LRR Phase 1 shipped this path via an inlined helper).
- ``agents/hapax_daimonion/conversation_pipeline.py`` — voice pipeline
  grounding DVs (LRR Phase 4 scope item 1 adds this path).
- ``agents/hapax_daimonion/grounding_evaluator.py`` — grounding DV
  scorers called from ``conversation_pipeline`` (same LRR Phase 4 scope
  item — one DEVIATION covers the frozen-file edit).

Before LRR Phase 4 this reader lived inline in ``director_loop.py`` as
``_read_research_marker()``. This module hoists it so both
``director_loop`` and the Phase 4 voice-pipeline consumers depend on a
single implementation — consistent 5-second TTL, consistent fail-safe
behavior, single place to mock in tests.

The cache is keyed on the marker ``Path`` so production (single default
path) and tests (per-test override paths) do not cross-contaminate.
Callers that need a fresh read (typically tests after writing a new
marker) call :func:`clear_cache`.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

RESEARCH_MARKER_PATH = Path("/dev/shm/hapax-compositor/research-marker.json")
"""Canonical marker location. ``scripts/research-registry.py`` writes
here; all production consumers read here."""

CACHE_TTL_S = 5.0
"""Cache lifetime in seconds. Matches the original inlined helper in
``director_loop.py``. Short enough that a new ``research-registry
open`` becomes visible to livestream reactions within 5 s; long enough
that the reader is not a per-tick filesystem hit on the 30 fps
compositor main loop."""


_cache_by_path: dict[Path, tuple[float, str | None]] = {}
"""Module-level cache keyed on marker Path so distinct paths (e.g.,
different test tmp dirs) do not cross-contaminate. Production uses a
single key (``RESEARCH_MARKER_PATH``); tests may use many."""


def read_research_marker(
    *,
    marker_path: Path | None = None,
    now: float | None = None,
) -> str | None:
    """Return the active LRR research ``condition_id``, or ``None``.

    Cached for :data:`CACHE_TTL_S` seconds on the monotonic clock. Any
    filesystem or JSON error silently yields ``None`` — callers treat
    ``None`` as "no active research condition, do not stamp telemetry
    with a condition_id."

    The helper never raises. Every observed failure mode (file absent,
    unreadable, not valid JSON, not a dict, missing ``condition_id``
    key, ``condition_id`` is ``None``, ``condition_id`` is empty
    string, ``condition_id`` is a non-string type) resolves to
    ``None``.

    Args:
        marker_path: Override for tests. Defaults to
            :data:`RESEARCH_MARKER_PATH`.
        now: Override for the monotonic clock. Defaults to
            :func:`time.monotonic`. Tests that want deterministic cache
            behavior pass their own value rather than relying on wall
            clock.

    Returns:
        The active research condition_id string, or ``None`` if no
        active condition is set.
    """
    path = marker_path or RESEARCH_MARKER_PATH
    now_ts = now if now is not None else time.monotonic()

    cached = _cache_by_path.get(path)
    if cached is not None:
        loaded_at, cached_id = cached
        if (now_ts - loaded_at) < CACHE_TTL_S:
            return cached_id

    condition_id: str | None = None
    try:
        raw = path.read_text()
        data = json.loads(raw)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = None

    if isinstance(data, dict):
        raw_id = data.get("condition_id")
        if isinstance(raw_id, str) and raw_id:
            condition_id = raw_id

    _cache_by_path[path] = (now_ts, condition_id)
    return condition_id


def clear_cache() -> None:
    """Clear the in-memory cache. Useful for tests that need a fresh read.

    Production callers should not normally invoke this — the cache is
    part of the contract and a 5-second stale window is intentional.
    """
    _cache_by_path.clear()


__all__ = [
    "CACHE_TTL_S",
    "RESEARCH_MARKER_PATH",
    "clear_cache",
    "read_research_marker",
]
