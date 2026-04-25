"""Tests for ``durf_redaction`` — AUDIT-01 acceptance pin tests.

Each fixture PNG renders one sample line with PIL using a default font;
tesseract reads the rendered glyphs back as text. The risk patterns
checked here mirror the upstream-audit acceptance examples (``sk-ant-``)
plus the additional high-confidence patterns enumerated in
:data:`agents.studio_compositor.durf_redaction.RISK_PATTERNS`.

Tests that don't need real OCR (bypass + missing-file + ocr-failure
fallthrough) monkeypatch :func:`durf_redaction._ocr_png` so they run
without invoking tesseract.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image, ImageDraw, ImageFont

from agents.studio_compositor import durf_redaction
from agents.studio_compositor.durf_redaction import (
    DURF_RAW_ENV,
    RedactionAction,
    redact_terminal_capture,
)


def _render_text_png(path: Path, text: str) -> None:
    """Render a multi-line text block into a 1280×400 PNG.

    Default PIL font is a tiny bitmap; works for tesseract on plain
    ASCII and is good enough for the regex matchers — these tests pin
    redaction behaviour, not OCR fidelity.
    """
    img = Image.new("RGB", (1280, 400), color=(8, 8, 12))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSansMono.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    y = 16
    for line in text.splitlines() or [text]:
        draw.text((16, y), line, fill=(220, 220, 220), font=font)
        y += 28
    img.save(str(path), "PNG")


@pytest.fixture
def tmp_png(tmp_path: Path) -> Path:
    return tmp_path / "capture.png"


@pytest.fixture(autouse=True)
def _clear_raw_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DURF_RAW_ENV, raising=False)


_TESSERACT_AVAILABLE = shutil.which("tesseract") is not None
needs_tesseract = pytest.mark.skipif(not _TESSERACT_AVAILABLE, reason="tesseract not installed")


class TestRiskPatterns:
    def test_pattern_names_unique(self) -> None:
        names = [name for name, _ in durf_redaction.RISK_PATTERNS]
        assert len(names) == len(set(names))

    def test_anthropic_pattern_matches_realistic_key(self) -> None:
        pat = dict(durf_redaction.RISK_PATTERNS)["anthropic_api_key"]
        assert pat.search("export KEY=sk-ant-api01-AAAAAAAAAAAAAAAAAAAAAA")

    def test_anthropic_pattern_does_not_match_short_prefix(self) -> None:
        pat = dict(durf_redaction.RISK_PATTERNS)["anthropic_api_key"]
        assert not pat.search("the prefix sk-ant- alone is harmless")

    def test_aws_pattern_matches_akia(self) -> None:
        pat = dict(durf_redaction.RISK_PATTERNS)["aws_access_key"]
        assert pat.search("AKIA1234567890ABCDEF")

    def test_github_pattern_matches_ghp(self) -> None:
        pat = dict(durf_redaction.RISK_PATTERNS)["github_token"]
        assert pat.search("ghp_AAAAAAAAAAAAAAAAAAAA")

    def test_private_key_pattern(self) -> None:
        pat = dict(durf_redaction.RISK_PATTERNS)["private_key_block"]
        assert pat.search("-----BEGIN RSA PRIVATE KEY-----")

    def test_operator_home_pattern_matches_runtime_path(self) -> None:
        pat = dict(durf_redaction.RISK_PATTERNS)["operator_home_path"]
        # Built at runtime so the test source itself does not embed
        # the literal substring (mirrors the production module).
        runtime_path = "/" + "home" + "/" + "hapax" + "/somefile"
        assert pat.search(runtime_path)


class TestRawBypass:
    def test_bypass_returns_clean_without_ocr(
        self, tmp_png: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(DURF_RAW_ENV, "1")
        # File doesn't even need to exist — bypass short-circuits first
        result = redact_terminal_capture(tmp_png)
        assert result.action is RedactionAction.CLEAN
        assert result.detail == "raw bypass"

    def test_bypass_only_on_value_one(self, tmp_png: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(DURF_RAW_ENV, "true")  # not "1"
        # Falls through to UNAVAILABLE because the file doesn't exist
        result = redact_terminal_capture(tmp_png)
        assert result.action is RedactionAction.UNAVAILABLE


class TestMissingFile:
    def test_missing_png_is_unavailable(self, tmp_png: Path) -> None:
        assert not tmp_png.exists()
        result = redact_terminal_capture(tmp_png)
        assert result.action is RedactionAction.UNAVAILABLE
        assert result.detail == "png missing"


class TestOcrFailure:
    def test_ocr_returns_none_yields_unavailable(
        self, tmp_png: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tmp_png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        monkeypatch.setattr(durf_redaction, "_ocr_png", lambda _p: None)
        result = redact_terminal_capture(tmp_png)
        assert result.action is RedactionAction.UNAVAILABLE
        assert result.detail == "ocr failed"

    def test_ocr_subprocess_oserror_is_unavailable(self, tmp_png: Path) -> None:
        tmp_png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        with patch.object(
            durf_redaction.subprocess,
            "run",
            side_effect=FileNotFoundError("tesseract not found"),
        ):
            result = redact_terminal_capture(tmp_png)
        assert result.action is RedactionAction.UNAVAILABLE


class TestSuppressPaths:
    def test_suppresses_when_ocr_returns_anthropic_key(
        self, tmp_png: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tmp_png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        monkeypatch.setattr(
            durf_redaction,
            "_ocr_png",
            lambda _p: "ANTHROPIC_API_KEY=sk-ant-api01-AAAAAAAAAAAAAAAAAAAAA",
        )
        result = redact_terminal_capture(tmp_png)
        assert result.action is RedactionAction.SUPPRESS
        # First-match wins: anthropic_api_key fires before the assignment pattern
        assert result.matched_pattern == "anthropic_api_key"

    def test_suppresses_on_aws_access_key(
        self, tmp_png: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tmp_png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        monkeypatch.setattr(
            durf_redaction,
            "_ocr_png",
            lambda _p: "Access key: AKIA1234567890ABCDEF saved\n",
        )
        result = redact_terminal_capture(tmp_png)
        assert result.action is RedactionAction.SUPPRESS
        assert result.matched_pattern == "aws_access_key"

    def test_suppresses_on_github_token(
        self, tmp_png: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tmp_png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        monkeypatch.setattr(
            durf_redaction,
            "_ocr_png",
            lambda _p: "git clone https://ghp_AAAAAAAAAAAAAAAAAAAAAAA@github.com/x/y.git",
        )
        result = redact_terminal_capture(tmp_png)
        assert result.action is RedactionAction.SUPPRESS
        assert result.matched_pattern == "github_token"

    def test_suppresses_on_bearer_token(
        self, tmp_png: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tmp_png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        monkeypatch.setattr(
            durf_redaction,
            "_ocr_png",
            lambda _p: "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9XYZXYZXYZ\n",
        )
        result = redact_terminal_capture(tmp_png)
        assert result.action is RedactionAction.SUPPRESS
        # authorization_header is checked AFTER bearer_token in the
        # tuple; bearer_token wins here.
        assert result.matched_pattern == "bearer_token"

    def test_suppresses_on_private_key_block(
        self, tmp_png: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tmp_png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        monkeypatch.setattr(
            durf_redaction,
            "_ocr_png",
            lambda _p: "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZX...",
        )
        result = redact_terminal_capture(tmp_png)
        assert result.action is RedactionAction.SUPPRESS
        assert result.matched_pattern == "private_key_block"

    def test_suppresses_on_operator_home_path(
        self, tmp_png: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tmp_png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        runtime_path = "/" + "home" + "/" + "hapax" + "/projects"
        monkeypatch.setattr(
            durf_redaction,
            "_ocr_png",
            lambda _p, _path=runtime_path: f"$ ls {_path}\n",
        )
        result = redact_terminal_capture(tmp_png)
        assert result.action is RedactionAction.SUPPRESS
        assert result.matched_pattern == "operator_home_path"


class TestCleanPath:
    def test_no_match_returns_clean(self, tmp_png: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        tmp_png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        monkeypatch.setattr(
            durf_redaction,
            "_ocr_png",
            lambda _p: "$ pytest tests/ -q\n12 passed in 3.21s\n",
        )
        result = redact_terminal_capture(tmp_png)
        assert result.action is RedactionAction.CLEAN
        assert result.matched_pattern is None


@needs_tesseract
class TestRealOcrSmoke:
    """End-to-end smoke that the OCR call path actually executes.

    OCR fidelity on PIL-rendered fixture PNGs depends on the local
    tesseract trained-data version and the available font. We do NOT
    assert which redaction action fires — only that the call returns
    one of the documented enum values without raising. Pattern-match
    correctness is pinned by :class:`TestSuppressPaths` with mocked
    OCR text; this test catches regressions in the subprocess plumbing.
    """

    def test_runs_without_raising_and_returns_known_action(self, tmp_png: Path) -> None:
        _render_text_png(tmp_png, "$ pytest tests/ -q\n12 passed in 3.21s\n")
        result = redact_terminal_capture(tmp_png)
        assert result.action in {
            RedactionAction.CLEAN,
            RedactionAction.SUPPRESS,
            RedactionAction.UNAVAILABLE,
        }
