"use client";

import type { RadarV2SummaryResponse, SignalSeverity } from "@/lib/types";
import { SEVERITY_LABELS } from "@/lib/constants";
import { Activity, BriefcaseBusiness, Filter, Info } from "lucide-react";

interface RadarSummaryStripProps {
  summary: RadarV2SummaryResponse | null;
  loading: boolean;
  activeSeverity?: string;
  onSeverityClick: (severity: SignalSeverity) => void;
}

export function RadarSummaryStrip({
  summary,
  loading,
  activeSeverity,
  onSeverityClick,
}: RadarSummaryStripProps) {
  if (loading || !summary) {
    return (
      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={`radar-summary-skeleton-${i}`}
            className="h-24 animate-pulse rounded-xl border border-gov-gray-200 bg-white"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="mt-6 space-y-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="metric-card">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium uppercase tracking-wide text-gov-gray-500">
              Total de sinais
            </p>
            <Activity className="h-4 w-4 text-gov-blue-600" />
          </div>
          <p className="mt-2 text-2xl font-semibold text-gov-gray-900">
            {summary.totals.signals}
          </p>
        </div>
        <div className="metric-card">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium uppercase tracking-wide text-gov-gray-500">
              Total de casos
            </p>
            <BriefcaseBusiness className="h-4 w-4 text-gov-blue-600" />
          </div>
          <p className="mt-2 text-2xl font-semibold text-gov-gray-900">
            {summary.totals.cases}
          </p>
        </div>
        <div className="metric-card">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium uppercase tracking-wide text-gov-gray-500">
              Filtros ativos
            </p>
            <Filter className="h-4 w-4 text-gov-blue-600" />
          </div>
          <p className="mt-2 text-2xl font-semibold text-gov-gray-900">
            {summary.active_filters_count}
          </p>
        </div>
        <div className="metric-card">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium uppercase tracking-wide text-gov-gray-500">
              Tipologias detectadas
            </p>
            <Info className="h-4 w-4 text-gov-blue-600" />
          </div>
          <p className="mt-2 text-2xl font-semibold text-gov-gray-900">
            {summary.typology_counts.length}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {(["critical", "high", "medium", "low"] as const).map((severity) => {
          const isActive = activeSeverity === severity;
          const severityTone = severity === "critical"
            ? "text-red-700"
            : severity === "high"
              ? "text-orange-700"
              : severity === "medium"
                ? "text-amber-700"
                : "text-blue-700";
          return (
            <button
              key={severity}
              type="button"
              onClick={() => onSeverityClick(severity)}
              className={`rounded-xl border p-3.5 text-left transition ${
                isActive
                  ? "border-gov-blue-300 bg-gov-blue-50 shadow-sm"
                  : "border-gov-gray-200/90 bg-white/90 hover:border-gov-blue-200 hover:shadow-sm"
              }`}
            >
              <p className="text-sm font-semibold uppercase tracking-wide text-gov-gray-500">
                {SEVERITY_LABELS[severity]}
              </p>
              <p className={`mt-1 text-xl font-semibold ${severityTone}`}>
                {summary.severity_counts[severity]}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
