"use client";

import type { CoverageV2SourceItem } from "@/lib/types";
import { coverageStatusColor, formatDateTime } from "@/lib/utils";
import { ChevronLeft, ChevronRight, Eye } from "lucide-react";

interface CoverageSourcesListProps {
  loading: boolean;
  items: CoverageV2SourceItem[];
  total: number;
  offset: number;
  limit: number;
  onOffsetChange: (nextOffset: number) => void;
  onPreview: (item: CoverageV2SourceItem) => void;
}

export function CoverageSourcesList({
  loading,
  items,
  total,
  offset,
  limit,
  onOffsetChange,
  onPreview,
}: CoverageSourcesListProps) {
  const nextOffset = offset + limit;
  const previousOffset = Math.max(offset - limit, 0);
  const hasPrevious = offset > 0;
  const hasNext = nextOffset < total;

  return (
    <div className="rounded-xl border border-gov-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gov-gray-600">Fontes e jobs monitorados</h2>
        <span className="text-xs text-gov-gray-500">{total} fonte(s)</span>
      </div>

      {loading ? (
        <div className="mt-3 space-y-2">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={`source-skeleton-${index}`} className="h-20 animate-pulse rounded-lg bg-gov-gray-100" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="mt-4 rounded-lg border border-gov-gray-200 bg-gov-gray-50 p-4 text-sm text-gov-gray-600">
          Nenhuma fonte encontrada para os filtros selecionados.
        </div>
      ) : (
        <div className="mt-3 space-y-2">
          {items.map((item) => (
            <article key={item.connector} className="rounded-lg border border-gov-gray-200 p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-gov-gray-900">{item.connector_label}</p>
                  <p className="text-xs text-gov-gray-500">
                    {item.job_count} jobs ({item.enabled_job_count} habilitados)
                  </p>
                </div>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${coverageStatusColor(item.worst_status)}`}>
                  {item.worst_status}
                </span>
              </div>

              <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-gov-gray-600 md:grid-cols-4">
                <p>OK: {item.status_counts.ok}</p>
                <p>Atencao: {item.status_counts.warning + item.status_counts.stale}</p>
                <p>Erro: {item.status_counts.error}</p>
                <p>Pendentes: {item.status_counts.pending}</p>
                <p>Running: {item.runtime.running_jobs}</p>
                <p>Travados: {item.runtime.stuck_jobs}</p>
                <p>Erro runtime: {item.runtime.error_jobs}</p>
                <p>
                  Ultimo sucesso: {item.last_success_at ? formatDateTime(item.last_success_at) : "Nao informado"}
                </p>
              </div>

              <div className="mt-3 flex justify-end">
                <button
                  type="button"
                  onClick={() => onPreview(item)}
                  className="inline-flex items-center gap-1 rounded-md border border-gov-blue-200 bg-gov-blue-50 px-3 py-1.5 text-xs font-medium text-gov-blue-700 hover:bg-gov-blue-100"
                >
                  <Eye className="h-3.5 w-3.5" />
                  Diagnosticar fonte
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      <div className="mt-3 flex items-center justify-between border-t border-gov-gray-100 pt-3">
        <p className="text-xs text-gov-gray-500">
          Mostrando {total === 0 ? 0 : offset + 1} - {Math.min(offset + limit, total)} de {total}
        </p>
        <div className="flex gap-1">
          <button
            type="button"
            disabled={!hasPrevious}
            onClick={() => onOffsetChange(previousOffset)}
            className="inline-flex items-center gap-1 rounded-md border border-gov-gray-200 px-2 py-1 text-xs text-gov-gray-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Anterior
          </button>
          <button
            type="button"
            disabled={!hasNext}
            onClick={() => onOffsetChange(nextOffset)}
            className="inline-flex items-center gap-1 rounded-md border border-gov-gray-200 px-2 py-1 text-xs text-gov-gray-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Proxima
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
