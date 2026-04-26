"""Tests for ``agents.attribution.swh_archive_daemon`` orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from agents.attribution.repos import HapaxRepo
from agents.attribution.swh_archive_daemon import (
    ArchiveOutcome,
    archive_all_repos,
    archive_one_repo,
)
from agents.attribution.swh_register import SaveResult, VisitStatus
from agents.attribution.swhids_yaml import SwhidRecord, load_swhids

_REPO = HapaxRepo(
    slug="hapax-council",
    git_url="https://github.com/ryanklee/hapax-council",
    description="x",
)


class TestArchiveOneRepo:
    @patch("agents.attribution.swh_archive_daemon.resolve_swhid")
    @patch("agents.attribution.swh_archive_daemon.poll_visit")
    @patch("agents.attribution.swh_archive_daemon.trigger_save")
    def test_full_flow_resolves_swhid(
        self,
        mock_trigger,
        mock_poll,
        mock_resolve,
    ) -> None:
        mock_trigger.return_value = SaveResult(
            repo_url=_REPO.git_url,
            request_id=1,
            visit_status=VisitStatus.QUEUED,
        )
        mock_poll.return_value = SaveResult(
            repo_url=_REPO.git_url,
            request_id=1,
            visit_status=VisitStatus.DONE,
        )
        mock_resolve.return_value = SaveResult(
            repo_url=_REPO.git_url,
            visit_status=VisitStatus.DONE,
            swhid="swh:1:snp:" + "a" * 40,
        )
        outcome = archive_one_repo(_REPO)
        assert outcome.record.swhid == "swh:1:snp:" + "a" * 40
        assert outcome.record.visit_status == "done"
        assert outcome.refusal_event is None

    @patch("agents.attribution.swh_archive_daemon.resolve_swhid")
    @patch("agents.attribution.swh_archive_daemon.poll_visit")
    @patch("agents.attribution.swh_archive_daemon.trigger_save")
    def test_403_emits_refusal_event(self, mock_trigger, mock_poll, mock_resolve) -> None:
        mock_trigger.return_value = SaveResult(
            repo_url=_REPO.git_url,
            visit_status=VisitStatus.FAILED,
            error="swh refused (403): private repository",
        )
        # Poll/resolve not called when trigger fails
        outcome = archive_one_repo(_REPO)
        assert outcome.record.swhid is None
        assert outcome.record.error is not None
        assert outcome.refusal_event is not None
        assert outcome.refusal_event.surface == "attribution:swh-archive"
        assert outcome.refusal_event.axiom == "full_auto_or_nothing"
        mock_poll.assert_not_called()
        mock_resolve.assert_not_called()

    @patch("agents.attribution.swh_archive_daemon.resolve_swhid")
    @patch("agents.attribution.swh_archive_daemon.poll_visit")
    @patch("agents.attribution.swh_archive_daemon.trigger_save")
    def test_ongoing_visit_skips_resolve(self, mock_trigger, mock_poll, mock_resolve) -> None:
        mock_trigger.return_value = SaveResult(
            repo_url=_REPO.git_url,
            request_id=1,
            visit_status=VisitStatus.QUEUED,
        )
        mock_poll.return_value = SaveResult(
            repo_url=_REPO.git_url,
            visit_status=VisitStatus.ONGOING,
        )
        outcome = archive_one_repo(_REPO)
        assert outcome.record.swhid is None
        assert outcome.record.visit_status == "ongoing"
        mock_resolve.assert_not_called()


class TestArchiveAllRepos:
    @patch("agents.attribution.swh_archive_daemon.append")
    @patch("agents.attribution.swh_archive_daemon.archive_one_repo")
    def test_writes_swhids_yaml(self, mock_one, mock_append, tmp_path: Path) -> None:
        path = tmp_path / "swhids.yaml"
        mock_one.side_effect = lambda repo: ArchiveOutcome(
            record=SwhidRecord(
                slug=repo.slug,
                repo_url=repo.git_url,
                swhid="swh:1:snp:" + "c" * 40,
                visit_status="done",
            ),
            refusal_event=None,
        )
        repos = [
            HapaxRepo(
                slug="repo-a",
                git_url="https://github.com/ryanklee/a",
                description="x",
            ),
            HapaxRepo(
                slug="repo-b",
                git_url="https://github.com/ryanklee/b",
                description="y",
            ),
        ]
        archive_all_repos(repos=repos, swhids_path=path)
        loaded = load_swhids(path=path)
        assert set(loaded.keys()) == {"repo-a", "repo-b"}

    @patch("agents.attribution.swh_archive_daemon.append")
    @patch("agents.attribution.swh_archive_daemon.archive_one_repo")
    def test_emits_refusal_brief_for_403(
        self,
        mock_one,
        mock_append,
        tmp_path: Path,
    ) -> None:
        from datetime import UTC, datetime

        from agents.refusal_brief.writer import RefusalEvent

        path = tmp_path / "swhids.yaml"
        repos = [
            HapaxRepo(
                slug="repo-x",
                git_url="https://github.com/ryanklee/x",
                description="x",
            ),
        ]
        event = RefusalEvent(
            timestamp=datetime.now(UTC),
            axiom="full_auto_or_nothing",
            surface="attribution:swh-archive",
            reason="swh refused (403)",
        )
        mock_one.return_value = ArchiveOutcome(
            record=SwhidRecord(
                slug="repo-x",
                repo_url="https://github.com/ryanklee/x",
                error="403",
            ),
            refusal_event=event,
        )
        archive_all_repos(repos=repos, swhids_path=path)
        mock_append.assert_called_once_with(event)

    @patch("agents.attribution.swh_archive_daemon.append")
    @patch("agents.attribution.swh_archive_daemon.archive_one_repo")
    def test_increments_counter_per_repo(
        self,
        mock_one,
        mock_append,
        tmp_path: Path,
    ) -> None:
        from agents.attribution.swh_archive_daemon import swh_archives_total

        path = tmp_path / "swhids.yaml"
        mock_one.side_effect = lambda repo: ArchiveOutcome(
            record=SwhidRecord(
                slug=repo.slug,
                repo_url=repo.git_url,
                swhid="swh:1:snp:" + "d" * 40,
                visit_status="done",
            ),
            refusal_event=None,
        )
        repos = [
            HapaxRepo(
                slug=f"counter-test-{i}",
                git_url=f"https://github.com/ryanklee/counter-test-{i}",
                description="x",
            )
            for i in range(3)
        ]
        before = swh_archives_total.labels(repo="counter-test-0", status="done")._value.get()
        archive_all_repos(repos=repos, swhids_path=path)
        after = swh_archives_total.labels(repo="counter-test-0", status="done")._value.get()
        assert after == before + 1
