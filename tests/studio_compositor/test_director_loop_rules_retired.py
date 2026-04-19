"""Regression pin for HOMAGE Phase F2 — director_loop expert-system rules retired.

Per ``docs/research/2026-04-19-expert-system-blinding-audit.md`` §A6:

- ``_narrative_too_similar`` second-guessed the director LLM by dropping
  its narrative into ``_emit_micromove_fallback`` 40+ times/12h.
- ``_maybe_rotate_repeated_activity`` mechanically rewrote the LLM's
  ``activity`` label to an ``observe/music/study/chat`` rotation when it
  had repeated 3 times in a row, firing 11+ times/12h including the
  pathological ``music → music`` self-rotation.

Both rules are retired. These tests pin the retirement: the methods are
gone from ``DirectorLoop``; the call sites no longer route through the
hardcoded ``_emit_micromove_fallback`` when a narrative repeats; the
activity label the LLM produced survives unchanged.

The ``_emit_micromove_fallback`` method body itself is preserved for
HOMAGE Phase F4 (post-live) retirement — it still serves the
LLM-empty-response path via ``continue`` with ``reason="llm_empty"``.
"""

from __future__ import annotations

from agents.studio_compositor.director_loop import DirectorLoop


class _FakeSlot:
    def __init__(self, slot_id: int) -> None:
        self.slot_id = slot_id
        self._title = "test video"
        self._channel = "test channel"
        self.is_active = slot_id == 0


class _FakeReactor:
    def set_header(self, *args, **kwargs) -> None:
        pass

    def set_text(self, *args, **kwargs) -> None:
        pass

    def set_speaking(self, *args, **kwargs) -> None:
        pass

    def feed_pcm(self, *args, **kwargs) -> None:
        pass


def _director() -> DirectorLoop:
    return DirectorLoop(
        video_slots=[_FakeSlot(0), _FakeSlot(1), _FakeSlot(2)],
        reactor_overlay=_FakeReactor(),
    )


class TestNarrativeTooSimilarRetired:
    """The ``_narrative_too_similar`` similarity check is gone."""

    def test_method_is_removed_from_director_loop(self) -> None:
        """Attribute lookup must fail — the method body has been deleted.

        Previously this method ran Jaccard + 3-shingle + 2-shingle
        dedup against a rolling history of the last 15 narratives and
        redirected the director tick to ``_emit_micromove_fallback``
        when it returned True. Post-retirement, nothing calls it and
        the binding no longer exists on the class.
        """
        director = _director()
        assert not hasattr(director, "_narrative_too_similar"), (
            "HOMAGE Phase F2 retirement: _narrative_too_similar must not exist "
            "on DirectorLoop. If this test fails, the rule was reintroduced "
            "or partially retired — check call site at director_loop.py around "
            "line 1094 in the pre-retirement revision."
        )

    def test_source_has_no_similar_narrative_micromove_call(self) -> None:
        """Grep-level pin: the narrative_repeat micromove-fallback call
        site must be absent from the director module source. A future
        refactor bringing back the call would silently regress the
        retirement even if the helper method stayed gone.
        """
        from pathlib import Path

        from agents.studio_compositor import director_loop

        src = Path(director_loop.__file__).read_text()
        assert 'reason="narrative_repeat"' not in src, (
            "HOMAGE Phase F2 retirement regressed: the narrative-repeat "
            "micromove-fallback call site is present in director_loop.py."
        )
        assert "_narrative_too_similar(" not in src, (
            "HOMAGE Phase F2 retirement regressed: a call to "
            "_narrative_too_similar was reintroduced in director_loop.py."
        )


class TestActivityRotationRetired:
    """The ``_maybe_rotate_repeated_activity`` enforcer is gone."""

    def test_method_is_removed_from_director_loop(self) -> None:
        """The enforcer used to mechanically rewrite the activity label
        after the LLM picked the same one 3× in a row. Post-retirement
        the method no longer exists and the LLM's choice is honored.
        """
        director = _director()
        assert not hasattr(director, "_maybe_rotate_repeated_activity"), (
            "HOMAGE Phase F2 retirement: _maybe_rotate_repeated_activity must "
            "not exist on DirectorLoop. If the LLM wants variety, it comes "
            "from the prompt / impingement side — not a post-hoc rewrite."
        )

    def test_source_has_no_rotation_call(self) -> None:
        """Grep-level pin: no call to the retired rotation enforcer."""
        from pathlib import Path

        from agents.studio_compositor import director_loop

        src = Path(director_loop.__file__).read_text()
        assert "_maybe_rotate_repeated_activity(" not in src, (
            "HOMAGE Phase F2 retirement regressed: a call to "
            "_maybe_rotate_repeated_activity was reintroduced in director_loop.py."
        )

    def test_activity_label_survives_unchanged(self) -> None:
        """Direct invariant: without the enforcer, an activity label the
        LLM chose passes through the tick path untouched. This test
        exercises ``_maybe_override_activity`` (which remains — it is a
        stimmung-driven override, not a repetition rewriter) and asserts
        that the output equals the input whenever stimmung is nominal
        and no override criterion fires.

        If future refactors reintroduce a categorical rewrite, the label
        that comes out of ``_maybe_override_activity`` will diverge from
        the one going in for a repeated label, and this test flags it.
        """
        director = _director()
        # Simulate three prior "music" activities — the retired enforcer
        # would have rewritten a 4th "music" to the next rotation slot.
        director._recent_activities = ["music", "music", "music"]
        # _maybe_override_activity is stimmung-driven; without any
        # stimmung signal it is a no-op pass-through.
        out = director._maybe_override_activity("music")
        assert out == "music", (
            f"activity label was rewritten from 'music' to {out!r}; HOMAGE "
            "Phase F2 retirement regressed or a new post-hoc rewrite rule "
            "was added."
        )


class TestMicromoveFallbackBodyPreserved:
    """Phase F2 is scoped: the ``_emit_micromove_fallback`` method stays.

    F4 (post-live) retires it once the 7 hardcoded tuples are registered
    as capabilities that the AffordancePipeline can recruit against. Until
    then, the llm-empty-response path and the silence/empty-text path
    still route through it.
    """

    def test_emit_micromove_fallback_still_exists(self) -> None:
        director = _director()
        assert hasattr(director, "_emit_micromove_fallback"), (
            "HOMAGE Phase F2 scope violation: _emit_micromove_fallback was "
            "removed, but F2 only retires the CALL SITES for narrative_repeat "
            "and activity-rotation. The method body stays for F4 post-live."
        )
