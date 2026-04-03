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
      {/* Top bar: case info — modernized with Navy/Red/Cyan design tokens */}
      <div className="absolute top-4 left-4 right-4 z-20 flex items-center gap-3 rounded-lg border border-[var(--color-border-light)] bg-white shadow-[var(--shadow-md)] backdrop-blur-sm p-4">
        {/* Back link */}
        <Link
          href={`/case/${caseId}`}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--color-text-secondary)] transition hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-accent-alert)]"
          title="Voltar ao caso"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>

        <div className="h-5 w-px bg-[var(--color-border-light)]" />

        {/* Title & severity */}
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-sm font-bold font-[var(--font-display)] text-[var(--color-text-primary)]">
            {caseTitle}
          </h1>
        </div>

        <span
          className={cn(
            "shrink-0 rounded-full px-3 py-1 text-xs font-semibold",
            severityColor(caseSeverity),
          )}
        >
          {SEVERITY_LABELS[caseSeverity]}
        </span>

        <div className="h-5 w-px bg-[var(--color-border-light)]" />

        {/* Stats — improved typography and spacing */}
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-2">
            <CircleDot className="h-3 w-3 text-[var(--color-accent-trust)]" />
            <span className="text-[var(--color-text-secondary)]">
              <strong className="font-semibold text-[var(--color-text-primary)]">{nodeCount}</strong> nós
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[var(--color-text-secondary)]">
              <strong className="font-semibold text-[var(--color-text-primary)]">{edgeCount}</strong> arestas
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[var(--color-text-secondary)]">
              <strong className="font-semibold text-[var(--color-text-primary)]">{seedCount}</strong> seeds
            </span>
          </div>
        </div>

        {/* Status indicators — updated colors */}
        {truncated && (
          <span className="flex items-center gap-1.5 rounded-full border border-[var(--color-high)]/30 bg-[#FEF3C7] px-3 py-1 text-xs font-semibold text-[var(--color-high)]">
            <AlertTriangle className="h-3.5 w-3.5" />
            Truncado
          </span>
        )}

        {expanding && (
          <span className="flex items-center gap-1.5 text-xs font-semibold text-[var(--color-accent-alert)]">
            <div className="h-3 w-3 animate-spin rounded-full border-2 border-[var(--color-accent-alert)] border-t-transparent" />
            Expandindo...
          </span>
        )}
      </div>

      {/* Bottom-left toolbar: canvas actions — modernized */}
      <div className="absolute bottom-16 left-4 z-20 flex gap-1 rounded-lg border border-[var(--color-border-light)] bg-white shadow-[var(--shadow-md)] p-1">
        <button
          onClick={onFitView}
          title="Ajustar vista (Espaço)"
          className="flex h-8 items-center gap-1.5 rounded-md px-3 text-xs font-semibold text-[var(--color-text-secondary)] transition hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
        >
          <Maximize2 className="h-4 w-4" />
          Ajustar
        </button>
        <div className="w-px bg-[var(--color-border-light)]" />
        <button
          onClick={onToggleLegend}
          title="Mostrar legenda"
          className={cn(
            "flex h-8 items-center gap-1.5 rounded-md px-3 text-xs font-semibold transition",
            legendOpen
              ? "bg-[var(--color-accent-alert)]/10 text-[var(--color-accent-alert)]"
              : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]",
          )}
        >
          <Map className="h-4 w-4" />
          Legenda
        </button>
      </div>
    </>
  );
}
