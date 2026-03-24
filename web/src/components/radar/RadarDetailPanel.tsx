"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import type { RadarV2CasePreviewResponse, RadarV2SignalPreviewResponse } from "@/lib/types";
import { formatBRL, formatDate, normalizeUnknownDisplay } from "@/lib/utils";
import { Badge } from "@/components/Badge";
import { SignalFlowInline } from "@/components/radar/SignalFlowInline";
import {
  Calendar,
  ChevronLeft,
  FileText,
  Network,
  Users,
  X,
} from "lucide-react";

const ROLE_LABEL: Record<string, string> = {
  buyer: "Órgão comprador",
  supplier: "Fornecedor",
  winner: "Vencedor",
  bidder: "Licitante",
  sanctioned: "Sancionado",
  owner: "Sócio",
  employee: "Servidor",
  manager: "Gestor",
};

const ROLE_BADGE_STYLE: Record<string, React.CSSProperties> = {
  buyer:      { background: "rgba(74,130,212,0.12)",  borderColor: "rgba(74,130,212,0.35)",  color: "#7AAAF0" },
  supplier:   { background: "rgba(138,99,232,0.12)",  borderColor: "rgba(138,99,232,0.35)",  color: "#B090F8" },
  winner:     { background: "rgba(48,160,96,0.12)",   borderColor: "rgba(48,160,96,0.35)",   color: "#50D090" },
  bidder:     { background: "rgba(200,152,32,0.12)",  borderColor: "rgba(200,152,32,0.35)",  color: "#E8B840" },
  sanctioned: { background: "rgba(224,80,80,0.12)",   borderColor: "rgba(224,80,80,0.35)",   color: "#F08080" },
  owner:      { background: "rgba(212,96,32,0.12)",   borderColor: "rgba(212,96,32,0.35)",   color: "#F09050" },
  employee:   { background: "rgba(58,144,160,0.12)",  borderColor: "rgba(58,144,160,0.35)",  color: "#50C0D8" },
  manager:    { background: "rgba(110,62,214,0.12)",  borderColor: "rgba(110,62,214,0.35)",  color: "#A878F0" },
  _default:   { background: "rgba(112,112,168,0.12)", borderColor: "rgba(112,112,168,0.35)", color: "#9090C0" },
};

interface RadarDetailPanelProps {
  open: boolean;
  type: "signal" | "case" | null;
  loading: boolean;
  error: string | null;
  signalPreview: RadarV2SignalPreviewResponse | null;
  casePreview: RadarV2CasePreviewResponse | null;
  onClose: () => void;
}

export function RadarDetailPanel({
  open,
  type,
  loading,
  error,
  signalPreview,
  casePreview,
  onClose,
}: RadarDetailPanelProps) {
  const [showFlow, setShowFlow] = useState(false);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) setShowFlow(false);
  }, [open, signalPreview?.signal.id]);

  const signal = type === "signal" ? signalPreview : null;
  const caseData = type === "case" ? casePreview : null;

  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sliding panel */}
      <div
        className={`ledger-page fixed right-0 top-0 z-40 flex h-full w-full flex-col border-l border-border bg-surface-card shadow-2xl transition-transform duration-300 sm:w-[480px] lg:static lg:z-auto lg:h-auto lg:w-[420px] lg:shrink-0 lg:translate-x-0 lg:shadow-none lg:transition-none xl:w-[460px] ${
          open ? "translate-x-0" : "translate-x-full lg:hidden"
        }`}
      >
        {/* Ledger header: ID on left, date on right */}
        {(signal || caseData) && (
          <div
            className="ledger-header shrink-0 flex items-center justify-between px-4 py-2 border-b border-border"
            style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--color-muted)" }}
          >
            <span>
              {signal
                ? `SIG-${signal.signal.id.slice(-8).toUpperCase()}`
                : caseData
                ? `CASE-${caseData.case.id.slice(-8).toUpperCase()}`
                : null}
            </span>
            <span>
              {signal
                ? new Date(signal.signal.created_at ?? "").toLocaleDateString("pt-BR")
                : caseData
                ? new Date(caseData.case.created_at ?? "").toLocaleDateString("pt-BR")
                : null}
            </span>
          </div>
        )}

        {/* Header */}
        <div className="relative flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-3">
          {showFlow ? (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowFlow(false)}
                className="rounded-md p-1 text-muted hover:bg-surface-subtle"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-sm font-semibold text-primary">Teia de ligações</span>
            </div>
          ) : (
            <div>
              <p className="text-sm font-semibold text-primary">
                {type === "signal" ? "Detalhe do Sinal" : "Detalhe do Caso"}
              </p>
              <p className="text-[10px] text-muted">Análise sem sair do Radar</p>
            </div>
          )}
          <div className="flex items-center gap-1.5">
            {signal && !showFlow && (
              <button
                type="button"
                onClick={() => setShowFlow(true)}
                className="flex items-center gap-1.5 rounded-md border border-accent/30 bg-accent/10 px-2.5 py-1 text-[10px] font-semibold text-accent hover:bg-accent/20 transition-colors"
              >
                <Network className="h-3 w-3" />
                Ver teia
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-1 text-muted hover:bg-surface-subtle"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Flow */}
        {showFlow && signal && (
          <div className="flex-1 overflow-hidden p-3">
            <SignalFlowInline signalId={signal.signal.id} />
          </div>
        )}

        {/* Body */}
        {!showFlow && (
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
            {loading && (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 animate-pulse rounded-lg border border-border bg-surface-base" />
                ))}
              </div>
            )}
            {error && <p className="text-sm text-error">{error}</p>}

            {/* ── Signal detail ── */}
            {signal && (
              <div className="space-y-3">
                {/* Title + badge */}
                <div className="rounded-lg border border-border bg-surface-base p-3 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-sm font-semibold text-primary leading-snug flex-1">
                      {signal.signal.title}
                    </h4>
                    <Badge severity={signal.signal.severity} dot />
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="rounded-full border border-border bg-surface-subtle px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-muted">
                      {signal.signal.typology_code}
                    </span>
                    <span className="text-xs text-secondary">{signal.signal.typology_name}</span>
                  </div>
                  {signal.signal.investigation_summary && (
                    <div className="flex flex-wrap gap-1.5">
                      <span className="rounded-md border border-border bg-surface-subtle px-2 py-0.5 text-[10px] text-secondary">
                        Razão:{" "}
                        <span className="font-semibold text-primary">
                          {signal.signal.investigation_summary.ratio_over_threshold != null
                            ? `${Number(signal.signal.investigation_summary.ratio_over_threshold).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}×`
                            : "—"}
                        </span>
                      </span>
                      {signal.signal.investigation_summary.legal_reference && (
                        <span className="rounded-md border border-border bg-surface-subtle px-2 py-0.5 text-[10px] text-secondary">
                          {signal.signal.investigation_summary.legal_reference}
                        </span>
                      )}
                    </div>
                  )}
                  {signal.signal.summary && (
                    <p className="text-xs text-secondary leading-relaxed border-t border-border pt-2">
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
                    <p className="text-xs text-secondary leading-relaxed">
                      {signal.graph.pattern_story.why_flagged}
                    </p>
                  </div>
                )}

                {/* Period */}
                <div className="rounded-lg border border-accent/20 bg-accent/5 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-accent mb-1.5">
                    Período do padrão
                  </p>
                  <p className="text-sm text-primary">
                    {signal.graph.pattern_story.started_at
                      ? formatDate(signal.graph.pattern_story.started_at)
                      : "—"}
                    {signal.graph.pattern_story.ended_at &&
                      signal.graph.pattern_story.ended_at !== signal.graph.pattern_story.started_at && (
                        <> → {formatDate(signal.graph.pattern_story.ended_at)}</>
                      )}
                  </p>
                </div>

                {/* Flow targets */}
                {signal.graph.pattern_story.flow_targets.length > 0 && (
                  <div className="rounded-lg border border-border p-3">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
                      Destino do fluxo
                    </p>
                    <div className="space-y-1.5">
                      {signal.graph.pattern_story.flow_targets.slice(0, 5).map((t) => (
                        <div key={t.entity_id} className="flex items-center gap-2 flex-wrap">
                          <Users className="h-3.5 w-3.5 shrink-0 text-muted" />
                          <span className="text-xs text-primary font-medium">
                            {t.name.trim() || `${t.node_type} sem nome`}
                          </span>
                          {t.roles.map((role) => (
                            <span
                              key={role}
                              className="rounded-full px-2 py-0.5 text-[10px] font-semibold border"
                              style={ROLE_BADGE_STYLE[role] ?? ROLE_BADGE_STYLE._default}
                            >
                              {ROLE_LABEL[role] ?? role}
                            </span>
                          ))}
                          {t.event_count > 0 && (
                            <span className="ml-auto text-[10px] text-muted">{t.event_count} ev.</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Origin entities */}
                {signal.graph.pattern_story.started_from_entities.length > 0 && (
                  <div className="rounded-lg border border-border p-3">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
                      Entidades de origem
                    </p>
                    <div className="space-y-1.5">
                      {signal.graph.pattern_story.started_from_entities.slice(0, 5).map((e) => (
                        <div key={e.entity_id} className="flex items-center gap-2 flex-wrap">
                          <Users className="h-3.5 w-3.5 shrink-0 text-muted" />
                          <span className="text-xs text-primary font-medium">
                            {e.name.trim() || `${e.node_type} sem nome`}
                          </span>
                          {e.roles.map((role) => (
                            <span
                              key={role}
                              className="rounded-full px-2 py-0.5 text-[10px] font-semibold border"
                              style={ROLE_BADGE_STYLE[role] ?? ROLE_BADGE_STYLE._default}
                            >
                              {ROLE_LABEL[role] ?? role}
                            </span>
                          ))}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Evidences */}
                {signal.evidence.items.length > 0 && (
                  <div className="rounded-lg border border-border p-3">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
                      Evidências ({signal.evidence.total})
                    </p>
                    <div className="space-y-2">
                      {signal.evidence.items.slice(0, 5).map((item) => (
                        <div key={item.event_id} className="rounded-md border border-border bg-surface-base p-2.5 space-y-1.5">
                          <p className="text-[9px] font-bold uppercase tracking-widest text-amber">
                            {item.evidence_reason}
                          </p>
                          <p className="text-xs font-medium text-primary">{item.description}</p>
                          <div className="grid grid-cols-2 gap-x-3 text-[10px] text-secondary">
                            <span>
                              <span className="text-muted">Data </span>
                              {item.occurred_at ? formatDate(item.occurred_at) : "—"}
                            </span>
                            {typeof item.value_brl === "number" && (
                              <span>
                                <span className="text-muted">Valor </span>
                                <span className="font-semibold text-primary">{formatBRL(item.value_brl)}</span>
                              </span>
                            )}
                            <span>
                              <span className="text-muted">Modalidade </span>
                              {normalizeUnknownDisplay(item.modality)}
                            </span>
                            <span className="col-span-2 font-mono">
                              <span className="text-muted">Fonte </span>
                              {item.source_connector}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Timeline */}
                {signal.graph.timeline && signal.graph.timeline.length > 0 && (
                  <div className="rounded-lg border border-border p-3">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
                      Linha do tempo ({signal.graph.timeline.length})
                    </p>
                    <div className="space-y-2">
                      {signal.graph.timeline.slice(0, 6).map((ev) => (
                        <div key={ev.event_id} className="flex items-start gap-2 text-xs">
                          <Calendar className="h-3 w-3 mt-0.5 shrink-0 text-muted" />
                          <div>
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-mono text-[10px] text-muted">
                                {ev.occurred_at
                                  ? new Date(ev.occurred_at).toLocaleDateString("pt-BR")
                                  : "—"}
                              </span>
                              <span className="rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase bg-surface-subtle text-muted border border-border">
                                {ev.source_connector}
                              </span>
                              {typeof ev.value_brl === "number" && ev.value_brl > 0 && (
                                <span className="font-semibold text-primary text-[10px]">
                                  {formatBRL(ev.value_brl)}
                                </span>
                              )}
                            </div>
                            <p className="text-[10px] text-secondary leading-relaxed mt-0.5">
                              {ev.evidence_reason}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <Link
                  href={`/signal/${signal.signal.id}`}
                  className="flex items-center justify-center gap-2 rounded-lg border border-accent/30 bg-accent/10 px-4 py-2.5 text-sm font-semibold text-accent hover:bg-accent/20 transition-colors w-full"
                >
                  <FileText className="h-4 w-4" />
                  Ver sinal completo
                </Link>
              </div>
            )}

            {/* ── Case detail ── */}
            {caseData && (
              <div className="space-y-3">
                <div className="rounded-lg border border-border bg-surface-base p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-primary leading-snug">
                        {caseData.case.title}
                      </p>
                      <p className="text-xs text-muted mt-0.5">
                        {caseData.case.signal_count} sinais conectados
                      </p>
                    </div>
                    <Badge severity={caseData.case.severity} dot />
                  </div>
                  {caseData.case.summary && (
                    <p className="mt-2 text-xs text-secondary leading-relaxed border-t border-border pt-2">
                      {caseData.case.summary}
                    </p>
                  )}
                </div>

                <div className="rounded-lg border border-border p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
                    Sinais associados
                  </p>
                  <div className="space-y-1.5">
                    {caseData.top_signals.map((sig) => (
                      <div key={sig.id} className="rounded-md bg-surface-base p-2">
                        <p className="text-xs font-medium text-primary">{sig.title}</p>
                        <p className="mt-0.5 text-[10px] text-secondary">
                          {sig.typology_code} ·{" "}
                          <span className="font-mono">{Math.round(sig.confidence * 100)}%</span>
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-lg border border-border p-3 text-xs text-secondary">
                  Teia:{" "}
                  <span className="font-mono tabular-nums">{caseData.graph.nodes.length}</span>{" "}
                  entidades ·{" "}
                  <span className="font-mono tabular-nums">{caseData.graph.edges.length}</span>{" "}
                  conexões
                </div>

                <Link
                  href={`/case/${caseData.case.id}`}
                  className="flex items-center justify-center gap-2 rounded-lg border border-accent/30 bg-accent/10 px-4 py-2.5 text-sm font-semibold text-accent hover:bg-accent/20 transition-colors w-full"
                >
                  <FileText className="h-4 w-4" />
                  Ver caso completo
                </Link>
                <Link
                  href={`/investigation/${caseData.case.id}`}
                  className="flex items-center justify-center gap-2 rounded-lg border border-border bg-surface-subtle px-4 py-2.5 text-sm font-semibold text-secondary hover:bg-surface-base transition-colors w-full"
                >
                  <Network className="h-4 w-4" />
                  Ver teia do caso
                </Link>
                <Link
                  href={`/case/${caseData.case.id}/dossier`}
                  className="flex items-center justify-center gap-2 rounded-lg border border-border bg-surface-subtle px-4 py-2.5 text-sm font-semibold text-secondary hover:bg-surface-base transition-colors w-full"
                >
                  <FileText className="h-4 w-4" />
                  Gerar Dossiê
                </Link>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
