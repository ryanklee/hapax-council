"""Graph compiler — validates an EffectGraph and produces an ExecutionPlan."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from agents.effect_graph.registry import ShaderRegistry
from agents.effect_graph.types import EdgeDef, EffectGraph

VALID_LAYER_SOURCES = {"@live", "@smooth", "@hls"}


class GraphValidationError(Exception):
    """Raised when a graph fails structural validation."""


@dataclass
class ExecutionStep:
    """A single node ready for GPU dispatch, in topological order."""

    node_id: str
    node_type: str
    params: dict[str, Any]
    shader_source: str | None
    input_edges: list[EdgeDef]
    output_edges: list[EdgeDef]
    temporal: bool
    temporal_buffers: int
    needs_dedicated_fbo: bool


@dataclass
class ExecutionPlan:
    """Compiled execution plan for a complete effect graph."""

    name: str
    steps: list[ExecutionStep]
    layer_sources: set[str] = field(default_factory=set)
    transition_ms: int = 500


class GraphCompiler:
    """Compiles an EffectGraph into a topologically sorted ExecutionPlan."""

    def __init__(self, registry: ShaderRegistry) -> None:
        self._registry = registry

    def compile(self, graph: EffectGraph) -> ExecutionPlan:
        """Validate and compile a graph into an execution plan."""
        edges = graph.parsed_edges
        self._validate(graph, edges)
        sorted_ids = self._topological_sort(graph, edges)
        steps = self._build_steps(graph, edges, sorted_ids)
        layer_sources = {e.source_node for e in edges if e.is_layer_source}
        return ExecutionPlan(
            name=graph.name,
            steps=steps,
            layer_sources=layer_sources,
            transition_ms=graph.transition_ms,
        )

    def _validate(self, graph: EffectGraph, edges: list[EdgeDef]) -> None:
        # Must have an output node
        has_output = any(node.type == "output" for node in graph.nodes.values())
        if not has_output:
            raise GraphValidationError("Graph must contain an output node")

        # No unknown node types
        for node_id, node in graph.nodes.items():
            if self._registry.get(node.type) is None:
                raise GraphValidationError(f"Unknown node type '{node.type}' for node '{node_id}'")

        # No invalid layer sources
        for edge in edges:
            if edge.is_layer_source and edge.source_node not in VALID_LAYER_SOURCES:
                raise GraphValidationError(
                    f"Invalid layer source '{edge.source_node}' — "
                    f"must be one of {sorted(VALID_LAYER_SOURCES)}"
                )

        # Build adjacency from edges (only among graph nodes, not layer sources)
        node_ids = set(graph.nodes.keys())
        connected: set[str] = set()
        for edge in edges:
            if not edge.is_layer_source:
                connected.add(edge.source_node)
            connected.add(edge.target_node)

        # No disconnected nodes
        for node_id in node_ids:
            if node_id not in connected:
                raise GraphValidationError(f"Node '{node_id}' is disconnected from the graph")

        # No cycles (checked during topological sort)
        self._topological_sort(graph, edges)

    def _topological_sort(self, graph: EffectGraph, edges: list[EdgeDef]) -> list[str]:
        """Kahn's algorithm. Layer sources are external inputs, not graph nodes."""
        node_ids = set(graph.nodes.keys())

        # Build in-degree map and adjacency list (only for graph nodes)
        in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
        successors: dict[str, list[str]] = defaultdict(list)

        for edge in edges:
            target = edge.target_node
            if target not in node_ids:
                continue
            if edge.is_layer_source:
                # Layer sources don't contribute to in-degree — they're external
                continue
            source = edge.source_node
            if source in node_ids:
                in_degree[target] += 1
                successors[source].append(target)

        queue: deque[str] = deque()
        for nid in sorted(node_ids):  # sorted for determinism
            if in_degree[nid] == 0:
                queue.append(nid)

        result: list[str] = []
        while queue:
            node_id = queue.popleft()
            result.append(node_id)
            for succ in successors[node_id]:
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        if len(result) != len(node_ids):
            raise GraphValidationError("Graph contains a cycle")

        return result

    def _build_steps(
        self,
        graph: EffectGraph,
        edges: list[EdgeDef],
        sorted_ids: list[str],
    ) -> list[ExecutionStep]:
        # Count consumers per source node to detect fan-out
        consumer_count: dict[str, int] = defaultdict(int)
        for edge in edges:
            if not edge.is_layer_source:
                consumer_count[edge.source_node] += 1

        steps: list[ExecutionStep] = []
        for node_id in sorted_ids:
            node = graph.nodes[node_id]
            shader_def = self._registry.get(node.type)

            input_edges = [e for e in edges if e.target_node == node_id]
            output_edges = [e for e in edges if e.source_node == node_id]

            temporal = shader_def.temporal if shader_def else False
            temporal_buffers = shader_def.temporal_buffers if shader_def else 0
            shader_source = shader_def.glsl_source if shader_def else None

            steps.append(
                ExecutionStep(
                    node_id=node_id,
                    node_type=node.type,
                    params=dict(node.params),
                    shader_source=shader_source,
                    input_edges=input_edges,
                    output_edges=output_edges,
                    temporal=temporal,
                    temporal_buffers=temporal_buffers,
                    needs_dedicated_fbo=consumer_count.get(node_id, 0) > 1,
                )
            )

        return steps
