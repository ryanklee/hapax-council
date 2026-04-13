# tests/test_reverie_daemon.py
"""Tests for the standalone Reverie daemon entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_daemon_tick_consumes_impingements(tmp_path: Path):
    """Daemon reads impingements from JSONL and dispatches to mixer.

    Post-F6 (start_at_end=True) the daemon's consumer seeks to end on
    construction, so the test writes the impingement AFTER construction
    to exercise the actual dispatch path.
    """
    imp_file = tmp_path / "impingements.jsonl"
    imp_file.touch()  # Empty file at construction time so seek-to-end = 0.

    mock_mixer = MagicMock()
    mock_mixer.tick = AsyncMock()
    mock_mixer.dispatch_impingement = MagicMock()

    from agents.reverie.__main__ import ReverieDaemon

    daemon = ReverieDaemon(
        impingement_path=imp_file,
        mixer=mock_mixer,
        skip_bootstrap=True,
    )

    # Append a fresh impingement after the daemon's consumer has seeked
    # to the (empty) end. This is the normal steady-state path.
    imp_data = {
        "id": "test-001",
        "timestamp": 1000.0,
        "source": "dmn.evaluative",
        "type": "salience_integration",
        "strength": 0.7,
        "content": {"metric": "tension", "dimensions": {"intensity": 0.5}},
    }
    imp_file.write_text(json.dumps(imp_data) + "\n")

    await daemon.tick()

    mock_mixer.dispatch_impingement.assert_called_once()
    mock_mixer.tick.assert_awaited_once()


@pytest.mark.asyncio
async def test_daemon_skips_backlog_on_startup(tmp_path: Path):
    """F6: daemon's consumer skips accumulated impingements on construction.

    Ensures stale backlog (e.g. 4000 entries accumulated while reverie was
    restarting) does not stall the first tick for 5-15 min.
    """
    imp_file = tmp_path / "impingements.jsonl"
    # Pre-populate with "backlog" entries that should be skipped.
    backlog_lines = []
    for i in range(100):
        backlog_lines.append(
            json.dumps(
                {
                    "id": f"backlog-{i:03d}",
                    "timestamp": 1000.0 + i,
                    "source": "dmn.backlog",
                    "type": "salience_integration",
                    "strength": 0.3,
                    "content": {"metric": "tension"},
                }
            )
        )
    imp_file.write_text("\n".join(backlog_lines) + "\n")

    mock_mixer = MagicMock()
    mock_mixer.tick = AsyncMock()
    mock_mixer.dispatch_impingement = MagicMock()

    from agents.reverie.__main__ import ReverieDaemon

    daemon = ReverieDaemon(
        impingement_path=imp_file,
        mixer=mock_mixer,
        skip_bootstrap=True,
    )

    await daemon.tick()

    # First tick after startup should NOT have dispatched any backlog.
    mock_mixer.dispatch_impingement.assert_not_called()
    mock_mixer.tick.assert_awaited_once()


@pytest.mark.asyncio
async def test_daemon_tick_tolerates_missing_impingement_file(tmp_path: Path):
    """Daemon handles missing impingement file gracefully."""
    mock_mixer = MagicMock()
    mock_mixer.tick = AsyncMock()

    from agents.reverie.__main__ import ReverieDaemon

    daemon = ReverieDaemon(
        impingement_path=tmp_path / "nonexistent.jsonl",
        mixer=mock_mixer,
        skip_bootstrap=True,
    )

    await daemon.tick()  # Should not raise

    mock_mixer.tick.assert_awaited_once()
    mock_mixer.dispatch_impingement.assert_not_called()
