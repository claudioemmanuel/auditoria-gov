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
      {/* Identity card */}
      <div className="rounded-lg border border-border bg-surface-card p-4 space-y-3">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-accent-subtle border border-accent/20">
            <TypeIcon className="h-6 w-6 text-accent" />
          </div>
          <div className="min-w-0">
            <h2 className="font-display text-sm font-bold text-primary truncate">{entity.name}</h2>
            <p className="text-xs text-muted">{typeLabel}</p>
          </div>
        </div>

        {/* Identifiers */}
        {identifierEntries.length > 0 && (
          <div className="border-t border-border pt-3 space-y-2">
            {identifierEntries.map(([key, value]) => (
              <div key={key}>
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted">{key}</p>
                <p className="font-mono tabular-nums text-xs text-primary">
                  {normalizeUnknownDisplay(value)}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Cluster */}
        {entity.cluster_id && (
          <div className="border-t border-border pt-3">
            <p className="text-[10px] font-medium uppercase tracking-wide text-muted">Cluster</p>
            <p className="font-mono tabular-nums text-xs text-secondary">
              #{entity.cluster_id.slice(0, 8)}
            </p>
          </div>
        )}

        {/* Aliases */}
        {entity.aliases.length > 0 && (
          <div className="border-t border-border pt-3">
            <p className="text-[10px] font-medium uppercase tracking-wide text-muted mb-1">
              Nomes alternativos
            </p>
            <ul className="space-y-1">
              {entity.aliases.map((alias, i) => (
                <li key={i} className="text-xs text-secondary">
                  {alias.value}
                  <span className="ml-1 text-[10px] text-muted">
                    ({normalizeUnknownDisplay(alias.type)})
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Health status card */}
      {(() => {
        const eventCount = neighborhood?.diagnostics?.entity_event_count ?? 0;
        const cpCount = coParticipants.length;
        let statusLabel: string;
        let statusClass: string;
        if (eventCount === 0) {
          statusLabel = "Sem dados";
          statusClass = "bg-gray-500/10 text-gray-400 border-gray-500/20";
        } else if (cpCount === 0) {
          statusLabel = "Baixo risco";
          statusClass = "bg-green-500/10 text-green-400 border-green-500/20";
        } else if (cpCount <= 5) {
          statusLabel = "Conectividade moderada";
          statusClass = "bg-amber-500/10 text-amber-400 border-amber-500/20";
        } else {
          statusLabel = "Alta conectividade";
          statusClass = "bg-red-500/10 text-red-400 border-red-500/20";
        }
        return (
          <div className="rounded-lg border border-border bg-surface-card p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted" />
              <p className="text-[10px] font-medium uppercase tracking-wide text-muted">
                Saúde da Entidade
              </p>
            </div>
            <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusClass}`}>
              {statusLabel}
            </span>
            <p className="text-xs text-secondary">
              {eventCount} evento{eventCount !== 1 ? "s" : ""} · {cpCount} conexõe{cpCount !== 1 ? "s" : ""}
            </p>
          </div>
        );
      })()}

      {/* Radar link */}
      <div className="rounded-lg border border-border bg-surface-card p-4">
        <Link
          href={`/radar?entity=${entity.id}`}
          className="flex items-center gap-2 rounded-md bg-accent-subtle text-accent px-3 py-2 text-xs font-medium transition hover:opacity-80 w-full"
        >
          <Radar className="h-3.5 w-3.5" />
          Ver no Radar
        </Link>
      </div>
    </>
  );

  // ── Main ─────────────────────────────────────────────────────────
  const main = (
    <>
      {/* Risk Signals */}
      <section className="rounded-lg border border-border bg-surface-card p-4">
        <h2 className="font-display flex items-center gap-2 text-sm font-semibold text-primary mb-3">
          <AlertTriangle className="h-4 w-4 text-severity-high" />
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

      {/* Relationship Graph */}
      <section>
        <h2 className="font-display flex items-center gap-2 text-sm font-semibold text-primary mb-3">
          <GitBranch className="h-4 w-4 text-accent" />
          Rede de Relacionamentos
        </h2>
        <EntityNetworkGraph
          entityId={entity.id}
          className="border border-border rounded-lg overflow-hidden"
        />
      </section>

      {/* Co-participants */}
      <section>
        <h2 className="font-display flex items-center gap-2 text-sm font-semibold text-primary mb-3">
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
  );
}
