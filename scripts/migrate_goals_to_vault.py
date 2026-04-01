"""Migrate goals from operator.json to Obsidian vault notes.

Usage: uv run python scripts/migrate_goals_to_vault.py [--dry-run]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

OPERATOR_JSON = Path.home() / ".hapax" / "operator.json"
FALLBACK = Path(__file__).resolve().parents[1] / "profiles" / "operator-profile.json"
VAULT_GOALS_DIR = Path.home() / "Documents" / "Personal" / "20 Projects" / "hapax-goals"

DRY_RUN = "--dry-run" in sys.argv


def load_operator_goals() -> list[dict]:
    """Load goals from operator.json."""
    for path in [OPERATOR_JSON, FALLBACK]:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            goals = data.get("goals", {})
            if not isinstance(goals, dict):
                continue
            primary = goals.get("primary", [])
            secondary = goals.get("secondary", [])
            return [{**g, "category": "primary"} for g in primary] + [
                {**g, "category": "secondary"} for g in secondary
            ]
    return []


def goal_to_note(g: dict) -> tuple[str, str]:
    """Convert operator.json goal to vault note content."""
    fm = {
        "type": "goal",
        "title": g.get("name", g.get("id", "untitled")),
        "domain": "research",  # default — operator should recategorize
        "status": g.get("status", "active"),
        "priority": "P1" if g.get("category") == "primary" else "P2",
    }
    if g.get("last_activity_at"):
        fm["started_at"] = g["last_activity_at"][:10]

    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    body = g.get("description", "") or g.get("progress_summary", "") or ""
    slug = g.get("id", "goal").replace(" ", "-").lower()
    content = f"---\n{yaml_str}---\n\n{body}\n"
    return slug, content


def main() -> None:
    goals = load_operator_goals()
    if not goals:
        print("No goals found in operator.json. Nothing to migrate.")
        return

    if not DRY_RUN:
        VAULT_GOALS_DIR.mkdir(parents=True, exist_ok=True)

    for g in goals:
        slug, content = goal_to_note(g)
        path = VAULT_GOALS_DIR / f"{slug}.md"
        if DRY_RUN:
            print(f"[dry-run] Would write: {path}")
            print(content[:200])
            print("---")
        else:
            path.write_text(content, encoding="utf-8")
            print(f"Created: {path}")

    print(f"\nMigrated {len(goals)} goals to {VAULT_GOALS_DIR}")
    if not DRY_RUN:
        print("Review domain assignments — all defaulted to 'research'.")


if __name__ == "__main__":
    main()
