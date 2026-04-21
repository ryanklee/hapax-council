"""FINDING-V chat-state sidecar — ChatSignalsAggregator.write_chat_state."""

from __future__ import annotations

import json
from pathlib import Path

from agents.studio_compositor.chat_queues import StructuralSignalQueue
from agents.studio_compositor.chat_signals import (
    DEFAULT_CHAT_STATE_PATH,
    ChatSignals,
    ChatSignalsAggregator,
)


def _make_aggregator(tmp_path: Path) -> ChatSignalsAggregator:
    return ChatSignalsAggregator(
        queue=StructuralSignalQueue(),
        output_path=tmp_path / "chat-signals.json",
        chat_state_path=tmp_path / "chat-state.json",
    )


def _make_signals(total: int, authors: int) -> ChatSignals:
    return ChatSignals(
        window_seconds=60.0,
        window_end_ts=1_700_000_000.0,
        message_count_60s=total,
        message_rate_per_min=float(total),
        unique_authors_60s=authors,
        high_value_queue_depth=0,
        chat_entropy=0.0,
        chat_novelty=0.0,
        audience_engagement=0.0,
    )


def test_default_chat_state_path_is_compositor_shm() -> None:
    assert Path("/dev/shm/hapax-compositor/chat-state.json") == DEFAULT_CHAT_STATE_PATH


def test_write_chat_state_emits_two_field_schema(tmp_path: Path) -> None:
    agg = _make_aggregator(tmp_path)
    agg.write_chat_state(_make_signals(total=12, authors=4))

    payload_path = tmp_path / "chat-state.json"
    assert payload_path.exists()
    payload = json.loads(payload_path.read_text())
    assert payload["total_messages"] == 12
    assert payload["unique_authors"] == 4
    assert "generated_at" in payload
    # Sidecar schema intentionally minimal — no tier rates, no entropy.
    assert set(payload) == {"generated_at", "total_messages", "unique_authors"}


def test_write_chat_state_atomic_no_tmp_sidecar(tmp_path: Path) -> None:
    agg = _make_aggregator(tmp_path)
    agg.write_chat_state(_make_signals(total=3, authors=2))

    leftover = list(tmp_path.glob(".chat-state.json.*.tmp"))
    assert leftover == []


def test_write_chat_state_and_write_shm_independent(tmp_path: Path) -> None:
    agg = _make_aggregator(tmp_path)
    signals = _make_signals(total=7, authors=3)
    agg.write_shm(signals)
    agg.write_chat_state(signals)

    sigs = json.loads((tmp_path / "chat-signals.json").read_text())
    state = json.loads((tmp_path / "chat-state.json").read_text())

    # chat-signals.json retains the full schema
    assert "message_count_60s" in sigs
    assert "chat_entropy" in sigs
    assert "audience_engagement" in sigs
    # chat-state.json is the projection only
    assert state["total_messages"] == sigs["message_count_60s"] == 7
    assert state["unique_authors"] == sigs["unique_authors_60s"] == 3
