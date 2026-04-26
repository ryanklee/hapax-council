"""Cross-link from REFUSED cc-tasks to refusal-annex slugs — Phase 2c.

Per cc-task ``leverage-mktg-refusal-annex-series`` Phase 2c. Each
refusal annex has a corresponding cc-task in the operator's vault
(``~/Documents/Personal/20-projects/hapax-cc-tasks/``); this module
renders the slug↔cc-task mapping as a single markdown index so the
operator dashboard, the annex series, and downstream consumers all
see one canonical cross-reference table.

Discovery heuristic: an annex slug ``declined-bandcamp`` matches a
cc-task whose filename contains the slug stem (``bandcamp``,
case-insensitive) under the active or closed vault directories. The
heuristic is intentionally loose because cc-task names use varied
prefixes (``leverage-REFUSED-``, ``pub-bus-``, ``leverage-money-``,
etc.); refining is a Phase 2d concern if false positives appear.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

log = logging.getLogger(__name__)

DEFAULT_CC_TASKS_DIR: Final[Path] = (
    Path.home() / "Documents" / "Personal" / "20-projects" / "hapax-cc-tasks" / "active"
)
"""Operator-canonical cc-task vault dir (active items)."""

DEFAULT_CLOSED_CC_TASKS_DIR: Final[Path] = (
    Path.home() / "Documents" / "Personal" / "20-projects" / "hapax-cc-tasks" / "closed"
)

DEFAULT_OUTPUT_PATH: Final[Path] = (
    Path.home() / "hapax-state" / "publications" / "refusal-annex-cross-links.md"
)
"""Per-spec: cross-link index lives alongside the per-annex markdown
files in the publications directory."""


def discover_cc_task_for_slug(
    slug: str,
    *,
    cc_tasks_dir: Path = DEFAULT_CC_TASKS_DIR,
    closed_dir: Path | None = DEFAULT_CLOSED_CC_TASKS_DIR,
) -> str | None:
    """Find a cc-task ID matching the annex slug; ``None`` when no match.

    Searches ``cc_tasks_dir`` first (active items take priority), then
    ``closed_dir`` (when provided). The heuristic strips the
    ``declined-`` prefix from the slug and checks each ``.md`` filename
    for a case-insensitive substring match. The first match wins —
    operator can pin specific mappings via Phase 2d if disambiguation
    is required.
    """
    stem = slug.removeprefix("declined-").lower()
    candidates: list[Path] = []
    for d in [cc_tasks_dir, closed_dir]:
        if d is None or not d.exists():
            continue
        candidates.extend(p for p in d.glob("*.md") if stem in p.stem.lower())
    if not candidates:
        return None
    return candidates[0].stem


def build_cross_link_map(
    *,
    slugs: tuple[str, ...] | list[str],
    cc_tasks_dir: Path = DEFAULT_CC_TASKS_DIR,
    closed_dir: Path | None = DEFAULT_CLOSED_CC_TASKS_DIR,
) -> dict[str, str | None]:
    """Build ``{slug: cc_task_id_or_None}`` for every requested slug."""
    return {
        slug: discover_cc_task_for_slug(slug, cc_tasks_dir=cc_tasks_dir, closed_dir=closed_dir)
        for slug in slugs
    }


def render_cross_link_index(mapping: dict[str, str | None]) -> str:
    """Render the cross-link index as markdown.

    Format:

      # Refusal Annex ↔ cc-task Cross-Links

      | Annex slug | cc-task |
      | --- | --- |
      | declined-bandcamp | leverage-REFUSED-bandcamp |
      | declined-tutorial-videos | — (no match) |
    """
    lines: list[str] = []
    lines.append("# Refusal Annex ↔ cc-task Cross-Links")
    lines.append("")
    lines.append("| Annex slug | cc-task |")
    lines.append("| --- | --- |")
    for slug in sorted(mapping):
        cc_id = mapping[slug]
        cell = cc_id if cc_id is not None else "— (no match)"
        lines.append(f"| `{slug}` | `{cell}` |")
    lines.append("")
    return "\n".join(lines)


def publish_cross_links(
    *,
    slugs: tuple[str, ...] | list[str],
    cc_tasks_dir: Path = DEFAULT_CC_TASKS_DIR,
    closed_dir: Path | None = DEFAULT_CLOSED_CC_TASKS_DIR,
    output_dir: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    """Build the cross-link map + render + write to disk.

    Returns the path written. Either ``output_path`` (full file path)
    or ``output_dir`` (write to ``output_dir/<filename>``) may be
    provided; absent both, falls back to :data:`DEFAULT_OUTPUT_PATH`.
    """
    mapping = build_cross_link_map(slugs=slugs, cc_tasks_dir=cc_tasks_dir, closed_dir=closed_dir)
    text = render_cross_link_index(mapping)

    if output_path is not None:
        target = output_path
    elif output_dir is not None:
        target = output_dir / DEFAULT_OUTPUT_PATH.name
    else:
        target = DEFAULT_OUTPUT_PATH

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    return target


def main() -> int:
    """Entry for ``python -m agents.marketing.cc_task_cross_linker``."""
    from agents.marketing.refusal_annex_renderer import REFUSAL_ANNEX_SLUGS

    logging.basicConfig(level=logging.INFO)
    path = publish_cross_links(slugs=REFUSAL_ANNEX_SLUGS)
    log.info("wrote refusal annex cross-link index: %s", path)
    return 0


__all__ = [
    "DEFAULT_CC_TASKS_DIR",
    "DEFAULT_CLOSED_CC_TASKS_DIR",
    "DEFAULT_OUTPUT_PATH",
    "build_cross_link_map",
    "discover_cc_task_for_slug",
    "main",
    "publish_cross_links",
    "render_cross_link_index",
]


if __name__ == "__main__":
    raise SystemExit(main())
