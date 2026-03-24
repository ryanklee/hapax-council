import { memo } from "react";
import type { FortressState } from "../../../api/types";

interface Props {
  state: FortressState;
}

const MOOD_THRESHOLDS = [
  { label: "Ecstatic", max: 0, color: "var(--color-green-400)" },
  { label: "Content", max: 25000, color: "var(--color-green-300)" },
  { label: "Fine", max: 75000, color: "var(--color-yellow-400)" },
  { label: "Unhappy", max: 100000, color: "var(--color-orange-400)" },
  { label: "Miserable", max: Infinity, color: "var(--color-red-400)" },
];

function moodColor(stress: number): string {
  for (const t of MOOD_THRESHOLDS) {
    if (stress <= t.max) return t.color;
  }
  return "var(--color-red-400)";
}

function moodLabel(stress: number): string {
  for (const t of MOOD_THRESHOLDS) {
    if (stress <= t.max) return t.label;
  }
  return "Miserable";
}

export const PopulationPanel = memo(function PopulationPanel({ state }: Props) {
  return (
    <div
      className="rounded p-3 text-xs font-mono"
      style={{ background: "var(--color-bg-elevated)" }}
    >
      <div className="font-bold mb-2" style={{ color: "var(--color-fg-secondary)" }}>
        Population
      </div>
      <div className="grid grid-cols-3 gap-2">
        <div>
          <div
            className="text-lg tabular-nums"
            style={{ color: "var(--color-fg-primary)" }}
          >
            {state.population}
          </div>
          <div style={{ color: "var(--color-fg-muted)" }}>citizens</div>
        </div>
        <div>
          <div
            className="text-lg tabular-nums"
            style={{ color: "var(--color-fg-primary)" }}
          >
            {state.idle_dwarf_count}
          </div>
          <div style={{ color: "var(--color-fg-muted)" }}>idle</div>
        </div>
        <div>
          <div
            className="text-lg tabular-nums"
            style={{ color: moodColor(state.most_stressed_value) }}
          >
            {state.most_stressed_value > 100000 ? "⚠" : "●"}
          </div>
          <div style={{ color: "var(--color-fg-muted)" }}>
            {moodLabel(state.most_stressed_value)}
          </div>
        </div>
      </div>
    </div>
  );
});
