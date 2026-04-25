"""Tests for shared/chat_url_pipeline.py — Phase 2 of YT bundle (#144).

Verifies:
  - URL extraction from a chat message → AttributionEntry per URL
  - Classifier routing (github / youtube / wikipedia / etc.)
  - Author-ID hashing privacy invariant (raw ID never appears in source)
  - Empty author ID → "anon" hash (not empty source)
  - Per-process dedup: same URL twice in successive messages → one entry
  - Empty / no-URL messages produce no entries
  - Writer failure is exception-safe (doesn't break the chat loop)
  - Source format ``chat:<hash>`` exactly
  - Phase 6c-ii.B.1: engine wire-in tags AttributionEntry metadata
    with ``operator_attributed`` when the chat-author engine asserts
    operator identity (positive-only, additive — does not gate or
    drop entries)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.hapax_daimonion.chat_author_is_operator_engine import (
    ChatAuthorIsOperatorEngine,
)
from shared.chat_url_pipeline import ChatUrlPipeline, hash_author_id


@pytest.fixture
def pipeline(tmp_path: Path) -> ChatUrlPipeline:
    return ChatUrlPipeline(root=tmp_path / "attribution")


# ── hash_author_id ────────────────────────────────────────────────────


class TestHashAuthor:
    def test_empty_returns_anon(self) -> None:
        assert hash_author_id("") == "anon"

    def test_consistent_hashing(self) -> None:
        assert hash_author_id("user-123") == hash_author_id("user-123")

    def test_different_authors_different_hashes(self) -> None:
        assert hash_author_id("alice") != hash_author_id("bob")

    def test_eight_char_prefix(self) -> None:
        assert len(hash_author_id("any-author-here")) == 8

    def test_raw_author_not_in_hash(self) -> None:
        """Privacy invariant: raw author id never leaks via the hash."""
        raw = "alice@example.com"
        assert raw not in hash_author_id(raw)


# ── process_message — URL extraction ──────────────────────────────────


class TestUrlExtraction:
    def test_no_urls_in_message_writes_nothing(
        self, pipeline: ChatUrlPipeline, tmp_path: Path
    ) -> None:
        count = pipeline.process_message("hello world no urls here", author_id="alice")
        assert count == 0

    def test_empty_message_writes_nothing(self, pipeline: ChatUrlPipeline) -> None:
        assert pipeline.process_message("", author_id="alice") == 0

    def test_single_url_writes_one_entry(self, pipeline: ChatUrlPipeline, tmp_path: Path) -> None:
        count = pipeline.process_message(
            "check this out https://github.com/example/repo", author_id="alice"
        )
        assert count == 1
        # JSONL file at root/<kind>.jsonl
        assert (tmp_path / "attribution" / "github.jsonl").exists()

    def test_multiple_urls_all_written(self, pipeline: ChatUrlPipeline) -> None:
        text = (
            "thoughts: https://github.com/foo/bar and "
            "https://en.wikipedia.org/wiki/Cybernetics and "
            "https://youtu.be/abc123"
        )
        count = pipeline.process_message(text, author_id="alice")
        assert count == 3


# ── Classification routing ────────────────────────────────────────────


class TestClassificationRouting:
    @pytest.mark.parametrize(
        "url,expected_kind",
        [
            ("https://github.com/foo/bar", "github"),
            ("https://youtu.be/abc", "youtube"),
            ("https://en.wikipedia.org/wiki/X", "wikipedia"),
            ("https://twitter.com/handle/status/123", "tweet"),
            ("https://doi.org/10.1234/abc", "doi"),
            ("https://bandcamp.com/album/x", "album-ref"),
            ("https://arxiv.org/abs/2401.12345", "citation"),
            ("https://random-blog.example.com/post", "other"),
        ],
    )
    def test_url_routes_to_correct_kind(
        self, pipeline: ChatUrlPipeline, tmp_path: Path, url: str, expected_kind: str
    ) -> None:
        pipeline.process_message(f"see {url}", author_id="alice")
        path = tmp_path / "attribution" / f"{expected_kind}.jsonl"
        assert path.exists(), f"file for {expected_kind!r} missing at {path}"


# ── Privacy invariants ────────────────────────────────────────────────


class TestPrivacy:
    def test_source_uses_hashed_author_not_raw(
        self, pipeline: ChatUrlPipeline, tmp_path: Path
    ) -> None:
        raw_author = "alice@example.com"
        pipeline.process_message("https://github.com/foo/bar", author_id=raw_author)
        path = tmp_path / "attribution" / "github.jsonl"
        content = path.read_text()
        assert raw_author not in content, "raw author leaked into attribution file"
        records = [json.loads(line) for line in content.strip().splitlines()]
        assert any(r["source"].startswith("chat:") for r in records)

    def test_anon_author_renders_as_chat_anon(
        self, pipeline: ChatUrlPipeline, tmp_path: Path
    ) -> None:
        pipeline.process_message("https://github.com/foo/bar", author_id="")
        path = tmp_path / "attribution" / "github.jsonl"
        records = [json.loads(line) for line in path.read_text().strip().splitlines()]
        assert any(r["source"] == "chat:anon" for r in records)


# ── Dedup ─────────────────────────────────────────────────────────────


class TestDedup:
    def test_same_url_twice_writes_once(self, pipeline: ChatUrlPipeline) -> None:
        url = "https://github.com/foo/bar"
        first = pipeline.process_message(f"check {url}", author_id="alice")
        second = pipeline.process_message(f"again {url}", author_id="bob")
        assert first == 1
        assert second == 0  # dedup'd

    def test_different_urls_both_written(self, pipeline: ChatUrlPipeline) -> None:
        first = pipeline.process_message("https://github.com/a/b", author_id="alice")
        second = pipeline.process_message("https://github.com/c/d", author_id="alice")
        assert first == 1
        assert second == 1


# ── Defensive ─────────────────────────────────────────────────────────


class TestDefensive:
    def test_writer_failure_does_not_propagate(self, pipeline: ChatUrlPipeline) -> None:
        """A writer exception is logged at DEBUG; pipeline returns
        partial count. The chat-monitor must never crash on attribution
        write failure."""

        class _Boom:
            def append(self, entry):
                raise RuntimeError("writer broken")

        pipeline._writer = _Boom()  # type: ignore[assignment]
        count = pipeline.process_message("https://github.com/foo/bar", author_id="alice")
        assert count == 0  # nothing written but no exception

    def test_invalid_url_classified_as_other(
        self, pipeline: ChatUrlPipeline, tmp_path: Path
    ) -> None:
        # Malformed-looking URL still extracts as `https://...`; classifier
        # returns "other" for unknown hosts.
        pipeline.process_message("https://random-host-xyz.example.io/path", author_id="alice")
        assert (tmp_path / "attribution" / "other.jsonl").exists()


# ── End-to-end fixture (plan §3.2 exit criterion) ─────────────────────


# ── Phase 6c-ii.B.1: ChatAuthorIsOperatorEngine wire-in ───────────────


class TestOperatorAttributionWireIn:
    """Engine wire-in is purely ADDITIVE — no existing entries are
    dropped or modified except for an additional ``operator_attributed``
    metadata key when the engine asserts operator identity.

    The engine is optional. When ``None`` (default), pipeline behaves
    exactly as before (backward compat). When wired, every URL-bearing
    message ticks the engine with ``handle_match`` derived from the
    operator-handles set + ``persona_match=None``."""

    def test_no_engine_no_operator_attributed_metadata(
        self, pipeline: ChatUrlPipeline, tmp_path: Path
    ) -> None:
        """Default construction: engine is None; entries have no
        ``operator_attributed`` metadata."""
        pipeline.process_message("https://github.com/foo/bar", author_id="alice")
        path = tmp_path / "attribution" / "github.jsonl"
        records = [json.loads(line) for line in path.read_text().strip().splitlines()]
        assert all("operator_attributed" not in r["metadata"] for r in records)

    def test_engine_asserted_tags_operator_attributed_true(self, tmp_path: Path) -> None:
        """When the engine asserts (handle in operator_handles set
        AND posterior ≥ narration floor), the metadata contains
        ``operator_attributed: True``."""
        # High prior ensures asserted() is True immediately (skips
        # k_enter ticks for test ergonomics; production pipelines
        # use the conservative default prior).
        engine = ChatAuthorIsOperatorEngine(prior=0.95)
        pipeline = ChatUrlPipeline(
            root=tmp_path / "attribution",
            chat_author_engine=engine,
            operator_handles=frozenset({"oudepode"}),
        )
        pipeline.process_message("https://github.com/foo/bar", author_id="oudepode")
        path = tmp_path / "attribution" / "github.jsonl"
        records = [json.loads(line) for line in path.read_text().strip().splitlines()]
        assert any(r["metadata"].get("operator_attributed") is True for r in records)

    def test_engine_unasserted_no_operator_attributed_tag(self, tmp_path: Path) -> None:
        """Author handle not in operator_handles + low prior → engine
        does NOT assert → no metadata tag."""
        engine = ChatAuthorIsOperatorEngine(prior=0.05)
        pipeline = ChatUrlPipeline(
            root=tmp_path / "attribution",
            chat_author_engine=engine,
            operator_handles=frozenset({"oudepode"}),
        )
        pipeline.process_message("https://github.com/foo/bar", author_id="random_viewer")
        path = tmp_path / "attribution" / "github.jsonl"
        records = [json.loads(line) for line in path.read_text().strip().splitlines()]
        assert all(r["metadata"].get("operator_attributed") is not True for r in records)

    def test_engine_ticks_with_handle_match_True_for_known_handle(self, tmp_path: Path) -> None:
        """Wiring contract: process_message ticks the engine with
        ``handle_match=True`` when author_id is in operator_handles
        (the engine's posterior is what asserts; we just verify the
        tick happened by observing posterior change with a sequence)."""
        engine = ChatAuthorIsOperatorEngine(prior=0.05)
        pipeline = ChatUrlPipeline(
            root=tmp_path / "attribution",
            chat_author_engine=engine,
            operator_handles=frozenset({"oudepode"}),
        )
        prior_post = engine.posterior
        pipeline.process_message("https://github.com/foo/bar", author_id="oudepode")
        # Posterior must have moved up after a positive handle_match
        # tick — even from prior 0.05, one tick of LR=950 lifts it.
        assert engine.posterior > prior_post

    def test_engine_does_not_tick_when_no_urls(self, tmp_path: Path) -> None:
        """No-URL messages don't advance the engine — engine is
        per-attribution-event, not per-incoming-message. Keeps the
        engine's hysteresis aligned with the attribution surface
        (consumer of the posterior)."""
        engine = ChatAuthorIsOperatorEngine(prior=0.05)
        pipeline = ChatUrlPipeline(
            root=tmp_path / "attribution",
            chat_author_engine=engine,
            operator_handles=frozenset({"oudepode"}),
        )
        prior_post = engine.posterior
        pipeline.process_message("just chatting, no urls", author_id="oudepode")
        assert engine.posterior == prior_post

    def test_engine_None_explicit_passthrough(self, tmp_path: Path) -> None:
        """Explicitly passing ``chat_author_engine=None`` is the same
        as not passing (default). Pipeline ignores the engine entirely."""
        pipeline = ChatUrlPipeline(
            root=tmp_path / "attribution",
            chat_author_engine=None,
        )
        pipeline.process_message("https://github.com/foo/bar", author_id="oudepode")
        path = tmp_path / "attribution" / "github.jsonl"
        records = [json.loads(line) for line in path.read_text().strip().splitlines()]
        assert all("operator_attributed" not in r["metadata"] for r in records)

    def test_engine_does_not_tag_when_not_asserted_for_known_handle(self, tmp_path: Path) -> None:
        """A known operator handle on a single-tick low-prior engine
        does NOT assert — the engine's threshold check is what matters,
        not the handle membership alone. Pin this so the wire-in
        doesn't accidentally substitute handle membership for the
        engine's calibrated decision."""
        # Default prior (0.05) + default threshold (0.85). A single
        # handle_match tick raises posterior to ~0.95+ (LR=950), so
        # asserted() WILL be True. To produce a known-handle without
        # assertion, use a much weaker handle LR via a custom engine
        # — but that's out of scope here. Instead verify the behavior
        # we care about: a non-asserting engine produces no tag.
        from agents.hapax_daimonion.chat_author_is_operator_engine import (
            AUTHENTICATED_HANDLE_SIGNAL,
            CLAIM_NAME,
        )
        from shared.claim import LRDerivation

        weak_handle_lr = LRDerivation(
            signal_name=AUTHENTICATED_HANDLE_SIGNAL,
            claim_name=CLAIM_NAME,
            source_category="expert_elicitation_shelf",
            p_true_given_h1=0.5,
            p_true_given_h0=0.49,  # near-1 LR; barely moves posterior
            positive_only=True,
            estimation_reference="test calibration",
        )
        engine = ChatAuthorIsOperatorEngine(prior=0.05, handle_lr=weak_handle_lr)
        pipeline = ChatUrlPipeline(
            root=tmp_path / "attribution",
            chat_author_engine=engine,
            operator_handles=frozenset({"oudepode"}),
        )
        pipeline.process_message("https://github.com/foo/bar", author_id="oudepode")
        path = tmp_path / "attribution" / "github.jsonl"
        records = [json.loads(line) for line in path.read_text().strip().splitlines()]
        # Posterior was 0.05 → ~0.052 (weak LR); below 0.85 threshold.
        assert all(r["metadata"].get("operator_attributed") is not True for r in records)


class TestEndToEnd:
    def test_ten_message_fixture_per_kind_counts(
        self, pipeline: ChatUrlPipeline, tmp_path: Path
    ) -> None:
        """Plan §3.2 fixture: feed 10 chat messages with mix of URLs;
        assert per-kind sections accumulate.
        """
        messages = [
            ("alice", "check https://github.com/repo/one"),
            ("bob", "and https://en.wikipedia.org/wiki/Topic"),
            ("alice", "no urls here"),
            ("carol", "https://youtu.be/abc123"),
            ("bob", "https://github.com/repo/two"),
            ("alice", "again https://github.com/repo/one"),  # dedup
            ("dan", "https://twitter.com/handle/status/4"),
            ("carol", "https://arxiv.org/abs/2401.12345"),
            ("alice", "another wikipedia https://en.wikipedia.org/wiki/Other"),
            ("eve", "https://random-blog.example.com/post"),
        ]
        total = 0
        for author, msg in messages:
            total += pipeline.process_message(msg, author_id=author)
        # 9 URLs across 10 messages, one dedup → 8 written.
        assert total == 8
        # Per-kind JSONL files:
        for kind in ("github", "wikipedia", "youtube", "tweet", "citation", "other"):
            path = tmp_path / "attribution" / f"{kind}.jsonl"
            assert path.exists(), f"file for {kind} missing"
