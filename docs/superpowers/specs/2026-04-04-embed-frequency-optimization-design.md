# Embed Frequency Optimization

**Date:** 2026-04-04
**Status:** Design
**Problem:** Ollama nomic-embed-cpu consumes ~380% CPU (4 cores on 8-core machine) due to high embed call volume — 142 individual calls at every daimonion restart plus ~3.3 calls/second at steady state.

## Context

The affordance pipeline embeds capability descriptions into Qdrant for semantic retrieval. Every impingement (detected deviation from the DMN's predictive model) is embedded and matched against capability descriptions via cosine similarity.

**Current state:**
- 142 capabilities indexed individually at daimonion startup (1 speech + 9 vocal chain + 1 system awareness + 1 discovery + 31 tools + 99 world affordances), each a separate Ollama API call taking ~1s on CPU
- Additional capabilities indexed by logos engine (reactive rules), reverie, and fortress at their respective startups
- Capability descriptions are static text — never change between restarts
- The `EmbeddingCache` in `AffordancePipeline` keys on impingement `content` dict (md5 of sorted items), so sensor impingements with changing numeric values always miss even when the rendered narrative text is identical
- `embed_batch()` exists in `shared/config.py` and `agents/_config.py` but is unused for capability indexing
- nomic-embed-cpu (475M MoE) uses ~4 CPU threads per inference

**Measured impact:**
- Startup: ~142 sequential Ollama calls = ~140s of sustained CPU load
- Steady state: ~200 embed API calls per 30s = 3.3/s from 5 processes
- CPU: nomic-embed runner at 380% (3.8 cores) — the single largest CPU consumer after Hyprland

## Design

### 1. Batch Capability Indexing

Add `index_capabilities_batch()` to `AffordancePipeline`:

```python
def index_capabilities_batch(self, records: list[CapabilityRecord]) -> int:
    """Index multiple capabilities in a single embed + upsert operation.

    Embeds all descriptions in one embed_batch() call, upserts all points
    to Qdrant in a single request. Returns count of successfully indexed.
    """
```

**Behavior:**
1. Collect all capability descriptions from the input records
2. Check disk cache for existing embeddings (see section 2)
3. Call `embed_batch()` once for any cache misses
4. Merge cached + fresh embeddings
5. Build `PointStruct` list and call `client.upsert()` once with all points
6. Update `_activation` state for new capabilities
7. Save updated disk cache

**Callers to update:**

| File | Current pattern | New pattern |
|------|----------------|-------------|
| `agents/hapax_daimonion/init_pipeline.py` | 142 individual `index_capability()` calls across speech, vocal chain, system awareness, discovery, tools, world affordances | Collect all `CapabilityRecord` into a list, call `index_capabilities_batch()` once |
| `agents/hapax_daimonion/tool_recruitment.py:63` | Loop calling `index_capability()` per tool | `index_capabilities_batch(tool_records)` |
| `logos/engine/__init__.py:469` | Loop indexing reactive rules on first cascade | Collect rule records, `index_capabilities_batch()` once, set `_cascade_initialized` |
| `agents/reverie/_affordances.py:68` | Loop calling `index_capability()` | `index_capabilities_batch(reverie_records)` |
| `agents/fortress/__main__.py:94` | Single `index_capability()` | Keep as-is (single capability, not worth batching) |

The single-record `index_capability()` method remains for runtime capability registration (rare, event-driven additions after startup).

### 2. Disk-Persisted Embedding Cache

New module: `shared/embed_cache.py`

```python
class DiskEmbeddingCache:
    """Persistent cache mapping text → embedding vector.

    Stored at ~/.cache/hapax/embed-cache.json. Keyed by SHA-256 of the
    input text (with prefix). Invalidated when model name or embedding
    dimension changes.
    """
```

**Cache file format** (`~/.cache/hapax/embed-cache.json`):
```json
{
  "model": "nomic-embed-cpu",
  "dimension": 768,
  "entries": {
    "<sha256 of 'search_document: capability description text'>": [0.123, ...],
    ...
  }
}
```

**Cache key:** SHA-256 of the full prefixed text (e.g., `"search_document: Sense current weather..."`) — same string that gets sent to Ollama.

**Invalidation:** If the stored `model` or `dimension` differs from current config, the entire cache is flushed. No TTL — capability descriptions are static text, embeddings are deterministic for a given model.

**Integration with `index_capabilities_batch()`:**
1. Load disk cache
2. For each record, compute cache key from `f"search_document: {record.description}"`
3. Separate into cache hits and misses
4. Call `embed_batch()` only for misses
5. Merge results, save cache

**Expected impact:** Second-and-subsequent daimonion restarts index 142 capabilities in <100ms (all cache hits → only Qdrant upsert, no Ollama calls).

### 3. Impingement Embed Cache Key Fix

The `EmbeddingCache` in `AffordancePipeline` currently keys on the raw `content` dict:

```python
def _key(self, content: dict[str, Any]) -> str:
    raw = str(sorted(content.items()))
    return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()
```

Sensor impingements carry changing numeric values (heart rate, stress, flow score), so the cache key changes every tick even when the rendered narrative text (what actually gets embedded) is identical.

**Change:** Key the `EmbeddingCache` on the **rendered text** rather than the raw content dict:

```python
# In _get_embedding():
text = render_impingement_text(impingement)
cached = self._embed_cache.get_by_text(text)
if cached is not None:
    return cached
embedding = embed_safe(text, prefix="search_query")
if embedding is not None:
    self._embed_cache.put_by_text(text, embedding)
return embedding
```

Add `get_by_text(text: str)` and `put_by_text(text: str, embedding)` methods that key on md5 of the text string directly.

**Expected impact:** Sensor impingements with stable narrative text (e.g., "keyboard monitoring is engaged but noticing reduced activity") will hit cache across ticks. Estimated 30-50% reduction in steady-state embed calls, since many consecutive impingements from the same sensor render identically.

### 4. Expected Results

| Metric | Before | After |
|--------|--------|-------|
| Startup embed calls | 142 | 0-5 (cache misses only) |
| Startup Ollama time | ~140s | <1s (second run onward) |
| Steady-state calls/s | ~3.3 | ~1.5-2.0 |
| nomic-embed CPU | ~380% | ~150-200% |
| System load contribution | ~15 threads | ~6-8 threads |

### 5. Files Changed

| File | Change |
|------|--------|
| `shared/embed_cache.py` | **New:** `DiskEmbeddingCache` class |
| `shared/affordance_pipeline.py` | Add `index_capabilities_batch()`, add text-keyed cache methods to `EmbeddingCache` |
| `agents/hapax_daimonion/init_pipeline.py` | Collect all records into list, call `index_capabilities_batch()` once |
| `agents/hapax_daimonion/tool_recruitment.py` | Use `index_capabilities_batch()` for bulk tool registration |
| `logos/engine/__init__.py` | Batch-index reactive rules on first cascade |
| `agents/reverie/_affordances.py` | Use `index_capabilities_batch()` |
| `tests/test_embed_cache.py` | **New:** disk cache load/save/invalidation tests |
| `tests/test_affordance_pipeline.py` | Add batch indexing tests, text-keyed cache tests |

### 6. Testing

- **Unit:** `DiskEmbeddingCache` — load, save, cache hit, cache miss, invalidation on model change, concurrent access safety
- **Unit:** `AffordancePipeline.index_capabilities_batch()` — correct embedding, Qdrant upsert with all points, activation state initialization
- **Unit:** `EmbeddingCache` text-keyed methods — hit/miss behavior, LRU eviction
- **Integration:** Daimonion startup indexes all capabilities via batch path, verify Qdrant collection populated correctly

### 7. Non-Goals

- Replacing nomic-embed-cpu with Model2Vec for pipeline queries (separate research cycle on retrieval quality impact)
- Reducing impingement generation rate (architectural decision about perception tick cadence)
- Changing the Ollama runner's thread count or parallelism settings
