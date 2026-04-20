"""Voice-path runtime switcher — dual-fx-routing Phase 4.

Bridges the static voice-path router (``agents.hapax_daimonion.voice_path``,
which decides WHICH path) and the live PipeWire graph (which determines
WHERE audio actually goes). The router emits a ``VoicePath`` choice;
this module mutates the live graph so subsequent and existing audio
streams land on the right sink.

Two operations per switch:

1. **Default sink update.** Sets ``metadata.default.audio.sink`` via
   ``pw-cli set-default-audio-sink``. Future sink-inputs (e.g., a
   freshly-spawned Kokoro TTS subprocess) inherit the new default.
2. **Active sink-input migration.** Iterates ``pactl list short
   sink-inputs`` and runs ``pactl move-sink-input <id> <target>`` for
   any input currently bound to the prior sink. Without this step the
   switch only takes effect for new streams; the in-flight TTS
   utterance keeps playing through the old sink.

The subprocess runner is injectable so tests can capture calls without
spinning up PipeWire. Production passes the default ``_subprocess_run``
which invokes the real ``pactl``/``pw-cli`` binaries.

References:
- Plan: docs/superpowers/plans/2026-04-20-dual-fx-routing-plan.md §Phase 4
- Routing map: config/voice-paths.yaml
- Path router: agents/hapax_daimonion/voice_path.py
"""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommandResult:
    """Subprocess result reduced to the fields the switcher cares about."""

    returncode: int
    stdout: str
    stderr: str


CommandRunner = Callable[[list[str]], CommandResult]


def _subprocess_run(cmd: list[str]) -> CommandResult:
    """Default runner — wraps subprocess.run with a 5s timeout."""
    proc = subprocess.run(  # noqa: S603 — args list is constructed, not shell-interpolated
        cmd,
        capture_output=True,
        text=True,
        timeout=5.0,
        check=False,
    )
    return CommandResult(
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


@dataclass(frozen=True)
class SwitchResult:
    """Outcome of a voice-path switch.

    ``target_sink`` is the sink the switcher tried to make default.
    ``moved_input_ids`` lists the sink-input IDs that were migrated
    from the prior sink onto the target. ``default_set_ok`` flags
    whether ``pw-cli set-default-audio-sink`` succeeded; ``warnings``
    aggregates non-fatal failures (e.g., a single ``pactl
    move-sink-input`` call failing when others succeeded).
    """

    target_sink: str
    moved_input_ids: tuple[str, ...]
    default_set_ok: bool
    warnings: tuple[str, ...]


def _parse_sink_inputs(stdout: str, prior_sink_id: str | None) -> list[str]:
    """Parse ``pactl list short sink-inputs`` output for IDs bound to prior_sink_id.

    Output format (tab-separated):
        <input_id>\\t<driver>\\t<client>\\t<sink_id>\\t<sample_spec>...

    When ``prior_sink_id`` is None, returns ALL active input IDs (the
    caller wants every input migrated regardless of source).
    """
    out: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        cols = line.split("\t")
        if len(cols) < 4:
            continue
        input_id = cols[0]
        sink_id = cols[3]
        if prior_sink_id is None or sink_id == prior_sink_id:
            out.append(input_id)
    return out


def _resolve_sink_id(stdout: str, sink_name: str) -> str | None:
    """Parse ``pactl list short sinks`` output to find the numeric id
    corresponding to ``sink_name``. Returns None when not found.

    Output format (tab-separated):
        <sink_id>\\t<sink_name>\\t<driver>\\t<sample_spec>\\t<state>
    """
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        cols = line.split("\t")
        if len(cols) < 2:
            continue
        if cols[1] == sink_name:
            return cols[0]
    return None


def switch_voice_path(
    target_sink_name: str,
    *,
    prior_sink_name: str | None = None,
    _runner: CommandRunner = _subprocess_run,
) -> SwitchResult:
    """Make ``target_sink_name`` the default audio sink and migrate
    any sink-inputs currently bound to ``prior_sink_name``.

    Args:
        target_sink_name: PipeWire sink node name (e.g.
            ``alsa_output.usb-Torso_Electronics_S-4``). Must already
            exist in the live graph; this function does NOT create
            sinks.
        prior_sink_name: When set, only inputs currently routed to
            this sink are migrated — leaves unrelated streams alone.
            When None, every active sink-input is migrated to the
            target (heavier hammer; use only when a full repoint is
            intended).
        _runner: Injectable subprocess runner. Tests pass a mock to
            capture commands without invoking pw-cli/pactl.

    Returns:
        SwitchResult with target sink, moved input IDs, default-set
        outcome, and any non-fatal warnings.
    """
    warnings: list[str] = []

    # 1) Set the default sink — affects future inputs.
    default_cmd = ["pw-cli", "set-default-audio-sink", target_sink_name]
    default_result = _runner(default_cmd)
    default_ok = default_result.returncode == 0
    if not default_ok:
        warnings.append(
            f"pw-cli set-default-audio-sink failed (rc={default_result.returncode}): "
            f"{default_result.stderr.strip()}"
        )
        log.warning(
            "voice-path switch: set-default-audio-sink %s failed: %s",
            target_sink_name,
            default_result.stderr.strip(),
        )

    # 2) Look up sink IDs so move-sink-input can use the numeric form
    #    (pactl accepts either name or id; numeric id is more reliable
    #    when sink names contain spaces or special characters).
    sinks_result = _runner(["pactl", "list", "short", "sinks"])
    if sinks_result.returncode != 0:
        warnings.append(
            f"pactl list short sinks failed (rc={sinks_result.returncode}); "
            "skipping sink-input migration"
        )
        return SwitchResult(
            target_sink=target_sink_name,
            moved_input_ids=(),
            default_set_ok=default_ok,
            warnings=tuple(warnings),
        )
    target_sink_id = _resolve_sink_id(sinks_result.stdout, target_sink_name)
    if target_sink_id is None:
        warnings.append(
            f"target sink {target_sink_name!r} not found in pactl listing; "
            "skipping sink-input migration"
        )
        return SwitchResult(
            target_sink=target_sink_name,
            moved_input_ids=(),
            default_set_ok=default_ok,
            warnings=tuple(warnings),
        )
    prior_sink_id = (
        _resolve_sink_id(sinks_result.stdout, prior_sink_name)
        if prior_sink_name is not None
        else None
    )

    # 3) Enumerate active sink-inputs bound to the prior sink (or all).
    inputs_result = _runner(["pactl", "list", "short", "sink-inputs"])
    if inputs_result.returncode != 0:
        warnings.append(
            f"pactl list short sink-inputs failed (rc={inputs_result.returncode}); "
            "no inputs migrated"
        )
        return SwitchResult(
            target_sink=target_sink_name,
            moved_input_ids=(),
            default_set_ok=default_ok,
            warnings=tuple(warnings),
        )
    candidate_ids = _parse_sink_inputs(inputs_result.stdout, prior_sink_id)

    # 4) Migrate each.
    moved: list[str] = []
    for input_id in candidate_ids:
        move_cmd = ["pactl", "move-sink-input", input_id, target_sink_id]
        move_result = _runner(move_cmd)
        if move_result.returncode == 0:
            moved.append(input_id)
        else:
            warnings.append(
                f"move-sink-input {input_id} → {target_sink_name} failed: "
                f"{move_result.stderr.strip()}"
            )

    return SwitchResult(
        target_sink=target_sink_name,
        moved_input_ids=tuple(moved),
        default_set_ok=default_ok,
        warnings=tuple(warnings),
    )


__all__ = [
    "CommandResult",
    "CommandRunner",
    "SwitchResult",
    "switch_voice_path",
]
