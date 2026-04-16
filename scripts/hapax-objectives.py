#!/usr/bin/env python3
"""hapax-objectives — CLI for the research-objectives vault registry.

LRR Phase 8 item 2. Reads and writes markdown files under
``~/Documents/Personal/30-areas/hapax-objectives/`` with YAML frontmatter
matching the ``Objective`` schema from ``shared.objective_schema``.

Subcommands:
    open <title>                    Open a new active objective.
    close <objective_id>            Mark an objective closed; stamp closed_at.
    defer <objective_id>            Mark an objective deferred.
    list [--status=...]             List objectives, optionally filtered.
    current                         Print the single highest-priority active objective.
    advance <objective_id> <activity>  Record that `activity` advanced this objective.

All write subcommands also emit a JSON event to
``~/hapax-state/hapax-objectives/events.jsonl`` so downstream consumers
(HSEA Phase 3 C10 milestone generator, Phase 9 narration hook) can react.

Usage:
    uv run python scripts/hapax-objectives.py list
    uv run python scripts/hapax-objectives.py open "Close LRR epic" \\
        --priority high --activity study --activity observe \\
        --success "All 11 phases have closure handoffs"
    uv run python scripts/hapax-objectives.py current
    uv run python scripts/hapax-objectives.py close obj-002
    uv run python scripts/hapax-objectives.py advance obj-002 study
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.objective_schema import (  # noqa: E402
    Objective,
    ObjectivePriority,
    ObjectiveStatus,
)

OBJECTIVES_DIR_DEFAULT = Path.home() / "Documents" / "Personal" / "30-areas" / "hapax-objectives"
EVENTS_FILE_DEFAULT = Path.home() / "hapax-state" / "hapax-objectives" / "events.jsonl"
KNOWN_ACTIVITIES = {"react", "chat", "vinyl", "study", "observe", "silence"}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _allocate_next_id(objectives_dir: Path) -> str:
    existing = sorted(objectives_dir.glob("obj-*.md"))
    max_n = 0
    for path in existing:
        m = re.match(r"obj-(\d+)", path.stem)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"obj-{max_n + 1:03d}"


def _load_objective(path: Path) -> Objective | None:
    from shared.frontmatter import parse_frontmatter

    fm, _body = parse_frontmatter(path)
    if not fm:
        return None
    try:
        return Objective(**fm)
    except Exception:
        return None


def _iter_objectives(objectives_dir: Path):
    if not objectives_dir.exists():
        return
    for path in sorted(objectives_dir.glob("obj-*.md")):
        obj = _load_objective(path)
        if obj is not None:
            yield path, obj


def _write_objective(path: Path, obj: Objective, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = obj.model_dump(mode="json", exclude_none=True)
    # Pydantic emits datetimes as ISO already via mode="json"
    yaml_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    out = f"---\n{yaml_text}\n---\n\n{body}".rstrip() + "\n"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(out, encoding="utf-8")
    tmp.replace(path)


def _emit_event(events_file: Path, kind: str, objective_id: str, **extra) -> None:
    events_file.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": _now_iso(),
        "kind": kind,
        "objective_id": objective_id,
        **extra,
    }
    with events_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def cmd_open(args, *, objectives_dir: Path, events_file: Path) -> int:
    activities = [a for a in args.activity if a in KNOWN_ACTIVITIES]
    if not activities:
        print(
            f"error: need at least one --activity from {sorted(KNOWN_ACTIVITIES)}",
            file=sys.stderr,
        )
        return 2
    if not args.success:
        print("error: need at least one --success criterion", file=sys.stderr)
        return 2

    objectives_dir.mkdir(parents=True, exist_ok=True)
    obj_id = _allocate_next_id(objectives_dir)
    now = datetime.now(UTC)
    obj = Objective(
        objective_id=obj_id,
        title=args.title,
        status=ObjectiveStatus.active,
        priority=ObjectivePriority(args.priority),
        opened_at=now,
        linked_claims=args.claim,
        linked_conditions=args.condition,
        success_criteria=args.success,
        activities_that_advance=activities,
    )
    path = objectives_dir / f"{obj_id}.md"
    _write_objective(path, obj, body=args.body or "")
    _emit_event(events_file, "open", obj_id, title=args.title)
    print(f"{obj_id}\t{path}")
    return 0


def _find_path(objective_id: str, objectives_dir: Path) -> Path | None:
    path = objectives_dir / f"{objective_id}.md"
    return path if path.exists() else None


def cmd_close(args, *, objectives_dir: Path, events_file: Path) -> int:
    path = _find_path(args.objective_id, objectives_dir)
    if path is None:
        print(f"error: {args.objective_id} not found", file=sys.stderr)
        return 1
    obj = _load_objective(path)
    if obj is None:
        print(f"error: {args.objective_id} failed to parse", file=sys.stderr)
        return 1
    obj = obj.model_copy(update={"status": ObjectiveStatus.closed, "closed_at": datetime.now(UTC)})
    from shared.frontmatter import parse_frontmatter

    _fm, body = parse_frontmatter(path)
    _write_objective(path, obj, body=body)
    _emit_event(events_file, "close", args.objective_id)
    print(f"closed {args.objective_id}")
    return 0


def cmd_defer(args, *, objectives_dir: Path, events_file: Path) -> int:
    path = _find_path(args.objective_id, objectives_dir)
    if path is None:
        print(f"error: {args.objective_id} not found", file=sys.stderr)
        return 1
    obj = _load_objective(path)
    if obj is None:
        print(f"error: {args.objective_id} failed to parse", file=sys.stderr)
        return 1
    obj = obj.model_copy(update={"status": ObjectiveStatus.deferred})
    from shared.frontmatter import parse_frontmatter

    _fm, body = parse_frontmatter(path)
    _write_objective(path, obj, body=body)
    _emit_event(events_file, "defer", args.objective_id)
    print(f"deferred {args.objective_id}")
    return 0


def cmd_list(args, *, objectives_dir: Path, events_file: Path) -> int:
    status_filter = ObjectiveStatus(args.status) if args.status else None
    for _path, obj in _iter_objectives(objectives_dir):
        if status_filter is not None and obj.status != status_filter:
            continue
        print(f"{obj.objective_id}\t{obj.status.value}\t{obj.priority.value}\t{obj.title}")
    return 0


_PRIORITY_RANK = {
    ObjectivePriority.high: 3,
    ObjectivePriority.normal: 2,
    ObjectivePriority.low: 1,
}


def cmd_current(args, *, objectives_dir: Path, events_file: Path) -> int:
    best = None
    for _path, obj in _iter_objectives(objectives_dir):
        if obj.status != ObjectiveStatus.active:
            continue
        if best is None or (
            _PRIORITY_RANK[obj.priority],
            -obj.opened_at.timestamp(),
        ) > (
            _PRIORITY_RANK[best.priority],
            -best.opened_at.timestamp(),
        ):
            best = obj
    if best is None:
        print("(no active objectives)")
        return 1
    print(f"{best.objective_id}\t{best.priority.value}\t{best.title}")
    return 0


def cmd_advance(args, *, objectives_dir: Path, events_file: Path) -> int:
    if args.activity not in KNOWN_ACTIVITIES:
        print(f"error: activity must be one of {sorted(KNOWN_ACTIVITIES)}", file=sys.stderr)
        return 2
    path = _find_path(args.objective_id, objectives_dir)
    if path is None:
        print(f"error: {args.objective_id} not found", file=sys.stderr)
        return 1
    obj = _load_objective(path)
    if obj is None:
        print(f"error: {args.objective_id} failed to parse", file=sys.stderr)
        return 1
    if args.activity not in obj.activities_that_advance:
        print(
            f"warning: {args.activity} is not in {args.objective_id}.activities_that_advance",
            file=sys.stderr,
        )
    _emit_event(
        events_file,
        "advance",
        args.objective_id,
        activity=args.activity,
    )
    print(f"advanced {args.objective_id} via {args.activity}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hapax-objectives")
    parser.add_argument(
        "--dir",
        type=Path,
        default=OBJECTIVES_DIR_DEFAULT,
        help="Objectives directory (default: vault 30-areas/hapax-objectives)",
    )
    parser.add_argument(
        "--events-file",
        type=Path,
        default=EVENTS_FILE_DEFAULT,
        help="Events JSONL (default: ~/hapax-state/hapax-objectives/events.jsonl)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    po = sub.add_parser("open", help="Open a new active objective")
    po.add_argument("title")
    po.add_argument("--priority", choices=["high", "normal", "low"], default="normal")
    po.add_argument("--activity", action="append", default=[])
    po.add_argument("--success", action="append", default=[])
    po.add_argument("--claim", action="append", default=[])
    po.add_argument("--condition", action="append", default=[])
    po.add_argument("--body", default=None)
    po.set_defaults(func=cmd_open)

    pc = sub.add_parser("close", help="Mark an objective closed")
    pc.add_argument("objective_id")
    pc.set_defaults(func=cmd_close)

    pd = sub.add_parser("defer", help="Mark an objective deferred")
    pd.add_argument("objective_id")
    pd.set_defaults(func=cmd_defer)

    pl = sub.add_parser("list", help="List objectives")
    pl.add_argument("--status", choices=["active", "closed", "deferred"], default=None)
    pl.set_defaults(func=cmd_list)

    pcur = sub.add_parser("current", help="Print the top active objective")
    pcur.set_defaults(func=cmd_current)

    pa = sub.add_parser("advance", help="Record that `activity` advanced this objective")
    pa.add_argument("objective_id")
    pa.add_argument("activity")
    pa.set_defaults(func=cmd_advance)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args, objectives_dir=args.dir, events_file=args.events_file)


if __name__ == "__main__":
    raise SystemExit(main())
