/**
 * Design token values for JavaScript/TypeScript contexts
 * (React Flow node colors, chart rendering, canvas operations).
 *
 * CSS custom properties in globals.css are the single source of truth (ADR-1).
 * This module reads them at runtime via getComputedStyle — no hardcoded values.
 */

export type Theme = "light" | "dark";

function getCSSToken(varName: string): string {
  if (typeof document === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}

export interface TokenSet {
  readonly bg: string;
  readonly fg: string;
  readonly surface: string;
  readonly border: string;
  readonly muted: string;
  readonly accent: string;
  readonly accentDim: string;
  readonly critical: string;
  readonly high: string;
  readonly medium: string;
  readonly low: string;
  readonly success: string;
  readonly warning: string;
  readonly error: string;
  readonly info: string;
}

/** SSR fallback — Intelligence Vault light palette */
const fallbackTokens: TokenSet = {
  bg:        "#F5F5FC",
  fg:        "#0A0A1A",
  surface:   "#EAEAF5",
  border:    "#CACAE0",
  muted:     "#5252A0",
  accent:    "#6E3ED6",
  accentDim: "#E8E0FA",
  critical:  "#9B1616",
  high:      "#C94A0A",
  medium:    "#8A6400",
  low:       "#1A6840",
  success:   "#1A6840",
  warning:   "#8A6400",
  error:     "#9B1616",
  info:      "#3848C8",
};

/**
 * Get the full token set, reading current CSS custom property values.
 * Theme argument is kept for API compatibility but is unused —
 * the active theme is determined by the html.dark class (ADR-2).
 */
export function getTokens(_theme?: Theme): TokenSet {
  if (typeof document === "undefined") return fallbackTokens;
  return {
    bg:        getCSSToken("--color-bg")         || fallbackTokens.bg,
    fg:        getCSSToken("--color-fg")         || fallbackTokens.fg,
    surface:   getCSSToken("--color-surface")    || fallbackTokens.surface,
    border:    getCSSToken("--color-border")     || fallbackTokens.border,
    muted:     getCSSToken("--color-muted")      || fallbackTokens.muted,
    accent:    getCSSToken("--color-accent")     || fallbackTokens.accent,
    accentDim: getCSSToken("--color-accent-dim") || fallbackTokens.accentDim,
    critical:  getCSSToken("--color-critical")   || fallbackTokens.critical,
    high:      getCSSToken("--color-high")       || fallbackTokens.high,
    medium:    getCSSToken("--color-medium")     || fallbackTokens.medium,
    low:       getCSSToken("--color-low")        || fallbackTokens.low,
    success:   getCSSToken("--color-success")    || fallbackTokens.success,
    warning:   getCSSToken("--color-warning")    || fallbackTokens.warning,
    error:     getCSSToken("--color-error")      || fallbackTokens.error,
    info:      getCSSToken("--color-info")       || fallbackTokens.info,
  };
}

/** Default export — reads current CSS tokens (SSR-safe, falls back to Forensic Ledger light palette). */
export const tokens: TokenSet = fallbackTokens;

export type SeverityLevel = "critical" | "high" | "medium" | "low";
