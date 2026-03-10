"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import type { RadarV2CasePreviewResponse, RadarV2SignalPreviewResponse } from "@/lib/types";
import { formatBRL, formatDate, normalizeUnknownDisplay } from "@/lib/utils";
import { Badge } from "@/components/Badge";
import { SignalFlowInline } from "@/components/radar/SignalFlowInline";
import { Calendar, FileText, Network, Users, X, ChevronDown, ChevronUp } from "lucide-react";

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
  buyer:      { background: "rgba(59,130,246,0.1)",  borderColor: "rgba(59,130,246,0.3)",  color: "#60a5fa" },
  supplier:   { background: "rgba(168,85,247,0.1)",  borderColor: "rgba(168,85,247,0.3)",  color: "#c084fc" },
  winner:     { background: "rgba(34,197,94,0.1)",   borderColor: "rgba(34,197,94,0.3)",   color: "#4ade80" },
  bidder:     { background: "rgba(234,179,8,0.1)",   borderColor: "rgba(234,179,8,0.3)",   color: "#facc15" },
  sanctioned: { background: "rgba(239,68,68,0.1)",   borderColor: "rgba(239,68,68,0.3)",   color: "#f87171" },
  owner:      { background: "rgba(251,146,60,0.1)",  borderColor: "rgba(251,146,60,0.3)",  color: "#fb923c" },
  employee:   { background: "rgba(20,184,166,0.1)",  borderColor: "rgba(20,184,166,0.3)",  color: "#2dd4bf" },
  manager:    { background: "rgba(99,102,241,0.1)",  borderColor: "rgba(99,102,241,0.3)",  color: "#818cf8" },
  _default:   { background: "rgba(100,116,139,0.1)", borderColor: "rgba(100,116,139,0.3)", color: "#94a3b8" },
};

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
  const [showFlow, setShowFlow] = useState(false);

  // Escape key closes modal
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  // Reset flow state when modal closes or switches signal
  useEffect(() => {
    if (!open) setShowFlow(false);
  }, [open, signalPreview?.signal.id]);

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
        className={`relative flex flex-col rounded-2xl bg-surface-card shadow-2xl transition-all duration-300 ${showFlow ? "w-full max-w-6xl" : "w-full max-w-4xl"}`}
        style={{ maxHeight: "92vh" }}
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between gap-4 border-b border-border px-6 py-4">
          {showFlow ? (
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setShowFlow(false)}
                className="rounded-md p-1.5 text-muted hover:bg-surface-subtle"
                aria-label="Voltar"
              >
                <ChevronDown className="h-4 w-4 -rotate-90" />
              </button>
              <div>
                <h3 className="font-display text-lg font-semibold text-primary">Teia de ligações</h3>
                <p className="text-xs text-muted">{signal?.signal.title}</p>
              </div>
            </div>
          ) : (
            <div>
              <h3 className="font-display text-lg font-semibold text-primary">
                {type === "signal" ? "Prévia do sinal" : "Prévia do caso"}
              </h3>
              <p className="text-xs text-muted">Entenda o padrão sem sair do Radar.</p>
            </div>
          )}
          <div className="flex items-center gap-2">
            {signal && !showFlow && (
              <button
                type="button"
                onClick={() => setShowFlow(true)}
                className="flex items-center gap-1.5 rounded-md border border-accent/30 bg-accent/10 px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent/20 transition-colors"
              >
                <Network className="h-3.5 w-3.5" />
                Ver teia
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="shrink-0 rounded-md p-1.5 text-muted hover:bg-surface-subtle"
              aria-label="Fechar"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Flow view */}
        {showFlow && signal && (
          <div className="flex-1 overflow-hidden p-4">
            <SignalFlowInline signalId={signal.signal.id} />
          </div>
        )}

        {/* Scrollable body — details view */}
        {!showFlow && <div className="overflow-y-auto flex-1 px-6 py-5">
          {loading && <p className="text-sm text-secondary">Carregando prévia...</p>}
          {error && <p className="text-sm text-error">{error}</p>}

          {/* ── Signal details ────────────────────────────────────── */}
          {signal && (
            <div className="space-y-4">
              <div className="rounded-lg border border-border bg-surface-base p-4 space-y-3">
                {/* Title row */}
                <div className="flex items-start justify-between gap-3">
                  <h4 className="text-base font-semibold text-primary leading-snug flex-1">
                    {signal.signal.title}
                  </h4>
                  <Badge severity={signal.signal.severity} dot />
                </div>

                {/* Typology chip */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="rounded-full border border-border bg-surface-subtle px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-muted">
                    {signal.signal.typology_code}
                  </span>
                  <span className="text-xs text-secondary">{signal.signal.typology_name}</span>
                </div>

                {/* Investigation metadata chips */}
                {signal.signal.investigation_summary && (
                  <div className="flex flex-wrap gap-2">
                    <div className="flex items-center gap-1.5 rounded-md border border-border bg-surface-subtle px-2.5 py-1">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                        Razão
                      </span>
                      <span className="text-xs text-primary font-medium">
                        {signal.signal.investigation_summary.ratio_over_threshold != null
                          ? `${Number(signal.signal.investigation_summary.ratio_over_threshold).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}×`
                          : "—"}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 rounded-md border border-border bg-surface-subtle px-2.5 py-1">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                        Base legal
                      </span>
                      <span className="text-xs text-primary font-medium">
                        {signal.signal.investigation_summary.legal_reference || "—"}
                      </span>
                    </div>
                  </div>
                )}

                {/* Summary */}
                {signal.signal.summary && (
                  <p className="text-sm text-secondary leading-relaxed border-t border-border pt-3">
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

              {/* Period */}
              <div className="rounded-lg border border-accent/20 bg-accent/5 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-accent mb-2">
                  Período do padrão
                </p>
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-primary">
                    {signal.graph.pattern_story.started_at
                      ? formatDate(signal.graph.pattern_story.started_at)
                      : "—"}
                  </span>
                  {signal.graph.pattern_story.ended_at &&
                    signal.graph.pattern_story.ended_at !== signal.graph.pattern_story.started_at && (
                      <>
                        <span className="text-muted">→</span>
                        <span className="text-primary">
                          {formatDate(signal.graph.pattern_story.ended_at)}
                        </span>
                      </>
                    )}
                </div>
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
                        {t.name.trim() ? (
                          <span className="text-sm text-primary font-medium">{t.name}</span>
                        ) : (
                          <span className="text-sm text-muted italic">{t.node_type} sem nome</span>
                        )}
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
                          <span className="text-[10px] text-muted ml-auto">
                            {t.event_count} evento(s)
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Entities */}
              {signal.graph.pattern_story.started_from_entities.length > 0 && (
                <div className="rounded-lg border border-border p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
                    Entidades de origem
                  </p>
                  <div className="space-y-1.5">
                    {signal.graph.pattern_story.started_from_entities.slice(0, 5).map((e) => (
                      <div key={e.entity_id} className="flex items-center gap-2 flex-wrap">
                        <Users className="h-3.5 w-3.5 shrink-0 text-muted" />
                        {e.name.trim() ? (
                          <span className="text-sm text-primary font-medium">{e.name}</span>
                        ) : (
                          <span className="text-sm text-muted italic">{e.node_type} sem nome</span>
                        )}
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
              <div className="rounded-lg border border-border p-3">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
                  Evidências ({signal.evidence.total})
                </p>
                <div className="space-y-3">
                  {signal.evidence.items.map((item) => (
                    <div key={item.event_id} className="rounded-md border border-border bg-surface-base p-3 space-y-2">
                      {/* Why it's evidence */}
                      <div className="flex items-start gap-1.5">
                        <span className="mt-0.5 shrink-0 text-[9px] font-bold uppercase tracking-widest text-amber">
                          Por que é evidência
                        </span>
                      </div>
                      <p className="text-xs text-secondary leading-relaxed -mt-1">
                        {item.evidence_reason}
                      </p>

                      {/* Description */}
                      <p className="text-sm font-medium text-primary border-t border-border pt-2">
                        {item.description}
                      </p>

                      {/* Metadata grid */}
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-secondary">
                        <div>
                          <span className="text-muted">Data</span>{" "}
                          {item.occurred_at ? formatDate(item.occurred_at) : "—"}
                        </div>
                        {typeof item.value_brl === "number" && (
                          <div>
                            <span className="text-muted">Valor</span>{" "}
                            <span className="text-primary font-medium">{formatBRL(item.value_brl)}</span>
                          </div>
                        )}
                        <div>
                          <span className="text-muted">Modalidade</span>{" "}
                          {normalizeUnknownDisplay(item.modality)}
                        </div>
                        <div>
                          <span className="text-muted">CATMAT</span>{" "}
                          {normalizeUnknownDisplay(item.catmat_group)}
                        </div>
                        <div className="col-span-2">
                          <span className="text-muted">Fonte</span>{" "}
                          <span className="font-mono">{item.source_connector}</span>
                          {" · "}
                          <span className="font-mono text-muted">{item.source_id}</span>
                        </div>
                      </div>
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
                  <div className="space-y-3">
                    {signal.graph.timeline.slice(0, 8).map((ev) => (
                      <div key={ev.event_id} className="flex items-start gap-2 text-xs">
                        <Calendar className="h-3 w-3 mt-0.5 shrink-0 text-muted" />
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-muted font-mono">
                              {ev.occurred_at
                                ? new Date(ev.occurred_at).toLocaleDateString("pt-BR")
                                : "—"}
                            </span>
                            <span className="rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider bg-surface-subtle text-muted border border-border">
                              {ev.source_connector}
                            </span>
                            {typeof ev.value_brl === "number" && ev.value_brl > 0 && (
                              <span className="text-primary font-semibold">
                                {formatBRL(ev.value_brl)}
                              </span>
                            )}
                          </div>
                          <p className="text-secondary leading-relaxed">{ev.evidence_reason}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

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

              <Link
                href={`/case/${caseData.case.id}`}
                target="_blank"
                className="flex items-center justify-center gap-2 rounded-lg border border-accent/30 bg-accent/10 px-4 py-3 text-sm font-semibold text-accent hover:bg-accent/20 transition-colors w-full"
              >
                <FileText className="h-4 w-4" />
                Ver caso completo
              </Link>

              <Link
                href={`/investigation/${caseData.case.id}`}
                target="_blank"
                className="flex items-center justify-center gap-2 rounded-lg border border-border bg-surface-subtle px-4 py-3 text-sm font-semibold text-secondary hover:bg-surface-base transition-colors w-full"
              >
                <Network className="h-4 w-4" />
                Ver teia do caso
              </Link>
            </div>
          )}
        </div>}
      </div>
    </div>
  );
}
