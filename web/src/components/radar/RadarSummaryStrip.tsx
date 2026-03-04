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
            className="h-24 animate-pulse rounded-xl border border-border bg-surface-card"
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
            <p className="text-xs font-medium uppercase tracking-wide text-muted">
              Total de sinais
            </p>
            <Activity className="h-4 w-4 text-accent" />
          </div>
          <p className="mt-2 text-2xl font-semibold text-primary">
            {summary.totals.signals}
          </p>
        </div>
        <div className="metric-card">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-muted">
              Total de casos
            </p>
            <BriefcaseBusiness className="h-4 w-4 text-accent" />
          </div>
          <p className="mt-2 text-2xl font-semibold text-primary">
            {summary.totals.cases}
          </p>
        </div>
        <div className="metric-card">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-muted">
              Filtros ativos
            </p>
            <Filter className="h-4 w-4 text-accent" />
          </div>
          <p className="mt-2 text-2xl font-semibold text-primary">
            {summary.active_filters_count}
          </p>
        </div>
        <div className="metric-card">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-muted">
              Tipologias detectadas
            </p>
            <Info className="h-4 w-4 text-accent" />
          </div>
          <p className="mt-2 text-2xl font-semibold text-primary">
            {summary.typology_counts.length}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {(["critical", "high", "medium", "low"] as const).map((severity) => {
          const isActive = activeSeverity === severity;
          const severityTone = severity === "critical"
            ? "text-severity-critical"
            : severity === "high"
              ? "text-severity-high"
              : severity === "medium"
                ? "text-severity-medium"
                : "text-severity-low";
          return (
            <button
              key={severity}
              type="button"
              onClick={() => onSeverityClick(severity)}
              className={`rounded-xl border p-3 text-left transition ${
                isActive
                  ? "border-accent bg-accent-subtle"
                  : "border-border bg-surface-card hover:border-accent/20"
              }`}
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">
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
