"use client";

import Link from "next/link";
import { useEffect } from "react";
import type { RadarV2CasePreviewResponse, RadarV2SignalPreviewResponse } from "@/lib/types";
import { formatBRL, formatDate, normalizeUnknownDisplay } from "@/lib/utils";
import { Badge } from "@/components/Badge";
import { Calendar, Network, Users, X } from "lucide-react";

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
  // Escape key closes modal
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  const signal = type === "signal" ? signalPreview : null;
  const caseData = type === "case" ? casePreview : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="relative flex w-full max-w-4xl flex-col rounded-2xl bg-surface-card shadow-2xl"
        style={{ maxHeight: "90vh" }}
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between gap-4 border-b border-border px-6 py-4">
          <div>
            <h3 className="font-display text-lg font-semibold text-primary">
              {type === "signal" ? "Prévia do sinal" : "Prévia do caso"}
            </h3>
            <p className="text-xs text-muted">Entenda o padrão sem sair do Radar.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-md p-1.5 text-muted hover:bg-surface-subtle"
            aria-label="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="overflow-y-auto flex-1 px-6 py-5">
          {loading && <p className="text-sm text-secondary">Carregando prévia...</p>}
          {error && <p className="text-sm text-error">{error}</p>}

          {/* ── Signal details ────────────────────────────────────── */}
          {signal && (
            <div className="space-y-4">
              <div className="rounded-lg border border-border bg-surface-base p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-base font-semibold text-primary">{signal.signal.title}</p>
                    <p className="text-xs text-secondary mt-0.5">
                      {signal.signal.typology_code} — {signal.signal.typology_name}
                    </p>
                  </div>
                  <Badge severity={signal.signal.severity} dot />
                </div>
                {signal.signal.investigation_summary && (
                  <p className="mt-2 text-sm text-secondary">
                    Razão sobre limite:{" "}
                    {signal.signal.investigation_summary.ratio_over_threshold != null
                      ? `${Number(
                          signal.signal.investigation_summary.ratio_over_threshold,
                        ).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}×`
                      : "Não informado"}
                    {" | "}
                    Base legal:{" "}
                    {signal.signal.investigation_summary.legal_reference || "Não informada"}
                  </p>
                )}
                {signal.signal.summary && (
                  <p className="mt-2 text-sm text-secondary leading-relaxed">
                    {signal.signal.summary}
                  </p>
                )}
              </div>

              {/* Why flagged */}
              {signal.graph.pattern_story.why_flagged && (
                <div className="rounded-lg border border-amber/20 bg-amber/5 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-amber mb-1">
                    Por que foi sinalizado
                  </p>
                  <p className="text-sm text-secondary leading-relaxed">
                    {signal.graph.pattern_story.why_flagged}
                  </p>
                </div>
              )}

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-accent/20 bg-accent/5 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-accent">
                    Onde começou
                  </p>
                  <p className="mt-1 text-sm text-primary">
                    {signal.graph.pattern_story.started_at
                      ? formatDate(signal.graph.pattern_story.started_at)
                      : "Data não informada"}
                  </p>
                </div>
                <div className="rounded-lg border border-accent/20 bg-accent/5 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-accent">
                    Para onde foi
                  </p>
                  <p className="mt-1 text-sm text-primary">
                    {signal.graph.pattern_story.ended_at
                      ? formatDate(signal.graph.pattern_story.ended_at)
                      : "Data não informada"}
                  </p>
                </div>
              </div>

              {/* Entities */}
              {signal.graph.pattern_story.started_from_entities.length > 0 && (
                <div className="rounded-lg border border-border p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
                    Entidades de origem
                  </p>
                  <div className="space-y-1.5">
                    {signal.graph.pattern_story.started_from_entities.slice(0, 5).map((e) => (
                      <div key={e.entity_id} className="flex items-center gap-2 text-sm">
                        <Users className="h-3.5 w-3.5 shrink-0 text-muted" />
                        <span className="text-primary font-medium">{e.name}</span>
                        {e.roles.length > 0 && (
                          <span className="text-muted text-xs">({e.roles.join(", ")})</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Evidences */}
              <div className="rounded-lg border border-border p-3">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
                  Evidências ({signal.evidence.total})
                </p>
                <div className="space-y-2">
                  {signal.evidence.items.map((item) => (
                    <div key={item.event_id} className="rounded-md bg-surface-base p-2">
                      <p className="text-sm font-medium text-primary">{item.description}</p>
                      <p className="mt-0.5 text-xs text-secondary">
                        {item.occurred_at ? formatDate(item.occurred_at) : "Sem data"}
                        {typeof item.value_brl === "number"
                          ? ` | ${formatBRL(item.value_brl)}`
                          : ""}
                        {" | "}CATMAT: {normalizeUnknownDisplay(item.catmat_group)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Timeline */}
              {signal.graph.timeline && signal.graph.timeline.length > 0 && (
                <div className="rounded-lg border border-border p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
                    Linha do tempo ({signal.graph.timeline.length} evento(s))
                  </p>
                  <div className="space-y-2">
                    {signal.graph.timeline.slice(0, 8).map((ev) => (
                      <div key={ev.event_id} className="flex items-start gap-2 text-xs text-secondary">
                        <Calendar className="h-3 w-3 mt-0.5 shrink-0 text-muted" />
                        <div>
                          <span className="text-muted font-mono">
                            {ev.occurred_at
                              ? new Date(ev.occurred_at).toLocaleDateString("pt-BR")
                              : "—"}
                          </span>
                          {" — "}
                          <span>{ev.description}</span>
                          {typeof ev.value_brl === "number" && ev.value_brl > 0 && (
                            <span className="ml-1 text-primary font-medium">
                              {formatBRL(ev.value_brl)}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Ver teia button */}
              <Link
                href={`/signal/${signal.signal.id}/flow`}
                target="_blank"
                className="flex items-center justify-center gap-2 rounded-lg border border-accent/30 bg-accent/10 px-4 py-3 text-sm font-semibold text-accent hover:bg-accent/20 transition-colors w-full"
              >
                <Network className="h-4 w-4" />
                Ver teia de ligações em tela cheia
              </Link>
            </div>
          )}

          {/* ── Case details ──────────────────────────────────────── */}
          {caseData && (
            <div className="space-y-4">
              <div className="rounded-lg border border-border bg-surface-base p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-base font-semibold text-primary">{caseData.case.title}</p>
                    <p className="text-xs text-secondary mt-0.5">
                      {caseData.case.signal_count} sinais conectados
                    </p>
                  </div>
                  <Badge severity={caseData.case.severity} dot />
                </div>
                {caseData.case.summary && (
                  <p className="mt-2 text-sm text-secondary leading-relaxed">
                    {caseData.case.summary}
                  </p>
                )}
              </div>

              <div className="rounded-lg border border-border p-3">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
                  Sinais associados
                </p>
                <div className="space-y-2">
                  {caseData.top_signals.map((sig) => (
                    <div key={sig.id} className="rounded-md bg-surface-base p-2">
                      <p className="text-sm font-medium text-primary">{sig.title}</p>
                      <p className="mt-0.5 text-xs text-secondary">
                        {sig.typology_code} — {sig.typology_name}{" "}
                        <span className="font-mono tabular-nums">
                          | {Math.round(sig.confidence * 100)}% confiança
                        </span>
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-border p-3 text-xs text-secondary">
                Teia do caso:{" "}
                <span className="font-mono tabular-nums">{caseData.graph.nodes.length}</span>{" "}
                entidades e{" "}
                <span className="font-mono tabular-nums">{caseData.graph.edges.length}</span>{" "}
                conexões.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
