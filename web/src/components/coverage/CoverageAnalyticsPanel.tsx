"use client";

import type { CoverageV2AnalyticsResponse } from "@/lib/types";
import { ChevronDown, ChevronUp } from "lucide-react";

interface CoverageAnalyticsPanelProps {
  open: boolean;
  loading: boolean;
  data: CoverageV2AnalyticsResponse | null;
  onToggle: () => void;
}

export function CoverageAnalyticsPanel({
  open,
  loading,
  data,
  onToggle,
}: CoverageAnalyticsPanelProps) {
  return (
    <div className="rounded-xl border border-gov-gray-200 bg-white p-4 shadow-sm">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between text-left"
      >
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gov-gray-600">Cobertura analitica</h2>
          <p className="text-xs text-gov-gray-500">Aptidao das tipologias e bloqueios de dominio</p>
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-gov-gray-500" /> : <ChevronDown className="h-4 w-4 text-gov-gray-500" />}
      </button>

      {open && (
        <div className="mt-3">
          {loading ? (
            <div className="h-24 animate-pulse rounded-lg bg-gov-gray-100" />
          ) : !data ? (
            <p className="text-sm text-gov-gray-500">Nao foi possivel carregar os indicadores analiticos.</p>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
                <div className="rounded-lg border border-gov-gray-200 bg-gov-gray-50 p-3">
                  <p className="text-xs uppercase tracking-wide text-gov-gray-500">Tipologias</p>
                  <p className="mt-1 text-lg font-semibold text-gov-gray-900">{data.summary.total_typologies}</p>
                </div>
                <div className="rounded-lg border border-gov-gray-200 bg-gov-gray-50 p-3">
                  <p className="text-xs uppercase tracking-wide text-gov-gray-500">Aptas</p>
                  <p className="mt-1 text-lg font-semibold text-green-700">{data.summary.apt_count}</p>
                </div>
                <div className="rounded-lg border border-gov-gray-200 bg-gov-gray-50 p-3">
                  <p className="text-xs uppercase tracking-wide text-gov-gray-500">Bloqueadas</p>
                  <p className="mt-1 text-lg font-semibold text-red-700">{data.summary.blocked_count}</p>
                </div>
                <div className="rounded-lg border border-gov-gray-200 bg-gov-gray-50 p-3">
                  <p className="text-xs uppercase tracking-wide text-gov-gray-500">Com sinais (30d)</p>
                  <p className="mt-1 text-lg font-semibold text-gov-blue-700">{data.summary.with_signals_30d}</p>
                </div>
              </div>

              <div className="mt-3 max-h-64 overflow-auto rounded-lg border border-gov-gray-200">
                <table className="min-w-full text-sm">
                  <thead className="bg-gov-gray-50 text-left text-xs uppercase tracking-wide text-gov-gray-500">
                    <tr>
                      <th className="px-3 py-2">Tipologia</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Sinais (30d)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.slice(0, 25).map((item) => (
                      <tr key={item.typology_code} className="border-t border-gov-gray-100">
                        <td className="px-3 py-2">
                          <span className="font-medium text-gov-gray-800">{item.typology_code}</span>
                          <span className="ml-1 text-gov-gray-500">- {item.typology_name}</span>
                        </td>
                        <td className="px-3 py-2">
                          {item.apt ? (
                            <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                              Apta
                            </span>
                          ) : (
                            <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                              Bloqueada
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-gov-gray-700">{item.signals_30d}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
