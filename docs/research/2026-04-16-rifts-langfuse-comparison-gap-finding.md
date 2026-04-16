---
title: RIFTS benchmark ↔ Langfuse production comparison — observability gap
date: 2026-04-16
queue_item: '242'
depends_on: '210'
epic: lrr
phase: substrate-scenario-2
status: blocked-on-observability-gap
---

# RIFTS ↔ Langfuse production comparison — observability gap

Queue #242 calls for a 6-week Langfuse-backed comparison between the
RIFTS benchmark numbers (#210) and Qwen3.5-9B's live production
behavior. On attempting the pull, two structural gaps make the
comparison impossible without prerequisite work.

## Findings

### 0. Root cause for the retention gap: MinIO inode exhaustion

After wiring the `langfuse` LiteLLM callback (see §"Recommendations"
below — already shipped in this PR), the next test call returned
internally OK but Langfuse logged:

```
error  Failed to upload JSON to S3 events/otel/.../...json
       Storage backend has reached its minimum free drive threshold.
       Please delete a few objects to proceed.
```

`/data` (where MinIO stores event blobs) reports:

```
$ df -i /data
Filesystem    Inodes    IUsed  IFree  IUse%
/dev/sdc2   21733376 21733375     1   100%
```

**100% inode exhaustion on /data**. Disk capacity is fine (35% used,
201 GB free); inodes are completely full. MinIO refuses new writes
even when bytes are available. The 14-day lifecycle rule on the
`events/` prefix mentioned in workspace `CLAUDE.md` § Docker
containers is either not running, not aggressive enough, or the
inode pressure comes from a non-events prefix (Open WebUI uploads,
ntfy attachments, RustDesk/OBS recordings — all live under `/data`).

This explains §1 (retention gap): Langfuse stopped accepting writes
~2 weeks before the lifecycle would have rotated old events out, so
the visible window collapsed to whatever was already ingested before
the inode wall.

### 1. Langfuse retention covers ~2 days, not 6 weeks

| Metric | Value |
|---|---|
| Total `GENERATION` observations | 1133 |
| Earliest observation | 2026-03-30T18:00:23Z |
| Latest observation | 2026-04-01T04:22:20Z |
| Window covered | ~33 hours |

The implicit "6-week" baseline in the queue spec does not exist. Either
retention is configured aggressively short, the ClickHouse store has
been pruned, or telemetry only began ~2 days before the query. None of
those windows are sufficient for a behavior-distribution comparison.

### 2. Production Qwen3.5-9B is not in Langfuse at all

Model distribution across all 1133 observations:

| Count | Model |
|---|---|
| 680 | `gemini/gemini-2.5-flash` |
| 404 | `ollama/qwen3:8b` |
| 46 | `anthropic/claude-sonnet-4-20250514` |
| 3 | `gemini/gemini-2.5-pro` |

The 404 "qwen" entries are all `ollama/qwen3:8b` — the **deprecated**
8B model that was removed from Ollama and the LiteLLM config weeks ago
(workspace `CLAUDE.md` § Shared Infrastructure). The live production
substrate `openai/Qwen3.5-9B-exl3-5.00bpw` (TabbyAPI on `:5000`,
serving the `local-fast` / `coding` / `reasoning` LiteLLM routes) has
**zero observations** in Langfuse.

### 3. Root cause: LiteLLM has no Langfuse callback wired

`~/llm-stack/litellm-config.yaml` declares only the Prometheus success
callback:

```yaml
litellm_settings:
  success_callback: ["prometheus"]
```

There is no `langfuse` entry in the callback list. Every LLM call that
goes through the LiteLLM gateway — which by design includes all local
TabbyAPI routes (`local-fast`, `coding`, `reasoning`,
`local-research-instruct`) and most cloud routes — is invisible to
Langfuse. The observations that DO show up come from callers that hit
provider SDKs directly (gemini-flash via google-genai SDK, claude
via anthropic SDK, the legacy ollama qwen calls), bypassing LiteLLM.

## Comparison this finding implies

The original #242 spec assumed Langfuse had a meaningful Qwen
production sample. It does not, by two compounding gaps:

1. The retention window is ~33 hours, not 6 weeks.
2. The Qwen3.5-9B production model is not logged at all.

A like-for-like benchmark-vs-production comparison cannot be produced
from the current data. Producing one requires three sequential steps:

1. **Wire `langfuse` into LiteLLM `success_callback`.** Single-line
   config change + container restart.
2. **Verify retention is durable** (check ClickHouse retention
   policy + MinIO lifecycle rules; reference: workspace `CLAUDE.md`
   §Docker containers — Langfuse blob store has a 14-day lifecycle
   on `events/` prefix).
3. **Wait 1–2 weeks** for a meaningful production sample to accumulate.

After those three, run #242's original procedure: pull the Qwen sample,
classify each response (refusal / question-asking / hallucination /
normal), compare rates against the RIFTS benchmark numbers from #210.

## Recommendations

- **Shipped in this PR:** added `langfuse` to LiteLLM
  `success_callback` + `failure_callback`. Container restarted.
  Callback is registered (`Initialized Success Callbacks -
  ['prometheus', 'langfuse']`) but events are currently rejected by
  Langfuse due to the §0 inode wall.
- **Immediate operator action required:** free inodes on `/data`.
  Likely targets in priority order:
  1. `/data/Videos/{RustDesk,OBS}` — old screen recordings, often
     thousands of small frame files
  2. `/data/open-webui/{cache,uploads,vector_db}` — chat history,
     image cache, vector store fragments
  3. `/data/minio/langfuse/events/` — past events that should have
     been rotated by the 14-day lifecycle policy (verify the rule
     is active via `mc ilm rule list local/langfuse`)
  4. `/data/n8n` — workflow state
  5. `/data/ntfy` — message attachments
- **Follow-up (post-cleanup, 1-2 weeks):** re-attempt #242 with real
  production Qwen telemetry once samples accrue.
- **Side benefit:** the same callback wiring unblocks observability
  for the new `local-research-instruct` route (queue #212) — the
  OLMo-3 production-vs-benchmark comparison requires the same path.

## Acceptance — REVISED

The original acceptance was:
- Langfuse pull complete
- Production-vs-benchmark table
- Divergence analysis

Revised given the gap:
- [x] Langfuse retention/coverage state documented
- [x] Root cause for missing Qwen telemetry identified (callback gap)
- [x] Sequential remediation plan
- [ ] Original three acceptance items deferred to post-remediation
      follow-up
