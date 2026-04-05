"""Uniform modulation — binds node parameters to perceptual signal sources."""

from __future__ import annotations

from .types import ModulationBinding


class UniformModulator:
    def __init__(self) -> None:
        self._bindings: list[ModulationBinding] = []
        self._smoothed: dict[tuple[str, str], float] = {}

    @property
    def bindings(self) -> list[ModulationBinding]:
        return list(self._bindings)

    def add_binding(self, b: ModulationBinding) -> None:
        self._bindings = [
            x for x in self._bindings if not (x.node == b.node and x.param == b.param)
        ]
        self._bindings.append(b)

    def remove_binding(self, node: str, param: str) -> None:
        self._bindings = [x for x in self._bindings if not (x.node == node and x.param == param)]
        self._smoothed.pop((node, param), None)

    def replace_all(self, bindings: list[ModulationBinding]) -> None:
        self._bindings = list(bindings)
        self._smoothed.clear()

    def tick(self, signals: dict[str, float]) -> dict[tuple[str, str], float]:
        updates: dict[tuple[str, str], float] = {}
        for b in self._bindings:
            raw = signals.get(b.source)
            if raw is None:
                continue
            target = raw * b.scale + b.offset
            key = (b.node, b.param)
            prev = self._smoothed.get(key)
            if prev is None:
                val = target
            elif b.attack is not None and b.decay is not None:
                # Asymmetric envelope: fast attack for transients, slow decay
                coeff = b.attack if target > prev else b.decay
                val = coeff * prev + (1.0 - coeff) * target
            elif b.smoothing == 0.0:
                val = target
            else:
                val = b.smoothing * prev + (1.0 - b.smoothing) * target
            self._smoothed[key] = val
            updates[key] = val

        # NOTE: Reverie's uniforms.json is written by the Reverie actuation loop
        # (agents/reverie/actuation.py), not by the compositor modulator.
        # The compositor modulator drives GStreamer slot pipeline uniforms only.

        return updates
