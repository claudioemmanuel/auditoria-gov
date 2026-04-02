"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Building2, User, Landmark, GitBranch, AlertTriangle, Users, Radar, Activity,
} from "lucide-react";
import { getEntity, getGraphNeighborhood } from "@/lib/api";
import { EntityNetworkGraph } from "@/components/EntityNetworkGraph";
import { EmptyState } from "@/components/EmptyState";
import { DetailPageLayout } from "@/components/DetailPageLayout";
import { DetailHeader } from "@/components/DetailHeader";
import { DetailSkeleton } from "@/components/Skeleton";
import { normalizeUnknownDisplay } from "@/lib/utils";
import type { SignalSeverity, EntityDetail, NeighborhoodResponse } from "@/lib/types";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";

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


export default function EntityDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [entity, setEntity] = useState<EntityDetail | null>(null);
  const [neighborhood, setNeighborhood] = useState<NeighborhoodResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    async function load() {
      try {
        const e = await getEntity(id);
        if (cancelled) return;
        setEntity(e);
      } catch (err) {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : "Unknown error";
        setError(msg.includes("404") ? "not_found" : msg);
        return;
      }
      try {
        const n = await getGraphNeighborhood(id);
        if (!cancelled) setNeighborhood(n);
      } catch {
        // neighborhood is optional
      }
    }

    load();
    return () => { cancelled = true; };
  }, [id]);

  if (error === "not_found") {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <EmptyState title="Entidade nao encontrada" description="A entidade solicitada nao existe ou foi removida." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <EmptyState title="Erro ao carregar entidade" description={error} />
      </div>
    );
  }

  if (!entity) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <DetailSkeleton />
      </div>
    );
  }

  const TypeIcon = TYPE_ICONS[entity.type as keyof typeof TYPE_ICONS] ?? Building2;
  const typeLabel = TYPE_LABELS[entity.type] ?? normalizeUnknownDisplay(entity.type);
  const identifierEntries = Object.entries(entity.identifiers);
  const coParticipants = neighborhood?.co_participants ?? [];

  // ── Aside ────────────────────────────────────────────────────────
  const aside = (
    <>
      {/* Identity card - updated styling */}
      <div className="rounded-lg border border-[var(--color-border-light)] bg-white p-6 space-y-4">
        <div className="flex items-center gap-4">
          <div className="inline-flex h-14 w-14 shrink-0 items-center justify-center bg-[var(--color-secondary)]/10 border border-[var(--color-secondary)]/20 rounded-lg">
            <TypeIcon className="h-7 w-7 text-[var(--color-secondary)]" />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="font-display text-lg font-bold text-[var(--color-text-primary)] line-clamp-1">{entity.name}</h2>
            <p className="text-sm text-[var(--color-text-secondary)]">{typeLabel}</p>
          </div>
        </div>

        {/* Identifiers */}
        {identifierEntries.length > 0 && (
          <div className="border-t border-[var(--color-border-light)] pt-4 space-y-3">
            {identifierEntries.map(([key, value]) => (
              <div key={key}>
                <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-secondary)] mb-1">{key}</p>
                <p className="font-mono text-sm tabular-nums text-[var(--color-text-primary)]">
                  {normalizeUnknownDisplay(value)}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Cluster */}
        {entity.cluster_id && (
          <div className="border-t border-[var(--color-border-light)] pt-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-secondary)] mb-2">Cluster ID</p>
            <p className="font-mono text-sm tabular-nums text-[var(--color-text-primary)]">
              #{entity.cluster_id.slice(0, 8)}
            </p>
          </div>
        )}

        {/* ER confidence badge */}
        <ConfidenceBadge score={entity.cluster_confidence} />

        {/* Aliases */}
        {entity.aliases.length > 0 && (
          <div className="border-t border-[var(--color-border-light)] pt-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-secondary)] mb-2">
              Nomes Alternativos
            </p>
            <ul className="space-y-1.5">
              {entity.aliases.map((alias, i) => (
                <li key={i} className="text-sm text-[var(--color-text-secondary)]">
                  {alias.value}
                  <span className="ml-2 text-xs text-[var(--color-text-secondary)] opacity-70">
                    ({normalizeUnknownDisplay(alias.type)})
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Health status card - updated styling */}
      {(() => {
        const eventCount = neighborhood?.diagnostics?.entity_event_count ?? 0;
        const cpCount = coParticipants.length;
        let statusLabel: string;
        let statusClass: string;
        if (eventCount === 0) {
          statusLabel = "Sem dados";
          statusClass = "bg-gray-100 text-gray-700 border-gray-300";
        } else if (cpCount === 0) {
          statusLabel = "Baixo risco";
          statusClass = "bg-green-100 text-green-700 border-green-300";
        } else if (cpCount <= 5) {
          statusLabel = "Conectividade moderada";
          statusClass = "bg-amber-100 text-amber-700 border-amber-300";
        } else {
          statusLabel = "Alta conectividade";
          statusClass = "bg-red-100 text-red-700 border-red-300";
        }
        return (
          <div className="rounded-lg border border-[var(--color-border-light)] bg-white p-6 space-y-4">
            <div className="flex items-center gap-3">
              <Activity className="h-5 w-5 text-[var(--color-secondary)]" />
              <p className="text-sm font-semibold uppercase tracking-widest text-[var(--color-text-secondary)]">
                Saúde da Entidade
              </p>
            </div>
            <span className={`inline-flex items-center rounded-full border px-3.5 py-1.5 text-sm font-semibold ${statusClass}`}>
              {statusLabel}
            </span>
            <p className="text-sm text-[var(--color-text-secondary)]">
              <span className="font-semibold">{eventCount}</span> evento{eventCount !== 1 ? "s" : ""} · 
              <span className="font-semibold ml-1">{cpCount}</span> conexão{cpCount !== 1 ? "es" : ""}
            </p>
          </div>
        );
      })()}

      {/* Radar link - updated styling */}
      <div className="rounded-lg border border-[var(--color-border-light)] bg-white p-6">
        <Link
          href={`/radar?entity=${entity.id}`}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-[var(--color-secondary)] text-white px-4 py-3 text-sm font-semibold transition-all hover:shadow-md hover:shadow-[var(--color-secondary)]/30 w-full"
        >
          <Radar className="h-4 w-4" />
          Ver no Radar
        </Link>
      </div>
    </>
  );

  // ── Main ─────────────────────────────────────────────────────────
  const main = (
    <>
      {/* Risk Signals - modernized section header */}
      <section className="rounded-lg border border-[var(--color-border-light)] bg-white p-6">
        <h2 className="font-display flex items-center gap-2 text-xl font-bold text-[var(--color-text-primary)] mb-4">
          <AlertTriangle className="h-5 w-5 text-[var(--color-severity-high)]" />
          Sinais de Risco
        </h2>
        <div className="space-y-1.5">
          {SEVERITY_ORDER.map((sev) => (
            <div key={sev} className="flex items-center gap-2 text-sm">
              <span className={`h-2.5 w-2.5 rounded-full ${SEVERITY_DOT_CLASS[sev]}`} />
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
      </section>

      {/* Relationship Graph - modernized section header */}
      <section>
        <h2 className="font-display flex items-center gap-2 text-xl font-bold text-[var(--color-text-primary)] mb-4">
          <GitBranch className="h-5 w-5 text-[var(--color-secondary)]" />
          Rede de Relacionamentos
        </h2>
        <EntityNetworkGraph
          entityId={entity.id}
          className="border border-border rounded-lg overflow-hidden"
        />
      </section>

      {/* Co-participants - modernized section header */}
      <section>
        <h2 className="font-display flex items-center gap-2 text-xl font-bold text-[var(--color-text-primary)] mb-4">
          <Users className="h-5 w-5 text-[var(--color-secondary)]" />
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
                      NODE_TYPE_ICONS[cp.node_type as keyof typeof NODE_TYPE_ICONS] ?? User;
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
      </section>
    </>
  );

  return (
    <div className="ledger-page">
      <DetailPageLayout
        header={
          <DetailHeader
            breadcrumbs={[{ label: "Radar", href: "/radar" }, { label: entity.name }]}
            title={entity.name}
          />
        }
        aside={aside}
        main={main}
        maxWidth="6xl"
      />
    </div>
  );
}
