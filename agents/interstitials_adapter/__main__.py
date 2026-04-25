"""Interstitials adapter — found-sounds + WWII-peak newsclips → JSONL pool.

Per operator directive 2026-04-24, the bed-music programmer interleaves
brief accents between operator's-own SoundCloud tracks. Two admitted
interstitial categories share a single union pool:

* ``found-sound`` — Epidemic Sound SFX, field recordings, ambient texture.
  Curated dir: ``~/hapax-state/music-repo/interstitials/found-sounds/``.
* ``wwii-newsclip`` — 1941–1945 American radio newsclips (topic-agnostic;
  era is the constraint, not the subject). Curated dir:
  ``~/hapax-state/music-repo/interstitials/wwii-newsclips/``.
  Likely upstream: Internet Archive / Library of Congress.

This adapter scans both dirs for audio files and writes
``~/hapax-state/music-repo/interstitials.jsonl`` with
:class:`shared.music_repo.LocalMusicTrack`-shaped records.

Usage::

    uv run python -m agents.interstitials_adapter --auto
    uv run python -m agents.interstitials_adapter --stats
    uv run python -m agents.interstitials_adapter --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

INTERSTITIALS_REPO_PATH: Path = Path.home() / "hapax-state" / "music-repo" / "interstitials.jsonl"
INTERSTITIALS_ROOT: Path = Path.home() / "hapax-state" / "music-repo" / "interstitials"

# Audio extensions the player can pipe through pw-cat (via sndfile or
# the local-file path). Kept conservative — the player stages the file
# directly into pw-cat without a transcode step.
AUDIO_EXTENSIONS: frozenset[str] = frozenset({".mp3", ".wav", ".flac", ".ogg", ".m4a", ".opus"})

# Default duration when the file's actual duration cannot be determined
# without an audio library (mutagen is optional; the adapter degrades to
# this placeholder so missing metadata never blocks ingest). The
# programmer doesn't gate on duration — it's recorded for observability.
DEFAULT_DURATION_S: float = 8.0


@dataclass(frozen=True)
class CategoryConfig:
    """One interstitial category — a directory and a source label."""

    dir_name: str
    source: str
    artist_label: str
    tag: str


CATEGORIES: tuple[CategoryConfig, ...] = (
    CategoryConfig(
        dir_name="found-sounds",
        source="found-sound",
        artist_label="(found sound)",
        tag="found-sound",
    ),
    CategoryConfig(
        dir_name="wwii-newsclips",
        source="wwii-newsclip",
        artist_label="(WWII-era US radio)",
        tag="wwii-newsclip",
    ),
)


def _probe_duration_s(path: Path) -> float:
    """Best-effort duration probe via mutagen; placeholder on failure."""
    try:
        from mutagen import File as MutagenFile  # type: ignore[import-untyped]
    except ImportError:
        return DEFAULT_DURATION_S
    try:
        media = MutagenFile(str(path))
        if media is None:
            return DEFAULT_DURATION_S
        length = getattr(getattr(media, "info", None), "length", None)
        if length is None:
            return DEFAULT_DURATION_S
        # Floor to 0.1s and never return 0 — pydantic gates on > 0.
        return max(float(length), 0.1)
    except Exception:
        log.debug("mutagen probe failed for %s", path, exc_info=True)
        return DEFAULT_DURATION_S


def _scan_category(root: Path, category: CategoryConfig) -> Iterator[dict[str, Any]]:
    """Yield LocalMusicTrack-shaped dicts for every audio file in a category dir."""
    cat_dir = root / category.dir_name
    if not cat_dir.is_dir():
        log.debug("category dir absent: %s", cat_dir)
        return
    for path in sorted(cat_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        yield {
            "path": str(path),
            "title": path.stem,
            "artist": category.artist_label,
            "album": "",
            "duration_s": _probe_duration_s(path),
            "tags": [category.tag, "interstitial"],
            "energy": 0.3,
            "bpm": None,
            "last_played_ts": None,
            "play_count": 0,
            "source": category.source,
            # Interstitials are operator-curated — assumed broadcast-safe
            # by curation. Non-broadcast-safe files should not be staged
            # in these directories.
            "content_risk": "tier_1_platform_cleared",
            "broadcast_safe": True,
            "whitelist_source": "operator-curated",
        }


def scan_all(root: Path = INTERSTITIALS_ROOT) -> list[dict[str, Any]]:
    """Scan every category dir and return the merged track list."""
    rows: list[dict[str, Any]] = []
    for category in CATEGORIES:
        rows.extend(_scan_category(root, category))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    lines = [json.dumps(r, sort_keys=True) for r in rows]
    tmp.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    tmp.replace(path)
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Interstitials adapter — found-sounds + WWII-newsclips → JSONL.",
    )
    parser.add_argument("--auto", action="store_true", help="Scan once and write JSONL.")
    parser.add_argument("--stats", action="store_true", help="Print existing pool stats.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and report counts without writing.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=INTERSTITIALS_ROOT,
        help="Root directory containing category subdirs (default: ~/hapax-state/...).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=INTERSTITIALS_REPO_PATH,
        help="Output JSONL path.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.stats:
        if args.out.exists():
            count = sum(1 for line in args.out.read_text().splitlines() if line.strip())
            print(f"interstitials.jsonl: {count} tracks at {args.out}")
        else:
            print(f"interstitials.jsonl: missing ({args.out})")
        return 0

    started = time.time()
    rows = scan_all(args.root)
    by_source: dict[str, int] = {}
    for row in rows:
        by_source[row["source"]] = by_source.get(row["source"], 0) + 1
    breakdown = ", ".join(f"{src}={n}" for src, n in sorted(by_source.items())) or "(empty)"
    log.info("scan: %d tracks (%s)", len(rows), breakdown)

    if args.dry_run:
        return 0

    written = _write_jsonl(args.out, rows)
    log.info(
        "interstitials sync: wrote %d tracks to %s in %.2fs",
        written,
        args.out,
        time.time() - started,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
