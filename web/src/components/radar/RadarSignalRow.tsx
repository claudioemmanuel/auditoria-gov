"use client";

import { ArrowRight } from "lucide-react";
import type { SignalSeverity } from "@/lib/types";
import { TYPOLOGY_LABELS } from "@/lib/constants";

const SEV_CODE_COLOR: Record<string, string> = {
  critical: "text-severity-critical",
  high:     "text-severity-high",
  medium:   "text-severity-medium",
  low:      "text-severity-low",
};

interface RadarSignalRowProps {
  signal: {
    id: string;
    typology_code: string;
    typology_name: string;
    severity: SignalSeverity;
    confidence: number;
    title: string;
    period_start?: string | null;
    period_end?: string | null;
    entity_count?: number;
    event_count?: number;
  };
  onClick: (signalId: string) => void;
  active?: boolean;
}

export function RadarSignalRow({ signal, onClick, active }: RadarSignalRowProps) {
  const codeColor = SEV_CODE_COLOR[signal.severity] ?? "text-masthead";

  return (
    <button
      type="button"
      onClick={() => onClick(signal.id)}
      className={`group flex w-full items-center gap-3 border-b border-border-subtle px-3 py-2.5 text-left transition-colors duration-100 ${
        active
          ? "bg-masthead/8 border-masthead/30"
          : "bg-newsprint-card hover:bg-newsprint-hover"
      }`}
    >
      {/* Typology code — masthead red, mono bold */}
      <span className={`w-8 shrink-0 font-mono text-[10px] font-bold tracking-[0.05em] ${codeColor}`}>
        {signal.typology_code}
      </span>

      {/* Signal title — serif */}
      <span
        className="flex-1 truncate text-[13px] text-ink-secondary group-hover:text-ink"
        style={{ fontFamily: "var(--font-ibm-plex-serif, Georgia, serif)" }}
        title={TYPOLOGY_LABELS[signal.typology_code] ?? signal.title}
      >
        {TYPOLOGY_LABELS[signal.typology_code] ?? signal.title}
      </span>

      <ArrowRight className="h-3 w-3 shrink-0 text-ink-muted opacity-0 transition-opacity group-hover:opacity-100" />
    </button>
  );
}
