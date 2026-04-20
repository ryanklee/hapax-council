"""Concurrency test for monetization_egress_audit._DEFAULT_WRITER lazy init (D-19)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import shared.governance.monetization_egress_audit as egress


class TestDefaultWriterTOCTOU:
    def test_concurrent_first_call_returns_single_instance(self) -> None:
        """N threads racing on first default_writer() call — exactly one MonetizationEgressAudit."""
        # Reset module state so every test observes a fresh race.
        egress._DEFAULT_WRITER = None
        results: list[egress.MonetizationEgressAudit] = []
        with ThreadPoolExecutor(max_workers=16) as ex:
            futures = [ex.submit(egress.default_writer) for _ in range(64)]
            for f in futures:
                results.append(f.result())
        first = results[0]
        for r in results[1:]:
            assert r is first, "TOCTOU: concurrent first-callers got different writer instances"

    def test_idempotent_after_construction(self) -> None:
        """Once constructed, all subsequent calls return the cached instance."""
        egress._DEFAULT_WRITER = None
        first = egress.default_writer()
        for _ in range(100):
            assert egress.default_writer() is first

    def test_lock_released_after_construction(self) -> None:
        """The lock is released after the first init so subsequent calls don't block."""
        egress._DEFAULT_WRITER = None
        egress.default_writer()
        # If the lock were still held, this would deadlock. Smoke check.
        with egress._DEFAULT_WRITER_LOCK:
            pass  # acquires + releases cleanly
