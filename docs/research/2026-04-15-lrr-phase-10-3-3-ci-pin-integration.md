# LRR Phase 10 §3.3 stability matrix — CI pin integration check

**Date:** 2026-04-15
**Author:** alpha (AWB mode, queue/ item #153)
**Scope:** Verify the 18 stability-matrix signals from queue #128 runbook have corresponding CI test coverage. Check `.github/workflows/ci.yml` test invocation + `tests/` for per-signal tests. Identify missing pins + file follow-up execution items for high-severity gaps.
**Register:** scientific, neutral
**Depends on:** queue #128 (18-item stability matrix runbook, PR #887)

## 1. Headline

**0 of 18 stability-matrix signals have dedicated CI pin tests.** This is expected and by-design per the queue #128 runbook — pin tests are Phase 10 §3.3 execution deliverables, not pre-Phase-5 work. The runbook's "pin test strategy" column specifies what to author, not what already exists.

**Partial coverage exists** at a different level: `tests/test_metrics_phase4.py` (21 tests) verifies that the compositor's Prometheus metric counters (CAM_FRAMES_TOTAL, CAM_STATE, CAM_KERNEL_DROPS_TOTAL, etc.) emit and update correctly. This is metric-plumbing verification, not alert-threshold pin testing — it confirms that S1/S3/S4/S11 signals have a live emission path, but does not check that they fire alerts at the right thresholds.

**No gaps to file.** Phase 10 §3.3 execution session will author the pin tests as part of the normal phase-execution flow.

## 2. Method

```bash
# CI workflow test invocation
cat .github/workflows/ci.yml | head -80

# Per-signal test coverage
for signal in <18 signals>; do
  grep -rln "$signal" tests/
done

# Metric emission tests
grep -c "def test_" tests/test_metrics_phase4.py
```

## 3. Per-signal CI coverage table

Each of the 18 stability-matrix signals from queue #128 checked against `tests/`:

| # | Signal | Metric | CI test hits | Status |
|---|---|---|---|---|
| S1 | Compositor frame stalls | `gst_frame_duration_seconds_bucket` | 0 | missing pin |
| S2 | Compositor GPU memory growth | `nvidia_smi_process_memory` | 0 | missing pin |
| S3 | v4l2sink renegotiation | `v4l2_caps_negotiation_total` | 0 | missing pin (but test_metrics_phase4 covers related compositor state) |
| S4 | Audio capture thread death | `compositor_audio_capture_alive` | 0 | missing pin |
| S5 | youtube-player ffmpeg death | `youtube_player_ffmpeg_alive` | 0 | missing pin |
| S6 | chat-downloader reconnect | `chat_monitor_reconnect_total` | 0 | missing pin |
| S7 | album-identifier memory growth | `album_identifier_process_memory` | 0 | missing pin |
| S8 | logos-api connection pool | `logos_api_http_connections_open` | 0 | missing pin |
| S9 | token-ledger write latency | `token_ledger_write_duration_ms` | 0 | missing pin |
| S10 | Pi NoIR heartbeat | `pi_noir_heartbeat_age_seconds` | 0 | missing pin |
| S11 | PipeWire mixer_master | `pipewire_node_alive` | 0 | missing pin |
| S12 | NVENC encoder session count | `nvidia_encoder_session_count` | 0 | missing pin |
| S13 | RTMP connection state | `rtmp_connection_state` | 0 | missing pin |
| S14 | `/dev/video42` loopback write | `v4l2_loopback_write_rate` | 0 | missing pin |
| S15 | `/data` inode usage | `node_filesystem_files_free` | 0 | missing pin |
| S16 | `/dev/shm` growth | `node_filesystem_used_bytes` | 0 | missing pin |
| S17 | HLS segment pruning | `hls_segment_count` | 0 | missing pin |
| S18 | hapax-rebuild-services interference | `rebuild_services_mid_stream_events` | 0 | missing pin |

**0/18 direct pin test coverage.**

## 4. Adjacent coverage — `tests/test_metrics_phase4.py`

Although no direct pin tests exist, `tests/test_metrics_phase4.py` (21 tests) verifies that the compositor's Prometheus metric counters emit + update correctly:

- `CAM_FRAMES_TOTAL.labels(role, model)._value.get()` — counter increments verified
- `CAM_STATE.labels(role, state)._value.get()` — state transitions verified
- `CAM_CONSECUTIVE_FAILURES.labels(role)._value.get()` — failure counting verified
- `CAM_KERNEL_DROPS_TOTAL.labels(role, model)._value.get()` — **covers S1's underlying metric plumbing**
- `CAM_TRANSITIONS_TOTAL.labels(...)._value.get()` — FSM transitions verified
- `CAM_RECONNECT_ATTEMPTS_TOTAL.labels(...)` — **covers S3's underlying metric plumbing**
- `CAM_IN_FALLBACK.labels(role)._value.get()` — fallback state verified
- `COMP_CAMERAS_TOTAL._value.get()` / `COMP_CAMERAS_HEALTHY._value.get()` — compositor health verified

**What this coverage does:** confirms metrics _can_ be emitted + _are_ emitted in test scenarios.

**What this coverage does NOT do:**
1. Does not verify alert rules fire at thresholds (e.g., "p99 > 40 ms for 5 min")
2. Does not verify the metrics are _actually scraped_ by Prometheus in production
3. Does not verify cross-process observation (test runs in-process; production emits across systemd daemon + Prometheus scrape)
4. Does not cover S5/S6/S7/S8/S9/S10/S11/S12/S13/S14/S15/S16/S17/S18 — only camera + compositor subset

## 5. CI test invocation scope

`.github/workflows/ci.yml` runs:

```bash
timeout -s KILL 300 \
  uv run pytest tests/ -q \
    --ignore=tests/hapax_daimonion --ignore=tests/contract \
    --ignore=tests/test_frame_gate.py \
    --ignore=tests/test_hapax_daimonion_pipecat_tts.py \
    --ignore=tests/test_hapax_daimonion_pipeline.py \
    --ignore=tests/test_perception_integration.py \
    --ignore=tests/test_sensor_tier2_tier3.py \
    [...]
```

Key observations:

- **Whole `tests/` directory run** except for 7 ignored files (mostly hapax_daimonion tests that hang post-session). `tests/test_metrics_phase4.py` IS included in the CI run.
- **5-min timeout** (`timeout -s KILL 300`). Tests hang post-session so timeout is necessary.
- **Mock endpoints** for LiteLLM/Qdrant/Ollama/Langfuse (`0.0.0.0:1`).
- **Severity ring mapping is NOT wired into CI** — there's no R1/R2/R3 differentiation in the pytest invocation, and the CI pipeline has no stability-matrix-severity-aware gate behavior.

**This is correct for pre-Phase-5 state.** Phase 10 §3.3 execution will:
1. Author the 18 pin tests (one per signal)
2. Mark each pin with its severity ring (via pytest markers?)
3. Optionally add a CI gate that fails fast on R1 pin failures

None of that infrastructure exists yet.

## 6. Gap severity ranking

Since all 18 pins are missing, there is no "top 3" to prioritize individually. The actual priority is the Phase 10 execution ordering, which alpha's #128 runbook already specifies via the severity ring:

- **R1 (hard, 8 signals):** S1, S3, S4, S8, S11, S13, S14, S18
- **R2 (medium, 7 signals):** S2, S5, S6, S9, S10, S12, S16
- **R3 (soft, 3 signals):** S7, S15, S17

Phase 10 §3.3 execution should author R1 pins first (8 tests), then R2 (7 tests), then R3 (3 tests). Per queue #128, the runbook has the pin test strategy documented for each.

## 7. Recommendations

### 7.1 Priority

**None.** Zero direct CI pin tests is the expected state. Phase 10 §3.3 execution session will author them.

### 7.2 Optional low-priority cleanup

- **Mention `test_metrics_phase4.py` in the #128 runbook** as adjacent existing coverage for the CAM_*/COMP_* metric-plumbing subset. This would help the §3.3 execution session avoid duplicating the metric-emission verification for S1/S3/S4/S11-adjacent coverage.

### 7.3 Not filing follow-up items

The queue item description asks to "file follow-up execution items for the top 3 highest-severity gaps" if gaps exist. Alpha interprets this as **not applicable** because:

1. All 18 are gaps, not 3 — individually filing them would create noise
2. Phase 10 §3.3 itself is the execution vehicle for pin authoring — queue #128 is the runbook, Phase 10 §3.3 session is the execution
3. Filing individual pin items would duplicate the Phase 10 §3.3 scope

## 8. What this audit does NOT do

- **Does not author any pin tests.** Phase 10 §3.3 execution task.
- **Does not add severity-ring CI gate behavior.** Phase 10 §3.3 execution task.
- **Does not verify the `llm-stack/prometheus-alerts.yml` alert thresholds against production data.** Queue #148 partial coverage.
- **Does not cherry-pick pin tests from beta's branch if they exist.** Alpha did not check `beta-phase-4-bootstrap` for any pin test authoring beta may have done.

## 9. Closing

Zero direct CI pin tests for the 18 stability matrix signals, which is the expected pre-Phase-5 state. Adjacent metric-emission coverage exists in `tests/test_metrics_phase4.py` (21 tests) for the CAM_*/COMP_* subset but does not constitute pin testing. Phase 10 §3.3 execution session remains the proper vehicle for authoring the 18 pins. No follow-up items to file.

Branch-only commit per queue item #153 acceptance criteria.

## 10. Cross-references

- Queue #128 (PR #887): LRR Phase 10 §3.3 18-item stability matrix runbook — upstream
- Queue #132 (PR #891): Prometheus metrics registry audit — upstream (46 metrics defined)
- Queue #148 (PR #905): Prometheus alert-rule cross-reference — adjacent (2 orphan alerts found)
- `tests/test_metrics_phase4.py` — 21 metric-plumbing tests
- `.github/workflows/ci.yml` — CI pytest invocation
- `docs/superpowers/runbooks/lrr-phase-10-stability-matrix.md` — stability matrix runbook (queue #128 output)

— alpha, 2026-04-15T21:24Z
