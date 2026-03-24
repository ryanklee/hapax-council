import { memo } from "react";

interface Props {
  survivalDays: number;
}

export const SurvivalCounter = memo(function SurvivalCounter({ survivalDays }: Props) {
  return (
    <div className="absolute top-4 right-6 z-10 pointer-events-none text-right">
      <div
        className="text-2xl font-mono tabular-nums font-bold"
        style={{ color: "var(--color-fg-primary)" }}
      >
        {survivalDays.toLocaleString()}
      </div>
      <div className="text-xs" style={{ color: "var(--color-fg-muted)" }}>
        days survived
      </div>
    </div>
  );
});
