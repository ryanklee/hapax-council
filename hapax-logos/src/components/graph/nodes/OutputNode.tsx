import { memo, useEffect, useRef, useState } from "react";
import { Handle, Position, type NodeProps, NodeResizer } from "@xyflow/react";
import { LOGOS_API_URL } from "../../../config";

export interface OutputNodeData {
  label: string;
  [key: string]: unknown;
}

function OutputNodeInner({ data, selected }: NodeProps) {
  const { label } = data as OutputNodeData;
  const imgRef = useRef<HTMLImageElement>(null);
  const [isStale, setIsStale] = useState(false);
  const lastSuccess = useRef(Date.now());

  useEffect(() => {
    let running = true;
    const poll = () => {
      if (!running || !imgRef.current) return;
      const url = `${LOGOS_API_URL}/studio/stream/fx?_t=${Date.now()}`;
      const loader = new Image();
      loader.onload = () => {
        if (running && imgRef.current) imgRef.current.src = loader.src;
        lastSuccess.current = Date.now();
        setIsStale(false);
      };
      loader.onerror = () => {};
      loader.src = url;
    };
    poll();
    const pollTimer = setInterval(poll, 83);
    const staleTimer = setInterval(() => {
      if (Date.now() - lastSuccess.current > 5000) setIsStale(true);
    }, 2000);
    return () => {
      running = false;
      clearInterval(pollTimer);
      clearInterval(staleTimer);
    };
  }, []);

  return (
    <div
      style={{
        minWidth: 220,
        minHeight: 140,
        width: "100%",
        height: "100%",
        background: "#1d2021",
        border: selected ? "1px solid #b8bb26" : "1px solid #3c3836",
        borderRadius: 4,
        position: "relative",
        overflow: "hidden",
        fontFamily: "JetBrains Mono, monospace",
      }}
    >
      <NodeResizer
        isVisible={!!selected}
        minWidth={220}
        minHeight={140}
        lineStyle={{ borderColor: "#b8bb26", borderWidth: 1 }}
        handleStyle={{ background: "#b8bb26", width: 6, height: 6, borderRadius: 2, border: "none" }}
      />
      <img
        ref={imgRef}
        alt={label}
        draggable={false}
        style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          padding: "4px 8px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "linear-gradient(transparent, rgba(29,32,33,0.85))",
        }}
      >
        <span style={{ fontSize: 10, color: "#bdae93" }}>{label}</span>
        {isStale && <span style={{ fontSize: 9, color: "#fb4934" }}>stale</span>}
      </div>
      <Handle
        type="target"
        position={Position.Left}
        style={{ width: 8, height: 8, background: "#3c3836", border: "2px solid #b8bb26", borderRadius: "50%" }}
      />
    </div>
  );
}

export const OutputNode = memo(OutputNodeInner);
