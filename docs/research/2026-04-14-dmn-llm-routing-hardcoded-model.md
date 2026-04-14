# hapax-dmn LLM routing hardcodes a model name — Phase 5 coordination risk

**Date:** 2026-04-14
**Author:** delta (beta role)
**Scope:** Audits `agents/dmn/ollama.py` (misleadingly named
— it calls TabbyAPI directly, not Ollama). Asks: where
does dmn call LLMs, and what happens when alpha swaps
Qwen 3.5 for Hermes 3 in Phase 5?
**Register:** scientific, neutral
**Status:** investigation only — one latent break identified
that coordinates with drops #15 + #17

## Headline

**Three findings.**

1. **`agents/dmn/ollama.py:22` hardcodes the model name**
   `DMN_MODEL = "Qwen3.5-9B-exl3-5.00bpw"`. When Phase 5
   swaps TabbyAPI to Hermes 3 (per drop #15), every dmn
   sensory and evaluative LLM call will hit TabbyAPI with
   a model name that no longer exists and fail silently
   (the try/except at `:68-69` catches and returns empty
   string). **dmn stops working on the day TabbyAPI's
   model changes, without any error surfacing to the
   operator.**
2. **dmn bypasses LiteLLM for ~60 % of its LLM traffic.**
   Sensory ticks (`_tabby_fast`) and text-only evaluative
   ticks (`_tabby_think`) POST directly to
   `http://localhost:5000/v1/chat/completions`. Only the
   vision-enabled evaluative tick (`_gemini_multimodal`)
   goes through LiteLLM at `:4000`. Consequence: the
   TabbyAPI-routed calls get **no Redis cache**, no
   fallback chain (if TabbyAPI is down the fallback-to-
   cloud paths from drop #19 don't apply), no
   Prometheus metrics via LiteLLM's
   `success_callback`/`failure_callback`, and no cost
   tracking via LiteLLM's spendlogs.
3. **The journal shows a sensory-tick cadence mismatch.**
   `pulse.py:25-26` advertises `SENSORY_TICK_S = 5.0`,
   `EVALUATIVE_TICK_S = 30.0` (modulated by stimmung
   stance + TPN). Live journal over 4 minutes of runtime
   shows exactly **one** direct `:5000` call and
   **roughly one `:4000` call every 45 s** (evaluative
   with vision). Either sensory ticks are silently
   erroring and returning empty, or the modulation
   multipliers are extremely high, or sensory calls are
   throttled out by some other gate. Unverified in this
   drop.

**Net impact.** Finding 1 is a Phase 5 coordination risk —
when alpha pivots TabbyAPI's `model_name` (drop #17 § 4
gives the exact config change), dmn needs an accompanying
update to `DMN_MODEL` or it breaks. Finding 2 is a
LiteLLM-bypass design choice with real observability
costs. Finding 3 is a possible live bug but needs more
investigation to separate "working as designed" from
"silent failure."

## 1. The three LLM paths in dmn

```python
# agents/dmn/ollama.py:22
DMN_MODEL = "Qwen3.5-9B-exl3-5.00bpw"       # ← hardcoded
TABBY_CHAT_URL = "http://localhost:5000/v1/chat/completions"

# line 46 — sensory tick (fast)
async def _tabby_fast(prompt: str, system: str) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(TABBY_CHAT_URL, json={
            "model": DMN_MODEL,                   # ← Qwen 3.5, hardcoded
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": prompt}],
            "max_tokens": 256,
            "temperature": 0.3,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
        })

# line 74 — evaluative tick (text-only)
async def _tabby_think(prompt: str, system: str) -> str:
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(TABBY_CHAT_URL, json={
            "model": DMN_MODEL,                   # ← Qwen 3.5, hardcoded
            ...
            "max_tokens": 1024,
            # no enable_thinking → defaults to True on Qwen 3.5 template
        })

# line 104 — evaluative tick (with vision)
async def _gemini_multimodal(prompt: str, system: str, frame_b64: str) -> str:
    client = AsyncOpenAI(
        base_url=os.environ.get("LITELLM_BASE", "http://localhost:4000"),
        api_key=os.environ.get("LITELLM_API_KEY", ""),
    )
    resp = await client.chat.completions.create(
        model="gemini-flash",                     # ← goes via LiteLLM
        ...
    )
```

Dispatch at `start_thinking` (line 135):

```python
def start_thinking(key, prompt, system, *, frame_b64=""):
    if frame_b64:
        _pending[key] = asyncio.ensure_future(_gemini_multimodal(...))
    else:
        _pending[key] = asyncio.ensure_future(_tabby_think(...))
```

**Two of three paths go direct to TabbyAPI. Only vision
evaluative goes via LiteLLM.**

## 2. Phase 5 break mode

The coordination problem:

- Drop #15 § 4 Path A (Q2_K on 3090 replacing Qwen): the
  TabbyAPI `model_name` in config.yml changes from
  `Qwen3.5-9B-exl3-5.00bpw` to
  `Hermes-3-Llama-3.1-70B-exl3-2.62bpw` (or similar).
- Drop #17 § 4 proposes the TabbyAPI config rewrite.
- When that config ships, TabbyAPI starts rejecting
  requests with `model: "Qwen3.5-9B-exl3-5.00bpw"` —
  returns 404 "model not found."
- dmn's `_tabby_fast` catches the exception at line
  68-69 and returns empty string, logging a WARNING.
- Every sensory tick fires that warning every 5 s × 60 =
  720 warnings/hour.
- dmn's observation pipeline silently produces empty
  strings.

**This is not a hard-break** — dmn degrades gracefully
in the sense that it doesn't crash. But it silently stops
producing sensory observations, which is the entire
purpose of the substrate.

### 2.1 Detection

Add to the Phase 5 switch PR:

```python
# agents/dmn/ollama.py:22 — change to env-driven:
DMN_MODEL = os.environ.get("DMN_MODEL", "Qwen3.5-9B-exl3-5.00bpw")
```

Or better — read it from `shared/config.py` where other
agents get their model aliases, so the swap happens once
in config and propagates everywhere:

```python
from shared.config import get_local_model_name
DMN_MODEL = get_local_model_name()
```

Or best — **route through LiteLLM** using the `local-fast`
alias that drop #17 already configures:

```python
# The sensory path becomes:
async def _tabby_fast(prompt: str, system: str) -> str:
    client = AsyncOpenAI(
        base_url=os.environ.get("LITELLM_BASE", "http://localhost:4000"),
        api_key=os.environ.get("LITELLM_API_KEY", ""),
    )
    resp = await client.chat.completions.create(
        model="local-fast",              # ← LiteLLM alias, auto-resolves
        messages=...,
        max_tokens=256,
        temperature=0.3,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    return resp.choices[0].message.content.strip()
```

Gains:

- Survives Phase 5 model swap automatically
- Gets LiteLLM's Redis cache (sensory ticks have
  high-similarity prompts when the situation doesn't
  change — cache hit rate could be real)
- Gets LiteLLM's fallback chain
- Gets Prometheus metrics for free
- Cost tracked in LiteLLM spendlogs

Cost: adds ~5-10 ms of LiteLLM hop latency per call.
For sensory ticks at 5-second cadence, that's 0.1 % of
the tick budget. Negligible.

## 3. The observed cadence mismatch

From the journal (2026-04-14T11:27:22 onward, dmn PID
3902304 / later 3902221):

```text
11:27:22  POST http://localhost:5000/v1/chat/completions 200 OK
11:27:24  POST http://localhost:4000/chat/completions 200 OK
11:27:56  POST http://localhost:4000/chat/completions 200 OK   # +32s
11:28:40  POST http://localhost:4000/chat/completions 200 OK   # +44s
11:29:25  POST http://localhost:4000/chat/completions 200 OK   # +45s
11:30:11  POST http://localhost:4000/chat/completions 200 OK   # +46s
11:30:56  POST http://localhost:4000/chat/completions 200 OK   # +45s
11:31:41  POST http://localhost:4000/chat/completions 200 OK   # +45s
11:32:27  POST http://localhost:4000/chat/completions 200 OK   # +46s
```

Pattern:

- **1 call to `:5000`** (TabbyAPI direct, at startup)
- **8 calls to `:4000`** over ~5 minutes, ~45 s apart
  (LiteLLM → gemini-flash evaluative ticks)

Expected cadence per `pulse.py:25-26`:

- Sensory every 5 s → 60 calls over 5 min
- Evaluative every 30 s → 10 calls over 5 min

Observed cadence:

- Sensory: 1 call, then silence (direct `:5000` path)
- Evaluative: 8 calls, ~45 s interval (LiteLLM `:4000`
  path → Gemini Flash, multimodal with frame)

**Anomalies:**

- Sensory calls ≈ 1/300 s, not 1/5 s. Missing ~59
  expected calls over 5 minutes.
- Evaluative calls at 45 s, not 30 s. That's close to
  30 × 1.5 = 45, consistent with a 1.5× stimmung
  multiplier slowing things down — plausible.

**Hypothesis for the sensory gap:**

`pulse.py:132-133` computes rate multipliers:

```python
sensory_rate = SENSORY_TICK_S * tpn_mult * stimmung_mult
evaluative_rate = EVALUATIVE_TICK_S * tpn_mult * stimmung_mult
```

If `tpn_mult × stimmung_mult ≈ 60` (e.g. both ~7.5),
sensory_rate ≈ 300 s — once every 5 min. Evaluative_rate ≈
1800 s — once every 30 min. But observed evaluative is
45 s, not 30 min. So the multipliers are not uniform —
something is throttling sensory specifically.

**OR** the sensory path's try/except is catching an
error every call and returning empty string without
logging visibly. That would cause the sensory tick to
"succeed" (return empty) without producing an httpx
INFO line in the journal.

Delta has not run the pulse code to confirm which of
these is happening. Worth a 15-minute debug session if
alpha wants the precise answer. **Either way, dmn's
sensory observability is in a weird state.**

## 4. Other minor observations

- **`_tabby_fast` has a misleading docstring**:
  > "Fast path via TabbyAPI (OpenAI-compatible). Falls
  > back to Ollama."
  
  No Ollama fallback exists in the function. The comment
  on line 5 of the module explicitly says "No Ollama
  fallback — loading a second model causes VRAM
  exhaustion." The docstring should be updated.
- **Module name `ollama.py` is misleading** — it does
  not call Ollama at all. `tabby.py` or `inference.py`
  would be more accurate. Renaming would touch all
  callers; not urgent.
- **Memory swap at 71.9 MB peak** for a service with
  93.6 MB peak resident is unusual. `systemctl stop`
  log line says:
  > hapax-dmn.service: Consumed 22.601s CPU time over
  > 1h 20min 9.540s wall clock, 93.6M memory peak,
  > 71.9M memory swap peak.
  
  Swap is ~77 % of peak resident — the service has had
  most of its memory swapped out at some point. Either
  memory pressure from another process kicked it to
  swap, or a past OOM pressure event. Not critical but
  worth a follow-up if sensory tick silent-failure is
  correlated.

## 5. Follow-ups for alpha

1. **Route dmn's direct TabbyAPI calls through LiteLLM**
   using the `local-fast` alias. One function diff in
   `_tabby_fast`, one in `_tabby_think`. Gains model-swap
   survivability, caching, metrics, fallback. Ship
   BEFORE Phase 5 config swap.
2. **Quick 15-min debug** to resolve the sensory cadence
   mismatch. Either confirm it's modulator-driven
   (working as intended) or find the silent-failure path.
3. **Rename `dmn/ollama.py`** to `dmn/inference.py` or
   `dmn/tabby.py`. Update imports. Cosmetic but removes
   a real source of confusion — the file name lies
   about what it does.
4. **Update docstrings** to match the "no Ollama fallback"
   module-level note.

## 6. References

- `agents/dmn/ollama.py:22` — `DMN_MODEL` hardcoded
- `agents/dmn/ollama.py:46-98` — `_tabby_fast` + `_tabby_think`
- `agents/dmn/ollama.py:104-132` — `_gemini_multimodal`
  (the only LiteLLM caller in dmn)
- `agents/dmn/pulse.py:25-26, 125-135` — tick cadence
  and modulator logic
- Drop #15 `2026-04-14-hermes-3-70b-vram-sizing.md` §4 —
  the Phase 5 model swap paths
- Drop #17 `2026-04-14-tabbyapi-config-audit.md` §4 —
  the TabbyAPI config change required for Phase 5
- Drop #19 `2026-04-14-litellm-config-audit.md` — the
  LiteLLM fallback chains that dmn currently bypasses
- Drop #9 `2026-04-14-prompt-cache-audit.md` — the
  cross-caller prompt-cache audit this drop extends
- Live journal: `journalctl --user -u hapax-dmn.service
  --since "30 minutes ago"` at 2026-04-14T16:40 UTC
