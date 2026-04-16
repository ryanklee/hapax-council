"""Tests for agents.telemetry.condition_metrics."""

from __future__ import annotations

import pytest
from prometheus_client import CollectorRegistry


@pytest.fixture
def reset_metrics_module():
    """Give each test a fresh CollectorRegistry for isolated registration."""
    import agents.telemetry.condition_metrics as cm

    cm.reset_for_testing()
    registry = CollectorRegistry()
    cm._ensure_metrics(registry=registry)
    yield cm
    cm.reset_for_testing()


@pytest.fixture
def patch_condition_qwen(monkeypatch):
    monkeypatch.setattr(
        "shared.research_condition.get_current_condition",
        lambda *_a, **_kw: "qwen3.5-9b-baseline",
    )


@pytest.fixture
def patch_condition_unavailable(monkeypatch):
    def _boom(*_a, **_kw):
        raise RuntimeError("transient registry read failure")

    monkeypatch.setattr(
        "shared.research_condition.get_current_condition",
        _boom,
    )


class TestRecording:
    def test_start_increments_call_counter(self, reset_metrics_module, patch_condition_qwen):
        cm = reset_metrics_module
        cm.record_llm_call_start(model="qwen3.5-9b", route="local-fast")
        assert cm._LLM_CALLS_TOTAL is not None
        val = cm._LLM_CALLS_TOTAL.labels(
            condition="qwen3.5-9b-baseline", model="qwen3.5-9b", route="local-fast"
        )._value.get()
        assert val == 1

    def test_finish_records_latency_and_outcome(self, reset_metrics_module, patch_condition_qwen):
        cm = reset_metrics_module
        cm.record_llm_call_finish(
            model="qwen3.5-9b",
            route="local-fast",
            outcome="success",
            latency_seconds=0.75,
        )
        assert cm._LLM_CALL_OUTCOMES_TOTAL is not None
        val = cm._LLM_CALL_OUTCOMES_TOTAL.labels(
            condition="qwen3.5-9b-baseline",
            model="qwen3.5-9b",
            route="local-fast",
            outcome="success",
        )._value.get()
        assert val == 1

    def test_condition_read_failure_falls_back_to_unknown(
        self, reset_metrics_module, patch_condition_unavailable
    ):
        cm = reset_metrics_module
        # Must not raise
        cm.record_llm_call_start(model="qwen3.5-9b", route="local-fast")
        assert cm._LLM_CALLS_TOTAL is not None
        val = cm._LLM_CALLS_TOTAL.labels(
            condition="unknown", model="qwen3.5-9b", route="local-fast"
        )._value.get()
        assert val == 1

    def test_multiple_conditions_produce_separate_time_series(
        self, reset_metrics_module, monkeypatch
    ):
        cm = reset_metrics_module
        calls = [iter(["qwen-base", "olmo-sft", "olmo-sft"])]

        def _next_condition(*_a, **_kw):
            return next(calls[0])

        monkeypatch.setattr("shared.research_condition.get_current_condition", _next_condition)
        cm.record_llm_call_start(model="m", route="r")
        cm.record_llm_call_start(model="m", route="r")
        cm.record_llm_call_start(model="m", route="r")

        assert cm._LLM_CALLS_TOTAL is not None
        q = cm._LLM_CALLS_TOTAL.labels(condition="qwen-base", model="m", route="r")._value.get()
        o = cm._LLM_CALLS_TOTAL.labels(condition="olmo-sft", model="m", route="r")._value.get()
        assert q == 1
        assert o == 2
