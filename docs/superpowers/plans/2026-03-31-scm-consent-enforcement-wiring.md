# Consent Enforcement Wiring

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the existing (proven but dormant) consent algebra into every person-adjacent data flow, add fail-closed partition behavior, and add consent state staleness detection.

**Architecture:** ConsentGatedWriter and ConsentGatedReader already exist with correct interfaces. This plan wires them into the 5 sync agents and pipelines that currently write person-adjacent data without consent checks: gcalendar_sync, gmail_sync, ingest, video_processor, and conversation_pipeline. It also adds fail-closed behavior to ConsentRegistry and staleness detection to consent state files.

**Tech Stack:** Python 3.12+, pydantic, ConsentGatedWriter/Reader (shared/governance/), ConsentRegistry (shared/governance/consent.py)

**SCM Gaps Closed:** #5 (dormant algebra), #6 (missing callsites), #7 (fail-closed), #8 (staleness)

**Depends on:** Nothing (Track B — can proceed immediately, parallel to Track A)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `shared/governance/consent.py` | Modify | Add fail-closed flag, staleness detection |
| `agents/gcalendar_sync.py` | Modify | Gate attendee data writes |
| `agents/gmail_sync.py` | Modify | Gate sender/recipient data writes |
| `agents/hapax_daimonion/conversation_pipeline.py` | Modify | Wire ConsentGatedReader |
| `agents/video_processor.py` | Modify | Gate guest presence metadata |
| `tests/test_consent_fail_closed.py` | Create | Verify fail-closed behavior |
| `tests/test_consent_staleness.py` | Create | Verify staleness detection |
| `tests/test_consent_sync_wiring.py` | Create | Verify sync agent gating |

---

### Task 1: Add Fail-Closed Flag to ConsentRegistry

**Files:**
- Modify: `shared/governance/consent.py`
- Test: `tests/test_consent_fail_closed.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_consent_fail_closed.py
"""Test ConsentRegistry fail-closed behavior."""

import time
from pathlib import Path


def test_registry_fail_closed_on_load_failure(tmp_path):
    """Registry should enter fail-closed state when contracts dir is missing."""
    from shared.governance.consent import ConsentRegistry

    registry = ConsentRegistry()
    registry.load(tmp_path / "nonexistent_dir")
    assert registry.fail_closed is True


def test_fail_closed_denies_all_checks():
    """When fail-closed, contract_check returns False for all non-operator persons."""
    from shared.governance.consent import ConsentRegistry

    registry = ConsentRegistry()
    registry._fail_closed = True
    assert registry.contract_check("alice", "audio") is False
    assert registry.contract_check("bob", "calendar") is False


def test_fail_closed_clears_on_successful_load(tmp_path):
    """After successful load, fail-closed state should clear."""
    from shared.governance.consent import ConsentRegistry

    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir()

    registry = ConsentRegistry()
    registry._fail_closed = True
    registry.load(contracts_dir)
    assert registry.fail_closed is False


def test_staleness_triggers_fail_closed():
    """Registry should enter fail-closed when loaded_at exceeds threshold."""
    from shared.governance.consent import ConsentRegistry

    registry = ConsentRegistry()
    registry._loaded_at = time.time() - 600  # 10 minutes ago
    assert registry.is_stale(stale_threshold_s=300.0) is True


def test_fresh_registry_not_stale():
    """Recently loaded registry should not be stale."""
    from shared.governance.consent import ConsentRegistry

    registry = ConsentRegistry()
    registry._loaded_at = time.time()
    assert registry.is_stale(stale_threshold_s=300.0) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_consent_fail_closed.py -v`
Expected: FAIL (no fail_closed property, no is_stale method)

- [ ] **Step 3: Add fail-closed and staleness to ConsentRegistry**

In `shared/governance/consent.py`, add to `ConsentRegistry.__init__`:

```python
self._fail_closed: bool = False
self._loaded_at: float = 0.0
```

Add property:

```python
@property
def fail_closed(self) -> bool:
    """True when consent infrastructure is unavailable — deny all non-operator checks."""
    return self._fail_closed
```

Add method:

```python
def is_stale(self, stale_threshold_s: float = 300.0) -> bool:
    """Check if the registry was loaded too long ago to trust."""
    if self._loaded_at == 0.0:
        return True
    return time.time() - self._loaded_at > stale_threshold_s
```

Modify `load()`:
```python
def load(self, contracts_dir: Path) -> int:
    try:
        # ... existing loading logic ...
        self._fail_closed = False
        self._loaded_at = time.time()
        return count
    except Exception:
        self._fail_closed = True
        log.warning("Failed to load consent contracts — entering fail-closed state")
        return 0
```

Modify `contract_check()`:
```python
def contract_check(self, person_id: str, data_category: str) -> bool:
    if self._fail_closed or self.is_stale():
        return False
    # ... existing logic ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_consent_fail_closed.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add shared/governance/consent.py tests/test_consent_fail_closed.py
git commit -m "feat(consent): add fail-closed state and staleness detection to ConsentRegistry"
```

---

### Task 2: Gate Calendar Sync Attendee Writes

**Files:**
- Modify: `agents/gcalendar_sync.py`
- Test: `tests/test_consent_sync_wiring.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_consent_sync_wiring.py
"""Test consent gating in sync agents."""

import ast


def test_gcalendar_sync_checks_consent():
    """gcalendar_sync must call contract_check before writing attendee data."""
    source = open("agents/gcalendar_sync.py").read()
    assert "contract_check" in source or "ConsentGatedWriter" in source, (
        "gcalendar_sync.py must check consent before writing attendee data"
    )


def test_gmail_sync_checks_consent():
    """gmail_sync must call contract_check before writing sender/recipient data."""
    source = open("agents/gmail_sync.py").read()
    assert "contract_check" in source or "ConsentGatedWriter" in source, (
        "gmail_sync.py must check consent before writing sender/recipient data"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_consent_sync_wiring.py::test_gcalendar_sync_checks_consent -v`
Expected: FAIL

- [ ] **Step 3: Wire consent into gcalendar_sync**

In `agents/gcalendar_sync.py`, modify `_write_upcoming_events()`:

```python
from shared.governance.consent import ConsentRegistry

def _write_upcoming_events(state: CalendarSyncState) -> int:
    GCALENDAR_DIR.mkdir(parents=True, exist_ok=True)

    # Load consent registry for attendee checking
    registry = ConsentRegistry()
    try:
        registry.load(Path("axioms/contracts"))
    except Exception:
        log.warning("Consent registry unavailable — stripping all attendee data")

    written = 0
    for event in state.events.values():
        # Extract attendees
        attendees = event.get("attendees", [])
        attendee_emails = [a.get("email", "") for a in attendees if a.get("email")]

        # Filter to consented attendees only
        consented_attendees = []
        for email in attendee_emails:
            if registry.contract_check(email, "calendar"):
                consented_attendees.append(email)

        # Format event with only consented attendee data
        md = _format_event_markdown(event, consented_attendees=consented_attendees)
        filepath = GCALENDAR_DIR / f"{event['id']}.md"
        filepath.write_text(md, encoding="utf-8")
        written += 1

    return written
```

Also modify `_write_profile_facts()` to skip attendee frequency stats when consent is unavailable:

```python
def _write_profile_facts(state: CalendarSyncState) -> int:
    registry = ConsentRegistry()
    try:
        registry.load(Path("axioms/contracts"))
    except Exception:
        pass

    # Only count consented attendees in frequency stats
    attendee_counts: Counter[str] = Counter()
    for e in state.events.values():
        for a in e.get("attendees", []):
            email = a.get("email", "")
            if email and registry.contract_check(email, "calendar"):
                attendee_counts[email] += 1
    # ... rest of profile fact generation with filtered counts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_consent_sync_wiring.py::test_gcalendar_sync_checks_consent -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/gcalendar_sync.py tests/test_consent_sync_wiring.py
git commit -m "feat(consent): gate calendar attendee data writes with contract_check"
```

---

### Task 3: Gate Gmail Sync Sender/Recipient Writes

**Files:**
- Modify: `agents/gmail_sync.py`

- [ ] **Step 1: Wire consent into gmail_sync**

In `agents/gmail_sync.py`, modify `_write_recent_emails()`:

```python
from shared.governance.consent import ConsentRegistry

def _write_recent_emails(state: GmailSyncState) -> int:
    GMAIL_DIR.mkdir(parents=True, exist_ok=True)

    registry = ConsentRegistry()
    try:
        registry.load(Path("axioms/contracts"))
    except Exception:
        log.warning("Consent registry unavailable — stripping all person data from emails")

    written = 0
    for email in state.messages.values():
        # Extract persons
        persons = set()
        if email.get("from"):
            persons.add(email["from"])
        for field in ("to", "cc", "bcc"):
            persons.update(email.get(field, []))

        # Check consent for each person
        unconsented = {p for p in persons if not registry.contract_check(p, "email")}

        # Format with unconsented persons stripped
        md = _format_email_markdown(email, strip_persons=unconsented)
        filepath = GMAIL_DIR / f"{email['id']}.md"
        filepath.write_text(md, encoding="utf-8")
        written += 1

    return written
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_consent_sync_wiring.py::test_gmail_sync_checks_consent -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add agents/gmail_sync.py
git commit -m "feat(consent): gate email sender/recipient data with contract_check"
```

---

### Task 4: Wire ConsentGatedReader into Conversation Pipeline

**Files:**
- Modify: `agents/hapax_daimonion/conversation_pipeline.py`
- Test: `tests/test_consent_pipeline_reader.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_consent_pipeline_reader.py
"""Test ConsentGatedReader wiring in conversation pipeline."""

import ast


def test_pipeline_calls_filter_tool_result():
    """Conversation pipeline must call consent_reader.filter_tool_result."""
    source = open("agents/hapax_daimonion/conversation_pipeline.py").read()
    assert "filter_tool_result" in source, (
        "conversation_pipeline must call consent_reader.filter_tool_result for tool results"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_consent_pipeline_reader.py -v`
Expected: FAIL (filter_tool_result not in source)

- [ ] **Step 3: Wire reader into pipeline**

In `agents/hapax_daimonion/conversation_pipeline.py`, find `_handle_tool_calls()` or the equivalent method where tool results are processed before being fed to the LLM. Add:

```python
# After getting tool result, before feeding to LLM:
if self._consent_reader is not None:
    try:
        result = self._consent_reader.filter_tool_result(tool_name, result)
    except Exception:
        log.warning("Consent filtering failed for %s", tool_name, exc_info=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_consent_pipeline_reader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_daimonion/conversation_pipeline.py tests/test_consent_pipeline_reader.py
git commit -m "feat(consent): wire ConsentGatedReader into conversation pipeline tool results"
```

---

### Task 5: Add Consent State File Staleness Check

**Files:**
- Modify: `shared/governance/consent.py`
- Test: `tests/test_consent_staleness.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_consent_staleness.py
"""Test consent state file staleness detection."""

import json
import time
from pathlib import Path


def test_consent_state_file_staleness(tmp_path):
    """Verify stale consent state file is detected."""
    from shared.governance.consent import check_consent_state_freshness

    state_file = tmp_path / "consent-state.json"
    state_file.write_text(json.dumps({"phase": "NO_GUEST"}))

    # Artificially age the file (would need os.utime in real test)
    import os
    old_time = time.time() - 600
    os.utime(state_file, (old_time, old_time))

    assert check_consent_state_freshness(state_file, stale_threshold_s=300.0) is False


def test_fresh_consent_state_file(tmp_path):
    """Verify fresh consent state file passes."""
    from shared.governance.consent import check_consent_state_freshness

    state_file = tmp_path / "consent-state.json"
    state_file.write_text(json.dumps({"phase": "NO_GUEST"}))

    assert check_consent_state_freshness(state_file, stale_threshold_s=300.0) is True


def test_missing_consent_state_file(tmp_path):
    """Missing file should be treated as stale (fail-closed)."""
    from shared.governance.consent import check_consent_state_freshness

    assert check_consent_state_freshness(tmp_path / "missing.json", stale_threshold_s=300.0) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_consent_staleness.py -v`
Expected: FAIL (no check_consent_state_freshness function)

- [ ] **Step 3: Implement consent state freshness check**

Add to `shared/governance/consent.py`:

```python
def check_consent_state_freshness(
    path: Path, *, stale_threshold_s: float = 300.0
) -> bool:
    """Check if a consent state file on disk is fresh enough to trust.

    Returns False (fail-closed) if the file is missing, unreadable, or older
    than stale_threshold_s seconds.
    """
    try:
        mtime = path.stat().st_mtime
        return (time.time() - mtime) < stale_threshold_s
    except OSError:
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_consent_staleness.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add shared/governance/consent.py tests/test_consent_staleness.py
git commit -m "feat(consent): add consent state file staleness detection"
```
