"""Integration test for the LRR Phase 9 §3.1 chat-monitor wiring.

Loads ``scripts/chat-monitor.py`` as a module (like the drill-harness
tests do) and exercises the structural-signals publish path without
spinning up the real YouTube chat downloader.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def chat_monitor_mod():
    if "chat_monitor_script" in sys.modules:
        return sys.modules["chat_monitor_script"]
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "chat-monitor.py"
    spec = importlib.util.spec_from_file_location("chat_monitor_script", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["chat_monitor_script"] = module
    spec.loader.exec_module(module)
    return module


class TestPublishStructuralSignals:
    def test_empty_window_does_not_write(
        self, chat_monitor_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        from agents.chat_monitor import sink as sink_mod

        target = tmp_path / "hapax-chat-signals.json"
        monkeypatch.setattr(sink_mod, "SHM_PATH", target)

        mon = chat_monitor_mod.ChatMonitor(video_id="dummy")
        # messages deque empty — publish should no-op
        mon._publish_structural_signals()
        assert not target.exists()

    def test_publishes_with_no_embedder(
        self, chat_monitor_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        from agents.chat_monitor import sink as sink_mod

        target = tmp_path / "hapax-chat-signals.json"
        monkeypatch.setattr(sink_mod, "SHM_PATH", target)
        # Force the embedder to return zero-vectors — avoids real HTTP.
        monkeypatch.setattr(
            chat_monitor_mod, "_batch_embedder", lambda texts: [[0.0] for _ in texts]
        )

        mon = chat_monitor_mod.ChatMonitor(video_id="dummy")
        for i in range(3):
            mon.messages.append(
                {
                    "text": f"hello world message {i}",
                    "author": f"user{i}",
                    "author_id": f"u{i}",
                    "timestamp": 1000.0 + i,
                    "type": "text_message",
                    "amount": 0,
                }
            )

        mon._publish_structural_signals()

        assert target.exists()
        payload = json.loads(target.read_text(encoding="utf-8"))
        assert payload["window_size"] == 3
        assert payload["participant_diversity"] == 1.0  # all unique authors
        assert payload["novelty_rate"] > 0
        # Zero-vector embedder → zero coherence + 1-cluster fallback
        assert payload["thread_count"] >= 1
        assert "ts" in payload

    def test_uses_last_50_messages_only(
        self, chat_monitor_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        from agents.chat_monitor import sink as sink_mod

        target = tmp_path / "hapax-chat-signals.json"
        monkeypatch.setattr(sink_mod, "SHM_PATH", target)
        monkeypatch.setattr(
            chat_monitor_mod, "_batch_embedder", lambda texts: [[0.0] for _ in texts]
        )

        mon = chat_monitor_mod.ChatMonitor(video_id="dummy")
        for i in range(120):
            mon.messages.append(
                {
                    "text": f"m{i}",
                    "author": f"u{i}",
                    "author_id": f"id{i}",
                    "timestamp": float(i),
                    "type": "text_message",
                    "amount": 0,
                }
            )

        mon._publish_structural_signals()

        payload = json.loads(target.read_text(encoding="utf-8"))
        assert payload["window_size"] == 50  # last 50 slice

    def test_publish_failure_is_isolated(
        self, chat_monitor_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """A raising embedder shouldn't propagate into the batch loop."""
        from agents.chat_monitor import sink as sink_mod

        target = tmp_path / "hapax-chat-signals.json"
        monkeypatch.setattr(sink_mod, "SHM_PATH", target)

        def boom(_texts):
            raise RuntimeError("nomic down")

        monkeypatch.setattr(chat_monitor_mod, "_batch_embedder", boom)

        mon = chat_monitor_mod.ChatMonitor(video_id="dummy")
        mon.messages.append(
            {
                "text": "hi there",
                "author": "a",
                "author_id": "aa",
                "timestamp": 1.0,
                "type": "text_message",
                "amount": 0,
            }
        )

        # Analyzer catches embedder exception internally and still publishes.
        mon._publish_structural_signals()
        assert target.exists()
        payload = json.loads(target.read_text(encoding="utf-8"))
        assert payload["window_size"] == 1
        assert payload["thread_count"] == 0  # embedder fell through
