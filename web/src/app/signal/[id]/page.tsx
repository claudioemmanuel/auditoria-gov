import Link from "next/link";
import { notFound } from "next/navigation";
import { getSignal } from "@/lib/api";
import { Markdown } from "@/components/Markdown";
import { Badge } from "@/components/Badge"
import { SignalEvidenceSection } from "@/components/SignalEvidenceSection";
import { formatBRL, formatDate, normalizeUnknownDisplay } from "@/lib/utils";
import { TYPOLOGY_LABELS } from "@/lib/constants";
import type { SignalDetail, FactorMeta, SignalSeverity } from "@/lib/types";
import {
  ArrowLeft,
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
  try {
    signal = await getSignal(id);
  } catch {
    notFound();
    // notFound() throws — this line is unreachable but satisfies the compiler
    return null as never;
  }

  const shortId = id.slice(0, 8);
  const confidence = signal.confidence;
  const completeness = signal.completeness_score;
  const factorDescriptions = signal.factor_descriptions ?? {};
  const entities = signal.entities ?? [];

  const fallbackInvestigation =
    signal.typology_code === "T03"
      ? {
          what_crossed: [
            "orgao_comprador",
            "modalidade_dispensa",
            "grupo_catmat",
            "janela_temporal",
          ],
          period_start: signal.period_start ?? null,
          period_end: signal.period_end ?? null,
          observed_total_brl: toNumberOrNull(signal.factors?.total_value_brl),
          legal_threshold_brl: toNumberOrNull(signal.factors?.threshold_brl),
          ratio_over_threshold: toNumberOrNull(signal.factors?.ratio),
          legal_reference: "Lei 14.133/2021",
        }
      : null;

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

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">

        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 text-sm text-secondary" aria-label="Breadcrumb">
          <Link
            href="/radar"
            className="inline-flex items-center gap-1 hover:text-primary transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Radar
          </Link>
          <span className="text-muted">/</span>
          <span className="text-primary font-mono text-xs">Sinal #{shortId}</span>
        </nav>

        {/* ─── Header card (always visible) ─── */}
        <div className="mt-4 rounded-lg border border-border bg-surface-card p-4 lg:p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">

            {/* Left: typology + name + period */}
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded bg-accent-subtle px-1.5 py-0.5 font-mono text-xs font-bold text-accent">
                  {signal.typology_code}
                </span>
                <h1 className="text-base font-semibold text-primary sm:text-lg">
                  {TYPOLOGY_LABELS[signal.typology_code] ?? signal.typology_name}
                </h1>
              </div>
              <p className="mt-1.5 text-sm font-medium text-primary">
                {sanitizeText(signal.title)}
              </p>
              {(signal.period_start || signal.period_end) && (
                <p className="mt-1 font-mono tabular-nums text-xs text-secondary">
                  {signal.period_start ? formatDate(signal.period_start) : "—"}
                  {" → "}
                  {signal.period_end ? formatDate(signal.period_end) : "—"}
                </p>
              )}
            </div>

            {/* Right: severity + confidence + completeness */}
            <div className="flex shrink-0 flex-col items-start gap-2 sm:items-end">
              <Badge severity={signal.severity as SignalSeverity} dot />
              <ScorePill label="Confianca" value={confidence} />
              <ScorePill label="Completude" value={completeness} />
            </div>
          </div>
        </div>

        {/* ─── Action buttons ─── */}
        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            href={`/signal/${signal.id}/graph`}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface-card px-3 py-1.5 text-xs font-medium text-primary transition hover:bg-surface-subtle"
          >
            <Network className="h-4 w-4" />
            Ver Grafo
          </Link>
          {signal.case_id && (
            <Link
              href={`/case/${signal.case_id}`}
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface-card px-3 py-1.5 text-xs font-medium text-primary transition hover:bg-surface-subtle"
            >
              <Briefcase className="h-4 w-4" />
              Investigar Caso
              {signal.case_title && (
                <span className="text-muted">: {signal.case_title}</span>
              )}
            </Link>
          )}
        </div>

        {/* ─── Resumo (explanation_md) ─── */}
        {signal.explanation_md && (
          <section className="mt-6">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-secondary">
              Resumo
            </h2>
            <div className="mt-2">
              <Markdown content={signal.explanation_md} />
            </div>
          </section>
        )}

        {/* Fallback summary text */}
        {!signal.explanation_md && signal.summary && (
          <section className="mt-6">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-secondary">
              Resumo
            </h2>
            <p className="mt-2 text-sm text-primary">{sanitizeText(signal.summary)}</p>
          </section>
        )}

        {/* ─── Two-column: Risk Factors + Entities ─── */}
        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">

          {/* Fatores de Risco */}
          {signal.factors && Object.keys(signal.factors).length > 0 && (
            <div className="rounded-lg border border-border bg-surface-card p-4">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-primary">
                <Layers className="h-4 w-4 text-accent" />
                Fatores de Risco
              </h2>
              <dl className="mt-3 space-y-2">
                {Object.entries(signal.factors).map(([key, value]) => {
                  const meta = factorDescriptions[key];
                  const isBoolean =
                    meta?.unit === "boolean" || typeof value === "boolean";
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
                              <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
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
            </div>
          )}

          {/* Entidades Envolvidas */}
          {(entities.length > 0 || signal.entity_ids.length > 0) && (
            <div className="rounded-lg border border-border bg-surface-card p-4">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-primary">
                <Building2 className="h-4 w-4 text-accent" />
                Entidades Envolvidas
              </h2>
              <ul className="mt-3 space-y-2">
                {entities.length > 0
                  ? entities.map((entity) => {
                      const EntityIcon =
                        ENTITY_TYPE_ICONS[entity.type] ?? Building2;
                      const identifierEntries = Object.entries(
                        entity.identifiers,
                      );
                      return (
                        <li key={entity.id}>
                          <Link
                            href={`/entity/${entity.id}`}
                            className="flex items-start gap-2.5 rounded-md border border-border bg-surface-base p-2.5 transition hover:border-accent/30 hover:bg-accent-subtle/30"
                          >
                            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface-card border border-border">
                              <EntityIcon className="h-3.5 w-3.5 text-accent" />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-xs font-semibold text-primary truncate">
                                {entity.name}
                              </p>
                              {identifierEntries.length > 0 && (
                                <p className="mt-0.5 font-mono tabular-nums text-xs text-muted">
                                  {identifierEntries
                                    .map(
                                      ([k, v]) =>
                                        `${k.toUpperCase()}: ${maskIdentifier(k, v)}`,
                                    )
                                    .join(" · ")}
                                </p>
                              )}
                            </div>
                            <ExternalLink className="mt-0.5 h-3 w-3 shrink-0 text-muted" />
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
        </div>

        {/* ─── Investigation summary (contextual box) ─── */}
        {investigation && (
          <div className="mt-6 rounded-lg border border-border bg-surface-base p-4">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-primary">
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

        {/* ─── Evidence section (client component) ─── */}
        <SignalEvidenceSection
          signalId={signal.id}
          evidenceRefs={signal.evidence_refs}
          evidenceStats={signal.evidence_stats}
        />

        {/* ─── Legal disclaimer ─── */}
        <div className="mt-6 rounded-lg border border-border bg-surface-base p-3">
          <p className="text-xs text-muted">
            <strong className="text-secondary">Aviso legal:</strong>{" "}
            Este sinal constitui uma{" "}
            <em>hipótese investigativa</em> baseada em cruzamento automático de
            dados publicos. Nao equivale a acusacao, condenacao ou juizo de
            culpa. A decisao final pertence aos orgaos competentes (controle
            interno, auditoria, corregedoria, Ministerio Publico e Judiciario).
          </p>
        </div>

    </div>
  );
}
