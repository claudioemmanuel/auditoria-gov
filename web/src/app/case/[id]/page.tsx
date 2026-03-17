"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getCase, fetchCaseLegalHypotheses, fetchRelatedCases } from "@/lib/api";
import { Badge } from "@/components/Badge";
import { DetailSkeleton } from "@/components/Skeleton";
import { DetailPageLayout } from "@/components/DetailPageLayout";
import { DetailHeader } from "@/components/DetailHeader";
import { LegalInferencePanel } from "@/components/LegalInferencePanel";
import { CaseTypeBadge } from "@/components/CaseTypeBadge";
import { EmptyState } from "@/components/EmptyState";
import { formatBRL, formatDate, severityDotColor, cn } from "@/lib/utils";
import { TYPOLOGY_LABELS } from "@/lib/constants";
import { Network, Radar, Building2, User, Landmark, ExternalLink, FileText } from "lucide-react";
import type { SignalSeverity, CaseDetail, CaseSignal, RelatedCase, LegalHypothesis } from "@/lib/types";

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

function EntityTypeIcon({ type }: { type: string }) {
  const t = type.toLowerCase();
  if (t === "person" || t === "individual" || t === "cpf") {
    return <User className="h-3.5 w-3.5 shrink-0 text-muted" />;
  }
  if (t === "org" || t === "organization" || t === "landmark") {
    return <Landmark className="h-3.5 w-3.5 shrink-0 text-muted" />;
  }
  return <Building2 className="h-3.5 w-3.5 shrink-0 text-muted" />;
}

export default function CaseDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [hypotheses, setHypotheses] = useState<LegalHypothesis[]>([]);
  const [relatedCases, setRelatedCases] = useState<RelatedCase[]>([]);
  const [error, setError] = useState<string | null>(null);

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

  if (error === "not_found") {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <EmptyState title="Caso nao encontrado" description="O caso solicitado nao existe ou foi removido." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <EmptyState title="Erro ao carregar caso" description={error} />
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

  const shortId = caseData.id.slice(0, 8).toUpperCase();
  const entityNames = caseData.entity_names ?? [];
  const sortedSignals = sortBySeverity(caseData.signals);

  const periodLabel =
    caseData.period_start || caseData.period_end
      ? `${caseData.period_start ? formatDate(caseData.period_start) : "---"} → ${caseData.period_end ? formatDate(caseData.period_end) : "---"}`
      : null;

  // ── Aside ────────────────────────────────────────────────────────
  const aside = (
    <>
      {/* Severity + Period + Value */}
      <div className="rounded-lg border border-border bg-surface-card p-4 space-y-3">
        <Badge severity={caseData.severity} />

        {periodLabel && (
          <div className="border-t border-border pt-3">
            <p className="text-[10px] font-medium uppercase tracking-wide text-muted mb-1">Período</p>
            <p className="font-mono tabular-nums text-xs text-primary">{periodLabel}</p>
          </div>
        )}

        {caseData.total_value_brl != null && caseData.total_value_brl > 0 && (
          <div className="border-t border-border pt-3">
            <p className="text-[10px] font-medium uppercase tracking-wide text-muted mb-1">Valor Total</p>
            <p className="font-mono tabular-nums text-sm font-bold text-primary">
              {formatBRL(caseData.total_value_brl)}
            </p>
          </div>
        )}

        <div className="flex gap-4 border-t border-border pt-3 text-xs text-secondary">
          <span>
            <span className="font-mono tabular-nums font-semibold text-primary">
              {caseData.signals.length}
            </span>{" "}
            {caseData.signals.length === 1 ? "sinal" : "sinais"}
          </span>
          <span>
            <span className="font-mono tabular-nums font-semibold text-primary">
              {entityNames.length}
            </span>{" "}
            {entityNames.length === 1 ? "entidade" : "entidades"}
          </span>
        </div>
      </div>

      {/* Signals compact list */}
      {sortedSignals.length > 0 && (
        <div className="rounded-lg border border-border bg-surface-card p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted mb-2">
            Sinais ({sortedSignals.length})
          </h3>
          <ul className="space-y-1.5">
            {sortedSignals.map((signal) => (
              <li key={signal.id} className="flex items-center gap-2">
                <span
                  className={cn(
                    "h-2 w-2 shrink-0 rounded-full",
                    severityDotColor(signal.severity),
                  )}
                />
                <span className="font-mono tabular-nums text-[10px] text-secondary w-7 shrink-0">
                  {signal.typology_code}
                </span>
                <span className="flex-1 truncate text-xs text-secondary" title={TYPOLOGY_LABELS[signal.typology_code] ?? signal.typology_name}>
                  {TYPOLOGY_LABELS[signal.typology_code] ?? signal.typology_name}
                </span>
                <span className="font-mono tabular-nums text-[10px] text-muted shrink-0">
                  {signal.confidence.toFixed(2)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Related Cases */}
      {relatedCases.length > 0 && (
        <div className="rounded-lg border border-border bg-surface-card p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted mb-2">
            Casos Relacionados ({relatedCases.length})
          </h3>
          <ul className="space-y-1.5">
            {relatedCases.map((rc) => (
              <li key={rc.id}>
                <Link
                  href={`/case/${rc.id}`}
                  className="flex items-center gap-2 rounded-md border border-border bg-surface-base px-2.5 py-1.5 transition hover:bg-surface-subtle"
                >
                  <span className={cn("h-2 w-2 shrink-0 rounded-full", severityDotColor(rc.severity))} />
                  <span className="flex-1 truncate text-xs text-secondary" title={rc.title}>{rc.title}</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="rounded-lg border border-border bg-surface-card p-4 space-y-2">
        <Link
          href={`/investigation/${caseData.id}`}
          className="flex items-center gap-2 rounded-md bg-accent-subtle text-accent px-3 py-2 text-xs font-medium transition hover:opacity-80 w-full"
        >
          <Network className="h-3.5 w-3.5" />
          Investigar no Grafo
        </Link>
        <Link
          href="/radar"
          className="flex items-center gap-2 rounded-md border border-border bg-surface-base px-3 py-2 text-xs font-medium text-secondary transition hover:bg-surface-subtle w-full"
        >
          <Radar className="h-3.5 w-3.5" />
          Ver no Radar
        </Link>
        <Link
          href={`/case/${caseData.id}/dossier`}
          className="flex items-center gap-2 rounded-md border border-border bg-surface-base px-3 py-2 text-xs font-medium text-secondary transition hover:bg-surface-subtle w-full"
        >
          <FileText className="h-3.5 w-3.5" />
          Gerar Dossiê
        </Link>
      </div>

      {/* Case ID */}
      <div className="rounded-lg border border-border bg-surface-card p-4">
        <p className="text-[10px] font-medium uppercase tracking-wide text-muted mb-1">ID do Caso</p>
        <p className="font-mono text-xs text-primary break-all">{shortId}</p>
      </div>
    </>
  );

  // ── Main ─────────────────────────────────────────────────────────
  const main = (
    <>
      {/* Summary */}
      {caseData.summary && (
        <section className="rounded-lg border border-border bg-surface-card p-4">
          <h2 className="font-display text-sm font-semibold text-primary mb-2">Resumo do Caso</h2>
          <p className="text-sm text-secondary leading-relaxed">{caseData.summary}</p>
        </section>
      )}

      {/* Grouping rationale */}
      {(() => {
        const rationale = (caseData.attrs as Record<string, unknown> | undefined)?.grouping_rationale as string | null | undefined;
        const fallback = `${caseData.signals.length} ${caseData.signals.length !== 1 ? "sinais" : "sinal"} agrupado${caseData.signals.length !== 1 ? "s" : ""} por entidade compartilhada.`;
        const text = rationale ?? fallback;
        return (
          <details className="rounded-lg border border-border bg-surface-card p-4">
            <summary className="cursor-pointer text-xs font-semibold text-secondary select-none list-none flex items-center gap-1.5">
              <span className="text-muted">▶</span>
              Por que este caso foi criado?
            </summary>
            <p className="mt-2 text-xs text-secondary leading-relaxed">{text}</p>
          </details>
        );
      })()}

      {/* Entities expanded */}
      {(caseData.entities?.length ?? entityNames.length) > 0 && (
        <section className="rounded-lg border border-border bg-surface-card p-4">
          <h2 className="font-display text-sm font-semibold text-primary mb-3">
            Entidades{" "}
            <span className="font-mono tabular-nums text-muted">
              ({caseData.entities?.length ?? entityNames.length})
            </span>
          </h2>
          <ul className="space-y-2">
            {caseData.entities
              ? caseData.entities.map((entity) => (
                  <li key={entity.id} className="flex items-center gap-2.5 rounded-md bg-surface-base px-3 py-2">
                    <EntityTypeIcon type={entity.type} />
                    <Link
                      href={`/entity/${entity.id}`}
                      className="flex-1 text-sm text-secondary truncate hover:text-primary"
                      title={entity.name}
                    >
                      {entity.name}
                    </Link>
                    {entity.signal_ids.length > 0 && (
                      <span className="font-mono tabular-nums text-[10px] text-muted shrink-0">
                        {entity.signal_ids.length} {entity.signal_ids.length !== 1 ? "sinais" : "sinal"}
                      </span>
                    )}
                  </li>
                ))
              : entityNames.map((name, i) => (
                  <li key={i} className="flex items-center gap-2.5 rounded-md bg-surface-base px-3 py-2">
                    <EntityTypeIcon type="company" />
                    <span className="flex-1 text-sm text-secondary truncate" title={name}>
                      {name}
                    </span>
                  </li>
                ))}
          </ul>
        </section>
      )}

      {/* Detailed Signals */}
      {sortedSignals.length > 0 && (
        <section>
          <h2 className="font-display text-sm font-semibold text-primary mb-3">
            Sinais Detalhados
          </h2>
          <div className="space-y-2">
            {sortedSignals.map((signal) => {
              const pct = Math.round(signal.confidence * 100);
              return (
                <Link
                  key={signal.id}
                  href={`/signal/${signal.id}`}
                  className="flex items-start gap-3 rounded-lg border border-border bg-surface-card p-3 transition hover:border-accent/30 hover:bg-accent-subtle/10"
                >
                  <span
                    className={cn(
                      "mt-1 h-2.5 w-2.5 shrink-0 rounded-full",
                      severityDotColor(signal.severity),
                    )}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono tabular-nums text-xs font-bold text-accent shrink-0">
                        {signal.typology_code}
                      </span>
                      <span className="text-xs text-secondary truncate">
                        {TYPOLOGY_LABELS[signal.typology_code] ?? signal.typology_name}
                      </span>
                    </div>
                    {signal.title && (
                      <p className="mt-1 text-xs font-medium text-primary truncate">
                        {signal.title}
                      </p>
                    )}
                    {signal.summary && (
                      <p className="mt-0.5 text-[11px] text-secondary line-clamp-2">
                        {signal.summary}
                      </p>
                    )}
                    <div className="mt-2 flex items-center gap-2">
                      <div className="h-1.5 flex-1 rounded-full bg-surface-base">
                        <div
                          className="h-1.5 rounded-full bg-accent"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="font-mono tabular-nums text-xs text-muted shrink-0">
                        {pct}%
                      </span>
                    </div>
                  </div>
                  <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted" />
                </Link>
              );
            })}
          </div>
        </section>
      )}
    </>
  );

  return (
    <DetailPageLayout
      header={
        <DetailHeader
          breadcrumbs={[{ label: "Radar", href: "/radar" }, { label: `Caso #${shortId}` }]}
          title={caseData.title}
          badge={
            <div className="flex items-center gap-2 shrink-0">
              <Badge severity={caseData.severity} />
              <CaseTypeBadge caseType={caseData.case_type} />
            </div>
          }
        />
      }
      aside={aside}
      main={
        <>
          {main}
          <LegalInferencePanel hypotheses={hypotheses} />
        </>
      }
    />
  );
}
