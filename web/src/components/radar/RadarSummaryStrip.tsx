"use client";

import type { RadarV2SummaryResponse, SignalSeverity } from "@/lib/types";
import { SEVERITY_LABELS } from "@/lib/constants";

interface RadarSummaryStripProps {
  summary: RadarV2SummaryResponse | null;
  loading: boolean;
  activeSeverity?: string;
  onSeverityClick: (severity: SignalSeverity) => void;
}

export function RadarSummaryStrip({
  summary,
  loading,
  activeSeverity,
  onSeverityClick,
}: RadarSummaryStripProps) {
  if (loading || !summary) {
    return (
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-20 animate-pulse rounded-[10px] border border-border bg-surface-card" />
        ))}
      </div>
    );
  }

  const sc = summary.severity_counts;

  const kpis: {
    label: string;
    value: number;
    severity?: SignalSeverity;
  }[] = [
    { label: "Sinais",                     value: summary.totals.signals },
    { label: "Casos",                      value: summary.totals.cases   },
    { label: SEVERITY_LABELS.critical,     value: sc.critical, severity: "critical" },
    { label: SEVERITY_LABELS.high,         value: sc.high,     severity: "high"     },
    { label: SEVERITY_LABELS.medium,       value: sc.medium,   severity: "medium"   },
    { label: SEVERITY_LABELS.low,          value: sc.low,      severity: "low"      },
  ];

  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
      {kpis.map((k) => {
        const isActive = k.severity && activeSeverity === k.severity;
        const inner = (
          <>
            <p className="section-kicker mb-2">{k.label}</p>
            <p className="data-num text-3xl text-primary leading-none">
              {k.value.toLocaleString("pt-BR")}
            </p>
          </>
        );

        if (k.severity) {
          return (
            <button
              key={k.label}
              type="button"
              onClick={() => onSeverityClick(k.severity!)}
              className={`rounded-[10px] border px-3 py-3 text-left transition-colors duration-100 scanline-texture ${
                isActive
                  ? "border-accent bg-accent/10 shadow-[inset_0_0_0_1px] shadow-accent/30"
                  : "border-border bg-surface-card hover:border-accent/40"
              }`}
            >
              {inner}
            </button>
          );
        }

        return (
          <div key={k.label} className="rounded-[10px] border border-border bg-surface-card px-3 py-3 scanline-texture">
            {inner}
          </div>
        );
      })}
    </div>
  );
}
