#!/usr/bin/env bash
# sierpinski-cpu-baseline.sh — LRR Phase 0 item 5
#
# Captures studio-compositor CPU utilization over a 5-minute window with
# Sierpinski live in default.json. Computes mean and p95 from per-snapshot
# %CPU readings. Output: ~/.cache/hapax/relay/context/2026-04-14-sierpinski-cpu-baseline.md
#
# Phase 3 will re-measure under Hermes 3 cadence load to detect regressions
# attributable to the substrate swap; this script captures the baseline.
#
# Usage: scripts/sierpinski-cpu-baseline.sh

set -euo pipefail

OUT_DIR="${HOME}/.cache/hapax/relay/context"
OUT_FILE="${OUT_DIR}/2026-04-14-sierpinski-cpu-baseline.md"
SAMPLES=30          # 30 samples × 10s = 300s = 5 minutes
SAMPLE_INTERVAL=10  # seconds between top snapshots
mkdir -p "${OUT_DIR}"

PID=$(pgrep -f "agents.studio_compositor" | head -1 || true)
if [[ -z "${PID}" ]]; then
    echo "ERROR: studio-compositor not running. Start it before capturing baseline." >&2
    exit 1
fi
echo "studio-compositor PID = ${PID}" >&2

CPU_VALUES=()
START_TS="$(date -Iseconds)"
echo "Capturing ${SAMPLES} CPU snapshots, ${SAMPLE_INTERVAL}s apart (~$((SAMPLES * SAMPLE_INTERVAL))s total)..." >&2

for i in $(seq 1 "${SAMPLES}"); do
    # `top -bn1` writes one batch snapshot. The %CPU column for our PID is field 9.
    cpu=$(top -bn1 -p "${PID}" 2>/dev/null | awk -v pid="${PID}" '$1 == pid {print $9}' | head -1)
    if [[ -n "${cpu}" ]]; then
        CPU_VALUES+=("${cpu}")
        printf "  sample %2d/%d: %s%%\n" "${i}" "${SAMPLES}" "${cpu}" >&2
    else
        printf "  sample %2d/%d: (process gone?)\n" "${i}" "${SAMPLES}" >&2
    fi
    if (( i < SAMPLES )); then
        sleep "${SAMPLE_INTERVAL}"
    fi
done

END_TS="$(date -Iseconds)"
N=${#CPU_VALUES[@]}
if (( N == 0 )); then
    echo "ERROR: zero valid CPU samples captured." >&2
    exit 1
fi

# Mean + p95 in awk (no python dependency)
STATS=$(printf '%s\n' "${CPU_VALUES[@]}" | sort -n | awk '
    {
        values[NR] = $1
        sum += $1
    }
    END {
        n = NR
        mean = sum / n
        p95_idx = int(n * 0.95)
        if (p95_idx < 1) p95_idx = 1
        p95 = values[p95_idx]
        max = values[n]
        min = values[1]
        printf "%.1f|%.1f|%.1f|%.1f", mean, p95, max, min
    }
')
MEAN=$(echo "${STATS}" | cut -d'|' -f1)
P95=$(echo "${STATS}" | cut -d'|' -f2)
MAX=$(echo "${STATS}" | cut -d'|' -f3)
MIN=$(echo "${STATS}" | cut -d'|' -f4)

cat > "${OUT_FILE}" <<EOF
# Sierpinski CPU Baseline (LRR Phase 0 item 5)

**Date captured:** ${START_TS}
**Window:** ${START_TS} → ${END_TS} (~$((SAMPLES * SAMPLE_INTERVAL)) seconds)
**Samples:** ${N} valid (of ${SAMPLES} planned)
**Process:** studio-compositor (PID ${PID})
**Capture method:** \`top -bn1 -p ${PID}\` × ${SAMPLES} snapshots, ${SAMPLE_INTERVAL}s apart
**Sierpinski state:** live in \`presets/default.json\` (LRR Phase 0 verification confirmed)

## Results

| metric | value |
|---|---|
| mean %CPU | **${MEAN}%** |
| p95 %CPU | ${P95}% |
| max %CPU | ${MAX}% |
| min %CPU | ${MIN}% |

## Use in subsequent phases

- **Phase 3 (Hardware Migration):** re-run this script after the X670E motherboard install to verify partition reconciliation didn't change CPU footprint.
- **Phase 5 (Hermes 3 substrate swap):** re-run after Hermes 3 is live to measure the cadence load delta. The Phase 5 latency mitigation decision uses this delta to attribute compositor-side cost vs daimonion-side cost.
- **Phase 10 (Observability):** if compositor CPU regresses against this baseline by >50%, that's a dashboard-level alert candidate.

## Method

This is intentionally a coarse measurement (5-minute single capture, no warm-up window, no synthetic load). For a more precise baseline, Phase 10 will add a continuous Prometheus scrape of compositor CPU and we can derive p99 over rolling windows. This file is the single-shot snapshot for the LRR Phase 0 baseline.
EOF

echo "" >&2
echo "Written: ${OUT_FILE}" >&2
echo "Mean ${MEAN}%, p95 ${P95}%, max ${MAX}%, min ${MIN}%" >&2
