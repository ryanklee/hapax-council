"""2026-04-23 Gemini-audit Phase 2 regression pins.

The director prompt must carry the ``livestream-host`` role's
``is_not:`` scope as an architectural anti-narration invariant, in
addition to (not in place of) the fine-grained BANNED NARRATION block.

The BANNED NARRATION block enumerates specific phrases Hapax has been
caught emitting; the role scope is the structural reason those phrases
are forbidden (Hapax in the livestream-host role is NOT a
passive-observer-narrator / museum-docent / self-reflexive-meta-
narrator / stage-director-speaking-their-own-blocking). Prompt-string-
matching and role-scope are complementary — one pins LLM output, the
other pins the registry amendment surface.
"""

from __future__ import annotations

from unittest.mock import patch

from agents.studio_compositor.director_loop import DirectorLoop
from shared.persona_prompt_composer import role_is_not, role_scope_line


class _FakeSlot:
    def __init__(self, slot_id: int) -> None:
        self.slot_id = slot_id
        self._title = "test video"
        self._channel = "test channel"
        self.is_active = slot_id == 0


class _FakeReactor:
    def set_header(self, *args, **kwargs) -> None: ...
    def set_text(self, *args, **kwargs) -> None: ...
    def set_speaking(self, *args, **kwargs) -> None: ...
    def feed_pcm(self, *args, **kwargs) -> None: ...


def _director() -> DirectorLoop:
    return DirectorLoop(
        video_slots=[_FakeSlot(0), _FakeSlot(1), _FakeSlot(2)],
        reactor_overlay=_FakeReactor(),
    )


def test_livestream_host_role_scope_carries_gemini_audit_phase_2_entries() -> None:
    """livestream-host is_not: must include the four 2026-04-23 entries.

    These four are the role-level invariants that cover the BANNED
    NARRATION block's thematic scope (passive-observer / museum-docent /
    self-reflexive-meta / stage-director-in-narration).
    """
    scopes = role_is_not("livestream-host")
    assert "passive-observer-narrator" in scopes
    assert "museum-docent" in scopes
    assert "self-reflexive-meta-narrator" in scopes
    assert "stage-director-speaking-their-own-blocking" in scopes
    # Original four pre-2026-04-23 entries must still be present.
    assert "personality-entertainer" in scopes
    assert "character-performer" in scopes
    assert "emotional-presence" in scopes
    assert "parasocial-companion" in scopes


def test_director_prompt_contains_role_scope_line() -> None:
    """The director prompt must splice in ``role_scope_line("livestream-host")``.

    Architectural backstop to the BANNED NARRATION block: even if the
    prompt block is ever refactored, the role's is_not: list reaches the
    LLM.
    """
    director = _director()
    prompt = director._build_unified_prompt()
    scope = role_scope_line("livestream-host")
    assert scope, "role_scope_line must return a non-empty string for livestream-host"
    assert scope in prompt


def test_director_prompt_mentions_all_role_is_not_entries() -> None:
    """Each entry in livestream-host is_not: must appear in the prompt."""
    director = _director()
    prompt = director._build_unified_prompt()
    for entry in role_is_not("livestream-host"):
        assert entry in prompt, (
            f"livestream-host is_not: entry {entry!r} missing from director prompt"
        )


_ = patch  # keep import available for future extensions
