import { useReactFlow } from "@xyflow/react";
import { useStudioGraph, type StudioGraphState } from "../../stores/studioGraphStore";

type S = StudioGraphState;

const btn = {
  background: "none",
  border: "1px solid #504945",
  borderRadius: 2,
  padding: "2px 8px",
  cursor: "pointer",
  fontFamily: "JetBrains Mono, monospace",
  fontSize: 10,
  lineHeight: 1.4,
} as const;

export function GraphToolbar() {
  const { fitView, zoomIn, zoomOut } = useReactFlow();
  const graphName = useStudioGraph((s: S) => s.graphName);
  const graphDirty = useStudioGraph((s: S) => s.graphDirty);
  const hapaxLocked = useStudioGraph((s: S) => s.hapaxLocked);
  const toggleHapaxLock = useStudioGraph((s: S) => s.toggleHapaxLock);

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        height: 32,
        background: "#282828",
        borderBottom: "1px solid #3c3836",
        display: "flex",
        alignItems: "center",
        padding: "0 12px",
        gap: 8,
        zIndex: 10,
        fontFamily: "JetBrains Mono, monospace",
      }}
    >
      {/* Graph name */}
      <span style={{ fontSize: 11, color: "#ebdbb2", fontWeight: 600 }}>
        {graphName}
      </span>
      {graphDirty && (
        <span style={{ fontSize: 11, color: "#fabd2f" }}>*</span>
      )}

      <div style={{ flex: 1 }} />

      {/* Hapax governance toggle */}
      <button
        onClick={toggleHapaxLock}
        title={hapaxLocked ? "Hapax suppressed (Space)" : "Hapax active (Space)"}
        style={{
          ...btn,
          color: hapaxLocked ? "#fb4934" : "#b8bb26",
          borderColor: hapaxLocked ? "#9d0006" : "#79740e",
        }}
      >
        {hapaxLocked ? "⊘ locked" : "◉ hapax"}
      </button>

      {/* Zoom */}
      <div style={{ display: "flex", gap: 2 }}>
        <button onClick={() => zoomOut()} style={{ ...btn, color: "#928374", border: "none", padding: "2px 4px" }}>
          −
        </button>
        <button onClick={() => zoomIn()} style={{ ...btn, color: "#928374", border: "none", padding: "2px 4px" }}>
          +
        </button>
      </div>

      <button onClick={() => fitView({ padding: 0.15 })} style={{ ...btn, color: "#928374" }}>
        fit
      </button>
    </div>
  );
}
