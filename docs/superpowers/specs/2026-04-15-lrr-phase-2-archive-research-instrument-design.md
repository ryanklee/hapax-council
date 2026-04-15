# LRR Phase 2 — Archive + Replay as Research Instrument — Design Spec

**Date:** 2026-04-15
**Author:** delta (pre-staging extraction from LRR epic spec; LRR execution remains alpha's workstream)
**Status:** DRAFT pre-staging — awaiting operator sign-off + LRR UP-1 close before Phase 2 open
**Epic reference:** `docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md` §5 Phase 2 (canonical source)
**Plan reference:** `docs/superpowers/plans/2026-04-15-lrr-phase-2-archive-research-instrument-plan.md` (companion TDD checkbox plan)
**Branch target:** `feat/lrr-phase-2-archive-research-instrument`
**Cross-epic authority:** `docs/research/2026-04-14-cross-epic-fold-in-lrr-hsea.md` (drop #62) — §3 row 14 (surface registration) + §5 unified sequence row UP-3 take precedence over any conflicting claim in this spec
**Unified phase mapping:** **UP-3 Archive Instrument** (drop #62 §5 line 137): depends on UP-1 closed; 2-3 sessions, ~1500 LOC; blocks UP-4 (HSEA Phase 1 visibility surfaces) because HSEA Phase 1 uses the SourceRegistry/OutputRouter registration pattern Phase 2 ships in item 10

---

## 1. Phase goal

Re-enable the currently-disabled archival pipeline (audio/video recording, classification, RAG ingest) with research-grade metadata injection, per-segment condition tags, and retention guarantees. **Archive moves from "liability" to "research instrument"** under Option B: archived segments become the raw data for A-vs-A' (baseline vs treatment) statistical analysis, so losing archive data is equivalent to losing the control arm of the experiment.

**What this phase is:** re-enable the disabled archival services, move HLS segments to a persistent `~/hapax-state/stream-archive/` tree, attach `condition_id`-tagged JSON sidecars to every segment, inject visible research-marker frames on condition changes, archive audio parallel to video, ship an `archive-search.py` CLI, integrate with the operator's Obsidian vault, codify the retention policy, ship a consent-revocation-tied purge CLI, and **migrate the stream output path to layout-declared `video_out` surfaces** via the `OutputRouter` abstraction that already exists but is not yet wired up.

**What this phase is NOT:** this phase does not re-enable the RAG ingest pipeline at full volume (that's Phase 5 substrate work + a separate Qdrant cardinality decision), does not ship the `objective-overlay` or the Logos studio view tile (LRR Phase 8), does not ship HSEA visibility surfaces (HSEA Phase 1 / UP-4), does not author new research claims (ongoing operator work), and does not add automatic deletion policies (the retention policy is explicit no-auto-delete without explicit policy change).

**Theoretical grounding** (per LRR epic spec): under Option B, archived segments are the raw data for A-vs-A' analysis. The impact analysis §Archive captures why this is load-bearing — without a durable archive, the Condition A baseline cannot be retroactively compared against Condition A' treatment data once the substrate swap happens.

---

## 2. Dependencies + preconditions

**Cross-epic (from drop #62):**

1. **LRR UP-0 (verification) closed.** Standard LRR phase precondition.

2. **LRR UP-1 (research registry) closed.** Phase 2 depends on Phase 1's `condition_id` + `research-marker.json` infrastructure:
   - Per-segment sidecars include `condition_id` from the research marker (deliverable 3.3)
   - Research-marker frame injection (deliverable 3.4) is triggered by `research-registry.py open|close` state transitions
   - Archive search CLI (deliverable 3.6) has a `by-condition` subcommand that consumes the condition_id taxonomy
   - Per drop #62 §3 row 2, `condition.yaml` is LRR Phase 1 owned; Phase 2 reads via atomic-read pattern

3. **FDL-1 deployed to a running compositor.** Phase 2 cannot meaningfully ship if the compositor is not producing HLS segments for the pipeline to consume. Post-mobo-swap verification is required.

4. **HSEA Phase 1 (UP-4) consumes this phase's `SourceRegistry`/`OutputRouter` pattern** (drop #62 §3 row 14). Phase 2 item 10 is the load-bearing migration that enables HSEA Phase 1 surface registration. HSEA Phase 1 onboarding verifies UP-3 closed; without UP-3's layout-declared `video_out` migration, HSEA Phase 1 cannot register its 5 new Cairo sources cleanly.

**Intra-epic:** LRR Phase 1 closed. No other LRR phase prerequisite.

**Infrastructure:**

1. `systemd/README.md § Disabled Services` (existing) — documents which archival services were disabled. Phase 2 item 1 reads this as the starting point for re-enablement.
2. `studio-compositor.service` (existing, running) — currently runs `ExecStartPre=/usr/bin/find %h/.cache/hapax-compositor/hls -type f -delete`; Phase 2 item 2 replaces this pre-start purge with rotation to `~/hapax-state/stream-archive/hls/YYYY-MM-DD/`.
3. `~/hapax-state/` tmpfs/disk (existing) — Phase 2 creates `stream-archive/` subtree.
4. `agents/studio_compositor/compositor.py` + `rtmp_output.py` (existing) — currently has hardcoded output paths; Phase 2 item 10 migrates to `OutputRouter.from_layout()` driven construction.
5. `agents/studio_compositor/output_router.py` (existing, "Phase 5b3" per the epic spec) — the `OutputRouter` abstraction already exists but is not yet driving production output.
6. `config/compositor-layouts/default.json` (existing) — layout file; currently declares zero `video_out` surfaces; Phase 2 item 10 adds them.
7. `/dev/video42` (existing v4l2loopback device for OBS fallback), `rtmp://127.0.0.1:1935/studio` (existing MediaMTX relay) — current stream sinks that become layout-declared surfaces.
8. `shared/research_marker.py` (LRR Phase 1 deliverable) — used to read condition changes for item 4 frame injection.
9. `scripts/research-registry.py` (LRR Phase 1 deliverable) — hooked by item 4 for condition change detection.
10. `~/Documents/Personal/30-areas/legomena-live/` (existing or to-be-created) — operator's vault archive subtree for item 7 integration.
11. `shared/consent.py::ConsentRegistry` (existing) — consulted by item 9 purge CLI for consent-revocation lookups.
12. `qdrant-client` library (existing) — used by item 7 vault integration if vault notes get ingested for search.

---

## 3. Deliverables (10 items)

Each item below extracts directly from LRR epic spec §5 Phase 2 items 1–10.

### 3.1 Re-enable archival pipeline (item 1)

**Scope:**
- Read `systemd/README.md § Disabled Services` to enumerate the currently-disabled archival services
- Identify which ones are safe to re-enable vs which ones are disabled for reasons Phase 2 does not resolve (e.g., Qdrant inode pressure was the original disabling reason per LRR Phase 0 verification work; Phase 0 should have tightened the lifecycle rule before Phase 2 opens)
- Re-enable selectively: audio recording + video recording + sidecar writing for Phase 2; DEFER classification + RAG ingest to later phases (Phase 5+) because those have independent concerns
- For each re-enabled service:
  - Verify the systemd unit file still exists and is syntactically valid
  - Verify any required disk paths exist and are writable
  - Run `systemctl --user daemon-reload` + `systemctl --user enable --now <service>`
  - Monitor for the first successful run via journal tail (`journalctl --user -u <service> -f` for ~60 seconds after enablement)
- **Target files:**
  - Various `systemd/user/*.service` files (re-enabled by `systemctl enable`; no file edits needed unless a unit's `WantedBy=` list needs updating)
  - `systemd/README.md` (update § Disabled Services to reflect Phase 2 re-enablements)
- **Deliverable size:** ~50 LOC (mostly systemd unit state changes + doc edits), 0.3 day serial work (plus operator verification of stream health post-reenablement)

### 3.2 HLS segment persistence policy (item 2)

**Scope:**
- **Current behavior:** `studio-compositor.service` ExecStartPre deletes all files in `~/.cache/hapax-compositor/hls` on service start (`/usr/bin/find %h/.cache/hapax-compositor/hls -type f -delete`)
- **New behavior:** segments ROTATE to `~/hapax-state/stream-archive/hls/YYYY-MM-DD/` on HLS segment rotation (not on service start)
- Rotation trigger: when `hlssink2` finalizes a segment, a sidecar-writer systemd path or inotify watcher moves the finalized segment + its `.ts` / `.m3u8` tail to the dated archive directory
- Retention: **indefinite during active conditions**; no automatic deletion
- `studio-compositor.service` ExecStartPre REMOVED (or changed to an idempotent directory-create instead of the delete)
- The HLS playlist pointer (`~/.cache/hapax-compositor/hls/playlist.m3u8`) continues to reference the CURRENT live segments as before; the archive tree only holds rotated-out segments
- **Target files:**
  - `systemd/user/studio-compositor.service` (edit ExecStartPre)
  - `systemd/user/hapax-hls-archive-rotator.service` + `.path` or `.timer` (new unit that watches `~/.cache/hapax-compositor/hls` for segment finalization)
  - OR: extend the compositor's existing sidecar writer to do the rotation inline (simpler if the compositor already has a sidecar writer for RTMP; verify at open time)
- **Deliverable size:** ~150 LOC (systemd unit + rotation script), 0.3 day serial work

### 3.3 Per-segment metadata sidecar (item 3)

**Scope:**
- Each HLS segment gets a `.json` sidecar file alongside it in the archive tree
- Schema:
  ```json
  {
    "segment_id": "<uuid>",
    "segment_path": "hls/2026-04-15/segment-00042.ts",
    "segment_start_ts": "2026-04-15T06:50:00.000Z",
    "segment_end_ts": "2026-04-15T06:50:06.000Z",
    "condition_id": "cond-phase-a-baseline-qwen-001",
    "reaction_ids": ["reaction-abc", "reaction-xyz"],
    "active_activity": "react",
    "stimmung_snapshot": {
      "stance": "curious",
      "dimensions": {
        "intensity": 0.42,
        "tension": 0.18,
        "depth": 0.61,
        "coherence": 0.55,
        "spectral_color": 0.3,
        "temporal_distortion": 0.1,
        "degradation": 0.05,
        "pitch_displacement": 0.0,
        "diffusion": 0.22
      }
    },
    "directives_hash": "<sha256>",
    "written_at": "2026-04-15T06:50:06.500Z"
  }
  ```
- Writer: the sidecar-writer runs when a segment is finalized (same trigger as the rotation in deliverable 3.2); reads the research marker for `condition_id`, queries the reactor log for `reaction_ids` whose timestamp falls in the segment window, reads stimmung state from `/dev/shm/hapax-vla/stimmung.json` or equivalent, reads current activity from the director loop state
- `directives_hash`: SHA-256 of the current `grounding_directives.py` file (or whichever directives manifest is authoritative), for change detection when directives are modified mid-condition
- **Target files:**
  - `agents/hapax_archive/segment_sidecar_writer.py` (~250 LOC sidecar assembly + atomic write)
  - `shared/segment_metadata_schema.py` (~80 LOC pydantic model)
  - `tests/hapax_archive/test_segment_sidecar_writer.py` (~180 LOC)
- **Deliverable size:** ~510 LOC, 0.5 day serial work

### 3.4 Research-marker frame injection (item 4)

**Scope:**
- At every condition change (when `research-registry.py open|close` modifies `/dev/shm/hapax-compositor/research-marker.json`), write a visible text overlay to the HLS stream for ~3 seconds
- Overlay content: "CONDITION CHANGE → cond-phase-a-prime-hermes-8b-002" with the condition_id prominently displayed
- This gives frame-accurate boundary detection in the archive: a reviewer can scrub to the overlay and find the exact condition transition timestamp
- Implementation: a new `ResearchMarkerFrameSource(CairoSource)` that watches research-marker.json via inotify; on mtime change, renders the overlay for 3 seconds then hides
- Zone: full-screen overlay (with a high opacity) for the 3-second window, so the marker is unambiguous
- **Coordination with Phase 2 (HSEA)** is not required — this is LRR-owned; HSEA reads the segments for playback but does not inject its own markers
- **Target files:**
  - `agents/studio_compositor/research_marker_frame_source.py` (~150 LOC Cairo source)
  - `tests/studio_compositor/test_research_marker_frame_source.py` (~100 LOC)
- **Deliverable size:** ~250 LOC, 0.3 day serial work

### 3.5 Audio archive (item 5)

**Scope:**
- Capture `mixer_master` (the main mixed output) + `echo_cancel_source` (the microphone after echo cancellation) to `~/hapax-state/stream-archive/audio/YYYY-MM-DD/`
- Same retention as video (indefinite during active conditions)
- Format: Opus or FLAC (Opus preferred for size; FLAC for lossless research analysis if operator prefers). Decision gate at open time.
- Segment rotation: ~6 second segments matching the HLS video rotation so audio + video segments can be correlated
- Each audio segment has a `.json` sidecar with the same schema as video (deliverable 3.3) + an `audio_source: mixer_master|echo_cancel_source` field
- Capture pipeline: new systemd unit `hapax-audio-archive-capture.service` that uses `pw-cat` or similar to capture the PipeWire source
- **Target files:**
  - `agents/hapax_archive/audio_capture.py` (~180 LOC)
  - `systemd/user/hapax-audio-archive-capture.service` (new)
  - `tests/hapax_archive/test_audio_capture.py` (~80 LOC — mocks the PipeWire source)
- **Deliverable size:** ~310 LOC, 0.3 day serial work

### 3.6 Archive search CLI (item 6)

**Scope:**
- `scripts/archive-search.py` with subcommands:
  - `by-condition <condition_id>` — returns all segments (video + audio) whose sidecar has the matching condition_id
  - `by-reaction <reaction_id>` — returns the segment(s) whose sidecar's `reaction_ids` list contains the matching reaction
  - `by-timerange <start> <end>` — returns all segments whose `segment_start_ts` falls in the range
  - `extract <segment_id> <output>` — copies a segment to a specified output path (for operator analysis / sharing)
  - `stats` — prints summary stats: total segments, per-condition breakdown, date range, disk usage
  - `verify <condition_id>` — runs consistency checks: every sidecar parseable, segment files exist, no orphaned sidecars or segments
- Implementation: scan the `~/hapax-state/stream-archive/` tree for `.json` sidecars, filter by the subcommand criteria
- Performance: for large archives, implement the scan with `os.scandir` (not `os.walk` recursion) and stream results rather than loading all sidecars into memory
- **Target files:**
  - `scripts/archive-search.py` (~350 LOC including all 6 subcommands)
  - `tests/scripts/test_archive_search.py` (~200 LOC)
- **Deliverable size:** ~550 LOC, 0.5 day serial work

### 3.7 Vault integration (item 7)

**Scope:**
- Each archived segment metadata file optionally links to a vault note at `~/Documents/Personal/30-areas/legomena-live/archive/YYYY-MM/segment-<id>.md`
- Note is Templater-rendered from segment metadata; operator adds commentary as the segment is reviewed
- Template structure:
  ```markdown
  ---
  type: archive-segment
  segment_id: <id>
  condition_id: cond-...
  segment_start: 2026-04-15T06:50:00Z
  reactions: [reaction-abc, reaction-xyz]
  ---

  # Segment <id>

  ## Auto-populated
  - Condition: {{condition_id}}
  - Duration: 6.0s
  - Reactions: {{reaction_count}}
  - Active activity: {{active_activity}}
  - Stimmung stance: {{stance}}

  ## Operator commentary
  (empty; operator fills in)

  ## Claim links
  (empty; operator links to analytical claims)
  ```
- This becomes the operator's research notebook linking segments to claim state
- Vault note creation is OPTIONAL (not every segment gets a note; the operator decides which segments warrant notes; the sidecar writer does not create notes automatically)
- A companion CLI subcommand: `archive-search.py note <segment_id>` creates the vault note from the template + segment metadata
- **Target files:**
  - `scripts/archive-search.py` extension (+50 LOC for `note` subcommand)
  - `~/Documents/Personal/50-templates/tpl-archive-segment.md` (Obsidian template)
  - `tests/scripts/test_archive_note_creation.py` (~50 LOC)
- **Deliverable size:** ~150 LOC (mostly template content), 0.2 day serial work

### 3.8 Lifecycle policy (item 8)

**Scope:**
- Document retention rules in `docs/superpowers/specs/2026-04-15-lrr-phase-2-archive-retention.md` (or similar):
  - **Active condition data:** indefinite retention while the condition is `closed_at: null` in its condition.yaml
  - **Closed condition data:** retained until the claim linked to that condition is analyzed AND a report has been authored (operator decision; not automatic)
  - **All condition data:** revocable per consent contract (see deliverable 3.9 purge CLI)
  - **No automatic deletion** without explicit policy change via a `DEVIATION-NNN` or a new retention policy doc
- Retention policy is READ by Phase 2 tooling but ENFORCED only by the purge CLI (no automatic background deletion)
- **Target file:** `docs/superpowers/specs/2026-04-15-lrr-phase-2-archive-retention.md` (~100 lines markdown)
- **Deliverable size:** ~100 lines markdown, 0.1 day serial work

### 3.9 Purge CLI (item 9)

**Scope:**
- `scripts/archive-purge.py --condition <id> --confirm` performs auditable deletion tied to the consent revocation flow
- Prerequisites for purge:
  - The condition's consent contract has been revoked (check via `shared/consent.py::ConsentRegistry`)
  - OR explicit `--force` flag with operator justification string
- Purge steps:
  1. Enumerate all segments (video + audio + sidecars + vault notes) whose `condition_id` matches
  2. Print a dry-run summary: count of segments + total disk usage + date range
  3. Wait for `--confirm` interactive prompt or CLI flag
  4. Delete segments one at a time, writing an audit log entry per deletion
  5. Audit log: `~/hapax-state/stream-archive/audit/purge-YYYY-MM-DD.jsonl` with per-entry schema: `{deleted_at, segment_id, condition_id, reason, actor, size_bytes}`
- **Target files:**
  - `scripts/archive-purge.py` (~250 LOC)
  - `~/hapax-state/stream-archive/audit/` directory (created on first purge)
  - `tests/scripts/test_archive_purge.py` (~180 LOC including dry-run tests)
- **Deliverable size:** ~430 LOC, 0.5 day serial work

### 3.10 Layout-declared `video_out` surfaces migration (item 10)

**Scope (HSEA Phase 1 dependency per drop #62 §3 row 14):**

This is the item that unblocks HSEA Phase 1 (UP-4) for surface registration. HSEA Phase 1 needs the `SourceRegistry` / `OutputRouter` pattern to register its 5 new Cairo sources cleanly; without this migration, HSEA Phase 1 cannot ship its overlays.

- **Current state:** `agents/studio_compositor/output_router.py` exists (Phase 5b3 per epic spec) but `config/compositor-layouts/default.json` declares ZERO `video_out` surfaces. The actual stream output is hardcoded in `compositor.py` + `rtmp_output.py`.
- **Migration:**
  - Add `video_out` surfaces to `default.json` for each current sink:
    - `/dev/video42` (v4l2 loopback for OBS fallback)
    - `rtmp://127.0.0.1:1935/studio` (MediaMTX relay)
    - HLS playlist output (`~/.cache/hapax-compositor/hls/playlist.m3u8`)
    - Local archive branch (from this phase's deliverable 3.2 rotation)
  - Wire `OutputRouter.from_layout()` into `compositor.start()` so `OutputBinding` enumeration drives actual sink construction
  - Legacy hardcoded paths remain as FALLBACK during transition (compositor tries layout-declared surfaces first; if layout is invalid or misses a required sink, fall back to hardcoded)
  - Deprecation: hardcoded paths are marked for removal in Phase 10 polish
- **Why this is in Phase 2** (per epic spec item 10): "archival work here adds a new sink (local archive branch), which is the natural pressure to generalize. Layout-declared outputs let Phase 8 add further sinks (NDI tap, winit preview, secondary RTMP) by editing JSON."
- **CairoSourceRegistry integration** (post-2026-04-15T13:40Z architectural judgment — see §4 decision 8): the same migration adds a NEW `CairoSourceRegistry.register(source_cls, zone, priority)` API in a NEW file, distinct from the existing `agents/studio_compositor/source_registry.py` which manages surface backend binding (`register(source_id, backend)` + `get_current_surface(source_id)`). The two registries serve different concerns and coexist. The registration pattern is:
  ```python
  from agents.studio_compositor.cairo_source_registry import CairoSourceRegistry

  CairoSourceRegistry.register(
      source_cls=HudSource,  # HSEA Phase 1 deliverable 1.1
      zone="hud_top_left",
      priority=10,
  )
  ```
- Phase 2 item 10 ships the NEW `CairoSourceRegistry` AND registers the current CairoSources (album overlay, Sierpinski renderer, overlay zones, token pole) via this pattern
- **Naming resolution (2026-04-15T13:40Z):** the existing `source_registry.py` shipped in Reverie source-registry completion epic (PR #822) handles surface backend binding and is untouched by Phase 2 item 10. The new `cairo_source_registry.py` handles zone → CairoSource-subclass binding and is Phase 2's contribution. This avoids the naming collision alpha flagged at 13:35Z exhaustion inflection.
- **Target files:**
  - `agents/studio_compositor/cairo_source_registry.py` (NEW, ~200 LOC; NOT the existing `source_registry.py`)
  - `agents/studio_compositor/compositor.py` (~100 LOC edits to wire `OutputRouter.from_layout()` + `CairoSourceRegistry` enumeration)
  - `agents/studio_compositor/rtmp_output.py` (~50 LOC edits to accept layout-declared sink config)
  - `config/compositor-layouts/default.json` (new video_out declarations + CairoSourceRegistry entries)
  - `config/compositor-zones.yaml` (NEW file — the zone registry HSEA Phase 1 references)
  - `tests/studio_compositor/test_cairo_source_registry.py` (~150 LOC)
  - `tests/studio_compositor/test_output_router_layout.py` (~150 LOC)
- **Deliverable size:** ~800 LOC, 1 day serial work

**Note on `config/compositor-zones.yaml`:** HSEA Phase 1 spec references this file as a Phase 2 deliverable. Phase 2 item 10 is where it gets created. The file declares every zone available to Cairo sources + which source owns each zone by default. HSEA Phase 1 adds 5 new zones to this file (one per new surface).

---

## 4. Phase-specific decisions since epic authored

Drop #62 fold-in (2026-04-14) + operator batch ratification (2026-04-15T05:35Z) introduce the following clarifications:

1. **Item 10 (layout-declared `video_out` migration) is load-bearing for HSEA Phase 1 (UP-4)** per drop #62 §3 row 14. The migration was originally motivated by Phase 2's need for a new sink (archive branch); the cross-epic fold-in reveals it's also the load-bearing mechanism for HSEA Phase 1's Cairo source registration. Phase 2 must ship item 10 with the HSEA Phase 1 use case in mind — the `SourceRegistry.register()` API must accept Cairo source classes from ANY module (not just `agents/studio_compositor/`), and the `config/compositor-zones.yaml` file must be extensible without re-authoring the registry.

2. **No additional new work from operator ratifications.** Drop #62 §10 Q2–Q10 ratifications do not affect Phase 2 scope directly. Q3 (HSEA Phase 4 rescoping) is downstream; Q8 (shared state index authority) applies to alpha at UP-0 fold-in and does not change Phase 2's state file authoring.

3. **RAG ingest pipeline re-enablement is NOT in Phase 2 scope.** Epic spec item 1 says "re-enable archival pipeline" which in LRR epic spec language includes "audio/video recording, classification, RAG ingest". This extraction scopes DOWN to just audio/video recording. Classification and RAG ingest are deferred to Phase 5+ because they have independent concerns (classifier model decisions, Qdrant cardinality budget) that should not block Phase 2's archival enablement.

4. **`condition_id` on Qdrant (LRR Phase 1 item 2)** is satisfied by LRR Phase 1 for NEW points. Phase 2 archival writes do NOT insert into Qdrant — the archive is filesystem-backed; RAG ingest (deferred) would populate Qdrant. Phase 2 does not create Qdrant entries.

5. **Drop #57 T1.5 "Archive-based replay as content"** is enabled by Phase 2 but is a downstream HSEA Phase 7 / UP-12 implementation concern, not Phase 2 scope.

6. **CairoSourceRegistry naming resolution (2026-04-15T13:40Z)** per alpha's 13:35Z exhaustion inflection §"What would unblock alpha" item 4: the existing `agents/studio_compositor/source_registry.py` (shipped in PR #822 Reverie source-registry completion epic) manages SURFACE BACKEND BINDING (`register(source_id, backend)` + `get_current_surface(source_id)`). Delta's original Phase 2 item 10 spec used the same `source_registry.py` path + `SourceRegistry` class name, causing a collision. **Resolution:** Phase 2 item 10 creates a NEW file at `agents/studio_compositor/cairo_source_registry.py` with a NEW class `CairoSourceRegistry` that handles ZONE → CAIRO-SOURCE-SUBCLASS BINDING (`register(source_cls, zone, priority)` + `get_for_zone(zone)`). The two registries serve different concerns and coexist without conflict. **Rejected alternatives:**
   - (1) rename existing to `surface_registry.py` — disruptive, breaks existing imports in Reverie source-registry work, requires test updates
   - (2) extend existing with zone-aware methods — conflates two different concerns (surface backend management vs cairo source zone binding) in one registry, harder to reason about
   - (3) ✓ **ADOPTED: new file at different path (`cairo_source_registry.py`)** — cleanest, zero disruption to existing code, preserves concern separation

---

## 5. Exit criteria

Phase 2 closes when ALL of the following are verified:

1. **Archival pipeline services re-enabled** (audio + video recording + sidecar writing). Verify via `systemctl --user list-units --state=running | grep hapax-archive` or equivalent — at least the recording services are active.

2. **Segments accumulate in `~/hapax-state/stream-archive/`.** Verify: run the compositor for 60 seconds; check that `ls ~/hapax-state/stream-archive/hls/$(date +%Y-%m-%d)/` shows at least 10 `.ts` segments (at 6s segments, ~10 per minute).

3. **Per-segment sidecar JSON files present** with all required fields. Verify: pick a random segment; `jq .` its sidecar; confirm all schema fields are populated (condition_id, reaction_ids, stimmung_snapshot, etc.).

4. **Condition change triggers frame marker.** Verify: run `scripts/research-registry.py open phase-a-prime-hermes-8b` (or similar test condition); review the segment at the transition timestamp; confirm the visible research-marker overlay is present in the frame.

5. **`archive-search.py by-condition cond-phase-a-baseline-qwen-001` returns segments.** The search CLI functions; running it with a known condition_id returns non-empty results.

6. **Vault integration produces a segment note on demand.** Verify: `scripts/archive-search.py note <segment_id>` creates the expected `.md` file at `~/Documents/Personal/30-areas/legomena-live/archive/YYYY-MM/segment-<id>.md` with template-rendered content.

7. **Purge CLI tested with `--dry-run` + audit log entry confirmed.** Verify: `scripts/archive-purge.py --condition cond-test-001 --dry-run` prints the would-be-deleted summary without actually deleting; the audit log entry is NOT written for dry-run, only for real purges.

8. **Retention policy documented** at `docs/superpowers/specs/2026-04-15-lrr-phase-2-archive-retention.md` with all four retention tiers covered.

9. **Audio archive running.** Verify: `ls ~/hapax-state/stream-archive/audio/$(date +%Y-%m-%d)/` shows audio segments with sidecars.

10. **Layout-declared `video_out` surfaces live.** Verify: `jq '.surfaces[] | select(.kind == "video_out")' config/compositor-layouts/default.json` returns ≥4 entries; compositor is using `OutputRouter.from_layout()` (verified by a debug log line in compositor startup).

11. **`config/compositor-zones.yaml` exists** with all current Cairo source zones declared. HSEA Phase 1 will add its 5 new zones to this file post-Phase-2.

12. **`SourceRegistry` functional.** Verify: `SourceRegistry.register(HudStubSource, "test_zone", priority=1)` succeeds; `SourceRegistry.get_for_zone("test_zone")` returns the stub.

13. **`lrr-state.yaml::phase_statuses[2].status == closed`** written at phase close. `research-stream-state.yaml::unified_sequence[UP-3].status == closed` if shared index has landed.

14. **Phase 2 handoff doc written** at `docs/superpowers/handoff/2026-04-15-lrr-phase-2-complete.md`.

15. **HSEA Phase 1 (UP-4) pre-open dry-run.** With Phase 2 closed, a dry-run of the HSEA Phase 1 opening procedure succeeds: a stub HSEA Cairo source registers via `SourceRegistry`, appears in a zone, and renders without errors. This is the acceptance test that Phase 2 is actually ready to support HSEA Phase 1.

---

## 6. Risks + mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Disk space pressure (24/7 stream at ~70 GB/day video alone) | HIGH | Archive fills disk quickly; retention becomes forced | Phase 2 onboarding verifies `~/hapax-state/` disk has ≥200 GB free; if not, operator provisions separate storage (external drive, symlink, etc.) BEFORE the archive is enabled. Retention policy in deliverable 3.8 documents the disk-pressure escalation path (operator-driven, no auto-delete). |
| RAG ingest re-enablement pressures `/data` inodes | MEDIUM | Old problem from LRR Phase 0 | Phase 2 does NOT re-enable RAG ingest (per §4 decision 3); deferred to later phases after Phase 0's lifecycle rule tightening is verified to have held |
| Research notebook vault schema needs operator buy-in | MEDIUM | Vault template mismatch with operator's existing notes | Deliverable 3.7 is OPTIONAL (no auto-creation); operator reviews the template and adjusts before Phase 2 close. Template lives in `50-templates/` so operator can edit freely. |
| `OutputRouter` layout migration breaks compositor output mid-stream | HIGH | Stream goes down | Phase 2 item 10 keeps hardcoded paths as fallback during transition; migration tested on a throwaway branch first; deprecation of hardcoded paths is Phase 10 polish work, NOT Phase 2 close |
| `SourceRegistry` API is not rich enough for HSEA Phase 1 use cases | MEDIUM | HSEA Phase 1 has to retrofit the registry | Phase 2 item 10 designs the API with HSEA Phase 1's 5 surfaces in mind; coordinates with whoever opens HSEA Phase 1 before locking the API |
| `hapax-hls-archive-rotator` conflicts with existing find-delete in compositor startup | LOW | Duplicated deletes or missed rotations | Phase 2 item 2 REMOVES the find-delete in ExecStartPre; the rotator is the only component touching those paths |
| Audio capture via `pw-cat` has latency or dropout issues | MEDIUM | Audio archive has gaps | Fallback: `gst-launch-1.0` PipeWire pipeline with explicit buffer sizes; operator can switch at open time |
| `shared/consent.py` integration with purge CLI doesn't match existing consent contract format | MEDIUM | Purge can't identify revoked consent | Phase 2 item 9 tests against the existing ConsentRegistry API; if mismatch, coordinates with whoever maintains consent.py |
| 6-second segment duration is too coarse for reaction-level search | LOW | Archive-based replay is imprecise | 6s matches current HLS config; if imprecise, can be reduced in a follow-up; not a Phase 2 blocker |
| Backfilled segments from existing `~/.cache/hapax-compositor/hls/` are not captured | MEDIUM | Pre-Phase-2 stream data is lost to the `find -delete` | One-time migration: Phase 2 item 2 runs a `rsync --remove-source-files` at first rotation to salvage any segments currently in the cache dir |

---

## 7. Open questions

All drop #62 §10 open questions are resolved. LRR Phase 2 has no remaining operator-pending decisions from the cross-epic fold-in.

Phase-2-specific design questions:

1. **Audio archive format (deliverable 3.5): Opus vs FLAC.** Default recommendation: Opus for size efficiency. Operator can override to FLAC for lossless research analysis. Decision gate at open time.

2. **Segment duration (deliverable 3.2 + 3.3).** Current HLS config uses 6s segments. Operator can tune if reaction-level search needs finer granularity.

3. **Vault note auto-creation threshold (deliverable 3.7).** Should `archive-search.py note` require a segment_id argument, or can it create notes automatically when the operator opens a vault note for a timerange? Default: explicit segment_id only, no auto-creation.

4. **Retention policy escalation path (deliverable 3.8).** When disk pressure forces a retention decision, what is the operator's preferred workflow? File a DEVIATION, file a task in the governance queue, or direct edit of the policy doc? Default: governance queue task (HSEA Phase 0 0.2 deliverable), with audit trail.

5. **Purge CLI tied to consent revocation (deliverable 3.9) — what happens if `shared/consent.py::ConsentRegistry` doesn't recognize the condition_id's contract?** Default: fail-closed (refuse to purge without explicit `--force`).

---

## 8. Companion plan doc

TDD checkbox task breakdown at `docs/superpowers/plans/2026-04-15-lrr-phase-2-archive-research-instrument-plan.md`.

Execution order inside Phase 2:

1. **Item 1 Re-enable archival pipeline** — first, verifies infrastructure is ready for subsequent work
2. **Item 2 HLS segment persistence policy** — ships second; establishes the archive tree
3. **Item 3 Per-segment metadata sidecar** — depends on items 1, 2
4. **Item 5 Audio archive** — parallel to item 3; same rotation pattern
5. **Item 4 Research-marker frame injection** — depends on item 2 (rotation pattern) + LRR Phase 1 research marker
6. **Item 10 Layout-declared `video_out` surfaces migration** — large item; ships mid-phase so HSEA Phase 1 unblock is visible early
7. **Item 6 Archive search CLI** — depends on items 3 + 5
8. **Item 7 Vault integration** — extends item 6 CLI
9. **Item 9 Purge CLI** — independent of search CLI; depends on item 3 schema
10. **Item 8 Lifecycle policy** — documentation only; can ship at any point; recommend last so it references the actual deliverable shapes

Each item is a separate PR or a single multi-commit PR.

---

## 9. End

This is the standalone per-phase design spec for LRR Phase 2. It extracts the Phase 2 section of the LRR epic spec (`docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md` §5 Phase 2) and incorporates drop #62 §3 row 14 cross-epic coordination (HSEA Phase 1 depends on item 10's SourceRegistry/OutputRouter migration).

This spec is pre-staging. Phase 2 opens only when:
- LRR UP-1 is closed (research registry + condition_id live)
- FDL-1 deployed to a running compositor
- Sufficient disk space verified in `~/hapax-state/`
- A session claims the phase via `~/.cache/hapax/relay/lrr-state.yaml::phase_statuses[2].status: open`

**LRR execution remains alpha's workstream.** Pre-staging authored by delta as coordinator-plus-extractor per the 06:45Z role activation.

— delta, 2026-04-15
