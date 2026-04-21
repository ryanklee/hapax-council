---
date: 2026-04-21
author: delta
status: draft
supersedes: null
related:
  - docs/research/2026-04-21-missing-publishers-research.md
  - docs/research/2026-04-20-wiring-audit-findings.md
  - docs/research/2026-04-21-comprehensive-wiring-audit-alpha.md
scope: publisher architecture for 5 orphan-consumer wards identified in FINDING-V
---

# FINDING-V Publisher Remediation — Design

## 1. Context

Six ward inputs were flagged in `docs/research/2026-04-20-wiring-audit-findings.md` §FINDING-V as having no upstream producer. The research drop at `docs/research/2026-04-21-missing-publishers-research.md` resolved per-publisher verdicts:

| File | Consumer | Verdict |
|---|---|---|
| `recent-impingements.json` | `ImpingementCascadeCairoSource` (`hothouse_sources.py`) | **IMPLEMENT** |
| `chat-keyword-aggregate.json` | `ChatAmbientWard` (t5/t6 rate fields) | **IMPLEMENT (alias)** |
| `chat-tier-aggregates.json` | `ChatAmbientWard` (t4+ counter fields) | **IMPLEMENT (alias, merged)** |
| `youtube-viewer-count.txt` | `WhosHereCairoSource` | **IMPLEMENT (activate)** |
| `grounding-provenance.jsonl` | `GroundingProvenanceTickerCairoSource` | **RETIRE** (consumer already tails INTENT JSONL) |
| `chat-state.json` | `StreamOverlayCairoSource` | **IMPLEMENT (sidecar)** |

This spec defines the architectural home, data contracts, lifecycle, and observability for the four new publishers plus the one retirement. Publishers 2 and 3 collapse into a single aliasing concern.

## 2. Scope

**In scope**

- Process/service location for each publisher
- Pydantic schemas for each output file
- Cadence contracts
- Atomic write pattern reuse
- Observability (Prometheus counters + freshness gauges per existing pattern)
- Retirement of `grounding-provenance.jsonl` from the orphan list
- Alias strategy for chat-ambient ward's two field groups

**Out of scope**

- HARDM perception cascade publishers (FINDING-V-corollary — separate spec)
- FINDING-W (pipeline-composition decisions)
- New consumer ward authorship
- Chat monitor architectural rewrite — this spec only reads from the existing aggregator

## 3. Architectural Baseline

Every existing compositor-ward publisher writes to `/dev/shm/hapax-compositor/<filename>` via atomic `tmp + os.replace`. Readers poll at `rate_hz` declared on the `CairoSource`. Staleness cutoff is 10s in all current consumers.

**Process locations observed in the repo:**

- Compositor-internal Cairo sources: in-process threads via `CairoSourceRunner` (`agents/studio_compositor/cairo_source.py`)
- Chat aggregator: `ChatSignalsAggregator` in `agents/chat_monitor/` as a side-thread of `chat_monitor` service
- YouTube viewer count: standalone script `scripts/youtube-viewer-count-producer.py` intended for systemd timer invocation
- Daimonion impingements: written to `/dev/shm/hapax-dmn/impingements.jsonl` by daimonion's recruitment loop

The spec defaults to the simplest location per publisher; see §5.

## 4. Data Contracts

All schemas declared as frozen Pydantic models in `shared/ward_publisher_schemas.py` (new file). One schema per output file. Schemas are imported by both the publisher (for validation on write) and by a single consolidated test (for contract regression). The consumer wards already parse these files via ad-hoc `.get("field")` lookups; consumer changes are optional but recommended to use the shared schemas.

### 4.1 `recent-impingements.json`

```python
class RecentImpingementEntry(BaseModel, frozen=True):
    path: str
    value: float
    family: str

class RecentImpingements(BaseModel, frozen=True):
    generated_at: float  # epoch seconds
    entries: list[RecentImpingementEntry]  # top-N by salience, N<=6
```

**Source:** tail-read `/dev/shm/hapax-dmn/impingements.jsonl`, select top-6 by `salience`, project into `RecentImpingementEntry` via `(path=intent_family, value=salience, family=intent_family)`.

### 4.2 `chat-keyword-aggregate.json` and `chat-tier-aggregates.json`

Both files are **symlinks or aliases** of a single source file. The research verdict collapsed them into one canonical file. Two options:

- **Option A (simplest):** Patch `ChatAmbientWard` to read directly from `/dev/shm/hapax-chat-signals.json` and remove the two alias paths from the FINDING-V list. The ward's two field groups come from the same file.
- **Option B:** Have `ChatSignalsAggregator` write three files: canonical + two aliases (`chat-keyword-aggregate.json` + `chat-tier-aggregates.json`) with identical content. Back-compat for any external consumer reading the alias paths.

**Recommended: Option A** — the consumer is internal to the repo, read the source file directly. Reduces duplication and staleness risk. Defer Option B only if an external reader surfaces.

Shared schema (re-used by Publisher 6):

```python
class ChatSignalsSnapshot(BaseModel, frozen=True):
    generated_at: float
    t5_rate_per_min: float = 0.0
    t6_rate_per_min: float = 0.0
    unique_t4_plus_authors_60s: int = 0
    t4_plus_rate_per_min: float = 0.0
    message_count_60s: int = 0
    unique_authors_60s: int = 0
    message_rate_per_min: float = 0.0
    audience_engagement: float = 0.0  # [0, 1]
```

### 4.3 `youtube-viewer-count.txt`

**Not JSON.** Plain integer text, no newline, no trailing whitespace. Consumer uses `int(text.strip())`. Producer already exists (`scripts/youtube-viewer-count-producer.py`) and uses atomic tmp+rename. Activation only.

### 4.4 `chat-state.json`

```python
class ChatState(BaseModel, frozen=True):
    generated_at: float
    total_messages: int
    unique_authors: int
```

**Source:** `ChatSignalsSnapshot` field projection: `total_messages = message_count_60s`, `unique_authors = unique_authors_60s`. Sidecar service emits the simplified schema every ~30s alongside the existing chat-signals write.

## 5. Publisher Hosts

| File | Host | Rationale |
|---|---|---|
| `recent-impingements.json` | **compositor-embedded thread** (new `CairoSourceRunner` sibling, not a Cairo source but same threading model) | Needs read access to `/dev/shm/hapax-dmn/` AND write access to `/dev/shm/hapax-compositor/`; tail-read pattern is proven in compositor-side code (`legibility_sources.py::_read_recent_intents`). New module: `agents/studio_compositor/recent_impingements_publisher.py`. |
| Chat ambient ward inputs (Option A) | **no new host** — redirect consumer read | Internal-only consumer; patch `agents/studio_compositor/chat_ambient_ward.py` to read `/dev/shm/hapax-chat-signals.json` directly. Remove the two alias paths from FINDING-V. |
| `youtube-viewer-count.txt` | **systemd user timer** | Producer already designed as a timer-triggered script. New units: `systemd/hapax-youtube-viewer-count.{service,timer}`. Cadence 90s per the existing script. |
| `chat-state.json` | **chat_monitor-embedded** (extend `ChatSignalsAggregator`) | Same process already owns the source data. Projection is a 2-field slice. New method: `ChatSignalsAggregator.write_chat_state_snapshot()`. |
| `grounding-provenance.jsonl` | **RETIRE** | Consumer already tails INTENT JSONL via `_read_latest_intent()`. Update the orphan-publishers audit to close this entry. |

## 6. Cadence Contract

Publisher cadence ≤ 3× consumer cadence. Consumer wards run at 2.0 Hz.

| Publisher | Source cadence | Publisher cadence | Consumer cadence |
|---|---|---|---|
| `recent-impingements.json` | daimonion writes 10–100 ms | 500 ms | 500 ms (2.0 Hz) |
| `chat-state.json` | `ChatSignalsAggregator` 30 s | 30 s | 500 ms (consumer reads stale-but-coherent) |
| `youtube-viewer-count.txt` | YouTube API call | 90 s | 500 ms (consumer reads stale-but-coherent) |
| chat-ambient direct-read | `ChatSignalsAggregator` 30 s | 30 s | 500 ms (consumer reads stale-but-coherent) |

## 7. Write Pattern

All publishers use the atomic tmp+rename pattern already in use elsewhere in the repo. Canonical implementation in `shared/atomic_write.py` (new if not already present; check before authoring).

```python
def atomic_write_json(path: Path, data: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data.model_dump_json())
    tmp.replace(path)

def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)
```

Fail-closed: any write error propagates; callers log + continue (staleness degrades gracefully on the consumer side).

## 8. Observability

Each new publisher exposes two Prometheus metrics via the existing compositor or chat_monitor Prometheus registries:

- `hapax_publisher_writes_total{publisher="<name>"}` — counter, increments on every successful write
- `hapax_publisher_file_age_seconds{publisher="<name>"}` — gauge, set to `now - generated_at` on every write

The systemd-hosted YouTube publisher exposes metrics via the same counter/gauge pattern on `127.0.0.1:9484` (new port), or reuses an existing publisher-focused scraper if one exists.

Freshness alerts are out of scope for this spec — Grafana dashboard work is a follow-up once the publishers have been in production for 48h.

## 9. Failure Modes

| Mode | Detection | Handling |
|---|---|---|
| Source file missing | publisher IOError on read | log WARN, skip this cycle, retry next cadence tick |
| Source file stale | `generated_at` older than 2× source cadence | log INFO, publish anyway (consumer handles stale) |
| Write failure | `tmp.replace(path)` error | log ERROR, skip this cycle, surface via metric `hapax_publisher_write_errors_total` |
| Publisher crash | process supervisor (compositor/systemd) restart policy | existing supervision suffices; no new policy needed |

## 10. Test Coverage

Each publisher is covered by a dedicated test module under `tests/studio_compositor/` (or `tests/chat_monitor/` for the chat sidecar). Each test module covers:

- Happy-path write (schema validates + file contains the written content)
- Source-missing path (no write or empty-default write, per publisher)
- Atomic write (no partial file visible mid-write — use `os.replace` mock)
- Schema round-trip (write → parse → compare)

Consumer wards are not retested — existing tests continue to cover them.

## 11. Out-of-Scope Clarifications

- **No MockChatPublisher change.** `scripts/mock-chat.py` remains for local dev; production uses the `ChatSignalsAggregator` extension.
- **No viewer-count source switching.** The existing YouTube Data API path stays; HLS-manifest scraping is a separate (non-FINDING-V) concern.
- **No re-architecting of SHM ownership.** Compositor continues to own `/dev/shm/hapax-compositor/`; daimonion owns `/dev/shm/hapax-dmn/`; chat_monitor writes to `/dev/shm/hapax-chat-signals.json` (unchanged path).

## 12. Dependencies and Risks

- `recent-impingements.json` publisher depends on daimonion's impingements.jsonl format remaining stable. If daimonion changes the JSONL schema, this publisher's tail-read will degrade to warnings; consumer renders fallback state. No cascading failure.
- `chat-state.json` sidecar depends on `ChatSignalsSnapshot` schema; any field rename in `ChatSignals` would break the projection. Pydantic model enforces this at import time via the shared schema.

## 13. Acceptance Criteria

- All four IMPLEMENT verdicts ship with tests and Prometheus metrics wired.
- Consumer wards render populated content on the live stream within 60 s of service start (no bare-fallback flicker).
- FINDING-V audit entry for `grounding-provenance.jsonl` marked RETIRED with a pointer to this spec.
- No new SHM ownership boundaries introduced.
