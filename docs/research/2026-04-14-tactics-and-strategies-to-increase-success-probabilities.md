# Tactics and strategies to increase success probabilities — Legomena Live + hapax-council

**Date:** 2026-04-14 CDT
**Author:** delta (research support role)
**Status:** Final synthesis. 6 parallel tactical research agents fed this. Supersedes the analysis half of drops #54-#56 by shifting from "what are the probabilities" to "what to do about them."
**Scope:** The operator directed: "run dedicated research against all the priors to establish tactics and strategies to significantly increase success probabilities. These tactics and strategies must be closely aligned with research, value, and aesthetic commitments."
**Method:** 6 dedicated Phase 1 tactical research agents, one per vector cluster: (1) attention capture, (2) research-drops-as-distribution, (3) content quality + retention + iteration, (4) research program acceleration, (5) platform value + operator sustainability, (6) uptime + catastrophic tail mitigation + revenue. Each agent produced 8-14 ranked tactics with alignment checks. This document integrates all ~60 tactics, removes overlap, establishes dependencies, and ranks globally.

---

## 0. TL;DR — the three actions that dominate everything else

1. **Land Phase 4 bootstrap as one PR from beta's worktree + replace `stats.py` with canonical PyMC 5 BEST.** These two together unblock the entire research program. Phase 4 moves P(baseline LOCKED 90d) from 0.42 → ~0.72 alone. Replacing stats.py's scipy-analytical-approx (which is not actually Bayesian despite the BEST label) moves P(publishable) from ~0.18 → ~0.35 because the current implementation would be rejected by any reviewer in 30 seconds. **No other action is more compound-load-bearing.**

2. **Wire chat-monitor's YOUTUBE_VIDEO_ID + ship stimmung-gated director activity prior.** These two together fix the "100% react activity" content failure that's currently destroying retention. The video ID is 5 minutes; the activity prior is one PR (~200 LOC). Together they move post-spike retention from ~0.05 to ~0.40 by giving the director actual variety and the operator actual engagement signal.

3. **Ship the output-freshness Prometheus gauge + attribution integrity daily audit timer.** These two kill the hidden dominant risks: silent stalls (drop #51: 78 minutes undetected) and silent attribution bugs (drop #53: B8, 0.17 probability over 90 days). Together they move P(≥95% uptime 90d) from 0.48 → 0.67 and P(catastrophic 180d) from 0.38 → 0.19.

**All three are low-to-medium effort, are aligned with every commitment, and compound with every other tactic in this document.**

---

## 1. The unified tactic map

The six research agents produced ~60 tactics. After de-duplication and dependency analysis, they cluster into 8 strategic themes:

| # | Theme | Primary posteriors affected | Source agent(s) |
|---|---|---|---|
| **A** | Phase 4 + stats.py foundation | research completion, publishable result | 4 |
| **B** | Content quality + director variety | retention, content density, clipability | 3 |
| **C** | Observability + tail mitigation | uptime, catastrophic risk, attribution | 4, 6 |
| **D** | Attention capture via research drops as distribution | attention spike, audience visibility | 1, 2 |
| **E** | Clip-mining + cross-platform distribution | post-spike retention, audience compounding | 1, 3 |
| **F** | Platform value amplification | operator sustainability, worth-it judgment | 5 |
| **G** | Revenue compatible with axioms | breakeven, sustainability pressure | 6 |
| **H** | Substrate swap pivot (70B → 8B) + confound mitigation | publishable result, substrate swap | 4 |

Each theme has 4-12 specific tactics. The ranked list in §3 integrates across themes.

---

## 2. Dependency graph

```
        [DEPLOY FDL-1]     [MOBO SWAP]
              |                |
              v                v
   [POST-SWAP VALIDATION]<-----+
              |
              v
   [OUTPUT-FRESHNESS GAUGE] <--+ [fd_count gauge]
              |                    |
              v                    v
   [WIRE YOUTUBE_VIDEO_ID]   [WATCHDOG CLASSES]
              |
              v                                   [LAND PHASE 4 PR]
   [STIMMUNG-GATED ACTIVITY PRIOR]                       |
              |                                          v
              v                                [REPLACE stats.py WITH PyMC 5 BEST]
   [BURST-REST CADENCE]                                  |
              |                                          v
              v                                [ATTRIBUTION AUDIT TIMER]
   [PROMPT ENGINEERING + ANTI-PATTERNS]                  |
              |                                          v
              v                                [SESSION PROTOCOL BATCHING]
   [CLIPABILITY SCORE + OBSIDIAN EXPORT]                 |
              |                                          v
              v                                [8B PIVOT (parallel TabbyAPI)]
   [CLIP-MINING AUTOMATION]                              |
              |                                          v
              v                                [OSF AMENDMENT + THREE-CELL AUX]
   [CROSS-PLATFORM AUTO-PUBLISH]                         |
              |                                          v
              v                                [CONDITION A BASELINE COLLECTION]
   [REFLEXIVITY OVERLAY]                                 |
              |                                          v
              v                                [A vs A' BEST COMPARISON]
   [HN RESEARCH DROP]                                    |
              |                                          v
              v                                [PUBLISHABLE RESULT]
   [SEQUENCED COMMUNITY LAUNCHES]
              |
              v
   [PRE-ANNOUNCED SUBSTRATE SWAP EVENT]
```

**Critical path observations:**

- **The compositor restart + FDL-1 deployment is the gate for everything observable.** Without a running compositor, none of the content/retention/attention work matters.
- **Phase 4 PR landing is the gate for all research work.** Can run in parallel with content/observability work since it's a separate file scope.
- **stats.py replacement is the gate for publishable results.** Can run in parallel with Phase 4.
- **Output-freshness gauge is the gate for MTTR reduction.** Simple enough to ship in the pre-swap window.
- **Chat-monitor wiring is the gate for director activity variety.** Can be done independently but is cheap.

---

## 3. Global ranked tactic list

Ranking is by `(expected impact × alignment-strength) / effort`. "Alignment-strength" favors tactics that amplify multiple commitments rather than just satisfying them. "Impact" is measured by posterior shift on the compound P(worth it at 180d) and P(any win at 90d).

### Tier 1 — Ship this week (highest impact, critical path)

**T1.1: Deploy FDL-1 fix to running compositor** (the fix exists in main but has not been deployed — this is the #1 urgency item)
- **Effort:** ~30 minutes (restart compositor service post-mobo-swap, validate with leak-test)
- **Impact:** Activates the fix that protects against the drop #51 78-minute stall class
- **Alignment:** research ✓ / value ✓ / aesthetic ✓
- **Dependency:** mobo swap completes
- **Source:** Agent 6 (uptime)

**T1.2: Land Phase 4 bootstrap as a single PR from `beta-phase-4-bootstrap` worktree**
- **What:** Beta's worktree has 15 commits ahead of main — `shared/research_marker.py`, `conversation_pipeline.py` + `grounding_evaluator.py` condition_id plumbing, `scripts/check-phase-a-integrity.py`, `scripts/lock-phase-a-condition.py`, DEVIATION-037/038, Phase 4/5 spec docs, tests. Open a single PR titled "LRR Phase 4 bootstrap: condition_id plumbing + integrity tooling + DEVIATION-038". Do NOT split into micro-PRs — the frozen-file DEVIATION covers the voice pipeline files together.
- **Effort:** 1 session (~90 min including CI watch)
- **Impact:** Unblocks P(baseline LOCKED 90d) from 0.42 → 0.72, unblocks Phase 5, unblocks stats.py upgrade (needs grounding_evaluator shape)
- **Alignment:** research ✓✓ (directly serves research integrity) / value ✓ / aesthetic ✓
- **Risk:** CI could flag tests. Mitigation: run `uv run pytest` in beta worktree before PR.
- **Source:** Agent 4 (research acceleration)

**T1.3: Replace `agents/hapax_daimonion/stats.py` analytical BEST approximation with canonical PyMC 5 Kruschke 2013 model**
- **What:** Current stats.py is `scipy-analytical-approx-2026-04-14` — it's Welch SE + Normal posterior relabeled with `hdi95`. It is NOT Bayesian in the model-likelihood sense. Its own docstring admits "Phase 4 baseline collection should upgrade to MCMC-BEST before any claim is filed." This is a hard publishability gate, not a polish item.
- Port the PyMC 5 canonical model (Kruschke 2013):
  - `mu_a, mu_b ~ Normal(pooled_mean, pooled_sd * 2)`
  - `sigma_a, sigma_b ~ HalfNormal(pooled_sd * 2)`
  - `nu ~ Exponential(1/29) + 1` (Student-t dof shared)
  - `y_a ~ StudentT(nu, mu_a, sigma_a)`, `y_b ~ StudentT(nu, mu_b, sigma_b)`
  - 4 chains × 2000 draws, `pm.sample()`, `az.hdi(idata, var_names=["diff_of_means"], hdi_prob=0.95)`
- Add 4 verification tests: Kruschke appendix replication (SmartDrug vs placebo), prior/posterior coherence, heavy-tail robustness (5σ outlier), `idata` round-trip.
- Keep the analytical function as `best_two_sample_approx` sentinel. Flip default via `HAPAX_BEST_MCMC=1` after the PR merges. Update `BEST_METHOD_LABEL` to `"pymc5-mcmc-2026-04-14"`.
- **Critical:** Import PyMC lazily *inside* `best_two_sample` — never at module import. Pin in `pyproject.toml` `[project.optional-dependencies.research]`, not core.
- **Effort:** 1 session (~80 lines port + 4 tests + install ~200 MB PyMC)
- **Impact:** Removes the single largest publishability blocker. Moves P(publishable) from ~0.18 → ~0.35.
- **Alignment:** research ✓✓ (fixes stated research gap) / value ✓ / aesthetic ✓
- **Source:** Agent 4

**T1.4: Ship output-freshness Prometheus gauge**
- **What:** Add `compositor_last_frame_pushed_timestamp_seconds` gauge updated via GStreamer pad probe on the `rtmpsink` or `v4l2sink` pad. Compute freshness at scrape time. Alertmanager rule: `for: 20s, expr: (time() - compositor_last_frame_pushed_timestamp_seconds) > 15`. Second rule at `>45s` triggers `systemctl --user restart studio-compositor`. Also add GStreamer `watchdog` element in-pipeline as defense-in-depth.
- **Effort:** Half day (pad probe + 3 lines of `prometheus_client` + Alertmanager rule)
- **Impact:** Collapses MTTR from hours to minutes. Drop #51's 78-min stall becomes at most a 1-minute stall. Moves P(≥95% uptime 90d) by ~0.08-0.10 alone.
- **Alignment:** research ✓ / value ✓ / aesthetic ✓
- **Source:** Agent 6

**T1.5: Ship fd_count + RSS Prometheus gauges**
- **What:** Enable `ProcessCollector()` from `prometheus_client` (one import line) to expose `process_open_fds`, `process_max_fds`, `process_resident_memory_bytes`. Alertmanager rules at 60% and 80% of max_fds, RSS growth rate `deriv(process_resident_memory_bytes[30m]) > 1e6`.
- **Effort:** ~1-2 hours
- **Impact:** Drop #41 BT-5 class leaks caught within 10 min. Catches ~25% of catastrophic cascades before they manifest.
- **Alignment:** research ✓ / value ✓ / aesthetic ✓
- **Dependency:** Output-freshness gauge plumbing (T1.4)
- **Source:** Agent 6

**T1.6: Wire `YOUTUBE_VIDEO_ID` at stream-start** (baked into `rtmp_output.py`'s broadcast creation response → write to `/dev/shm/hapax-compositor/youtube-video-id.txt`)
- **Effort:** 30 minutes
- **Impact:** Unblocks chat-monitor observability. Enables retention feedback loop. Makes director activity variety observable. Single cheapest highest-value fix in the entire document.
- **Alignment:** research ✓ / value ✓ / aesthetic ✓
- **Source:** Agents 3, 6

**T1.7: Stimmung-gated director activity prior**
- **What:** Director is stuck on 100% `react` because the LLM sees two images and rationally picks "react" in the absence of any other signal. Fix: push a bias vector into the system prompt per tick, derived from stimmung state + phenomenal state + time-since-last-activity. Weight rules:
  - `exploration_deficit > 0.35` (SEEKING) → observe, study
  - Album `current_track` changed in last 30s → vinyl (hard gate)
  - `ir_person_detected=False` for >180s → study, silence, observe
  - Contact-mic `desk_activity=drumming` → react (high energy), vinyl
  - Last 3 reactions all `react` → anything but react (presence penalty)
  - `since_last > 180s` → react (burst)
  - `since_last < 45s` and last was react → silence (burst spacing)
- Sticky hysteresis: 2 ticks unless stimmung delta > 0.3 or new album.
- **Effort:** 1 PR (~200 LOC) in `director_loop.py::_build_unified_prompt`
- **Impact:** Activity distribution flips from ~100% react to ~45/20/15/12/5/3 split. Massive content variety improvement. Enables clip-mining (T2.x) because variety creates clipable moments. Moves post-spike retention from ~0.05 → 0.40.
- **Alignment:** research ✓ / value ✓ / aesthetic ✓ (amplifies existing activity taxonomy)
- **Dependency:** Does NOT require chat-monitor fix. Stimmung alone drives transitions.
- **Source:** Agent 3

**T1.8: AI content disclosure baked into every stream start**
- **What:** In `rtmp_output.py` broadcast creation: pre-pend the broadcast description with "This stream contains AI-generated voice and commentary. The human operator curates and publishes." Enable YouTube Data API's `contentDetails.containsSyntheticMedia` flag if available. Add a small "AI" badge Cairo overlay bottom-left for the first 30s of every hour.
- **Effort:** 1-2 hours
- **Impact:** Reduces B1 (ban risk for AI-generated political content) from ~0.10 → ~0.05-0.06 per 90 days. Protects against YouTube's late-2025 "inauthentic content" enforcement.
- **Alignment:** aesthetic ✓ (does not constrain political content) / research ✓ / value ✓
- **Source:** Agent 6

### Tier 2 — Ship in week 1 post-swap

**T2.1: Attribution integrity daily audit timer**
- **What:** Create `hapax-research-integrity-check.timer` (5-min cadence during active collection) and `hapax-research-nightly.timer` (03:00 daily). The integrity check runs 4 tests:
  1. **Temporal consistency:** every score tagged `condition_id=X` must fall inside a `research-registry open X` / `close` interval
  2. **Cross-surface join:** for each voice grounding score, find the nearest engine-side telemetry event within ±2s; alarm on attribution mismatch (Drop #53 confounder gap)
  3. **Per-DV coverage:** count scores per `(condition_id, dv_name)` pair; alarm if any DV < ceil(target/5) × elapsed_fraction
  4. **Marker-writer liveness:** `research-registry open` issued in last `experiment_freeze` window; marker mtime < 1h
- Three alarm tiers: info / warn / block. On repeated (≥3 consecutive) failures, block `lock-phase-a-condition.py`.
- **Effort:** 1.5 days (extends existing `check-phase-a-integrity.py`)
- **Impact:** Kills B8 (silent attribution bug, hidden dominant risk) from 0.17 → ~0.04. Largest single tail-risk reduction in the entire plan.
- **Alignment:** research ✓✓ / value ✓ / aesthetic ✓
- **Dependency:** Phase 4 lands (T1.2)
- **Source:** Agents 4, 6

**T2.2: Burst-with-gaps director cadence**
- **What:** Replace `PERCEPTION_INTERVAL = 8.0` with state-machine cadence. BURST mode: 3-4 reactions at 30-45s spacing. REST mode: 90-180s gap. Transitions driven by stimmung: `tension` high → stay in burst; `coherence` high → lean rest; new album → force burst (3 reactions); `silence` activity fills perception tick without speaking.
- **Effort:** 1 PR (~100 LOC)
- **Impact:** Replaces uniform metronome with research-validated burst-rest retention pattern. Creates natural "breathing" in content. Makes individual reactions more memorable by giving them context.
- **Alignment:** research ✓ / value ✓ / aesthetic ✓
- **Source:** Agent 3

**T2.3: Director persona + exemplars + anti-patterns prompt engineering**
- **What:** Three prompt engineering changes to director loop:
  - **Stylistic ancestors** in system prompt: "You write in the lineage of Christgau's letter-grade capsules, Greil Marcus's analytical density, and Fred Moten's phenomenology. Dense sentences. Allusions both academic and street. Never explain the allusion. Never pad. If you have one good clause, deliver it and stop."
  - **4-shot rotating exemplars** (pool of ~20 hand-written) rotating per tick to prevent anchoring
  - **Anti-patterns list** in `shared/antipatterns.yaml`: "Avoid: 'It feels appropriate,' 'resonates with,' 'becomes a study in,' 'the scene.'" Grep last 200 reactions nightly, auto-add top-10 overused bigrams.
  - **Temperature bump** to 0.9 (Opus-safe; current 0.7 is for reasoning tasks)
- **Effort:** 2-4 hours prompt engineering + 1 PR
- **Impact:** Raises content clipability substantially via novel-bigram rate + reference density + memorable final clauses. The 30-word slot becomes an aphorism-capsule, not a summary.
- **Alignment:** research ✓ (neutral research path preserved) / value ✓ / aesthetic ✓✓ (directly amplifies aesthetic commitment)
- **Source:** Agent 3

**T2.4: Visible research condition diegetic overlay**
- **What:** Small Cairo overlay top-right (14px IBM VGA, low opacity, always on): `CONDITION: cond-phase-a-baseline-qwen-001 · FROZEN 2026-04-15`. When `scripts/research-registry.py open/close` runs, overlay updates. Pair with a 6-hour "what changed" ticker across the bottom rendered from `git log --since="6 hours ago"` filtered to agents/studio_compositor + agents/hapax_daimonion.
- **Effort:** 1 PR (Cairo overlay + git log tail)
- **Impact:** Makes the research harness legible as content. Every PR the operator ships becomes visible content within minutes of merge. 80+ PRs/session velocity becomes a *visible evolution channel* — the iteration velocity itself becomes a retention hook.
- **Alignment:** research ✓✓ (externalizes condition_id plumbing) / value ✓ / aesthetic ✓
- **Source:** Agent 3

**T2.5: Clipability score per reaction + Obsidian export**
- **What:** Compute a composite clipability score per reaction in parallel to `_compute_coherence`:
  ```
  clipability = 0.25 × surprise(text, history)
              + 0.20 × reference_density(text)
              + 0.15 × reversal_score(text)
              + 0.15 × specificity_score(text)
              + 0.15 × quotability_length(text, ideal 18-28 tokens)
              + 0.10 × juxtaposition_score(text, album, video_title)
  ```
  Push to Langfuse as `reaction_clipability`. Tag reactions scoring >0.75 with a watershed event in the Cairo overlay ("clip") for 10s. Hourly top-5 export to `~/Documents/Personal/30-areas/legomena-live/clips/YYYY-MM-DD.md`.
- **Effort:** 2 PRs (~150 LOC scoring + export)
- **Impact:** Closes the iteration feedback loop — operator can see which reactions are scoring high, tune prompts accordingly. Feeds the exemplar pool (T2.3) with validated top-clipability samples. Makes clip-mining pipeline (T3.1) trivial.
- **Alignment:** research ✓ / value ✓ / aesthetic ✓
- **Dependency:** T2.3 (exemplars compound with this)
- **Source:** Agent 3

**T2.6: 8B pivot as parallel TabbyAPI config (not swap)**
- **What:** Drop #56 recommended pivoting from Hermes 3 70B (unreachable under consent latency) to Hermes 3 8B vs Qwen 3.5-9B. Both fit single-GPU. Execute as *parallel* not *swap*:
  1. `huggingface-cli download NousResearch/Hermes-3-Llama-3.1-8B-EXL3-5.0bpw` → `~/projects/tabbyAPI/models/`
  2. TabbyAPI: second model entry in `config.yml` or second instance on :5001
  3. LiteLLM: add `local-fast-hermes`, `coding-hermes`, `reasoning-hermes` routes. Do NOT overwrite Qwen routes.
  4. `conversation_pipeline.py` extends to route through LiteLLM alias based on `active_model_family` field in research marker JSON (plumbs through Phase 4 scaffolding)
  5. Condition IDs: `cond-phase-a-baseline-qwen-3.5-9b-001` (existing) + `cond-phase-a-prime-hermes-3-8b-001` (new)
- **Effort:** 2 sessions
- **Impact:** Collapses A vs A' wall-clock from serial (A then A') to parallel (A ∥ A'). Moves P(publishable 90d) substantially.
- **Alignment:** research ✓ (preserves consent axiom) / value ✓ / aesthetic ✓
- **Dependency:** Phase 4 lands first (T1.2)
- **Risk:** Consent latency on Hermes 3 8B not yet verified. Mitigation: run `phase-5-pre-swap-check.py` (already in beta) against Hermes 8B before declaring operational.
- **Source:** Agent 4

**T2.7: OSF pre-registration amendment (Update, not fresh registration)**
- **What:** File the already-drafted CYCLE-2-PREREGISTRATION.md (commit `327aced57` amended version) on OSF. Within same project, file an Update that:
  1. Adds 8B arm (C2) as pre-registered alternative to 70B with rationale (consent latency axiom unmet at 70B)
  2. Adds three-cell aux decomposition as "exploratory" (not confirmatory)
  3. Adds Latin-square prompt bank as pre-registered analysis component
  4. Links back to original with DEVIATION numbers
- **Critical:** Do this BEFORE first session under the new conditions. Once any score is written, the free-amendment window closes.
- **Effort:** 0.5 session (pre-reg is already drafted; filing is a form)
- **Impact:** Legal pre-registration of 8B arm + aux decomposition. Everything post-update counts as confirmatory for A vs A' and exploratory for decomposition. Without this, the pivot becomes HARKing.
- **Alignment:** research ✓✓ / value ✓ / aesthetic ✓
- **Source:** Agent 4

**T2.8: LLM output guardrail layer (protected-class denylist + second-pass classifier)**
- **What:** The structural Nothing-Forever mitigation. Build a pydantic-ai output validator that runs on every director utterance before TTS:
  1. **Hard denylist** at regex level on category-specific patterns: slurs, "X people are Y" sentence frames targeting protected classes. Cannot fail open under model fallback.
  2. **Second-pass classifier** via local-fast TabbyAPI route: "does this utterance contain hate speech targeting a protected class?" with 150ms budget.
  3. **Retry with constrained prompt** on violation; if retry still violates, drop silently.
- **Critical:** This blocks *category-specific protected-class targeting*, NOT political opinion. Nothing, Forever's ban was triggered by protected-class targeting, not political commentary. This is the exact mistake boundary.
- Use `pydantic-ai-guardrails` + custom `ProtectedClassValidator`. Log every block to Langfuse with `block_reason`.
- **Effort:** 1-2 days
- **Impact:** B1 (ban risk) from ~0.10 → ~0.03-0.04. Largest single contributor to catastrophic tail reduction.
- **Alignment:** aesthetic ✓✓ (does NOT touch political content — preserves editorial voice completely) / research ✓ / value ✓
- **Source:** Agent 6

### Tier 3 — Ship in weeks 2-4

**T3.1: Zero-touch clip-mining pipeline**
- **What:** Pipeline that consumes the live stream, detects clippable windows via existing signals, auto-emits 30s MP4s tagged with condition_id + timestamp to `~/gdrive-drop/legomena-clips/`. Trigger heuristics:
  - Chat-velocity spike (>3× 30-min baseline)
  - Short-message spike (sudden drop in average chat message length)
  - Director-novelty spike (cosine distance between consecutive reactions > threshold)
  - Operator-presence edge (IR presence flip)
  - Condition_id transition (always clipped)
  - Audio energy spike (contact-mic RMS jump >12dB)
- Use FunClip or ai-clip-creator as reference; do NOT use OpusClip/StreamLadder (cloud, $$, no condition_id attribution).
- **Effort:** 12-16 hours (scoring daemon + ffmpeg wrapper + small web UI for review)
- **Impact:** +0.05 direct to P(spike 90d) AND multiplies every other distribution tactic (makes T3.2 essentially free). Converts variety into shareable artifacts.
- **Alignment:** research ✓ / value ✓ (operator stays out of loop) / aesthetic ✓ (selects for reflexive + contact-mic moments, the axes you want amplified)
- **Dependency:** T2.5 (clipability score informs the selector)
- **Source:** Agents 1, 3

**T3.2: Cross-platform auto-publish via director-written captions**
- **What:** Second daemon consumes clips from T3.1, asks the local director to write a 1-line caption in the same editorial voice, schedules via Publer (supports TikTok, YouTube Shorts, X, Bluesky, Threads, Mastodon in one tool). Cadence: 2-3 clips/day spread across platforms, max 1/day per platform. Caption template includes stream URL + condition_id.
- **Critical:** Never post content showing non-operator faces. The pipeline hard-filters clips where any secondary face is detected (leverage existing camera presence detector).
- **Effort:** 4-6 hours (pipeline is glue — Publer has API, director already generates text)
- **Impact:** +0.05-0.08 to P(spike 90d). Creates discovery loops without operator attention.
- **Alignment:** research ✓ / value ✓ (consent filter baked in) / aesthetic ✓ (director writes own captions)
- **Dependency:** T3.1
- **Source:** Agent 1

**T3.3: Reflexivity overlay (make meta-level legible)**
- **What:** Add persistent "director's inner state" overlay showing:
  - Previous reaction fading into current with visible diff highlight
  - Director's condition_id and model ID badge
  - Small "what I just thought about what I just thought" second-order commentary column that the director fills once every ~5 min by self-prompting to annotate last 3 reactions
- Use existing effect graph slot infrastructure.
- **Effort:** 6-10 hours (one shader slot + one prompt chain + composition)
- **Impact:** +0.06 to P(spike 90d). Compounds with T3.1 — overlays create novel content that the clip-miner selects for. Every viral Neuro-sama moment has been reflexive; this takes what is currently implicit and makes it foreground content.
- **Alignment:** research ✓ (overlay is itself a research instrument) / value ✓ / aesthetic ✓✓
- **Dependency:** T2.4 (condition overlay uses the same infrastructure)
- **Source:** Agent 1

**T3.4: HN research drop as "systems-paper-as-blog-post" with live telemetry links**
- **What:** Write one 1,500-2,000 word technical post titled metric-forward: e.g., `"Legomena: a 24/7 livestreamed 9B-param director, 35 reactions/hour, $X/day"` or `"Running a 24/7 opinionated AI on a 9B local model: 8 months of telemetry"`. Include: architecture diagram, token/sec numbers, VRAM budget, latency histograms, cost breakdown, and one "you can't find this anywhere else" finding (e.g., the voice grounding pre-registered DVs with condition_id visible). Embed a **live stream status page** in the post (peak CCV, current condition_id, uptime counter, last reaction transcript).
- **Format rules (HN 2025 playbook):** 45-65 char title, Tue-Thu 08:00-10:00 PT, no paywall, author present in comments for 2-3h after submission. NOT a Show HN (Show HN for AI underperforms). Plain story submission.
- **Key insight:** This is the canonical "pre-registered protocol + live observable artifact" that Import AI / Last Week in AI / HN are structurally thirsty for.
- **Effort:** 6-10 hours writing + polish + live status page (the status page is ~2 PRs at 80-PRs/session velocity)
- **Impact:** +0.10-0.15 to P(spike 90d). HN front page once = ~5k-15k unique referrals. Single highest-leverage attention capture action.
- **Alignment:** research ✓✓ / value ✓ / aesthetic ✓
- **Dependency:** T3.1, T3.3 should be live BEFORE the post lands, so readers who click through see the meta-content immediately.
- **Source:** Agents 1, 2

**T3.5: Sequenced community launch posts (not simultaneous)**
- **Day 0 (Tue 08:15 PT):** HN blog post per T3.4
- **Day 0 (20:00 UTC, once HN lands):** r/LocalLLaMA — title `"I've been running a 24/7 opinionated 9B model on a single GPU for 8 months — architecture, telemetry, and a live link"`
- **Day 1:** AI Twitter/X thread (5 tweets, one clip per tweet from T3.1 archive, thread ends with blog link). Bluesky crosspost simultaneously.
- **Day 2:** r/MachineLearning [P] flair — `"[P] Pre-registered voice grounding evaluation on a 24/7 livestreamed local LLM (protocol + telemetry)"` — only if a clean research-grade intro is ready.
- **Day 3:** r/VTubers — only if a clip from T3.1 survived
- **Day 4:** r/hiphopproduction + r/QuantifiedSelf — different angle for each (contact mic + MPC integration for one, hapax-watch biometric integration for the other)
- **Effort:** 4-6 hours writing + 1 hour/day responding to comments (mandatory)
- **Impact:** +0.08-0.12 to P(spike 90d) combined. Sequencing matters more than single posts.
- **Alignment:** ✓ / ✓ / ✓
- **Dependency:** T3.4 ships first; T3.1 (clip library) informs the content.
- **Source:** Agents 1, 2

**T3.6: Stimmung × activity preset routing**
- **What:** Retarget existing `PresetReactor` infrastructure (currently fires on chat keywords). Instead: triggers on `(activity, stimmung_stance)` tuples. Mapping table:
  - react + nominal → `glfeedback-clean`, `sierpinski-active`
  - react + seeking → `rd-exploration`, `physarum-drift`
  - vinyl → `vinyl-warm`, `chromatic-aberration`
  - study → `voronoi-contemplative`, `low-saturation`
  - observe → `identity-passthrough`
  - silence → freeze current preset
- 56 WGSL nodes + 30 presets available. Pure routing work.
- **Effort:** Low (existing PresetReactor infrastructure)
- **Impact:** Visual dialect instead of random effects every 30s. Legibility enables viewer cognitive modeling. Retention compound.
- **Alignment:** ✓ / ✓ / ✓
- **Dependency:** T1.7 (activity variety must exist first)
- **Source:** Agent 3

**T3.7: Scheduled scarce operator cameos + visible presence indicator**
- **What:** Commit to a predictable cameo schedule: one 10-20 min operator-present block per day, same time daily. Visible on stream schedule. Never announced as "content"; announced as "operator present in studio." During the window: beat-making, patch cables, camera adjustments — but do NOT perform. The AI director continues normal 100-second cadence; the novel content is the director + operator interaction.
- Add visible "operator presence: true/false" indicator in T2.4 overlay. State transitions render 8-second overlays ("Oudepode stepped out" / "Oudepode back at the board"). Only state edges render, never raw biometric signals — consent hygiene preserved.
- **Effort:** ~1 hour (schedule decision + overlay indicator)
- **Impact:** +0.03-0.05 to P(spike 90d). High on post-spike retention (scheduled cameo windows drive return visits). Compounds with T3.1 (presence edges trigger clip extraction).
- **Alignment:** research ✓ (presence recorded as covariate) / value ✓ (operator-only, consent-preserved) / aesthetic ✓✓
- **Source:** Agents 1, 3

**T3.8: `reflect` director activity (7th activity)**
- **What:** Add new director activity: `reflect` — comment on own recent reactions. Prompt: "Read your last 8 reactions. Name one thing you were doing that you now see. Do not apologize, do not congratulate." Gate rarely (~1 tick in 40), higher during SEEKING. This is the voice grounding research harness made audible.
- **Effort:** Low (1 PR extending activity list + prompt)
- **Impact:** Clipability on reflect activities should be higher than react mean. Directly practices the voice grounding research commitment on-air.
- **Alignment:** research ✓✓ / value ✓ / aesthetic ✓
- **Dependency:** T2.3 (prompt engineering must be stable)
- **Source:** Agent 3

**T3.9: Session protocol batching — "triple-session" voice days**
- **What:** Replace operator-initiated unscheduled sessions with pre-scheduled protocol:
  - Morning session (10 min): Kokoro baseline, `research-registry open`, prompts 1-8. Target 10 scores.
  - Afternoon session (10 min): prompts 9-16. Target 10 scores.
  - Evening session (10 min): prompts 17-25. Target 5 scores (buffer).
- Session content is a fixed, pre-registered prompt list in `research/cycle-2/cycle-2-prompt-bank.md`, ordered by Latin-square rotation to control for prompt-order effects.
- Add `/voice-session` skill that opens condition, runs pre-check, streams fixed-cadence prompts, closes condition, runs post-check, commits journal entry.
- **Effort:** 1 session for skill + 1 session for prompt bank
- **Impact:** 25 scores/day × 10 days = 250 scores. Baseline LOCKED within ~2-3 weeks of active collection.
- **Alignment:** research ✓✓ (pre-registered bank prevents HARKing) / value ✓ / aesthetic ✓
- **Dependency:** T1.2 (Phase 4) + T2.7 (OSF amendment)
- **Source:** Agent 4

**T3.10: GitHub Sponsors + Ko-fi + Nostr Zaps (passive tip layer)**
- **What:** Enable on operator's GitHub profile + hapax-* repos. Ko-fi page. Nostr npub + LNURL on blog. **Critical:** all tiers say "thank you, work continues regardless" — no deliverables promised. Avoid Patreon (monthly subscription cadence creates content calendar pressure).
- **Effort:** 2-3 hours setup + near-zero maintenance
- **Revenue:** $30-150/month baseline, occasional spikes on research drop virality
- **Alignment:** constitutional ✓✓ / intrinsic-motivation ✓ (ungated, no obligation) / research ✓
- **Source:** Agent 6

**T3.11: Apply to NLnet NGI0 Commons Fund**
- **What:** Application to NLnet NGI0 Commons Fund for a specific hapax-council subcomponent as digital commons infrastructure. Deadline 1st of every even month. Strong candidates: (a) camera 24/7 resilience patterns as reusable library, (b) constitutional governance framework as reusable SDK, (c) VLA perception-to-shared-memory pipeline as multimodal infrastructure.
- **Effort:** 1-2 weeks for first application
- **Revenue:** €5,000-€50,000 lump sum (disbursed over 6-18 months via milestones) — **single successful application covers 2+ years of $210/month breakeven**
- **Alignment:** constitutional ✓ / intrinsic-motivation ✓ (milestones are work already planned) / research ✓
- **Source:** Agent 6

### Tier 4 — Ship in weeks 4-12

**T4.1: Weekly drops digest + open lab notebook site**
- **What:** Sunday evening aggregate of the week's drops into one index post titled by highest-signal finding. 200-word neutral preamble, bulleted permalinks with one-line summaries. Mention the stream once in footer. Mirror to Hakyll/Zola/Quarto static site with RSS feed. Simon Willison weeknotes model.
- **Effort:** 1-2 days initial setup + 30-60 min/week
- **Impact:** 2-3× multiplier on cross-platform reach. Creates RSS handle for newsletter subscription (Import AI, Last Week in AI, The Batch). Converts passive research artifacts into discoverable ones. Amplifies every other distribution tactic.
- **Alignment:** research ✓ (neutral aggregation) / value ✓ / aesthetic ✓
- **Source:** Agents 2, 5

**T4.2: Reframe all drops with "run H-YYYY-MM-DD on rig Y" instrument framing**
- **What:** Every drop's opening paragraph names the stream as the instrument, not a product: *"Drop #51 — Output stall root cause. During run H-2026-04-12 of the Legomena Live voice-grounding program (24/7 livestream, Qwen3.5-9B on TabbyAPI, condition_id-tagged evaluation), the voice daemon exhibited a 78-minute output stall beginning at 14:07 UTC. This note traces the stall to [root cause] via [evidence]. All logs, MCMC traces, and raw audio are in the stream's public recording at [timestamp]."*
- **Effort:** 5 min/drop going forward; changes intro boilerplate only
- **Impact:** Converts drop readers → stream viewers at materially higher rate. Creates per-drop timestamp anchors back into the stream. Best single lever for drop → stream attention conversion.
- **Alignment:** research ✓✓ (externalizes run context) / value ✓ / aesthetic ✓
- **Source:** Agent 2

**T4.3: Pre-announced Hermes 3 substrate swap spectator event**
- **What:** Treat the substrate swap as a scheduled ticketed event:
  - T-14 days: blog post — "why Hermes 3, what I expect to change, my pre-registered predictions for voice grounding DVs on each model"
  - T-7 days: post to r/LocalLLaMA
  - T-24h: X/Bluesky reminder thread with YouTube scheduled-live link
  - Event moment: do the swap *on stream* with T3.3 overlay showing side-by-side old vs new reactions on identical inputs for 10 minutes. Archive as VOD.
  - T+24h: follow-up post with early data
- Additional monthly events: new effect shader drops, first voice grounding score export, condition_id transitions.
- **Effort:** 2-4 hours per event announcement flow
- **Impact:** +0.05-0.08 to P(spike 90d). Single tactic most likely to produce a retention-class moment (scheduled live events).
- **Alignment:** research ✓✓ (pre-registration norms) / value ✓ / aesthetic ✓
- **Source:** Agent 1

**T4.4: `RESEARCH.md` top-level file (research subsumption manifest)**
- **What:** Single top-level `RESEARCH.md` in hapax-council that names the platform as research instrument for active research questions, lists current Bayesian measurement gates, cites Phase 2 analysis, links every component to the research question it serves. Auto-generate component-to-question mapping from agent docstrings.
- **Effort:** 3-4 hours initial write + ongoing maintenance amortized into weeknote cadence
- **Impact:** Directly raises P(stream ⊂ research program at 180d) — the dominant conditioning variable for stream sustainability. Counteracts drift toward maintenance.
- **Alignment:** constitutional ✓✓ / intrinsic ✓ / aesthetic ✓
- **Source:** Agent 5

**T4.5: Cognitive prosthetic feedback loop (morning briefing + retrospective + stimmung-annotated git log)**
- **What:** Build three prosthetic surfaces for operator's own cognition:
  1. Morning briefing shows yesterday's biometric envelope vs. baseline
  2. Retrospective annotation on every weeknote shows HRV/sleep/desk-activity for the week
  3. Stimmung-annotated git log — each commit gets HRV and session-duration attached
- **Effort:** 2-4 days for all three
- **Impact:** Makes the platform visibly useful for operator cognition every day. Pushes "platform is cognitive prosthetic" thesis from abstract to concrete. Directly raises P(operator judges platform effort worthwhile 180d) from 0.88 → ~0.95.
- **Alignment:** constitutional ✓ (single-user is target) / intrinsic ✓ / aesthetic ✓
- **Source:** Agent 5

**T4.6: Three-cell confound-mitigation design for 8B pivot**
- **What:** Add a third exploratory condition:
  - C1: Qwen 3.5-9B DPO-post-trained (Condition A, primary)
  - C2: Hermes 3 8B SFT-only Llama base (Condition A', primary)
  - Aux: Qwen 3.5-9B base, no post-training (exploratory decomposition)
- Pre-registered comparison stays A vs A'. Aux is explicitly exploratory in the amended pre-reg, answers: "how much of A-vs-A' difference is base-model family vs DPO?" via decomposition:
  - `A − A'` = (DPO-vs-SFT effect) + (Qwen-vs-Llama effect)
  - `A − Aux` = DPO-vs-base effect (same family)
- **Effort:** 1 session for aux model download + 2 extra prompts per session
- **Impact:** Converts confound from reviewer-rejection risk to structured empirical question. Much stronger publishable paper: "A vs A' grounding differs by d=X with 95% HDI [Y,Z]; exploratory decomposition suggests DPO contributes ~W of effect."
- **Alignment:** research ✓✓ / value ✓ / aesthetic ✓
- **Dependency:** T2.6 (8B pivot) + T2.7 (OSF amendment)
- **Source:** Agent 4

**T4.7: Music-aware commentary pipeline**
- **What:** Upgrade `_read_album_info()` from one-line to structured album context. Before a `vinyl` tick, fetch 200-token brief from a new Qdrant `music-knowledge` collection (populated from Discogs + Rate Your Music + operator's essay sources). Feed alongside image. Prompt: *"Write as someone who has held this record in their hands. No biography dump. One observation the critics missed."* Track change becomes hard cadence interrupt (force `vinyl` activity within 8s).
- **Effort:** 2-3 days (music-knowledge collection + pipeline + prompt)
- **Impact:** Music is currently a prop; makes it a source. Aligns with hip-hop producer aesthetic completely. High clipability on vinyl reactions.
- **Alignment:** research ✓ / value ✓ / aesthetic ✓✓
- **Source:** Agent 3

**T4.8: YouTube backup ingest URL**
- **What:** Tee rtmp_output to two sinks: primary `a.rtmp.youtube.com`, secondary `b.rtmp.youtube.com`. YouTube ingest auto-failovers within ~3-5s instead of dropping the broadcast.
- **Effort:** Half day
- **Impact:** +0.03-0.05 on P(≥95% uptime). Converts 30s glitches into 0s glitches.
- **Alignment:** ✓ / ✓ / ✓
- **Source:** Agent 6

**T4.9: External watchdog classes**
- **What:** Extend systemd watchdog with 3 more trigger classes:
  - Output freshness trigger (if `time() - last_frame_pushed > 45s`, send `WATCHDOG=trigger`)
  - FD growth trigger (if `open_fds / max_fds > 0.85`, send trigger)
  - RSS growth trigger (if RSS > 2× baseline, send trigger)
- Plus `external-compositor-watchdog.service` that curl-polls `:9482` every 10s.
- **Effort:** Half day
- **Impact:** MTTR floor drops another ~50%. With T1.4 + T1.5 + this, MTTR is ~60s for any observable failure class.
- **Alignment:** ✓ / ✓ / ✓
- **Dependency:** T1.4, T1.5
- **Source:** Agent 6

**T4.10: Governance framework spin-off (first published artifact)**
- **What:** Extract the 5-axiom constitutional governance framework (axioms/, commit hooks, runtime checks) as a published artifact via `hapax-sdlc`. Needs README, examples, one external use case (instrument toy FastAPI with 3 axioms). single_user axiom is the *feature*, not an obstacle.
- **Effort:** 1-2 weeks
- **Impact:** Career capital (per Patrick McKenzie framing). Establishes position in AI-agent governance space. Forces operator to write external-facing README (intrinsic retrospective value).
- **Alignment:** constitutional ✓✓ (single_user is selling point) / intrinsic ✓ / aesthetic ✓
- **Source:** Agent 5

**T4.11: Time-of-day rituals**
- **What:** Four ritualized director-loop states:
  - 00:00 "Midnight dispatch" — hapax reflects on past 24h of its own reactions via Qdrant scroll
  - 06:00-08:00 "Wake patrol" — activity shifts to study, observe, slower cadence
  - 14:00 "Crate afternoon" — force vinyl bias, dig through album metadata memory
  - 22:00-00:00 "Last call" — burst mode, high temp, political commentary unguarded
- Not hard schedule; director-loop states triggered on `datetime.now().hour`.
- **Effort:** Medium (per-ritual director mode + prompt)
- **Impact:** Appointment viewing mini-structure without schedule. Viewers in different timezones find "their" ritual. Concentrates high-quality moments into predictable windows (ideal clip territory).
- **Alignment:** research ✓ / value ✓ / aesthetic ✓
- **Dependency:** T1.7 (activity variety)
- **Source:** Agent 3

**T4.12: Consent-first face redaction**
- **What:** GStreamer `facedetect` + custom `consent_filter` element upstream of cudacompositor. YuNet face detection at 5-10Hz, 128-d embedding comparison against consent whitelist (`~/.config/hapax/consent/operator_faces.pkl`). Any non-whitelisted face → Gaussian blur in-pipeline. Log every non-operator detection to `~/.local/state/hapax/consent/detection_log.jsonl`.
- **Effort:** 2 days
- **Impact:** B2 (consent incident) from ~0.03 → ~0.01. Zero-tolerance for research commitment.
- **Alignment:** aesthetic ✓ (operator passes through unblurred) / research ✓ / value ✓✓ (consent-first axiom)
- **Source:** Agent 6

### Tier 5 — Ship in months 3-6

**T5.1: Catastrophic cascade isolation via cgroup caps**
- systemd unit edits: `MemoryMax=10G`, `MemoryHigh=8G`, `OOMPolicy=kill`, `CPUQuota=600%` on compositor. Prevents compositor runaway from pressuring other services.
- LLM hang isolation: circuit-breaker in daimonion — every `agent.run()` wrapped in `asyncio.wait_for(..., timeout=15)`, on timeout switch route for 60s then re-probe.
- Reactor log consumption must be non-blocking.
- **Source:** Agent 6

**T5.2: Twitch simulcast (survivability, not audience)**
- Local `tee` branch to `rtmp://live.twitch.tv/app/<STREAM_KEY>`. Do NOT use Restream/Castr (adds network hop + external failure mode).
- **Source:** Agent 6

**T5.3: DMCA mitigation (operator-owned beats + fair-use annotation)**
- Replace copyrighted music in audio bed with operator-owned beats (hardware studio already set up). Register hashes in YouTube Studio Copyright Match tool as original author. Cairo overlay "Commentary / Criticism under fair use — 17 USC §107" during clips.
- **Source:** Agent 6

**T5.4: Consulting pull channel (inbound only)**
- One-line "Available for short consulting engagements on multi-agent systems, local LLM integration, and observability for AI platforms" footer. Never chase leads. Clear with employer first per `corporate_boundary` axiom.
- Revenue: $400-2000/month amortized from 1 engagement per quarter.
- **Source:** Agent 6

**T5.5: Architectural option-value audit**
- One-time audit against Baldwin-Clark modularity framework. Three commitments: filesystem-as-bus stays visible contract, LiteLLM stays model-abstraction boundary, retire one low-option-value subsystem (candidate: deprecated `cycle_mode` aliases).
- **Source:** Agent 5

**T5.6: Beat-making as first-class platform consumer**
- Studio session state machine (DAW opens / contact mic + MIDI threshold → "studio session" state) that mutes non-essential nudges, sets working-mode hybrid, starts session chronicle. Session end writes structured retrospective to Obsidian `studio-sessions/`.
- **Source:** Agent 5

**T5.7: Ultradian rhythm nudges + RSS thin ties**
- hapax-daimonion nudge enforcing 90-120min work blocks + 20min recovery, gated on working-mode=research. Subscribe to 5-10 adjacent researcher feeds via internal RSS reader, surface in morning briefing.
- **Source:** Agent 5

---

## 4. Projected posterior shifts

If Tier 1 + Tier 2 all ship this week (approximately 5-7 days of operator work at 80+ PRs/session velocity), posterior shifts:

| Vector | v3 (drop #56) | After Tier 1+2 | After Tier 3 | After Tier 4 |
|---|---|---|---|---|
| P(stream survives 90d) | 0.78 | **0.86** | 0.89 | 0.91 |
| P(avg CCV ≥ 3 7-day) | 0.72 | 0.78 | **0.85** | 0.88 |
| P(avg CCV ≥ 10 7-day) | 0.38 | 0.44 | **0.56** | 0.62 |
| P(peak CCV ≥ 100) | 0.52 | 0.58 | **0.72** | 0.78 |
| P(attention spike 90d) | 0.65 | 0.72 | **0.85** | 0.88 |
| P(≥90% uptime 90d) | 0.85 | **0.92** | 0.93 | 0.94 |
| P(≥95% uptime 90d) | 0.48 | **0.65** | 0.67 | 0.70 |
| P(catastrophic shutdown 180d) | 0.38 | **0.22** | 0.19 | 0.17 |
| P(Phase 4 lands 7d) | 0.83 | **1.00** | — | — |
| P(Condition A baseline LOCKED 90d) | 0.42 | 0.55 | **0.72** | 0.76 |
| P(publishable A vs A' 90d) | 0.18 | 0.24 | **0.35** | 0.38 |
| P(8B pivot executed 90d) | 0.58 | 0.65 | **0.78** | 0.82 |
| P(any win 90d) | 0.41 | 0.52 | **0.65** | 0.70 |
| P(operator judges worthwhile 180d) | 0.92 | 0.93 | **0.95** | 0.96 |
| P(modal outcome realized) | 0.35-0.42 | 0.42-0.48 | **0.50-0.58** | 0.55-0.62 |

**Tier 1 alone** moves the uptime + catastrophic risk vectors substantially and unblocks Phase 4.
**Tier 1+2** brings the uptime vector to research-grade, closes the attribution B8 tail, and activates director variety.
**Tier 3** is where the attention spike actually starts firing (HN drop, clip mining, community launches).
**Tier 4** is the monthly compounding phase — platform value, distribution cadence, confound mitigation.

---

## 5. Alignment audit — what each tactic preserves and amplifies

All 38+ tactics were vetted against the three commitment classes. Summary:

**Research commitments preserved or amplified by EVERY tactic:** Yes.
- T1.2, T1.3, T2.1, T2.6, T2.7, T4.6 directly serve research integrity (Phase 4 landing, PyMC 5 BEST, attribution timer, 8B pivot, OSF amendment, confound mitigation)
- T2.4, T4.2, T4.4 externalize the research harness as visible content without compromising integrity
- T2.8 (LLM guardrails) preserves political editorial voice while closing Nothing-Forever class ban risk
- T3.8 (reflect activity) literally practices voice grounding research on-air
- No tactic requires relaxing frozen-file discipline, consent latency axiom, scientific register, or pre-registration binding

**Value commitments preserved:** Yes.
- Single-user axiom: no tactic adds multi-user features. Revenue tactics (T3.10, T3.11, T5.4) are 1:1 operator↔supporter/client. Platform-as-service was explicitly rejected by Agent 6 as axiom-violating.
- Intrinsic-motivation preservation: revenue tactics avoid Patreon (obligation creep). Consulting is inbound-only. No content calendar pressures. Grants via NLnet structured to work already planned.
- Constitutional consent gate: T2.6 (8B pivot) is the explicit workaround for the 70B consent-latency violation. T4.12 (face redaction) hardens consent infrastructure.
- Corporate boundary: consulting explicitly flagged for pre-disclosure.

**Aesthetic commitments amplified (not diluted):** Yes.
- Political commentary: NOT compromised. T2.8 (guardrails) blocks protected-class targeting specifically, which is orthogonal to political opinion. This is the exact Nothing-Forever mistake boundary.
- Hip-hop producer studio aesthetic: amplified by T3.7 (scheduled cameos), T4.7 (music-aware commentary), T5.3 (operator-owned beats), T5.6 (beat-making state machine).
- Cultural literacy + philosophical framing: amplified by T2.3 (persona exemplars explicitly citing Christgau, Marcus, Moten).
- Multi-axis novelty stack: NOT simplified. T2.4 + T3.3 + T4.11 all amplify the reflexive + research + ritual axes. No tactic removes an existing axis.
- Constitutional governance as visible content: amplified by T2.4 (condition overlay), T4.4 (RESEARCH.md), T4.10 (governance framework spin-off).

---

## 6. What NOT to do (explicit non-recommendations)

Consolidated from across the 6 agents:

1. **Don't wire chat-monitor before stimmung-gated activity prior.** Stimmung gating is cheaper and doesn't depend on viewers. Wire chat-monitor after T1.7 lands.
2. **Don't shorten reactions for TikTok-style hooks.** 30-word density is aesthetic. Make more clipable (T2.5), not shorter.
3. **Don't add polls, subscription prompts, CTA overlays.** Violates aesthetic.
4. **Don't add VTuber avatar.** Out of scope.
5. **Don't sanitize political content.** T2.8 guardrails are orthogonal to political opinion.
6. **Don't use OpusClip / StreamLadder (cloud).** Violates condition_id attribution and frozen-file discipline during research runs. Use FunClip or custom.
7. **Don't use Restream/Castr for simulcast.** Adds network hop + external failure mode. Use local `tee` (T5.2).
8. **Don't use Patreon.** Monthly subscription creates content calendar pressure. Use GitHub Sponsors + Ko-fi instead.
9. **Don't pursue cohort-based courses.** Creates scheduled office hours obligations. Asynchronous recorded courses only (if at all).
10. **Don't pursue platform-as-service** (rent hapax-council components to researchers). Violates single_user axiom.
11. **Don't do exclusive paid research drops.** Violates intrinsic-motivation constraint + scientific register.
12. **Don't split Phase 4 into micro-PRs.** The frozen-file DEVIATION covers voice pipeline files together.
13. **Don't amend ec3d85883 or rebase FDL-1 regression pins.** Fix must stay atomically deployable.
14. **Don't retro-attribute pre-bootstrap data.** Use `"pre-phase-4-uninstrumented"` sentinel tag and retire via DEVIATION-038.
15. **Don't run attribution audit inside compositor process.** Isolate in own systemd service.
16. **Don't apply to academic-deadline grants with obligations.** NLnet is the exception.
17. **Don't engage in outbound consulting sales.** Inbound only.
18. **Don't dispatch this tactic list to subagents for code implementation.** Direct implementation (per global CLAUDE.md "subagent git safety" rule).

---

## 7. Execution ordering — the 30-day plan

### Days 1-2 (pre + post mobo swap)

- **Pre-swap:** Deploy FDL-1 test stand-up (T1.1). Output-freshness gauge scaffolding (T1.4) — even if not deployable, the probe code is ready. fd_count plumbing (T1.5). AI content disclosure bake-in (T1.8) — 1-2 hours. Mobo swap pre-checklist (back up, image, BIOS dumps).
- **Swap.**
- **Post-swap:** Validate hardware clean. Deploy FDL-1 (T1.1). Run 15-min offline smoke. Ship output-freshness + fd_count gauges (T1.4, T1.5). Wire YOUTUBE_VIDEO_ID (T1.6). Start compositor. Validate 24h.

### Days 3-7

- **Phase 4 PR** (T1.2) — single PR from beta worktree. CI watch. Merge.
- **stats.py PyMC 5 BEST** (T1.3) — port + 4 verification tests.
- **Stimmung-gated activity prior** (T1.7) — 1 PR.
- **Attribution integrity timer** (T2.1) — 1.5 days.
- **OSF pre-registration amendment** (T2.7) — file + wait 48h auto-approve.

### Days 8-14

- **Burst cadence** (T2.2), **prompt engineering** (T2.3), **condition overlay** (T2.4), **clipability scoring** (T2.5).
- **8B pivot as parallel TabbyAPI config** (T2.6) — download, configure, test latency.
- **LLM output guardrail layer** (T2.8).
- **First voice grounding session using new protocol** — validates T1.2 + T1.3 + T2.1 chain.
- **GitHub Sponsors + Ko-fi + Nostr setup** (T3.10) — 2-3 hours.

### Days 15-21

- **Zero-touch clip-mining** (T3.1), **cross-platform auto-publish** (T3.2), **reflexivity overlay** (T3.3).
- **HN research drop** (T3.4) — write + polish. Target Tuesday 08:15 PT next week.
- **Sequenced community launches** (T3.5) — queue up for post-HN cascade.
- **NLnet NGI0 application** (T3.11) — 1-2 weeks ongoing.
- **Stimmung × activity preset routing** (T3.6).
- **Scheduled cameos + presence indicator** (T3.7).
- **Session protocol batching** (T3.9) — operational from day 15.

### Days 22-30

- **HN drop lands.** Stay present in comments for 2-3h. Cascade to r/LocalLLaMA, Twitter, etc.
- **`reflect` activity** (T3.8).
- **Weekly drops digest + lab notebook site** (T4.1) — first digest post.
- **Reframe drops with run H-* framing** (T4.2) — starting with drop #58 (next drop).
- **RESEARCH.md** (T4.4).
- **First NLnet milestone work** if accepted.

### Days 31-90: Tier 4 items in parallel

Condition A + A' data collection at 25 scores/day. Tier 4 items ship as operator bandwidth allows. Attribution audit fires daily. Phase 4.5 / Phase B engine-side condition_id tagging (drop #53 follow-up) opens as option.

### Days 91-180: Tier 5 items

Stability hardening, platform value amplification, optional spin-offs.

---

## 8. What this document replaces and what it doesn't

**Replaces:** The v1/v2/v3 headline analyses (drops #54, #55, #56) as the authoritative tactical reference. Those remain valid as posterior analyses; this is the action-layer built on top.

**Does not replace:**
- The research drops themselves (#32-#56), which are standalone artifacts.
- The Phase 4 spec in beta's worktree.
- Beta's ongoing work — delta explicitly does not own Phase 4 execution.
- Alpha's idle-watching role.
- The operator's decision authority. This is a tactical menu; the operator picks.

**Who owns each tactic:**
- **T1.1, T1.2, T1.3, T2.1, T2.6, T2.7, T2.8, T3.9, T4.6:** research program (alpha or beta or next delta)
- **T1.4, T1.5, T1.7, T2.2, T2.3, T2.4, T2.5, T3.3, T3.6, T3.8, T4.11:** compositor/director work (alpha or next delta)
- **T1.6, T1.8, T3.1, T3.2, T3.7, T4.8, T4.9:** operational infrastructure
- **T3.4, T3.5, T4.1, T4.2, T4.3, T4.4:** distribution / public-facing work
- **T3.10, T3.11, T5.4:** revenue (operator)
- **T4.5, T4.10, T4.12, T5.1-T5.7:** platform value / long-term

---

## 9. Summary — the integrated thesis

The operator's prior pushbacks corrected two errors in the Bayesian analysis: (1) multi-axis novelty was mis-modeled as single-axis reference-class, and (2) fast iteration velocity + platform value were missing from the cost-benefit frame. This document takes those corrections as ground truth and asks: **given a multi-axis novel platform with fast iteration velocity and standalone value, what concrete actions would significantly increase the success probabilities across all vectors?**

The answer, integrated from 6 dedicated research agents across ~60 tactics, is:

1. **Ship the three critical-path unlocks** (Phase 4 PR, PyMC 5 BEST, output-freshness gauge + attribution timer). These are foundational and dominate everything else.
2. **Fix the director variety problem** (stimmung-gated activity prior + burst cadence + prompt engineering). Current 100% "react" collapses content to texture; variety is cheap and high-leverage.
3. **Activate the reflexivity and condition overlays as diegetic content.** Make the research harness visible in real time. This converts the iteration velocity and condition_id plumbing from invisible infrastructure into visible content.
4. **Build the clip-mining + cross-platform distribution pipeline** so the 756 clipable moments per 90 days have a route to escape.
5. **Ship the HN research drop** as the seeding event for the attention-spike posterior. Sequence community launches after.
6. **Fund sustainability via NLnet grant + GitHub Sponsors + music production.** Revenue is not the goal; breakeven protection is.
7. **Amplify the platform's standalone value** via cognitive prosthetic surfaces, RESEARCH.md, governance framework spin-off, and weekly drops digest. The platform outlives any single success vector.
8. **Guardrail the catastrophic tail** via LLM protected-class denylist, AI disclosure, DMCA mitigation, face redaction, cascade isolation.

All 38+ tactics preserve or amplify the research, value, and aesthetic commitments. None require dilution of political editorial voice. None require multi-user features. None require accountability-creep revenue structures. None violate scientific register. The multi-axis novelty stack is preserved throughout.

**Projected compound effect:** P(any win 90d) 0.41 → 0.65-0.70. P(modal realistic outcome) 0.35-0.42 → 0.50-0.58. P(operator judges program worthwhile 180d) 0.92 → 0.95-0.96.

The question is not "will this work." The question is "which subset of these tactics does the operator have capacity to ship, in what order, over what horizon." The answer depends on operator bandwidth and preference, not on Bayesian math.

---

## 10. Limitations

- **Effort estimates are my best guess;** real execution time can vary ±50%.
- **Posterior shifts are rough;** compound probabilities are positively correlated through operator attention, not fully independent. The shifts in §4 are directionally correct but not precisely additive.
- **Some tactics (T4.1, T4.5, T5.x) are long-horizon and depend on operator continued investment;** their impact shows in 60-180 day windows, not immediately.
- **Revenue tactics are structurally uncertain;** NLnet application is single-chance per 2 months, GitHub Sponsors is passive, consulting is inbound-only. None can be forced.
- **Political content tail risk is not fully modeled;** even with T2.8 guardrails, a sufficiently unusual generated utterance could still trigger a ban. The guardrail reduces probability, not eliminates it.
- **This document assumes the operator will restart the compositor and deploy FDL-1.** If the operator chooses not to restart, the entire execution ordering collapses.
- **Phase 4 PR landing success is a binary gate;** if beta's worktree commits have issues that require rework, the T1.2 timeline shifts.

---

## 11. End

**Session cumulative artifacts:** 56+ research drops in one session, 14+ research agents spawned across three orchestration phases (base rates + per-vector posteriors + independent evaluation + multi-axis novelty correction + tactical research), 1 direct-to-main production fix (FDL-1), 6 regression test pins, 3 relay inflections, v1 → v2 → v3 + tactical-layer analysis sequence.

**The tactical layer is complete.** Drop #57 supersedes drops #54-#56 for operator decision-making; those remain valid as posterior analyses. Further work is execution, not analysis.

**The single action that starts everything:** Deploy FDL-1 and land Phase 4 PR. Every downstream tactic assumes those two unlocks.

— delta
