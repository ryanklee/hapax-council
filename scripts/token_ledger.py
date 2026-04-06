"""token_ledger.py — Shared token spend accumulator for Legomena Live.

All LLM-consuming components write their token spend here.
The token pole overlay reads the running total to drive the visual.

Architecture:
  Writers: album-identifier, chat-monitor, youtube-player (via shm file)
  Reader: compositor token pole overlay (via shm file)
  Persistence: /dev/shm/hapax-compositor/token-ledger.json

Each writer atomically appends entries. The ledger tracks:
  - Total tokens spent this session
  - Running cost estimate (USD)
  - Per-component breakdown
  - Current pole position (0.0 → 1.0)
  - Explosion count (how many times the pole has been filled)
"""

from __future__ import annotations

import json
import logging
import math
import time
from pathlib import Path

log = logging.getLogger(__name__)

LEDGER_FILE = Path("/dev/shm/hapax-compositor/token-ledger.json")


def _load() -> dict:
    try:
        if LEDGER_FILE.exists():
            return json.loads(LEDGER_FILE.read_text())
    except Exception:
        pass
    return {
        "session_start": time.time(),
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "components": {},
        "pole_position": 0.0,
        "explosions": 0,
        "active_viewers": 1,
    }


def _save(state: dict) -> None:
    try:
        LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = LEDGER_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state))
        tmp.rename(LEDGER_FILE)
    except OSError:
        pass


def _threshold(active_viewers: int) -> int:
    """Sub-logarithmic scaling: 5 viewers → ~19, 5000 viewers → ~37.

    threshold(n) = base * log2(1 + log2(1 + n))
    """
    base = 5000  # tokens per pole fill at minimum scale
    n = max(1, active_viewers)
    return int(base * math.log2(1 + math.log2(1 + n)))


def record_spend(
    component: str, prompt_tokens: int, completion_tokens: int, cost: float = 0.0
) -> dict:
    """Record token spend from any component. Returns updated ledger state."""
    state = _load()
    total = prompt_tokens + completion_tokens
    state["total_tokens"] += total
    state["total_cost_usd"] += cost

    if component not in state["components"]:
        state["components"][component] = {"tokens": 0, "calls": 0}
    state["components"][component]["tokens"] += total
    state["components"][component]["calls"] += 1

    # Update pole position
    threshold = _threshold(state.get("active_viewers", 1))
    # Tokens since last explosion
    tokens_in_cycle = state["total_tokens"] - (state["explosions"] * threshold)
    position = min(1.0, tokens_in_cycle / threshold) if threshold > 0 else 0.0

    if position >= 1.0:
        state["explosions"] += 1
        state["pole_position"] = 0.0
        log.info("TOKEN POLE EXPLOSION #%d! (threshold=%d)", state["explosions"], threshold)
    else:
        state["pole_position"] = position

    _save(state)
    return state


def set_active_viewers(count: int) -> None:
    """Update active viewer count (from chat monitor)."""
    state = _load()
    state["active_viewers"] = max(1, count)
    _save(state)


def get_state() -> dict:
    """Read current ledger state (for overlay)."""
    return _load()


def record_chat_metrics(unique_authors: int, thread_depth: float, novelty_rate: float) -> None:
    """Record structural chat metrics (no token spend, just community signal)."""
    state = _load()
    state["chat"] = {
        "unique_authors": unique_authors,
        "thread_depth": thread_depth,
        "novelty_rate": novelty_rate,
        "updated": time.time(),
    }
    _save(state)
