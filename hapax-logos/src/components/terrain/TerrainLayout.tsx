import { useEffect, useCallback } from "react";
import { AmbientShader } from "../hapax/AmbientShader";
import { HorizonRegion } from "./regions/HorizonRegion";
import { FieldRegion } from "./regions/FieldRegion";
import { GroundRegion } from "./regions/GroundRegion";
import { WatershedRegion } from "./regions/WatershedRegion";
import { BedrockRegion } from "./regions/BedrockRegion";
import { VoiceOverlay } from "./overlays/VoiceOverlay";
import { InvestigationOverlay } from "./overlays/InvestigationOverlay";
import { useVisualLayer } from "../../hooks/useVisualLayer";
import { useTerrain } from "../../contexts/TerrainContext";

export function TerrainLayout() {
  const vl = useVisualLayer();
  const { activeOverlay, setOverlay } = useTerrain();

  // Voice overlay: auto-show when voice active
  useEffect(() => {
    if (vl.voiceSession.active && activeOverlay !== "investigation") {
      setOverlay("voice");
    } else if (!vl.voiceSession.active && activeOverlay === "voice") {
      setOverlay(null);
    }
  }, [vl.voiceSession.active, activeOverlay, setOverlay]);

  // Keyboard: `/` toggles investigation overlay
  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "/" && !e.ctrlKey && !e.metaKey) {
        // Don't toggle if typing in an input
        const target = e.target as HTMLElement;
        if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)
          return;
        e.preventDefault();
        setOverlay(activeOverlay === "investigation" ? null : "investigation");
      }
      if (e.key === "Escape" && activeOverlay) {
        setOverlay(null);
      }
    },
    [activeOverlay, setOverlay],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [handleKey]);

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

      {/* z-40: Investigation overlay */}
      <InvestigationOverlay />

      {/* z-50: Voice overlay */}
      <VoiceOverlay vl={vl} />
    </div>
  );
}
