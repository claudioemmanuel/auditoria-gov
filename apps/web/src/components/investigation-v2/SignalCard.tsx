"use client";

import type { RadarV2SignalItem, SignalSeverity } from "@/lib/types";
import { cn } from "@/lib/utils";

const SEVERITY_COLORS: Record<SignalSeverity, string> = {
  critical: "bg-error text-white",
  high: "bg-warning text-white",
  medium: "bg-amber-500 text-white",
  low: "bg-info text-white",
};

const SEVERITY_LABELS: Record<SignalSeverity, string> = {
  critical: "Critico",
  high: "Alto",
  medium: "Medio",
  low: "Baixo",
};

interface SignalCardProps {
  signal: RadarV2SignalItem;
  onClick?: (signalId: string) => void;
  active?: boolean;
}

export function SignalCard({ signal, onClick, active }: SignalCardProps) {
  const period = [signal.period_start, signal.period_end]
    .filter(Boolean)
    .map((d) => new Date(d!).toLocaleDateString("pt-BR", { month: "short", year: "numeric" }))
    .join(" — ");

  return (
    <button
      onClick={() => onClick?.(signal.id)}
      className={cn(
        "w-full text-left rounded-xl border p-4 transition-all duration-120",
        "hover:shadow-sm hover:border-accent/30",
        active
          ? "border-accent bg-accent/5 shadow-sm"
          : "border-border bg-surface-card",
      )}
    >
      <div className="flex items-start gap-3">
        {/* Severity badge */}
        <span
          className={cn(
            "shrink-0 rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider",
            SEVERITY_COLORS[signal.severity],
          )}
        >
          {SEVERITY_LABELS[signal.severity]}
        </span>

        <div className="min-w-0 flex-1">
          {/* Typology */}
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {signal.typology_code} · {signal.typology_name}
          </p>

          {/* Title */}
          <p className="mt-1 text-sm font-medium text-primary line-clamp-2">
            {signal.title}
          </p>

          {/* Meta row */}
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
            <span>{signal.entity_count} entidades</span>
            <span>{signal.event_count} eventos</span>
            {period && <span>{period}</span>}
          </div>

          {/* Confidence bar */}
          <div className="mt-2 flex items-center gap-2">
            <div className="h-1.5 flex-1 rounded-full bg-surface-subtle overflow-hidden">
              <div
                className="h-full rounded-full bg-accent"
                style={{ width: `${Math.round(signal.confidence * 100)}%` }}
              />
            </div>
            <span className="font-mono text-[10px] text-muted">
              {Math.round(signal.confidence * 100)}%
            </span>
          </div>
        </div>
      </div>
    </button>
  );
}
