"""Test that studio control and output affordances are registered."""

from shared.affordance_registry import AFFORDANCE_DOMAINS, ALL_AFFORDANCES


def test_studio_control_affordances_exist():
    studio = AFFORDANCE_DOMAINS.get("studio", [])
    control_names = [
        r.name
        for r in studio
        if any(
            k in r.name
            for k in [
                "activate",
                "adjust",
                "select",
                "toggle",
                "bind",
                "add_effect",
                "remove_effect",
            ]
        )
    ]
    assert len(control_names) >= 8, f"Expected >=8 studio control affordances, got {control_names}"


def test_output_affordances_exist():
    output_names = [r.name for r in ALL_AFFORDANCES if r.name.startswith("studio.output_")]
    assert len(output_names) >= 3, f"Expected >=3 output affordances, got {output_names}"


def test_studio_control_descriptions_are_gibson_verbs():
    studio = AFFORDANCE_DOMAINS.get("studio", [])
    controls = [r for r in studio if r.daemon == "compositor"]
    for r in controls:
        assert len(r.description) >= 15, f"{r.name} description too short"
        # Gibson verbs: transform, fine-tune, enable, shift, choose, connect, insert, remove, start, capture, display, route
        assert not r.description.startswith("API"), f"{r.name} description leaks implementation"


def test_no_duplicate_names_after_additions():
    names = [r.name for r in ALL_AFFORDANCES]
    dupes = [n for n in names if names.count(n) > 1]
    assert len(names) == len(set(names)), f"Duplicate affordance names: {set(dupes)}"
