# Plan C — FINDING-V Q4 Chat-Keywords Ward

**Design:** `docs/superpowers/specs/2026-04-23-gemini-reapproach-epic-design.md` §Epic C + `docs/research/2026-04-20-chat-keywords-ward-design.md`
**Task:** #180 (pending)

2 phases. Ships inline this session.

## Phase C1 — Producer: `scripts/chat-keywords-producer.py` + systemd unit

**Branch:** `feat/chat-keywords-c1-producer`

- [ ] `scripts/chat-keywords-producer.py`:
  - Reads `/dev/shm/hapax-chat-signals.json` for rolling-window message buffer (tail last 30 minutes).
  - Tokenize each message via simple lowercase + word-boundary split.
  - Stop-word filter: english-common list + hapax-specific (hapax, oudepode, legomena, etc.).
  - Weight by author diversity: a keyword used by K distinct authors within the window scores K² — suppresses single-author spam, rewards genuine topical recurrence.
  - Top-20 keywords with per-keyword `{keyword, score, author_count, first_seen_ts, last_seen_ts}`.
  - Atomic tmp+rename write to `/dev/shm/hapax-compositor/chat-keywords.json` on 5-second cadence.
  - Schema matches `shared/ward_publisher_schemas.py` pattern.
- [ ] `systemd/units/hapax-chat-keywords.service`:
  - `Type=simple`, `ExecStart=.venv/bin/python scripts/chat-keywords-producer.py`, `Restart=on-failure`, `BindsTo=hapax-daimonion.service` (needs chat-signals SHM from the daimonion).
- [ ] Tests: fake chat-signals SHM input + assert top-20 keyword output; author-diversity weighting pin; stop-word filter pin; atomic write (tmp file never world-visible).
- [ ] Local verify: `uv run pytest tests/scripts/test_chat_keywords_producer.py -q`
- [ ] Post-merge: install service symlink, start unit, verify `/dev/shm/hapax-compositor/chat-keywords.json` appears within 10s.

## Phase C2 — Consumer: `ChatKeywordsWard` + layout wiring

**Branch:** `feat/chat-keywords-c2-ward`

- [ ] `agents/studio_compositor/chat_keywords_ward.py::ChatKeywordsWard` — `CairoSource` protocol:
  - Read `/dev/shm/hapax-compositor/chat-keywords.json` (tolerate missing → blank frame).
  - Render top-12 keywords as tag-cloud (font-size ∝ score, weighted by `author_count` for tonal emphasis).
  - Staleness indicator: if file mtime > 60s old, dim overall alpha to 0.4 (constant across staleness, not time-varying — respects `feedback_no_blinking_homage_wards`).
  - Theme-aware colors (var(--color-homage-*)).
- [ ] `config/compositor-layouts/default.json`:
  - Add `chat_keywords` source (backend=cairo, class_name=ChatKeywordsWard).
  - Add `chat-keywords-midleft` surface at (16, 440, 480, 120) — below grounding-ticker-bl, clear of pip-ll.
  - Add assignment pair.
- [ ] Update `_FALLBACK_LAYOUT` to match.
- [ ] Update `test_default_layout_loading.py` to include the new ward.
- [ ] Register class in `cairo_sources/__init__.py`.
- [ ] Tests: ward renders without error on missing file, blank file, valid file; staleness-dimming invariant (alpha doesn't vary); layout no-occlusion test passes.
- [ ] Local verify: `uv run pytest tests/studio_compositor/test_chat_keywords_ward.py tests/studio_compositor/test_default_layout_no_occlusion.py -q`

## Deferred

- Per-keyword sentiment classification — out of scope; `feedback_no_expert_system_rules`.
- Chat operator-tier-aware weighting (mods / VIPs) — no chat tier data exists yet.

## Rollback

Both phases are additive. Revert Phase C2 first (removes ward + layout entry), then C1 (stops producer). Live system is stable without either.
