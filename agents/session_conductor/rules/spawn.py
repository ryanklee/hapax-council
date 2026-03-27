"""Session spawn and reunion rule — child session lifecycle management."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml

from agents.session_conductor.rules import HookEvent, HookResponse, RuleBase
from agents.session_conductor.state import ChildSession, SessionState
from agents.session_conductor.topology import TopologyConfig

log = logging.getLogger(__name__)

DEFAULT_SPAWNS_DIR = Path.home() / ".cache" / "hapax" / "conductor" / "spawns"

MANIFEST_CLAIM_WINDOW = timedelta(minutes=10)

_SPAWN_PATTERNS = [
    re.compile(r"\bbreak\s+this\s+out\b", re.IGNORECASE),
    re.compile(r"\banother\s+session\s+fix\b", re.IGNORECASE),
    re.compile(r"\bspawn\s+a\s+(child|session|subagent)\b", re.IGNORECASE),
    re.compile(r"\boffload\s+to\s+(another|a\s+new)\s+session\b", re.IGNORECASE),
    re.compile(r"\bsplit\s+(this\s+)?off\b", re.IGNORECASE),
    re.compile(r"\bhand\s+off\b", re.IGNORECASE),
]

_EDIT_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})


def detect_spawn_intent(text: str) -> bool:
    """Return True if the text expresses intent to spawn a child session."""
    return any(p.search(text) for p in _SPAWN_PATTERNS)


class SpawnRule(RuleBase):
    """Manage child session spawning, manifest lifecycle, and reunion."""

    def __init__(
        self,
        topology: TopologyConfig,
        state: SessionState,
        spawns_dir: Path | None = None,
    ) -> None:
        super().__init__(topology)
        self._state = state
        self.spawns_dir = spawns_dir or DEFAULT_SPAWNS_DIR
        self.spawns_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _blocked_patterns(self) -> list[str]:
        """Return glob patterns of files the parent has in-flight."""
        return list(self._state.in_flight_files)

    def _write_manifest(self, topic: str, context: str = "") -> Path:
        """Write a spawn manifest YAML and record the child in state."""
        child_id = str(uuid.uuid4())[:8]
        manifest: dict[str, Any] = {
            "child_id": child_id,
            "parent_session": self._state.session_id,
            "topic": topic,
            "context": context,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "blocked_patterns": self._blocked_patterns(),
        }
        manifest_path = self.spawns_dir / f"{child_id}.yaml"
        manifest_path.write_text(yaml.dump(manifest, default_flow_style=False))
        log.info("SpawnRule: wrote spawn manifest %s for topic '%s'", child_id, topic)

        child = ChildSession(
            session_id=child_id,
            topic=topic,
            spawn_manifest=manifest_path,
            status="pending",
        )
        self._state.children.append(child)
        return manifest_path

    # ------------------------------------------------------------------
    # Public API for child sessions
    # ------------------------------------------------------------------

    def claim_pending_manifest(self, state: SessionState) -> dict[str, Any] | None:
        """Claim a pending manifest within the 10-minute window.

        Scans spawns_dir for pending manifests. Returns the manifest data
        (with 'status' updated to 'claimed') if one is found within the
        claim window, otherwise None.
        """
        now = datetime.now()
        for manifest_path in sorted(self.spawns_dir.glob("*.yaml")):
            try:
                data: dict[str, Any] = yaml.safe_load(manifest_path.read_text()) or {}
            except (OSError, yaml.YAMLError):
                continue

            if data.get("status") != "pending":
                continue

            created_at_str = data.get("created_at", "")
            try:
                created_at = datetime.fromisoformat(created_at_str)
            except (ValueError, TypeError):
                continue

            age = now - created_at
            if age > MANIFEST_CLAIM_WINDOW:
                log.debug("SpawnRule: manifest %s is stale (age=%s)", manifest_path.name, age)
                continue

            # Claim it
            data["status"] = "claimed"
            data["claimed_by"] = state.session_id
            data["claimed_at"] = now.isoformat()
            manifest_path.write_text(yaml.dump(data, default_flow_style=False))
            state.parent_session = data.get("parent_session")
            log.info("SpawnRule: claimed manifest %s", manifest_path.name)
            return data

        return None

    def check_completed_children(self, state: SessionState) -> list[dict[str, Any]]:
        """Scan for completed spawn manifests and return their result data."""
        completed = []
        for child in state.children:
            try:
                data: dict[str, Any] = yaml.safe_load(child.spawn_manifest.read_text()) or {}
            except (OSError, yaml.YAMLError):
                continue
            if data.get("status") == "completed":
                completed.append(data)
                child.status = "completed"
        return completed

    # ------------------------------------------------------------------
    # RuleBase interface
    # ------------------------------------------------------------------

    def on_pre_tool_use(self, event: HookEvent) -> HookResponse | None:
        # Block child from editing parent's in-flight files
        if self._state.parent_session and event.tool_name in _EDIT_TOOLS:
            file_path: str = event.tool_input.get("file_path", "")
            if file_path:
                for pattern in self._blocked_patterns():
                    if fnmatch(file_path, pattern) or file_path == pattern:
                        log.warning("SpawnRule: child blocked from parent file %s", file_path)
                        return HookResponse.block(
                            f"File '{file_path}' is owned by parent session "
                            f"'{self._state.parent_session}'. Edit it there."
                        )
        return None

    def on_post_tool_use(self, event: HookEvent) -> HookResponse | None:
        # Detect spawn intent in user message and write manifest
        if event.user_message and detect_spawn_intent(event.user_message):
            # Extract a minimal topic from the user message (first ~50 chars)
            topic = event.user_message[:50].strip().rstrip(".")
            log.info("SpawnRule: spawn intent detected — writing manifest")
            self._write_manifest(topic=topic, context=event.user_message)

        # Check for completed children and inject their results
        if self._state.children:
            completed = self.check_completed_children(self._state)
            for result in completed:
                log.info(
                    "SpawnRule: child session %s completed, injecting results",
                    result.get("child_id"),
                )

        return None
