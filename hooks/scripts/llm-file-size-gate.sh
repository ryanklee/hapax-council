#!/usr/bin/env bash
# llm-file-size-gate.sh — PreToolUse hook (Edit, Write, MultiEdit)
#
# Blocks file writes that would produce a Python file over 300 LOC.
# Forces modular code that fits in LLM context windows.
#
# Exemptions: test files, generated files, vendored shims, non-Python.
set -euo pipefail

input="$(cat)"
tool_name="$(printf '%s' "$input" | jq -r '.tool_name // empty')"

case "$tool_name" in
  Edit|Write|MultiEdit) ;;
  *) exit 0 ;;
esac

file_path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null || true)"
[ -n "$file_path" ] || exit 0

# Only check Python files
case "$file_path" in
  *.py) ;;
  *) exit 0 ;;
esac

# Exempt: test files, generated files, vendored shims, shared/ itself
basename="$(basename "$file_path")"
case "$file_path" in
  */tests/*|*/test_*) exit 0 ;;
  */shared/*) exit 0 ;;
esac
case "$basename" in
  _*.py) exit 0 ;;
  *.generated.py) exit 0 ;;
esac

MAX_LINES=300

if [ "$tool_name" = "Write" ]; then
  # For Write: count lines in new content
  line_count="$(printf '%s' "$input" | jq -r '.tool_input.content // empty' 2>/dev/null | wc -l)"
elif [ "$tool_name" = "Edit" ] || [ "$tool_name" = "MultiEdit" ]; then
  # For Edit: estimate result size
  if [ ! -f "$file_path" ]; then
    # New file via Edit — just check new_string length
    line_count="$(printf '%s' "$input" | jq -r '.tool_input.new_string // empty' 2>/dev/null | wc -l)"
  else
    current_lines="$(wc -l < "$file_path" 2>/dev/null || echo 0)"
    old_lines="$(printf '%s' "$input" | jq -r '.tool_input.old_string // empty' 2>/dev/null | wc -l)"
    new_lines="$(printf '%s' "$input" | jq -r '.tool_input.new_string // empty' 2>/dev/null | wc -l)"
    line_count=$(( current_lines - old_lines + new_lines ))
  fi
fi

if [ "$line_count" -gt "$MAX_LINES" ]; then
  echo "BLOCKED: File would be ${line_count} lines (max ${MAX_LINES}). Split into smaller modules." >&2
  exit 2
fi

exit 0
