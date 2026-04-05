# Local Model Optimization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reclaim ~8.5GB VRAM and reduce cloud API dependency without compromising quality, enabling future deployment of larger local models.

**Architecture:** Four independent batches ordered by risk. Batch 1 is config-only (zero code). Batch 2 is single-file code changes. Batch 3 is multi-file routing governance. Batch 4 is future infrastructure (documented but not implemented now). All changes are independently reversible.

**Tech Stack:** LiteLLM, Ollama, Kokoro TTS, Redis, systemd, hapax-council agents, hapax-officium agents

---

## File Map

| File | Action | Batch | Purpose |
|------|--------|-------|---------|
| `~/llm-stack/litellm-config.yaml` | Modify | 1 | Enable Redis caching |
| `shared/config.py` | Modify | 1 | Change embedding model constant |
| `agents/_config.py` | Modify | 1 | Change embedding model constant (vendored copy) |
| `agents/hapax_daimonion/tts.py` | Modify | 2 | Add `device="cpu"` to KPipeline init |
| `agents/dmn/ollama.py` | Modify | 2 | Consolidate to single model |
| `agents/briefing.py` | Modify | 3 | `get_model` → `get_model_adaptive` |
| `agents/digest.py` | Modify | 3 | `get_model` → `get_model_adaptive` |
| `agents/activity_analyzer.py` | Modify | 3 | `get_model` → `get_model_adaptive` |
| `agents/profiler.py` | Modify | 3 | `get_model` → `get_model_adaptive` |
| `agents/drift_detector/agent.py` | Modify | 3 | `get_model` → `get_model_adaptive` |
| `agents/drift_detector/fixes.py` | Modify | 3 | `get_model` → `get_model_adaptive` |
| `agents/knowledge_maint.py` | Modify | 3 | `get_model` → `get_model_adaptive` |
| `agents/_pattern_consolidation.py` | Modify | 3 | `get_model` → `get_model_adaptive` |
| `agents/_threshold_tuner.py` | Modify | 3 | `get_model` → `get_model_adaptive` |

Officium agents (`hapax-officium/agents/`) that use `get_model("fast")` are listed in Batch 3 but officium lacks `get_model_adaptive`. Those changes route directly to `get_model("local-fast")` since officium has no realtime latency requirements.

---

## Batch 1: Config-Only Changes (Zero Risk)

### Task 1: Enable LiteLLM Redis Caching

**Files:**
- Modify: `~/llm-stack/litellm-config.yaml:142-144`

- [ ] **Step 1: Edit LiteLLM config to enable Redis caching**

In `~/llm-stack/litellm-config.yaml`, replace:

```yaml
litellm_settings:
  drop_params: true
  modify_params: true
  set_verbose: false
  cache: false
```

With:

```yaml
litellm_settings:
  drop_params: true
  modify_params: true
  set_verbose: false
  cache: true
  cache_params:
    type: "redis"
    host: "redis"
    port: 6379
    password: "redissecret"
    ttl: 3600
```

Redis is already running in the Docker stack (`redis:7-alpine`, port 6379, password `redissecret`, 768MB max, `allkeys-lru` eviction). No new infrastructure needed.

Default TTL is 1h. Identical prompts (same model + messages + temperature) return cached responses. LLM calls with `temperature > 0` and non-deterministic sampling will rarely hit cache — this primarily benefits repeated tool/status queries.

- [ ] **Step 2: Restart LiteLLM to pick up config**

```bash
cd ~/llm-stack && docker compose restart litellm
```

- [ ] **Step 3: Verify cache is active**

```bash
# Make the same call twice, second should be faster
curl -s http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3:8b","messages":[{"role":"user","content":"say hello"}],"temperature":0}' \
  | jq '.usage'

# Check Redis has cache keys
docker exec -it $(docker ps -qf name=redis) redis-cli -a redissecret KEYS 'litellm*' | head -5
```

Expected: second call returns faster; Redis shows `litellm*` keys.

- [ ] **Step 4: Commit**

```bash
cd ~/llm-stack
git add litellm-config.yaml
git commit -m "feat: enable Redis response caching in LiteLLM"
```

---

### Task 2: Move Embeddings to CPU

**Files:**
- Modify: `hapax-council/shared/config.py:102`
- Modify: `hapax-council/agents/_config.py:91`

The Ollama model `nomic-embed-cpu` is already pulled and available. It's the same nomic-embed-text model with CPU inference. Same 768-dim output — all Qdrant collections remain compatible.

All embedding call sites are async/batch (timers: 15min ingest, 30min av-correlator, 12h profile). Voice salience routing uses Model2Vec (potion-base-8M, already CPU-only) — NOT Nomic. Zero impact on realtime paths.

- [ ] **Step 1: Change embedding model constant in shared/config.py**

In `hapax-council/shared/config.py:102`, change:

```python
EMBEDDING_MODEL: str = "nomic-embed-text-v2-moe"
```

To:

```python
EMBEDDING_MODEL: str = "nomic-embed-cpu"
```

- [ ] **Step 2: Change embedding model constant in agents/_config.py**

In `hapax-council/agents/_config.py:91`, change:

```python
EMBEDDING_MODEL: str = "nomic-embed-text-v2-moe"
```

To:

```python
EMBEDDING_MODEL: str = "nomic-embed-cpu"
```

- [ ] **Step 3: Verify nomic-embed-cpu is available in Ollama**

```bash
ollama list | grep nomic-embed-cpu
```

Expected: model listed and available.

- [ ] **Step 4: Verify embedding dimensions are still 768**

```bash
cd ~/projects/hapax-council
uv run python -c "
from agents._config import embed
v = embed('test embedding')
print(f'Dimensions: {len(v)}')
assert len(v) == 768, f'Expected 768, got {len(v)}'
print('OK: 768-dim confirmed')
"
```

- [ ] **Step 5: Unload GPU embedding model from Ollama**

```bash
# The GPU model will unload naturally after keep_alive expires,
# but we can force it to free VRAM immediately:
curl -s http://localhost:11434/api/generate -d '{"model":"nomic-embed-text-v2-moe","keep_alive":0}'
```

- [ ] **Step 6: Verify VRAM freed**

```bash
nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv,noheader
```

Expected: nomic-embed-text-v2-moe no longer in GPU memory. ~1GB VRAM freed.

- [ ] **Step 7: Commit**

```bash
cd ~/projects/hapax-council
git add shared/config.py agents/_config.py
git commit -m "feat: move embedding inference to CPU (nomic-embed-cpu)

Frees ~1GB VRAM. All embedding paths are async/batch (timers),
no realtime latency impact. Voice salience uses Model2Vec (already CPU).
Same 768-dim output — Qdrant collections unaffected."
```

---

## Batch 2: Single-File Code Changes (Low Risk)

### Task 3: Move Kokoro TTS to CPU Inference

**Files:**
- Modify: `hapax-council/agents/hapax_daimonion/tts.py:43`

Kokoro 82M's `KPipeline` accepts `device="cpu"` natively (see `kokoro/pipeline.py:63-104`). Currently auto-selects CUDA. TTS runs in a background thread (`asyncio.to_thread` in `pipecat_tts.py:54`) with a 30s timeout — ample for CPU inference at 3-5x realtime (a 5-second utterance synthesizes in ~1-1.7s on CPU).

Bridge phrase pre-synthesis at startup (25 phrases) will take ~8-20s on CPU vs ~2-4s on GPU. This runs in a background thread and does not block daemon initialization.

- [ ] **Step 1: Add device parameter to KPipeline initialization**

In `hapax-council/agents/hapax_daimonion/tts.py:43`, change:

```python
            self._pipeline = KPipeline(lang_code="a")  # American English
```

To:

```python
            self._pipeline = KPipeline(lang_code="a", device="cpu")
```

- [ ] **Step 2: Restart daimonion and verify TTS works**

```bash
sudo systemctl --user restart hapax-daimonion
sleep 5
journalctl --user -u hapax-daimonion --since "1 min ago" | grep -i "kokoro\|tts\|pre-synth"
```

Expected: "Kokoro TTS ready" log line, bridge pre-synthesis completes (may take ~10-20s), no errors.

- [ ] **Step 3: Verify VRAM freed**

```bash
nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv,noheader
```

Expected: Kokoro's ~600MB VRAM allocation no longer present under the daimonion process.

- [ ] **Step 4: Commit**

```bash
cd ~/projects/hapax-council
git add agents/hapax_daimonion/tts.py
git commit -m "feat: move Kokoro TTS to CPU inference

Frees ~600MB VRAM. CPU runs 3-5x realtime (sufficient for 30s
timeout). Bridge pre-synthesis slightly slower at startup (~15s
vs ~3s) but non-blocking."
```

---

### Task 4: Consolidate DMN to Single Model

**Files:**
- Modify: `hapax-council/agents/dmn/ollama.py:18-19`

DMN currently runs two Ollama models simultaneously:
- `qwen3:4b` (fast/sensory path, ~2-3GB VRAM)
- `qwen3.5:4b` (thinking/evaluative path, ~6.1GB VRAM)

Consolidating both to `qwen3:8b` (already loaded for other agents):
- **Sensory quality:** qwen3:8b ≥ qwen3:4b (larger model, better instruction following for constrained 1-sentence output)
- **Thinking quality:** qwen3:8b ≥ qwen3.5:4b (more capacity for trajectory assessment)
- **Latency:** Fast path ~2-4s (within 5s tick window). Control law auto-doubles interval if consistently over budget.
- **VRAM:** Eliminates dedicated DMN model slots. qwen3:8b is already GPU-resident for other agent use. Net savings: ~6.1GB (qwen3.5:4b evicted).

The fast path uses `keep_alive: "10m"` to keep the model warm. Since qwen3:8b is already warm for other agents (reasoning, coding, local-fast aliases), there's no cold-start penalty.

- [ ] **Step 1: Change model constants in ollama.py**

In `hapax-council/agents/dmn/ollama.py:18-19`, change:

```python
DMN_MODEL_FAST = "qwen3:4b"
DMN_MODEL_THINK = "qwen3.5:4b"
```

To:

```python
DMN_MODEL_FAST = "qwen3:8b"
DMN_MODEL_THINK = "qwen3:8b"
```

- [ ] **Step 2: Restart DMN and verify ticks fire**

```bash
sudo systemctl --user restart hapax-dmn
sleep 10
journalctl --user -u hapax-dmn --since "1 min ago" | grep -E "sensory|evaluative|tick"
```

Expected: sensory ticks firing every ~5s, no errors. Log lines show observations being produced.

- [ ] **Step 3: Unload the old models from Ollama**

```bash
# Force unload qwen3:4b and qwen3.5:4b from VRAM
curl -s http://localhost:11434/api/generate -d '{"model":"qwen3.5:4b","keep_alive":0}'
# qwen3:4b may not be loaded — safe to try
curl -s http://localhost:11434/api/generate -d '{"model":"qwen3:4b","keep_alive":0}'
```

- [ ] **Step 4: Update OLLAMA_MAX_LOADED_MODELS**

With DMN consolidated, only 2 models need to be GPU-resident (qwen3:8b + nomic-embed-cpu on CPU). Reduce from 3 to 2:

```bash
# Check current setting
grep OLLAMA_MAX_LOADED_MODELS /etc/systemd/system/ollama.service 2>/dev/null || \
  grep OLLAMA_MAX_LOADED_MODELS ~/.config/systemd/user/ollama.service 2>/dev/null || \
  echo "Set via environment variable or Ollama defaults"
```

If set as env var, update to `OLLAMA_MAX_LOADED_MODELS=2`. If using default, leave as-is (Ollama defaults to auto-managing based on VRAM).

- [ ] **Step 5: Verify VRAM freed**

```bash
nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv,noheader
```

Expected: qwen3.5:4b (~6.1GB) no longer loaded. Only qwen3:8b remains for both DMN and general agent use.

- [ ] **Step 6: Monitor DMN health for 5 minutes**

```bash
# Watch for control law degradation (interval doubling)
journalctl --user -u hapax-dmn -f --since "now" | head -30
```

Expected: sensory ticks complete within 5s budget. No "doubling interval" messages. If latency exceeds budget, the control law safely doubles the interval — this is acceptable, not a failure.

- [ ] **Step 7: Commit**

```bash
cd ~/projects/hapax-council
git add agents/dmn/ollama.py
git commit -m "feat: consolidate DMN to qwen3:8b for both paths

Eliminates dedicated qwen3:4b and qwen3.5:4b model slots.
qwen3:8b is already GPU-resident for other agents — no new
VRAM cost. Frees ~6.1GB. Quality equivalent or better (larger
model for both sensory observation and trajectory assessment).
Control law auto-scales if latency exceeds 5s tick budget."
```

---

## Batch 3: Agent Routing Governance (Moderate Scope)

### Task 5: Wire Council Agents to Stimmung-Aware Routing

**Files (hapax-council):**
- Modify: `agents/briefing.py:226`
- Modify: `agents/digest.py:180`
- Modify: `agents/activity_analyzer.py:783`
- Modify: `agents/profiler.py:153,277,1202`
- Modify: `agents/drift_detector/agent.py:61`
- Modify: `agents/drift_detector/fixes.py:52`
- Modify: `agents/knowledge_maint.py:467`
- Modify: `agents/_pattern_consolidation.py:144`
- Modify: `agents/_threshold_tuner.py:95`

These 9 agents currently call `get_model("fast")` which always routes to `gemini-flash` (cloud). None of them need vision or tool calling — they're pure text synthesis/classification.

Switching to `get_model_adaptive("fast")` preserves quality (still routes to `gemini-flash` under normal conditions) but enables automatic downgrade to local models when stimmung detects resource or cost pressure. This is a governance improvement, not a quality compromise.

`get_model_adaptive` is defined in both `shared/config.py:130` and `agents/_config.py:112`. Each agent file imports from whichever config it already uses.

- [ ] **Step 1: Update all council agent import+call sites**

For each file, change `get_model("fast")` to `get_model_adaptive("fast")`. Ensure `get_model_adaptive` is imported. The import source depends on what the file already imports:

**agents/briefing.py:226** — uses `from shared.config import get_model` → add `get_model_adaptive`:

```python
# Change import line to include get_model_adaptive
from shared.config import get_model_adaptive
# At line 226, change:
#   get_model("fast"),
# To:
    get_model_adaptive("fast"),
```

Apply the same pattern to each file. For files importing from `agents._config`, import `get_model_adaptive` from `agents._config`.

The exact files and lines:

| File | Line | Import source |
|------|------|---------------|
| `agents/briefing.py` | 226 | `shared.config` |
| `agents/digest.py` | 180 | `shared.config` |
| `agents/activity_analyzer.py` | 783 | `shared.config` |
| `agents/profiler.py` | 153, 277 | `shared.config` |
| `agents/profiler.py` | 1202 | `agents._config` (local `_get_model`) |
| `agents/drift_detector/agent.py` | 61 | `shared.config` |
| `agents/drift_detector/fixes.py` | 52 | `shared.config` |
| `agents/knowledge_maint.py` | 467 | `shared.config` |
| `agents/_pattern_consolidation.py` | 144 | `agents._config` |
| `agents/_threshold_tuner.py` | 95 | `agents._config` |

For `profiler.py:1202` which uses a local `_get_model("fast")` wrapper — change the wrapper to call `get_model_adaptive` internally, or replace the call site directly.

- [ ] **Step 2: Run existing tests**

```bash
cd ~/projects/hapax-council
uv run pytest tests/test_stimmung_refinements.py -v
```

Expected: all stimmung routing tests pass (they already test `get_model_adaptive`).

- [ ] **Step 3: Run a smoke test on one agent**

```bash
cd ~/projects/hapax-council
uv run python -m agents.briefing --dry-run 2>&1 | head -20
```

Expected: agent initializes without import errors.

- [ ] **Step 4: Commit council changes**

```bash
cd ~/projects/hapax-council
git add agents/briefing.py agents/digest.py agents/activity_analyzer.py \
  agents/profiler.py agents/drift_detector/agent.py agents/drift_detector/fixes.py \
  agents/knowledge_maint.py agents/_pattern_consolidation.py agents/_threshold_tuner.py
git commit -m "feat: wire 9 agents to stimmung-aware model routing

All pure-text agents now use get_model_adaptive('fast') instead
of get_model('fast'). Under normal stimmung, routes to gemini-flash
(no quality change). Under resource/cost pressure, automatically
downgrades to local models. Governance improvement — agents
participate in system-wide resource management."
```

---

### Task 6: Route Officium Agents to Local

**Files (hapax-officium):**
- Modify: `agents/digest.py:168`
- Modify: `agents/drift_detector.py:138,746`
- Modify: `agents/knowledge_maint.py:351`
- Modify: `agents/meeting_lifecycle.py:153`

Officium does not have `get_model_adaptive`. These 4 agents are batch/timer-driven with no realtime requirements. They can safely route to `get_model("local-fast")` (qwen3:8b) directly.

Excluded from this change (keep on cloud):
- `management_briefing.py` — 80K token input, needs cloud context window
- `management_prep.py` — 150K token input, needs cloud context window
- `management_profiler.py` — profiling quality matters for management decisions

- [ ] **Step 1: Update officium agent call sites**

For each file, change `get_model("fast")` to `get_model("local-fast")`:

| File | Line | Change |
|------|------|--------|
| `agents/digest.py` | 168 | `get_model("fast")` → `get_model("local-fast")` |
| `agents/drift_detector.py` | 138 | `get_model("fast")` → `get_model("local-fast")` |
| `agents/drift_detector.py` | 746 | `get_model("fast")` → `get_model("local-fast")` |
| `agents/knowledge_maint.py` | 351 | `get_model("fast")` → `get_model("local-fast")` |
| `agents/meeting_lifecycle.py` | 153 | `get_model("fast")` → `get_model("local-fast")` |

- [ ] **Step 2: Smoke test one officium agent**

```bash
cd ~/projects/hapax-officium
uv run python -m agents.digest --dry-run 2>&1 | head -20
```

Expected: agent initializes without errors.

- [ ] **Step 3: Commit officium changes**

```bash
cd ~/projects/hapax-officium
git add agents/digest.py agents/drift_detector.py agents/knowledge_maint.py agents/meeting_lifecycle.py
git commit -m "feat: route 4 batch agents to local-fast (qwen3:8b)

Digest, drift detector, knowledge maint, and meeting lifecycle
are timer-driven batch agents with no realtime or long-context
requirements. Management briefing, prep, and profiler stay on
cloud models (large context windows needed)."
```

---

## Batch 4: Future — TabbyAPI Deployment (Documented, Not Implemented)

This batch is deferred until Batches 1-3 are validated and VRAM savings confirmed (~8.5GB recovered). TabbyAPI deployment becomes the path to serving larger models (Qwen3.5-35B-A3B at EXL2) once headroom exists.

**Prerequisites:**
- Batches 1-3 complete and stable
- VRAM headroom confirmed at ~13GB free
- Decision on target model (Qwen3-30B-A3B vs Qwen3.5-35B-A3B)

**Steps when ready:**
1. Download pre-quantized EXL2 model: `cd ~/projects/tabbyAPI && ./start.sh download turboderp/Qwen3-8B-exl2 --revision 4.0bpw`
2. Create `~/projects/tabbyAPI/config.yml` from `config_sample.yml` (port 5000, localhost only, model dir, cache mode Q6)
3. Create systemd user unit `tabbyapi.service` (Type=simple, After=network.target)
4. Add LiteLLM route: `model_name: qwen3:8b-exl2` → `api_base: http://127.0.0.1:5000`
5. Test inference quality matches Ollama qwen3:8b
6. If quality matches, update `local-fast` alias in LiteLLM to route to TabbyAPI instead of Ollama

---

## VRAM Impact Summary

| Change | VRAM Freed | Batch |
|--------|-----------|-------|
| Embeddings → CPU | +1,000 MB | 1 |
| Kokoro TTS → CPU | +600 MB | 2 |
| DMN qwen3.5:4b evicted | +6,100 MB | 2 |
| TabbyAPI EXL2 efficiency | +800 MB | 4 (future) |
| **Total (Batches 1-3)** | **~7,700 MB** | |
| **Total (all batches)** | **~8,500 MB** | |

Post-implementation VRAM budget (after Batches 1-3):

| Service | VRAM |
|---------|------|
| Daimonion (STT + YOLO, no TTS) | ~3,400 MB |
| Reverie/Compositor | ~3,100 MB |
| Imagination (wgpu) | ~220 MB |
| Ollama: qwen3:8b (shared: DMN + agents) | ~5,700 MB |
| CUDA/Hyprland overhead | ~400 MB |
| **Total** | **~12,820 MB** |
| **Free** | **~11,750 MB** |

---

## Rollback

Every change is independently reversible:
- **LiteLLM cache:** Set `cache: false`, restart LiteLLM
- **Embeddings:** Change constant back to `nomic-embed-text-v2-moe`
- **Kokoro:** Remove `device="cpu"` parameter
- **DMN:** Restore `qwen3:4b` / `qwen3.5:4b` constants
- **Agent routing:** Revert `get_model_adaptive` → `get_model`
