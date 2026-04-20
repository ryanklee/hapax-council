"""End-to-end tests for the hapax-audio-topology CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

CLI_PATH = Path(__file__).resolve().parents[2] / "scripts" / "hapax-audio-topology"


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI_PATH), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
    )


def _write_yaml(tmp: Path, body: str) -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / "topo.yaml"
    path.write_text(dedent(body).strip() + "\n")
    return path


@pytest.fixture
def basic_yaml(tmp_path: Path) -> Path:
    return _write_yaml(
        tmp_path,
        """
        schema_version: 1
        description: cli smoketest
        nodes:
          - id: l6-capture
            kind: alsa_source
            pipewire_name: alsa_input.usb-ZOOM_L6-00
            hw: hw:L6,0
          - id: livestream-tap
            kind: tap
            pipewire_name: hapax-livestream-tap
        edges:
          - source: l6-capture
            target: livestream-tap
        """,
    )


class TestDescribe:
    def test_prints_node_and_edge_counts(self, basic_yaml: Path) -> None:
        result = _run(["describe", str(basic_yaml)])
        assert result.returncode == 0
        assert "nodes (2)" in result.stdout
        assert "edges (1)" in result.stdout
        assert "l6-capture" in result.stdout
        assert "livestream-tap" in result.stdout

    def test_missing_file_exits_1(self, tmp_path: Path) -> None:
        result = _run(["describe", str(tmp_path / "does-not-exist.yaml")])
        assert result.returncode == 1
        assert "not found" in result.stderr


class TestGenerate:
    def test_generate_stdout(self, basic_yaml: Path) -> None:
        result = _run(["generate", str(basic_yaml)])
        assert result.returncode == 0
        assert "pipewire/l6-capture.conf" in result.stdout
        assert "pipewire/livestream-tap.conf" in result.stdout
        assert "factory.name = api.alsa.pcm.source" in result.stdout
        assert "support.null-audio-sink" in result.stdout

    def test_generate_output_dir(self, basic_yaml: Path, tmp_path: Path) -> None:
        outdir = tmp_path / "out"
        result = _run(["generate", str(basic_yaml), "--output-dir", str(outdir)])
        assert result.returncode == 0
        assert (outdir / "pipewire" / "l6-capture.conf").exists()
        assert (outdir / "pipewire" / "livestream-tap.conf").exists()
        # Content matches template.
        conf = (outdir / "pipewire" / "l6-capture.conf").read_text()
        assert "api.alsa.pcm.source" in conf
        assert 'api.alsa.path = "hw:L6,0"' in conf


class TestDiff:
    def test_match_exits_0(self, basic_yaml: Path, tmp_path: Path) -> None:
        dup = tmp_path / "dup.yaml"
        dup.write_text(basic_yaml.read_text())
        result = _run(["diff", str(basic_yaml), str(dup)])
        assert result.returncode == 0
        assert "match" in result.stdout

    def test_added_node_exits_2(self, basic_yaml: Path, tmp_path: Path) -> None:
        augmented = _write_yaml(
            tmp_path / "aug",
            """
            schema_version: 1
            description: added voice-fx
            nodes:
              - id: l6-capture
                kind: alsa_source
                pipewire_name: alsa_input.usb-ZOOM_L6-00
                hw: hw:L6,0
              - id: livestream-tap
                kind: tap
                pipewire_name: hapax-livestream-tap
              - id: voice-fx
                kind: filter_chain
                pipewire_name: hapax-voice-fx-capture
                target_object: alsa_output.pci-0000_73_00.6.analog-stereo
            edges:
              - source: l6-capture
                target: livestream-tap
            """,
        )
        result = _run(["diff", str(basic_yaml), str(augmented)])
        assert result.returncode == 2
        assert "added nodes" in result.stdout
        assert "voice-fx" in result.stdout

    def test_changed_gain_shift(self, basic_yaml: Path, tmp_path: Path) -> None:
        # Build two descriptors that differ only by edge gain.
        a = _write_yaml(
            tmp_path / "a",
            """
            schema_version: 1
            nodes:
              - id: src
                kind: alsa_source
                pipewire_name: in
                hw: hw:0,0
              - id: sink
                kind: tap
                pipewire_name: tap
            edges:
              - source: src
                target: sink
                makeup_gain_db: 6.0
            """,
        )
        b = _write_yaml(
            tmp_path / "b",
            """
            schema_version: 1
            nodes:
              - id: src
                kind: alsa_source
                pipewire_name: in
                hw: hw:0,0
              - id: sink
                kind: tap
                pipewire_name: tap
            edges:
              - source: src
                target: sink
                makeup_gain_db: 12.0
            """,
        )
        result = _run(["diff", str(a), str(b)])
        assert result.returncode == 2
        assert "changed edges" in result.stdout
        assert "+6.0 dB → +12.0 dB" in result.stdout

    def test_removed_node(self, basic_yaml: Path, tmp_path: Path) -> None:
        stripped = _write_yaml(
            tmp_path / "stripped",
            """
            schema_version: 1
            nodes:
              - id: l6-capture
                kind: alsa_source
                pipewire_name: alsa_input.usb-ZOOM_L6-00
                hw: hw:L6,0
            """,
        )
        result = _run(["diff", str(basic_yaml), str(stripped)])
        assert result.returncode == 2
        assert "removed nodes" in result.stdout
        assert "livestream-tap" in result.stdout


class TestInvalidDescriptor:
    def test_dangling_edge_exits_1(self, tmp_path: Path) -> None:
        bad = _write_yaml(
            tmp_path,
            """
            schema_version: 1
            nodes:
              - id: a
                kind: tap
                pipewire_name: a
            edges:
              - source: nonexistent
                target: a
            """,
        )
        result = _run(["describe", str(bad)])
        assert result.returncode == 1
        assert "source not in" in result.stderr
