# RIFTS harness error recovery verification

**Date:** 2026-04-15
**Author:** beta (queue #231, identity verified via `hapax-whoami`)
**Scope:** static audit of the RIFTS benchmark harness for error handling, checkpoint persistence, and resume behavior. Non-disruptive — does not touch the running queue #210 process.
**Branch:** `beta-phase-4-bootstrap`

---

## 0. Summary

**Verdict: graceful per-prompt error recovery + NO checkpoint/resume mechanism.** The harness (`scripts/run_rifts_benchmark.py`, 409 LOC) correctly records per-prompt errors and continues to the next prompt — but a **mid-run interruption (SIGINT, crash, OOM, disk-full)** loses all progress on restart because the output path is opened with `"w"` mode, which truncates the existing file to empty on re-invocation.

**Findings:**

1. ✅ **Per-prompt error handling is correct.** `_call_litellm()` wraps the HTTP POST in `try/except httpx.HTTPError`; non-200, JSON decode failure, and schema failure each return an error string. `_real_run()` records the error in the JSONL row and increments `count_error`, then moves to the next prompt. **No uncaught exceptions in the per-prompt path.**
2. ✅ **Write-after-each-prompt with flush.** Every prompt result hits `out_f.write() + out_f.flush()` immediately (lines 380-381). Python-level buffer is drained per prompt — interrupts after flush preserve the written line.
3. ⚠️ **No `os.fsync()`.** `flush()` only drains the Python buffer to the OS buffer; a kernel panic or power loss could lose the last few lines. Non-critical for this run (controlled workstation, no power events expected).
4. ⚠️ **No retry on transient errors.** 5xx / timeout / connect errors each record one error entry and move on. The 19:50Z progress snapshot showed 5 errors at 0.98% error rate; the 20:12Z resource check showed 8 errors at 1.10%; extrapolated to full 1740 prompts the final dataset will contain ~20 error rows with empty `response`/`tokens_in`/`tokens_out` fields.
5. 🔴 **CRITICAL: No `--resume` flag, no checkpoint file, output path opens with `"w"` (truncate).** A mid-run SIGINT preserves all flushed lines on disk, but re-running with the same `--output` will **destroy the partial output**. The operator MUST rename the existing file before restart, or restart will silently lose ~41.8% of progress (the current in-flight state).
6. ⚠️ **Spec file-name drift.** Queue #231 spec says `scripts/benchmark_rifts_harness.py`; actual file is `scripts/run_rifts_benchmark.py`. Low-severity, noted for queue-index cleanup.

**Severity: MEDIUM for the output-file-truncation finding.** The current in-flight run is healthy (~63% at 20:40Z) so there's no immediate risk, but any operator who assumes "restart will resume" would be wrong. Recommended operator-facing safety note below + proposed follow-ups.

## 1. Harness file identity

```
$ wc -l scripts/run_rifts_benchmark.py
409 scripts/run_rifts_benchmark.py

$ head -2 scripts/run_rifts_benchmark.py
#!/usr/bin/env python3
"""RIFTS benchmark harness — runs microsoft/rifts prompts against a LiteLLM model route.
```

**Queue #231 spec drift:** the YAML says `scripts/benchmark_rifts_harness.py` but no such file exists. The canonical path is `scripts/run_rifts_benchmark.py` (committed `a52dafc87` per queue #210 context, shipped pre-run). Non-urgent — flag for queue-index cleanup.

## 2. Error handling audit (per-prompt path)

### 2.1 HTTP call wrapping — `_call_litellm()` lines 255-304

```python
try:
    response = client.post(
        f"{url}/v1/chat/completions",
        json=body,
        headers=headers,
        timeout=DEFAULT_TIMEOUT_S,
    )
except httpx.HTTPError as exc:
    latency_ms = (time.perf_counter() - t_start) * 1000.0
    return "", None, None, latency_ms, f"httpx error: {exc}"
latency_ms = (time.perf_counter() - t_start) * 1000.0

if response.status_code != 200:
    return "", None, None, latency_ms, f"HTTP {response.status_code}: {response.text[:200]}"

try:
    data = response.json()
except ValueError as exc:
    return "", None, None, latency_ms, f"json decode: {exc}"

try:
    content = data["choices"][0]["message"]["content"] or ""
except (KeyError, IndexError, TypeError) as exc:
    return "", None, None, latency_ms, f"response schema: {exc}"
```

Every failure mode in the HTTP call surface returns a tuple with an error message as the fifth element. The caller at line 359 unpacks exactly this tuple and records it.

**Error envelope coverage:**

| Failure mode | Caught? | Recorded as |
|---|---|---|
| DNS / connect error | ✅ `httpx.HTTPError` | `"httpx error: {exc}"` |
| Read timeout (> 60s) | ✅ `httpx.HTTPError` | `"httpx error: timed out"` |
| Non-200 status (5xx) | ✅ explicit check | `"HTTP {code}: {text[:200]}"` |
| JSON decode failure | ✅ `ValueError` | `"json decode: {exc}"` |
| Missing `choices[0]` | ✅ `(KeyError, IndexError, TypeError)` | `"response schema: {exc}"` |
| `content` is None or empty | ✅ explicit `or ""` | returns empty string + tokens_in/tokens_out |

**Uncaught failure modes:**

- `httpx.Client` construction failure (at `with httpx.Client() as client` on line 349) — would bubble up and crash `_real_run()`. Unlikely, but not handled.
- `out_f.write()` `OSError` (disk full) — uncaught, harness crashes. Unhandled.
- Dataset iteration `StopIteration` (should not occur — generators handle naturally)
- Python-level `MemoryError` — uncaught, process dies

### 2.2 Retry behavior

**No retries.** Each prompt gets exactly one `_call_litellm()` invocation. The harness does not:

- Retry with backoff on 5xx
- Retry on httpx timeout
- Distinguish transient from permanent errors
- Record retry attempts in the output schema

**Observed in current run:** the 8 errors at 20:12Z were:
- 3 × HTTP 503 `litellm.ServiceUnavailableError`
- 5 × httpx timeouts

Each of these is a candidate for retry (both are transient classes). If the harness had 3× retry with exponential backoff, the likely error count would drop below the 20-row end-state estimate. Non-urgent — the post-run analysis step already handles error rows as "missing data" rather than "failed prompts", so retries would improve coverage but aren't required for the findings template.

### 2.3 Error row schema

```python
result = RunResult(
    prompt_id=prompt_id,
    ambiguous=ambiguous,
    prompt_text=prompt_text,
    model=args.model,
    response=response,           # "" on error
    latency_ms=latency_ms,       # real latency even for errors
    tokens_in=tokens_in,         # None on error
    tokens_out=tokens_out,       # None on error
    error=error,                 # str or None
    timestamp=datetime.now(UTC).isoformat(),
)
out_f.write(json.dumps(result.__dict__) + "\n")
out_f.flush()
```

**Error rows preserve:**

- `prompt_id` (for post-run attribution)
- `ambiguous` flag (so the error can be counted against the right split)
- `prompt_text` (so a future retry pass has the prompt without re-reading the parquet)
- `latency_ms` (for "how long did the error take" analysis — useful for timeout vs immediate-5xx classification)
- `error` string (the specific failure mode)

**Missing fields:** no retry counter, no attempt timestamp separate from the write timestamp, no HTTP response headers. Sufficient for the current analysis scope.

## 3. Write + persistence path audit

### 3.1 Output file open mode

```python
# scripts/run_rifts_benchmark.py:349
with httpx.Client() as client, output_path.open("w") as out_f:
    for raw in _load_dataset(args.dataset_path):
```

**Critical line:** `output_path.open("w")` opens the file in **write mode, truncating any existing content**. This is the key finding of this audit.

**Implications:**

- **First run:** works as intended — fresh output file receives 1740 lines (minus errors) over ~2h 40m.
- **Second run with same `--output`:** **silently destroys the previous output**. No warning, no check, no "append?" prompt. The operator sees a fresh empty file and the harness starts from prompt 1.
- **Mid-run SIGINT + restart with same `--output`:** same as second run — the 1100+ flushed lines are truncated to zero and the harness restarts from prompt 1.

### 3.2 Per-prompt flush

```python
# lines 380-381
out_f.write(json.dumps(result.__dict__) + "\n")
out_f.flush()
```

**Good:** every prompt triggers a flush. Python's internal buffer (typically 8 KB for text mode) is drained to the OS. A subsequent `cat` or `tail` will see the line.

**Missing:** no `os.fsync(out_f.fileno())`. Python's `flush()` drains to the OS write cache; it does NOT force the kernel to write dirty pages to disk. A kernel panic or power loss within ~5 seconds of a flush can still lose the line.

**Impact assessment:** the workstation is a controlled environment with UPS + ECC memory + filesystem journaling (ext4 under `/dev/nvme0n1p2`). The probability of a mid-run kernel panic is low, and the blast radius is bounded to the last ~5 seconds of output (~2-3 prompts at 11 prompts/min). **Not urgent.** A future hardening pass could add `os.fsync()` every N prompts (e.g., every 50) to bound the worst-case loss without tanking throughput.

### 3.3 Context manager behavior on interrupt

```python
with httpx.Client() as client, output_path.open("w") as out_f:
    for raw in _load_dataset(args.dataset_path):
        ...
```

On SIGINT (Ctrl+C), Python raises `KeyboardInterrupt` inside the loop body. The `with` statement's `__exit__` runs:

1. `out_f.__exit__()` calls `out_f.close()` — which first flushes the Python buffer, then closes the file descriptor. The OS cache already contains the flushed lines; close does not additionally fsync.
2. `httpx.Client.__exit__()` tears down the HTTP session cleanly.
3. The traceback prints to stderr; Python exits non-zero.

**Result:** the 1097 (or however many) already-flushed lines are preserved on disk. The in-flight prompt (the one that was mid-HTTP-call when SIGINT hit) is lost — partial HTTP response body is discarded.

### 3.4 Disk-full failure

`out_f.write()` raises `OSError(ENOSPC)` on a full disk. This is uncaught by the harness:

```python
# line 380 — no try/except around write
out_f.write(json.dumps(result.__dict__) + "\n")
```

The exception propagates out of `_real_run()` → `main()` → `sys.exit(main())` → the harness dies with a traceback. The partial output file up to the failure point is preserved (the flushed lines).

**Impact on current run:** queue #229 verified 690 GB free on `/home`; the harness output file is currently 1.4 MB and will max out at ~3.5 MB for the full 1740 prompts. **Zero risk of disk-full in the current run.**

## 4. Resume / checkpoint audit

### 4.1 No checkpoint file

The harness has no separate state file. There is no:

- `.checkpoint.json` tracking current position
- `.progress.txt` with last processed prompt ID
- Atomic rename pattern for partial output

The output JSONL **is** the de-facto checkpoint — every flushed line represents one processed prompt — but the harness cannot read it back because the truncating `"w"` open mode destroys it before iteration begins.

### 4.2 No `--resume` flag

```python
# _parse_args() lines 98-145 — no --resume flag
```

No CLI arg for resume. No environment variable. The harness has no mechanism to skip already-processed prompts.

### 4.3 Deterministic iteration order

```python
# _load_dataset() lines 196-200
for parquet_path in sorted(parquet_candidates):  # ← alphabetical
    df = pd.read_parquet(parquet_path)
    for _, row in df.iterrows():                  # ← natural row order
        yield row.to_dict()
```

**Deterministic across runs.** `sorted()` on parquet filenames + `iterrows()` preserves row order means a second run would see the same prompts in the same order. This is the property that makes a future `--resume` implementable: "skip the first N rows" or "skip rows whose `prompt_id` is already in the existing JSONL" would work correctly.

### 4.4 Restart cost estimate

If the current run is interrupted mid-way and restarted from scratch:

- ~63% progress lost → ~1100 prompts wasted
- ~1100 prompts × 5.55 s/prompt average = ~1h 42m of compute wasted
- Plus the ~2h 40m remaining original budget → total ~4h 22m to completion on restart
- Queue #229 error rate holds at ~1.1% → ~12 new error rows in the second pass (transient errors are not correlated across retries)

**Operator cost is significant** — the unblock mechanism is simply "don't interrupt the run", which is fine for the current healthy run but brittle against any unforeseen system event.

## 5. Failure-mode simulation table

Simulated cold-read of what happens under each failure signature:

| Failure | During-run behavior | Disk state | Restart behavior |
|---|---|---|---|
| Single prompt 5xx (503) | Records error row, continues | JSONL grows by 1 error line | N/A — no restart needed |
| Single httpx timeout (60s) | Records error row, continues | JSONL grows by 1 error line | N/A |
| TabbyAPI process restart | Burst of 5-10 errors during reload window, then recovers | ~5-10 error rows | N/A |
| SIGINT (operator Ctrl+C) | KeyboardInterrupt, context managers close | Partial JSONL preserved | **If restarted with same --output: JSONL TRUNCATED, progress lost** |
| OOM killer | Process killed SIGKILL | Partial JSONL preserved | Same as SIGINT |
| Disk full | OSError uncaught, harness crashes | Partial JSONL preserved up to failure | Same as SIGINT |
| Kernel panic / power loss | No graceful close | Last ~5s of flushed lines may be lost (no fsync) | Same as SIGINT |
| `scripts/run_rifts_benchmark.py` edited mid-run | Python doesn't re-read source; harness continues | Unaffected | N/A |
| Parquet file corruption | Dataset iteration raises mid-loop | Partial JSONL preserved | Same as SIGINT |

**The dominant failure-mode recovery pattern:** all terminal failures preserve the partial JSONL on disk, but the restart behavior truncates it. The operator's only safe restart workflow is:

1. `mv results-local-fast-qwen-20260415.jsonl results-local-fast-qwen-20260415.PARTIAL.jsonl`
2. Re-run the harness with a new `--output` path
3. Post-run, manually concatenate the two JSONL files (or write a one-shot Python script to merge by prompt_id deduplication)

## 6. Operator safety note (immediate-actionable)

**If the current queue #210 run needs to be restarted for any reason (not currently expected — run is healthy, ETA ~21:44Z):**

```bash
# DO NOT re-run without renaming the existing output first!
# The harness opens --output with "w" mode, truncating existing content.

# Safe restart procedure:
cd ~/projects/hapax-council--beta
mv research/benchmarks/rifts/results-local-fast-qwen-20260415.jsonl \
   research/benchmarks/rifts/results-local-fast-qwen-20260415.PARTIAL.jsonl

# Re-run with a new output path
LITELLM_MASTER_KEY=sk-... uv run --with pandas --with pyarrow python \
    scripts/run_rifts_benchmark.py \
    --model local-fast \
    --dataset-path research/benchmarks/rifts/microsoft_rifts \
    --output research/benchmarks/rifts/results-local-fast-qwen-20260415.RESUMED.jsonl

# Post-run: merge the two files, deduplicate by prompt_id
python3 -c "
import json
seen = set()
with open('research/benchmarks/rifts/results-local-fast-qwen-20260415.jsonl', 'w') as out:
    for path in ['.../results-local-fast-qwen-20260415.PARTIAL.jsonl', '.../results-local-fast-qwen-20260415.RESUMED.jsonl']:
        with open(path) as f:
            for line in f:
                d = json.loads(line)
                if d['prompt_id'] not in seen and not d.get('error'):
                    out.write(line)
                    seen.add(d['prompt_id'])
print(f'merged {len(seen)} unique prompts')
"
```

**This dedupe-merge does NOT give a resumed run** — the RESUMED.jsonl will start from prompt 1, so it will re-process all 1100+ already-done prompts. True resume requires either (a) renaming + running a full second pass + merging (total cost: full re-run), or (b) implementing `--resume` in the harness.

## 7. Recommended follow-ups

### 7.1 #235 — Add `--resume` flag to `run_rifts_benchmark.py`

```yaml
id: "235"
title: "Add --resume flag to RIFTS harness"
assigned_to: beta
status: offered
depends_on: []
priority: low
description: |
  Queue #231 audit found the RIFTS harness has no checkpoint/resume
  mechanism — restart with same --output truncates progress. Since
  iteration order is deterministic (sorted parquet + iterrows), resume
  can be implemented by:
  
  1. Add --resume flag
  2. When --resume is set AND --output exists:
     - Open output in "a" (append) mode instead of "w"
     - Read existing JSONL, build set of seen prompt_ids (and optionally
       track error_ids separately for retry)
     - Skip rows in _load_dataset() whose prompt_id is already in seen
     - Continue from the first unseen row
  3. Without --resume, current "w" truncate behavior preserved
     (explicit opt-in for safety)
  4. Add --retry-errors flag as a companion: re-run only rows whose
     error field is non-null
  
  Estimated diff: ~40 LOC in _real_run() + 2 new CLI args + 1 small
  helper function to read the existing JSONL.
size_estimate: "~45 min implementation + test + commit"
```

### 7.2 #236 — Add per-prompt retry with exponential backoff

```yaml
id: "236"
title: "RIFTS harness per-prompt retry with backoff"
assigned_to: beta
status: offered
depends_on: []
priority: low
description: |
  Queue #231 audit found each prompt gets exactly one _call_litellm()
  invocation. Transient errors (503, httpx timeout) are recorded and
  skipped rather than retried. The current #210 run has ~1.1% error
  rate; a 3x retry with 1s/2s/4s backoff would likely drop this to
  <0.3% without impacting throughput.
  
  Actions:
  1. Add --retries flag (default 0 = current behavior)
  2. Wrap _call_litellm() call site in a retry loop
  3. Classify errors as retryable (HTTP 5xx, httpx timeout, connect)
     vs permanent (HTTP 4xx, schema errors)
  4. Log each retry attempt; final error row records total attempt
     count in a new `retry_count` field
size_estimate: "~30 min"
```

### 7.3 #237 — fsync hardening

```yaml
id: "237"
title: "RIFTS harness fsync every N prompts"
assigned_to: beta
status: offered
depends_on: []
priority: low
description: |
  Queue #231 audit found out_f.flush() drains to OS cache but does NOT
  fsync to disk. A kernel panic or power loss within ~5s of a flush can
  lose the last ~2-3 prompts worth of output. Bound the worst case by
  adding os.fsync(out_f.fileno()) every 50 prompts.
  
  Trivial patch; negligible throughput impact (one fsync per ~4 min of
  prompts). Non-urgent for the current controlled workstation but good
  hardening for any future unattended runs.
size_estimate: "~5 min"
```

### 7.4 #238 — Queue-spec path cleanup

```yaml
id: "238"
title: "Fix queue #231 spec path drift"
assigned_to: delta  # meta
status: offered
depends_on: []
priority: low
description: |
  Queue #231 spec references scripts/benchmark_rifts_harness.py but the
  canonical path is scripts/run_rifts_benchmark.py. Update the queue
  YAML file reference or add an alias note. Low-severity cleanup.
size_estimate: "~1 min"
```

## 8. Non-drift observations

- **The harness is well-structured.** Single file, no globals beyond constants, clean separation between dataset loading, HTTP call, and orchestration. ~400 LOC including the docstring and argparse block. Easy target for additive improvements (#235, #236, #237).
- **Queue #210 current run is healthy under the current recovery semantics.** The 1.1% error rate is dominated by transient LiteLLM backend hiccups; no systemic failures; no restart trigger in sight. The audit's severity-MEDIUM finding is about a hypothetical restart scenario, not the current run state.
- **The harness does NOT depend on `out_f.close()` being called to preserve data.** Per-prompt flush means even a hard kill (SIGKILL) preserves the flushed lines. The restart-truncation finding is the only gap in the recovery story.
- **No impact on queue #210 ETA.** This audit was non-disruptive and does not require any action mid-run. The findings apply to future runs + to contingency planning if the current run needs to be interrupted (not currently expected).
- **Complements queue #227 findings template.** The template's §1 "Errors captured" row will record the final error count per category; this audit explains WHY those errors exist (no retry) and WHAT gaps the retry work (#236) would close.

## 9. Cross-references

- Queue spec: `queue/231-beta-rifts-harness-error-recovery-verify.yaml`
- Harness source: `scripts/run_rifts_benchmark.py` (409 LOC, commit `a52dafc87` for the microsoft/rifts schema fix)
- Queue #210 run: `research/benchmarks/rifts/results-local-fast-qwen-20260415.jsonl` (in progress; ~1097/1740 at audit time)
- Queue #223 progress snapshot: `~/.cache/hapax/relay/inflections/20260415-195000-beta-delta-rifts-progress-snapshot.md` (noted the "no --resume flag" gap in §4, this audit expands on it)
- Queue #229 resource check: `~/.cache/hapax/relay/inflections/20260415-201130-beta-delta-229-rifts-resource-check-green-with-production-finding.md`
- Queue #227 findings template: `docs/research/2026-04-15-rifts-qwen3.5-9b-baseline.md` (commit `4967d7bdf`)
- Queue #232 (follow-up): "RIFTS harness checkpoint resume capability test" — depends on this audit; will now be informed by §4 + §7.1 recommendations
- RIFTS paper: Shaikh et al. ACL 2025, arXiv [2503.13975](https://arxiv.org/abs/2503.13975)
- README: `research/benchmarks/rifts/README.md` (lists "no retry on transient errors" in §"Known limitations" §4 — consistent with this audit)

— beta, 2026-04-15T20:45Z (identity: `hapax-whoami` → `beta`)
