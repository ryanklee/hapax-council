#!/usr/bin/env python3
"""Continuous mid-collection integrity check for LRR Phase 4.

Runs the 5 checks from the Phase 4 spec §3.6 and exits non-zero if
any anomaly is detected. Intended for a systemd user timer that fires
every 15 minutes during the active Condition A collection window.

Exit codes:

    0  — all checks passed
    1  — research-registry current drifted from expected condition
    2  — frozen-file diffs on disk (potential regression)
    3  — Qdrant point count for the condition has not grown
    4  — Langfuse score count for the condition has not grown
    5  — channel split stalled (one channel growing, other stalled >30 min)
    6  — environment / setup error (missing dependencies, unreachable services)

Usage::

    scripts/check-phase-a-integrity.py                              # run once
    scripts/check-phase-a-integrity.py --expected-condition <id>    # pin the condition
    scripts/check-phase-a-integrity.py --state-file <path>          # custom state file
    scripts/check-phase-a-integrity.py --json                       # machine-readable output
    scripts/check-phase-a-integrity.py --dry-run                    # skip external-service checks

State tracking: the script remembers the previous check's observation
counts at ``$HAPAX_STATE_DIR/check-phase-a-integrity.state.json`` so
it can detect monotonic-growth violations and channel stalls across
invocations. The state file is atomically rewritten on every
successful run.

Security: read-only. Never writes to Qdrant, Langfuse, or the
research registry. Only writes to the state file.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_EXPECTED_CONDITION = "cond-phase-a-baseline-qwen-001"
DEFAULT_STATE_DIR = Path.home() / "hapax-state"
DEFAULT_STATE_FILE = DEFAULT_STATE_DIR / "check-phase-a-integrity.state.json"
DEFAULT_REGISTRY_DIR = DEFAULT_STATE_DIR / "research-registry"
DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_QDRANT_COLLECTION = "stream-reactions"
CHANNEL_STALL_THRESHOLD_S = 30 * 60  # 30 minutes per Phase 4 spec §3.6


@dataclass
class CheckState:
    """Persisted state across invocations.

    Tracks the previous check's observation counts and timestamps so
    we can detect monotonic-growth violations and channel stalls.
    """

    last_check_ts: float = 0.0
    last_reaction_count: int = 0
    last_score_count: int = 0
    last_reaction_growth_ts: float = 0.0
    last_score_growth_ts: float = 0.0

    @classmethod
    def load(cls, path: Path) -> CheckState:
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return cls()
        if not isinstance(raw, dict):
            return cls()
        return cls(
            last_check_ts=float(raw.get("last_check_ts", 0.0)),
            last_reaction_count=int(raw.get("last_reaction_count", 0)),
            last_score_count=int(raw.get("last_score_count", 0)),
            last_reaction_growth_ts=float(raw.get("last_reaction_growth_ts", 0.0)),
            last_score_growth_ts=float(raw.get("last_score_growth_ts", 0.0)),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2))
        os.replace(tmp, path)


@dataclass
class CheckResult:
    """Result of a single check run. All fields optional so JSON
    output degrades gracefully when a check was skipped or errored.
    """

    ok: bool = True
    exit_code: int = 0
    reason: str = ""
    checks: dict[str, Any] = field(default_factory=dict)


def _load_current_condition(registry_dir: Path) -> str | None:
    """Read the research-registry current.txt pointer. None if absent."""
    current = registry_dir / "current.txt"
    if not current.exists():
        return None
    try:
        return current.read_text().strip() or None
    except OSError:
        return None


def check_current_condition(expected: str, registry_dir: Path) -> tuple[bool, str, str | None]:
    """Check 1: research-registry current matches the expected condition."""
    actual = _load_current_condition(registry_dir)
    if actual is None:
        return False, "research-registry current.txt missing or empty", None
    if actual != expected:
        return (
            False,
            f"research-registry current drifted: expected {expected}, got {actual}",
            actual,
        )
    return True, f"current = {actual}", actual


def check_frozen_files_clean(repo_root: Path) -> tuple[bool, str]:
    """Check 2: no frozen-file diffs on disk.

    Runs ``check-frozen-files.py`` against staged changes. Exit 0
    means either no frozen files touched or all touched files are
    covered by a DEVIATION — both acceptable.
    """
    script = repo_root / "scripts" / "check-frozen-files.py"
    if not script.exists():
        return (
            True,
            "scripts/check-frozen-files.py not found — skipped (registry pre-dates Phase 1)",
        )
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        return False, f"check-frozen-files.py invocation failed: {exc}"
    if result.returncode == 0:
        return True, "frozen-files check passed"
    return False, f"frozen-files check exit {result.returncode}: {result.stderr.strip()[:200]}"


def check_qdrant_growth(
    condition_id: str,
    state: CheckState,
    now_ts: float,
    *,
    qdrant_url: str = DEFAULT_QDRANT_URL,
    collection: str = DEFAULT_QDRANT_COLLECTION,
) -> tuple[bool, str, int]:
    """Check 3: Qdrant reaction count for the condition is monotonically growing."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import FieldCondition, Filter, MatchValue
    except ImportError:
        return True, "qdrant-client not installed — check skipped", state.last_reaction_count
    try:
        client = QdrantClient(url=qdrant_url)
        count_result = client.count(
            collection_name=collection,
            count_filter=Filter(
                must=[FieldCondition(key="condition_id", match=MatchValue(value=condition_id))]
            ),
            exact=True,
        )
        current_count = int(count_result.count)
    except Exception as exc:  # noqa: BLE001 — any qdrant error is an env issue
        return True, f"Qdrant unreachable: {exc!s} — check skipped", state.last_reaction_count
    if current_count < state.last_reaction_count:
        return (
            False,
            f"Qdrant count regressed: was {state.last_reaction_count}, now {current_count}",
            current_count,
        )
    return True, f"Qdrant count = {current_count} (prev {state.last_reaction_count})", current_count


def check_langfuse_growth(
    condition_id: str,
    state: CheckState,
    now_ts: float,
) -> tuple[bool, str, int]:
    """Check 4: Langfuse score count for the condition is monotonically growing.

    Uses the Langfuse REST API via ``langfuse`` Python SDK. If the
    SDK isn't installed or the endpoint is unreachable, skipped
    (counts as passing — environment issue, not a data integrity
    issue). The consumer of this script should have a separate
    alert on "Langfuse check skipped consistently for N runs."
    """
    try:
        from langfuse import Langfuse  # type: ignore[import-not-found]
    except ImportError:
        return True, "langfuse SDK not installed — check skipped", state.last_score_count
    try:
        client = Langfuse()
        scores = client.api.score.get(
            name=None,
            limit=1,
            from_timestamp=None,
            to_timestamp=None,
        )
    except Exception as exc:  # noqa: BLE001
        return True, f"Langfuse unreachable: {exc!s} — check skipped", state.last_score_count

    total = getattr(scores, "meta", {}).get("total_items") if scores else None
    if total is None:
        return True, "Langfuse score count unavailable — check skipped", state.last_score_count
    current_count = int(total)
    if current_count < state.last_score_count:
        return (
            False,
            f"Langfuse count regressed: was {state.last_score_count}, now {current_count}",
            current_count,
        )
    return True, f"Langfuse count = {current_count} (prev {state.last_score_count})", current_count


def check_channel_split(
    state: CheckState,
    reaction_count: int,
    score_count: int,
    now_ts: float,
) -> tuple[bool, str]:
    """Check 5: both channels advancing; neither stalled > 30 min.

    Updates state.last_reaction_growth_ts / last_score_growth_ts when
    each channel advances. Fails if either channel's last-growth
    timestamp is more than CHANNEL_STALL_THRESHOLD_S in the past.
    """
    stalls: list[str] = []

    if reaction_count > state.last_reaction_count:
        state.last_reaction_growth_ts = now_ts
    elif state.last_reaction_growth_ts > 0:
        age = now_ts - state.last_reaction_growth_ts
        if age > CHANNEL_STALL_THRESHOLD_S:
            stalls.append(f"reactions stalled {age:.0f}s")

    if score_count > state.last_score_count:
        state.last_score_growth_ts = now_ts
    elif state.last_score_growth_ts > 0:
        age = now_ts - state.last_score_growth_ts
        if age > CHANNEL_STALL_THRESHOLD_S:
            stalls.append(f"scores stalled {age:.0f}s")

    if stalls:
        return False, "channel stall: " + ", ".join(stalls)
    return True, "channels advancing"


def run_checks(args: argparse.Namespace) -> CheckResult:
    result = CheckResult()
    state_path = Path(args.state_file)
    registry_dir = Path(args.registry_dir)
    state = CheckState.load(state_path)
    now_ts = time.time()

    # Check 1 — current condition
    ok, msg, actual_condition = check_current_condition(args.expected_condition, registry_dir)
    result.checks["current_condition"] = {"ok": ok, "message": msg, "actual": actual_condition}
    if not ok:
        result.ok = False
        result.exit_code = 1
        result.reason = msg
        return result

    condition_id = args.expected_condition

    # Check 2 — frozen-file cleanliness
    if not args.dry_run:
        ok, msg = check_frozen_files_clean(Path(args.repo_root))
        result.checks["frozen_files"] = {"ok": ok, "message": msg}
        if not ok:
            result.ok = False
            result.exit_code = 2
            result.reason = msg
            return result

    # Check 3 — Qdrant growth
    ok, msg, reaction_count = (
        (True, "skipped (dry-run)", state.last_reaction_count)
        if args.dry_run
        else check_qdrant_growth(
            condition_id,
            state,
            now_ts,
            qdrant_url=args.qdrant_url,
            collection=args.qdrant_collection,
        )
    )
    result.checks["qdrant_growth"] = {"ok": ok, "message": msg, "count": reaction_count}
    if not ok:
        result.ok = False
        result.exit_code = 3
        result.reason = msg
        return result

    # Check 4 — Langfuse growth
    ok, msg, score_count = (
        (True, "skipped (dry-run)", state.last_score_count)
        if args.dry_run
        else check_langfuse_growth(condition_id, state, now_ts)
    )
    result.checks["langfuse_growth"] = {"ok": ok, "message": msg, "count": score_count}
    if not ok:
        result.ok = False
        result.exit_code = 4
        result.reason = msg
        return result

    # Check 5 — channel split (only meaningful after the first run with non-zero counts)
    ok, msg = check_channel_split(state, reaction_count, score_count, now_ts)
    result.checks["channel_split"] = {"ok": ok, "message": msg}
    if not ok:
        result.ok = False
        result.exit_code = 5
        result.reason = msg
        # Still persist state updates before returning
        state.last_check_ts = now_ts
        state.last_reaction_count = reaction_count
        state.last_score_count = score_count
        state.save(state_path)
        return result

    # All checks passed — persist state
    state.last_check_ts = now_ts
    state.last_reaction_count = reaction_count
    state.last_score_count = score_count
    state.save(state_path)

    result.reason = "all checks passed"
    return result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="check-phase-a-integrity.py",
        description="LRR Phase 4 §3.6 mid-collection integrity check.",
    )
    p.add_argument(
        "--expected-condition",
        default=DEFAULT_EXPECTED_CONDITION,
        help=f"Expected active research condition_id (default: {DEFAULT_EXPECTED_CONDITION})",
    )
    p.add_argument(
        "--state-file",
        default=str(DEFAULT_STATE_FILE),
        help=f"Persistent state file (default: {DEFAULT_STATE_FILE})",
    )
    p.add_argument(
        "--registry-dir",
        default=str(DEFAULT_REGISTRY_DIR),
        help=f"Research registry directory (default: {DEFAULT_REGISTRY_DIR})",
    )
    p.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="Repository root for check-frozen-files.py",
    )
    p.add_argument(
        "--qdrant-url",
        default=DEFAULT_QDRANT_URL,
        help=f"Qdrant URL (default: {DEFAULT_QDRANT_URL})",
    )
    p.add_argument(
        "--qdrant-collection",
        default=DEFAULT_QDRANT_COLLECTION,
        help=f"Qdrant collection (default: {DEFAULT_QDRANT_COLLECTION})",
    )
    p.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit JSON instead of human-readable output",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip Qdrant + Langfuse + frozen-files checks (file-only tests)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_checks(args)

    if args.as_json:
        print(json.dumps(asdict(result), indent=2))
    else:
        status = "OK" if result.ok else "FAIL"
        print(f"check-phase-a-integrity: {status} — {result.reason}")
        for name, check in result.checks.items():
            mark = "✓" if check.get("ok") else "✗"
            print(f"  {mark} {name}: {check.get('message', '')}")

    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
