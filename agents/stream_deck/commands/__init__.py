"""Stream Deck command handlers (task #142, Phase 2).

Handlers live here so the adapter module stays device-focused. Each
submodule exposes a single callable that the WebSocket relay (or an
in-process dispatcher) can route ``(command, args)`` pairs to. The
initial set covers the vinyl rate preset keys shipped in the #140
manifest.
"""

from agents.stream_deck.commands.vinyl import (
    VINYL_RATE_COMMAND,
    VinylRatePresetError,
    handle_vinyl_rate_preset,
    resolve_rate,
)

__all__ = [
    "VINYL_RATE_COMMAND",
    "VinylRatePresetError",
    "handle_vinyl_rate_preset",
    "resolve_rate",
]
