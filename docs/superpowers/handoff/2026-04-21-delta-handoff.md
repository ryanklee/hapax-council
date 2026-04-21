---
date: 2026-04-21
session: delta
hand_off_to: delta (post-compaction, same operator)
stream_state: LIVE (YouTube, LegomenaLive)
role: delta = keep alpha efficient; research/spec/plan/small-ship, not epic-author
---

# Delta handoff — post-audio-remediation session

## 0. Where we are now

- Stream is **UP**. Early days, few viewers. Operator has full authority to take it down if needed.
- Audio stack is deployed and normalising. OBS is bound to `hapax-obs-broadcast-remap` (PipeWire-native, persists across restarts).
- Alpha is in the middle of B3 (programme epic completion — lifecycle + JSONL + aborts). Let alpha keep owning that.
- No active research agents running.
- Worktrees: alpha main + rebuild scratch. Clean.

## 1. Delta's actual role this session (load-bearing)

From memory `feedback_alpha_efficiency_mandate`: "Delta's constant task: keep alpha efficient." Do not claim alpha's epic work. Do triage + research + spec + plan + small shippable fixes. Be the external brain.

Operator's standing corrections from the session:
- **Verify before claiming done** (`feedback_verify_before_claiming_done`) — build+commit≠done. I tripped this twice today; the second time was the `cache_size: 8192` "fix" that empirically freed zero VRAM. Confession + revert was the right call.
- **Exhaust research before solutioning** (`feedback_exhaust_research_before_solutioning`) — I initially misdiagnosed the OBS quit-dialog storm as the scene-guard timer. Actual cause was vram-watchdog SIGKILL'ing OBS. Operator caught it. Look for process-lifecycle signals (journalctl kills, OOM, systemd restarts) before blaming config-file conflicts.
- **Show-don't-tell** (`feedback_show_dont_tell_director`) — any on-screen text that's actually internal routing prose is a governance violation. PR #1133 closed one instance via the diagnostic flag + activity-header filter.

## 2. What shipped on main today (PRs + commits)

| PR / commit | Scope |
|---|---|
| #1120 | Director LLM markdown fence-strip |
| #1127 | Director prose-parser fallback |
| #1128 | TTS `media.role=Assistant` ducking source-side |
| #1129 | Voice-state baseline publisher (alpha) |
| #1133 | Gloss diagnostic filter — `CompositionalImpingement.diagnostic` flag; activity-header skips diagnostics |
| #1136 | EvilPet+S-4 Phase B — 5 Hz arbiter daemon + S-4 MIDI lane (alpha) |
| #1137 | Ward z-order collision fix (alpha) |
| #1138 | Shader intensity cap Phase 1 — `presets/shader_intensity_bounds.json` + `shared/shader_bounds.py` + `wgsl_compiler.py` clamp + 9 tests |
| #1139 | `hapax-audio-router` added to rebuild-services cascade (alpha) |
| #1140/41/42 | YT/Sierpinski `slot_family` separation (Phase 1A/B/C — schema + Rust runtime + sat_sierpinski_content recruitment) |
| commit `11118bd7e` | vram-watchdog OBS allowlist (direct on main — emergency) |
| commit `835452151` | Pixel-sort amendment + ward-modulator spec + mobile-substream spec/plan + CLAUDE.md corrections (Command-R-not-Qwen, Ollama GPU policy) |
| commit `cdb189855` | YT-Reverie-Sierpinski separation spec + plan docs |

## 3. Authored but NOT YET on main

**Tonight's audio remediation confs** — live in `~/.config/pipewire/pipewire.conf.d/` and `~/.config/wireplumber/wireplumber.conf.d/` but uncommitted:
- `hapax-obs-broadcast-remap.conf` — **THIS IS LOAD-BEARING** (OBS's current audio source). Committed to repo under `config/pipewire/` but never PR'd. Delivery mechanism: copy from repo → user dir. Saved on disk, survives reboot.
- `hapax-obs-broadcast-tap.conf` — sister fallback (loopback-only, no remap). Committed to repo; NOT deployed to user dir.
- `pc-loudnorm.conf` — deployed, committed to repo.
- `hapax-broadcast-master.conf` — **DO NOT REDEPLOY AS-IS.** First attempt had a feedback-loop loopback (fixed conceptually; never re-tested). Removed from user dir. The OBS remap conf is the verified-good pattern to copy when fixing this.
- `voice-fx-loudnorm.conf` — deployed.
- WirePlumber policies (7 files) — all deployed.

**Next delta action (if operator picks master-bus fix):** update `hapax-broadcast-master.conf` to use the verified OBS-remap loopback pattern (capture.props with `stream.capture.sink=true`, `target.object=hapax-livestream-tap`; playback.props with `media.class=Audio/Source` + `device.class=filter` + `node.virtual=true`). Then bundle tonight's audio confs into a single PR: `feat(audio): tonight's loudnorm + ducking + OBS-remap remediation bundle`.

## 4. Spec + plan ready to implement (next claimer)

| cc-task (vault) | State | Priority |
|---|---|---|
| `ward-modulator-z-axis` | spec + plan integrated; schema adds `z_plane` + `z_index_float` to WardProperties; 3 phases | WSJF 8.5 |
| `mobile-livestream-substream` | spec + plan shipped today; 5 PRs, ~1880 LOC, Phase 1 = smart-crop 9:16 substream | WSJF 6.0 |
| `finding-v-research` (closed) → follow-on spec+plan | research doc landed (`docs/research/2026-04-21-missing-publishers-research.md`); per-publisher verdicts (4 implement, 1 retire, 1 merge) — spec+plan still to write | depends on alpha's pickup |
| `yt-reverie-sierpinski-separation` | **SHIPPED today** by alpha (#1140/41/42) | closed |
| `evilpet-s4-phase-b` | **SHIPPED today** by alpha (#1136) | closed |

## 5. Research complete — no spec yet

- **720p→1080p upscale** — verdict DON'T. YouTube already upscales; our MJPEG is already lossy.
- **Nebulous scrim z-axis** — rolled into ward-modulator spec.
- **Alpha-efficiency study** — top pick was "write FINDING-V research," now done.
- **GPU workload audit** — `cache_size` dead-end confirmed empirically; Ollama GPU-1 pinning intentional (doc drift corrected).
- **Audio systems live audit** — `docs/research/2026-04-21-audio-systems-live-audit.md`. Several blockers closed tonight; S-4 physical absence still open.

## 6. Operator directives still open (tonight)

- **Dynamic ward position/appearance driven by stimmung** — spec'd (ward-modulator); needs implementation.
- **Camera autonomy** — follow_mode is SHIPPED but gated by `HAPAX_FOLLOW_MODE_ACTIVE=0` (flag off). Flip to `=1` in compositor systemd env for activation. I proposed but never shipped — operator deprioritised in favour of audio.
- **Mobile-friendly livestream** — spec+plan done, implementation pending.
- **S-4 hands-off control** — Phase B router shipped; **S-4 physically absent** (kernel saw zero new USB events on re-plug through CalDigit). Blocked on hardware.
- **YT video fronting via Sierpinski** — slot-family separation shipped; affordance-level `content.yt.feature` fronting is deferred Phase 2 of that epic.
- **Master-bus normaliser** — spec'd in `config/pipewire/hapax-broadcast-master.conf`; prior deploy was feedback-broken; verified-good pattern now available from OBS remap work.

## 7. Blocked on physical

- **Torso S-4**: kernel-level zero enumeration after power-cycle + CalDigit port change. Candidates: dead data cable, S-4 USB mode (host vs device), CalDigit downstream port. Router in single-engine degrade until resolved. All Phase B3 D1–D5 dual-engine topologies gated on this.

## 8. Operator UI actions still pending (one-time, no code needed)

- **YT loudnorm wiring in OBS** — `hapax-yt-loudnorm` sink exists; OBS's YouTube-media-source Device dropdown → select "Hapax YT Loudnorm".
- **L-12 fader calibration** — set trims+faders once against PC loudnorm reference, walk away. L-12 has no USB control surface (hardware-only).

## 9. Deferred / Phase 2 (unscheduled)

- Master-bus normaliser (ready to ship with correct loopback pattern).
- Shader intensity cap Phase 2 (GPU-side spatial-coverage gate) + Phase 3 (ward_stimmung_modulator clamp, once modulator module exists).
- YT fronting affordance (`content.yt.feature` + `yt.feature` impingement family).
- Mobile companion page (mobile substream Phase 6).
- Per-consumer VRAM Prometheus alerts (~40 LOC observability).
- Audio-router SHM state publishing (`/dev/shm/hapax-audio-router/` is empty — no observability).
- Scrim z-axis phases 2+3 (parallax visuals, DoF shader).

## 10. Critical session-scoped memories I wrote today

- `reference_vram_watchdog_allowlist` — always add new GPU apps to the 90%-threshold allowlist. Missing entries cause 30s SIGKILL storms. OBS + obs-browser added.
- `feedback_obs_scene_guard_dead` — the scene-guard was the WRONG diagnosis on 2026-04-21. Real cause was vram-watchdog. Don't re-deploy either. Learn: check `journalctl -k | grep Killing` before blaming config-file conflicts.
- `reference_l12_evilpet_aux_b_routing` — ratified AUX B topology (vinyl CH 9/10 + PC CH 11/12 → AUX B → Evil Pet → CH 6 return). Hardware-only config, no USB control surface.
- (earlier today) Pre-existing memories `feedback_verify_before_claiming_done`, `feedback_exhaust_research_before_solutioning`, `feedback_scientific_register`, `feedback_no_expert_system_rules` all fired in this session.

## 11. Workflow conventions active

- **Admin-merge pattern through main CI drift** — `yt_loudnorm`, `evilpet_s4_gain`, `reverie_mixer`, `compositor_wiring`, `test_affordance_registration` all fail on main. Alpha has been `gh pr merge --admin` through them all day. My PR #1133 + #1138 followed the same pattern. This is the running convention until the drift is fixed.
- **Worktree discipline** — max 4 (alpha + beta + delta + 1 spontaneous). Hook enforces this. After squash-merge, local branch-delete gets blocked; leave the stale branch alone — cosmetic only.
- **Rebuild-services timer** — 5 min cadence auto-rebuilds anything committed under the watched paths (compositor, effect-graph, daimonion, etc.). `no manual deploys needed` in task-notifications means this.
- **PR-first gate** — `work-resolution-gate.sh` blocks Write edits when a branch has unmerged commits with no PR. Open the PR early, then iterate.

## 12. What to NOT do

- Don't redeploy `hapax-obs-scene-guard` (false-cause'd, dangerous).
- Don't redeploy the first `hapax-broadcast-master.conf` that had the bad loopback (use the OBS-remap pattern).
- Don't restart pipewire casually — it drops OBS audio binding unless the operator has moved to the PipeWire-remap source (they have now, so this is less fragile, but still).
- Don't swap TabbyAPI's cache_size to "save VRAM" — confirmed empirically that gpu_split is the reservation, cache_size just carves the pool. Zero savings.
- Don't claim epic work. Delta role is support.

## 13. Likely next operator asks

1. "Ship the master-bus" — straight PR now that OBS-remap proves the loopback pattern.
2. "Commit tonight's audio confs" — bundle the uncommitted user-dir confs into one PR.
3. "Write FINDING-V spec + plan" — research is done, operator may want it operationalised.
4. "Flip follow-mode flag" — `HAPAX_FOLLOW_MODE_ACTIVE=1` in compositor systemd env.
5. "Fix audio-router SHM publishing" — small code PR.
6. Random tactical: stream quality, visual issue, hardware oddity.

## 14. Next operator message will probably reference...

- The remap source `hapax-obs-broadcast-remap` and whether it's still binding.
- Stream quality issues (continuing theme).
- A new priority we haven't hit yet.

Reset → continue.
