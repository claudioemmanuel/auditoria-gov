"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import type { EntityDetail, RadarV2SignalPreviewResponse } from "@/lib/types";
import { getEntity, getRadarV2SignalPreview } from "@/lib/api";
import { formatBRL, formatDate, normalizeUnknownDisplay } from "@/lib/utils";
import { Badge } from "@/components/Badge";
import { SignalFlowInline } from "@/components/radar/SignalFlowInline";
import { EntityNetworkGraph } from "@/components/EntityNetworkGraph";
import {
  Building2,
  Calendar,
  ChevronLeft,
  ChevronRight as ChevronRightIcon,
  FileText,
  Landmark,
  Network,
  User,
  Users,
  X,
} from "lucide-react";

/** Read CSS variable at runtime */
function getCSSToken(varName: string): string {
  if (typeof document === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}

/** Build role badge style from CSS token */
function getRoleBadgeStyle(role: string): React.CSSProperties {
  const tokenMap: Record<string, string> = {
    buyer:      "--color-role-buyer",
    supplier:   "--color-role-supplier",
    winner:     "--color-role-winner",
    bidder:     "--color-role-bidder",
    sanctioned: "--color-role-sanctioned",
    owner:      "--color-role-owner",
    employee:   "--color-role-employee",
    manager:    "--color-role-manager",
    _default:   "--color-muted",
  };
  const token = tokenMap[role] || tokenMap._default;
  const color = getCSSToken(token);
  
  try {
    const hex = color.trim();
    if (!hex.startsWith("#")) {
      return { background: "rgba(112,112,168,0.12)", borderColor: "rgba(112,112,168,0.35)", color: "#9090C0" };
    }
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return {
      background: `rgba(${r},${g},${b},0.12)`,
      borderColor: `rgba(${r},${g},${b},0.35)`,
      color: hex,
    };
  } catch {
    return { background: "rgba(112,112,168,0.12)", borderColor: "rgba(112,112,168,0.35)", color: "#9090C0" };
  }
}

const ROLE_LABEL: Record<string, string> = {
  buyer: "Orgao comprador",
  supplier: "Fornecedor",
  winner: "Vencedor",
  bidder: "Licitante",
  sanctioned: "Sancionado",
  owner: "Socio",
  employee: "Servidor",
  manager: "Gestor",
};

const TYPE_CONFIG: Record<string, { label: string; icon: typeof Building2; color: string }> = {
  company: { label: "Empresa", icon: Building2, color: "bg-emerald-500/10 text-emerald-600" },
  person: { label: "Pessoa", icon: User, color: "bg-blue-500/10 text-blue-600" },
  org: { label: "Orgao", icon: Landmark, color: "bg-violet-500/10 text-violet-600" },
};

interface DossierDetailPanelProps {
  panelMode: "signal" | "entity" | "network" | null;
  selectedSignalId: string | null;
  selectedEntityId: string | null;
  selectedCaseId: string | null;
  onClose: () => void;
  onGoBack: () => void;
  onSelectEntity: (entityId: string) => void;
  onNavigateToNetwork: (entityId: string) => void;
}

export function DossierDetailPanel({
  panelMode,
  selectedSignalId,
  selectedEntityId,
  selectedCaseId,
  onClose,
  onGoBack,
  onSelectEntity,
  onNavigateToNetwork,
}: DossierDetailPanelProps) {
  const open = panelMode !== null;

  // Signal state
  const [signalPreview, setSignalPreview] = useState<RadarV2SignalPreviewResponse | null>(null);
  const [signalLoading, setSignalLoading] = useState(false);
  const [signalError, setSignalError] = useState<string | null>(null);
  const [showFlow, setShowFlow] = useState(false);

  // Entity state
  const [entityDetail, setEntityDetail] = useState<EntityDetail | null>(null);
  const [entityLoading, setEntityLoading] = useState(false);
  const [entityError, setEntityError] = useState<string | null>(null);

  // Escape to close
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  // Load signal preview (with staleness guard)
  useEffect(() => {
    if (!selectedSignalId || panelMode !== "signal") {
      setSignalPreview(null);
      setShowFlow(false);
      return;
    }
    let stale = false;
    setSignalLoading(true);
    setSignalError(null);
    setShowFlow(false);
    getRadarV2SignalPreview(selectedSignalId, { limit: 10 })
      .then((data) => { if (!stale) setSignalPreview(data); })
      .catch(() => { if (!stale) setSignalError("Nao foi possivel carregar a previa do sinal"); })
      .finally(() => { if (!stale) setSignalLoading(false); });
    return () => { stale = true; };
  }, [selectedSignalId, panelMode]);

  // Load entity detail (with staleness guard)
  useEffect(() => {
    if (!selectedEntityId || panelMode !== "entity") {
      setEntityDetail(null);
      return;
    }
    let stale = false;
    setEntityLoading(true);
    setEntityError(null);
    getEntity(selectedEntityId)
      .then((data) => { if (!stale) setEntityDetail(data); })
      .catch(() => { if (!stale) setEntityError("Nao foi possivel carregar a entidade"); })
      .finally(() => { if (!stale) setEntityLoading(false); });
    return () => { stale = true; };
  }, [selectedEntityId, panelMode]);

  // Breadcrumb segments
  const breadcrumbs: { label: string; onClick?: () => void }[] = [];
  if (selectedCaseId) {
    breadcrumbs.push({
      label: "Caso",
      onClick: panelMode !== null ? () => onClose() : undefined,
    });
  }
  if (selectedSignalId) {
    breadcrumbs.push({
      label: "Sinal",
      onClick: panelMode === "entity" ? () => onGoBack() : undefined,
    });
  }
  if (selectedEntityId && panelMode === "entity") {
    breadcrumbs.push({ label: "Entidade" });
  }

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
        className={`fixed right-0 top-0 z-40 flex h-full w-full flex-col border-l border-border bg-surface-card shadow-2xl transition-transform duration-300 sm:w-[480px] lg:static lg:z-auto lg:h-auto lg:w-[420px] lg:shrink-0 lg:translate-x-0 lg:shadow-none lg:transition-none xl:w-[460px] ${
          open ? "translate-x-0" : "translate-x-full lg:hidden"
        }`}
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-3">
          {showFlow ? (
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => setShowFlow(false)} className="rounded-md p-1 text-muted hover:bg-surface-subtle">
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-sm font-semibold text-primary">Teia de ligacoes</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 min-w-0">
              {breadcrumbs.length > 1 && (
                <button type="button" onClick={onGoBack} className="rounded-md p-1 text-muted hover:bg-surface-subtle shrink-0">
                  <ChevronLeft className="h-4 w-4" />
                </button>
              )}
              <div className="min-w-0">
                {/* Breadcrumb */}
                <div className="flex items-center gap-1 text-[10px] text-muted">
                  {breadcrumbs.map((bc, i) => (
                    <React.Fragment key={i}>
                      {i > 0 && <ChevronRightIcon className="h-2.5 w-2.5" />}
                      {bc.onClick ? (
                        <button type="button" onClick={bc.onClick} className="hover:text-accent transition-colors">
                          {bc.label}
                        </button>
                      ) : (
                        <span className="text-secondary font-semibold">{bc.label}</span>
                      )}
                    </React.Fragment>
                  ))}
                </div>
                <p className="text-sm font-semibold text-primary">
                  {panelMode === "signal" ? "Detalhe do Sinal" : panelMode === "entity" ? "Perfil da Entidade" : "Rede"}
                </p>
              </div>
            </div>
          )}
          <div className="flex items-center gap-1.5 shrink-0">
            {panelMode === "signal" && signalPreview && !showFlow && (
              <button
                type="button"
                onClick={() => setShowFlow(true)}
                className="flex items-center gap-1.5 rounded-md border border-accent/30 bg-accent/10 px-2.5 py-1 text-[10px] font-semibold text-accent hover:bg-accent/20 transition-colors"
              >
                <Network className="h-3 w-3" />
                Ver teia
              </button>
            )}
            <button type="button" onClick={onClose} className="rounded-md p-1 text-muted hover:bg-surface-subtle">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Flow view */}
        {showFlow && signalPreview && (
          <div className="flex-1 overflow-hidden p-3">
            <SignalFlowInline signalId={signalPreview.signal.id} />
          </div>
        )}

        {/* Body */}
        {!showFlow && (
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
            {/* ── Signal mode ── */}
            {panelMode === "signal" && (
              <>
                {signalLoading && (
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-16 animate-pulse rounded-lg border border-border bg-surface-base" />
                    ))}
                  </div>
                )}
                {signalError && <p className="text-sm text-error">{signalError}</p>}
                {signalPreview && <SignalContent signal={signalPreview} onSelectEntity={onSelectEntity} />}
              </>
            )}

            {/* ── Entity mode ── */}
            {panelMode === "entity" && (
              <>
                {entityLoading && (
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-16 animate-pulse rounded-lg border border-border bg-surface-base" />
                    ))}
                  </div>
                )}
                {entityError && <p className="text-sm text-error">{entityError}</p>}
                {entityDetail && selectedEntityId && (
                  <EntityContent
                    entity={entityDetail}
                    entityId={selectedEntityId}
                    onNavigateToNetwork={onNavigateToNetwork}
                  />
                )}
              </>
            )}
          </div>
        )}
      </div>
    </>
  );
}

// ── Signal content ──────────────────────────────────────────────────────────

function SignalContent({
  signal,
  onSelectEntity,
}: {
  signal: RadarV2SignalPreviewResponse;
  onSelectEntity: (entityId: string) => void;
}) {
  return (
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
              Razao:{" "}
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
          Periodo do padrao
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

      {/* Flow targets — clickable entities */}
      {signal.graph.pattern_story.flow_targets.length > 0 && (
        <div className="rounded-lg border border-border p-3">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
            Destino do fluxo
          </p>
          <div className="space-y-1.5">
            {signal.graph.pattern_story.flow_targets.slice(0, 5).map((t) => (
              <div key={t.entity_id} className="flex items-center gap-2 flex-wrap">
                <Users className="h-3.5 w-3.5 shrink-0 text-muted" />
                <button
                  type="button"
                  onClick={() => onSelectEntity(t.entity_id)}
                  className="text-xs text-primary font-medium hover:text-accent transition-colors underline-offset-2 hover:underline"
                >
                  {t.name.trim() || `${t.node_type} sem nome`}
                </button>
                {t.roles.map((role) => (
                  <span
                    key={role}
                    className="rounded-full px-2 py-0.5 text-[10px] font-semibold border"
                    style={getRoleBadgeStyle(role)}
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

      {/* Origin entities — clickable */}
      {signal.graph.pattern_story.started_from_entities.length > 0 && (
        <div className="rounded-lg border border-border p-3">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
            Entidades de origem
          </p>
          <div className="space-y-1.5">
            {signal.graph.pattern_story.started_from_entities.slice(0, 5).map((e) => (
              <div key={e.entity_id} className="flex items-center gap-2 flex-wrap">
                <Users className="h-3.5 w-3.5 shrink-0 text-muted" />
                <button
                  type="button"
                  onClick={() => onSelectEntity(e.entity_id)}
                  className="text-xs text-primary font-medium hover:text-accent transition-colors underline-offset-2 hover:underline"
                >
                  {e.name.trim() || `${e.node_type} sem nome`}
                </button>
                {e.roles.map((role) => (
                  <span
                    key={role}
                    className="rounded-full px-2 py-0.5 text-[10px] font-semibold border"
                    style={getRoleBadgeStyle(role)}
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
            Evidencias ({signal.evidence.total})
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
  );
}

// ── Entity content ──────────────────────────────────────────────────────────

function EntityContent({
  entity,
  entityId,
  onNavigateToNetwork,
}: {
  entity: EntityDetail;
  entityId: string;
  onNavigateToNetwork: (entityId: string) => void;
}) {
  const config = TYPE_CONFIG[entity.type] ?? TYPE_CONFIG.company;
  const Icon = config.icon;
  const cnpj = entity.identifiers?.cnpj || entity.identifiers?.cpf;

  return (
    <div className="space-y-3">
      {/* Name + type */}
      <div className="rounded-lg border border-border bg-surface-base p-3 space-y-2">
        <div className="flex items-start gap-3">
          <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${config.color}`}>
            <Icon className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <h4 className="text-sm font-semibold text-primary leading-snug">{entity.name}</h4>
            <div className="mt-1 flex items-center gap-2 flex-wrap">
              <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-medium ${config.color}`}>
                {config.label}
              </span>
              {cnpj && <span className="font-mono text-[10px] text-muted">{cnpj}</span>}
            </div>
          </div>
        </div>
      </div>

      {/* Identifiers */}
      {Object.keys(entity.identifiers).length > 0 && (
        <div className="rounded-lg border border-border p-3">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
            Identificadores
          </p>
          <div className="space-y-1">
            {Object.entries(entity.identifiers).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between text-xs">
                <span className="text-muted uppercase font-mono text-[10px]">{key}</span>
                <span className="text-primary font-mono text-[10px]">{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Aliases */}
      {entity.aliases.length > 0 && (
        <div className="rounded-lg border border-border p-3">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
            Aliases ({entity.aliases.length})
          </p>
          <div className="space-y-1">
            {entity.aliases.slice(0, 10).map((a, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span className="rounded bg-surface-subtle px-1.5 py-0.5 text-[10px] text-muted font-mono">{a.type}</span>
                <span className="text-primary flex-1 truncate">{a.value}</span>
                <span className="text-[10px] text-muted">{a.source}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Mini network graph */}
      <div className="rounded-lg border border-border p-3">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2">
          Rede de conexoes
        </p>
        <div className="h-[280px] rounded-lg overflow-hidden border border-border">
          <EntityNetworkGraph entityId={entityId} />
        </div>
      </div>

      {/* Actions */}
      <button
        type="button"
        onClick={() => onNavigateToNetwork(entityId)}
        className="flex items-center justify-center gap-2 rounded-lg border border-accent/30 bg-accent/10 px-4 py-2.5 text-sm font-semibold text-accent hover:bg-accent/20 transition-colors w-full"
      >
        <Network className="h-4 w-4" />
        Ver Rede Completa
      </button>
      <Link
        href={`/entity/${entityId}`}
        className="flex items-center justify-center gap-2 rounded-lg border border-border bg-surface-subtle px-4 py-2.5 text-sm font-semibold text-secondary hover:bg-surface-base transition-colors w-full"
      >
        <FileText className="h-4 w-4" />
        Ver perfil completo
      </Link>
    </div>
  );
}
