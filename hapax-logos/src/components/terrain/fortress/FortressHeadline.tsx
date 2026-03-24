import { memo } from "react";
import type { FortressState } from "../../../api/types";

const SEASONS = ["Spring", "Summer", "Autumn", "Winter"];

interface Props {
  state: FortressState | undefined;
}

export const FortressHeadline = memo(function FortressHeadline({ state }: Props) {
  if (!state) return null;
  const season = SEASONS[state.season] ?? "?";
  const threatBadge =
    state.active_threats > 0 ? (
      <span className="ml-2 text-red-400 font-bold animate-pulse">⚔ Siege!</span>
    ) : null;

  return (
    <div className="absolute top-4 left-6 z-10 pointer-events-none">
      <div className="text-sm font-mono" style={{ color: "var(--color-fg-secondary)" }}>
        Year {state.year}, {season} — {state.population} dwarves
        {threatBadge}
      </div>
      <div className="text-xs mt-0.5" style={{ color: "var(--color-fg-muted)" }}>
        {state.fortress_name}
      </div>
    </div>
  );
});
