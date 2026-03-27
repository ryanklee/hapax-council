"""Smoke test rule — activates smoke test mode and rewrites Playwright tool calls."""

from __future__ import annotations

import logging
import re

from agents.session_conductor.rules import HookEvent, HookResponse, RuleBase
from agents.session_conductor.rules.relay import detect_pr_event
from agents.session_conductor.state import SessionState
from agents.session_conductor.topology import TopologyConfig

log = logging.getLogger(__name__)

_SMOKE_TRIGGER_RE = re.compile(r"\bsmoke\s+test\b", re.IGNORECASE)


def is_smoke_test_trigger(text: str) -> bool:
    """Return True if the text contains 'smoke test'."""
    return bool(_SMOKE_TRIGGER_RE.search(text))


class SmokeRule(RuleBase):
    """Activate smoke test mode on trigger and rewrite Playwright browser_* calls."""

    def __init__(self, topology: TopologyConfig, state: SessionState) -> None:
        super().__init__(topology)
        self._state = state

    def on_pre_tool_use(self, event: HookEvent) -> HookResponse | None:
        # Rewrite browser_* calls when smoke test is active
        if self._state.smoke_test_active and event.tool_name.startswith("browser_"):
            cfg = self.topology.smoke_test
            rewritten = dict(event.tool_input)
            rewritten["workspace"] = cfg.workspace
            rewritten["fullscreen"] = cfg.fullscreen
            rewritten["launch_method"] = cfg.launch_method
            rewritten["screenshot_interval_ms"] = cfg.screenshot_interval_ms
            log.debug("SmokeRule: rewrote %s with smoke test config", event.tool_name)
            return HookResponse(
                action="rewrite",
                message="Browser tool rewritten with smoke test config",
                rewrite=rewritten,
            )
        return None

    def on_post_tool_use(self, event: HookEvent) -> HookResponse | None:
        # Activate on user message containing "smoke test"
        if event.user_message and is_smoke_test_trigger(event.user_message):
            if not self._state.smoke_test_active:
                log.info("SmokeRule: activating smoke test mode (user message trigger)")
                self._state.smoke_test_active = True
            return None

        # Activate on PR creation in Bash output
        if event.tool_name == "Bash":
            output: str = event.user_message or ""
            pr_event = detect_pr_event(output)
            if pr_event and pr_event["type"] == "create":
                if not self._state.smoke_test_active:
                    log.info("SmokeRule: activating smoke test mode (PR create trigger)")
                    self._state.smoke_test_active = True

        return None
