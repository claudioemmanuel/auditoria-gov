"use client";

import Link from "next/link";
import { severityColor } from "@/lib/utils";
import { SEVERITY_LABELS } from "@/lib/constants";
import type { SignalSeverity } from "@/lib/types";
import { ArrowLeft, CircleDot, AlertTriangle } from "lucide-react";

interface InvestigationToolbarProps {
  caseId: string;
  caseTitle: string;
  caseSeverity: SignalSeverity;
  nodeCount: number;
  edgeCount: number;
  seedCount: number;
  truncated: boolean;
  expanding: boolean;
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
}: InvestigationToolbarProps) {
  return (
    <div className="absolute top-3 left-3 right-3 z-20 flex items-center gap-2.5 rounded-xl border border-gray-200/80 bg-white/95 px-3.5 py-2 shadow-md backdrop-blur-sm">
      {/* Back */}
      <Link
        href={`/case/${caseId}`}
        className="flex h-7 w-7 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-700"
        title="Voltar ao caso"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
      </Link>

      <div className="h-4 w-px bg-gray-200" />

      {/* Title */}
      <h1 className="min-w-0 flex-1 truncate text-[13px] font-semibold text-gray-800">
        {caseTitle}
      </h1>

      <span
        className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${severityColor(caseSeverity)}`}
      >
        {SEVERITY_LABELS[caseSeverity]}
      </span>

      <div className="h-4 w-px bg-gray-200" />

      {/* Stats */}
      <div className="flex items-center gap-2.5 text-[10px] text-gray-400">
        <span className="flex items-center gap-1">
          <CircleDot className="h-2.5 w-2.5" />
          <strong className="font-semibold text-gray-600">{nodeCount}</strong> nos
        </span>
        <span>
          <strong className="font-semibold text-gray-600">{edgeCount}</strong> arestas
        </span>
        <span>
          <strong className="font-semibold text-gray-600">{seedCount}</strong> seeds
        </span>
      </div>

      {/* Status indicators */}
      {truncated && (
        <span className="flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-600 border border-amber-200">
          <AlertTriangle className="h-2.5 w-2.5" />
          Truncado
        </span>
      )}

      {expanding && (
        <span className="flex items-center gap-1.5 text-[10px] font-medium text-gov-blue-600">
          <div className="h-2.5 w-2.5 animate-spin rounded-full border-[1.5px] border-gov-blue-500 border-t-transparent" />
          Expandindo...
        </span>
      )}
    </div>
  );
}
