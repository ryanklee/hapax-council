# Local Music Repository (Task #130) — Implementation Plan

**Status:** ready-to-execute (BLOCKED on #127 SPLATTRIBUTION shipping the `vinyl_playing` signal)
**Date:** 2026-04-20
**Author:** alpha (refining 2026-04-18 spec)
**Owner:** alpha (zone — studio compositor)
**Spec:** `docs/superpowers/specs/2026-04-18-local-music-repository-design.md`
**Origin:** D-31 unplanned-spec triage (last still-relevant unplanned spec; MED priority)
**WSJF:** 3.5 (MED — depends on #127 + relates to #131 SoundCloud + #142 vinyl rate)
**Branch:** trio-direct (per existing burst pattern; ships in 4-5 commits)
**Total effort:** ~5-7h focused work across 4 phases

## 0. Why this plan exists

D-31 unplanned-specs triage classified this `still-relevant-needs-plan`
(MED priority). Spec was authored 2026-04-18 and provisionally
approved per dossier task #130; no plan was filed.

Operator directive in spec §1: "Decouple music featuring from vinyl.
Task #65 completed the attribution + overlay layer when vinyl IS
playing; this is the next layer — what Hapax features when the vinyl
is quiet."

DMCA posture per spec §1: every track in the pool is pre-licensed
(operator-owned masters, CC-licensed, public domain). No fingerprint-
matchable commercial recordings. **Primary safety invariant.**

## 1. Pre-flight

- [ ] **HARD BLOCKER:** verify #127 SPLATTRIBUTION has shipped the
      `vinyl_playing` derived signal at `shared/signals.py`. Run
      `Grep -n "vinyl_playing" shared/signals.py` — if 0 hits, this
      plan blocks until #127 lands.
- [ ] Verify `~/music/hapax-pool/` directory exists OR plan to create
      it as part of Phase 1 with a README + 5 seed tracks
      (operator-owned legomena output if available).
- [ ] Verify `agents/studio_compositor/album_overlay.py` still reads
      `/dev/shm/hapax-compositor/music-attribution.txt` per spec §6
      line 110. If file format has changed, Phase 4 attribution writer
      needs to follow.
- [ ] Verify `scripts/youtube-player.py::VideoSlot` still exists per
      spec §6 line 100 (template for ffmpeg subprocess + EOF watchdog).

## 2. Phase 1 — Repository scaffold + validation CLI (~1.5h)

Spec §2 + §6.

### 2.1 Tasks

**T1.1** Create `~/music/hapax-pool/` with subdirs:
- `operator-owned/`, `cc-by/`, `cc-by-sa/`, `cc0/`, `other-licensed/`
- `README.md` with operator-curation notes template
- `index.json` placeholder (empty `{}` initially; Phase 2 module
  populates on first scan)

**T1.2** New `scripts/hapax-music-pool-validate`:
- Walks pool root
- For each `.flac`/`.mp3`/`.ogg`/`.wav`, locates sibling `.yaml`
  frontmatter
- Validates schema per spec §2 (BPM, key in Camelot, license SPDX,
  attribution.title/artist/source-url required)
- Reports missing/invalid + suggests fixes
- Exit codes: 0 healthy, 1 invalid frontmatter, 2 missing tracks
- `--apply-fixes` flag (operator-only) — auto-creates skeleton .yaml
  for new audio files; never overwrites existing.

**T1.3** Tests at `tests/scripts/test_hapax_music_pool_validate.py`:
- Synthetic pool fixture under tmp_path
- Cases: healthy / malformed YAML / missing BPM / bad license SPDX

### 2.2 Exit criterion

`bash scripts/hapax-music-pool-validate` returns 0 against the empty
pool (no tracks, no errors). Operator drops a few seed tracks; CLI
reports their state correctly.

### 2.3 Commit

```
feat(local-music): #130 Phase 1 — pool scaffold + validation CLI
```

## 3. Phase 2 — LocalMusicRepository + selection logic (~2h)

Spec §3.

### 3.1 Tasks

**T2.1** New `agents/studio_compositor/local_music/__init__.py`.

**T2.2** New `agents/studio_compositor/local_music/repository.py`:
- `LocalMusicRepository(pool_root: Path)` class
- `scan() -> list[Track]` — walks pool, parses sidecar YAML,
  validates, caches `index.json` keyed on mtime
- `select_next(stimmung, last_n_played, *, seed=None) -> Track`:
  - Filter: licensed (excludes invalid/missing-license tracks)
  - Filter: not in last_n_played (per-session repetition penalty)
  - Score: stimmung-cosine × BPM-fitness × Camelot-distance
  - Softmax over scores with τ from `config/local_music.yaml`
  - Sample one track (deterministic with `seed` for tests)
- `Track` dataclass (Pydantic): file_path, frontmatter,
  computed_score (cached on scan)

**T2.3** New `config/local_music.yaml`:
- `pool_root: ~/music/hapax-pool/`
- `softmax_temperature: 0.5`
- `repetition_window: 5` (last-N-played per spec §8 #4 default)
- `stimmung_weights: {tension: 0.4, depth: 0.3, ...}` (operator-tunable)

**T2.4** Tests at `tests/studio_compositor/local_music/`:
- `test_repository_selection.py` — stimmung + BPM + key fixtures →
  deterministic top-1 with fixed seed
- `test_frontmatter_validation.py` — malformed YAML, missing fields,
  bad license SPDX → all excluded with log lines
- Hypothesis property test: Camelot distance symmetry, stimmung
  cosine bounds, selection NEVER returns unlicensed

### 3.2 Exit criterion

`uv run pytest tests/studio_compositor/local_music/ -q` green for
selection + validation. Property tests pass.

### 3.3 Commit

```
feat(local-music): #130 Phase 2 — LocalMusicRepository + selection logic
```

## 4. Phase 3 — VinylGate + Player (~2h)

Spec §4 + §5.

### 4.1 Tasks

**T3.1** New `agents/studio_compositor/local_music/gate.py`:
- `VinylGate` reads `vinyl_playing` signal from `shared/signals.py`
- State machine: ACTIVE (vinyl playing → local-music silent) ↔
  IDLE (vinyl quiet → local-music can play)
- Debounce: 5s minimum in each state to avoid flapping
- Halt-at-boundary: when transitioning IDLE → ACTIVE mid-track,
  finish the current track THEN halt (don't cut mid-bar)

**T3.2** New `agents/studio_compositor/local_music/player.py`:
- `LocalMusicPlayer` class — ffmpeg subprocess, PipeWire sink target
- Cribbed from `scripts/youtube-player.py::VideoSlot` patterns
- Rate control: `HAPAX_LOCAL_MUSIC_PLAYBACK_RATE` env var (default
  1.0), clamped to [0.5, 2.0]
- EOF watchdog: when ffmpeg exits, advance to next track via
  `repository.select_next()`
- Graceful shutdown: SIGTERM ffmpeg + wait 5s + SIGKILL fallback

**T3.3** New `systemd/units/hapax-local-music.{service,timer}`:
- `Type=simple` long-running player service
- `OnFailure=notify-failure@%n.service` (existing pattern)
- `WantedBy=default.target`

**T3.4** Tests:
- `tests/studio_compositor/local_music/test_gate_state_machine.py` —
  vinyl on/off transitions, debounce window, halt-at-boundary
- `tests/studio_compositor/local_music/test_rate_env.py` —
  env-var parsing, clamping, default 1.0
- Player tests use `subprocess.Popen` mock; no live ffmpeg

### 4.2 Exit criterion

`uv run pytest tests/studio_compositor/local_music/ -q` all green.
`systemctl --user start hapax-local-music` succeeds with empty pool
(player idles waiting for tracks).

### 4.3 Commit

```
feat(local-music): #130 Phase 3 — VinylGate + Player + systemd unit
```

## 5. Phase 4 — Attribution writer + integration (~1h)

Spec §6 line 102 + §7 line 120.

### 5.1 Tasks

**T4.1** New `agents/studio_compositor/local_music/attribution.py`:
- Writes `/dev/shm/hapax-compositor/music-attribution.txt` in the
  exact format `album_overlay._draw_attrib` expects (3 lines: title,
  artist, source-url per spec §6 line 110)
- Atomic via tmp+rename
- Called from `LocalMusicPlayer` on each track-start

**T4.2** Tests at
`tests/studio_compositor/local_music/test_attribution_write.py`:
- Track frontmatter → file content matches album_overlay parser
  format

**T4.3** Smoke test: run player end-to-end with 3 fixture tracks;
verify `/dev/shm/hapax-compositor/music-attribution.txt` updates per
track + album_overlay renders attribution.

### 5.2 Exit criterion

album_overlay reads + renders local-music attribution correctly when
the player is active. End-to-end fixture passes.

### 5.3 Commit

```
feat(local-music): #130 Phase 4 — attribution writer + album_overlay integration
```

## 6. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| #127 SPLATTRIBUTION ships `vinyl_playing` differently than spec assumes | M | VinylGate rewire | Pre-flight check; if signal shape differs, document deviation in plan + adjust |
| Pool is empty at activation time | M | Player silent + ntfy spam | Spec §8 #3 default: silent + Prometheus gauge `hapax_local_music_empty_pool=1` + throttled ntfy. Explicit opt-in for SoundCloud fallback (#131) |
| ffmpeg subprocess crashes mid-track | M | Audio gap | EOF watchdog + retry-once policy; on second fail, mark track as bad + advance |
| Operator drops unlicensed track in pool | L (operator-discipline) | DMCA exposure | hapax-music-pool-validate enforces license SPDX; selection filters out invalid frontmatter |
| BPM/key auto-tagging produces wrong values | M | Bad selections | Per spec §8 #2: validate CLI offers librosa/madmom auto-compute but does NOT auto-write; operator authors frontmatter as contract |
| Repetition penalty too narrow → operator hears same track twice | L | Operator complaint | Default rolling 5; operator can raise via config |

## 7. Acceptance criteria

- [ ] Pool scaffold + 5+ seed tracks (operator-owned) under
      `~/music/hapax-pool/`
- [ ] `hapax-music-pool-validate` returns 0 on healthy pool
- [ ] `LocalMusicRepository.select_next()` produces deterministic
      output with fixed seed
- [ ] `VinylGate` debounces correctly (5s minimum per state)
- [ ] `LocalMusicPlayer` advances on EOF without intervention
- [ ] `HAPAX_LOCAL_MUSIC_PLAYBACK_RATE` env var honored
- [ ] `/dev/shm/hapax-compositor/music-attribution.txt` updates per
      track in album_overlay-readable format
- [ ] Selection NEVER returns unlicensed track (Hypothesis property
      assertion)
- [ ] Empty-pool case: Prometheus gauge fires + ntfy throttled
- [ ] systemd service runs cleanly + survives daimonion restart

## 8. Sequencing relative to other in-flight work

- **HARD BLOCKED on #127 SPLATTRIBUTION** for the `vinyl_playing`
  signal. Per spec §9 line 135.
- **Sibling to #131 SoundCloud integration** (also unplanned per
  D-31; LOW/BLOCKED). This plan is the first-line music source; #131
  is the fallback when this plan's pool is empty.
- **Independent of** D-30 SSOT, HSEA Phase 0, OQ-02, programme-layer
  phases.
- **Adjacent to** #142 vinyl rate (orthogonal — both are "how fast
  music plays" but one is analog turntable pitch, this is software
  ffmpeg rate).

Recommend operator + delta confirm #127 status before alpha picks
this up. If #127 is a long-tail item, the plan can stay drafted while
alpha works on other items.

## 9. References

- Spec: `docs/superpowers/specs/2026-04-18-local-music-repository-design.md`
- D-31 triage: `docs/research/2026-04-20-d31-unplanned-specs-triage.md`
- Sibling spec: `docs/superpowers/specs/2026-04-18-soundcloud-integration-design.md`
- Upstream blocker: `docs/superpowers/specs/2026-04-18-splattribution-no-vinyl-design.md`
- Player template: `scripts/youtube-player.py::VideoSlot`
- Attribution consumer: `agents/studio_compositor/album_overlay.py`
- Existing pattern: `agents/studio_compositor/youtube_description.py`
  (for systemd-service+ffmpeg+attribution shape reference)
