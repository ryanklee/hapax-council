"""Tests for agents/studio_compositor/chat_signals.py — LRR Phase 9 item 3."""

from __future__ import annotations

import json
from pathlib import Path

import pytest  # noqa: TC002 — runtime dep for fixtures

from agents.studio_compositor.chat_classifier import ChatTier, Classification
from agents.studio_compositor.chat_queues import (
    ChatMessage,
    StructuralSignalQueue,
    fake_embedder,
)
from agents.studio_compositor.chat_signals import (
    DEFAULT_CHAT_SIGNALS_PATH,
    ChatSignalsAggregator,
    compute_audience_engagement,
)


def _t4(
    text: str, *, ts: float = 1000.0, handle: str = "user", with_embedding: bool = False
) -> ChatMessage:
    embedding = tuple(fake_embedder(text)) if with_embedding else None
    return ChatMessage(
        text=text,
        author_handle=handle,
        ts=ts,
        classification=Classification(
            tier=ChatTier.T4_STRUCTURAL_SIGNAL, reason="test", confidence=0.5
        ),
        embedding=embedding,
    )


class TestComputeAudienceEngagement:
    def test_zero_traffic_is_low(self) -> None:
        result = compute_audience_engagement(
            message_rate_per_min=0.0,
            chat_entropy=0.0,
            chat_novelty=0.0,
            unique_authors_60s=0,
            high_value_queue_depth=0,
        )
        assert 0.0 <= result <= 0.2

    def test_high_traffic_high_diversity_is_high(self) -> None:
        result = compute_audience_engagement(
            message_rate_per_min=50.0,
            chat_entropy=3.0,
            chat_novelty=0.9,
            unique_authors_60s=30,
            high_value_queue_depth=2,
        )
        assert result >= 0.9

    def test_high_value_bonus_fires(self) -> None:
        without = compute_audience_engagement(
            message_rate_per_min=5.0,
            chat_entropy=1.0,
            chat_novelty=0.2,
            unique_authors_60s=3,
            high_value_queue_depth=0,
        )
        with_hv = compute_audience_engagement(
            message_rate_per_min=5.0,
            chat_entropy=1.0,
            chat_novelty=0.2,
            unique_authors_60s=3,
            high_value_queue_depth=1,
        )
        assert with_hv > without

    def test_result_clamped_to_unit_interval(self) -> None:
        # Intentionally out-of-range novelty still produces [0,1] output
        result = compute_audience_engagement(
            message_rate_per_min=10000.0,
            chat_entropy=10.0,
            chat_novelty=5.0,  # should clamp to 1.0
            unique_authors_60s=100,
            high_value_queue_depth=1,
        )
        assert 0.0 <= result <= 1.0


class TestChatSignalsAggregator:
    def test_empty_queue_zero_signals(self, tmp_path: Path) -> None:
        queue = StructuralSignalQueue()
        agg = ChatSignalsAggregator(queue, output_path=tmp_path / "signals.json")
        signals = agg.compute_signals(now=1000.0)
        assert signals.message_count_60s == 0
        assert signals.message_rate_per_min == 0.0
        assert signals.unique_authors_60s == 0
        assert signals.chat_entropy == 0.0
        assert signals.chat_novelty == 0.0
        assert 0.0 <= signals.audience_engagement <= 1.0

    def test_message_count_and_rate(self, tmp_path: Path) -> None:
        queue = StructuralSignalQueue(window_seconds=60.0)
        for i in range(30):
            queue.push(_t4(f"msg {i}", ts=1000.0 + i))
        agg = ChatSignalsAggregator(queue, output_path=tmp_path / "signals.json")
        signals = agg.compute_signals(now=1030.0)
        assert signals.message_count_60s == 30
        # 30 messages in a 60s window → 30/min
        assert signals.message_rate_per_min == pytest.approx(30.0, abs=0.01)

    def test_unique_authors_counted(self, tmp_path: Path) -> None:
        queue = StructuralSignalQueue()
        for handle in ["alice", "bob", "alice", "carol", "bob"]:
            queue.push(_t4("msg", handle=handle, ts=1000.0))
        agg = ChatSignalsAggregator(queue, output_path=tmp_path / "signals.json")
        signals = agg.compute_signals(now=1001.0)
        assert signals.unique_authors_60s == 3

    def test_write_shm_atomic(self, tmp_path: Path) -> None:
        queue = StructuralSignalQueue()
        queue.push(_t4("hello", ts=1000.0))
        out = tmp_path / "signals.json"
        agg = ChatSignalsAggregator(queue, output_path=out)
        signals = agg.compute_signals(now=1001.0)
        agg.write_shm(signals)
        assert out.exists()
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["message_count_60s"] == 1
        assert "audience_engagement" in payload

    def test_write_shm_overwrites(self, tmp_path: Path) -> None:
        queue = StructuralSignalQueue()
        out = tmp_path / "signals.json"
        agg = ChatSignalsAggregator(queue, output_path=out)
        agg.write_shm(agg.compute_signals(now=1000.0))
        original = out.read_text(encoding="utf-8")

        queue.push(_t4("new", ts=1010.0))
        agg.write_shm(agg.compute_signals(now=1015.0))
        updated = out.read_text(encoding="utf-8")
        assert original != updated

    def test_signals_includes_high_value_depth(self, tmp_path: Path) -> None:
        queue = StructuralSignalQueue()
        agg = ChatSignalsAggregator(queue, output_path=tmp_path / "signals.json")
        signals = agg.compute_signals(now=1000.0, high_value_queue_depth=3)
        assert signals.high_value_queue_depth == 3

    def test_entropy_with_embeddings(self, tmp_path: Path) -> None:
        queue = StructuralSignalQueue()
        # 10 distinct texts → diverse vectors → positive entropy
        for i in range(10):
            queue.push(_t4(f"different text {i}", ts=1000.0 + i, with_embedding=True))
        agg = ChatSignalsAggregator(queue, output_path=tmp_path / "signals.json")
        signals = agg.compute_signals(now=1010.0)
        assert signals.chat_entropy > 0.0


class TestDefaultPath:
    def test_default_shm_path(self) -> None:
        assert str(DEFAULT_CHAT_SIGNALS_PATH).startswith("/dev/shm/")


# ── Task #123 — tier-disaggregated aggregates (ChatAmbientWard inputs) ────


class TestTierDisaggregatedAggregates:
    """Pin the four new fields added for the ChatAmbientWard (task #123).

    Each field is computed from classifier events recorded via
    ``ChatSignalsAggregator.record_classification``. The aggregator
    stores ``(ts, tier_int, author_hash)`` triples only — never text,
    never the raw handle. These tests verify each rate + unique count
    under a 60s rolling window, matching the ``t4_plus_rate_per_min``,
    ``unique_t4_plus_authors_60s``, ``t5_rate_per_min``, and
    ``t6_rate_per_min`` semantics in :class:`ChatSignals`.
    """

    def test_zero_classifications_yields_zero_tier_fields(self, tmp_path: Path) -> None:
        queue = StructuralSignalQueue()
        agg = ChatSignalsAggregator(queue, output_path=tmp_path / "signals.json")
        signals = agg.compute_signals(now=1000.0)
        assert signals.t4_plus_rate_per_min == 0.0
        assert signals.unique_t4_plus_authors_60s == 0
        assert signals.t5_rate_per_min == 0.0
        assert signals.t6_rate_per_min == 0.0

    def test_t4_plus_rate_per_min(self, tmp_path: Path) -> None:
        queue = StructuralSignalQueue()
        agg = ChatSignalsAggregator(queue, output_path=tmp_path / "signals.json")
        # 30 T4-tier events within 60s → 30/min
        for i in range(30):
            agg.record_classification(
                ts=1000.0 + i,
                tier=ChatTier.T4_STRUCTURAL_SIGNAL,
                author_handle=f"user-{i}",
            )
        signals = agg.compute_signals(now=1030.0)
        assert signals.t4_plus_rate_per_min == pytest.approx(30.0, abs=0.01)

    def test_t4_plus_rate_includes_t5_and_t6(self, tmp_path: Path) -> None:
        queue = StructuralSignalQueue()
        agg = ChatSignalsAggregator(queue, output_path=tmp_path / "signals.json")
        # 5 T4, 3 T5, 2 T6 = 10 T4+ events total
        for i in range(5):
            agg.record_classification(
                ts=1000.0 + i, tier=ChatTier.T4_STRUCTURAL_SIGNAL, author_handle=f"a{i}"
            )
        for i in range(3):
            agg.record_classification(
                ts=1000.0 + i, tier=ChatTier.T5_RESEARCH_RELEVANT, author_handle=f"b{i}"
            )
        for i in range(2):
            agg.record_classification(
                ts=1000.0 + i, tier=ChatTier.T6_HIGH_VALUE, author_handle=f"c{i}"
            )
        signals = agg.compute_signals(now=1005.0)
        assert signals.t4_plus_rate_per_min == pytest.approx(10.0, abs=0.01)

    def test_unique_t4_plus_authors_dedups(self, tmp_path: Path) -> None:
        queue = StructuralSignalQueue()
        agg = ChatSignalsAggregator(queue, output_path=tmp_path / "signals.json")
        # alice posts T4 twice + T5 once → still 1 unique author
        for ts in (1000.0, 1005.0):
            agg.record_classification(
                ts=ts, tier=ChatTier.T4_STRUCTURAL_SIGNAL, author_handle="alice"
            )
        agg.record_classification(
            ts=1010.0, tier=ChatTier.T5_RESEARCH_RELEVANT, author_handle="alice"
        )
        # bob + carol each post once → total 3 unique authors
        agg.record_classification(
            ts=1015.0, tier=ChatTier.T4_STRUCTURAL_SIGNAL, author_handle="bob"
        )
        agg.record_classification(ts=1020.0, tier=ChatTier.T6_HIGH_VALUE, author_handle="carol")
        signals = agg.compute_signals(now=1030.0)
        assert signals.unique_t4_plus_authors_60s == 3

    def test_t5_rate_isolates_research_relevant(self, tmp_path: Path) -> None:
        queue = StructuralSignalQueue()
        agg = ChatSignalsAggregator(queue, output_path=tmp_path / "signals.json")
        for i in range(6):
            agg.record_classification(
                ts=1000.0 + i, tier=ChatTier.T5_RESEARCH_RELEVANT, author_handle=f"r{i}"
            )
        # T4 and T6 should NOT contribute to t5_rate.
        for i in range(10):
            agg.record_classification(
                ts=1000.0 + i, tier=ChatTier.T4_STRUCTURAL_SIGNAL, author_handle=f"x{i}"
            )
        agg.record_classification(ts=1005.0, tier=ChatTier.T6_HIGH_VALUE, author_handle="cite")
        signals = agg.compute_signals(now=1010.0)
        # 6 T5 events in 60s window → 6.0/min
        assert signals.t5_rate_per_min == pytest.approx(6.0, abs=0.01)

    def test_t6_rate_isolates_high_value(self, tmp_path: Path) -> None:
        queue = StructuralSignalQueue()
        agg = ChatSignalsAggregator(queue, output_path=tmp_path / "signals.json")
        for i in range(3):
            agg.record_classification(
                ts=1000.0 + i, tier=ChatTier.T6_HIGH_VALUE, author_handle=f"c{i}"
            )
        signals = agg.compute_signals(now=1005.0)
        assert signals.t6_rate_per_min == pytest.approx(3.0, abs=0.01)
        # Sanity: T5 must remain at 0 when only T6 events were recorded.
        assert signals.t5_rate_per_min == 0.0

    def test_tier_events_prune_outside_window(self, tmp_path: Path) -> None:
        queue = StructuralSignalQueue()
        agg = ChatSignalsAggregator(queue, output_path=tmp_path / "signals.json")
        # Old event (>60s before 'now')
        agg.record_classification(
            ts=100.0, tier=ChatTier.T4_STRUCTURAL_SIGNAL, author_handle="ancient"
        )
        # Fresh event
        agg.record_classification(
            ts=990.0, tier=ChatTier.T4_STRUCTURAL_SIGNAL, author_handle="fresh"
        )
        signals = agg.compute_signals(now=1000.0)
        # Only "fresh" counts; the "ancient" event is pruned.
        assert signals.unique_t4_plus_authors_60s == 1
        assert signals.t4_plus_rate_per_min == pytest.approx(1.0, abs=0.01)

    def test_record_classification_stores_only_hash_not_raw_handle(self, tmp_path: Path) -> None:
        """The aggregator must never retain the raw author handle.

        After recording a classification, the internal ``_tier_events``
        list should contain the sha256-first-16-hex digest of the
        handle, never the handle string itself. This is the
        ``interpersonal_transparency`` axiom enforced at storage time.
        """
        queue = StructuralSignalQueue()
        agg = ChatSignalsAggregator(queue, output_path=tmp_path / "signals.json")
        agg.record_classification(
            ts=1000.0,
            tier=ChatTier.T4_STRUCTURAL_SIGNAL,
            author_handle="alice_sensitive_handle_9000",
        )
        # Internal state inspection is intentional — this is a
        # privacy-invariant test that verifies *nothing* stores the raw handle.
        for _ts, _tier_int, author_hash in agg._tier_events:  # noqa: SLF001
            assert "alice_sensitive_handle_9000" not in author_hash
            assert len(author_hash) == 16  # 16 hex chars per class docstring

    def test_signals_shm_payload_contains_tier_fields(self, tmp_path: Path) -> None:
        """Published JSON payload includes all four new fields."""
        queue = StructuralSignalQueue()
        agg = ChatSignalsAggregator(queue, output_path=tmp_path / "signals.json")
        agg.record_classification(
            ts=1000.0, tier=ChatTier.T5_RESEARCH_RELEVANT, author_handle="dave"
        )
        signals = agg.compute_signals(now=1001.0)
        agg.write_shm(signals)
        payload = json.loads((tmp_path / "signals.json").read_text(encoding="utf-8"))
        assert "t4_plus_rate_per_min" in payload
        assert "unique_t4_plus_authors_60s" in payload
        assert "t5_rate_per_min" in payload
        assert "t6_rate_per_min" in payload
