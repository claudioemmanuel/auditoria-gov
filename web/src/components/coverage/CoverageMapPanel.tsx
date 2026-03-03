"use client";

import { useEffect, useMemo, useState } from "react";
import type { CoverageMapItem, CoverageV2MapResponse } from "@/lib/types";
import { COVERAGE_STATUS_LABELS } from "@/lib/constants";
import { formatNumber } from "@/lib/utils";

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

const UF_REGION: Record<string, string> = {
  AC: "Norte", AL: "Nordeste", AP: "Norte", AM: "Norte", BA: "Nordeste",
  CE: "Nordeste", DF: "Centro-Oeste", ES: "Sudeste", GO: "Centro-Oeste", MA: "Nordeste",
  MT: "Centro-Oeste", MS: "Centro-Oeste", MG: "Sudeste", PA: "Norte", PB: "Nordeste",
  PR: "Sul", PE: "Nordeste", PI: "Nordeste", RJ: "Sudeste", RN: "Nordeste",
  RS: "Sul", RO: "Norte", RR: "Norte", SC: "Sul", SP: "Sudeste", SE: "Nordeste", TO: "Norte",
};

function cellClass(item?: CoverageMapItem, metric: "coverage" | "freshness" | "risk" = "coverage"): string {
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

function metricLabel(item?: CoverageMapItem, metric: "coverage" | "freshness" | "risk" = "coverage"): string {
  if (!item) return "Sem dados";
  if (metric === "risk") return `${Math.round(item.risk_score * 100)}%`;
  if (metric === "freshness") {
    if (item.freshness_hours == null) return "Sem leitura";
    return `${Math.round(item.freshness_hours)}h`;
  }
  return `${Math.round(item.coverage_score * 100)}%`;
}

export function CoverageMapPanel({ map, metric, loading, onMetricChange }: CoverageMapPanelProps) {
  const [selectedUf, setSelectedUf] = useState<string>("SP");

  const mapByUf = useMemo(() => {
    const ufMap = new Map<string, CoverageMapItem>();
    for (const item of map?.items || []) {
      ufMap.set(item.code, item);
    }
    return ufMap;
  }, [map]);

  useEffect(() => {
    if (mapByUf.has(selectedUf)) return;
    const firstWithData = (map?.items || []).find((item) => item.event_count > 0)?.code;
    if (firstWithData) setSelectedUf(firstWithData);
  }, [map, mapByUf, selectedUf]);

  const selectedItem = mapByUf.get(selectedUf);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="panel-title">Visao territorial</h3>
          <p className="mt-1 text-xs text-gov-gray-500">
            Clique em uma UF para detalhar cobertura, frescor e risco.
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-lg border border-gov-gray-200 bg-gov-gray-50 p-1">
          {(["coverage", "freshness", "risk"] as const).map((entry) => (
            <button
              key={entry}
              type="button"
              onClick={() => onMetricChange(entry)}
              className={`rounded-md px-2 py-1 text-xs font-medium ${
                metric === entry
                  ? "bg-gov-blue-100 text-gov-blue-700"
                  : "text-gov-gray-600 hover:bg-gov-gray-100"
              }`}
            >
              {entry === "coverage" ? "Cobertura" : entry === "freshness" ? "Frescor" : "Risco"}
            </button>
          ))}
        </div>
      </div>

      {loading || !map ? (
        <div className="h-64 animate-pulse rounded-lg bg-gov-gray-100" />
      ) : (
        <>
          <div className="overflow-x-auto">
            <div className="grid min-w-[760px] grid-cols-9 gap-2">
              {UF_ORDER.map((uf) => {
                const item = mapByUf.get(uf);
                const selected = selectedUf === uf;
                return (
                  <button
                    key={uf}
                    type="button"
                    onClick={() => setSelectedUf(uf)}
                    className={`min-h-[86px] rounded-lg border px-2 py-2 text-left transition ${cellClass(item, metric)} ${
                      selected ? "ring-2 ring-gov-blue-500" : ""
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <span className="text-sm font-bold">{uf}</span>
                      <span className="text-[10px] opacity-80">{UF_REGION[uf]}</span>
                    </div>
                    <p className="mt-1 text-sm font-semibold">{metricLabel(item, metric)}</p>
                    <p className="mt-1 text-[11px] opacity-80">
                      {item ? `${formatNumber(item.event_count)} eventos` : "Sem dados"}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-12">
            <div className="rounded-xl border border-gov-gray-200 bg-gov-gray-50/70 p-3 lg:col-span-4">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-gov-gray-500">UF selecionada</h4>
              <p className="mt-1 text-base font-semibold text-gov-gray-900">
                {selectedUf}{selectedItem?.label ? ` - ${selectedItem.label}` : ""}
              </p>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-gov-gray-700">
                <p>
                  Cobertura:{" "}
                  <span className="font-semibold">
                    {selectedItem ? `${Math.round(selectedItem.coverage_score * 100)}%` : "Sem dados"}
                  </span>
                </p>
                <p>
                  Risco:{" "}
                  <span className="font-semibold">
                    {selectedItem ? `${Math.round(selectedItem.risk_score * 100)}%` : "Sem dados"}
                  </span>
                </p>
                <p>
                  Frescor:{" "}
                  <span className="font-semibold">
                    {selectedItem?.freshness_hours == null ? "Nao informado" : `${Math.round(selectedItem.freshness_hours)}h`}
                  </span>
                </p>
                <p>
                  Status:{" "}
                  <span className="font-semibold">
                    {selectedItem ? COVERAGE_STATUS_LABELS[selectedItem.status] : "Sem dados"}
                  </span>
                </p>
                <p className="col-span-2">
                  Eventos: <span className="font-semibold">{selectedItem ? formatNumber(selectedItem.event_count) : 0}</span>
                  {" • "}
                  Sinais: <span className="font-semibold">{selectedItem ? formatNumber(selectedItem.signal_count) : 0}</span>
                </p>
              </div>
            </div>

            <div className="rounded-xl border border-gov-gray-200 bg-gov-gray-50/70 p-3 lg:col-span-8">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Resumo nacional</h4>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-gov-gray-700 sm:grid-cols-4">
                <p>
                  UFs com dados: <span className="font-semibold">{map.national.regions_with_data}</span>
                </p>
                <p>
                  UFs sem dados: <span className="font-semibold">{map.national.regions_without_data}</span>
                </p>
                <p>
                  Eventos: <span className="font-semibold">{formatNumber(map.national.total_events)}</span>
                </p>
                <p>
                  Sinais: <span className="font-semibold">{formatNumber(map.national.total_signals)}</span>
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
