# LRR Phase 2 — Archive + Replay as Research Instrument — Plan

**Date:** 2026-04-15
**Author:** delta (pre-staging extraction from LRR epic plan; LRR execution remains alpha's workstream)
**Status:** DRAFT pre-staging — awaiting operator sign-off + LRR UP-1 close before Phase 2 open
**Spec reference:** `docs/superpowers/specs/2026-04-15-lrr-phase-2-archive-research-instrument-design.md`
**Branch target:** `feat/lrr-phase-2-archive-research-instrument`
**Cross-epic authority:** drop #62 §3 row 14 + §5 unified sequence UP-3 (HSEA Phase 1 depends on item 10)
**Unified phase mapping:** UP-3 Archive Instrument (~1500 LOC, 2-3 sessions)

---

## 0. Preconditions (MUST verify before task 1.1)

- [ ] **LRR UP-0 closed.**
- [ ] **LRR UP-1 (research registry) closed.** Verify `shared/research_marker.read_marker()` is importable and `/dev/shm/hapax-compositor/research-marker.json` exists with a valid condition_id.
- [ ] **FDL-1 deployed to a running compositor.** Verify `systemctl --user is-active studio-compositor` returns `active` and HLS segments are being written to `~/.cache/hapax-compositor/hls/`.
- [ ] **Disk space verification.** Check `~/hapax-state/` has ≥200 GB free (`df -h ~/hapax-state/`). If less, operator provisions storage BEFORE Phase 2 begins.
- [ ] **Compositor-stopped window OR operator approval to restart compositor mid-phase.** Several items (2, 4, 10) require compositor restart to pick up new config; Phase 2 opener coordinates with operator on restart timing.
- [ ] **Session claims the phase.** Write `~/.cache/hapax/relay/lrr-state.yaml::phase_statuses[2].status: open` + `current_phase: 2` + `current_phase_owner: <session>` + `current_phase_branch: feat/lrr-phase-2-archive-research-instrument`.

---

## 1. Item 1 — Re-enable archival pipeline

### 1.1 Inventory disabled services

- [ ] Read `systemd/README.md § Disabled Services` to enumerate disabled archival units
- [ ] For each unit: document current state (`systemctl --user show -p UnitFileState <unit>`), WHY it was disabled (from README + git log)
- [ ] Categorize: **safe to re-enable now** (recording services), **deferred** (RAG ingest, classification — out of Phase 2 scope per §4 decision 3)

### 1.2 Re-enable recording services

- [ ] For each safe-to-re-enable unit:
  - [ ] Verify unit file is syntactically valid: `systemctl --user cat <unit> | systemd-analyze verify -`
  - [ ] Verify disk paths exist + writable: `test -w "$(systemctl --user show -p WorkingDirectory --value <unit>)"` OR verify the target dir
  - [ ] `systemctl --user daemon-reload`
  - [ ] `systemctl --user enable --now <unit>`
  - [ ] Tail journal for 60s to verify startup: `journalctl --user -u <unit> -n 50 --no-pager`

### 1.3 Update systemd/README.md

- [ ] Edit `systemd/README.md § Disabled Services` to reflect Phase 2 re-enablements
- [ ] Keep deferred items documented as still-disabled + WHY (Phase 5+ dependency)

### 1.4 Commit item 1

- [ ] `git add systemd/README.md`
- [ ] `git commit -m "feat(lrr-phase-2): item 1 re-enable archival recording services (audio+video)"`
- [ ] Update `lrr-state.yaml::phase_statuses[2].deliverables[1].status: completed`

---

## 2. Item 2 — HLS segment persistence policy

### 2.1 Tests first

- [ ] Create `tests/studio_compositor/test_hls_archive_rotator.py`:
  - [ ] `test_segment_moved_to_archive_on_finalization` — fixture: place a fake `.ts` file in the cache dir; invoke rotator; assert file is now at `~/hapax-state/stream-archive/hls/YYYY-MM-DD/` and removed from cache
  - [ ] `test_playlist_m3u8_not_moved` — the live playlist pointer is NOT rotated
  - [ ] `test_incomplete_segment_not_moved` — a `.ts.partial` or actively-being-written file is skipped
  - [ ] `test_date_directory_created` — target dated dir created if not exists
  - [ ] `test_concurrent_writes_safe` — fcntl lock or similar to prevent rotation while segment is mid-write

### 2.2 Implementation

- [ ] Create `agents/hapax_archive/hls_rotator.py` (~100 LOC):
  - [ ] Watches `~/.cache/hapax-compositor/hls/` via `inotify_simple.INotify()` for `IN_MOVED_TO | IN_CLOSE_WRITE`
  - [ ] On finalization of a `.ts` segment, `shutil.move()` to `~/hapax-state/stream-archive/hls/YYYY-MM-DD/<segment_name>`
  - [ ] Creates dated dir if not exists
  - [ ] Writes a simple counter of rotations to `/var/run/user/.../hapax-archive-rotations.count` for observability

### 2.3 systemd unit

- [ ] Create `systemd/user/hapax-hls-archive-rotator.service`:
  - [ ] `Type=simple`
  - [ ] `Restart=on-failure`
  - [ ] `ExecStart=uv run python -m agents.hapax_archive.hls_rotator`
- [ ] Enable via `systemctl --user enable --now hapax-hls-archive-rotator.service`

### 2.4 Compositor unit edit

- [ ] Edit `systemd/user/studio-compositor.service`:
  - [ ] Remove `ExecStartPre=/usr/bin/find %h/.cache/hapax-compositor/hls -type f -delete`
  - [ ] Replace with `ExecStartPre=/bin/mkdir -p %h/.cache/hapax-compositor/hls %h/hapax-state/stream-archive/hls` (idempotent)
- [ ] `systemctl --user daemon-reload`
- [ ] Next compositor restart picks up the change; cache segments are preserved

### 2.5 Commit item 2

- [ ] Lint + format + pyright
- [ ] `git add agents/hapax_archive/hls_rotator.py tests/studio_compositor/test_hls_archive_rotator.py systemd/user/hapax-hls-archive-rotator.service systemd/user/studio-compositor.service`
- [ ] `git commit -m "feat(lrr-phase-2): item 2 HLS segment archive rotation (no auto-delete on compositor restart)"`
- [ ] Update `lrr-state.yaml::phase_statuses[2].deliverables[2].status: completed`

---

## 3. Item 3 — Per-segment metadata sidecar

### 3.1 Pydantic schema

- [ ] Create `shared/segment_metadata_schema.py`:
  - [ ] `class SegmentMetadata(BaseModel)`: segment_id, segment_path, segment_start_ts, segment_end_ts, condition_id, reaction_ids, active_activity, stimmung_snapshot, directives_hash, written_at
  - [ ] `class StimmungSnapshot(BaseModel)`: stance, dimensions (dict of 9 canonical dimensions)
- [ ] Tests: round-trip JSON serialization, validation of required fields

### 3.2 Sidecar writer

- [ ] Create `tests/hapax_archive/test_segment_sidecar_writer.py`:
  - [ ] `test_sidecar_written_on_segment_finalization` — fixture segment + state; invoke writer; assert `.json` sidecar exists alongside segment
  - [ ] `test_condition_id_from_research_marker` — mock marker; assert sidecar has correct condition_id
  - [ ] `test_reaction_ids_from_reactor_log` — seed reactor log with 2 reactions in segment window; assert both ids appear in sidecar
  - [ ] `test_stimmung_snapshot_captured` — fixture stimmung state; assert all 9 dimensions in sidecar
  - [ ] `test_directives_hash_computed` — fixture directives file; assert sha256 matches manual `sha256sum`
  - [ ] `test_atomic_write_no_partial` — kill writer mid-write; assert no partial JSON visible
  - [ ] `test_graceful_missing_reactor_log` — no reactor log file; sidecar has `reaction_ids: []`
- [ ] Create `agents/hapax_archive/segment_sidecar_writer.py` (~250 LOC):
  - [ ] Triggered by hls_rotator after a segment is moved
  - [ ] Constructs `SegmentMetadata` by reading research marker, reactor log tail, stimmung state file, directives file
  - [ ] Atomic-write via `shared/atomic_io.atomic_write_json`

### 3.3 Wire writer into rotator

- [ ] Extend `hls_rotator.py` to invoke the sidecar writer after each successful segment rotation

### 3.4 Commit item 3

- [ ] Lint + format + pyright
- [ ] `git add shared/segment_metadata_schema.py agents/hapax_archive/segment_sidecar_writer.py tests/shared/test_segment_metadata_schema.py tests/hapax_archive/test_segment_sidecar_writer.py`
- [ ] `git commit -m "feat(lrr-phase-2): item 3 per-segment metadata sidecar JSON writer"`
- [ ] Update `lrr-state.yaml::phase_statuses[2].deliverables[3].status: completed`

---

## 4. Item 5 — Audio archive (parallel to item 3)

### 4.1 Audio capture agent

- [ ] Create `tests/hapax_archive/test_audio_capture.py`:
  - [ ] `test_capture_writes_audio_file` — mock pw-cat; invoke capture; assert audio file exists in dated dir
  - [ ] `test_audio_sidecar_matches_video_schema` — audio sidecar has same fields as video plus `audio_source`
  - [ ] `test_capture_resumes_on_pipewire_error` — simulate pw-cat failure; capture retries after backoff
- [ ] Create `agents/hapax_archive/audio_capture.py` (~180 LOC):
  - [ ] Subprocess-launches `pw-cat --record --target "mixer_master"` (or `gst-launch-1.0` with PipeWire source as fallback)
  - [ ] Rotates output files every 6s (matching video segment duration)
  - [ ] Writes sidecar per rotation
  - [ ] Format: Opus by default (decision gate per spec §7 Q1)

### 4.2 systemd unit

- [ ] Create `systemd/user/hapax-audio-archive-capture.service`
- [ ] Enable

### 4.3 Commit item 5

- [ ] Lint + format + pyright
- [ ] `git add agents/hapax_archive/audio_capture.py tests/hapax_archive/test_audio_capture.py systemd/user/hapax-audio-archive-capture.service`
- [ ] `git commit -m "feat(lrr-phase-2): item 5 audio archive capture + rotation + sidecars"`
- [ ] Update `lrr-state.yaml::phase_statuses[2].deliverables[5].status: completed`

---

## 5. Item 4 — Research-marker frame injection

### 5.1 Tests

- [ ] Create `tests/studio_compositor/test_research_marker_frame_source.py`:
  - [ ] `test_overlay_renders_on_marker_change` — update marker file mtime; invoke render; assert overlay Cairo draws contain condition_id text
  - [ ] `test_overlay_fades_after_3s` — advance time 4s after change; assert overlay no longer renders
  - [ ] `test_no_overlay_steady_state` — no marker change; assert no render
  - [ ] `test_inotify_watcher_responds_to_mtime` — mock inotify event; assert overlay triggered

### 5.2 Implementation

- [ ] Create `agents/studio_compositor/research_marker_frame_source.py` (~150 LOC):
  - [ ] `class ResearchMarkerFrameSource(CairoSource)`:
    - [ ] `__init__(zone: str = "fullscreen_overlay")`
    - [ ] Inotify watcher on `/dev/shm/hapax-compositor/research-marker.json`
    - [ ] `_render()` renders the overlay for 3 seconds from last change
    - [ ] Design-language color tokens for the overlay background + text

### 5.3 Register via SourceRegistry

- [ ] After item 10 lands (later in the phase), register `ResearchMarkerFrameSource` via `SourceRegistry.register(...)` in the compositor bootstrap

### 5.4 Commit item 4

- [ ] Lint + format + pyright
- [ ] `git add agents/studio_compositor/research_marker_frame_source.py tests/studio_compositor/test_research_marker_frame_source.py`
- [ ] `git commit -m "feat(lrr-phase-2): item 4 research-marker frame injection overlay on condition change"`
- [ ] Update `lrr-state.yaml::phase_statuses[2].deliverables[4].status: completed`

---

## 6. Item 10 — Layout-declared `video_out` surfaces migration + SourceRegistry

**LOAD-BEARING for HSEA Phase 1 (UP-4) per drop #62 §3 row 14.** Ships mid-phase so HSEA Phase 1 unblock is visible early.

### 6.1 `SourceRegistry` implementation

- [ ] Create `tests/studio_compositor/test_source_registry.py`:
  - [ ] `test_register_source_class` — register a stub CairoSource subclass for zone "test_zone" with priority 1; assert `get_for_zone("test_zone")` returns it
  - [ ] `test_priority_ordering` — register 3 sources for same zone with priorities 1/5/10; assert get_for_zone returns highest-priority
  - [ ] `test_register_same_class_twice` — registering the same class twice is idempotent (no duplicate in registry)
  - [ ] `test_enumerate_all_sources` — `all_sources()` returns list of all registered
  - [ ] `test_zone_not_found` — `get_for_zone("nonexistent")` returns None gracefully
- [ ] Create `agents/studio_compositor/source_registry.py` (~200 LOC):
  - [ ] `class SourceRegistry`:
    - [ ] Module-level singleton
    - [ ] `register(source_cls, zone, priority)`
    - [ ] `get_for_zone(zone) -> type[CairoSource] | None`
    - [ ] `all_sources() -> list[tuple[type[CairoSource], str, int]]`
    - [ ] `clear()` for tests only

### 6.2 `OutputRouter.from_layout()` wiring

- [ ] Create `tests/studio_compositor/test_output_router_layout.py`:
  - [ ] `test_from_layout_constructs_sinks` — fixture layout JSON with 4 video_out surfaces; assert OutputRouter constructs 4 sinks
  - [ ] `test_fallback_to_hardcoded_on_layout_error` — fixture with invalid JSON; assert hardcoded fallback paths used + warning log
  - [ ] `test_layout_declared_surfaces_registered` — `OutputRouter.from_layout()` passes surfaces to compositor.start()
- [ ] Edit `agents/studio_compositor/compositor.py`:
  - [ ] Replace hardcoded sink construction in `start()` with `OutputRouter.from_layout(config_path)` call
  - [ ] Keep hardcoded paths as fallback if layout lookup fails
- [ ] Edit `agents/studio_compositor/output_router.py` if not already supporting `from_layout()`:
  - [ ] `@classmethod def from_layout(cls, layout_path: Path) -> OutputRouter`
  - [ ] Parses layout JSON, constructs `OutputBinding` instances for each `video_out` surface, returns configured router

### 6.3 `config/compositor-layouts/default.json` edit

- [ ] Add `video_out` surfaces to the layout:
  - [ ] `{"kind": "video_out", "sink": "/dev/video42", "codec": "yuv422"}` — v4l2 loopback
  - [ ] `{"kind": "video_out", "sink": "rtmp://127.0.0.1:1935/studio", "codec": "h264"}` — MediaMTX relay
  - [ ] `{"kind": "video_out", "sink": "~/.cache/hapax-compositor/hls/playlist.m3u8", "codec": "h264"}` — HLS playlist
  - [ ] `{"kind": "video_out", "sink": "~/hapax-state/stream-archive/", "codec": "h264"}` — archive branch (from item 2 rotation)
- [ ] Verify valid JSON

### 6.4 `config/compositor-zones.yaml` (NEW file for HSEA Phase 1 consumption)

- [ ] Create `config/compositor-zones.yaml`:
  - [ ] `schema_version: 1`
  - [ ] `zones:` — list of currently-existing zones (album_overlay, sierpinski_*, token_pole, etc.) with position + size + default owner
  - [ ] Leave room for HSEA Phase 1 to append 5 new zones (hud_top_left, research_state_top_right, prompt_glass_left_middle, orchestration_strip_lower, governance_queue_pill_bottom_center)
- [ ] Tests: `tests/config/test_compositor_zones.py` — load + validate + no duplicate zone names

### 6.5 Register existing Cairo sources

- [ ] Edit compositor bootstrap to `SourceRegistry.register(...)` each existing CairoSource (album overlay, sierpinski, overlay zones, token pole) with their current zone names
- [ ] Verify existing surfaces still render after migration (no visual regression)

### 6.6 Commit item 10

- [ ] Lint + format + pyright
- [ ] `git add agents/studio_compositor/source_registry.py agents/studio_compositor/output_router.py agents/studio_compositor/compositor.py config/compositor-layouts/default.json config/compositor-zones.yaml tests/studio_compositor/test_source_registry.py tests/studio_compositor/test_output_router_layout.py tests/config/test_compositor_zones.py`
- [ ] `git commit -m "feat(lrr-phase-2): item 10 SourceRegistry + layout-declared video_out + compositor-zones.yaml (HSEA Phase 1 unblock)"`
- [ ] Update `lrr-state.yaml::phase_statuses[2].deliverables[10].status: completed`
- [ ] **HSEA Phase 1 unblock announcement:** write a brief inflection to peer sessions noting that UP-4 preconditions are now satisfied on the SourceRegistry/OutputRouter/zones axis

---

## 7. Item 6 — Archive search CLI

### 7.1 Tests

- [ ] Create `tests/scripts/test_archive_search.py`:
  - [ ] `test_by_condition_returns_matching_segments` — fixture with 3 segments tagged with 2 different conditions; `by-condition cond-1` returns 2
  - [ ] `test_by_reaction_finds_segment` — fixture segment with reaction_ids=["reaction-abc"]; `by-reaction reaction-abc` returns the segment
  - [ ] `test_by_timerange_filters_correctly` — fixture 5 segments over 30s window; `by-timerange 10s 20s` returns 2
  - [ ] `test_extract_copies_segment` — fixture segment; `extract <id> /tmp/out.ts`; assert file copied
  - [ ] `test_stats_prints_summary` — assert output contains total count + date range
  - [ ] `test_verify_flags_orphaned_sidecar` — create a sidecar without a matching segment file; `verify <condition>` flags it
  - [ ] `test_verify_flags_orphaned_segment` — create a segment without a sidecar; `verify` flags it

### 7.2 Implementation

- [ ] Create `scripts/archive-search.py` (~350 LOC with all 6 subcommands):
  - [ ] argparse with subcommands
  - [ ] Scanner uses `os.scandir` recursively; streams results
  - [ ] For large archives, optional `--index-rebuild` flag that creates a SQLite index for faster lookups

### 7.3 Commit item 6

- [ ] Lint + format + pyright
- [ ] `git add scripts/archive-search.py tests/scripts/test_archive_search.py`
- [ ] `git commit -m "feat(lrr-phase-2): item 6 archive-search.py CLI with 6 subcommands"`
- [ ] Update `lrr-state.yaml::phase_statuses[2].deliverables[6].status: completed`

---

## 8. Item 7 — Vault integration

### 8.1 Obsidian template

- [ ] Create `~/Documents/Personal/50-templates/tpl-archive-segment.md` with the frontmatter + template content from spec §3.7

### 8.2 `note` subcommand extension

- [ ] Extend `scripts/archive-search.py` with `note <segment_id>` subcommand
- [ ] Looks up the segment's sidecar metadata
- [ ] Renders the template with metadata (simple string substitution for `{{field}}` placeholders)
- [ ] Writes the rendered note to `~/Documents/Personal/30-areas/legomena-live/archive/YYYY-MM/segment-<id>.md`
- [ ] Creates parent dirs if not exists

### 8.3 Tests

- [ ] `tests/scripts/test_archive_note_creation.py`:
  - [ ] `test_note_created_from_template` — fixture segment + template; invoke note; assert file exists + content matches expected
  - [ ] `test_parent_dir_auto_created`
  - [ ] `test_existing_note_not_overwritten` — `note` on a segment that already has a note; assert no overwrite (or --force flag required)

### 8.4 Commit item 7

- [ ] `git add scripts/archive-search.py tests/scripts/test_archive_note_creation.py`
- [ ] NOTE: the Obsidian template file at `~/Documents/Personal/50-templates/` is NOT committed (it's in the operator's vault, not the repo). Document its creation in the handoff instead.
- [ ] `git commit -m "feat(lrr-phase-2): item 7 vault integration (note subcommand + archive template)"`
- [ ] Update `lrr-state.yaml::phase_statuses[2].deliverables[7].status: completed`

---

## 9. Item 9 — Purge CLI

### 9.1 Tests

- [ ] Create `tests/scripts/test_archive_purge.py`:
  - [ ] `test_dry_run_no_deletion` — fixture archive; `--dry-run` + `--condition cond-test`; assert summary printed, no files deleted
  - [ ] `test_real_purge_requires_consent_revocation` — fixture condition with ACTIVE consent; `--condition cond-test` without `--force` → refuse
  - [ ] `test_real_purge_with_revoked_consent` — fixture condition with REVOKED consent; purge succeeds
  - [ ] `test_force_bypass` — `--force "operator justification"` bypasses consent check
  - [ ] `test_audit_log_entry_per_deletion` — real purge deletes 3 segments; audit log has 3 entries
  - [ ] `test_dry_run_no_audit_log` — `--dry-run` does NOT write to audit log

### 9.2 Implementation

- [ ] Create `scripts/archive-purge.py` (~250 LOC):
  - [ ] Parses `--condition`, `--dry-run`, `--confirm`, `--force`
  - [ ] Queries `shared/consent.py::ConsentRegistry` for the condition's consent state
  - [ ] Enumerates segments by condition (uses `archive-search.py by-condition` internally OR imports the scan logic)
  - [ ] Dry-run: prints summary, exits
  - [ ] Real: deletes + writes audit log entry per deletion

### 9.3 Commit item 9

- [ ] Lint + format + pyright
- [ ] `git add scripts/archive-purge.py tests/scripts/test_archive_purge.py`
- [ ] `git commit -m "feat(lrr-phase-2): item 9 archive-purge.py CLI + consent revocation tie-in"`
- [ ] Update `lrr-state.yaml::phase_statuses[2].deliverables[9].status: completed`

---

## 10. Item 8 — Lifecycle policy documentation

### 10.1 Retention policy doc

- [ ] Create `docs/superpowers/specs/2026-04-15-lrr-phase-2-archive-retention.md`:
  - [ ] Active condition: indefinite retention rationale + criteria
  - [ ] Closed condition: retention until claim analyzed rationale + criteria
  - [ ] Revocation: consent-contract tied purge workflow (cross-ref to item 9)
  - [ ] No automatic deletion without explicit policy change
  - [ ] Disk pressure escalation: governance queue task workflow (cross-ref to HSEA Phase 0 0.2)

### 10.2 Commit item 8

- [ ] `git add docs/superpowers/specs/2026-04-15-lrr-phase-2-archive-retention.md`
- [ ] `git commit -m "docs(lrr-phase-2): item 8 archive retention policy"`
- [ ] Update `lrr-state.yaml::phase_statuses[2].deliverables[8].status: completed`

---

## 11. Phase 2 close

### 11.1 Smoke tests (spec §5 exit criteria)

- [ ] Archival services re-enabled + running (`systemctl --user list-units | grep hapax-archive`)
- [ ] Segments in `~/hapax-state/stream-archive/hls/` (run compositor 60s + count)
- [ ] Sidecars parseable + all fields populated (pick random segment + `jq`)
- [ ] Condition change triggers visible frame marker (run `research-registry.py open test` + review HLS playback at that timestamp)
- [ ] `archive-search.py by-condition cond-phase-a-baseline-qwen-001` returns segments
- [ ] `archive-search.py note <segment_id>` creates vault note
- [ ] `archive-purge.py --dry-run --condition cond-test` prints summary without deletion
- [ ] Retention policy doc exists
- [ ] Audio archive populated
- [ ] Layout-declared video_out surfaces in default.json
- [ ] `config/compositor-zones.yaml` exists with current zones
- [ ] `SourceRegistry` register + lookup works
- [ ] HSEA Phase 1 pre-open dry-run: stub Cairo source registers + renders in a zone

### 11.2 Handoff doc

- [ ] Write `docs/superpowers/handoff/2026-04-15-lrr-phase-2-complete.md`:
  - [ ] 10 items shipped + PR/commit links
  - [ ] Disk usage snapshot (pre + post Phase 2)
  - [ ] HSEA Phase 1 unblock confirmation
  - [ ] Next phase (LRR Phase 3 — Hardware Validation + Hermes 3 Prep) preconditions

### 11.3 State file close-out

- [ ] `lrr-state.yaml::phase_statuses[2].status: closed` + `closed_at` + `handoff_path`
- [ ] `deliverables[1..10].status: completed`
- [ ] `last_completed_phase: 2`
- [ ] Request operator update to `unified_sequence[UP-3].status: closed`

### 11.4 Final verification

- [ ] 10+ `feat(lrr-phase-2): …` commits in `git log`
- [ ] All 15 spec exit criteria pass
- [ ] Fresh shell shows `LRR: Phase 2 · status=closed`
- [ ] Inflection to peers: Phase 2 closed; HSEA Phase 1 + LRR Phase 3 unblocked

---

## 12. Cross-epic coordination

- **LRR Phase 1** provides research marker (read by item 4 frame injection + item 3 sidecar writer) + condition_id (tagged in every sidecar + reactor log). Phase 2 does NOT modify Phase 1 artifacts.
- **HSEA Phase 1 (UP-4)** depends on item 10 SourceRegistry + `config/compositor-zones.yaml` per drop #62 §3 row 14. Phase 2 designs item 10's API with HSEA Phase 1's 5-source use case in mind.
- **LRR Phase 3 (UP-5)** uses the re-enabled archival pipeline for condition comparison work (archive serves as the raw data for A-vs-A' analysis once Phase 5a lands).
- **LRR Phase 8 (UP-11)** adds further layout-declared surfaces (objective overlay, studio view tile, terminal capture, PR/CI status) on top of item 10's pattern. Phase 2 ships the mechanism; Phase 8 uses it.

---

## 13. End

Standalone per-phase plan for LRR Phase 2 Archive + Replay as Research Instrument. Pre-staging; not executed until UP-1 closed and a session claims the phase. Companion spec at `docs/superpowers/specs/2026-04-15-lrr-phase-2-archive-research-instrument-design.md`.

Pre-staging authored by delta as coordinator-plus-extractor per the 06:45Z role activation.

— delta, 2026-04-15
