/**
 * ThemeProvider — applies mode-driven color palettes at runtime.
 *
 * Reads the working mode from the API (research/rnd) and sets CSS custom
 * properties on <html> to override Tailwind's @theme values. This makes
 * all Tailwind color classes (bg-zinc-900, text-green-400, etc.) respond
 * to mode changes without rebuilding CSS.
 */

import { createContext, useContext, useEffect, useMemo } from "react";
import { useWorkingMode } from "../api/hooks";
import {
  GRUVBOX_DARK,
  SOLARIZED_DARK,
  semanticColors,
  type SemanticColors,
  type ThemePalette,
} from "./palettes";

interface ThemeContextValue {
  mode: "rnd" | "research";
  palette: ThemePalette;
  colors: SemanticColors;
}

const ThemeContext = createContext<ThemeContextValue>({
  mode: "rnd",
  palette: GRUVBOX_DARK,
  colors: semanticColors(GRUVBOX_DARK),
});

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { data: workingMode } = useWorkingMode();
  const mode = (workingMode?.mode ?? "rnd") as "rnd" | "research";

  const palette = mode === "research" ? SOLARIZED_DARK : GRUVBOX_DARK;
  const colors = useMemo(() => semanticColors(palette), [palette]);

  // Apply CSS custom properties to <html> whenever the palette changes
  useEffect(() => {
    const root = document.documentElement;
    for (const [key, value] of Object.entries(palette)) {
      root.style.setProperty(`--color-${key}`, value);
    }

    // Also set the meta theme-color for mobile/PWA
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute("content", palette["zinc-950"]);
    }

    return () => {
      // Cleanup: remove inline styles so @theme defaults take over
      for (const key of Object.keys(palette)) {
        root.style.removeProperty(`--color-${key}`);
      }
    };
  }, [palette]);

  const value = useMemo(() => ({ mode, palette, colors }), [mode, palette, colors]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
