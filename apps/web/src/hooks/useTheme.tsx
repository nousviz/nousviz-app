import { useState, useEffect, useContext, createContext } from "react";

export type Theme = "light" | "dark";
export type ColorPalette = "default-light" | "default-dark" | "sovereign" | "aurora" | "nord" | "gruvbox" | "solarized" | "paper" | "custom";

export interface CustomColors {
  background: string;
  foreground: string;
  card: string;
  primary: string;
  secondary: string;
  muted: string;
  border: string;
  sidebar: string;
}

const DEFAULT_CUSTOM: CustomColors = {
  background: "#0f0f1a",
  foreground: "#f0f0f5",
  card: "#16161f",
  primary: "#3b82f6",
  secondary: "#1e1e2a",
  muted: "#2a2a38",
  border: "#2a2a38",
  sidebar: "#12121a",
};

interface ThemeContextValue {
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
  palette: ColorPalette;
  setPalette: (p: ColorPalette) => void;
  customColors: CustomColors;
  setCustomColors: (c: CustomColors) => void;
}

export const ThemeContext = createContext<ThemeContextValue | null>(null);

// ── Provider (mount once in App) ──────────────────────────────────────

export function ThemeProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window === "undefined") return "dark";
    return (localStorage.getItem("nousviz-theme") as Theme) ?? "dark";
  });

  const [palette, setPaletteState] = useState<ColorPalette>(() => {
    // Sovereign is the default dark palette — chosen for the NousViz aesthetic.
    // Users who previously had default-dark stored keep it; new users land on sovereign.
    if (typeof window === "undefined") return "sovereign";
    return (localStorage.getItem("nousviz-palette") as ColorPalette) ?? "sovereign";
  });

  const [customColors, setCustomColorsState] = useState<CustomColors>(() => {
    if (typeof window === "undefined") return DEFAULT_CUSTOM;
    try {
      const stored = localStorage.getItem("nousviz-custom-colors");
      return stored ? { ...DEFAULT_CUSTOM, ...JSON.parse(stored) } : DEFAULT_CUSTOM;
    } catch {
      return DEFAULT_CUSTOM;
    }
  });

  // Apply everything in one effect so it's always in sync
  useEffect(() => {
    const root = document.documentElement;

    // dark/light class
    const isDark = palette !== "default-light" && palette !== "paper" && palette !== "solarized";
    if (isDark) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }

    // palette-sovereign class (uses CSS-only definition in index.css)
    root.classList.remove("palette-sovereign");
    if (palette === "sovereign") {
      root.classList.add("palette-sovereign");
      clearInlineVars(root);
    } else if (palette === "default-light" || palette === "default-dark") {
      clearInlineVars(root);
    } else if (palette === "custom") {
      applyCustomVars(root, customColors);
    } else {
      const vars = PRESETS[palette];
      if (vars) applyPresetVars(root, vars);
    }

    localStorage.setItem("nousviz-theme", theme);
    localStorage.setItem("nousviz-palette", palette);
  }, [theme, palette, customColors]);

  // setTheme: light = default-light, dark = sovereign (the NousViz default dark).
  // Users can still pick default-dark or any other dark palette via the Settings palette picker.
  const setTheme = (t: Theme) => {
    setThemeState(t);
    setPaletteState(t === "light" ? "default-light" : "sovereign");
  };

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  const setPalette = (p: ColorPalette) => {
    setPaletteState(p);
    // Keep theme state aligned for display purposes
    const lightPalettes: ColorPalette[] = ["default-light", "paper", "solarized"];
    setThemeState(lightPalettes.includes(p) ? "light" : "dark");
  };

  const setCustomColors = (c: CustomColors) => {
    setCustomColorsState(c);
    localStorage.setItem("nousviz-custom-colors", JSON.stringify(c));
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme, palette, setPalette, customColors, setCustomColors }}>
      {children}
    </ThemeContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside ThemeProvider");
  return ctx;
}

// ── Preset palette CSS variable sets ─────────────────────────────────

type VarMap = Record<string, string>;

const PRESETS: Partial<Record<ColorPalette, VarMap>> = {
  aurora: {
    "--background":                   "222 47% 7%",
    "--foreground":                   "210 40% 92%",
    "--card":                         "222 40% 10%",
    "--card-foreground":              "210 40% 92%",
    "--popover":                      "222 40% 9%",
    "--popover-foreground":           "210 40% 92%",
    "--primary":                      "170 80% 55%",
    "--primary-foreground":           "222 47% 7%",
    "--secondary":                    "222 35% 15%",
    "--secondary-foreground":         "210 30% 75%",
    "--muted":                        "222 35% 13%",
    "--muted-foreground":             "210 20% 55%",
    "--accent":                       "170 80% 55%",
    "--accent-foreground":            "222 47% 7%",
    "--destructive":                  "0 84% 60%",
    "--destructive-foreground":       "0 0% 100%",
    "--border":                       "222 30% 20% / 0.5",
    "--input":                        "222 35% 15%",
    "--ring":                         "170 80% 55%",
    "--sidebar-background":           "222 47% 5%",
    "--sidebar-foreground":           "210 40% 92%",
    "--sidebar-primary":              "170 80% 55%",
    "--sidebar-primary-foreground":   "222 47% 7%",
    "--sidebar-accent":               "222 35% 13%",
    "--sidebar-accent-foreground":    "210 40% 92%",
    "--sidebar-border":               "222 30% 18% / 0.4",
    "--sidebar-ring":                 "170 80% 55%",
  },
  nord: {
    "--background":                   "220 16% 14%",
    "--foreground":                   "218 27% 92%",
    "--card":                         "222 16% 18%",
    "--card-foreground":              "218 27% 92%",
    "--popover":                      "220 16% 16%",
    "--popover-foreground":           "218 27% 92%",
    "--primary":                      "213 32% 52%",
    "--primary-foreground":           "220 16% 14%",
    "--secondary":                    "220 16% 22%",
    "--secondary-foreground":         "218 20% 75%",
    "--muted":                        "220 16% 20%",
    "--muted-foreground":             "218 15% 55%",
    "--accent":                       "193 43% 67%",
    "--accent-foreground":            "220 16% 14%",
    "--destructive":                  "354 42% 56%",
    "--destructive-foreground":       "0 0% 100%",
    "--border":                       "220 14% 28% / 0.5",
    "--input":                        "220 16% 22%",
    "--ring":                         "213 32% 52%",
    "--sidebar-background":           "220 17% 11%",
    "--sidebar-foreground":           "218 27% 92%",
    "--sidebar-primary":              "213 32% 52%",
    "--sidebar-primary-foreground":   "220 16% 14%",
    "--sidebar-accent":               "220 16% 20%",
    "--sidebar-accent-foreground":    "218 27% 92%",
    "--sidebar-border":               "220 14% 22% / 0.4",
    "--sidebar-ring":                 "213 32% 52%",
  },
  gruvbox: {
    "--background":                   "0 7% 11%",
    "--foreground":                   "43 59% 81%",
    "--card":                         "0 7% 14%",
    "--card-foreground":              "43 59% 81%",
    "--popover":                      "0 7% 12%",
    "--popover-foreground":           "43 59% 81%",
    "--primary":                      "40 72% 50%",
    "--primary-foreground":           "0 7% 11%",
    "--secondary":                    "0 5% 20%",
    "--secondary-foreground":         "43 40% 68%",
    "--muted":                        "0 5% 17%",
    "--muted-foreground":             "43 20% 50%",
    "--accent":                       "104 35% 47%",
    "--accent-foreground":            "0 7% 11%",
    "--destructive":                  "6 96% 59%",
    "--destructive-foreground":       "0 0% 100%",
    "--border":                       "0 5% 26% / 0.5",
    "--input":                        "0 5% 20%",
    "--ring":                         "40 72% 50%",
    "--sidebar-background":           "0 8% 9%",
    "--sidebar-foreground":           "43 59% 81%",
    "--sidebar-primary":              "40 72% 50%",
    "--sidebar-primary-foreground":   "0 7% 11%",
    "--sidebar-accent":               "0 5% 17%",
    "--sidebar-accent-foreground":    "43 59% 81%",
    "--sidebar-border":               "0 5% 22% / 0.4",
    "--sidebar-ring":                 "40 72% 50%",
  },
  solarized: {
    "--background":                   "44 87% 94%",
    "--foreground":                   "192 81% 14%",
    "--card":                         "44 80% 90%",
    "--card-foreground":              "192 81% 14%",
    "--popover":                      "44 80% 88%",
    "--popover-foreground":           "192 81% 14%",
    "--primary":                      "205 69% 49%",
    "--primary-foreground":           "44 87% 94%",
    "--secondary":                    "44 65% 83%",
    "--secondary-foreground":         "192 50% 28%",
    "--muted":                        "44 65% 80%",
    "--muted-foreground":             "192 30% 45%",
    "--accent":                       "68 100% 30%",
    "--accent-foreground":            "44 87% 94%",
    "--destructive":                  "1 71% 52%",
    "--destructive-foreground":       "44 87% 94%",
    "--border":                       "192 20% 72% / 0.5",
    "--input":                        "44 65% 83%",
    "--ring":                         "205 69% 49%",
    "--sidebar-background":           "44 80% 88%",
    "--sidebar-foreground":           "192 81% 14%",
    "--sidebar-primary":              "205 69% 49%",
    "--sidebar-primary-foreground":   "44 87% 94%",
    "--sidebar-accent":               "44 65% 80%",
    "--sidebar-accent-foreground":    "192 81% 14%",
    "--sidebar-border":               "192 20% 66% / 0.4",
    "--sidebar-ring":                 "205 69% 49%",
  },
  paper: {
    "--background":                   "40 33% 97%",
    "--foreground":                   "30 15% 15%",
    "--card":                         "40 25% 93%",
    "--card-foreground":              "30 15% 15%",
    "--popover":                      "40 25% 91%",
    "--popover-foreground":           "30 15% 15%",
    "--primary":                      "25 90% 40%",
    "--primary-foreground":           "40 33% 97%",
    "--secondary":                    "40 20% 87%",
    "--secondary-foreground":         "30 12% 35%",
    "--muted":                        "40 20% 84%",
    "--muted-foreground":             "30 10% 50%",
    "--accent":                       "25 90% 40%",
    "--accent-foreground":            "40 33% 97%",
    "--destructive":                  "0 75% 50%",
    "--destructive-foreground":       "40 33% 97%",
    "--border":                       "30 12% 78% / 0.6",
    "--input":                        "40 20% 87%",
    "--ring":                         "25 90% 40%",
    "--sidebar-background":           "40 25% 91%",
    "--sidebar-foreground":           "30 15% 15%",
    "--sidebar-primary":              "25 90% 40%",
    "--sidebar-primary-foreground":   "40 33% 97%",
    "--sidebar-accent":               "40 20% 84%",
    "--sidebar-accent-foreground":    "30 15% 15%",
    "--sidebar-border":               "30 12% 72% / 0.4",
    "--sidebar-ring":                 "25 90% 40%",
  },
};

// ── Helpers ───────────────────────────────────────────────────────────

function applyPresetVars(root: HTMLElement, vars: VarMap) {
  clearInlineVars(root);
  for (const [prop, value] of Object.entries(vars)) {
    root.style.setProperty(prop, value);
  }
}

function applyCustomVars(root: HTMLElement, c: CustomColors) {
  clearInlineVars(root);
  root.style.setProperty("--background",             hexToHsl(c.background));
  root.style.setProperty("--foreground",             hexToHsl(c.foreground));
  root.style.setProperty("--card",                   hexToHsl(c.card));
  root.style.setProperty("--card-foreground",        hexToHsl(c.foreground));
  root.style.setProperty("--primary",                hexToHsl(c.primary));
  root.style.setProperty("--secondary",              hexToHsl(c.secondary));
  root.style.setProperty("--muted",                  hexToHsl(c.muted));
  root.style.setProperty("--muted-foreground",       hexToHsl(c.foreground) + " / 0.5");
  root.style.setProperty("--border",                 hexToHsl(c.border) + " / 0.15");
  root.style.setProperty("--sidebar-background",     hexToHsl(c.sidebar));
  root.style.setProperty("--sidebar-foreground",     hexToHsl(c.foreground));
  root.style.setProperty("--sidebar-accent",         hexToHsl(c.secondary));
  root.style.setProperty("--sidebar-border",         hexToHsl(c.border) + " / 0.10");
}

function clearInlineVars(root: HTMLElement) {
  [
    "--background","--foreground","--card","--card-foreground",
    "--popover","--popover-foreground",
    "--primary","--primary-foreground",
    "--secondary","--secondary-foreground",
    "--muted","--muted-foreground",
    "--accent","--accent-foreground",
    "--destructive","--destructive-foreground",
    "--border","--input","--ring",
    "--sidebar-background","--sidebar-foreground",
    "--sidebar-primary","--sidebar-primary-foreground",
    "--sidebar-accent","--sidebar-accent-foreground",
    "--sidebar-border","--sidebar-ring",
  ].forEach(v => root.style.removeProperty(v));
}

function hexToHsl(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h = 0, s = 0;
  const l = (max + min) / 2;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
      case g: h = ((b - r) / d + 2) / 6; break;
      case b: h = ((r - g) / d + 4) / 6; break;
    }
  }
  return `${Math.round(h * 360)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%`;
}
