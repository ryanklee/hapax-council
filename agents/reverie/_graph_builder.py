"""Graph builder — constructs EffectGraph from core vocabulary + recruited satellites.

Handles node insertion at layer-appropriate positions based on signal-flow
classification. The layer classification is about processing order
(generate→color→spatial→temporal→content→effects→detection→post),
not semantic meaning.
"""

from __future__ import annotations

import logging
from pathlib import Path

from agents.effect_graph.registry import ShaderRegistry
from agents.effect_graph.types import EffectGraph

log = logging.getLogger("reverie.graph_builder")

NODES_DIR = Path(__file__).resolve().parent.parent / "shaders" / "nodes"

# Signal-flow layer classification for all known node types.
# Lower layer = earlier in the pipeline. Unknown nodes default to EFFECTS (6).
NODE_LAYERS: dict[str, int] = {
    # Layer 0: Generation
    "noise_gen": 0,
    "solid": 0,
    # Layer 1: Reaction/Simulation (temporal)
    "reaction_diffusion": 1,
    "fluid_sim": 1,
    # Layer 2: Color
    "colorgrade": 2,
    "color_map": 2,
    "thermal": 2,
    "nightvision": 2,
    "invert": 2,
    # Layer 3: Spatial
    "drift": 3,
    "warp": 3,
    "displacement_map": 3,
    "fisheye": 3,
    "mirror": 3,
    "kaleidoscope": 3,
    "tile": 3,
    "tunnel": 3,
    "droste": 3,
    # Layer 4: Temporal
    "breathing": 4,
    "feedback": 4,
    "trail": 4,
    "echo": 4,
    "stutter": 4,
    "slitscan": 4,
    "syrup": 4,
    # Layer 5: Content
    "content_layer": 5,
    "blend": 5,
    "crossfade": 5,
    # Layer 6: Effects
    "bloom": 6,
    "chromatic_aberration": 6,
    "glitch_block": 6,
    "pixsort": 6,
    "halftone": 6,
    "ascii": 6,
    "dither": 6,
    "vhs": 6,
    "datamosh": 6,
    "scanlines": 6,
    "noise_overlay": 6,
    "strobe": 6,
    # Layer 7: Detection
    "edge_detect": 7,
    "diff": 7,
    "luma_key": 7,
    "chroma_key": 7,
    "silhouette": 7,
    "threshold": 7,
    "emboss": 7,
    "sharpen": 7,
    # Layer 8: Post
    "postprocess": 8,
    "vignette": 8,
    "rutt_etra": 8,
    "waveform_render": 8,
    "posterize": 8,
    "circular_mask": 8,
}
DEFAULT_LAYER = 6


def _node_layer(node_type: str) -> int:
    """Get the signal-flow layer index for a node type."""
    return NODE_LAYERS.get(node_type, DEFAULT_LAYER)


def build_graph(
    core_vocab: dict,
    recruited: dict[str, float],
) -> EffectGraph:
    """Build EffectGraph with core nodes + recruited satellites at layer-appropriate positions.

    Args:
        core_vocab: The base vocabulary dict (from reverie_vocabulary.json).
        recruited: Map of node_type → activation strength for satellites to insert.

    Returns:
        EffectGraph ready for compilation.
    """
    registry = ShaderRegistry(NODES_DIR)

    # Start with core nodes (preserve their params)
    nodes: dict[str, dict] = {}
    for node_id, node_def in core_vocab.get("nodes", {}).items():
        nodes[node_id] = {"type": node_def["type"], "params": dict(node_def.get("params", {}))}

    # Add recruited satellites with default params from registry
    for node_type in recruited:
        if node_type == "output":
            continue
        # Skip if already in core (e.g., reaction_diffusion is core)
        if any(n["type"] == node_type for n in nodes.values()):
            continue
        # Generate unique node_id
        node_id = f"sat_{node_type}"
        reg_def = registry.get(node_type)
        if reg_def is None:
            log.warning("Unknown node type for recruitment: %s", node_type)
            continue
        default_params = {k: v.default for k, v in reg_def.params.items()}
        nodes[node_id] = {"type": node_type, "params": default_params}

    # Sort nodes by layer, preserving relative order within same layer
    # Output node always last
    output_id = None
    sortable = []
    for node_id, node_def in nodes.items():
        if node_def["type"] == "output":
            output_id = node_id
        else:
            sortable.append((node_id, node_def))

    sortable.sort(key=lambda x: _node_layer(x[1]["type"]))

    # Build linear chain edges
    ordered_ids = [s[0] for s in sortable]
    if output_id:
        ordered_ids.append(output_id)

    edges = []
    for i in range(len(ordered_ids) - 1):
        edges.append([ordered_ids[i], ordered_ids[i + 1]])

    # Reconstruct ordered nodes dict
    ordered_nodes = {}
    for nid in ordered_ids:
        ordered_nodes[nid] = nodes[nid]

    return EffectGraph(
        name=core_vocab.get("name", "Reverie Dynamic"),
        nodes=ordered_nodes,
        edges=edges,
    )
