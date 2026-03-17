"use client";

import type { RadarV2SummaryResponse, SignalSeverity } from "@/lib/types";
import { SEVERITY_LABELS } from "@/lib/constants";

const SEV_DOT: Record<string, string> = {
  critical: "bg-severity-critical",
  high:     "bg-amber",
  medium:   "bg-yellow-500",
  low:      "bg-severity-low",
};

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
          <div key={i} className="h-16 animate-pulse rounded-lg border border-border bg-surface-card" />
        ))}
      </div>
    );
  }

  const sc = summary.severity_counts;

  const kpis: {
    label: string;
    value: number;
    dot: string | null;
    severity?: SignalSeverity;
  }[] = [
    { label: "Sinais",   value: summary.totals.signals, dot: null },
    { label: "Casos",    value: summary.totals.cases,   dot: null },
    { label: SEVERITY_LABELS.critical, value: sc.critical, dot: SEV_DOT.critical, severity: "critical" },
    { label: SEVERITY_LABELS.high,     value: sc.high,     dot: SEV_DOT.high,     severity: "high"     },
    { label: SEVERITY_LABELS.medium,   value: sc.medium,   dot: SEV_DOT.medium,   severity: "medium"   },
    { label: SEVERITY_LABELS.low,      value: sc.low,      dot: SEV_DOT.low,      severity: "low"      },
  ];

  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
      {kpis.map((k) => {
        const isActive = k.severity && activeSeverity === k.severity;
        const inner = (
          <>
            {k.dot ? (
              <div className="flex items-center gap-1.5 mb-1">
                <span className={`h-1.5 w-1.5 rounded-full ${k.dot}`} />
                <p className="font-mono text-[9px] uppercase tracking-widest text-muted">{k.label}</p>
              </div>
            ) : (
              <p className="font-mono text-[9px] uppercase tracking-widest text-muted mb-1">{k.label}</p>
            )}
            <p className="font-mono text-lg font-bold tabular-nums text-primary leading-none">
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
              className={`rounded-lg border px-3 py-3 text-left transition-colors ${
                isActive
                  ? "border-accent bg-accent-subtle"
                  : "border-border bg-surface-card hover:border-accent/40"
              }`}
            >
              {inner}
            </button>
          );
        }

        return (
          <div key={k.label} className="rounded-lg border border-border bg-surface-card px-3 py-3">
            {inner}
          </div>
        );
      })}
    </div>
  );
}
