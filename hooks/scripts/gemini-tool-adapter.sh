#!/usr/bin/env bash
# gemini-tool-adapter.sh — Translates Gemini CLI BeforeTool/AfterTool JSON
# to Claude Code PreToolUse/PostToolUse format, then delegates to an existing
# Claude Code hook script.
#
# Usage (in ~/.gemini/settings.json):
#   "command": "/path/to/gemini-tool-adapter.sh /path/to/claude-hook.sh"
#
# Translation:
#   tool_name:  run_shell_command→Bash, replace→Edit, write_file→Write, etc.
#   tool_input: field name normalization (old_str→old_string, path→file_path)
#
# Exit codes and stderr pass through unchanged — both protocols use
# exit 0 (allow) and exit 2 + stderr reason (block).
set -euo pipefail

DELEGATE="$1"
[ -x "$DELEGATE" ] || { echo "gemini-tool-adapter: delegate not executable: $DELEGATE" >&2; exit 0; }

INPUT="$(cat)"

TRANSLATED="$(echo "$INPUT" | jq '
  # Save original Gemini tool name for logging
  .original_tool_name = .tool_name |

  # Map Gemini CLI tool names → Claude Code tool names
  .tool_name = (
    if   .tool_name == "run_shell_command" then "Bash"
    elif .tool_name == "replace"           then "Edit"
    elif .tool_name == "write_file"        then "Write"
    elif .tool_name == "read_file"         then "Read"
    elif .tool_name == "read_many_files"   then "Read"
    elif .tool_name == "glob"              then "Glob"
    elif .tool_name == "grep_search"       then "Grep"
    elif .tool_name == "google_web_search" then "WebSearch"
    elif .tool_name == "web_fetch"         then "WebFetch"
    elif .tool_name == "activate_skill"    then "Skill"
    elif .tool_name == "write_todos"       then "TaskCreate"
    elif .tool_name == "ask_user"          then "AskUserQuestion"
    else .tool_name
    end
  ) |

  # Normalize tool_input field names for Edit (replace)
  if .tool_name == "Edit" then
    .tool_input = (
      .tool_input //= {} |
      .tool_input |
      (if has("new_str")  and (has("new_string") | not) then .new_string = .new_str  else . end) |
      (if has("old_str")  and (has("old_string") | not) then .old_string = .old_str  else . end) |
      (if has("path")     and (has("file_path")  | not) then .file_path  = .path     else . end)
    )
  # Normalize tool_input field names for Write (write_file)
  elif .tool_name == "Write" then
    .tool_input = (
      .tool_input //= {} |
      .tool_input |
      (if has("path") and (has("file_path") | not) then .file_path = .path else . end)
    )
  else .
  end
' 2>/dev/null)" || { echo "$INPUT" | exec "$DELEGATE"; exit $?; }

echo "$TRANSLATED" | exec "$DELEGATE"
