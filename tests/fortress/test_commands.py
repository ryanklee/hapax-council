"""Tests for FortressCommand construction and factory functions."""

from __future__ import annotations

import unittest

from agents.fortress.commands import (
    FortressCommand,
    cmd_build,
    cmd_dig,
    cmd_labor,
    cmd_military,
    cmd_order,
    cmd_pause,
    cmd_place,
)


class TestFortressCommand(unittest.TestCase):
    """Test FortressCommand dataclass behavior."""

    def test_frozen(self) -> None:
        cmd = FortressCommand(id="1", action="dig", chain="planner")
        with self.assertRaises(AttributeError):
            cmd.action = "build"  # type: ignore[misc]

    def test_default_params(self) -> None:
        cmd = FortressCommand(id="", action="pause", chain="crisis")
        self.assertEqual(cmd.params, {})
        self.assertTrue(cmd.governance_allowed)
        self.assertEqual(cmd.governance_denied_by, ())

    def test_to_bridge_dict(self) -> None:
        cmd = FortressCommand(id="x", action="dig", chain="planner", params={"blueprint": "d,d,d"})
        bridge = cmd.to_bridge_dict()
        self.assertEqual(bridge["action"], "dig")
        self.assertEqual(bridge["blueprint"], "d,d,d")

    def test_to_bridge_dict_merges_params(self) -> None:
        cmd = FortressCommand(
            id="y",
            action="order",
            chain="resource",
            params={"item_type": "helm", "material": "iron", "quantity": 5},
        )
        bridge = cmd.to_bridge_dict()
        self.assertEqual(bridge["action"], "order")
        self.assertEqual(bridge["quantity"], 5)


class TestFactoryFunctions(unittest.TestCase):
    """Test command factory helpers."""

    def test_cmd_dig(self) -> None:
        cmd = cmd_dig("planner", "d,d,d\nd,d,d")
        self.assertEqual(cmd.action, "dig")
        self.assertEqual(cmd.chain, "planner")
        self.assertEqual(cmd.params["blueprint"], "d,d,d\nd,d,d")

    def test_cmd_build(self) -> None:
        cmd = cmd_build("planner", "Cw,`,`")
        self.assertEqual(cmd.action, "build")
        self.assertEqual(cmd.params["blueprint"], "Cw,`,`")

    def test_cmd_place(self) -> None:
        cmd = cmd_place("planner", "b,`,`")
        self.assertEqual(cmd.action, "place")
        self.assertEqual(cmd.params["blueprint"], "b,`,`")

    def test_cmd_order(self) -> None:
        cmd = cmd_order("resource", "helm", material="iron", quantity=5)
        self.assertEqual(cmd.action, "order")
        self.assertEqual(cmd.params["item_type"], "helm")
        self.assertEqual(cmd.params["material"], "iron")
        self.assertEqual(cmd.params["quantity"], 5)

    def test_cmd_order_defaults(self) -> None:
        cmd = cmd_order("resource", "barrel")
        self.assertEqual(cmd.params["material"], "")
        self.assertEqual(cmd.params["quantity"], 1)

    def test_cmd_military(self) -> None:
        cmd = cmd_military("military", "station", squad_id=3)
        self.assertEqual(cmd.action, "military")
        self.assertEqual(cmd.params["operation"], "station")
        self.assertEqual(cmd.params["squad_id"], 3)

    def test_cmd_labor(self) -> None:
        cmd = cmd_labor("resource", unit_id=42, labor="MINING", enabled=True)
        self.assertEqual(cmd.action, "labor")
        self.assertEqual(cmd.params["unit_id"], 42)
        self.assertEqual(cmd.params["labor"], "MINING")
        self.assertTrue(cmd.params["enabled"])

    def test_cmd_labor_disable(self) -> None:
        cmd = cmd_labor("resource", unit_id=42, labor="MINING", enabled=False)
        self.assertFalse(cmd.params["enabled"])

    def test_cmd_pause(self) -> None:
        cmd = cmd_pause("crisis")
        self.assertEqual(cmd.action, "pause")
        self.assertTrue(cmd.params["state"])

    def test_cmd_pause_unpause(self) -> None:
        cmd = cmd_pause("crisis", state=False)
        self.assertFalse(cmd.params["state"])

    def test_factory_created_at(self) -> None:
        cmd = cmd_dig("planner", "d", created_at=123.456)
        self.assertEqual(cmd.created_at, 123.456)

    def test_factory_governance_denied(self) -> None:
        cmd = cmd_dig(
            "planner",
            "d",
            governance_allowed=False,
            governance_denied_by=("picks_available",),
        )
        self.assertFalse(cmd.governance_allowed)
        self.assertEqual(cmd.governance_denied_by, ("picks_available",))


if __name__ == "__main__":
    unittest.main()
