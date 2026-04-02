"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getSignal, fetchTypologyLegalBasis, fetchRelatedSignals } from "@/lib/api";
import type { TypologyLegalBasis, RelatedSignal } from "@/lib/types";
import { Markdown } from "@/components/Markdown";
import { SeverityBadge } from "@/components/Badge";
import { SignalEvidenceSection } from "@/components/SignalEvidenceSection";
import { DetailSkeleton } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { formatBRL, formatDate, normalizeUnknownDisplay, cn } from "@/lib/utils";
import { TYPOLOGY_LABELS } from "@/lib/constants";
import type { SignalDetail, FactorMeta, SignalSeverity } from "@/lib/types";
import {
  Building2,
  User,
  Landmark,
  Network,
  Briefcase,
  ExternalLink,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Scale,
  Layers,
  ChevronRight,
  AlertTriangle,
  FileText,
  GitBranch,
  Share2,
} from "lucide-react";

// ── Helpers ─────────────────────────────────────────────────────────────────

const ENTITY_TYPE_ICONS: Record<string, typeof Building2> = {
  company: Building2,
  person: User,
  org: Landmark,
};

function maskIdentifier(key: string, value: string): string {
  if (key === "cpf" && value.length >= 6) {
    return value.slice(0, 3) + ".***.***-**";
  }
  if (key === "cnpj" && value.length >= 8) {
    return value.slice(0, 2) + ".***.***/" + value.slice(-6);
  }
  return value;
}

function sanitizeText(value: string): string {
  return value
    .replace(/\bunknown\b/gi, "Nao informado pela fonte")
    .replace(/sem classificacao/gi, "Nao informado pela fonte")
    .replace(/sem classificação/gi, "Nao informado pela fonte");
}

function toNumberOrNull(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const normalized = value.replace(/\./g, "").replace(",", ".").trim();
    const parsed = Number(normalized);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function formatFactorValue(value: unknown, meta?: FactorMeta): string {
  if (value === null || value === undefined) return "—";
  if (meta?.unit === "boolean" || typeof value === "boolean") return "";
  if (meta?.unit === "brl" && typeof value === "number") return formatBRL(value);
  if (meta?.unit === "percent" && typeof value === "number") {
    const pct = value > 1 ? value : value * 100;
    return `${pct.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
  }
  if (meta?.unit === "days" && typeof value === "number") {
    return `${Math.round(value)} dias`;
  }
  if (typeof value === "number") {
    return value.toLocaleString("pt-BR", { maximumFractionDigits: 4 });
  }
  return normalizeUnknownDisplay(value);
}

// ── ScoreBar ─────────────────────────────────────────────────────────────────

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const barColor =
    pct >= 75
      ? "var(--color-low)"
      : pct >= 50
      ? "var(--color-medium)"
      : "var(--color-critical)";
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-caption" style={{ color: "var(--color-text-2)" }}>
          {label}
        </span>
        <span
          className="text-mono-sm font-semibold tabular-nums"
          style={{ color: "var(--color-text)" }}
        >
          {pct}%
        </span>
      </div>
      <div
        className="h-1 w-full rounded-full overflow-hidden"
        style={{ background: "var(--color-surface-3)" }}
      >
        <div
          className="h-1 rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: barColor }}
        />
      </div>
    </div>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────────────

type TabId = "resumo" | "evidencias" | "legal" | "relacionados";

const TABS: { id: TabId; label: string; Icon: typeof FileText }[] = [
  { id: "resumo", label: "Resumo", Icon: FileText },
  { id: "evidencias", label: "Evidências", Icon: Layers },
  { id: "legal", label: "Base Legal", Icon: Scale },
  { id: "relacionados", label: "Relacionados", Icon: GitBranch },
];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SignalDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [signal, setSignal] = useState<SignalDetail | null>(null);
  const [legalBasis, setLegalBasis] = useState<TypologyLegalBasis | null>(null);
  const [relatedSignals, setRelatedSignals] = useState<RelatedSignal[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("resumo");

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    async function load() {
      try {
        const s = await getSignal(id);
        if (cancelled) return;
        setSignal(s);

        const [lb, rs] = await Promise.all([
          fetchTypologyLegalBasis(s.typology_code).catch(() => null),
          fetchRelatedSignals(id).catch((): RelatedSignal[] => []),
        ]);
        if (cancelled) return;
        setLegalBasis(lb);
        setRelatedSignals(rs);
      } catch {
        if (!cancelled) setError("not_found");
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error === "not_found") {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 animate-fade-in">
        <EmptyState
          title="Sinal nao encontrado"
          description="O sinal solicitado nao existe ou foi removido."
        />
      </div>
    );
  }

  if (!signal) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
        <DetailSkeleton />
      </div>
    );
  }

  const shortId = id.slice(0, 8);
  const confidence = signal.confidence;
  const completeness = signal.completeness_score;
  const factorDescriptions = signal.factor_descriptions ?? {};
  const entities = signal.entities ?? [];

  const fallbackInvestigation = {
    what_crossed:
      signal.typology_code === "T03"
        ? ["orgao_comprador", "modalidade_dispensa", "grupo_catmat", "janela_temporal"]
        : ["entidades", "eventos", "fatores_quantitativos"],
    period_start: signal.period_start ?? null,
    period_end: signal.period_end ?? null,
    observed_total_brl: toNumberOrNull(
      signal.factors?.total_value_brl ?? signal.factors?.value_brl
    ),
    legal_threshold_brl: toNumberOrNull(
      signal.factors?.threshold_brl ?? signal.factors?.limit_brl
    ),
    ratio_over_threshold: toNumberOrNull(signal.factors?.ratio),
    legal_reference:
      signal.typology_code === "T03"
        ? "Lei 14.133/2021"
        : (legalBasis?.law_articles[0]?.law_name ?? null),
  };

  const investigation = signal.investigation_summary ?? fallbackInvestigation;

  const WHAT_CROSSED_LABELS: Record<string, string> = {
    orgao_comprador: "Órgão comprador",
    modalidade_dispensa: "Modalidade de compra direta (dispensa)",
    grupo_catmat: "Classificacao do item (CATMAT/CATSER)",
    janela_temporal: "Janela temporal das compras",
    entidades: "Entidades envolvidas",
    eventos: "Eventos publicos vinculados",
    fatores_quantitativos: "Indicadores quantitativos da tipologia",
  };

  const severityAccent: Record<SignalSeverity, string> = {
    critical: "var(--color-critical)",
    high: "var(--color-high)",
    medium: "var(--color-medium)",
    low: "var(--color-low)",
  };

  return (
    <div
      className="min-h-screen animate-fade-in"
      style={{ background: "var(--color-surface)" }}
    >
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 space-y-5">

        {/* Breadcrumb */}
        <nav
          className="flex items-center gap-1.5 text-caption"
          style={{ color: "var(--color-text-3)" }}
        >
          <Link
            href="/radar"
            className="transition-colors hover:text-white"
          >
            Radar
          </Link>
          <ChevronRight className="h-3.5 w-3.5 opacity-40" />
          <span
            className="text-mono-sm font-bold"
            style={{ color: "var(--color-amber)" }}
          >
            #{shortId.toUpperCase()}
          </span>
        </nav>

        {/* Page header card */}
        <div
          className="ow-card animate-slide-up overflow-hidden"
          style={{ border: "1px solid var(--color-border)" }}
        >
          {/* Severity accent line */}
          <div
            className="h-px w-full"
            style={{
              background: `linear-gradient(90deg, ${severityAccent[signal.severity as SignalSeverity] ?? "var(--color-border)"} 0%, transparent 60%)`,
            }}
          />

          <div className="p-5 space-y-4">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              {/* Title block */}
              <div className="space-y-2.5 flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className="text-mono-sm font-bold px-2 py-0.5 rounded"
                    style={{
                      background: "var(--color-surface-3)",
                      border: "1px solid var(--color-border-strong)",
                      color: "var(--color-amber)",
                    }}
                  >
                    {signal.typology_code}
                  </span>
                  <SeverityBadge severity={signal.severity as SignalSeverity} />
                  {signal.completeness_status === "insufficient" && (
                    <span className="ow-badge ow-badge-neutral flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      Evidência parcial
                    </span>
                  )}
                </div>
                <h1
                  className="text-display-md leading-tight"
                  style={{ color: "var(--color-text)" }}
                >
                  {sanitizeText(signal.title)}
                </h1>
                <p className="text-caption" style={{ color: "var(--color-text-3)" }}>
                  {TYPOLOGY_LABELS[signal.typology_code] ?? signal.typology_name}
                </p>
              </div>

              {/* Action buttons */}
              <div className="flex flex-row sm:flex-col gap-2 sm:items-end shrink-0">
                {signal.case_id && (
                  <Link
                    href={`/case/${signal.case_id}`}
                    className="ow-btn ow-btn-primary ow-btn-md flex items-center gap-1.5"
                  >
                    <Briefcase className="h-3.5 w-3.5" />
                    <span className="truncate max-w-[160px]">
                      {signal.case_title ? signal.case_title : "Ver Caso"}
                    </span>
                  </Link>
                )}
                <Link
                  href={`/signal/${signal.id}/graph`}
                  className="ow-btn ow-btn-ghost ow-btn-sm flex items-center gap-1.5"
                >
                  <Network className="h-3.5 w-3.5" />
                  Grafo
                </Link>
              </div>
            </div>

            {/* Meta strip */}
            <div
              className="ow-divider"
              style={{ borderColor: "var(--color-border)" }}
            />
            <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
              <div>
                <p
                  className="text-label uppercase tracking-widest mb-1"
                  style={{ color: "var(--color-text-3)" }}
                >
                  Severidade
                </p>
                <SeverityBadge severity={signal.severity as SignalSeverity} />
              </div>
              <div>
                <p
                  className="text-label uppercase tracking-widest mb-1"
                  style={{ color: "var(--color-text-3)" }}
                >
                  ID do Sinal
                </p>
                <span className="ow-id">{shortId}…</span>
              </div>
              {signal.period_start && (
                <div>
                  <p
                    className="text-label uppercase tracking-widest mb-1"
                    style={{ color: "var(--color-text-3)" }}
                  >
                    Início
                  </p>
                  <span
                    className="text-mono-sm tabular-nums"
                    style={{ color: "var(--color-text)" }}
                  >
                    {formatDate(signal.period_start)}
                  </span>
                </div>
              )}
              {signal.period_end && (
                <div>
                  <p
                    className="text-label uppercase tracking-widest mb-1"
                    style={{ color: "var(--color-text-3)" }}
                  >
                    Fim
                  </p>
                  <span
                    className="text-mono-sm tabular-nums"
                    style={{ color: "var(--color-text)" }}
                  >
                    {formatDate(signal.period_end)}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Body: aside + tabbed main */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[288px_1fr]">

          {/* ── Aside ──────────────────────────────────────────────── */}
          <aside className="space-y-3">

            {/* Score indicators */}
            <div
              className="ow-card p-4 space-y-4"
              style={{ border: "1px solid var(--color-border)" }}
            >
              <h3
                className="text-label uppercase tracking-widest"
                style={{ color: "var(--color-text-3)" }}
              >
                Indicadores
              </h3>
              <ScoreBar label="Confiança" value={confidence} />
              <ScoreBar label="Completude" value={completeness} />
            </div>

            {/* Entities */}
            {(entities.length > 0 || signal.entity_ids.length > 0) && (
              <div
                className="ow-card p-4 space-y-3"
                style={{ border: "1px solid var(--color-border)" }}
              >
                <h3
                  className="text-label uppercase tracking-widest"
                  style={{ color: "var(--color-text-3)" }}
                >
                  Entidades
                </h3>
                <ul className="space-y-2">
                  {entities.length > 0
                    ? entities.map((entity) => {
                        const EntityIcon =
                          ENTITY_TYPE_ICONS[entity.type] ?? Building2;
                        const identifierEntries = Object.entries(
                          entity.identifiers
                        );
                        return (
                          <li key={entity.id}>
                            <Link
                              href={`/entity/${entity.id}`}
                              className="ow-card-hover flex items-center gap-2.5 rounded-md p-2.5 transition-colors"
                              style={{
                                background: "var(--color-surface-2)",
                                border: "1px solid var(--color-border)",
                              }}
                            >
                              <div
                                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full"
                                style={{
                                  background: "var(--color-surface-3)",
                                  border: "1px solid var(--color-border-strong)",
                                }}
                              >
                                <EntityIcon
                                  className="h-3.5 w-3.5"
                                  style={{ color: "var(--color-amber)" }}
                                />
                              </div>
                              <div className="min-w-0 flex-1">
                                <p
                                  className="text-body font-medium truncate"
                                  style={{ color: "var(--color-text)" }}
                                >
                                  {entity.name}
                                </p>
                                {identifierEntries.length > 0 && (
                                  <p
                                    className="text-mono-xs truncate"
                                    style={{ color: "var(--color-text-3)" }}
                                  >
                                    {identifierEntries
                                      .map(
                                        ([k, v]) =>
                                          `${k.toUpperCase()}: ${maskIdentifier(k, v)}`
                                      )
                                      .join(" · ")}
                                  </p>
                                )}
                              </div>
                              <ExternalLink
                                className="h-3 w-3 shrink-0"
                                style={{ color: "var(--color-text-3)" }}
                              />
                            </Link>
                          </li>
                        );
                      })
                    : signal.entity_ids.map((eid) => (
                        <li key={eid}>
                          <Link
                            href={`/entity/${eid}`}
                            className="ow-card-hover flex items-center gap-2 rounded-md p-2.5 transition-colors"
                            style={{
                              background: "var(--color-surface-2)",
                              border: "1px solid var(--color-border)",
                            }}
                          >
                            <span className="ow-id flex-1">
                              {eid.slice(0, 8)}…
                            </span>
                            <ExternalLink
                              className="h-3 w-3"
                              style={{ color: "var(--color-amber)" }}
                            />
                          </Link>
                        </li>
                      ))}
                </ul>
              </div>
            )}

            {/* Metadata */}
            <div
              className="ow-card p-4 space-y-3"
              style={{ border: "1px solid var(--color-border)" }}
            >
              <h3
                className="text-label uppercase tracking-widest"
                style={{ color: "var(--color-text-3)" }}
              >
                Metadados
              </h3>
              <dl className="space-y-3">
                <div>
                  <dt
                    className="text-label mb-0.5"
                    style={{ color: "var(--color-text-3)" }}
                  >
                    ID
                  </dt>
                  <dd>
                    <span className="ow-id">{shortId}…</span>
                  </dd>
                </div>
                <div>
                  <dt
                    className="text-label mb-0.5"
                    style={{ color: "var(--color-text-3)" }}
                  >
                    Tipologia
                  </dt>
                  <dd
                    className="text-mono-sm"
                    style={{ color: "var(--color-text)" }}
                  >
                    {signal.typology_code}
                  </dd>
                </div>
                {signal.created_at && (
                  <div>
                    <dt
                      className="text-label mb-0.5"
                      style={{ color: "var(--color-text-3)" }}
                    >
                      Detectado em
                    </dt>
                    <dd
                      className="text-mono-sm tabular-nums"
                      style={{ color: "var(--color-text)" }}
                    >
                      {formatDate(signal.created_at)}
                    </dd>
                  </div>
                )}
                <div>
                  <dt
                    className="text-label mb-0.5"
                    style={{ color: "var(--color-text-3)" }}
                  >
                    Status evidência
                  </dt>
                  <dd>
                    <span
                      className={cn(
                        "ow-badge",
                        signal.completeness_status === "sufficient"
                          ? "ow-badge-info"
                          : "ow-badge-neutral"
                      )}
                    >
                      {signal.completeness_status === "sufficient"
                        ? "Suficiente"
                        : "Insuficiente"}
                    </span>
                  </dd>
                </div>
              </dl>
            </div>
          </aside>

          {/* ── Main: Tabs ─────────────────────────────────────────── */}
          <div className="min-w-0">
            {/* Tab navigation */}
            <div
              className="flex items-center gap-0 rounded-t-lg border-b overflow-x-auto"
              style={{
                background: "var(--color-surface-2)",
                borderColor: "var(--color-border)",
                borderLeft: "1px solid var(--color-border)",
                borderRight: "1px solid var(--color-border)",
                borderTop: "1px solid var(--color-border)",
              }}
            >
              {TABS.map(({ id: tabId, label, Icon }) => (
                <button
                  key={tabId}
                  onClick={() => setActiveTab(tabId)}
                  className="relative flex items-center gap-1.5 px-5 py-3.5 text-label font-medium whitespace-nowrap transition-colors"
                  style={{
                    color:
                      activeTab === tabId
                        ? "var(--color-text)"
                        : "var(--color-text-3)",
                  }}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                  {activeTab === tabId && (
                    <span
                      className="absolute bottom-0 left-0 right-0 h-px rounded-t-full"
                      style={{ background: "var(--color-amber)" }}
                    />
                  )}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div
              className="rounded-b-lg p-5 space-y-5"
              style={{
                background: "var(--color-surface-2)",
                border: "1px solid var(--color-border)",
                borderTop: "none",
              }}
            >
              {/* ── Resumo ── */}
              {activeTab === "resumo" && (
                <div className="space-y-6 animate-fade-in">

                  {/* Summary / explanation */}
                  {(signal.explanation_md || signal.summary) && (
                    <section>
                      <h2
                        className="text-label uppercase tracking-widest mb-3"
                        style={{ color: "var(--color-text-3)" }}
                      >
                        Análise do Sinal
                      </h2>
                      <div
                        className="text-body rounded-md p-4"
                        style={{
                          borderLeft: "3px solid var(--color-amber)",
                          background: "var(--color-surface-3)",
                          color: "var(--color-text-2)",
                        }}
                      >
                        {signal.explanation_md ? (
                          <Markdown content={signal.explanation_md} />
                        ) : (
                          <p>{sanitizeText(signal.summary ?? "")}</p>
                        )}
                      </div>
                    </section>
                  )}

                  {/* Risk Factors */}
                  {signal.factors && Object.keys(signal.factors).length > 0 && (
                    <section>
                      <h2
                        className="text-label uppercase tracking-widest mb-3 flex items-center gap-1.5"
                        style={{ color: "var(--color-text-3)" }}
                      >
                        <Layers className="h-3.5 w-3.5" />
                        Fatores de Risco
                      </h2>
                      <div className="ow-table-wrapper">
                        <table className="ow-table">
                          <thead>
                            <tr>
                              <th>Fator</th>
                              <th>Valor</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(signal.factors).map(
                              ([key, value]) => {
                                const meta = factorDescriptions[key];
                                const isBoolean =
                                  meta?.unit === "boolean" ||
                                  typeof value === "boolean";
                                const boolVal = isBoolean
                                  ? Boolean(value)
                                  : null;
                                return (
                                  <tr key={key}>
                                    <td>
                                      <span
                                        className="flex items-center gap-1.5"
                                        style={{ color: "var(--color-text-2)" }}
                                      >
                                        {meta?.label ?? key}
                                        {meta?.description && (
                                          <span className="group relative inline-flex">
                                            <HelpCircle
                                              className="h-3 w-3"
                                              style={{
                                                color:
                                                  "var(--color-text-3)",
                                              }}
                                            />
                                            <span
                                              className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden w-56 -translate-x-1/2 rounded-md px-3 py-2 text-xs group-hover:block"
                                              style={{
                                                background:
                                                  "var(--color-surface-3)",
                                                border:
                                                  "1px solid var(--color-border-strong)",
                                                color: "var(--color-text)",
                                              }}
                                            >
                                              {meta.description}
                                            </span>
                                          </span>
                                        )}
                                      </span>
                                    </td>
                                    <td>
                                      <span
                                        className="text-mono-sm font-semibold tabular-nums"
                                        style={{ color: "var(--color-text)" }}
                                      >
                                        {isBoolean ? (
                                          <span className="inline-flex items-center gap-1">
                                            {boolVal ? (
                                              <CheckCircle2
                                                className="h-3.5 w-3.5"
                                                style={{
                                                  color: "var(--color-low)",
                                                }}
                                              />
                                            ) : (
                                              <XCircle
                                                className="h-3.5 w-3.5"
                                                style={{
                                                  color:
                                                    "var(--color-text-3)",
                                                }}
                                              />
                                            )}
                                            {boolVal ? "Sim" : "Nao"}
                                          </span>
                                        ) : (
                                          formatFactorValue(value, meta)
                                        )}
                                      </span>
                                    </td>
                                  </tr>
                                );
                              }
                            )}
                          </tbody>
                        </table>
                      </div>
                    </section>
                  )}

                  {/* Investigation summary */}
                  {investigation && (
                    <section>
                      <h2
                        className="text-label uppercase tracking-widest mb-3 flex items-center gap-1.5"
                        style={{ color: "var(--color-text-3)" }}
                      >
                        <Scale className="h-3.5 w-3.5" />
                        Por que este sinal existe?
                      </h2>
                      <div
                        className="rounded-md p-4 space-y-4"
                        style={{
                          background: "var(--color-surface-3)",
                          border: "1px solid var(--color-border)",
                        }}
                      >
                        <p
                          className="text-caption"
                          style={{ color: "var(--color-text-3)" }}
                        >
                          O motor cruzou dados públicos para identificar um
                          padrão atípico nesta tipologia.
                        </p>
                        <div className="grid grid-cols-2 gap-3">
                          {[
                            {
                              label: "Valor observado",
                              value:
                                typeof investigation.observed_total_brl ===
                                "number"
                                  ? formatBRL(investigation.observed_total_brl)
                                  : null,
                            },
                            {
                              label: "Limite de referência",
                              value:
                                typeof investigation.legal_threshold_brl ===
                                "number"
                                  ? formatBRL(investigation.legal_threshold_brl)
                                  : null,
                            },
                            {
                              label: "Razão sobre limite",
                              value:
                                typeof investigation.ratio_over_threshold ===
                                "number"
                                  ? `${investigation.ratio_over_threshold.toLocaleString(
                                      "pt-BR",
                                      { maximumFractionDigits: 2 }
                                    )}x`
                                  : null,
                            },
                            {
                              label: "Base legal",
                              value: investigation.legal_reference ?? null,
                            },
                          ].map(({ label, value }) => (
                            <div
                              key={label}
                              className="rounded-md p-3"
                              style={{
                                background: "var(--color-surface-2)",
                                border: "1px solid var(--color-border)",
                              }}
                            >
                              <p
                                className="text-label mb-1"
                                style={{ color: "var(--color-text-3)" }}
                              >
                                {label}
                              </p>
                              <p
                                className="text-mono-sm font-semibold"
                                style={{
                                  color: value
                                    ? "var(--color-text)"
                                    : "var(--color-text-3)",
                                }}
                              >
                                {value ?? "Nao informado"}
                              </p>
                            </div>
                          ))}
                        </div>
                        {investigation.what_crossed.length > 0 && (
                          <div>
                            <p
                              className="text-label mb-2"
                              style={{ color: "var(--color-text-3)" }}
                            >
                              Dados cruzados
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {investigation.what_crossed.map((item) => (
                                <span
                                  key={item}
                                  className="ow-badge ow-badge-neutral"
                                >
                                  {WHAT_CROSSED_LABELS[item] ?? item}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </section>
                  )}

                  {/* Legal disclaimer */}
                  <div className="ow-alert ow-alert-warning flex gap-2.5">
                    <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                    <p className="text-caption">
                      <strong>Aviso legal:</strong>{" "}
                      Este sinal constitui uma{" "}
                      <em>hipótese investigativa</em> baseada em cruzamento
                      automático de dados públicos. Nao equivale a acusação,
                      condenação ou juízo de culpa. A decisão final pertence
                      aos órgãos competentes (controle interno, auditoria,
                      corregedoria, Ministério Público e Judiciário).
                    </p>
                  </div>
                </div>
              )}

              {/* ── Evidências ── */}
              {activeTab === "evidencias" && (
                <div className="animate-fade-in">
                  <SignalEvidenceSection
                    signalId={signal.id}
                    evidenceRefs={signal.evidence_refs}
                    evidenceStats={signal.evidence_stats}
                  />
                </div>
              )}

              {/* ── Base Legal ── */}
              {activeTab === "legal" && (
                <div className="space-y-5 animate-fade-in">
                  {legalBasis ? (
                    <>
                      {legalBasis.description_legal && (
                        <div
                          className="text-body rounded-md p-4"
                          style={{
                            borderLeft: "3px solid var(--color-amber)",
                            background: "var(--color-surface-3)",
                            color: "var(--color-text-2)",
                          }}
                        >
                          {legalBasis.description_legal}
                        </div>
                      )}

                      {legalBasis.law_articles.length > 0 && (
                        <div>
                          <h3
                            className="text-label uppercase tracking-widest mb-3"
                            style={{ color: "var(--color-text-3)" }}
                          >
                            Artigos aplicáveis
                          </h3>
                          <div className="ow-table-wrapper">
                            <table className="ow-table">
                              <thead>
                                <tr>
                                  <th>Lei</th>
                                  <th>Artigo</th>
                                  <th>Tipo de Violação</th>
                                </tr>
                              </thead>
                              <tbody>
                                {legalBasis.law_articles.map((article, i) => (
                                  <tr key={i}>
                                    <td
                                      className="font-medium"
                                      style={{ color: "var(--color-text)" }}
                                    >
                                      {article.law_name}
                                    </td>
                                    <td
                                      className="text-mono-sm"
                                      style={{ color: "var(--color-text-2)" }}
                                    >
                                      {article.article || "—"}
                                    </td>
                                    <td
                                      style={{ color: "var(--color-text-3)" }}
                                    >
                                      {article.violation_type || "—"}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {legalBasis.corruption_types?.length > 0 && (
                        <div>
                          <p
                            className="text-label uppercase tracking-widest mb-2"
                            style={{ color: "var(--color-text-3)" }}
                          >
                            Tipos de corrupção relacionados
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {legalBasis.corruption_types.map((type) => (
                              <span key={type} className="ow-badge ow-badge-high">
                                {type}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="ow-empty">
                      <Scale className="h-8 w-8 opacity-30 mb-2" />
                      <p>
                        Nenhuma base legal disponível para esta tipologia.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* ── Relacionados ── */}
              {activeTab === "relacionados" && (
                <div className="animate-fade-in">
                  {relatedSignals.length > 0 ? (
                    <ul className="space-y-2">
                      {relatedSignals.map((s) => (
                        <li key={s.id}>
                          <Link
                            href={`/signal/${s.id}`}
                            className="ow-signal-card ow-card-hover flex items-center gap-3 rounded-md p-3 transition-colors"
                            style={{
                              background: "var(--color-surface-3)",
                              border: "1px solid var(--color-border)",
                            }}
                          >
                            <SeverityBadge severity={s.severity} />
                            <span
                              className="text-mono-sm font-bold shrink-0"
                              style={{ color: "var(--color-amber)" }}
                            >
                              {s.typology_code}
                            </span>
                            <span
                              className="flex-1 truncate text-body"
                              style={{ color: "var(--color-text-2)" }}
                            >
                              {s.title}
                            </span>
                            <span
                              className="text-mono-xs tabular-nums shrink-0"
                              style={{ color: "var(--color-text-3)" }}
                            >
                              {Math.round(s.confidence * 100)}%
                            </span>
                            <ExternalLink
                              className="h-3.5 w-3.5 shrink-0"
                              style={{ color: "var(--color-text-3)" }}
                            />
                          </Link>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="ow-empty">
                      <Share2 className="h-8 w-8 opacity-30 mb-2" />
                      <p>
                        Nenhum sinal relacionado encontrado para estas
                        entidades.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
