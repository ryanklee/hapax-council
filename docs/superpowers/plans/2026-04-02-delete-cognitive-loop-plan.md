# Delete CognitiveLoop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete CognitiveLoop and make CPAL the sole conversation coordinator, with session lifecycle managed by the engagement callback.

**Architecture:** The engagement callback (`on_engagement_detected`) opens sessions and ensures the pipeline exists. CpalRunner polls ConversationBuffer for utterances and delegates to `pipeline.process_utterance()` for STT→LLM→TTS. Session timeout moves from `run_inner.py` main loop into CpalRunner's `_tick()`.

**Tech Stack:** Python 3.12, asyncio, systemd

**Spec:** `docs/superpowers/specs/2026-04-02-delete-cognitive-loop-design.md`

---

## File Structure

**Delete:**
- `agents/hapax_daimonion/cognitive_loop.py`

**Modify:**
| File | Change |
|------|--------|
| `agents/hapax_daimonion/config.py:89` | Remove `use_cpal` field |
| `agents/hapax_daimonion/run_inner.py:48-189,196-217` | Remove all CPAL/legacy branching |
| `agents/hapax_daimonion/session_events.py:55-112` | Replace 3 functions with 1 |
| `agents/hapax_daimonion/pipeline_start.py:176-183` | Remove CognitiveLoop creation |
| `agents/hapax_daimonion/cpal/runner.py:159-234` | Add session lifecycle to `_tick()` |
| `agents/hapax_daimonion/run_loops.py:19-82` | Clean up engagement_processor remnants |
| `agents/hapax_daimonion/daemon.py` | Remove `_cognitive_loop` attribute |

---

### Task 1: Rewrite `session_events.py` — unified engagement handler

The new `on_engagement_detected` combines the CPAL gain boost with the legacy session lifecycle (axiom veto, session open, pipeline creation).

**Files:**
- Modify: `agents/hapax_daimonion/session_events.py:55-112`

- [ ] **Step 1: Replace the three engagement functions with one**

Replace `on_engagement_detected` (lines 55-58), `on_engagement_detected_cpal` (lines 61-81), and `engagement_processor` (lines 83-112) with:

```python
async def on_engagement_detected(daemon: VoiceDaemon) -> None:
    """Engagement fired — open session, boost gain, ensure pipeline.

    Runs axiom compliance check before opening. If session already
    active, just boost gain (repeated engagement during conversation).
    """
    if daemon._cpal_runner is None:
        return

    # Boost gain on every engagement event
    from agents.hapax_daimonion.cpal.types import GainUpdate

    daemon._cpal_runner.evaluator.gain_controller.apply(
        GainUpdate(delta=0.2, source="engagement_detected")
    )

    if daemon.session.is_active:
        return

    # Axiom compliance gate
    state = daemon.perception.tick()
    veto = daemon.governor._veto_chain.evaluate(state)
    if not veto.allowed and "axiom_compliance" in veto.denied_by:
        log.warning("Engagement blocked by axiom compliance: %s", veto.denied_by)
        acknowledge(daemon, "denied")
        return

    # Open session
    acknowledge(daemon, "activation")
    daemon.governor.engagement_active = True
    daemon._frame_gate.set_directive("process")
    daemon.session.open(trigger="engagement")
    daemon.session.set_speaker("operator", confidence=1.0)
    daemon._conversation_buffer.activate()
    log.info("Session opened via engagement detection")
    daemon.event_log.set_session_id(daemon.session.session_id)
    daemon.event_log.emit("session_lifecycle", action="opened", trigger="engagement")

    # Ensure pipeline exists for T3
    if daemon._conversation_pipeline is None:
        try:
            await daemon._start_pipeline()
            if daemon._cpal_runner is not None:
                daemon._cpal_runner.set_pipeline(daemon._conversation_pipeline)
            log.info("Pipeline started for CPAL T3")
        except Exception:
            log.exception("Pipeline start failed")
```

- [ ] **Step 2: Update the audio loop engagement call site**

In `agents/hapax_daimonion/run_loops.py`, the inline engagement check calls `daemon._engagement.on_speech_detected(behaviors)` which triggers the `on_engaged` callback. The callback is a sync lambda that calls `on_engagement_detected(daemon)`. Since the new function is async, wrap it:

In `run_inner.py` where `daemon._engagement` is created, the callback becomes:
```python
daemon._engagement = EngagementClassifier(
    on_engaged=lambda: asyncio.ensure_future(on_engagement_detected(daemon)),
)
```

Note: `ensure_future` schedules the coroutine on the running event loop without blocking the audio loop.

- [ ] **Step 3: Verify existing tests still pass**

Run: `uv run pytest tests/hapax_daimonion/test_concurrency_interleavings.py tests/test_consent_wiring.py tests/test_experiential_proofs.py -q --tb=short`
Expected: Tests may fail on `engagement_processor` references — fix in Task 4.

- [ ] **Step 4: Commit**

```bash
git add agents/hapax_daimonion/session_events.py
git commit -m "feat(voice): unified on_engagement_detected — session + gain + pipeline"
```

---

### Task 2: Rewrite `run_inner.py` — remove all CPAL/legacy branching

**Files:**
- Modify: `agents/hapax_daimonion/run_inner.py:48-217`

- [ ] **Step 1: Replace the CPAL/legacy conditional block (lines 48-94)**

Delete the `if daemon.cfg.use_cpal: ... else: ...` block and replace with the CPAL-only path:

```python
    # Create CPAL runner
    from agents.hapax_daimonion.cpal.runner import CpalRunner

    daemon._cpal_runner = CpalRunner(
        buffer=daemon._conversation_buffer,
        stt=daemon._resident_stt,
        salience_router=daemon._salience_router,
        audio_output=getattr(daemon, "_audio_output", None),
        grounding_ledger=getattr(daemon, "_grounding_ledger", None),
        tts_manager=daemon.tts,
        echo_canceller=getattr(daemon, "_echo_canceller", None),
    )

    # Presynthesis: CPAL signal cache + bridge phrases (both in background)
    import threading

    def _presynth() -> None:
        daemon._cpal_runner.presynthesize_signals()
        log.info("CPAL signal cache presynthesized")
        try:
            daemon._bridge_engine.presynthesize_all(daemon.tts)
            log.info("Bridge phrases presynthesized")
        except Exception:
            log.warning("Bridge presynthesis failed (will retry on first session)")

    threading.Thread(target=_presynth, daemon=True, name="presynth").start()

    # Initialize engagement classifier
    from agents.hapax_daimonion.engagement import EngagementClassifier
    from agents.hapax_daimonion.session_events import on_engagement_detected

    daemon._engagement = EngagementClassifier(
        on_engaged=lambda: asyncio.ensure_future(on_engagement_detected(daemon)),
    )
```

- [ ] **Step 2: Replace the background task scheduling (lines 155-189)**

Delete the `if daemon.cfg.use_cpal: ... else: ...` block and replace with CPAL-only tasks:

```python
    # CPAL runner + impingement consumer
    daemon._background_tasks.append(asyncio.create_task(daemon._cpal_runner.run()))

    async def _impingement_loop() -> None:
        from agents._impingement_consumer import ImpingementConsumer

        consumer = ImpingementConsumer(Path("/dev/shm/hapax-dmn/impingements.jsonl"))
        while daemon._running:
            try:
                for imp in consumer.read_new():
                    await daemon._cpal_runner.process_impingement(imp)
            except Exception:
                log.debug("Impingement consumer error", exc_info=True)
            await asyncio.sleep(0.5)

    from pathlib import Path

    daemon._background_tasks.append(asyncio.create_task(_impingement_loop()))
```

- [ ] **Step 3: Move session timeout into CPAL (lines 196-217)**

Delete the session timeout block from the main loop. This moves to Task 3 (CPAL runner). The main loop becomes:

```python
    try:
        while daemon._running:
            daemon.notifications.prune_expired()

            # Sweep orphan temp wav files
            if not hasattr(daemon, "_wav_sweep_counter"):
                daemon._wav_sweep_counter = 0
            daemon._wav_sweep_counter += 1
            if daemon._wav_sweep_counter >= 60:
                daemon._wav_sweep_counter = 0
                from agents._tmp_wav import cleanup_stale_wavs
                cleanup_stale_wavs()

            await asyncio.sleep(1)
            # ... rest of main loop (workspace analysis etc.) unchanged
```

- [ ] **Step 4: Remove `daemon._cognitive_loop = None` (line 105)**

Delete line 105. The attribute no longer exists.

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_daimonion/run_inner.py
git commit -m "feat(voice): remove CPAL/legacy branching — CPAL-only path"
```

---

### Task 3: Add session lifecycle to CpalRunner._tick()

**Files:**
- Modify: `agents/hapax_daimonion/cpal/runner.py:159-234`

- [ ] **Step 1: Add session timeout + buffer management to `_tick()`**

After the existing silence tracking (line 171), add session timeout:

```python
        # Session timeout: close after prolonged silence
        if (
            hasattr(self, "_daemon")
            and self._daemon is not None
            and self._daemon.session.is_active
            and self._accumulated_silence_s > self._daemon.cfg.silence_timeout_s
            and not self._processing_utterance
            and not self._production.is_producing
        ):
            from agents.hapax_daimonion.session_events import close_session

            asyncio.create_task(close_session(self._daemon, reason="silence_timeout"))
            self._accumulated_silence_s = 0.0
```

- [ ] **Step 2: Mark session activity during production**

After the utterance dispatch (line 179), add activity marking:

```python
        # Keep session alive during production
        if (
            hasattr(self, "_daemon")
            and self._daemon is not None
            and self._daemon.session.is_active
            and (self._processing_utterance or self._production.is_producing)
        ):
            self._daemon.session.mark_activity()
```

- [ ] **Step 3: Add `_daemon` reference to CpalRunner.__init__**

Add `daemon` parameter to `__init__` and store as `self._daemon`:

```python
def __init__(self, *, buffer, stt, salience_router, audio_output,
             grounding_ledger, tts_manager, echo_canceller, daemon=None):
    ...
    self._daemon = daemon
```

Update the creation in `run_inner.py` to pass `daemon`:

```python
daemon._cpal_runner = CpalRunner(
    buffer=daemon._conversation_buffer,
    ...,
    daemon=daemon,
)
```

- [ ] **Step 4: Publish simplified perception behaviors**

Add to end of `_tick()`, replacing what CognitiveLoop.contribute() did:

```python
        # Publish turn phase equivalent for perception consumers
        if hasattr(self, "_daemon") and self._daemon is not None:
            now = time.monotonic()
            phase = "hapax_speaking" if self._production.is_producing else "mutual_silence"
            behaviors = self._daemon.perception.behaviors
            if "turn_phase" in behaviors:
                behaviors["turn_phase"].update(phase, now)
            if "cognitive_readiness" in behaviors:
                behaviors["cognitive_readiness"].update(
                    1.0 if self._pipeline is not None else 0.0, now
                )
```

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_daimonion/cpal/runner.py
git commit -m "feat(voice): CPAL owns session lifecycle + behavior publishing"
```

---

### Task 4: Delete CognitiveLoop and clean references

**Files:**
- Delete: `agents/hapax_daimonion/cognitive_loop.py`
- Modify: `agents/hapax_daimonion/pipeline_start.py:176-183`
- Modify: `agents/hapax_daimonion/daemon.py`
- Modify: `agents/hapax_daimonion/config.py:89`

- [ ] **Step 1: Delete cognitive_loop.py**

```bash
git rm agents/hapax_daimonion/cognitive_loop.py
```

- [ ] **Step 2: Remove CognitiveLoop from pipeline_start.py**

Delete lines 176-183 (the `_start_cognitive_loop` call and its follow-up wiring). Replace with CPAL pipeline wiring:

```python
    # Wire pipeline to CPAL runner for T3 delegation
    if daemon._cpal_runner is not None:
        daemon._cpal_runner.set_pipeline(daemon._conversation_pipeline)
```

Delete the `_start_cognitive_loop()` function definition (lines 225-250).

- [ ] **Step 3: Remove `use_cpal` from config.py**

Delete line 89 (`use_cpal: bool = True`).

- [ ] **Step 4: Remove `_cognitive_loop` from daemon.py**

Remove `self._cognitive_loop = None` and any `_cognitive_loop` references.

- [ ] **Step 5: Grep for stragglers**

```bash
grep -rn "CognitiveLoop\|cognitive_loop\|use_cpal" agents/hapax_daimonion/ --include="*.py" | grep -v __pycache__ | grep -v test
```

Fix any remaining references. Common ones:
- `run_inner.py` line 198: `daemon._cognitive_loop` in session timeout — already deleted in Task 2
- Import statements referencing `cognitive_loop` module

- [ ] **Step 6: Commit**

```bash
git add -A agents/hapax_daimonion/
git commit -m "feat(voice): delete CognitiveLoop — CPAL is sole coordinator"
```

---

### Task 5: Fix tests

**Files:**
- Modify: `tests/hapax_daimonion/test_cognitive_loop.py` → delete or rewrite
- Modify: `tests/hapax_daimonion/test_daemon_lifecycle_matrix.py`
- Modify: `tests/hapax_daimonion/conftest.py`
- Modify: any test referencing `CognitiveLoop`, `use_cpal`, `engagement_processor`

- [ ] **Step 1: Delete cognitive loop test file**

```bash
git rm tests/hapax_daimonion/test_cognitive_loop.py
```

- [ ] **Step 2: Find all test references**

```bash
grep -rn "CognitiveLoop\|cognitive_loop\|use_cpal\|engagement_processor\|on_engagement_detected_cpal" tests/ --include="*.py" | grep -v __pycache__
```

For each hit:
- `CognitiveLoop` imports → delete the test or rewrite against CPAL
- `use_cpal` config references → remove the field from test configs
- `engagement_processor` patches → replace with `on_engagement_detected` async
- `on_engagement_detected_cpal` → replace with `on_engagement_detected`

- [ ] **Step 3: Update conftest stub daemon**

In `tests/hapax_daimonion/conftest.py`, the `make_stub_daemon` helper sets `_cognitive_loop = None`. Remove it and add `_cpal_runner = MagicMock()`.

- [ ] **Step 4: Run full test suite**

```bash
uv run pytest tests/ -q --tb=line --ignore=tests/hapax_daimonion/test_audio_input.py
```

Fix any remaining failures. The main categories will be:
- Missing `CognitiveLoop` import → delete test
- Missing `use_cpal` config field → remove from test DaimonionConfig construction
- `engagement_processor` not found → use `on_engagement_detected` instead

- [ ] **Step 5: Commit**

```bash
git add tests/
git commit -m "fix(tests): remove CognitiveLoop and use_cpal references"
```

---

### Task 6: Restart daemon + smoke test

- [ ] **Step 1: Clear bytecode and restart**

```bash
find agents/ -name "*.pyc" -delete
find agents/ -name "__pycache__" -type d -exec rm -rf {} +
systemctl --user restart hapax-daimonion.service
```

- [ ] **Step 2: Wait for warmup (2.5 min) and verify**

```bash
sleep 150
# Check perception state exists
ls ~/.cache/hapax-daimonion/perception-state.json
# Check presence
python3 -c "import json; d=json.load(open('$HOME/.cache/hapax-daimonion/perception-state.json')); print(f'presence={d[\"presence_state\"]}')"
# Check engagement fires (speak at mic)
journalctl --user -u hapax-daimonion.service --since "30 sec ago" | grep -i "engagement\|session.*open\|utterance\|STT"
```

- [ ] **Step 3: Verify stragglers are gone**

```bash
grep -rn "CognitiveLoop\|use_cpal" agents/ --include="*.py" | grep -v __pycache__
```

Expected: zero hits.

- [ ] **Step 4: Push and PR**

```bash
git push origin <branch>
gh pr create --title "feat(voice): delete CognitiveLoop — CPAL sole coordinator"
```

---

## Verification Checklist

- [ ] `agents/hapax_daimonion/cognitive_loop.py` deleted
- [ ] `grep -r CognitiveLoop agents/` returns zero
- [ ] `grep -r use_cpal agents/` returns zero
- [ ] Operator speaks → engagement → session → STT → LLM → TTS → audio
- [ ] Session closes after silence timeout
- [ ] All tests pass
