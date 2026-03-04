import { notFound } from "next/navigation";
import Link from "next/link";
import { Building2, User, Landmark, GitBranch, AlertTriangle, Users } from "lucide-react";
import { getEntity, getGraphNeighborhood } from "@/lib/api";
import { GraphView } from "@/components/GraphView";
import { EmptyState } from "@/components/EmptyState";
import { normalizeUnknownDisplay } from "@/lib/utils";
import type { SignalSeverity } from "@/lib/types";

const TYPE_ICONS = {
  pessoa_fisica: User,
  person: User,
  pessoa_juridica: Building2,
  company: Building2,
  orgao: Landmark,
  org: Landmark,
} as const;

const TYPE_LABELS: Record<string, string> = {
  pessoa_fisica: "Pessoa Fisica",
  person: "Pessoa",
  pessoa_juridica: "Empresa",
  company: "Empresa",
  orgao: "Órgão",
  org: "Órgão",
};

const SEVERITY_ORDER: SignalSeverity[] = ["critical", "high", "medium", "low"];

const SEVERITY_LABELS: Record<SignalSeverity, string> = {
  critical: "CRITICO",
  high: "ALTO",
  medium: "MEDIO",
  low: "BAIXO",
};

const SEVERITY_DOT_CLASS: Record<SignalSeverity, string> = {
  critical: "bg-severity-critical",
  high: "bg-severity-high",
  medium: "bg-severity-medium",
  low: "bg-severity-low",
};

const SEVERITY_TEXT_CLASS: Record<SignalSeverity, string> = {
  critical: "text-severity-critical",
  high: "text-severity-high",
  medium: "text-severity-medium",
  low: "text-severity-low",
};

const NODE_TYPE_ICONS = {
  person: User,
  company: Building2,
  org: Landmark,
} as const;

const NODE_TYPE_LABELS: Record<string, string> = {
  person: "Pessoa",
  company: "Empresa",
  org: "Órgão",
};

export default async function EntityDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let entity: Awaited<ReturnType<typeof getEntity>>;
  try {
    entity = await getEntity(id);
  } catch {
    notFound();
    return null as never;
  }

  let neighborhood;
  try {
    neighborhood = await getGraphNeighborhood(id);
  } catch {
    neighborhood = null;
  }

  const TypeIcon =
    TYPE_ICONS[entity.type as keyof typeof TYPE_ICONS] ?? Building2;
  const typeLabel = TYPE_LABELS[entity.type] ?? normalizeUnknownDisplay(entity.type);

  // Primary identifier for sub-line (CNPJ, CPF, or first key)
  const identifierEntries = Object.entries(entity.identifiers);
  const primaryId = identifierEntries[0];

  // Co-participants from neighborhood
  const coParticipants = neighborhood?.co_participants ?? [];

  return (
    <div>
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 space-y-6">

        {/* Header */}
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-accent-subtle">
            <TypeIcon className="h-6 w-6 text-accent" />
          </div>
          <div className="min-w-0">
            <h1 className="text-2xl font-bold text-primary truncate">
              {entity.name}
            </h1>
            <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-secondary">
              {primaryId && (
                <>
                  <span className="font-mono tabular-nums text-muted">
                    {primaryId[0].toUpperCase()}: {primaryId[1]}
                  </span>
                  <span className="text-placeholder">·</span>
                </>
              )}
              <span>{typeLabel}</span>
              {entity.cluster_id && (
                <>
                  <span className="text-placeholder">·</span>
                  <span className="font-mono tabular-nums text-muted text-xs">
                    Cluster #{entity.cluster_id.slice(0, 8)}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Two-column grid: Risk signals + Identifiers */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">

          {/* Sinais de Risco */}
          <div className="rounded-lg border border-border bg-surface-card p-4">
            <div className="flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-primary">
                <AlertTriangle className="h-4 w-4 text-severity-high" />
                Sinais de Risco
              </h2>
              <Link
                href={`/radar?entity=${entity.id}`}
                className="text-xs text-accent hover:underline"
              >
                Ver no Radar
              </Link>
            </div>
            <div className="mt-3 space-y-1.5">
              {SEVERITY_ORDER.map((sev) => (
                <div key={sev} className="flex items-center gap-2 text-sm">
                  <span
                    className={`h-2 w-2 rounded-full ${SEVERITY_DOT_CLASS[sev]}`}
                  />
                  <span className={`font-semibold text-xs ${SEVERITY_TEXT_CLASS[sev]}`}>
                    {SEVERITY_LABELS[sev]}
                  </span>
                  <span className="text-muted text-xs">— ver Radar para contagem</span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-muted">
              Contagem de sinais disponivel no Radar.
            </p>
          </div>

          {/* Identificadores */}
          <div className="rounded-lg border border-border bg-surface-card p-4">
            <h2 className="text-sm font-semibold text-primary">
              Identificadores
            </h2>
            {identifierEntries.length > 0 ? (
              <dl className="mt-3 space-y-2">
                {identifierEntries.map(([key, value]) => (
                  <div key={key} className="flex flex-col gap-0.5">
                    <dt className="text-xs font-medium uppercase text-muted tracking-wide">
                      {key}
                    </dt>
                    <dd className="font-mono tabular-nums text-sm text-primary">
                      {normalizeUnknownDisplay(value)}
                    </dd>
                  </div>
                ))}
                {entity.aliases.length > 0 && (
                  <>
                    <dt className="text-xs font-medium uppercase text-muted tracking-wide pt-1">
                      Nomes alternativos
                    </dt>
                    {entity.aliases.map((alias, i) => (
                      <dd key={i} className="text-sm text-secondary">
                        {alias.value}
                        <span className="ml-1 text-xs text-muted">
                          ({normalizeUnknownDisplay(alias.type)})
                        </span>
                      </dd>
                    ))}
                  </>
                )}
              </dl>
            ) : (
              <p className="mt-3 text-sm text-muted">
                Nenhum identificador disponivel.
              </p>
            )}
          </div>
        </div>

        {/* Rede de Relacionamentos */}
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-primary mb-3">
            <GitBranch className="h-4 w-4 text-accent" />
            Rede de Relacionamentos
          </h2>
          <GraphView entityId={entity.id} height={400} className="border border-border rounded-lg overflow-hidden" />
        </div>

        {/* Co-Participantes */}
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-primary mb-3">
            <Users className="h-4 w-4 text-accent" />
            Co-Participantes ({coParticipants.length})
          </h2>
          {coParticipants.length === 0 ? (
            <EmptyState
              title="Nenhum co-participante encontrado"
              description="Esta entidade nao possui co-participantes identificados nos eventos analisados."
            />
          ) : (
            <div className="overflow-hidden rounded-lg border border-border bg-surface-card">
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-surface-base">
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">
                        Nome
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">
                        Tipo
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-muted">
                        Eventos em comum
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {coParticipants.map((cp) => {
                      const CpIcon =
                        NODE_TYPE_ICONS[cp.node_type as keyof typeof NODE_TYPE_ICONS] ??
                        User;
                      return (
                        <tr
                          key={cp.entity_id}
                          className="group cursor-pointer hover:bg-surface-subtle transition-colors"
                        >
                          <td className="px-4 py-3">
                            <Link
                              href={`/entity/${cp.entity_id}`}
                              className="font-medium text-primary group-hover:text-accent transition-colors"
                            >
                              {cp.label}
                            </Link>
                          </td>
                          <td className="px-4 py-3">
                            <span className="inline-flex items-center gap-1.5 text-secondary">
                              <CpIcon className="h-3.5 w-3.5 text-muted" />
                              {NODE_TYPE_LABELS[cp.node_type] ??
                                normalizeUnknownDisplay(cp.node_type)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums text-secondary">
                            {cp.shared_events}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
