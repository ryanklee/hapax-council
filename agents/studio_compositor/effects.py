"""Effect graph integration for the compositor."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Legacy preset name -> graph file name mapping
GRAPH_PRESET_ALIASES: dict[str, str] = {
    "ascii": "ascii_preset",
    "diff": "diff_preset",
    "feedback": "feedback_preset",
    "glitchblocks": "glitch_blocks_preset",
    "halftone": "halftone_preset",
    "pixsort": "pixsort_preset",
    "slitscan": "slitscan_preset",
    "thermal": "thermal_preset",
    "vhs": "vhs_preset",
}


def init_graph_runtime(compositor: Any) -> Any:
    """Initialize the effect node graph system."""
    try:
        from agents.effect_graph.compiler import GraphCompiler
        from agents.effect_graph.modulator import UniformModulator
        from agents.effect_graph.registry import ShaderRegistry
        from agents.effect_graph.runtime import GraphRuntime

        shader_nodes_dir = Path(__file__).parent.parent / "shaders" / "nodes"
        registry = ShaderRegistry(shader_nodes_dir)
        compiler = GraphCompiler(registry)
        modulator = UniformModulator()
        runtime = GraphRuntime(registry=registry, compiler=compiler, modulator=modulator)

        runtime._on_params_changed = compositor._on_graph_params_changed
        runtime._on_plan_changed = compositor._on_graph_plan_changed

        try:
            from logos.api.routes.studio import set_graph_runtime, set_shader_registry

            set_graph_runtime(runtime)
            set_shader_registry(registry)
        except ImportError:
            log.debug("API routes not available — graph runtime not exposed")

        log.info("Effect node graph: %d node types loaded", len(registry.node_types))
        return runtime
    except Exception:
        log.warning("Effect node graph system not available", exc_info=True)
        return None


def try_graph_preset(compositor: Any, name: str) -> bool:
    """Try to load a graph-based preset. Returns True if found and loaded."""
    candidates = [name]
    alias = GRAPH_PRESET_ALIASES.get(name)
    if alias:
        candidates.append(alias)

    for dir_ in (
        Path.home() / ".config" / "hapax" / "effect-presets",
        Path(__file__).parent.parent.parent / "presets",
    ):
        for candidate in candidates:
            preset_path = dir_ / f"{candidate}.json"
            if preset_path.is_file():
                try:
                    from agents.effect_graph.types import EffectGraph

                    raw = json.loads(preset_path.read_text())
                    graph = EffectGraph(**raw)
                    graph = merge_default_modulations(graph)
                    compositor._graph_runtime.load_graph(graph)
                    log.info("Activated graph preset: %s (file: %s)", name, candidate)
                    return True
                except Exception:
                    log.warning("Failed to load graph preset %s", candidate, exc_info=True)
    return False


def merge_default_modulations(graph: Any) -> Any:
    """Merge default modulation template into a graph's modulations."""
    template_path = Path(__file__).parent.parent.parent / "presets" / "_default_modulations.json"
    if not template_path.is_file():
        return graph

    try:
        defaults = json.loads(template_path.read_text()).get("default_modulations", [])
    except Exception:
        return graph

    existing = {(m.node, m.param) for m in graph.modulations}

    # Build type→node_id map for matching default bindings to prefixed nodes
    type_to_ids: dict[str, list[str]] = {}
    for nid, node in graph.nodes.items():
        t = node.type
        if t not in type_to_ids:
            type_to_ids[t] = []
        type_to_ids[t].append(nid)

    from agents.effect_graph.types import ModulationBinding

    merged = list(graph.modulations)
    for d in defaults:
        target_type = d["node"]
        # Find all nodes matching this type (handles prefixed IDs like p0_bloom)
        matching_ids = type_to_ids.get(target_type, [])
        if not matching_ids:
            continue
        # Apply to the LAST matching node — in chains, earlier instances are
        # neutralized (identity params), so modulations should target the
        # last instance which retains authored params.
        node_id = matching_ids[-1]
        key = (node_id, d["param"])
        if key not in existing:
            merged.append(
                ModulationBinding(
                    node=node_id,
                    param=d["param"],
                    source=d["source"],
                    scale=d.get("scale", 1.0),
                    offset=d.get("offset", 0.0),
                    smoothing=d.get("smoothing", 0.85),
                    attack=d.get("attack"),
                    decay=d.get("decay"),
                )
            )

    return graph.model_copy(update={"modulations": merged})


def get_available_preset_names() -> set[str]:
    """Return set of preset names that exist on disk."""
    names: set[str] = set()
    for dir_ in (
        Path.home() / ".config" / "hapax" / "effect-presets",
        Path(__file__).parent.parent.parent / "presets",
    ):
        if dir_.is_dir():
            for f in dir_.glob("*.json"):
                if not f.name.startswith("_"):
                    names.add(f.stem)
    return names
