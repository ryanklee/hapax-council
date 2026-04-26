"""Axiom-check primitives.

Three public entrypoints:

* `scan_text(text)` — generic regex pass over arbitrary text.
* `scan_file(path)` — open a source file and scan its contents (skips files
  that exceed `max_bytes`, defaulting to 1 MiB).
* `scan_commit_message(message)` — scan a commit-message string after
  stripping comment lines, the way `git commit-msg` hooks expect.

All three return `list[Violation]`. Caller decides whether T0 violations
abort the operation.

Sub-millisecond regex matching, no LLM calls, no I/O beyond the file read.
Pattern compilation is cached per-process.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from hapax_axioms.models import Pattern, Tier
from hapax_axioms.registry import load_patterns

_DEFAULT_MAX_BYTES = 1 * 1024 * 1024

_TIER_ORDER: dict[Tier, int] = {"T0": 0, "T1": 1, "T2": 2, "T3": 3}


@dataclass(frozen=True)
class Violation:
    """A single match against an axiom-violation pattern."""

    pattern_id: str
    axiom_id: str
    implication_id: str
    tier: Tier
    matched_text: str
    line_number: int
    description: str

    def format(self) -> str:
        """Format a single human-readable line — useful for hook output."""
        return (
            f"[{self.tier}] {self.axiom_id}/{self.implication_id} "
            f"(line {self.line_number}): {self.matched_text!r} — {self.description.strip()}"
        )


_compiled_cache: tuple[tuple[Pattern, re.Pattern[str]], ...] | None = None


def _compiled_patterns(
    *,
    patterns: Iterable[Pattern] | None = None,
) -> tuple[tuple[Pattern, re.Pattern[str]], ...]:
    """Compile and cache patterns. Pass `patterns=` to bypass the cache."""
    global _compiled_cache
    if patterns is not None:
        return tuple((p, re.compile(p.regex, re.IGNORECASE)) for p in patterns)
    if _compiled_cache is None:
        bundle = load_patterns()
        _compiled_cache = tuple((p, re.compile(p.regex, re.IGNORECASE)) for p in bundle.patterns)
    return _compiled_cache


def reload_patterns() -> None:
    """Invalidate the compiled-pattern cache (test/hot-reload helper)."""
    global _compiled_cache
    _compiled_cache = None


def _line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def scan_text(
    text: str,
    *,
    tier_filter: Tier | None = None,
    axiom_filter: str | None = None,
    patterns: Iterable[Pattern] | None = None,
) -> list[Violation]:
    """Scan arbitrary text for axiom-violation pattern matches.

    Args:
        text: Source code, commit message, or any other text body.
        tier_filter: If set, only report violations at this tier.
        axiom_filter: If set, only report violations for this axiom_id.
        patterns: Optional iterable to override the bundled set (bypasses cache).
    """
    out: list[Violation] = []
    for pat, compiled in _compiled_patterns(patterns=patterns):
        if tier_filter is not None and pat.tier != tier_filter:
            continue
        if axiom_filter is not None and pat.axiom_id != axiom_filter:
            continue
        for match in compiled.finditer(text):
            out.append(
                Violation(
                    pattern_id=pat.id,
                    axiom_id=pat.axiom_id,
                    implication_id=pat.implication_id,
                    tier=pat.tier,
                    matched_text=match.group(),
                    line_number=_line_for_offset(text, match.start()),
                    description=pat.description,
                ),
            )
    out.sort(key=lambda v: (_TIER_ORDER.get(v.tier, 9), v.line_number))
    return out


def scan_file(
    path: Path | str,
    *,
    tier_filter: Tier | None = None,
    axiom_filter: str | None = None,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    patterns: Iterable[Pattern] | None = None,
) -> list[Violation]:
    """Scan a single file for axiom violations.

    Returns an empty list for files that don't exist, exceed `max_bytes`,
    or are binary (decode error). Use `scan_text` for in-memory content.
    """
    p = Path(path)
    if not p.is_file():
        return []
    try:
        if p.stat().st_size > max_bytes:
            return []
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return scan_text(
        text,
        tier_filter=tier_filter,
        axiom_filter=axiom_filter,
        patterns=patterns,
    )


def scan_commit_message(
    message: str,
    *,
    tier_filter: Tier | None = None,
    axiom_filter: str | None = None,
    patterns: Iterable[Pattern] | None = None,
) -> list[Violation]:
    """Scan a commit message after stripping git comment lines.

    Mirrors the behaviour expected of a `commit-msg` hook: any line whose
    first non-whitespace character is `#` is treated as a comment and
    omitted before pattern matching.
    """
    cleaned = "\n".join(line for line in message.splitlines() if not line.lstrip().startswith("#"))
    return scan_text(
        cleaned,
        tier_filter=tier_filter,
        axiom_filter=axiom_filter,
        patterns=patterns,
    )
