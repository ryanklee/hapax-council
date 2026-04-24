"""Tests for AUTH2 — provenance presence enforcement.

Verifies the `AestheticLibrary.missing_provenance()` gate detects source
groups that have manifest entries but no sibling `provenance.yaml`. This
is the governance seam between "asset added to tree" and "asset shippable
to public CDN" — without attribution, the asset cannot lawfully ship.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from shared.aesthetic_library.loader import AestheticLibrary


@pytest.fixture
def library_with_two_sources(tmp_path: Path) -> Path:
    """A library with two sources (bitchx + fonts), both with valid
    provenance.yaml. Tests remove provenance files to simulate drift.
    """
    root = tmp_path / "aesthetic-library"
    root.mkdir()

    # bitchx source
    banner = root / "bitchx" / "splash" / "banner.txt"
    banner.parent.mkdir(parents=True)
    banner.write_bytes(b"BitchX banner\n")
    bitchx_sha = hashlib.sha256(b"BitchX banner\n").hexdigest()
    (root / "bitchx" / "provenance.yaml").write_text(
        "source: bitchx\n"
        "source_url: https://example.com/bitchx\n"
        'extracted_date: "2026-04-24"\n'
        "original_author: test\n"
        "license: BSD-3-Clause\n"
        'attribution_line: "test (BSD-3-Clause)"\n'
    )

    # fonts source
    font = root / "fonts" / "px437.ttf"
    font.parent.mkdir(parents=True)
    font.write_bytes(b"FAKE-TTF-BYTES")
    font_sha = hashlib.sha256(b"FAKE-TTF-BYTES").hexdigest()
    (root / "fonts" / "provenance.yaml").write_text(
        "source: fonts\n"
        "source_url: https://example.com/fonts\n"
        'extracted_date: "2026-04-24"\n'
        "original_author: VileR\n"
        "license: CC-BY-SA-4.0\n"
        'attribution_line: "VileR (CC-BY-SA-4.0)"\n'
    )

    manifest = {
        "assets": [
            {
                "source": "bitchx",
                "kind": "splash",
                "name": "banner",
                "path": "bitchx/splash/banner.txt",
                "sha256": bitchx_sha,
                "license": "BSD-3-Clause",
                "author": "test",
                "source_url": "https://example.com/bitchx",
                "extracted_date": "2026-04-24",
            },
            {
                "source": "fonts",
                "kind": "font",
                "name": "px437",
                "path": "fonts/px437.ttf",
                "sha256": font_sha,
                "license": "CC-BY-SA-4.0",
                "author": "VileR",
                "source_url": "https://example.com/fonts",
                "extracted_date": "2026-04-24",
            },
        ]
    }
    (root / "_manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))
    return root


class TestMissingProvenance:
    def test_clean_library_has_no_missing_provenance(self, library_with_two_sources: Path) -> None:
        lib = AestheticLibrary(root=library_with_two_sources)
        assert lib.missing_provenance() == []

    def test_detects_single_missing_provenance(self, library_with_two_sources: Path) -> None:
        (library_with_two_sources / "bitchx" / "provenance.yaml").unlink()
        lib = AestheticLibrary(root=library_with_two_sources)
        missing = lib.missing_provenance()
        assert missing == ["bitchx"]

    def test_detects_multiple_missing_provenance(self, library_with_two_sources: Path) -> None:
        (library_with_two_sources / "bitchx" / "provenance.yaml").unlink()
        (library_with_two_sources / "fonts" / "provenance.yaml").unlink()
        lib = AestheticLibrary(root=library_with_two_sources)
        missing = lib.missing_provenance()
        assert sorted(missing) == ["bitchx", "fonts"]

    def test_real_library_has_no_missing_provenance(self) -> None:
        """The shipped assets/aesthetic-library/ tree must satisfy the gate
        at all times — this is the fail-loud regression pin."""
        from shared.aesthetic_library.loader import ASSETS_ROOT_DEFAULT

        lib = AestheticLibrary(root=ASSETS_ROOT_DEFAULT / "aesthetic-library")
        assert lib.missing_provenance() == []
