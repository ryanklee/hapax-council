# FINDING-V Publisher Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the four new publishers identified in FINDING-V, retire the fifth, so the five currently-orphaned consumer wards render populated content on the live stream.

**Architecture:** Two compositor-embedded publishers (impingement cascade + direct-read redirect), one systemd timer (YouTube viewer count), one chat_monitor-embedded publisher (chat state), one retirement (grounding-provenance). Shared schemas in `shared/ward_publisher_schemas.py`; atomic-write pattern already in repo. See spec: `docs/superpowers/specs/2026-04-21-finding-v-publishers-design.md`.

**Tech Stack:** Python 3.12+, Pydantic, uv, pytest, systemd user units, prometheus_client.

---

## File Structure

**New files:**

- `shared/ward_publisher_schemas.py` — Pydantic models for all four publisher outputs.
- `agents/studio_compositor/recent_impingements_publisher.py` — Embedded publisher thread for `/dev/shm/hapax-compositor/recent-impingements.json`.
- `systemd/user/hapax-youtube-viewer-count.service` — Systemd unit for viewer-count script.
- `systemd/user/hapax-youtube-viewer-count.timer` — 90 s cadence.
- `tests/studio_compositor/test_recent_impingements_publisher.py`
- `tests/chat_monitor/test_chat_state_sidecar.py`
- `tests/shared/test_ward_publisher_schemas.py`

**Modified files:**

- `agents/studio_compositor/chat_ambient_ward.py` — Redirect read path to `/dev/shm/hapax-chat-signals.json` (retire the two alias file assumptions).
- `agents/chat_monitor/chat_signals.py` — Extend `ChatSignalsAggregator` to also emit `chat-state.json`.
- `agents/studio_compositor/compositor.py` — Spawn `RecentImpingementsPublisher` in the compositor startup.
- `docs/research/2026-04-20-wiring-audit-findings.md` — Mark `grounding-provenance.jsonl` RETIRED in FINDING-V, pointing at this plan.

---

## Task 1: Shared publisher schemas

**Files:**

- Create: `shared/ward_publisher_schemas.py`
- Test: `tests/shared/test_ward_publisher_schemas.py`

- [ ] **Step 1: Write failing schema round-trip test**

```python
# tests/shared/test_ward_publisher_schemas.py
from shared.ward_publisher_schemas import (
    RecentImpingementEntry,
    RecentImpingements,
    ChatSignalsSnapshot,
    ChatState,
)

def test_recent_impingements_round_trip():
    r = RecentImpingements(
        generated_at=1000.0,
        entries=[RecentImpingementEntry(path="focus.narrow", value=0.82, family="focus")],
    )
    payload = r.model_dump_json()
    restored = RecentImpingements.model_validate_json(payload)
    assert restored == r

def test_chat_state_projection_from_snapshot():
    snap = ChatSignalsSnapshot(
        generated_at=1000.0,
        message_count_60s=12,
        unique_authors_60s=4,
    )
    state = ChatState(
        generated_at=snap.generated_at,
        total_messages=snap.message_count_60s,
        unique_authors=snap.unique_authors_60s,
    )
    assert state.total_messages == 12
    assert state.unique_authors == 4
```

- [ ] **Step 2: Run test, confirm it fails with ImportError**

```bash
uv run pytest tests/shared/test_ward_publisher_schemas.py -v
```

- [ ] **Step 3: Implement schemas**

```python
# shared/ward_publisher_schemas.py
from pydantic import BaseModel, ConfigDict

class RecentImpingementEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: str
    value: float
    family: str

class RecentImpingements(BaseModel):
    model_config = ConfigDict(frozen=True)
    generated_at: float
    entries: list[RecentImpingementEntry]

class ChatSignalsSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    generated_at: float
    t5_rate_per_min: float = 0.0
    t6_rate_per_min: float = 0.0
    unique_t4_plus_authors_60s: int = 0
    t4_plus_rate_per_min: float = 0.0
    message_count_60s: int = 0
    unique_authors_60s: int = 0
    message_rate_per_min: float = 0.0
    audience_engagement: float = 0.0

class ChatState(BaseModel):
    model_config = ConfigDict(frozen=True)
    generated_at: float
    total_messages: int
    unique_authors: int
```

- [ ] **Step 4: Run tests, confirm PASS**

```bash
uv run pytest tests/shared/test_ward_publisher_schemas.py -v
```

- [ ] **Step 5: Commit**

```bash
git add shared/ward_publisher_schemas.py tests/shared/test_ward_publisher_schemas.py
git commit -m "feat(shared): ward publisher schemas for FINDING-V remediation"
```

---

## Task 2: `recent-impingements.json` publisher

**Files:**

- Create: `agents/studio_compositor/recent_impingements_publisher.py`
- Modify: `agents/studio_compositor/compositor.py` (spawn in startup)
- Test: `tests/studio_compositor/test_recent_impingements_publisher.py`

- [ ] **Step 1: Write failing publisher behavior test**

```python
# tests/studio_compositor/test_recent_impingements_publisher.py
import json
import time
from pathlib import Path
from unittest.mock import patch

from agents.studio_compositor.recent_impingements_publisher import (
    RecentImpingementsPublisher,
    TOP_N,
)

def test_reads_impingements_and_writes_top_n(tmp_path: Path):
    src = tmp_path / "impingements.jsonl"
    dst = tmp_path / "recent-impingements.json"
    lines = [
        json.dumps({"intent_family": f"family_{i}", "salience": i * 0.1}) + "\n"
        for i in range(10)
    ]
    src.write_text("".join(lines))

    pub = RecentImpingementsPublisher(src=src, dst=dst)
    pub.tick()

    assert dst.exists()
    payload = json.loads(dst.read_text())
    assert len(payload["entries"]) == TOP_N
    assert payload["entries"][0]["value"] == 0.9  # highest salience first

def test_missing_source_does_not_crash(tmp_path: Path):
    pub = RecentImpingementsPublisher(
        src=tmp_path / "nonexistent.jsonl",
        dst=tmp_path / "recent-impingements.json",
    )
    pub.tick()  # no exception
    assert not (tmp_path / "recent-impingements.json").exists()

def test_malformed_line_skipped(tmp_path: Path):
    src = tmp_path / "impingements.jsonl"
    dst = tmp_path / "recent-impingements.json"
    src.write_text(
        json.dumps({"intent_family": "good", "salience": 0.5}) + "\n"
        "this is not json\n"
    )
    pub = RecentImpingementsPublisher(src=src, dst=dst)
    pub.tick()
    payload = json.loads(dst.read_text())
    assert len(payload["entries"]) == 1
```

- [ ] **Step 2: Run test, confirm it fails with ImportError**

```bash
uv run pytest tests/studio_compositor/test_recent_impingements_publisher.py -v
```

- [ ] **Step 3: Implement publisher**

```python
# agents/studio_compositor/recent_impingements_publisher.py
from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

from shared.ward_publisher_schemas import (
    RecentImpingementEntry,
    RecentImpingements,
)

log = logging.getLogger(__name__)
TOP_N = 6
TICK_INTERVAL_SEC = 0.5
TAIL_BYTES = 4096

class RecentImpingementsPublisher:
    """Reads top-N impingements by salience and writes to the compositor SHM.

    Runs as a background thread in the compositor process.
    """

    def __init__(self, src: Path, dst: Path) -> None:
        self.src = src
        self.dst = dst
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, name="recent-impingements-publisher", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                log.exception("recent-impingements publisher tick failed")
            self._stop.wait(TICK_INTERVAL_SEC)

    def tick(self) -> None:
        if not self.src.exists():
            return
        with self.src.open("rb") as fh:
            fh.seek(max(0, self.src.stat().st_size - TAIL_BYTES))
            buf = fh.read().decode("utf-8", errors="replace")
        rows: list[tuple[float, RecentImpingementEntry]] = []
        for line in buf.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            family = obj.get("intent_family") or obj.get("family") or ""
            salience = float(obj.get("salience", 0.0))
            rows.append(
                (
                    salience,
                    RecentImpingementEntry(
                        path=family, value=salience, family=family
                    ),
                )
            )
        rows.sort(key=lambda r: r[0], reverse=True)
        entries = [entry for _, entry in rows[:TOP_N]]
        payload = RecentImpingements(generated_at=time.time(), entries=entries)
        self._write(payload)

    def _write(self, payload: RecentImpingements) -> None:
        self.dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.dst.with_suffix(self.dst.suffix + ".tmp")
        tmp.write_text(payload.model_dump_json())
        tmp.replace(self.dst)
```

- [ ] **Step 4: Run tests, confirm PASS**

```bash
uv run pytest tests/studio_compositor/test_recent_impingements_publisher.py -v
```

- [ ] **Step 5: Wire into compositor startup**

Find the compositor's thread-startup site in `agents/studio_compositor/compositor.py` (look for existing `CairoSourceRunner.start()` calls). Add:

```python
from pathlib import Path
from agents.studio_compositor.recent_impingements_publisher import RecentImpingementsPublisher

_recent_pub = RecentImpingementsPublisher(
    src=Path("/dev/shm/hapax-dmn/impingements.jsonl"),
    dst=Path("/dev/shm/hapax-compositor/recent-impingements.json"),
)
_recent_pub.start()
# Register _recent_pub.stop in the compositor's shutdown hook.
```

- [ ] **Step 6: Commit**

```bash
git add agents/studio_compositor/recent_impingements_publisher.py \
  agents/studio_compositor/compositor.py \
  tests/studio_compositor/test_recent_impingements_publisher.py
git commit -m "feat(compositor): recent-impingements publisher (FINDING-V P1)"
```

---

## Task 3: Chat ambient ward direct-read

**Files:**

- Modify: `agents/studio_compositor/chat_ambient_ward.py`
- Test: existing tests for `ChatAmbientWard` (extend to cover direct-read path)

- [ ] **Step 1: Audit existing test coverage**

```bash
uv run pytest tests/studio_compositor/ -k chat_ambient -v
```

- [ ] **Step 2: Update ward to read `/dev/shm/hapax-chat-signals.json` directly**

Locate the current two reads in `agents/studio_compositor/chat_ambient_ward.py` (likely named `chat_keyword_aggregate_path` and `chat_tier_aggregates_path`). Replace both with a single read of `/dev/shm/hapax-chat-signals.json`, typed through `ChatSignalsSnapshot`:

```python
from shared.ward_publisher_schemas import ChatSignalsSnapshot

_CHAT_SIGNALS_PATH = Path("/dev/shm/hapax-chat-signals.json")

def _read_chat_signals(self) -> ChatSignalsSnapshot | None:
    if not _CHAT_SIGNALS_PATH.exists():
        return None
    try:
        return ChatSignalsSnapshot.model_validate_json(_CHAT_SIGNALS_PATH.read_text())
    except Exception:
        return None
```

Replace both alias reads with this single call. Field access unchanged (`snapshot.t5_rate_per_min`, `snapshot.t4_plus_rate_per_min`, etc.).

- [ ] **Step 3: Add test for the direct-read path**

```python
def test_chat_ambient_reads_chat_signals_direct(tmp_path, monkeypatch):
    # write a chat-signals snapshot, monkey-patch _CHAT_SIGNALS_PATH,
    # assert the ward renders expected BitchX grammar cells.
    ...
```

- [ ] **Step 4: Run tests, confirm PASS**

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/chat_ambient_ward.py tests/studio_compositor/
git commit -m "feat(compositor): chat-ambient direct read from chat-signals (FINDING-V P2+P3 merge)"
```

---

## Task 4: YouTube viewer count systemd activation

**Files:**

- Create: `systemd/user/hapax-youtube-viewer-count.service`
- Create: `systemd/user/hapax-youtube-viewer-count.timer`
- Verify: `scripts/youtube-viewer-count-producer.py` still runs standalone (no test changes).

- [ ] **Step 1: Author service unit**

```ini
# systemd/user/hapax-youtube-viewer-count.service
[Unit]
Description=Hapax YouTube viewer count publisher (FINDING-V P4)
After=hapax-secrets.service
Requires=hapax-secrets.service

[Service]
Type=oneshot
EnvironmentFile=%h/.config/hapax/secrets.env
WorkingDirectory=%h/projects/hapax-council
ExecStart=%h/projects/hapax-council/.venv/bin/python scripts/youtube-viewer-count-producer.py --once
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

- [ ] **Step 2: Author timer unit**

```ini
# systemd/user/hapax-youtube-viewer-count.timer
[Unit]
Description=Hapax YouTube viewer count publisher cadence (90s)
After=graphical-session.target

[Timer]
OnBootSec=120
OnUnitActiveSec=90
AccuracySec=5
Unit=hapax-youtube-viewer-count.service

[Install]
WantedBy=timers.target
```

- [ ] **Step 3: Verify producer script supports `--once`**

```bash
uv run python scripts/youtube-viewer-count-producer.py --once --dry-run 2>&1 | head -20
```

If `--once` is not a flag, add it to the argparser to do a single publish then exit (systemd `Type=oneshot` requires single-shot semantics).

- [ ] **Step 4: Commit**

```bash
git add systemd/user/hapax-youtube-viewer-count.service systemd/user/hapax-youtube-viewer-count.timer
# if argparse was modified: scripts/youtube-viewer-count-producer.py
git commit -m "feat(systemd): youtube-viewer-count timer activation (FINDING-V P4)"
```

- [ ] **Step 5: Post-merge operator step**

Document in the PR body: operator runs `systemctl --user daemon-reload && systemctl --user enable --now hapax-youtube-viewer-count.timer` after merge. Then verify `cat /dev/shm/hapax-compositor/youtube-viewer-count.txt` returns an integer within 120 s.

---

## Task 5: `chat-state.json` sidecar

**Files:**

- Modify: `agents/chat_monitor/chat_signals.py`
- Test: `tests/chat_monitor/test_chat_state_sidecar.py`

- [ ] **Step 1: Write failing sidecar test**

```python
# tests/chat_monitor/test_chat_state_sidecar.py
import json
from pathlib import Path
from agents.chat_monitor.chat_signals import ChatSignalsAggregator

def test_aggregator_writes_chat_state(tmp_path: Path, monkeypatch):
    state_path = tmp_path / "chat-state.json"
    monkeypatch.setattr(
        "agents.chat_monitor.chat_signals.CHAT_STATE_PATH", state_path
    )
    agg = ChatSignalsAggregator()
    agg._message_count_60s = 7
    agg._unique_authors_60s = 3
    agg.write_chat_state_snapshot()

    assert state_path.exists()
    payload = json.loads(state_path.read_text())
    assert payload["total_messages"] == 7
    assert payload["unique_authors"] == 3
    assert "generated_at" in payload
```

- [ ] **Step 2: Implement sidecar method**

Add to `agents/chat_monitor/chat_signals.py`:

```python
import time
from pathlib import Path
from shared.ward_publisher_schemas import ChatState

CHAT_STATE_PATH = Path("/dev/shm/hapax-compositor/chat-state.json")

class ChatSignalsAggregator:
    # ... existing ...

    def write_chat_state_snapshot(self) -> None:
        state = ChatState(
            generated_at=time.time(),
            total_messages=self._message_count_60s,
            unique_authors=self._unique_authors_60s,
        )
        CHAT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = CHAT_STATE_PATH.with_suffix(".json.tmp")
        tmp.write_text(state.model_dump_json())
        tmp.replace(CHAT_STATE_PATH)
```

- [ ] **Step 3: Wire into the aggregator's existing write cycle**

Find where the existing `/dev/shm/hapax-chat-signals.json` write happens (likely in a periodic `aggregate()` or `_write_signals()` method). Add a call to `self.write_chat_state_snapshot()` immediately after.

- [ ] **Step 4: Run tests, confirm PASS**

- [ ] **Step 5: Commit**

```bash
git add agents/chat_monitor/chat_signals.py tests/chat_monitor/test_chat_state_sidecar.py
git commit -m "feat(chat_monitor): chat-state sidecar writer (FINDING-V P6)"
```

---

## Task 6: Retire `grounding-provenance.jsonl` from FINDING-V

**Files:**

- Modify: `docs/research/2026-04-20-wiring-audit-findings.md`

- [ ] **Step 1: Mark RETIRED in the audit**

Locate the §FINDING-V table entry for `grounding-provenance.jsonl`. Replace its row with:

```markdown
| `grounding-provenance.jsonl` | GroundingProvenanceTickerCairoSource | **RETIRED** — consumer tails INTENT JSONL directly; see `docs/superpowers/specs/2026-04-21-finding-v-publishers-design.md` §5. No publisher needed. |
```

- [ ] **Step 2: Commit**

```bash
git add docs/research/2026-04-20-wiring-audit-findings.md
git commit -m "docs(audit): retire grounding-provenance.jsonl from FINDING-V (consumer tails INTENT JSONL)"
```

---

## Task 7: Observability

**Files:**

- Modify: `agents/studio_compositor/recent_impingements_publisher.py`
- Modify: `agents/chat_monitor/chat_signals.py`

Both newly-authored publishers gain Prometheus metrics:

```python
from prometheus_client import Counter, Gauge

WRITES = Counter(
    "hapax_publisher_writes_total",
    "Publisher successful writes",
    ["publisher"],
)
ERRORS = Counter(
    "hapax_publisher_write_errors_total",
    "Publisher write errors",
    ["publisher"],
)
FILE_AGE = Gauge(
    "hapax_publisher_file_age_seconds",
    "Publisher-emitted file age",
    ["publisher"],
)
```

Increment on every write / error; set `FILE_AGE.labels(publisher="recent-impingements").set(0.0)` at write time, consumer can read later-as-staleness.

- [ ] **Step 1: Add metrics to impingements publisher, assert in test**

- [ ] **Step 2: Add metrics to chat-state sidecar, assert in test**

- [ ] **Step 3: Run tests, confirm PASS**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(publishers): Prometheus metrics for FINDING-V writers"
```

---

## Task 8: End-to-end PR and post-merge verification

- [ ] **Step 1: Open PR**

```bash
git push -u origin feat/finding-v-publishers
gh pr create --title "feat(publishers): FINDING-V remediation — 4 publishers + 1 retirement" --body "$(cat <<'EOF'
## Summary

- Ships publishers for `recent-impingements.json`, `chat-state.json`, `youtube-viewer-count.txt` activation.
- Redirects `ChatAmbientWard` to read `/dev/shm/hapax-chat-signals.json` directly, closing two FINDING-V alias entries with one change.
- Retires `grounding-provenance.jsonl` from the orphan-publishers list (consumer already tails INTENT JSONL).

Spec: `docs/superpowers/specs/2026-04-21-finding-v-publishers-design.md`
Research: `docs/research/2026-04-21-missing-publishers-research.md`

## Test plan

- [ ] `uv run pytest tests/shared/test_ward_publisher_schemas.py tests/studio_compositor/test_recent_impingements_publisher.py tests/chat_monitor/test_chat_state_sidecar.py -v`
- [ ] Admin-merge through known CI drift (same pattern as #1127/#1133/#1138/#1144).
- [ ] Post-merge: operator enables the YouTube viewer-count timer, verifies `cat /dev/shm/hapax-compositor/youtube-viewer-count.txt` returns an integer.
- [ ] Live-stream observation: five orphan wards render populated (non-fallback) content within 60 s of compositor restart.
EOF
)"
```

- [ ] **Step 2: Operator verifies five wards render on live stream**

Open the stream output, confirm: `ImpingementCascadeCairoSource` shows entries, `ChatAmbientWard` shows non-zero counts when chat is active, `WhosHereCairoSource` shows viewer N>1 when livestream has viewers, `StreamOverlayCairoSource` shows `[CHAT|…]` with real numbers, `GroundingProvenanceTickerCairoSource` continues to show provenance from INTENT JSONL (unchanged).

---

## Sequencing Notes

Tasks are independent except:

- Task 2, 3, 5 depend on Task 1 (shared schemas).
- Task 7 (observability) depends on Tasks 2 + 5 existing.
- Task 4 (systemd) is independent; can ship in its own PR if desired.
- Task 6 (retirement) is independent; trivial.

Recommended sequence: 1 → (2, 3, 5 in parallel) → 7 → 4 → 6 → 8.

## Acceptance Criteria

Mirrored from spec §13:

- All four IMPLEMENT verdicts ship with tests and Prometheus metrics wired.
- Consumer wards render populated content on the live stream within 60 s of service start (no bare-fallback flicker).
- FINDING-V audit entry for `grounding-provenance.jsonl` marked RETIRED.
- No new SHM ownership boundaries introduced.
