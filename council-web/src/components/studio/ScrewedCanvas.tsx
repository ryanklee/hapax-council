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
    let holdFor = 4;
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
          if (Math.random() < 0.18 && available > 4) {
            stutterPhase = "holding";
            holdFor = 6 + Math.floor(Math.random() * 8);
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
        ctx.globalAlpha = 0.08 + (3 - g) * 0.05;
        ctx.globalCompositeOperation = "lighter";
        ctx.drawImage(ghost, g * 0.5, g * 3, w, h);
        ctx.restore();
      }

      // Main frame
      const main = frameRing[safeIdx];
      if (main) {
        ctx.drawImage(main, 0, 0, w, h);
      }

      // Desaturate via "saturation" composite
      ctx.save();
      ctx.globalCompositeOperation = "saturation";
      ctx.fillStyle = "hsl(270, 10%, 50%)";
      ctx.globalAlpha = 0.45;
      ctx.fillRect(0, 0, w, h);
      ctx.restore();

      // Purple tint
      ctx.save();
      ctx.globalCompositeOperation = "multiply";
      ctx.fillStyle = "rgb(180, 130, 200)";
      ctx.globalAlpha = 0.2;
      ctx.fillRect(0, 0, w, h);
      ctx.restore();

      // Syrup gradient
      const grad = ctx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, "rgba(80, 40, 100, 0.0)");
      grad.addColorStop(0.6, "rgba(80, 40, 100, 0.08)");
      grad.addColorStop(1, "rgba(60, 20, 80, 0.2)");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      // Light vignette
      const vig = ctx.createRadialGradient(w / 2, h / 2, w * 0.35, w / 2, h / 2, w * 0.75);
      vig.addColorStop(0, "rgba(0,0,0,0)");
      vig.addColorStop(1, "rgba(0,0,0,0.3)");
      ctx.fillStyle = vig;
      ctx.fillRect(0, 0, w, h);

      // Band displacement — 8% chance
      if (Math.random() < 0.08 && main) {
        const bandY = Math.floor(Math.random() * h * 0.7) + h * 0.15;
        const bandH = 3 + Math.floor(Math.random() * 8);
        const shift = (Math.random() > 0.5 ? 1 : -1) * (2 + Math.random() * 6);
        ctx.save();
        ctx.beginPath();
        ctx.rect(0, bandY, w, bandH);
        ctx.clip();
        ctx.drawImage(main, shift, 0, w, h);
        ctx.restore();
      }

      // Subtle flash when frozen
      if (stutterPhase === "holding") {
        ctx.fillStyle = "rgba(100, 50, 120, 0.06)";
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
