"""Tests for operator-shared YouTube link capture (task #144)."""

from __future__ import annotations

import json
from pathlib import Path

from agents.studio_compositor import yt_shared_links
from agents.studio_compositor.yt_shared_links import (
    append_shared_link,
    load_cursor,
    parse_link_command,
    queue_link_for_next_broadcast,
    save_cursor,
    tail_shared_links,
)


class TestParseLinkCommand:
    def test_empty_is_none(self) -> None:
        assert parse_link_command("") is None
        assert parse_link_command("   ") is None

    def test_non_link_text_is_none(self) -> None:
        assert parse_link_command("hello there") is None
        assert parse_link_command("link without a url") is None

    def test_simple_link(self) -> None:
        assert parse_link_command("link https://youtu.be/abc123") == "https://youtu.be/abc123"

    def test_link_with_leading_whitespace(self) -> None:
        assert parse_link_command("  link  https://example.com/foo") == "https://example.com/foo"

    def test_link_with_trailing_commentary(self) -> None:
        # Regex greedily matches the URL up to the next whitespace.
        result = parse_link_command("link https://youtu.be/abc123 good track")
        assert result == "https://youtu.be/abc123"

    def test_case_insensitive_prefix(self) -> None:
        assert parse_link_command("LINK https://example.com") == "https://example.com"

    def test_http_also_accepted(self) -> None:
        assert parse_link_command("link http://example.com/path") == "http://example.com/path"

    def test_no_url_in_link_command_is_none(self) -> None:
        # `link bare-word` has no URL → None.
        assert parse_link_command("link foo bar") is None


class TestAppendAndTail:
    def test_append_and_tail_roundtrip(self, tmp_path: Path) -> None:
        target = tmp_path / "yt-shared-links.jsonl"
        append_shared_link("https://youtu.be/aaa", ts=100.0, path=target)
        append_shared_link("https://youtu.be/bbb", ts=200.0, path=target)

        records = list(tail_shared_links(since_ts=0.0, path=target))
        assert len(records) == 2
        assert records[0]["url"] == "https://youtu.be/aaa"
        assert records[1]["url"] == "https://youtu.be/bbb"
        assert records[0]["source"] == "sidechat"

    def test_tail_respects_since_ts(self, tmp_path: Path) -> None:
        target = tmp_path / "yt-shared-links.jsonl"
        append_shared_link("https://a/", ts=100.0, path=target)
        append_shared_link("https://b/", ts=200.0, path=target)
        append_shared_link("https://c/", ts=300.0, path=target)

        recent = list(tail_shared_links(since_ts=150.0, path=target))
        assert [r["url"] for r in recent] == ["https://b/", "https://c/"]

    def test_tail_skips_malformed_lines(self, tmp_path: Path) -> None:
        target = tmp_path / "yt-shared-links.jsonl"
        target.write_text(
            '{"ts": 1.0, "url": "https://a/", "source": "sidechat"}\n'
            "this is not json\n"
            '{"ts": 2.0, "url": "https://b/", "source": "sidechat"}\n'
        )
        records = list(tail_shared_links(since_ts=0.0, path=target))
        urls = [r["url"] for r in records]
        assert urls == ["https://a/", "https://b/"]

    def test_append_rejects_empty_url(self, tmp_path: Path) -> None:
        target = tmp_path / "yt-shared-links.jsonl"
        try:
            append_shared_link("", path=target)
        except ValueError:
            return
        raise AssertionError("expected ValueError for empty url")


class TestCursor:
    def test_load_missing_is_zero(self, tmp_path: Path) -> None:
        assert load_cursor(path=tmp_path / "missing.txt") == 0.0

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        cursor = tmp_path / "cursor.txt"
        save_cursor(42.5, path=cursor)
        assert abs(load_cursor(path=cursor) - 42.5) < 1e-9


class TestQueue:
    def test_queue_append_roundtrip(self, tmp_path: Path) -> None:
        queue = tmp_path / "yt-queue.jsonl"
        record = {"ts": 10.0, "url": "https://youtu.be/x", "source": "sidechat"}
        queue_link_for_next_broadcast(record, path=queue)
        assert queue.exists()
        payload = json.loads(queue.read_text().splitlines()[0])
        assert payload == record


class TestSyncSharedLinks:
    """Integration tests for sync_shared_links_once."""

    def test_no_records_noop(self, tmp_path: Path, monkeypatch) -> None:
        from agents.studio_compositor import youtube_description_syncer as sync

        monkeypatch.setattr(yt_shared_links, "YT_LINKS_CURSOR_PATH", tmp_path / "cursor.txt")
        result = sync.sync_shared_links_once(
            video_id="vid-001",
            links_reader=lambda since_ts=0.0: iter([]),
            updater=lambda *a, **kw: True,
            description_reader=lambda vid: "",
        )
        assert result == 0

    def test_appends_to_live_description(self, tmp_path: Path) -> None:
        from agents.studio_compositor import youtube_description_syncer as sync

        records = [
            {"ts": 100.0, "url": "https://youtu.be/a", "source": "sidechat"},
            {"ts": 200.0, "url": "https://youtu.be/b", "source": "sidechat"},
        ]
        sent: list[tuple[str, str]] = []
        saved_ts: list[float] = []

        result = sync.sync_shared_links_once(
            video_id="vid-001",
            links_reader=lambda since_ts=0.0: iter(records),
            updater=lambda vid, desc, *, dry_run=False: sent.append((vid, desc)) or True,
            description_reader=lambda vid: "Existing description.\n",
            cursor_loader=lambda: 0.0,
            cursor_saver=lambda ts: saved_ts.append(ts),
            queue_writer=lambda rec: (_ for _ in ()).throw(
                AssertionError("should not queue when updater succeeds")
            ),
        )

        assert result == 2
        assert len(sent) == 1
        _, desc = sent[0]
        assert "https://youtu.be/a" in desc
        assert "https://youtu.be/b" in desc
        assert "Existing description." in desc
        # Cursor advanced to the most-recent record's ts.
        assert saved_ts[-1] == 200.0

    def test_queues_when_no_video_id(self, tmp_path: Path, monkeypatch) -> None:
        from agents.studio_compositor import youtube_description_syncer as sync

        monkeypatch.delenv("HAPAX_YOUTUBE_VIDEO_ID", raising=False)

        records = [{"ts": 10.0, "url": "https://x/", "source": "sidechat"}]
        queued: list[dict] = []

        result = sync.sync_shared_links_once(
            links_reader=lambda since_ts=0.0: iter(records),
            updater=lambda *a, **kw: (_ for _ in ()).throw(
                AssertionError("should not update without video_id")
            ),
            cursor_loader=lambda: 0.0,
            cursor_saver=lambda ts: None,
            queue_writer=lambda rec: queued.append(rec),
        )

        assert result == 1
        assert queued == records

    def test_queues_when_updater_declines(self, tmp_path: Path) -> None:
        from agents.studio_compositor import youtube_description_syncer as sync

        records = [{"ts": 10.0, "url": "https://x/", "source": "sidechat"}]
        queued: list[dict] = []

        result = sync.sync_shared_links_once(
            video_id="vid-001",
            links_reader=lambda since_ts=0.0: iter(records),
            updater=lambda *a, **kw: False,
            description_reader=lambda vid: "",
            cursor_loader=lambda: 0.0,
            cursor_saver=lambda ts: None,
            queue_writer=lambda rec: queued.append(rec),
        )

        assert result == 1
        assert queued == records


class TestDescriptionComposer:
    def test_compose_initial_block(self) -> None:
        from agents.studio_compositor.youtube_description_syncer import (
            _append_links_to_description,
        )

        out = _append_links_to_description("Head.", ["https://a/"])
        assert "Head." in out
        assert "--- Links ---" in out
        assert "https://a/" in out

    def test_dedups_existing_links(self) -> None:
        from agents.studio_compositor.youtube_description_syncer import (
            _append_links_to_description,
        )

        existing = "Head.\n--- Links ---\nhttps://a/\n"
        out = _append_links_to_description(existing, ["https://a/", "https://b/"])
        # Existing https://a/ should appear only once.
        assert out.count("https://a/") == 1
        assert "https://b/" in out

    def test_preserves_head_text(self) -> None:
        from agents.studio_compositor.youtube_description_syncer import (
            _append_links_to_description,
        )

        existing = "Stream description.\n\nSupports:\n- X\n"
        out = _append_links_to_description(existing, ["https://a/"])
        assert "Stream description." in out
        assert "Supports:" in out
