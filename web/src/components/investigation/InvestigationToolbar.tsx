"use client";

import Link from "next/link";
import { severityColor } from "@/lib/utils";
import { SEVERITY_LABELS } from "@/lib/constants";
import type { SignalSeverity } from "@/lib/types";
import { ArrowLeft, CircleDot, AlertTriangle, Maximize2, Map } from "lucide-react";
import { cn } from "@/lib/utils";

interface InvestigationToolbarProps {
  caseId: string;
  caseTitle: string;
  caseSeverity: SignalSeverity;
  nodeCount: number;
  edgeCount: number;
  seedCount: number;
  truncated: boolean;
  expanding: boolean;
  onFitView?: () => void;
  onToggleLegend?: () => void;
  legendOpen?: boolean;
}

export function InvestigationToolbar({
  caseId,
  caseTitle,
  caseSeverity,
  nodeCount,
  edgeCount,
  seedCount,
  truncated,
  expanding,
  onFitView,
  onToggleLegend,
  legendOpen,
}: InvestigationToolbarProps) {
  return (
    <>
      {/* Top bar: case info */}
      <div className="absolute top-3 left-3 right-3 z-20 flex items-center gap-2 rounded-xl border border-border bg-surface-card/95 px-3 py-2 shadow-sm backdrop-blur-sm">
        {/* Back */}
        <Link
          href={`/case/${caseId}`}
          className="flex h-7 w-7 items-center justify-center rounded-lg text-muted transition hover:bg-surface-subtle hover:text-secondary"
          title="Voltar ao caso"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
        </Link>

        <div className="h-4 w-px bg-border" />

        {/* Title */}
        <h1 className="min-w-0 flex-1 truncate text-[13px] font-semibold text-primary">
          {caseTitle}
        </h1>

        <span
          className={cn("shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold", severityColor(caseSeverity))}
        >
          {SEVERITY_LABELS[caseSeverity]}
        </span>

        <div className="h-4 w-px bg-border" />

        {/* Stats */}
        <div className="flex items-center gap-2 text-[10px] text-muted">
          <span className="flex items-center gap-1">
            <CircleDot className="h-2.5 w-2.5" />
            <strong className="font-semibold text-secondary">{nodeCount}</strong> nos
          </span>
          <span>
            <strong className="font-semibold text-secondary">{edgeCount}</strong> arestas
          </span>
          <span>
            <strong className="font-semibold text-secondary">{seedCount}</strong> seeds
          </span>
        </div>

        {/* Status indicators */}
        {truncated && (
          <span className="flex items-center gap-1 rounded-full border border-amber/20 bg-amber-subtle px-2 py-0.5 text-[10px] font-medium text-amber">
            <AlertTriangle className="h-2.5 w-2.5" />
            Truncado
          </span>
        )}

        {expanding && (
          <span className="flex items-center gap-1.5 text-[10px] font-medium text-accent">
            <div className="h-2.5 w-2.5 animate-spin rounded-full border-[1.5px] border-accent border-t-transparent" />
            Expandindo...
          </span>
        )}
      </div>

      {/* Bottom-left toolbar: canvas actions */}
      <div className="absolute bottom-4 left-4 z-20 flex gap-1 rounded-lg border border-border bg-surface-card p-1 shadow-sm">
        <button
          onClick={onFitView}
          title="Ajustar vista (Espaco / F)"
          className="flex h-7 items-center gap-1.5 rounded-md px-2.5 text-[11px] font-medium text-secondary transition hover:bg-surface-subtle hover:text-primary"
        >
          <Maximize2 className="h-3.5 w-3.5" />
          Fit
        </button>
        <div className="w-px bg-border" />
        <button
          onClick={onToggleLegend}
          title="Mostrar legenda"
          className={cn(
            "flex h-7 items-center gap-1.5 rounded-md px-2.5 text-[11px] font-medium transition",
            legendOpen
              ? "bg-accent-subtle text-accent"
              : "text-secondary hover:bg-surface-subtle hover:text-primary",
          )}
        >
          <Map className="h-3.5 w-3.5" />
          Legenda
        </button>
      </div>
    </>
  );
}
