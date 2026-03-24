"""Logos API routes for fortress governance data.

Serves fortress state, governance chain status, goals, events,
metrics, and session history for the Logos frontend.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from agents.fortress.config import BridgeConfig

router = APIRouter(prefix="/api/fortress", tags=["fortress"])
log = logging.getLogger(__name__)

_bridge_config = BridgeConfig()


def _read_state_file() -> dict | None:
    """Read raw state JSON from bridge, or None if unavailable."""
    path = _bridge_config.state_path
    if not path.exists():
        return None
    try:
        import time

        age = time.time() - path.stat().st_mtime
        if age > _bridge_config.staleness_threshold_s:
            return None
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("Failed to read fortress state: %s", exc)
        return None


@router.get("/state")
async def get_fortress_state():
    """Current fortress state from DFHack bridge."""
    data = _read_state_file()
    if data is None:
        raise HTTPException(status_code=503, detail="Fortress not active")
    return data


@router.get("/events")
async def get_fortress_events(limit: int = 50):
    """Recent fortress events from state."""
    data = _read_state_file()
    if data is None:
        raise HTTPException(status_code=503, detail="Fortress not active")
    events = data.get("pending_events", [])
    return {"events": events[-limit:]}


@router.get("/governance")
async def get_fortress_governance():
    """Governance chain activity and suppression field levels.

    Returns placeholder structure — populated when FortressGovernor is running.
    """
    return {
        "chains": {
            "fortress_planner": {"active": False, "last_action": None},
            "military_commander": {"active": False, "last_action": None},
            "resource_manager": {"active": False, "last_action": None},
            "crisis_responder": {"active": False, "last_action": None},
            "storyteller": {"active": False, "last_action": None},
            "advisor": {"active": False, "last_action": None},
        },
        "suppression": {
            "crisis_suppression": 0.0,
            "military_alert": 0.0,
            "resource_pressure": 0.0,
            "planner_activity": 0.0,
        },
    }


@router.get("/goals")
async def get_fortress_goals():
    """Active compound goals and subgoal states.

    Returns placeholder — populated when GoalPlanner is running.
    """
    return {"goals": []}


@router.get("/metrics")
async def get_fortress_metrics():
    """Current session metrics (live)."""
    return {
        "session_id": None,
        "survival_days": 0,
        "total_commands": 0,
        "chain_metrics": {},
    }


@router.get("/sessions")
async def get_fortress_sessions(limit: int = 20):
    """Historical session list with survival times."""
    sessions_path = Path("profiles/fortress-sessions.jsonl")
    if not sessions_path.exists():
        return {"sessions": []}
    entries = []
    for line in sessions_path.read_text().strip().split("\n"):
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return {"sessions": entries[-limit:]}


@router.get("/sessions/{session_id}")
async def get_fortress_session(session_id: str):
    """Detailed session record."""
    sessions_path = Path("profiles/fortress-sessions.jsonl")
    if not sessions_path.exists():
        raise HTTPException(status_code=404, detail="No sessions recorded")
    for line in sessions_path.read_text().strip().split("\n"):
        if line:
            try:
                entry = json.loads(line)
                if entry.get("session_id") == session_id:
                    return entry
            except json.JSONDecodeError:
                continue
    raise HTTPException(status_code=404, detail=f"Session {session_id} not found")


@router.get("/chronicle")
async def get_fortress_chronicle(limit: int = 50):
    """Narrative chronicle entries."""
    chronicle_path = Path("profiles/fortress-chronicle.jsonl")
    if not chronicle_path.exists():
        return {"entries": []}
    entries = []
    for line in chronicle_path.read_text().strip().split("\n"):
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return {"entries": entries[-limit:]}
