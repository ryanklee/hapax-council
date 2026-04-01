"""Content resolver daemon — resolves slow imagination content references.

Watches /dev/shm/hapax-imagination/current.json for new fragments.
Resolves slow content types (text, qdrant_query, url) to JPEG files.
Writes resolved content to /dev/shm/hapax-imagination/content/active/.

Usage:
    uv run python -m agents.content_resolver
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import time
from pathlib import Path

from agents.imagination import CURRENT_PATH, ImaginationFragment
from agents.imagination_resolver import CONTENT_DIR, resolve_references_staged
from shared.control_signal import ControlSignal, publish_health

log = logging.getLogger("content-resolver")

POLL_INTERVAL_S = 0.5
MAX_FAILURES_PER_FRAGMENT = 5
SKIP_DURATION_S = 60.0


def check_for_new_fragment(
    last_id: str, *, path: Path = CURRENT_PATH
) -> tuple[str | None, dict | None]:
    """Check for a new imagination fragment. Returns (id, data) or (None, None)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        frag_id = data.get("id", "")
        if frag_id and frag_id != last_id:
            return frag_id, data
        return None, None
    except (OSError, json.JSONDecodeError):
        return None, None


class ContentResolverDaemon:
    """Watches for new imagination fragments and resolves slow content."""

    def __init__(self) -> None:
        self._running = True
        self._failures: dict[str, int] = {}
        self._skip_until: dict[str, float] = {}
        self._last_fragment_id = ""

    async def run(self) -> None:
        log.info("Content resolver daemon starting")
        CONTENT_DIR.mkdir(parents=True, exist_ok=True)

        while self._running:
            try:
                frag_id, data = check_for_new_fragment(self._last_fragment_id)
                if frag_id is not None and data is not None:
                    skip_until = self._skip_until.get(frag_id)
                    if skip_until and time.time() < skip_until:
                        pass
                    else:
                        if skip_until:
                            del self._skip_until[frag_id]
                        self._last_fragment_id = frag_id
                        try:
                            frag = ImaginationFragment.model_validate(data)
                            resolve_references_staged(frag)
                            self._failures.pop(frag_id, None)
                            log.debug("Resolved content for fragment %s", frag_id)
                            publish_health(
                                ControlSignal(
                                    component="content_resolver", reference=1.0, perception=1.0
                                )
                            )
                        except Exception:
                            count = self._failures.get(frag_id, 0) + 1
                            self._failures[frag_id] = count
                            if count >= MAX_FAILURES_PER_FRAGMENT:
                                self._skip_until[frag_id] = time.time() + SKIP_DURATION_S
                                log.warning(
                                    "Skipping fragment %s after %d failures", frag_id, count
                                )
                            else:
                                log.debug(
                                    "Resolver failed for %s (%d/%d)",
                                    frag_id,
                                    count,
                                    MAX_FAILURES_PER_FRAGMENT,
                                )
                            publish_health(
                                ControlSignal(
                                    component="content_resolver", reference=1.0, perception=0.0
                                )
                            )
            except Exception:
                log.warning("Resolver tick failed", exc_info=True)

            await asyncio.sleep(POLL_INTERVAL_S)

        log.info("Content resolver daemon stopped")

    def stop(self) -> None:
        self._running = False


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    daemon = ContentResolverDaemon()

    loop = asyncio.new_event_loop()

    def _handle_signal(sig: int, frame: object) -> None:
        daemon.stop()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    try:
        loop.run_until_complete(daemon.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
