"""Deterministic session inference — answers 'where did the operator leave off'.

Zero LLM. Reads telemetry signals (stimmung, sprint state, git recency, vault mtime)
and produces a SessionContext consumed by the orientation collector.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

STIMMUNG_STATE = Path("/dev/shm/hapax-stimmung/state.json")
SPRINT_STATE = Path("/dev/shm/hapax-sprint/state.json")
SESSION_BOUNDARY_HOURS = 2.0
PROJECTS_DIR = Path.home() / "projects"
VAULT_BASE = Path.home() / "Documents" / "Personal"


@dataclass
class SessionContext:
    """Inferred session state for the orientation system."""

    last_active_domain: str = ""
    last_active_goal: str | None = None
    last_active_measure: str | None = None
    absence_hours: float = 0.0
    session_boundary: bool = False  # True if absence > 2h
    domain_recency: dict[str, float] = field(default_factory=dict)
    active_signals: list[str] = field(default_factory=list)


def _read_stimmung() -> dict:
    """Read stimmung state from shared memory. Returns {} on failure."""
    try:
        return json.loads(STIMMUNG_STATE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _read_sprint_state() -> dict:
    """Read sprint state from shared memory. Returns {} on failure."""
    try:
        return json.loads(SPRINT_STATE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _git_recency(repos: list[str] | None = None) -> dict[str, float]:
    """Return {repo_name: hours_since_last_commit} for each repo."""
    if not repos:
        return {}
    now = time.time()
    result: dict[str, float] = {}
    for repo in repos:
        repo_path = PROJECTS_DIR / repo
        if not repo_path.is_dir():
            continue
        try:
            proc = subprocess.run(
                ["git", "-C", str(repo_path), "log", "-1", "--format=%ct"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                commit_ts = float(proc.stdout.strip())
                result[repo] = (now - commit_ts) / 3600.0
        except (subprocess.TimeoutExpired, ValueError):
            continue
    return result


def _vault_recency(vault_paths: list[str] | None = None) -> float:
    """Return hours since newest .md file across given vault paths."""
    if not vault_paths:
        return 999.0
    now = time.time()
    newest_mtime = 0.0
    for vpath in vault_paths:
        full = VAULT_BASE / vpath
        if not full.is_dir():
            continue
        for md in full.rglob("*.md"):
            try:
                mt = md.stat().st_mtime
                if mt > newest_mtime:
                    newest_mtime = mt
            except OSError:
                continue
    if newest_mtime == 0.0:
        return 999.0
    return (now - newest_mtime) / 3600.0


def infer_session(*, domains: dict[str, dict] | None = None) -> SessionContext:
    """Infer current session context from telemetry signals.

    Args:
        domains: Optional mapping of domain_name -> config dict with keys:
            - repos: list[str] — git repo names under PROJECTS_DIR
            - vault_paths: list[str] — paths relative to VAULT_BASE
    """
    ctx = SessionContext()
    stimmung = _read_stimmung()
    sprint = _read_sprint_state()

    # --- Absence detection from IR presence ---
    last_detected = stimmung.get("last_person_detected_at")
    if last_detected is not None:
        ctx.absence_hours = (time.time() - float(last_detected)) / 3600.0
        ctx.session_boundary = ctx.absence_hours >= SESSION_BOUNDARY_HOURS
        ctx.active_signals.append("ir_presence")

    # --- Sprint state ---
    if sprint.get("active_measure"):
        ctx.last_active_measure = sprint["active_measure"]
        ctx.active_signals.append("sprint_state")
    if sprint.get("active_goal"):
        ctx.last_active_goal = sprint["active_goal"]

    # --- Domain recency ---
    if not domains:
        return ctx

    # Collect all repos across domains for a single git batch
    all_repos: list[str] = []
    for domain_cfg in domains.values():
        all_repos.extend(domain_cfg.get("repos", []))
    git_hours = _git_recency(all_repos if all_repos else None)

    for domain_name, domain_cfg in domains.items():
        best = 999.0

        # Git recency for this domain's repos
        for repo in domain_cfg.get("repos", []):
            if repo in git_hours:
                best = min(best, git_hours[repo])

        # Vault recency for this domain's paths
        vault_paths = domain_cfg.get("vault_paths")
        if vault_paths:
            vault_h = _vault_recency(vault_paths)
            best = min(best, vault_h)

        if best < 999.0:
            ctx.domain_recency[domain_name] = best

    # Pick most recent domain
    if ctx.domain_recency:
        ctx.last_active_domain = min(ctx.domain_recency, key=ctx.domain_recency.get)  # type: ignore[arg-type]

    return ctx
