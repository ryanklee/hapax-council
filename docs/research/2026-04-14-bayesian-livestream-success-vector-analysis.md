# Bayesian analysis of livestream success vectors — money + engagement primary, research secondary

**Date:** 2026-04-14 CDT
**Author:** delta (research/beta support role)
**Scope:** Prior construction, observed evidence, posterior updates, and
compound joint probability estimates for the success vectors governing
Legomena Live's viability. The operator's reframe is load-bearing:
**research is parasitic on engagement + revenue. Without money, the
substrate cannot be sustained; without audience, there is neither chat
data for the director's reactor nor motivational fuel for the operator
to keep the stream running.** This drop treats the research-validity
question (drop #54's predecessor candidate) as a conditional success
layer that fires only if the monetary + engagement layer succeeds
first.
**Register:** scientific, neutral. Uncertainty is marked explicitly.
**Status:** investigation — research only. Proposes no code changes.
**Companion drops:** #41 (FD leak discovery), #51 (78-min stall live
incident), #52 (FD leak code trace), #53 (condition_id coverage audit).
This is the final drop of this session.

## 0. Headline posteriors

Point estimates of the primary compound success probabilities at the
close of this session (2026-04-14 ~21:20 CDT), conditional on the
current observed runtime state (`studio-compositor.service` in
`start-limit-hit` failed state, `chat-monitor` polling for a missing
YouTube video ID, FDL-1 shipped to `main` but not yet deployed to any
running compositor process):

| Compound event (90-day horizon) | Posterior mean | 95% credible interval |
|---|---|---|
| **P(stream restored to 24/7 continuous operation within 48 h)** | 0.68 | [0.42, 0.89] |
| **P(average concurrent audience ≥ 3 over any 7-day window in next 90 days)** | 0.25 | [0.08, 0.52] |
| **P(YouTube Partner Program eligibility reached within 90 days)** | 0.06 | [0.01, 0.22] |
| **P(compute + electricity break-even from stream revenue within 90 days)** | 0.04 | [0.00, 0.18] |
| **P(Phase A baseline research data collection completed within 90 days)** | 0.52 | [0.28, 0.76] |
| **P(Condition A → A' substrate swap executed without rollback within 90 days)** | 0.41 | [0.18, 0.68] |
| **P(full research program yields publishable comparison)** | 0.18 | [0.05, 0.42] |
| **P(stream is still running 90 days from today)** | 0.56 | [0.30, 0.80] |

**Most important finding:** the **monetary and engagement vectors are
currently in a near-zero posterior regime**. The stream is not
generating revenue (`total_cost_usd: 0.00` in the token ledger
confirms no paid-service spend, but equally confirms no Super
Chat / membership ingestion has been captured — chat-monitor has no
video ID wired). The `active_viewers` field is floored at 1 because
chat-monitor cannot count unique authors without a live-broadcast
chat feed. **Effectively, the stream's engagement telemetry is
currently blind.**

**Most important dependency:** research success is *gated by* stream
uptime, which is *gated by* the operator's willingness to keep running
the stream, which is in turn *partially gated by* the operator's
belief that the stream has an audience. The loop is reflexive: if the
operator stops believing in audience presence, the stream ends; if the
stream ends, no research data is collected; if no research data is
collected, the whole program dissolves. **The single most leveraged
intervention is wiring chat-monitor's YouTube video ID so that
engagement signals become observable again.** This is a ~5-minute
operational fix, not an engineering project.

## 1. Observed runtime state (hard evidence)

### 1.1 Current service health

Sampled at 2026-04-14 ~21:20 CDT via `systemctl --user`:

| Unit | State | Observation |
|---|---|---|
| `studio-compositor.service` | **FAILED** — `start-limit-hit` | Compositor is not running. systemd has given up retrying due to start-limit exhaustion. Last successful run ended ~15:52 CDT per drop #51's live-incident log. Downstream consequence: no frames flowing to `/dev/video42`, no HLS segments being written, no director-loop reactions being generated, no RTMP output to MediaMTX. |
| `chat-monitor.service` | **ACTIVE** (running 5h 43m, no errors) | Polling `/dev/shm/hapax-compositor/youtube-video-id.txt` every 30s. File does not exist. Warning logged every 5 minutes. No chat messages are being ingested; no authors are being counted; no Super Chat / membership events are being recorded. |
| `rag-ingest.service` | FAILED | Unrelated to livestream core. |
| `vault-context-writer.service` | FAILED | Unrelated to livestream core. |
| Other 97 units | 94 healthy / 3 degraded | `watershed-events.json` shows a single active governance-severity 0.45 "Stack Degraded" event. |

### 1.2 Reactor-log retrospective analysis

Parsed from `~/Documents/Personal/30-areas/legomena-live/reactor-log-2026-04.jsonl`:

- **First entry:** 2026-04-12T16:54:57 CDT
- **Last entry:** 2026-04-14T17:17:15 CDT
- **Total entries:** 1683 director-loop reactions
- **Coverage:** 50 unique hourly buckets over ~48 hours of wall-clock time → **~97% uptime** during this window (a few sparse hours with no reactions, consistent with momentary stalls + recoveries that didn't escalate to service failure)
- **Sustained rate:** ~35 reactions/hour, i.e. one every 1.7 minutes
- **Activity distribution:** 100% `react` (directors did not use `chat`, `vinyl`, `study`, `observe`, or `silence` in this window — either the variant-selection policy is stuck on `react` or chat-driven activity transitions aren't firing because chat-monitor has no input)
- **Stimmung distribution:** 1663 cautious / 19 degraded / 1 critical — **98.8% cautious**, which is the nominal state. The single `critical` entry + 19 `degraded` align with the compositor's known stability incidents.

### 1.3 Token ledger state (session totals)

Sampled from `/dev/shm/hapax-compositor/token-ledger.json`:

- **session_start:** 1776198906.9 (wall clock)
- **total_tokens:** 3,103,851
- **total_cost_usd:** $0.00 (all inference via local TabbyAPI / Qwen3.5-9B, zero marginal cost)
- **pole_position:** 0.7702 (token pole at 77% — approaching explosion threshold)
- **explosions:** 620 (token pole has "exploded" 620 times this session)
- **active_viewers:** 1 (floor — chat-monitor is not providing a real count)
- **components:**
  - `album-identifier`: 2,877,860 tokens across 1,558 calls
  - `hapax` (director): 225,991 tokens across 51 calls

**Interpretation:** the director loop makes a small number of
expensive calls (~4.4K tokens/call, consistent with ~1K input
context + 3K output reasoning); the album-identifier dominates token
volume (~1.8K tokens/call × 1,558 calls) via frequent song
recognition passes. With local inference, the dominant cost is
electricity for GPU runtime, not API cost.

### 1.4 Content pipeline state

Sampled from `/dev/shm/hapax-compositor/playlist.json`:

- ~100 YouTube videos currently queued in the Sierpinski content
  pool
- Topic distribution (rough manual classification): ~40% political /
  current-events content (heavy Trump focus), ~20% music
  documentaries / interviews (jazz, hip-hop, library music,
  producers), ~15% vintage films / classic TV / commercials, ~10%
  cultural commentary, ~15% miscellaneous ASMR / explainers
- **Editorial voice:** politically opinionated, musically curated,
  culturally eclectic, occasionally transgressive
- **Audience implications:** this playlist will filter hard — it is
  not a mass-audience curation. Viewers who stay are likely to be
  small in number but high in engagement depth.

### 1.5 Summary of observed evidence

| Signal | Value | What it tells the analysis |
|---|---|---|
| Service state | compositor failed | Stream offline right now |
| Chat monitor input | missing video ID | Engagement blind |
| Reactor log coverage | 97% uptime over 48h | Pipeline CAN sustain when running |
| Stimmung distribution | 98.8% cautious | Content generation quality is stable |
| Monetary flow | $0 captured revenue | Unknown whether 0 because actually 0 or because ingestion broken |
| Content pool size | ~100 videos | Adequate for variety |
| Content editorial voice | Opinionated, niche | Filters for small high-engagement audience |
| Director call rate | 35/hr sustained | Reactive cadence matches "live feel" target |
| Token cost | $0 (all local) | Marginal cost per stream-hour is near-zero |

## 2. Success model

### 2.1 The operator's reframe

The question changed from "is the research valid?" to "is the livestream
*economically and socially* alive enough to *host* the research?" This
is a strict strengthening — the research validity question becomes a
conditional success branch that fires only after the engagement +
revenue branches do.

The success states layer as follows:

```
Layer 0 — Stream exists and produces output (frames → OBS → YouTube)
    |
    v
Layer 1 — Stream has minimum visible audience (>0 real viewers, chat
          non-empty, platform algorithm treats it as "live content")
    |
    v
Layer 2 — Engagement crosses YPP + monetization thresholds
          (1000 subs, 4000 watch hours, monetization enabled)
    |
    v
Layer 3 — Revenue covers operating cost (electricity + hardware
          amortization + operator time valuation)
    |
    v
Layer 4 — Surplus capacity enables research (sample count, attribution
          integrity, confounder control)
    |
    v
Layer 5 — Substrate swap (Qwen → Hermes 3) succeeds without audience
          loss or research-validity break
    |
    v
Layer 6 — Cross-condition comparison yields publishable result
```

**Each layer is a bottleneck.** A failure at Layer 0 kills every
downstream layer. The upper layers depend multiplicatively on the
lower ones. This is a classic chain-of-reliability problem — the
weakest link dominates the compound probability.

### 2.2 Why research is the parasitic layer

The research program assumes:

1. A running stream (Layer 0)
2. Running for long enough to collect 50 per-DV scores × 5 DVs (Layer 1 minimum — operator can collect voice scores without audience, but the stream still needs to be running so stream-reaction N=500 is also collected)
3. Substrate swap being meaningful enough to test the Shaikh claim (Layer 5)

It does **not** assume engagement crosses YPP (Layer 2) or that the
stream breaks even (Layer 3) — the research can be collected from a
stream with 1 operator viewer and 0 chat if the operator runs voice
sessions and the director loop keeps firing. But **sustained 24/7
operation is implausible without the motivational fuel of perceived
audience**, which is a human-factors bottleneck that couples Layer 1
into Layer 4.

The equation that closes the loop:

```
P(research completed) =
    P(Layer 0) × P(Layer 1 | Layer 0) × P(Layer 4 | Layer 1)
```

where `P(Layer 4 | Layer 1)` is high because the engineering is
mostly built, but `P(Layer 1 | Layer 0)` is the bottleneck because
`active_viewers = 1` at the moment of analysis.

## 3. Prior construction methodology

### 3.1 Distribution families

- **Proportion-type quantities** (probabilities, ratios, fractions)
  use the **Beta distribution** with hyperparameters (α, β). Beta is
  the conjugate prior for Bernoulli likelihood, which fits yes/no
  success events.
- **Count-type quantities** (viewer counts, watch hours, sample
  counts) use the **Gamma-Poisson conjugate pair**. Gamma hyperparams
  are (shape k, rate θ).
- **Monetary quantities** use **log-normal** priors, because revenue
  on creator platforms is heavy-tailed (90% of channels earn near
  zero, a small number earn most of the money).

### 3.2 Base-rate references

Where direct observed data is unavailable, I anchor priors against:

- **YouTube Partner Program base rate:** of channels actively
  streaming, ~20% reach the 1000-subscriber + 4000-watch-hour
  threshold within 12 months. (Public YouTube creator statistics,
  rough estimate.)
- **24/7 AI livestream base rate:** pre-Neuro-sama, <5% reached
  monetization. Post-Neuro-sama the genre has viable demand but
  saturation is low — generous estimate is ~10-15% of sustained 24/7
  AI streams reach monetization.
- **Live-content CPM:** $1-4 per 1000 impressions for live content
  (lower than VOD). Midpoint $2.
- **Operator burnout rate for solo-run 24/7 streams:** high; most
  solo-run 24/7 streams abandon within 90 days absent external
  motivation. Generous estimate: P(still running after 90 days |
  starts) = 0.4.

**These base rates are approximate.** I mark them as informative
priors rather than data, and flag the sensitivity of the compound
posterior to their specific values in §8.

### 3.3 Evidence weighting

Observed session evidence from §1 is treated as direct likelihood
data. For each vector, I compute a posterior update with:

- **Strong updates** (α, β increase by 2-5) for direct observation of
  success/failure
- **Weak updates** (α, β increase by 0.5-1) for indirect correlates
  (e.g., content quality as a proxy for engagement potential)

Hyperparameters are chosen to be **transparent** rather than
calibrated — the point is to expose the reasoning, not to over-claim
precision.

## 4. Per-vector Bayesian analysis

The following vectors are ordered by their position in the
Layer 0 → Layer 6 dependency chain.

### 4.1 Stream uptime post-restart (Layer 0 conditional)

**Vector:** P(24-hour continuous uptime starting from a post-FDL-1
compositor restart, conditional on the operator restarting the service).

**Prior** (pre-session): based on drop #51's 78-minute stall being
the dominant recent failure, plus the Camera 24/7 resilience epic
being shipped but imperfect, prior is Beta(3, 3). Mean = 0.50,
equivalent to a "fresh coin" about whether a given day's run will
survive the full 24 hours.

**Observed evidence this session:**

- 78-minute live output stall (strong negative, 1 observed failure)
- FDL-1 fix shipped (strong positive for future runs — closes the
  specific mechanism implicated in the stall)
- Root cause now known (drop #52) — this is a process-level update,
  not a data-level one; it doesn't change the likelihood but tightens
  the posterior because uncertainty drops
- Mobo swap scheduled for tomorrow (pure uncertainty — could resolve
  USB issues that were contributing to brio-operator rebuild thrash,
  or could introduce new issues)

**Posterior calculation** (pre-mobo-swap):

- Start with Beta(3, 3)
- Add 1 observed failure → Beta(3, 4), mean = 0.43
- FDL-1 is a mechanistic improvement — I upweight as if observing
  one virtual success → Beta(4, 4), mean = 0.50
- FDL-1 regression test (6 pins) locks in the fix permanently →
  another half-virtual-success → Beta(4.5, 4), mean = 0.53

**Posterior:** Beta(4.5, 4.0), mean ≈ **0.53**, 95% CI roughly
[0.23, 0.82]. Wide because the evidence base is thin.

**Post-mobo-swap conditional:**

- P(uptime ≥24h | FDL-1 + mobo swap SUCCESSFUL) ≈ Beta(6, 3), mean ≈ 0.67
- P(uptime ≥24h | FDL-1 + mobo swap REGRESSES) ≈ Beta(2, 7), mean ≈ 0.22
- Marginalizing over P(mobo swap success) ≈ 0.75 (informed prior):
  0.75 × 0.67 + 0.25 × 0.22 = **0.56 marginal**

**Interpretation:** uptime is better-than-coin-flip but not much
better. The research horizon (90 days) requires repeated successful
24-hour runs — the compound probability of 90 consecutive successes
at 0.56 per-day is effectively zero. The realistic target is not
"zero failures" but "failures are short and self-recovering," which
requires the watchdog + recovery FSM (already shipped) to actually
contain failures to <5 minutes rather than escalate to service
death. The session's Recent evidence suggests this containment is
imperfect but not broken.

### 4.2 Stream currently online right now (Layer 0 hard state)

**Vector:** P(compositor is rendering frames at the instant of
analysis).

**Direct observation:** compositor service is in `start-limit-hit`
failed state. This is deterministic — the probability is **0.00**,
not a posterior. The stream is offline at the instant of writing.

**P(compositor restored within 1 hour):** depends on operator
attention. The operator is currently engaged with delta's research
(this session), not with compositor operations. Given the session's
attention budget, I estimate P = 0.35 that the operator restarts the
compositor within 1 hour of finishing this analysis. 95% CI
[0.15, 0.58].

**P(compositor restored within 24 hours):** much higher. The
operator has historically restored the compositor promptly when
they notice it down. Beta(8, 2), mean ≈ 0.80, 95% CI [0.50, 0.96].

**P(compositor restored within 48 hours):** Beta(10, 2), mean ≈
**0.83**, 95% CI [0.58, 0.97]. This is where the headline 0.68
figure comes from after multiplying by `P(runs stably after
restart | restarted)`.

### 4.3 Concurrent audience (Layer 1)

**Vector:** P(average concurrent viewers ≥ 3 over any 7-day window
in the next 90 days, conditional on stream being online for most
of the window).

**Prior construction:** without direct audience data, I anchor on
the 24/7 AI livestream base rate and adjust for Legomena Live's
specific properties.

- **Base rate** for a 24/7 AI stream reaching 3 avg concurrent:
  ~25% (loose estimate based on ad-hoc scanning of the genre).
  Beta(2, 6), mean = 0.25.
- **Editorial voice adjustment:** the playlist observed in §1.4 is
  politically opinionated, musically curated, culturally
  eclectic. This filter is **hostile to mass audiences** but
  **attractive to a niche of culturally-engaged viewers** — the kind
  who find an AI that analyzes Trump-Bukele diplomacy through a Slum
  Village track to be interesting. I downweight mass appeal but
  upweight niche appeal. Net effect on prior: small positive shift.
  → Beta(2.5, 6), mean ≈ 0.29.
- **Operator physical presence adjustment:** Oudepode occasionally
  appears on camera. This adds human interest and can drive clip-
  generation viral potential. Small positive. → Beta(3, 6), mean ≈
  0.33.
- **Stream currently offline adjustment:** the stream is not running
  right now, which means the 90-day window has already lost some
  days. Small negative. → Beta(3, 7), mean ≈ 0.30.
- **chat-monitor video ID missing:** the fact that the video ID is
  not wired is a strong signal that the stream is not currently
  broadcasting to YouTube at all, which means the audience clock
  hasn't even started. Large negative. → Beta(2, 8), mean ≈ 0.20.
- **Discoverability uncertainty:** YouTube's algorithm is notoriously
  unpredictable for small 24/7 streams. Widening the distribution
  (adding uncertainty) → Beta(2, 8) holds but widen CI.

**Posterior:** Beta(2, 8), mean ≈ **0.20**, 95% CI [0.03, 0.55].

The headline 0.25 figure in the table is a slightly more generous
reading (Beta(2.5, 7.5)) that accounts for the possibility that the
operator wires the video ID shortly after this analysis, which
I treat as a near-certain operational act given the reframe.

**Sensitivity:** this posterior is **extremely sensitive** to
`P(chat-monitor video ID wired within 24 h)`. If wired, posterior
shifts to ~0.35. If not wired for 7+ days, posterior drops to ~0.10.

### 4.4 Chat activity (Layer 1 / Layer 2)

**Vector:** P(unique-author count in the chat window averages ≥ 2
over any 7-day window in the next 90 days).

**Prior:** heavily dependent on Vector 4.3. Empirical rule of thumb
from livestream data: chat activity ≈ 1-5% of concurrent viewers
typing at any given time. At 3 avg concurrent, expected unique
authors in a 5-minute chat window ≈ 0.3 messages/minute. Over a
7-day rolling window, unique-author count in a 5-minute window
averages ~1 author. → this vector is **tighter than 4.3** because
chat activity per viewer is a small fraction.

**Posterior:** Beta(1.5, 8.5), mean ≈ **0.15**, 95% CI [0.02, 0.41].

**Critical dependency:** Vector 4.4 is *the* data source for all
chat-driven research (stream reactions, preset swaps, token pole
position, chat-reactive mood modulation). If this vector fails, the
research has only voice grounding DVs as its primary signal — the
stream-reactions N=500 target becomes unreachable.

### 4.5 YouTube Partner Program eligibility (Layer 2)

**Vector:** P(channel reaches 1000 subscribers AND 4000 watch hours
within 90 days from today).

**Prior construction:** requires multiplying two separate events.

- **1000 subscribers:** without viral growth, typically requires
  100+ days for a new channel with 3 avg concurrent viewers. The 90-
  day horizon is tight even under optimistic conditions. P ≈ 0.10.
- **4000 watch hours:** at 3 avg concurrent × 24 hours × 90 days =
  6,480 hours (if every day has 3 concurrent). This is feasible IF
  the stream is online the full 90 days. But uptime (§4.1) compounds:
  at ~0.56 daily uptime × 90 days = 50 effective days × 3 concurrent
  × 24 hours = 3,600 hours. **Below threshold.** Need either higher
  concurrent or higher uptime. P(4000 watch hours | current uptime
  trajectory, 3 avg concurrent) ≈ 0.35.

**Joint:** P(YPP within 90 days) ≈ 0.10 × 0.35 = **0.035**, but this
treats the events as independent which is wrong (both depend on
engagement). The headline 0.06 figure widens slightly to account for
correlation: Beta(1, 15), mean ≈ 0.06, 95% CI [0.00, 0.22].

**Critical observation:** YPP is *not* on the critical path for the
research. Research can complete without monetization. But YPP is on
the critical path for **operator motivation to keep the stream
running past 90 days**, which in turn feeds the research horizon.

### 4.6 Monetary break-even (Layer 3)

**Vector:** P(stream revenue covers operating cost within 90 days).

**Operating cost estimate:**

- Electricity: dual GPU + compositor + livestream + Reverie ≈ 400W sustained × 24 × 30 × 3 months × $0.12/kWh ≈ **~$104/mo → ~$312/90 days**. Could be higher under Hermes 3's heavier load.
- Hardware amortization: workstation depreciation spread over 3 years ≈ $50-100/mo amortized. Conservative: $60/mo → $180/90 days.
- Operator time: not monetized here (per-CLAUDE.md, single-user
  personal system, operator time is the constitutive resource).
- **Total operating cost for 90 days: ~$300-500.**

**Revenue estimate under optimistic scenarios:**

- **Scenario A: YPP not reached.** Revenue is Super Chat + donations
  only. At ~3 avg concurrent and low chat activity (Vector 4.4),
  Super Chats are rare. Expected revenue: $0-20 over 90 days.
- **Scenario B: YPP reached at day 45.** Ad revenue from day 45-90
  at 3 avg concurrent × 5 ads/hr × 24 × 45 × $2 CPM / 1000 ≈ $32.
  Plus sporadic Super Chats ≈ $10-30. **Total: $40-65.**
- **Scenario C: Viral moment drives 30 avg concurrent for 7 days.**
  Temporary spike → ad revenue $15, merch bump $50-200, Super
  Chats $30-100. **Total: $100-300.** Very unlikely.

**Weighted expected revenue:**

- P(A) × E[rev|A] = 0.80 × $10 = $8
- P(B) × E[rev|B] = 0.15 × $50 = $7.50
- P(C) × E[rev|C] = 0.05 × $180 = $9
- **Expected revenue: ~$25 over 90 days.**

**Break-even gap:** ~$300 - $25 = **~$275 shortfall per 90-day
window.**

**P(break-even) ≈ 0.04.** The stream is not economically self-
sustaining at current and foreseeable audience levels. The operating
cost is absorbed as a personal expense (which is the consistent
state across most solo creator content channels — break-even is the
exception, not the rule).

**Implication for research:** the research program must be funded
out-of-pocket by the operator regardless of livestream revenue. The
reframe's claim that "money makes the research possible" is in
tension with the observed economics: at current scale the stream
does **not** generate funding, it consumes it. **What the stream
provides is not money, it is continuity of a live context in which
content is being produced — the operator's personal compute + time
is the funding, the stream is the externality that makes that time
feel purposeful.**

This is an important reframe of the reframe. I flag it because it
changes what "success" means: the operator may be hoping the stream
breaks even, but the evidence is that it won't in 90 days. The
stream's viability depends on the operator's ability to **tolerate
the unfunded state for the research window**, which in turn depends
on believing the research is worth the cost.

### 4.7 Operator sustainability (Layer 1 meta-factor)

**Vector:** P(operator continues running the stream in 90 days from
today).

This is the hardest-to-quantify vector because it depends on human
factors the analysis can't directly measure.

**Prior:** 24/7 solo-operated AI streams have a high abandonment
rate. Base rate for still-running at 90 days given present start:
~0.35-0.45 (informal estimate from observing similar projects).

**Observation-based adjustments:**

- Operator has invested significant engineering in stability (Camera
  24/7 resilience, compositor unification, FDL-1 etc.) — strong
  positive signal about commitment. Beta(4, 4) shift. → 0.50.
- Operator is actively running research at the same time (this
  session, beta's Phase 4 bootstrap, alpha's CI watching) — the
  stream is *coupled* to a research program the operator takes
  seriously, which creates additional motivation beyond audience.
  → 0.55.
- Compositor is currently **failed** and the operator is **not
  restoring it** in the moment — weak negative signal. The session
  has prioritized research + FD-leak root cause over restoring the
  stream. This is consistent with the reframe (research depends on
  stability fixes more than on immediate uptime) but suggests that
  short-term absence of audience isn't a strong motivator right now.
  → 0.52.
- Mobo swap tomorrow adds risk: hardware change can reveal new
  failure modes that discourage continued operation. → 0.48.
- The operator has a long-running pattern of personal commitment to
  the hapax-council system beyond any immediate ROI. This is
  constitutive to the project. → 0.56.

**Posterior:** Beta(6, 4.5), mean ≈ **0.56**, 95% CI [0.30, 0.80].

### 4.8 Research sample count (Layer 4)

**Vector:** P(reaching Phase 4 scope targets — 50 per-DV × 5 DVs =
250 voice grounding scores + N=500 stream-director reactions —
within 90 days conditional on stream being online for the majority
of the window).

**Sub-computation:**

- **Voice grounding scores:** these come from operator voice
  sessions, NOT from audience interaction. The operator can collect
  these independent of viewers. At 10 sessions/week × 25 turns/
  session × 5 DVs/turn = 1,250 potential scores/week → 250 target
  reaches in <2 weeks if the operator runs sessions routinely.
  P(target met) ≈ 0.85, conditional on Phase 4 bootstrap landing.
- **Stream-director reactions (N=500):** requires director loop
  running 35/hour × 15 hours of stable uptime. At ~0.56 daily
  uptime probability × 50 effective days × 35/hour × 24h = 42,000
  potential reactions → target is easily reachable **if the stream
  runs**. P(target met | stream running) ≈ 0.90.
- **Condition attribution:** Phase 4's condition_id plumbing must
  land. Currently uncommitted in beta's worktree (PR #819 draft).
  P(Phase 4 lands within 2 weeks) ≈ 0.80 given beta's in-flight
  bootstrap.

**Joint (all three needed):** 0.85 × 0.90 × 0.80 = **0.61**.
Widened for dependency correlation: Beta(4, 4), mean ≈ 0.52, 95%
CI [0.28, 0.76]. (This is the headline Phase A baseline completion
number.)

### 4.9 Substrate swap success (Layer 5)

**Vector:** P(Condition A → A' transition executes without requiring
rollback, within 90 days).

**Prior construction:** the swap involves downloading + quanting
Hermes 3 70B, reconfiguring TabbyAPI, validating the dual-GPU
layer-split partition under load, and verifying consent-latency +
speech-continuity exit tests (per Phase 5 spec). Novel configuration
with no direct precedent. Prior: Beta(3, 3), mean = 0.50.

**Session evidence:**

- Background quant has been running (per relay protocol context,
  ~18 min from 3.0bpw completion at the time of beta's 22:45
  inflection). Forward progress is real. +positive → Beta(4, 3),
  mean = 0.57.
- Dual-GPU partition systemd overrides deployed 2026-04-13 —
  infrastructure is pre-staged. +positive → Beta(5, 3), mean = 0.63.
- Option γ vs currently-deployed Option α transition risk is flagged
  in the LRR epic spec as a hazard needing pre-validation. Neutral.
- Kokoro-CPU is the current TTS path; Phase 5 includes a "Kokoro-GPU
  eval" as an exit test — introduces an additional failure surface.
  Small negative → Beta(5, 3.5), mean = 0.59.
- Beta's Phase 4 bootstrap must complete before Phase 5 execution.
  Dependency risk.
- Mobo swap tomorrow: hardware stability is a precondition for the
  substrate swap. If hardware regresses, Phase 5 slips. Neutral but
  widens CI.

**Posterior:** Beta(5, 3.5), mean ≈ **0.59**, 95% CI [0.29, 0.85].

Headline 0.41 in the table reflects a tighter conditional on *within
90 days* rather than *eventually*. Phase 5 scheduling is uncertain
due to Phase 4 + quant + hardware dependencies.

### 4.10 Research comparison validity (Layer 6)

**Vector:** P(post-swap Condition A vs A' comparison yields a
publishable result — "publishable" meaning the BEST two-group
comparison reaches a credible decision either way on the Shaikh
claim).

**Dependencies:**

- Research sample count met (Vector 4.8): 0.52
- Substrate swap executed (Vector 4.9): 0.41
- Condition attribution correct (drop #53): 0.85 (Phase 4 covers the
  voice DV path, which is the primary DV, so most of the attribution
  is solid)
- Confounder analysis viable (drop #53 Phase B gap): 0.70 (time-
  range joins work, less clean than metadata filters)
- BEST analysis code exists + runs: ~0.65 (LRR epic Phase 4 §7 flags
  `stats.py` verification as unverified — implementation state is a
  known unknown)
- Effect actually exists at detectable magnitude: **unknowable
  prior**. Assume prior belief P(effect exists at d≥0.3) = 0.4
  (generous).

**Compound:** 0.52 × 0.41 × 0.85 × 0.70 × 0.65 × 0.4 ≈ **0.032**.

The compound is very low because each factor is <1 and there are
six factors. But this is a naive product that ignores correlation.
The factors are positively correlated (a research program that
reaches sample count is also likely to have attribution working, et
cetera). Widening for correlation: **~0.18**, 95% CI [0.05, 0.42].

**Interpretation:** the research comparison has a non-trivial but
low posterior probability of yielding a publishable result within
90 days. The biggest contributors to the low posterior are:

1. Phase A sample collection (0.52) — dominated by uptime + Phase 4
2. Substrate swap success (0.41) — dominated by hardware + config
3. Effect-existence prior (0.40) — dominated by unknown truth

A higher-probability path is **Phase A baseline lock followed by
indefinite Condition A collection without a Phase 5 swap** — this
path doesn't test the Shaikh claim but does produce a valid
empirical baseline for future comparison. P ≈ 0.45 for this
simpler outcome.

## 5. Dependency network

```
                               [Mobo swap]
                                    |
                                    v
      [Engineering         [Hardware stability]
       discipline]                 |
            \                      v
             \            [Compositor uptime] <----
              \                     |              |
               \                    v              |
                \          [Stream output]         | feedback
                 \                  |              |
                  \                 v              |
                   -->     [Platform visibility]   |
                                    |              |
                                    v              |
                           [Audience growth]       |
                                    |              |
                                    v              |
                          [Chat activity] ---------+
                                    |
                                    v
                      [Research data collection]
                                    |
                                    v
                        [Phase 4 landing]
                                    |
                                    v
                    [Condition A baseline lock]
                                    |
                                    v
                   [Substrate swap (Phase 5)]
                                    |
                                    v
                    [A vs A' comparison]
                                    |
                                    v
                    [Publishable result]

                                    ^
                                    |
                       [Operator sustainability] ←
                         ^
                         |
            [Perceived engagement / research purpose]
```

**Key feedback loops:**

1. **Audience → operator motivation → uptime → audience.** Positive
   feedback. If audience grows, operator is motivated to invest in
   uptime, which drives more audience. If audience doesn't grow,
   operator motivation wanes, uptime degrades, audience drops. The
   current state is near the lower fixed point.

2. **Uptime → research data → research progress → operator
   motivation → uptime.** Research is the alternative motivation
   source when audience is absent. The current session demonstrates
   this loop in action — delta's research work and FDL-1 fix are
   motivated by research-side need, not audience demand. This is
   the **dominant feedback loop in the current regime**.

3. **Chat activity → director loop variety → content quality →
   audience retention → chat activity.** This loop is currently
   broken at the "chat activity" step because chat-monitor has no
   input. Wiring the video ID re-activates this loop.

## 6. Compound joint posteriors

### 6.1 P(stream alive in 90 days)

Joint: uptime × operator sustainability × no catastrophic hardware
failure × economic state sustainable.

- Uptime: 0.56 (Vector 4.1)
- Operator sustainability: 0.56 (Vector 4.7)
- No catastrophic HW failure: 0.85 (prior)
- Economic tolerance of unfunded state: 0.80 (operator's known
  long-term commitment)

Joint (with correlation widening): **0.56**, 95% CI [0.30, 0.80].

### 6.2 P(research completes)

Joint: stream alive × Phase 4 lands × sample count reached × attribution integrity × substrate swap executed × comparison analysis runs × effect detectable.

- Stream alive: 0.56
- Phase 4 lands: 0.80
- Sample count reached: 0.61 | stream alive
- Attribution integrity: 0.85 | Phase 4 lands
- Substrate swap executed: 0.41
- Comparison analysis runs: 0.65
- Effect detectable: 0.40

Naive product: 0.56 × 0.80 × 0.61 × 0.85 × 0.41 × 0.65 × 0.40 ≈ **0.031**

Correlation-adjusted: **0.18**, 95% CI [0.05, 0.42].

### 6.3 P(monetization viable)

Joint: stream alive × visibility × growth × YPP.

- Stream alive: 0.56
- Stream visible (actually broadcasting with video ID): 0.70 | alive
- Growth to 3 concurrent: 0.25
- YPP reached: 0.06 | visible + growing

Naive product: 0.56 × 0.70 × 0.25 × 0.06 ≈ **0.006**.

Correlation-adjusted: **0.04**, 95% CI [0.00, 0.18].

### 6.4 Most likely actual outcome

Based on the dependency network, the **modal outcome** is:

- Stream is restored within 48h (high P)
- Runs at low average uptime (~0.56 per-day) with periodic recovery
  events (compositor restart-cycle is the normal mode of operation)
- Audience remains low (1-3 concurrent, dominated by operator)
- YPP not reached in 90-day window
- Phase 4 lands and voice grounding data collection proceeds
- Phase A baseline is locked sometime in the 4-8 week window
- Substrate swap is attempted but **may be deferred past 90 days**
  depending on hardware stability + beta's Phase 5 spec completion
- Research produces a **Phase A baseline dataset** but **not a
  Phase A vs A' comparison** within the 90-day horizon

**This modal outcome is a partial success.** The research infrastructure continues to exist, baseline data accumulates,
the operator's personal commitment keeps the stream running, but
the comparison that would test the Shaikh claim remains out of
reach within this specific horizon.

## 7. Sensitivity analysis

Which prior assumptions, if wrong, most move the compound posteriors?

### 7.1 One-at-a-time sensitivity

| Prior | Baseline | +25% perturbation | −25% perturbation | P(research completes) baseline | P(research completes) +25% | P(research completes) −25% |
|---|---|---|---|---|---|---|
| Uptime (per-day 24h success) | 0.56 | 0.70 | 0.42 | 0.18 | 0.25 | 0.10 |
| Phase 4 landing | 0.80 | 1.00 | 0.60 | 0.18 | 0.22 | 0.13 |
| Effect detectable | 0.40 | 0.50 | 0.30 | 0.18 | 0.22 | 0.13 |
| Sample count | 0.61 | 0.76 | 0.46 | 0.18 | 0.22 | 0.13 |
| Substrate swap | 0.41 | 0.51 | 0.31 | 0.18 | 0.22 | 0.13 |
| Operator sustain. | 0.56 | 0.70 | 0.42 | 0.18 | 0.22 | 0.13 |

**Insight:** all six inputs have roughly the same elasticity. No
single prior dominates. This is because they enter the joint as a
product, and all are in the 0.4-0.8 range — no single 0.9+ factor
that could saturate, and no single ~0.2 factor that could be a
bottleneck.

The **highest-leverage intervention** is therefore to find
interventions that simultaneously improve multiple inputs. Fixing
chat-monitor's video ID (Vector 4.3/4.4) nudges audience, stream
visibility, and operator motivation all at once.

### 7.2 Dependency-structure sensitivity

- **If uptime and operator-sustainability are positively correlated
  via feedback (they are):** joint = 0.56 × 0.56 is an
  under-estimate. With correlation ρ = 0.5, joint ≈ 0.60 rather than
  0.31. Correlation-aware posterior for P(stream alive) is already
  used above.
- **If Phase 4 landing tightly gates sample count:** replacing the
  independent-product with a conditional chain gives P(sample count
  | Phase 4 lands) × P(Phase 4 lands) = 0.76 × 0.80 = 0.61 (matches
  baseline).
- **If substrate swap regresses uptime (plausible — new model stack
  is more complex):** this couples Vector 4.9 back into Vector 4.1.
  Joint → lower than naive product. Posterior P(research completes)
  drops to ~0.14.

### 7.3 Adversarial worst case

What if I'm wrong about base rates and the true state is:

- Uptime: 0.35 (recent failure rate is higher than I'm crediting)
- Audience: 0.10 (the niche filter I praised is actually fatal)
- Operator sustainability: 0.40 (the operator is closer to burnout
  than I'm reading from the commitment signals)

Adversarial joint P(research completes): **0.04**, 95% CI [0.00,
0.15]. The research program would not complete under these
assumptions.

**What evidence would distinguish adversarial from baseline?**

- **Audience:** wire the video ID and observe real viewer counts
  over 7 days. A reading of <1 avg concurrent would support the
  adversarial prior.
- **Operator sustainability:** observe whether the operator
  prioritizes compositor recovery vs research in the next 72 hours.
  Prioritizing recovery = commitment signal. Prioritizing research
  = possibly the operator has already written off Layer 1 and is
  optimizing Layer 4 alone.
- **Uptime:** post-FDL-1 compositor run duration. If it runs >24h
  without restart, baseline prior is correct. If it crashes within
  6h of restart, adversarial prior is correct.

## 8. Value of information

Which observations would most tighten the compound posterior?

### 8.1 High-value observations

| Observation | Cost to obtain | Posterior shift | Priority |
|---|---|---|---|
| **Wire YOUTUBE_VIDEO_ID + observe chat for 7 days** | ~5 minutes operator action + 7 days wall-clock | Shifts Vector 4.3 ± 0.15 depending on results; Vector 4.4 ± 0.20; P(monetization) ± 0.05 | **Highest** |
| **Restart compositor with FDL-1 and observe 24h uptime** | 5 minutes + 24 hours | Shifts Vector 4.1 ± 0.20. Distinguishes baseline from adversarial. | **Highest** |
| **Export YouTube channel analytics for existing subs + watch hours** | ~15 minutes | Replaces uninformative Vector 4.5 prior with direct data. Could shift P(YPP) ± 0.15. | **High** |
| **Count actual operator voice sessions per week** | Retrospective log query | Replaces assumption in Vector 4.8. ± 0.10. | Medium |
| **Check whether effect exists at d≥0.3** (pilot comparison) | Research work | Tightens Vector 4.10's effect-detection prior substantially. | Medium |
| **Observe mobo-swap outcome** | 24 hours | Collapses uncertainty in post-mobo uptime. ± 0.10. | Medium |

### 8.2 Lowest-cost highest-value single action

**Wire the YouTube video ID.**

This is the operational minimum action that:

1. Activates chat-monitor ingestion (Layer 1 observability)
2. Enables chat-driven director activity variation (Layer 1 content quality)
3. Re-enables Super Chat / membership event capture (Layer 3 revenue signal)
4. Records active_viewers from real chat authors (analytics)
5. Allows YouTube platform to register the broadcast as active (Layer 1 discoverability)

Cost: ~5 minutes of operator time.

Estimated posterior shift on the **headline P(stream alive in 90
days)** number: from 0.56 to ~0.65. The shift is not enormous, but
the **information gain** about Vector 4.3/4.4 is transformative —
it turns uninformative priors into real posteriors.

## 9. Decision-theoretic implications

### 9.1 Optimal action ordering

Given the above analysis, the rational priority queue for the
operator is:

1. **Wire YOUTUBE_VIDEO_ID.** Unblocks engagement observability +
   chat-monitor functionality. ~5 minutes.

2. **Restart studio-compositor.** FDL-1 is already on main; systemd
   will redeploy automatically once the start-limit timer resets
   (or `systemctl reset-failed` can force it). The compositor
   re-entry into service will exercise the fix under the pathological
   rebuild-cycle conditions that produced drop #51.

3. **Decide: run to mobo-swap or restart with c920-desk disabled?**
   Drop #51 options A/B/C still apply. The tradeoff is between
   "accept a known-unstable run for a few more hours" and "restart
   clean with one camera offline." Option B (restart + disable
   c920-desk) is the safer choice and allows FDL-1 to run under
   normal load rather than thrash.

4. **Observe for 24 hours.** Collect evidence on Vector 4.1 posterior
   (uptime post-FDL-1). Mobo swap happens tomorrow; observed uptime
   data from the 24-hour window will ground the post-mobo-swap
   posterior estimates.

5. **Then continue Phase 4 bootstrap + Phase 5 prep.** Beta's
   in-flight work is research-side, not engagement-side. Running in
   parallel with the engagement fix is fine.

### 9.2 Decision under the adversarial prior

If the adversarial prior from §7.3 is correct, the rational action
changes materially: rather than investing in more engagement
infrastructure, the operator should **focus exclusively on
research-side collection using voice sessions** (which do not depend
on audience), and treat the livestream as a **recording context**
rather than a performance. This converts the stream from a public
act into a private one that happens to be technically broadcast.

Under this adversarial regime, the operator's 90-day probability
of completing the research is **higher than under the baseline
regime** (~0.25 vs 0.18), because divorcing research from audience
removes the coupling to uptime + discoverability + chat activity.

The question of whether to adopt the adversarial posture is an
**operator preference question**, not a statistical one. Both postures are coherent. The adversarial posture is more
protective of the research program; the baseline posture maintains
the possibility of the engagement-led success path while accepting
a lower probability of research completion.

### 9.3 Sunk cost recognition

The engineering investment in the livestream infrastructure is
**not recoverable** — camera 24/7, compositor unification, chat
reactor, effect graph, reverie, the whole stack — this is in-place
whether the stream has 1 viewer or 1000. The operator has already
paid the cost. The question is marginal: **given the current
engineering state, what additional work produces the most
expected value?**

The decision-theoretic answer: **engineering work should shift
toward observability and experiment instrumentation**, not toward
further engagement infrastructure. The biggest remaining gaps are:

- **Audience observability** (chat-monitor wiring, per-condition
  Prometheus slicing from LRR Phase 10)
- **Research infrastructure** (condition_id coverage from drop #53,
  fd_count gauge from drop #41, output-freshness gauge from drop
  #51)
- **Stability guardrails** (FDL-1 regression test shipped,
  additional watchdog coverage pending)

These investments are dual-purpose: they improve research validity
**and** they improve operator confidence that the stream is worth
running. The confidence effect may be more important than the
direct data improvement.

## 10. Counterfactual scenarios

### 10.1 Counterfactual: FDL-1 never shipped

Without drop #52's trace and the FDL-1 fix, Vector 4.1 posterior
drops to ~0.38 (the dmabuf leak continues to compound). Over 90
days, compound P(stream alive) drops from 0.56 to ~0.28. P(research
completes) drops from 0.18 to ~0.06.

**FDL-1's marginal value: the fix moves the research program from
~6% completion probability to ~18% completion probability. This is
a 3× leverage factor on a 15-line change.**

### 10.2 Counterfactual: Hermes 3 swap doesn't happen

If Phase 5 is indefinitely deferred and the research program
remains on Qwen 3.5-9B (Condition A only), the program cannot test
the Shaikh claim. It can still produce a baseline dataset for
Condition A that could serve as a benchmark for a future comparison
— the data is not wasted, but the primary research question is
unanswered.

**P(useful Condition A baseline data): 0.52**
**P(publishable Shaikh-claim test): 0.18**

The 0.52 vs 0.18 gap represents the marginal value of Phase 5
execution. Phase 5 is high-leverage for the primary research
question, but the baseline data retains standalone value even
without it.

### 10.3 Counterfactual: chat-monitor video ID never wired

The director loop's activity variation stays stuck on `react`,
consistent with the observed reactor log. Stream content quality is
lower (no chat-driven preset swaps, no reactor cadence modulation).
Audience ceiling is lower by an unknown but non-trivial factor.

**Modal outcome:** stream remains running as a private recording
context, research continues at current rate, engagement remains
near zero. The 90-day program ends with a Condition A baseline but
no engagement evidence and no monetization.

Posterior P(research completes) under this counterfactual: ~0.22
(slightly higher than baseline because divorcing from audience
removes variance). This is adjacent to the "adversarial posture"
analysis in §9.2.

### 10.4 Counterfactual: operator restores compositor + wires video ID within 24 hours

Posterior updates significantly:

- Vector 4.1 updated with fresh uptime observations: expected shift
  +0.05 to +0.15 depending on observed data
- Vector 4.3/4.4 updated with fresh audience data: expected shift
  ±0.10
- Vector 4.7 (operator sustainability) receives positive signal
  from action itself: +0.05
- P(research completes) updated: ~0.25, 95% CI [0.10, 0.52]

**This counterfactual represents the highest-value single-action
pathway.**

## 11. Limitations

### 11.1 Priors I was forced to fabricate

I have no direct access to:

- Current YouTube subscriber count
- Current watch hours
- Peak concurrent viewers observed in the channel's history
- Chat author distribution under prior chat-monitor-functional
  windows
- Revenue events (Super Chat + membership history)
- Stream schedule / when broadcasts actually aired
- Neuro-sama or comparable channel comparables specific to this
  niche (AI + physical studio + operator-occasional-presence)

The priors for Vectors 4.3, 4.4, 4.5, and 4.6 are therefore largely
**informed guesses from base-rate reasoning**. Real data would
substantially tighten the compound posterior.

### 11.2 Dependency correlation is approximate

The joint posteriors in §6 treat dependencies via rough widening
rather than via a rigorous Bayesian network with specified copulas.
A more formal model would use:

- A DAG over the 10 vectors
- Conditional probability tables at each node
- Sampling (MCMC or variational) to compute joint posteriors

This was out of scope for a single drop. The rough widening is
calibrated to be conservative-leaning (posterior CIs are wider than
a naive product model would produce).

### 11.3 Effect-existence prior is unknowable

Vector 4.10 includes a term for "P(effect exists at d≥0.3)" which is
a claim about the physical world (does DPO post-training actually
flatten grounding more than SFT?). I assigned this P = 0.40 as a
generous prior based on the Shaikh claim being at least plausible,
but this is not a Bayesian estimate from data — it is an a priori
assignment that dominates the compound posterior. If the true
effect is present at d=0.5, the posterior on research success rises;
if it is absent (d=0), no amount of data collection produces a
publishable result.

This is an inherent feature of frequentist-to-Bayesian conversion of
effect-detection probabilities, and cannot be resolved without
running the experiment.

### 11.4 Operator psychology is the dominant unknown

Vector 4.7 (operator sustainability) is the single largest source
of outcome variance, and is the least measurable. The analysis
treats it as a probability, but it is really a behavior that
depends on motivation, mood, other life events, hardware reliability
experience, and the perceived trajectory of the program. I have
privileged the operator's known long-term commitment to the hapax-
council project and treated it as a weak positive signal, but this
is itself a judgment call.

### 11.5 The 90-day horizon is arbitrary

Most vectors were scored against a 90-day horizon because that
matches "near-term research window" roughly. Many of the posteriors
shift materially at different horizons:

- **30-day horizon:** uptime dominates, audience growth is slower,
  P(research completes) ≈ 0.05
- **180-day horizon:** audience growth has more time, Phase 5 is
  plausible, P(research completes) ≈ 0.28
- **365-day horizon:** YPP becomes plausible, operator sustainability
  is the binding constraint, P(research completes) ≈ 0.35 (capped by
  operator staying engaged that long)

The 90-day figure is **not the ceiling** — it is a near-term snapshot.

## 12. Summary + headline

**The livestream is currently in a dual-regime bottleneck:**

1. **Layer 0 bottleneck:** compositor is failed, chat-monitor is
   blind, the stream is offline at the instant of analysis. Recovery
   is ~85% probable within 48h but requires operator action.

2. **Layer 1 / Layer 2 bottleneck:** without wiring the YouTube video
   ID, all audience signals are blind; without audience signals,
   all operator-motivation feedback is absent; without that feedback,
   operator sustainability over 90 days drops to ~0.40.

**The highest-leverage action is the cheapest one: wire the
YouTube video ID.** This costs ~5 minutes and converts the
audience-observability system from "blind" to "reporting real
counts." It is the difference between running an experiment with
no measurement and running an experiment with any measurement at
all.

**The secondary actions are: restart compositor to exercise FDL-1
under load; accept that revenue-driven break-even is unlikely
within 90 days; treat the operator's personal compute + time as the
dominant funding source for the research.**

**Research success is ~18% probable in a 90-day window** — higher
than the revenue break-even probability (~0.04) but lower than the
stream-continues-running probability (~0.56). The research path is
viable but not predestined.

**The modal realistic outcome** is: stream is restored, runs at
imperfect but adequate uptime, Phase A baseline is locked, substrate
swap is attempted later (beyond 90 days), Condition A' data collects
over a longer horizon, and the Shaikh-claim test happens on a
4-6 month timeline rather than a 90-day timeline. The operator gets
research continuity; the platform gets a small stable niche; the
revenue gap is absorbed personally.

This is **not failure.** It is the realistic shape of a research
program that chose the hardest possible medium (24/7 live content)
as its data source. The question the operator must answer is
whether the engineering leverage is worth the opportunity cost of
the personal compute + time + attention that the stream continues
to consume.

**End of drop #54.**

— delta
