/**
 * Scene-level classification badges — ambient indicators for scene type,
 * audio scene, and lighting rendered on camera views.
 *
 * These are per-frame ambient signals (not per-entity detections).
 * Rendered at surface-appropriate opacity (10-15%).
 */
import { useSignals } from "../../contexts/ClassificationOverlayContext";

interface SceneBadgesProps {
  /** Position CSS class (e.g., "top-2 right-2" or "bottom-1 left-1"). */
  position?: string;
  /** Scale factor for smaller/larger text. */
  scale?: "sm" | "md";
}

export function SceneBadges({ position = "top-2 right-12", scale = "md" }: SceneBadgesProps) {
  const { perception } = useSignals();
  if (!perception) return null;

  const sceneType = perception.scene_type;
  const audioScene = perception.audio_scene;
  const colorTemp = perception.color_temperature;

  // Only show non-default values
  const badges: { label: string; color: string }[] = [];

  if (sceneType && sceneType !== "unknown") {
    badges.push({ label: sceneType.replace(/_/g, " "), color: "#83a598" });
  }
  if (audioScene && audioScene !== "silence" && audioScene !== "unknown") {
    badges.push({ label: audioScene, color: "#fabd2f" });
  }
  if (colorTemp && colorTemp !== "unknown" && colorTemp !== "neutral") {
    badges.push({
      label: colorTemp,
      color: colorTemp === "warm" ? "#fe8019" : "#83a598",
    });
  }

  if (!badges.length) return null;

  const textSize = scale === "sm" ? "text-[7px]" : "text-[9px]";

  return (
    <div className={`absolute ${position} pointer-events-none flex gap-1 z-20`}>
      {badges.map((b) => (
        <span
          key={b.label}
          className={`${textSize} rounded px-1 py-px font-mono`}
          style={{
            color: b.color,
            opacity: 0.15,
            background: "rgba(29, 32, 33, 0.4)",
          }}
        >
          {b.label}
        </span>
      ))}
    </div>
  );
}
