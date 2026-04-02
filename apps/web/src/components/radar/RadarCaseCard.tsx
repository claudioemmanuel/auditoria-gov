"use client";

import { ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import Link from "next/link";
import type { RadarV2CaseItem, RadarV2CasePreviewResponse } from "@/lib/types";
import { TYPOLOGY_LABELS } from "@/lib/constants";
import { formatBRL } from "@/lib/utils";
import { RadarSignalRow } from "./RadarSignalRow";

const SEV: Record<string, { flagBg: string; label: string; accentColor: string }> = {
  critical: { flagBg: "bg-severity-critical text-white", label: "Crítico", accentColor: "var(--color-critical, #ef4444)" },
  high:     { flagBg: "bg-severity-high text-white",     label: "Alto",    accentColor: "var(--color-high, #f97316)"    },
  medium:   { flagBg: "bg-severity-medium text-white",   label: "Médio",   accentColor: "var(--color-medium, #eab308)"  },
  low:      { flagBg: "bg-severity-low text-white",      label: "Baixo",   accentColor: "var(--color-low, #0ea5e9)"     },
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
  const periodTo   = formatPeriod(item.period_end);
  const periodStr  = periodFrom && periodTo
    ? `${periodFrom} – ${periodTo}`
    : periodFrom ?? periodTo ?? null;

  const extraSignals  = item.signal_count > 5 ? item.signal_count - 5 : 0;
  const primaryEntity: string | null = preview ? (preview.case.entity_names[0] ?? null) : null;
  const extraEntities = preview && preview.case.entity_names.length > 1
    ? preview.case.entity_names.length - 1
    : 0;

  const foundDate = new Date(item.created_at).toLocaleDateString("pt-BR", {
    day: "2-digit", month: "short", year: "numeric",
  });

  const totalValue = preview?.case.total_value_brl ?? null;

  return (
    <div
      className={`ledger-row transition-colors ${expanded ? "bg-newsprint-subtle" : ""}`}
      style={{ borderLeft: `2px solid ${s.accentColor}` }}
    >

      {/* Card body */}
      <div className="p-4 sm:p-5">

        {/* Row 1: severity flag + typology codes + date */}
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className={`font-mono text-[9px] font-bold tracking-[0.2em] uppercase px-2 py-1 ${s.flagBg}`}>
            {s.label}
          </span>

          {item.typology_codes.slice(0, 4).map((code) => (
            <span
              key={code}
              className="data-value uppercase text-xs border border-border px-1.5 py-0.5 font-bold tracking-[0.1em] text-masthead"
              title={TYPOLOGY_LABELS[code]}
            >
              {code}
            </span>
          ))}
          {item.typology_codes.length > 4 && (
            <span className="font-mono text-[9px] text-ink-muted">
              +{item.typology_codes.length - 4}
            </span>
          )}

          <time className="ml-auto font-mono text-[10px] tabular-nums text-ink-muted shrink-0">
            {foundDate}
          </time>
        </div>

        {/* Row 2: entity name — headline de artigo */}
        <div className="mb-3">
          {previewLoading ? (
            <div className="h-6 w-56 animate-pulse bg-newsprint-hover" />
          ) : primaryEntity ? (
            <h3
              className="font-bold text-ink leading-snug text-lg"
              title={primaryEntity}
            >
              {primaryEntity}
              {extraEntities > 0 && (
                <span className="ml-2 text-sm font-normal text-ink-muted">
                  +{extraEntities} {extraEntities === 1 ? "entidade" : "entidades"}
                </span>
              )}
            </h3>
          ) : (
            <h3 className="font-bold text-ink-secondary leading-snug text-lg">
              {item.entity_count} {item.entity_count !== 1 ? "entidades" : "entidade"}
            </h3>
          )}
        </div>

        {/* Row 3: stats byline */}
        <div className="byline mb-3 flex flex-wrap items-center gap-x-3 gap-y-1">
          <span>
            <span className="text-ink font-bold tabular-nums">{item.signal_count}</span>
            {" "}{item.signal_count !== 1 ? "sinais" : "sinal"}
          </span>

          {previewLoading ? (
            <span className="h-3 w-20 animate-pulse bg-newsprint-hover inline-block" />
          ) : totalValue ? (
            <span>
              <span className="text-ink font-bold tabular-nums">{formatBRL(totalValue)}</span>
            </span>
          ) : null}

          {periodStr && (
            <span className="tabular-nums">{periodStr}</span>
          )}
        </div>

        {/* Row 4: expand toggle */}
        <button
          type="button"
          onClick={onToggleExpand}
          className="byline flex items-center gap-1 text-masthead hover:text-masthead-hover transition-colors duration-100"
        >
          {expanded
            ? <ChevronDown className="h-3 w-3" />
            : <ChevronRight className="h-3 w-3" />
          }
          {expanded ? "RECOLHER" : `VER ${item.signal_count !== 1 ? "SINAIS" : "SINAL"}`}
        </button>
      </div>

      {/* Expanded: signal rows */}
      {expanded && (
        <div className="border-t border-border bg-newsprint-subtle px-4 pb-4 pt-3 space-y-px">
          {previewLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-9 animate-pulse bg-newsprint-hover" />
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
                  className="byline inline-flex items-center gap-1 pt-2 text-masthead hover:text-masthead-hover transition-colors duration-100"
                >
                  <ExternalLink className="h-3 w-3" />
                  +{extraSignals} MAIS — VER CASO COMPLETO
                </Link>
              )}
            </>
          ) : (
            <p className="text-xs text-ink-muted">Sem sinais disponíveis.</p>
          )}
        </div>
      )}
    </div>
  );
}
