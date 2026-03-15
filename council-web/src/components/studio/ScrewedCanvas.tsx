import { useEffect, useRef } from "react";

interface Props {
  role: string;
  className?: string;
}

/**
 * Canvas-based screwed renderer.
 * - Frame stutter: holds frames, then replays last few before continuing
 * - Downward-drifting ghost trails
 * - Desaturate then purple shift (works with any source lighting)
 * - Light vignette, NOT heavy darkness
 */
export function ScrewedCanvas({ role, className }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let running = true;
    let pending = false;
    const frameRing: HTMLImageElement[] = [];
    const RING_SIZE = 16;
    let writeHead = 0;

    let displayIdx = 0;
    let ticksSinceAdvance = 0;
    let holdFor = 8;
    let stutterPhase: "normal" | "holding" | "replaying" = "normal";
    let replayStart = 0;
    let replayStep = 0;

    const fetchFrame = () => {
      if (!running || pending) return;
      pending = true;
      const loader = new Image();
      loader.crossOrigin = "anonymous";
      loader.onload = () => {
        if (!running) { pending = false; return; }
        frameRing[writeHead % RING_SIZE] = loader;
        writeHead++;
        if (canvas.width !== loader.naturalWidth) {
          canvas.width = loader.naturalWidth;
          canvas.height = loader.naturalHeight;
        }
        pending = false;
      };
      loader.onerror = () => { pending = false; };
      loader.src = `/api/studio/stream/camera/${role}?_t=${Date.now()}`;
    };

    const render = () => {
      if (!running) return;
      const w = canvas.width;
      const h = canvas.height;
      if (w === 0) return;
      const available = Math.min(writeHead, RING_SIZE);
      if (available < 2) return;

      ticksSinceAdvance++;

      if (stutterPhase === "normal") {
        if (ticksSinceAdvance >= 2) {
          displayIdx = (writeHead - 1) % RING_SIZE;
          ticksSinceAdvance = 0;
          if (Math.random() < 0.45 && available > 3) { // 45% chance to freeze
            stutterPhase = "holding";
            holdFor = 10 + Math.floor(Math.random() * 15); // freeze for 10-24 ticks (~700-1680ms)
            ticksSinceAdvance = 0;
          }
        }
      } else if (stutterPhase === "holding") {
        if (ticksSinceAdvance >= holdFor) {
          stutterPhase = "replaying";
          replayStart = displayIdx;
          replayStep = 0;
          ticksSinceAdvance = 0;
        }
      } else if (stutterPhase === "replaying") {
        if (ticksSinceAdvance >= 2) {
          ticksSinceAdvance = 0;
          replayStep++;
          const replayLen = 4;
          displayIdx = (replayStart - replayLen + replayStep + RING_SIZE * 10) % RING_SIZE;
          if (replayStep >= replayLen) {
            stutterPhase = "normal";
            ticksSinceAdvance = 0;
          }
        }
      }

      const safeIdx = displayIdx % available;
      ctx.clearRect(0, 0, w, h);

      // Ghost trails drifting downward
      for (let g = 3; g >= 1; g--) {
        const ghostIdx = (safeIdx - g * 2 + available * 100) % available;
        const ghost = frameRing[ghostIdx];
        if (!ghost) continue;
        ctx.save();
        ctx.globalAlpha = 0.12 + (3 - g) * 0.08; // 0.12, 0.20, 0.28
        ctx.globalCompositeOperation = "lighter";
        ctx.drawImage(ghost, g * 0.5, g * 3, w, h);
        ctx.restore();
      }

      // Main frame
      const main = frameRing[safeIdx];
      if (main) {
        ctx.drawImage(main, 0, 0, w, h);
      }

      // Color: re-draw main frame with CSS filter applied via ctx.filter
      if (main) {
        ctx.save();
        ctx.filter = "saturate(0.5) sepia(0.5) hue-rotate(240deg) brightness(0.85) contrast(1.1)";
        ctx.globalCompositeOperation = "source-over";
        ctx.globalAlpha = 0.7;
        ctx.drawImage(main, 0, 0, w, h);
        ctx.restore();
      }

      // Syrup gradient — purple settling toward bottom
      const grad = ctx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, "rgba(60, 20, 80, 0.0)");
      grad.addColorStop(0.5, "rgba(70, 30, 90, 0.12)");
      grad.addColorStop(1, "rgba(50, 10, 70, 0.3)");
      ctx.filter = "none";
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      // Vignette
      const vig = ctx.createRadialGradient(w / 2, h / 2, w * 0.3, w / 2, h / 2, w * 0.7);
      vig.addColorStop(0, "rgba(0,0,0,0)");
      vig.addColorStop(1, "rgba(0,0,0,0.35)");
      ctx.fillStyle = vig;
      ctx.fillRect(0, 0, w, h);

      // Band displacement — 8% chance
      if (Math.random() < 0.15 && main) { // 15% chance
        const bandY = Math.floor(Math.random() * h * 0.7) + h * 0.15;
        const bandH = 3 + Math.floor(Math.random() * 8);
        const shift = (Math.random() > 0.5 ? 1 : -1) * (4 + Math.random() * 12); // bigger displacement
        ctx.save();
        ctx.beginPath();
        ctx.rect(0, bandY, w, bandH);
        ctx.clip();
        ctx.drawImage(main, shift, 0, w, h);
        ctx.restore();
      }

      // Visible freeze indicator — purple wash intensifies when stuck
      if (stutterPhase === "holding") {
        ctx.fillStyle = "rgba(80, 20, 100, 0.15)";
        ctx.fillRect(0, 0, w, h);
      } else if (stutterPhase === "replaying") {
        // Flash on replay
        ctx.fillStyle = "rgba(120, 60, 160, 0.08)";
        ctx.fillRect(0, 0, w, h);
      }
    };

    fetchFrame();
    const fetchTimer = setInterval(fetchFrame, 120);
    const renderTimer = setInterval(render, 70);

    return () => {
      running = false;
      clearInterval(fetchTimer);
      clearInterval(renderTimer);
    };
  }, [role]);

  return (
    <canvas
      ref={canvasRef}
      className={className ?? "h-full w-full bg-black object-contain"}
    />
  );
}
