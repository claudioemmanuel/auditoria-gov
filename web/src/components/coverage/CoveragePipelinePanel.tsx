"use client";

import type { CoverageV2SummaryResponse } from "@/lib/types";
import { CheckCircle2, Clock3, Loader2, AlertTriangle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

interface CoveragePipelinePanelProps {
  summary: CoverageV2SummaryResponse | null;
  loading: boolean;
}

const STATIC_STEPS = [
  { code: "ingest", label: "Ingestão de Dados" },
  { code: "entity_resolution", label: "Resolução de Entidades" },
  { code: "baselines", label: "Cálculo de Baselines" },
  { code: "signals", label: "Detecção de Sinais" },
];

const STATUS_LABELS: Record<string, string> = {
  up_to_date: "Atualizado",
  processing: "Processando",
  stale: "Desatualizado",
  warning: "Atenção",
  error: "Erro",
  pending: "Pendente",
};

function stepConfig(status: string) {
  if (status === "up_to_date") {
    return {
      ring: "ring-success/30",
      bg: "bg-success-subtle",
      icon: CheckCircle2,
      iconCls: "text-success",
      labelCls: "text-primary",
      statusCls: "text-success",
    };
  }
  if (status === "stale") {
    return {
      ring: "ring-amber/30",
      bg: "bg-amber-subtle",
      icon: RefreshCw,
      iconCls: "text-amber",
      labelCls: "text-primary",
      statusCls: "text-amber",
    };
  }
  if (status === "processing") {
    return {
      ring: "ring-accent/30",
      bg: "bg-accent-subtle",
      icon: Loader2,
      iconCls: "text-accent animate-spin",
      labelCls: "text-primary",
      statusCls: "text-accent",
    };
  }
  if (status === "error") {
    return {
      ring: "ring-error/30",
      bg: "bg-error-subtle",
      icon: AlertTriangle,
      iconCls: "text-error",
      labelCls: "text-primary",
      statusCls: "text-error",
    };
  }
  if (status === "warning") {
    return {
      ring: "ring-amber/30",
      bg: "bg-amber-subtle",
      icon: AlertTriangle,
      iconCls: "text-amber",
      labelCls: "text-primary",
      statusCls: "text-amber",
    };
  }
  // pending
  return {
    ring: "ring-border",
    bg: "bg-surface-base",
    icon: Clock3,
    iconCls: "text-muted",
    labelCls: "text-muted",
    statusCls: "text-muted",
  };
}

export function CoveragePipelinePanel({ summary, loading }: CoveragePipelinePanelProps) {
  if (loading || !summary) {
    return (
      <div className="rounded-xl border border-border bg-surface-card p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">Pipeline de Ingestão</p>
        <div className="mt-4 flex items-center gap-0">
          {STATIC_STEPS.map((step, index) => (
            <div key={step.code} className="flex items-center">
              <div className="flex flex-col items-center gap-1.5">
                <div className="h-10 w-10 animate-pulse rounded-full bg-surface-base" />
                <div className="h-3 w-20 animate-pulse rounded bg-surface-base" />
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
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">Pipeline de Ingestão</p>
          <p className="mt-0.5 text-[11px] text-secondary">Estado atual de cada etapa de processamento</p>
        </div>
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
            summary.pipeline.overall_status === "healthy"
              ? "status-ok"
              : summary.pipeline.overall_status === "blocked"
                ? "status-error"
                : "status-warning",
          )}
        >
          {summary.pipeline.overall_status === "healthy"
            ? "Saudável"
            : summary.pipeline.overall_status === "blocked"
              ? "Bloqueado"
              : "Atenção"}
        </span>
      </div>

      <div className="mt-5 grid grid-cols-4 gap-3">
        {steps.map((step) => {
          const cfg = stepConfig(step.status);
          const Icon = cfg.icon;
          return (
            <div
              key={step.code}
              className={cn(
                "rounded-lg border p-3 transition-colors",
                step.status === "up_to_date"
                  ? "border-success/20 bg-success/5"
                  : step.status === "stale"
                    ? "border-amber/20 bg-amber/5"
                    : step.status === "processing"
                      ? "border-accent/20 bg-accent/5"
                      : step.status === "error"
                        ? "border-red-500/20 bg-red-500/5"
                        : step.status === "warning"
                          ? "border-amber/20 bg-amber/5"
                          : "border-border bg-surface-subtle",
              )}
            >
              <div className="flex items-center justify-center mb-2">
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-full ring-2",
                    cfg.ring,
                    cfg.bg,
                  )}
                >
                  <Icon className={cn("h-5 w-5", cfg.iconCls)} />
                </div>
              </div>
              <p className={cn("text-center text-[11px] font-semibold leading-tight", cfg.labelCls)}>
                {step.label}
              </p>
              <p className={cn("mt-0.5 text-center text-[10px] font-semibold uppercase", cfg.statusCls)}>
                {STATUS_LABELS[step.status] ?? step.status}
              </p>
              {step.reason && (
                <p className="mt-1.5 text-center text-[9px] text-muted leading-relaxed">
                  {step.reason}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
