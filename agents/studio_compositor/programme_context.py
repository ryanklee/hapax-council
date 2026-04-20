"""Programme-context lookup for the structural director (Phase 5).

Mirrors ``agents.hapax_daimonion.cpal.programme_context`` and
``agents.reverie.programme_context`` — a thin provider helper that goes
through ``shared.programme_store`` so the studio compositor never imports
``agents.programme_manager`` (which would introduce a circular dependency
between the structural director and the programme lifecycle).

Default reads the canonical store on every call; the structural director
ticks every ~90s so the file read cost is negligible.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from shared.programme import Programme
from shared.programme_store import default_store

log = logging.getLogger(__name__)


ProgrammeProvider = Callable[[], Programme | None]


def default_provider() -> Programme | None:
    """Return the active Programme from the canonical store, or ``None``."""
    try:
        return default_store().active_programme()
    except Exception:
        log.debug("structural programme_context: lookup failed", exc_info=True)
        return None


def null_provider() -> Programme | None:
    """Test/dev provider — always returns ``None``."""
    return None


__all__ = ["ProgrammeProvider", "default_provider", "null_provider"]
