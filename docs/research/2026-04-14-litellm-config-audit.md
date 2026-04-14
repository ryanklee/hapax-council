# LiteLLM gateway config audit

**Date:** 2026-04-14
**Author:** delta (beta role)
**Scope:** Reviews `llm-stack/litellm-config.yaml`. LiteLLM is
the gateway every council agent's LLM call routes through.
Complements drop #8 (director_loop cost) and drop #17
(TabbyAPI config). Asks: are there configured limits,
routing choices, or model-version issues that affect
cost/latency/quality across the whole council?
**Register:** scientific, neutral
**Status:** investigation only — five findings, each a
one-line config edit

## Headline

**Five findings.**

1. **Model pins are 8–9 months stale.** The config routes
   `claude-opus` → `anthropic/claude-opus-4-20250514` and
   `claude-sonnet` → `anthropic/claude-sonnet-4-20250514`
   — the May 2025 snapshots of Claude Opus 4 / Sonnet 4.
   As of the current session date (2026-04-14), the latest
   Claude models are **Opus 4.6** (`claude-opus-4-6`) and
   **Sonnet 4.6** (`claude-sonnet-4-6`). Memory
   `feedback_model_routing_patience.md` explicitly says
   the operator wants the best Claude model and is willing
   to wait. The current pins contradict that preference.
2. **`max_parallel_requests: 5` at the global level is a
   hard throttle.** Per-model routes are pinned at 2
   parallel requests each. The global cap of 5 means
   across all concurrent agents (daimonion voice conversation,
   director_loop react loop, imagination tick, fortress
   deliberation, manual probes), **only 5 LLM requests can
   be in flight simultaneously**. The rest queue. Symptoms:
   intermittent high latency, voice reply stutters under
   agent load.
3. **`max_budget: 50, budget_duration: 30d` ≈ $1.67/day cap
   is unrealistic** relative to drop #8's estimate of
   ~$2100/month for director_loop alone. Either the cap is
   not enforced, or director_loop is hitting it and the
   failures are logged but cost-blocked, or the estimate
   is wrong. Needs live verification.
4. **`local-fast`, `coding`, `reasoning` all point to the
   same Qwen 3.5 9B model.** The only difference is
   `extra_body.chat_template_kwargs.enable_thinking`
   (false / false / true). This is fine functionally but
   the three route names suggest three different backends.
   Post-Phase 5, when Hermes 3 arrives, the `reasoning`
   route is the obvious landing site while `local-fast`
   / `coding` stay on Qwen. Worth renaming or consolidating
   for clarity before that swap.
5. **`reasoning` fallback chain is `claude-sonnet → claude-opus
   → gemini-pro`** — three cloud fallbacks for a route
   nominally meant to be local. Any TabbyAPI hiccup
   (model unload, restart, OOM) cascades to cloud bills
   for imagination's entire reasoning tick budget. The
   ALPHA-FINDING-2026-04-13-2 comment explains the rationale
   (without a fallback the P9 watchdog fires on every
   503) but the specific chain choice is cost-exposed.

## 1. Stale model pins

```yaml
# llm-stack/litellm-config.yaml lines 3-19 (abbreviated)
- model_name: claude-opus-4-20250514
  litellm_params:
    model: anthropic/claude-opus-4-20250514

- model_name: claude-opus       # alias
  litellm_params:
    model: anthropic/claude-opus-4-20250514
```

**Same for `claude-sonnet-4-20250514`** at lines 3-7 and
the `claude-sonnet` alias at line 33-37. The `claude-haiku`
alias at line 15 points at `claude-haiku-4-5-20251001` —
that one is the current 4.5 Haiku.

**Current Claude family** (as of this session's system
prompt): Opus 4.6, Sonnet 4.6, Haiku 4.5. The Opus/Sonnet
snapshots in the config are from May 2025 — 9 months stale.

**Why this matters:**

- Per memory `feedback_model_routing_patience.md`: *"CAPABLE
  tier = best Claude model (Opus). Operator always willing
  to wait if indicated and justified. Never downgrade for
  speed."* The May 2025 Opus is not the best Claude model
  anymore.
- Model quality has improved across revisions: Opus 4.6
  is measurably better than Opus 4 on most benchmarks.
- Pricing is often unchanged or lower on newer snapshots
  — Anthropic tends to hold list price constant across
  minor revisions.

**Fix (two lines):**

```yaml
- model_name: claude-opus
  litellm_params:
    model: anthropic/claude-opus-4-6        # was: claude-opus-4-20250514

- model_name: claude-sonnet
  litellm_params:
    model: anthropic/claude-sonnet-4-6      # was: claude-sonnet-4-20250514
```

The full-name aliases `claude-opus-4-20250514` and
`claude-sonnet-4-20250514` can either be removed (nothing
should pin to a specific snapshot for a workstation use
case) or left as explicit historical-pin aliases for
reproducibility.

**Risk of the upgrade:** minor — Anthropic's backward
compatibility on the message API has been stable across
Opus/Sonnet revisions. Callers that depend on specific
tool-call JSON formats should be re-tested.

## 2. `max_parallel_requests: 5` is a hard throttle

```yaml
# litellm_settings at line 116
litellm_settings:
  ...
  max_parallel_requests: 5
```

**Per-model** `max_parallel_requests: 2` applies per model
— 2 concurrent Opus calls, 2 concurrent Sonnet calls, etc.
**Global** `max_parallel_requests: 5` in `litellm_settings`
is the ceiling across all routes.

**Why this is a choke point:**

Concurrent LLM-using agents on this workstation:

- `hapax_daimonion` — voice conversation loop, one call per
  user turn (bursty)
- `studio_compositor.director_loop` — react loop, one call
  every ~90 s (sustained background)
- `hapax_imagination_loop` — imagination tick, one call per
  tick (sustained background)
- `fortress.deliberation` — deliberation (episodic)
- `hapax_daimonion.screen_analyzer` / `workspace_analyzer`
  — vision analyses (operator-driven bursts)
- Any `hapax-mcp` call from a Claude Code session
- Any `pydantic-ai` agent a manual session triggers

**Under sustained load** the 5 slots fill, and additional
requests block on LiteLLM's internal queue. The symptom is
latency spikes that don't correspond to network or model
latency — they're pure queue depth.

**Fix:**

```yaml
litellm_settings:
  ...
  max_parallel_requests: 20    # was 5
```

For a single-operator workstation with ~10 concurrent
agent processes, 20 is a comfortable ceiling. It does
NOT mean 20 concurrent calls to the same model — the
per-model `max_parallel_requests: 2` keeps each upstream
provider from being hammered. It just means LiteLLM
stops queueing requests that are waiting for different
providers.

Anthropic and Gemini both handle dozens of concurrent
requests per API key without issue. The 2/provider cap
is the real rate limiter; the global cap just prevents
the LiteLLM internal request queue from growing.

## 3. Budget cap — live verification needed

```yaml
general_settings:
  ...
  max_budget: 50
  budget_duration: 30d
```

$50 / 30 d ≈ $1.67/day. Drop #8 estimated director_loop
alone at ~$70/day for the Opus route. If the budget cap
is enforced, director_loop hits it within the first 18
hours of the budget window and every subsequent call gets
rate-limited or rejected.

**Two outcomes possible:**

- **The cap is not enforced.** `max_budget` in LiteLLM
  requires the database-backed budget tracking, which
  requires `store_model_in_db: true` (set at line 142)
  AND the `database_url` to resolve. If either is missing
  or misconfigured, the budget is a no-op.
- **The cap is enforced but director_loop's cost is lower
  than drop #8 estimated.** If director_loop is actually
  running closer to 1500 prompt tokens instead of 5000,
  that's 1/3 the cost → ~$23/day → monthly ~$700. Still
  above $50.

**Delta's recommendation: check the LiteLLM dashboard at
`http://127.0.0.1:4000/spend` (or equivalent) and the
Postgres `litellm_spendlogs` table for the current window's
actual spend.** Then pick one of:

- Remove `max_budget` entirely if the cap is a fossil
- Bump to a realistic number (e.g. $500/30d) with a
  ntfy alert at 80 %
- If the cap was deliberate, instrument director_loop
  to report its current spend rate for visibility

## 4. `local-fast`, `coding`, `reasoning` share a backend

```yaml
# lines 57-83
- model_name: local-fast
  litellm_params:
    model: openai/Qwen3.5-9B-exl3-5.00bpw
    extra_body:
      chat_template_kwargs:
        enable_thinking: false

- model_name: coding
  litellm_params:
    model: openai/Qwen3.5-9B-exl3-5.00bpw
    extra_body:
      chat_template_kwargs:
        enable_thinking: false

- model_name: reasoning
  litellm_params:
    model: openai/Qwen3.5-9B-exl3-5.00bpw
    extra_body:
      chat_template_kwargs:
        enable_thinking: true     # only difference
```

Three routes, one model, one bit of difference (thinking
mode on/off). Not a bug — it's how alpha exposes two
behaviors of the same model as three semantically distinct
aliases. But:

- **`local-fast` and `coding` are identical.** They
  differ in name only.
- **Post-Phase 5**, the `reasoning` route is the obvious
  landing site for Hermes 3 (if path A from drop #15 is
  picked). When that happens, `local-fast` and `coding`
  stay on Qwen (or move to Qwen subset), and the three
  routes genuinely diverge.

**Fix consideration for alpha's Phase 5 planning:**

When Hermes 3 lands, decide:

- `reasoning` → Hermes 3 (70B, better classification)
- `coding` → Qwen 3.5 9B (faster, enough for code tasks)
- `local-fast` → Qwen 3.5 9B (alias to `coding`)

Or consolidate to two: `reasoning` + `local`. Simpler, but
existing code paths hard-code the three names and would
need auditing.

## 5. Reasoning fallback chain exposes cloud billing on local hiccups

```yaml
fallbacks:
  ...
  # Closes ALPHA-FINDING-2026-04-13-2
  - reasoning: [claude-sonnet, claude-opus, gemini-pro]
  - local-fast: [gemini-flash, claude-haiku]
  - coding: [claude-sonnet, claude-opus]
```

**The context** (from the inline comment): imagination-loop
uses `reasoning` as its primary path. Without a fallback,
every TabbyAPI 503 (auto-unload, model swap, brief restart)
kills a tick and fires the P9 watchdog. Alpha added the
fallback chain to absorb these hiccups.

**The cost exposure:** `reasoning` → `claude-sonnet →
claude-opus → gemini-pro` is a three-step fallback. If
TabbyAPI is flaky for a sustained period (e.g. during a
model-swap window for Phase 5 testing), every imagination
tick becomes a cloud call. At imagination's typical tick
rate (~one per ~30 s), a 10-minute TabbyAPI outage would
produce 20 cloud calls → ~$5–10 in unplanned Claude spend
if Sonnet; more if it cascades to Opus.

**Fix options:**

- **Accept the current chain** — it closes a real
  reliability issue and the operator has explicitly
  prioritized reliability over cost. Document and move
  on.
- **Replace the Claude fallback with Gemini-only**
  (`reasoning: [gemini-flash, gemini-pro]`) — cheaper per
  call, different model characteristics but still
  acceptable for imagination's use case.
- **Add a circuit breaker** — after N consecutive
  fallbacks within a window, stop auto-falling-back and
  fail loudly until the operator intervenes. Prevents
  runaway cost on a stuck TabbyAPI.

Alpha's choice. Delta's lean is "document and leave" —
the current chain is a deliberate tradeoff and the drop
#18 Hermes 3 ready-check captures the Phase 5 transition
risks more directly.

## 6. Good things in the current config

Noting these so a follow-up "everything's wrong" read
doesn't throw the baby out:

- **`cache: true` with Redis backend** — 1 h TTL, working
  against the `redis` container alpha reads at the same
  hostname. This was the container delta bumped to 2 GiB
  in the CPU audit earlier today. Cache is functional.
- **`drop_params: true, modify_params: true`** —
  LiteLLM silently drops provider-specific params it
  doesn't recognize and auto-adjusts `max_tokens` to
  fit the model's context window. Protects against
  message-shape bugs from callers.
- **`success_callback: ["prometheus"]` +
  `failure_callback: ["prometheus"]`** — per-request
  metrics exported to the same Prometheus the council
  observes. Visibility is in place even if dashboards
  aren't tuned yet.
- **`store_model_in_db: true` + `database_url` from
  Postgres** — per-request spend logs persist across
  restarts. Enables longitudinal cost analysis that
  drop #8's estimate was hand-rolling.

## 7. Follow-ups for alpha

Ordered by severity × ease:

1. **Upgrade Claude pins** to `claude-opus-4-6` and
   `claude-sonnet-4-6`. Two-line change. Aligns with
   operator-preference memory.
2. **Bump `max_parallel_requests` to 20** (or higher).
   One-line change. Unblocks concurrent agent load.
3. **Verify `max_budget` status**. Check
   `litellm_spendlogs` in Postgres + the LiteLLM dashboard.
   Then either remove the cap, raise it, or document the
   enforcement path.
4. **Decide on `local-fast` / `coding` / `reasoning`
   routing** before Phase 5 Hermes 3 lands. Whatever
   the decision, sync it with TabbyAPI's `model_name` and
   with pydantic-ai agent configs.
5. **Document the `reasoning` fallback cost exposure**
   in the unit's design doc. It's a deliberate tradeoff
   alpha should own explicitly.

## 8. References

- `~/llm-stack/litellm-config.yaml` — 145 lines, the whole
  file
- Memory: `feedback_model_routing_patience.md` — operator
  prefers best Claude model
- Drop #8 `2026-04-14-director-loop-prompt-cache-gap.md`
  — director_loop cost estimate
- Drop #15 `2026-04-14-hermes-3-70b-vram-sizing.md` —
  Phase 5 Hermes 3 routing options
- Drop #17 `2026-04-14-tabbyapi-config-audit.md` —
  complementary audit on the backend this gateway routes to
- LiteLLM docs (public): `max_parallel_requests`,
  `max_budget`, fallback syntax, `cache_control` passthrough
- Session system prompt: current Claude family is Opus 4.6,
  Sonnet 4.6, Haiku 4.5
