"use client";

import type { CoverageV2SummaryResponse } from "@/lib/types";
import { CheckCircle2, Clock3, Loader2, AlertTriangle } from "lucide-react";

interface CoveragePipelinePanelProps {
  summary: CoverageV2SummaryResponse | null;
  loading: boolean;
}

function stageBadge(stageStatus: string) {
  if (stageStatus === "done") {
    return { cls: "bg-green-100 text-green-700 border-green-200", Icon: CheckCircle2, label: "Concluido" };
  }
  if (stageStatus === "processing") {
    return { cls: "bg-blue-100 text-blue-700 border-blue-200", Icon: Loader2, label: "Em andamento" };
  }
  if (stageStatus === "error") {
    return { cls: "bg-red-100 text-red-700 border-red-200", Icon: AlertTriangle, label: "Erro" };
  }
  if (stageStatus === "warning") {
    return { cls: "bg-amber-100 text-amber-700 border-amber-200", Icon: AlertTriangle, label: "Atencao" };
  }
  return { cls: "bg-gov-gray-100 text-gov-gray-700 border-gov-gray-200", Icon: Clock3, label: "Pendente" };
}

export function CoveragePipelinePanel({ summary, loading }: CoveragePipelinePanelProps) {
  return (
    <div className="rounded-xl border border-gov-gray-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-gov-gray-600">Pipeline investigativo</h2>
      {loading || !summary ? (
        <div className="mt-3 space-y-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={`pipeline-skeleton-${index}`} className="h-16 animate-pulse rounded-lg bg-gov-gray-100" />
          ))}
        </div>
      ) : (
        <div className="mt-3 space-y-2">
          {summary.pipeline.stages.map((stage) => {
            const badge = stageBadge(stage.status);
            const BadgeIcon = badge.Icon;
            return (
              <div key={stage.code} className="rounded-lg border border-gov-gray-200 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-gov-gray-900">{stage.label}</p>
                    <p className="text-xs text-gov-gray-600">{stage.reason}</p>
                  </div>
                  <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${badge.cls}`}>
                    <BadgeIcon className="h-3.5 w-3.5" />
                    {badge.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
      {!loading && summary && (
        <div className="mt-4 rounded-lg border border-gov-gray-200 bg-gov-gray-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Janelas de agenda</p>
          <ul className="mt-2 space-y-1 text-xs text-gov-gray-700">
            {summary.schedule_windows_brt.slice(0, 6).map((windowItem) => (
              <li key={windowItem.job_code}>
                <span className="font-medium">{windowItem.job_code}</span>: {windowItem.window}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
