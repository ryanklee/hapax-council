"""Per-directory test fixtures for integration tests.

Auto-isolates the programme outcome JSONL log from the real
~/hapax-state/programmes/ vault so the e2e programme-layer test
doesn't pollute the operator's filesystem.

See tests/programme_manager/conftest.py for the same isolation
applied to the unit tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_programme_outcome_log(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from shared import programme_outcome_log as pol

    tmp_root: Path = tmp_path_factory.mktemp("programmes")
    isolated = pol.ProgrammeOutcomeLog(root=tmp_root)
    monkeypatch.setattr(pol, "get_default_log", lambda: isolated)
    monkeypatch.setattr(pol, "_DEFAULT_LOG", None)
