"""Tests for ``shared/research_marker.py`` — the hoisted LRR Phase 1
research marker reader introduced by LRR Phase 4 scope item 1.

Before Phase 4, the reader lived inline in
``agents/studio_compositor/director_loop.py`` as ``_read_research_marker()``.
Phase 4 hoists it to a shared module so both ``director_loop`` and the
voice pipeline (``conversation_pipeline.py``) depend on a single
implementation with consistent 5-second cache TTL and fail-safe
behavior.

Tests cover:

- Happy path: marker file present with valid JSON and a condition_id string
- Marker absent (FileNotFoundError)
- Malformed JSON
- JSON payload is not a dict (e.g., a list)
- JSON payload is a dict but missing ``condition_id`` key
- ``condition_id`` is explicitly ``null``
- ``condition_id`` is an empty string
- ``condition_id`` is a non-string type (int)
- Cache hit within TTL (file change not visible until TTL elapses)
- Cache miss after TTL (file change visible after TTL elapses)
- :func:`clear_cache` forces a re-read within the TTL window
- Cache is keyed on marker ``Path`` — two distinct paths do not
  cross-contaminate
- ``None`` is also cached (don't keep retrying filesystem after absent)
- Transient file absence after successful read returns cached value
- Canonical path + TTL constant pins
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shared import research_marker


@pytest.fixture(autouse=True)
def _clear_cache_before_each_test():
    """Every test starts with an empty cache so ordering does not leak
    state between tests. Autouse so no test has to remember to call it.
    """
    research_marker.clear_cache()
    yield
    research_marker.clear_cache()


def _write_marker(path: Path, condition_id: str | None, *, extra: dict | None = None) -> None:
    payload: dict = {"condition_id": condition_id, "written_at": "2026-04-14T12:00:00+00:00"}
    if extra is not None:
        payload.update(extra)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


class TestHappyPath:
    def test_returns_condition_id_when_marker_present(self, tmp_path: Path) -> None:
        marker = tmp_path / "research-marker.json"
        _write_marker(marker, "cond-phase-a-baseline-qwen-001")

        result = research_marker.read_research_marker(marker_path=marker, now=0.0)

        assert result == "cond-phase-a-baseline-qwen-001"

    def test_caches_condition_id_within_ttl(self, tmp_path: Path) -> None:
        marker = tmp_path / "research-marker.json"
        _write_marker(marker, "cond-alpha")

        first = research_marker.read_research_marker(marker_path=marker, now=0.0)
        # Overwrite the marker — the cache should NOT see the new value
        # because the monotonic clock has not advanced past TTL.
        _write_marker(marker, "cond-beta")
        second = research_marker.read_research_marker(marker_path=marker, now=1.0)

        assert first == "cond-alpha"
        assert second == "cond-alpha"

    def test_cache_miss_after_ttl_elapses(self, tmp_path: Path) -> None:
        marker = tmp_path / "research-marker.json"
        _write_marker(marker, "cond-alpha")

        first = research_marker.read_research_marker(marker_path=marker, now=0.0)
        _write_marker(marker, "cond-beta")
        # Advance past TTL (default 5.0 s) — cache should refresh.
        second = research_marker.read_research_marker(
            marker_path=marker, now=research_marker.CACHE_TTL_S + 0.1
        )

        assert first == "cond-alpha"
        assert second == "cond-beta"


class TestFailSafe:
    def test_returns_none_when_marker_absent(self, tmp_path: Path) -> None:
        marker = tmp_path / "does-not-exist.json"

        result = research_marker.read_research_marker(marker_path=marker, now=0.0)

        assert result is None

    def test_returns_none_on_malformed_json(self, tmp_path: Path) -> None:
        marker = tmp_path / "research-marker.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("not-json {{{")

        result = research_marker.read_research_marker(marker_path=marker, now=0.0)

        assert result is None

    def test_returns_none_when_payload_is_not_a_dict(self, tmp_path: Path) -> None:
        marker = tmp_path / "research-marker.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        # A list is valid JSON but not a dict — reader must refuse.
        marker.write_text('["cond-phase-a-baseline-qwen-001"]')

        result = research_marker.read_research_marker(marker_path=marker, now=0.0)

        assert result is None

    def test_returns_none_when_condition_id_key_missing(self, tmp_path: Path) -> None:
        marker = tmp_path / "research-marker.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"written_at": "2026-04-14T12:00:00+00:00"}))

        result = research_marker.read_research_marker(marker_path=marker, now=0.0)

        assert result is None

    def test_returns_none_when_condition_id_is_null(self, tmp_path: Path) -> None:
        marker = tmp_path / "research-marker.json"
        _write_marker(marker, None)

        result = research_marker.read_research_marker(marker_path=marker, now=0.0)

        assert result is None

    def test_returns_none_when_condition_id_is_empty_string(self, tmp_path: Path) -> None:
        marker = tmp_path / "research-marker.json"
        _write_marker(marker, "")

        result = research_marker.read_research_marker(marker_path=marker, now=0.0)

        assert result is None

    def test_returns_none_when_condition_id_is_non_string(self, tmp_path: Path) -> None:
        marker = tmp_path / "research-marker.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"condition_id": 42, "written_at": "x"}))

        result = research_marker.read_research_marker(marker_path=marker, now=0.0)

        assert result is None


class TestCacheBehavior:
    def test_clear_cache_forces_reread_within_ttl(self, tmp_path: Path) -> None:
        marker = tmp_path / "research-marker.json"
        _write_marker(marker, "cond-alpha")

        first = research_marker.read_research_marker(marker_path=marker, now=0.0)
        _write_marker(marker, "cond-beta")
        # Still within TTL — would normally cache-hit.
        research_marker.clear_cache()
        second = research_marker.read_research_marker(marker_path=marker, now=1.0)

        assert first == "cond-alpha"
        assert second == "cond-beta"

    def test_cache_is_keyed_by_path(self, tmp_path: Path) -> None:
        """Two distinct marker paths must not cross-contaminate the cache."""
        marker_a = tmp_path / "a" / "research-marker.json"
        marker_b = tmp_path / "b" / "research-marker.json"
        _write_marker(marker_a, "cond-alpha")
        _write_marker(marker_b, "cond-beta")

        result_a = research_marker.read_research_marker(marker_path=marker_a, now=0.0)
        result_b = research_marker.read_research_marker(marker_path=marker_b, now=0.0)
        # Read both again within TTL — each path must still resolve to its own value.
        result_a2 = research_marker.read_research_marker(marker_path=marker_a, now=1.0)
        result_b2 = research_marker.read_research_marker(marker_path=marker_b, now=1.0)

        assert result_a == "cond-alpha"
        assert result_b == "cond-beta"
        assert result_a2 == "cond-alpha"
        assert result_b2 == "cond-beta"

    def test_cache_absorbs_transient_filesystem_error(self, tmp_path: Path) -> None:
        """If the marker file becomes absent after a successful read, the
        cached value should continue to be returned until TTL elapses.
        This matches the original ``director_loop.py`` behavior where a
        transient hiccup in /dev/shm does not momentarily drop the
        condition tag from in-flight reactions.
        """
        marker = tmp_path / "research-marker.json"
        _write_marker(marker, "cond-alpha")

        first = research_marker.read_research_marker(marker_path=marker, now=0.0)
        marker.unlink()  # simulate file becoming unavailable
        second = research_marker.read_research_marker(marker_path=marker, now=1.0)

        assert first == "cond-alpha"
        assert second == "cond-alpha"  # cached value still returned

    def test_none_is_also_cached(self, tmp_path: Path) -> None:
        """If the marker file is absent at first read, the ``None`` result
        is cached for TTL — we don't keep trying filesystem reads every
        call. Matches the original inlined helper's behavior.
        """
        marker = tmp_path / "research-marker.json"
        # Marker absent at first read
        first = research_marker.read_research_marker(marker_path=marker, now=0.0)
        # Write a marker BEFORE TTL elapses — should still see None (cached)
        _write_marker(marker, "cond-alpha")
        second = research_marker.read_research_marker(marker_path=marker, now=1.0)
        # After TTL elapses, should see the new value
        third = research_marker.read_research_marker(
            marker_path=marker, now=research_marker.CACHE_TTL_S + 0.1
        )

        assert first is None
        assert second is None
        assert third == "cond-alpha"


class TestModuleConstants:
    def test_canonical_marker_path_is_shm(self) -> None:
        """Pin the canonical path so any accidental relocation is caught."""
        expected = Path("/dev/shm/hapax-compositor/research-marker.json")
        assert expected == research_marker.RESEARCH_MARKER_PATH

    def test_cache_ttl_matches_director_loop_inlined_version(self) -> None:
        """Pin the 5-second TTL so it matches the behavior of the original
        inlined ``_read_research_marker()`` in ``director_loop.py``. If the
        TTL drifts, livestream reactions and voice grounding DVs start
        seeing the active condition on different cadences.
        """
        assert research_marker.CACHE_TTL_S == 5.0
