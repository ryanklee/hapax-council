"""Topology descriptor → PipeWire conf generator (CLI Phase 2).

Emits PipeWire context.objects / context.modules fragments for each
node in a ``TopologyDescriptor`` so the live ``.conf`` files become a
deterministic artifact of the descriptor instead of a hand-authored
collection.

Current workstation confs the generator has to match:

- ``hapax-l6-evilpet-capture.conf`` — filter-chain with builtin mixer
  for +12 dB makeup gain on the L6 Main Mix AUX10+11 tap
- ``hapax-stream-split.conf`` — loopback pair (hapax-livestream +
  hapax-private) → Ryzen
- ``voice-fx-chain.conf`` — biquad-chain filter-chain targeting Ryzen

Scope:

- Phase 2 = per-node conf-fragment emission. ``node_to_conf_fragment``
  returns the text for one node; ``generate_confs`` groups them into
  descriptor-level ``{filename: content}`` dict.
- Out of scope: writing to disk, hot-reloading PipeWire (Phase 3 CLI),
  live-graph inspection (Phase 4).
- No Jinja dependency — f-string templates per kind keep the dep
  surface flat.

Round-trip guarantee: ``generate_confs(d)`` output captures enough to
reconstruct ``d`` when paired with Phase 4's ``pw_dump_to_descriptor``.
The confs themselves are not human-authored — operators edit the YAML
descriptor and regenerate.

Reference:
    - docs/superpowers/plans/2026-04-20-unified-audio-architecture-plan.md §2
"""

from __future__ import annotations

from shared.audio_topology import (
    Edge,
    Node,
    NodeKind,
    TopologyDescriptor,
)


def _gain_db_to_linear(db: float) -> float:
    """Convert dB to PipeWire ``builtin mixer`` ``Gain`` linear scalar."""
    return 10 ** (db / 20.0)


def _channels_line(node: Node) -> str:
    """Format ``audio.channels = N`` / ``audio.position = [...]`` lines."""
    cm = node.channels
    positions = " ".join(cm.positions) if cm.positions else ""
    lines = [f"            audio.channels = {cm.count}"]
    if positions:
        lines.append(f"            audio.position = [ {positions} ]")
    return "\n".join(lines)


def _params_lines(node: Node, indent: int = 12) -> str:
    """Format extra ``params`` as ``key = value`` conf lines.

    Skips keys that the node-kind template emits directly
    (``makeup_gain_linear``, ``audio.position``). Unknown keys
    round-trip verbatim so operator-supplied PipeWire tunables are
    preserved on regeneration.
    """
    reserved = {
        "makeup_gain_linear",
        "audio.channels",
        "audio.position",
    }
    pad = " " * indent
    out: list[str] = []
    for k, v in node.params.items():
        if k in reserved:
            continue
        if isinstance(v, bool):
            literal = "true" if v else "false"
        elif isinstance(v, (int, float)):
            literal = str(v)
        else:
            # Strings get quoted — matches PipeWire's accepting syntax.
            literal = f'"{v}"'
        out.append(f"{pad}{k} = {literal}")
    return "\n".join(out)


def _alsa_source_fragment(node: Node) -> str:
    channels = _channels_line(node)
    extra = _params_lines(node)
    extra_block = f"\n{extra}" if extra else ""
    return f"""# {node.description or node.pipewire_name}
context.objects = [
    {{  factory = adapter
        args = {{
            factory.name = api.alsa.pcm.source
            node.name    = "{node.pipewire_name}"
            media.class  = Audio/Source
            audio.format = S32LE
{channels}
            api.alsa.path = "{node.hw}"{extra_block}
        }}
    }}
]
"""


def _alsa_sink_fragment(node: Node) -> str:
    channels = _channels_line(node)
    extra = _params_lines(node)
    extra_block = f"\n{extra}" if extra else ""
    return f"""# {node.description or node.pipewire_name}
context.objects = [
    {{  factory = adapter
        args = {{
            factory.name = api.alsa.pcm.sink
            node.name    = "{node.pipewire_name}"
            media.class  = Audio/Sink
            audio.format = S32LE
{channels}
            api.alsa.path = "{node.hw}"{extra_block}
        }}
    }}
]
"""


def _filter_chain_fragment(node: Node, incoming_edges: list[Edge]) -> str:
    """Emit a filter-chain module with optional per-edge makeup gain.

    If any ``incoming_edge.makeup_gain_db != 0``, a ``builtin mixer``
    node is inserted with ``Gain 1`` set to the linear equivalent.
    Multiple distinct gains on different incoming ports produce
    multiple mixer nodes (one per port).
    """
    cm = node.channels
    target_line = (
        f'            target.object = "{node.target_object}"' if node.target_object else ""
    )
    positions_str = " ".join(cm.positions) if cm.positions else ""
    position_block = f"\n            audio.position = [ {positions_str} ]" if positions_str else ""

    gain_edges = [e for e in incoming_edges if e.makeup_gain_db != 0.0]
    graph_block = ""
    if gain_edges:
        mixer_nodes = []
        inputs = []
        outputs = []
        for i, edge in enumerate(gain_edges):
            linear = _gain_db_to_linear(edge.makeup_gain_db)
            mixer_name = f"gain_{i}"
            mixer_nodes.append(
                f"                    {{ type = builtin label = mixer name = {mixer_name}\n"
                f'                      control = {{ "Gain 1" = {linear:.4f} }} }}'
            )
            inputs.append(f'"{mixer_name}:In 1"')
            outputs.append(f'"{mixer_name}:Out"')
        graph_block = f"""
            filter.graph = {{
                nodes = [
{chr(10).join(mixer_nodes)}
                ]
                inputs  = [ {" ".join(inputs)} ]
                outputs = [ {" ".join(outputs)} ]
            }}"""

    return f"""# {node.description or node.pipewire_name}
context.modules = [
    {{  name = libpipewire-module-filter-chain
        args = {{
            node.description = "{node.description or node.pipewire_name}"
            audio.rate = 48000
            audio.channels = {cm.count}{position_block}{graph_block}
            capture.props = {{
                node.name = "{node.pipewire_name}"
            }}
            playback.props = {{
                node.name = "{node.pipewire_name}-playback"
{target_line}
            }}
        }}
    }}
]
"""


def _loopback_fragment(node: Node) -> str:
    cm = node.channels
    positions_str = " ".join(cm.positions) if cm.positions else ""
    position_block = f"\n            audio.position = [ {positions_str} ]" if positions_str else ""
    target_line = (
        f'            target.object = "{node.target_object}"' if node.target_object else ""
    )
    return f"""# {node.description or node.pipewire_name}
context.modules = [
    {{  name = libpipewire-module-loopback
        args = {{
            node.description = "{node.description or node.pipewire_name}"
            audio.rate = 48000
            audio.channels = {cm.count}{position_block}
            capture.props = {{
                node.name = "{node.pipewire_name}"
                media.class = Audio/Sink
            }}
            playback.props = {{
                node.name = "{node.pipewire_name}-output"
{target_line}
            }}
        }}
    }}
]
"""


def _tap_fragment(node: Node) -> str:
    """Null-sink / virtual sink — no audio processing, just a fan-out point."""
    cm = node.channels
    positions_str = " ".join(cm.positions) if cm.positions else ""
    position_block = (
        f"\n                audio.position = [ {positions_str} ]" if positions_str else ""
    )
    return f"""# {node.description or node.pipewire_name}
context.objects = [
    {{  factory = adapter
        args = {{
            factory.name = support.null-audio-sink
            node.name    = "{node.pipewire_name}"
            media.class  = Audio/Sink
            audio.channels = {cm.count}{position_block}
        }}
    }}
]
"""


_FORMATTERS = {
    NodeKind.ALSA_SOURCE: lambda n, _e: _alsa_source_fragment(n),
    NodeKind.ALSA_SINK: lambda n, _e: _alsa_sink_fragment(n),
    NodeKind.FILTER_CHAIN: _filter_chain_fragment,
    NodeKind.LOOPBACK: lambda n, _e: _loopback_fragment(n),
    NodeKind.TAP: lambda n, _e: _tap_fragment(n),
}


def node_to_conf_fragment(node: Node, descriptor: TopologyDescriptor) -> str:
    """Emit the PipeWire conf fragment for a single node.

    Pulls incoming edges from the descriptor so filter-chain gain
    stages can be emitted correctly; other node kinds ignore edges.
    """
    incoming = descriptor.edges_to(node.id)
    formatter = _FORMATTERS[node.kind]
    return formatter(node, incoming)


def generate_confs(descriptor: TopologyDescriptor) -> dict[str, str]:
    """Emit ``{suggested_filename: conf_content}`` for every node.

    File-naming convention: ``pipewire/<node.id>.conf``. Keeps the
    scope one-node-per-file so a descriptor change regenerates a
    bounded set of files and the git diff is readable.
    """
    out: dict[str, str] = {}
    for node in descriptor.nodes:
        filename = f"pipewire/{node.id}.conf"
        out[filename] = node_to_conf_fragment(node, descriptor)
    return out
