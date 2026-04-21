"""Phase 1C regression pin — sat_sierpinski_content recruitment wiring.

Pre-fix: `sat_sierpinski_content` was never registered as an affordance,
so the recruitment pipeline could never score it above threshold and
the Sierpinski shader never appeared in Reverie's compiled graph.
Post-fix: a `node.sierpinski_content` CapabilityRecord lives in
`shared.affordance_registry.SHADER_NODE_AFFORDANCES`. The reverie mixer
strips the `node.` prefix and calls `SatelliteManager.recruit("sierpinski_content")`,
which causes `_graph_builder.build_graph()` to insert a graph node
named `sat_sierpinski_content` (per the existing `f"sat_{node_type}"`
convention).

This test pins the registration so future shader-affordance edits
can't silently drop sierpinski_content and re-break the YT-into-Reverie
bleed.
"""

from __future__ import annotations

from agents.reverie._affordances import SHADER_NODE_AFFORDANCES
from shared.affordance_registry import (
    SHADER_NODE_AFFORDANCES as REGISTRY_NODES,
)


def test_node_sierpinski_content_registered_in_shared_registry() -> None:
    """Registration lives in the canonical shared registry."""
    names = {r.name for r in REGISTRY_NODES}
    assert "node.sierpinski_content" in names, (
        "node.sierpinski_content MUST be in shared.affordance_registry."
        "SHADER_NODE_AFFORDANCES so the recruitment pipeline can score it. "
        "Without this entry, sat_sierpinski_content never enters the graph "
        "and YouTube frames bleed into Reverie's content_layer."
    )


def test_node_sierpinski_content_propagates_to_reverie_view() -> None:
    """The reverie shim mirrors the registry — keeps the registry
    authoritative without forcing reverie callers to import the
    shared module directly."""
    names = {name for name, _desc in SHADER_NODE_AFFORDANCES}
    assert "node.sierpinski_content" in names


def test_sierpinski_content_record_is_visual_realtime() -> None:
    """Operational properties match the rest of the shader-node cluster
    so the affordance pipeline routes it to the visual modality."""
    record = next(r for r in REGISTRY_NODES if r.name == "node.sierpinski_content")
    assert record.daemon == "reverie"
    assert record.operational.medium == "visual"
    assert record.operational.latency_class == "realtime"


def test_sierpinski_content_description_uses_gibson_verb() -> None:
    """CLAUDE.md § Unified Semantic Recruitment requires Gibson-verb
    affordance descriptions (15-30 words, cognitive function not
    implementation). Smoke-check: starts with a verb phrase + has the
    expected length range."""
    record = next(r for r in REGISTRY_NODES if r.name == "node.sierpinski_content")
    word_count = len(record.description.split())
    assert 8 <= word_count <= 40, (
        f"description should be ~15-30 words for affordance discoverability; "
        f"got {word_count}: {record.description!r}"
    )
    # First word should be a verb (action affordance, not a noun
    # implementation reference). "Tile" is a transitive verb.
    first_word = record.description.split()[0].lower()
    assert first_word == "tile", (
        f"Gibson-verb convention: description should open with an action verb. got: {first_word!r}"
    )


def test_recruitment_node_id_follows_sat_prefix_convention() -> None:
    """Per CLAUDE.md § Reverie Vocabulary Integrity:
    'Sierpinski or other satellite shader nodes in Reverie MUST be
    recruited dynamically via the affordance pipeline (prefix
    sat_<node_type>), NOT wired into the core vocabulary.'

    Verify the graph builder actually generates `sat_sierpinski_content`
    when sierpinski_content is in the recruited set.
    """
    from agents.reverie._graph_builder import build_graph

    minimal_core = {
        "nodes": {
            "noise": {"type": "noise_gen", "params": {}},
            "output": {"type": "output", "params": {}},
        }
    }
    graph = build_graph(minimal_core, recruited={"sierpinski_content": 0.7})
    node_ids = set(graph.nodes.keys())
    assert "sat_sierpinski_content" in node_ids, (
        f"build_graph must generate sat_sierpinski_content when "
        f"sierpinski_content is recruited. Got node_ids: {sorted(node_ids)}"
    )
