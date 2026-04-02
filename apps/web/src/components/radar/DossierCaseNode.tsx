"use client";

import { ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import Link from "next/link";
import type { RadarV2CaseItem, RadarV2CasePreviewResponse } from "@/lib/types";
import { TYPOLOGY_LABELS } from "@/lib/constants";
import { formatBRL } from "@/lib/utils";
import { RadarSignalRow } from "./RadarSignalRow";

const SEV: Record<string, { dot: string; text: string; border: string; bg: string; label: string }> = {
  critical: { dot: "bg-error",     text: "text-error",     border: "border-error/30",     bg: "bg-error/5",     label: "Critico" },
  high:     { dot: "bg-amber",     text: "text-amber",     border: "border-amber/30",     bg: "bg-amber/5",     label: "Alto"    },
  medium:   { dot: "bg-yellow-500",text: "text-yellow-600",border: "border-yellow-500/30",bg: "bg-yellow-500/5",label: "Medio"  },
  low:      { dot: "bg-info",      text: "text-info",      border: "border-info/30",      bg: "bg-info/5",      label: "Baixo"  },
};

interface DossierCaseNodeProps {
  case: RadarV2CaseItem;
  preview: RadarV2CasePreviewResponse | null;
  previewLoading: boolean;
  expanded: boolean;
  onToggleExpand: () => void;
  onSignalClick: (caseId: string, signalId: string) => void;
  activeSignalId?: string | null;
}

export function DossierCaseNode({
  case: item,
  preview,
  previewLoading,
  expanded,
  onToggleExpand,
  onSignalClick,
  activeSignalId,
}: DossierCaseNodeProps) {
  const s = SEV[item.severity] ?? SEV.low;

  const avgConfidence = preview && preview.top_signals.length > 0
    ? preview.top_signals.reduce((sum, sig) => sum + sig.confidence, 0) / preview.top_signals.length
    : null;
  const pct = avgConfidence !== null ? Math.round(avgConfidence * 100) : null;
  const pctColor = pct !== null
    ? pct >= 80 ? "bg-success" : pct >= 50 ? "bg-amber" : "bg-error"
    : "bg-surface-subtle";

  const formatPeriod = (d?: string | null) =>
    d ? new Date(d).toLocaleDateString("pt-BR", { month: "short", year: "2-digit" }) : null;
  const periodFrom = formatPeriod(item.period_start);
  const periodTo = formatPeriod(item.period_end);
  const periodStr = [periodFrom, periodTo].filter(Boolean).join(" → ");

  const extraSignals = item.signal_count > 5 ? item.signal_count - 5 : 0;

  return (
    <div className={`rounded-xl border bg-surface-card transition-all ${s.border}`}>
      {/* Collapsed header */}
      <div className="p-4">
        {/* Row 1: severity + entity info + typology pills */}
        <div className="flex items-center gap-2 flex-wrap mb-2">
          <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${s.border} ${s.bg} ${s.text}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
            {s.label}
          </span>

          {previewLoading ? (
            <span className="h-3 w-32 animate-pulse rounded bg-surface-subtle" />
          ) : preview ? (
            <span className="text-xs font-medium text-primary truncate max-w-[200px]">
              {preview.case.entity_names.slice(0, 2).join(", ")}
              {preview.case.entity_names.length > 2 && (
                <span className="text-muted"> +{preview.case.entity_names.length - 2}</span>
              )}
            </span>
          ) : (
            <span className="text-xs text-muted">{item.entity_count} entidade{item.entity_count !== 1 ? "s" : ""}</span>
          )}

          <div className="flex-1" />

          {/* Typology pills */}
          <div className="flex items-center gap-1 flex-wrap">
            {item.typology_codes.slice(0, 3).map((code) => (
              <span key={code} className="font-mono text-[10px] font-bold text-accent bg-accent/10 rounded px-1.5 py-0.5" title={TYPOLOGY_LABELS[code]}>
                {code}
              </span>
            ))}
            {item.typology_codes.length > 3 && (
              <span className="text-[10px] text-muted">+{item.typology_codes.length - 3}</span>
            )}
          </div>
        </div>

        {/* Row 2: title */}
        <p className="text-sm font-medium text-primary line-clamp-2 mb-3">
          {item.title}
        </p>

        {/* Row 3: stats */}
        <div className="flex items-center gap-3 flex-wrap text-[11px] text-muted mb-3">
          <span>{item.signal_count} {item.signal_count !== 1 ? "sinais" : "sinal"}</span>

          {previewLoading ? (
            <span className="h-2.5 w-16 animate-pulse rounded bg-surface-subtle" />
          ) : preview?.case.total_value_brl ? (
            <span className="font-medium text-secondary">{formatBRL(preview.case.total_value_brl)}</span>
          ) : null}

          {periodStr && <span>{periodStr}</span>}

          {/* Confidence bar */}
          {pct !== null ? (
            <div className="flex items-center gap-1.5 ml-auto" title={`Confianca media: ${pct}%`}>
              <div className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-subtle">
                <div className={`h-full ${pctColor} transition-all`} style={{ width: `${pct}%` }} />
              </div>
              <span className="font-mono tabular-nums text-[10px]">{pct}%</span>
            </div>
          ) : previewLoading ? (
            <div className="ml-auto h-1.5 w-20 animate-pulse rounded-full bg-surface-subtle" />
          ) : null}
        </div>

        {/* Row 4: expand toggle */}
        <button
          type="button"
          onClick={onToggleExpand}
          className="inline-flex items-center gap-1 text-[11px] font-medium text-accent hover:text-accent/80 transition-colors"
        >
          {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          {expanded ? "Recolher" : `Ver ${item.signal_count} sinal${item.signal_count !== 1 ? "is" : ""}`}
        </button>
      </div>

      {/* Expanded: signal rows with tree-style connector */}
      {expanded && (
        <div className="border-t border-border px-4 pb-4 pt-3">
          <div className="border-l-2 border-accent/20 ml-4 pl-3 space-y-1.5">
            {previewLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-9 animate-pulse rounded-lg bg-surface-subtle" />
              ))
            ) : preview ? (
              <>
                {preview.top_signals.map((sig) => (
                  <RadarSignalRow
                    key={sig.id}
                    signal={sig}
                    onClick={(signalId) => onSignalClick(item.id, signalId)}
                    active={sig.id === activeSignalId}
                  />
                ))}
                {extraSignals > 0 && (
                  <Link
                    href={`/case/${item.id}`}
                    className="inline-flex items-center gap-1 text-[11px] text-muted hover:text-accent transition-colors pt-1"
                  >
                    <ExternalLink className="h-3 w-3" />
                    +{extraSignals} mais — ver caso completo
                  </Link>
                )}
              </>
            ) : (
              <p className="text-xs text-muted">Sem sinais disponiveis.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
