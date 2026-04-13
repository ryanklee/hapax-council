"""LayoutState — in-memory authority for the compositor Layout.

Holds the current :class:`shared.compositor_model.Layout` behind an RLock,
exposes atomic :meth:`mutate` for edits, emits events to subscribers, and
records self-initiated writes so a file watcher can skip its own echoes.

Part of the compositor source-registry epic PR 1. See
``docs/superpowers/specs/2026-04-12-compositor-source-registry-foundation-design.md``
§ "Live state".
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from shared.compositor_model import Layout

log = logging.getLogger(__name__)

Mutator = Callable[[Layout], Layout]
Subscriber = Callable[[Layout], None]


class LayoutState:
    """In-memory authority for the current compositor Layout.

    All reads return a snapshot of the current layout. All writes go through
    :meth:`mutate` which takes a pure function ``Layout -> Layout``, validates
    the result via pydantic (catching broken references), atomically installs
    it, and emits to subscribers.

    Thread-safe: RLock-guarded. Readers never block on each other; a writer
    blocks readers only for the duration of ``fn(current) + validation``.
    """

    def __init__(self, initial: Layout) -> None:
        self._layout = Layout.model_validate(initial.model_dump())
        self._lock = threading.RLock()
        self._subscribers: list[Subscriber] = []
        self._last_self_write_mtime: float = 0.0

    def get(self) -> Layout:
        """Return the current layout snapshot.

        Callers must treat the returned value as immutable — mutations go
        through :meth:`mutate`, not by editing the return value. Pydantic
        models are frozen-by-convention here; any in-place mutation of the
        returned object is a bug on the caller's side.
        """
        with self._lock:
            return self._layout

    def mutate(self, fn: Mutator) -> None:
        """Atomically replace the layout with ``fn(current)``.

        The callable must return a new Layout (typically via ``model_copy``).
        The result is re-validated by ``Layout.model_validate`` — validation
        failures raise without mutating state, so assignment/reference
        breakage (e.g. an Assignment that names a dropped source) is caught
        before the bad state is installed.

        Subscribers are invoked after the swap, under no lock. Subscriber
        exceptions are logged but do not roll back the mutation.
        """
        with self._lock:
            candidate = fn(self._layout)
            validated = Layout.model_validate(candidate.model_dump())
            self._layout = validated
            subscribers_snapshot = list(self._subscribers)
        for sub in subscribers_snapshot:
            try:
                sub(validated)
            except Exception:
                log.exception("LayoutState subscriber raised; continuing")

    def subscribe(self, callback: Subscriber) -> None:
        """Register a callback invoked on every successful mutation."""
        with self._lock:
            self._subscribers.append(callback)

    def mark_self_write(self, mtime: float) -> None:
        """Record the mtime of a self-initiated write-back to disk.

        The :class:`LayoutFileWatcher` consults this to skip inotify events
        that match within a tolerance window, preventing reload loops
        between the auto-saver and the file watcher.
        """
        with self._lock:
            self._last_self_write_mtime = mtime

    def is_self_write(self, mtime: float, tolerance: float = 2.0) -> bool:
        """True iff ``mtime`` is within ``tolerance`` seconds of the last self-write."""
        with self._lock:
            return abs(mtime - self._last_self_write_mtime) <= tolerance
