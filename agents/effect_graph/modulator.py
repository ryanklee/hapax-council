"""Uniform modulator — drives shader uniforms from perceptual signals."""

from __future__ import annotations

from agents.effect_graph.types import ModulationBinding


class UniformModulator:
    """Drives shader uniforms from perceptual signal sources.

    Each binding maps a (node, param) pair to a named signal source with
    scale, offset, and exponential smoothing.
    """

    def __init__(self) -> None:
        self._bindings: dict[tuple[str, str], ModulationBinding] = {}
        self._smoothed: dict[tuple[str, str], float] = {}

    @property
    def bindings(self) -> list[ModulationBinding]:
        return list(self._bindings.values())

    def add_binding(self, binding: ModulationBinding) -> None:
        """Add or replace binding (same node+param replaces existing)."""
        key = (binding.node, binding.param)
        self._bindings[key] = binding
        # Clear smoothed state when binding is replaced.
        self._smoothed.pop(key, None)

    def remove_binding(self, node: str, param: str) -> None:
        key = (node, param)
        self._bindings.pop(key, None)
        self._smoothed.pop(key, None)

    def replace_all(self, bindings: list[ModulationBinding]) -> None:
        """Replace all bindings, clear smoothed state."""
        self._bindings.clear()
        self._smoothed.clear()
        for b in bindings:
            self._bindings[(b.node, b.param)] = b

    def tick(self, signals: dict[str, float]) -> dict[tuple[str, str], float]:
        """Process one frame tick. Returns {(node_id, param_name): value}."""
        updates: dict[tuple[str, str], float] = {}
        for key, binding in self._bindings.items():
            if binding.source not in signals:
                continue
            raw = signals[binding.source]
            target = raw * binding.scale + binding.offset
            if binding.smoothing > 0.0 and key in self._smoothed:
                prev = self._smoothed[key]
                value = binding.smoothing * prev + (1.0 - binding.smoothing) * target
            else:
                value = target
            self._smoothed[key] = value
            updates[key] = value
        return updates
