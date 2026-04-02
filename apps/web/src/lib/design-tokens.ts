/**
 * Design token values for JavaScript/TypeScript contexts
 * (React Flow node colors, chart rendering, canvas operations).
 * CSS custom properties in globals.css are the single source of truth.
 */

export type Theme = "dark";

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
  readonly entityPerson: string;
  readonly entityCompany: string;
  readonly entityOrg: string;
}

const fallbackTokens: TokenSet = {
  bg:            "#09090b",
  fg:            "#fafafa",
  surface:       "#111113",
  border:        "#27272a",
  muted:         "#52525b",
  accent:        "#f59e0b",
  accentDim:     "#1c1505",
  critical:      "#ef4444",
  high:          "#f97316",
  medium:        "#eab308",
  low:           "#22c55e",
  success:       "#22c55e",
  warning:       "#eab308",
  error:         "#ef4444",
  info:          "#3b82f6",
  entityPerson:  "#a78bfa",
  entityCompany: "#f59e0b",
  entityOrg:     "#60a5fa",
};

export function getTokens(_theme?: Theme): TokenSet {
  if (typeof document === "undefined") return fallbackTokens;
  return {
    bg:            getCSSToken("--color-bg")             || fallbackTokens.bg,
    fg:            getCSSToken("--color-text")           || fallbackTokens.fg,
    surface:       getCSSToken("--color-surface")        || fallbackTokens.surface,
    border:        getCSSToken("--color-border")         || fallbackTokens.border,
    muted:         getCSSToken("--color-text-3")         || fallbackTokens.muted,
    accent:        getCSSToken("--color-amber")          || fallbackTokens.accent,
    accentDim:     getCSSToken("--color-amber-dim")      || fallbackTokens.accentDim,
    critical:      getCSSToken("--color-critical")       || fallbackTokens.critical,
    high:          getCSSToken("--color-high")           || fallbackTokens.high,
    medium:        getCSSToken("--color-medium")         || fallbackTokens.medium,
    low:           getCSSToken("--color-low")            || fallbackTokens.low,
    success:       getCSSToken("--color-success")        || fallbackTokens.success,
    warning:       getCSSToken("--color-medium")         || fallbackTokens.warning,
    error:         getCSSToken("--color-critical")       || fallbackTokens.error,
    info:          getCSSToken("--color-info")           || fallbackTokens.info,
    entityPerson:  getCSSToken("--color-entity-person")  || fallbackTokens.entityPerson,
    entityCompany: getCSSToken("--color-entity-company") || fallbackTokens.entityCompany,
    entityOrg:     getCSSToken("--color-entity-org")     || fallbackTokens.entityOrg,
  };
}

export const tokens: TokenSet = fallbackTokens;
export type SeverityLevel = "critical" | "high" | "medium" | "low";
