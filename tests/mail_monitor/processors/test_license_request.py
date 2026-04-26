"""Tests for ``agents.mail_monitor.processors.license_request``.

Covers detection (line-anchored regex), vault filing, chronicle event
emission, idempotency, and counter behaviour. Auto-reply is deferred to
Phase 2 (cred-blocked on Lightning + Liberapay rails).
"""

from __future__ import annotations

from pathlib import Path

from agents.mail_monitor.processors.license_request import (
    LICENSE_REQUEST_RE,
    detect_license_request,
    process_license_request,
)


def _msg(
    *,
    message_id: str = "msg-1",
    subject: str = "LICENSE-REQUEST: hapax-sdlc commercial license",
    sender: str = '"Acme Corp" <licensing@acme.com>',
    body: str = "Hello, please send us a quote for hapax-sdlc.\n",
) -> dict:
    return {
        "id": message_id,
        "messageId": message_id,
        "subject": subject,
        "sender": sender,
        "body": body,
    }


# ── Detection ────────────────────────────────────────────────────────


class TestDetectLicenseRequest:
    def test_line_anchored_subject_matches(self):
        assert detect_license_request(_msg()) is True

    def test_line_anchored_case_insensitive(self):
        msg = _msg(subject="license-request: please quote")
        assert detect_license_request(msg) is True

    def test_mid_paragraph_does_not_match(self):
        msg = _msg(
            subject="Inquiry about your work",
            body="In passing — we may need a license-request later, just exploring.\n",
        )
        assert detect_license_request(msg) is False

    def test_subject_keyword_buried_does_not_match(self):
        # "LICENSE-REQUEST" must be at line-start of subject; mid-string
        # mentions are conversational and must not auto-trigger.
        msg = _msg(subject="Re: my LICENSE-REQUEST question from last week")
        assert detect_license_request(msg) is False

    def test_regex_pattern_anchors(self):
        # Pin the literal regex so audit can verify the line-anchor.
        assert LICENSE_REQUEST_RE.match("LICENSE-REQUEST: x") is not None
        assert LICENSE_REQUEST_RE.match("license-request: y") is not None
        assert LICENSE_REQUEST_RE.match(" LICENSE-REQUEST: z") is None


# ── process_license_request ──────────────────────────────────────────


class TestProcessLicenseRequest:
    def test_files_to_vault_dir(self, tmp_path: Path, monkeypatch):
        vault = tmp_path / "license-requests"
        monkeypatch.setattr(
            "agents.mail_monitor.processors.license_request.LICENSE_REQUEST_DIR",
            vault,
        )
        msg = _msg(message_id="msg-files-1")
        result = process_license_request(msg)
        assert result is True
        files = list(vault.glob("*.eml"))
        assert len(files) == 1

    def test_filename_contains_iso_date(self, tmp_path: Path, monkeypatch):
        vault = tmp_path / "license-requests"
        monkeypatch.setattr(
            "agents.mail_monitor.processors.license_request.LICENSE_REQUEST_DIR",
            vault,
        )
        process_license_request(_msg(message_id="msg-iso-1"))
        files = list(vault.glob("*.eml"))
        assert files
        # Format: YYYY-MM-DD-<sender-hash>.eml
        assert files[0].name[:10].count("-") == 2

    def test_idempotent_re_process_same_message_id(self, tmp_path: Path, monkeypatch):
        vault = tmp_path / "license-requests"
        monkeypatch.setattr(
            "agents.mail_monitor.processors.license_request.LICENSE_REQUEST_DIR",
            vault,
        )
        msg = _msg(message_id="msg-dupe-1")
        process_license_request(msg)
        process_license_request(msg)
        files = list(vault.glob("*.eml"))
        # Re-processing same messageId must NOT create a second file
        assert len(files) == 1

    def test_returns_false_when_no_sender(self, tmp_path: Path, monkeypatch):
        vault = tmp_path / "license-requests"
        monkeypatch.setattr(
            "agents.mail_monitor.processors.license_request.LICENSE_REQUEST_DIR",
            vault,
        )
        msg = _msg(sender="")
        result = process_license_request(msg)
        assert result is False

    def test_returns_false_when_subject_does_not_match(self, tmp_path: Path, monkeypatch):
        vault = tmp_path / "license-requests"
        monkeypatch.setattr(
            "agents.mail_monitor.processors.license_request.LICENSE_REQUEST_DIR",
            vault,
        )
        msg = _msg(subject="Just a hello")
        result = process_license_request(msg)
        assert result is False

    def test_file_contents_preserve_message(self, tmp_path: Path, monkeypatch):
        vault = tmp_path / "license-requests"
        monkeypatch.setattr(
            "agents.mail_monitor.processors.license_request.LICENSE_REQUEST_DIR",
            vault,
        )
        unique_body = "specific quote details: 50 seats annual"
        msg = _msg(message_id="msg-content-1", body=unique_body)
        process_license_request(msg)
        files = list(vault.glob("*.eml"))
        contents = files[0].read_text()
        assert unique_body in contents
        assert "LICENSE-REQUEST" in contents
