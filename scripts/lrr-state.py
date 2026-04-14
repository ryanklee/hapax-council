#!/usr/bin/env python3
"""LRR state CLI — read/write the LIVESTREAM RESEARCH READY epic state file.

Epic design: docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md
Epic plan:   docs/superpowers/plans/2026-04-14-livestream-research-ready-epic-plan.md

The state file at ``~/.cache/hapax/relay/lrr-state.yaml`` tracks which phase
of the LRR epic is currently open, the owning role, and known blockers.
Every session that picks up LRR execution work reads this file first.

This is a minimal bootstrap implementation intended to be expanded during
Phase 0. Commands:

    lrr-state.py show           # print the current state
    lrr-state.py current        # print just the current_phase value
    lrr-state.py init           # create an empty state file at Phase 0

Subcommands for state mutation (open, close, block, unblock) are intentionally
deferred to Phase 0 — the expansion should happen under the same branch that
executes the Phase 0 kickoff.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print(
        "lrr-state: PyYAML is required. Install via `uv sync` or `pip install pyyaml`.",
        file=sys.stderr,
    )
    sys.exit(2)


STATE_PATH = Path.home() / ".cache" / "hapax" / "relay" / "lrr-state.yaml"


def _load_state() -> dict[str, Any] | None:
    if not STATE_PATH.exists():
        return None
    return yaml.safe_load(STATE_PATH.read_text()) or {}


def _empty_state() -> dict[str, Any]:
    return {
        "epic_id": "livestream-research-ready",
        "epic_design_doc": "docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md",
        "epic_plan_doc": "docs/superpowers/plans/2026-04-14-livestream-research-ready-epic-plan.md",
        "current_phase": 0,
        "current_phase_owner": None,
        "current_phase_branch": None,
        "current_phase_pr": None,
        "current_phase_opened_at": None,
        "last_completed_phase": None,
        "last_completed_at": None,
        "last_completed_handoff": None,
        "completed_phases": [],
        "known_blockers": [],
        "current_condition": None,
        "previous_condition": None,
        "notes": "",
    }


def cmd_show(_args: argparse.Namespace) -> int:
    state = _load_state()
    if state is None:
        print(f"lrr-state: no state file at {STATE_PATH}", file=sys.stderr)
        print("Run `lrr-state.py init` to create one.", file=sys.stderr)
        return 1
    print(yaml.safe_dump(state, sort_keys=False, default_flow_style=False), end="")
    return 0


def cmd_current(_args: argparse.Namespace) -> int:
    state = _load_state()
    if state is None:
        print("null")
        return 0
    current = state.get("current_phase")
    print("null" if current is None else current)
    return 0


def cmd_init(_args: argparse.Namespace) -> int:
    if STATE_PATH.exists():
        print(f"lrr-state: {STATE_PATH} already exists; refusing to overwrite.", file=sys.stderr)
        return 1
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(yaml.safe_dump(_empty_state(), sort_keys=False, default_flow_style=False))
    print(f"lrr-state: created {STATE_PATH} at Phase 0")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="lrr-state", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show", help="print the full state as YAML")
    sub.add_parser("current", help="print just current_phase")
    sub.add_parser("init", help="create an empty Phase 0 state file")
    args = parser.parse_args()
    return {
        "show": cmd_show,
        "current": cmd_current,
        "init": cmd_init,
    }[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
