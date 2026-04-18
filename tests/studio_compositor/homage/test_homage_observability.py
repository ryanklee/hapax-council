"""Presence + shape tests for HOMAGE Prometheus metrics."""

from __future__ import annotations

import pytest


@pytest.fixture
def reset_registry():
    """Prometheus metric registries are process-global; tests don't
    need to reset between cases since we only inspect presence."""
    yield


class TestHomageMetricsPresent:
    def test_emit_homage_package_active_exported(self, reset_registry):
        from shared import director_observability as obs

        # Should not raise; metric is present and callable.
        obs.emit_homage_package_active("bitchx")
        obs.emit_homage_package_inactive("bitchx")

    def test_emit_homage_transition_exported(self, reset_registry):
        from shared import director_observability as obs

        obs.emit_homage_transition("bitchx", "ticker-scroll-in")

    def test_emit_homage_choreographer_rejection_exported(self, reset_registry):
        from shared import director_observability as obs

        obs.emit_homage_choreographer_rejection("concurrency-limit")

    def test_emit_homage_violation_exported(self, reset_registry):
        from shared import director_observability as obs

        obs.emit_homage_violation("bitchx", "emoji")

    def test_emit_homage_signature_artefact_exported(self, reset_registry):
        from shared import director_observability as obs

        obs.emit_homage_signature_artefact("bitchx", "quit-quip")


class TestAllExports:
    def test_homage_emitters_are_in_dunder_all(self):
        from shared import director_observability as obs

        expected = {
            "emit_homage_package_active",
            "emit_homage_package_inactive",
            "emit_homage_transition",
            "emit_homage_choreographer_rejection",
            "emit_homage_violation",
            "emit_homage_signature_artefact",
        }
        assert expected.issubset(set(obs.__all__))
