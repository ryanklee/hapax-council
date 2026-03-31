"""DMN endpoints — buffer, impingements, and status."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse

router = APIRouter(prefix="/api/dmn", tags=["dmn"])

DMN_STATE_DIR = Path("/dev/shm/hapax-dmn")
BUFFER_FILE = DMN_STATE_DIR / "buffer.txt"
STATUS_FILE = DMN_STATE_DIR / "status.json"
IMPINGEMENTS_FILE = DMN_STATE_DIR / "impingements.jsonl"


@router.get("/buffer")
async def dmn_buffer() -> PlainTextResponse:
    """Current DMN buffer formatted for TPN consumption."""
    if not BUFFER_FILE.exists():
        return PlainTextResponse("", status_code=204)
    try:
        return PlainTextResponse(BUFFER_FILE.read_text(encoding="utf-8"))
    except OSError:
        return PlainTextResponse("", status_code=503)


@router.get("/status")
async def dmn_status() -> JSONResponse:
    """DMN daemon status (uptime, tick count, buffer entries)."""
    if not STATUS_FILE.exists():
        return JSONResponse({"error": "DMN not running"}, status_code=503)
    try:
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        return JSONResponse(data)
    except (OSError, json.JSONDecodeError):
        return JSONResponse({"error": "Failed to read DMN status"}, status_code=503)


@router.get("/impingements")
async def dmn_impingements(tail: int = 50) -> JSONResponse:
    """Recent impingements from the DMN JSONL stream.

    Args:
        tail: Number of most recent impingements to return (default 50).
    """
    if not IMPINGEMENTS_FILE.exists():
        return JSONResponse([])
    try:
        lines = IMPINGEMENTS_FILE.read_text(encoding="utf-8").strip().splitlines()
        recent = lines[-tail:] if len(lines) > tail else lines
        result = []
        for line in recent:
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return JSONResponse(result)
    except OSError:
        return JSONResponse({"error": "Failed to read impingements"}, status_code=503)
