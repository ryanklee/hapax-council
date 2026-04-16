# LRR Phase 10 — Observability, Drills, Polish — Plan

**Date:** 2026-04-15
**Author:** beta (pre-staging extraction per delta's nightly queue Item #14 / #45; pattern matches delta's LRR Phase 1/2/7/8/9 plans)
**Status:** DRAFT pre-staging — awaiting LRR UP-11 (Phase 9) close + HSEA UP-2/UP-4 close
**Spec reference:** `docs/superpowers/specs/2026-04-15-lrr-phase-10-observability-drills-polish-design.md`
**Epic reference:** `docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md` §5 Phase 10
**Branch target:** `feat/lrr-phase-10-observability-drills-polish`

---

## 0. Preconditions

- [ ] **LRR UP-11 (Phase 9 closed-loop feedback) closed.** Check `~/.cache/hapax/relay/lrr-state.yaml::phase_statuses[9].status == closed`
- [ ] **HSEA UP-2 (Phase 0 foundation primitives) closed.** Provides `shared/prom_query.py` used by items 2 + 3
- [ ] **HSEA UP-4 (Phase 1 visibility surfaces) closed.** Provides `SourceRegistry` used by item 9
- [ ] **Prometheus reachable** at `127.0.0.1:9090`; `curl -s http://localhost:9090/api/v1/targets` returns JSON with expected scrape jobs
- [ ] **Grafana reachable** at `127.0.0.1:3001`; existing hapax dashboards load
- [ ] **`llm-stack/` sibling repo** checked out and editable (item 10 A11/A12/Q023 are cross-repo yaml edits)
- [ ] **Session claims the phase:** write `hsea-state.yaml` + `lrr-state.yaml::phase_statuses[10].status: open` + `current_phase_branch: feat/lrr-phase-10-observability-drills-polish`
- [ ] **Operator availability** for item 5 FINDING-S decision + item 11 2-hour drill + item 14 subjective rating

---

## 1. Item 1 — Per-condition Prometheus slicing (ships first; unblocks items 2 + 3 + 13)

### 1.1 Test scaffolding

- [ ] Create `tests/agents/studio_compositor/test_metrics_model_condition.py`:
  - [ ] `test_metric_emitted_with_model_condition_label` — fixture `research_marker.json` with `cond-phase-a-baseline-qwen-001`; emit a metric; assert label present
  - [ ] `test_metric_without_active_condition_falls_back` — no marker file; metric emitted with `model_condition="none"` or similar sentinel
  - [ ] `test_marker_stale_detection` — stale marker (mtime > 30 s old); metric emitted with `model_condition="stale"`
- [ ] Create `tests/agents/hapax_daimonion/test_telemetry_model_condition.py` for the voice-grounding DV side

### 1.2 Implementation

- [ ] `agents/studio_compositor/metrics.py` — extend every metric emission site with `model_condition=_read_current_condition_id()` (use `shared/research_marker.read_research_marker`)
- [ ] `agents/hapax_daimonion/_telemetry.py` — same pattern for `hapax_score` + `hapax_bool_score` emissions; use existing `metadata` kwarg from the Phase 4 plumbing
- [ ] `shared/research_marker.py` — if not already present, add a convenience `current_condition_id_or_none() -> str | None` function

### 1.3 Commit

- [ ] Run tests; all pass
- [ ] `git commit -m "feat(lrr-phase-10): 1.1 per-condition Prometheus slicing with model_condition label"`
- [ ] Update `lrr-state.yaml::phase_statuses[10].deliverables[0.1].status: completed`

---

## 2. Item 10 — Cross-repo scrape fixes (ships second; unblocks item 3 stability matrix alerts)

### 2.1 A11 — LiteLLM scrape path fix

- [ ] In `llm-stack/prometheus.yml`, find the LiteLLM scrape job; change `metrics_path: /metrics` → `metrics_path: /metrics/`
- [ ] Commit to `llm-stack/` (cross-repo)
- [ ] Wait for Prometheus config reload; verify via `curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="litellm") | .health'` returns `"up"`

### 2.2 A12 — studio-compositor scrape job

- [ ] In `llm-stack/prometheus.yml`, add:
  ```yaml
  - job_name: studio-compositor
    scrape_interval: 15s
    static_configs:
      - targets: ['host.docker.internal:9482']
  ```
- [ ] Commit to `llm-stack/`
- [ ] Verify via `curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="studio-compositor")'` returns an entry

### 2.3 A13 — ufw rules (operator-gated sudo)

- [ ] Operator runs: `sudo ufw allow from 172.18.0.0/16 to any port 9100 proto tcp` + same for 9482
- [ ] Verify via `sudo ufw status | grep -E "9100|9482"`

### 2.4 Q023 — Grafana dashboard panel fixes

- [ ] In `llm-stack/grafana-dashboards/`, fix whichever panel broke per drop #23 / queue 023
- [ ] Commit to `llm-stack/`

### 2.5 Verification script

- [ ] Create `scripts/verify-phase-10-scrape-targets.py` (~100 LOC):
  - [ ] Queries `http://localhost:9090/api/v1/targets`
  - [ ] Asserts expected job list present: `litellm`, `studio-compositor`, `node-exporter`, `tabbyapi`, `hapax-logos-api`, etc.
  - [ ] Exits 0 on all-up, non-zero otherwise
- [ ] Run the script; all targets up
- [ ] `git commit -m "feat(lrr-phase-10): 10 cross-repo scrape target verification"`

---

## 3. Item 3 — 18-item continuous-operation stability matrix (depends on items 1 + 10)

### 3.1 Prometheus alert rules

- [ ] Create/edit `llm-stack/prometheus-alerts.yml` with 18 rules per spec §3.3 table
- [ ] Each rule has `severity: warning` or `severity: critical` label
- [ ] Each rule routes to ntfy via Alertmanager config
- [ ] Commit to `llm-stack/`

### 3.2 Grafana dashboard

- [ ] Create `grafana/dashboards/stability-matrix.json` with 18 panels (one per matrix item)
- [ ] Each panel plots the relevant metric + threshold line
- [ ] Commit to this repo (or `llm-stack/grafana-dashboards/` if that's the canonical location)

### 3.3 Missing metric emitters

- [ ] S2 compositor GPU memory slope — verify metric exists from FDL-1; if not, add emitter
- [ ] S7 album-identifier memory growth — verify; add if missing
- [ ] S18 `rebuild_services_mid_stream_events` — verify; add counter emission if missing

### 3.4 Synthetic trigger tests

- [ ] For each of the 18 rules, trigger the condition once (e.g., simulate frame stall via test harness) and verify the alert fires + ntfy is received
- [ ] Document triggered alerts in `docs/drills/2026-<date>-stability-matrix-alert-verification.md`

### 3.5 Commit

- [ ] `git commit -m "feat(lrr-phase-10): 3 18-item continuous-operation stability matrix"`

---

## 4. Item 2 — Stimmung dashboards (parallelizable with item 3 after item 1)

- [ ] Create `grafana/dashboards/stimmung-research.json` with panels per spec §3.2:
  - [ ] 11-dim stimmung time-series by condition
  - [ ] Stance transition frequency
  - [ ] SEEKING dwell time
  - [ ] Auto-private trigger count per day
  - [ ] Correlation with activity selection
  - [ ] Correlation with chat engagement
- [ ] Test dashboard loads + data flows from Prometheus
- [ ] `git commit -m "feat(lrr-phase-10): 2 stimmung research dashboards"`

---

## 5. Item 6 — T3 prompt caching redesign (parallelizable; small)

- [ ] `agents/hapax_daimonion/persona.py` — wrap persona system prompt header with `{"type": "text", "text": "...", "cache_control": {"type": "ephemeral"}}` block
- [ ] `agents/hapax_daimonion/conversation_pipeline.py` — preserve cache-control markers through LiteLLM call construction
- [ ] `shared/config.py` — gate cache-control on model tier (Anthropic tiers only)
- [ ] Test: fixture call with cache-control; verify round-trip preserved
- [ ] `git commit -m "feat(lrr-phase-10): 6 T3 prompt caching (Anthropic ephemeral)"`

---

## 6. Item 7 — PERCEPTION_INTERVAL tuning (parallelizable; trivial)

- [ ] `agents/hapax_daimonion/director_loop.py` — change `PERCEPTION_INTERVAL = 8` → `12` (or make dynamic based on last response latency)
- [ ] Test: director loop fires at 12s cadence
- [ ] `git commit -m "feat(lrr-phase-10): 7 PERCEPTION_INTERVAL tuning 8s -> 12s"`

---

## 7. Item 8 — Consent audit trail (parallelizable)

- [ ] `shared/consent.py` — append-on-mutation pattern: every create/revoke/enforce writes a line to `axioms/contracts/audit.jsonl`
- [ ] `scripts/consent-audit.py` — CLI with filtering by contract / actor / event / date range
- [ ] Tests: round-trip + query coverage
- [ ] `git commit -m "feat(lrr-phase-10): 8 consent audit trail + CLI"`

---

## 8. Item 9 — Per-surface visibility audit log (parallelizable)

- [ ] `agents/studio_compositor/source_registry.py` — emit audit events to `/dev/shm/hapax-surface-audit.jsonl` on register/unregister
- [ ] HSEA Phase 1 Cairo sources — emit on first render + last render before replacement
- [ ] `scripts/surface-audit-query.py` — CLI
- [ ] Tests
- [ ] `git commit -m "feat(lrr-phase-10): 9 per-surface visibility audit log"`

---

## 9. Item 4 — Operational drills (after items 1 + 3)

Each drill is a discrete attended execution; document in `docs/drills/`.

- [ ] **Pre-stream consent verification drill** — verify all active contracts before stream start
- [ ] **Mid-stream consent revocation drill** — trigger revocation mid-stream; verify cascade per Phase 6 §3.2
- [ ] **Stimmung breach → auto-private drill** — synthetically drive stimmung to critical; verify stream mode flips to private
- [ ] **Failure-mode rehearsal** — 5 sub-drills (RTMP disconnect, OOM, MediaMTX crash, v4l2loopback loss, Pi-6 network drop)
- [ ] **Privacy regression suite under load** — run the regression suite while stream is under synthetic chat load
- [ ] **Audience engagement A/B** — research-mode chat behavior measurement
- [ ] `scripts/run-drill.py` — orchestration harness for repeatable drills
- [ ] `docs/drills/2026-<date>-<drill>.md` — 6 result docs

---

## 10. Item 5 — FINDING-S SDLC pipeline decision (operator-gated)

- [ ] Write `docs/research/2026-<date>-finding-s-sdlc-decision.md` presenting the 3 options (retire / revive / integrate) with beta's recommendation (default: retire)
- [ ] Wait for operator input
- [ ] Execute the chosen option
- [ ] `git commit -m "chore(sdlc): FINDING-S decision — <option>"`

---

## 11. Item 11 — Uninterrupted 2-hour compositor stability drill

- [ ] `scripts/run-stability-drill.py` — orchestration + metric capture (~200 LOC)
- [ ] Execute drill: 2 hours continuous compositor under typical livestream load
- [ ] Monitor: frame drops, memory growth, v4l2sink renegotiation, GPU memory drift, cudacompositor element survival
- [ ] Success: zero unhandled errors, memory footprint ±5%, frame rate stable
- [ ] `docs/drills/2026-<date>-compositor-2h-stability.md` results doc
- [ ] `git commit -m "feat(lrr-phase-10): 11 2-hour compositor stability drill harness + results"`

---

## 12. Item 12 — C2 + C3 Daimonion + VLA in-process Prometheus exporters (optional)

- [ ] `agents/hapax_daimonion/_prometheus.py` (~300 LOC FastAPI sidecar)
- [ ] `agents/visual_layer_aggregator/_prometheus.py` (~200 LOC same pattern)
- [ ] `llm-stack/prometheus.yml` — scrape job additions
- [ ] Tests
- [ ] `git commit -m "feat(lrr-phase-10): 12 daimonion + VLA in-process Prometheus exporters"` OR defer with explicit rationale in handoff

---

## 13. Item 13 — Weekly stimmung × stream correlation report

- [ ] `scripts/weekly-stimmung-report.py` (~250 LOC): Prometheus query + Qdrant reaction count + hapax-watch sleep data + markdown rendering to `~/Documents/Personal/40-calendar/weekly/YYYY-WW-stimmung-stream.md`
- [ ] `systemd/user/hapax-weekly-stimmung-report.timer` + `.service` (Saturday 08:00 local)
- [ ] Tests: fixture-based report generation
- [ ] First report runs; verify vault note appears
- [ ] `git commit -m "feat(lrr-phase-10): 13 weekly stimmung × stream correlation report"`

---

## 14. Item 14 — Pre/post stream stimmung delta protocol

- [ ] `agents/hapax_daimonion/stimmung_snapshot.py` (~100 LOC): hooks into stream-mode transitions via Phase 6 stream-mode API
- [ ] `scripts/log-stream-rating.py` (~60 LOC): voice-triggered operator rating input
- [ ] Stream Deck button config snippet (operator action to wire)
- [ ] Tests: snapshot round-trip + rating log round-trip
- [ ] First transition captures pre + post snapshots
- [ ] `git commit -m "feat(lrr-phase-10): 14 pre/post stream stimmung delta protocol"`

---

## 15. Phase close

### 15.1 Exit criteria verification

- [ ] Run through the 16 exit criteria in spec §5; check each box
- [ ] Each failing criterion either ships or is explicitly deferred with rationale

### 15.2 Handoff doc

- [ ] Write `docs/superpowers/handoff/2026-<date>-lrr-phase-10-complete.md` — this is the epic's final retirement artifact (LRR is DONE after Phase 10)

### 15.3 State file updates

- [ ] `lrr-state.yaml::phase_statuses[10].status: closed`
- [ ] `lrr-state.yaml::current_phase: null`
- [ ] `lrr-state.yaml::last_completed_phase: 10`
- [ ] `research-stream-state.yaml::unified_sequence[UP-13].status: closed` (if shared index exists)

### 15.4 Celebration commit

- [ ] `git commit -m "chore(lrr): Phase 10 complete — LRR epic retired"`

---

## 16. Cross-epic coordination

- **HSEA Phase 10 Reflexive Stack (UP-13 sibling)** — HSEA Phase 10 is the F-cluster reflexive layers. LRR Phase 10 is LRR's observability polish. Distinct phases sharing the UP-13 label. No merge conflict risk.
- **HSEA Phase 12 Long-tail + Handoff (UP-13 terminal)** — HSEA's final phase is where HSEA's epic-close is written. LRR Phase 10 close is separate from HSEA Phase 12 close. Both can happen in either order.

---

## 17. End

This plan translates LRR Phase 10's 14 spec deliverables into a TDD checkbox execution breakdown. Execution order is documented in spec §8 + this plan's per-item ordering. Phase 10 closes the LRR epic.

— beta (PR #819 author) per delta's nightly queue Item #14 / #45, 2026-04-15
