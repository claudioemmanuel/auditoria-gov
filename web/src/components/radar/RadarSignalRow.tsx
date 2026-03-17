"use client";

import { ArrowRight } from "lucide-react";
import type { SignalSeverity } from "@/lib/types";
import { TYPOLOGY_LABELS } from "@/lib/constants";

const SEV_DOT: Record<string, string> = {
  critical: "bg-error",
  high: "bg-amber",
  medium: "bg-yellow-500",
  low: "bg-info",
};

const SEV_TEXT: Record<string, string> = {
  critical: "text-error",
  high: "text-amber",
  medium: "text-yellow-600",
  low: "text-info",
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
  const dot = SEV_DOT[signal.severity] ?? "bg-info";

  return (
    <button
      type="button"
      onClick={() => onClick(signal.id)}
      className={`group flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left transition-all ${
        active
          ? "border-accent/40 bg-accent-subtle/30"
          : "border-border bg-surface-base hover:border-accent/20 hover:bg-surface-subtle"
      }`}
    >
      <span className={`h-2 w-2 shrink-0 rounded-full ${dot}`} />

      <span className="w-7 shrink-0 font-mono text-[10px] font-bold text-accent">
        {signal.typology_code}
      </span>

      <span className="flex-1 truncate text-xs text-secondary group-hover:text-primary" title={signal.title}>
        {TYPOLOGY_LABELS[signal.typology_code] ?? signal.title}
      </span>

<ArrowRight className="h-3 w-3 shrink-0 text-muted opacity-0 transition-opacity group-hover:opacity-100" />
    </button>
  );
}
