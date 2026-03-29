# Deviation Record: DEVIATION-026

**Date:** 2026-03-30
**Phase at time of change:** baseline (Cycle 2 Phase A)
**Author:** Claude (alpha session)

## What Changed

`agents/hapax_daimonion/conversation_pipeline.py` — 3 changes:

1. Line ~1233: un-comment `kwargs["tools"] = self.tools` so tools are
   passed to the LLM via function-calling.
2. Lines ~1428-1436: replace the skip block with
   `await self._handle_tool_calls(tool_calls_data, full_text)` to execute
   tools instead of logging and discarding.
3. Inside `_handle_tool_calls` (~line 1496): wrap handler call with
   `asyncio.wait_for(handler(args), timeout)` for per-tool timeout safety.

## Why

Tool execution was disabled due to latency concerns (10-15s round-trip).
The existing `_handle_tool_calls()` method is complete (bridge phrases,
consent filtering, follow-up generation) but never called. With per-tool
timeouts (3s default) and dynamic tool filtering (heavy tools suppressed
under resource pressure), the latency concern is addressed.

## Impact on Experiment Validity

Low. Tool execution is gated by `ToolContext`: in Research mode, tools are
suppressed unless `experiment_tools_enabled` flag is set. Baseline Phase A
data collection uses Research mode with tools disabled. R&D mode (current)
enables tools — this is non-experiment usage.

## Mitigation

- Per-tool timeout prevents runaway execution
- Dynamic filtering suppresses heavy tools under stimmung pressure
- Research mode suppresses all tools by default
- Existing consent filtering in `_handle_tool_calls` preserved
- Bridge phrase ("Let me check...") covers tool execution latency
