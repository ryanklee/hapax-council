/** Composite visual presets for studio camera feeds. */

export type OverlayType =
  | "scanlines"
  | "rgbsplit"
  | "vignette"
  | "huecycle"
  | "noise"
  | "screwed";

export interface CompositePreset {
  name: string;
  description: string;

  colorFilter: string; // ctx.filter for main frame

  trail: {
    filter: string; // ctx.filter for ghost frames
    blendMode: string; // globalCompositeOperation
    opacity: number; // base opacity (fades with age)
    count: number; // number of ghost frames
    driftX: number; // px per layer horizontal
    driftY: number; // px per layer vertical
  };

  overlay?: {
    delayFrames: number;
    filter: string;
    alpha: number;
    blendMode: string;
    driftY: number;
  };

  warp?: {
    panX: number;
    panY: number;
    rotate: number;
    zoom: number;
    zoomBreath: number;
    sliceCount: number; // 0 = no slicing, >0 = horizontal slice warp
    sliceAmplitude: number;
  };

  stutter?: {
    checkInterval: number;
    freezeChance: number;
    freezeMin: number;
    freezeMax: number;
    replayFrames: number;
  };

  effects: {
    scanlines: boolean;
    bandDisplacement: boolean;
    bandChance: number;
    bandMaxShift: number;
    vignette: boolean;
    vignetteStrength: number;
    syrupGradient: boolean;
    syrupColor: string; // e.g. "60, 20, 80"
  };

  overlays: OverlayType[]; // CSS overlays (kept for non-canvas elements if needed)
  cellAnimation?: string;
  livePullIntervalMs?: number;
}

const NO_EFFECTS: CompositePreset["effects"] = {
  scanlines: false,
  bandDisplacement: false,
  bandChance: 0,
  bandMaxShift: 0,
  vignette: false,
  vignetteStrength: 0,
  syrupGradient: false,
  syrupColor: "0, 0, 0",
};

export const PRESETS: CompositePreset[] = [
  {
    name: "Ghost",
    description: "Transparent echo",
    colorFilter: "none",
    trail: {
      filter: "brightness(1.2)",
      blendMode: "lighter",
      opacity: 0.35,
      count: 4,
      driftX: 2,
      driftY: 5,
    },
    warp: { panX: 3, panY: 2, rotate: 0.005, zoom: 1.01, zoomBreath: 0.005, sliceCount: 0, sliceAmplitude: 0 },
    effects: { ...NO_EFFECTS, vignette: true, vignetteStrength: 0.3 },
    overlays: [],
  },
  {
    name: "Trails",
    description: "Bright motion trails",
    colorFilter: "none",
    trail: {
      filter: "brightness(1.3) saturate(1.5)",
      blendMode: "lighter",
      opacity: 0.5,
      count: 6,
      driftX: 3,
      driftY: 4,
    },
    warp: { panX: 2, panY: 1, rotate: 0.003, zoom: 1.005, zoomBreath: 0.003, sliceCount: 0, sliceAmplitude: 0 },
    effects: { ...NO_EFFECTS },
    overlays: [],
  },
  {
    name: "Screwed",
    description: "Houston syrup — dim, heavy, sinking",
    colorFilter:
      "saturate(0.55) sepia(0.4) hue-rotate(250deg) contrast(1.05) brightness(0.9)",
    trail: {
      filter: "saturate(0.3) brightness(0.5) sepia(0.6) hue-rotate(250deg)",
      blendMode: "lighter",
      opacity: 0.2,
      count: 3,
      driftX: 0,
      driftY: 6,
    },
    overlay: {
      delayFrames: 10,
      filter:
        "saturate(0.4) sepia(0.6) hue-rotate(280deg) brightness(1.2)",
      alpha: 0.45,
      blendMode: "lighter",
      driftY: 8,
    },
    warp: {
      panX: 20,
      panY: 22, // 14 + 8
      rotate: 0.025,
      zoom: 1.06,
      zoomBreath: 0.04,
      sliceCount: 24,
      sliceAmplitude: 6,
    },
    stutter: {
      checkInterval: 10,
      freezeChance: 0.5,
      freezeMin: 3,
      freezeMax: 10,
      replayFrames: 3,
    },
    effects: {
      scanlines: true,
      bandDisplacement: true,
      bandChance: 0.18,
      bandMaxShift: 15,
      vignette: true,
      vignetteStrength: 0.3,
      syrupGradient: true,
      syrupColor: "60, 20, 80",
    },
    overlays: [],
    livePullIntervalMs: 180,
  },
  {
    name: "Datamosh",
    description: "Glitch — RGB split + difference",
    colorFilter: "contrast(1.3) saturate(1.4)",
    trail: {
      filter: "saturate(2) contrast(1.3)",
      blendMode: "difference",
      opacity: 0.85,
      count: 6,
      driftX: 4,
      driftY: 3,
    },
    overlay: {
      delayFrames: 8,
      filter: "saturate(2) hue-rotate(90deg) contrast(1.5)",
      alpha: 0.4,
      blendMode: "difference",
      driftY: 0,
    },
    stutter: {
      checkInterval: 15,
      freezeChance: 0.25,
      freezeMin: 2,
      freezeMax: 5,
      replayFrames: 2,
    },
    effects: {
      ...NO_EFFECTS,
      bandDisplacement: true,
      bandChance: 0.3,
      bandMaxShift: 25,
    },
    overlays: [],
  },
  {
    name: "VHS",
    description: "Lo-fi tape — scan lines, jitter",
    colorFilter: "contrast(1.4) saturate(1.5) brightness(1.1) blur(0.3px)",
    trail: {
      filter: "blur(1px) brightness(1.2)",
      blendMode: "lighter",
      opacity: 0.25,
      count: 3,
      driftX: 1,
      driftY: 2,
    },
    warp: { panX: 1, panY: 0.5, rotate: 0.002, zoom: 1.01, zoomBreath: 0.003, sliceCount: 0, sliceAmplitude: 0 },
    stutter: {
      checkInterval: 30,
      freezeChance: 0.1,
      freezeMin: 2,
      freezeMax: 4,
      replayFrames: 2,
    },
    effects: {
      ...NO_EFFECTS,
      scanlines: true,
      bandDisplacement: true,
      bandChance: 0.2,
      bandMaxShift: 12,
      vignette: true,
      vignetteStrength: 0.35,
    },
    overlays: [],
  },
  {
    name: "Neon",
    description: "Color-cycling glow",
    colorFilter: "contrast(1.3) saturate(2) brightness(1.1)",
    trail: {
      filter: "saturate(4) brightness(1.2)",
      blendMode: "lighter",
      opacity: 0.4,
      count: 5,
      driftX: 2,
      driftY: 3,
    },
    overlay: {
      delayFrames: 6,
      filter: "saturate(3) brightness(1.3) hue-rotate(120deg)",
      alpha: 0.3,
      blendMode: "lighter",
      driftY: 2,
    },
    warp: { panX: 4, panY: 3, rotate: 0.008, zoom: 1.02, zoomBreath: 0.01, sliceCount: 0, sliceAmplitude: 0 },
    effects: { ...NO_EFFECTS, vignette: true, vignetteStrength: 0.35 },
    overlays: [],
  },
  {
    name: "Trap",
    description: "Dark, high-contrast",
    colorFilter: "contrast(1.5) saturate(0.6) brightness(0.8)",
    trail: {
      filter: "sepia(0.6) hue-rotate(-20deg) saturate(2) brightness(0.4)",
      blendMode: "multiply",
      opacity: 0.6,
      count: 4,
      driftX: 1,
      driftY: 4,
    },
    warp: { panX: 2, panY: 1, rotate: 0.003, zoom: 1.01, zoomBreath: 0.005, sliceCount: 0, sliceAmplitude: 0 },
    effects: { ...NO_EFFECTS, vignette: true, vignetteStrength: 0.55, bandDisplacement: true, bandChance: 0.05, bandMaxShift: 6 },
    overlays: [],
  },
  {
    name: "Diff",
    description: "Motion highlight",
    colorFilter: "contrast(1.2) brightness(1.1)",
    trail: {
      filter: "contrast(1.5) brightness(1.3)",
      blendMode: "difference",
      opacity: 0.8,
      count: 3,
      driftX: 1,
      driftY: 1,
    },
    overlay: {
      delayFrames: 8,
      filter: "contrast(1.5)",
      alpha: 0.5,
      blendMode: "difference",
      driftY: 0,
    },
    effects: { ...NO_EFFECTS },
    overlays: [],
  },
  {
    name: "Clean",
    description: "Subtle overlay + vignette",
    colorFilter: "none",
    trail: {
      filter: "none",
      blendMode: "source-over",
      opacity: 0.2,
      count: 2,
      driftX: 0,
      driftY: 1,
    },
    effects: { ...NO_EFFECTS, vignette: true, vignetteStrength: 0.15 },
    overlays: [],
  },
];
