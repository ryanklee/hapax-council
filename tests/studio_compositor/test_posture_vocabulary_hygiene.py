"""A7: posture-vocabulary hygiene regression pin.

Posture vocabulary is a *glossary* for about-Hapax talk. It must NOT leak
into LLM prompt scaffolding or typed schemas the LLM observes. A leak
reifies posture as something Hapax performs, which invites personification
— the exact failure the LRR Phase 7 redesign was meant to prevent.

This test walks every string literal in the two director modules and
asserts none of them contains a posture-vocabulary token (the leaf names
defined in ``axioms/persona/posture-vocabulary.md``). The vocabulary
document itself is the source of truth — we parse it at test time so
additions/deletions to the glossary automatically update the test.

History: a literal ``"research-foregrounded"`` in ``structural_director``'s
``SceneMode`` Literal was caught in the Epic-2 audit (A1).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VOCAB_DOC = _REPO_ROOT / "axioms" / "persona" / "posture-vocabulary.md"
_FILES_UNDER_TEST = [
    _REPO_ROOT / "agents" / "studio_compositor" / "director_loop.py",
    _REPO_ROOT / "agents" / "studio_compositor" / "structural_director.py",
]

# Stance values are legitimate architectural state the LLM is allowed to
# observe in prompts and emit in DirectorIntent.stance. They happen to
# overlap with some posture-vocabulary entries (the glossary sometimes
# uses a stance value when the posture is defined primarily by that
# stance). Exclude them from the leak check — the thing we're catching
# is *posture-only* vocabulary (observing, drafting, research-foregrounded,
# etc.), not stance names.
_STANCE_VALUES: frozenset[str] = frozenset(
    {"nominal", "cautious", "seeking", "degraded", "critical"}
)


def _read_posture_tokens() -> set[str]:
    """Parse the vocabulary doc for every ``### `token``` header, excluding stance values."""
    text = _VOCAB_DOC.read_text(encoding="utf-8")
    matches = re.findall(r"^###\s+`([^`]+)`", text, re.MULTILINE)
    return {m.strip() for m in matches} - _STANCE_VALUES


def _collect_string_literals(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    strings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append((node.lineno, node.value))
    return strings


@pytest.mark.parametrize("path", _FILES_UNDER_TEST, ids=lambda p: p.name)
def test_no_posture_vocabulary_token_in_string_literals(path: Path) -> None:
    tokens = _read_posture_tokens()
    assert tokens, "posture vocabulary parse returned nothing — document moved?"
    strings = _collect_string_literals(path)
    offenders: list[str] = []
    for lineno, literal in strings:
        for token in tokens:
            if re.search(rf"(?<![\w-]){re.escape(token)}(?![\w-])", literal):
                offenders.append(
                    f"{path.name}:{lineno}: literal contains posture token '{token}'\n"
                    f"    literal: {literal!r}"
                )
    assert not offenders, (
        "Posture-vocabulary leak into LLM-adjacent string literals:\n"
        + "\n".join(offenders)
        + "\n\nPostures are named consequences of architectural state "
        "(axioms/persona/posture-vocabulary.md). They must not appear in "
        "prompt scaffolding, Literal types, or any string the LLM observes. "
        "If you need a state name for the LLM, pick a non-posture term."
    )


def test_posture_vocabulary_source_is_parseable() -> None:
    tokens = _read_posture_tokens()
    # Anchor on the canonical LRR-Phase-7 set so drift in the parser shows up
    # here, not silently in the main test.
    assert "focused" in tokens
    assert "research-foregrounded" in tokens
    assert "drafting" in tokens
