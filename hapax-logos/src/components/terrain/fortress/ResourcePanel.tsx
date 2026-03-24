import { memo } from "react";
import type { FortressState } from "../../../api/types";

interface Props {
  state: FortressState;
}

function Bar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div
      className="h-2 rounded-full overflow-hidden"
      style={{ background: "var(--color-bg-inset)" }}
    >
      <div
        className="h-full rounded-full transition-all"
        style={{ width: `${pct}%`, background: color }}
      />
    </div>
  );
}

function barColor(value: number, perCapita: number, population: number): string {
  const ratio = population > 0 ? value / population : 1;
  if (ratio >= perCapita) return "var(--color-green-400)";
  if (ratio >= perCapita * 0.5) return "var(--color-yellow-400)";
  return "var(--color-red-400)";
}

export const ResourcePanel = memo(function ResourcePanel({ state }: Props) {
  const maxFood = Math.max(state.food_count, state.population * 15, 100);
  const maxDrink = Math.max(state.drink_count, state.population * 10, 100);

  return (
    <div
      className="rounded p-3 text-xs font-mono"
      style={{ background: "var(--color-bg-elevated)" }}
    >
      <div className="font-bold mb-2" style={{ color: "var(--color-fg-secondary)" }}>
        Resources
      </div>
      <div className="space-y-2">
        <div>
          <div className="flex justify-between mb-0.5">
            <span style={{ color: "var(--color-fg-muted)" }}>Food</span>
            <span
              className="tabular-nums"
              style={{ color: "var(--color-fg-primary)" }}
            >
              {state.food_count}
            </span>
          </div>
          <Bar
            value={state.food_count}
            max={maxFood}
            color={barColor(state.food_count, 10, state.population)}
          />
        </div>
        <div>
          <div className="flex justify-between mb-0.5">
            <span style={{ color: "var(--color-fg-muted)" }}>Drink</span>
            <span
              className="tabular-nums"
              style={{ color: "var(--color-fg-primary)" }}
            >
              {state.drink_count}
            </span>
          </div>
          <Bar
            value={state.drink_count}
            max={maxDrink}
            color={barColor(state.drink_count, 5, state.population)}
          />
        </div>
      </div>
    </div>
  );
});
