# FINDING-V — Missing Publishers Research

**Author:** Delta (pydantic-ai research)  
**Date:** 2026-04-21  
**References:**  
- Audit: `docs/research/2026-04-20-wiring-audit-findings.md` §FINDING-V (lines 650–688)
- Audit: `docs/research/2026-04-20-wiring-audit-findings.md` §Per-Ward Signal-Publisher Investigation (line 630)
- Handoff: `~/.cache/hapax/relay/alpha-to-delta-2026-04-21-finding-v-producers.md`

---

## Executive Summary

Six ward inputs have no upstream producers: **recent-impingements.json**, **chat-keyword-aggregate.json**, **chat-tier-aggregates.json**, **youtube-viewer-count.txt**, **grounding-provenance.jsonl**, and **chat-state.json** (production). Five wards are shipped with Cairo consumer code but cannot render because the upstream data never writes. This research examines each ward's expectations, available upstream data, cadence requirements, and recommends IMPLEMENT or RETIRE verdicts per ward.

---

## Context

Consumer wards run at **2.0 Hz** (default compositor cadence per `default.json`). All are BitchX-grammar emissive surfaces. All degrade gracefully when input files are absent or stale. All read from `/dev/shm/hapax-compositor/` (SHM within the compositor process boundary).

---

## Publisher 1: `recent-impingements.json`

### Consumer: ImpingementCascadeCairoSource (hothouse_sources.py)

**Behavior:** Renders the top-N perceptual impingements (narrowed-salience feed). 480×360 emissive surface, row-stacked signals with per-row slide-in (400 ms envelope) and alpha-decay ghost trail. Expected fields:
- `generated_at` (float, epoch seconds) — staleness cutoff 10s
- `entries` (list of dicts) — each with `path` (str), `value` (float), `family` (str)
- `entries[:N]` capped at limit for layout

**Fallback:** when file absent or stale >10s, cascades to raw perception-state walk via `_active_perceptual_signals()`. Ward renders 6 signals max, each as emissive row with centre-dot + Pango label.

### Upstream Availability

**Source:** `/dev/shm/hapax-dmn/impingements.jsonl` — the full impingement queue written by daimonion (1 per 100–500 ms depending on load). Existing query: `_read_recent_intents()` in legibility_sources.py shows the tail-read pattern (tail 4096 bytes, split lines, parse last as JSON).

**Schema:** each impingement is a dict with `narrative`, `dimensions`, `material`, `salience`, `grounding_provenance`, `intent_family`, etc. Sortable by salience. Top-6 by salience yields the cascade input.

**Challenge:** `/dev/shm/hapax-dmn/` is owned by daimonion; `/dev/shm/hapax-compositor/` is the compositor's write-allowed path. The publisher must **run inside the compositor process** or as a side-car feeding it.

### Cadence + Size Budget

- **Cadence:** 2.0 Hz (consumer rate_hz). Data should refresh ~500 ms to feel responsive.
- **Source cadence:** daimonion emits impingements at variable rate (10–100 ms inter-arrival during active recruitment, sparse during idle).
- **Strategy:** tail-read `/dev/shm/hapax-dmn/impingements.jsonl` every 500 ms, extract top-6 by salience, write JSON to `recent-impingements.json` with `generated_at` timestamp.
- **Size:** ~400–600 bytes (6 entries × 60–80 bytes each).

### Verdict: **IMPLEMENT**

**Rationale:**
- Upstream data exists and is actively written by daimonion.
- Consumer ward is shipped and renders correctly when data present.
- Tail-read pattern is proven (used in legibility_sources.py).
- Salience-weighted feed is more useful than full impingement dump for visual comprehension.
- Zero operator input required; pure data transformation.

---

## Publisher 2: `chat-keyword-aggregate.json`

### Consumer: ChatAmbientWard (chat_ambient_ward.py) — **50% of inputs**

**Behavior:** Renders chat signal aggregates as BitchX grammar: `[Mode +v +H]` cell. Reads state dict keys (not files directly):
- `t5_rate_per_min` (float) — voice/participation rate, saturates at 6/min, renders +v intensity
- Palette role: `accent_green` if >0.5/min, muted below
- T5 classification = structural (high-value participation per ChatTier enum)

**Fallback:** when state missing, renders `[Mode +v +H]` with all zeros/muted.

### Upstream Availability

**Source:** `ChatSignals` dataclass (chat_signals.py) already computes `t5_rate_per_min` and `t6_rate_per_min` aggregates. These are written to `/dev/shm/hapax-chat-signals.json` by `ChatSignalsAggregator` every ~30s (per chat_signals.py docstring).

**Schema:** `ChatSignals` includes:
```python
t5_rate_per_min: float = 0.0
t6_rate_per_min: float = 0.0
unique_t4_plus_authors_60s: int = 0
t4_plus_rate_per_min: float = 0.0
```
All four are pure aggregates derived from `ChatMessage.classification` tier labels (no identity leak per axiom redaction).

**Challenge:** The file name is `chat-signals.json`, not `chat-keyword-aggregate.json`. **Rename or alias the output path**, or have the ward read from the correct path.

### Cadence + Size Budget

- **Cadence:** 2.0 Hz (consumer), but source writes ~30s. **Acceptable lag:** consumer polls file, reads stale data; sub-second responsiveness not expected.
- **Size:** ~200 bytes (minimal JSON with 4 floats + metadata).

### Verdict: **IMPLEMENT**

**Rationale:**
- Upstream aggregator already exists and computes all required fields.
- No new data source needed; redirect existing output.
- Zero operator input required.
- Ward is shipped and functional when data present.

**Action:** Confirm `/dev/shm/hapax-chat-signals.json` path or alias to `chat-keyword-aggregate.json` in the consumer.

---

## Publisher 3: `chat-tier-aggregates.json`

### Consumer: ChatAmbientWard — **other 50% of inputs**

**Behavior:** Renders chat tier aggregates as `[Users(#hapax:1/N)]` and rate-gauge cells. Reads:
- `unique_t4_plus_authors_60s` (int) — unique T4+ (high-value) authors in 60s window, N in gauge
- `t4_plus_rate_per_min` (float) — T4+ message rate, 0–60 msg/min → 0–8 gauge cells (log-scaled)
- `message_rate_per_min` (float) — overall rate for engagement cell conditional
- `audience_engagement` (float) — [0, 1] determines quiet/active/omitted cell

### Upstream Availability

**Source:** Same `ChatSignals` aggregator writes all four fields. Same `/dev/shm/hapax-chat-signals.json`.

**Schema:** Identical to Publisher 2. The two "publishers" are a false split — they are **one file with two field subsets read by the same ward**.

### Cadence + Size Budget

- **Same as Publisher 2:** ~30s source cadence, ~200 bytes total.

### Verdict: **IMPLEMENT (merged with Publisher 2)**

**Rationale:**
- Same upstream source, same data, same path.
- The two "missing publishers" are actually **one publisher serving two consumer field groups**.
- No new work needed beyond confirming the path alias.

---

## Publisher 4: `youtube-viewer-count.txt`

### Consumer: WhosHereCairoSource (hothouse_sources.py)

**Behavior:** Renders viewer count as `[hapax:1/N]` grammar where N = 1 (operator, always) + external (YouTube viewers). Reads:
- File format: plain integer text, no newline, no JSON
- Fallback: `0` on missing file (render N=1, audience colour muted)
- Field: `external_viewers` parsed via `int(text.strip())`

### Upstream Availability

**Source:** **Already implemented.** Script `scripts/youtube-viewer-count-producer.py` exists and is fully functional:
- Polls YouTube Data API every 90s
- Fetches `concurrentViewers` from `videos.list` endpoint
- Writes plain integer to `/dev/shm/hapax-compositor/youtube-viewer-count.txt` via atomic tmp+rename
- Handles offline broadcasts (writes `0`)
- Includes Prometheus freshness metrics

**Quota cost:** ~1 unit/call (960 units/day at 90s cadence). Feasible under standard quota.

### Cadence + Size Budget

- **Cadence:** 90s (production), acceptable for viewer count (changes every 10–30s in typical stream, no sub-minute churn expected)
- **Consumer refresh:** 2.0 Hz reads stable data
- **Size:** 1–5 bytes (single integer)

### Verdict: **IMPLEMENT (activate existing producer)**

**Rationale:**
- Producer code is **complete and tested** (see tests/scripts/test_youtube_viewer_count_producer.py)
- Zero implementation work; ship existing script as systemd timer
- Uses proven atomic-write pattern
- YouTube API is the ground truth for concurrent viewers (HLS manifest scrape alternative exists but is less reliable)

**Action:** Confirm `youtube-viewer-count-producer.service` + `.timer` systemd units exist and are enabled.

---

## Publisher 5: `grounding-provenance.jsonl`

### Consumer: GroundingProvenanceTickerCairoSource (legibility_sources.py)

**Behavior:** Renders signal provenance (grounding sources for intent). 480×40 emissive surface, row-stacked entries. Expected data:
- Source: `director-intent.jsonl`
- Field: `grounding_provenance` — list of strings (signal names, 6 max)
- Fallback: renders `*  (ungrounded)` with breathing empty state

**Current pattern:** `_read_latest_intent()` tails `~/hapax-state/stream-experiment/director-intent.jsonl`, parses last line JSON, reads `.get("grounding_provenance")`. **This is already working correctly** for the consumer.

### Upstream Availability

**Source:** Director writes `grounding_provenance` array to each INTENT JSONL entry. Example from audit:
```json
{"grounding_provenance": ["fallback.micromove.llm_empty"], ...}
```

**Challenge:** Consumer reads **directly from the INTENT JSONL file**, not from a separate `grounding-provenance.jsonl`. The ward is **not blocked by missing file** — it works as-is via tail-read.

**Verification:** legibility_sources.py lines 62–64, 690–691 show the pattern. Ward is **rendering correctly**.

### Cadence + Size Budget

- Director emits INTENT every 5–30s (on state change)
- Consumer polls every 500 ms via CairoSourceRunner
- No separate file needed; tail-read is sufficient

### Verdict: **RETIRE (no separate publisher needed)**

**Rationale:**
- Ward **already has working upstream data** (director-intent.jsonl)
- Ward's `_read_latest_intent()` correctly tails the INTENT JSONL
- No "missing publisher" — the data is there, consumer works
- Creating a separate file would duplicate data and introduce staleness
- FINDING-V audit mistook "data not in a separate SHM file" for "no producer"

**Action:** Remove from the "missing publishers" list. Ward is operational.

---

## Publisher 6: `chat-state.json` (production)

### Consumer: StreamOverlayCairoSource (stream_overlay.py)

**Behavior:** Renders chat activity status in bottom-right corner as `>>> [CHAT|<status>]` line. Reads:
- `total_messages` (int) — cumulative message count
- `unique_authors` (int) — unique author count
- Renders: `[CHAT|idle]` (0 msgs) → `[CHAT|quiet N]` (1 author) → `[CHAT|M/N]` (M authors, N msgs)

**Current state:** Only writer is `scripts/mock-chat.py` (dev-time mock, manual use). No production producer.

### Upstream Availability

**Source:** Chat stream consumption lives in `agents/chat_monitor/`. The sink (`chat_monitor/sink.py`) receives messages from YouTube IRC or Twitch. The `StructuralSignalQueue` accumulates messages in a rolling window.

**Existing aggregation:** `ChatSignalsAggregator` already computes `unique_authors_60s` and `message_count_60s`. These are written to `/dev/shm/hapax-chat-signals.json` every ~30s.

**Challenge:** `chat-state.json` and `chat-signals.json` have **different schemas**:
- `chat-signals.json`: 8 fields (structured metrics: rate, entropy, novelty, engagement)
- `chat-state.json`: 2 fields (simple counters: total_messages, unique_authors)

The consumer (stream_overlay) expects the simpler schema for legibility.

### Cadence + Size Budget

- **Cadence:** ~30s (same as chat-signals source)
- **Consumer refresh:** 2.0 Hz polls file
- **Size:** ~80 bytes

### Verdict: **IMPLEMENT**

**Rationale:**
- Upstream chat aggregation already runs (ChatSignalsAggregator is active)
- Simple schema transformation: `{total_messages, unique_authors}` ← `{message_count_60s, unique_authors_60s}` from chat-signals.json
- Ward is shipped and functional when data present
- Mock-chat path proves the schema is correct
- Production producer must replace mock-chat.py with a systematic writer

**Action:** Author a side-car service or embed logic in ChatSignalsAggregator to emit simplified schema to `/dev/shm/hapax-compositor/chat-state.json` every ~30s, using atomic tmp+rename.

---

## Summary Table

| File | Consumer Ward | Verdict | Reason | Blocker | Priority |
|------|---------------|---------|--------|---------|----------|
| `recent-impingements.json` | impingement_cascade | **IMPLEMENT** | Upstream exists (`impingements.jsonl`); tail-read proven pattern; zero operator input | None | HIGH |
| `chat-keyword-aggregate.json` | chat_ambient (t5/t6 rates) | **IMPLEMENT** | Output redirect; data in `/dev/shm/hapax-chat-signals.json` already | Path alias confirmation | MEDIUM |
| `chat-tier-aggregates.json` | chat_ambient (t4+ counters) | **IMPLEMENT** | Same source as above; one file, two field groups | Path alias confirmation | MEDIUM |
| `youtube-viewer-count.txt` | whos_here / hothouse | **IMPLEMENT** | Producer script complete + tested; systemd timer required only | Systemd unit activation | LOW |
| `grounding-provenance.jsonl` | grounding_provenance_ticker | **RETIRE** | Ward reads directly from INTENT JSONL; no separate file needed; already working | None — close FINDING-V for this ward | N/A |
| `chat-state.json` | stream_overlay | **IMPLEMENT** | Schema transform of chat-signals; mock-chat.py proves schema; production writer needed | New side-car or aggregator enrichment | MEDIUM |

---

## Atomic Write Pattern Reference

All new publishers **must use tmp+rename** for atomic writes (fail-closed on any error):

```python
from pathlib import Path
import json

def write_state(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(path)  # atomic on POSIX
```

Pattern used in: `audio_ducking.py::set_yt_audio_active` (line 286), `youtube-viewer-count-producer.py::write_viewer_count` (line 46).

---

## Cadence Reference (CairoSourceRunner)

Consumer wards poll SHM files at declared `rate_hz`:
- **2.0 Hz (default):** all legibility + hothouse wards
- **always (null Hz):** Sierpinski, reverie, album (GPU-driven)

Publisher cadence should be <= 3× consumer cadence to avoid perceptual lag. 30s for chat signals is acceptable (2.0 Hz consumer reads stale but coherent state).

---

## Constraints Applied

- **Scientific register:** Neutral language; no pitchy recommendations
- **Axiom compliance:** No operator hand-input as sole data source (all 5 IMPLEMENT verdicts use machine-generated upstream data)
- **Composability:** Each publisher is independent; retirement of grounding-provenance does not affect others
- **Show-don't-tell:** No publisher narrates director actions (all emit structural aggregates only)

---

## Out of Scope

- **Spec:** Publisher architecture (where to run, Pydantic schemas, lifecycle)
- **Plan:** Sequenced rollout, phase dependencies, verification commands
- **FINDING-W:** Architectural pipeline-composition decisions (alpha handles)
- **FINDING-V-corollary:** HARDM perception sources empty (separate cascade chain)

