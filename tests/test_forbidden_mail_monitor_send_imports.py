"""CI guard: no email-send libraries in mail-monitor path.

Per cc-task ``mail-monitor-refused-auto-reply`` (mail-monitoring
research §Anti-patterns #3): the mail-monitor daemon must NEVER
send mail in response to inbound mail. Auto-reply manufactures
correspondence the operator has not authored or read.

The mail-monitor surface is purely RECEIVE-shaped: it consumes
inbound Gmail API events, classifies them, files into vault.
Outbound is the publication-bus's job, not mail-monitor's.

The single permitted exception is **outbound-correlated DOI-retry**
(per ``mail-monitor-009-verify-processor``): if a deposit's DOI
fails to resolve, the verifier MAY call the originating service's
``/actions/publish`` API directly (e.g., Zenodo deposit-action).
That is NOT a mail send — it's a deposit-action API call. SMTP
libraries aren't required and aren't permitted.

This guard scans only the ``agents/mail_monitor/`` tree.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent

FORBIDDEN_SMTP_LIBS: Final[tuple[str, ...]] = (
    "smtplib",
    "aiosmtplib",
    "sendgrid",
    "mailgun",
    "sendinblue",
)

MAIL_MONITOR_PATH: Final[str] = "agents/mail_monitor"


_IMPORT_PATTERN_TEMPLATE = r"^\s*(?:from\s+{lib}\s+import|import\s+{lib})\b"


def _scan_mail_monitor_for_send_imports(
    forbidden: tuple[str, ...] = FORBIDDEN_SMTP_LIBS,
    *,
    repo_root: Path = REPO_ROOT,
) -> list[tuple[Path, str, int, str]]:
    """Walk ``agents/mail_monitor/`` for SMTP-send imports.

    Returns one ``(path, lib, line_no, line)`` per match. Empty list
    means clean.
    """
    findings: list[tuple[Path, str, int, str]] = []
    scope = repo_root / MAIL_MONITOR_PATH
    if not scope.is_dir():
        return findings
    for py_file in scope.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lib in forbidden:
            pattern = _IMPORT_PATTERN_TEMPLATE.format(lib=re.escape(lib))
            for line_no, line in enumerate(text.splitlines(), 1):
                if re.search(pattern, line):
                    findings.append((py_file, lib, line_no, line))
    return findings


class TestMailMonitorNoSmtpImports:
    def test_mail_monitor_path_clean_of_smtp_imports(self) -> None:
        """mail_monitor must not import SMTP / email-send libraries."""
        findings = _scan_mail_monitor_for_send_imports()
        assert findings == [], (
            "SMTP-send imports detected in mail_monitor path:\n"
            + "\n".join(
                f"  {path}:{line_no}: {line.strip()} (lib: {lib})"
                for path, lib, line_no, line in findings
            )
            + "\n\n"
            "Per mail-monitor-refused-auto-reply, the mail-monitor surface "
            "is RECEIVE-shaped only. Outbound mail is forbidden. "
            "Outbound-API actions (e.g., Zenodo /actions/publish) are "
            "permitted via the publication-bus, not via SMTP from this "
            "daemon."
        )

    def test_scanner_detects_smtplib_in_mail_monitor(self, tmp_path: Path) -> None:
        """Self-test: planted smtplib import in mail_monitor is detected."""
        mm_dir = tmp_path / "agents" / "mail_monitor"
        mm_dir.mkdir(parents=True)
        bad_file = mm_dir / "bad.py"
        bad_file.write_text("import smtplib\n")
        findings = _scan_mail_monitor_for_send_imports(repo_root=tmp_path)
        assert len(findings) == 1
        assert findings[0][1] == "smtplib"

    def test_scanner_skips_non_mail_monitor_paths(self, tmp_path: Path) -> None:
        """Self-test: smtplib in unrelated dir is NOT flagged.

        The mail-monitor guard is path-scoped; other surfaces
        (e.g., publication-bus) might use SMTP for deposit-related
        notifications and are not within scope.
        """
        other_dir = tmp_path / "agents" / "publication_bus"
        other_dir.mkdir(parents=True)
        ok_file = other_dir / "ok.py"
        ok_file.write_text("import smtplib\n")
        findings = _scan_mail_monitor_for_send_imports(repo_root=tmp_path)
        assert findings == []

    def test_scanner_detects_aiosmtplib(self, tmp_path: Path) -> None:
        """Self-test: aiosmtplib variant detected."""
        mm_dir = tmp_path / "agents" / "mail_monitor"
        mm_dir.mkdir(parents=True)
        bad_file = mm_dir / "bad.py"
        bad_file.write_text("from aiosmtplib import SMTP\n")
        findings = _scan_mail_monitor_for_send_imports(repo_root=tmp_path)
        assert len(findings) == 1
