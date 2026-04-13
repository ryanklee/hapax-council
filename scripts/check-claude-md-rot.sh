#!/usr/bin/env bash
# check-claude-md-rot — scan CLAUDE.md files for content classes that decay into noise.
#
# Operationalizes the rotation policy from
# docs/superpowers/specs/2026-04-13-claude-md-excellence-design.md.
#
# Forbidden patterns (matches outside of pointer contexts):
#   - "fixed YYYY-MM-DD"        (commit-message content)
#   - "(PR #NNN)" "(beta PR #NNN)" "(alpha PR #NNN)" "(delta PR #NNN)"
#   - "currently (non-functional|broken|disabled)"
#
# Usage:
#   scripts/check-claude-md-rot.sh                 # scan known CLAUDE.md files
#   scripts/check-claude-md-rot.sh path/to/file    # scan one file
#
# Exits non-zero on any match. Intended for ad-hoc audits, not as a hook (yet).

set -euo pipefail

if [[ $# -gt 0 ]]; then
    targets=("$@")
else
    targets=(CLAUDE.md vscode/CLAUDE.md)
fi

found=0
for target in "${targets[@]}"; do
    if [[ ! -f "$target" ]]; then
        continue
    fi

    if grep -nIE 'fixed 20[0-9]{2}-[0-9]{2}-[0-9]{2}' "$target"; then
        found=1
    fi
    if grep -nIE '\((alpha |beta |delta )?PR #[0-9]+\)' "$target"; then
        found=1
    fi
    if grep -nIE 'currently (non-functional|broken|disabled)' "$target"; then
        found=1
    fi
done

if [[ $found -ne 0 ]]; then
    echo
    echo "CLAUDE.md rotation policy violations found." >&2
    echo "See docs/superpowers/specs/2026-04-13-claude-md-excellence-design.md" >&2
    exit 1
fi
