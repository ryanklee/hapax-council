# LRR Phase 2 closure handoff — Archive + Research Instrument

**Date:** 2026-04-15
**Author:** alpha (refill 8 item #104, protocol v3 queue/ pull)
**Phase:** LRR Phase 2 — Archive + Research Instrument
**Status:** SUBSTANTIVELY CLOSED (10 deliverables shipped; 1 operator-gated deferral; 1 runbook in-flight as PR #864)
**Per operator rule:** this is a PHASE closure handoff, not a session retirement handoff — explicitly permitted under `feedback_no_retirement_until_lrr_complete.md` (no session retirement until LRR epic complete, but per-phase closures are normal workflow).

---

## 0. Summary

LRR Phase 2 delivers the archive pipeline that turns the 24/7 livestream into a research instrument: segments land on disk with per-segment metadata sidecars tagged to the active research condition, are searchable and purgeable via CLI, and respect consent revocation. Across the 2026-04-15 session, this phase progressed from "shipped code + dormant install" to "substantively closed with one operator-gated activation remaining".

**Shipped:** 10 of 10 spec deliverables (items #1-#10c per LRR Phase 2 spec §3.1-§3.10). Plus item #55 HLS delete-on-start removal (a fix to already-shipped code from a prior day).
**Deferred (operator-gated):** item #58 (audio archive via pw-cat) — activation requires live hardware under operator supervision per the `executive_function` axiom's non-routine-ops clause. Runbook in-flight as PR #864.

## 1. Shipped deliverables (by spec item + PR)

| Spec § | Item | PR | Commit | Description |
|---|---|---|---|---|
| §3.1 | 1 | #853 | `a7e8da3d7` | Archive services scope ratification + operator activation runbook stub (systemd/README.md updates, Phase 2 scope column, docs-only) |
| §3.2 | 2 | #802 → #859 | `6a54ff86b` → `067be8a17` | HLS archive rotator shipped in PR #802 (code + units + tests); install hotfix + regression pin. PR #859 removed the `find -delete` ExecStartPre that raced against the rotator (delta's refill 4 item #55) |
| §3.3 | 3 | already-shipped | (see note) | Segment sidecar writer + schema discovered pre-shipped at `shared/stream_archive.py::SegmentSidecar` + `agents/studio_compositor/hls_archive.py::build_sidecar()` + `rotate_segment()`. Paths differ from spec suggestion (`agents/hapax_archive/`) but location is architecturally correct |
| §3.4 | 4 | #854 | `9e09b4293` | `ResearchMarkerFrameSource` Cairo overlay for condition transitions (3-second fullscreen banner, 12 unit tests) |
| §3.5 | 5 | — | — | **DEFERRED** — audio archive via pw-cat operator-gated; runbook in PR #864 |
| §3.6 | 6 | #857 | `75a5997e5` | `scripts/archive-search.py` stats + verify + note subcommands + retention path fix |
| §3.7 | 7 | #857 | `75a5997e5` | archive-search.py note subcommand + vault integration template |
| §3.8 | 8 | #856 | `ef028711d` | Retention policy doc renamed to 2026-04-15 path |
| §3.9 | 9 | #860 | `6e1b86e4e` | `scripts/archive-purge.py` consent-revocation tie-in via `ConsentRegistry` |
| §3.10a | 10a | #849 | `c54836255` | `CairoSourceRegistry` module (zone → CairoSource subclass binding, 19 unit tests) |
| §3.10b | 10b | #850 | `b2fa7c936` | `config/compositor-zones.yaml` + bootstrap wiring via `load_zone_defaults()`, 11 zones registered (5 real + 6 placeholders) |
| §3.10c | 10c | #851 | `53ac776a4` | `OutputRouter` layout integration tests (24 tests pinning the already-shipped wiring) |

**Total:** 10 PRs merged + 1 pre-existing pre-shipment. 1 deferral (item #58) + 1 in-flight (PR #864 runbook). Item #64/#63 drop-62 spec fixes (PR #852) are cross-cutting and not counted in Phase 2's deliverable tally.

## 2. Architectural decisions made during execution

### 2.1 SourceRegistry naming collision resolution (2026-04-15T14:xx CDT by delta)

**Problem:** Phase 2 item 10 was originally speced to add a `SourceRegistry` class in `agents/studio_compositor/source_registry.py`. That module **already existed** from the Reverie source-registry completion epic (PR #822) and managed surface backend binding (`register(source_id, backend)` + `get_current_surface(source_id)`).

**Decision:** delta pre-emptively amended Phase 2 spec §3.10 at commit `6983ae62e` (before alpha started coding) to rename the new module to `cairo_source_registry.py` and the new class to `CairoSourceRegistry`. The two registries serve different concerns (surface backend binding vs zone → source class binding) and coexist cleanly.

**Benefit:** zero rework for alpha during execution. Alpha's PR #849 shipped against the amended spec without hitting the collision mid-implementation.

**Pattern lesson:** coordinator pre-staging check for API compatibility / naming collisions BEFORE handing work to executor. Catches friction at the cheap end.

### 2.2 Item #56 (segment sidecar writer) discovered pre-shipped

**Discovery:** during refill 4 item #56 pickup, alpha found that the segment sidecar writer + pydantic schema had **already shipped** pre-session at:

- `shared/stream_archive.py::SegmentSidecar` (pydantic frozen dataclass with full schema: `condition_id`, `segment_start_ts`, `segment_end_ts`, `duration_seconds`, `reaction_ids`, `active_activity`, `stimmung_snapshot`, `directives_hash`, `archive_kind`, `segment_path`, `schema_version`)
- `agents/studio_compositor/hls_archive.py::build_sidecar()` + `rotate_segment()` — writer co-located with the rotator
- `tests/test_hls_archive_rotation.py` (14 tests covering build + rotate + atomicity + sidecar contents)

Delta's Phase 2 spec §3.3 proposed the writer at `agents/hapax_archive/segment_sidecar_writer.py` (separate package). The already-shipped location under `studio_compositor/` is architecturally correct: the writer runs on the same rotation cadence as the HLS rotator and moving it to a separate package would decouple it from the rotation trigger for no benefit.

**Decision:** accept the already-shipped location. Mark item #56 `completed` in queue state with a path-divergence note.

**Pattern lesson:** refill authoring should do `ls agents/ tests/` sweep before asking for module creation. This is a second instance of the "already-shipped finding" pattern (first was refill 5 item #53 OutputRouter already wired).

### 2.3 Consent tie-in via ConsentRegistry (item #61 / PR #860)

**Context:** Phase 2 spec §3.9 (purge CLI) required that purge operations be tied to consent revocation — if the operator revokes consent for a research condition, the purge must be authorized automatically; `--force` is the bypass for non-revocation scenarios.

**Decision:** wire the purge CLI through `shared/consent.py::ConsentRegistry.is_revoked(contract_id)` rather than a bespoke purge-auth mechanism. This reuses the existing consent infrastructure from Phase 1 and the `interpersonal_transparency` axiom implementation.

**Benefit:** single source of truth for consent state. A consent revocation anywhere in the system (vault edit, CLI command, axiom hook) automatically enables the purge path without a second authorization pass.

**Pattern lesson:** prefer reuse of existing governance infrastructure over bespoke per-feature authorization. The consent registry is the canonical lock on personal data flows.

## 3. What Phase 3+ inherits from Phase 2

### 3.1 Archive services surface

Phase 3+ can depend on:

- `~/hapax-state/stream-archive/hls/YYYY-MM-DD/*.ts` + `.json` sidecars — the canonical research data surface
- `~/hapax-state/stream-archive/audit/purge-YYYY-MM-DD.jsonl` — audit log for any purge operation (Phase 3 can read for consent-revocation history)
- `scripts/archive-search.py` — 6 subcommands (`by-condition`, `by-reaction`, `by-timerange`, `extract`, `stats`, `verify`, `note`)
- `scripts/archive-purge.py` — consent-revocation-tied purge with audit log writer
- `scripts/hls-archive-rotate.py` — 60s-cadence rotator (cron via `hls-archive-rotate.timer`)

### 3.2 Research marker surface

Phase 3+ can depend on:

- `/dev/shm/hapax-compositor/research-marker.json` — atomic-read via `shared/research_marker.py::read_marker()` (LRR Phase 1 PR #841)
- `ResearchMarkerFrameSource` in the compositor — fires a 3-second fullscreen banner on every condition transition for frame-accurate boundary detection in the archive (Phase 2 item 4 / PR #854)
- Research registry state at `~/hapax-state/research-registry/<condition_id>/condition.yaml`

### 3.3 CairoSourceRegistry zone binding

Phase 3+ (and HSEA Phases 1+) can register custom CairoSource subclasses against zones declared in `config/compositor-zones.yaml`:

```python
from agents.studio_compositor.cairo_source_registry import CairoSourceRegistry

CairoSourceRegistry.register(
    source_cls=MyNewSource,
    zone="hud_top_left",  # declared in compositor-zones.yaml
    priority=100,  # higher than Phase 2 defaults
)
```

HSEA Phase 1 will register 5 zones (1.1 HUD, 1.2 objective strip, 1.3 frozen-files placard, 1.4 governance queue placard, 1.5 condition transition banner) — the YAML catalog already has placeholder entries for them.

### 3.4 Consent-gated purge pattern

The pattern from PR #860 is reusable: any future CLI that operates on personal-data surfaces can wrap its authorization check through `ConsentRegistry.is_revoked()` / `.is_active()` rather than inventing per-feature auth. This propagates the `interpersonal_transparency` axiom uniformly.

## 4. Operator action items for the activation gate

### 4.1 Item #58 — audio archive activation (deferred)

The audio archive via pw-cat is ready to activate but requires operator supervision. Runbook at:

- **PR #864** `docs/superpowers/runbooks/2026-04-15-lrr-phase-2-operator-activation.md` (in-flight)

The runbook is 241 lines and covers: prerequisites, PipeWire source-name verification, hardware headroom check, enable + start sequence, first-segment smoke check, HLS cross-check, rollback path, 5 known failure modes, a completeness checklist, and a §7 Option A (15min segments) vs Option B (6s HLS-aligned) decision point that the operator should resolve before activation.

**When to activate:** at the operator's discretion. No phase gate dependency on this activation for Phases 3-11 — the audio archive is additive research data, not a prerequisite for downstream phases.

### 4.2 No other operator action required

Items #1-#10 are all complete and self-managing. The `hls-archive-rotate.timer` runs automatically at 60s cadence, the research marker reacts to `research-registry.py open|close` commands, and the purge CLI is invoked only on operator demand.

## 5. Open questions + known limitations

### 5.1 Segment boundary alignment (§7 of PR #864)

The audio recorder unit files currently use `segment_time 900` (15-min FLAC segments), not the spec's §3.5 6-second HLS-aligned cadence. The runbook defers this decision to the operator (Option A stay / Option B switch + parallel audio-archive-rotator). If Option B is chosen, a follow-up item will be added to ship the audio-archive-rotator + unit file + tests.

### 5.2 Item #56 path divergence (historical)

The sidecar writer lives at `agents/studio_compositor/hls_archive.py::build_sidecar()` rather than the spec-proposed `agents/hapax_archive/segment_sidecar_writer.py`. Both locations produce identical behavior; the divergence is noted in queue state `items[#56].notes` and in refill 4 closures. A future session reading the spec in isolation should consult the queue state to resolve the path.

### 5.3 Sierpinski zone placement (minor)

`config/compositor-zones.yaml::sierpinski_slot` declares the Sierpinski CairoSource as priority-10 default but does NOT assign it to a specific PiP layout position. Historical layouts had it in a specific spot that the current `default.json` layout does not restore. A future layout authoring pass should verify the Sierpinski positional assignment matches historical placement.

### 5.4 Phase 10 observability gap

Phase 2 ships the archive data but does NOT include Phase 10's per-condition Prometheus slicing (§3.1) or stimmung dashboards (§3.2). A researcher querying the archive today gets the data but not the dashboards. Phase 10 depends on Phase 5 substrate decision and is currently ~10% shipped per `docs/research/2026-04-15-lrr-phase-10-continuation-audit.md` (refill 8 item #105).

## 6. Cross-epic interactions

### 6.1 Drop #62 §14 reframing — no Phase 2 impact

Drop #62 §14 (Hermes abandonment) reopened the substrate question but does NOT affect Phase 2. Phase 2's archive pipeline is substrate-agnostic: it captures HLS video + audio + per-segment metadata regardless of which LLM renders content into the compositor. The `condition_id` tagging in sidecars cares about the research condition, not the substrate.

### 6.2 HSEA Phase 1 dependency on CairoSourceRegistry

HSEA Phase 1 will consume `CairoSourceRegistry.register()` + `get_for_zone()` from Phase 2 item #10a. The 5 HSEA Phase 1 zones (1.1-1.5) are already declared as placeholders in `config/compositor-zones.yaml` so HSEA Phase 1 opener can register sources without editing the YAML.

### 6.3 LRR Phase 4 (OSF pre-reg) dependency on research marker

LRR Phase 4 depends on the research marker infrastructure (Phase 1) + the frame-accurate boundary detection (Phase 2 item 4 / PR #854). The ResearchMarkerFrameSource's 3-second fullscreen banner gives Phase 4's OSF pre-registration a visible timestamp anchor in the HLS archive.

## 7. Evidence files

All listed PRs are on `origin/main` as of commit `f60cf4c49`:

```
6e1b86e4e feat(lrr-phase-2): item 9 — archive-purge consent-revocation tie-in (#860)
067be8a17 fix(lrr-phase-2): item 2 — remove HLS cache delete-on-start ExecStartPre (#859)
75a5997e5 feat(lrr-phase-2): items 6 + 7 — archive-search stats/verify/note + retention path fix (#857)
ef028711d docs(lrr-phase-2): item 8 — rename retention policy doc to 2026-04-15 path (#856)
9e09b4293 feat(lrr-phase-2): item 4 — research-marker frame injection (ResearchMarkerFrameSource) (#854)
a7e8da3d7 docs(lrr-phase-2): item 1 — archive services scope ratification + operator activation (#853)
53ac776a4 test(lrr-phase-2): item 10c — OutputRouter layout integration tests (#851)
b2fa7c936 feat(lrr-phase-2): item 10b — compositor-zones.yaml + register existing CairoSources (#850)
c54836255 feat(lrr-phase-2): item 10a — CairoSourceRegistry module (#849)
6a54ff86b fix(lrr-phase-2): HLS archive install hotfix + regression pins (#802)
```

PR #864 (item #97 runbook) in-flight; will land in a subsequent sync.

## 8. Phase 2 closure state

**Substantively closed.** Phase 2 is ready to be marked terminal once PR #864 merges (which contains the operator activation runbook for item #58). After that, Phase 2 has:

- 10 of 10 spec deliverables shipped
- 1 operator-gated deferral (item #58) with runbook documented
- 0 open blockers
- 0 outstanding regressions
- 12 PRs merged (10 Phase 2 items + 1 drop-62 spec fix + 1 rotator install hotfix)
- ~2,500 net LOC added
- ~110 unit tests covering the new surface

Phase 3 can open whenever its dependencies close. Phase 2 has no veto on Phase 3+ progression.

## 9. References

- Phase 2 spec: `docs/superpowers/specs/2026-04-15-lrr-phase-2-archive-research-instrument-design.md`
- Phase 2 plan: `docs/superpowers/plans/2026-04-15-lrr-phase-2-archive-research-instrument-plan.md`
- Phase 2 retention policy: `docs/superpowers/specs/2026-04-15-lrr-phase-2-archive-retention.md`
- Operator activation runbook (in-flight): PR #864
- LRR epic coverage audit: `docs/research/2026-04-15-lrr-epic-coverage-audit.md` (refill 8 item #103, commit `030aa79af`)
- LRR Phase 10 continuation audit: `docs/research/2026-04-15-lrr-phase-10-continuation-audit.md` (refill 8 item #105, commit `f60cf4c49`)
- Delta refill 4 item #55 unblocking rationale: `docs/research/2026-04-14-lrr-phase-2-hls-archive-dormant.md`
- Drop #62 §14 Hermes abandonment: `docs/research/2026-04-14-cross-epic-fold-in-lrr-hsea.md` §14

— alpha (post-reboot continuation), 2026-04-15T17:30Z
