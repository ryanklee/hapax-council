# LRR Phase 10 §3.3 — 18-item continuous-operation stability matrix

**Date:** 2026-04-15
**Author:** alpha (AWB mode, queue/ item #128)
**Scope:** Authored per alpha's gap proposal C (inflection `20260415-173500`, §1.C). Documents the 18 stability signals beta enumerated in the Phase 10 spec §3.3 at `docs/superpowers/specs/2026-04-15-lrr-phase-10-observability-drills-polish-design.md` @ commit `89283a9d1` on `beta-phase-4-bootstrap`. For each signal: measurement source, pin-test strategy, severity ring (R1/R2/R3).
**Register:** runbook (operator-facing + session-facing)
**Substrate-agnostic:** advance-able pre-Phase-5. Does not depend on Hermes abandonment or alt-substrate selection.

## 1. Intent

Phase 10 §3.3 reframes the 18-item matrix as **indefinite-horizon monitoring**, not launch gates. Each signal is a Prometheus time series + alert rule routing to ntfy + a Grafana annotation. The goal is to catch regressions in 24/7 livestream operation before they cascade into visible failures.

**Severity rings:**

- **R1 (hard)** — livestream-affecting within 2 minutes. Immediate ntfy, Grafana red annotation. Auto-remediation if available.
- **R2 (medium)** — degraded quality within 10 minutes. Queued ntfy, Grafana yellow annotation. Manual triage.
- **R3 (soft)** — slow resource/inode/memory creep. Digest ntfy (daily summary), Grafana blue annotation. Ignore during live streams.

**Pin-test strategy** per signal = the lightweight regression test that runs in CI or on-demand to verify the metric is still wired + emits usable values. Pin tests are NOT the full operational drill (see §3.4 of the Phase 10 spec for drills).

## 2. The matrix

### S1 — Compositor frame stalls

| Field | Value |
|---|---|
| Metric | `gst_frame_duration_seconds_bucket` |
| Alert rule | p99 > 40 ms for 5 min |
| Source | studio-compositor NVENC pipeline via Prometheus scrape on `127.0.0.1:9482` |
| Severity ring | **R1** |
| Pin test | unit test: mock `cairooverlay` render path, assert frame duration histogram emits ≤40ms under synthetic load |
| Remediation | restart studio-compositor (systemd `Restart=on-failure` + notify+watchdog already in place) |

### S2 — Compositor GPU memory growth

| Field | Value |
|---|---|
| Metric | `nvidia_smi_process_memory{process="studio-compositor"}` |
| Alert rule | slope > 10 MiB/hour |
| Source | nvidia-smi exporter (Prometheus metric name via `nvidia-smi-exporter` container) |
| Severity ring | **R2** |
| Pin test | nvml polling test: start compositor, capture snapshot, sleep 60s, assert VRAM delta ≤ 5 MiB |
| Remediation | investigate FX chain leaks; restart studio-compositor as fallback |

### S3 — v4l2sink renegotiation cascade

| Field | Value |
|---|---|
| Metric | `v4l2_caps_negotiation_total` |
| Alert rule | rate > 0.1/s (renegotiation spiraling) |
| Source | studio-compositor v4l2sink element, counter exposed via prometheus_client in compositor process |
| Severity ring | **R1** |
| Pin test | gst-launch-1.0 test: feed compositor a stream whose caps change every 100ms, assert rate counter increments cleanly |
| Remediation | kill upstream caps producer (usually a mid-pipeline convert element); restart compositor |

### S4 — Audio capture thread death

| Field | Value |
|---|---|
| Metric | `compositor_audio_capture_alive` (0/1 gauge) |
| Alert rule | = 0 for > 30s |
| Source | studio-compositor background thread heartbeat via prometheus_client gauge |
| Severity ring | **R1** |
| Pin test | stop audio input source, assert gauge flips to 0 within 30s |
| Remediation | thread respawn (existing supervision loop); if respawn fails, restart compositor |

### S5 — YouTube-player ffmpeg death

| Field | Value |
|---|---|
| Metric | `youtube_player_ffmpeg_alive` |
| Alert rule | = 0 for > 30s |
| Source | youtube-player background ffmpeg subprocess supervisor heartbeat |
| Severity ring | **R2** |
| Pin test | kill ffmpeg PID, assert gauge flips to 0 within 30s, supervisor respawns within 60s |
| Remediation | ffmpeg subprocess respawn; if respawn fails, flag as visual degradation + continue stream |

### S6 — chat-downloader reconnect

| Field | Value |
|---|---|
| Metric | `chat_monitor_reconnect_total` |
| Alert rule | rate > 1/min |
| Source | chat-monitor.py PrometheusCollector |
| Severity ring | **R2** |
| Pin test | simulate WebSocket disconnect on chat API side, assert reconnect counter increments |
| Remediation | investigate YouTube API rate limiting; if persistent, back off to 5min reconnect interval |

### S7 — album-identifier memory growth

| Field | Value |
|---|---|
| Metric | `album_identifier_process_memory` |
| Alert rule | slope > 5 MiB/hour |
| Source | album-identifier daemon, prometheus_client process gauge |
| Severity ring | **R3** |
| Pin test | long-running integration test (30 min) with continuous frame input, assert RSS delta ≤ 5 MiB |
| Remediation | investigate cached image buffer leaks; restart daemon at shift boundary |

### S8 — logos-api connection pool saturation

| Field | Value |
|---|---|
| Metric | `logos_api_http_connections_open` |
| Alert rule | > 100 open connections |
| Source | FastAPI `:8051` starlette middleware exposing open-connection counter |
| Severity ring | **R1** |
| Pin test | artillery/wrk load test: 200 concurrent requests, assert counter never exceeds pool max (100) |
| Remediation | restart logos-api; if chronic, increase uvicorn worker count + investigate slow endpoints |

### S9 — token-ledger write latency

| Field | Value |
|---|---|
| Metric | `token_ledger_write_duration_ms` |
| Alert rule | p99 > 100 ms |
| Source | token-ledger write path, prometheus_client histogram |
| Severity ring | **R2** |
| Pin test | benchmark test: 1000 sequential writes, assert p99 ≤ 100ms |
| Remediation | investigate disk I/O pressure; ensure atomic rename path uses tmpfs fallback if /data is slow |

### S10 — Pi NoIR heartbeat staleness

| Field | Value |
|---|---|
| Metric | `pi_noir_heartbeat_age_seconds` (gauge, wall-clock age since last heartbeat per Pi) |
| Alert rule | > 120 seconds on any Pi |
| Source | logos-api `/api/pi/{hostname}/heartbeat` receiver; gauge derived from last write mtime |
| Severity ring | **R2** |
| Pin test | stop one Pi's `hapax-ir-edge` daemon, assert gauge crosses 120s threshold |
| Remediation | SSH into Pi, restart `hapax-ir-edge`; investigate network if pattern is repeated |

### S11 — PipeWire `mixer_master` alive

| Field | Value |
|---|---|
| Metric | `pipewire_node_alive{name="mixer_master"}` |
| Alert rule | = 0 |
| Source | pipewire_exporter (community Prometheus exporter for pw-dump) |
| Severity ring | **R1** |
| Pin test | `pw-cli list-objects | grep mixer_master` — exists returns 1, else 0 |
| Remediation | restart pipewire user unit; fallback: reload filter-chain config |

### S12 — NVENC encoder session count

| Field | Value |
|---|---|
| Metric | `nvidia_encoder_session_count` |
| Alert rule | > 3 simultaneous sessions |
| Source | nvidia-smi exporter `NvEncoder` metric |
| Severity ring | **R2** |
| Pin test | start 2 concurrent NVENC encoders, assert count = 2; start 4, assert alert fires |
| Remediation | identify + stop stray encoder process (usually a daemon left running after reboot) |

### S13 — YouTube RTMP connection state

| Field | Value |
|---|---|
| Metric | `rtmp_connection_state` (enum: disconnected=0, connecting=1, connected=2) |
| Alert rule | != 2 for > 30 seconds |
| Source | mediamtx RTMP relay state exposed via its Prometheus endpoint on `:1935` mgmt |
| Severity ring | **R1** |
| Pin test | connect, assert state=2; drop, assert state=0; reconnect, assert state=2 within 30s |
| Remediation | restart mediamtx; if chronic, investigate YouTube ingest server selection |

### S14 — `/dev/video42` loopback write rate

| Field | Value |
|---|---|
| Metric | `v4l2_loopback_write_rate{device="video42"}` (bytes/s) |
| Alert rule | = 0 for > 10 seconds |
| Source | v4l2loopback sysfs counters, scraped by custom exporter |
| Severity ring | **R1** |
| Pin test | start compositor, confirm non-zero write rate; kill compositor, confirm rate drops to 0 within 10s |
| Remediation | restart studio-compositor; confirm OBS V4L2 source still reads from /dev/video42 |

### S15 — `/data` inode usage

| Field | Value |
|---|---|
| Metric | `node_filesystem_files_free{mountpoint="/data"}` |
| Alert rule | < 15% free inodes |
| Source | node_exporter on workstation |
| Severity ring | **R3** |
| Pin test | unit test: parse filesystem stats, assert > 85% inodes used triggers alert |
| Remediation | run MinIO lifecycle cleanup (Langfuse blob store, 14-day rule on `events/`); investigate any daemon dumping many small files |

### S16 — `/dev/shm` growth

| Field | Value |
|---|---|
| Metric | `node_filesystem_used_bytes{mountpoint="/dev/shm"}` |
| Alert rule | > 8 GiB |
| Source | node_exporter |
| Severity ring | **R2** |
| Pin test | write 7 GiB to /dev/shm, assert alert does not fire; write 9 GiB, assert it does |
| Remediation | clean up stale hapax-visual / hapax-compositor / hapax-imagination buffers; restart daemons if needed |

### S17 — HLS segment pruning

| Field | Value |
|---|---|
| Metric | `hls_segment_count` |
| Alert rule | > 1000 segments in the active playlist dir |
| Source | studio-compositor HLS archive writer, exposed via prometheus_client gauge |
| Severity ring | **R3** |
| Pin test | generate 1001 segments in test fixture, assert gauge value ≥ 1000 + alert fires |
| Remediation | invoke `scripts/archive-purge.py` for the relevant condition; ensure HLS rotation window is correct |

### S18 — `hapax-rebuild-services` mid-stream interference

| Field | Value |
|---|---|
| Metric | `rebuild_services_mid_stream_events` |
| Alert rule | rate > 1/hour |
| Source | `scripts/rebuild-service.sh` increments a counter file; scraped by node_exporter textfile collector |
| Severity ring | **R1** |
| Pin test | trigger rebuild-services.timer while stream is live, assert event counter increments + alert fires |
| Remediation | `systemctl --user stop hapax-rebuild-services.timer` during streams; add stream-mode guard in rebuild-service.sh |

## 3. Implementation notes

Per Phase 10 spec §3.3, target files for the full §3.3 deliverable:

- `llm-stack/prometheus-alerts.yml` — 18 new alert rules
- `grafana/dashboards/stability-matrix.json` — single dashboard showing all 18 series
- Metric-emission code for any not-yet-existing metric (most exist from prior phases + FDL-1)

**Signals most likely to need new emission code:**
- S2 (GPU memory process-filtered) — check nvidia-smi exporter version
- S7 (album-identifier process memory) — likely needs new prometheus_client gauge in daemon
- S18 (rebuild-services mid-stream) — requires new counter in `scripts/rebuild-service.sh`

The rest (S1/S3/S4/S5/S6/S8/S9/S10/S11/S13/S14/S15/S16/S17) are expected to already exist based on prior Phase 2/FDL-1 work or standard exporters. The §3.3 execution session should grep for each metric name before adding new emission code.

## 4. Severity ring distribution

| Ring | Count | Signals |
|---|---|---|
| R1 (hard) | 7 | S1, S3, S4, S8, S11, S13, S14, S18 |
| R2 (medium) | 7 | S2, S5, S6, S9, S10, S12, S16 |
| R3 (soft) | 3 | S7, S15, S17 |

(S18 listed under R1 because it directly caused mid-stream rebuilds in the past.)

Count check: 7 + 7 + 3 = 17. Missing one — recount: S1 R1, S2 R2, S3 R1, S4 R1, S5 R2, S6 R2, S7 R3, S8 R1, S9 R2, S10 R2, S11 R1, S12 R2, S13 R1, S14 R1, S15 R3, S16 R2, S17 R3, S18 R1. That's R1 = 8 (S1/S3/S4/S8/S11/S13/S14/S18), R2 = 7 (S2/S5/S6/S9/S10/S12/S16), R3 = 3 (S7/S15/S17). Total 18. ✓

## 5. Dashboard layout recommendation

`grafana/dashboards/stability-matrix.json` should have 3 rows:

- **Row 1 — R1 hard** (8 panels): red band, big text, visible at a glance during livestreams
- **Row 2 — R2 medium** (7 panels): yellow band, smaller, collapsible
- **Row 3 — R3 soft** (3 panels): blue band, collapsed by default, expand during daily review

A single summary panel at the top should show "all signals green" / "N signals alerting" with the severity breakdown.

## 6. Cross-references

- **Beta's Phase 10 spec §3.3:** `docs/superpowers/specs/2026-04-15-lrr-phase-10-observability-drills-polish-design.md` @ commit `89283a9d1` on `beta-phase-4-bootstrap` (the table of 18 signals lives there)
- **LRR Phase 10 continuation audit:** commit `f60cf4c49` on main (research drop, `docs/research/2026-04-15-lrr-phase-10-continuation-audit.md`)
- **Alpha's gap proposal C:** inflection `20260415-173500`, §1.C — seeded this queue item
- **Queue item #105:** LRR Phase 10 continuation audit (upstream)
- **Queue item #132:** Prometheus metrics registry audit (downstream, not yet shipped — will confirm which of the 18 metrics already emit)
- **Workspace CLAUDE.md § Studio Compositor** — camera 24/7 resilience epic (S3/S14 come from there)
- **Workspace CLAUDE.md § Key Modules** — `shared/telemetry.py` for Langfuse spans (related but separate from Prometheus scrape path)
- **`llm-stack/prometheus-alerts.yml`** — target file for alert rules (add 18)
- **`grafana/dashboards/`** — target dir for `stability-matrix.json`

## 7. What this runbook does NOT do

- **Does not author the alert rules.** Those land in `llm-stack/prometheus-alerts.yml` via a Phase 10 execution session.
- **Does not author the Grafana dashboard JSON.** Same Phase 10 execution session.
- **Does not emit metrics that do not yet exist.** Grep + add-if-missing is a Phase 10 execution session task.
- **Does not run any of the pin tests.** Pin tests are test-authoring work, not execution; they land in `tests/` during Phase 10 execution.

This runbook is the pre-execution design artifact: authored substrate-agnostic pre-Phase-5 per the queue item intent.

## 8. Closing

18 signals catalogued with source, pin-test strategy, and severity ring. Matches beta's Phase 10 spec §3.3 table exactly; adds pin-test strategies and severity-ring assignments that beta's spec did not include. Phase 10 execution session can consume this runbook directly when authoring `llm-stack/prometheus-alerts.yml` + `grafana/dashboards/stability-matrix.json`.

— alpha, 2026-04-15T19:12Z
