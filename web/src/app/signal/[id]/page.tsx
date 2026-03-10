import Link from "next/link";
import { notFound } from "next/navigation";
import { getSignal, fetchTypologyLegalBasis, fetchRelatedSignals } from "@/lib/api";
import type { TypologyLegalBasis, RelatedSignal } from "@/lib/types";
import { Markdown } from "@/components/Markdown";
import { Badge } from "@/components/Badge";
import { SignalEvidenceSection } from "@/components/SignalEvidenceSection";
import { DetailPageLayout } from "@/components/DetailPageLayout";
import { DetailHeader } from "@/components/DetailHeader";
import { formatBRL, formatDate, normalizeUnknownDisplay, severityDotColor, cn } from "@/lib/utils";
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
} from "lucide-react";

// ---- Helpers ----

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

// ---- Score pill ----

function ScorePill({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-secondary">{label}:</span>
      <span className="font-mono tabular-nums text-xs font-semibold text-primary">
        {pct}%
      </span>
      <div className="h-1.5 w-16 rounded-full bg-surface-base">
        <div
          className="h-1.5 rounded-full bg-accent"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ---- Page ----

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function SignalDetailPage({ params }: PageProps) {
  const { id } = await params;

  let signal: SignalDetail;
  let legalBasis: TypologyLegalBasis | null = null;
  try {
    signal = await getSignal(id);
  } catch {
    notFound();
    return null as never;
  }
  try {
    legalBasis = await fetchTypologyLegalBasis(signal.typology_code);
  } catch {
    // legal basis not available for all typologies
  }
  let relatedSignals: RelatedSignal[] = [];
  try {
    relatedSignals = await fetchRelatedSignals(id);
  } catch {
    // ignore
  }

  const shortId = id.slice(0, 8);
  const confidence = signal.confidence;
  const completeness = signal.completeness_score;
  const factorDescriptions = signal.factor_descriptions ?? {};
  const entities = signal.entities ?? [];

  const fallbackInvestigation = {
    what_crossed: signal.typology_code === "T03"
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

  // ── Aside ──────────────────────────────────────────────────────────
  const aside = (
    <>
      {/* Typology + Severity */}
      <div className="rounded-lg border border-border bg-surface-card p-4 space-y-3">
        <div className="space-y-1.5">
          <span className="rounded bg-accent-subtle px-1.5 py-0.5 font-mono text-xs font-bold text-accent">
            {signal.typology_code}
          </span>
          <p className="text-xs font-medium text-secondary leading-snug">
            {TYPOLOGY_LABELS[signal.typology_code] ?? signal.typology_name}
          </p>
        </div>
        <div>
          <Badge severity={signal.severity as SignalSeverity} dot />
        </div>
        <div className="space-y-1.5 pt-1 border-t border-border">
          <ScorePill label="Confianca" value={confidence} />
          <ScorePill label="Completude" value={completeness} />
        </div>
        {(signal.period_start || signal.period_end) && (
          <div className="pt-1 border-t border-border">
            <p className="text-xs font-medium text-muted mb-1">Período</p>
            <p className="font-mono tabular-nums text-xs text-primary">
              {signal.period_start ? formatDate(signal.period_start) : "—"}
              {" → "}
              {signal.period_end ? formatDate(signal.period_end) : "—"}
            </p>
          </div>
        )}
      </div>

      {/* Entities */}
      {(entities.length > 0 || signal.entity_ids.length > 0) && (
        <div className="rounded-lg border border-border bg-surface-card p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted mb-2">
            Entidades
          </h3>
          <ul className="space-y-1.5">
            {entities.length > 0
              ? entities.map((entity) => {
                  const EntityIcon = ENTITY_TYPE_ICONS[entity.type] ?? Building2;
                  const identifierEntries = Object.entries(entity.identifiers);
                  return (
                    <li key={entity.id}>
                      <Link
                        href={`/entity/${entity.id}`}
                        className="flex items-center gap-2 rounded-md border border-border bg-surface-base p-2 transition hover:border-accent/30 hover:bg-accent-subtle/30"
                      >
                        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-card border border-border">
                          <EntityIcon className="h-3 w-3 text-accent" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-semibold text-primary truncate">
                            {entity.name}
                          </p>
                          {identifierEntries.length > 0 && (
                            <p className="font-mono tabular-nums text-[10px] text-muted truncate">
                              {identifierEntries
                                .map(([k, v]) => `${k.toUpperCase()}: ${maskIdentifier(k, v)}`)
                                .join(" · ")}
                            </p>
                          )}
                        </div>
                        <ExternalLink className="h-3 w-3 shrink-0 text-muted" />
                      </Link>
                    </li>
                  );
                })
              : signal.entity_ids.map((eid) => (
                  <li key={eid}>
                    <Link
                      href={`/entity/${eid}`}
                      className="flex items-center gap-1.5 rounded-md border border-border bg-surface-base px-2.5 py-1.5 font-mono text-xs text-accent transition hover:bg-accent-subtle/30"
                    >
                      {eid.slice(0, 8)}...
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  </li>
                ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="rounded-lg border border-border bg-surface-card p-4 space-y-2">
        <Link
          href={`/signal/${signal.id}/graph`}
          className="flex items-center gap-2 rounded-md border border-border bg-surface-base px-3 py-2 text-xs font-medium text-primary transition hover:bg-surface-subtle w-full"
        >
          <Network className="h-3.5 w-3.5 text-accent" />
          Ver Grafo
        </Link>
        {signal.case_id && (
          <Link
            href={`/case/${signal.case_id}`}
            className="flex items-center gap-2 rounded-md border border-accent/30 bg-accent-subtle/40 px-3 py-2 text-xs font-medium text-accent transition hover:bg-accent-subtle w-full"
          >
            <Briefcase className="h-3.5 w-3.5" />
            <span className="truncate">
              Investigar Caso{signal.case_title ? `: ${signal.case_title}` : ""}
            </span>
          </Link>
        )}
      </div>

      {/* Metadata */}
      <div className="rounded-lg border border-border bg-surface-card p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted mb-2">
          Metadados
        </h3>
        <dl className="space-y-1.5">
          <div>
            <dt className="text-[10px] font-medium uppercase tracking-wide text-muted">ID</dt>
            <dd className="font-mono text-xs text-primary">{shortId}…</dd>
          </div>
        </dl>
      </div>
    </>
  );

  // ── Main ───────────────────────────────────────────────────────────
  const main = (
    <>
      {/* Summary */}
      {signal.explanation_md ? (
        <section>
          <h2 className="font-display text-sm font-semibold uppercase tracking-wide text-secondary mb-2">
            Resumo
          </h2>
          <Markdown content={signal.explanation_md} />
        </section>
      ) : signal.summary ? (
        <section>
          <h2 className="font-display text-sm font-semibold uppercase tracking-wide text-secondary mb-2">
            Resumo
          </h2>
          <p className="text-sm text-primary">{sanitizeText(signal.summary)}</p>
        </section>
      ) : null}

      {/* Risk Factors */}
      {signal.factors && Object.keys(signal.factors).length > 0 && (
        <section className="rounded-lg border border-border bg-surface-card p-4">
          <h2 className="font-display flex items-center gap-2 text-sm font-semibold text-primary mb-3">
            <Layers className="h-4 w-4 text-accent" />
            Fatores de Risco
          </h2>
          <dl className="space-y-2">
            {Object.entries(signal.factors).map(([key, value]) => {
              const meta = factorDescriptions[key];
              const isBoolean = meta?.unit === "boolean" || typeof value === "boolean";
              const boolVal = isBoolean ? Boolean(value) : null;
              return (
                <div
                  key={key}
                  className="flex items-start justify-between gap-2 rounded-md bg-surface-base px-3 py-2"
                >
                  <dt className="flex items-center gap-1 text-xs text-secondary">
                    {meta?.label ?? key}
                    {meta?.description && (
                      <span className="group relative">
                        <HelpCircle className="h-3 w-3 text-muted" />
                        <span className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 hidden w-52 -translate-x-1/2 rounded-lg bg-surface-card border border-border px-3 py-2 text-xs text-primary group-hover:block">
                          {meta.description}
                        </span>
                      </span>
                    )}
                  </dt>
                  <dd className="font-mono tabular-nums text-xs font-semibold text-primary">
                    {isBoolean ? (
                      <span className="inline-flex items-center gap-1">
                        {boolVal ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                        ) : (
                          <XCircle className="h-3.5 w-3.5 text-muted" />
                        )}
                        {boolVal ? "Sim" : "Nao"}
                      </span>
                    ) : (
                      formatFactorValue(value, meta)
                    )}
                  </dd>
                </div>
              );
            })}
          </dl>
        </section>
      )}

      {/* Investigation summary */}
      {investigation && (
        <div className="rounded-lg border border-border bg-surface-base p-4">
          <h2 className="font-display flex items-center gap-2 text-sm font-semibold text-primary">
            <Scale className="h-4 w-4 text-accent" />
            Por que este sinal existe?
          </h2>
          <p className="mt-2 text-xs text-secondary">
            O motor cruzou dados públicos para identificar um padrão atípico nesta tipologia.
          </p>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <div className="rounded-md bg-surface-card border border-border px-3 py-2">
              <p className="text-xs font-semibold text-secondary">Valor observado</p>
              <p className="mt-0.5 font-mono tabular-nums text-xs font-semibold text-primary">
                {typeof investigation.observed_total_brl === "number"
                  ? formatBRL(investigation.observed_total_brl)
                  : "Nao informado"}
              </p>
            </div>
            <div className="rounded-md bg-surface-card border border-border px-3 py-2">
              <p className="text-xs font-semibold text-secondary">Limite de referencia</p>
              <p className="mt-0.5 font-mono tabular-nums text-xs font-semibold text-primary">
                {typeof investigation.legal_threshold_brl === "number"
                  ? formatBRL(investigation.legal_threshold_brl)
                  : "Nao informado"}
              </p>
            </div>
            <div className="rounded-md bg-surface-card border border-border px-3 py-2">
              <p className="text-xs font-semibold text-secondary">Razao sobre limite</p>
              <p className="mt-0.5 font-mono tabular-nums text-xs font-semibold text-primary">
                {typeof investigation.ratio_over_threshold === "number"
                  ? `${investigation.ratio_over_threshold.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}x`
                  : "Nao informado"}
              </p>
            </div>
            <div className="rounded-md bg-surface-card border border-border px-3 py-2">
              <p className="text-xs font-semibold text-secondary">Base legal</p>
              <p className="mt-0.5 text-xs text-primary">
                {investigation.legal_reference ?? "Nao informado"}
              </p>
            </div>
          </div>
          {investigation.what_crossed.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-semibold text-secondary">Dados cruzados</p>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {investigation.what_crossed.map((item) => (
                  <span
                    key={item}
                    className="rounded-full bg-surface-card border border-border px-2 py-0.5 text-xs text-secondary"
                  >
                    {WHAT_CROSSED_LABELS[item] ?? item}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Base Legal */}
      {legalBasis && legalBasis.law_articles.length > 0 && (
        <section className="rounded-lg border border-border bg-surface-card p-4">
          <h2 className="font-display flex items-center gap-2 text-sm font-semibold text-primary mb-3">
            <Scale className="h-4 w-4 text-accent" />
            Base Legal
          </h2>
          {legalBasis.description_legal && (
            <p className="text-xs text-secondary mb-3">{legalBasis.description_legal}</p>
          )}
          <ul className="space-y-2">
            {legalBasis.law_articles.map((article, i) => (
              <li key={i} className="rounded-md bg-surface-base px-3 py-2">
                <p className="text-xs font-semibold text-primary">{article.law_name}</p>
                {article.article && (
                  <p className="text-[11px] text-secondary mt-0.5">{article.article}</p>
                )}
                {article.violation_type && (
                  <p className="text-[11px] text-muted mt-0.5">{article.violation_type}</p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Related Signals */}
      {relatedSignals.length > 0 && (
        <section className="rounded-lg border border-border bg-surface-card p-4">
          <h2 className="font-display text-sm font-semibold text-primary mb-3">
            Outros Sinais com as Mesmas Entidades
          </h2>
          <ul className="space-y-1.5">
            {relatedSignals.map((s) => (
              <li key={s.id}>
                <Link
                  href={`/signal/${s.id}`}
                  className="flex items-center gap-2 rounded-md border border-border bg-surface-base px-3 py-2 text-xs transition hover:bg-surface-subtle"
                >
                  <span className={cn("h-2 w-2 shrink-0 rounded-full", severityDotColor(s.severity))} />
                  <span className="font-mono tabular-nums font-bold text-accent shrink-0">{s.typology_code}</span>
                  <span className="flex-1 truncate text-secondary">{s.title}</span>
                  <ExternalLink className="h-3 w-3 shrink-0 text-muted" />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Evidence */}
      <SignalEvidenceSection
        signalId={signal.id}
        evidenceRefs={signal.evidence_refs}
        evidenceStats={signal.evidence_stats}
      />

      {/* Legal disclaimer */}
      <div className="rounded-lg border border-border bg-surface-base p-3">
        <p className="text-xs text-muted">
          <strong className="text-secondary">Aviso legal:</strong>{" "}
          Este sinal constitui uma{" "}
          <em>hipótese investigativa</em> baseada em cruzamento automático de
          dados publicos. Nao equivale a acusacao, condenacao ou juizo de
          culpa. A decisao final pertence aos orgaos competentes (controle
          interno, auditoria, corregedoria, Ministerio Publico e Judiciario).
        </p>
      </div>
    </>
  );

  return (
    <DetailPageLayout
      header={
        <DetailHeader
          breadcrumbs={[{ label: "Radar", href: "/radar" }, { label: `Sinal #${shortId}` }]}
          title={sanitizeText(signal.title)}
          badge={<Badge severity={signal.severity as SignalSeverity} dot />}
        />
      }
      aside={aside}
      main={main}
    />
  );
}
