"""Focus enforcement rule — keeps Playwright tools in the testing workspace."""

from __future__ import annotations

import logging
import re

from agents.session_conductor.rules import HookEvent, HookResponse, RuleBase
from agents.session_conductor.topology import TopologyConfig

log = logging.getLogger(__name__)

# Matches: hyprctl dispatch workspace <number> (non-silent)
_WORKSPACE_SWITCH_RE = re.compile(
    r"hyprctl\s+dispatch\s+workspace\s+(?!silent:)(\S+)",
    re.IGNORECASE,
)


class FocusRule(RuleBase):
    """Enforce that browser tools stay in the testing workspace.

    - Rewrites all browser_* tool calls to include the configured testing workspace.
    - Rewrites non-silent ``hyprctl dispatch workspace`` commands to the silent variant
      so operator focus is never stolen.
    """

    def __init__(self, topology: TopologyConfig) -> None:
        super().__init__(topology)

    def on_pre_tool_use(self, event: HookEvent) -> HookResponse | None:
        # Rewrite Playwright / browser_* tools to include workspace constraint
        if event.tool_name.startswith("browser_"):
            workspace = self.topology.playwright.testing_workspace
            rewritten = dict(event.tool_input)
            rewritten["workspace"] = workspace
            log.debug(
                "FocusRule: rewriting %s to use testing workspace %d",
                event.tool_name,
                workspace,
            )
            return HookResponse(
                action="rewrite",
                message=f"Redirected to testing workspace {workspace}",
                rewrite=rewritten,
            )

        # Rewrite non-silent workspace switches
        if event.tool_name == "Bash":
            command: str = event.tool_input.get("command", "")
            m = _WORKSPACE_SWITCH_RE.search(command)
            if m:
                target = m.group(1)
                silent_command = _WORKSPACE_SWITCH_RE.sub(
                    f"hyprctl dispatch workspace silent:{target}", command
                )
                log.debug("FocusRule: rewrote workspace switch to silent variant")
                return HookResponse(
                    action="rewrite",
                    message="Workspace switch rewritten to silent variant",
                    rewrite={"command": silent_command},
                )

        return None

    def on_post_tool_use(self, event: HookEvent) -> HookResponse | None:
        return None
