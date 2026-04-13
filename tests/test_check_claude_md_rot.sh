#!/usr/bin/env bash
# Smoke tests for scripts/check-claude-md-rot.sh.
#
# Run from the council repo root:  bash tests/test_check_claude_md_rot.sh
#
# Each test sets up a fixture in $TMPDIR and asserts the script's exit code +
# matched/unmatched output. Tests are independent; failures don't short-circuit.

set -uo pipefail

SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/scripts/check-claude-md-rot.sh"
[[ -x "$SCRIPT" ]] || { echo "FAIL: script not executable: $SCRIPT"; exit 1; }

passes=0
fails=0
tmproot=$(mktemp -d)
trap 'rm -rf "$tmproot"' EXIT

assert() {
    local name=$1 expected=$2 actual=$3
    if [[ "$expected" == "$actual" ]]; then
        printf 'PASS: %s\n' "$name"
        passes=$((passes + 1))
    else
        printf 'FAIL: %s — expected %s, got %s\n' "$name" "$expected" "$actual"
        fails=$((fails + 1))
    fi
}

run() {
    local fixture=$1 mode=$2
    local rc
    if [[ -n "$mode" ]]; then
        "$SCRIPT" "$mode" "$fixture" >/dev/null 2>&1; rc=$?
    else
        "$SCRIPT" "$fixture" >/dev/null 2>&1; rc=$?
    fi
    echo $rc
}

# --- fixture 1: clean file, no rot ---
clean_file=$(mktemp -p "$tmproot" CLAUDE.md.XXXXXX)
cat > "$clean_file" <<'EOF'
# Clean

This file has no rot patterns. Architecture, build commands, invariants.
See docs/foo.md for the design.
EOF
assert "clean file exits 0" 0 "$(run "$clean_file" '')"

# --- fixture 2: fix-date pattern ---
fix_file=$(mktemp -p "$tmproot" CLAUDE.md.XXXXXX)
cat > "$fix_file" <<'EOF'
# Has rot

Director loop bootstrap (fixed 2026-04-12): we now write a marker file.
EOF
assert "fix-date pattern exits 1" 1 "$(run "$fix_file" '')"

# --- fixture 3: PR fingerprint ---
pr_file=$(mktemp -p "$tmproot" CLAUDE.md.XXXXXX)
cat > "$pr_file" <<'EOF'
# Has rot

The bridge was repaired (PR #696 + #700) and now writes both paths.
EOF
assert "PR fingerprint exits 1" 1 "$(run "$pr_file" '')"

# --- fixture 4: beta PR fingerprint ---
beta_file=$(mktemp -p "$tmproot" CLAUDE.md.XXXXXX)
cat > "$beta_file" <<'EOF'
# Has rot

Cursor persistence shipped (beta PR #705).
EOF
assert "beta-PR fingerprint exits 1" 1 "$(run "$beta_file" '')"

# --- fixture 5: currently broken claim ---
broken_file=$(mktemp -p "$tmproot" CLAUDE.md.XXXXXX)
cat > "$broken_file" <<'EOF'
# Has rot

Person detection currently non-functional — retraining planned.
EOF
assert "currently-broken exits 1" 1 "$(run "$broken_file" '')"

# --- fixture 6: in-flight admission ---
inflight_file=$(mktemp -p "$tmproot" CLAUDE.md.XXXXXX)
cat > "$inflight_file" <<'EOF'
# Has rot

Battery percentage not yet captured — TODO exists in HapaxTransport.kt.
EOF
assert "in-flight not-yet exits 1" 1 "$(run "$inflight_file" '')"

# --- fixture 7: TODO marker — only fails in strict mode ---
todo_file=$(mktemp -p "$tmproot" CLAUDE.md.XXXXXX)
cat > "$todo_file" <<'EOF'
# Has rot in strict mode only

The audit revealed a TODO comment in the test runner.
EOF
assert "TODO non-strict exits 0" 0 "$(run "$todo_file" '')"
assert "TODO strict exits 1"     1 "$(run "$todo_file" '--strict')"

# --- fixture 8: missing explicit target — typo guard ---
assert "missing target exits 2" 2 "$(run "$tmproot/no-such-file" '')"

# --- summary ---
echo
printf 'tests: %d passed, %d failed\n' "$passes" "$fails"
[[ $fails -eq 0 ]]
