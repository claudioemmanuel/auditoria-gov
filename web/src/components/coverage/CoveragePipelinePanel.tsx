"use client";

import type { CoverageV2SummaryResponse } from "@/lib/types";
import { CheckCircle2, Clock3, Loader2, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface CoveragePipelinePanelProps {
  summary: CoverageV2SummaryResponse | null;
  loading: boolean;
}

const STATIC_STEPS = [
  { code: "ingest", label: "Ingestão" },
  { code: "normalization", label: "Normalização" },
  { code: "entity_resolution", label: "Entidade Res." },
  { code: "signals", label: "Sinais" },
];

function stepConfig(status: string) {
  if (status === "done") {
    return {
      dot: "bg-green-500",
      ring: "ring-green-200",
      icon: CheckCircle2,
      iconCls: "text-green-600",
      labelCls: "text-primary",
    };
  }
  if (status === "processing") {
    return {
      dot: "bg-blue-500",
      ring: "ring-blue-200",
      icon: Loader2,
      iconCls: "text-blue-600 animate-spin",
      labelCls: "text-primary",
    };
  }
  if (status === "error") {
    return {
      dot: "bg-red-500",
      ring: "ring-red-200",
      icon: AlertTriangle,
      iconCls: "text-red-600",
      labelCls: "text-primary",
    };
  }
  if (status === "warning") {
    return {
      dot: "bg-yellow-500",
      ring: "ring-yellow-200",
      icon: AlertTriangle,
      iconCls: "text-yellow-600",
      labelCls: "text-primary",
    };
  }
  return {
    dot: "bg-surface-subtle border border-border",
    ring: "ring-border",
    icon: Clock3,
    iconCls: "text-muted",
    labelCls: "text-muted",
  };
}

export function CoveragePipelinePanel({ summary, loading }: CoveragePipelinePanelProps) {
  if (loading || !summary) {
    return (
      <div className="rounded-xl border border-border bg-surface-card p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">Pipeline</p>
        <div className="mt-4 flex items-center gap-0">
          {STATIC_STEPS.map((step, index) => (
            <div key={step.code} className="flex items-center">
              <div className="flex flex-col items-center gap-1.5">
                <div className="h-8 w-8 animate-pulse rounded-full bg-surface-subtle" />
                <div className="h-3 w-16 animate-pulse rounded bg-surface-subtle" />
              </div>
              {index < STATIC_STEPS.length - 1 && (
                <div className="mx-1 h-px w-8 bg-border sm:w-12" />
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Merge static step order with real data from API
  const stagesByCode = new Map(summary.pipeline.stages.map((s) => [s.code, s]));

  const steps = STATIC_STEPS.map((staticStep) => {
    const live = stagesByCode.get(staticStep.code);
    return {
      code: staticStep.code,
      label: live?.label ?? staticStep.label,
      status: live?.status ?? "pending",
      reason: live?.reason ?? "",
    };
  });

  return (
    <div className="rounded-xl border border-border bg-surface-card p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">Pipeline</p>
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
            summary.pipeline.overall_status === "healthy"
              ? "bg-green-100 text-green-700"
              : summary.pipeline.overall_status === "blocked"
                ? "bg-red-100 text-red-700"
                : "bg-yellow-100 text-yellow-700",
          )}
        >
          {summary.pipeline.overall_status === "healthy"
            ? "Saudável"
            : summary.pipeline.overall_status === "blocked"
              ? "Bloqueado"
              : "Atenção"}
        </span>
      </div>

      <div className="mt-4 flex items-start justify-between gap-0 overflow-x-auto pb-1">
        {steps.map((step, index) => {
          const cfg = stepConfig(step.status);
          const Icon = cfg.icon;
          return (
            <div key={step.code} className="flex items-start">
              <div className="flex flex-col items-center gap-1.5" title={step.reason || step.label}>
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full ring-2",
                    cfg.ring,
                    step.status === "pending"
                      ? "bg-surface-subtle"
                      : step.status === "done"
                        ? "bg-green-50"
                        : step.status === "error"
                          ? "bg-red-50"
                          : step.status === "warning"
                            ? "bg-yellow-50"
                            : "bg-blue-50",
                  )}
                >
                  <Icon className={cn("h-4 w-4", cfg.iconCls)} />
                </div>
                <span className={cn("max-w-[70px] text-center text-[10px] font-medium leading-tight", cfg.labelCls)}>
                  {step.label}
                </span>
              </div>
              {index < steps.length - 1 && (
                <div className="mx-1 mt-4 h-px w-8 flex-shrink-0 bg-border sm:w-10" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
