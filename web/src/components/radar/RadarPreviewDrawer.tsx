"use client";

import Link from "next/link";
import type { RadarV2CasePreviewResponse, RadarV2SignalPreviewResponse } from "@/lib/types";
import { formatBRL, formatDate, normalizeUnknownDisplay } from "@/lib/utils";
import { SEVERITY_LABELS } from "@/lib/constants";
import { Badge } from "@/components/Badge"
import { X } from "lucide-react";

interface RadarPreviewDrawerProps {
  open: boolean;
  type: "signal" | "case" | null;
  loading: boolean;
  error: string | null;
  signalPreview: RadarV2SignalPreviewResponse | null;
  casePreview: RadarV2CasePreviewResponse | null;
  onClose: () => void;
}

export function RadarPreviewDrawer({
  open,
  type,
  loading,
  error,
  signalPreview,
  casePreview,
  onClose,
}: RadarPreviewDrawerProps) {
  if (!open) return null;

  const signal = type === "signal" ? signalPreview : null;
  const caseData = type === "case" ? casePreview : null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30">
      <div className="h-full w-full max-w-2xl overflow-y-auto bg-surface-card p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 border-b border-border pb-3">
          <div>
            <h3 className="text-lg font-semibold text-primary">
              {type === "signal" ? "Previa do sinal" : "Previa do caso"}
            </h3>
            <p className="text-xs text-muted">Entenda o padrão sem sair do Radar.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-muted hover:bg-surface-subtle"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {loading && (
          <p className="mt-4 text-sm text-secondary">Carregando previa...</p>
        )}
        {error && (
          <p className="mt-4 text-sm text-red-600">{error}</p>
        )}

        {/* Signal preview */}
        {signal && (
          <div className="mt-4 space-y-4">
            <div className="rounded-lg border border-border bg-surface-card p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-base font-semibold text-primary">{signal.signal.title}</p>
                  <p className="text-xs text-secondary">
                    {signal.signal.typology_code} — {signal.signal.typology_name}
                  </p>
                </div>
                <Badge severity={signal.signal.severity} dot />
              </div>
              {signal.signal.investigation_summary && (
                <p className="mt-2 text-sm text-secondary">
                  Razao sobre limite:{" "}
                  {signal.signal.investigation_summary.ratio_over_threshold != null
                    ? `${Number(signal.signal.investigation_summary.ratio_over_threshold).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}x`
                    : "Nao informado"}
                  {" | "}
                  Base legal: {signal.signal.investigation_summary.legal_reference || "Nao informada"}
                </p>
              )}
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-accent/20 bg-accent-subtle p-3">
                <p className="text-xs font-semibold uppercase text-accent">Onde começou</p>
                <p className="mt-1 text-sm text-primary">
                  {signal.graph.pattern_story.started_at
                    ? formatDate(signal.graph.pattern_story.started_at)
                    : "Data nao informada"}
                </p>
              </div>
              <div className="rounded-lg border border-accent/20 bg-accent-subtle p-3">
                <p className="text-xs font-semibold uppercase text-accent">Para onde foi</p>
                <p className="mt-1 text-sm text-primary">
                  {signal.graph.pattern_story.ended_at
                    ? formatDate(signal.graph.pattern_story.ended_at)
                    : "Data nao informada"}
                </p>
              </div>
            </div>

            <div className="rounded-lg border border-border p-3">
              <p className="text-xs font-semibold uppercase text-muted">
                Evidências ({signal.evidence.total})
              </p>
              <div className="mt-2 space-y-2">
                {signal.evidence.items.map((item) => (
                  <div key={item.event_id} className="rounded-md bg-surface-base p-2">
                    <p className="text-sm font-medium text-primary">{item.description}</p>
                    <p className="mt-1 text-xs text-secondary">
                      {item.occurred_at ? formatDate(item.occurred_at) : "Sem data"}{" "}
                      {typeof item.value_brl === "number" ? `| ${formatBRL(item.value_brl)}` : ""}
                      {" | "}CATMAT: {normalizeUnknownDisplay(item.catmat_group)}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Link
                href={`/signal/${signal.signal.id}`}
                className="rounded-md border border-border bg-surface-card px-3 py-1.5 text-xs font-medium text-secondary hover:bg-surface-subtle"
              >
                Abrir detalhe
              </Link>
              <Link
                href={`/signal/${signal.signal.id}/graph`}
                className="rounded-md border border-accent/20 bg-accent-subtle px-3 py-1.5 text-xs font-medium text-accent hover:bg-accent-subtle/80"
              >
                Ver teia
              </Link>
            </div>
          </div>
        )}

        {/* Case preview */}
        {caseData && (
          <div className="mt-4 space-y-4">
            <div className="rounded-lg border border-border bg-surface-card p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-base font-semibold text-primary">{caseData.case.title}</p>
                  <p className="text-xs text-secondary">
                    {caseData.case.signal_count} sinais conectados
                  </p>
                </div>
                <Badge severity={caseData.case.severity} dot />
              </div>
              {caseData.case.summary && (
                <p className="mt-2 text-sm text-secondary">{caseData.case.summary}</p>
              )}
            </div>

            <div className="rounded-lg border border-border p-3">
              <p className="text-xs font-semibold uppercase text-muted">Sinais associados</p>
              <div className="mt-2 space-y-2">
                {caseData.top_signals.map((sig) => (
                  <div key={sig.id} className="rounded-md bg-surface-base p-2">
                    <p className="text-sm font-medium text-primary">{sig.title}</p>
                    <p className="mt-1 text-xs text-secondary">
                      {sig.typology_code} — {sig.typology_name} |{" "}
                      <span className="font-mono tabular-nums">{Math.round(sig.confidence * 100)}%</span>
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-border p-3 text-xs text-secondary">
              Teia do caso: <span className="font-mono tabular-nums">{caseData.graph.nodes.length}</span> entidades e{" "}
              <span className="font-mono tabular-nums">{caseData.graph.edges.length}</span> conexões.
            </div>

            <div className="flex flex-wrap gap-2">
              <Link
                href={`/case/${caseData.case.id}`}
                className="rounded-md border border-border bg-surface-card px-3 py-1.5 text-xs font-medium text-secondary hover:bg-surface-subtle"
              >
                Abrir detalhe
              </Link>
              <Link
                href={`/investigation/${caseData.case.id}`}
                className="rounded-md border border-accent/20 bg-accent-subtle px-3 py-1.5 text-xs font-medium text-accent hover:bg-accent-subtle/80"
              >
                Abrir investigacao
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
