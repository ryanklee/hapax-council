"""Tests for LLM import graph analyzer."""

from __future__ import annotations

from scripts.llm_import_graph import ImportInfo, build_graph, extract_imports  # noqa: F401


def test_extract_imports_from_source():
    source = """
from shared.config import get_model, PROFILES_DIR
from shared.operator import get_system_prompt_fragment
from agents.introspect import InfrastructureManifest
import json
import asyncio
"""
    result = extract_imports(source, "agents/drift_detector.py")
    internal = [i for i in result if i.is_internal]
    external = [i for i in result if not i.is_internal]

    assert len(internal) == 3
    assert internal[0].module == "shared.config"
    assert internal[0].names == ["get_model", "PROFILES_DIR"]
    assert len(external) == 2


def test_build_graph_includes_agents():
    graph = build_graph(["agents"])
    assert len(graph) > 10, f"Expected many agent modules, got {len(graph)}"
    for name, info in graph.items():
        assert info.path, f"{name} has no path"
        assert info.token_cost >= 0, f"{name} has negative token cost"


def test_transitive_cost_exceeds_self_cost():
    graph = build_graph(["agents", "shared"])
    # Find any agent that still imports from shared (drift_detector is now self-contained)
    found = False
    for name, info in graph.items():
        if name.startswith("agents.") and info.transitive_deps:
            assert info.transitive_token_cost >= info.token_cost, (
                f"{name} transitive cost should be >= self cost"
            )
            if info.transitive_token_cost > info.token_cost:
                found = True
                break
    assert found, "Expected at least one agent with transitive deps exceeding self cost"
