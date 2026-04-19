"""Tests for ``scripts/run-phase-10-rehearsal.sh`` (HOMAGE Phase 10 rehearsal).

Phase C4 of the homage-completion-plan. The script walks the auto-checkable
items in ``docs/runbooks/homage-phase-10-rehearsal.md``. We exercise it with
shim binaries for ``systemctl``, ``curl`` and ``uv`` plus a synthetic
``/dev/shm`` and ``~/hapax-state`` tree under pytest's ``tmp_path``, so the
tests do not depend on a running compositor or systemd.
"""

from __future__ import annotations

import os
import stat
import subprocess
import time
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run-phase-10-rehearsal.sh"
REPO_DIR = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Shim helpers — tiny executables the script calls in place of real binaries.
# ---------------------------------------------------------------------------


def _write_exec(path: Path, body: str) -> Path:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _fake_systemctl(tmp_path: Path, *, active: bool = True) -> Path:
    status = "active" if active else "inactive"
    return _write_exec(
        tmp_path / "systemctl",
        "#!/usr/bin/env bash\n"
        'for arg in "$@"; do\n'
        '  if [[ "$arg" == "is-active" ]]; then\n'
        f'    echo "{status}"\n'
        "    exit 0\n"
        "  fi\n"
        "done\n"
        "exit 0\n",
    )


def _fake_curl(tmp_path: Path, *, body: str, succeed: bool = True) -> Path:
    exit_line = "" if succeed else "exit 7\n"
    payload_path = tmp_path / "curl-body.txt"
    payload_path.write_text(body)
    return _write_exec(
        tmp_path / "curl",
        f'#!/usr/bin/env bash\n{exit_line}cat "{payload_path}"\n',
    )


def _fake_uv(tmp_path: Path, *, registry_count: int = 16, font_ok: bool = True) -> Path:
    """Shim for ``uv run python -c '<snippet>' [argv...]``.

    Inspects the -c snippet via a substring check and emits the response
    for each of the three call sites in the script.
    """
    font_rc = 0 if font_ok else 1
    script_body = f"""#!/usr/bin/env bash
if [[ "${{1:-}}" != "run" || "${{2:-}}" != "python" || "${{3:-}}" != "-c" ]]; then
  exit 64
fi
snippet="${{4:-}}"
shift 4

if [[ "$snippet" == *"json.loads(open(sys.argv[1]).read())"* ]]; then
  exec python3 -c "$snippet" "$@"
fi

if [[ "$snippet" == *"cairo_sources import list_classes"* ]]; then
  echo "{registry_count}"
  exit 0
fi

if [[ "$snippet" == *"text_render import has_font"* ]]; then
  exit {font_rc}
fi

echo "uv shim: unexpected snippet: $snippet" >&2
exit 99
"""
    return _write_exec(tmp_path / "uv", script_body)


# ---------------------------------------------------------------------------
# Filesystem fixture helpers.
# ---------------------------------------------------------------------------


_SHM_FILES = (
    "hapax-compositor/homage-substrate-package.json",
    "hapax-compositor/ward-properties.json",
    "hapax-compositor/research-marker.json",
    "hapax-director/narrative-structural-intent.json",
)


def _populate_shm(shm_root: Path, *, fresh: bool = True) -> None:
    for rel in _SHM_FILES:
        path = shm_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")
        if not fresh:
            old = time.time() - 24 * 3600
            os.utime(path, (old, old))


def _write_condition(state_dir: Path, *, closed: bool = False) -> Path:
    cond_dir = state_dir / "research-registry" / "cond-phase-a-homage-active-001"
    cond_dir.mkdir(parents=True, exist_ok=True)
    closed_val = "'2026-04-20T00:00:00Z'" if closed else "null"
    (cond_dir / "condition.yaml").write_text(
        "condition_id: cond-phase-a-homage-active-001\n"
        "claim_id: claim-phase-a-homage-active\n"
        "opened_at: '2026-04-19T06:47:48.326535Z'\n"
        f"closed_at: {closed_val}\n"
    )
    return cond_dir / "condition.yaml"


_HOMAGE_METRICS = """# HELP hapax_homage_transition_total Transitions.
# TYPE hapax_homage_transition_total counter
hapax_homage_transition_total{package="bitchx"} 12
hapax_homage_violation_total 0
hapax_homage_package_active{package="bitchx"} 1
hapax_homage_render_cadence_hz 30
hapax_homage_rotation_mode{mode="steady"} 1
hapax_homage_active_package{package="bitchx"} 1
hapax_homage_substrate_saturation_target 0.6
"""


# ---------------------------------------------------------------------------
# Test runner.
# ---------------------------------------------------------------------------


def _run(
    tmp_path: Path,
    *,
    systemctl: Path,
    curl: Path,
    uv: Path,
    shm_dir: Path,
    state_dir: Path,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "HOMAGE_REHEARSAL_SYSTEMCTL": str(systemctl),
            "HOMAGE_REHEARSAL_CURL": str(curl),
            "HOMAGE_REHEARSAL_UV": str(uv),
            "HOMAGE_REHEARSAL_METRICS_URL": "http://127.0.0.1:9482/metrics",
            "HOMAGE_REHEARSAL_SHM_DIR": str(shm_dir),
            "HOMAGE_REHEARSAL_STATE_DIR": str(state_dir),
            "HOMAGE_REHEARSAL_REPO_DIR": str(REPO_DIR),
            "HOMAGE_REHEARSAL_FRESHNESS_S": "900",
            "HOMAGE_REHEARSAL_HOMAGE_METRICS_MIN": "6",
            "HOMAGE_REHEARSAL_REGISTRY_MIN": "16",
            "HOME": str(tmp_path),
        }
    )
    return subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _baseline_state(tmp_path: Path) -> dict[str, Path]:
    shm = tmp_path / "shm"
    shm.mkdir()
    _populate_shm(shm, fresh=True)
    state = tmp_path / "hapax-state"
    state.mkdir()
    _write_condition(state, closed=False)
    return {
        "systemctl": _fake_systemctl(tmp_path, active=True),
        "curl": _fake_curl(tmp_path, body=_HOMAGE_METRICS, succeed=True),
        "uv": _fake_uv(tmp_path, registry_count=16, font_ok=True),
        "shm_dir": shm,
        "state_dir": state,
    }


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


def test_all_preconditions_met_exits_zero(tmp_path: Path) -> None:
    state = _baseline_state(tmp_path)
    result = _run(tmp_path, **state)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "[PASS] studio-compositor.service is-active" in result.stdout
    assert "[PASS] layout default.json parses as JSON" in result.stdout
    assert "[PASS] layout consent-safe.json parses as JSON" in result.stdout
    assert "[PASS] cairo_sources.list_classes() returned 16" in result.stdout
    assert "[PASS] Px437 IBM VGA 8x16 resolvable via Pango" in result.stdout
    assert (
        "[PASS] hapax_homage_* metric lines: 6" in result.stdout
        or "[PASS] hapax_homage_* metric lines: 7" in result.stdout
    )
    assert "[PASS] condition YAML exists and status is open" in result.stdout
    assert "[OPERATOR VERIFY]" in result.stdout
    assert "[FAIL]" not in result.stdout


def test_missing_condition_yaml_exits_nonzero(tmp_path: Path) -> None:
    state = _baseline_state(tmp_path)
    cond_path = (
        state["state_dir"]
        / "research-registry"
        / "cond-phase-a-homage-active-001"
        / "condition.yaml"
    )
    cond_path.unlink()
    result = _run(tmp_path, **state)
    assert result.returncode == 1, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "[FAIL] condition YAML not found" in result.stdout
    assert str(cond_path) in result.stdout


def test_metrics_scrape_failure_exits_nonzero(tmp_path: Path) -> None:
    state = _baseline_state(tmp_path)
    state["curl"] = _fake_curl(tmp_path, body="", succeed=False)
    result = _run(tmp_path, **state)
    assert result.returncode == 1, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "[FAIL] Prometheus scrape failed or empty" in result.stdout


def test_metrics_below_threshold_exits_nonzero(tmp_path: Path) -> None:
    state = _baseline_state(tmp_path)
    state["curl"] = _fake_curl(
        tmp_path,
        body=(
            "# HELP hapax_homage_transition_total Transitions.\n"
            "hapax_homage_transition_total 1\n"
            "hapax_homage_violation_total 0\n"
            "hapax_homage_package_active 1\n"
        ),
        succeed=True,
    )
    result = _run(tmp_path, **state)
    assert result.returncode == 1
    assert "[FAIL] hapax_homage_* metric lines: 3" in result.stdout


def test_service_inactive_exits_nonzero(tmp_path: Path) -> None:
    state = _baseline_state(tmp_path)
    state["systemctl"] = _fake_systemctl(tmp_path, active=False)
    result = _run(tmp_path, **state)
    assert result.returncode == 1
    assert "[FAIL] studio-compositor.service is-active returned 'inactive'" in result.stdout


def test_stale_shm_files_fail(tmp_path: Path) -> None:
    state = _baseline_state(tmp_path)
    _populate_shm(state["shm_dir"], fresh=False)
    result = _run(tmp_path, **state)
    assert result.returncode == 1
    assert "[FAIL] /dev/shm file stale" in result.stdout


def test_registry_too_small_fails(tmp_path: Path) -> None:
    state = _baseline_state(tmp_path)
    state["uv"] = _fake_uv(tmp_path, registry_count=5, font_ok=True)
    result = _run(tmp_path, **state)
    assert result.returncode == 1
    assert "[FAIL] cairo_sources.list_classes() returned '5'" in result.stdout


def test_missing_font_fails(tmp_path: Path) -> None:
    state = _baseline_state(tmp_path)
    state["uv"] = _fake_uv(tmp_path, registry_count=16, font_ok=False)
    result = _run(tmp_path, **state)
    assert result.returncode == 1
    assert "[FAIL] Px437 IBM VGA 8x16 NOT resolvable" in result.stdout


def test_report_file_written(tmp_path: Path) -> None:
    state = _baseline_state(tmp_path)
    result = _run(tmp_path, **state)
    assert result.returncode == 0
    reports = list((state["state_dir"] / "rehearsal").glob("phase-10-*.txt"))
    assert len(reports) == 1, f"expected exactly one report, got {reports}"
    body = reports[0].read_text()
    assert "[PASS] studio-compositor.service is-active" in body
    assert "[OPERATOR VERIFY]" in body


def test_idempotent_second_run_produces_distinct_report(tmp_path: Path) -> None:
    state = _baseline_state(tmp_path)
    first = _run(tmp_path, **state)
    assert first.returncode == 0
    time.sleep(1.05)
    second = _run(tmp_path, **state)
    assert second.returncode == 0
    reports = sorted((state["state_dir"] / "rehearsal").glob("phase-10-*.txt"))
    assert len(reports) == 2, f"idempotent re-run should add a report, got {reports}"


@pytest.mark.parametrize(
    "missing_file",
    [
        "hapax-compositor/homage-substrate-package.json",
        "hapax-compositor/ward-properties.json",
        "hapax-compositor/research-marker.json",
        "hapax-director/narrative-structural-intent.json",
    ],
)
def test_any_missing_shm_file_fails(tmp_path: Path, missing_file: str) -> None:
    state = _baseline_state(tmp_path)
    target = state["shm_dir"] / missing_file
    target.unlink()
    fallback = state["shm_dir"] / "hapax-compositor" / Path(missing_file).name
    if fallback.exists() and fallback != target:
        fallback.unlink()
    result = _run(tmp_path, **state)
    assert result.returncode == 1
    assert "[FAIL] /dev/shm file missing" in result.stdout
