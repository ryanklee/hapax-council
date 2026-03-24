import { memo } from "react";
import type { FortressState } from "../../../api/types";

interface Props {
  state: FortressState;
}

export const MilitaryPanel = memo(function MilitaryPanel({ state }: Props) {
  const threatLevel =
    state.active_threats === 0
      ? { label: "Peaceful", color: "var(--color-green-400)" }
      : state.active_threats <= 2
        ? { label: "Under Attack", color: "var(--color-orange-400)" }
        : { label: "Siege", color: "var(--color-red-400)" };

  return (
    <div
      className="rounded p-3 text-xs font-mono"
      style={{ background: "var(--color-bg-elevated)" }}
    >
      <div className="font-bold mb-2" style={{ color: "var(--color-fg-secondary)" }}>
        Military
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <div className="text-lg tabular-nums" style={{ color: threatLevel.color }}>
            {state.active_threats}
          </div>
          <div style={{ color: "var(--color-fg-muted)" }}>threats</div>
        </div>
        <div>
          <div className="text-lg" style={{ color: threatLevel.color }}>
            {threatLevel.label}
          </div>
          <div style={{ color: "var(--color-fg-muted)" }}>status</div>
        </div>
      </div>
      <div className="mt-2 pt-2" style={{ borderTop: "1px solid var(--color-border)" }}>
        <div className="flex justify-between">
          <span style={{ color: "var(--color-fg-muted)" }}>Job queue</span>
          <span className="tabular-nums" style={{ color: "var(--color-fg-primary)" }}>
            {state.job_queue_length}
          </span>
        </div>
      </div>
    </div>
  );
});
