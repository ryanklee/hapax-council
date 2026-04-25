"""AUDIT-21 — SHA-pinned-URL bit-stability + cdn-index regression.

Pins the protective behavior that makes :func:`build_web_url` a
canonical primitive:

  * **Bit-stable across runs** — same ``(library_root, asset_path,
    sha256)`` always produces same URL string. Cached references in
    OMG posts / livestream descriptions / generated docs must not
    drift between identical manifest snapshots.
  * **Invalidation handle flips on SHA change** — different SHA
    inputs produce distinguishable URLs.
  * **CDN base URL is governance-stable** — flipping ``CDN_BASE_URL``
    is a deliberate operator action, not silent drift.

Plus a regression on
``scripts/generate-aesthetic-library-cdn-index.py`` to ensure the
new outside-OMG consumer stays wired to the primitive.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from shared.aesthetic_library.web_export import CDN_BASE_URL, build_web_url

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "generate-aesthetic-library-cdn-index.py"
INDEX_PATH = REPO_ROOT / "docs" / "aesthetic-library" / "cdn-index.md"


class TestUrlStability:
    """Bit-stability invariant — load-bearing for cached-reference safety."""

    def test_same_inputs_produce_same_url(self) -> None:
        url1 = build_web_url(
            Path("/repo/assets"),
            Path("/repo/assets/fonts/Px437_IBM_VGA_8x16.woff2"),
            "0cc1138b" + "0" * 56,
        )
        url2 = build_web_url(
            Path("/repo/assets"),
            Path("/repo/assets/fonts/Px437_IBM_VGA_8x16.woff2"),
            "0cc1138b" + "0" * 56,
        )
        assert url1 == url2

    def test_different_sha_produces_different_url(self) -> None:
        url1 = build_web_url(
            Path("/repo/assets"),
            Path("/repo/assets/fonts/x.woff2"),
            "a" * 64,
        )
        url2 = build_web_url(
            Path("/repo/assets"),
            Path("/repo/assets/fonts/x.woff2"),
            "b" * 64,
        )
        assert url1 != url2

    def test_url_starts_with_cdn_base(self) -> None:
        url = build_web_url(
            Path("/repo/assets"),
            Path("/repo/assets/fonts/x.woff2"),
            "a" * 64,
        )
        assert url.startswith(CDN_BASE_URL)

    def test_url_contains_short_sha_query(self) -> None:
        """The first 8 hex of the SHA appears as the cache-bust query."""
        sha = "abcdef0123456789" * 4
        url = build_web_url(
            Path("/repo/assets"),
            Path("/repo/assets/fonts/x.woff2"),
            sha,
        )
        assert "?sha=abcdef01" in url

    def test_path_is_relative_to_root(self) -> None:
        """Build-result is independent of absolute-path prefix as long
        as the asset is under ``library_root``."""
        url1 = build_web_url(
            Path("/a/repo/assets"),
            Path("/a/repo/assets/fonts/x.woff2"),
            "a" * 64,
        )
        url2 = build_web_url(
            Path("/b/elsewhere/assets"),
            Path("/b/elsewhere/assets/fonts/x.woff2"),
            "a" * 64,
        )
        # Both produce the same URL — the absolute-path prefix is
        # not part of the URL surface.
        assert url1 == url2


class TestCdnIndexScript:
    """The cdn-index generator is the AUDIT-21 ≥1-new-consumer-outside-OMG.

    Pins that the script (a) runs cleanly against the live manifest
    and (b) emits byte-stable output for the same manifest. Re-runs
    of the script must not change the file (otherwise CI's --check
    mode flaps without source change)."""

    def test_script_exists(self) -> None:
        assert SCRIPT.is_file(), f"AUDIT-21 consumer missing: {SCRIPT}"

    def test_script_check_passes_against_committed_index(self) -> None:
        """The committed ``cdn-index.md`` must match what the script
        would emit *right now* — drift between manifest and committed
        index is a CI-failable regression."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--check"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, (
            f"cdn-index drift detected — regenerate via "
            f"`python scripts/generate-aesthetic-library-cdn-index.py`\n"
            f"stderr: {result.stderr}"
        )

    def test_committed_index_exists(self) -> None:
        assert INDEX_PATH.is_file(), (
            "cdn-index missing: regenerate via "
            "`python scripts/generate-aesthetic-library-cdn-index.py`"
        )

    def test_committed_index_has_cdn_urls(self) -> None:
        """Sanity check — the committed index actually contains the
        CDN base URL (not a stub)."""
        text = INDEX_PATH.read_text(encoding="utf-8")
        assert CDN_BASE_URL in text


class TestDocsReadme:
    """Pin the README presence — its absence is itself an AUDIT-21
    regression (the canonical-primitive documentation is the spec
    contract)."""

    def test_readme_exists(self) -> None:
        readme = REPO_ROOT / "docs" / "aesthetic-library" / "README.md"
        assert readme.is_file()

    def test_readme_documents_primitive(self) -> None:
        readme = REPO_ROOT / "docs" / "aesthetic-library" / "README.md"
        text = readme.read_text(encoding="utf-8")
        # Three load-bearing names that must appear in the docs:
        # the function, the convenience method, and the primitive
        # invariant property.
        assert "build_web_url" in text
        assert "library().web_url" in text
        assert "bit-stable" in text or "bit-identical" in text
