# Session Handoff — 2026-04-12 (alpha stream)

**Previous handoff:** `docs/superpowers/handoff/2026-04-12-session-handoff.md` (alpha-led compositor unification epic closure), plus `docs/superpowers/handoff/2026-04-12-beta-stream-handoff.md` for the parallel stream.
**Scope of this session:** Stream A of the 2026-04-12 work-stream split — studio livestream surface (compositor, cameras, streaming output).
**Session role:** alpha
**Branch at end:** alpha worktree on `main` at `fc4ca5cbc` + this handoff PR. Clean working tree.
**Work-stream split reference:** `~/.cache/hapax/relay/context/2026-04-12-work-stream-split.md`

---

## What was shipped

All five PRs merged to `main`.

| PR | Item | Title | Result |
|----|------|-------|--------|
| [#679](https://github.com/ryanklee/hapax-council/pull/679) | A1 | `fix(compositor)`: cold-start YT slots missing frame files on director startup | `DirectorLoop.start()` now dispatches a playlist reload (daemon thread) for any slot whose `yt-frame-N.jpg` is absent. Prevents the 13 h blank-corners failure mode observed 2026-04-12 after the `youtube-player.service` yt-dlp hang. 5 new tests. |
| [#682](https://github.com/ryanklee/hapax-council/pull/682) | A2 | `fix(profiler)`: absorb transient LLM failures in `run_auto` synthesis path | Wraps both `synthesize_profile` call sites in `run_auto` so an empty `choices[]` response from the upstream LLM doesn't crash a 15-minute run. First synthesis persists source mtimes and returns cleanly; post-curation re-synthesis falls back to the already-saved curated profile. |
| [#685](https://github.com/ryanklee/hapax-council/pull/685) | A10 layer 1 | `fix(telemetry)`: `hapax_span` no longer masks caller exceptions as `RuntimeError` | `hapax_span` was wrapping both Langfuse setup and the yielded block in one try/except with a second `yield None` on failure — which after a caller exception triggered `RuntimeError: generator didn't stop after throw()` and masked the real error. Rewrote as `ExitStack`-based so setup failures and caller-block failures take separate paths. Cross-cutting: every caller of `hapax_span` whose yielded block could raise was silently broken. Regression test included. |
| [#686](https://github.com/ryanklee/hapax-council/pull/686) | A10 layer 2 | `fix(compositor)`: restore playlist loader + load secrets so director actually runs | Two related silent-failure fixes: (1) restored `_load_playlist()` helper in `director_loop.py` (deleted with `spirograph_reactor.py` in PR #644 without migration), and (2) added `EnvironmentFile=/run/user/1000/hapax-secrets.env` to `studio-compositor.service` matching peer services. Without (1) the A1 cold-start dispatch was a silent no-op; without (2) `LITELLM_API_KEY` and `LANGFUSE_PUBLIC_KEY` were never loaded, so LLM calls and Langfuse telemetry both silently failed. 4 new tests. |
| (this PR) | — | `docs`: alpha Stream A handoff + CLAUDE.md director-loop/env notes | Doc-only. Updates "Studio Compositor" section to reflect fixed bootstrap path, new "Studio compositor service env" note, new `shared/telemetry.py` entry in "Key Modules" with a do-not-refactor warning. |

### Items closed without a PR

| # | Item | Why no PR |
|---|------|-----------|
| A11 | Verify stale `feat/sierpinski-visual-layout` branch closed | Checked: branch already deleted on remote (HTTP 404), no local ref, PR #644 merged 2026-04-11. Nothing to clean up. |

### Documentation written or updated

- `docs/superpowers/handoff/2026-04-12-alpha-stream-handoff.md` — this file
- `CLAUDE.md` — "Studio Compositor" section updated (director-loop bootstrap fixed, EnvironmentFile note), new `shared/telemetry.py` entry in "Key Modules"
- `~/.cache/hapax/relay/context/2026-04-12-work-stream-split.md` — work-stream split doc (created at start of session)
- `~/.cache/hapax/relay/alpha.yaml` — status kept up to date through the session
- `~/.cache/hapax/relay/convergence.log` — three sightings logged: A1↔B1 COMPLEMENTARY (resilience fixes), A10 cross-cutting observation, A10 3-layer root-cause analysis

### Convergence sightings logged

- **A1 (#679) ↔ B1 (#678) COMPLEMENTARY:** both are resilience fixes born from the 2026-04-12 incident. A1 prevents the 13 h blank-corners; B1 prevents the 18 h frozen `plan.json`. Same pattern: runtime state loss should auto-recover without operator intervention. Beta independently logged the same sighting.
- **A10 cross-cutting:** every caller of `hapax_span` whose yielded block could raise was masked by the same `RuntimeError`. Probably silently broken across all 5 circulatory systems (perception, stimmung, visual, experiential, prediction). Worth a sweep of other long-running loops post-merge.
- **A10 3-layer root cause:** Director loop was silent for 47+ min because three distinct bugs masked each other. Layer 1: `hapax_span` yielded after throw → RuntimeError cascade (#685). Layer 2: `_load_playlist` deleted in PR #644 without consumer migration → silent no-op (#686). Layer 3: `studio-compositor.service` missing `EnvironmentFile=` → LLM/Langfuse secrets never loaded (#686). Each bug masked the next; the top one had to be fixed before the underlying ones surfaced. Classic silent-failure onion.

---

## Delta from the 2026-04-12 (compositor epic) handoff

The prior handoff listed pending items after the compositor epic closed. For Stream A items:

| Item from the prior handoff | Status now |
|---|---|
| **Director loop cold-start for YT slots** — "Needs `_start_director` to push an initial `/slot/N/play` if `yt-frame-N.jpg` doesn't exist within N seconds. Small PR." | **Shipped** as PR #679 (A1) for the dispatch logic, and PR #686 for the underlying `_load_playlist` helper that A1 silently depended on. The original scoping was accurate for layer 1; the missing playlist loader was discovered during post-deploy verification (see "Live debugging" below). |
| **Failed services sweep** (`llm-cost-alert`, `vault-context-writer`, `hapax-rebuild-services`, `hapax-build-reload`) | **All four now inactive with `Result=success`** — they were timer-triggered oneshots that ran and succeeded post-reboot; the handoff's "failing" state was stale. One genuine new failure surfaced: `profile-update.service` crashed with `IndexError: list index out of range` in `pydantic_ai/models/openai.py:784` on empty `choices[]`. Fixed by A2 (#682) which wraps both `synthesize_profile` call sites so transient LLM failures no longer invalidate a 15-minute run. |
| **Stale `feat/sierpinski-visual-layout` branch** | **Already closed** — PR #644 merged 2026-04-11, branch deleted on remote, no local ref. Nothing to do. |
| **Stream research infrastructure** (Qdrant persistence + Langfuse scoring) | **Verified + fixed** as A10. Qdrant persistence was structurally correct (1076 points in `stream-reactions`) but latest point was 2026-04-10 — stale. Langfuse had 0 traces with `stream-experiment` tag. Root cause was the 3-layer bug above; once all three were shipped, 17 `stream-experiment` traces landed in Langfuse within 4 minutes of restart and the director loop started iterating at the expected ~8 s perception cadence. See "Verification" below. |
| **BRIO USB investigation** | **Not touched** — hardware. The research note at `docs/research/2026-04-12-brio-usb-robustness.md` is unchanged. Two BRIOs still offline. Cheapest try: swap to the bus-8 Renesas port that `brio-synths` uses. |
| **Dynamic camera resolution** | **Not touched** — spec only. |
| **Simulcast / native GStreamer RTMP / TikTok clip pipeline / stream overlay / chat-reactive effects / stream as affordance** | **All not touched.** These were the "large / later" items on the split suggested-order. |

---

## Decisions made this session

1. **A1 design: cold-start dispatch in daemon threads from `DirectorLoop.start()`.** Not a timed watchdog. Only checks frame-file presence (not freshness) to avoid disturbing actively-playing slots. Each cold-start POST runs in a named daemon thread (`cold-start-slot-N`) so the synchronous 90 s `urlopen` timeout cannot block director startup.

2. **A2 design: narrow try/except around the two unwrapped `synthesize_profile` call sites.** Other `*_agent.run()` sites in `profiler.py` already had their own try/except. First synthesis failure persists source mtimes (so the next 12 h timer doesn't re-walk unchanged sources) and returns cleanly. Post-curation re-synthesis failure falls back to the already-saved curated profile — dimension summaries from pre-curation are still correct.

3. **A10 layer 1: `hapax_span` uses `ExitStack`, not a single try/except.** Setup failures close the stack and yield a no-op span. Yield-block failures propagate through `with stack:` cleanly with real `exc_info`. Any future refactor that wraps the yield in an outer try/except will reintroduce the `generator didn't stop after throw()` bug — the `shared/telemetry.py` docstring and `CLAUDE.md` "Key Modules" entry now call this out.

4. **A10 layer 2: restore `_load_playlist` in `director_loop.py`, not in `sierpinski_loader.py`.** `director_loop` is the only consumer and the helper is < 50 lines. No new module. Hardened against `TimeoutExpired` and `FileNotFoundError` so a missing or slow `yt-dlp` degrades cleanly to an empty list.

5. **A10 layer 2: add `EnvironmentFile=` to the main unit file, not a drop-in.** Matches how `hapax-daimonion.service` and `logos-api.service` declare it. The existing drop-ins under `systemd/overrides/studio-compositor.service.d/` are for ordering and priority tweaks only.

6. **A10 scope: shipped both layers as separate PRs.** Layer 1 first (#685) so the telemetry RuntimeError stopped masking everything else, then layer 2 (#686) for the underlying silent no-ops that layer 1 unmasked. Either alone would have been insufficient.

7. **A-stream execution order:** A1 → A2 → A11 → A10. A4 (stream overlay compositor source), A5 (chat-reactive), A3 (BRIO USB), A6 (dynamic camera res), A7 (native RTMP), A8 (simulcast), A9 (TikTok clip) are all still open for the next alpha session in roughly that suggested order.

---

## Live debugging this session

Not code changes — things the next session should know about.

### 1. Director loop post-restart verification (2026-04-12 ~16:09 CDT)

After `systemctl --user daemon-reload && systemctl --user restart studio-compositor.service` on the rebased main:

- `SierpinskiLoader started` at 16:08:54.
- `Loaded 20 reactions from Qdrant` at 16:09:25.
- `Cold-starting slot 0/1/2 (no frame file)` (A1) × 3 at 16:09:26.
- `Director loop started (slot 0 active)` at 16:09:26.
- `Extracted 105 videos from playlist` (A10 layer 2) × 3 at 16:09:28 (three parallel cold-start threads all hit the extractor concurrently — cache was empty, each invoked yt-dlp before the first write landed; harmless but mildly wasteful. See "Pending" below.).
- `Slot 0 reloaded from playlist: Democracy Manifest...` at 16:09:39.
- `Slot 2 reloaded from playlist: ...` at 16:09:54.
- `Slot 1 reloaded from playlist: Rare Bill Evans Interview 1972 ...` at 16:10:09.
- All 3 `yt-frame-N.jpg` files present in `/dev/shm/hapax-compositor/`.
- 0 `"public_key"` warnings, 0 `"generator didn't stop after throw()"` RuntimeErrors, 0 `"Activity LLM call failed"` errors.
- LiteLLM saw 67 POSTs in the first 5 min across all services, director contributing ~20.
- Langfuse: 17 `stream-experiment` traces named `stream.reaction` within 4 minutes (was 0 pre-fix).
- `py-spy dump` on the compositor process confirmed the director-loop thread is live inside `_call_activity_llm` → `urlopen` → `readinto`, and the Langfuse `score_ingestion_consumer` thread is running.

### 2. Observation: `_speak_activity` logs not firing post-restart

**Not blocking, not in A10's scope, but the next session should be aware.** After the full 3-layer A10 fix, the director loop is demonstrably iterating at the ~8 s perception cadence (visible via `Propagated attribute 'metadata.slot' value is not a string. Dropping value.` warnings every ~8 s — that's langfuse reacting to the `metadata={"slot": int}` from `_call_activity_llm`). LLM calls are hitting LiteLLM successfully. Langfuse is receiving spans. Qdrant's `stream-reactions` collection has points from this session.

What we are **not** seeing post-restart: `REACT [react]: ...` messages from `_speak_activity`. No `"Activity: X → Y"` transitions. No `"Activity LLM call failed"` errors. The Langfuse trace bodies are empty (`input`, `output`, `metadata` all blank), which hints the LLM is returning a shape that parses to empty `react` text — so `_loop` hits `if not result: time.sleep(1.0); continue` every tick, silently.

Pre-restart the same code path was producing `REACT [react]: The **SPLATTTRIBUTION** box...` logs successfully. Something changed in the LLM response shape — candidates:

- The `model="claude-opus"` alias in `_call_activity_llm` no longer resolves to a valid LiteLLM route (check `config/litellm.yaml`)
- `_parse_llm_response` is producing empty strings on a JSON shape it used to accept
- The activity prompt is triggering a content filter / refusal on the upstream provider
- `_call_activity_llm` is silently returning `""` on some exception path I didn't trace

**First probe for the next session:** instrument `_call_activity_llm` just before the `return react` line to log `len(raw_content)`, `react[:80]`, and the parsed `activity`. One log line per tick should reveal which branch is firing. Or: set `HAPAX_REACTOR_DEBUG=1` and grep the compositor journal, if that env var exists yet.

### 3. Observation: Langfuse `metadata.slot` value type warning

Every perception tick logs:

```
Propagated attribute 'metadata.slot' value is not a string. Dropping value.
```

Because `director_loop._call_activity_llm` passes `metadata={"activity": self._activity, "slot": self._active_slot}` and `self._active_slot` is an `int`. Langfuse requires string metadata values and drops the offending key. Non-blocking — the span still gets created, just without the slot attribution. Trivial fix: `metadata={"activity": self._activity, "slot": str(self._active_slot)}`. I did not ship this in this session to keep A10 narrow.

### 4. Observation: parallel `yt-dlp` invocation on cold start

`_dispatch_cold_starts` fires three daemon threads simultaneously, all calling `_reload_slot_from_playlist`, which all call `_load_playlist`, which all hit `yt-dlp` before the first cache write. Harmless (all three write the same JSON back) but wasteful (three 60 s budgets instead of one). Small fix for the next session: add a module-level lock around the extraction path in `_load_playlist` or make cold-start dispatch sequential.

---

## Current system state (as of 2026-04-12 ~16:13 CDT)

- **Git:** main at `fc4ca5cbc` plus this handoff PR. Alpha worktree clean. Beta worktree on `feat/b4-transient-pool-wiring` (B4 in progress per beta's `~/.cache/hapax/relay/beta.yaml`).
- **Compositor:** running since 16:08:55 CDT (PID differs from beta-side). Director loop alive at ~8 s perception cadence. Langfuse spans flowing. All 3 Sierpinski corner slots populated with video frames. Slot advance via `yt-finished-N` markers working. `_speak_activity` logs not firing — see §2 above.
- **Langfuse:** 17 `stream-experiment` traces since 16:09, rising. Score ingestion thread active.
- **Qdrant:** `stream-reactions` collection at 1076+ points (new points being added now that the director is actually running).
- **LiteLLM:** healthy, 67 POSTs / 5 min total system-wide.
- **YouTube player:** `/dev/shm/hapax-compositor/playlist.json` populated with 105 video entries from PL-4nvD1KwuH--sViEAFY2cHVmS6_B4CQ5. yt-player service on :8055 responsive.
- **Cameras:** 4 of 6 active per compositor state. `brio-operator` + `brio-room` still offline (hardware, see A3). `brio-synths`, `c920-desk`, `c920-room`, `c920-overhead` up.
- **Failed services:** none currently showing in `systemctl --user --failed`. (Earlier in the session `profile-update.service` was failing; the A2 fix absorbs the failure mode so the next 12 h tick will not crash the run.)
- **Infrastructure:** 13 Docker containers running per `docker ps`.
- **Worktrees:** alpha (`hapax-council/`), beta (`hapax-council--beta/`), plus the spontaneous handoff worktree (`hapax-council--a-handoff/`) which will be cleaned up when this PR merges.

---

## Pending / open items

### Stream A, not started this session (for the next alpha)

- **A3** — BRIO USB investigation (hardware + possible diagnostic watcher daemon)
- **A4** — Stream overlay compositor source (new `CairoSource` for viewer count / chat / preset name)
- **A5** — Chat-reactive effects (YouTube Live chat → preset switching via effect graph)
- **A6** — Dynamic camera resolution/framerate spec + impl
- **A7** — Native GStreamer RTMP (eliminate OBS)
- **A8** — Simulcast (Twitch/Kick via tee or Restream.io) — depends on A7
- **A9** — TikTok clip pipeline

Suggested order: **A4 → A5 → A3 → A6 → A7 → A8 → A9**. A11 is done, A10 is done, A1/A2 are done.

### Follow-ups surfaced by A10 verification (small fixes, any session)

- **FU-1** — Instrument `_call_activity_llm` return path to explain the missing `_speak_activity` logs (§2 above). First probe before any fix.
- **FU-2** — Langfuse `metadata.slot` type warning: cast to `str` in `director_loop._call_activity_llm` (§3 above). One-line fix.
- **FU-3** — Parallel `yt-dlp` invocation on cold start: module-level lock or sequential dispatch (§4 above). Small fix.
- **FU-4** — Sweep all `hapax_span` call sites for masked-exception regressions: with the telemetry bug fixed, any long-running loop that was silently stuck pre-2026-04-12 may now be visibly erroring or still broken in a different way. Worth a pass through reverie / dmn / VLA / experiential loops.

### Cross-cutting

- **CC1** — Stream as affordance: DMN decides when to go live. Beta-side registers `go_live` affordance; alpha-side implements RTMP trigger. Depends on A7.
- **CC2** — `OutputRouter.validate_against_plan`: deferred until first real consumer lands (explicit from the 2026-04-12 audit).

### Deferred from earlier handoffs

- **Stream infra — Qdrant persistence**: verified working (1076 points, now growing again). No action.
- **Stream infra — Langfuse scoring**: verified working as of A10 (17 traces in 4 min). The `hapax_score` calls are queued by the score_ingestion_consumer thread and flushed to Langfuse — no additional wiring required on the alpha side.

---

## How to continue in a fresh alpha session

1. **Pull main and verify clean state:**
   - `git pull --ff-only origin main`
   - `git status` — expect clean
   - `git worktree list` — expect alpha + beta only (the handoff worktree auto-cleans on PR merge; if not, `git worktree remove ../hapax-council--a-handoff` from the primary)

2. **Read this handoff + the beta stream handoff + the work-stream split:**
   - `docs/superpowers/handoff/2026-04-12-alpha-stream-handoff.md` (this file)
   - `docs/superpowers/handoff/2026-04-12-beta-stream-handoff.md` (parallel stream)
   - `~/.cache/hapax/relay/context/2026-04-12-work-stream-split.md` (the split this stream is a half of)
   - `~/.cache/hapax/relay/convergence.log` (structural similarities logged this session)

3. **Read the last two alpha status files:**
   - `~/.cache/hapax/relay/alpha.yaml` (what I left pending)
   - `~/.cache/hapax/relay/beta.yaml` (what beta is currently doing — right now on B4 per `feat/b4-transient-pool-wiring`)

4. **Verify the compositor is still behaving:**
   - `systemctl --user is-active studio-compositor` — expect `active`
   - `ls /dev/shm/hapax-compositor/yt-frame-*.jpg` — expect 3 files, fresh mtimes
   - `ls /dev/shm/hapax-compositor/playlist.json` — expect fresh
   - `journalctl --user -u studio-compositor -n 200 | grep director_loop` — expect `_loop` / `_reload_slot_from_playlist` / ideally `_speak_activity` events
   - `curl -s "http://localhost:3000/api/public/traces?tags=stream-experiment&limit=5" -u "$(pass show langfuse/public-key):$(pass show langfuse/secret-key)"` — expect non-zero traces

5. **If `_speak_activity` is still silent, start with FU-1.** That single probe should explain which branch of `_call_activity_llm` / `_loop` is draining the ticks into nothing.

6. **For the next productive work:** A4 (stream overlay `CairoSource`) is the smallest new-feature win. A3 (BRIO USB) is orthogonal and can interleave if beta is on small PRs. A5 (chat-reactive) depends on understanding the LLM response path (blocked on FU-1). A7 (native RTMP) is the first of the three "large" items and is the prerequisite for A8 / CC1.

7. **Watch for beta merges:** beta is mid-B4 on `feat/b4-transient-pool-wiring`. After beta merges, rebase the alpha worktree onto `main` (the workspace CLAUDE.md rule for dev-server freshness still holds).

---

## Notes for the archaeology

- The compositor unification epic's cleanup left live dead code: `spirograph_reactor.py` deletion in PR #644 removed `_load_playlist` with no consumer migration. This was invisible for ~28 hours because the `hapax_span` RuntimeError was simultaneously masking the director loop's silent failures. Both bugs had to be present for the symptom (silent director loop) to exist; fixing either one alone would have re-exposed the other.
- **Lesson:** cross-file helper deletions need an explicit consumer audit — a grep for every `from <deleted_module> import` and every module-level reference — before the delete commit lands. A single post-merge smoke test on the compositor would have caught this, since the symptom ("no slot reloads after restart") is observable within 30 s.
- **Lesson:** the `hapax_span` bug is the kind of thing that only surfaces when upstream I/O fails — exactly the case the instrumentation was supposed to observe. Context managers that yield in both the success and failure branches of an outer `try/except` are a footgun. Prefer `ExitStack` or explicit `__enter__` / `__exit__` calls when a context manager needs to handle setup failures separately from yield-block failures.
- **Lesson:** "silent failure onion" is a real pattern. When a system-level symptom has been observed for multiple hours with no error logs, suspect that at least one layer of exception handling is swallowing the real error. The first fix often reveals a second bug that was hidden behind it.
