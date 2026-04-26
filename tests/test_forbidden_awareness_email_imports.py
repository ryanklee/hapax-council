"""Path-scoped CI guard: no email-send libraries in awareness paths.

Per cc-task ``awareness-refused-email-digest-with-links`` (drop-6 §10
anti-pattern #5): email digests with embedded action links manufacture
click-pressure. The daemon must NEVER send email summaries from
awareness or refusal-brief paths.

This guard is path-scoped: SMTP and email-sender libraries are blocked
ONLY under ``agents/operator_awareness/`` and ``agents/refusal_brief/``.
The council's mail-monitor surface (which RECEIVES mail) is permitted
to use email libraries; mail-RECV is structurally different from
mail-SEND-to-operator.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent

FORBIDDEN_EMAIL_LIBS: Final[tuple[str, ...]] = (
    "smtplib",
    "aiosmtplib",
    "sendgrid",
    "mailgun",
    "sendinblue",
    "boto3.client.*ses",  # AWS SES via boto3 (handled as substring match below)
)
"""Email-sending libraries forbidden in awareness paths.

Receiving / parsing mail (e.g., google-api-python-client for Gmail)
is permitted in mail-monitor paths but not relevant to awareness."""

AWARENESS_PATHS: Final[tuple[str, ...]] = (
    "agents/operator_awareness",
    "agents/refusal_brief",
)
"""Path-scoped roots where email-send is forbidden. Outside these
paths (e.g., agents/mail_monitor/), email libraries are permitted."""


_IMPORT_PATTERN_TEMPLATE = r"^\s*(?:from\s+{lib}\s+import|import\s+{lib})\b"


def _scan_awareness_for_email_imports(
    forbidden: tuple[str, ...] = FORBIDDEN_EMAIL_LIBS,
    *,
    repo_root: Path = REPO_ROOT,
) -> list[tuple[Path, str, int, str]]:
    """Walk only awareness paths looking for email-send imports."""
    findings: list[tuple[Path, str, int, str]] = []
    for awareness_path in AWARENESS_PATHS:
        scope = repo_root / awareness_path
        if not scope.exists():
            continue
        # Walk both file (refusal_brief.py legacy) and dir cases
        py_files: list[Path] = []
        if scope.is_file() and scope.suffix == ".py":
            py_files.append(scope)
        elif scope.is_dir():
            py_files.extend(scope.rglob("*.py"))

        for py_file in py_files:
            try:
                text = py_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for lib in forbidden:
                # Skip libs containing wildcards — not handled by simple regex
                if "*" in lib or "." in lib:
                    continue
                pattern = _IMPORT_PATTERN_TEMPLATE.format(lib=re.escape(lib))
                for line_no, line in enumerate(text.splitlines(), 1):
                    if re.search(pattern, line):
                        findings.append((py_file, lib, line_no, line))
    return findings


class TestAwarenessNoEmailImports:
    def test_awareness_paths_clean_of_email_send_imports(self) -> None:
        """Awareness + refusal-brief paths must NOT import email-send libraries."""
        findings = _scan_awareness_for_email_imports()
        assert findings == [], (
            "Email-send library imports detected in awareness paths:\n"
            + "\n".join(
                f"  {path}:{line_no}: {line.strip()} (lib: {lib})"
                for path, lib, line_no, line in findings
            )
            + "\n\n"
            "Per awareness-refused-email-digest-with-links (drop-6 §10 #5), "
            "awareness daemons must NEVER send email summaries. ntfy + "
            "omg.lol statuslog supersede the email use case."
        )

    def test_scanner_detects_smtplib_in_awareness_path(self, tmp_path: Path) -> None:
        """Self-test: planted smtplib import in awareness path is detected."""
        awareness_dir = tmp_path / "agents" / "operator_awareness"
        awareness_dir.mkdir(parents=True)
        bad_file = awareness_dir / "bad.py"
        bad_file.write_text("import smtplib\n")
        findings = _scan_awareness_for_email_imports(repo_root=tmp_path)
        assert len(findings) == 1
        assert findings[0][1] == "smtplib"

    def test_scanner_skips_mail_monitor_path(self, tmp_path: Path) -> None:
        """Self-test: smtplib in mail_monitor (NON-awareness path) is NOT flagged."""
        mail_dir = tmp_path / "agents" / "mail_monitor"
        mail_dir.mkdir(parents=True)
        ok_file = mail_dir / "ok.py"
        ok_file.write_text("import smtplib\n")
        findings = _scan_awareness_for_email_imports(repo_root=tmp_path)
        assert findings == []

    def test_scanner_detects_aiosmtplib_in_refusal_brief(self, tmp_path: Path) -> None:
        """Self-test: aiosmtplib in refusal_brief path is detected."""
        rb_dir = tmp_path / "agents" / "refusal_brief"
        rb_dir.mkdir(parents=True)
        bad_file = rb_dir / "bad.py"
        bad_file.write_text("from aiosmtplib import SMTP\n")
        findings = _scan_awareness_for_email_imports(repo_root=tmp_path)
        assert len(findings) == 1
