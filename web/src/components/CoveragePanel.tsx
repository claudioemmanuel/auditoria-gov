"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { coverageStatusColor, formatDate, formatDateTime } from "@/lib/utils";
import { COVERAGE_STATUS_LABELS } from "@/lib/constants";
import type { CoverageItem, CoverageStatus, IngestRun } from "@/lib/types";
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  HelpCircle,
  Database,
  RefreshCw,
  Loader2,
  ChevronDown,
  ChevronUp,
  CircleX,
  CircleAlert,
  PlayCircle,
} from "lucide-react";

interface CoveragePanelProps {
  items: CoverageItem[];
  recentRuns: IngestRun[];
}

type RunBadge = "running" | "stuck" | "error" | "completed" | "none";

const STATUS_ICONS = {
  ok: CheckCircle2,
  warning: CircleAlert,
  stale: Clock,
  error: AlertCircle,
  pending: HelpCircle,
} as const;

const STATUS_PRIORITY: Record<CoverageStatus, number> = {
  ok: 0,
  pending: 1,
  stale: 2,
  warning: 3,
  error: 4,
};

const CONNECTOR_TONE: Record<CoverageStatus, string> = {
  ok: "border-gov-gray-200",
  pending: "border-gov-gray-200",
  stale: "border-yellow-200",
  warning: "border-amber-200",
  error: "border-red-200",
};

function getErrorMessage(errors: IngestRun["errors"]): string | null {
  if (!errors) return null;
  const value = errors.error;
  if (typeof value === "string") {
    return value.trim() || "Erro sem mensagem detalhada";
  }
  if (value != null) return String(value);
  return null;
}

function getRunBadge(run?: IngestRun): RunBadge {
  if (!run) return "none";
  if (run.status === "error") return "error";
  if (run.status === "running") {
    if (run.started_at) {
      const started = new Date(run.started_at).getTime();
      if (!Number.isNaN(started) && Date.now() - started > 20 * 60 * 1000) {
        return "stuck";
      }
    }
    return "running";
  }
  if (run.status === "completed") return "completed";
  return "none";
}

function getRunBadgeUI(runBadge: RunBadge): {
  label: string;
  className: string;
  icon: React.ElementType;
} | null {
  if (runBadge === "none") return null;
  if (runBadge === "stuck") {
    return {
      label: "Travado",
      className: "bg-red-100 text-red-700",
      icon: CircleX,
    };
  }
  if (runBadge === "error") {
    return {
      label: "Falha",
      className: "bg-red-100 text-red-700",
      icon: AlertCircle,
    };
  }
  if (runBadge === "running") {
    return {
      label: "Rodando",
      className: "bg-blue-100 text-blue-700",
      icon: Loader2,
    };
  }
  return {
    label: "Concluido",
    className: "bg-green-100 text-green-700",
    icon: PlayCircle,
  };
}

function prettifyConnectorName(name: string): string {
  return name.replace(/_/g, " ");
}

export function CoveragePanel({ items, recentRuns }: CoveragePanelProps) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null);

  const latestRunsByJob = useMemo(() => {
    const map = new Map<string, IngestRun>();
    for (const run of recentRuns) {
      const key = `${run.connector}:${run.job}`;
      if (!map.has(key)) map.set(key, run);
    }
    return map;
  }, [recentRuns]);

  const connectors = useMemo(() => {
    const grouped = items.reduce(
      (acc, item) => {
        if (!acc[item.connector]) acc[item.connector] = [];
        acc[item.connector].push(item);
        return acc;
      },
      {} as Record<string, CoverageItem[]>
    );

    const result = Object.entries(grouped).map(([connector, jobs]) => {
      const sortedJobs = [...jobs].sort((a, b) => a.job.localeCompare(b.job));
      const counts = sortedJobs.reduce(
        (acc, job) => {
          acc[job.status] += 1;
          return acc;
        },
        { ok: 0, warning: 0, stale: 0, error: 0, pending: 0 }
      );
      const worstStatus = sortedJobs.reduce<CoverageStatus>(
        (worst, job) =>
          STATUS_PRIORITY[job.status] > STATUS_PRIORITY[worst] ? job.status : worst,
        "ok"
      );

      const lastSuccessAt = sortedJobs
        .map((job) => job.last_success_at)
        .filter((value): value is string => Boolean(value))
        .sort((a, b) => new Date(b).getTime() - new Date(a).getTime())[0];

      const maxLagHours = sortedJobs.reduce<number | null>((max, job) => {
        if (job.freshness_lag_hours == null) return max;
        if (max == null) return job.freshness_lag_hours;
        return Math.max(max, job.freshness_lag_hours);
      }, null);

      return {
        connector,
        jobs: sortedJobs,
        counts,
        worstStatus,
        lastSuccessAt,
        maxLagHours,
      };
    });

    return result.sort((a, b) => {
      const severityDiff = STATUS_PRIORITY[b.worstStatus] - STATUS_PRIORITY[a.worstStatus];
      if (severityDiff !== 0) return severityDiff;
      return a.connector.localeCompare(b.connector);
    });
  }, [items]);

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 2xl:grid-cols-3">
      {connectors.map((connector) => (
        <section
          key={connector.connector}
          className={`rounded-xl border bg-white p-4 shadow-sm ${CONNECTOR_TONE[connector.worstStatus]}`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 shrink-0 text-gov-blue-600" />
                <h3 className="truncate text-base font-semibold text-gov-gray-900">
                  {prettifyConnectorName(connector.connector)}
                </h3>
              </div>
              <p className="mt-1 text-xs text-gov-gray-500">
                {connector.counts.ok} atualizado(s) • {connector.counts.warning + connector.counts.stale} alerta(s) •{" "}
                {connector.counts.error} erro(s) • {connector.counts.pending} pendente(s)
              </p>
            </div>
            <span className="inline-flex shrink-0 items-center rounded-full bg-gov-gray-100 px-2.5 py-1 text-xs font-medium text-gov-gray-700">
              {connector.jobs.length} jobs
            </span>
          </div>

          <div className="mt-4 space-y-2">
            {connector.jobs.map((job) => {
              const StatusIcon = STATUS_ICONS[job.status];
              const jobKey = `${job.connector}:${job.job}`;
              const run = latestRunsByJob.get(jobKey);
              const runBadge = getRunBadge(run);
              const runBadgeUI = getRunBadgeUI(runBadge);
              const runError = getErrorMessage(run?.errors);
              const isExpanded = expandedKey === jobKey;
              const targetId = `coverage-item-${jobKey.replace(/[^a-zA-Z0-9_-]/g, "_")}`;

              return (
                <div key={job.job} className="rounded-lg border border-gov-gray-200 bg-gov-gray-50/40">
                  <button
                    type="button"
                    className="flex w-full flex-col gap-2 px-3 py-2.5 text-left transition hover:bg-gov-gray-100/80 sm:grid sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:gap-3"
                    onClick={() => setExpandedKey(isExpanded ? null : jobKey)}
                    aria-expanded={isExpanded}
                    aria-controls={targetId}
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-gov-gray-900">
                        {job.job}
                      </p>
                      <p className="mt-0.5 truncate text-xs text-gov-gray-500">
                        {job.description || `Dominio: ${job.domain}`}
                        {job.enabled_in_mvp === false && (
                          <span className="ml-1.5 text-gov-gray-400">(desabilitado)</span>
                        )}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5 sm:justify-end">
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${coverageStatusColor(job.status)}`}
                      >
                        <StatusIcon className="h-3 w-3" />
                        {COVERAGE_STATUS_LABELS[job.status]}
                      </span>
                      {runBadgeUI && (
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${runBadgeUI.className}`}
                        >
                          <runBadgeUI.icon
                            className={`h-3 w-3 ${runBadge === "running" ? "animate-spin" : ""}`}
                          />
                          {runBadgeUI.label}
                        </span>
                      )}
                      {isExpanded ? (
                        <ChevronUp className="h-4 w-4 text-gov-gray-500" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-gov-gray-500" />
                      )}
                    </div>
                  </button>

                  {isExpanded && (
                    <div id={targetId} className="space-y-3 border-t border-gov-gray-200 px-3 py-3 text-xs text-gov-gray-600">
                      {run ? (
                        <>
                          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                            <div className="rounded bg-white px-2.5 py-2">
                              <p className="text-[11px] uppercase tracking-wide text-gov-gray-400">
                                Ultimo Status
                              </p>
                              <p className="mt-0.5 font-medium text-gov-gray-800">{run.status}</p>
                            </div>
                            <div className="rounded bg-white px-2.5 py-2">
                              <p className="text-[11px] uppercase tracking-wide text-gov-gray-400">
                                Itens Processados
                              </p>
                              <p className="mt-0.5 font-medium text-gov-gray-800">
                                {run.items_normalized} de {run.items_fetched}
                              </p>
                            </div>
                            {run.started_at && (
                              <div className="rounded bg-white px-2.5 py-2">
                                <p className="text-[11px] uppercase tracking-wide text-gov-gray-400">
                                  Inicio
                                </p>
                                <p className="mt-0.5 font-medium text-gov-gray-800">
                                  {formatDateTime(run.started_at)}
                                </p>
                              </div>
                            )}
                          {run.finished_at && (
                            <div className="rounded bg-white px-2.5 py-2">
                              <p className="text-[11px] uppercase tracking-wide text-gov-gray-400">
                                Fim
                              </p>
                                <p className="mt-0.5 font-medium text-gov-gray-800">
                                  {formatDateTime(run.finished_at)}
                              </p>
                            </div>
                          )}
                          {run.status === "completed" && run.items_fetched > 0 && (
                            <div className="sm:col-span-2">
                              <Link
                                href={`/coverage/run/${run.id}`}
                                className="inline-flex items-center rounded-md border border-gov-blue-200 bg-gov-blue-50 px-3 py-1.5 text-xs font-medium text-gov-blue-700 transition hover:bg-gov-blue-100"
                              >
                                Ver detalhe do que foi processado
                              </Link>
                            </div>
                          )}
                        </div>
                        {runError && (
                          <div className="rounded-md border border-red-200 bg-red-50 p-2 text-red-700">
                              <p className="font-medium">Erro reportado</p>
                              <p className="mt-1 break-words">{runError}</p>
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="rounded bg-white px-2.5 py-2">
                          Nenhuma execucao recente para este job.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {(connector.lastSuccessAt || connector.maxLagHours != null) && (
            <div className="mt-4 space-y-1 border-t border-gov-gray-100 pt-3 text-xs text-gov-gray-500">
              {connector.lastSuccessAt && (
                <div className="flex items-center gap-1">
                  <RefreshCw className="h-3 w-3" />
                  Ultima atualizacao: {formatDate(connector.lastSuccessAt)}
                </div>
              )}
              {connector.maxLagHours != null && (
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Maior atraso observado: {Math.round(connector.maxLagHours)}h
                </div>
              )}
            </div>
          )}
        </section>
      ))}
    </div>
  );
}
