"""Regression tests pinning the ORCID concept-DOI-only contract.

Per cc-task ``repo-pres-version-doi-test`` and drop-5 anti-pattern:
ORCID's DataCite auto-update operates at concept-DOI granularity
only. Hapax's publication bus must NEVER push version-DOIs to ORCID
directly (e.g., per-version PUTs to ORCID API).

These tests pin the contract so future refactors do not accidentally
introduce per-version PUT logic.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final
from unittest.mock import MagicMock, patch

from agents.publication_bus.orcid_verifier import (
    extract_dois,
    fetch_orcid_works,
    verify_dois_present,
)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent.parent.parent
PUBLICATION_BUS_ROOT: Final[Path] = REPO_ROOT / "agents" / "publication_bus"


def _mock_orcid_response(works: list[dict[str, str]]) -> MagicMock:
    """Build a minimal ORCID v3.0 ``works`` response with one DOI per work."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "group": [
            {
                "external-ids": {
                    "external-id": [
                        {
                            "external-id-type": "doi",
                            "external-id-value": work["doi"],
                        }
                    ]
                },
                "work-summary": [{"title": {"title": {"value": work.get("title", "")}}}],
            }
            for work in works
        ]
    }
    return response


class TestConceptDoiOnlyContract:
    @patch("agents.publication_bus.orcid_verifier.requests")
    def test_orcid_receives_concept_doi_only(self, mock_requests: MagicMock) -> None:
        """Pin: ORCID DataCite auto-update operates at concept-DOI
        granularity only.

        When concept-DOI 10.5281/zenodo.123 is the operator-minted
        umbrella DOI for 5 versions (124..128), the verifier must
        check ORCID for the concept-DOI only — never for any
        version-DOI.
        """
        concept_doi = "10.5281/zenodo.123"
        version_dois = [f"10.5281/zenodo.{n}" for n in range(124, 129)]

        # ORCID record contains the concept-DOI only (per DataCite
        # auto-update contract). Version-DOIs must NOT appear.
        mock_requests.get.return_value = _mock_orcid_response([{"doi": concept_doi}])

        response = fetch_orcid_works(orcid_id="0000-0000-0000-0000")
        present_dois = extract_dois(response)

        assert concept_doi in present_dois
        for vdoi in version_dois:
            assert vdoi not in present_dois, (
                f"Version-DOI {vdoi} appeared in ORCID — auto-update "
                "should be concept-DOI only per drop-5 anti-pattern"
            )

    @patch("agents.publication_bus.orcid_verifier.requests")
    def test_verify_only_against_concept_dois(self, mock_requests: MagicMock) -> None:
        """Pin: ``verify_dois_present`` is called with concept-DOIs
        only — never with version-DOIs.

        The verifier consumes a list of expected DOIs from local
        state. Per the concept-DOI-only contract, only concept-DOIs
        belong on that list.
        """
        concept_doi = "10.5281/zenodo.123"
        mock_requests.get.return_value = _mock_orcid_response([{"doi": concept_doi}])

        response = fetch_orcid_works(orcid_id="0000-0000-0000-0000")
        fetched = extract_dois(response)
        expected_concept_only = {concept_doi}

        missing = verify_dois_present(
            expected_dois=expected_concept_only,
            fetched_dois=fetched,
        )
        assert missing == set(), (
            f"Concept-DOI 10.5281/zenodo.123 should be present; missing={missing!r}"
        )


_ORCID_PUT_REGEX = re.compile(
    r"""(?ix)
    \brequests?\s*\.\s*put\s*\(.*?orcid             # requests.put(...orcid...)
    |
    \bhttpx?\s*\.\s*put\s*\(.*?orcid                # httpx.put(...orcid...)
    """,
    re.DOTALL,
)
"""Static-check regex for ORCID PUT calls. Per drop-5 anti-pattern,
the publication-bus must NEVER PUT directly to ``api.orcid.org`` —
DataCite auto-update is the only authorized channel."""


class TestNoPerVersionOrcidPut:
    def test_no_orcid_put_in_publication_bus(self) -> None:
        """Pin: no PUT calls to ORCID API anywhere in publication_bus.

        DataCite auto-update is the only authorized ORCID-mutation
        channel. Direct PUTs would bypass the auto-update contract
        and introduce per-version push logic.
        """
        findings: list[tuple[Path, int, str]] = []
        for py_file in PUBLICATION_BUS_ROOT.rglob("*.py"):
            try:
                text = py_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                # Skip comment-only lines mentioning ORCID PUT in prose
                stripped = line.lstrip()
                if stripped.startswith("#") or stripped.startswith('"'):
                    continue
                if _ORCID_PUT_REGEX.search(line):
                    findings.append((py_file, line_no, line.strip()))

        assert findings == [], (
            "Direct ORCID PUT calls detected in publication_bus:\n"
            + "\n".join(f"  {path}:{line_no}: {snippet}" for path, line_no, snippet in findings)
            + "\n\nDataCite auto-update is the only authorized ORCID-mutation "
            "channel per drop-5 anti-pattern. Per-version PUT logic is REFUSED."
        )

    def test_static_regex_self_test_positive_case(self, tmp_path: Path) -> None:
        """Self-test: regex correctly detects a planted ORCID PUT call."""
        bad_file = tmp_path / "bad.py"
        bad_file.write_text(
            "import requests\ndef push():\n    requests.put('https://api.orcid.org/v3.0/...')\n"
        )
        match_count = 0
        for line in bad_file.read_text().splitlines():
            if _ORCID_PUT_REGEX.search(line):
                match_count += 1
        assert match_count == 1

    def test_static_regex_self_test_negative_case(self, tmp_path: Path) -> None:
        """Self-test: regex does NOT match GET calls or non-ORCID PUTs."""
        clean_file = tmp_path / "clean.py"
        clean_file.write_text(
            "import requests\n"
            "def fetch():\n"
            "    requests.get('https://pub.orcid.org/v3.0/...')\n"
            "def push_zenodo():\n"
            "    requests.put('https://zenodo.org/api/...')\n"
        )
        for line in clean_file.read_text().splitlines():
            assert not _ORCID_PUT_REGEX.search(line)
