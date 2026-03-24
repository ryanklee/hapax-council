import { memo } from "react";
import type { FortressGovernance } from "../../../api/types";

interface Props {
  governance: FortressGovernance | undefined;
}

const CHAIN_ORDER = ["perception", "planning", "military", "economic", "social", "override"];

function suppressionColor(level: number): string {
  if (level <= 0) return "var(--color-green-400)";
  if (level <= 0.3) return "var(--color-yellow-400)";
  if (level <= 0.7) return "var(--color-orange-400)";
  return "var(--color-red-400)";
}

export const ActivityPanel = memo(function ActivityPanel({ governance }: Props) {
  if (!governance) {
    return (
      <div
        className="rounded p-3 text-xs font-mono"
        style={{ background: "var(--color-bg-elevated)" }}
      >
        <div className="font-bold mb-2" style={{ color: "var(--color-fg-secondary)" }}>
          Governance
        </div>
        <div style={{ color: "var(--color-fg-muted)" }}>No data</div>
      </div>
    );
  }

  return (
    <div
      className="rounded p-3 text-xs font-mono"
      style={{ background: "var(--color-bg-elevated)" }}
    >
      <div className="font-bold mb-2" style={{ color: "var(--color-fg-secondary)" }}>
        Governance
      </div>

      {/* Chain activity dots */}
      <div className="flex gap-1.5 mb-3">
        {CHAIN_ORDER.map((chain) => {
          const status = governance.chains[chain];
          const suppression = governance.suppression[chain] ?? 0;
          const active = status?.active ?? false;
          return (
            <div key={chain} className="flex flex-col items-center gap-0.5">
              <div
                className="w-3 h-3 rounded-full transition-colors"
                style={{
                  background: active
                    ? suppressionColor(suppression)
                    : "var(--color-bg-inset)",
                  boxShadow: active ? `0 0 4px ${suppressionColor(suppression)}` : "none",
                }}
                title={`${chain}: ${active ? "active" : "idle"} (suppression: ${Math.round(suppression * 100)}%)`}
              />
              <span
                className="text-[8px] leading-none"
                style={{ color: "var(--color-fg-muted)" }}
              >
                {chain.slice(0, 3)}
              </span>
            </div>
          );
        })}
      </div>

      {/* Last actions */}
      <div className="space-y-0.5">
        {CHAIN_ORDER.map((chain) => {
          const status = governance.chains[chain];
          if (!status?.last_action) return null;
          return (
            <div
              key={chain}
              className="truncate"
              style={{ color: "var(--color-fg-muted)" }}
              title={status.last_action}
            >
              <span style={{ color: "var(--color-fg-secondary)" }}>{chain.slice(0, 3)}:</span>{" "}
              {status.last_action}
            </div>
          );
        }).filter(Boolean)}
      </div>
    </div>
  );
});
