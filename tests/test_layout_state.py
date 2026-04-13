"""LayoutState tests — in-memory authority for the compositor Layout.

Part of the compositor source-registry epic PR 1. See
``docs/superpowers/plans/2026-04-12-compositor-source-registry-foundation-plan.md``
§ Phase A Task 2.
"""

from __future__ import annotations

import threading

import pytest

from agents.studio_compositor.layout_state import LayoutState
from shared.compositor_model import (
    Assignment,
    Layout,
    SourceSchema,
    SurfaceGeometry,
    SurfaceSchema,
)


def _minimal_layout() -> Layout:
    return Layout(
        name="test",
        sources=[
            SourceSchema(
                id="src1",
                kind="cairo",
                backend="cairo",
                params={"class_name": "TestSource", "natural_w": 100, "natural_h": 100},
            )
        ],
        surfaces=[
            SurfaceSchema(
                id="pip-ul",
                geometry=SurfaceGeometry(kind="rect", x=0, y=0, w=100, h=100),
            )
        ],
        assignments=[Assignment(source="src1", surface="pip-ul")],
    )


class TestLayoutStateBasics:
    def test_get_returns_current_snapshot(self):
        state = LayoutState(_minimal_layout())
        layout = state.get()
        assert layout.name == "test"
        assert len(layout.surfaces) == 1

    def test_mutate_replaces_layout_atomically(self):
        state = LayoutState(_minimal_layout())

        def move_pip(layout: Layout) -> Layout:
            new_surfaces = [
                s.model_copy(
                    update={"geometry": s.geometry.model_copy(update={"x": 500, "y": 400})}
                )
                for s in layout.surfaces
            ]
            return layout.model_copy(update={"surfaces": new_surfaces})

        state.mutate(move_pip)
        assert state.get().surfaces[0].geometry.x == 500
        assert state.get().surfaces[0].geometry.y == 400

    def test_subscribe_receives_mutated_layout(self):
        state = LayoutState(_minimal_layout())
        received: list[Layout] = []
        state.subscribe(received.append)
        state.mutate(lambda layout: layout.model_copy(update={"description": "mutated"}))
        assert len(received) == 1
        assert received[0].description == "mutated"

    def test_mutate_validation_failure_rolls_back(self):
        state = LayoutState(_minimal_layout())

        def break_layout(layout: Layout) -> Layout:
            return layout.model_copy(
                update={"assignments": [Assignment(source="nonexistent", surface="pip-ul")]}
            )

        with pytest.raises(ValueError, match="unknown source"):
            state.mutate(break_layout)
        assert state.get().assignments[0].source == "src1"

    def test_subscriber_exception_does_not_break_mutation(self):
        state = LayoutState(_minimal_layout())

        def bad_sub(_layout: Layout) -> None:
            raise RuntimeError("subscriber failure")

        good_received: list[Layout] = []
        state.subscribe(bad_sub)
        state.subscribe(good_received.append)
        state.mutate(lambda layout: layout.model_copy(update={"description": "x"}))
        assert len(good_received) == 1
        assert good_received[0].description == "x"


class TestLayoutStateConcurrency:
    def test_mutate_is_atomic_under_concurrent_readers(self):
        state = LayoutState(_minimal_layout())
        done = threading.Event()
        observed_xs: list[int] = []

        def writer() -> None:
            for i in range(100):
                state.mutate(
                    lambda layout, i=i: layout.model_copy(
                        update={
                            "surfaces": [
                                s.model_copy(
                                    update={"geometry": s.geometry.model_copy(update={"x": i})}
                                )
                                for s in layout.surfaces
                            ]
                        }
                    )
                )
            done.set()

        def reader() -> None:
            while not done.is_set():
                x = state.get().surfaces[0].geometry.x
                if x is not None:
                    observed_xs.append(x)

        writers = [threading.Thread(target=writer) for _ in range(5)]
        readers = [threading.Thread(target=reader) for _ in range(20)]
        for t in readers + writers:
            t.start()
        for t in writers:
            t.join()
        done.set()
        for t in readers:
            t.join()
        assert observed_xs, "readers should have observed at least one value"
        for x in observed_xs:
            assert 0 <= x <= 99


class TestLayoutStateSelfWrite:
    def test_mark_and_detect_self_write_within_tolerance(self):
        state = LayoutState(_minimal_layout())
        state.mark_self_write(1_000.0)
        assert state.is_self_write(1_000.5)
        assert state.is_self_write(1_001.9)
        assert not state.is_self_write(1_010.0)

    def test_is_self_write_tolerance_kwarg(self):
        state = LayoutState(_minimal_layout())
        state.mark_self_write(100.0)
        assert state.is_self_write(105.0, tolerance=6.0)
        assert not state.is_self_write(105.0, tolerance=3.0)
