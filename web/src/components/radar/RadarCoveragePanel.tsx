"use client";

import type { RadarV2CoverageResponse } from "@/lib/types";
import { AlertTriangle, CheckCircle2, Clock, X } from "lucide-react";

interface RadarCoveragePanelProps {
  open: boolean;
  loading: boolean;
  error: string | null;
  data: RadarV2CoverageResponse | null;
  onClose: () => void;
}

export function RadarCoveragePanel({
  open,
  loading,
  error,
  data,
  onClose,
}: RadarCoveragePanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30">
      <div className="h-full w-full max-w-xl overflow-y-auto bg-white p-4 shadow-2xl">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gov-gray-900">
            Confiabilidade da analise
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-gov-gray-500 hover:bg-gov-gray-100"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {loading && (
          <p className="mt-4 text-sm text-gov-gray-600">Carregando cobertura...</p>
        )}
        {error && (
          <p className="mt-4 text-sm text-red-600">{error}</p>
        )}

        {data && (
          <div className="mt-4 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-gov-gray-200 bg-gov-gray-50 p-3">
                <p className="text-xs text-gov-gray-500">Tipologias aptas</p>
                <p className="mt-1 text-xl font-semibold text-gov-gray-900">
                  {data.summary.apt_count}/{data.summary.total_typologies}
                </p>
              </div>
              <div className="rounded-lg border border-gov-gray-200 bg-gov-gray-50 p-3">
                <p className="text-xs text-gov-gray-500">Com sinais em 30d</p>
                <p className="mt-1 text-xl font-semibold text-gov-gray-900">
                  {data.summary.with_signals_30d}
                </p>
              </div>
            </div>

            <div className="space-y-2">
              {data.items.map((item) => {
                const status = item.last_run_status || "unknown";
                const Icon = status === "success"
                  ? CheckCircle2
                  : status === "error"
                    ? AlertTriangle
                    : Clock;
                return (
                  <div
                    key={item.typology_code}
                    className="rounded-lg border border-gov-gray-200 p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium text-gov-gray-900">
                        {item.typology_code} - {item.typology_name}
                      </p>
                      <Icon className="h-4 w-4 text-gov-gray-500" />
                    </div>
                    <p className="mt-1 text-xs text-gov-gray-600">
                      Apta: {item.apt ? "sim" : "nao"} | Sinais 30d: {item.signals_30d}
                    </p>
                    {item.domains_missing?.length > 0 && (
                      <p className="mt-1 text-xs text-amber-700">
                        Faltam: {item.domains_missing.join(", ")}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
