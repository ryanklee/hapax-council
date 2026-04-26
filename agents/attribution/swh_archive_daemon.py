"""SWH archive daemon — orchestrates trigger → poll → resolve over HAPAX_REPOS.

Per cc-task ``leverage-attrib-swh-swhid-bibtex`` Phase 2. One pass:

  1. For each repo in :data:`agents.attribution.repos.HAPAX_REPOS`:
     a. ``trigger_save`` — POST queues a save request (idempotent on SWH side).
     b. ``poll_visit`` — GET the latest save status.
     c. ``resolve_swhid`` — once visit reached terminal state, fetch the SWHID.
  2. Aggregate :class:`SwhidRecord` per repo.
  3. ``save_swhids`` to ``hapax-state/attribution/swhids.yaml`` (atomic).
  4. Emit ``hapax_leverage_swh_archives_total{repo,status}`` Prometheus counter.
  5. Append a ``RefusalEvent`` to the canonical refusal log on 403/error
     (constitutional refusal-as-data substrate).

Entry: ``python -m agents.attribution.swh_archive_daemon`` runs one pass
and exits. Wrap in a systemd timer (recommended cadence: 1h) — SWH crawls
take minutes-to-hours, so re-running every tick re-checks open visits and
captures completions without re-queueing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from prometheus_client import Counter

from agents.attribution.repos import HAPAX_REPOS, HapaxRepo
from agents.attribution.swh_register import (
    SaveResult,
    VisitStatus,
    poll_visit,
    resolve_swhid,
    trigger_save,
)
from agents.attribution.swhids_yaml import (
    DEFAULT_SWHIDS_PATH,
    SwhidRecord,
    save_swhids,
)
from agents.refusal_brief.writer import RefusalEvent, append

log = logging.getLogger(__name__)

REFUSAL_SURFACE: str = "attribution:swh-archive"
"""Surface label for refusal-brief events emitted by this daemon."""

REFUSAL_AXIOM: str = "full_auto_or_nothing"
"""Axiom invoked when SWH refuses to archive a repo (private/deleted).
The full-automation pact treats SWH refusal as a structural ceiling on
the citation graph; refusal-as-data captures that ceiling."""

_TERMINAL_VISIT_STATUSES: frozenset[VisitStatus] = frozenset(
    {VisitStatus.DONE, VisitStatus.FULL, VisitStatus.PARTIAL, VisitStatus.FAILED}
)
"""Visit states that signal the SWH crawl has stopped (success or fail);
``poll_visit`` need not be retried for these."""


swh_archives_total = Counter(
    "hapax_leverage_swh_archives_total",
    "Number of SWH archive cycles completed per repo + status.",
    ["repo", "status"],
)


@dataclass(frozen=True)
class ArchiveOutcome:
    """One repo's archive-cycle outcome.

    ``record`` is always populated; ``refusal_event`` is only set when
    SWH refused the archive request, in which case the daemon appends
    it to the refusal-brief log.
    """

    record: SwhidRecord
    refusal_event: RefusalEvent | None


def archive_one_repo(repo: HapaxRepo) -> ArchiveOutcome:
    """Run one trigger → poll → resolve cycle for ``repo``.

    Short-circuits early on ``trigger_save`` failure (no point polling
    a repo SWH refused). Otherwise polls visit state; if terminal,
    resolves SWHID; populates :class:`SwhidRecord` accordingly.
    """
    now = datetime.now(UTC)

    triggered: SaveResult = trigger_save(repo.git_url)
    if _is_refusal(triggered):
        record = SwhidRecord(
            slug=repo.slug,
            repo_url=repo.git_url,
            visit_status=_visit_status_str(triggered.visit_status),
            request_id=triggered.request_id,
            error=triggered.error,
            last_attempted=now,
        )
        event = _make_refusal_event(repo, triggered, now)
        return ArchiveOutcome(record=record, refusal_event=event)

    polled: SaveResult = poll_visit(repo.git_url)
    if polled.visit_status in _TERMINAL_VISIT_STATUSES:
        resolved: SaveResult = resolve_swhid(repo.git_url)
        record = SwhidRecord(
            slug=repo.slug,
            repo_url=repo.git_url,
            swhid=resolved.swhid,
            visit_status=_visit_status_str(resolved.visit_status or polled.visit_status),
            request_id=triggered.request_id or polled.request_id,
            error=resolved.error,
            last_attempted=now,
        )
        return ArchiveOutcome(record=record, refusal_event=None)

    # Visit still in flight — record state, will retry on next pass.
    record = SwhidRecord(
        slug=repo.slug,
        repo_url=repo.git_url,
        visit_status=_visit_status_str(polled.visit_status),
        request_id=triggered.request_id or polled.request_id,
        error=polled.error,
        last_attempted=now,
    )
    return ArchiveOutcome(record=record, refusal_event=None)


def archive_all_repos(
    *,
    repos: list[HapaxRepo] | None = None,
    swhids_path=DEFAULT_SWHIDS_PATH,
) -> dict[str, ArchiveOutcome]:
    """Run :func:`archive_one_repo` for every repo and persist results.

    Returns ``{slug: ArchiveOutcome}`` for caller introspection (test
    harness uses this; production daemon discards the return value).
    """
    repos = list(repos) if repos is not None else list(HAPAX_REPOS)
    outcomes: dict[str, ArchiveOutcome] = {}
    for repo in repos:
        try:
            outcome = archive_one_repo(repo)
        except Exception as exc:  # pragma: no cover — defensive
            log.warning("swh archive cycle raised for %s: %s", repo.slug, exc)
            outcome = ArchiveOutcome(
                record=SwhidRecord(
                    slug=repo.slug,
                    repo_url=repo.git_url,
                    error=f"daemon exception: {exc}",
                    last_attempted=datetime.now(UTC),
                ),
                refusal_event=None,
            )
        outcomes[repo.slug] = outcome
        status = outcome.record.visit_status or "unknown"
        swh_archives_total.labels(repo=repo.slug, status=status).inc()
        if outcome.refusal_event is not None:
            append(outcome.refusal_event)

    save_swhids(
        {slug: outcome.record for slug, outcome in outcomes.items()},
        path=swhids_path,
    )
    return outcomes


def _is_refusal(result: SaveResult) -> bool:
    """Did SWH refuse this archive request?

    Refusal = trigger returned ``FAILED`` with an explicit 403 error
    (private repo, deleted repo, blocked origin). Transport failures
    or other 5xx are NOT refusals — they're transient and retry-eligible.
    """
    if result.visit_status != VisitStatus.FAILED:
        return False
    return bool(result.error and "403" in result.error)


def _make_refusal_event(
    repo: HapaxRepo,
    result: SaveResult,
    now: datetime,
) -> RefusalEvent:
    reason = (result.error or "swh refused archive request")[:160]
    return RefusalEvent(
        timestamp=now,
        axiom=REFUSAL_AXIOM,
        surface=REFUSAL_SURFACE,
        reason=reason,
        public=False,
    )


def _visit_status_str(status: VisitStatus | None) -> str | None:
    return status.value if status is not None else None


def main() -> int:
    """Single-pass entry for ``python -m agents.attribution.swh_archive_daemon``."""
    logging.basicConfig(level=logging.INFO)
    outcomes = archive_all_repos()
    refused = sum(1 for o in outcomes.values() if o.refusal_event is not None)
    resolved = sum(1 for o in outcomes.values() if o.record.swhid is not None)
    log.info(
        "swh archive cycle complete: %d repos / %d resolved / %d refused",
        len(outcomes),
        resolved,
        refused,
    )
    return 0


__all__ = [
    "REFUSAL_AXIOM",
    "REFUSAL_SURFACE",
    "ArchiveOutcome",
    "archive_all_repos",
    "archive_one_repo",
    "main",
    "swh_archives_total",
]


if __name__ == "__main__":
    raise SystemExit(main())
