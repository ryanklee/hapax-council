"""Tests for shared.research_condition."""

from __future__ import annotations

import pytest

from shared.research_condition import (
    UNKNOWN_CONDITION_LABEL,
    ConditionUnavailable,
    get_current_condition,
    get_current_condition_strict,
)


class TestGetCurrentConditionStrict:
    def test_missing_pointer_raises(self, tmp_path):
        with pytest.raises(ConditionUnavailable):
            get_current_condition_strict(tmp_path / "nope.txt")

    def test_empty_pointer_raises(self, tmp_path):
        p = tmp_path / "current.txt"
        p.write_text("")
        with pytest.raises(ConditionUnavailable):
            get_current_condition_strict(p)

    def test_whitespace_only_raises(self, tmp_path):
        p = tmp_path / "current.txt"
        p.write_text("   \n  ")
        with pytest.raises(ConditionUnavailable):
            get_current_condition_strict(p)

    def test_returns_condition(self, tmp_path):
        p = tmp_path / "current.txt"
        p.write_text("qwen3.5-9b-baseline\n")
        assert get_current_condition_strict(p) == "qwen3.5-9b-baseline"


class TestGetCurrentCondition:
    def test_missing_returns_unknown(self, tmp_path):
        assert get_current_condition(tmp_path / "nope.txt") == UNKNOWN_CONDITION_LABEL

    def test_empty_returns_unknown(self, tmp_path):
        p = tmp_path / "current.txt"
        p.write_text("")
        assert get_current_condition(p) == UNKNOWN_CONDITION_LABEL

    def test_normal_returns_value(self, tmp_path):
        p = tmp_path / "current.txt"
        p.write_text("olmo-3-7b-instruct")
        assert get_current_condition(p) == "olmo-3-7b-instruct"
