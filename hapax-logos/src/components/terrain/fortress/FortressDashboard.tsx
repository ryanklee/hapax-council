import { memo } from "react";
import { FortressHeadline } from "./FortressHeadline";
import { SurvivalCounter } from "./SurvivalCounter";
import { PopulationPanel } from "./PopulationPanel";
import { ResourcePanel } from "./ResourcePanel";
import { MilitaryPanel } from "./MilitaryPanel";
import { ActivityPanel } from "./ActivityPanel";
import { EventTimeline } from "./EventTimeline";
import {
  useFortressState,
  useFortressGovernance,
  useFortressMetrics,
  useFortressEvents,
} from "../../../api/hooks";

interface Props {
  depth: "surface" | "stratum" | "core";
}

export const FortressDashboard = memo(function FortressDashboard({ depth }: Props) {
  const { data: state } = useFortressState();
  const { data: governance } = useFortressGovernance();
  const { data: metrics } = useFortressMetrics();
  const { data: events } = useFortressEvents();

  return (
    <div className="h-full relative">
      {/* Always visible: headline + survival counter */}
      <FortressHeadline state={state} />
      <SurvivalCounter survivalDays={metrics?.survival_days ?? 0} />

      {/* Stratum: 2x2 panel grid */}
      {depth !== "surface" && state && (
        <div
          className="absolute inset-0 top-16 p-4 grid grid-cols-2 gap-3 overflow-y-auto"
          style={{ zIndex: 5 }}
        >
          <PopulationPanel state={state} />
          <ResourcePanel state={state} />
          <MilitaryPanel state={state} />
          <ActivityPanel governance={governance} />
        </div>
      )}

      {/* Core: event timeline at bottom */}
      {depth === "core" && (
        <div className="absolute bottom-0 left-0 right-0 p-4" style={{ zIndex: 6 }}>
          <EventTimeline events={events?.events ?? []} />
        </div>
      )}
    </div>
  );
});
