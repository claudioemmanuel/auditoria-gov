"use client";

import { useEffect, useMemo, useState } from "react";
import { getCoverage, getCoverageMap, getIngestStatus, getRadar } from "@/lib/api";
import { CoveragePanel } from "@/components/CoveragePanel";
import { ProcessingStatus } from "@/components/ProcessingStatus";
import { GridSkeleton } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { Breadcrumb } from "@/components/Breadcrumb";
import type { CoverageItem, CoverageMapItem, IngestRun } from "@/lib/types";
import { Database, AlertTriangle, Activity, Play, CircleX, Workflow } from "lucide-react";

function isStuckRun(run: IngestRun): boolean {
  if (run.status !== "running" || !run.started_at) return false;
  const startedAt = new Date(run.started_at).getTime();
  if (Number.isNaN(startedAt)) return false;
  return Date.now() - startedAt > 20 * 60 * 1000;
}

export default function CoveragePage() {
  const [items, setItems] = useState<CoverageItem[]>([]);
  const [mapItems, setMapItems] = useState<CoverageMapItem[]>([]);
  const [mapMetric, setMapMetric] = useState<"coverage" | "freshness" | "risk">("coverage");
  const [recentRuns, setRecentRuns] = useState<IngestRun[]>([]);
  const [signalCount, setSignalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const latestRuns = useMemo(() => {
    const map = new Map<string, IngestRun>();
    for (const run of recentRuns) {
      const key = `${run.connector}:${run.job}`;
      if (!map.has(key)) map.set(key, run);
    }
    return Array.from(map.values());
  }, [recentRuns]);

  const summary = useMemo(() => {
    const connectors = new Set(items.map((i) => i.connector)).size;
    const running = latestRuns.filter((run) => run.status === "running").length;
    const stuck = latestRuns.filter(isStuckRun).length;
    const failed = latestRuns.filter((run) => run.status === "error").length + stuck;
    return {
      connectors,
      jobs: items.length,
      running,
      failed,
    };
  }, [items, latestRuns]);

  const ufMap = useMemo(() => {
    const map = new Map<string, CoverageMapItem>();
    for (const item of mapItems) map.set(item.code, item);
    return map;
  }, [mapItems]);

  const ufOrder = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
  ];

  function ufCellClass(item?: CoverageMapItem): string {
    if (!item) return "bg-gray-100 text-gray-400 border-gray-200";
    if (mapMetric === "risk") {
      if (item.risk_score >= 0.75) return "bg-red-100 text-red-700 border-red-200";
      if (item.risk_score >= 0.5) return "bg-amber-100 text-amber-700 border-amber-200";
      if (item.risk_score > 0) return "bg-blue-100 text-blue-700 border-blue-200";
      return "bg-gray-100 text-gray-500 border-gray-200";
    }
    if (mapMetric === "freshness") {
      if (item.freshness_hours == null) return "bg-gray-100 text-gray-500 border-gray-200";
      if (item.freshness_hours < 24) return "bg-emerald-100 text-emerald-700 border-emerald-200";
      if (item.freshness_hours < 72) return "bg-amber-100 text-amber-700 border-amber-200";
      return "bg-red-100 text-red-700 border-red-200";
    }
    if (item.coverage_score >= 0.75) return "bg-emerald-100 text-emerald-700 border-emerald-200";
    if (item.coverage_score >= 0.45) return "bg-amber-100 text-amber-700 border-amber-200";
    if (item.coverage_score > 0) return "bg-blue-100 text-blue-700 border-blue-200";
    return "bg-gray-100 text-gray-500 border-gray-200";
  }

  function ufCellMetric(item?: CoverageMapItem): string {
    if (!item) return "sem dados";
    if (mapMetric === "risk") return `${Math.round(item.risk_score * 100)}% risco`;
    if (mapMetric === "freshness") {
      if (item.freshness_hours == null) return "sem frescor";
      return `${Math.round(item.freshness_hours)}h`;
    }
    return `${Math.round(item.coverage_score * 100)}% cobertura`;
  }

  useEffect(() => {
    let active = true;

    Promise.allSettled([getCoverage(), getRadar({ limit: 1 }), getIngestStatus(), getCoverageMap({ layer: "uf", metric: mapMetric })])
      .then(([coverageResult, radarResult, ingestResult, mapResult]) => {
        if (!active) return;

        if (coverageResult.status === "fulfilled") {
          setItems(coverageResult.value);
        } else {
          setError("Erro ao carregar cobertura");
        }

        if (radarResult.status === "fulfilled") {
          setSignalCount(radarResult.value.total);
        }

        if (ingestResult.status === "fulfilled") {
          setRecentRuns(ingestResult.value.recent_runs);
        }

        if (mapResult.status === "fulfilled") {
          setMapItems(mapResult.value.items);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [mapMetric]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <Breadcrumb items={[{ label: "Cobertura" }]} />

      <div className="mt-4 flex items-center gap-3">
        <Database className="h-7 w-7 text-gov-blue-600" />
        <div>
          <h1 className="text-2xl font-bold text-gov-gray-900">
            Cobertura de Dados
          </h1>
          <p className="text-sm text-gov-gray-500">
            Status e atualidade das fontes de dados integradas
          </p>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div
              key={`summary-skeleton-${i}`}
              className="h-24 animate-pulse rounded-xl border border-gov-gray-200 bg-white"
            />
          ))
        ) : (
          <>
            <div className="rounded-xl border border-gov-gray-200 bg-white p-4">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium uppercase tracking-wide text-gov-gray-500">
                  Fontes Monitoradas
                </p>
                <Database className="h-4 w-4 text-gov-blue-600" />
              </div>
              <p className="mt-2 text-2xl font-semibold text-gov-gray-900">{summary.connectors}</p>
            </div>
            <div className="rounded-xl border border-gov-gray-200 bg-white p-4">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium uppercase tracking-wide text-gov-gray-500">
                  Jobs Catalogados
                </p>
                <Workflow className="h-4 w-4 text-gov-blue-600" />
              </div>
              <p className="mt-2 text-2xl font-semibold text-gov-gray-900">{summary.jobs}</p>
            </div>
            <div className="rounded-xl border border-gov-gray-200 bg-white p-4">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium uppercase tracking-wide text-gov-gray-500">
                  Em Execucao
                </p>
                <Play className="h-4 w-4 text-gov-blue-600" />
              </div>
              <p className="mt-2 text-2xl font-semibold text-gov-gray-900">{summary.running}</p>
            </div>
            <div className="rounded-xl border border-gov-gray-200 bg-white p-4">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium uppercase tracking-wide text-gov-gray-500">
                  Falhas/Travados
                </p>
                <CircleX className="h-4 w-4 text-red-500" />
              </div>
              <p className="mt-2 text-2xl font-semibold text-gov-gray-900">{summary.failed}</p>
            </div>
          </>
        )}
      </div>

      <div className="mt-8">
        <div className="mb-3 flex items-center gap-2">
          <Activity className="h-4 w-4 text-gov-gray-500" />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gov-gray-600">
            Pipeline
          </h2>
        </div>
        {loading ? (
          <ProcessingStatus coverage={[]} recentRuns={[]} signalCount={0} loading />
        ) : error ? (
          <div className="flex flex-col items-center justify-center rounded-lg border border-red-200 bg-red-50 py-12">
            <AlertTriangle className="h-8 w-8 text-red-400" />
            <p className="mt-2 text-sm text-red-600">{error}</p>
          </div>
        ) : (
          <ProcessingStatus
            coverage={items}
            recentRuns={recentRuns}
            signalCount={signalCount}
            loading={false}
          />
        )}
      </div>

      <div className="mt-8">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-gov-gray-500" />
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gov-gray-600">
              Mapa Brasil (UF)
            </h2>
          </div>
          <div className="flex items-center gap-1 rounded-lg border border-gov-gray-200 bg-white p-1">
            <button
              onClick={() => setMapMetric("coverage")}
              className={`rounded-md px-2 py-1 text-xs font-medium ${
                mapMetric === "coverage" ? "bg-gov-blue-100 text-gov-blue-700" : "text-gov-gray-500"
              }`}
            >
              Cobertura
            </button>
            <button
              onClick={() => setMapMetric("freshness")}
              className={`rounded-md px-2 py-1 text-xs font-medium ${
                mapMetric === "freshness" ? "bg-gov-blue-100 text-gov-blue-700" : "text-gov-gray-500"
              }`}
            >
              Frescor
            </button>
            <button
              onClick={() => setMapMetric("risk")}
              className={`rounded-md px-2 py-1 text-xs font-medium ${
                mapMetric === "risk" ? "bg-gov-blue-100 text-gov-blue-700" : "text-gov-gray-500"
              }`}
            >
              Risco
            </button>
          </div>
        </div>
        {loading ? (
          <GridSkeleton cols={5} cards={10} />
        ) : (
          <div className="rounded-xl border border-gov-gray-200 bg-white p-4">
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-9">
              {ufOrder.map((uf) => {
                const item = ufMap.get(uf);
                return (
                  <div
                    key={uf}
                    className={`rounded-lg border px-2 py-2 text-center ${ufCellClass(item)}`}
                    title={`${uf}: ${ufCellMetric(item)}`}
                  >
                    <div className="text-xs font-semibold">{uf}</div>
                    <div className="mt-1 text-[10px]">{ufCellMetric(item)}</div>
                  </div>
                );
              })}
            </div>
            <p className="mt-3 text-xs text-gov-gray-500">
              Escala de calor por UF baseada em {mapMetric === "coverage" ? "volume relativo de eventos" : mapMetric === "freshness" ? "horas desde o último evento" : "severidade média dos sinais ligados a eventos da UF"}.
            </p>
          </div>
        )}
      </div>

      <div className="mt-8">
        <div className="mb-3 flex items-center gap-2">
          <Database className="h-4 w-4 text-gov-gray-500" />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gov-gray-600">
            Fontes e Jobs
          </h2>
        </div>
        {loading ? (
          <GridSkeleton cols={3} cards={6} />
        ) : error ? null : items.length === 0 ? (
          <EmptyState
            icon={Database}
            title="Nenhuma fonte de dados configurada"
            description="As fontes serao registradas apos a primeira ingestao de dados"
          />
        ) : (
          <CoveragePanel items={items} recentRuns={recentRuns} />
        )}
      </div>
    </div>
  );
}
