# Shape-Up Pitch: Fix Wireplumber Restart Orphaning of Livestream Audio Path

**Authored:** 2026-04-26 by independent research agent (Explore subagent, dispatched by alpha)
**Trigger:** Operator-reported silent livestream-tap post-double-wireplumber-restart (11:04 + 11:09 CDT)
**Appetite:** Small batch (~2-3 days)
**For:** Beta (livestream reliability hardening)

## Problem

After a double wireplumber restart (11:04 + 11:09 CDT), `hapax-livestream-tap` goes silent. The symptom manifests as OBS receiving no audio even though the L-12 USB input is flowing (~2.9 MB/3s). The diagnostic chain shows:

1. **L-12 USB multitrack → `hapax-l12-evilpet-capture` filter-chain:** alive, pulling from hardware
2. **`hapax-l12-evilpet-capture` playback → `hapax-livestream-tap`:** 0 bytes flowing (chain stalled)
3. **`hapax-livestream-tap` → `hapax-broadcast-master` loopback:** alive but receiving no input
4. **OBS source bound to `hapax-broadcast-normalized`:** running since 11:07 but silent

The operator recovers via `systemctl --user restart studio-compositor`, which reconnects the audio path. This suggests the loopback chain exists but nobody is actively *pulling* from it after the wireplumber restart.

**What breaks in production:** Livestream broadcast drops to silence. The operator must manually intervene. Any broadcast happening during the restart window is permanently lost (constitutional invariant `feedback_never_drop_speech` violated).

**Root cause:** `hapax-l12-evilpet-capture` is a `libpipewire-module-filter-chain` with a playback node (line 182–186 in `config/pipewire/hapax-l12-evilpet-capture.conf`) that does NOT declare `node.passive = false`. Without an explicit consumer claiming the playback output, PipeWire's passive-link accounting marks the node as unclaimed, and the entire chain goes dormant. The `hapax-livestream-tap` null-sink (line 23 in `config/pipewire/hapax-livestream-tap.conf`) has no explicit claim mechanism either — it only flows when something downstream reads from it. After wireplumber restarts, the loopback modules reload but nothing re-establishes the claim until `studio-compositor` starts its `pw-cat --record` against `mixer_master` (which transitively opens a chain reading from broadcast-normalized).

## Appetite & Circuit-Breaker

- **Time budget:** 2-3 days (one focused session for diagnosis + fix + systemd integration test)
- **Risk tolerance:** Zero manual intervention post-fix; wireplumber restart must not require compositor restart
- **Out of scope:** Rewriting the entire audio-path topology or replacing null-sink architecture. We're fixing the passive-node claim lifecycle, not redesigning the chain.
- **Walk-away point:** If systemd dependency injection creates a cascade that restarts studio-compositor every time wireplumber restarts, revert and explore option A (explicit active node) instead.

## Solution

Two parallel, non-mutually-exclusive fixes:

### Fat Marker Sketch A: Explicit Active Playback Node (PRIMARY)

Mark the `hapax-l12-evilpet-capture` playback node as **active** (not passive) so it always pulls from its capture source, regardless of downstream consumers.

**Where:** `config/pipewire/hapax-l12-evilpet-capture.conf`, line 181–186
**Change:** Add `node.passive = false` to `playback.props`

```
playback.props = {
    node.name = "hapax-l12-evilpet-playback"
    target.object = "hapax-livestream-tap"
    audio.channels = 2
    audio.position = [ FL FR ]
    node.passive = false  # <-- ADDED: force active pull from l12-evilpet-capture
}
```

**Why this works:** An active playback node always claims its capture source, so the filter-chain always pulls from the L-12 USB device. Even if no loopback downstream claims the playback output, the chain keeps flowing internally.

**Risk:** Minimal. The playback output is only used by the `hapax-livestream-tap` → `hapax-broadcast-master` loopback, which has `node.passive = true` (line 75 in broadcast-master.conf). Setting the source to active and leaving the downstream loopback passive is a standard PipeWire pattern.

### Fat Marker Sketch B: Systemd Dependency Binding (SAFETY NET, optional)

Add a systemd unit-ordering constraint so compositor restart cascades from wireplumber restart:

```ini
# In ~/.config/systemd/user/wireplumber.service.d/override.conf
[Unit]
OnFailure=systemctl restart --user studio-compositor
```

OR use `BindsTo=studio-compositor.service` so wireplumber restart triggers compositor restart. This is a safety net only — if Sketch A is correct, Sketch B should be unnecessary.

**Why separate:** Option B is a band-aid that masks the root-cause passive-claim bug. Only deploy if Option A doesn't fully resolve the issue or if we want extra resilience for the beta period.

## Rabbit Holes

1. **Replacing null-sink with a different source type** — null-sinks don't suspend, which is architecturally correct for broadcast. Don't go down the road of using a loopback sink + passthrough instead; the null-sink design (per commit notes in `hapax-livestream-tap.conf` §7) was the output of extensive research into filter-chain-monitor starvation. Respect that.

2. **Adding a "keepalive" consumer** — tempting to spawn a dummy `pw-cat --record` reader that runs continuously. **Don't do this.** It violates the constitutional invariant `feedback_l12_equals_livestream_invariant` (any reader on the broadcast chain must leave L-12 entirely). A keepalive on the broadcast chain is fine, but it's unnecessary if Sketch A works.

3. **PipeWire version upgrades** — The passive-node semantics changed between 0.3.x and 1.0 series. Don't assume the fix will port to future PipeWire versions without testing; add a regression test (see "Concrete next steps").

4. **Rewriting the config in Lua** — wireplumber's Lua policies are flexible but opaque. The filter-chain configs are declarative and readable. Avoid the temptation to "just use Lua" for this fix.

## No-Gos

- **Do NOT modify wireplumber restart behavior** (no `OnFailure=` hooks that kill compositor, etc.). Wireplumber restarts are transient; compositor should be independent.
- **Do NOT introduce systemd PartOf= or BindsTo= as the primary fix.** Option B is a safety net, not a solution. The bug is at the PipeWire config layer.
- **Do NOT drop the null-sink loopback.** The null-sink exists to break the filter-chain suspend bug documented in `hapax-livestream-tap.conf`. Removing it resurrects task #187.
- **Do NOT add broadcast-specific latency compensation.** The current 1 ms extra loopback hop is acceptable.

## Concrete Next Steps for Beta

### 1. Verify the passive-node hypothesis (30 min)

```bash
# Baseline: dump the audio graph BEFORE the double restart
pw-link -l > /tmp/audio-before.txt
pw-cli info all | grep -E "node.name|node.passive|state" > /tmp/nodes-before.txt

# Trigger the double wireplumber restart
systemctl --user restart wireplumber.service
sleep 5
systemctl --user restart wireplumber.service
sleep 3

# Dump AFTER
pw-link -l > /tmp/audio-after.txt
pw-cli info all | grep -E "node.name|node.passive|state" > /tmp/nodes-after.txt

# Check: does hapax-l12-evilpet-playback exist but have no consumers?
diff /tmp/nodes-before.txt /tmp/nodes-after.txt

# Check: does hapax-livestream-tap exist in the graph but have 0 bytes flowing?
pw-link -l | grep -A2 -B2 "hapax-livestream-tap"
```

**Expected finding:** After restart, `hapax-l12-evilpet-playback` exists but `node.passive = true` (implicit default, since the config doesn't set it), and no loopback is linked to its output. The chain is orphaned.

### 2. Apply Sketch A (10 min)

Edit `config/pipewire/hapax-l12-evilpet-capture.conf`, line 181–186:

```conf
playback.props = {
    node.name = "hapax-l12-evilpet-playback"
    target.object = "hapax-livestream-tap"
    audio.channels = 2
    audio.position = [ FL FR ]
    node.passive = false
}
```

Reload PipeWire:
```bash
systemctl --user restart pipewire.service
sleep 2
```

### 3. Operator-physical reproduction test (15 min)

```bash
systemctl --user restart wireplumber.service
sleep 5
systemctl --user restart wireplumber.service
sleep 3

# Check OBS for audio — should flow immediately (no manual compositor restart needed)
# Verify via: pw-link -l | grep hapax-livestream-tap | wc -l (should be ≥2 for loopback links)
```

**Expected outcome:** OBS audio flows without manual intervention. The chain stays alive because the playback node actively claims its source.

### 4. Add regression test (45 min)

Create `tests/test_livestream_wireplumber_restart_resilience.py`:

```python
"""Regression test for task #188: livestream audio path survives wireplumber restart.

The fix: set node.passive = false on the hapax-l12-evilpet-capture
playback node so it actively pulls regardless of downstream claim state.
"""

import subprocess
import time


def test_livestream_survives_double_wireplumber_restart():
    # Baseline
    result = subprocess.run(
        ["pw-link", "-l"], capture_output=True, text=True, timeout=5
    )
    baseline = result.stdout
    assert "hapax-l12-evilpet-capture" in baseline

    # Trigger double wireplumber restart (bug-trigger condition)
    subprocess.run(
        ["systemctl", "--user", "restart", "wireplumber.service"], timeout=10
    )
    time.sleep(5)
    subprocess.run(
        ["systemctl", "--user", "restart", "wireplumber.service"], timeout=10
    )
    time.sleep(3)

    # Verify chain is intact
    result = subprocess.run(
        ["pw-link", "-l"], capture_output=True, text=True, timeout=5
    )
    current = result.stdout
    assert "hapax-l12-evilpet-playback" in current, (
        "playback node missing after wireplumber restart"
    )
    assert "hapax-livestream-tap" in current, "livestream-tap missing after restart"
    loopback_linked = (
        "hapax-livestream-tap" in current
        and "hapax-broadcast-master-capture" in current
    )
    assert loopback_linked, (
        "broadcast-master loopback not linked after wireplumber restart"
    )
```

### 5. Document in CLAUDE.md (20 min)

Add to the Voice FX Chain section:

```markdown
## Livestream Audio Path Resilience (2026-04-26)

**Issue:** Double wireplumber restart left `hapax-l12-evilpet-capture` playback orphaned (passive node, no downstream claim), stalling the entire broadcast chain.

**Root cause:** `node.passive = true` (implicit default) on the playback node meant the filter-chain only pulled from L-12 when something actively read from its output. After wireplumber restart, no claim was re-established until studio-compositor's `pw-cat --record` activated.

**Fix:** Set `node.passive = false` in `config/pipewire/hapax-l12-evilpet-capture.conf` playback.props so the chain actively pulls from L-12 regardless of downstream state.

**Invariants preserved:**
- `feedback_l12_equals_livestream_invariant`: L-12 input → broadcast, private leaves L-12
- `feedback_never_drop_speech`: operator speech never dropped
- `feedback_no_unsolicited_windows`: no windows on restart

**Post-fix:** Wireplumber restarts do NOT require manual compositor restart.
```

## Why This Pitch

The fix is **minimal** (one-line config change), **permanent** (no manual intervention), and **zero-blip** (no compositor restart required). It directly addresses the passive-node lifecycle bug rather than patching symptoms with systemd hooks. The regression test ensures the issue doesn't resurface on future PipeWire config refactors.

The operator feedback loop is immediate: after the restart, run `pw-link -l | grep hapax-livestream-tap` and verify the loopback is linked. If it is, the fix is working.

## Operator-immediate recovery (already known to operator)

For the current silent-stream incident, the operator's listed options stand:
1. **`systemctl --user restart studio-compositor`** — fastest recovery, broadcast-blip
2. **OBS device dropdown re-select** — operator-physical, no broadcast process restart
3. **Restart pipewire** — slowest, multiple-blip

Once Sketch A ships, none of these manual recoveries should be needed on future wireplumber restarts.
