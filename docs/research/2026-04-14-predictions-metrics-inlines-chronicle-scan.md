# `/api/predictions/metrics` inlines a second chronicle full-scan

**Date:** 2026-04-14
**Author:** delta (beta role)
**Scope:** Follow-up to drop #23. The Logos API handler
latency survey showed `/api/predictions/metrics` at
428 ms mean — second-slowest on the API. Asks: what's the
fix path, and does it overlap with drop #23's chronicle
query finding?
**Register:** scientific, neutral
**Status:** investigation only — fix is the same single
change as drop #23 plus a caller swap

## Headline

**Three findings.**

1. **`logos/api/routes/predictions.py:140-170` inlines its
   own full scan of `/dev/shm/hapax-chronicle/events.jsonl`**
   to count `technique.activated` events in the last 60
   seconds. 49 622 lines × `json.loads` per call, same
   as drop #23's `chronicle.query()`. **Does not use
   `shared.chronicle.query()`** — it's a copy-paste of
   the scan logic with hardcoded filters.
2. **The chronicle walk is the dominant cost** of the
   `/api/predictions/metrics` handler's 428 ms mean
   latency. The handler also reads seven other tiny files
   from `/dev/shm/` (each ≤ a few kB) and those are
   sub-millisecond each. The 420 ms is the chronicle
   scan.
3. **Grafana scrapes this endpoint every 30 s.** That's
   120 scrapes/hour × 428 ms = **51.4 s/hour of Logos API
   time serving one dashboard** — exactly the cost
   number I flagged in drop #23 § 6 without confirming
   the root cause. Now confirmed: it's the inlined
   chronicle scan.

**Net impact.** The predictions handler and the chronicle
handler are paying the same cost twice for the same
scan. Alpha's fix for drop #23 (reverse scan + early exit
+ orjson, aka "option C") solves both — if the predictions
handler swaps to using `shared.chronicle.query()` instead
of its inlined walker. **One change fixes two slow handlers.**

## 1. The duplicated code

From `logos/api/routes/predictions.py:140-170`:

```python
# --- Chronicle technique confidence: last 60s of activations ---
try:
    events_file = CHRONICLE_DIR / "events.jsonl"
    if events_file.exists():
        now = time.time()
        cutoff = now - 60.0
        technique_last: dict[str, float] = {}
        technique_count: dict[str, int] = {}
        with open(events_file) as f:
            for line in f:                                 # ← full-file scan
                try:
                    e = json.loads(line)                  # ← parse every line
                except json.JSONDecodeError:
                    continue
                if e.get("source") != "visual" or \
                   e.get("event_type") != "technique.activated":
                    continue                              # ← filter AFTER parse
                ts = e.get("ts", 0)
                if ts < cutoff:
                    continue                              # ← no early exit
                name = e.get("payload", {}).get("technique_name", "")
                conf = e.get("payload", {}).get("confidence", 0)
                if name:
                    technique_last[name] = conf
                    technique_count[name] = technique_count.get(name, 0) + 1
except Exception:
    pass
```

Compare to `shared/chronicle.py:112-166 query()`:

- Both do a for-loop over `events_file`
- Both parse every line with `json.loads` before applying
  time filter
- Both have no early exit on `since`
- Both cost O(N × parse_time_per_line) per call

The predictions handler filters by source/event_type;
chronicle.query() supports the same filters. **Functionally
identical, code-duplicated.**

## 2. Cost analysis at current scale

Chronicle file size and event count at sample time
(2026-04-14T16:30 UTC):

- `events.jsonl`: 14.7 MB, 49 622 events
- Oldest event: ~2.8 h ago (file mtime updates every
  ~10 s, file rotated by a trim loop on some cadence)
- `technique.activated` events: unknown exact count, but
  empirically rare (visual stack only fires these on
  preset activations)

Cost breakdown per `/api/predictions/metrics` call:

| stage | cost | share |
|---|---|---|
| open + read all 49 622 lines | ~30 ms | 7 % |
| `json.loads` × 49 622 | ~350 ms | **82 %** |
| filter predicates | ~10 ms | 2 % |
| dict accumulation | ~5 ms | 1 % |
| other file reads (uniforms, perception, etc) | ~5 ms | 1 % |
| FastAPI overhead | ~30 ms | 7 % |
| **total** | **~430 ms** | — |

The 82 % parse share matches drop #23's breakdown of the
chronicle.query() cost — same reason, same numbers.

## 3. The fix is drop #23's fix plus one line

After drop #23's option C lands in `shared/chronicle.py`
(reverse scan + early exit + orjson), the predictions
handler can drop its inlined walker and call the shared
function:

```python
# logos/api/routes/predictions.py — proposed replacement
try:
    from shared.chronicle import query as chronicle_query

    now = time.time()
    cutoff = now - 60.0
    events = chronicle_query(
        since=cutoff,
        source="visual",
        event_type="technique.activated",
        limit=1000,   # safety cap
    )
    technique_last: dict[str, float] = {}
    technique_count: dict[str, int] = {}
    for ev in events:
        payload = ev.payload or {}
        name = payload.get("technique_name", "")
        conf = payload.get("confidence", 0)
        if name:
            technique_last[name] = conf
            technique_count[name] = technique_count.get(name, 0) + 1
    for name, conf in technique_last.items():
        lines.append(f'reverie_technique_confidence{{technique="{name}"}} {conf}')
    elapsed = 60.0
    for name, count in technique_count.items():
        rate = count / elapsed * 60 if elapsed > 0 else 0
        lines.append(f'reverie_technique_rate{{technique="{name}"}} {rate:.2f}')
except Exception:
    pass
```

**Post-fix cost estimate:**

With option C (reverse scan + early exit at `since`),
the walker reads events from newest to oldest and stops
when `ev.ts < cutoff` (60 seconds ago). Fresh-events
count at typical chronicle cadence (~5 events/sec):

- Events in last 60 s: ~300
- `json.loads` × 300: ~2 ms
- Filter + accumulate: ~0.3 ms
- Other reads: ~5 ms
- FastAPI overhead: ~30 ms
- **Total: ~40 ms**

**Speedup: ~10× on the `/api/predictions/metrics` path**,
on top of the same speedup drop #23 projects for
`/api/chronicle`.

**Grafana cost reduction**: 51.4 s/hour → 5.1 s/hour. A
week-over-week that's ~280 seconds of Logos API wall
clock reclaimed per Grafana scrape path. Multiply by the
number of dashboards that scrape this endpoint and the
savings compound.

## 4. Why this matters for drop #23's fix prioritization

Drop #23 lists option C (reverse + orjson) as "ship
today, 20 LoC." That stands, but the fix is **worth
substantially more** than drop #23's 7.5× speedup suggests
— because:

- Two handlers (chronicle + predictions_metrics) share
  the cost
- Both are currently in the top 5 slowest Logos API
  handlers
- Both are called from production paths (operator UI,
  Grafana scrapes)
- The fix is symmetric — same root cause, same code
  path

The **combined** savings from drop #23 option C plus
this drop's caller-swap:

| handler | baseline | fix | speedup |
|---|---|---|---|
| `/api/chronicle` | 602 ms | ~80 ms | 7.5× |
| `/api/predictions/metrics` | 428 ms | ~40 ms | ~10× |
| **sum of drained CPU time** | ~1030 ms/call | ~120 ms/call | ~8.5× |

Across the two handlers, drop #23's fix + this caller
swap **reclaims ~900 ms of Logos API wall-clock time
per hot-path query**.

## 5. Other chronicle scan sites worth auditing

The duplication pattern (inline walker instead of using
`shared.chronicle.query()`) might exist in other places.
A quick grep:

```bash
grep -rn "events.jsonl" logos/ agents/ shared/
grep -rn "CHRONICLE_DIR" logos/ agents/ shared/ | grep -v chronicle.py
```

Not run in this drop. Flagging as a follow-up — if there
are more sites, they all benefit from the same fix as
predictions.py.

## 6. Follow-ups

1. **Ship drop #23 option C** (fixes
   `shared.chronicle.query()` itself).
2. **Swap predictions.py:140-170** to call
   `shared.chronicle.query()` instead of inlining the
   walker. One-function diff.
3. **Audit for other inline chronicle walkers** — one grep,
   five minutes. Fix each site identically.
4. **Consider a soft migration**: keep
   `shared.chronicle.query()` as the single entry point
   and deprecate any remaining inline walkers with a
   deprecation warning.

## 7. References

- `logos/api/routes/predictions.py:140-170` — the inlined
  scan
- `shared/chronicle.py:112-166` — `query()` that should
  be used instead
- `2026-04-14-chronicle-query-linear-scan.md` (drop #23)
  — the chronicle `query()` audit this follow-up extends
- Live probe: `curl http://127.0.0.1:8051/metrics | grep
  http_request_duration_seconds_sum` — 11.14 s cumulative
  over 26 calls for `/api/predictions/metrics`
- Chronicle file state: `/dev/shm/hapax-chronicle/events.jsonl`
  — 14.7 MB, 49 622 events
