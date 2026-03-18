import { AmbientShader } from "../hapax/AmbientShader";
import { HorizonRegion } from "./regions/HorizonRegion";
import { FieldRegion } from "./regions/FieldRegion";
import { GroundRegion } from "./regions/GroundRegion";
import { WatershedRegion } from "./regions/WatershedRegion";
import { BedrockRegion } from "./regions/BedrockRegion";
import { useVisualLayer } from "../../hooks/useVisualLayer";

export function TerrainLayout() {
  const vl = useVisualLayer();

  return (
    <div
      className="h-screen w-screen overflow-hidden relative"
      style={{ fontFamily: "'JetBrains Mono', monospace", background: "#1d2021" }}
    >
      {/* z-0: Ambient shader background — always alive, driven by visual layer */}
      <AmbientShader
        speed={vl.ambient.speed}
        turbulence={vl.ambient.turbulence}
        warmth={vl.ambient.color_warmth}
        brightness={vl.ambient.brightness * 0.6}
        displayState={vl.state}
      />

      {/* z-1: Terrain grid */}
      <div
        className="absolute inset-0"
        style={{
          zIndex: 1,
          display: "grid",
          gridTemplateColumns: "minmax(180px, 1fr) 3fr minmax(180px, 1fr)",
          gridTemplateRows: "12vh 1fr 10vh",
        }}
      >
        <HorizonRegion />
        <FieldRegion />
        <GroundRegion vl={vl} />
        <WatershedRegion />
        <BedrockRegion />
      </div>
    </div>
  );
}
