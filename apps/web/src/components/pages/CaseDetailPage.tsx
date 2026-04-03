"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { clsx } from "clsx";
import { getCase, fetchCaseLegalHypotheses, fetchRelatedCases } from "@/lib/api";
import { SeverityBadge } from "@/components/Badge";
import { PageHeader } from "@/components/PageHeader";
import { DetailSkeleton } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { formatBRL, formatDate } from "@/lib/utils";
import { TYPOLOGY_LABELS } from "@/lib/constants";
import {
  Network,
  Radar,
  Building2,
  User,
  Landmark,
  ExternalLink,
  FileText,
  Scale,
  AlertTriangle,
  Activity,
} from "lucide-react";
import type {
  SignalSeverity,
  CaseDetail,
  CaseSignal,
  RelatedCase,
  LegalHypothesis,
} from "@/lib/types";

/* ── Helpers ────────────────────────────────────────────────────── */

const SEVERITY_ORDER: Record<SignalSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

function sortBySeverity(signals: CaseSignal[]): CaseSignal[] {
  return [...signals].sort(
    (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity],
  );
}

const SIGNAL_CARD_CLASS: Record<SignalSeverity, string> = {
  critical: "ow-signal-card ow-signal-card-critical",
  high: "ow-signal-card ow-signal-card-high",
  medium: "ow-signal-card ow-signal-card-medium",
  low: "ow-signal-card ow-signal-card-low",
};

function EntityTypeIcon({ type }: { type: string }) {
  const t = type.toLowerCase();
  if (t === "person" || t === "individual" || t === "cpf") {
    return <User className="h-3.5 w-3.5 shrink-0" style={{ color: "var(--color-text-3)" }} />;
  }
  if (t === "org" || t === "organization" || t === "landmark") {
    return <Landmark className="h-3.5 w-3.5 shrink-0" style={{ color: "var(--color-text-3)" }} />;
  }
  return <Building2 className="h-3.5 w-3.5 shrink-0" style={{ color: "var(--color-text-3)" }} />;
}

function ConfidenceBar({ pct }: { pct: number }) {
  return (
    <div className="flex items-center gap-2">
      <div
        className="h-1 flex-1 rounded-full"
        style={{ background: "var(--color-surface-3)" }}
      >
        <div
          className="h-1 rounded-full transition-all"
          style={{ width: `${pct}%`, background: "var(--color-amber)", opacity: 0.75 }}
        />
      </div>
      <span className="text-mono-xs shrink-0" style={{ color: "var(--color-text-3)" }}>
        {pct}%
      </span>
    </div>
  );
}

/* ── Tabs ───────────────────────────────────────────────────────── */

type TabId = "signals" | "entities" | "legal" | "related";

const TABS: { id: TabId; label: string }[] = [
  { id: "signals",  label: "Sinais" },
  { id: "entities", label: "Entidades" },
  { id: "legal",    label: "Hipóteses Legais" },
  { id: "related",  label: "Casos Relacionados" },
];

/* ── Page ───────────────────────────────────────────────────────── */

export default function CaseDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [caseData, setCaseData]       = useState<CaseDetail | null>(null);
  const [hypotheses, setHypotheses]   = useState<LegalHypothesis[]>([]);
  const [relatedCases, setRelatedCases] = useState<RelatedCase[]>([]);
  const [error, setError]             = useState<string | null>(null);
  const [activeTab, setActiveTab]     = useState<TabId>("signals");

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    async function load() {
      try {
        const c = await getCase(id);
        if (cancelled) return;
        setCaseData(c);

        const [h, rc] = await Promise.all([
          fetchCaseLegalHypotheses(id),
          fetchRelatedCases(id).catch((): RelatedCase[] => []),
        ]);
        if (cancelled) return;
        setHypotheses(h);
        setRelatedCases(rc);
      } catch (err) {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : "";
        setError(msg.includes("404") ? "not_found" : msg);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [id]);

  /* ── Error / Loading ──────────────────────────────────────────── */

  if (error === "not_found") {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
        <EmptyState
          title="Caso não encontrado"
          description="O caso solicitado não existe ou foi removido."
        />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
        <div className="ow-alert ow-alert-error flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          <span className="text-body">{error}</span>
        </div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <DetailSkeleton />
      </div>
    );
  }

  /* ── Derived data ─────────────────────────────────────────────── */

  const shortId      = caseData.id.slice(0, 8).toUpperCase();
  const entityNames  = caseData.entity_names ?? [];
  const entityList   = caseData.entities ?? [];
  const sortedSignals = sortBySeverity(caseData.signals);
  const entityCount  = entityList.length || entityNames.length;

  const periodLabel =
    caseData.period_start || caseData.period_end
      ? `${caseData.period_start ? formatDate(caseData.period_start) : "—"} → ${caseData.period_end ? formatDate(caseData.period_end) : "—"}`
      : null;

  const tabCounts: Record<TabId, number> = {
    signals:  sortedSignals.length,
    entities: entityCount,
    legal:    hypotheses.length,
    related:  relatedCases.length,
  };

  const groupingRationale = (caseData.attrs as Record<string, unknown> | undefined)
    ?.grouping_rationale as string | null | undefined;

  /* ── Render ───────────────────────────────────────────────────── */

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 animate-fade-in">

      <PageHeader
        breadcrumbs={[
          { label: "Radar", href: "/radar" },
          { label: "Casos", href: "/radar" },
          { label: `#${shortId}` },
        ]}
        eyebrow={caseData.case_type ? `Caso · ${caseData.case_type}` : "Caso investigativo"}
        title={caseData.title}
        description={
          caseData.summary ??
          (periodLabel
            ? `Período de análise: ${periodLabel}`
            : "Agrupamento investigativo de sinais com contexto, hipóteses e entidades relacionadas.")
        }
        variant="hero"
        icon={<Scale className="h-5 w-5" />}
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            <SeverityBadge severity={caseData.severity} />
            {caseData.case_type && (
              <span className="ow-badge ow-badge-info">{caseData.case_type}</span>
            )}
            <span className="ow-badge ow-badge-neutral text-mono-xs">{caseData.status}</span>
          </div>
        }
        stats={[
          { label: "Sinais", value: caseData.signals.length, mono: true },
          { label: "Entidades", value: entityCount, mono: true },
          ...(periodLabel ? [{ label: "Período", value: periodLabel, mono: true }] : []),
          ...(caseData.total_value_brl != null && caseData.total_value_brl > 0
            ? [{ label: "Valor total", value: formatBRL(caseData.total_value_brl), tone: "warning" as const }]
            : []),
          { label: "ID do caso", value: shortId, mono: true },
        ]}
      />

      {/* Action buttons */}
      <div className="flex flex-wrap gap-2 mb-8">
        <Link
          href={`/investigation/${caseData.id}`}
          className="ow-btn ow-btn-primary ow-btn-md flex items-center gap-2"
        >
          <Network className="h-4 w-4" />
          Investigar no Grafo
        </Link>
        <Link
          href={`/case/${caseData.id}/dossier`}
          className="ow-btn ow-btn-secondary ow-btn-md flex items-center gap-2"
        >
          <FileText className="h-4 w-4" />
          Gerar Dossiê
        </Link>
        <Link
          href="/radar"
          className="ow-btn ow-btn-ghost ow-btn-sm flex items-center gap-2"
        >
          <Radar className="h-3.5 w-3.5" />
          Ver no Radar
        </Link>
      </div>

      {/* Grouping rationale alert */}
      {groupingRationale && (
        <div className="ow-alert ow-alert-info flex items-start gap-2 mb-8">
          <Activity className="h-4 w-4 shrink-0 mt-0.5" />
          <span className="text-caption">{groupingRationale}</span>
        </div>
      )}

      {/* ── Tabs ──────────────────────────────────────────────────── */}
      <div
        className="flex gap-0 border-b mb-6"
        style={{ borderColor: "var(--color-border)" }}
        role="tablist"
      >
        {TABS.map((tab) => {
          const count = tabCounts[tab.id];
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                "px-4 py-2.5 text-sm font-medium transition-colors relative border-b-2 -mb-px",
                isActive
                  ? "border-[var(--color-amber)] text-[var(--color-text)]"
                  : "border-transparent text-[var(--color-text-3)] hover:text-[var(--color-text-2)]",
              )}
            >
              {tab.label}
              {count > 0 && (
                <span
                  className={clsx(
                    "ml-2 text-mono-xs rounded px-1.5 py-0.5",
                    isActive
                      ? "text-[var(--color-amber)]"
                      : "text-[var(--color-text-3)]",
                  )}
                  style={{
                    background: isActive
                      ? "color-mix(in srgb, var(--color-amber) 12%, transparent)"
                      : "var(--color-surface-3)",
                  }}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ── Signals Tab ─────────────────────────────────────────── */}
      {activeTab === "signals" && (
        <div className="space-y-2 animate-fade-in" role="tabpanel">
          {sortedSignals.length === 0 ? (
            <EmptyState
              title="Nenhum sinal"
              description="Este caso não possui sinais associados."
            />
          ) : (
            sortedSignals.map((signal) => {
              const pct = Math.round(signal.confidence * 100);
              return (
                <Link key={signal.id} href={`/signal/${signal.id}`} className="block">
                  <div className={SIGNAL_CARD_CLASS[signal.severity]}>
                    <div className="flex items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <span
                            className="text-mono-sm font-bold shrink-0"
                            style={{ color: "var(--color-amber)" }}
                          >
                            {signal.typology_code}
                          </span>
                          <SeverityBadge severity={signal.severity} />
                          <span
                            className="text-caption truncate"
                            style={{ color: "var(--color-text-2)" }}
                          >
                            {TYPOLOGY_LABELS[signal.typology_code] ?? signal.typology_name}
                          </span>
                        </div>

                        {signal.title && (
                          <p
                            className="text-body font-medium truncate mb-1"
                            style={{ color: "var(--color-text)" }}
                          >
                            {signal.title}
                          </p>
                        )}

                        {signal.summary && (
                          <p
                            className="text-caption line-clamp-2 mb-2"
                            style={{ color: "var(--color-text-2)" }}
                          >
                            {signal.summary}
                          </p>
                        )}

                        <div className="flex items-center gap-4">
                          <ConfidenceBar pct={pct} />
                          {signal.evidence_count != null && signal.evidence_count > 0 && (
                            <span
                              className="text-mono-xs shrink-0"
                              style={{ color: "var(--color-text-3)" }}
                            >
                              {signal.evidence_count} evidências
                            </span>
                          )}
                          {signal.entity_count != null && signal.entity_count > 0 && (
                            <span
                              className="text-mono-xs shrink-0"
                              style={{ color: "var(--color-text-3)" }}
                            >
                              {signal.entity_count} entidades
                            </span>
                          )}
                        </div>
                      </div>

                      <ExternalLink
                        className="h-3.5 w-3.5 shrink-0 mt-0.5"
                        style={{ color: "var(--color-text-3)" }}
                      />
                    </div>
                  </div>
                </Link>
              );
            })
          )}
        </div>
      )}

      {/* ── Entities Tab ──────────────────────────────────────────── */}
      {activeTab === "entities" && (
        <div className="animate-fade-in" role="tabpanel">
          {entityList.length === 0 && entityNames.length === 0 ? (
            <EmptyState
              title="Nenhuma entidade"
              description="Não há entidades associadas a este caso."
            />
          ) : (
            <div className="ow-card">
              <ul>
                {entityList.length > 0
                  ? entityList.map((entity, i) => (
                      <li
                        key={entity.id}
                        className={clsx(
                          "flex items-center gap-3 px-4 py-3",
                          i < entityList.length - 1 &&
                            "border-b border-[var(--color-border)]",
                        )}
                      >
                        <EntityTypeIcon type={entity.type} />

                        <Link
                          href={`/entity/${entity.id}`}
                          className="flex-1 text-body truncate transition-colors hover:text-[var(--color-text)]"
                          style={{ color: "var(--color-text-2)" }}
                          title={entity.name}
                        >
                          {entity.name}
                        </Link>

                        {entity.cnpj_masked && (
                          <span className="ow-id text-mono-xs shrink-0 hidden sm:inline">
                            {entity.cnpj_masked}
                          </span>
                        )}

                        {entity.roles.length > 0 && (
                          <span className="ow-badge ow-badge-neutral shrink-0 hidden md:inline-flex">
                            {entity.roles[0]}
                          </span>
                        )}

                        {entity.signal_ids.length > 0 && (
                          <span
                            className="text-mono-xs shrink-0"
                            style={{ color: "var(--color-text-3)" }}
                          >
                            {entity.signal_ids.length}{" "}
                            {entity.signal_ids.length !== 1 ? "sinais" : "sinal"}
                          </span>
                        )}
                      </li>
                    ))
                  : entityNames.map((name, i) => (
                      <li
                        key={i}
                        className={clsx(
                          "flex items-center gap-3 px-4 py-3",
                          i < entityNames.length - 1 &&
                            "border-b border-[var(--color-border)]",
                        )}
                      >
                        <EntityTypeIcon type="company" />
                        <span
                          className="flex-1 text-body truncate"
                          style={{ color: "var(--color-text-2)" }}
                          title={name}
                        >
                          {name}
                        </span>
                      </li>
                    ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* ── Legal Tab ─────────────────────────────────────────────── */}
      {activeTab === "legal" && (
        <div className="space-y-3 animate-fade-in" role="tabpanel">
          {hypotheses.length === 0 ? (
            <EmptyState
              title="Sem hipóteses legais"
              description="Nenhuma hipótese legal foi identificada para este caso."
            />
          ) : (
            hypotheses.map((h) => {
              const pct = Math.round(h.confidence * 100);
              return (
                <div key={h.id} className="ow-card ow-card-section">
                  <div className="flex items-start gap-4">
                    <div
                      className="flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-lg"
                      style={{
                        background: "var(--color-surface-3)",
                        color: "var(--color-amber)",
                      }}
                    >
                      <Scale className="h-4 w-4" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span
                          className="text-body font-semibold"
                          style={{ color: "var(--color-text)" }}
                        >
                          {h.law_name}
                        </span>
                        {h.article && (
                          <span className="ow-badge ow-badge-info text-mono-xs">
                            Art. {h.article}
                          </span>
                        )}
                      </div>

                      {h.violation_type && (
                        <p
                          className="text-caption mb-3"
                          style={{ color: "var(--color-text-2)" }}
                        >
                          {h.violation_type}
                        </p>
                      )}

                      <div className="flex items-center gap-4">
                        <ConfidenceBar pct={pct} />
                        {h.signal_cluster.length > 0 && (
                          <span
                            className="text-mono-xs shrink-0"
                            style={{ color: "var(--color-text-3)" }}
                          >
                            {h.signal_cluster.length}{" "}
                            {h.signal_cluster.length !== 1 ? "sinais" : "sinal"} correlacionados
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* ── Related Tab ───────────────────────────────────────────── */}
      {activeTab === "related" && (
        <div className="animate-fade-in" role="tabpanel">
          {relatedCases.length === 0 ? (
            <EmptyState
              title="Nenhum caso relacionado"
              description="Não foram encontrados casos relacionados a este."
            />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {relatedCases.map((rc) => (
                <Link key={rc.id} href={`/case/${rc.id}`} className="block">
                  <div className="ow-card ow-card-hover p-4 flex flex-col gap-3 h-full">
                    <div className="flex items-center gap-2 flex-wrap">
                      <SeverityBadge severity={rc.severity} />
                      {rc.case_type && (
                        <span className="ow-badge ow-badge-info">{rc.case_type}</span>
                      )}
                      <span className="ow-id text-mono-xs ml-auto">
                        {rc.id.slice(0, 8).toUpperCase()}
                      </span>
                    </div>

                    <p
                      className="text-body font-medium line-clamp-2 flex-1"
                      style={{ color: "var(--color-text)" }}
                    >
                      {rc.title}
                    </p>

                    <div
                      className="flex items-center gap-3 text-mono-xs pt-1 border-t"
                      style={{
                        borderColor: "var(--color-border)",
                        color: "var(--color-text-3)",
                      }}
                    >
                      {rc.signal_count != null && rc.signal_count > 0 && (
                        <span>{rc.signal_count} sinais</span>
                      )}
                      <span className="ml-auto">{formatDate(rc.created_at)}</span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
