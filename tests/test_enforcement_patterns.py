"""Tests for enforcement pattern false-positive prevention."""

from __future__ import annotations

import re

import pytest

IT_PERSIST_REGEX = re.compile(
    r"\b(?:(?:noted|recorded|stored|saved|logged|tracking|updating)"
    r"\s+(?:that\s+)?"
    r"(?!(?:Logos|Qdrant|Ollama|Docker|Prometheus|Grafana|Langfuse|PostgreSQL|Redis|"
    r"ClickHouse|MinIO|Publius|Brutus|Scout|Profile|Engine|Dashboard|Activity|Health|"
    r"Drift|Agent|Compositor|Pipeline|Monitor|Profiler|Ingest|Digest|Calendar|Gmail|"
    r"Chrome|Obsidian|YouTube|LiteLLM)\b)"
    r"[A-Z][a-z]+\s+"
    r"(?:tends|prefers|likes|dislikes|always|never|usually|struggles|excels|avoids|resists))\b",
    re.IGNORECASE,
)


class TestItPersistPattern:
    @pytest.mark.parametrize(
        "text",
        [
            "noted Logos is responding at 47ms",
            "tracking Ollama is consuming 4GB",
            "recorded Agent is handling requests",
            "logged Qdrant has 8 collections",
            "noted Prometheus was down for 5 minutes",
            "updating Dashboard is refreshed",
        ],
    )
    def test_component_names_do_not_trigger(self, text: str) -> None:
        assert not IT_PERSIST_REGEX.search(text), f"False positive: {text}"

    @pytest.mark.parametrize(
        "text",
        [
            "noted Sarah tends to avoid confrontation",
            "recorded Alex always arrives late",
            "stored that Marcus prefers written feedback",
            "logged Chen usually delegates",
            "tracking that Kim resists change",
        ],
    )
    def test_person_state_does_trigger(self, text: str) -> None:
        assert IT_PERSIST_REGEX.search(text), f"Missed: {text}"

    @pytest.mark.parametrize(
        "text",
        [
            "noted Sarah is unavailable",
            "recorded Alex was in a meeting",
            "logged Chen has three reports",
        ],
    )
    def test_generic_status_does_not_trigger(self, text: str) -> None:
        assert not IT_PERSIST_REGEX.search(text), f"False positive: {text}"


class TestItPersistLivePattern:
    def test_live_pattern_rejects_component(self) -> None:
        from shared.axiom_pattern_checker import check_output, reload_patterns

        reload_patterns()
        violations = check_output("noted Logos is responding well")
        assert not [v for v in violations if v.pattern_id == "out-it-persist-001"]

    def test_live_pattern_catches_person_state(self) -> None:
        from shared.axiom_pattern_checker import check_output, reload_patterns

        reload_patterns()
        violations = check_output("noted Sarah tends to avoid confrontation")
        assert [v for v in violations if v.pattern_id == "out-it-persist-001"]
