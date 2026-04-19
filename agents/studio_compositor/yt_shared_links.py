"""Operator-shared YouTube link capture (task #144).

A private, local-only JSONL channel for URLs the operator surfaces during
a livestream (via sidechat ``link <url>`` or phone push). Each line is a
record appended atomically via ``O_APPEND``. The YouTube description
syncer (``youtube_description_syncer.sync_shared_links_once``) tails this
file and appends each URL to the live broadcast description, respecting
the existing per-stream + daily quota caps shipped with Phase 8 item 7.

**Privacy posture:** the same shape as
``shared/operator_sidechat`` — the on-disk JSONL is LOCAL-ONLY; only the
URLs explicitly approved by the operator for reference in the public
YouTube description are egressed. This module does not egress anything
on its own; it merely stages the URLs for the syncer.

**Record format:** one JSON object per line::

    {"ts": 1776563400.123, "url": "https://youtu.be/...",
     "source": "sidechat"}

**Transport:** append-only JSONL at
``/dev/shm/hapax-compositor/yt-shared-links.jsonl`` via
``O_APPEND | O_CREAT | O_WRONLY`` so concurrent writers (sidechat
consumer + phone push handler) produce well-formed lines.

**Cursor:** consumers track last-seen ``ts`` at
``~/.cache/hapax/yt-links-cursor.txt`` via atomic tmp+rename.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

__all__ = [
    "YT_SHARED_LINKS_PATH",
    "YT_LINKS_CURSOR_PATH",
    "YT_QUEUE_PATH",
    "URL_REGEX",
    "LINK_COMMAND_PREFIX",
    "append_shared_link",
    "tail_shared_links",
    "load_cursor",
    "save_cursor",
    "parse_link_command",
    "queue_link_for_next_broadcast",
]

log = logging.getLogger(__name__)

YT_SHARED_LINKS_PATH: Path = Path("/dev/shm/hapax-compositor/yt-shared-links.jsonl")
YT_LINKS_CURSOR_PATH: Path = Path.home() / ".cache" / "hapax" / "yt-links-cursor.txt"
YT_QUEUE_PATH: Path = Path.home() / "hapax-state" / "yt-queue.jsonl"

LINK_COMMAND_PREFIX: str = "link "

# Conservative URL regex — matches http/https, captures the first plausible
# URL token in the payload. Intentionally loose so YouTube share-links with
# tracking params still match.
URL_REGEX: re.Pattern[str] = re.compile(r"https?://[^\s]+", re.IGNORECASE)

Source = Literal["sidechat", "phone", "other"]


def _ensure_parent(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        log.debug("Could not create parent %s", path.parent, exc_info=True)


def parse_link_command(text: str) -> str | None:
    """Return the URL if ``text`` is a ``link <url>`` command, else ``None``.

    Lenient parsing — accepts leading/trailing whitespace, extra text
    after the URL (treated as a comment and discarded for the record),
    and any ``http(s)://`` URL. Non-``link ...`` text returns ``None``
    so callers can pass through to the default sidechat handling.
    """
    if not text:
        return None
    stripped = text.strip()
    if not stripped.lower().startswith(LINK_COMMAND_PREFIX):
        return None
    remainder = stripped[len(LINK_COMMAND_PREFIX) :].strip()
    if not remainder:
        return None
    match = URL_REGEX.search(remainder)
    if not match:
        return None
    return match.group(0).strip()


def append_shared_link(
    url: str,
    *,
    source: Source = "sidechat",
    ts: float | None = None,
    path: Path | None = None,
) -> dict:
    """Append a shared-link record to the JSONL atomically.

    Uses ``O_APPEND`` so concurrent writers (sidechat + phone) produce
    well-formed lines. Returns the serialized record (for logging / tests).
    """
    if not url or not url.strip():
        raise ValueError("shared-link url must be non-empty")
    target = path if path is not None else YT_SHARED_LINKS_PATH
    record = {
        "ts": ts if ts is not None else time.time(),
        "url": url.strip(),
        "source": source,
    }
    line = (json.dumps(record) + "\n").encode("utf-8")
    _ensure_parent(target)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)
    return record


def tail_shared_links(
    since_ts: float | None = None,
    *,
    path: Path | None = None,
) -> Iterator[dict]:
    """Yield records with ``ts > since_ts`` from the shared-links JSONL.

    Malformed lines are skipped silently (debug-logged).
    """
    target = path if path is not None else YT_SHARED_LINKS_PATH
    if not target.exists():
        return
    cutoff = since_ts if since_ts is not None else float("-inf")
    try:
        raw = target.read_text(encoding="utf-8")
    except OSError:
        log.debug("Failed to read %s", target, exc_info=True)
        return
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            log.debug("Malformed yt-shared-links line: %s", stripped[:80])
            continue
        if not isinstance(obj, dict):
            continue
        try:
            ts = float(obj.get("ts", 0.0))
        except (TypeError, ValueError):
            continue
        if ts > cutoff:
            yield obj


def load_cursor(path: Path | None = None) -> float:
    """Load last-seen ts cursor, or 0.0 on missing / malformed."""
    target = path if path is not None else YT_LINKS_CURSOR_PATH
    try:
        raw = target.read_text(encoding="utf-8").strip()
        return float(raw) if raw else 0.0
    except (FileNotFoundError, ValueError, OSError):
        return 0.0


def save_cursor(ts: float, *, path: Path | None = None) -> None:
    """Persist cursor atomically via tmp+rename."""
    target = path if path is not None else YT_LINKS_CURSOR_PATH
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".txt.tmp")
        tmp.write_text(f"{ts}", encoding="utf-8")
        tmp.replace(target)
    except OSError:
        log.debug("Failed to persist yt-links cursor", exc_info=True)


def queue_link_for_next_broadcast(
    record: dict,
    *,
    path: Path | None = None,
) -> None:
    """Persist a shared-link record to the next-broadcast queue.

    Called when the syncer can't update a live broadcast (no active
    broadcast, quota exhausted, or no video_id configured). The next
    broadcast's start-up hook drains the queue into the initial
    description.
    """
    target = path if path is not None else YT_QUEUE_PATH
    _ensure_parent(target)
    line = (json.dumps(record) + "\n").encode("utf-8")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)
