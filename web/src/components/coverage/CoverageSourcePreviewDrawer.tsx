"use client";

import Link from "next/link";
import type { CoverageV2SourcePreviewResponse } from "@/lib/types";
import { coverageStatusColor, formatDateTime } from "@/lib/utils";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface CoverageSourcePreviewDrawerProps {
  open: boolean;
  loading: boolean;
  error: string | null;
  data: CoverageV2SourcePreviewResponse | null;
  onClose: () => void;
}

export function CoverageSourcePreviewDrawer({
  open,
  loading,
  error,
  data,
  onClose,
}: CoverageSourcePreviewDrawerProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30">
      <div className="h-full w-full max-w-2xl overflow-y-auto bg-surface-card p-4 shadow-2xl">
        <div className="flex items-start justify-between gap-3 border-b border-border pb-3">
          <div>
            <h3 className="text-lg font-semibold text-primary">Diagnostico da fonte</h3>
            <p className="text-xs text-muted">Drill-down operacional sem sair da cobertura.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-muted hover:bg-surface-subtle"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {loading && (
          <p className="mt-4 text-sm text-muted">Carregando preview da fonte...</p>
        )}
        {error && (
          <p className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>
        )}

        {!loading && !error && data && (
          <div className="mt-4 space-y-4">
            {/* Connector summary */}
            <div className="rounded-lg border border-border bg-surface-card p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-base font-semibold text-primary">{data.connector.connector_label}</p>
                  <p className="text-xs text-muted">
                    {data.connector.job_count} jobs ({data.connector.enabled_job_count} habilitados)
                  </p>
                </div>
                <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", coverageStatusColor(data.connector.worst_status))}>
                  {data.connector.worst_status}
                </span>
              </div>
            </div>

            {/* Insights */}
            <div className="rounded-lg border border-border p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Insights</p>
              <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-secondary">
                {data.insights.map((insight) => (
                  <li key={insight}>{insight}</li>
                ))}
              </ul>
            </div>

            {/* Jobs */}
            <div className="rounded-lg border border-border p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Jobs</p>
              <div className="mt-2 space-y-2">
                {data.jobs.map((job) => (
                  <div key={job.job} className="rounded-md bg-surface-subtle p-2">
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className="text-sm font-medium text-primary">{job.job}</p>
                        <p className="text-xs text-muted">{job.domain}</p>
                      </div>
                      <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", coverageStatusColor(job.status))}>
                        {job.status}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-muted">
                      Ultimo sucesso: {job.last_success_at ? formatDateTime(job.last_success_at) : "Nao informado"}
                    </p>
                    {job.latest_run && (
                      <div className="mt-2 rounded border border-border bg-surface-card p-2 text-xs text-secondary">
                        <p>
                          Execucao mais recente:{" "}
                          <span className="font-medium">{job.latest_run.status}</span>
                          {job.latest_run.is_stuck ? " (travada)" : ""}
                        </p>
                        <p className="font-mono tabular-nums">
                          Itens: {job.latest_run.items_fetched.toLocaleString("pt-BR")} coletados /{" "}
                          {job.latest_run.items_normalized.toLocaleString("pt-BR")} normalizados
                        </p>
                        <div className="mt-1">
                          <Link
                            href={`/coverage/run/${job.latest_run.id}`}
                            className="text-accent underline"
                          >
                            Abrir detalhe da execucao
                          </Link>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Recent runs */}
            <div className="rounded-lg border border-border p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Execucoes recentes</p>
              <div className="mt-2 space-y-2">
                {data.recent_runs.map((run) => (
                  <div key={run.id} className="rounded-md bg-surface-subtle p-2 text-xs text-secondary">
                    <p className="font-medium">
                      {run.status}
                      {run.is_stuck ? " (travada)" : ""}
                    </p>
                    <p>Inicio: {run.started_at ? formatDateTime(run.started_at) : "Nao informado"}</p>
                    <p>Fim: {run.finished_at ? formatDateTime(run.finished_at) : "Em andamento"}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
