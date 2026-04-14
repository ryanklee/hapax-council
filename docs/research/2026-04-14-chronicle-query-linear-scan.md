# Chronicle query is a full JSONL linear scan

**Date:** 2026-04-14
**Author:** delta (beta role)
**Scope:** Surfaced during a Logos API latency survey. The
`/api/chronicle` handler has 602 ms mean latency — 40× slower
than comparable handlers on the same API. Asks: why, and
what's the smallest cheap fix?
**Register:** scientific, neutral
**Status:** investigation only — four fix paths, ordered
by invasiveness

## Headline

**Three findings.**

1. **`shared/chronicle.py:112 query()` reads the entire
   `events.jsonl` file from start to end on every call.**
   It parses each line as JSON, applies filters in memory,
   then sorts by timestamp and truncates to `limit`. No
   indexing, no early exit, no caching. The file is currently
   14.7 MB / 49 622 events; each query parses all 49 k lines.
2. **Mean latency for `/api/chronicle` is 602 ms** measured
   over 14 calls in the current Logos API process (8.43 s
   cumulative time / 14 calls). Compared to
   `/api/studio/stream/camera/{role}` at 5 ms/call and
   `/api/health` at 2.4 ms/call, chronicle is **~250×
   slower than peer handlers**.
3. **The write path is unbounded append-only.** `record()`
   appends to the JSONL file with no rotation. A `trim()`
   function exists but is called by the `_chronicle_trim_loop`
   background task in `logos/api/app.py:103` — unclear
   cadence, unclear retention. At the current growth rate
   (file mtime updates every ~10 s), the file adds ~300
   events/min; at 49 622 events it's been accumulating for
   ~2.8 hours of uptime since the last trim or the last
   process restart.

**Net impact.** `/api/chronicle` is the second-slowest
handler on the Logos API by cumulative time (8.43 s total),
only behind `/api/predictions/metrics` (11.14 s). It's
called by operator UI paths (observability dashboards,
chronicle narration) where perceived latency matters —
600 ms is "sluggish" territory. The asymptotics get worse:
**every doubling of the event count doubles the query
time.** At a week of operation, events.jsonl would be
~200k events and query latency ~2.5 s per call.

## 1. The offending code

```python
# shared/chronicle.py:112-166 (abbreviated)
def query(
    *,
    since: float,
    until: float | None = None,
    source: str | None = None,
    event_type: str | None = None,
    trace_id: str | None = None,
    limit: int = 500,
    path: Path = CHRONICLE_FILE,
) -> list[ChronicleEvent]:
    if not path.exists():
        return []

    effective_until = until if until is not None else time.time()
    results: list[ChronicleEvent] = []

    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:                                  # ← O(N) scan
            raw = raw.strip()
            if not raw:
                continue
            try:
                ev = ChronicleEvent.from_json(raw)      # ← O(N) JSON parse
            except (json.JSONDecodeError, KeyError):
                continue
            if ev.ts < since or ev.ts > effective_until:
                continue                                # ← filter AFTER parse
            if source is not None and ev.source != source:
                continue
            if event_type is not None and ev.event_type != event_type:
                continue
            if trace_id is not None and ev.trace_id != trace_id:
                continue
            results.append(ev)

    results.sort(key=lambda e: e.ts, reverse=True)      # ← O(K log K) sort
    return results[:limit]                              # ← then truncate
```

Observations:

- **Parse-then-filter**: every line is JSON-parsed, then
  tested against `since`. Lines that fail the time filter
  still pay the parse cost. For a typical query (last
  1 hour), ~97 % of lines in a 2.8-hour file will be parsed
  and discarded.
- **No early exit on `since`**: events.jsonl is append-only,
  so timestamps are monotonically non-decreasing. The first
  line where `ev.ts >= since` marks the start of relevant
  data; everything before can be skipped. Without early
  exit, the scanner reads the whole file.
- **Sort-after-collect**: results are collected forward,
  then sorted reverse at the end. If the file is already
  in ascending ts order (it is, because writes are
  append-only), `reversed(results)` is O(K) instead of
  O(K log K).
- **Single file handle, line-buffered read**: fine at
  14 MB. Becomes a memory issue at multi-GB files, not
  a problem today.

## 2. Per-call cost breakdown

At 49 622 events / 14 MB and 602 ms mean:

| phase | estimated share | notes |
|---|---|---|
| `fh.readline()` × N | ~5 % (30 ms) | kernel read from `/dev/shm` tmpfs is ~GB/s, not the bottleneck |
| `ChronicleEvent.from_json` × N | **~85 %** (510 ms) | stdlib `json.loads` + dataclass construction |
| filter predicate × N | ~2 % (12 ms) | integer / string compares, cheap |
| `results.sort` | ~5 % (30 ms) | K is the filtered subset; typically < 500 |
| rest | ~3 % (20 ms) | list appends, context switches, overhead |

**Parsing is the dominant cost.** Any fix that reduces
the number of lines parsed is a proportional speedup.

## 3. Four fix paths, ordered by invasiveness

### 3.1 Option A — reverse scan + early exit on `since`

Smallest change, largest win for the common case:

```python
from collections import deque

def query(...):
    if not path.exists():
        return []
    effective_until = until if until is not None else time.time()

    # Read lines in reverse (newest first). For a file on tmpfs,
    # reading the whole file into memory and reversing is simpler
    # than seeking. 14 MB is cheap.
    lines = path.read_text(encoding="utf-8").splitlines()

    results: list[ChronicleEvent] = []
    for raw in reversed(lines):
        if not raw:
            continue
        try:
            ev = ChronicleEvent.from_json(raw)
        except (json.JSONDecodeError, KeyError):
            continue
        if ev.ts > effective_until:
            continue
        if ev.ts < since:
            break                              # ← early exit
        if source is not None and ev.source != source:
            continue
        if event_type is not None and ev.event_type != event_type:
            continue
        if trace_id is not None and ev.trace_id != trace_id:
            continue
        results.append(ev)
        if len(results) >= limit:
            break                              # ← second early exit
    return results
```

**Why this is fast:**

- For a 1-hour query on a 2.8-hour file, only ~36 % of
  lines are parsed (the ones newer than `since`). Median
  latency drops to ~215 ms.
- For a 15-minute query, only ~9 % of lines are parsed.
  Median ~55 ms.
- The `len(results) >= limit` early exit caps work at
  `limit` parse operations in the best case — for a
  trace_id lookup with limit=500, this is negligible.
- No sort at the end because the reverse-walk naturally
  produces newest-first order.

**Risk:** `path.read_text().splitlines()` loads the whole
file into memory. At 14 MB that's fine. At 1 GB it's
not — but trim() should keep it from getting that big.

**Effort:** ~15 LoC diff. Preserves all existing filter
semantics. One new test (verify empty result when `since
> newest ts`).

### 3.2 Option B — orjson swap

`orjson.loads` is 2-3× faster than stdlib `json.loads`.
Drop-in replacement:

```python
import orjson as _orjson

def _from_json_fast(raw: str) -> ChronicleEvent:
    d = _orjson.loads(raw)
    return ChronicleEvent(**d)
```

Swap `ChronicleEvent.from_json(raw)` for `_from_json_fast(raw)`.
Cuts the 85 % parse share to ~35 % → total query latency
~310 ms.

**Risk:** orjson requires `bytes` input, not `str` — but
tmpfs reads can come back as bytes directly (`path.read_bytes()`
then split on `b"\n"`). Minor refactor.

**Effort:** ~5 LoC if orjson is already a council dep
(it is, widely used for the logos API).

### 3.3 Option C — reverse scan + orjson (A + B combined)

Both optimizations together. 1-hour query on current file:

- 36 % of lines parsed (from A)
- 2-3× faster per parse (from B)

Net: ~80 ms/query. **7.5× faster than the baseline.**

### 3.4 Option D — sqlite migration

Replace `events.jsonl` with `events.db` (sqlite). Index on
`(ts DESC, source, event_type, trace_id)`.

```python
cur.execute("""
    SELECT * FROM events
    WHERE ts >= ? AND ts <= ?
    AND (? IS NULL OR source = ?)
    AND (? IS NULL OR event_type = ?)
    AND (? IS NULL OR trace_id = ?)
    ORDER BY ts DESC
    LIMIT ?
""", (since, until, source, source, event_type, event_type,
      trace_id, trace_id, limit))
```

O(log N) seek + O(K) read, regardless of total file size.

**Risks:**

- Concurrent write safety: multiple processes currently
  append to `events.jsonl` via line-atomic writes
  (`fh.write(line + "\n")`). sqlite write semantics differ
  (transactions, file locking).
- Record path needs updating too — bigger change surface.
- Migration script for existing jsonl → db.
- Write latency increases slightly (sqlite journal sync).

**Upside:**

- Query latency stops scaling with file size.
- Richer queries become possible (joins, aggregations).
- Clean separation between hot read path and archive.

**Effort:** multi-file refactor, ~200 LoC + migration
script + tests. Plus updating all `record()` callers.

## 4. Comparison

| option | effort | query latency at current size | query latency at 10× size | new risks |
|---|---|---|---|---|
| baseline | — | 602 ms | 6 020 ms | — |
| A (reverse + early exit) | 15 LoC | 215 ms (1 h window) | 215 ms (constant) | full-file read |
| B (orjson) | 5 LoC | 310 ms | 3 100 ms | orjson API |
| C (A + B) | 20 LoC | **80 ms** | **80 ms** | both |
| D (sqlite) | ~200 LoC | ~10 ms | ~10 ms | write path, migration |

**Delta's recommendation:** ship **option C** now. It's
a 20-LoC diff that gives a 7.5× speedup on the current
workload AND a 75× speedup at projected scale. sqlite
(D) is a legitimate longer-term target but not warranted
by current numbers.

## 5. Secondary finding — trim loop cadence is unclear

`logos/api/app.py:103` has an `_chronicle_trim_loop()` —
the periodic task that calls `trim()` to prune old events
based on `retention_s`. Didn't read the full loop in this
drop.

**Worth verifying:**

- How often does trim run? If hourly, the file can reach
  10× its current size before being pruned.
- What's `retention_s`? A reasonable default for an
  operator-facing chronicle is 7 days.
- Does trim hold a lock that blocks concurrent record()
  writes? At current size trim takes ~200 ms (full file
  rewrite); at 10× it's ~2 s.

All three questions are separate from the query-speed fix
but relevant to the overall health of the chronicle
subsystem. Flag for alpha.

## 6. Secondary finding — `/api/predictions/metrics` at 428 ms

Same Logos API probe surfaced `/api/predictions/metrics`
at 428 ms mean latency (26 calls, 11.14 s total). This
handler is the Grafana reverie-predictions dashboard
scrape target (council CLAUDE.md §). At Grafana's typical
30 s scrape interval, the scrape cost is:

- 428 ms × 120 scrapes/hour = 51.4 s/hour of Logos API
  time serving one dashboard

Not drop-worthy on its own but worth flagging. Likely
cause: the predictions endpoint queries several data
sources (Prometheus, SQLite, Qdrant) serially. Parallelizing
them with `asyncio.gather` would cut the wall clock to
max(sources) instead of sum(sources).

**Flag for a follow-up audit** — not in scope for this
drop.

## 7. Follow-ups

1. **Ship option C** — 20-LoC diff in `shared/chronicle.py`
   + one test. Immediate 7.5× speedup. Alpha review for
   orjson edge cases (empty lines, BOM, encoding).
2. **Verify trim loop** — read `logos/api/app.py:103`
   to confirm cadence and retention. Adjust if needed.
3. **Parallelize `/api/predictions/metrics`** — separate
   follow-up, same class of speedup.
4. **Optional: sqlite migration (option D)** — queue as
   a standalone epic when/if chronicle data volume
   justifies it. Current trajectory doesn't.

## 8. References

- `shared/chronicle.py:112-166` — the `query()` function
- `shared/chronicle.py:17-18` — `CHRONICLE_DIR = /dev/shm/hapax-chronicle`
- `logos/api/routes/chronicle.py:85-106` — the `/api/chronicle`
  FastAPI handler
- `logos/api/app.py:103` — `_chronicle_trim_loop()` (not
  audited in this drop)
- Live probe: `curl http://127.0.0.1:8051/metrics | grep
  http_request_duration_seconds_sum` at 2026-04-14T16:30 UTC
- File state: `/dev/shm/hapax-chronicle/events.jsonl`
  — 14 765 425 bytes, 49 622 lines, mtime updating every
  ~10 s
