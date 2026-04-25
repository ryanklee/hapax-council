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

Phase 6c-ii.B.1: optional :class:`ChatAuthorIsOperatorEngine` wire-in.
When wired, every URL-bearing message ticks the engine with
``handle_match`` derived from membership in ``operator_handles`` +
``persona_match=None``. If the engine asserts, ``operator_attributed:
True`` is added to the AttributionEntry metadata. Purely additive — no
existing entries are dropped or modified, downstream consumers can
ignore the new key without breaking. The engine ticks only on
URL-bearing messages so the hysteresis aligns with the attribution
surface (the consumer of the posterior).

Spec: ``docs/superpowers/specs/2026-04-18-youtube-broadcast-bundle-design.md``
§2.3 + plan ``docs/superpowers/plans/2026-04-20-youtube-broadcast-bundle-plan.md``
Phase 2 T2.1.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from shared.attribution import (
    DEFAULT_VAULT_ATTRIBUTION_ROOT,
    AttributionEntry,
    AttributionFileWriter,
)
from shared.url_extractor import classify_url, extract_urls

if TYPE_CHECKING:
    from agents.hapax_daimonion.chat_author_is_operator_engine import (
        ChatAuthorIsOperatorEngine,
    )

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

    Phase 6c-ii.B.1: optionally wire a
    :class:`ChatAuthorIsOperatorEngine` + ``operator_handles`` set.
    When both are provided, every URL-bearing message ticks the engine
    and (if asserted) tags the resulting :class:`AttributionEntry`
    metadata with ``operator_attributed: True``. Default: no engine →
    no tag (backward compat).
    """

    def __init__(
        self,
        *,
        root: Path = DEFAULT_VAULT_ATTRIBUTION_ROOT,
        chat_author_engine: ChatAuthorIsOperatorEngine | None = None,
        operator_handles: frozenset[str] = frozenset(),
    ) -> None:
        self._writer = AttributionFileWriter(root=root)
        # Per-process dedup so a chat that pastes the same URL three
        # times in a row only writes one entry. Bounded growth is fine
        # at chat scale (operator never streams more than 24h);
        # AttributionFileWriter itself dedups across runs via its
        # own JSONL read.
        self._seen_urls: set[str] = set()
        self._engine = chat_author_engine
        self._operator_handles = operator_handles

    def process_message(self, text: str, author_id: str = "") -> int:
        """Extract URLs from ``text``, classify each, append an
        AttributionEntry per new URL.

        Returns the number of entries written. Exception-safe: any
        failure (extraction, classification, file write) is logged at
        DEBUG and the count returned reflects only successful writes.

        Phase 6c-ii.B.1: when a chat-author engine is wired, ticks the
        engine BEFORE the per-URL loop with the raw ``author_id`` (so
        membership lookup hits the unhashed handle). The engine's
        asserted state is then attached to every attribution emitted
        from this message.
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
        operator_attributed = self._tick_engine_and_query(author_id)
        author_hash = hash_author_id(author_id)
        source = f"chat:{author_hash}"
        metadata: dict = {"operator_attributed": True} if operator_attributed else {}
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
                    metadata=metadata,
                )
                self._writer.append(entry)
                self._seen_urls.add(url)
                written += 1
            except Exception:
                log.debug("attribution write failed for %s", url, exc_info=True)
                continue
        return written

    def _tick_engine_and_query(self, author_id: str) -> bool:
        """Tick the wired engine (if any) and return its asserted
        state. Returns False (default) when no engine is wired.

        Membership lookup uses the raw author_id BEFORE hashing so the
        engine sees the actual handle from the chat-monitor; the hash
        only happens for the AttributionEntry source field.
        """
        if self._engine is None:
            return False
        handle_match = bool(author_id) and author_id in self._operator_handles
        # persona_match left None — that signal would be computed by a
        # separate persona-similarity scorer not yet wired. The engine
        # treats None as no-evidence-this-tick.
        self._engine.tick(handle_match=handle_match, persona_match=None)
        return self._engine.asserted()


__all__ = ["ChatUrlPipeline", "hash_author_id"]
