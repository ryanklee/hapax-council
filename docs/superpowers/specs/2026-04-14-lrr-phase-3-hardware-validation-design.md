# LRR Phase 3 — Hardware Migration Validation + Hermes 3 Preparation

**Epic:** Livestream Research Ready
**Phase:** 3 of 11
**Date:** 2026-04-14
**Dependency:** Phase 2 complete (shipped in PRs #797, #802, #805).
**Session:** alpha (resumed after operator directive "do everything we can sans Hermes prep completion")

## 0. Motivation + operator correction

The original Phase 3 design (`livestream-research-ready-epic-design.md` §"Phase 3 — Hardware Migration Validation + Hermes 3 Preparation") assumed the X670E motherboard install was a blocking prerequisite for most of Phase 3's work. Beta's verification pass on 2026-04-14 (see `~/.cache/hapax/relay/context/2026-04-14-beta-phase-3-supplement-verified-preconditions.md`) — triggered by operator correction "why are we waiting for the X670E? Don't we have almost everything on board this rig other than increased ram and mobo itself?" — demonstrated that **only items 4, 10, and 11 are truly hardware-gated on the new motherboard**:

| Item | Pre-mobo | Notes |
|---|---|---|
| 0 — sm_120 precondition check | ✅ | beta verified shell-level 2026-04-14 |
| 1 — Partition reconciliation α→γ | ✅ | systemd drop-in changes |
| 2 — Driver + CUDA verification | ✅ | 590.48.01 + CUDA 12.8, both GPUs compute-tested |
| 3 — PSU combined-load stress test | ✅ | PSU unchanged; test can run on current rig |
| 4 — PCIe link width verification | 🚫 | mobo-gated (slot topology changes) |
| 5 — Thermal validation | ✅ | can run on current rig |
| 6 — Hermes 3 70B EXL3 3.0bpw | 🟡 | BF16 download complete; self-quantization is Phase 3 PR #2 (multi-hour; deferred) |
| 7 — TabbyAPI config draft | ✅ | config.yml.hermes-draft |
| 8 — TabbyAPI systemd timeout increase | ✅ | 120 → 180 |
| 9 — Rollback plan | ✅ | documented in this spec |
| 10 — Cable hygiene pass | 🚫 | operator physical touch point |
| 11 — BRIO replacement | 🚫 | operator physical swap |

**This PR (Phase 3 PR #1) covers items 1, 2, 7, 8, 9 plus documented rollback procedures.** Items 0, 3, 4, 5 are run as operational verification and findings are added to §6 of this spec in a follow-up commit. Item 6 (self-quantization) is deferred as Phase 3 PR #2 per operator direction ("do everything we can sans Hermes prep completion"). Items 10 and 11 remain as Phase 3 PR #3 to land after the X670E install window.

## 1. Scope (this PR, items 1 + 2 + 7 + 8 + 9)

### 1.1 Item 1 — Partition reconciliation α → γ

**Current (Option α):**
- `tabbyapi.service`: `CUDA_DEVICE_ORDER=PCI_BUS_ID`, `CUDA_VISIBLE_DEVICES=1` — pinned to 3090 only (single-GPU)
- `hapax-dmn.service`: no explicit GPU pin, runs on GPU 1 (3090) by default

**Target (Option γ):**
- `tabbyapi.service`: `CUDA_DEVICE_ORDER=PCI_BUS_ID`, `CUDA_VISIBLE_DEVICES=0,1` — both GPUs visible for layer-split
- `hapax-dmn.service`: `CUDA_DEVICE_ORDER=PCI_BUS_ID`, `CUDA_VISIBLE_DEVICES=0` — pinned to 5060 Ti

Both unit files are shipped in this PR as repo-tracked drop-ins at:

- `systemd/units/tabbyapi.service.d/gpu-pin.conf`
- `systemd/units/hapax-dmn.service.d/gpu-pin.conf`

`install-units.sh` is extended in this PR to symlink `*.service.d/` directories into `~/.config/systemd/user/` (previously the script only handled top-level unit files). See § 2 for the install-units.sh extension.

**VRAM math under Option γ** (per beta's supplement §1.4):

| GPU | Residents | Total | Headroom |
|---|---|---|---|
| 5060 Ti (sm_120, 16 GiB) | compositor 3.3 + imagination 0.3 + hapax-dmn 3.4 + Hermes overflow 2.75 + faster-whisper STT 2.5 | 12.25 GiB | 3.25 GiB |
| 3090 (sm_86, 24 GiB) | Hermes 3 layers 0-76 23.5 + activations + KV cache | ~24 GiB | ~0.1 GiB |

**The 3090 is tight.** If Hermes 3's actual VRAM overshoots the spec's 23.5 GB, there is no room. Contingency: drop to 2.5 bpw (tighter quant) or `max_seq_len=2048`. Mitigation plan: the `config.yml.hermes-draft` shipped in this PR uses `max_seq_len=4096` (not 8192 as the original Hermes 3 plan specified) to leave ~0.3 GiB of slack.

### 1.2 Item 2 — Driver + CUDA verification

Beta verified at 2026-04-14T15:30Z:

- Driver: **590.48.01** (matches alpha.yaml session 1 state; pinned in pacman.conf per `feedback_nvidia_595_crash.md`)
- CUDA: **12.8** (via PyTorch 2.9.0+cu128 wheel)
- `nvidia-smi -L` → both GPUs listed
- Direct PyTorch matmul test on both devices under `CUDA_VISIBLE_DEVICES=0,1` + `CUDA_DEVICE_ORDER=PCI_BUS_ID`:
  - `cuda:0` = "NVIDIA GeForce RTX 5060 Ti" sm_120, 4096² fp16 matmul in 327 ms
  - `cuda:1` = "NVIDIA GeForce RTX 3090" sm_86, 4096² fp16 matmul no errors
- No warnings beyond the benign `PYTORCH_CUDA_ALLOC_CONF` deprecation notice

**Conclusion:** the exllamav3 "seems to work™" caveat for Blackwell sm_120 is empirically confirmed working on this rig at the PyTorch matmul kernel level. The full systemd-integrated path (TabbyAPI loading Qwen3.5-9B on the 5060 Ti) remains to be verified as part of the alpha-side precondition re-run referenced in `~/.cache/hapax/relay/context/2026-04-14-lrr-phase-3-prestaged-artifacts.md` Stage 1 Task 1.3.

### 1.3 Item 7 — TabbyAPI config draft (Hermes 3)

Ships as `~/projects/tabbyAPI/config.yml.hermes-draft` (local tabbyAPI repo, not active). The draft is committed to the upstream-clone's local git but NOT pushed to `theroyallab/tabbyAPI` per the `.git/info/exclude` pattern for upstream-clones.

Key differences from the current active `config.yml`:

- `model_name: Hermes-3-Llama-3.1-70B-EXL3-3.0bpw` (replaces `Qwen3.5-9B-exl3-5.00bpw`)
- `gpu_split: [2.75, 23.5]` — **CORRECTED from original Hermes 3 plan's `[23.5, 2.75]`**. The original order would OOM the 5060 Ti immediately (tries to put 23.5 GB on a 15.5 GB card). Beta's PyTorch verification (§1.2) pinned the device-index-to-card mapping: process index 0 = 5060 Ti, process index 1 = 3090.
- `cache_mode: Q8` — down from `4,4` (Q4 KV). Q8 KV is slightly larger but safer for 70B first-load.
- `cache_size: 4096` + `max_seq_len: 4096` — pulled back from the original plan's 8192 to leave ~0.3 GiB slack on GPU 1's ~0.1 GiB headroom under Option γ.
- `chunk_size: 2048` — unchanged from current Qwen config
- `inline_model_loading: false` — unchanged

### 1.4 Item 8 — TabbyAPI systemd `TimeoutStartSec` 120 → 180

`systemd/units/tabbyapi.service` bumped from `TimeoutStartSec=120` → `180`. Qwen3.5-9B EXL3 loads in ~40-50 s; Hermes 3 70B EXL3 3.0bpw (~26 GB) is expected to load in ~70-90 s based on comparable 70B EXL3 benchmarks. The 120-second cap is tight enough that a cold-cache first-load from the 30 safetensors shards could hit it. 180 s gives 60 s of cushion without being so loose that a genuinely-broken model load escapes the watchdog.

Rollback: just change `TimeoutStartSec=180` back to `120`.

### 1.5 Item 9 — Rollback plan

See §5 for the full rollback procedure.

## 2. `install-units.sh` extension for `.service.d/` drop-ins

Previously the script iterated `*.service *.timer *.target *.path` under `systemd/units/` and symlinked each into `~/.config/systemd/user/`. It did NOT handle `*.service.d/` drop-in directories. Existing drop-ins under `systemd/units/audio-recorder.service.d/` and `systemd/units/contact-mic-recorder.service.d/` were silently not installed — a latent gap.

Phase 3 adds `tabbyapi.service.d/` and `hapax-dmn.service.d/`, both of which MUST be active for the partition reconciliation to take effect. Extending the script now fixes both the new drop-ins and the latent existing ones as a single change.

The extension:

1. After the main unit-file link loop, walk `systemd/units/*.service.d/` directories.
2. For each found, ensure `$DEST_DIR/<service>.service.d/` exists (as a real directory, not symlink — this matches how the existing tabbyapi.service.d/ works on disk today).
3. Symlink every `*.conf` file inside into the matching destination `.d/` directory.
4. Report counts + trigger `daemon-reload` if anything changed.

Regression pin: `tests/test_install_units_sweep_pin.py` extended to assert that the script walks `*.service.d/` directories and links `*.conf` files into the matching destination `.d/` dir.

## 3. Rollback procedures (item 9)

### 3.1 Revert Option γ → Option α (partition)

If Hermes 3 fails to load or benchmarks below threshold:

```bash
# 1. Edit the tabbyapi drop-in
sed -i 's/CUDA_VISIBLE_DEVICES=0,1/CUDA_VISIBLE_DEVICES=1/' \
    ~/projects/hapax-council/systemd/units/tabbyapi.service.d/gpu-pin.conf

# 2. Edit the hapax-dmn drop-in
sed -i 's/CUDA_VISIBLE_DEVICES=0/CUDA_VISIBLE_DEVICES=1/' \
    ~/projects/hapax-council/systemd/units/hapax-dmn.service.d/gpu-pin.conf

# 3. Re-run install-units.sh to refresh symlinks (no-op if still correct)
bash ~/projects/hapax-council/systemd/scripts/install-units.sh

# 4. Reload + restart
systemctl --user daemon-reload
systemctl --user restart tabbyapi.service
systemctl --user restart hapax-dmn.service

# 5. Verify rollback
nvidia-smi  # confirm: 3090 has tabbyapi + hapax-dmn; 5060 Ti has compositor only
```

### 3.2 Revert Hermes 3 → Qwen3.5-9B (config)

If the config swap is also applied:

```bash
# 1. Revert tabbyAPI config
cd ~/projects/tabbyAPI
git checkout -- config.yml  # discard local Hermes 3 changes

# 2. Restart tabbyapi
systemctl --user restart tabbyapi.service

# 3. Verify
curl -s http://localhost:5000/v1/models | jq '.data[0].id'
# expected: "Qwen3.5-9B-exl3-5.00bpw"
```

### 3.3 Revert systemd timeout change

```bash
cd ~/projects/hapax-council
git revert <commit-sha-of-this-pr>  # or manually edit systemd/units/tabbyapi.service
bash systemd/scripts/install-units.sh
systemctl --user daemon-reload
```

The `TimeoutStartSec=180` value is forward-compatible with smaller models — no functional regression on Qwen, just an unused 60 s of slack. So the rollback is only needed if there's a genuine reason to restore the 120 s value.

## 4. Exit criteria

- [x] Partition drop-ins at `systemd/units/tabbyapi.service.d/gpu-pin.conf` and `systemd/units/hapax-dmn.service.d/gpu-pin.conf` present and correct
- [x] `install-units.sh` extended to install drop-in directories
- [x] `tabbyapi.service` `TimeoutStartSec` raised to 180
- [x] `config.yml.hermes-draft` staged at `~/projects/tabbyAPI/` (local-only commit, not pushed to upstream)
- [x] Rollback procedure documented (this spec §3)
- [ ] Alpha re-runs formal sm_120 precondition check at systemd-integrated level (follow-up)
- [ ] PSU combined-load stress test documented in spec §6 (follow-up operational task)
- [ ] Thermal validation under combined load (follow-up operational task)
- [ ] `sudo lspci -vvs` PCIe link width output recorded (follow-up operational task; operator now considers this unblocked)
- [ ] Regression test pinning gpu_split ordering + drop-in presence (this PR)

## 5. Risks

- **3090 headroom is tight.** GPU 1 has ~0.1 GiB free after Hermes 3 + activations + KV cache. Any overshoot on actual VRAM vs the 23.5 GB spec number forces fallback to 2.5 bpw or `max_seq_len=2048`. Contingency documented in §1.3.
- **Partition activation requires a service restart.** Activating Option γ means restarting both `tabbyapi.service` and `hapax-dmn.service`. The restart window briefly kills local LLM routing (`local-fast`/`coding`/`reasoning`) and voice STT. Schedule during an idle window.
- **Self-quantization (Phase 3 PR #2) is multi-hour.** The 6-12 hour window blocks TabbyAPI from handling simultaneous inference (the 3090 is busy with quant compute). Plan for overnight.
- **X670E install (Phase 3 PR #3) is a separate operator window** (~2026-04-16). Items 4, 10, 11 ship there.

## 6. Operational verification findings (follow-up)

This section is updated by a second commit on this branch after the operational tasks run. Placeholder for:

- [ ] Item 0 formal systemd-integrated sm_120 test
- [ ] Item 3 PSU combined-load stress (30 min)
- [ ] Item 4 PCIe link width `lspci -vvs` output
- [ ] Item 5 thermal validation during stress
- [ ] Item 11 brio-operator fps re-measurement under Option γ

## 7. Handoff implications

Phase 3 PR #1 (this PR) ships the non-runtime-destructive bits. After merge, the operator decides when to apply the partition via `systemctl --user daemon-reload && restart tabbyapi && restart hapax-dmn`. Phase 5 (Hermes 3 actual substrate swap) is unblocked from this PR + the Phase 3 PR #2 self-quantization.

Phase 4 (Condition A collection) can run in parallel with Phase 3's pre-mobo work under the original epic design's time-gating rule — Phase 4 runs on Qwen (current substrate) while Phase 3 prepares Hermes (next substrate).

## 8. References

- `docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md` §"Phase 3" — original design (items enumerated)
- `~/.cache/hapax/relay/context/2026-04-14-beta-phase-3-supplement-verified-preconditions.md` — beta's shell-level verification
- `~/.cache/hapax/relay/context/2026-04-14-lrr-phase-3-prestaged-artifacts.md` — beta's session 2 pre-staged artifacts
- `feedback_nvidia_595_crash.md` — driver 590.48.01 pinning rationale
- PR #801 (Phase 10 observability polish) — set `CUDA_VISIBLE_DEVICES=0` at the compositor level (already compatible with Option γ)
- PR #803 (install-units.sh sweep + primary-worktree guard) — prior art for the install-units.sh extension in this PR
