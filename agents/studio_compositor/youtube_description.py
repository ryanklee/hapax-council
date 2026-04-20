"""YouTube video description auto-update with quota enforcement.

Writes the current research condition + active objective + stimmung snapshot
to the YouTube video description during livestream operation. Used by the
LRR Phase 9 content-programming loop (hook 3) and Phase 8 item 7.

Quota policy lives in ``config/youtube-quota.yaml``. The writer is the single
source of quota enforcement in the repo; no other code should call
``youtube.videos().update(snippet=...)`` directly.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger("youtube_description")

CONFIG_FILE = Path(__file__).parent.parent.parent / "config" / "youtube-quota.yaml"
QUOTA_FILE_DEFAULT = Path("/dev/shm/hapax-compositor/youtube-quota.json")


class QuotaExhausted(Exception):
    """Raised when the daily quota budget is exhausted for today."""


def _load_config() -> dict[str, Any]:
    with CONFIG_FILE.open() as f:
        return yaml.safe_load(f)


def _pacific_date_now() -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now(UTC).strftime("%Y-%m-%d")


def _read_quota_state(quota_file: Path) -> dict[str, Any]:
    if not quota_file.exists():
        return {"date": _pacific_date_now(), "units_spent": 0, "stream_updates": {}}
    try:
        state = json.loads(quota_file.read_text())
    except (OSError, json.JSONDecodeError):
        return {"date": _pacific_date_now(), "units_spent": 0, "stream_updates": {}}
    if state.get("date") != _pacific_date_now():
        return {"date": _pacific_date_now(), "units_spent": 0, "stream_updates": {}}
    return state


def _write_quota_state(quota_file: Path, state: dict[str, Any]) -> None:
    quota_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = quota_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(state))
    tmp.replace(quota_file)


def check_and_debit(
    video_id: str,
    cfg: dict[str, Any] | None = None,
    quota_file: Path | None = None,
) -> None:
    """Verify quota allows another update, then debit its unit cost.

    Raises ``QuotaExhausted`` if either the per-stream cap or daily budget
    would be exceeded. Callers should catch + skip silently per the
    ``on_budget_exhausted`` policy.
    """
    cfg = cfg or _load_config()
    quota_file = quota_file or Path(cfg.get("quota_file", QUOTA_FILE_DEFAULT))

    state = _read_quota_state(quota_file)
    unit_cost = int(cfg["per_update_unit_cost"])
    daily_cap = int(cfg["daily_budget_units"])
    per_stream_cap = int(cfg["per_stream_max_updates"])

    if state["units_spent"] + unit_cost > daily_cap:
        raise QuotaExhausted(f"daily cap {daily_cap}u would be exceeded")

    per_stream_updates = int(state.get("stream_updates", {}).get(video_id, 0))
    if per_stream_updates + 1 > per_stream_cap:
        raise QuotaExhausted(f"per-stream cap {per_stream_cap} reached for {video_id}")

    state["units_spent"] += unit_cost
    state.setdefault("stream_updates", {})[video_id] = per_stream_updates + 1
    _write_quota_state(quota_file, state)


def assemble_description(
    *,
    condition_id: str,
    claim_id: str | None,
    objective_title: str | None,
    substrate_model: str,
    reaction_count: int | None = None,
    extra: str | None = None,
    attributions: list[Any] | None = None,
    attribution_max: int = 50,
    attribution_max_chars: int = 5000,
) -> str:
    """Assemble a description snippet from current research state.

    YT bundle B2 wire-in: when ``attributions`` carries
    AttributionEntry objects (URLs accumulated by the chat URL
    pipeline + other AttributionSource producers), they're rendered
    in a "Sources / Attribution" section grouped by kind. Hard caps:
    ``attribution_max`` entries (newest first) and a total character
    budget of ``attribution_max_chars`` for the section so a runaway
    URL flood can never blow YouTube's 5000-char description ceiling.
    """
    lines = [f"Condition: {condition_id}"]
    if claim_id:
        lines.append(f"Claim: {claim_id}")
    if objective_title:
        lines.append(f"Current objective: {objective_title}")
    lines.append(f"Substrate: {substrate_model}")
    if reaction_count is not None:
        lines.append(f"Reactions observed: {reaction_count}")
    if extra:
        lines.extend(["", extra])
    if attributions:
        attrib_block = _render_attribution_block(
            attributions, max_entries=attribution_max, max_chars=attribution_max_chars
        )
        if attrib_block:
            lines.extend(["", attrib_block])
    return "\n".join(lines)


def _render_attribution_block(
    entries: list[Any],
    *,
    max_entries: int,
    max_chars: int,
) -> str:
    """Render attribution entries as a grouped-by-kind section.

    Newest-first ordering; per-kind grouping; cap on entry count and
    total character budget so a chat URL flood never blows the
    description ceiling. Each entry renders as ``- {title or url}: {url}``
    when ``title`` is set, ``- {url}`` otherwise. De-duplicated by
    ``(kind, url)`` so multi-producer overlaps surface once.
    """
    if not entries:
        return ""
    # De-dup by (kind, url) — newest entry wins.
    seen: dict[tuple[str, str], Any] = {}
    for entry in sorted(entries, key=lambda e: getattr(e, "emitted_at", 0), reverse=True):
        key = (getattr(entry, "kind", ""), getattr(entry, "url", ""))
        if not key[1]:
            continue
        if key not in seen:
            seen[key] = entry
        if len(seen) >= max_entries:
            break
    if not seen:
        return ""
    by_kind: dict[str, list[Any]] = {}
    for entry in seen.values():
        by_kind.setdefault(entry.kind, []).append(entry)
    lines = ["Sources:"]
    for kind in sorted(by_kind.keys()):
        lines.append(f"  [{kind}]")
        for e in by_kind[kind]:
            label = e.title.strip() if getattr(e, "title", None) else None
            line = f"    - {label}: {e.url}" if label else f"    - {e.url}"
            lines.append(line)
    block = "\n".join(lines)
    if len(block) > max_chars:
        # Truncate at a line boundary just below the budget to keep
        # the section parseable rather than ending mid-URL.
        truncated_lines: list[str] = []
        running = 0
        for line in lines:
            if running + len(line) + 1 > max_chars - 50:  # 50-char overflow notice budget
                truncated_lines.append(f"  [...{len(lines) - len(truncated_lines)} more truncated]")
                break
            truncated_lines.append(line)
            running += len(line) + 1  # +1 for the join newline
        block = "\n".join(truncated_lines)
    return block


def update_video_description(
    video_id: str,
    description: str,
    *,
    dry_run: bool = False,
    cfg: dict[str, Any] | None = None,
    quota_file: Path | None = None,
) -> bool:
    """Update a YouTube video's description with quota enforcement.

    Returns True on success, False if quota-limited. Any other exception
    propagates (OAuth errors, API errors). When ``dry_run`` is True, the
    quota is still debited (so tests can exercise the rate-limiter) but
    no API call is made.
    """
    cfg = cfg or _load_config()
    try:
        check_and_debit(video_id, cfg=cfg, quota_file=quota_file)
    except QuotaExhausted as exc:
        policy = cfg.get("on_budget_exhausted", "skip_silent")
        if policy == "skip_silent":
            log.info("youtube_description: quota exhausted (%s); skipping", exc)
            return False
        raise

    if dry_run:
        log.info("youtube_description: dry-run update on %s (%d chars)", video_id, len(description))
        return True

    from shared.google_auth import get_google_credentials

    creds = get_google_credentials([cfg["oauth_scope"]])
    from googleapiclient.discovery import build

    service = build("youtube", "v3", credentials=creds)
    existing = service.videos().list(part="snippet", id=video_id).execute().get("items", [])
    if not existing:
        log.warning("youtube_description: no video %s visible to auth user", video_id)
        return False
    snippet = existing[0]["snippet"]
    snippet["description"] = description
    service.videos().update(part="snippet", body={"id": video_id, "snippet": snippet}).execute()
    return True
