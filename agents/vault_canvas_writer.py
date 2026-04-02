"""Vault canvas writer — generates a JSON Canvas goal dependency map.

Reads vault goal notes (type: goal), builds a dependency graph from
depends_on fields, and writes a .canvas file to the vault. The operator
opens this in Obsidian Canvas for a spatial view of goal relationships.

Deterministic (tier 3, no LLM). Runs via obsidian_sync or on-demand.

Usage:
    uv run python -m agents.vault_canvas_writer
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from logos.data.vault_goals import VaultGoal, collect_vault_goals

log = logging.getLogger(__name__)

CANVAS_PATH = (
    Path.home() / "Documents" / "Personal" / "20-projects" / "hapax-goals" / "goal-map.canvas"
)

# Layout constants
NODE_W = 300
NODE_H = 80
COL_SPACING = 400
ROW_SPACING = 120

# Domain colors (Gruvbox palette)
DOMAIN_COLORS: dict[str, str] = {
    "research": "4",  # green
    "management": "5",  # purple
    "studio": "6",  # cyan
    "personal": "1",  # red
    "health": "3",  # yellow
}


def _build_canvas(goals: list[VaultGoal]) -> dict:
    """Build JSON Canvas structure from goals."""
    nodes = []
    edges = []
    goal_map = {g.id: g for g in goals}

    # Group by domain for columnar layout
    domains: dict[str, list[VaultGoal]] = {}
    for g in goals:
        domains.setdefault(g.domain, []).append(g)

    # Position nodes in columns by domain
    col = 0
    for _domain, domain_goals in sorted(domains.items()):
        for row, g in enumerate(domain_goals):
            status_icon = {"active": "●", "paused": "◌", "completed": "✓", "abandoned": "✗"}.get(
                g.status, "?"
            )
            label = f"{status_icon} {g.title}\n{g.priority} · {g.domain}"
            if g.progress is not None:
                label += f" · {round(g.progress * 100)}%"

            nodes.append(
                {
                    "id": g.id,
                    "type": "text",
                    "x": col * COL_SPACING,
                    "y": row * ROW_SPACING,
                    "width": NODE_W,
                    "height": NODE_H,
                    "text": label,
                    "color": DOMAIN_COLORS.get(g.domain, "0"),
                }
            )

            # Add dependency edges
            for dep_id in g.depends_on:
                if dep_id in goal_map:
                    edges.append(
                        {
                            "id": f"{dep_id}->{g.id}",
                            "fromNode": dep_id,
                            "toNode": g.id,
                            "fromSide": "right",
                            "toSide": "left",
                        }
                    )

        col += 1

    return {"nodes": nodes, "edges": edges}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    goals = [
        g
        for g in collect_vault_goals()
        if g.status in ("active", "paused")
        and "templates" not in str(g.file_path)
        and "fileclass" not in str(g.file_path)
    ]

    if not goals:
        log.info("No active goals — writing empty canvas")

    canvas = _build_canvas(goals)
    CANVAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CANVAS_PATH.write_text(json.dumps(canvas, indent=2), encoding="utf-8")
    log.info(
        "Wrote goal map canvas: %s (%d nodes, %d edges)",
        CANVAS_PATH,
        len(canvas["nodes"]),
        len(canvas["edges"]),
    )


if __name__ == "__main__":
    main()
