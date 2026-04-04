import Link from "next/link";
import { notFound } from "next/navigation";
import { getCase, fetchCaseLegalHypotheses, getCaseProvenance } from "@/lib/api";
import { Badge } from "@/components/Badge";
import { CaseTypeBadge } from "@/components/CaseTypeBadge";
import { formatBRL, formatDate, severityDotColor, cn } from "@/lib/utils";
import { TYPOLOGY_LABELS } from "@/lib/constants";
import type { SignalSeverity, CaseDetail, CaseEntityBrief, LegalHypothesis, CaseProvenanceWeb } from "@/lib/types";
import {
  ArrowLeft,
  Printer,
  AlertTriangle,
  Scale,
  BookOpen,
  Link2,
  Building2,
  FileText,
  ShieldAlert,
  User,
  Landmark,
  ExternalLink,
  Users,
} from "lucide-react";

const SEVERITY_ORDER: Record<SignalSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const SEVERITY_LABEL: Record<SignalSeverity, string> = {
  critical: "Crítico",
  high: "Alto",
  medium: "Médio",
  low: "Baixo",
};

const VIOLATION_TYPE_LABELS: Record<string, string> = {
  fraude_licitatoria: "Fraude Licitatória",
  corrupcao_ativa: "Corrupção Ativa",
  corrupcao_passiva: "Corrupção Passiva",
  corrupcao_ativa_passiva: "Corrupção Ativa/Passiva",
  nepotismo_clientelismo: "Nepotismo / Clientelismo",
  peculato: "Peculato",
  lavagem: "Lavagem de Dinheiro",
};

const ROLE_LABELS: Record<string, string> = {
  buyer: "Comprador",
  supplier: "Fornecedor",
  winner: "Vencedor",
  procuring_entity: "Órgão Contratante",
  bidder: "Licitante",
};

function EntityTypeIcon({ type }: { type: string }) {
  const t = type.toLowerCase();
  if (t === "person" || t === "individual" || t === "cpf") {
    return <User className="h-3.5 w-3.5 shrink-0 text-muted" />;
  }
  if (t === "org" || t === "organization") {
    return <Landmark className="h-3.5 w-3.5 shrink-0 text-muted" />;
  }
  return <Building2 className="h-3.5 w-3.5 shrink-0 text-muted" />;
}

function DossierSection({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2 border-b border-border pb-2">
        <Icon className="h-4 w-4 text-accent" />
        <h2 className="font-display text-sm font-semibold uppercase tracking-wide text-primary">
          {title}
        </h2>
      </div>
      {children}
    </section>
  );
}

export default async function DossierPage({ id }: { id: string }) {

  let caseData: CaseDetail;
  try {
    caseData = await getCase(id);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "";
    if (msg.includes("404")) notFound();
    throw err;
  }

  const [hypotheses, provenance] = await Promise.all([
    fetchCaseLegalHypotheses(id).catch((): LegalHypothesis[] => []),
    getCaseProvenance(id).catch(
      (): CaseProvenanceWeb => ({
        case_id: id,
        case_title: caseData.title,
        signals: [],
        event_raw_sources: {},
      }),
    ),
  ]);

  const shortId = caseData.id.slice(0, 8).toUpperCase();
  const entityNames = caseData.entity_names ?? [];
  const sortedSignals = [...caseData.signals].sort(
    (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity],
  );

  const periodLabel =
    caseData.period_start || caseData.period_end
      ? `${caseData.period_start ? formatDate(caseData.period_start) : "—"} → ${caseData.period_end ? formatDate(caseData.period_end) : "—"}`
      : null;

  // Count unique sources from provenance
  const allSources = Object.values(provenance.event_raw_sources).flat();
  const uniqueConnectors = [...new Set(allSources.map((s) => s.connector))];

  return (
    <div className="ledger-page mx-auto max-w-3xl px-4 py-8 sm:px-6 print:px-0 print:py-4">
      {/* Toolbar — hidden when printing */}
      <div className="mb-6 flex items-center justify-between print:hidden">
        <Link
          href={`/case/${id}`}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-card px-3 py-1.5 text-xs font-medium text-secondary shadow-sm transition hover:bg-surface-subtle"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Voltar ao Caso
        </Link>
        <button
          onClick={undefined}
          type="button"
          className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-white shadow-sm transition hover:opacity-90 print:hidden"
          // Uses browser print via inline script below
          id="print-btn"
        >
          <Printer className="h-3.5 w-3.5" />
          Imprimir / Exportar PDF
        </button>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              document.getElementById('print-btn')?.addEventListener('click', () => window.print());
            `,
          }}
        />
      </div>

      {/* ── COVER ─────────────────────────────────────────────── */}
      <div className="ledger-row relative mb-8 border border-border bg-surface-card p-6 print:border-0 print:shadow-none">
        {/* System header */}
        <div className="mb-4 flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-accent" />
          <span className="font-mono text-xs font-semibold uppercase tracking-widest text-accent">
            OpenWatch — Dossiê Investigativo
          </span>
        </div>

        <h1 className="font-display text-xl font-bold text-primary leading-tight">
          {caseData.title}
        </h1>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Badge severity={caseData.severity as SignalSeverity} dot />
          <CaseTypeBadge caseType={caseData.case_type} />
          <span className="rounded bg-surface-subtle px-2 py-0.5 font-mono text-[10px] text-muted">
            #{shortId}
          </span>
        </div>

        {/* Metadata grid */}
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-lg border border-border bg-surface-base px-3 py-2">
            <p className="text-[10px] font-medium uppercase tracking-wide text-muted">Sinais</p>
            <p className="mt-0.5 font-mono tabular-nums text-sm font-bold text-primary">
              {caseData.signals.length}
            </p>
          </div>
          <div className="rounded-lg border border-border bg-surface-base px-3 py-2">
            <p className="text-[10px] font-medium uppercase tracking-wide text-muted">Entidades</p>
            <p className="mt-0.5 font-mono tabular-nums text-sm font-bold text-primary">
              {entityNames.length}
            </p>
          </div>
          {caseData.total_value_brl != null && caseData.total_value_brl > 0 && (
            <div className="col-span-2 rounded-lg border border-border bg-surface-base px-3 py-2">
              <p className="text-[10px] font-medium uppercase tracking-wide text-muted">
                Valor Total Estimado
              </p>
              <p className="mt-0.5 font-mono tabular-nums text-sm font-bold text-primary">
                {formatBRL(caseData.total_value_brl)}
              </p>
            </div>
          )}
          {periodLabel && (
            <div className="col-span-2 rounded-lg border border-border bg-surface-base px-3 py-2">
              <p className="text-[10px] font-medium uppercase tracking-wide text-muted">Período</p>
              <p className="mt-0.5 font-mono tabular-nums text-xs font-medium text-primary">
                {periodLabel}
              </p>
            </div>
          )}
        </div>

        {/* Entities list */}
        {entityNames.length > 0 && (
          <div className="mt-4">
            <p className="text-[10px] font-medium uppercase tracking-wide text-muted mb-1.5">
              Entidades Identificadas
            </p>
            <div className="flex flex-wrap gap-1.5">
              {entityNames.map((name, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 rounded-full border border-border bg-surface-base px-2.5 py-0.5 text-xs text-secondary"
                >
                  <Building2 className="h-3 w-3 text-muted" />
                  {name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Summary */}
        {caseData.summary && (
          <div className="mt-4 rounded-lg border border-border bg-surface-base p-3">
            <p className="text-xs leading-relaxed text-secondary">{caseData.summary}</p>
          </div>
        )}
      </div>

      {/* ── RESPONSÁVEIS ──────────────────────────────────────── */}
      <div className="space-y-6">
        {(caseData.entities?.length ?? 0) > 0 && (
          <DossierSection icon={Users} title="Responsáveis Identificados">
            <div className="space-y-2">
              {(caseData.entities as CaseEntityBrief[]).map((entity) => (
                <div
                  key={entity.id}
                  className="flex items-start gap-3 rounded-lg border border-border bg-surface-card p-3"
                >
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border bg-surface-base mt-0.5">
                    <EntityTypeIcon type={entity.type} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <Link
                      href={`/entity/${entity.id}`}
                      className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:text-accent print:pointer-events-none"
                    >
                      {entity.name}
                      <ExternalLink className="h-3 w-3 text-muted print:hidden" />
                    </Link>
                    {(entity.cnpj ?? entity.cnpj_masked) && (
                      <p className="font-mono text-[10px] text-muted mt-0.5">
                        CNPJ: {entity.cnpj ?? entity.cnpj_masked}
                      </p>
                    )}
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                      {entity.roles.map((role) => (
                        <span
                          key={role}
                          className="rounded-full border border-border bg-surface-base px-2 py-0.5 text-[10px] text-secondary"
                        >
                          {ROLE_LABELS[role] ?? role}
                        </span>
                      ))}
                      {entity.signal_ids.length > 0 && (
                        <span className="text-[10px] text-muted">
                          ·{" "}
                          {entity.signal_ids.length} {entity.signal_ids.length !== 1 ? "sinais" : "sinal"}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </DossierSection>
        )}

        {/* ── SIGNALS ───────────────────────────────────────────── */}
        <DossierSection icon={AlertTriangle} title="Sinais de Risco Detectados">
          <div className="space-y-3">
            {sortedSignals.map((signal) => (
              <div
                key={signal.id}
                className="rounded-lg border border-border bg-surface-card p-4"
              >
                <div className="flex items-start gap-3">
                  <span
                    className={cn(
                      "mt-1 h-2.5 w-2.5 shrink-0 rounded-full",
                      severityDotColor(signal.severity),
                    )}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono tabular-nums text-xs font-bold text-accent">
                        {signal.typology_code}
                      </span>
                      <span className="text-xs text-secondary">
                        {TYPOLOGY_LABELS[signal.typology_code] ?? signal.typology_name}
                      </span>
                      <Badge severity={signal.severity as SignalSeverity} />
                    </div>
                    <p className="mt-1.5 text-sm font-medium text-primary leading-snug">
                      {signal.title}
                    </p>
                    {signal.summary && (
                      <p className="mt-1 text-xs text-secondary leading-relaxed">
                        {signal.summary}
                      </p>
                    )}
                    <div className="mt-2 flex items-center gap-3 text-xs text-muted">
                      <span>
                        Confiança:{" "}
                        <span className="font-mono tabular-nums font-semibold text-primary">
                          {Math.round(signal.confidence * 100)}%
                        </span>
                      </span>
                      {(signal.period_start || signal.period_end) && (
                        <span>
                          Período:{" "}
                          <span className="font-mono tabular-nums text-primary">
                            {signal.period_start ? formatDate(signal.period_start) : "—"}
                            {" → "}
                            {signal.period_end ? formatDate(signal.period_end) : "—"}
                          </span>
                        </span>
                      )}
                      {signal.evidence_count != null && signal.evidence_count > 0 && (
                        <span>
                          {signal.evidence_count} evidência{signal.evidence_count !== 1 ? "s" : ""}
                        </span>
                      )}
                    </div>
                    {(() => {
                      const topFactors = Object.entries(signal.factors ?? {})
                        .filter(([, v]) => v !== null && v !== undefined && v !== false && v !== "")
                        .slice(0, 2);
                      if (topFactors.length === 0) return null;
                      return (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {topFactors.map(([key, value]) => {
                            const meta = signal.factor_descriptions?.[key];
                            const label = meta?.label ?? key;
                            let display = String(value);
                            if (meta?.unit === "brl" && typeof value === "number") {
                              display = formatBRL(value);
                            } else if (meta?.unit === "percent" && typeof value === "number") {
                              const pct = value > 1 ? value : value * 100;
                              display = `${pct.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
                            } else if (meta?.unit === "days" && typeof value === "number") {
                              display = `${Math.round(value)} dias`;
                            } else if (typeof value === "number") {
                              display = value.toLocaleString("pt-BR", { maximumFractionDigits: 4 });
                            }
                            return (
                              <span
                                key={key}
                                className="inline-flex items-center gap-1 rounded border border-border bg-surface-base px-2 py-0.5 text-[10px] text-secondary"
                              >
                                <span className="text-muted">{label}:</span>
                                <span className="font-mono tabular-nums font-semibold text-primary">{display}</span>
                              </span>
                            );
                          })}
                        </div>
                      );
                    })()}
                  </div>
                  <Link
                    href={`/signal/${signal.id}`}
                    className="shrink-0 rounded-md border border-border bg-surface-base px-2 py-1 text-[10px] font-medium text-secondary transition hover:bg-surface-subtle print:hidden"
                  >
                    Ver sinal
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </DossierSection>

        {/* ── LEGAL HYPOTHESES ──────────────────────────────── */}
        {hypotheses.length > 0 && (
          <DossierSection icon={Scale} title="Hipóteses de Violação Legal">
            <div className="overflow-hidden rounded-lg border border-border">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-border bg-surface-subtle">
                  <tr>
                    <th className="px-3 py-2 font-semibold uppercase tracking-wide text-muted">
                      Lei
                    </th>
                    <th className="px-3 py-2 font-semibold uppercase tracking-wide text-muted">
                      Artigo
                    </th>
                    <th className="px-3 py-2 font-semibold uppercase tracking-wide text-muted">
                      Tipo de Violação
                    </th>
                    <th className="px-3 py-2 text-right font-semibold uppercase tracking-wide text-muted">
                      Confiança
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {hypotheses.map((h) => (
                    <tr key={h.id} className="bg-surface-card">
                      <td className="px-3 py-2 font-medium text-primary">{h.law_name}</td>
                      <td className="px-3 py-2 font-mono text-primary">{h.article ?? "—"}</td>
                      <td className="px-3 py-2 text-secondary">
                        {VIOLATION_TYPE_LABELS[h.violation_type ?? ""] ?? h.violation_type ?? "—"}
                      </td>
                      <td className="px-3 py-2 text-right">
                        <span className="font-mono tabular-nums font-semibold text-primary">
                          {Math.round(h.confidence * 100)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </DossierSection>
        )}

        {/* ── EVIDENCE / PROVENANCE ─────────────────────────── */}
        {provenance.signals.length > 0 && (
          <DossierSection icon={BookOpen} title="Cadeia de Evidências">
            <div className="space-y-3">
              {provenance.signals.map((sig) => {
                const sources = sig.event_ids
                  .flatMap((eid) => provenance.event_raw_sources[eid] ?? [])
                  .filter(Boolean);
                return (
                  <div
                    key={sig.id}
                    className="rounded-lg border border-border bg-surface-card p-3"
                  >
                    <p className="text-xs font-medium text-primary">{sig.title}</p>
                    {sources.length > 0 ? (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {sources.slice(0, 8).map((src, i) => (
                          <span
                            key={i}
                            className="inline-flex items-center gap-1 rounded border border-border bg-surface-base px-2 py-0.5 font-mono text-[10px] text-muted"
                          >
                            <Link2 className="h-2.5 w-2.5" />
                            {src.connector}/{src.raw_id}
                          </span>
                        ))}
                        {sources.length > 8 && (
                          <span className="text-[10px] text-muted">
                            +{sources.length - 8} mais
                          </span>
                        )}
                      </div>
                    ) : (
                      <p className="mt-1 text-[10px] text-muted">
                        Referências de eventos sem rastreamento de fonte disponível.
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
            {uniqueConnectors.length > 0 && (
              <p className="text-[10px] text-muted">
                Fontes utilizadas:{" "}
                <span className="font-mono">{uniqueConnectors.join(", ")}</span>
              </p>
            )}
          </DossierSection>
        )}

        {/* ── DATA SOURCES ──────────────────────────────────── */}
        <DossierSection icon={FileText} title="Fontes de Dados">
          <div className="rounded-lg border border-border bg-surface-card p-4">
            <p className="text-xs text-secondary leading-relaxed">
              Este dossiê foi gerado automaticamente com base em dados públicos disponíveis no
              Portal da Transparência Federal, PNCP (Portal Nacional de Contratações Públicas),
              ComprasGov, Receita Federal (CNPJ), e TSE (financiamento eleitoral). Todos os sinais
              são hipóteses investigativas determinísticas — não constituem acusação ou julgamento.
            </p>
            <p className="mt-2 text-[10px] text-muted">
              Gerado por OpenWatch — {new Date().toLocaleDateString("pt-BR")}
            </p>
          </div>
        </DossierSection>

        {/* ── DISCLAIMER ────────────────────────────────────── */}
        <div className="rounded-lg border border-border bg-surface-base p-4">
          <p className="text-xs text-muted leading-relaxed">
            <strong className="text-secondary">Aviso legal:</strong> Os sinais de risco
            apresentados neste dossiê constituem{" "}
            <em>hipóteses investigativas</em> baseadas em cruzamento automático de dados públicos.
            Não equivalem a acusação, condenação ou juízo de culpa. A decisão final pertence
            exclusivamente aos órgãos competentes (controle interno, auditoria, corregedoria,
            Ministério Público e Judiciário).
          </p>
        </div>
      </div>
    </div>
  );
}
