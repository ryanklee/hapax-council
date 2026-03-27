import { useEffect, useRef } from "react";
import { usePageVisible } from "../../hooks/usePageVisible";

const FRAME_URL = "http://127.0.0.1:8053/frame";
const MIN_FRAME_MS = 33; // ~30fps

/**
 * Displays the wgpu visual surface as a fullscreen background image.
 * Fetches JPEG frames from the Rust HTTP server at 30fps.
 */
export function VisualSurface() {
  const imgRef = useRef<HTMLImageElement>(null);
  const prevUrlRef = useRef<string | null>(null);
  const visible = usePageVisible();

  useEffect(() => {
    if (!visible) return;

    let active = true;
    let lastFrame = 0;

    const tick = async (now: number) => {
      if (!active) return;

      if (now - lastFrame >= MIN_FRAME_MS) {
        lastFrame = now;
        try {
          const res = await fetch(FRAME_URL);
          if (res.ok) {
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            if (prevUrlRef.current) {
              URL.revokeObjectURL(prevUrlRef.current);
            }
            prevUrlRef.current = url;
            if (imgRef.current) {
              imgRef.current.src = url;
            }
          }
        } catch {
          // Frame server not available yet — skip
        }
      }

      if (active) {
        requestAnimationFrame(tick);
      }
    };

    requestAnimationFrame(tick);

    return () => {
      active = false;
      if (prevUrlRef.current) {
        URL.revokeObjectURL(prevUrlRef.current);
        prevUrlRef.current = null;
      }
    };
  }, [visible]);

  return (
    <img
      ref={imgRef}
      className="visual-surface"
      alt=""
      style={{
        position: "fixed",
        inset: 0,
        width: "100%",
        height: "100%",
        objectFit: "cover",
        zIndex: -1,
        pointerEvents: "none",
      }}
    />
  );
}
