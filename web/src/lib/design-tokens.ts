/**
 * Design token values for JavaScript/TypeScript contexts
 * (React Flow node colors, chart rendering, canvas operations).
 *
 * Must stay in sync with CSS custom properties in globals.css.
 */

export type Theme = "light" | "dark";

const light = {
  surface: {
    base: "#F5F7FA",
    card: "#FFFFFF",
    subtle: "#EDF2F7",
    hover: "#E2E8F0",
  },
  border: "#D7E0E8",
  borderSubtle: "#E2E8F0",
  text: {
    primary: "#10212B",
    secondary: "#425466",
    muted: "#7B8FA2",
    placeholder: "#A0AEC0",
  },
  accent: "#0F4C5C",
  accentHover: "#0B3D4A",
  accentSubtle: "#E6F0F2",
  sidebar: {
    bg: "#0E171D",
    hover: "#1B2B35",
    active: "#223540",
    text: "#A8BBC9",
    textActive: "#E7EEF3",
    border: "#2A3A45",
  },
  severity: {
    critical: { fg: "#dc2626", bg: "#fef2f2" },
    high: { fg: "#ea580c", bg: "#fff7ed" },
    medium: { fg: "#ca8a04", bg: "#fefce8" },
    low: { fg: "#2563eb", bg: "#eff6ff" },
  },
  amber: { fg: "#D97706", bg: "#FEF3C7" },
  success: { fg: "#059669", bg: "#ECFDF5" },
  error: { fg: "#DC2626", bg: "#FEF2F2" },
} as const;

const dark = {
  surface: {
    base: "#0E171D",
    card: "#142129",
    subtle: "#1B2B35",
    hover: "#223540",
  },
  border: "#2A3A45",
  borderSubtle: "#1F3040",
  text: {
    primary: "#E7EEF3",
    secondary: "#A8BBC9",
    muted: "#6B8295",
    placeholder: "#4A6577",
  },
  accent: "#3C8EA2",
  accentHover: "#57A8BC",
  accentSubtle: "#142E36",
  sidebar: {
    bg: "#0A1117",
    hover: "#142129",
    active: "#1B2B35",
    text: "#6B8295",
    textActive: "#E7EEF3",
    border: "#1F3040",
  },
  severity: {
    critical: { fg: "#F87171", bg: "#371717" },
    high: { fg: "#FB923C", bg: "#3B2010" },
    medium: { fg: "#FACC15", bg: "#352A0A" },
    low: { fg: "#60A5FA", bg: "#152040" },
  },
  amber: { fg: "#FBBF24", bg: "#352A0A" },
  success: { fg: "#34D399", bg: "#0A2920" },
  error: { fg: "#F87171", bg: "#371717" },
} as const;

interface FgBg {
  readonly fg: string;
  readonly bg: string;
}

export interface TokenSet {
  readonly surface: { readonly base: string; readonly card: string; readonly subtle: string; readonly hover: string };
  readonly border: string;
  readonly borderSubtle: string;
  readonly text: { readonly primary: string; readonly secondary: string; readonly muted: string; readonly placeholder: string };
  readonly accent: string;
  readonly accentHover: string;
  readonly accentSubtle: string;
  readonly sidebar: { readonly bg: string; readonly hover: string; readonly active: string; readonly text: string; readonly textActive: string; readonly border: string };
  readonly severity: { readonly critical: FgBg; readonly high: FgBg; readonly medium: FgBg; readonly low: FgBg };
  readonly amber: FgBg;
  readonly success: FgBg;
  readonly error: FgBg;
}

/** Get the full token set for a given theme. */
export function getTokens(theme: Theme): TokenSet {
  return theme === "dark" ? dark : light;
}

/** Default export for backward compatibility — light tokens. */
export const tokens = light;

export type SeverityLevel = keyof typeof light.severity;
