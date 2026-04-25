#!/usr/bin/env python3
"""Validate the Claim/LR registry consistency — HPX003 + HPX004 enforcement.

CI + pre-commit gate per docs/operations/2026-04-24-workstream-realignment-v3.md
§7 gates 11+12 (Phase-0-FULL-enabled).

Checks:

* HPX003: every signal listed under a claim in `shared/lr_registry.yaml`
  validates against the `LRDerivation` Pydantic schema.
* HPX003-AST (audit-incorporated v4 follow-up): every Python module under
  `agents/` declaring a `DEFAULT_SIGNAL_WEIGHTS: dict[str, ...]`
  module-level annotated assignment must have each of its keys present
  in `shared/lr_registry.yaml`. Closes the bypass that let Phase 6c-i.A
  and Phase 6d-i.A ship with inline LR weights bypassing the registry.
* HPX004: every claim referenced in `lr_registry.yaml` has a matching
  entry in `shared/prior_provenance.yaml`, validated against the
  `PriorProvenance` schema.

Operator directive (verbatim 2026-04-24T22:40Z):
    "Lack of priors is itself a prior and we must somehow ensure that
     priors are not generated adhoc but derivations of invariants that
     won't keep us guessing."

Exit codes:
  0 — all checks pass
  1 — at least one violation
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
LR_REGISTRY = REPO_ROOT / "shared" / "lr_registry.yaml"
PRIOR_PROVENANCE = REPO_ROOT / "shared" / "prior_provenance.yaml"
AGENTS_DIR = REPO_ROOT / "agents"


def fail(msg: str) -> None:
    print(f"VIOLATION: {msg}", file=sys.stderr)


def _extract_default_signal_weights_keys(py_path: Path) -> list[str] | None:
    """Return the keys of a module-level `DEFAULT_SIGNAL_WEIGHTS: dict[...]`
    annotated assignment, or None if the module has no such symbol.

    Handles only literal-key dicts (string constants). Computed keys are
    skipped (returned as the literal string ``<computed>``) so a violation
    surfaces at registry-lookup time rather than silently accepting.
    """
    try:
        tree = ast.parse(py_path.read_text(), filename=str(py_path))
    except (SyntaxError, UnicodeDecodeError):
        return None
    for node in tree.body:
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        if node.target.id != "DEFAULT_SIGNAL_WEIGHTS":
            continue
        if not isinstance(node.value, ast.Dict):
            return []
        keys: list[str] = []
        for key_node in node.value.keys:
            if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                keys.append(key_node.value)
            else:
                keys.append("<computed>")
        return keys
    return None


def _collect_registry_signal_names(lr_data: dict) -> set[str]:
    names: set[str] = set()
    for signals in lr_data.values():
        if isinstance(signals, dict):
            names.update(signals.keys())
    return names


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    from shared.claim import LRDerivation, PriorProvenance

    violations = 0

    # HPX003 — all LRDerivation entries validate
    if not LR_REGISTRY.exists():
        fail(f"HPX003: {LR_REGISTRY} missing")
        return 1
    lr_data = yaml.safe_load(LR_REGISTRY.read_text()) or {}
    claim_names_in_lr: set[str] = set()
    signal_count = 0
    for block_key, signals in lr_data.items():
        if not isinstance(signals, dict):
            continue
        for sig_name, fields in signals.items():
            if not isinstance(fields, dict):
                continue
            try:
                rec = LRDerivation(signal_name=sig_name, **fields)
            except Exception as e:
                fail(f"HPX003: {block_key}.{sig_name} fails LRDerivation validation: {e}")
                violations += 1
                continue
            claim_names_in_lr.add(rec.claim_name)
            signal_count += 1

    # HPX003-AST — every DEFAULT_SIGNAL_WEIGHTS literal in agents/**/*.py
    # must have keys covered by the registry.
    registry_signals = _collect_registry_signal_names(lr_data)
    ast_modules_checked = 0
    if AGENTS_DIR.exists():
        for py_path in sorted(AGENTS_DIR.rglob("*.py")):
            keys = _extract_default_signal_weights_keys(py_path)
            if keys is None:
                continue
            ast_modules_checked += 1
            rel_path = py_path.relative_to(REPO_ROOT)
            for key in keys:
                if key == "<computed>":
                    fail(
                        f"HPX003-AST: {rel_path} has DEFAULT_SIGNAL_WEIGHTS with a non-literal "
                        f"key — registry coverage cannot be statically verified. Either inline "
                        f"the signal name as a string literal or move the dict construction "
                        f"into a place HPX003-AST can audit."
                    )
                    violations += 1
                    continue
                if key not in registry_signals:
                    fail(
                        f"HPX003-AST: {rel_path} declares DEFAULT_SIGNAL_WEIGHTS[{key!r}] "
                        f"but {key!r} is absent from shared/lr_registry.yaml. Add it under "
                        f"the appropriate claim's signal block (e.g. system_degraded_signals)."
                    )
                    violations += 1

    # HPX004 — every claim referenced in LR registry has prior_provenance entry
    if not PRIOR_PROVENANCE.exists():
        fail(f"HPX004: {PRIOR_PROVENANCE} missing")
        return 1
    pp_data = yaml.safe_load(PRIOR_PROVENANCE.read_text()) or {}

    for claim_name, fields in pp_data.items():
        if not isinstance(fields, dict):
            continue
        try:
            PriorProvenance(**fields)
        except Exception as e:
            fail(f"HPX004: prior_provenance[{claim_name}] fails PriorProvenance validation: {e}")
            violations += 1

    missing = claim_names_in_lr - set(pp_data.keys())
    for claim_name in sorted(missing):
        fail(
            f"HPX004: claim {claim_name!r} appears in lr_registry.yaml but has no entry "
            f"in prior_provenance.yaml. Operator directive: 'priors are not generated "
            f"adhoc but derivations of invariants'."
        )
        violations += 1

    if violations == 0:
        print(
            f"check-claim-registry: HPX003 + HPX004 OK "
            f"({len(claim_names_in_lr)} claim(s), {signal_count} signal(s) validated, "
            f"{ast_modules_checked} module(s) AST-walked)"
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
