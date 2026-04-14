# LRR Phase 0 — Verification & Stabilization (per-phase plan)

**Spec:** `docs/superpowers/specs/2026-04-14-lrr-phase-0-verification-design.md`
**Branch:** `feat/lrr-phase-0-verification`
**Estimated effort:** 4 PRs across 1-2 sessions

## Stage 1 — Phase 0 PR #1 (this PR)

### Task 1.1 — Claim Phase 0 in lrr-state.yaml ✓

- [x] Edit `~/.cache/hapax/relay/lrr-state.yaml`
- [x] Set `current_phase_owner: alpha`, `current_phase_branch: feat/lrr-phase-0-verification`, `current_phase_opened_at: 2026-04-14T06:37:00Z`
- [x] Add `beta_drops_queued` block tracking the 2 beta artifacts already dropped (Bundle 1, Bundle 4)

### Task 1.2 — Per-phase spec + plan ✓

- [x] `docs/superpowers/specs/2026-04-14-lrr-phase-0-verification-design.md`
- [x] `docs/superpowers/plans/2026-04-14-lrr-phase-0-verification-plan.md` (this file)

### Task 1.3 — Item 1: chat-monitor wait-loop fix ✓ (shipped via PR #785)

- [x] Wait-loop implementation in `scripts/chat-monitor.py`
- [x] Regression pin tests in `tests/test_chat_monitor_wait_loop.py`
- [x] Deployed live: `systemctl --user restart chat-monitor`
- [x] Verified `systemctl --user is-active chat-monitor` returns `active`
- [x] Confirmed journal no longer spams the No-video-ID line every 10 s

### Task 1.4 — Item 7: huggingface-cli install ✓

- [x] `huggingface-hub[cli]` installed via `uv tool install`
- [x] Note the rename: upstream now uses `hf` instead of `huggingface-cli`. Phase 3 docs/scripts must use `hf download` not `huggingface-cli download`.
- [x] Verified: `which hf` returns the user's `~/.local/bin/hf`, version 1.9.0
- [x] Verified: `hf download --help` exits 0

### Task 1.5 — Item 9: voice transcript chmod 600 ✓

- [x] `chmod 600 ~/.local/share/hapax-daimonion/events-*.jsonl`
- [x] Verified all daily files now show `-rw-------`
- [x] Filed Phase 6 follow-up in spec §1.2: daimonion daily rotation hook must enforce `umask 077` or post-create `chmod 600` for new files

### Task 1.6 — Item 10: Kokoro TTS latency baseline ✓

- [x] Wrote `scripts/kokoro-baseline.py` — drives `agents.hapax_daimonion.tts.TTSManager` with 5 fixed phrases, captures cold + warm timings
- [x] Ran the script; baseline written to `~/hapax-state/benchmarks/kokoro-latency/baseline.json`
- [x] Numbers: cold 29.8 s (includes one-time spaCy `en_core_web_sm` install), warm p50 2253.9 ms, warm p95 2361.6 ms, warm RTF p50 0.415

### Task 1.7 — Item 8: RESEARCH-STATE.md Phase A note

- [ ] Add a 2026-04-14 dated entry to `agents/hapax_daimonion/proofs/RESEARCH-STATE.md` noting:
    - Phase A is READY but not started
    - Pre-registration written but not filed
    - OSF project not created
    - LRR Phase 4 will close all three

### Task 1.8 — Commit + push + PR

- [ ] Commit (one commit per task where reasonable)
- [ ] Push `feat/lrr-phase-0-verification`
- [ ] Open PR with title `feat(lrr): Phase 0 PR #1 — verification + Kokoro baseline + chmod 600 + huggingface-cli rename note`
- [ ] PR body includes the exit-criteria checklist with current state (5 of 10 closed)

## Stage 2 — Phase 0 PR #2 (next session, same branch)

### Task 2.1 — Item 2: token ledger writers

- [ ] Find LLM call sites in `scripts/album_identifier.py` (or `agents/album_identifier/__main__.py` if that's where it lives)
- [ ] Find LLM call sites in `scripts/chat-monitor.py` (likely in `_batch_analyze` or wherever the batch LLM call lives)
- [ ] Add `record_spend(component, prompt_tok, completion_tok, cost)` after each call
- [ ] Verify `cat /dev/shm/hapax-compositor/token-ledger.json | jq '.components | keys'` includes `album-identifier` and `chat-monitor`

### Task 2.2 — Item 5: Sierpinski performance baseline

- [ ] Write `scripts/sierpinski-cpu-baseline.sh` — captures `top -bn5 -p $(pgrep -f studio_compositor)` snapshots over 5 minutes, summarizes mean/p95 CPU
- [ ] Run during a normal compositor session (Sierpinski live in `default.json`)
- [ ] Document the result in a context artifact under `~/.cache/hapax/relay/context/`

### Task 2.3 — Item 6: RTMP path documentation

- [ ] Read `agents/studio_compositor/compositor.py:594-628` for the `toggle_livestream` definition
- [ ] Check current runtime state via the `rtmp_bin.is_attached()` query
- [ ] Document in PR #781's W4.6 audit doc (or a new short doc) that native RTMP is the canonical LRR output path; OBS-fork is legacy
- [ ] Cross-link from the LRR epic Phase 0 spec § exit criteria

## Stage 3 — Phase 0 PR #3 (next session or two)

### Task 3.1 — Item 4: FINDING-Q steps 2–4 (multi-session)

- [ ] **Spike first**: read `hapax-imagination/src-imagination/dynamic_pipeline.rs` end-to-end. Take notes on the WGSL hot-reload path. May want to write a mini-design doc if the surface is larger than expected.
- [ ] **Step 2**: WGSL manifest validation BEFORE the hot-reload swap. Validate: manifest parses, bind groups match, entry points exist. Reject on failure with a structured log line including the manifest hash.
- [ ] **Step 3**: Previous-good shader rollback panic handler. When step 2 fails, roll back to the last-known-good plan and log a structured event.
- [ ] **Step 4**: `hapax_imagination_shader_rollback_total` counter. Increments on every rollback path entry. Wired through the existing prometheus exporter.
- [ ] Tests for steps 2-4 (unit-level, mocking the validation surface)
- [ ] Verify the next wgpu shader reload failure (synthetic injection or natural occurrence) triggers the rollback path and increments the counter

## Stage 4 — Phase 0 PR #4 (operator-gated)

### Task 4.1 — Item 3: /data inode pressure + alerts

- [ ] Verify Langfuse MinIO `events/` 14-day lifecycle rule is live (`mc ilm rule list local/events`)
- [ ] If not live, reinstall the rule
- [ ] Add Prometheus alert rules at 85 % and 95 % inode thresholds for `/data` mount in `llm-stack/alertmanager-rules.yml` (cross-repo, operator-gated like W1.1)
- [ ] Apply `sudo ufw` rule if needed (probably not — alertmanager already in stack)
- [ ] Verify `df -i /data` ≤ 85 % within 24 h of rule taking effect

## Stage 5 — Phase 0 close

- [ ] All 10 exit criteria in spec §2 satisfied
- [ ] Write `docs/superpowers/handoff/2026-04-14-lrr-phase-0-complete.md` per LRR plan §7 template
- [ ] Update `~/.cache/hapax/relay/lrr-state.yaml`: `current_phase: 1`, `last_completed_phase: 0`, `last_completed_handoff: <path>`, append `0` to `completed_phases`
- [ ] Open Phase 1 (or hand off to next session)

---

## Notes

- **Operator-in-the-loop check-ins:** none mandatory in Phase 0 except item 3 (/data inodes) which is operator-gated. The chmod 600 retroactive change is flagged in the spec body so the operator notices the privacy posture change.
- **Verification-before-claiming-done:** every checkbox above has a paired verification command in the spec § exit criteria. Don't tick the box until the verification passes.
- **Beta drops queued:** Bundle 1 (Phase 3+5) and Bundle 4 (Phase 6) are already dropped to `~/.cache/hapax/relay/context/`. Do NOT consume them in Phase 0 — they belong to their target phases. Watch for Bundle 5 (Phase 7 persona literature) which is next in beta's priority order.
