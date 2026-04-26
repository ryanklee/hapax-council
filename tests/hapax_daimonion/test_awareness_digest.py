"""Pure-logic tests for ``agents.hapax_daimonion.awareness_digest``."""

from __future__ import annotations

from agents.hapax_daimonion.awareness_digest import (
    CONDENSE_SYSTEM_PROMPT,
    AwarenessDigestState,
    build_condense_prompt,
    extract_awareness_section,
    is_mode_shift,
    is_stimmung_threshold_cross,
    stimmung_bucket,
    update_for_event,
)


class TestStimmungBucket:
    def test_low_load_below_threshold(self) -> None:
        assert stimmung_bucket(0.0) == "low_load"
        assert stimmung_bucket(0.32) == "low_load"

    def test_nominal_in_middle(self) -> None:
        assert stimmung_bucket(0.33) == "nominal"
        assert stimmung_bucket(0.5) == "nominal"
        assert stimmung_bucket(0.65) == "nominal"

    def test_high_load_above_threshold(self) -> None:
        assert stimmung_bucket(0.66) == "high_load"
        assert stimmung_bucket(1.0) == "high_load"


class TestModeShift:
    def test_first_event_triggers(self) -> None:
        s = AwarenessDigestState()
        assert is_mode_shift(s, "research") is True

    def test_same_mode_does_not_trigger(self) -> None:
        s = AwarenessDigestState(last_mode="rnd")
        assert is_mode_shift(s, "rnd") is False

    def test_different_mode_triggers(self) -> None:
        s = AwarenessDigestState(last_mode="research")
        assert is_mode_shift(s, "fortress") is True


class TestStimmungThresholdCross:
    def test_first_event_triggers(self) -> None:
        s = AwarenessDigestState()
        assert is_stimmung_threshold_cross(s, 0.5) is True

    def test_same_bucket_does_not_trigger(self) -> None:
        s = AwarenessDigestState(last_stimmung_bucket="nominal")
        assert is_stimmung_threshold_cross(s, 0.5) is False

    def test_low_to_high_triggers(self) -> None:
        s = AwarenessDigestState(last_stimmung_bucket="low_load")
        assert is_stimmung_threshold_cross(s, 0.8) is True

    def test_within_bucket_micro_drift(self) -> None:
        # Drifting within the nominal range should not re-trigger.
        s = AwarenessDigestState(last_stimmung_bucket="nominal")
        assert is_stimmung_threshold_cross(s, 0.34) is False
        assert is_stimmung_threshold_cross(s, 0.65) is False


class TestUpdateForEvent:
    def test_mode_event_advances_state(self) -> None:
        s = AwarenessDigestState()
        triggered = update_for_event(s, mode="research")
        assert triggered is True
        assert s.last_mode == "research"
        # Same mode again — no trigger
        triggered2 = update_for_event(s, mode="research")
        assert triggered2 is False

    def test_stimmung_event_advances_state(self) -> None:
        s = AwarenessDigestState()
        triggered = update_for_event(s, stimmung_value=0.8)
        assert triggered is True
        assert s.last_stimmung_bucket == "high_load"
        # Stay in high_load
        triggered2 = update_for_event(s, stimmung_value=0.9)
        assert triggered2 is False

    def test_mode_dominates_when_both_set(self) -> None:
        # When both kwargs are passed, mode takes precedence per the
        # docstring contract — coarser-grained signals dominate.
        s = AwarenessDigestState(last_mode="rnd", last_stimmung_bucket="nominal")
        triggered = update_for_event(s, mode="rnd", stimmung_value=0.9)
        assert triggered is False
        # Stimmung bucket NOT advanced (only the dominant arm acted)
        assert s.last_stimmung_bucket == "nominal"

    def test_no_kwargs_is_noop(self) -> None:
        s = AwarenessDigestState(last_mode="research")
        assert update_for_event(s) is False
        assert s.last_mode == "research"


class TestExtractAwarenessSection:
    def test_simple_extraction(self) -> None:
        note = """\
# Daily 2026-04-26

## Log
- did stuff

## Awareness
Important fact A.
Important fact B.

## Refused
- spam from foo
"""
        body = extract_awareness_section(note)
        assert "Important fact A." in body
        assert "Important fact B." in body
        assert "spam from foo" not in body

    def test_section_at_end_of_file(self) -> None:
        note = "## Log\n- a\n\n## Awareness\nlast section content\n"
        body = extract_awareness_section(note)
        assert body == "last section content"

    def test_missing_section_returns_empty(self) -> None:
        note = "## Log\n- nothing\n"
        assert extract_awareness_section(note) == ""

    def test_case_insensitive_header(self) -> None:
        note = "## awareness\nlowercase header still matches\n"
        assert "lowercase header" in extract_awareness_section(note)


class TestBuildCondensePrompt:
    def test_returns_two_message_pair(self) -> None:
        msgs = build_condense_prompt("some awareness text")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
        assert msgs[0]["content"] == CONDENSE_SYSTEM_PROMPT

    def test_user_message_includes_section(self) -> None:
        msgs = build_condense_prompt("important fact")
        assert "important fact" in msgs[1]["content"]

    def test_empty_section_marked_explicitly(self) -> None:
        msgs = build_condense_prompt("")
        assert "(empty)" in msgs[1]["content"]

    def test_system_prompt_carries_referent_policy(self) -> None:
        # Pin: every operator-facing prompt template MUST list the
        # 4 sanctioned non-formal referents per project_operator_referent_policy.
        for ref in ("The Operator", "Oudepode", "OTO"):
            assert ref in CONDENSE_SYSTEM_PROMPT
