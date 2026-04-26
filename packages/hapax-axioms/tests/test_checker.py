"""Tests for the axiom-check primitives.

These tests construct violation strings dynamically (no inline axiom
trigger literals in the test source) so the test file itself does not
trip pre-commit axiom scanners that may run over the council monorepo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hapax_axioms.checker import (
    Violation,
    reload_patterns,
    scan_commit_message,
    scan_file,
    scan_text,
)

# Build trigger snippets at runtime so the literal strings only exist in
# memory during test execution. Prevents the council repo's own axiom
# hooks from scanning these test bodies and erroring.
_USER_MGR = "class " + "User" + "Manager:\n    pass\n"
_LOGIN = "def " + "authenticate" + "_user(token):\n    return True\n"
_PERM = "def " + "check" + "_permission(op):\n    return True\n"
_FEEDBACK_FN = "def " + "generate" + "_feedback(person):\n    return ''\n"
_FEEDBACK_CLS = "class " + "Feedback" + "Generator:\n    pass\n"


@pytest.fixture(autouse=True)
def _flush_pattern_cache() -> None:
    reload_patterns()
    yield
    reload_patterns()


def test_clean_text_returns_no_violations() -> None:
    body = "def add(a: int, b: int) -> int:\n    return a + b\n"
    assert scan_text(body) == []


def test_user_manager_triggers_single_user_block() -> None:
    hits = scan_text(_USER_MGR)
    assert hits, "expected single_user violation for user-manager class"
    assert all(isinstance(v, Violation) for v in hits)
    assert any(v.axiom_id == "single_user" and v.tier == "T0" for v in hits)


def test_login_function_triggers_single_user_block() -> None:
    hits = scan_text(_LOGIN)
    assert any(v.axiom_id == "single_user" for v in hits)


def test_permission_check_triggers_single_user_block() -> None:
    hits = scan_text(_PERM)
    assert any(v.axiom_id == "single_user" for v in hits)


def test_feedback_function_triggers_management_governance_block() -> None:
    hits = scan_text(_FEEDBACK_FN)
    assert any(v.axiom_id == "management_governance" and v.tier == "T0" for v in hits)


def test_feedback_class_triggers_management_governance_block() -> None:
    hits = scan_text(_FEEDBACK_CLS)
    assert any(v.axiom_id == "management_governance" for v in hits)


def test_axiom_filter_restricts_results() -> None:
    body = _USER_MGR + _FEEDBACK_FN
    only_su = scan_text(body, axiom_filter="single_user")
    only_mg = scan_text(body, axiom_filter="management_governance")
    assert only_su, "expected single_user hit"
    assert only_mg, "expected management_governance hit"
    assert all(v.axiom_id == "single_user" for v in only_su)
    assert all(v.axiom_id == "management_governance" for v in only_mg)


def test_tier_filter_restricts_results() -> None:
    hits_t0 = scan_text(_USER_MGR, tier_filter="T0")
    hits_t2 = scan_text(_USER_MGR, tier_filter="T2")
    assert hits_t0
    assert hits_t2 == []


def test_violation_format_is_human_readable() -> None:
    [v, *_] = scan_text(_USER_MGR)
    formatted = v.format()
    assert "T0" in formatted
    assert "single_user" in formatted


def test_violation_line_numbers_are_one_indexed() -> None:
    body = "# header line\n# second comment\n" + _USER_MGR
    [v, *_] = scan_text(body)
    assert v.line_number == 3


def test_scan_file_reads_source(tmp_path: Path) -> None:
    target = tmp_path / "bad.py"
    target.write_text(_USER_MGR, encoding="utf-8")
    hits = scan_file(target)
    assert hits, "expected scan_file to surface violations"
    assert all(isinstance(v, Violation) for v in hits)


def test_scan_file_handles_missing(tmp_path: Path) -> None:
    assert scan_file(tmp_path / "no-such-file.py") == []


def test_scan_file_skips_oversized(tmp_path: Path) -> None:
    target = tmp_path / "big.py"
    target.write_text(_USER_MGR, encoding="utf-8")
    assert scan_file(target, max_bytes=1) == []


def test_scan_file_handles_binary(tmp_path: Path) -> None:
    target = tmp_path / "blob.bin"
    target.write_bytes(b"\x00\x01\x02\xff\xfe")
    assert scan_file(target) == []


def test_scan_commit_message_strips_comment_lines() -> None:
    msg = "feat(governance): add manager\n\n# " + _USER_MGR
    # The trigger lives only in a `#`-prefixed comment. Should not fire.
    assert scan_commit_message(msg) == []


def test_scan_commit_message_catches_body_violations() -> None:
    msg = "chore: refactor\n\n" + _USER_MGR
    hits = scan_commit_message(msg)
    assert any(v.axiom_id == "single_user" for v in hits)


def test_results_are_sorted_t0_first_then_line() -> None:
    body = "\n\n\n" + _USER_MGR + "\n\n" + _LOGIN
    hits = scan_text(body)
    assert hits[0].line_number <= hits[-1].line_number
    assert all(v.tier == "T0" for v in hits)
