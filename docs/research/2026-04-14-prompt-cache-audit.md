# Prompt-cache audit — every council LLM caller

**Date:** 2026-04-14
**Author:** delta (beta role)
**Scope:** Extends `2026-04-14-director-loop-prompt-cache-gap.md`.
Enumerates every LLM-call site in the council, tags each with
its architecture, and reports whether it uses Anthropic prompt
caching. Asks: how many additional sites can use the same fix
pattern as director_loop, and what's the correct prioritization?
**Register:** scientific, neutral
**Status:** audit only — no code change

## Headline

**`grep -rn "cache_control" agents/` returns zero hits in any
LLM call path across `hapax_daimonion/`, `studio_compositor/`,
`fortress/`, `vision_observer/`, and `dmn/`.** Every council
LLM caller is paying regular input rate on every prompt token.

**Seven candidate sites** identified. Five route to Anthropic
via LiteLLM (either directly or through an OpenAI-compatible
proxy) and are fix-candidates. One routes to Ollama (local,
no Anthropic caching — not applicable). One is a pipecat
`OpenAILLMService` instance which is slightly trickier but
still fixable at the message-construction layer.

## Caller inventory

| # | file | client | model | system prompt shape | cache_control? | fix effort |
|---|---|---|---|---|---|---|
| 1 | `agents/studio_compositor/director_loop.py:592` | raw `urllib.request` → LiteLLM | hardcoded `"claude-opus"` | plain string `prompt: str`, ≥5 000 tokens measured | **no** | **S** (3 JSON keys, drop #9 § 5.1) |
| 2 | `agents/hapax_daimonion/pipeline.py:109` | pipecat `OpenAILLMService` → LiteLLM | config `llm_model` (default `claude-sonnet`) | `LLMContext(messages=[{"role": "system", "content": prompt}])` | **no** | **M** — requires converting context-construction to structured content blocks; pipecat-layer |
| 3 | `agents/hapax_daimonion/screen_analyzer.py:97` | `openai.AsyncOpenAI` → LiteLLM | config `self.model` | `self._system_prompt` with per-call `extra_context` appended — **prompt differs per call**, so cache must be split | **no** | **M** — split invariant prefix from dynamic suffix, mark prefix ephemeral |
| 4 | `agents/hapax_daimonion/workspace_analyzer.py:178` | `openai.AsyncOpenAI` → LiteLLM | config `self.model` | mirrors screen_analyzer | **no** | **M** — same pattern as screen_analyzer |
| 5 | `agents/fortress/deliberation.py:157` | `litellm.acompletion` direct | config | `build_deliberation_prompt()` builds a message list | **no** | **S** — analogous to director_loop, one function change |
| 6 | `agents/dmn/ollama.py` | local Ollama HTTP | local model | n/a — local inference | n/a | **not applicable** — no Anthropic prompt cache for local models |
| 7 | `agents/vision_observer/__main__.py` | not yet inspected in this drop | — | — | **no (by grep)** | **?** — needs a follow-up deep-read |

Two more candidate areas not fully enumerated in this drop:

- **Any pydantic-ai `Agent(...)` caller.** The workspace
  CLAUDE.md § Shared Conventions says `pydantic-ai` is the
  canonical LLM interface for most agents. pydantic-ai
  exposes `system_prompt=` at Agent construction time. Whether
  pydantic-ai v0.x emits `cache_control` on the system prompt
  when routed to Anthropic is an open question — the field
  would need either native pydantic-ai support, a model-level
  option, or a custom provider subclass. Not immediately
  actionable; flag for pydantic-ai feature research.
- **`agents/hapax_daimonion/tools.py` and `session_events.py`**
  both matched the initial grep for LLM-call keywords but
  weren't read in depth — they may be tool schemas or event
  plumbing, not LLM call sites.

## Why the fix pattern works through OpenAI-compatible clients

The concern with pipecat's `OpenAILLMService` and `openai.AsyncOpenAI`
is that they speak OpenAI protocol, not Anthropic native. But
LiteLLM's gateway supports Anthropic prompt caching via the
message body, not via SDK-level knobs. The content-block
structure with `cache_control` rides as a JSON field inside
the `messages` array:

```python
messages = [
    {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": large_static_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
    },
    …
]
```

When LiteLLM receives this through its OpenAI-compatible
endpoint, it recognizes the `cache_control` field in the
message content and forwards to Anthropic's API in the
correct shape. The OpenAI SDK happily serializes this
structure because `content` as a list of blocks is valid
OpenAI-compatible JSON (used for vision and tool-use). **The
cache_control annotation rides on top without the client SDK
needing to know about it.**

This means pipecat, openai SDK, and direct litellm.acompletion
all work — the fix lives in the message-construction code,
not in the client library.

## Prioritization

**Order to ship** (highest ratio first, matching drop #9's
rollup §):

1. **director_loop.py** — drop #9 already specifies the patch;
   ~39 calls/hour, ~$2 100/month spend, estimated ~$500–1 050
   /month recoverable.
2. **fortress/deliberation.py** — same raw-HTTP shape as
   director_loop, fix is analogous. Cadence unmeasured in this
   drop — if deliberation only fires on specific fortress
   events it may be low-volume; measure first.
3. **hapax_daimonion/pipeline.py** — voice conversation path,
   likely the highest-volume LLM caller in the council during
   operator voice sessions. System prompt is a persona doc
   (invariant across turns), ideal cache candidate. Fix is M
   because the `LLMContext` construction needs to switch from
   plain string to structured content blocks — verify pipecat
   tolerates the richer form, then ship.
4. **screen_analyzer.py + workspace_analyzer.py** — identical
   shape, both have per-call context suffixes. Fix is M-each
   because the invariant prefix and dynamic suffix need to be
   separated into two content blocks, only the first marked
   `ephemeral`. Volume is operator-driven (they fire on screen
   capture events), probably lower than voice.
5. **pydantic-ai-based agents** — research pydantic-ai feature
   support first. If the library has a `cache_system_prompt`
   option or similar, it's a config flag per Agent. If not,
   the fix may need to drop into the provider layer.
6. **dmn/ollama.py** — skip. Local Ollama has no prompt cache.

## Verification pattern (applies to every site once shipped)

After adding `cache_control`, the Anthropic response includes:

```python
usage = response.get("usage", {})
usage["cache_creation_input_tokens"]   # first call per 5 min: ~prefix length
usage["cache_read_input_tokens"]       # subsequent calls: ~prefix length
```

If both remain 0 after the second call, the annotation didn't
survive the client-side serialization. Common causes:

- pipecat / openai SDK stripped the unknown `cache_control` field
  during JSON serialization (mitigation: patch the service to
  preserve it, or use `extra_body`)
- LiteLLM version doesn't yet pass through `cache_control` for
  the model alias (mitigation: upgrade LiteLLM or add a
  provider override)
- The system prompt is < 1024 tokens (Anthropic's minimum
  cacheable block size) — cache is a no-op

Add these two fields to each caller's telemetry / token-ledger
hook at the same time as the cache_control annotation. That
makes the rollout self-verifying.

## Cross-drop link

This drop is a fan-out of
`2026-04-14-director-loop-prompt-cache-gap.md` § 6 and
contributes one new top-tier priority entry to the rollup
(`2026-04-14-perf-findings-rollup.md`): **"prompt-cache audit
sweep"** — bundle items #1-#5 above into a single sprint-style
prompt-caching pass. That pass has the same shape as alpha's
existing "watched-path service rebuild" invariant work — it's
a sweep across multiple files with the same pattern, benefiting
from being shipped as one reviewable unit rather than six
individual PRs.

## References

- `2026-04-14-director-loop-prompt-cache-gap.md` (drop 9) —
  the baseline analysis this extends
- `agents/studio_compositor/director_loop.py:592-632` — site 1
- `agents/hapax_daimonion/pipeline.py:94-139, 170-188` — site 2
- `agents/hapax_daimonion/screen_analyzer.py:85-119` — site 3
- `agents/hapax_daimonion/workspace_analyzer.py:123-187` — site 4
- `agents/fortress/deliberation.py:128-162` — site 5
- `agents/dmn/ollama.py` — local, not applicable
- LiteLLM prompt-caching docs (public) — describes cache_control
  passthrough for Anthropic-routed requests
- Anthropic prompt caching rules (public) — 1024-token minimum
  per block, 5-min default TTL, 0.10× cache read cost,
  1.25× cache write cost
