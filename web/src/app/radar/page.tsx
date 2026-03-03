"use client";

import { useEffect, useMemo, useState } from "react";
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
import { Breadcrumb } from "@/components/Breadcrumb";
import { TableSkeleton } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { RadarHeader } from "@/components/radar/RadarHeader";
import { RadarSummaryStrip } from "@/components/radar/RadarSummaryStrip";
import { RadarViewTabs, type RadarViewMode } from "@/components/radar/RadarViewTabs";
import { RadarFilterBar } from "@/components/radar/RadarFilterBar";
import { RadarSignalsList } from "@/components/radar/RadarSignalsList";
import { RadarCasesList } from "@/components/radar/RadarCasesList";
import { RadarPreviewDrawer } from "@/components/radar/RadarPreviewDrawer";
import { RadarCoveragePanel } from "@/components/radar/RadarCoveragePanel";
import { AlertTriangle, ChevronLeft, ChevronRight, ShieldCheck } from "lucide-react";

const PAGE_SIZE = 20;

export default function RadarPage() {
  const [view, setView] = useState<RadarViewMode>("signals");

  const [typology, setTypology] = useState("");
  const [severity, setSeverity] = useState("");
  const [sort, setSort] = useState<"analysis_date" | "ingestion_date">("analysis_date");
  const [periodFrom, setPeriodFrom] = useState("");
  const [periodTo, setPeriodTo] = useState("");
  const [corruptionType, setCorruptionType] = useState("");
  const [sphere, setSphere] = useState("");

  const [offset, setOffset] = useState(0);

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
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const queryView = params.get("view");
    if (queryView === "signals" || queryView === "cases") {
      setView(queryView);
      return;
    }
    const stored = window.localStorage.getItem("radar:last-view");
    if (stored === "signals" || stored === "cases") {
      setView(stored);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("radar:last-view", view);
  }, [view]);

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
      offset,
      limit: PAGE_SIZE,
      typology: typology || undefined,
      severity: severity || undefined,
      period_from: periodFrom || undefined,
      period_to: periodTo || undefined,
      corruption_type: corruptionType || undefined,
      sphere: sphere || undefined,
    };

    const task = view === "signals"
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
      .catch(() => setError("Erro ao carregar dados do Radar v2"))
      .finally(() => setLoading(false));
  }, [view, offset, typology, severity, sort, periodFrom, periodTo, corruptionType, sphere]);

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

  const clearAllFilters = () => {
    setTypology("");
    setSeverity("");
    setSort("analysis_date");
    setPeriodFrom("");
    setPeriodTo("");
    setCorruptionType("");
    setSphere("");
    setOffset(0);
  };

  const hasData = view === "signals" ? signals.length > 0 : cases.length > 0;

  const listLabel = useMemo(() => {
    if (view === "signals") return "sinais";
    return "casos";
  }, [view]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <Breadcrumb items={[{ label: "Radar" }]} />

      <RadarHeader />

      <RadarSummaryStrip
        summary={summary}
        loading={summaryLoading}
        activeSeverity={severity}
        onSeverityClick={(value) => {
          setSeverity((current) => (current === value ? "" : value));
          setOffset(0);
        }}
      />

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <RadarViewTabs
          value={view}
          onChange={(next) => {
            setView(next);
            setOffset(0);
          }}
        />
        <button
          type="button"
          onClick={openCoverage}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gov-blue-200 bg-gov-blue-50 px-3 py-1.5 text-xs font-medium text-gov-blue-700 hover:bg-gov-blue-100"
        >
          <ShieldCheck className="h-4 w-4" />
          Ver confiabilidade da analise
        </button>
      </div>

      <RadarFilterBar
        view={view}
        typology={typology}
        severity={severity}
        sort={sort}
        periodFrom={periodFrom}
        periodTo={periodTo}
        corruptionType={corruptionType}
        sphere={sphere}
        onTypologyChange={(value) => {
          setTypology(value);
          setOffset(0);
        }}
        onSeverityChange={(value) => {
          setSeverity(value);
          setOffset(0);
        }}
        onSortChange={(value) => {
          setSort(value);
          setOffset(0);
        }}
        onPeriodFromChange={(value) => {
          setPeriodFrom(value);
          setOffset(0);
        }}
        onPeriodToChange={(value) => {
          setPeriodTo(value);
          setOffset(0);
        }}
        onCorruptionTypeChange={(value) => {
          setCorruptionType(value);
          setOffset(0);
        }}
        onSphereChange={(value) => {
          setSphere(value);
          setOffset(0);
        }}
        onClearAll={clearAllFilters}
      />

      <div className="mt-6">
        {loading ? (
          <TableSkeleton rows={6} />
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
      </div>

      {!loading && !error && total > PAGE_SIZE && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-gov-gray-500">
            Mostrando {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} de {total}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              className="inline-flex items-center gap-1 rounded-md border border-gov-gray-300 bg-white px-3 py-1.5 text-sm transition hover:bg-gov-gray-50 disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" />
              Anterior
            </button>
            <button
              type="button"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
              className="inline-flex items-center gap-1 rounded-md border border-gov-gray-300 bg-white px-3 py-1.5 text-sm transition hover:bg-gov-gray-50 disabled:opacity-50"
            >
              Proximo
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

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
