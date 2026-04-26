"""End-to-end tests for the hapax-axioms CLI."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from hapax_axioms.cli import main

# Trigger built at runtime — see tests/test_checker.py rationale.
_USER_MGR = "class " + "User" + "Manager:\n    pass\n"


def test_list_axioms(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["list-axioms"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "single_user" in captured.out
    assert "interpersonal_transparency" in captured.out


def test_scan_file_clean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = tmp_path / "ok.py"
    p.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    rc = main(["scan-file", str(p)])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.err == ""


def test_scan_file_violation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = tmp_path / "bad.py"
    p.write_text(_USER_MGR, encoding="utf-8")
    rc = main(["scan-file", str(p)])
    captured = capsys.readouterr()
    assert rc == 2
    assert "single_user" in captured.err


def test_scan_commit_msg_clean(tmp_path: Path) -> None:
    msg = tmp_path / "MSG"
    msg.write_text("feat: refactor\n\nclean body\n", encoding="utf-8")
    rc = main(["scan-commit-msg", str(msg)])
    assert rc == 0


def test_scan_commit_msg_violation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    msg = tmp_path / "MSG"
    msg.write_text("chore: refactor\n\n" + _USER_MGR, encoding="utf-8")
    rc = main(["scan-commit-msg", str(msg)])
    captured = capsys.readouterr()
    assert rc == 2
    assert "single_user" in captured.err


def test_scan_commit_msg_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["scan-commit-msg", str(tmp_path / "no-such-file")])
    captured = capsys.readouterr()
    assert rc == 1
    assert "not found" in captured.err


def test_unknown_subcommand_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    # argparse uses sys.exit on unknown command; monkeypatch stderr to
    # silence it during the test.
    monkeypatch.setattr("sys.stderr", io.StringIO())
    with pytest.raises(SystemExit):
        main(["nope"])
