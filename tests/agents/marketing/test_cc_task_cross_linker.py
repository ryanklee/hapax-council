"""Tests for ``agents.marketing.cc_task_cross_linker``."""

from __future__ import annotations

from pathlib import Path

from agents.marketing.cc_task_cross_linker import (
    build_cross_link_map,
    discover_cc_task_for_slug,
    publish_cross_links,
    render_cross_link_index,
)


def _write_cc_task(dir_path: Path, task_id: str, body: str = "stub") -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / f"{task_id}.md").write_text(
        f"---\ntype: cc-task\ntask_id: {task_id}\nstatus: open\n---\n\n{body}\n"
    )


class TestDiscoverCcTaskForSlug:
    def test_matches_exact_slug_substring(self, tmp_path: Path) -> None:
        active_dir = tmp_path / "active"
        _write_cc_task(active_dir, "leverage-REFUSED-discord-community")
        result = discover_cc_task_for_slug("declined-discord-community", cc_tasks_dir=active_dir)
        assert result == "leverage-REFUSED-discord-community"

    def test_returns_none_when_no_match(self, tmp_path: Path) -> None:
        active_dir = tmp_path / "active"
        active_dir.mkdir()
        result = discover_cc_task_for_slug(
            "declined-bandcamp", cc_tasks_dir=active_dir, closed_dir=None
        )
        assert result is None

    def test_handles_missing_dir(self, tmp_path: Path) -> None:
        result = discover_cc_task_for_slug(
            "declined-bandcamp", cc_tasks_dir=tmp_path / "missing", closed_dir=None
        )
        assert result is None

    def test_finds_match_in_closed_dir(self, tmp_path: Path) -> None:
        # Should also search closed/ subdirectory if no active match
        closed_dir = tmp_path / "closed"
        _write_cc_task(closed_dir, "pub-bus-bandcamp-upload")
        result = discover_cc_task_for_slug(
            "declined-bandcamp",
            cc_tasks_dir=tmp_path / "active",
            closed_dir=closed_dir,
        )
        assert result == "pub-bus-bandcamp-upload"


class TestBuildCrossLinkMap:
    def test_returns_one_entry_per_slug(self, tmp_path: Path) -> None:
        active_dir = tmp_path / "active"
        _write_cc_task(active_dir, "leverage-REFUSED-discord-community")
        _write_cc_task(active_dir, "leverage-REFUSED-patreon-sponsorship")
        result = build_cross_link_map(
            slugs=("declined-discord-community", "declined-patreon"),
            cc_tasks_dir=active_dir,
            closed_dir=None,
        )
        assert result["declined-discord-community"] == "leverage-REFUSED-discord-community"
        assert result["declined-patreon"] == "leverage-REFUSED-patreon-sponsorship"

    def test_includes_unmatched_with_none(self, tmp_path: Path) -> None:
        active_dir = tmp_path / "active"
        active_dir.mkdir()
        result = build_cross_link_map(
            slugs=("declined-tutorial-videos",),
            cc_tasks_dir=active_dir,
            closed_dir=None,
        )
        assert result["declined-tutorial-videos"] is None


class TestRenderCrossLinkIndex:
    def test_lists_each_slug_and_cc_task(self) -> None:
        text = render_cross_link_index(
            {
                "declined-discord-community": "leverage-REFUSED-discord-community",
                "declined-patreon": "leverage-REFUSED-patreon-sponsorship",
            }
        )
        assert "declined-discord-community" in text
        assert "leverage-REFUSED-discord-community" in text
        assert "declined-patreon" in text
        assert "leverage-REFUSED-patreon-sponsorship" in text

    def test_renders_unmatched_as_no_cc_task(self) -> None:
        text = render_cross_link_index(
            {"declined-tutorial-videos": None},
        )
        assert "declined-tutorial-videos" in text
        # Unmatched should be visually flagged
        assert "—" in text or "(none)" in text or "no match" in text.lower()


class TestPublishCrossLinks:
    def test_writes_index_to_output_dir(self, tmp_path: Path) -> None:
        active_dir = tmp_path / "active"
        _write_cc_task(active_dir, "leverage-REFUSED-discord-community")
        output_dir = tmp_path / "publications"
        path = publish_cross_links(
            slugs=("declined-discord-community",),
            cc_tasks_dir=active_dir,
            closed_dir=None,
            output_dir=output_dir,
        )
        assert path.exists()
        assert "declined-discord-community" in path.read_text()
        assert "leverage-REFUSED-discord-community" in path.read_text()
