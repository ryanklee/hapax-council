"""DFHack bridge — reads fortress state from /dev/shm, writes commands.

Follows the same atomic-write-then-rename pattern used by
perception-state.json, stimmung, and visual-layer-state.
See docs/superpowers/specs/2026-03-23-dfhack-bridge-protocol.md.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from agents.fortress.config import BridgeConfig
from agents.fortress.schema import (
    FastFortressState,
    FortressEvent,
    FullFortressState,
)

log = logging.getLogger(__name__)


class DFHackBridge:
    """Bidirectional bridge to Dwarf Fortress via /dev/shm file polling.

    State reading:
      - Polls state_path for JSON, parses into FastFortressState or FullFortressState
      - Detects staleness (mtime > threshold = DF not running)
      - Graceful degradation: returns None if no state file

    Command writing:
      - Writes command JSON to commands_path (atomic: write tmp, rename)
      - Each command has a unique ID for result correlation
      - Commands consumed exactly once by DFHack Lua script

    Result reading:
      - Reads results_path, returns dict keyed by command ID
      - Clears results file after reading
    """

    def __init__(self, config: BridgeConfig | None = None) -> None:
        self._config = config or BridgeConfig()
        self._last_state: FastFortressState | FullFortressState | None = None
        self._last_read_time: float = 0.0

    @property
    def is_active(self) -> bool:
        """True if DF is running (state file exists and is fresh)."""
        path = self._config.state_path
        if not path.exists():
            return False
        try:
            age = time.time() - path.stat().st_mtime
            return age < self._config.staleness_threshold_s
        except OSError:
            return False

    def read_state(self) -> FastFortressState | FullFortressState | None:
        """Read and parse the current fortress state.

        Returns None if:
          - State file does not exist (DF not running)
          - State file is stale (DF paused or crashed)
          - JSON parsing fails
        """
        path = self._config.state_path
        if not path.exists():
            return None

        try:
            age = time.time() - path.stat().st_mtime
            if age > self._config.staleness_threshold_s:
                log.debug("State file stale (%.1fs old)", age)
                return self._last_state  # Return last known state

            raw = path.read_text()
            data = json.loads(raw)

            # Detect full vs fast state by presence of "units" key
            if "units" in data:
                state = FullFortressState.model_validate(data)
            else:
                state = FastFortressState.model_validate(data)

            self._last_state = state
            self._last_read_time = time.monotonic()
            return state

        except (OSError, json.JSONDecodeError, Exception) as exc:  # noqa: BLE001
            log.warning("Failed to read fortress state: %s", exc)
            return self._last_state

    def send_command(self, action: str, **params: Any) -> str:
        """Write a command for DFHack to execute.

        Returns the command ID for result correlation.
        """
        cmd_id = uuid.uuid4().hex[:12]
        command: dict[str, Any] = {"id": cmd_id, "action": action, **params}

        commands_path = self._config.commands_path
        tmp_path = commands_path.with_suffix(".tmp")

        # Read existing commands (append semantics)
        existing: list[dict[str, Any]] = []
        if commands_path.exists():
            try:
                existing = json.loads(commands_path.read_text())
            except (json.JSONDecodeError, OSError):
                existing = []

        existing.append(command)

        # Atomic write
        self._config.state_dir.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(json.dumps(existing, separators=(",", ":")))
        tmp_path.rename(commands_path)

        log.debug("Sent command %s: %s", cmd_id, action)
        return cmd_id

    def poll_results(self) -> dict[str, Any]:
        """Read and clear pending command results.

        Returns dict keyed by command ID with result payloads.
        """
        results_path = self._config.results_path
        if not results_path.exists():
            return {}

        try:
            raw = results_path.read_text()
            results: dict[str, Any] = json.loads(raw)
            results_path.unlink(missing_ok=True)
            return results
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Failed to read results: %s", exc)
            return {}

    def extract_events(self, state: FastFortressState | None) -> list[FortressEvent]:
        """Extract pending events from state, if any."""
        if state is None or not state.pending_events:
            return []
        return list(state.pending_events)
