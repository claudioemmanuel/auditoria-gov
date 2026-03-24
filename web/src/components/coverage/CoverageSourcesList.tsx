"use client";

import { useEffect, useState } from "react";
import type { CoverageStatus, CoverageV2SourceItem, CoverageV2SourcePreviewResponse } from "@/lib/types";
import { getCoverageV2SourcePreview } from "@/lib/api";
import { cn, formatDateTime } from "@/lib/utils";
import { COVERAGE_STATUS_LABELS } from "@/lib/constants";
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Eye, Loader2, Search } from "lucide-react";

interface CoverageSourcesListProps {
  loading: boolean;
  items: CoverageV2SourceItem[];
  total: number;
  offset: number;
  limit: number;
  onOffsetChange: (nextOffset: number) => void;
  onPreview: (item: CoverageV2SourceItem) => void;
}

type SortKey = "status" | "name" | "freshness";

const STATUS_DOT: Record<CoverageStatus, string> = {
  ok: "bg-success",
  warning: "bg-amber",
  stale: "bg-amber",
  error: "bg-error",
  pending: "bg-placeholder",
};

const STATUS_TEXT: Record<CoverageStatus, string> = {
  ok: "text-success",
  warning: "text-amber",
  stale: "text-amber",
  error: "text-error",
  pending: "text-muted",
};

function statusOrder(s: CoverageStatus): number {
  return { error: 0, stale: 1, warning: 2, pending: 3, ok: 4 }[s] ?? 5;
}

function freshnessHours(item: CoverageV2SourceItem): number {
  if (item.max_freshness_lag_hours != null) return item.max_freshness_lag_hours;
  if (!item.last_success_at) return Number.MAX_SAFE_INTEGER;
  const diffMs = Date.now() - new Date(item.last_success_at).getTime();
  return diffMs / (1000 * 60 * 60);
}

function sortItems(items: CoverageV2SourceItem[], key: SortKey): CoverageV2SourceItem[] {
  return [...items].sort((a, b) => {
    if (key === "status") return statusOrder(a.worst_status) - statusOrder(b.worst_status);
    if (key === "name") return a.connector_label.localeCompare(b.connector_label, "pt-BR");
    if (key === "freshness") return freshnessHours(b) - freshnessHours(a);
    return 0;
  });
}

function formatLag(item: CoverageV2SourceItem): string {
  const hours = freshnessHours(item);
  if (hours === Number.MAX_SAFE_INTEGER) return "—";
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  if (hours < 24) return `${Math.round(hours)}h`;
  return `${Math.round(hours / 24)}d`;
}

function totalItems(item: CoverageV2SourceItem): number {
  return (
    item.status_counts.ok +
    item.status_counts.warning +
    item.status_counts.stale +
    item.status_counts.error +
    item.status_counts.pending
  );
}

interface ExpandedRowProps {
  connector: string;
}

function ExpandedRow({ connector }: ExpandedRowProps) {
  const [data, setData] = useState<CoverageV2SourcePreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCoverageV2SourcePreview(connector, { runs_limit: 3 })
      .then((payload) => {
        setData(payload);
      })
      .catch(() => {
        setError("Não foi possível carregar execuções recentes.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [connector]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-4 py-3 text-xs text-muted">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Carregando execuções...
      </div>
    );
  }

  if (error) {
    return <div className="px-4 py-3 text-xs text-error">{error}</div>;
  }

  if (!data || data.recent_runs.length === 0) {
    return <div className="px-4 py-3 text-xs text-muted">Nenhuma execução recente encontrada.</div>;
  }

  return (
    <div className="space-y-1.5 px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">Últimas execuções</p>
      {data.recent_runs.slice(0, 3).map((run) => (
        <div key={run.id} className="flex flex-wrap items-center gap-3 rounded-lg bg-surface-subtle px-3 py-2 text-xs">
          <span
            className={cn(
              "font-medium",
              run.status === "completed"
                ? "text-success"
                : run.is_stuck
                  ? "text-error"
                  : run.status === "error" && run.is_retryable_error
                    ? "text-amber"
                    : run.status === "error"
                      ? "text-error"
                      : "text-muted",
            )}
          >
            {run.is_stuck ? "travada" : run.status === "error" && run.is_retryable_error ? "api externa" : run.status}
            {run.is_stuck ? "" : ""}
          </span>
          {run.started_at && (
            <span className="text-muted">{formatDateTime(run.started_at)}</span>
          )}
          <span className="font-mono tabular-nums text-secondary">
            {run.items_fetched.toLocaleString("pt-BR")} coletados / {run.items_normalized.toLocaleString("pt-BR")} norm.
          </span>
        </div>
      ))}
    </div>
  );
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
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("status");
  const [expandedConnectors, setExpandedConnectors] = useState<Set<string>>(new Set());

  const nextOffset = offset + limit;
  const previousOffset = Math.max(offset - limit, 0);
  const hasPrevious = offset > 0;
  const hasNext = nextOffset < total;

  const filtered = search.trim()
    ? items.filter((item) =>
        item.connector_label.toLowerCase().includes(search.toLowerCase()) ||
        item.connector.toLowerCase().includes(search.toLowerCase()),
      )
    : items;

  const sorted = sortItems(filtered, sortKey);

  function toggleExpand(connector: string) {
    setExpandedConnectors((prev) => {
      const next = new Set(prev);
      if (next.has(connector)) {
        next.delete(connector);
      } else {
        next.add(connector);
      }
      return next;
    });
  }

  return (
    <div className="rounded-xl border border-border bg-surface-card shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-3">
        <h2 className="font-display flex-1 text-sm font-semibold text-primary">Fontes de Dados</h2>
        <span className="font-mono tabular-nums text-xs text-muted">{total} fonte(s)</span>

        {/* Inline search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar fonte..."
            className="rounded-lg border border-border bg-surface-base py-1.5 pl-8 pr-3 text-xs text-primary placeholder:text-muted focus:border-accent focus:outline-none"
          />
        </div>

        {/* Sort */}
        <select
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value as SortKey)}
          className="rounded-lg border border-border bg-surface-base px-2 py-1.5 text-xs text-primary focus:outline-none"
        >
          <option value="status">Por status</option>
          <option value="name">Por nome</option>
          <option value="freshness">Por defasagem</option>
        </select>
      </div>

      {/* Body */}
      {loading ? (
        <div className="space-y-px">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={`source-skeleton-${index}`} className="h-14 animate-pulse bg-surface-subtle" />
          ))}
        </div>
      ) : sorted.length === 0 ? (
        <div className="px-4 py-8 text-center text-sm text-muted">
          Nenhuma fonte encontrada para os filtros selecionados.
        </div>
      ) : (
        <div className="divide-y divide-border">
          {sorted.map((item) => {
            const isExpanded = expandedConnectors.has(item.connector);
            const lag = formatLag(item);
            const itemCount = totalItems(item);

            return (
              <div key={item.connector}>
                <div className="flex items-center gap-3 px-4 py-3">
                  {/* Status dot */}
                  <span
                    className={cn("h-2.5 w-2.5 flex-shrink-0 rounded-full", STATUS_DOT[item.worst_status])}
                    title={COVERAGE_STATUS_LABELS[item.worst_status] ?? item.worst_status}
                  />

                  {/* Source name + status label */}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-primary">{item.connector_label}</p>
                    <p className={cn("text-xs", STATUS_TEXT[item.worst_status])}>
                      {COVERAGE_STATUS_LABELS[item.worst_status] ?? item.worst_status}
                    </p>
                  </div>

                  {/* Lag */}
                  <div className="hidden min-w-[48px] text-right sm:block">
                    <p className="font-mono tabular-nums text-xs text-secondary">{lag}</p>
                    <p className="text-[10px] text-muted">defasagem</p>
                  </div>

                  {/* Item count */}
                  <div className="hidden min-w-[64px] text-right md:block">
                    <p className="font-mono tabular-nums text-xs text-secondary">
                      {itemCount.toLocaleString("pt-BR")} itens
                    </p>
                    <p className="text-[10px] text-muted">{item.enabled_job_count} job(s)</p>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-shrink-0 items-center gap-1">
                    <button
                      type="button"
                      onClick={() => toggleExpand(item.connector)}
                      className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-secondary hover:bg-surface-subtle"
                      aria-label={isExpanded ? "Recolher" : "Expandir execuções"}
                    >
                      {isExpanded ? (
                        <ChevronUp className="h-3.5 w-3.5" />
                      ) : (
                        <ChevronDown className="h-3.5 w-3.5" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => onPreview(item)}
                      className="inline-flex items-center gap-1 rounded-md border border-border bg-accent-subtle px-2 py-1 text-xs text-accent hover:opacity-80"
                      aria-label="Diagnosticar fonte"
                    >
                      <Eye className="h-3.5 w-3.5" />
                      <span className="hidden sm:inline">Diagnosticar</span>
                    </button>
                  </div>
                </div>

                {/* Expanded runs */}
                {isExpanded && (
                  <div className="border-t border-border bg-surface-subtle">
                    <ExpandedRow connector={item.connector} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between border-t border-border px-4 py-3">
        <p className="font-mono tabular-nums text-xs text-muted">
          {total === 0 ? "0" : `${offset + 1}–${Math.min(offset + limit, total)}`} de {total}
        </p>
        <div className="flex gap-1">
          <button
            type="button"
            disabled={!hasPrevious}
            onClick={() => onOffsetChange(previousOffset)}
            className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-secondary disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Anterior
          </button>
          <button
            type="button"
            disabled={!hasNext}
            onClick={() => onOffsetChange(nextOffset)}
            className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-secondary disabled:cursor-not-allowed disabled:opacity-40"
          >
            Próxima
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
