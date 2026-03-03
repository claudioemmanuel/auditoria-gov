"use client";

import type { CoverageMapItem, CoverageV2MapResponse } from "@/lib/types";

interface CoverageMapPanelProps {
  map: CoverageV2MapResponse | null;
  metric: "coverage" | "freshness" | "risk";
  loading: boolean;
  onMetricChange: (metric: "coverage" | "freshness" | "risk") => void;
}

const UF_ORDER = [
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
  "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
  "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
];

function cellClass(item?: CoverageMapItem, metric: "coverage" | "freshness" | "risk" = "coverage") {
  if (!item) return "bg-gov-gray-100 text-gov-gray-400 border-gov-gray-200";
  if (metric === "risk") {
    if (item.risk_score >= 0.75) return "bg-red-100 text-red-700 border-red-200";
    if (item.risk_score >= 0.5) return "bg-amber-100 text-amber-700 border-amber-200";
    if (item.risk_score > 0) return "bg-blue-100 text-blue-700 border-blue-200";
    return "bg-gov-gray-100 text-gov-gray-500 border-gov-gray-200";
  }
  if (metric === "freshness") {
    if (item.freshness_hours == null) return "bg-gov-gray-100 text-gov-gray-500 border-gov-gray-200";
    if (item.freshness_hours < 24) return "bg-emerald-100 text-emerald-700 border-emerald-200";
    if (item.freshness_hours < 72) return "bg-amber-100 text-amber-700 border-amber-200";
    return "bg-red-100 text-red-700 border-red-200";
  }
  if (item.coverage_score >= 0.75) return "bg-emerald-100 text-emerald-700 border-emerald-200";
  if (item.coverage_score >= 0.45) return "bg-amber-100 text-amber-700 border-amber-200";
  if (item.coverage_score > 0) return "bg-blue-100 text-blue-700 border-blue-200";
  return "bg-gov-gray-100 text-gov-gray-500 border-gov-gray-200";
}

function metricLabel(item?: CoverageMapItem, metric: "coverage" | "freshness" | "risk" = "coverage") {
  if (!item) return "sem dados";
  if (metric === "risk") return `${Math.round(item.risk_score * 100)}% risco`;
  if (metric === "freshness") {
    if (item.freshness_hours == null) return "sem frescor";
    return `${Math.round(item.freshness_hours)}h`;
  }
  return `${Math.round(item.coverage_score * 100)}% cobertura`;
}

export function CoverageMapPanel({ map, metric, loading, onMetricChange }: CoverageMapPanelProps) {
  const mapByUf = new Map<string, CoverageMapItem>();
  for (const item of map?.items || []) {
    mapByUf.set(item.code, item);
  }

  return (
    <div className="rounded-xl border border-gov-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gov-gray-600">Mapa nacional (UF)</h2>
        <div className="flex items-center gap-1 rounded-lg border border-gov-gray-200 bg-gov-gray-50 p-1">
          {(["coverage", "freshness", "risk"] as const).map((entry) => (
            <button
              key={entry}
              type="button"
              onClick={() => onMetricChange(entry)}
              className={`rounded-md px-2 py-1 text-xs font-medium ${
                metric === entry
                  ? "bg-gov-blue-100 text-gov-blue-700"
                  : "text-gov-gray-500"
              }`}
            >
              {entry === "coverage" ? "Cobertura" : entry === "freshness" ? "Frescor" : "Risco"}
            </button>
          ))}
        </div>
      </div>

      {loading || !map ? (
        <div className="mt-3 h-28 animate-pulse rounded-lg bg-gov-gray-100" />
      ) : (
        <>
          <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-9">
            {UF_ORDER.map((uf) => {
              const item = mapByUf.get(uf);
              return (
                <div
                  key={uf}
                  className={`rounded-lg border px-2 py-2 text-center ${cellClass(item, metric)}`}
                  title={`${uf}: ${metricLabel(item, metric)}`}
                >
                  <div className="text-xs font-semibold">{uf}</div>
                  <div className="mt-1 text-[10px]">{metricLabel(item, metric)}</div>
                </div>
              );
            })}
          </div>
          <p className="mt-3 text-xs text-gov-gray-600">
            {map.national.regions_with_data} UFs com dados, {map.national.regions_without_data} sem dados.
          </p>
        </>
      )}
    </div>
  );
}
