# LRR Phase 8 — Hapax Content Programming via Research Objectives — Plan

**Date:** 2026-04-15
**Spec reference:** `docs/superpowers/specs/2026-04-15-lrr-phase-8-content-programming-via-objectives-design.md`
**Branch target:** `feat/lrr-phase-8-content-programming-via-objectives`
**Unified phase mapping:** UP-11 portion (~2,500 LOC, co-ships with LRR Phase 9 + HSEA Phase 3)

---

## 0. Preconditions

- [ ] LRR UP-0/UP-1/UP-3 closed
- [ ] LRR UP-9 (Phase 7 persona) closed — persona authored under post-Hermes substrate per drop #62 §14
- [ ] HSEA UP-2/UP-4/UP-10 closed (preferred — Phase 8 extends director loop that HSEA Phase 2 activities plug into)
- [ ] Session claims: `lrr-state.yaml::phase_statuses[8].status: open`

---

## 1. Item 1 — Objectives data structure

- [ ] Tests: `tests/shared/test_objective_schema.py` — round-trip YAML frontmatter, all required fields, linked_conditions[] format
- [ ] `shared/objective_schema.py` Pydantic model (~150 LOC)
- [ ] Operator authors 3+ seed objectives at `~/Documents/Personal/30-areas/hapax-objectives/obj-00N.md` (these live in the vault, not the repo)
- [ ] Commit: `feat(lrr-phase-8): item 1 objective schema + seed objectives`

## 2. Item 2 — Objectives registry CLI

- [ ] Tests: `tests/scripts/test_hapax_objectives.py` — open/close/list/current/advance subcommands
- [ ] `scripts/hapax-objectives.py` (~250 LOC)
- [ ] Event emission: write to `~/hapax-state/hapax-objectives/events.jsonl` on open/close/advance (HSEA Phase 3 C10 milestone generator watches this)
- [ ] Commit: `feat(lrr-phase-8): item 2 hapax-objectives.py CLI + event emission`

## 3. Item 3 — Director scoring extension

- [ ] Tests: scoring math matches formula, 70/30 tunable, multiple active objectives averaged correctly
- [ ] `agents/hapax_daimonion/director_loop.py` (~60 LOC edit to `_call_activity_llm`)
- [ ] `config/director_scoring.yaml` (new, operator-editable)
- [ ] Commit: `feat(lrr-phase-8): item 3 director scoring with objective advancement term`

## 4. Item 4 — Objective visibility overlay

- [ ] Tests: fixture objective → Cairo render ops → verify fields present
- [ ] `agents/studio_compositor/objective_overlay_source.py` (~180 LOC)
- [ ] Zone registration in `config/compositor-zones.yaml` (lower-right quadrant)
- [ ] Commit: `feat(lrr-phase-8): item 4 objective overlay Cairo source`

## 5. Item 12 — Overlay content system formalization

- [ ] Operator authors 3+ research-mode cards in `~/Documents/Personal/30-areas/stream-overlays/research/`
- [ ] Edit `agents/studio_compositor/overlay_zones.py` to add research zone (~20 LOC)
- [ ] Commit: `feat(lrr-phase-8): item 12 overlay content system research-mode zone`

## 6. Item 7 — YouTube description auto-update

- [ ] Tests: mock YouTube API + verify description template rendering
- [ ] `agents/studio_compositor/youtube_player.py` extension (~100 LOC)
- [ ] OAuth re-consent step: operator completes `youtube.force-ssl` scope grant before item ships
- [ ] Commit: `feat(lrr-phase-8): item 7 YouTube description auto-update on condition/objective change`

## 7. Item 9 — Research-mode tiles (3 sources)

Ship in parallel as independent deliverables.

### 7a. Logos studio view tile

- [ ] Tests + `agents/studio_compositor/logos_studio_view_source.py` (~250 LOC)
- [ ] `SourceRegistry.register(LogosStudioViewSource, "logos_studio_view", priority=5)`
- [ ] Commit: `feat(lrr-phase-8): item 9a Logos studio view tile`

### 7b. Terminal capture with secret obscuration

- [ ] Tests: fixture terminal frame with secrets → verify regex blur catches `pass show`, `LITELLM_*`, `*_API_KEY`, `Authorization: Bearer`
- [ ] `agents/studio_compositor/terminal_capture_source.py` (~300 LOC)
- [ ] Commit: `feat(lrr-phase-8): item 9b terminal capture tile with secret obscuration`

### 7c. PR/CI status overlay

- [ ] Tests: mock git + gh CLI → verify branch/status/PR rendering
- [ ] `agents/studio_compositor/pr_ci_status_source.py` (~200 LOC)
- [ ] Commit: `feat(lrr-phase-8): item 9c PR/CI status overlay`

## 8. Item 5 — Hero-mode camera switching

- [ ] Tests: profile switch with pipeline restart + display-side scaling
- [ ] `agents/studio_compositor/camera_profiles.py` (~300 LOC)
- [ ] `config/compositor-camera-profiles.yaml` (5 presets: hero_operator, hero_turntable, hero_screen, balanced, sierpinski)
- [ ] Command registry extension: `studio.camera_profile.set`
- [ ] Commit: `feat(lrr-phase-8): item 5 hero-mode camera switching + command registry integration`

## 9. Item 6 — Stream Deck integration

- [ ] Tests: mock streamdeck library + key press → command dispatch
- [ ] `agents/streamdeck_adapter/__init__.py` (~300 LOC)
- [ ] `config/streamdeck.yaml` operator-editable key map
- [ ] `systemd/user/hapax-streamdeck-adapter.service`
- [ ] Commit: `feat(lrr-phase-8): item 6 Stream Deck integration via command registry`

## 10. Item 8 — Stream-as-affordance reconciliation

- [ ] Tests: objective requires livestream → affordance recruited autonomously
- [ ] `agents/hapax_daimonion/objective_affordance_recruiter.py` (~150 LOC)
- [ ] Commit: `feat(lrr-phase-8): item 8 stream-as-affordance autonomous recruitment`

## 11. Item 11 — Environmental perception emphasis

- [ ] Tests: fixture high-salience IR signal + active objective with observe → hero mode promotion
- [ ] `agents/hapax_daimonion/environmental_salience_emphasis.py` (~200 LOC)
- [ ] Hysteresis + 30s cooldown
- [ ] Commit: `feat(lrr-phase-8): item 11 environmental salience → surface emphasis`

## 12. Item 10 — Attention bid mechanism (SHIPS LAST)

- [ ] Tests: synthetic high-score activity → bid lands on channel → 15min hysteresis prevents second → critical stimmung suppresses
- [ ] `agents/hapax_daimonion/attention_bid.py` (~250 LOC)
- [ ] PipeWire sink config for `hapax-attention-bids`
- [ ] `config/attention-bids.yaml` (operator-editable channel selection)
- [ ] `~/hapax-state/attention-bids.jsonl` audit log
- [ ] Commit: `feat(lrr-phase-8): item 10 attention bid mechanism (hapax-initiates-interaction)`

---

## 13. Phase 8 close

### Smoke tests

- All 14 exit criteria from spec §5 verified
- Phase 8 handoff doc written
- `lrr-state.yaml::phase_statuses[8].status: closed`
- Request operator update to `unified_sequence[UP-11]` partial completion (Phase 8 is one of 3 LRR/HSEA components of UP-11)
- Inflection to peers: Phase 8 closed + unblocks LRR Phase 9 closed-loop + HSEA Phase 3 C10 milestone generator

### Cross-epic coordination

- **HSEA Phase 3 C10** watches `~/hapax-state/hapax-objectives/events.jsonl` for milestone drops
- **LRR Phase 9** closed-loop feedback modulates the objective scorer via chat signals
- **LRR Phase 2** SourceRegistry/compositor-zones.yaml consumed by items 4, 9a, 9b, 9c
- **HSEA Phase 2 3.6 ComposeDropActivity** NOT used by Phase 8 directly; Phase 8 ships LRR-layer infrastructure that HSEA narrators (Phase 3) compose above

---

## 14. End

Compact plan for LRR Phase 8. Pre-staging. Tenth extraction in delta's pre-staging queue this session. LRR execution remains alpha/beta workstream.

— delta, 2026-04-15
