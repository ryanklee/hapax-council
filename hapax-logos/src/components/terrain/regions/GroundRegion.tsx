import { Region } from "../Region";
import { AmbientCanvas } from "../ground/AmbientCanvas";
import { SignalZones } from "../ground/SignalZones";
import { TimeDisplay } from "../ground/TimeDisplay";
import { AccommodationPanel } from "../../sidebar/AccommodationPanel";
import type { useVisualLayer } from "../../../hooks/useVisualLayer";

interface GroundRegionProps {
  vl: ReturnType<typeof useVisualLayer>;
}

export function GroundRegion({ vl }: GroundRegionProps) {
  return (
    <Region name="ground">
      {(depth) => (
        <div className="h-full relative">
          {/* Surface: ambient canvas + signals + time */}
          <AmbientCanvas ambientText={vl.ambientText} speed={vl.ambient.speed} />
          <SignalZones signals={vl.signals} opacities={vl.opacities} />
          <TimeDisplay
            activityLabel={vl.activityLabel}
            activityDetail={vl.activityDetail}
            displayState={vl.state}
          />

          {/* Stratum: accommodation panel */}
          {depth !== "surface" && (
            <div className="absolute inset-0 top-16 overflow-y-auto p-4">
              <AccommodationPanel />
            </div>
          )}
        </div>
      )}
    </Region>
  );
}
