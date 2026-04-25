"""Unit tests for the interstitials adapter scan + write path."""

from __future__ import annotations

import json
from pathlib import Path

from agents.interstitials_adapter.__main__ import (
    AUDIO_EXTENSIONS,
    main,
    scan_all,
)
from shared.music_repo import LocalMusicTrack


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


def test_scan_all_finds_audio_in_both_categories(tmp_path: Path) -> None:
    _touch(tmp_path / "found-sounds" / "creak.wav")
    _touch(tmp_path / "found-sounds" / "subdir" / "rain.flac")
    _touch(tmp_path / "wwii-newsclips" / "1942-broadcast.mp3")
    _touch(tmp_path / "found-sounds" / "ignored.txt")  # non-audio

    rows = scan_all(tmp_path)

    sources = {r["source"] for r in rows}
    assert sources == {"found-sound", "wwii-newsclip"}
    paths = sorted(Path(r["path"]).name for r in rows)
    assert paths == ["1942-broadcast.mp3", "creak.wav", "rain.flac"]
    # Every row is broadcast-safe + tagged
    assert all(r["broadcast_safe"] for r in rows)
    assert all("interstitial" in r["tags"] for r in rows)


def test_scan_all_handles_missing_root(tmp_path: Path) -> None:
    """Both category dirs absent → empty list (no exception)."""
    assert scan_all(tmp_path / "does-not-exist") == []


def test_scan_all_rows_validate_as_local_music_tracks(tmp_path: Path) -> None:
    """Adapter output must round-trip through LocalMusicTrack validation."""
    _touch(tmp_path / "found-sounds" / "a.wav")
    _touch(tmp_path / "wwii-newsclips" / "b.mp3")
    rows = scan_all(tmp_path)
    for row in rows:
        track = LocalMusicTrack(**row)
        assert track.broadcast_safe
        assert track.duration_s > 0
        assert track.source in {"found-sound", "wwii-newsclip"}


def test_scan_all_audio_extension_filter() -> None:
    """Sanity-pin the audio-extension allowlist."""
    assert ".mp3" in AUDIO_EXTENSIONS
    assert ".wav" in AUDIO_EXTENSIONS
    assert ".flac" in AUDIO_EXTENSIONS
    assert ".txt" not in AUDIO_EXTENSIONS


def test_main_auto_writes_jsonl(tmp_path: Path) -> None:
    """End-to-end: --root scans, --out writes a parseable JSONL."""
    root = tmp_path / "interstitials"
    out = tmp_path / "interstitials.jsonl"
    _touch(root / "found-sounds" / "x.wav")
    _touch(root / "wwii-newsclips" / "y.mp3")

    rc = main(["--auto", "--root", str(root), "--out", str(out)])
    assert rc == 0
    assert out.exists()
    lines = [line for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2
    parsed = [json.loads(line) for line in lines]
    sources = {r["source"] for r in parsed}
    assert sources == {"found-sound", "wwii-newsclip"}


def test_main_dry_run_does_not_write(tmp_path: Path) -> None:
    root = tmp_path / "interstitials"
    out = tmp_path / "interstitials.jsonl"
    _touch(root / "found-sounds" / "x.wav")

    rc = main(["--dry-run", "--root", str(root), "--out", str(out)])
    assert rc == 0
    assert not out.exists()
