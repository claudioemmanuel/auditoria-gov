"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  getRadarV2CasePreview,
  getRadarV2Cases,
  getRadarV2Coverage,
  getRadarV2SignalPreview,
  getRadarV2Signals,
  getRadarV2Summary,
} from "@/lib/api";
import type {
  RadarV2CaseItem,
  RadarV2CasePreviewResponse,
  RadarV2CoverageResponse,
  RadarV2SignalItem,
  RadarV2SignalPreviewResponse,
  RadarV2SummaryResponse,
} from "@/lib/types";
import { TableSkeleton } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { RadarViewTabs, type RadarViewMode } from "@/components/radar/RadarViewTabs";
import { RadarFilterPanel } from "@/components/radar/RadarFilterPanel";
import { RadarSignalsList } from "@/components/radar/RadarSignalsList";
import { RadarCasesList } from "@/components/radar/RadarCasesList";
import { RadarPreviewDrawer } from "@/components/radar/RadarPreviewDrawer";
import { RadarCoveragePanel } from "@/components/radar/RadarCoveragePanel";
import { AlertTriangle, ArrowUpDown, ChevronLeft, ChevronRight, Search, ShieldCheck } from "lucide-react";
import { cn, formatNumber } from "@/lib/utils";

const PAGE_SIZE = 20;

export default function RadarPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Read filter state from URL
  const view = (searchParams.get("view") as RadarViewMode) || "signals";
  const typology = searchParams.get("typology") || "";
  const severity = searchParams.get("severity") || "";
  const sort = (searchParams.get("sort") as "analysis_date" | "ingestion_date") || "analysis_date";
  const periodFrom = searchParams.get("period_from") || "";
  const periodTo = searchParams.get("period_to") || "";
  const corruptionType = searchParams.get("corruption_type") || "";
  const sphere = searchParams.get("sphere") || "";
  const offsetParam = Number(searchParams.get("offset") || "0");

  const [search, setSearch] = useState("");

  const updateParam = useCallback(
    (updates: Record<string, string>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value) {
          params.set(key, value);
        } else {
          params.delete(key);
        }
      }
      router.replace(`?${params.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  const setView = (next: RadarViewMode) => updateParam({ view: next, offset: "" });
  const setTypology = (v: string) => updateParam({ typology: v, offset: "" });
  const setSeverity = (v: string) => updateParam({ severity: v, offset: "" });
  const setSort = (v: string) => updateParam({ sort: v, offset: "" });
  const setPeriodFrom = (v: string) => updateParam({ period_from: v, offset: "" });
  const setPeriodTo = (v: string) => updateParam({ period_to: v, offset: "" });
  const setCorruptionType = (v: string) => updateParam({ corruption_type: v, offset: "" });
  const setSphere = (v: string) => updateParam({ sphere: v, offset: "" });
  const setOffset = (v: number) => updateParam({ offset: v > 0 ? String(v) : "" });

  const clearAllFilters = () => {
    router.replace("?", { scroll: false });
    setSearch("");
  };

  // Data state
  const [summary, setSummary] = useState<RadarV2SummaryResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  const [signals, setSignals] = useState<RadarV2SignalItem[]>([]);
  const [cases, setCases] = useState<RadarV2CaseItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewType, setPreviewType] = useState<"signal" | "case" | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [signalPreview, setSignalPreview] = useState<RadarV2SignalPreviewResponse | null>(null);
  const [casePreview, setCasePreview] = useState<RadarV2CasePreviewResponse | null>(null);

  const [coverageOpen, setCoverageOpen] = useState(false);
  const [coverageLoading, setCoverageLoading] = useState(false);
  const [coverageError, setCoverageError] = useState<string | null>(null);
  const [coverage, setCoverage] = useState<RadarV2CoverageResponse | null>(null);

  useEffect(() => {
    setSummaryLoading(true);
    getRadarV2Summary({
      typology: typology || undefined,
      severity: severity || undefined,
      period_from: periodFrom || undefined,
      period_to: periodTo || undefined,
      corruption_type: corruptionType || undefined,
      sphere: sphere || undefined,
    })
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setSummaryLoading(false));
  }, [typology, severity, periodFrom, periodTo, corruptionType, sphere]);

  useEffect(() => {
    setLoading(true);
    setError(null);

    const commonParams = {
      offset: offsetParam,
      limit: PAGE_SIZE,
      typology: typology || undefined,
      severity: severity || undefined,
      period_from: periodFrom || undefined,
      period_to: periodTo || undefined,
      corruption_type: corruptionType || undefined,
      sphere: sphere || undefined,
    };

    const task =
      view === "signals"
        ? getRadarV2Signals({ ...commonParams, sort })
        : getRadarV2Cases(commonParams);

    task
      .then((data) => {
        setTotal(data.total);
        if (view === "signals") {
          setSignals(data.items as RadarV2SignalItem[]);
          setCases([]);
        } else {
          setCases(data.items as RadarV2CaseItem[]);
          setSignals([]);
        }
      })
      .catch(() => setError("Erro ao carregar dados do Radar"))
      .finally(() => setLoading(false));
  }, [view, offsetParam, typology, severity, sort, periodFrom, periodTo, corruptionType, sphere]);

  const openSignalPreview = (signalId: string) => {
    setPreviewOpen(true);
    setPreviewType("signal");
    setPreviewLoading(true);
    setPreviewError(null);
    setSignalPreview(null);
    setCasePreview(null);
    getRadarV2SignalPreview(signalId, { limit: 10 })
      .then(setSignalPreview)
      .catch(() => setPreviewError("Nao foi possivel carregar a previa do sinal"))
      .finally(() => setPreviewLoading(false));
  };

  const openCasePreview = (caseId: string) => {
    setPreviewOpen(true);
    setPreviewType("case");
    setPreviewLoading(true);
    setPreviewError(null);
    setSignalPreview(null);
    setCasePreview(null);
    getRadarV2CasePreview(caseId)
      .then(setCasePreview)
      .catch(() => setPreviewError("Nao foi possivel carregar a previa do caso"))
      .finally(() => setPreviewLoading(false));
  };

  const openCoverage = () => {
    setCoverageOpen(true);
    if (coverage || coverageLoading) return;
    setCoverageLoading(true);
    setCoverageError(null);
    getRadarV2Coverage()
      .then(setCoverage)
      .catch(() => setCoverageError("Nao foi possivel carregar a cobertura analitica"))
      .finally(() => setCoverageLoading(false));
  };

  const hasData = view === "signals" ? signals.length > 0 : cases.length > 0;
  const listLabel = view === "signals" ? "sinais" : "casos";
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offsetParam / PAGE_SIZE) + 1;

  return (
    <div className="pt-14 lg:pt-0">
      {/* Page header */}
      <div className="border-b border-border bg-surface-card px-4 py-4 lg:px-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-primary">Radar de Riscos</h1>
            <p className="mt-0.5 text-xs text-muted">
              Monitoramento de sinais e casos de risco em tempo real
            </p>
          </div>
          <div className="flex items-center gap-3">
            {!summaryLoading && summary && (
              <span className="font-mono text-sm font-semibold tabular-nums text-secondary">
                {formatNumber(summary.totals.signals)} sinais
              </span>
            )}
            <button
              type="button"
              onClick={openCoverage}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-accent-subtle px-3 py-1.5 text-xs font-medium text-accent hover:bg-accent-subtle/80"
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              Confiabilidade
            </button>
          </div>
        </div>
      </div>

      {/* 2-column body */}
      <div className="flex min-h-0 flex-col gap-4 p-4 lg:flex-row lg:items-start lg:gap-6 lg:p-6">
        {/* Left: filter panel */}
        <RadarFilterPanel
          view={view}
          typology={typology}
          severity={severity}
          periodFrom={periodFrom}
          periodTo={periodTo}
          corruptionType={corruptionType}
          sphere={sphere}
          onTypologyChange={setTypology}
          onSeverityChange={setSeverity}
          onPeriodFromChange={setPeriodFrom}
          onPeriodToChange={setPeriodTo}
          onCorruptionTypeChange={setCorruptionType}
          onSphereChange={setSphere}
          onClearAll={clearAllFilters}
        />

        {/* Right: main content */}
        <div className="flex min-w-0 flex-1 flex-col gap-4">
          {/* Tabs + search + sort bar */}
          <div className="flex flex-wrap items-center gap-3">
            <RadarViewTabs
              value={view}
              onChange={(next) => setView(next)}
            />

            <div className="ml-auto flex items-center gap-2">
              {/* Search input */}
              <label className="flex items-center gap-2 rounded-lg border border-border bg-surface-card px-3 py-1.5 shadow-sm">
                <Search className="h-3.5 w-3.5 flex-shrink-0 text-muted" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Buscar..."
                  className="w-40 bg-transparent text-xs text-primary outline-none placeholder:text-muted"
                />
              </label>

              {/* Sort — only for signals */}
              {view === "signals" && (
                <label className="flex items-center gap-2 rounded-lg border border-border bg-surface-card px-3 py-1.5 shadow-sm">
                  <ArrowUpDown className="h-3.5 w-3.5 flex-shrink-0 text-muted" />
                  <select
                    value={sort}
                    onChange={(e) => setSort(e.target.value)}
                    className="bg-transparent text-xs text-primary outline-none"
                  >
                    <option value="analysis_date">Data de analise</option>
                    <option value="ingestion_date">Data de ingestao</option>
                  </select>
                </label>
              )}
            </div>
          </div>

          {/* Table area */}
          {loading ? (
            <TableSkeleton rows={8} />
          ) : error ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50 py-12">
              <AlertTriangle className="h-8 w-8 text-red-400" />
              <p className="mt-2 text-sm text-red-600">{error}</p>
            </div>
          ) : hasData ? (
            view === "signals" ? (
              <RadarSignalsList items={signals} onOpenPreview={openSignalPreview} />
            ) : (
              <RadarCasesList items={cases} onOpenPreview={openCasePreview} />
            )
          ) : (
            <EmptyState
              icon={AlertTriangle}
              title={`Nenhum ${listLabel} encontrado`}
              description="Ajuste os filtros para ampliar a busca investigativa."
            />
          )}

          {/* Pagination */}
          {!loading && !error && total > PAGE_SIZE && (
            <div className="flex items-center justify-between border-t border-border pt-3">
              <p className="font-mono text-xs tabular-nums text-muted">
                {offsetParam + 1}–{Math.min(offsetParam + PAGE_SIZE, total)} de {formatNumber(total)}
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={offsetParam === 0}
                  onClick={() => setOffset(Math.max(0, offsetParam - PAGE_SIZE))}
                  className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-card px-3 py-1.5 text-xs font-medium text-secondary transition hover:bg-surface-subtle disabled:opacity-50"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                  Anterior
                </button>
                <span className="text-xs text-muted">
                  Pg <span className="font-mono tabular-nums">{currentPage}</span>/<span className="font-mono tabular-nums">{totalPages}</span>
                </span>
                <button
                  type="button"
                  disabled={offsetParam + PAGE_SIZE >= total}
                  onClick={() => setOffset(offsetParam + PAGE_SIZE)}
                  className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-card px-3 py-1.5 text-xs font-medium text-secondary transition hover:bg-surface-subtle disabled:opacity-50"
                >
                  Proxima
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <RadarPreviewDrawer
        open={previewOpen}
        type={previewType}
        loading={previewLoading}
        error={previewError}
        signalPreview={signalPreview}
        casePreview={casePreview}
        onClose={() => {
          setPreviewOpen(false);
          setPreviewType(null);
          setPreviewError(null);
          setSignalPreview(null);
          setCasePreview(null);
        }}
      />

      <RadarCoveragePanel
        open={coverageOpen}
        loading={coverageLoading}
        error={coverageError}
        data={coverage}
        onClose={() => setCoverageOpen(false)}
      />
    </div>
  );
}
