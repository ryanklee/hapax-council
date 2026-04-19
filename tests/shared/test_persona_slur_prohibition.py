"""Ring 1 unit tests for the persona-level slur prohibition clause.

Research doc: docs/research/2026-04-20-prompt-level-slur-prohibition-design.md
§3.3 Ring 1 (Golden path — mock LLM, composer assertions).

These tests pin the invariant that every LLM prompt assembled via
:func:`shared.persona_prompt_composer.compose_persona_prompt` carries the
slur-prohibition clause AND at least one member of the substitute pool
from :data:`shared.speech_safety.REDACTION_SUBSTITUTE_POOL`.
"""

from __future__ import annotations

import pytest

from shared.persona_prompt_composer import (
    KNOWN_ROLE_IDS,
    compose_persona_prompt,
)
from shared.speech_safety import REDACTION_SUBSTITUTE_POOL


def test_full_fragment_contains_prohibition_sentinel():
    out = compose_persona_prompt(enforce=False)
    assert "Broadcast-safety absolute invariant — slurs" in out


def test_full_fragment_references_substitute_pool():
    out = compose_persona_prompt(enforce=False)
    assert any(sub in out for sub in REDACTION_SUBSTITUTE_POOL)


def test_every_role_fragment_carries_prohibition():
    for role_id in KNOWN_ROLE_IDS:
        out = compose_persona_prompt(role_id=role_id, enforce=False)
        assert "Broadcast-safety absolute invariant — slurs" in out, (
            f"role {role_id!r} missing prohibition clause"
        )


def test_enforce_mode_raises_when_sentinel_missing(monkeypatch, tmp_path):
    # Write a stub persona file that is missing the sentinel.
    stub = tmp_path / "stub.prompt.md"
    stub.write_text("You are Hapax. No broadcast safety clause here.\n")
    from shared import persona_prompt_composer as mod

    monkeypatch.setattr(mod, "PERSONA_PROMPT_PATH", stub)
    mod.reset_cache_for_testing()
    try:
        # Disable the anti-personification linter for this test — the
        # stub text does not exercise the linter surface and we only
        # care about the sentinel check firing.
        with pytest.raises(AssertionError, match="slur-prohibition sentinel missing"):
            compose_persona_prompt(enforce=True)
    finally:
        # Reset the lru_cache so the real persona file is reloaded for
        # subsequent tests in the same module.
        mod.reset_cache_for_testing()


def test_enforce_mode_passes_when_sentinel_present():
    # The real persona file should pass enforce=True. If not, this test
    # AND the anti-personification linter catch the regression.
    out = compose_persona_prompt(enforce=True)
    assert "Broadcast-safety absolute invariant — slurs" in out
    assert any(sub in out for sub in REDACTION_SUBSTITUTE_POOL)


def test_compressed_fragment_does_not_require_sentinel():
    # Compressed fragment is for LOCAL tier voice; inherits from
    # downstream gate rather than carrying the clause itself.
    # enforce=True should NOT raise on compressed output.
    out = compose_persona_prompt(compressed=True, enforce=True)
    # It's a short fragment; no sentinel required.
    assert len(out) > 0


def test_prohibition_lists_all_known_variant_forms():
    out = compose_persona_prompt(enforce=False)
    # The clause must name enough variants to cue the model. Spot-check
    # the discriminators that slipped past the original regex on
    # 2026-04-20 14:08: 'niggah' / 'niggaz' / 'nigguh'. These being
    # in the prompt anchors the model's generation distribution.
    assert "niggah" in out or "niggaz" in out or "nigguh" in out, (
        "prohibition clause must reference at least one h/z-terminal variant "
        "so the LLM anchors on the full family, not just the canonical form"
    )


def test_prohibition_references_research_mode_strengthening():
    out = compose_persona_prompt(enforce=False)
    assert "research mode" in out.lower(), (
        "research-context strengthening is load-bearing per design doc §3.2 — "
        "the 2026-04-20 leak happened while narrating rap analysis"
    )
