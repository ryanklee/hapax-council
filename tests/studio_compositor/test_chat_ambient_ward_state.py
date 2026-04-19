"""Tests for ChatAmbientWard.state() — FINDING-V Phase 1.

The ward self-serves its state dict by reading
/dev/shm/hapax-chat-signals.json. These tests monkeypatch the path so
no SHM/tmpfs dependency leaks into the test suite.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from agents.studio_compositor import chat_ambient_ward
from agents.studio_compositor.chat_ambient_ward import ChatAmbientWard


@pytest.fixture
def signals_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "hapax-chat-signals.json"
    monkeypatch.setattr(chat_ambient_ward, "DEFAULT_CHAT_SIGNALS_PATH", target)
    return target


def _write_payload(path: Path, payload: dict, mtime_delta_s: float = 0.0) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")
    if mtime_delta_s:
        stamp = time.time() - mtime_delta_s
        import os

        os.utime(path, (stamp, stamp))


def test_state_filters_to_counter_keys(signals_path: Path):
    payload = {
        "t4_plus_rate_per_min": 2.5,
        "unique_t4_plus_authors_60s": 4,
        "t5_rate_per_min": 1.0,
        "t6_rate_per_min": 0.5,
        "message_rate_per_min": 12.0,
        "audience_engagement": 0.7,
        # Upstream additions the aggregator may ship later — must be ignored.
        "future_keyword_rate": 9.9,
        "some_other_metric": "this_string_would_leak_if_not_filtered",
    }
    _write_payload(signals_path, payload)

    ward = ChatAmbientWard()
    state = ward.state()

    assert set(state.keys()) == {
        "t4_plus_rate_per_min",
        "unique_t4_plus_authors_60s",
        "t5_rate_per_min",
        "t6_rate_per_min",
        "message_rate_per_min",
        "audience_engagement",
    }
    assert state["t4_plus_rate_per_min"] == 2.5
    assert "future_keyword_rate" not in state
    assert "some_other_metric" not in state


def test_state_missing_file_returns_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(chat_ambient_ward, "DEFAULT_CHAT_SIGNALS_PATH", tmp_path / "nope.json")
    ward = ChatAmbientWard()
    assert ward.state() == {}


def test_state_malformed_json_returns_last_cache(signals_path: Path):
    ward = ChatAmbientWard()

    _write_payload(signals_path, {"t4_plus_rate_per_min": 3.0})
    assert ward.state()["t4_plus_rate_per_min"] == 3.0

    # Write invalid JSON on top — should fall back to cache.
    signals_path.write_text("{invalid", encoding="utf-8")
    assert ward.state()["t4_plus_rate_per_min"] == 3.0


def test_state_stale_mtime_drops_to_empty(signals_path: Path):
    _write_payload(
        signals_path,
        {"t4_plus_rate_per_min": 5.0, "unique_t4_plus_authors_60s": 2},
        mtime_delta_s=130.0,  # older than 120 s freshness window
    )
    ward = ChatAmbientWard()
    assert ward.state() == {}


def test_state_non_dict_payload_returns_last_cache(signals_path: Path):
    ward = ChatAmbientWard()

    _write_payload(signals_path, {"t4_plus_rate_per_min": 1.1})
    ward.state()

    signals_path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert ward.state() == {"t4_plus_rate_per_min": 1.1}


def test_state_returns_copy_not_cache_reference(signals_path: Path):
    _write_payload(signals_path, {"t4_plus_rate_per_min": 2.0})
    ward = ChatAmbientWard()
    a = ward.state()
    a["poisoned"] = 999
    b = ward.state()
    assert "poisoned" not in b


def test_state_never_leaks_string_values(signals_path: Path):
    # A malicious or buggy upstream shipping a string under a counter key
    # must not reach render_content. state() passes the raw value through
    # but the ward's _coerce_counters guard raises downstream.
    _write_payload(
        signals_path,
        {"t4_plus_rate_per_min": "NOT_A_NUMBER"},
    )
    ward = ChatAmbientWard()
    state = ward.state()
    # state() itself is permissive — it's a pass-through of filtered keys.
    # The _coerce_counters guard in render_content is what rejects.
    with pytest.raises(TypeError, match="must be numeric"):
        ward._coerce_counters(state)
