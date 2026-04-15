"""Tests for scripts/phase-5-pre-swap-check.py — LRR Phase 5 prerequisites.

The 8 checks are tested individually with synthetic filesystem state
in tmp_path. The systemctl checks (2 + 3) require mocking subprocess
because they shell out to `systemctl --user show`. Happy path +
failure modes for each.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "phase-5-pre-swap-check.py"
_spec = importlib.util.spec_from_file_location("phase_5_pre_swap_check", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
pre_swap_check = importlib.util.module_from_spec(_spec)
sys.modules["phase_5_pre_swap_check"] = pre_swap_check
_spec.loader.exec_module(pre_swap_check)  # type: ignore[union-attr]


def _make_locked_condition_dir(
    registry_dir: Path, condition_id: str, *, halted: bool = True
) -> Path:
    """Create a synthetic locked condition directory with the 3 artifacts."""
    cond_dir = registry_dir / condition_id
    cond_dir.mkdir(parents=True)
    (cond_dir / "data-checksums.txt").write_text("sha256  /path/x\n")
    (cond_dir / "qdrant-snapshot.tgz").write_bytes(b"fake-tarball")
    (cond_dir / "langfuse-scores.jsonl").write_text('{"id":"s1"}\n')
    halt_value = "2026-04-14T20:30:00+00:00" if halted else "null"
    (cond_dir / "condition.yaml").write_text(
        f"condition_id: {condition_id}\n"
        f"collection_halt_at: {halt_value}\n"
        f"frozen_files:\n  - foo.py\n"
    )
    return cond_dir


class TestCheckPhase4DataLock:
    def test_all_artifacts_present(self, tmp_path: Path) -> None:
        _make_locked_condition_dir(tmp_path, "cond-x")
        ok, msg = pre_swap_check.check_phase_4_data_lock("cond-x", tmp_path)
        assert ok is True
        assert "complete" in msg.lower()

    def test_missing_condition_dir(self, tmp_path: Path) -> None:
        ok, msg = pre_swap_check.check_phase_4_data_lock("cond-x", tmp_path)
        assert ok is False
        assert "condition directory missing" in msg

    def test_missing_qdrant_snapshot(self, tmp_path: Path) -> None:
        cond_dir = tmp_path / "cond-x"
        cond_dir.mkdir()
        (cond_dir / "data-checksums.txt").write_text("x")
        (cond_dir / "langfuse-scores.jsonl").write_text("y")
        # Qdrant snapshot missing
        ok, msg = pre_swap_check.check_phase_4_data_lock("cond-x", tmp_path)
        assert ok is False
        assert "qdrant-snapshot.tgz" in msg

    def test_missing_langfuse_export(self, tmp_path: Path) -> None:
        cond_dir = tmp_path / "cond-x"
        cond_dir.mkdir()
        (cond_dir / "data-checksums.txt").write_text("x")
        (cond_dir / "qdrant-snapshot.tgz").write_bytes(b"y")
        ok, msg = pre_swap_check.check_phase_4_data_lock("cond-x", tmp_path)
        assert ok is False
        assert "langfuse-scores.jsonl" in msg


class TestCheckSystemctlEnvironment:
    def test_happy_path(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="Environment=CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=0,1\n",
                stderr="",
            )
            ok, msg = pre_swap_check.check_systemctl_environment(
                "tabbyapi",
                {"CUDA_DEVICE_ORDER": "PCI_BUS_ID", "CUDA_VISIBLE_DEVICES": "0,1"},
            )
        assert ok is True
        assert "env OK" in msg

    def test_missing_env_var(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="Environment=CUDA_DEVICE_ORDER=PCI_BUS_ID\n",
                stderr="",
            )
            ok, msg = pre_swap_check.check_systemctl_environment(
                "tabbyapi",
                {"CUDA_DEVICE_ORDER": "PCI_BUS_ID", "CUDA_VISIBLE_DEVICES": "0,1"},
            )
        assert ok is False
        assert "CUDA_VISIBLE_DEVICES=<missing>" in msg

    def test_wrong_env_value(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="Environment=CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=1\n",
                stderr="",
            )
            ok, msg = pre_swap_check.check_systemctl_environment(
                "tabbyapi",
                {"CUDA_DEVICE_ORDER": "PCI_BUS_ID", "CUDA_VISIBLE_DEVICES": "0,1"},
            )
        assert ok is False
        assert "CUDA_VISIBLE_DEVICES=1" in msg

    def test_systemctl_nonzero_exit(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="Unit tabbyapi not found"
            )
            ok, msg = pre_swap_check.check_systemctl_environment(
                "tabbyapi", {"CUDA_DEVICE_ORDER": "PCI_BUS_ID"}
            )
        assert ok is False
        assert "systemctl exit" in msg


class TestCheckHermesQuantPresent:
    def test_quant_present(self, tmp_path: Path) -> None:
        models_dir = tmp_path / "models" / "Hermes-3-Llama-3.1-70B-EXL3-3.0bpw"
        models_dir.mkdir(parents=True)
        (models_dir / "config.json").write_text("{}")
        for i in range(1, 5):
            (models_dir / f"model-{i:05d}-of-00004.safetensors").write_bytes(b"x")
        ok, msg = pre_swap_check.check_hermes_quant_present(
            tmp_path, "Hermes-3-Llama-3.1-70B-EXL3-3.0bpw"
        )
        assert ok is True
        assert "4 shards" in msg

    def test_missing_directory(self, tmp_path: Path) -> None:
        ok, msg = pre_swap_check.check_hermes_quant_present(
            tmp_path, "Hermes-3-Llama-3.1-70B-EXL3-3.0bpw"
        )
        assert ok is False
        assert "missing" in msg

    def test_no_shards(self, tmp_path: Path) -> None:
        models_dir = tmp_path / "models" / "Hermes-3-Llama-3.1-70B-EXL3-3.0bpw"
        models_dir.mkdir(parents=True)
        (models_dir / "config.json").write_text("{}")
        # No safetensors shards
        ok, msg = pre_swap_check.check_hermes_quant_present(
            tmp_path, "Hermes-3-Llama-3.1-70B-EXL3-3.0bpw"
        )
        assert ok is False
        assert "no safetensors" in msg

    def test_missing_config(self, tmp_path: Path) -> None:
        models_dir = tmp_path / "models" / "Hermes-3-Llama-3.1-70B-EXL3-3.0bpw"
        models_dir.mkdir(parents=True)
        (models_dir / "model-00001-of-00004.safetensors").write_bytes(b"x")
        ok, msg = pre_swap_check.check_hermes_quant_present(
            tmp_path, "Hermes-3-Llama-3.1-70B-EXL3-3.0bpw"
        )
        assert ok is False
        assert "config.json missing" in msg


class TestCheckHermesConfigStaged:
    def test_staged(self, tmp_path: Path) -> None:
        (tmp_path / "config.yml.hermes-draft").write_text("model_name: hermes")
        ok, msg = pre_swap_check.check_hermes_config_staged(tmp_path)
        assert ok is True
        assert "staged" in msg

    def test_missing(self, tmp_path: Path) -> None:
        ok, msg = pre_swap_check.check_hermes_config_staged(tmp_path)
        assert ok is False
        assert "missing" in msg


class TestCheckDeviation037Draft:
    def test_present(self, tmp_path: Path) -> None:
        dev_dir = tmp_path / "research" / "protocols" / "deviations"
        dev_dir.mkdir(parents=True)
        (dev_dir / "DEVIATION-037.md").write_text("draft content")
        ok, msg = pre_swap_check.check_deviation_037_draft(tmp_path)
        assert ok is True

    def test_missing(self, tmp_path: Path) -> None:
        ok, msg = pre_swap_check.check_deviation_037_draft(tmp_path)
        assert ok is False
        assert "DEVIATION-037 missing" in msg


class TestCheckConditionLocked:
    def test_locked(self, tmp_path: Path) -> None:
        _make_locked_condition_dir(tmp_path, "cond-x", halted=True)
        ok, msg = pre_swap_check.check_condition_locked("cond-x", tmp_path)
        assert ok is True
        assert "2026-04-14" in msg

    def test_halt_unset_null(self, tmp_path: Path) -> None:
        _make_locked_condition_dir(tmp_path, "cond-x", halted=False)
        ok, msg = pre_swap_check.check_condition_locked("cond-x", tmp_path)
        assert ok is False
        assert "empty/null" in msg

    def test_condition_yaml_missing(self, tmp_path: Path) -> None:
        (tmp_path / "cond-x").mkdir()
        ok, msg = pre_swap_check.check_condition_locked("cond-x", tmp_path)
        assert ok is False
        assert "missing" in msg

    def test_halt_field_absent_entirely(self, tmp_path: Path) -> None:
        cond_dir = tmp_path / "cond-x"
        cond_dir.mkdir()
        (cond_dir / "condition.yaml").write_text("condition_id: cond-x\nfrozen_files: []\n")
        ok, msg = pre_swap_check.check_condition_locked("cond-x", tmp_path)
        assert ok is False
        assert "missing collection_halt_at" in msg


class TestRunChecksEndToEnd:
    """Synthetic registry + tabbyapi setup + --skip-systemctl for CI."""

    def _build_minimal_env(self, tmp_path: Path) -> tuple[Path, Path, Path]:
        registry_dir = tmp_path / "registry"
        _make_locked_condition_dir(registry_dir, "cond-phase-a-baseline-qwen-001")

        tabbyapi_dir = tmp_path / "tabbyapi"
        models_dir = tabbyapi_dir / "models" / "Hermes-3-Llama-3.1-70B-EXL3-3.0bpw"
        models_dir.mkdir(parents=True)
        (models_dir / "config.json").write_text("{}")
        for i in range(1, 5):
            (models_dir / f"model-{i:05d}-of-00004.safetensors").write_bytes(b"x")
        (tabbyapi_dir / "config.yml.hermes-draft").write_text("model_name: hermes")

        repo_root = tmp_path / "repo"
        (repo_root / "research" / "protocols" / "deviations").mkdir(parents=True)
        (repo_root / "research" / "protocols" / "deviations" / "DEVIATION-037.md").write_text(
            "draft"
        )
        (repo_root / "agents" / "hapax_daimonion" / "proofs").mkdir(parents=True)
        return registry_dir, tabbyapi_dir, repo_root

    def test_all_checks_pass_with_skip_systemctl(self, tmp_path: Path) -> None:
        registry_dir, tabbyapi_dir, repo_root = self._build_minimal_env(tmp_path)

        # Mock git status to return clean
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            args = pre_swap_check.build_parser().parse_args(
                [
                    "--registry-dir",
                    str(registry_dir),
                    "--tabbyapi-dir",
                    str(tabbyapi_dir),
                    "--repo-root",
                    str(repo_root),
                    "--skip-systemctl",
                ]
            )
            result = pre_swap_check.run_checks(args)

        assert result.ok is True
        assert result.exit_code == 0
        assert "all Phase 5 prereqs met" in result.reason

    def test_missing_phase_4_lock_fails_fast(self, tmp_path: Path) -> None:
        _, tabbyapi_dir, repo_root = self._build_minimal_env(tmp_path)
        empty_registry = tmp_path / "empty-registry"
        empty_registry.mkdir()

        args = pre_swap_check.build_parser().parse_args(
            [
                "--registry-dir",
                str(empty_registry),
                "--tabbyapi-dir",
                str(tabbyapi_dir),
                "--repo-root",
                str(repo_root),
                "--skip-systemctl",
            ]
        )
        result = pre_swap_check.run_checks(args)

        assert result.ok is False
        assert result.exit_code == 2
        assert "condition directory missing" in result.reason

    def test_missing_hermes_quant_fails_with_exit_4(self, tmp_path: Path) -> None:
        registry_dir, _, repo_root = self._build_minimal_env(tmp_path)
        empty_tabbyapi = tmp_path / "empty-tabbyapi"
        empty_tabbyapi.mkdir()

        args = pre_swap_check.build_parser().parse_args(
            [
                "--registry-dir",
                str(registry_dir),
                "--tabbyapi-dir",
                str(empty_tabbyapi),
                "--repo-root",
                str(repo_root),
                "--skip-systemctl",
            ]
        )
        result = pre_swap_check.run_checks(args)

        assert result.ok is False
        assert result.exit_code == 4


class TestBuildParser:
    def test_default_expected_condition(self) -> None:
        args = pre_swap_check.build_parser().parse_args(["--skip-systemctl"])
        assert args.expected_condition == "cond-phase-a-baseline-qwen-001"

    def test_skip_systemctl_flag(self) -> None:
        args = pre_swap_check.build_parser().parse_args(["--skip-systemctl"])
        assert args.skip_systemctl is True

    def test_json_flag(self) -> None:
        args = pre_swap_check.build_parser().parse_args(["--json"])
        assert args.as_json is True
