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
    low: "bg-blue-100 text-blue-800",
    medium: "bg-yellow-100 text-yellow-800",
    high: "bg-orange-100 text-orange-800",
    critical: "bg-red-100 text-red-800",
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
    low: "bg-blue-500",
    medium: "bg-yellow-500",
    high: "bg-orange-500",
    critical: "bg-red-500",
  };
  return map[severity];
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
