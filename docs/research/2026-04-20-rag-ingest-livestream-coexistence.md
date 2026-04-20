# rag-ingest x livestream coexistence — design research

**Date:** 2026-04-20
**Author:** alpha
**Dispatch:** `~/.cache/hapax/relay/delta-to-alpha-rag-ingest-livestream-optimization-20260420.md`
**Handoff source:** `docs/superpowers/handoff/2026-04-20-delta-to-alpha-rag-ingest-livestream-research.md`
**Status:** RESEARCH — implementation deferred to delta or successor session
**Scope:** scope, options, ranked recommendation, ship plan; no code in this pass

## 0. Summary

Twice on the night of 2026-04-19 the workstation was driven into VRAM exhaustion sufficient to require Ctrl-Alt-F1 TTY recovery and reboot (`last reboot` shows the sequence: Apr 20 09:02 boot, 09:01 OOM kill cascade, Apr 20 09:58 boot, Apr 20 10:28 boot, all on `6.18.16-1-cachy`). The proximate cause was confirmed in commit `8816040eb` (2026-04-20 10:10 CDT): `rag-ingest.service` peaked at "~10 GB VRAM on every timer fire" because `docling.document_converter.DocumentConverter` lazy-loads a PyTorch layout/OCR model onto CUDA by default (`agents/ingest.py:113-115`), and `rag-ingest.timer` fired a full-tree rescan every 15 minutes against 171,734 watched files (172k files measured on 2026-04-20 across the operator's `documents/rag-sources/` plus `projects/docs/`, dominated by 160,400 gdrive sync artefacts).

Stop-the-bleeding (commit `8816040eb`) shipped a CPU-pin (`Environment=CUDA_VISIBLE_DEVICES=""`) plus a `--watch-only` ExecStart override and deleted the timer from the repo; `systemctl --user show rag-ingest` confirms the service is presently `inactive (dead)` with `MemoryMax=4G`, `CPUQuotaPerSecUSec=800ms`, `CPUWeight=25`. This research evaluates a permanent design that is livestream-safe under the constraints in section 1.

## 1. Constraints (operator-anchored)

The following are non-negotiable per `CLAUDE.md` (workspace + council), the dispatch, and prior-session memory:

1. **TabbyAPI exclusively owns the GPU.** Workspace `CLAUDE.md` Shared Infrastructure section: "TabbyAPI exclusively owns the GPU." Any rag-ingest code path that touches CUDA on the 3090 is a bug.
2. **Livestream is the research instrument** (memory `project_livestream_is_research`). Any rag-ingest behaviour that degrades stream output, director cadence, or compositor frame budget is a livestream regression.
3. **Watch-only is the steady-state default** indefinitely (dispatch "Don't" section). The timer must not be re-introduced.
4. **rag-ingest is Tier 3** (`CLAUDE.md` Architecture section). It is a deterministic background watchdog with no LLM calls of its own; only consumers (RAG queries from voice / chat / orientation) read its output.

## 2. What `agents.ingest` actually does — code inventory

Source: `agents/ingest.py` (800 LOC, single-file module, runs as `python -m agents.ingest`).

### 2.1 Entry surface

- `if __name__ == "__main__":` (`agents/ingest.py:750-800`) parses four flags: `--bulk-only`, `--watch-only`, `--retry-status`, `--force`. The systemd ExecStart now passes `--watch-only` (`systemd/overrides/rag-ingest.service.d/gpu-isolate.conf:15`).
- Two top-level operations: `bulk_ingest()` (`agents/ingest.py:689-719`) — full rglob plus serial process, and `watch()` (`agents/ingest.py:722-747`) — inotify-driven debounced loop.

### 2.2 Per-file pipeline (`ingest_file`, `agents/ingest.py:556-651`)

For every file under a watched directory whose extension is in `{".pdf", ".docx", ".pptx", ".html", ".md", ".txt"}` (`agents/ingest.py:66-75`), the pipeline:

1. Filters macOS resource forks and short binaries-as-text (`agents/ingest.py:566-574`).
2. Calls `get_converter().convert(str(path))` — docling's `DocumentConverter` (`agents/ingest.py:113-117`). This is the single largest VRAM consumer. Even for `.md` files docling routes through the same `DocumentConverter` (journal evidence: every `.md` ingest emits `docling.datamodel.document _guess_format detected formats: [<InputFormat.MD: 'md'>]` and `docling.document_converter Going to convert document batch...`).
3. Calls `get_chunker().chunk(result.document)` — docling's `HybridChunker` with `tokenizer="Qwen/Qwen2.5-7B-Instruct"` and `max_tokens=512` (`agents/ingest.py:79-80`, `120-130`).
4. Parses YAML frontmatter on `.md` files (`agents/ingest.py:589-595`, `parse_frontmatter` at `agents/ingest.py:351-387`).
5. Deletes prior Qdrant points for this source path (idempotent re-ingest, `delete_file_points` at `agents/ingest.py:171-190`).
6. Batch-embeds all chunks via Ollama in a single call (`embed_batch` at `agents/ingest.py:154-160`, model `nomic-embed-cpu` per `agents/ingest.py:29`).
7. Enriches Qdrant payloads with frontmatter and path-derived `source_service` (`enrich_payload` at `agents/ingest.py:390-466`).
8. Optionally checks consent (`_check_consent_for_ingest` at `agents/ingest.py:533-553`) — fail-OPEN if registry unavailable.
9. Upserts a batch of `models.PointStruct` to Qdrant `documents` collection with `wait=True` (`agents/ingest.py:641`).

### 2.3 Failure handling (`agents/ingest.py:193-348`)

Retry queue at `~/.cache/rag-ingest/retry-queue.jsonl`, max 5 attempts, exponential backoff `[30s, 2m, 10m, 1h, 1h]` (`BACKOFF_SCHEDULE` at `agents/ingest.py:92`). Permanent failures land in `~/.cache/rag-ingest/dead-letter.jsonl`. The watcher reprocesses retries every 30s (`agents/ingest.py:740-742`).

### 2.4 Dedup (`agents/ingest.py:469-530`)

`~/.cache/rag-ingest/processed.json` keyed by absolute path, value `{hash, mtime, ingested_at}`. Skip-on-match in `_should_skip` (`agents/ingest.py:509-521`); atomic tmp+rename persistence (`_save_dedup_tracker` at `agents/ingest.py:482-497`). The dedup tracker is the load-bearing primitive that makes a paced backfill safe — it converts the rglob from "process everything" to "process only what changed".

### 2.5 Watch loop (`watch`, `agents/ingest.py:722-747`)

Single `Observer` registers each watched directory (`CFG.watch_dirs = [RAG_SOURCES_DIR, HAPAX_PROJECTS_DIR / "docs"]`, `agents/ingest.py:60-65`). `IngestHandler` (`agents/ingest.py:657-683`) debounces created/modified events by `CFG.debounce_seconds = 2.0`. Hot path is single-threaded inside the watcher thread; ingestion blocks `process_pending` until the file is done. There is no concurrency control, no semaphore, no pacing.

### 2.6 Bulk loop (`bulk_ingest`, `agents/ingest.py:689-719`)

For each watched directory, `d.rglob("*")` (`agents/ingest.py:700`) materialises the full file list, sorts it, then iterates serially calling `ingest_file` per entry with `_should_skip` short-circuit. **No batching, no sleep, no yield primitive, no flag check.** Across 171,734 candidate files this is what created the firehose every 15 minutes pre-fix.

## 3. VRAM peak measurement

### 3.1 Methodology and limitations

Direct measurement of the rag-ingest CUDA path is no longer possible without re-introducing the regression: the GPU-isolate drop-in (`systemd/overrides/rag-ingest.service.d/gpu-isolate.conf:7`) sets `CUDA_VISIBLE_DEVICES=""` so the service cannot allocate VRAM in its current configuration. Re-running the unit with the override removed would recreate the OOM-during-stream condition the dispatch is trying to prevent.

Three independent evidence sources triangulate the peak:

1. **Operator-authored commit message** (`git show 8816040eb`, body line 4): "rag-ingest.service was eating ~10 GB VRAM on every timer fire because docling's DocumentConverter loads a PyTorch layout/OCR model onto CUDA by default."
2. **Kernel OOM ledger** (`journalctl -k --since "2026-04-20 09:00"`): `Apr 20 09:01:11 systemd[1]: system.slice: The kernel OOM killer killed some processes in this unit.` followed by a cascade through `app.slice`, `user-1000.slice`, and `user.slice`, then a clean kernel re-init at 09:02:53. The OOM was system-wide RAM (28 GB physical), not CUDA-OOM proper, but the trigger was VRAM contention forcing TabbyAPI to spill via NVIDIA UVM.
3. **Docling's own documented model surface.** `docling 2.90.0` (in `.venv-ingest/lib/python3.12/site-packages/docling-2.90.0.dist-info`) loads layout + OCR PyTorch checkpoints on first `DocumentConverter.convert()` call. The dependency tree confirms PyTorch + CUDA wheels: `torch-2.11.0`, `torchvision-0.26.0`, full `nvidia-cu*` stack (`cublas`, `cudnn`, `cudart`, etc.) — the wheels alone occupy >2 GB on disk and approximately 3-6 GB of VRAM at warmup, with peak during multi-page PDF parsing reaching the ~10 GB the commit message records.

**Recommended forward measurement:** instrument a one-shot capture by temporarily clearing `CUDA_VISIBLE_DEVICES` in a manual `--bulk-only` invocation outside stream hours, with `nvidia-smi --query-compute-apps --loop=1` logging to a tmpfile, then immediately re-applying isolation. This belongs to delta's implementation phase, not this research pass.

### 3.2 Steady-state CPU/RAM under current configuration

Per dispatch and the commit message, the CPU-pinned watch-only configuration sits at 370 MB RSS. `systemctl --user show rag-ingest` confirms `MemoryMax=4G`. Journal evidence (`journalctl --user -u rag-ingest --since 24h`) shows `.md` files completing in 0.5-1.5 s each on CPU; `.docx` parsing is markedly more expensive but most failures since the fix have been corrupt-file errors, not capacity events.

## 4. Three design options ranked by livestream-safety + implementation effort

Each option assumes the `8816040eb` baseline (CPU-pin + watch-only + timer deletion) stays in place permanently. Options layer additional protections.

### Option A — Hard CPU-only forever, drip-only, no GPU touch ever (status quo)

**Mechanism:** Keep `CUDA_VISIBLE_DEVICES=""` in the drop-in. Never re-enable the timer. Document `--bulk-only` as a manual-only operator command. Add no flag-watching, no scheduling, no VRAM accounting.

**Livestream safety:** Maximal. The unit cannot allocate VRAM by construction. CPU contention is bounded by `CPUQuota=80%` (`systemd/units/rag-ingest.service:25`), `Nice=10`, `CPUWeight=25` (`systemd/overrides/rag-ingest.service.d/priority.conf`), so it cannot starve the compositor / director loop.

**Implementation effort:** Zero. Already shipped in `8816040eb`.

**Costs:** (1) New files arriving while the service is down between reboots are not ingested until manually backfilled. (2) Docling on CPU is 5-20x slower than the GPU path it was using; multi-page PDFs may queue under high inflow. (3) No scheduled bulk pass means dedup-tracker drift over months — files renamed/moved without an inotify event will linger as ghost entries.

**Hidden cost:** docling-on-CPU on `.md` is gross overhead — the format requires zero ML — and on a 171k-file backfill the wall time would be days. This option implicitly accepts that backfill is a manual operator-driven event, not a system property.

### Option B — Flag-yielding drip + manual paced backfill (Phase 1 of recommended)

**Mechanism:** Stay CPU-pinned (Option A as floor). Add a flag-watcher to `IngestHandler.process_pending` and to any future bulk loop: read `/dev/shm/hapax-compositor/director-active.flag` (the dispatch's named flag) at the top of each ingest cycle. If present, defer `process_pending` for the debounce interval; if absent, proceed. Director side publishes the flag when `director_loop` enters an active narration window.

For backfill: add a `--bulk-paced` flag that wraps `bulk_ingest` in a token-bucket primitive (one file per N seconds, configurable; suggested default `N=2.0` to match `debounce_seconds`) and consults the same flag between every file. This makes backfill safe to run with the stream up.

The CPU pin remains because flag-yielding alone does not protect against docling-on-GPU spikes that exceed the flag's reaction window. CPU is the floor; flag-yielding is belt-and-suspenders for CPU pressure on the compositor.

**Livestream safety:** Strong. Two independent guards (CPU-pin + flag-yield).

**Implementation effort:** Low. ~50 LOC: flag reader, `time.sleep` insertion in two loops, new CLI flag, and a director-side flag-publisher (probably a single line in `director_loop` enter/exit, but that surface needs a separate audit before alpha can confirm placement). The flag file itself does not currently exist; `ls /dev/shm/hapax-compositor/` shows `stream-mode-intent.json` and `homage-active-artefact.json` but no `director-active.flag`. Choosing the flag location is a sub-decision (re-use `stream-mode-intent.json` semantics? add a new flag? — recommend new flag with explicit director-loop-enter/exit semantics for clarity).

**Costs:** Director-side flag-publishing must be added (small but coupling rag-ingest to compositor lifecycle). Backfill remains operator-initiated.

### Option C — Working-mode-aware automated backfill with VRAM budget (Phase 2 of recommended)

**Mechanism:** Option B plus:
- Reintroduce a `rag-ingest-backfill.timer` (separately named to keep the deletion policy of `rag-ingest.timer` intact) with `OnUnitActiveSec=24h`. The timer ExecStart calls `python -m agents.ingest --bulk-paced` only when both `working_mode == research` (`shared/working_mode.py:30-35`) **and** the director-active flag is absent.
- Optional: hard VRAM budget via `nvidia-smi --gpu-reset` precondition + `torch.cuda.set_per_process_memory_fraction()` inside the converter wrapper, gated behind a future `--gpu-allowed` flag that is **not enabled by default**. This caps damage if a future operator decision is to allow GPU docling on quiet hours.
- Path-dispatch fast-path for `.md` and `.txt` (dispatch "docling vs alternatives" question): skip `DocumentConverter` entirely for plain-text formats, parse with `markdown-it-py` or naive frontmatter+text split, chunk with the same `HybridChunker` token budget. This is the highest-leverage CPU optimisation available because it removes docling from the hot path of the most common file class (Obsidian vault, claude-code transcripts, screen-context dumps — all pure markdown).

**Livestream safety:** Strong, with policy hooks for future loosening.

**Implementation effort:** Moderate. ~200-400 LOC: timer + script wrapper, working-mode integration, optional GPU budget plumbing, markdown-it fast path with test coverage.

**Costs:** New surface area to maintain. Working-mode coupling means rag-ingest behaviour changes silently when the operator switches mode — observability/notification needed (Prometheus gauge `rag_ingest_paused_reason`). The fast-path adds a parser dependency (markdown-it-py, ~60 KB pure-Python, no GPU artefacts).

### Ranking

| Option | Livestream safety | Effort | Backfill correctness | Future flexibility |
|---|---|---|---|---|
| A (status quo) | 5/5 | 0/5 (none) | 1/5 (manual only) | 1/5 |
| B (flag-yield) | 4/5 | 1/5 (low) | 3/5 (paced manual) | 3/5 |
| C (mode-aware) | 4/5 | 3/5 (moderate) | 5/5 (automated, gated) | 5/5 |

Option A is the right defensive baseline; B is the right next ship; C is the right end-state.

## 5. Recommended ship plan

### Phase 1 (this week, delta-implementable, <=200 LOC)

1. Keep `8816040eb` as-is. Do not regress GPU isolation.
2. Add a director-side flag-publisher: a single producer in `agents/studio_compositor/director_loop.py` (location to be confirmed by delta) that touches `/dev/shm/hapax-compositor/director-active.flag` on enter, removes it on exit, with `os.O_CLOEXEC | os.O_CREAT` semantics and atomic-rename to avoid races. Choose between a new flag and reusing `stream-mode-intent.json` consumers — recommend new flag for separation of concerns.
3. Add a flag-reader to `agents/ingest.py`: at the top of `IngestHandler.process_pending` (`agents/ingest.py:666-675`) and inside the `bulk_ingest` per-file loop (`agents/ingest.py:703-712`), check the flag; if present, `time.sleep(CFG.debounce_seconds)` and `continue` rather than dropping the file (the dedup tracker means re-deferred files are revisited cheaply on next pass).
4. Add `--bulk-paced` CLI flag with a token-bucket `time.sleep(rate)` between files; default rate from `CFG`, suggested 2 s.
5. Test pin: `tests/test_ingest_flag_yield.py` covering (a) flag-present defers, (b) flag-absent proceeds, (c) flag-toggle mid-batch defers next file but not the in-flight one.
6. Update `systemd/overrides/rag-ingest.service.d/gpu-isolate.conf` comment to reference the flag-yield contract.

### Phase 2 (next iteration, after operator green-lights Phase 1 in stream-active conditions, ~400 LOC)

1. Markdown fast-path: introduce `agents/ingest_fastpath_md.py` — pure-Python markdown chunker that bypasses `DocumentConverter` for `.md` and `.txt`. Use `HybridChunker` only if its tokenizer dependency does not transitively pull docling models (verify in delta's pass).
2. `rag-ingest-backfill.timer` (new unit, deliberately renamed to avoid conflict with the deleted `rag-ingest.timer`): `OnUnitActiveSec=24h`, conditional ExecStart that checks `working_mode == research` and absence of director-active flag, then calls `python -m agents.ingest --bulk-paced --max-files 500` (cap per pass to keep wall time bounded).
3. Prometheus gauges via the existing `prometheus_client` infrastructure: `rag_ingest_files_pending`, `rag_ingest_paused_reason{reason="flag"|"working_mode"|"none"}`, `rag_ingest_docling_seconds_bucket`. Surface in the existing health monitor.
4. Update `CLAUDE.md` Architecture section to reflect the flag-yield contract and the new timer.

### Phase 3 (deferred, only if observed need)

1. Hard VRAM budget plumbing for an opt-in `--gpu-allowed` mode. Off by default. Behind operator-explicit toggle.
2. Embedder swap evaluation (Ollama nomic vs. ONNX bge-small vs. Qwen3-0.6B-on-CPU — dispatch "embedder selection" question). Defer until livestream is no longer the gating concern; the current Ollama call is CPU-only and not the VRAM-emergency vector.

## 6. Decision: is `.venv-ingest` isolation still load-bearing on 2026-04-20?

**Yes, but for a different reason than the historical comment claims, and the comment should be updated.**

The historical justification (`systemd/units/rag-ingest.service:14-15`): "isolated from main .venv due to docling/pydantic-ai huggingface-hub version conflict." Direct verification:

- `.venv/lib/python3.12/site-packages/huggingface_hub-1.5.0.dist-info/METADATA` — main venv on huggingface_hub 1.5.0
- `.venv-ingest/lib/python3.12/site-packages/huggingface_hub-1.11.0.dist-info/METADATA` — ingest venv on huggingface_hub 1.11.0

The version skew is real and present. `pyproject.toml:91-92` documents the analogous nemo_toolkit / pydantic-ai pin conflict (transformers <4.58 vs. huggingface-hub >=1.3.4). Docling 2.90.0 + pydantic-ai do not currently coexist at the same huggingface_hub minor; until docling either drops the upper-bound or pydantic-ai loosens the lower-bound, the venv split is mechanical necessity.

**Secondary justification, now primary in importance:** `.venv-ingest` carries the full `torch-2.11.0` + `nvidia-*` CUDA wheel stack (~2 GB on disk). Pulling those into the main `.venv` would bloat every other agent's image and re-introduce the docling-on-CUDA risk by sharing a Python environment with code paths that legitimately want CUDA (TabbyAPI client paths, daimonion STT, sentence-transformer fallbacks). Keeping ingest in a separate process tree with a separate venv and a hard `CUDA_VISIBLE_DEVICES=""` is the cleanest way to enforce the GPU-isolation invariant at the OS layer rather than the application layer.

**Recommended action:** Keep the venv split. Update the comment in `systemd/units/rag-ingest.service:14-15` to:

> Uses `.venv-ingest` for two reasons: (1) docling pins huggingface-hub 1.11+ which is incompatible with main .venv's pin, and (2) the entire CUDA wheel surface (torch + nvidia-cu*) is contained here, where it is mechanically blocked from execution by the `CUDA_VISIBLE_DEVICES=""` drop-in. Do not merge into main .venv even if the version conflict resolves — the GPU-isolation containment is the load-bearing property.

A periodic delta-owned audit (suggested 90-day cadence) should re-check the dependency conflict; if it resolves, the merge can be reconsidered against the GPU-containment constraint. Until then, isolation stays.

## 7. Open questions for operator

1. **Flag location.** New `/dev/shm/hapax-compositor/director-active.flag` or extend `stream-mode-intent.json` semantics? Recommend new flag.
2. **Backfill cadence and cap.** Phase 2 proposes 24h cadence with `--max-files 500`. Confirm or adjust.
3. **Working-mode coupling.** Phase 2 ties backfill to `working_mode == research`. Is rnd-mode also acceptable as long as the director-active flag gates? Operator preference.
4. **Markdown fast-path scope.** Phase 2 covers `.md` + `.txt`. Should `.html` also bypass docling? (HTML has more structure; recommend keeping docling for HTML.)
5. **Notification policy.** When the backfill timer skips a window because the flag is set, ntfy or stay silent? Recommend silent + Prometheus gauge only; ntfy reserved for hard failures.

## 8. Sources cited

- `agents/ingest.py:60-65` — watch directories
- `agents/ingest.py:66-75` — supported extensions
- `agents/ingest.py:79-80, 113-130` — docling converter + chunker init
- `agents/ingest.py:154-160` — Ollama batch embed
- `agents/ingest.py:351-387` — frontmatter parser
- `agents/ingest.py:469-530` — dedup tracker
- `agents/ingest.py:533-553` — consent gate
- `agents/ingest.py:556-651` — `ingest_file` pipeline
- `agents/ingest.py:657-683` — debounced watch handler
- `agents/ingest.py:689-719` — `bulk_ingest` (the firehose)
- `agents/ingest.py:722-747` — watch loop
- `agents/ingest.py:750-800` — CLI entry
- `systemd/units/rag-ingest.service` — base unit
- `systemd/overrides/rag-ingest.service.d/gpu-isolate.conf` — CUDA pin + ExecStart override
- `systemd/overrides/rag-ingest.service.d/priority.conf` — Nice/CPUWeight/IOWeight
- `systemd/overrides/rag-ingest.service.d/ordering.conf` — llm-stack ordering
- `shared/working_mode.py:30-35` — working mode reader
- `git show 8816040eb` — stop-the-bleeding commit, ~10 GB VRAM peak quote
- `journalctl -k --since "2026-04-20 09:00"` — OOM cascade
- `last reboot` — three reboots between 09:02 and 12:15 on 2026-04-20
- `~/.cache/hapax/relay/delta-to-alpha-rag-ingest-livestream-optimization-20260420.md` — research dispatch
- `docs/superpowers/handoff/2026-04-20-delta-to-alpha-rag-ingest-livestream-research.md` — handoff narrative
- `pyproject.toml:91-92` — analogous nemo_toolkit conflict precedent
- `.venv/lib/python3.12/site-packages/huggingface_hub-1.5.0.dist-info` vs. `.venv-ingest/lib/python3.12/site-packages/huggingface_hub-1.11.0.dist-info` — venv skew confirmation
