#!/usr/bin/env python3
"""SDLC Issue Triage Agent.

Classifies GitHub issues by type, complexity, and axiom relevance.
Outputs structured JSON for workflow consumption.

Usage::

    uv run python -m scripts.sdlc_triage --issue-number 42
    uv run python -m scripts.sdlc_triage --issue-number 42 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

# Ensure project root is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.axiom_registry import load_axioms
from shared.langfuse_trace_export import TraceContext, is_file_export
from shared.sdlc_github import fetch_issue

# ---------------------------------------------------------------------------
# Structured output model
# ---------------------------------------------------------------------------


class TriageResult(BaseModel):
    type: Literal["bug", "feature", "chore"]
    complexity: Literal["S", "M", "L"]
    axiom_relevance: list[str]
    reject_reason: str | None = None
    file_hints: list[str] = []


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

PROTECTED_PATHS = [
    "agents/health_monitor.py",
    "shared/alert_state.py",
    "shared/axiom_enforcement.py",
    "shared/config.py",
    "axioms/",
    "hooks/",
    "systemd/",
    "hapax-backup-*.sh",
]


def _build_system_prompt(axioms: list) -> str:
    axiom_text = "\n".join(
        f"- **{a.id}**: {a.text.strip()}" for a in axioms
    )
    return f"""\
You are the triage agent for hapax-council, a single-user personal operating system.

Your job is to classify a GitHub issue by type, complexity, and axiom relevance.

## Constitutional Axioms
{axiom_text}

## Complexity Heuristics
- **S** (small): Single file change, isolated fix, clear solution path.
- **M** (medium): 2-5 files, moderate logic changes, tests need updating.
- **L** (large): Architectural, cross-cutting, > 5 files, ambiguous requirements.

## Rejection Criteria (set reject_reason if any apply)
- Complexity is L (too large for automated implementation).
- Requirements are ambiguous or missing acceptance criteria.
- Changes touch protected paths: {', '.join(PROTECTED_PATHS)}.
- Issue requires architectural decisions the operator should make.

## Output
Return a JSON object with:
- type: "bug" | "feature" | "chore"
- complexity: "S" | "M" | "L"
- axiom_relevance: list of axiom IDs relevant to this change (can be empty)
- reject_reason: null if agent-eligible, or a string explaining why not
- file_hints: list of file paths likely involved (best guess from issue description)
"""


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------


def _call_llm(system: str, user: str, *, dry_run: bool = False) -> TriageResult:
    if dry_run:
        return TriageResult(
            type="chore",
            complexity="S",
            axiom_relevance=[],
            reject_reason=None,
            file_hints=[],
        )

    try:
        import anthropic
    except ImportError:
        # Fall back to pydantic-ai via litellm for local dev.
        from pydantic_ai import Agent

        agent = Agent(
            os.environ.get("SDLC_TRIAGE_MODEL", "anthropic:claude-sonnet-4-6"),
            system_prompt=system,
            output_type=TriageResult,
        )
        result = agent.run_sync(user)
        return result.output

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=os.environ.get("SDLC_TRIAGE_MODEL", "claude-sonnet-4-6"),
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = response.content[0].text
    # Parse JSON from response (may be wrapped in ```json blocks).
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return TriageResult.model_validate_json(text.strip())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_triage(issue_number: int, *, dry_run: bool = False) -> TriageResult:
    """Triage a GitHub issue and return structured result."""
    issue = fetch_issue(issue_number)
    axioms = load_axioms(scope="constitutional")

    system_prompt = _build_system_prompt(axioms)
    user_prompt = f"# {issue.title}\n\n{issue.body}"

    trace_id = f"sdlc-triage-{issue_number}"
    with TraceContext("triage", trace_id, issue_number=issue_number) as span:
        result = _call_llm(system_prompt, user_prompt, dry_run=dry_run)
        span.model = os.environ.get("SDLC_TRIAGE_MODEL", "claude-sonnet-4-6")
        span.output_text = result.model_dump_json()

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="SDLC Issue Triage Agent")
    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true", help="Use fixture response")
    args = parser.parse_args()

    if not args.dry_run and not is_file_export():
        try:
            from shared import langfuse_config  # noqa: F401
        except ImportError:
            pass

    result = run_triage(args.issue_number, dry_run=args.dry_run)
    print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    main()
