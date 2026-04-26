"""Tests for ``agents.attribution.swhids_yaml`` persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from agents.attribution.swhids_yaml import (
    SwhidRecord,
    load_swhids,
    save_swhids,
)


class TestSwhidRecord:
    def test_minimal_construction(self) -> None:
        rec = SwhidRecord(slug="x", repo_url="https://github.com/ryanklee/x")
        assert rec.slug == "x"
        assert rec.swhid is None
        assert rec.error is None

    def test_full_construction(self) -> None:
        rec = SwhidRecord(
            slug="x",
            repo_url="https://github.com/ryanklee/x",
            swhid="swh:1:snp:" + "a" * 40,
            visit_status="done",
            last_attempted=datetime(2026, 4, 26, tzinfo=UTC),
        )
        assert rec.swhid is not None
        assert rec.visit_status == "done"


class TestSaveLoadRoundtrip:
    def test_save_and_load_returns_same_records(self, tmp_path: Path) -> None:
        path = tmp_path / "swhids.yaml"
        records = {
            "hapax-council": SwhidRecord(
                slug="hapax-council",
                repo_url="https://github.com/ryanklee/hapax-council",
                swhid="swh:1:snp:" + "b" * 40,
                visit_status="done",
            ),
            "hapax-officium": SwhidRecord(
                slug="hapax-officium",
                repo_url="https://github.com/ryanklee/hapax-officium",
                swhid=None,
                visit_status="ongoing",
            ),
        }
        save_swhids(records, path=path)
        loaded = load_swhids(path=path)
        assert set(loaded.keys()) == {"hapax-council", "hapax-officium"}
        assert loaded["hapax-council"].swhid == "swh:1:snp:" + "b" * 40
        assert loaded["hapax-officium"].visit_status == "ongoing"

    def test_load_missing_file_returns_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "does-not-exist.yaml"
        assert load_swhids(path=path) == {}

    def test_save_creates_parent_directory(self, tmp_path: Path) -> None:
        path = tmp_path / "nested" / "deep" / "swhids.yaml"
        save_swhids(
            {"x": SwhidRecord(slug="x", repo_url="https://github.com/ryanklee/x")},
            path=path,
        )
        assert path.exists()

    def test_save_is_atomic_no_partial_file_on_pre_existing(self, tmp_path: Path) -> None:
        path = tmp_path / "swhids.yaml"
        save_swhids(
            {"x": SwhidRecord(slug="x", repo_url="https://github.com/ryanklee/x")},
            path=path,
        )
        save_swhids(
            {"y": SwhidRecord(slug="y", repo_url="https://github.com/ryanklee/y")},
            path=path,
        )
        loaded = load_swhids(path=path)
        assert set(loaded.keys()) == {"y"}

    def test_save_serializes_datetime_as_iso(self, tmp_path: Path) -> None:
        path = tmp_path / "swhids.yaml"
        save_swhids(
            {
                "x": SwhidRecord(
                    slug="x",
                    repo_url="https://github.com/ryanklee/x",
                    last_attempted=datetime(2026, 4, 26, 14, 30, tzinfo=UTC),
                )
            },
            path=path,
        )
        text = path.read_text()
        assert "2026-04-26" in text
