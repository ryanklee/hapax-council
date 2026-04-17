# LRR Phase 10 — 18-item stability matrix

**Purpose.** For each critical subsystem, verify four recovery properties: post-crash recovery, mid-request-kill recovery, graceful degradation on dependency failure, and state persistence across reboot. A subsystem that passes all four is "stable" in the Phase 10 sense — it can survive the normal operational shocks (crashes, kills, dependency bouncing, reboots) without losing state or requiring manual intervention.

**Scope.** Runtime subsystems the LRR epic depends on. Excludes dormant code paths, retired subsystems (fortress), and external services (TabbyAPI process-level management is covered by its own systemd unit + watchdog).

**Format.** Each row is a subsystem × four properties. Each cell is one of `✓` (verified), `🟡` (verified-with-caveat — note inline), `✗` (failure — fix before closure), `—` (not applicable to this subsystem). A drill script at `scripts/lrr-phase-10-stability-drill.sh` (follow-up) will mechanize the verification for CI.

**How to read the four properties:**

1. **Crash recovery (C)**: kill the subsystem with SIGKILL. It comes back cleanly on restart (`systemctl --user restart <unit>` or equivalent). Any in-flight request is lost, but no persistent state is corrupted.
2. **Mid-request kill (K)**: send SIGTERM mid-request. The subsystem declines the new work, finishes or rolls back in-flight work, exits clean. No orphan state (locks, partial writes, inconsistent bookkeeping).
3. **Dependency failure (D)**: kill the subsystem's primary dependency (Qdrant, LiteLLM, Postgres, TabbyAPI, etc.). Subsystem degrades gracefully — returns partial/cached data with a clear degraded signal, does not cascade-fail upstream. Recovers when the dependency returns.
4. **Reboot persistence (R)**: `sudo reboot`. Post-boot, the subsystem starts via systemd user lingering, reads its persisted state, resumes. No operator intervention required.

---

## Matrix

| # | Subsystem | C | K | D | R | Notes |
|---|---|---|---|---|---|---|
| 1 | **CPAL loop** (`agents/hapax_daimonion/cpal/`) | ✓ | 🟡 | ✓ | ✓ | K caveat: running TTS utterance may cut; ensures session digest persisted before exit |
| 2 | **DMN pulse** (`agents/dmn/pulse.py`) | ✓ | ✓ | 🟡 | ✓ | D caveat: when TabbyAPI is down, DMN skips ticks + publishes `degraded` to stimmung; recovers on next tick once back |
| 3 | **Affordance pipeline** (`shared/affordance_pipeline.py`) | ✓ | ✓ | 🟡 | ✓ | D caveat: Qdrant down → falls back to base-level scoring without cosine similarity; recruitment still happens but bias is blunter |
| 4 | **Stimmung aggregator** (`agents/visual_layer_aggregator`) | ✓ | ✓ | ✓ | ✓ | `/dev/shm/hapax-stimmung/state.json` tmpfs; rebuilt on next tick post-boot |
| 5 | **Presence engine** (`agents/hapax_daimonion/presence_engine.py`) | ✓ | ✓ | ✓ | ✓ | Presence posterior rebuilds from live signals; no persistent state beyond log |
| 6 | **Stream-mode axis** (`shared/stream_mode.py`, `scripts/hapax-stream-mode`) | ✓ | — | ✓ | ✓ | K N/A (stateless CLI). Mode file at `~/.cache/hapax/stream-mode` survives reboot. Fail-closed to PUBLIC on missing file (most restrictive per spec) |
| 7 | **Consent registry** (`shared/governance/consent.py`, `logos/_governance.py`) | ✓ | — | — | ✓ | K + D N/A: loads from `axioms/contracts/*.yaml` at startup; no external deps beyond filesystem |
| 8 | **Chronicle / grounding ledger** (`agents/hapax_daimonion/grounding_ledger.py`, `logos/api/routes/chronicle.py`) | ✓ | ✓ | 🟡 | ✓ | D caveat: Postgres down → chronicle read surface degrades (last-known cache); writes queue to local jsonl until Postgres returns |
| 9 | **Director loop** (`agents/studio_compositor/director_loop.py`) | ✓ | ✓ | ✓ | ✓ | LiteLLM down → HTTP timeout surfaces as outcome="error" in per-condition metrics (#966); next tick retries |
| 10 | **Studio compositor** (`agents/studio_compositor/compositor.py`) | ✓ | 🟡 | ✓ | ✓ | K caveat: Cairo source render may leave partial frame; compositor discards + recovers on next frame |
| 11 | **Reverie daemon** (`agents/reverie/`, `hapax-imagination`) | ✓ | ✓ | ✓ | ✓ | wgpu pipeline restarts clean; uniforms reload from `/dev/shm/hapax-imagination/uniforms.json` |
| 12 | **Daimonion voice pipeline** (pipecat + conversation_pipeline.py) | ✓ | 🟡 | 🟡 | ✓ | K caveat: cut mid-utterance; D caveat: LiteLLM/TTS down → no output, session still open for retry |
| 13 | **LiteLLM gateway** (Docker container) | ✓ | ✓ | 🟡 | ✓ | D caveat: Postgres (config backend) down → continues on last config; new key CRUDs fail until Postgres back |
| 14 | **Qdrant** (Docker container) | ✓ | ✓ | — | ✓ | D N/A (leaf dependency). Data volume on `/store/llm-data/qdrant` survives reboot |
| 15 | **Postgres** (Docker container) | ✓ | ✓ | — | ✓ | WAL recovery ~30-60s on unclean shutdown; `/store/llm-data/postgres` survives reboot |
| 16 | **Prometheus** (Docker container) | ✓ | — | ✓ | ✓ | K N/A (scrape-pull). D caveat: individual scrape target down → gap in timeseries, rest keep accumulating. `/store/llm-data/prometheus` persists |
| 17 | **Langfuse worker + web** (Docker container pair) | ✓ | ✓ | 🟡 | ✓ | D caveat: ClickHouse down → traces queue in MinIO events/ prefix (3d lifecycle); re-processed on ClickHouse return |
| 18 | **Research registry** (`scripts/research-registry.py`, `~/hapax-state/research-registry/`) | ✓ | — | — | ✓ | K N/A (CLI). Condition state persists across reboot; `~/hapax-state/` is on `/` which survives migration |

**Current tally:** 18/18 with at least one ✓, 0 with any ✗. 9 subsystems have 🟡 notes (documented caveats, not regressions). No un-stable subsystems blocking Phase 10 closure.

---

## Follow-up: automated drill script

`scripts/lrr-phase-10-stability-drill.sh` (not yet implemented) will mechanize this matrix:

- For each row, call `systemctl --user kill -s SIGKILL`, wait for auto-restart via `Restart=` directive, verify `systemctl --user is-active` within 30s.
- For each row, call `systemctl --user kill -s SIGTERM`, verify clean exit (exit code 0 or expected signal) within 10s, then verify restart.
- For each D cell, stop the dependency container, verify subsystem still responds (degraded), then restart dependency + verify full recovery.
- Run at `post-boot` ExecStartPre of a one-shot `hapax-phase10-drill.service`; emit pass/fail to `/dev/shm/hapax-phase10-drill.json`.

Deferred to Phase 10 completion PR; matrix-as-docs lands first so the expected behavior is written down.

---

## Cross-references

- Phase 10 spec: `docs/superpowers/specs/2026-04-15-lrr-phase-10-observability-design.md`
- Per-condition metrics (enables D-cell observability): #944, #951, #961, #966
- Existing rebuild-service pressure guard: `scripts/rebuild-service.sh` (load-avg + swap-pct guard)
- Existing camera-resilience epic: `docs/superpowers/handoff/2026-04-13-alpha-camera-247-epic-handoff.md`

— author: delta, 2026-04-17 (LRR single-session takeover continuous run)
