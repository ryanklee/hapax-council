"""Tests for shared.audio_route_switcher — pactl command composition."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from shared.audio_route_switcher import (
    apply_switch,
    build_switch_commands,
    list_sink_inputs,
)


class TestBuildSwitchCommands:
    def test_empty_target_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            build_switch_commands("")

    def test_no_inputs_default_sink_only(self) -> None:
        cmds = build_switch_commands("alsa_output.s4", sink_input_ids=[])
        assert cmds == [["pactl", "set-default-sink", "alsa_output.s4"]]

    def test_none_inputs_default_sink_only(self) -> None:
        """None means 'don't move any inputs' at the build layer —
        list_sink_inputs() is a higher layer's responsibility."""
        cmds = build_switch_commands("alsa_output.s4", sink_input_ids=None)
        assert cmds == [["pactl", "set-default-sink", "alsa_output.s4"]]

    def test_multiple_inputs_move_each(self) -> None:
        cmds = build_switch_commands("alsa_output.ryzen", sink_input_ids=["101", "102", "103"])
        assert cmds == [
            ["pactl", "set-default-sink", "alsa_output.ryzen"],
            ["pactl", "move-sink-input", "101", "alsa_output.ryzen"],
            ["pactl", "move-sink-input", "102", "alsa_output.ryzen"],
            ["pactl", "move-sink-input", "103", "alsa_output.ryzen"],
        ]

    def test_int_ids_coerced_to_string(self) -> None:
        """list_sink_inputs returns strings; callers might pass ints."""
        cmds = build_switch_commands(
            "s4",
            sink_input_ids=[101, 102],  # type: ignore[list-item]
        )
        assert cmds[1] == ["pactl", "move-sink-input", "101", "s4"]
        assert cmds[2] == ["pactl", "move-sink-input", "102", "s4"]


class TestListSinkInputs:
    def test_parses_pactl_short_output(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "101\tPipeWire\tFirefox\n102\tPipeWire\tOBS\n103\tPipeWire\tKokoro\n"
        with patch("shared.audio_route_switcher.subprocess.run", return_value=mock_result):
            ids = list_sink_inputs()
        assert ids == ["101", "102", "103"]

    def test_empty_output(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch("shared.audio_route_switcher.subprocess.run", return_value=mock_result):
            assert list_sink_inputs() == []

    def test_tolerates_missing_pactl(self) -> None:
        """FileNotFoundError (pactl absent) returns empty list, doesn't raise."""
        with patch(
            "shared.audio_route_switcher.subprocess.run",
            side_effect=FileNotFoundError(),
        ):
            assert list_sink_inputs() == []

    def test_tolerates_nonzero_exit(self) -> None:
        with patch(
            "shared.audio_route_switcher.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "pactl"),
        ):
            assert list_sink_inputs() == []


class TestApplySwitch:
    def test_dry_run_executes_nothing(self) -> None:
        with patch("shared.audio_route_switcher.subprocess.run") as mock_run:
            results = apply_switch("s4", sink_input_ids=["101"], dry_run=True)
        assert results == []
        mock_run.assert_not_called()

    def test_executes_all_commands(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch(
            "shared.audio_route_switcher.subprocess.run", return_value=mock_result
        ) as mock_run:
            results = apply_switch("s4", sink_input_ids=["101", "102"])
        # Expect set-default-sink + 2 move-sink-input.
        assert len(results) == 3
        assert mock_run.call_count == 3

    def test_propagates_called_process_error(self) -> None:
        with patch(
            "shared.audio_route_switcher.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "pactl"),
        ):
            with pytest.raises(subprocess.CalledProcessError):
                apply_switch("s4", sink_input_ids=["101"])

    def test_auto_lists_inputs_when_none(self) -> None:
        """apply_switch with sink_input_ids=None queries list_sink_inputs."""
        mock_list = MagicMock()
        mock_list.stdout = "200\tx\ty\n201\ta\tb\n"
        # First call: list_sink_inputs. Remainder: switch commands.
        mock_run_call = MagicMock()
        mock_run_call.returncode = 0
        with patch(
            "shared.audio_route_switcher.subprocess.run",
            side_effect=[mock_list, mock_run_call, mock_run_call, mock_run_call],
        ) as mock_run:
            apply_switch("s4")
        # 1 list + 1 default-sink + 2 move-sink-input.
        assert mock_run.call_count == 4
