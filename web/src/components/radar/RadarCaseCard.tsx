"use client";

import { ChevronDown, ChevronRight, ExternalLink, Radio, DollarSign, CalendarRange } from "lucide-react";
import Link from "next/link";
import type { RadarV2CaseItem, RadarV2CasePreviewResponse } from "@/lib/types";
import { TYPOLOGY_LABELS } from "@/lib/constants";
import { formatBRL } from "@/lib/utils";
import { RadarSignalRow } from "./RadarSignalRow";

const SEV: Record<string, { dot: string; text: string; border: string; bg: string; bar: string; label: string }> = {
  critical: { dot: "bg-error",      text: "text-error",      border: "border-error/25",      bg: "bg-error/5",      bar: "bg-error",      label: "Crítico" },
  high:     { dot: "bg-amber",      text: "text-amber",      border: "border-amber/25",      bg: "bg-amber/5",      bar: "bg-amber",      label: "Alto"    },
  medium:   { dot: "bg-yellow-500", text: "text-yellow-600", border: "border-yellow-500/25", bg: "bg-yellow-500/5", bar: "bg-yellow-500", label: "Médio"   },
  low:      { dot: "bg-info",       text: "text-info",       border: "border-info/25",       bg: "bg-info/5",       bar: "bg-info",       label: "Baixo"   },
};

interface RadarCaseCardProps {
  case: RadarV2CaseItem;
  preview: RadarV2CasePreviewResponse | null;
  previewLoading: boolean;
  expanded: boolean;
  onToggleExpand: () => void;
  onSignalClick: (signalId: string) => void;
  activeSignalId?: string | null;
}

export function RadarCaseCard({
  case: item,
  preview,
  previewLoading,
  expanded,
  onToggleExpand,
  onSignalClick,
  activeSignalId,
}: RadarCaseCardProps) {
  const s = SEV[item.severity] ?? SEV.low;

  const formatPeriod = (d?: string | null) =>
    d ? new Date(d).toLocaleDateString("pt-BR", { month: "short", year: "2-digit" }) : null;
  const periodFrom = formatPeriod(item.period_start);
  const periodTo = formatPeriod(item.period_end);
  const periodStr = periodFrom && periodTo
    ? `${periodFrom} → ${periodTo}`
    : periodFrom ?? periodTo ?? null;

  const extraSignals = item.signal_count > 5 ? item.signal_count - 5 : 0;

  // Derive primary entity display name from preview or fall back to item.title heuristic
  const primaryEntity: string | null = preview
    ? (preview.case.entity_names[0] ?? null)
    : null;
  const extraEntities = preview && preview.case.entity_names.length > 1
    ? preview.case.entity_names.length - 1
    : 0;

  const foundDate = new Date(item.created_at).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  const totalValue = preview?.case.total_value_brl ?? null;

  return (
    <div className={`card-interactive relative flex overflow-hidden rounded-[10px] border bg-surface-card ${s.border} ${expanded ? s.bg : ""}`}>
      {/* Left severity accent bar */}
      <div className={`w-[3px] shrink-0 ${s.bar}`} />

      <div className="min-w-0 flex-1">
        {/* Card body */}
        <div className="p-4">

          {/* Row 1: entity name (hero) + found date */}
          <div className="mb-2 flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              {previewLoading ? (
                <div className="h-5 w-48 animate-pulse rounded bg-surface-subtle" />
              ) : primaryEntity ? (
                <h3 className="truncate font-display text-base font-bold leading-snug text-primary" title={primaryEntity}>
                  {primaryEntity}
                  {extraEntities > 0 && (
                    <span className="ml-1.5 text-xs font-normal text-muted font-sans">
                      +{extraEntities} {extraEntities === 1 ? "entidade" : "entidades"}
                    </span>
                  )}
                </h3>
              ) : (
                <h3 className="font-display text-base font-bold leading-snug text-secondary">
                  {item.entity_count} {item.entity_count !== 1 ? "entidades" : "entidade"}
                </h3>
              )}
            </div>

            {/* Found date — right-aligned, subtle mono */}
            <time className="shrink-0 font-mono text-[10px] tabular-nums text-muted">
              {foundDate}
            </time>
          </div>

          {/* Row 2: severity badge + typology pills */}
          <div className="mb-3 flex flex-wrap items-center gap-1.5">
            <span className={`audit-stamp border ${s.border} ${s.bg} ${s.text}`}>
              {s.label}
            </span>

            {item.typology_codes.slice(0, 3).map((code) => (
              <span
                key={code}
                className="rounded-[3px] border border-accent/20 bg-accent/8 px-1.5 py-0.5 font-mono text-[10px] font-bold tracking-[0.05em] text-accent"
                title={TYPOLOGY_LABELS[code]}
              >
                {code}
              </span>
            ))}
            {item.typology_codes.length > 3 && (
              <span className="font-mono text-[10px] text-muted">
                +{item.typology_codes.length - 3}
              </span>
            )}
          </div>

          {/* Row 3: stats strip */}
          <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1">
            {/* Signal count */}
            <span className="inline-flex items-center gap-1 text-[11px] text-secondary">
              <Radio className="h-3 w-3 shrink-0 text-muted" />
              <span className={`font-mono font-bold tabular-nums ${s.text}`}>{item.signal_count}</span>
              <span className="text-muted">{item.signal_count !== 1 ? "sinais" : "sinal"}</span>
            </span>

            {/* Monetary value */}
            {previewLoading ? (
              <span className="h-3 w-20 animate-pulse rounded bg-surface-subtle" />
            ) : totalValue ? (
              <span className="inline-flex items-center gap-1 text-[11px]">
                <DollarSign className="h-3 w-3 shrink-0 text-muted" />
                <span className="font-mono font-bold tabular-nums text-secondary">{formatBRL(totalValue)}</span>
              </span>
            ) : null}

            {/* Period */}
            {periodStr && (
              <span className="inline-flex items-center gap-1 text-[11px] text-muted">
                <CalendarRange className="h-3 w-3 shrink-0" />
                <span className="font-mono tabular-nums">{periodStr}</span>
              </span>
            )}
          </div>

          {/* Row 4: expand toggle */}
          <button
            type="button"
            onClick={onToggleExpand}
            className="inline-flex items-center gap-1 font-mono text-[10px] font-medium tracking-[0.08em] uppercase text-accent transition-colors duration-100 hover:text-accent/70"
          >
            {expanded ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
            {expanded
              ? "Recolher"
              : `Ver ${item.signal_count !== 1 ? "sinais" : "sinal"}`}
          </button>
        </div>

        {/* Expanded: signal rows */}
        {expanded && (
          <div className="border-t border-border bg-surface-subtle/40 px-4 pb-4 pt-3 space-y-1.5">
            {previewLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-9 animate-pulse rounded-[8px] bg-surface-hover" />
              ))
            ) : preview ? (
              <>
                {preview.top_signals.map((sig) => (
                  <RadarSignalRow
                    key={sig.id}
                    signal={sig}
                    onClick={onSignalClick}
                    active={sig.id === activeSignalId}
                  />
                ))}
                {extraSignals > 0 && (
                  <Link
                    href={`/case/${item.id}`}
                    className="inline-flex items-center gap-1 pt-1 font-mono text-[10px] text-muted transition-colors duration-100 hover:text-accent"
                  >
                    <ExternalLink className="h-3 w-3" />
                    +{extraSignals} mais — ver caso completo
                  </Link>
                )}
              </>
            ) : (
              <p className="text-xs text-muted">Sem sinais disponíveis.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
