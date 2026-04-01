# tests/test_consent_fail_closed.py
"""Test ConsentRegistry fail-closed behavior."""

import time


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
    """Registry should report stale when loaded_at exceeds threshold."""
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
