import { Region } from "../Region";
import { FlowSummary } from "../watershed/FlowSummary";
import { useSystemFlow } from "../../../hooks/useSystemFlow";
import { ProfilePanel } from "../../sidebar/ProfilePanel";

export function WatershedRegion() {
  const flow = useSystemFlow();

  return (
    <Region name="watershed">
      {(depth) => (
        <div className="h-full flex flex-col min-h-0">
          {/* Surface: stance + counts */}
          <div className="shrink-0">
            <FlowSummary
              stance={flow.stance}
              activeCount={flow.activeCount}
              totalCount={flow.totalCount}
              activeFlows={flow.activeFlows}
              totalFlows={flow.totalFlows}
            />
          </div>

          {/* Stratum: profile + compact topology info */}
          {depth !== "surface" && (
            <div className="px-3 overflow-y-auto flex-1 min-h-0">
              <ProfilePanel />
              {depth === "core" && (
                <div className="mt-2 text-[10px] text-zinc-600">
                  Full flow topology available at /legacy/flow
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </Region>
  );
}
