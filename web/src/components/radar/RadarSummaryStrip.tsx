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
    <div className="grid grid-cols-3 gap-px bg-border sm:grid-cols-6">
      {kpis.map((k) => {
        const isActive = k.severity && activeSeverity === k.severity;

        const inner = (
          <>
            <p className="byline mb-2">{k.label}</p>
            <p
              className="text-3xl font-bold text-ink leading-none tabular-nums"
              style={{ fontFamily: "var(--font-playfair)" }}
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
              className={`px-4 py-4 text-left transition-colors duration-100 paper-texture ${
                isActive
                  ? "bg-masthead text-newsprint"
                  : "bg-newsprint-card hover:bg-newsprint-hover"
              }`}
            >
              {inner}
            </button>
          );
        }

        return (
          <div key={k.label} className="bg-newsprint-card px-4 py-4 paper-texture">
            {inner}
          </div>
        );
      })}
    </div>
  );
}
