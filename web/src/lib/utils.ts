import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { SignalSeverity, CoverageStatus } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBRL(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function severityColor(severity: SignalSeverity): string {
  const map: Record<SignalSeverity, string> = {
    low: "bg-severity-low-bg text-severity-low",
    medium: "bg-severity-medium-bg text-severity-medium",
    high: "bg-severity-high-bg text-severity-high",
    critical: "bg-severity-critical-bg text-severity-critical",
  };
  return map[severity];
}

export function coverageStatusColor(status: CoverageStatus): string {
  const map: Record<CoverageStatus, string> = {
    ok: "bg-green-100 text-green-800",
    warning: "bg-amber-100 text-amber-800",
    stale: "bg-yellow-100 text-yellow-800",
    error: "bg-red-100 text-red-800",
    pending: "bg-gray-100 text-gray-800",
  };
  return map[status];
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("pt-BR").format(value);
}

export function severityDotColor(severity: SignalSeverity): string {
  const map: Record<SignalSeverity, string> = {
    low: "bg-severity-low",
    medium: "bg-severity-medium",
    high: "bg-severity-high",
    critical: "bg-severity-critical",
  };
  return map[severity];
}

export function relativeTime(dateStr: string): string {
  try {
    const diff = Date.now() - new Date(dateStr).getTime();
    const abs = Math.abs(diff);
    const rtf = new Intl.RelativeTimeFormat("pt-BR", { numeric: "auto" });
    if (abs < 60_000) return "agora";
    if (abs < 3_600_000) return rtf.format(-Math.round(diff / 60_000), "minute");
    if (abs < 86_400_000) return rtf.format(-Math.round(diff / 3_600_000), "hour");
    if (abs < 2_592_000_000) return rtf.format(-Math.round(diff / 86_400_000), "day");
    return rtf.format(-Math.round(diff / 2_592_000_000), "month");
  } catch {
    return dateStr;
  }
}

export function normalizeUnknownDisplay(
  value: unknown,
  fallback: string = "Nao informado pela fonte",
): string {
  const raw = String(value ?? "").trim();
  if (!raw) return fallback;
  const normalized = raw.toLowerCase();
  if (
    normalized === "unknown" ||
    normalized === "sem classificacao" ||
    normalized === "sem classificação" ||
    normalized === "null" ||
    normalized === "none" ||
    normalized === "nao_informado" ||
    normalized === "não informado"
  ) {
    return fallback;
  }
  return raw;
}
