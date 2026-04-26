"""hapax-axioms command-line entrypoint.

Three sub-commands wrap the public API for shell / git-hook use:

    hapax-axioms scan-file <path>...
    hapax-axioms scan-commit-msg <path>
    hapax-axioms list-axioms

Exit code is 2 when any T0 violation is found, 1 on argv/IO error, 0 on
clean scans.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hapax_axioms import __version__
from hapax_axioms.checker import (
    Violation,
    scan_commit_message,
    scan_file,
)
from hapax_axioms.registry import load_axioms


def _emit(violations: list[Violation], out: list[str]) -> int:
    """Write violation lines into `out`. Return exit code 2 if any T0 hits."""
    saw_block = False
    for v in violations:
        out.append(v.format())
        if v.tier == "T0":
            saw_block = True
    return 2 if saw_block else 0


def _scan_files(args: argparse.Namespace) -> int:
    out: list[str] = []
    rc = 0
    for raw in args.paths:
        path = Path(raw)
        violations = scan_file(path)
        if not violations:
            continue
        out.append(f"=== {path} ===")
        rc = max(rc, _emit(violations, out))
    if out:
        sys.stderr.write("\n".join(out) + "\n")
    return rc


def _scan_commit_msg(args: argparse.Namespace) -> int:
    msg_path = Path(args.path)
    if not msg_path.is_file():
        sys.stderr.write(f"hapax-axioms: commit message file not found: {msg_path}\n")
        return 1
    try:
        message = msg_path.read_text(encoding="utf-8")
    except OSError as e:
        sys.stderr.write(f"hapax-axioms: cannot read commit message: {e}\n")
        return 1
    violations = scan_commit_message(message)
    if not violations:
        return 0
    out: list[str] = [f"=== commit message: {msg_path} ==="]
    rc = _emit(violations, out)
    sys.stderr.write("\n".join(out) + "\n")
    return rc


def _list_axioms(_: argparse.Namespace) -> int:
    bundle = load_axioms()
    sys.stdout.write(
        f"# hapax-axioms snapshot {bundle.snapshot_date} (schema {bundle.schema_version})\n",
    )
    sys.stdout.write(f"# canonical source: {bundle.source_repo}\n\n")
    for ax in bundle.axioms:
        sys.stdout.write(
            f"{ax.id:<28} weight={ax.weight:>3}  {ax.scope:<14} ({ax.type}, {ax.status})\n",
        )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hapax-axioms",
        description=("Single-operator axiom enforcement library — pre-commit and CI primitives."),
    )
    parser.add_argument("--version", action="version", version=f"hapax-axioms {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sf = sub.add_parser(
        "scan-file",
        help="Scan one or more source files for T0 axiom violations.",
    )
    sf.add_argument("paths", nargs="+", help="Files to scan.")
    sf.set_defaults(func=_scan_files)

    cm = sub.add_parser(
        "scan-commit-msg",
        help="Scan a commit message file (commit-msg hook entrypoint).",
    )
    cm.add_argument("path", help="Path to the commit message file (e.g. .git/COMMIT_EDITMSG).")
    cm.set_defaults(func=_scan_commit_msg)

    la = sub.add_parser("list-axioms", help="Print the bundled axiom snapshot.")
    la.set_defaults(func=_list_axioms)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
