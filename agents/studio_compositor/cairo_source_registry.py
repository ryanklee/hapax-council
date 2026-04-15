"""CairoSourceRegistry — zone → CairoSource subclass binding.

LRR Phase 2 item 10a (per §3.10 of the amended Phase 2 spec). This
registry maps compositor zones (declared in ``config/compositor-zones.yaml``)
to ``CairoSource`` subclasses that render content in them.

Distinct from ``agents/studio_compositor/source_registry.py``:

- ``source_registry.py::SourceRegistry`` (shipped in Reverie
  source-registry completion epic / PR #822) manages SURFACE BACKEND
  BINDING: ``register(source_id, backend)`` + ``get_current_surface(source_id)``.
  The concern is "which backend renders the 'compositor_main' surface?"
- ``cairo_source_registry.py::CairoSourceRegistry`` (this module) manages
  ZONE → CAIRO-SOURCE-SUBCLASS BINDING: ``register(source_cls, zone, priority)``
  + ``get_for_zone(zone)``. The concern is "which CairoSource subclass
  renders in the 'hud_top_left' zone?"

The two registries serve different concerns and coexist cleanly. Phase 2
item 10 creates this new module; the existing ``source_registry.py`` is
untouched.

Registration pattern (from Phase 2 spec §3.10):

    from agents.studio_compositor.cairo_source_registry import CairoSourceRegistry

    CairoSourceRegistry.register(
        source_cls=HudSource,
        zone="hud_top_left",
        priority=10,
    )

HSEA Phase 1 uses this pattern to register its 5 new Cairo sources
(1.1 HUD, 1.2 objective strip, 1.3 frozen-files placard, 1.4 governance
queue placard, 1.5 condition transition banner).

Multiple sources can register for the same zone; the registry returns
them ordered by ``priority`` (highest first). Ties are broken by
registration order. This lets Phase 2 item 10b wire the current
CairoSources (album overlay, sierpinski, overlay zones, token pole)
into their current zones while HSEA Phase 1 adds higher-priority
sources that override them.

Spec: docs/superpowers/specs/2026-04-15-lrr-phase-2-archive-research-instrument-design.md §3.10
Architectural judgment: commit 6983ae62e (naming collision resolution)
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from agents.studio_compositor.cairo_source import CairoSource


@dataclass(frozen=True)
class CairoSourceBinding:
    """A single (source_cls, zone, priority) registration entry.

    Immutable dataclass. The registry stores these internally + returns
    them to callers via ``get_for_zone``. The ``registration_index`` is
    assigned at register-time so ties in ``priority`` resolve to
    registration order (earlier wins).
    """

    source_cls: type[CairoSource]
    zone: str
    priority: int
    registration_index: int = field(default=0, compare=False)


class CairoSourceRegistry:
    """Zone → CairoSource subclass binding registry.

    Module-level singleton. Use the class methods (``register``,
    ``get_for_zone``, ``all_sources``, ``clear``) rather than
    instantiating. All state lives in the class-level dict + counter +
    lock. ``clear()`` is provided for test fixtures.

    Thread-safety: the registry uses a class-level ``threading.Lock``
    around all mutation + read operations. Registration + lookup are
    expected to happen during compositor bootstrap (single thread) but
    the lock makes concurrent test invocations safe.
    """

    _bindings: dict[str, list[CairoSourceBinding]] = {}
    _counter: int = 0
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def register(
        cls,
        *,
        source_cls: type[CairoSource],
        zone: str,
        priority: int = 0,
    ) -> CairoSourceBinding:
        """Register a CairoSource subclass to a zone.

        ``source_cls`` must be a ``CairoSource`` subclass (enforced by
        ``issubclass``). ``zone`` is a non-empty string matching a zone
        declared in ``config/compositor-zones.yaml``. ``priority`` is an
        integer; higher values render "in front" when multiple sources
        compete for the same zone.

        Returns the created binding. Raises ``TypeError`` if
        ``source_cls`` is not a ``CairoSource`` subclass. Raises
        ``ValueError`` if ``zone`` is empty.
        """
        if not (isinstance(source_cls, type) and issubclass(source_cls, CairoSource)):
            raise TypeError(
                f"CairoSourceRegistry.register: source_cls must be a "
                f"CairoSource subclass, got {source_cls!r}"
            )
        if not zone:
            raise ValueError("CairoSourceRegistry.register: zone must be non-empty")
        with cls._lock:
            binding = CairoSourceBinding(
                source_cls=source_cls,
                zone=zone,
                priority=priority,
                registration_index=cls._counter,
            )
            cls._counter += 1
            cls._bindings.setdefault(zone, []).append(binding)
        return binding

    @classmethod
    def get_for_zone(cls, zone: str) -> list[CairoSourceBinding]:
        """Return all bindings registered for ``zone``, priority-sorted.

        Higher priority first; registration order breaks ties (earlier
        wins). Returns an empty list if no sources are registered for
        the zone. The returned list is a snapshot copy — mutating it
        does not affect the registry.
        """
        with cls._lock:
            bindings = list(cls._bindings.get(zone, []))
        bindings.sort(key=lambda b: (-b.priority, b.registration_index))
        return bindings

    @classmethod
    def all_sources(cls) -> list[CairoSourceBinding]:
        """Return every registered binding across all zones.

        Sorted by ``(zone, -priority, registration_index)`` for
        deterministic enumeration (e.g., for startup-probe logging).
        """
        with cls._lock:
            all_bindings: list[CairoSourceBinding] = []
            for zone_bindings in cls._bindings.values():
                all_bindings.extend(zone_bindings)
        all_bindings.sort(key=lambda b: (b.zone, -b.priority, b.registration_index))
        return all_bindings

    @classmethod
    def zones(cls) -> list[str]:
        """Return every zone that has at least one registered binding, sorted."""
        with cls._lock:
            return sorted(cls._bindings.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear the entire registry. For test fixtures only.

        Production code should never call this — once the compositor
        bootstraps, the registry is append-only until process exit. The
        method exists so tests can use ``CairoSourceRegistry`` as a
        singleton without leaking state between tests.
        """
        with cls._lock:
            cls._bindings = {}
            cls._counter = 0
