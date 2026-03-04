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
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/35 backdrop-blur-[1px]">
      <div className="h-full w-full max-w-xl overflow-y-auto border-l border-border bg-surface-card p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-bold text-primary">
            Confiabilidade da analise
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-muted hover:bg-surface-subtle"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {loading && (
          <p className="mt-4 text-sm text-secondary">Carregando cobertura...</p>
        )}
        {error && (
          <p className="mt-4 text-sm text-red-600">{error}</p>
        )}

        {data && (
          <div className="mt-4 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-border bg-surface-base p-3">
                <p className="text-xs text-muted">Tipologias aptas</p>
                <p className="mt-1 text-xl font-semibold text-primary">
                  {data.summary.apt_count}/{data.summary.total_typologies}
                </p>
              </div>
              <div className="rounded-lg border border-border bg-surface-base p-3">
                <p className="text-xs text-muted">Com sinais em 30d</p>
                <p className="mt-1 text-xl font-semibold text-primary">
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
                    className="rounded-lg border border-border p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium text-primary">
                        {item.typology_code} - {item.typology_name}
                      </p>
                      <Icon className="h-4 w-4 text-muted" />
                    </div>
                    <p className="mt-1 text-xs text-secondary">
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
