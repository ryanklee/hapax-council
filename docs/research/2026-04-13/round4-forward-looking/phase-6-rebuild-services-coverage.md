# Phase 6 — Rebuild-services coverage audit

**Queue item:** 025
**Phase:** 6 of 6
**Date:** 2026-04-13 CDT
**Register:** scientific, neutral (per `feedback_scientific_register.md`)

## Headline

The council has **26 long-running daemons** (`Type=notify|simple|exec`) out
of 86 total user systemd units. Only **4 daemons are covered by
`hapax-rebuild-services.service`** (hapax-dmn, hapax-daimonion,
logos-api, officium-api) — plus **2 by `hapax-rebuild-logos.service`**
(hapax-logos, hapax-imagination) — plus **1 by `studio-compositor-reload.path`**
(studio-compositor, via raw inotify without branch check).

**Coverage: 7 of 26 long-running daemons (27%).**

**19 of 26 long-running daemons have no automated rebuild path.**
When the operator edits their source code, the daemons keep
running the old binary until a manual `systemctl --user restart`.
The most important gaps:

- `visual-layer-aggregator` — perception fusion for the whole
  stimmung layer
- `hapax-content-resolver` — content scheduling for the ground
  surface
- `hapax-watch-receiver` — biometric ingestion
- `hapax-reverie` + `hapax-imagination-loop` — visual pipeline
- `studio-fx` + `studio-fx-output` — effect chain
- `studio-person-detector`
- `tabbyapi` — local LLM inference (upstream clone, rebuild is
  upstream-managed, but still a gap)

Plus secondary finding: the compositor's `studio-compositor-reload.path`
fires on raw file change with **no branch-check**, so editing
the compositor on a feature branch triggers a restart. Beta saw
this during queue 023 research (compositor restarted 3 times
mid-session while alpha was editing on `chore/compositor-small-fixes`).

## Coverage table

Long-running daemons (Type = simple/notify/exec), 26 total:

| # | daemon | covered by | gap? |
|---|---|---|---|
| 1 | `hapax-dmn` | rebuild-services (watch dmn, imagination, reverie, visual_chain, effect_graph, shared) | yes |
| 2 | `hapax-daimonion` | rebuild-services (watch agents/hapax_daimonion, shared) | yes |
| 3 | `logos-api` | rebuild-services (watch logos/) | yes |
| 4 | `officium-api` | rebuild-services (different repo) | yes |
| 5 | `hapax-logos` | rebuild-logos (wgpu binary) | yes |
| 6 | `hapax-imagination` | rebuild-logos (wgpu binary) | yes |
| 7 | `studio-compositor` | studio-compositor-reload.path (raw inotify, NO branch check) | partial |
| 8 | `visual-layer-aggregator` | NONE | **GAP** |
| 9 | `hapax-content-resolver` | NONE | **GAP** |
| 10 | `hapax-imagination-loop` | NONE (distinct from hapax-imagination wgpu binary) | **GAP** |
| 11 | `hapax-reverie` | NONE (rebuild-logos is for the Rust binary, reverie is Python) | **GAP** |
| 12 | `hapax-watch-receiver` | NONE | **GAP** |
| 13 | `hapax-stack` | wrapper unit, no rebuild path per se | — |
| 14 | `studio-fx` | NONE | **GAP** |
| 15 | `studio-fx-output` | NONE | **GAP** |
| 16 | `studio-person-detector` | NONE | **GAP** |
| 17 | `tabbyapi` | upstream clone, not rebuilt from council | — |
| 18 | `audio-recorder` | NONE | **GAP** |
| 19 | `chat-monitor` | NONE | **GAP** |
| 20 | `contact-mic-recorder` | NONE | **GAP** |
| 21 | `album-identifier` | NONE | **GAP** |
| 22 | `rag-ingest` | NONE | **GAP** |
| 23 | `youtube-player` | NONE | **GAP** |
| 24 | `logos-dev` | NONE (dev-only, but would be a daemon when running) | — |
| 25 | `keychron-keepalive` | NONE (infrastructure, not hapax-code) | — |
| 26 | `hapax-video-cam@` | NONE (template unit, instance-parameterized) | — |

### Summary

- **7 covered** (~27%)
- **12 true gaps** (marked "**GAP**") — long-running daemons that
  run Python code from hapax-council repo and have no rebuild path
- **7 classified out of scope** (wrappers, upstream clones, dev-only, infrastructure)

The gap list's most operationally-critical entries are
`visual-layer-aggregator`, `hapax-content-resolver`,
`hapax-watch-receiver`, `hapax-reverie`, `hapax-imagination-loop`,
`studio-fx`, and `studio-person-detector`. Each of these is a live
daemon running Python code from the council repo. Editing their
source does not propagate until a manual restart.

## Gap 1: `studio-compositor-reload.path` lacks branch check

`systemd/user/studio-compositor-reload.path`:

```ini
[Unit]
Description=Watch compositor source for changes

[Path]
PathChanged=<hapax-council>/agents/studio_compositor/
PathChanged=<hapax-council>/agents/effect_graph/
PathChanged=<hapax-council>/agents/shaders/nodes/
PathChanged=<hapax-council>/presets/
TriggerLimitIntervalSec=30
TriggerLimitBurst=1
```

The path unit fires on **any file change** in the watched
directories, regardless of which branch the worktree is on. If
alpha edits compositor code on `chore/compositor-small-fixes`,
the path watcher notices the file mtime change and fires
`studio-compositor-reload.service`, which unconditionally runs
`systemctl --user restart studio-compositor`.

### Evidence from queue 023 session

Beta observed 3 unexplained compositor restarts during queue 023
research (17:01:23, 17:16:22, later). The `NRestarts=0` on each
new PID suggested clean stop+starts. These were likely fired by
`studio-compositor-reload.path` as alpha edited the compositor
source on a feature branch. The `TriggerLimitBurst=1 / IntervalSec=30`
throttles the restart rate but does not prevent the restart
entirely.

Compare to `hapax-rebuild-services.service`, which calls
`rebuild-service.sh` that checks `git branch --show-current` and
skips the restart if not on main:

```bash
# from scripts/rebuild-service.sh:99
logger -t "$LOG_TAG" "repo not on main (on $CURRENT_BRANCH) — deploy skipped; SHA_FILE NOT updated"
```

**The path-unit has no equivalent check.** This is a silent
restart path that can disrupt operator-visible state (compositor
restart clears all cairo surface caches, rebuilds all GL shaders,
drops stream reaction count for ~10 seconds).

### Fix proposal

Either:

A. **Migrate studio-compositor to rebuild-services**. Add an
   ExecStart line:

   ```ini
   ExecStart=%h/projects/hapax-council/scripts/rebuild-service.sh \
     --repo %h/projects/hapax-council \
     --service studio-compositor.service \
     --watch "agents/studio_compositor/ agents/effect_graph/ agents/shaders/nodes/ presets/" \
     --sha-key compositor
   ```

   Drop `studio-compositor-reload.path` + `studio-compositor-reload.service`.
   Restart now happens only on 5-min timer tick with a branch
   check. Feature-branch edits no longer trigger restart.

B. **Add a branch-check to `studio-compositor-reload.service`**.
   Change the ExecStart from `systemctl --user restart studio-compositor`
   to a shell script that checks branch first:

   ```bash
   #!/bin/bash
   cd <hapax-council>
   branch=$(git branch --show-current)
   if [ "$branch" != "main" ]; then
     logger -t "studio-compositor-reload" "not on main ($branch) — skipping restart"
     exit 0
   fi
   exec systemctl --user restart studio-compositor
   ```

**Recommendation: Option A**. Consolidates all code-driven
restarts into one rebuild-services path with one branch-check
policy. Path units are more reactive but the loss of branch
awareness is not worth the reactivity.

## Gap 2: 12 daemons with no rebuild coverage

Each of these runs Python code from the council repo that the
operator or alpha may edit. The editing-then-restart pattern is
manual for all of them.

Proposed addition to `hapax-rebuild-services.service`:

```ini
# visual-layer-aggregator: perception fusion for stimmung layer
ExecStart=%h/projects/hapax-council/scripts/rebuild-service.sh \
  --repo %h/projects/hapax-council \
  --service visual-layer-aggregator.service \
  --watch "agents/visual_layer_aggregator/ shared/" \
  --sha-key vla

# hapax-content-resolver: content scheduling
ExecStart=%h/projects/hapax-council/scripts/rebuild-service.sh \
  --repo %h/projects/hapax-council \
  --service hapax-content-resolver.service \
  --watch "agents/content_resolver/ shared/" \
  --sha-key content-resolver

# hapax-watch-receiver: biometric ingestion
ExecStart=%h/projects/hapax-council/scripts/rebuild-service.sh \
  --repo %h/projects/hapax-council \
  --service hapax-watch-receiver.service \
  --watch "agents/watch_receiver/ shared/" \
  --sha-key watch-receiver

# hapax-reverie: visual expression Python daemon (distinct from wgpu binary)
ExecStart=%h/projects/hapax-council/scripts/rebuild-service.sh \
  --repo %h/projects/hapax-council \
  --service hapax-reverie.service \
  --watch "agents/reverie/ shared/" \
  --sha-key reverie

# hapax-imagination-loop: imagination daemon loop
ExecStart=%h/projects/hapax-council/scripts/rebuild-service.sh \
  --repo %h/projects/hapax-council \
  --service hapax-imagination-loop.service \
  --watch "agents/imagination.py agents/imagination_loop.py agents/imagination_resolver.py shared/" \
  --sha-key imagination-loop

# studio-fx: effect chain
ExecStart=%h/projects/hapax-council/scripts/rebuild-service.sh \
  --repo %h/projects/hapax-council \
  --service studio-fx.service \
  --watch "agents/studio_fx/ agents/effect_graph/ shared/" \
  --sha-key studio-fx

# studio-fx-output: effect chain output
ExecStart=%h/projects/hapax-council/scripts/rebuild-service.sh \
  --repo %h/projects/hapax-council \
  --service studio-fx-output.service \
  --watch "agents/studio_fx_output/ shared/" \
  --sha-key studio-fx-output

# studio-person-detector: camera-side person detection
ExecStart=%h/projects/hapax-council/scripts/rebuild-service.sh \
  --repo %h/projects/hapax-council \
  --service studio-person-detector.service \
  --watch "agents/studio_person_detector/ shared/" \
  --sha-key studio-person-detector
```

**8 new rebuild entries** added. Plus **1 move** (studio-compositor
from path unit into rebuild-services). Plus **4 non-critical
skipped** (audio-recorder, chat-monitor, contact-mic-recorder,
album-identifier, youtube-player, rag-ingest — most are
"scripts/*.py" style entries with less operator code, and are
OK to manual-restart).

## Gap 3: `repo not on main` silent deploy-skip

`scripts/rebuild-service.sh:99`:

```bash
logger -t "$LOG_TAG" "repo not on main (on $CURRENT_BRANCH) — deploy skipped; SHA_FILE NOT updated"
```

When the repo is on a feature branch, the rebuild skips but
**only logs via `logger` to syslog at no priority**. There is no
journal pattern that the operator monitors, no ntfy, no
dashboard. The deploy silently doesn't happen. The operator may
be unaware that their code edits are not landing in the running
daemon.

Alpha noted this exact pattern in queue 023's alpha.yaml:

> finding_1: "rebuild-services.timer silently skips voice rebuilds
> when the alpha worktree is on a feature branch. It logs 'repo
> not on main (on X) — deploy skipped; SHA_FILE NOT updated' but
> only at logger-tag level, not as a journal error. After PR #751
> merge, I had to switch alpha back to main and manually trigger
> the rebuild before daimonion actually picked up the fix."

Alpha is aware; no fix landed.

### Fix proposal

Upgrade the skip log from `logger -t` to an ntfy or stderr WARNING
level that surfaces in the journal at visible priority:

```bash
if [ "$CURRENT_BRANCH" != "main" ] && [ "$CURRENT_BRANCH" != "master" ]; then
  echo "[WARN] repo not on main (on $CURRENT_BRANCH) — deploy skipped for $SHA_KEY" >&2
  logger -t "$LOG_TAG" -p user.warning "deploy skipped: repo on $CURRENT_BRANCH, not main"
  # Optional: ntfy for persistent skips
  ...
fi
```

Or simpler: just increment a `hapax_rebuild_skipped_total{service,branch}`
counter on a future Prometheus exporter and let a Grafana alert
do the surfacing.

## Ranked backlog of additions

1. **Add 8 new ExecStart lines to `hapax-rebuild-services.service`**
   — covers the 8 most critical missing daemons. 5-minute diff +
   systemd reload. [High priority]
2. **Migrate `studio-compositor` from path-unit to rebuild-services** —
   consolidates restart policy with branch check. [High priority]
3. **Loudify the `repo not on main` skip** — ntfy on persistent
   skip, upgrade `logger` priority to `user.warning`. [Medium]
4. **Delete `studio-compositor-reload.{path,service}`** after
   item 2 lands. [Low]
5. **Audit the remaining 6 "skip" daemons** (audio-recorder,
   chat-monitor, contact-mic-recorder, album-identifier,
   youtube-player, rag-ingest) — some may warrant rebuild coverage
   too. [Low]
6. **Audit `hapax-stack.service`** — it's a wrapper unit; check
   if its code needs a rebuild path. [Low]
7. **Verify `tabbyapi` is actually upstream-only** — currently
   treated as skip, but check if there are local patches that
   need restart on change. [Low]

## Backlog additions (for retirement handoff)

128. **`fix(systemd): add 8 ExecStart entries to hapax-rebuild-services.service`** [Phase 6 fix 1] — covers visual-layer-aggregator, hapax-content-resolver, hapax-watch-receiver, hapax-reverie, hapax-imagination-loop, studio-fx, studio-fx-output, studio-person-detector. High priority.
129. **`fix(systemd): migrate studio-compositor from studio-compositor-reload.path to rebuild-services with branch check`** [Phase 6 fix 2] — prevents the feature-branch-restart pattern beta saw in queue 023. Delete path unit after migration.
130. **`fix(scripts): rebuild-service.sh — loudify 'repo not on main' skip`** [Phase 6 fix 3] — upgrade `logger -t` to `user.warning` priority + ntfy on persistent skip + Prometheus counter when exporter lands.
131. **`research(systemd): audit the 6 remaining uncovered daemons`** [Phase 6 fix 5] — determine which of audio-recorder, chat-monitor, contact-mic-recorder, album-identifier, youtube-player, rag-ingest warrant rebuild coverage.
132. **`feat(monitoring): hapax_rebuild_skipped_total{service,branch} counter`** [Phase 6 fix 3 extension] — depends on eventual monitoring exporter landing. Counter tracks persistent skips.
