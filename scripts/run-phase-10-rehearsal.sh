#!/usr/bin/env bash
# run-phase-10-rehearsal.sh — HOMAGE Phase 10 rehearsal automation.
#
# Walks the auto-checkable items from
# docs/runbooks/homage-phase-10-rehearsal.md:
#   - compositor service active
#   - layout JSONs parse
#   - cairo_sources registry contents (>=16 classes)
#   - Px437 IBM VGA raster font present
#   - /dev/shm substrate/director/research/ward files present + fresh
#   - Prometheus metrics scrape (hapax_homage_* lines >= 6)
#   - research condition YAML open
#
# Items requiring visual observation are printed as "OPERATOR VERIFY:"
# lines and never auto-pass.
#
# Output: ~/hapax-state/rehearsal/phase-10-<timestamp>.txt with per-line
# [PASS|FAIL|OPERATOR VERIFY] status. Exit code = 0 iff every
# auto-checkable item passes.
#
# Phase C4 of the HOMAGE completion plan.

set -u  # fail on unset vars; do NOT use -e — we want to observe failures

# ---------------------------------------------------------------------------
# Environment overrides (for tests). Default to real values.
# ---------------------------------------------------------------------------
: "${HOMAGE_REHEARSAL_SYSTEMCTL:=systemctl}"
: "${HOMAGE_REHEARSAL_CURL:=curl}"
: "${HOMAGE_REHEARSAL_UV:=uv}"
: "${HOMAGE_REHEARSAL_METRICS_URL:=http://127.0.0.1:9482/metrics}"
: "${HOMAGE_REHEARSAL_SHM_DIR:=/dev/shm}"
: "${HOMAGE_REHEARSAL_STATE_DIR:=${HOME}/hapax-state}"
: "${HOMAGE_REHEARSAL_REPO_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
: "${HOMAGE_REHEARSAL_FRESHNESS_S:=900}"  # 15 min; runbook allows some drift
: "${HOMAGE_REHEARSAL_HOMAGE_METRICS_MIN:=6}"
: "${HOMAGE_REHEARSAL_REGISTRY_MIN:=16}"

REPORT_DIR="${HOMAGE_REHEARSAL_STATE_DIR}/rehearsal"
mkdir -p "${REPORT_DIR}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_PATH="${REPORT_DIR}/phase-10-${TIMESTAMP}.txt"

FAIL_COUNT=0
PASS_COUNT=0

# Shared print helper: appends one line to stdout and the report.
emit() {
    local line="$1"
    printf '%s\n' "${line}"
    printf '%s\n' "${line}" >>"${REPORT_PATH}"
}

pass() {
    emit "[PASS] $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
    emit "[FAIL] $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

section() {
    emit ""
    emit "=== $1 ==="
}

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
emit "HOMAGE Phase 10 Rehearsal — ${TIMESTAMP}"
emit "Repo: ${HOMAGE_REHEARSAL_REPO_DIR}"
emit "Report: ${REPORT_PATH}"

# ---------------------------------------------------------------------------
# §2.1 Compositor service active
# ---------------------------------------------------------------------------
section "§2.1 studio-compositor.service"
_svc_status="$("${HOMAGE_REHEARSAL_SYSTEMCTL}" --user is-active studio-compositor.service 2>/dev/null || true)"
if [[ "${_svc_status}" == "active" ]]; then
    pass "studio-compositor.service is-active (${_svc_status})"
else
    fail "studio-compositor.service is-active returned '${_svc_status}' (expected 'active')"
fi

# ---------------------------------------------------------------------------
# §2.4 Layout JSON validates
# ---------------------------------------------------------------------------
section "§2.4 layout JSON validity"
for _layout in default.json consent-safe.json; do
    _layout_path="${HOMAGE_REHEARSAL_REPO_DIR}/config/compositor-layouts/${_layout}"
    if [[ ! -f "${_layout_path}" ]]; then
        fail "layout ${_layout} not found at ${_layout_path}"
        continue
    fi
    if "${HOMAGE_REHEARSAL_UV}" run python -c "import json,sys; json.loads(open(sys.argv[1]).read())" "${_layout_path}" >/dev/null 2>&1; then
        pass "layout ${_layout} parses as JSON"
    else
        fail "layout ${_layout} does NOT parse as JSON"
    fi
done

# ---------------------------------------------------------------------------
# §2.3 Cairo source registry — >=16 classes
# ---------------------------------------------------------------------------
section "§2.3 cairo_sources registry"
_registry_count="$(cd "${HOMAGE_REHEARSAL_REPO_DIR}" && "${HOMAGE_REHEARSAL_UV}" run python -c \
    "from agents.studio_compositor.cairo_sources import list_classes; print(len(list_classes()))" \
    2>/dev/null || echo 0)"
if [[ "${_registry_count}" =~ ^[0-9]+$ ]] && (( _registry_count >= HOMAGE_REHEARSAL_REGISTRY_MIN )); then
    pass "cairo_sources.list_classes() returned ${_registry_count} (>= ${HOMAGE_REHEARSAL_REGISTRY_MIN})"
else
    fail "cairo_sources.list_classes() returned '${_registry_count}' (need >= ${HOMAGE_REHEARSAL_REGISTRY_MIN})"
fi

# ---------------------------------------------------------------------------
# §2.6 Font availability — Px437 IBM VGA 8x16
# ---------------------------------------------------------------------------
section "§2.6 raster font Px437 IBM VGA 8x16"
if (cd "${HOMAGE_REHEARSAL_REPO_DIR}" && "${HOMAGE_REHEARSAL_UV}" run python -c \
    "from agents.studio_compositor.text_render import has_font; import sys; sys.exit(0 if has_font('Px437 IBM VGA 8x16') else 1)" \
    >/dev/null 2>&1); then
    pass "Px437 IBM VGA 8x16 resolvable via Pango"
else
    fail "Px437 IBM VGA 8x16 NOT resolvable (fontconfig missing the face?)"
fi

# ---------------------------------------------------------------------------
# §2.5 + §3.x — /dev/shm substrate / director / ward / research files
# ---------------------------------------------------------------------------
section "§2.5 + §3.x /dev/shm state files (presence + freshness)"
_shm_items=(
    "hapax-compositor/homage-substrate-package.json:${HOMAGE_REHEARSAL_FRESHNESS_S}"
    "hapax-compositor/ward-properties.json:${HOMAGE_REHEARSAL_FRESHNESS_S}"
    "hapax-compositor/research-marker.json:${HOMAGE_REHEARSAL_FRESHNESS_S}"
    "hapax-director/narrative-structural-intent.json:${HOMAGE_REHEARSAL_FRESHNESS_S}"
)
_now_epoch="$(date +%s)"
for _entry in "${_shm_items[@]}"; do
    _rel="${_entry%%:*}"
    _max_age="${_entry##*:}"
    _candidates=(
        "${HOMAGE_REHEARSAL_SHM_DIR}/${_rel}"
        # structural-intent lives under hapax-compositor in current builds too;
        # accept either location so the check tracks the runbook, not a guess.
        "${HOMAGE_REHEARSAL_SHM_DIR}/hapax-compositor/$(basename "${_rel}")"
    )
    _found=""
    for _cand in "${_candidates[@]}"; do
        if [[ -f "${_cand}" ]]; then
            _found="${_cand}"
            break
        fi
    done
    if [[ -z "${_found}" ]]; then
        fail "/dev/shm file missing: ${_rel}"
        continue
    fi
    _mtime="$(stat -c '%Y' "${_found}" 2>/dev/null || echo 0)"
    _age=$(( _now_epoch - _mtime ))
    if (( _age > _max_age )); then
        fail "/dev/shm file stale: ${_found} (age=${_age}s, max=${_max_age}s)"
    else
        pass "/dev/shm file fresh: ${_found} (age=${_age}s)"
    fi
done

# ---------------------------------------------------------------------------
# §2.7 + §5.2 + §8 Prometheus scrape — hapax_homage_* line count >= 6
# ---------------------------------------------------------------------------
section "§2.7 + §5.2 + §8 Prometheus hapax_homage_* metrics"
_metrics_body="$("${HOMAGE_REHEARSAL_CURL}" -sf --max-time 5 "${HOMAGE_REHEARSAL_METRICS_URL}" 2>/dev/null || true)"
if [[ -z "${_metrics_body}" ]]; then
    fail "Prometheus scrape failed or empty: ${HOMAGE_REHEARSAL_METRICS_URL}"
else
    _homage_lines="$(printf '%s\n' "${_metrics_body}" | grep -c '^hapax_homage_' || true)"
    # grep -c returns 0 with exit 1 when zero matches; normalise.
    [[ -z "${_homage_lines}" ]] && _homage_lines=0
    if (( _homage_lines >= HOMAGE_REHEARSAL_HOMAGE_METRICS_MIN )); then
        pass "hapax_homage_* metric lines: ${_homage_lines} (>= ${HOMAGE_REHEARSAL_HOMAGE_METRICS_MIN})"
    else
        fail "hapax_homage_* metric lines: ${_homage_lines} (< ${HOMAGE_REHEARSAL_HOMAGE_METRICS_MIN}; has the pipeline fired any events?)"
    fi
fi

# ---------------------------------------------------------------------------
# §7 Research condition YAML
# ---------------------------------------------------------------------------
section "§7 research condition YAML (cond-phase-a-homage-active-001)"
_cond_path="${HOMAGE_REHEARSAL_STATE_DIR}/research-registry/cond-phase-a-homage-active-001/condition.yaml"
if [[ ! -f "${_cond_path}" ]]; then
    fail "condition YAML not found at ${_cond_path}"
else
    _closed_at="$(grep -E '^closed_at:' "${_cond_path}" | head -1 | awk '{print $2}')"
    if [[ "${_closed_at}" == "null" || -z "${_closed_at}" ]]; then
        pass "condition YAML exists and status is open (closed_at=${_closed_at:-null})"
    else
        fail "condition YAML is CLOSED (closed_at=${_closed_at})"
    fi
fi

# ---------------------------------------------------------------------------
# OPERATOR VERIFY section — visual observations, never auto-passed
# ---------------------------------------------------------------------------
section "OPERATOR VERIFY — view mpv v4l2:///dev/video42 and confirm"
_operator_items=(
    "§3.1 token_pole: left-edge vertical pole with \`»»»\` marker on every row (no smiley)"
    "§3.2 album_overlay: box-drawn frame with signed \`by Hapax/bitchx@...\` attribution, no rounded corners"
    "§3.3 stance_indicator: bracketed [STANCE:<name>] pulses; colour matches current stance"
    "§3.4 activity_header: top-strip \`»»» [<activity>] :: homage.rotation=<mode>\` banner present"
    "§3.5 chat_ambient: aggregate counts only, NO author names, NO message bodies"
    "§3.6 grounding_provenance_ticker: ticker-scroll-in/out transitions, no fades"
    "§3.7 captions: raster CP437 font, bridge-short clipping, no emoji"
    "§3.8 stream_overlay: bottom-right three-line status strip with \`»»»\` markers"
    "§3.9 impingement_cascade: one row per event, join-message grammar"
    "§3.10 recruitment_candidate_panel: candidates with four-field bracketed-pipe, raw float scores"
    "§3.11 thinking_indicator: zero-frame state cuts, ASCII-7 dividers only"
    "§3.12 pressure_gauge: half-block glyph row of cells (NOT smooth gradient)"
    "§3.13 activity_variety_log: \`* activity <name> joined (N×)\` recency-ordered"
    "§3.14 whos_here: only @operator / @hapax / agent identifiers visible"
    "§3.15 hardm_dot_matrix: 16×16 grid of cells, half-block/shade glyphs only"
    "§3.16 research_marker_overlay: \`»»» [RESEARCH MARKER] HH:MM:SS\` — no ISO-8601 T/Z"
    "§4 voice register: TEXTMODE default, CONVERSING flip via /dev/shm within one tick"
    "§5 FSM + choreographer: at least three full rotation cycles observed"
    "§6 consent-safe: palette collapse to muted grey within one reconcile tick"
    "§7 palette: 5 wards sampled, mIRC-16 role colours within ±4 per channel"
    "§9 30-minute capture: replay shows zero governance exceptions"
    "Reverie reads as tinted ground, not kaleidoscope"
)
for _item in "${_operator_items[@]}"; do
    emit "[OPERATOR VERIFY] ${_item}"
done

# ---------------------------------------------------------------------------
# Summary + exit
# ---------------------------------------------------------------------------
section "Summary"
_total=$((PASS_COUNT + FAIL_COUNT))
emit "auto-checks: ${PASS_COUNT}/${_total} passed (${FAIL_COUNT} failed)"
emit "operator-verify items: ${#_operator_items[@]} (visual observation required)"
emit "report: ${REPORT_PATH}"

if (( FAIL_COUNT > 0 )); then
    exit 1
fi
exit 0
