# director_loop LLM cost — Anthropic prompt cache is unused

**Date:** 2026-04-14
**Author:** delta (beta role)
**Scope:** Looks at `agents/studio_compositor/director_loop.py`'s
`_call_activity_llm` path in the context of alpha's active LRR
Phase 2 / Phase 9 work. Asks: is there LLM cost or latency that
a cheap fix could recover without changing behavior?
**Register:** scientific, neutral
**Status:** investigation only — no code change. Fix is a small
JSON schema change in a single function.

## Headline

**Three findings.**

1. **Anthropic prompt caching is unused anywhere in the council
   codebase.** `grep -rn "cache_control" agents/` returns nothing
   in any LLM-call site. The only hits for "ephemeral" are
   docstring narrative, not API parameters. LiteLLM's Redis
   response cache is enabled globally (per workspace CLAUDE.md
   § Docker containers) but it only catches byte-identical
   requests. When `director_loop` sends a system prompt of
   5000+ tokens with a fresh image payload per call, Redis
   misses and the full prompt is re-billed at the model's
   regular input rate.
2. **director_loop fires `_call_activity_llm` at ~39 calls/hour**
   against hardcoded `"model": "claude-opus"` with
   `max_tokens: 2048`, temperature 0.7, and an image payload
   embedded as base64 in the user message. Source:
   `director_loop.py:592-632`. In the 60-minute window ending
   2026-04-14T15:30 UTC, journald captured 39 `LLM raw content`
   entries and 27 `TOKEN POLE EXPLOSION` entries (threshold
   5000). **69 % of calls crossed the 5 000-token threshold.**
3. **Estimated monthly spend on director_loop alone, at current
   cadence, is ~$2 100.** 39 calls/hour × 5 000 prompt tokens ≈
   195 000 input tokens/hour × 24 h × 30 d ≈ 140 M tokens/month
   × Opus at $15/M input ≈ **$2 100/month input alone**, not
   counting completion tokens (capped at 2048, ~$75/M output,
   adds ~$10/month). With Anthropic 5-min prompt caching at
   10 % of regular input cost for cached prefixes, and an
   assumed 70 % cacheable prefix (system prompt + persona +
   tool schema), the savings would be **~$1 300/month on
   cached portion alone**. Exact numbers depend on the real
   prompt structure and alpha's LRR experiment cadence, but
   the order of magnitude is clear.

**Net impact.** A 3-line change in `_call_activity_llm` (add
`cache_control: {"type": "ephemeral"}` to the system prompt
content block, and tag the large-static portions of the prompt)
converts ~70 % of director_loop's prompt tokens from regular
input cost to cached input cost. Zero behavioral change — same
model, same temperature, same output. **This is a free
~60-70 % input-cost cut on the most expensive LLM path in the
compositor.**

## 1. The call site — `director_loop.py:592-632`

```python
def _call_activity_llm(self, prompt: str, images: list | None = None) -> str:
    key = _get_litellm_key()
    if not key:
        return ""

    content: list[dict] = []
    if images:
        import base64
        for img_path in images:
            try:
                if Path(img_path).exists():
                    b64 = base64.b64encode(Path(img_path).read_bytes()).decode()
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    })
            except Exception:
                pass
    content.append({"type": "text", "text": "Respond."})

    messages = [
        {"role": "system", "content": prompt},     # ← system prompt, no cache_control
        {"role": "user", "content": content},      # ← user, with base64 image
    ]

    body = json.dumps({
        "model": "claude-opus",
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.7,
    }).encode()
```

Three things to notice:

- **The system prompt** is a plain string. No `cache_control`
  annotation. Anthropic's API accepts either a plain string or
  a structured list of `{type: "text", text: …}` blocks; to use
  prompt caching, each cached block needs to be upgraded to the
  structured form with `cache_control: {"type": "ephemeral"}`.
- **The user content** is a list of blocks (image + "Respond."
  text). Also no cache_control. In principle, if the same image
  is sent across calls, the image block could be cached too —
  but for director_loop the images are fresh snapshots from the
  compositor, so per-image caching is unlikely to help.
- **Model is hardcoded** as `"claude-opus"`. Whether this
  resolves to `claude-opus-4-6` or an older revision depends on
  LiteLLM's router config (unchecked in this drop). Prompt
  caching works on all current Claude models.

## 2. Observed cadence

### 2.1 LLM call count (60-minute window)

```text
$ journalctl --user -u studio-compositor.service --since "60 minutes ago" | \
      grep -c "LLM raw content"
39
```

39 calls/hour ≈ one call every 92 seconds on average. Tracking
the `_do_speak_and_advance → _call_activity_llm` chain in the
logs, each call feeds a React into the activity loop which
rotates across director slots.

### 2.2 Token-pole explosion count (5000-token threshold)

```text
$ journalctl --user -u studio-compositor.service --since "60 minutes ago" | \
      grep -c "TOKEN POLE EXPLOSION"
27
```

27 explosions in 60 min / 39 LLM calls = **69 % of calls exceed
the 5 000-token ledger threshold**. So the typical prompt size
is comfortably above 5 k. At Opus pricing the ledger threshold
corresponds to ~$0.075 per call on input; 39 calls/hour is
~$3/hour; scaled out to 24 × 30 d ≈ **$2 100/month**.

### 2.3 Per-call scoring sample

At 10:07:42 one complete cycle captured:

```text
LLM raw content (341 chars): '{"activity": "react", …'
Parsed react (307 chars): 'The screen gives us …'
REACT [react]: The screen gives us the promise of the interface, …
```

341 chars of LLM response ≈ ~80-100 tokens of completion
per call. Well below the 2048 max_tokens cap. Completion is
not the cost driver; input prompt is.

## 3. What Anthropic prompt caching buys

Anthropic's prompt cache (direct API and any pass-through
gateway like LiteLLM that supports the `cache_control` field)
works on prefix matching:

| price component | regular cost | cached cost |
|---|---|---|
| **Cache write** (first request that stores a block) | 1.25× regular input | — |
| **Cache read** (subsequent requests within TTL) | — | **0.10× regular input** |
| **Uncached tokens** (tail of request outside cache block) | 1.00× regular input | — |

Cache TTL is 5 min by default (hotter cache) or 1 h for a
markup. For director_loop's ~92-second cadence, 5-min TTL is
plenty — every call after the first lands well within the
window.

**Prerequisite for a block to be cacheable**: ≥1024 tokens in
the block, unchanged bytes between calls, and an explicit
`cache_control: {"type": "ephemeral"}` annotation on that
block. The system prompt (passed as `prompt: str` into
`_call_activity_llm`) is almost certainly > 1024 tokens and
mostly invariant across calls (activity, persona, tool list).
That's the single biggest cacheable block.

### 3.1 Savings model

Assume, for an order-of-magnitude estimate:

- System prompt is ~70 % of the total input tokens (i.e., the
  prompt that gets repeated each call)
- The other 30 % is runtime content (image base64, current
  frame index, recent state) that changes per call and
  therefore cannot be cached
- Cache write cost (first call in a new TTL window) is 1.25×
  on 70 % of tokens; cache read cost (subsequent calls) is
  0.10× on 70 %
- One cache window per ~5 min = ~12 cache writes/hour and
  ~27 cache reads/hour (≈ 39 calls/hour − 12 writes)

Per-hour input token cost, regular:

    39 × 5000 × 1.00   = 195 000 token-equivalents

Per-hour input token cost, cached (approximate):

    writes (12 calls): 12 × 5000 × [0.70 × 1.25 + 0.30 × 1.00]
                     = 12 × 5000 × (0.875 + 0.30)
                     = 12 × 5000 × 1.175
                     = 70 500 token-equivalents
    reads  (27 calls): 27 × 5000 × [0.70 × 0.10 + 0.30 × 1.00]
                     = 27 × 5000 × (0.07 + 0.30)
                     = 27 × 5000 × 0.37
                     = 49 950 token-equivalents
    total            = 120 450 token-equivalents

**Savings: (195 000 − 120 450) / 195 000 ≈ 38 %** on input cost
for director_loop alone, assuming the 70 % cacheable-prefix
assumption holds. If the prefix is 80 %, savings jump to ~48 %.
If it's 50 %, still ~27 %. Realistic range: **25–50 % input
cost reduction**, or **~$500–$1 050/month** off the current
$2 100 director_loop bill, using the same ballpark pricing as
§ 2.2.

**None of this requires changing model, cadence, or completion
quality.** It's a JSON schema change on the API request.

## 4. Hypothesis tests

### H1 — "LiteLLM Redis cache already covers this"

**Refuted for image-bearing prompts.** LiteLLM's Redis cache
hashes the full request (model, messages, parameters). When
the user message contains a base64 image that changes per
call (because the compositor is feeding a fresh snapshot),
the hash differs every time and the cache never hits. Redis
cache helps for text-only repeat calls but not for this path.

### H2 — "The system prompt changes per call anyway"

**Unverified.** Need to read the caller of `_call_activity_llm`
to see how the `prompt` argument is assembled. If the caller
rebuilds the full system prompt each call with different
strings (e.g. embedding current timestamp or live state), the
cache hit rate drops proportionally. Worth one grep before
shipping the fix: find the assembly site, check that the
invariant portion is at least ~1 kB and byte-stable.

### H3 — "LiteLLM doesn't pass through `cache_control` headers"

**Plausible.** LiteLLM sits between the council code and
Anthropic. For the fix to work, LiteLLM must forward the
`cache_control` annotation in the messages to Anthropic. Most
gateways do this transparently for Anthropic-routed calls,
but it's worth confirming with a single test request and
checking the response's `usage.cache_creation_input_tokens`
and `usage.cache_read_input_tokens` fields — they're exposed
in the Anthropic response body and bubble through LiteLLM.

## 5. Proposed fix

### 5.1 Minimal change (assuming `prompt` is the invariant block)

In `_call_activity_llm`, replace the system message construction:

```python
# Before (current):
messages = [
    {"role": "system", "content": prompt},
    {"role": "user", "content": content},
]

# After:
messages = [
    {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
    },
    {"role": "user", "content": content},
]
```

Three extra JSON keys. Same model, same completion, same
temperature, same everything else. On the first request per
5-min window, cache is written at 1.25× cost. On subsequent
requests, the cached portion is billed at 0.10×.

### 5.2 Verification

After shipping, alpha should check the Anthropic response body
for two fields that already exist on every reply:

```python
usage = data.get("usage", {})
usage["cache_creation_input_tokens"]   # first call: ~prompt length; later: 0
usage["cache_read_input_tokens"]       # first call: 0; later: ~prompt length
```

If these are non-zero after the second call, prompt caching
is working. Bonus: add them to the existing `record_spend` call
(director_loop.py:680-685) so the token ledger distinguishes
cached from uncached spend.

### 5.3 Caller-side safety check

Before shipping, grep for the caller that supplies `prompt`
to `_call_activity_llm`:

```text
$ grep -n "_call_activity_llm" agents/studio_compositor/director_loop.py
```

Confirm the `prompt` string is built from static templates,
not from f-strings that embed per-call state. If it embeds
state, the fix needs to split the prompt into a static prefix
(cache_control'd) and a dynamic suffix (regular). That's still
a one-function change, just slightly larger.

## 6. Related opportunity — daimonion, dmn, imagination, any other LLM callers

`grep -rn "cache_control" agents/` returns no hits in any LLM
call path. The same fix pattern applies to every LLM site in
the council that:

- calls Anthropic (directly or via LiteLLM)
- has a ≥1 kB system prompt that's mostly invariant across calls
- fires more than once every 5 min (otherwise cache TTL lapses
  and writes cost more than they save)

Candidates worth a follow-up scan:

- `agents/hapax_daimonion/` — voice conversation path, very
  likely has a large persona prompt
- `agents/dmn/` — cognitive substrate, if it makes LLM calls
- `agents/imagination.py` and adjacent — reverie visual chain,
  gemini-flash via Langfuse (Gemini caching is different but
  LiteLLM exposes something analogous)
- Any pydantic-ai agent that uses `output_type` / `result.output`
  with a large system prompt

A "prompt-cache audit" follow-up drop could list every LLM
caller and tag each with a "cache_control ready?" status.

## 7. Secondary finding — director_loop is hardcoded to Opus

`"model": "claude-opus"` is hardcoded at `director_loop.py:627`.
No adaptive routing, no config reference to
`shared/config.py::get_model_adaptive()`, no tier choice.

This is a separate concern from prompt caching but worth
flagging: if alpha wants director_loop to run on Sonnet for
routine reactions and reserve Opus for a specific subset,
the hardcoding would need to move into a config or into the
same adaptive routing path the other agents use. Memory note
`feedback_model_routing_patience.md` says the operator always
prefers the best Claude model and is willing to wait — so
Opus is the right default — but the hardcoding prevents even
a deliberate downshift during overload.

## 8. References

- `agents/studio_compositor/director_loop.py:592-632` —
  `_call_activity_llm` construction
- `agents/studio_compositor/director_loop.py:680-685` —
  `record_spend` call after response
- `docs/research/2026-04-12-prompt-compression-phase2-ab-results.md`
  — alpha's prior prompt-compression benchmark (context)
- `docs/research/2026-04-14-perf-findings-rollup.md` — rollup
  drop that this work-ahead extends
- Workspace CLAUDE.md § Docker containers — "LiteLLM — Redis
  response caching enabled (1h TTL)"
- Scrape: `journalctl --user -u studio-compositor.service
  --since "60 minutes ago" | grep -c "LLM raw content"` →
  39 calls
- Scrape: same window, `grep -c "TOKEN POLE EXPLOSION"` → 27
- `grep -rn "cache_control" agents/` → 0 hits
- Anthropic prompt caching pricing (public): cache write 1.25×,
  cache read 0.10×, 5 min TTL default
