/**
 * Design token values for use in JavaScript/TypeScript contexts
 * (e.g. React Flow node colors, chart colors, canvas rendering).
 *
 * These must stay in sync with the CSS custom properties in globals.css.
 */
export const tokens = {
  surface: {
    base: "#f7f8fc",
    card: "#ffffff",
    subtle: "#f1f3f8",
  },
  border: "#e4e7ef",
  text: {
    primary: "#0c1329",
    secondary: "#52607a",
    muted: "#8896b0",
  },
  accent: "#1d4ed8",
  accentSubtle: "#dbeafe",
  severity: {
    critical: { fg: "#dc2626", bg: "#fef2f2" },
    high: { fg: "#ea580c", bg: "#fff7ed" },
    medium: { fg: "#ca8a04", bg: "#fefce8" },
    low: { fg: "#2563eb", bg: "#eff6ff" },
  },
} as const;

export type SeverityLevel = keyof typeof tokens.severity;
