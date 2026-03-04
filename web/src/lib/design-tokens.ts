/**
 * Design token values for use in JavaScript/TypeScript contexts
 * (e.g. React Flow node colors, chart colors, canvas rendering).
 *
 * These must stay in sync with the CSS custom properties in globals.css.
 */
export const tokens = {
  surface: {
    base: "#f9f9fb",
    card: "#ffffff",
    subtle: "#f3f3f6",
    hover: "#ebebef",
  },
  border: "#e1e1e6",
  borderSubtle: "#ececf0",
  sidebar: {
    bg: "#1a1a2e",
    hover: "#252540",
    active: "#2d2d4a",
    text: "#a0a0b8",
    textActive: "#ffffff",
    border: "#2a2a42",
  },
  text: {
    primary: "#1a1a2e",
    secondary: "#5c5c72",
    muted: "#8b8ba0",
    placeholder: "#b0b0c0",
  },
  accent: "#5e6ad2",
  accentHover: "#4e5bc2",
  accentSubtle: "#eef0ff",
  severity: {
    critical: { fg: "#dc2626", bg: "#fef2f2" },
    high: { fg: "#ea580c", bg: "#fff7ed" },
    medium: { fg: "#ca8a04", bg: "#fefce8" },
    low: { fg: "#2563eb", bg: "#eff6ff" },
  },
} as const;

export type SeverityLevel = keyof typeof tokens.severity;
