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
      <div className="grid grid-cols-3 gap-px bg-border sm:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-20 animate-pulse bg-newsprint-card" />
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
    { label: "Sinais",                 value: summary.totals.signals },
    { label: "Casos",                  value: summary.totals.cases   },
    { label: SEVERITY_LABELS.critical, value: sc.critical, severity: "critical" },
    { label: SEVERITY_LABELS.high,     value: sc.high,     severity: "high"     },
    { label: SEVERITY_LABELS.medium,   value: sc.medium,   severity: "medium"   },
    { label: SEVERITY_LABELS.low,      value: sc.low,      severity: "low"      },
  ];

  return (
    <div className="ow-strip grid-cols-2 sm:grid-cols-3 xl:grid-cols-6">
      {kpis.map((k) => {
        const isActive = k.severity && activeSeverity === k.severity;

        const inner = (
          <>
            <p className="ow-strip-label mb-2">{k.label}</p>
            <p
              className="ow-strip-value tabular-nums"
              style={{ color: k.severity ? `var(--color-${k.severity})` : "var(--color-text)" }}
            >
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
              className={`ow-strip-item text-left transition-all duration-150 ${
                isActive
                  ? "bg-[color:var(--color-brand-dim)] shadow-[inset_0_0_0_1px_rgba(45,212,191,0.22)]"
                  : "hover:bg-[color:var(--color-surface-3)]"
              }`}
            >
              {inner}
            </button>
          );
        }

        return (
          <div key={k.label} className="ow-strip-item">
            {inner}
          </div>
        );
      })}
    </div>
  );
}
