"""Graph runtime — manages the live effect graph with three mutation levels."""

from __future__ import annotations

import copy
from typing import Any

from agents.effect_graph.compiler import ExecutionPlan, GraphCompiler
from agents.effect_graph.modulator import UniformModulator
from agents.effect_graph.registry import ShaderRegistry
from agents.effect_graph.types import EffectGraph, GraphPatch, LayerPalette


class GraphRuntime:
    """Manages the live effect graph.

    Three mutation levels:
    1. Param patch — update node params in-place, no recompilation
    2. Topology mutation — add/remove nodes/edges, recompile
    3. Full graph replace — load entirely new graph, recompile
    """

    def __init__(
        self,
        registry: ShaderRegistry,
        compiler: GraphCompiler,
        modulator: UniformModulator,
    ) -> None:
        self._registry = registry
        self._compiler = compiler
        self._modulator = modulator
        self._current_graph: EffectGraph | None = None
        self._current_plan: ExecutionPlan | None = None
        self._layer_palettes: dict[str, LayerPalette] = {
            "live": LayerPalette(),
            "smooth": LayerPalette(),
            "hls": LayerPalette(),
        }
        # Callbacks for GStreamer integration (set by compositor)
        self._on_plan_changed: Any = None  # callback(old_plan, new_plan)
        self._on_params_changed: Any = None  # callback(node_id, params)

    @property
    def current_graph(self) -> EffectGraph | None:
        return self._current_graph

    @property
    def current_plan(self) -> ExecutionPlan | None:
        return self._current_plan

    @property
    def modulator(self) -> UniformModulator:
        return self._modulator

    def load_graph(self, graph: EffectGraph) -> None:
        """Full graph replace. Compile, update state, replace modulations, apply layer palettes."""
        old_plan = self._current_plan
        new_plan = self._compiler.compile(graph)
        self._current_graph = graph
        self._current_plan = new_plan
        # Replace all modulation bindings from the graph
        self._modulator.replace_all(graph.modulations)
        # Apply layer palettes from the graph
        for layer_name, palette in graph.layer_palettes.items():
            self._layer_palettes[layer_name] = palette
        if self._on_plan_changed is not None:
            self._on_plan_changed(old_plan, new_plan)

    def patch_node_params(self, node_id: str, params: dict[str, Any]) -> None:
        """Update params in-place on current graph. No recompilation."""
        if self._current_graph is None:
            msg = "No graph loaded"
            raise RuntimeError(msg)
        if node_id not in self._current_graph.nodes:
            msg = f"Node '{node_id}' not found in current graph"
            raise KeyError(msg)
        self._current_graph.nodes[node_id].params.update(params)
        if self._on_params_changed is not None:
            self._on_params_changed(node_id, params)

    def apply_patch(self, patch: GraphPatch) -> None:
        """Topology mutation. Deep copy current graph, apply adds/removes, recompile."""
        if self._current_graph is None:
            msg = "No graph loaded"
            raise RuntimeError(msg)
        graph = copy.deepcopy(self._current_graph)
        # Remove nodes
        for node_id in patch.remove_nodes:
            graph.nodes.pop(node_id, None)
            # Remove edges referencing this node
            graph.edges = [e for e in graph.edges if not _edge_references_node(e, node_id)]
        # Remove specific edges
        for edge in patch.remove_edges:
            if edge in graph.edges:
                graph.edges.remove(edge)
        # Add nodes
        for node_id, node in patch.add_nodes.items():
            graph.nodes[node_id] = node
        # Add edges
        graph.edges.extend(patch.add_edges)
        # Recompile
        self.load_graph(graph)

    def remove_node(self, node_id: str) -> None:
        """Remove node and all its edges via apply_patch."""
        self.apply_patch(GraphPatch(remove_nodes=[node_id]))

    def set_layer_palette(self, layer: str, palette: LayerPalette) -> None:
        self._layer_palettes[layer] = palette

    def get_layer_palette(self, layer: str) -> LayerPalette:
        return self._layer_palettes.get(layer, LayerPalette())

    def get_graph_state(self) -> dict[str, Any]:
        """Export current state for API: graph, layer_palettes, modulations."""
        return {
            "graph": self._current_graph.model_dump() if self._current_graph else None,
            "layer_palettes": {
                name: palette.model_dump() for name, palette in self._layer_palettes.items()
            },
            "modulations": [b.model_dump() for b in self._modulator.bindings],
        }


def _edge_references_node(edge: list[str], node_id: str) -> bool:
    """Check if an edge list entry references a given node_id."""
    for endpoint in edge:
        # Strip port suffix (e.g. "blend:a" -> "blend")
        name = (
            endpoint.split(":")[0] if ":" in endpoint and not endpoint.startswith("@") else endpoint
        )
        if name == node_id:
            return True
    return False
