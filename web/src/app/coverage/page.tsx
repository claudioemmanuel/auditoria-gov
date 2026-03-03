"use client";

import { useEffect, useMemo, useState } from "react";
import {
  getCoverageV2Analytics,
  getCoverageV2SourcePreview,
  getCoverageV2Sources,
  getCoverageV2Summary,
} from "@/lib/api";
import { Breadcrumb } from "@/components/Breadcrumb";
import { CoverageAnalyticsPanel } from "@/components/coverage/CoverageAnalyticsPanel";
import { CoverageFilterBar, type CoverageFilterState } from "@/components/coverage/CoverageFilterBar";
import { CoverageHeader } from "@/components/coverage/CoverageHeader";
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

const PAGE_LIMIT = 12;
const DEFAULT_FILTERS: CoverageFilterState = {
  q: "",
  status: "",
  domain: "",
  enabledOnly: false,
  sort: "status_desc",
};

const DOMAIN_OPTIONS = [
  "despesa",
  "contrato",
  "compra",
  "licitacao",
  "beneficio",
  "remuneracao",
  "sancao",
  "politico",
  "empresa",
  "pessoa",
  "juridico",
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
      .then((payload) => {
        if (!active) return;
        setSummary(payload);
      })
      .catch(() => {
        if (!active) return;
        setSummaryError("Não foi possível carregar o resumo da cobertura.");
      })
      .finally(() => {
        if (active) setSummaryLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    setSourcesLoading(true);
    setSourcesError(null);
    getCoverageV2Sources({
      offset,
      limit: PAGE_LIMIT,
      status: filters.status || undefined,
      domain: filters.domain || undefined,
      enabled_only: filters.enabledOnly,
      q: filters.q.trim() || undefined,
      sort: filters.sort,
    })
      .then((payload) => {
        if (!active) return;
        setSources(payload);
      })
      .catch(() => {
        if (!active) return;
        setSourcesError("Falha de rede ao carregar fontes. Verifique a API e tente novamente.");
      })
      .finally(() => {
        if (active) setSourcesLoading(false);
      });
    return () => {
      active = false;
    };
  }, [filters, offset]);

  useEffect(() => {
    if (!analyticsOpen || analytics || analyticsLoading) {
      return;
    }
    let active = true;
    setAnalyticsLoading(true);
    setAnalyticsError(null);
    getCoverageV2Analytics()
      .then((payload) => {
        if (!active) return;
        setAnalytics(payload);
      })
      .catch(() => {
        if (!active) return;
        setAnalyticsError("Não foi possível carregar a cobertura analítica.");
      })
      .finally(() => {
        if (active) setAnalyticsLoading(false);
      });
    return () => {
      active = false;
    };
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
      .then((payload) => {
        setPreviewData(payload);
      })
      .catch(() => {
        setPreviewError("Não foi possível carregar o diagnóstico detalhado desta fonte.");
      })
      .finally(() => {
        setPreviewLoading(false);
      });
  }

  return (
    <div>
      <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-6">
        <Breadcrumb items={[{ label: "Cobertura" }]} />

        {/* Page title + snapshot */}
        <CoverageHeader snapshotAt={summary?.snapshot_at} />

        {summaryError && (
          <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {summaryError}
          </div>
        )}

        {/* Summary KPI strip */}
        <CoverageSummaryStrip summary={summary} loading={summaryLoading} />

        {/* Pipeline step indicator */}
        <div className="mt-6">
          <CoveragePipelinePanel summary={summary} loading={summaryLoading} />
        </div>

        {/* Sources table */}
        <div className="mt-6 space-y-3">
          <CoverageFilterBar value={filters} domains={domains} onChange={handleFiltersChange} />

          {sourcesError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
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

        {/* Typology analytics (collapsible) */}
        <div className="mt-6">
          <CoverageAnalyticsPanel
            open={analyticsOpen}
            loading={analyticsLoading}
            data={analytics}
            onToggle={() => setAnalyticsOpen((prev) => !prev)}
          />
          {analyticsError && (
            <div className="mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
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
