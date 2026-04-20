"""Chat URL extraction → AttributionFileWriter pipeline (#144 Phase 2).

Wraps the Phase 1 primitives (``shared.url_extractor`` +
``shared.attribution.AttributionFileWriter``) into a single per-message
helper that the chat-monitor script invokes after message ingestion.

Privacy invariants (per ``feedback_consent_latency_obligation`` and the
chat-monitor's existing posture):

- Author IDs are HASHED at the boundary (sha256, 8-char prefix). The
  raw author id never reaches the AttributionEntry.source field.
- Empty / missing author IDs hash to a stable ``"anon"`` token rather
  than the empty string so dedup queries can target anonymous traffic.
- The pipeline is exception-safe: a malformed URL or writer failure
  never propagates back into the chat-monitor's per-message loop.

Spec: ``docs/superpowers/specs/2026-04-18-youtube-broadcast-bundle-design.md``
§2.3 + plan ``docs/superpowers/plans/2026-04-20-youtube-broadcast-bundle-plan.md``
Phase 2 T2.1.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from shared.attribution import (
    DEFAULT_VAULT_ATTRIBUTION_ROOT,
    AttributionEntry,
    AttributionFileWriter,
)
from shared.url_extractor import classify_url, extract_urls

log = logging.getLogger(__name__)


def hash_author_id(author_id: str) -> str:
    """Sha256-hash + 8-char prefix. Empty input → ``"anon"``."""
    if not author_id:
        return "anon"
    return hashlib.sha256(author_id.encode("utf-8")).hexdigest()[:8]


class ChatUrlPipeline:
    """Per-message URL extraction → attribution-write pipeline.

    Construct once per chat-monitor run; call ``process_message(text,
    author_id)`` after each message ingestion. Returns the count of
    new attribution entries written so callers can log progress.
    """

    def __init__(self, *, root: Path = DEFAULT_VAULT_ATTRIBUTION_ROOT) -> None:
        self._writer = AttributionFileWriter(root=root)
        # Per-process dedup so a chat that pastes the same URL three
        # times in a row only writes one entry. Bounded growth is fine
        # at chat scale (operator never streams more than 24h);
        # AttributionFileWriter itself dedups across runs via its
        # own JSONL read.
        self._seen_urls: set[str] = set()

    def process_message(self, text: str, author_id: str = "") -> int:
        """Extract URLs from ``text``, classify each, append an
        AttributionEntry per new URL.

        Returns the number of entries written. Exception-safe: any
        failure (extraction, classification, file write) is logged at
        DEBUG and the count returned reflects only successful writes.
        """
        if not text:
            return 0
        try:
            urls = extract_urls(text)
        except Exception:
            log.debug("URL extraction failed", exc_info=True)
            return 0
        if not urls:
            return 0
        author_hash = hash_author_id(author_id)
        source = f"chat:{author_hash}"
        written = 0
        for url in urls:
            if url in self._seen_urls:
                continue
            try:
                kind = classify_url(url)
                entry = AttributionEntry(
                    kind=kind,
                    url=url,
                    source=source,
                )
                self._writer.append(entry)
                self._seen_urls.add(url)
                written += 1
            except Exception:
                log.debug("attribution write failed for %s", url, exc_info=True)
                continue
        return written


__all__ = ["ChatUrlPipeline", "hash_author_id"]
