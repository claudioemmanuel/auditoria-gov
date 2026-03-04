"use client";

import { useEffect, useMemo, useState } from "react";
import {
  getCoverageV2Analytics,
  getCoverageV2SourcePreview,
  getCoverageV2Sources,
  getCoverageV2Summary,
} from "@/lib/api";
import { CoverageAnalyticsPanel } from "@/components/coverage/CoverageAnalyticsPanel";
import { CoverageFilterBar, type CoverageFilterState } from "@/components/coverage/CoverageFilterBar";
import { CoveragePipelinePanel } from "@/components/coverage/CoveragePipelinePanel";
import { CoverageSourcePreviewDrawer } from "@/components/coverage/CoverageSourcePreviewDrawer";
import { CoverageSourcesList } from "@/components/coverage/CoverageSourcesList";
import { CoverageSummaryStrip } from "@/components/coverage/CoverageSummaryStrip";
import type {
  CoverageV2AnalyticsResponse,
  CoverageV2SourcePreviewResponse,
  CoverageV2SourcesResponse,
  CoverageV2SummaryResponse,
} from "@/lib/types";
import { Database, Clock } from "lucide-react";

const PAGE_LIMIT = 12;
const DEFAULT_FILTERS: CoverageFilterState = {
  q: "",
  status: "",
  domain: "",
  enabledOnly: false,
  sort: "status_desc",
};

const DOMAIN_OPTIONS = [
  "despesa", "contrato", "compra", "licitacao", "beneficio",
  "remuneracao", "sancao", "politico", "empresa", "pessoa", "juridico",
];

export default function CoveragePage() {
  const [summary, setSummary] = useState<CoverageV2SummaryResponse | null>(null);
  const [sources, setSources] = useState<CoverageV2SourcesResponse | null>(null);
  const [analytics, setAnalytics] = useState<CoverageV2AnalyticsResponse | null>(null);

  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [sourcesError, setSourcesError] = useState<string | null>(null);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

  const [summaryLoading, setSummaryLoading] = useState(true);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  const [filters, setFilters] = useState<CoverageFilterState>(DEFAULT_FILTERS);
  const [offset, setOffset] = useState(0);
  const [analyticsOpen, setAnalyticsOpen] = useState(false);

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<CoverageV2SourcePreviewResponse | null>(null);

  useEffect(() => {
    let active = true;
    setSummaryLoading(true);
    setSummaryError(null);
    getCoverageV2Summary()
      .then((p) => { if (active) setSummary(p); })
      .catch(() => { if (active) setSummaryError("Não foi possível carregar o resumo da cobertura."); })
      .finally(() => { if (active) setSummaryLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    setSourcesLoading(true);
    setSourcesError(null);
    getCoverageV2Sources({
      offset, limit: PAGE_LIMIT,
      status: filters.status || undefined,
      domain: filters.domain || undefined,
      enabled_only: filters.enabledOnly,
      q: filters.q.trim() || undefined,
      sort: filters.sort,
    })
      .then((p) => { if (active) setSources(p); })
      .catch(() => { if (active) setSourcesError("Falha de rede ao carregar fontes. Verifique a API e tente novamente."); })
      .finally(() => { if (active) setSourcesLoading(false); });
    return () => { active = false; };
  }, [filters, offset]);

  useEffect(() => {
    if (!analyticsOpen || analytics || analyticsLoading) return;
    let active = true;
    setAnalyticsLoading(true);
    setAnalyticsError(null);
    getCoverageV2Analytics()
      .then((p) => { if (active) setAnalytics(p); })
      .catch(() => { if (active) setAnalyticsError("Não foi possível carregar a cobertura analítica."); })
      .finally(() => { if (active) setAnalyticsLoading(false); });
    return () => { active = false; };
  }, [analyticsOpen, analytics, analyticsLoading]);

  const domains = useMemo(() => DOMAIN_OPTIONS, []);

  function handleFiltersChange(next: CoverageFilterState) {
    setFilters(next);
    setOffset(0);
  }

  function handlePreview(connector: string) {
    setPreviewOpen(true);
    setPreviewLoading(true);
    setPreviewError(null);
    setPreviewData(null);
    getCoverageV2SourcePreview(connector, { runs_limit: 12 })
      .then(setPreviewData)
      .catch(() => setPreviewError("Não foi possível carregar o diagnóstico detalhado desta fonte."))
      .finally(() => setPreviewLoading(false));
  }

  return (
    <div className="min-h-screen">

      {/* ── Page header ────────────────────────────────────────── */}
      <div className="border-b border-border bg-surface-card">
        <div className="mx-auto max-w-[1280px] px-4 py-5 sm:px-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent-subtle border border-accent/20">
                <Database className="h-5 w-5 text-accent" />
              </div>
              <div>
                <h1 className="font-display text-xl font-bold text-primary">Cobertura de Dados</h1>
                <p className="text-xs text-muted">Saúde do pipeline e qualidade operacional por fonte</p>
              </div>
            </div>

            {/* Snapshot timestamp */}
            <div className="shrink-0 rounded-lg border border-border bg-surface-base px-3 py-2 text-right">
              <p className="flex items-center gap-1 font-mono text-[10px] font-semibold uppercase tracking-wide text-muted">
                <Clock className="h-3 w-3" />
                Snapshot
              </p>
              <p className="mt-0.5 font-mono tabular-nums text-xs font-medium text-primary">
                {summary?.snapshot_at
                  ? new Date(summary.snapshot_at).toLocaleString("pt-BR")
                  : "Aguardando dados"}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Body ───────────────────────────────────────────────── */}
      <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-6 space-y-6">

        {summaryError && (
          <div className="rounded-lg border border-error/20 bg-error-subtle px-3 py-2 text-sm text-error">
            {summaryError}
          </div>
        )}

        {/* KPI strip */}
        <CoverageSummaryStrip summary={summary} loading={summaryLoading} />

        {/* Pipeline steps */}
        <CoveragePipelinePanel summary={summary} loading={summaryLoading} />

        {/* Sources */}
        <div className="space-y-3">
          <CoverageFilterBar value={filters} domains={domains} onChange={handleFiltersChange} />

          {sourcesError && (
            <div className="rounded-lg border border-error/20 bg-error-subtle px-3 py-2 text-sm text-error">
              {sourcesError}
            </div>
          )}

          <CoverageSourcesList
            loading={sourcesLoading}
            items={sources?.items ?? []}
            total={sources?.total ?? 0}
            offset={sources?.offset ?? 0}
            limit={sources?.limit ?? PAGE_LIMIT}
            onOffsetChange={setOffset}
            onPreview={(item) => handlePreview(item.connector)}
          />
        </div>

        {/* Analytics panel */}
        <div>
          <CoverageAnalyticsPanel
            open={analyticsOpen}
            loading={analyticsLoading}
            data={analytics}
            onToggle={() => setAnalyticsOpen((prev) => !prev)}
          />
          {analyticsError && (
            <div className="mt-2 rounded-lg border border-error/20 bg-error-subtle px-3 py-2 text-sm text-error">
              {analyticsError}
            </div>
          )}
        </div>
      </div>

      <CoverageSourcePreviewDrawer
        open={previewOpen}
        loading={previewLoading}
        error={previewError}
        data={previewData}
        onClose={() => setPreviewOpen(false)}
      />
    </div>
  );
}
