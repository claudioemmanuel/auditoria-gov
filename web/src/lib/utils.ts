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
    ok: "status-ok",
    warning: "status-warning",
    stale: "status-warning",
    error: "status-error",
    pending: "status-pending",
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

export function formatCPF(cpf: string): string {
  const d = cpf.replace(/\D/g, "");
  if (d.length !== 11) return cpf;
  return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
}

export function formatCNPJ(cnpj: string): string {
  const d = cnpj.replace(/\D/g, "");
  if (d.length !== 14) return cnpj;
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
}

export function formatIdentifier(identifiers: Record<string, string>): string {
  if (identifiers.cnpj) return formatCNPJ(identifiers.cnpj);
  if (identifiers.cpf) return formatCPF(identifiers.cpf);
  if (identifiers.cpf_partial) return identifiers.cpf_partial;
  return "";
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
