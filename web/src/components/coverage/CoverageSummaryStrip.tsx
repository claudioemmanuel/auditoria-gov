"use client";

import type { CoverageV2SummaryResponse } from "@/lib/types";
import { Activity, AlertTriangle, CheckCircle2, Database, Loader2, Workflow } from "lucide-react";

interface CoverageSummaryStripProps {
  summary: CoverageV2SummaryResponse | null;
  loading: boolean;
}

function overallBadge(status?: string) {
  if (status === "healthy") {
    return { label: "Saudavel", cls: "bg-green-100 text-green-700 border-green-200", Icon: CheckCircle2 };
  }
  if (status === "blocked") {
    return { label: "Bloqueado", cls: "bg-red-100 text-red-700 border-red-200", Icon: AlertTriangle };
  }
  return { label: "Atencao", cls: "bg-amber-100 text-amber-700 border-amber-200", Icon: Loader2 };
}

export function CoverageSummaryStrip({ summary, loading }: CoverageSummaryStripProps) {
  if (loading || !summary) {
    return (
      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <div
            key={`coverage-summary-skeleton-${index}`}
            className="h-24 animate-pulse rounded-xl border border-gov-gray-200 bg-white"
          />
        ))}
      </div>
    );
  }

  const badge = overallBadge(summary.pipeline.overall_status);
  const BadgeIcon = badge.Icon;

  return (
    <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <div className="rounded-xl border border-gov-gray-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-wide text-gov-gray-500">Fontes</p>
          <Database className="h-4 w-4 text-gov-blue-600" />
        </div>
        <p className="mt-2 text-2xl font-semibold text-gov-gray-900">{summary.totals.connectors}</p>
      </div>
      <div className="rounded-xl border border-gov-gray-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-wide text-gov-gray-500">Jobs</p>
          <Workflow className="h-4 w-4 text-gov-blue-600" />
        </div>
        <p className="mt-2 text-2xl font-semibold text-gov-gray-900">{summary.totals.jobs}</p>
        <p className="text-xs text-gov-gray-500">{summary.totals.jobs_enabled} habilitados no escopo atual</p>
      </div>
      <div className="rounded-xl border border-gov-gray-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-wide text-gov-gray-500">Execucao</p>
          <Activity className="h-4 w-4 text-gov-blue-600" />
        </div>
        <p className="mt-2 text-2xl font-semibold text-gov-gray-900">{summary.totals.runtime.running}</p>
        <p className="text-xs text-gov-gray-500">
          {summary.totals.runtime.failed_or_stuck} com falha/travamento
        </p>
      </div>
      <div className="rounded-xl border border-gov-gray-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-wide text-gov-gray-500">Sinais acumulados</p>
          <AlertTriangle className="h-4 w-4 text-gov-blue-600" />
        </div>
        <p className="mt-2 text-2xl font-semibold text-gov-gray-900">{summary.totals.signals_total}</p>
      </div>
      <div className={`rounded-xl border p-4 shadow-sm ${badge.cls}`}>
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-wide">Saude do pipeline</p>
          <BadgeIcon className="h-4 w-4" />
        </div>
        <p className="mt-2 text-2xl font-semibold">{badge.label}</p>
      </div>
    </div>
  );
}
