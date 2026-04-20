"""Tests for demonet_metrics lazy-registered counters (D-23)."""

from __future__ import annotations

from shared.governance.demonet_metrics import METRICS, _DemonetMetrics


class TestLazyRegistration:
    def test_metrics_singleton_exists(self) -> None:
        assert isinstance(METRICS, _DemonetMetrics)

    def test_inc_methods_are_noop_safe(self) -> None:
        """Every inc_* method runs cleanly even when prometheus_client missing."""
        # Fresh instance to avoid touching the module singleton.
        m = _DemonetMetrics()
        m.inc_gate_decision("medium", True, "tts")
        m.inc_gate_decision("high", False, None)
        m.inc_classifier_call("low", False)
        m.inc_classifier_call("medium", True)
        m.inc_classifier_transition("nominal", "degrade")
        m.inc_classifier_transition("degrade", "nominal")
        m.inc_music_mute("path_a", "path_a_detected")
        m.inc_music_mute("path_b", "detector_failure")
        # All above are no-ops when prometheus_client unavailable; no
        # assertion beyond "doesn't raise."

    def test_none_surface_labels_as_none(self) -> None:
        """gate_decisions accepts surface=None and labels safely."""
        m = _DemonetMetrics()
        # Should not crash.
        m.inc_gate_decision("none", True, None)


class TestGateIntegration:
    """End-to-end: GATE.assess bumps the counter."""

    def test_gate_assess_ticks_counter(self) -> None:
        from dataclasses import dataclass, field
        from typing import Any

        from shared.governance.monetization_safety import GATE

        @dataclass
        class _Cand:
            capability_name: str
            payload: dict[str, Any] = field(default_factory=dict)

        cand = _Cand("x", payload={"monetization_risk": "low"})
        # Prior count (if prometheus_client available).
        try:
            from prometheus_client import REGISTRY

            collector = REGISTRY._names_to_collectors.get(  # noqa: SLF001
                "hapax_demonet_gate_decisions_total"
            )
            before = 0.0
            if collector is not None:
                for sample in collector.collect()[0].samples:
                    if sample.labels.get("risk") == "low":
                        before += sample.value
            GATE.assess(cand)
            after = 0.0
            if collector is not None:
                for sample in collector.collect()[0].samples:
                    if sample.labels.get("risk") == "low":
                        after += sample.value
            # Counter bumped if prometheus_client available.
            if collector is not None:
                assert after >= before + 1.0
        except ImportError:
            # No prometheus_client — just exercise the path.
            GATE.assess(cand)
