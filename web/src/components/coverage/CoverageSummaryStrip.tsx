"use client";

import type { CoverageV2SummaryResponse } from "@/lib/types";
import { Activity, AlertTriangle, CheckCircle2, Database, Loader2, Workflow } from "lucide-react";
import { cn } from "@/lib/utils";

interface CoverageSummaryStripProps {
  summary: CoverageV2SummaryResponse | null;
  loading: boolean;
}

function overallBadge(status?: string) {
  if (status === "healthy") {
    return { label: "Saudável", cls: "border-green-200 bg-green-50 text-green-700", Icon: CheckCircle2 };
  }
  if (status === "blocked") {
    return { label: "Bloqueado", cls: "border-red-200 bg-red-50 text-red-700", Icon: AlertTriangle };
  }
  return { label: "Atenção", cls: "border-yellow-200 bg-yellow-50 text-yellow-700", Icon: Loader2 };
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
      <div className="rounded-xl border border-gov-gray-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-wide text-gov-gray-500">Fontes</p>
          <Database className="h-4 w-4 text-gov-blue-700" />
        </div>
        <p className="mt-2 font-mono tabular-nums text-2xl font-semibold text-gov-gray-900">
          {summary.totals.connectors}
        </p>
      </div>

      <div className="rounded-xl border border-gov-gray-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-wide text-gov-gray-500">Jobs</p>
          <Workflow className="h-4 w-4 text-gov-blue-700" />
        </div>
        <p className="mt-2 font-mono tabular-nums text-2xl font-semibold text-gov-gray-900">
          {summary.totals.jobs}
        </p>
        <p className="text-xs text-gov-gray-500">{summary.totals.jobs_enabled} habilitados</p>
      </div>

      <div className="rounded-xl border border-gov-gray-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-wide text-gov-gray-500">Execução</p>
          <Activity className="h-4 w-4 text-gov-blue-700" />
        </div>
        <p className="mt-2 font-mono tabular-nums text-2xl font-semibold text-gov-gray-900">
          {summary.totals.runtime.running}
        </p>
        <p className="text-xs text-gov-gray-500">
          {summary.totals.runtime.failed_or_stuck} com falha/travamento
        </p>
      </div>

      <div className="rounded-xl border border-gov-gray-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-wide text-gov-gray-500">Sinais acumulados</p>
          <AlertTriangle className="h-4 w-4 text-gov-blue-700" />
        </div>
        <p className="mt-2 font-mono tabular-nums text-2xl font-semibold text-gov-gray-900">
          {summary.totals.signals_total.toLocaleString("pt-BR")}
        </p>
      </div>

      <div className={cn("rounded-xl border p-4", badge.cls)}>
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-wide">Saúde do pipeline</p>
          <BadgeIcon className="h-4 w-4" />
        </div>
        <p className="mt-2 text-2xl font-semibold">{badge.label}</p>
      </div>
    </div>
  );
}
