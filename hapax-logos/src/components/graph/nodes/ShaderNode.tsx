import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { useStudioGraph, type StudioGraphState } from "../../../stores/studioGraphStore";
type S = StudioGraphState;

export interface ShaderNodeData {
  shaderType: string;
  label: string;
  params: Record<string, number | string | boolean>;
  [key: string]: unknown;
}

const TYPE_ACCENTS: Record<string, string> = {
  trail: "#83a598",
  feedback: "#83a598",
  echo: "#83a598",
  diff: "#83a598",
  stutter: "#83a598",
  slitscan: "#83a598",
  mirror: "#d3869b",
  kaleidoscope: "#d3869b",
  fisheye: "#d3869b",
  warp: "#d3869b",
  tunnel: "#d3869b",
  droste: "#d3869b",
  colorgrade: "#fabd2f",
  thermal: "#fabd2f",
  color_map: "#fabd2f",
  posterize: "#fabd2f",
  invert: "#fabd2f",
  vhs: "#fe8019",
  glitch_block: "#fe8019",
  pixsort: "#fe8019",
  chromatic_aberration: "#fe8019",
  ascii: "#fe8019",
  halftone: "#fe8019",
  noise_gen: "#8ec07c",
  solid: "#8ec07c",
  blend: "#b8bb26",
  content_layer: "#b8bb26",
  crossfade: "#b8bb26",
};

function paramLine(params: Record<string, number | string | boolean>): string {
  const entries = Object.entries(params).slice(0, 2);
  if (entries.length === 0) return "";
  return entries
    .map(([k, v]) => {
      const short = k.length > 8 ? k.slice(0, 8) : k;
      if (typeof v === "number") return `${short} ${v.toFixed(2)}`;
      return `${short} ${v}`;
    })
    .join("  ");
}

function ShaderNodeInner({ id, data, selected }: NodeProps) {
  const { shaderType, label, params } = data as ShaderNodeData;
  const selectedNodeId = useStudioGraph((s: S) => s.selectedNodeId);
  const selectNode = useStudioGraph((s: S) => s.selectNode);
  const isSelected = selected || selectedNodeId === id;
  const accent = TYPE_ACCENTS[shaderType] ?? "#504945";

  return (
    <div
      onClick={() => selectNode(id)}
      style={{
        width: 148,
        background: "#282828",
        border: isSelected ? `1px solid ${accent}` : "1px solid #3c3836",
        borderRadius: 4,
        cursor: "pointer",
        fontFamily: "JetBrains Mono, monospace",
        transition: "border-color 0.1s",
      }}
    >
      <div style={{ height: 2, background: accent, borderRadius: "3px 3px 0 0" }} />
      <div style={{ padding: "6px 8px 2px" }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: "#ebdbb2", lineHeight: 1.2 }}>
          {label || shaderType}
        </div>
        {label && label !== shaderType && (
          <div style={{ fontSize: 9, color: "#665c54", marginTop: 1 }}>{shaderType}</div>
        )}
      </div>
      <div
        style={{
          padding: "2px 8px 6px",
          fontSize: 9,
          color: "#928374",
          lineHeight: 1.3,
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}
      >
        {paramLine(params) || "\u2014"}
      </div>
      <Handle
        type="target"
        position={Position.Left}
        style={{ width: 8, height: 8, background: "#3c3836", border: `2px solid ${accent}`, borderRadius: "50%" }}
      />
      <Handle
        type="source"
        position={Position.Right}
        style={{ width: 8, height: 8, background: "#3c3836", border: "2px solid #665c54", borderRadius: "50%" }}
      />
    </div>
  );
}

export const ShaderNode = memo(ShaderNodeInner);
