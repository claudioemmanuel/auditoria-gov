import Link from "next/link";
import { notFound } from "next/navigation";
import { getCase } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { DetailSkeleton } from "@/components/Skeleton";
import { Suspense } from "react";
import { formatBRL, formatDate, severityDotColor, cn } from "@/lib/utils";
import { TYPOLOGY_LABELS } from "@/lib/constants";
import { ArrowLeft, Network, Radar, Building2, User, Landmark } from "lucide-react";
import type { SignalSeverity, CaseDetail, CaseSignal } from "@/lib/types";

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

async function CaseContent({ id }: { id: string }) {
  let caseData: CaseDetail;
  try {
    caseData = await getCase(id);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "";
    if (msg.includes("404")) notFound();
    throw err;
  }

  const shortId = caseData.id.slice(0, 8).toUpperCase();
  const entityNames = caseData.entity_names ?? [];
  const sortedSignals = sortBySeverity(caseData.signals);

  const periodLabel =
    caseData.period_start || caseData.period_end
      ? `${caseData.period_start ? formatDate(caseData.period_start) : "---"} → ${caseData.period_end ? formatDate(caseData.period_end) : "---"}`
      : null;

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-sm text-muted" aria-label="Breadcrumb">
        <Link
          href="/radar"
          className="inline-flex items-center gap-1 hover:text-primary transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Radar
        </Link>
        <span className="text-placeholder">/</span>
        <span className="text-secondary">Caso #{shortId}</span>
      </nav>

      {/* Header */}
      <div className="mt-4">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-2xl font-bold text-primary leading-snug">
            {caseData.title}
          </h1>
          <Badge severity={caseData.severity} className="shrink-0 mt-1" />
        </div>

        {/* Sub-header meta line */}
        <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-secondary">
          {periodLabel && (
            <span className="font-mono tabular-nums">{periodLabel}</span>
          )}
          {caseData.total_value_brl != null && caseData.total_value_brl > 0 && (
            <>
              {periodLabel && <span className="text-placeholder">·</span>}
              <span className="font-mono tabular-nums">
                {formatBRL(caseData.total_value_brl)} total
              </span>
            </>
          )}
          {entityNames.length > 0 && (
            <>
              <span className="text-placeholder">·</span>
              <span>
                <span className="font-mono tabular-nums">{entityNames.length}</span>{" "}
                {entityNames.length === 1 ? "entidade" : "entidades"}
              </span>
            </>
          )}
          {caseData.signals.length > 0 && (
            <>
              <span className="text-placeholder">·</span>
              <span>
                <span className="font-mono tabular-nums">{caseData.signals.length}</span>{" "}
                {caseData.signals.length === 1 ? "sinal" : "sinais"}
              </span>
            </>
          )}
        </p>
      </div>

      {/* Summary */}
      {caseData.summary && (
        <section className="mt-6 rounded-lg border border-border bg-surface-card p-4">
          <h2 className="text-sm font-semibold text-primary mb-2">Resumo do Caso</h2>
          <p className="text-sm text-secondary leading-relaxed">{caseData.summary}</p>
        </section>
      )}

      {/* Two-column grid: Signals + Entities */}
      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Signals */}
        <section className="rounded-lg border border-border bg-surface-card p-4">
          <h2 className="text-sm font-semibold text-primary mb-3">
            Sinais{" "}
            <span className="font-mono tabular-nums text-muted">
              ({caseData.signals.length})
            </span>
          </h2>
          {sortedSignals.length === 0 ? (
            <p className="text-sm text-muted">Nenhum sinal associado</p>
          ) : (
            <ul className="space-y-2">
              {sortedSignals.map((signal) => (
                <li
                  key={signal.id}
                  className="flex items-center gap-2.5"
                >
                  <span
                    className={cn(
                      "h-2 w-2 shrink-0 rounded-full",
                      severityDotColor(signal.severity),
                    )}
                  />
                  <span className="font-mono tabular-nums text-xs text-secondary w-8 shrink-0">
                    {signal.typology_code}
                  </span>
                  <span className="flex-1 truncate text-xs text-secondary" title={TYPOLOGY_LABELS[signal.typology_code] ?? signal.typology_name}>
                    {TYPOLOGY_LABELS[signal.typology_code] ?? signal.typology_name}
                  </span>
                  <span className="font-mono tabular-nums text-xs text-muted shrink-0">
                    {signal.confidence.toFixed(2)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Entities */}
        <section className="rounded-lg border border-border bg-surface-card p-4">
          <h2 className="text-sm font-semibold text-primary mb-3">
            Entidades{" "}
            <span className="font-mono tabular-nums text-muted">
              ({entityNames.length})
            </span>
          </h2>
          {entityNames.length === 0 ? (
            <p className="text-sm text-muted">Nenhuma entidade identificada</p>
          ) : (
            <ul className="space-y-2">
              {entityNames.map((name, i) => (
                <li key={i} className="flex items-center gap-2.5">
                  <EntityTypeIcon type="company" />
                  <span className="flex-1 truncate text-xs text-secondary" title={name}>
                    {name}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Action buttons */}
      <div className="mt-6 flex flex-wrap gap-3">
        <Link
          href={`/investigation/${caseData.id}`}
          className="inline-flex items-center gap-1.5 rounded-lg bg-accent-subtle text-accent px-4 py-2 text-sm font-medium transition hover:opacity-80"
        >
          <Network className="h-4 w-4" />
          Investigar no Grafo
        </Link>
        <Link
          href="/radar"
          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-card px-4 py-2 text-sm font-medium text-secondary transition hover:bg-surface-subtle"
        >
          <Radar className="h-4 w-4" />
          Ver no Radar
        </Link>
      </div>
    </div>
  );
}

export default async function CaseDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <main className="flex-1">
      <Suspense
        fallback={
          <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
            <DetailSkeleton />
          </div>
        }
      >
        <CaseContent id={id} />
      </Suspense>
    </main>
  );
}
