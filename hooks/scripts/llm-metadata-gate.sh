#!/usr/bin/env bash
# llm-metadata-gate.sh — PostToolUse hook (Write)
#
# Advisory: warns when a new __init__.py is created in agents/ without
# a sibling METADATA.yaml. Always exits 0 (never blocks).
set -euo pipefail

input="$(cat)"
tool_name="$(printf '%s' "$input" | jq -r '.tool_name // empty')"

[ "$tool_name" = "Write" ] || exit 0

file_path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null || true)"
[ -n "$file_path" ] || exit 0

# Only trigger on agents/*/__init__.py
case "$file_path" in
  */agents/*/__init__.py) ;;
  *) exit 0 ;;
esac

dir="$(dirname "$file_path")"
if [ ! -f "${dir}/METADATA.yaml" ]; then
  pkg_name="$(basename "$dir")"
  echo "WARNING: No METADATA.yaml found for agents/${pkg_name}/." >&2
  echo "Generate one: uv run python scripts/llm_metadata_gen.py agents.${pkg_name} --write" >&2
fi

exit 0
