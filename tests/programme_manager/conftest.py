"""Per-directory test fixtures.

Auto-isolates the programme outcome JSONL log from the real
~/hapax-state/programmes/ vault so manager lifecycle tests don't
pollute the operator's filesystem with synthetic show records.

The autouse fixture replaces the module-level singleton accessor
(``shared.programme_outcome_log.get_default_log``) with a tmp-path-
rooted instance for the duration of every test in this directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_programme_outcome_log(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Re-root ``get_default_log`` onto a tmp path so the manager's
    JSONL writer never touches ~/hapax-state/programmes/."""
    from shared import programme_outcome_log as pol

    tmp_root: Path = tmp_path_factory.mktemp("programmes")
    isolated = pol.ProgrammeOutcomeLog(root=tmp_root)
    monkeypatch.setattr(pol, "get_default_log", lambda: isolated)
    # Reset the module-level singleton too in case it was already
    # constructed by an earlier test before this autouse fired.
    monkeypatch.setattr(pol, "_DEFAULT_LOG", None)
