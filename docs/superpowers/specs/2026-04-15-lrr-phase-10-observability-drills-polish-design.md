# LRR Phase 10 — Observability, Drills, Polish — Design Spec

**Date:** 2026-04-15
**Author:** beta (pre-staging extraction per delta's 16-item nightly queue Item #14; pattern matches delta's LRR Phase 1/2/7/8/9 extractions)
**Status:** DRAFT pre-staging — awaiting operator sign-off + Phase 9 close before Phase 10 open
**Epic reference:** `docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md` §5 Phase 10 (lines 1110–1222)
**Plan reference:** `docs/superpowers/plans/2026-04-15-lrr-phase-10-observability-drills-polish-plan.md`
**Branch target:** `feat/lrr-phase-10-observability-drills-polish`
**Cross-epic authority:** `docs/research/2026-04-14-cross-epic-fold-in-lrr-hsea.md` (drop #62) — §5 row UP-13 (LRR Phase 10 is the terminal phase of the LRR side of UP-13 observability)
**Unified phase mapping:** UP-13 observability layer (shared with HSEA Phases 7 + 12 long-tail integration)

---

## 1. Phase goal

Ship the polish layer that makes LRR defensible as a continuous research instrument: per-condition Prometheus slicing, stimmung dashboards, the 18-item continuous-operation stability matrix, the operational drills suite, the FINDING-S SDLC pipeline decision, T3 prompt caching, PERCEPTION_INTERVAL tuning, consent + surface audit trails, cross-repo scrape fixes, the 2-hour stability drill, optional in-process Prometheus exporters, weekly stimmung × stream correlation reports, and the pre/post stream stimmung delta protocol.

**What this phase is:** 14 items of observability + drills + polish. After Phase 10, LRR is complete and any future work is a new epic.

**What this phase is NOT:** this phase does not ship new substrate decisions (Phase 5a scope), new governance axioms (Phase 6 scope), new persona work (Phase 7 scope), new objectives (Phase 8 scope), or new closed-loop primitives (Phase 9 scope). Phase 10 is the hardening + validation layer over all prior phases.

---

## 2. Dependencies + preconditions

**Intra-epic:**

1. **LRR UP-11 (Phase 9 closed-loop feedback) closed.** All 9 Phase 9 deliverables merged + verified. Phase 10 monitors the closed-loop stack that Phase 9 ships; it cannot add observability over a closed loop that does not yet exist.

2. **LRR UP-1 through UP-11 all closed.** Phase 10 is the last LRR phase; its scope assumes all prior phases have landed. Per drop #62 §5 unified sequence.

**Cross-epic (from drop #62):**

3. **HSEA UP-2 (Phase 0 foundation primitives) closed.** Phase 10 deliverable 2 (stimmung dashboards) consumes HSEA Phase 0 deliverable 0.1 `WatchedQueryPool` via `shared/prom_query.py`. Without it, Phase 10 has no abstracted Prometheus client.

4. **HSEA UP-4 (Phase 1 visibility surfaces) closed.** Phase 10 deliverable 9 (per-surface visibility audit log) extends HSEA Phase 1's surface-registration pattern; needs the `SourceRegistry` interface.

5. **No direct drop #62 §10 operator-decision dependencies.** All 10 ratifications are substrate-independent relative to Phase 10 scope.

**Infrastructure:**

1. Prometheus running at `127.0.0.1:9090`; scrape jobs configured for all monitored services.
2. Grafana running at `127.0.0.1:3001` with existing hapax dashboards.
3. ntfy notification channel operational (for S1–S18 alert routing).
4. `shared/prom_query.py` from HSEA Phase 0 0.1 (shared Prometheus client + `WatchedQueryPool`).
5. `scripts/research-registry.py` from LRR Phase 1 (query active condition for `model_condition` label).
6. Cross-repo edit authority on `llm-stack/prometheus.yml` + `llm-stack/grafana-dashboards/` (for A11, A12, A13, Q023 polish items).
7. `systemd/units/` for new timers (weekly stimmung report).
8. `~/Documents/Personal/40-calendar/weekly/` directory for operator-facing reports.

---

## 3. Deliverables (14 items)

### 3.1 Per-condition Prometheus slicing (item 1)

Extend metrics with a `model_condition` label that flows from the research-marker SHM file (LRR Phase 1 deliverable 3) into every scored metric. Required labels:

- `tabbyapi_request_duration_seconds{model_condition="cond-phase-a-baseline-qwen-001"}`
- `stream_reactions_total{model_condition, activity}`
- `turn_pair_coherence_score{model_condition}`
- `voice_grounding_directive_compliance_rate{model_condition}`

**Target files:**
- `agents/studio_compositor/metrics.py` — extend label set, read condition_id from research marker on each metric emission
- `agents/hapax_daimonion/_telemetry.py` — same, for the voice-grounding DV metrics
- `shared/prom_query.py` consumer updates where relevant
- `tests/` — fixture-based label-injection tests

**Cardinality budget:** expected 2–3 active conditions × ~50 metric series × ~10 activity labels = ~1,500 series. Well within Prometheus TSDB capacity.

**Size:** ~300 LOC (metric-site edits + tests), 0.5 day.

### 3.2 Stimmung dashboards (item 2)

Grafana panels for:
- 11-dim stimmung time-series by condition
- Stance transition frequency
- SEEKING dwell time
- Auto-private trigger count per day
- Correlation with activity selection
- Correlation with chat engagement

**Target files:**
- `grafana/dashboards/stimmung-research.json` (new dashboard)
- Grafana dashboard provisioning if not already in place (`llm-stack/grafana-dashboards/`)

**Size:** ~200 lines of JSON dashboard config, 0.5 day.

### 3.3 18-item continuous-operation stability matrix (item 3)

Per GDO 2026-04-09 handoff, reframed as indefinite-horizon monitoring (not launch gates). Each item is a Prometheus series + alert rule routing to ntfy + Grafana annotation.

| # | Item | Metric | Alert |
|---|---|---|---|
| S1 | compositor frame stalls | `gst_frame_duration_seconds_bucket` | p99 > 40 ms for 5 min |
| S2 | compositor GPU memory growth | `nvidia_smi_process_memory{process="studio-compositor"}` | slope > 10 MiB/hour |
| S3 | v4l2sink renegotiation cascade | `v4l2_caps_negotiation_total` | rate > 0.1/s |
| S4 | audio capture thread death | `compositor_audio_capture_alive` | 0 for > 30s |
| S5 | youtube-player ffmpeg death | `youtube_player_ffmpeg_alive` | 0 for > 30s |
| S6 | chat-downloader reconnect | `chat_monitor_reconnect_total` | rate > 1/min |
| S7 | album-identifier memory growth | `album_identifier_process_memory` | slope > 5 MiB/hour |
| S8 | logos-api connection pool | `logos_api_http_connections_open` | > 100 |
| S9 | token-ledger write latency | `token_ledger_write_duration_ms` | p99 > 100 ms |
| S10 | Pi NoIR heartbeat | `pi_noir_heartbeat_age_seconds` | > 120 |
| S11 | PipeWire mixer_master alive | `pipewire_node_alive{name="mixer_master"}` | 0 |
| S12 | NVENC encoder session count | `nvidia_encoder_session_count` | > 3 |
| S13 | YouTube RTMP connection | `rtmp_connection_state` | != "connected" for > 30s |
| S14 | /dev/video42 loopback write | `v4l2_loopback_write_rate{device="video42"}` | = 0 for > 10s |
| S15 | /data inode usage | `node_filesystem_files_free{mountpoint="/data"}` | < 15% free |
| S16 | /dev/shm growth | `node_filesystem_used_bytes{mountpoint="/dev/shm"}` | > 8 GiB |
| S17 | HLS segment pruning | `hls_segment_count` | > 1000 |
| S18 | hapax-rebuild-services interference | `rebuild_services_mid_stream_events` | rate > 1/hour |

**Target files:**
- `llm-stack/prometheus-alerts.yml` — 18 new alert rules
- `grafana/dashboards/stability-matrix.json` — dashboard showing all 18 series
- Any missing metric-emission code for S2 / S7 / S18 (most metrics already exist from prior phases + FDL-1)

**Size:** ~400 lines across alert rules + dashboard JSON + any missing metric emitters, 1 day.

### 3.4 Operational drills (item 4)

Run each at least once; document results in `docs/drills/2026-*.md`:
- Pre-stream consent verification drill
- Mid-stream consent revocation drill (covered in Phase 6; re-verify here)
- Stimmung breach → auto-private drill
- Failure-mode rehearsal (RTMP disconnect, Hermes 3/8B OOM, MediaMTX crash, v4l2loopback loss, Pi-6 network drop)
- Privacy regression suite under load
- Audience engagement A/B (research-mode chat behavior)

**Target files:**
- `docs/drills/2026-<date>-<drill-name>.md` (~6 new drill result docs)
- `scripts/run-drill.py` or equivalent orchestration script for repeatable drills (~200 LOC)
- `tests/` — any automated regression captures

**Size:** ~350 LOC drill harness + operator time for drill execution, 1 day.

### 3.5 FINDING-S SDLC pipeline decision (item 5)

Per alpha close-out retirement handoff. 324 dry-run events, 0 production executions, all 5 stages DORMANT. Present 3 options:

- **Option 1 — Retire.** Delete `.github/workflows/auto-fix.yml` + `claude-review.yml` + `profiles/sdlc-events.jsonl`. Free up CI minutes.
- **Option 2 — Revive.** Fix the 100%-failure workflows; dry-run for 2 weeks; reassess.
- **Option 3 — Integrate.** Use the SDLC pipeline's Triage → Plan → Implement → Review → Gate stages to orchestrate this epic's phase execution. Meaningful research artifact (Hapax orchestrating its own SDLC on the livestream) but substantial integration cost.

**Operator decision required. Default: Option 1 (retire) unless operator chooses otherwise.**

**Target files:**
- `docs/research/2026-<date>-finding-s-sdlc-decision.md` (decision record)
- Whichever GitHub Actions files are deleted / fixed / integrated, depending on option

**Size:** ~50 LOC if retire, ~500 LOC if revive, ~1,500 LOC if integrate. Operator-gated.

### 3.6 T3 prompt caching redesign (item 6)

Per alpha close-out handoff. ~100 lines across 3 files, ~42% per-turn cost reduction on cache hits, 40-60% TTFT drop on 2nd+ turn within 5-min cache window. Pattern 3 (prompt caching with `cache_control` markers).

**Target files:**
- `agents/hapax_daimonion/persona.py` — add `cache_control: ephemeral` markers to the persona system prompt header
- `agents/hapax_daimonion/conversation_pipeline.py` — extend prompt assembly to preserve cache-control markers through LiteLLM
- `shared/config.py` — tier-aware cache-control: enable for `claude-sonnet`/`claude-opus` (which support Anthropic prompt caching); skip for `local-fast`/`coding`/`reasoning` (TabbyAPI/Qwen3.5-9B don't support the same pattern)
- Tests (fixture-based cache-control round-trip)

**Size:** ~100 LOC + ~80 LOC tests, 0.3 day. Important because hapax's substrate decision surfaces latency sensitivity.

**Drop #62 §14 note:** the original epic spec framed T3 as *"important because Hermes 3's TTFT is the stress risk."* With Hermes abandoned, the framing shifts to *"important because Qwen3.5-9B's hybrid-attention JIT first-call risk + whichever substrate wins beta's substrate research §9 recommendation"*. The cache-control pattern is substrate-independent.

### 3.7 `director_loop.py` PERCEPTION_INTERVAL tuning (item 7)

Per impact analysis §Performance. Original framing was for Hermes 3's longer response times overlapping with 8s perception cadence; with Hermes abandoned, the tuning still matters for any substrate where sustained generation time exceeds 8s (including Qwen3.5-9B under long-form research mode).

- Tune `PERCEPTION_INTERVAL` from 8s → 12s, OR make it dynamic based on last response latency
- Test under live traffic post-tune; verify no activity-selection drift

**Target files:**
- `agents/hapax_daimonion/director_loop.py` — interval tuning + dynamic logic
- `tests/` — fixture tests for dynamic interval

**Size:** ~50 LOC, 0.2 day.

### 3.8 Consent audit trail (item 8)

Surface per-contract audit log at `axioms/contracts/audit.jsonl`. Every contract create / revoke / enforce event logged. Queryable via `scripts/consent-audit.py`.

**Target files:**
- `shared/consent.py` — append-on-mutation pattern
- `axioms/contracts/audit.jsonl` — append-only log
- `scripts/consent-audit.py` (~120 LOC CLI with filtering by contract / actor / event-type / date range)
- `tests/shared/test_consent_audit.py` — append-round-trip + query tests

**Size:** ~250 LOC, 0.3 day.

### 3.9 Per-surface visibility audit log (item 9)

`/dev/shm/hapax-surface-audit.jsonl` — every time a surface is added or removed from the stream output, log it. Queryable for post-hoc analysis of what was visible when.

- Per-entry schema: `{timestamp, event, source_id, zone, condition_id, actor}`
- `event` ∈ `{added, removed, stale_fallback, render_failure}`

**Target files:**
- `agents/studio_compositor/source_registry.py` — extend to emit audit events on register/unregister
- HSEA Phase 1 Cairo sources — emit events on first render + last render before replacement
- `scripts/surface-audit-query.py` (~80 LOC)
- Tests (~80 LOC)

**Size:** ~200 LOC, 0.3 day.

### 3.10 PR #775 cross-repo polish (item 10)

Verify these landed (may have landed mid-epic); if not, ship:

- **A11** — LiteLLM scrape path fix `/metrics` → `/metrics/` in `llm-stack/prometheus.yml` (1 yaml line)
- **A12** — `studio-compositor` scrape job in `llm-stack/prometheus.yml` targeting `127.0.0.1:9482` (7 yaml lines) — the 6-month drift between "compositor exposes metrics" and "Prometheus scrapes them" must be closed as part of Phase 10
- **A13** — `ufw` rules for `172.18.0.0/16 → 9100, 9482` (operator-gated sudo; 2 commands)
- **Q023 #53** — Grafana dashboard panel fixes (cross-repo `llm-stack/grafana-dashboards/`)
- `node-exporter :9100` DOWN target restoration (Sprint 6; may already be done)
- Prometheus scrape gap for studio-compositor (queue 024 FINDING-H)

**Target files:** cross-repo `llm-stack/` changes; this repo adds a verification script `scripts/verify-phase-10-scrape-targets.py` (~100 LOC) that `curl`s Prometheus's targets API and asserts all expected jobs are `up`.

**Size:** ~150 LOC verification script + ~20 lines of cross-repo yaml + 2 sudo commands. Operator-gated on A13. Low-urgency but load-bearing for Phase 10 exit.

### 3.11 Uninterrupted 2-hour compositor stability drill (item 11)

R11 from alpha close-out retirement handoff. Run the compositor continuously under typical livestream load for 2 hours without operator intervention. Monitor: frame drops, memory growth, v4l2sink renegotiation events, GPU memory drift, cudacompositor element survival.

**Success criteria:** zero unhandled errors, memory footprint within ±5%, frame rate stable.

**Distinct from the 18-item matrix** (which is continuous monitoring); this is an explicit attended drill.

**Target files:**
- `scripts/run-stability-drill.py` (~200 LOC orchestration + metric capture)
- `docs/drills/2026-<date>-compositor-2h-stability.md` (results doc)

**Size:** ~200 LOC + operator time, 2 hours wall + 0.3 day docs.

### 3.12 Daimonion + VLA in-process Prometheus exporters (item 12)

**C2 from alpha close-out** — Daimonion in-process Prometheus exporter (~300 LOC). Raises signal quality beyond the current SHM-file-based metrics.

**C3 from alpha close-out** — VLA in-process Prometheus exporter (~200 LOC).

Phase 10 includes them as OPTIONAL polish — ship if time permits, defer if Phase 10 is already full. Neither is blocking.

**Target files:**
- `agents/hapax_daimonion/_prometheus.py` — in-process exporter with FastAPI sidecar
- `agents/visual_layer_aggregator/_prometheus.py` — same pattern
- `llm-stack/prometheus.yml` — scrape job additions
- Tests

**Size:** ~500 LOC, 0.8 day. Optional.

### 3.13 Weekly stimmung × stream correlation report (item 13)

Automated report: Saturday 08:00 local timer runs `scripts/weekly-stimmung-report.py`, aggregates the past 7 days of stimmung dimensions × stream events × reaction counts × operator sleep data, renders to a vault note at `~/Documents/Personal/40-calendar/weekly/YYYY-WW-stimmung-stream.md`.

Answers the standing question: *"is the stream net positive or net negative on operator cognitive load this week?"* Closes the `executive_function` axiom loop at the reporting cadence.

**Target files:**
- `scripts/weekly-stimmung-report.py` (~250 LOC with Prometheus + Qdrant + hapax-watch data sources)
- `systemd/user/hapax-weekly-stimmung-report.timer` + `.service`
- Tests (~100 LOC)

**Size:** ~350 LOC, 0.5 day.

### 3.14 Pre/post stream stimmung delta protocol (item 14)

Lightweight: at every stream-mode transition (off → public_research or reverse), capture a stimmung snapshot. Delta analysis in the weekly report.

Operator-side observation: brief subjective 1-5 rating logged via a Stream Deck button or voice command after each streaming session. Qualitative companion to the quantitative stimmung time series.

**Target files:**
- `agents/hapax_daimonion/stimmung_snapshot.py` (~100 LOC, hooks into stream-mode transitions)
- `scripts/log-stream-rating.py` (~60 LOC, voice-triggered)
- Stream Deck config snippet for the rating button
- Tests (~80 LOC)

**Size:** ~240 LOC, 0.3 day.

---

## 4. Phase-specific decisions since epic authored

Drop #62 fold-in (2026-04-14) + operator ratifications (2026-04-15) + Hermes abandonment (drop #62 §14) introduce the following clarifications relative to the epic spec §5 Phase 10:

1. **Drop #62 §14 Hermes reframing applies to item 6 (T3 prompt caching).** Original framing cited "Hermes 3's TTFT is the stress risk." With Hermes abandoned, the framing shifts to whichever substrate wins beta's research §9 recommendation — most likely Qwen3.5-9B (with hybrid-attention JIT mitigation via beta's assignment #2 `bafd6b34f` cache warmup) or OLMo 3-7B parallel (per research §9.3). The cache-control pattern itself is substrate-independent.

2. **Drop #62 §14 Hermes reframing applies to item 7 (PERCEPTION_INTERVAL tuning).** Same pattern: the interval-vs-response-latency concern is not Hermes-specific; it applies to any substrate where long-form generation exceeds the 8s perception cadence. Tune to 12s (static) or make it dynamic based on last response.

3. **`model_condition` label ownership** (item 1) matches LRR Phase 1 deliverable 5. Phase 10 is the phase that finally exercises the condition label through every metric surface, closing the loop Phase 1 opened.

4. **HSEA Phase 0 `shared/prom_query.py` dependency** (item 2 + item 3) — Phase 10 consumes the WatchedQueryPool abstraction instead of raw `requests.get` calls. This is a cleaner pattern than the epic spec envisioned and was made possible by drop #62's HSEA fold-in.

5. **HSEA Phase 1 `SourceRegistry` dependency** (item 9) — per-surface visibility audit log extends the HSEA Phase 1 / LRR Phase 2 `SourceRegistry` with an audit-event emission path. Surface-adds / surface-removes are captured as audit events rather than inferred from logs.

6. **Drop #62 §10 Q8 state file ratification** — Phase 10 weekly stimmung report (item 13) may want to reference the shared `research-stream-state.yaml` index for per-UP unified-phase activity over the week. Currently out of scope; note for future reports.

7. **No direct operator-decision blockers.** Item 5 (FINDING-S) is operator-gated but phased-in: Phase 10 can ship items 1–4 + 6–14 without Item 5 resolved; Item 5 closes at operator's convenience.

---

## 5. Exit criteria

Phase 10 closes when ALL of the following are verified:

1. All 18 stability matrix items (§3.3) have Prometheus series + alert rules; alerts verified via at least one synthetic trigger each
2. Grafana stimmung dashboard (§3.2) operational; panels show current data with per-condition slicing
3. All 6 operational drills (§3.4) run at least once; results in `docs/drills/2026-*.md`
4. FINDING-S decision (§3.5) made and committed (retire / revive / integrate)
5. T3 prompt caching (§3.6) landed; TTFT improvement observed on 2nd-turn calls
6. PERCEPTION_INTERVAL tuning (§3.7) applied; no activity-selection drift in logs
7. Consent audit trail (§3.8) queryable via `scripts/consent-audit.py`
8. Per-surface visibility audit log (§3.9) operational
9. Per-condition Prometheus slicing (§3.1) operational; verify via `curl http://localhost:9482/metrics | grep model_condition`
10. Cross-repo scrape fixes (§3.10) landed: A11, A12, A13, Q023. Verify via `curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[].labels.job'` includes `studio-compositor`
11. Uninterrupted 2-hour compositor stability drill (§3.11) run and documented; zero unhandled errors, memory footprint within ±5%, frame rate stable
12. C2 + C3 Daimonion + VLA in-process Prometheus exporters (§3.12) live OR explicitly deferred with rationale
13. Weekly stimmung × stream correlation report (§3.13) runs via systemd timer; at least one week's report generated
14. Pre/post stream stimmung delta protocol (§3.14) operational; at least one stream-mode transition captured with pre + post snapshots + operator subjective rating
15. Privacy regression suite (§3.4 partial) has a test that scrapes rendered compositor frames for any text matching known operator utterance patterns (catches voice-transcript firewall regressions)
16. **Handoff doc written** at `docs/superpowers/handoff/2026-<date>-lrr-phase-10-complete.md` — LRR is DONE after Phase 10; this handoff is the epic's final retirement artifact

---

## 6. Risks + mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Per-condition labels multiply metric cardinality beyond Prometheus TSDB capacity | MEDIUM | Prometheus scrape failures / alert drift | Cardinality budget documented in §3.1; monitor TSDB size; drop low-value labels if approaching limit |
| Drills surface new issues that balloon Phase 10 scope | HIGH | Phase 10 never closes | Drill failures become separate follow-up issues (LRR is done after Phase 10; new work is a new epic) |
| T3 prompt caching changes prompt structure and breaks substrate behavior | MEDIUM | Cache-control markers confuse non-Anthropic substrates | Tier-aware cache-control enable (claude tiers only); skip for `local-fast`/`coding`/`reasoning` routes |
| Cross-repo `llm-stack/` edits (A11/A12/Q023) land late or require operator-gated sudo (A13) | LOW | Phase 10 waits on cross-repo PR cycle | `llm-stack/` is a sibling repo; yaml PRs are typically fast; A13 operator coordination at phase close |
| 2-hour stability drill fails due to pre-existing compositor bug | MEDIUM | Phase 10 blocked on fix | Compositor is pre-Phase-10 territory; failures become follow-up tickets; drill is re-run after fix |
| FINDING-S operator decision delayed | HIGH | Item 5 blocks Phase 10 close | Item 5 is phaseable: if operator defaults to Option 1 (retire), Phase 10 closes with a retirement commit; if operator wants Option 2 or 3, Phase 10 exits with item 5 as explicit deferred work |
| Daimonion + VLA in-process exporters (item 12) conflict with existing SHM-file-based metric emission | LOW | Duplicate metric series | Exporters are opt-in; SHM path stays as fallback until exporters are stable |

---

## 7. Open questions

1. **FINDING-S — retire / revive / integrate?** Operator decision required at phase open or early in phase. Default: retire (Option 1).
2. **T3 prompt caching tier scope — Anthropic only, or also include TabbyAPI EXL3 runtime once `exllamav3` adds prefix-cache-reuse hints?** Currently Anthropic-only per the epic spec. If exllamav3 0.0.30+ adds an equivalent cache-control surface, Phase 10 can be extended.
3. **Cardinality budget ceiling** — how many active conditions × activities × dimensions before Prometheus cardinality bites? Operator may need to set a hard cap.
4. **Operator Stream Deck button availability** for item 14 — if no Stream Deck button is available, voice-only rating path is the fallback.
5. **llm-stack cross-repo coordination** — who has write authority on `llm-stack/prometheus.yml`? Assumed to be the same operator that owns the hapax-council repo.

---

## 8. Companion plan doc

TDD checkbox task breakdown at `docs/superpowers/plans/2026-04-15-lrr-phase-10-observability-drills-polish-plan.md`.

**Execution order inside Phase 10 (single session, sequential where possible; parallelizable where noted):**

1. **Item 1 (per-condition Prometheus slicing)** — ships first because every other observability item uses the `model_condition` label
2. **Item 10 (PR #775 cross-repo polish: A11 + A12 + A13 + Q023)** — ships second because item 3 stability matrix alerts depend on scrape targets being live
3. **Item 3 (18-item stability matrix)** — alerts + dashboard
4. **Item 2 (stimmung dashboards)** — can parallelize with item 3 after item 1
5. **Item 6 (T3 prompt caching)** — parallelizable; small
6. **Item 7 (PERCEPTION_INTERVAL tuning)** — parallelizable; trivial
7. **Item 8 (consent audit trail)** — parallelizable
8. **Item 9 (per-surface visibility audit log)** — parallelizable
9. **Item 4 (operational drills)** — ships after items 1–3 because drills verify the observability
10. **Item 5 (FINDING-S decision)** — operator-gated; can ship anytime
11. **Item 11 (2-hour stability drill)** — ships after items 1+3 land so observability captures the drill
12. **Item 12 (C2 + C3 in-process exporters)** — optional; ships if bandwidth
13. **Item 13 (weekly stimmung report)** — ships after item 1 so reports have per-condition labels
14. **Item 14 (pre/post stream stimmung delta)** — ships last; integrates with item 13 reporting
15. **Exit criteria verification + handoff doc**

---

## 9. End

This spec extracts LRR epic spec §5 Phase 10 (lines 1110–1222) into a standalone per-phase design doc following the LRR extraction pattern delta established for Phase 1/2/7/8/9. It incorporates drop #62 §14 Hermes abandonment reframing for items 6 and 7, and cross-references HSEA Phase 0 + HSEA Phase 1 + LRR Phase 2 dependencies that the original epic spec did not enumerate.

Phase 10 is the terminal phase of LRR. After Phase 10 closes, the LRR epic is complete. Any future research-infrastructure work is a new epic — expected candidates include the HSEA UP-12 cluster basket + any follow-up on beta's substrate research recommendations.

This spec is pre-staging. It does not open Phase 10. Phase 10 opens only when LRR UP-11 (Phase 9) and HSEA UP-2 + UP-4 + UP-11 have closed.

— beta (PR #819 author) per delta's nightly queue Item #14, 2026-04-15
