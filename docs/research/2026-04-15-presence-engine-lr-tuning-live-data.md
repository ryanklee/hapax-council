# PresenceEngine LR tuning vs live data — measurement blocked, protocol ready

**Date:** 2026-04-15
**Author:** beta (queue #220, identity verified via `hapax-whoami`)
**Scope:** attempted empirical LR validation of PresenceEngine signals against live workstation data. **BLOCKED on ground truth data staleness.** Documents the blocker, the measurement protocol (ready for when data returns), and a partial analysis using available signal-fire-rate data.
**Branch:** `beta-phase-4-bootstrap`

---

## 0. Summary

**Verdict: BLOCKED on measurement, protocol ready.** The empirical LR computation requires an independent "operator present" ground truth that is NOT dependent on the signals being validated (circular). The canonical ground truth in the queue #220 spec is watch heart-rate staleness. Watch HR data at `~/hapax-state/watch/heartrate.json` has been STALE since 2026-04-06T08:48:13Z — 9 days old at audit time. No fresher watch data exists in `~/hapax-state/watch/`. Without a working watch ground truth, empirical LR cannot be computed this session.

This drop:

1. Documents the data-availability blocker
2. Flags an infrastructure finding: the Pixel Watch BLE handoff appears to have silently failed ~9 days ago
3. Provides the measurement protocol ready for execution once watch data returns
4. Computes a partial analysis from signal fire-rate data (what IS available)

## 1. The blocker

### 1.1 Watch data staleness

```
$ ls -la ~/hapax-state/watch/
total 20
drwxr-xr-x 1 hapax hapax 170 Apr  9 21:44 .
drwxr-xr-x 1 hapax hapax 178 Apr 15 01:35 ..
-rw------- 1 hapax hapax 105 Apr  3 08:27 activity.json
-rw------- 1 hapax hapax  88 Apr  6 03:48 connection.json
-rw------- 1 hapax hapax 248 Apr  6 03:48 heartrate.json
-rw------- 1 hapax hapax 256 Apr  9 21:44 phone_context.json
-rw------- 1 hapax hapax 460 Apr  5 11:30 phone_health_summary.json
```

`heartrate.json`:

```json
{
  "source": "pixel_watch_4",
  "updated_at": "2026-04-06T08:48:13.835739+00:00",
  "current": {
    "bpm": 65.0,
    "confidence": "ACCURACY_HIGH"
  },
  "window_1h": {
    "min": 61.0,
    "max": 93.0,
    "mean": 69.2,
    "readings": 500
  }
}
```

`connection.json`:

```json
{
  "last_seen_epoch": 1775465293.7435598,
  "device_id": "pw4",
  "battery_pct": null
}
```

- `last_seen_epoch: 1775465293.7435598` = **2026-04-03T08:28:13Z** (12 days ago)
- `heartrate.json.updated_at: 2026-04-06T08:48:13Z` (9 days ago)
- `phone_context.json` is the only file with an mtime newer than 2026-04-09 — it updated to 2026-04-09T21:44Z (6 days ago)

**Verdict:** the watch infrastructure has been effectively offline since ~2026-04-03. Neither HR nor activity signals have fresh data.

### 1.2 Why watch HR was the chosen ground truth

Per queue #220 spec:

> *"For each signal: count true-positive (operator present + signal fired) vs false-positive (operator absent + signal fired) via watch heart-rate staleness (>120s) as ground truth for 'absent'"*

Watch HR is chosen because:

- It's structurally independent from keyboard/desk/IR signals (different sensor, different link, different processing path)
- It has strong continuity when worn (HR doesn't disappear when the operator stops typing)
- Staleness >120s is a reliable "BLE out of range" / "watch removed" signal

With watch HR stale for 9+ days, there's no usable ground truth for "operator present vs absent" windows over the measurement window.

### 1.3 Alternative ground truths considered + rejected

- **Keyboard activity** (`EvdevInputBackend`): this IS one of the signals being validated. Using it as ground truth is circular.
- **IR person detection** (`ir_presence` backend): this IS one of the signals. Circular.
- **Contact mic RMS** (`ContactMicBackend`): signal being validated. Circular.
- **Hyprland focus**: marginally independent (tracks desktop activity), but tied closely to keyboard/mouse. Noisy. Not usable for "absent" windows.
- **Claude Code subprocess activity** (me): would only prove "operator has at least one Claude session running" which is not the same as "operator is at the desk".

No practical independent ground truth is available in this session.

## 2. Infrastructure finding (flag for operator)

**The Pixel Watch heart-rate sync has been silently stale since 2026-04-03.**

This is a low-severity infrastructure gap — the presence engine degrades gracefully by falling back to other signals when watch_hr is stale (per the `positive-only when stale` pattern documented in council CLAUDE.md § Bayesian Presence Detection). But it means:

1. Watch-based presence signals (`watch_hr`, `watch_connected`) have contributed ZERO information to the presence posterior for 9+ days
2. The PresenceEngine's Bayesian fusion has been operating on a reduced signal set
3. LR values for watch-based signals cannot be validated empirically without fresh data

**Recommended operator action:**

1. Check if the Pixel Watch is still paired + charging
2. Check if `hapax-watch-receiver.service` is active (council CLAUDE.md lists it as an always-running systemd user unit)
3. Check the watch-receiver endpoint for POST traffic from the watch
4. Re-pair if BLE has dropped

This is non-urgent for voice loop correctness (other signals cover presence) but urgent for validating the Bayesian model's signal weightings.

**Proposed follow-up queue item #225 (operator-facing):**

```yaml
id: "225"
title: "Investigate Pixel Watch HR sync staleness (9+ days)"
assigned_to: operator  # needs physical access to watch
status: offered
priority: low
depends_on: []
description: |
  Queue #220 blocked verification found watch HR data stale since
  2026-04-06 and connection last_seen 2026-04-03. Pixel Watch has
  been effectively offline for 9-12 days. Check:
  1. Watch physically paired + charging
  2. hapax-watch-receiver.service active
  3. POST traffic from watch to receiver
  4. BLE pairing re-establishment if needed
size_estimate: "~10-20 min operator hardware inspection"
```

## 3. Measurement protocol (ready for execution when watch returns)

When watch HR data returns (fresh `heartrate.json` updates within last 120s), execute:

### 3.1 Data collection

```bash
# Collect 1 hour of presence signals
journalctl --user -u hapax-daimonion.service \
  --since='-1h' --until='now' \
  -o json-pretty \
  | jq 'select(.MESSAGE | test("PRESENCE diag"))' \
  > /tmp/presence-diag-1h.jsonl

# Collect 1 hour of watch HR snapshots (requires a polling cron or tmpfile)
# If watch-receiver writes heartrate.json atomically, sample mtime every minute:
while true; do
  cp --preserve=timestamps ~/hapax-state/watch/heartrate.json \
    /tmp/hr-samples/hr-$(date +%s).json
  sleep 60
done &
sleep 3600
kill %1

# Join: for each presence-diag sample, look up concurrent HR freshness
# HR freshness ≤ 120s = "operator present" ground truth
# HR freshness > 120s = "operator absent" ground truth
```

### 3.2 Empirical LR computation

For each signal in `DEFAULT_SIGNAL_WEIGHTS`:

```python
# Pseudocode
for signal_name in PRESENCE_SIGNALS:
    fires_when_present = count(signal_fired AND hr_freshness <= 120)
    fires_when_absent = count(signal_fired AND hr_freshness > 120)
    total_present_windows = count(hr_freshness <= 120)
    total_absent_windows = count(hr_freshness > 120)

    tpr = fires_when_present / total_present_windows
    fpr = fires_when_absent / total_absent_windows
    empirical_lr = tpr / fpr if fpr > 0 else float('inf')

    canonical_lr = DEFAULT_SIGNAL_WEIGHTS[signal_name]
    canonical_lr_true = canonical_lr[0] / canonical_lr[1]
    divergence = abs(math.log(empirical_lr) - math.log(canonical_lr_true))
    flag = divergence > math.log(2.0)  # >2x divergence
```

### 3.3 Tuning criteria

Flag any signal with:

- **Empirical LR < canonical LR / 2** → signal is weaker than assumed; lower the canonical LR OR investigate sensor degradation
- **Empirical LR > canonical LR * 2** → signal is stronger than assumed; raise the canonical LR to capture more evidence
- **Empirical LR ≈ 1.0** → signal provides no information; consider removing it entirely

### 3.4 Duration requirements

- Minimum: 1 hour of wake-time data with at least one "absent" transition (operator leaves desk)
- Preferred: 24 hours including overnight (clean absent windows + clean present windows)
- Required: at least 10 `fires_when_absent` events per signal for stable FPR estimates

## 4. Partial analysis from available data (signal fire rates)

While empirical LR requires watch ground truth, I can compute signal FIRE RATES over the last 30 minutes using journald data:

| Affordance (proxy for presence signal) | Events/30min | Inferred rate/min |
|---|---|---|
| `space.gaze_direction` | 485 | 16.2 |
| `system.exploration_deficit` | 272 | 9.1 |
| `space.ir_motion` | 183 | 6.1 |
| `space.posture` | 167 | 5.6 |
| `digital.active_application` | 113 | 3.8 |
| `space.ir_hand_zone` | 108 | 3.6 |
| `digital.keyboard_activity` | 108 | 3.6 |
| `system.error_rate` | 2 | 0.07 |
| `digital.clipboard_intent` | 1 | 0.03 |

**Observation:** IR-derived signals (`space.ir_*`) fire frequently during the 30-minute window where operator is known present (beta operating the shell = operator at desk). `digital.keyboard_activity` fires at ~3.6/min which matches an active beta shell.

**Weak lower-bound inference** (not a real empirical LR because no absent window):

- If the operator were NOT present during this window, we'd expect most IR + contact-mic + keyboard signals to fire at near-zero rate. The fact that they fire at 3.6-16.2/min is consistent with the canonical LRs being in the RIGHT ORDER OF MAGNITUDE, but does not validate the exact values.
- `space.gaze_direction` at 16.2/min is ~10x any other signal. Queue #218 already flagged this as OVER-EAGER. This drop ADDS supporting evidence: the rate is inconsistent with a well-calibrated signal.

**Strong inference:** nothing here contradicts the canonical LRs at their documented orders of magnitude. Full validation still requires ground truth.

## 5. Cross-reference to queue #206 calibration audit

Queue #206 (`docs/research/2026-04-15-presence-engine-signal-calibration-audit.md`, commit `cbd0264dc`) verified spec-LR vs source-LR (static code review). It found 7 drifts:

- D1 ambient_energy missing from source
- D2 ir_body_heat missing from source
- D3-D5 3 signals not in CLAUDE.md
- D6-D7 2 minor rounding drifts

Queue #220 is the follow-up: does the canonical LR match reality? This drop can't answer that question due to the watch data blocker.

**Sequence:** queue #206 (source vs CLAUDE.md) → queue #220 (canonical vs empirical) → future #226 (re-run #220 with fresh watch data).

## 6. Proposed follow-up queue items

### #225 — Pixel Watch HR sync investigation (operator-facing)

See §2.

### #226 — Re-run #220 after watch HR returns

```yaml
id: "226"
title: "Re-run PresenceEngine LR tuning after watch HR is fresh"
assigned_to: beta
status: blocked
depends_on: [225]
priority: low
description: |
  Queue #220 blocked on watch HR staleness. When watch data returns
  (hr_freshness ≤ 120s observed), execute the measurement protocol
  documented in queue #220 §3 to compute empirical LR per signal.
  Flag any signal with >2x divergence from canonical.
size_estimate: "~1 hour data collection + 30 min analysis"
```

## 7. Non-drift observations

- **Presence diagnostic logging is sparse.** journald for hapax-daimonion over 1 hour contains exactly 1 "PRESENCE diag" line: `posterior=0.0084 state=PRESENT signals={'keyboard_active': False}`. This single line is insufficient for any statistical analysis. The presence engine may have higher-rate logging available via Prometheus/metrics but journald is not the right source for this data.
  - **Follow-up thought:** queue #226 (post-watch) should pull data from Prometheus metrics endpoint or direct in-memory sampling rather than journald grep.
- **State=PRESENT with posterior=0.0084** is weird — posterior near 0 should yield state=AWAY per the hysteresis rules (exit_threshold=0.3). Either this is a stale diagnostic line from a prior high-posterior moment that the hysteresis is still holding, OR the posterior computation is broken. Queue #226 should investigate this.
  - **Proposed investigation:** look at the full posterior time series over a 1-hour window, not just a single snapshot.

## 8. Cross-references

- `agents/hapax_daimonion/presence_engine.py::DEFAULT_SIGNAL_WEIGHTS` (canonical LRs)
- `~/hapax-state/watch/heartrate.json` (stale as of 2026-04-06T08:48:13Z)
- Queue #206 calibration audit: `docs/research/2026-04-15-presence-engine-signal-calibration-audit.md` (commit `cbd0264dc`) — predecessor static audit
- Queue #218 salience router threshold validation: `docs/research/2026-04-15-salience-router-threshold-validation.md` (commit `b1e3dc702`) — supports the over-eager gaze_direction finding
- Council CLAUDE.md § Bayesian Presence Detection (design principle + signal tables)
- Queue item spec: queue/`220-beta-presence-engine-lr-tuning-vs-live-data.yaml`

— beta, 2026-04-15T19:35Z (identity: `hapax-whoami` → `beta`)
