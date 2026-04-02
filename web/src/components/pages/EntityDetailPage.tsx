"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Building2,
  User,
  Landmark,
  AlertTriangle,
  Users,
  Radar,
  Activity,
  ChevronRight,
  Shield,
  FileText,
  Network,
} from "lucide-react";
import { getEntity, getGraphNeighborhood } from "@/lib/api";
import { EntityNetworkGraph } from "@/components/EntityNetworkGraph";
import { EmptyState } from "@/components/EmptyState";
import { DetailSkeleton } from "@/components/Skeleton";
import { normalizeUnknownDisplay } from "@/lib/utils";
import type { SignalSeverity, EntityDetail, NeighborhoodResponse } from "@/lib/types";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { EntityTypeBadge } from "@/components/Badge";
import { Button, LinkButton } from "@/components/Button";
import { clsx } from "clsx";

const TYPE_ICONS = {
  pessoa_fisica: User,
  person: User,
  pessoa_juridica: Building2,
  company: Building2,
  orgao: Landmark,
  org: Landmark,
} as const;

const TYPE_LABELS: Record<string, string> = {
  pessoa_fisica: "Pessoa Física",
  person: "Pessoa",
  pessoa_juridica: "Empresa",
  company: "Empresa",
  orgao: "Órgão",
  org: "Órgão",
};

const SEVERITY_ORDER: SignalSeverity[] = ["critical", "high", "medium", "low"];

const SEVERITY_LABELS: Record<SignalSeverity, string> = {
  critical: "CRÍTICO",
  high: "ALTO",
  medium: "MÉDIO",
  low: "BAIXO",
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

type Tab = "sinais" | "contratos" | "vinculos" | "sancoes";

const TABS: { id: Tab; label: string }[] = [
  { id: "sinais", label: "Sinais" },
  { id: "contratos", label: "Contratos" },
  { id: "vinculos", label: "Vínculos" },
  { id: "sancoes", label: "Sanções" },
];

function normalizeEntityType(type: string): "person" | "company" | "org" | "unknown" {
  if (type === "pessoa_fisica" || type === "person") return "person";
  if (type === "pessoa_juridica" || type === "company") return "company";
  if (type === "orgao" || type === "org") return "org";
  return "unknown";
}

export default function EntityDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [entity, setEntity] = useState<EntityDetail | null>(null);
  const [neighborhood, setNeighborhood] = useState<NeighborhoodResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("sinais");

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
        <EmptyState
          title="Entidade não encontrada"
          description="A entidade solicitada não existe ou foi removida."
        />
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
  const identifierEntries = Object.entries(entity.identifiers);
  const coParticipants = neighborhood?.co_participants ?? [];
  const eventCount = neighborhood?.diagnostics?.entity_event_count ?? 0;
  const normalizedType = normalizeEntityType(entity.type);
  const sector = entity.attrs?.sector as string | undefined;

  return (
    <div className="animate-slide-up mx-auto max-w-6xl px-4 py-6 sm:px-6 space-y-5">

      {/* ── Breadcrumb ─────────────────────────────────────────────── */}
      <nav className="flex items-center gap-1.5" style={{ color: "var(--color-text-3)" }}>
        <Link
          href="/radar"
          className="text-mono-xs transition-colors hover:text-[var(--color-amber-text)]"
        >
          Radar
        </Link>
        <ChevronRight className="h-3 w-3 opacity-40" />
        <Link
          href="/entidades"
          className="text-mono-xs transition-colors hover:text-[var(--color-amber-text)]"
        >
          Entidades
        </Link>
        <ChevronRight className="h-3 w-3 opacity-40" />
        <span className="text-mono-xs max-w-xs truncate" style={{ color: "var(--color-text-2)" }}>
          {entity.name}
        </span>
      </nav>

      {/* ── Entity Header Card ─────────────────────────────────────── */}
      <div className="ow-card">

        {/* Identity row */}
        <div className="ow-card-section flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-4">
            <div
              className="shrink-0 flex items-center justify-center h-16 w-16"
              style={{
                background: "var(--color-amber-dim)",
                border: "1px solid var(--color-amber-border)",
              }}
            >
              <TypeIcon className="h-8 w-8" style={{ color: "var(--color-amber)" }} />
            </div>

            <div className="min-w-0 space-y-2">
              <h1 className="text-display-lg leading-tight" style={{ color: "var(--color-text)" }}>
                {entity.name}
              </h1>
              <div className="flex flex-wrap items-center gap-2">
                <EntityTypeBadge type={normalizedType} />
                {sector && (
                  <span className="ow-badge ow-badge-neutral">{sector}</span>
                )}
              </div>
              {identifierEntries.length > 0 && (
                <div className="flex flex-wrap gap-x-6 gap-y-1.5 pt-1">
                  {identifierEntries.map(([key, value]) => (
                    <div key={key} className="flex items-baseline gap-1.5">
                      <span
                        className="text-mono-xs uppercase tracking-widest"
                        style={{ color: "var(--color-text-3)" }}
                      >
                        {key}
                      </span>
                      <span className="ow-id">{normalizeUnknownDisplay(value)}</span>
                    </div>
                  ))}
                </div>
              )}
              {entity.cluster_id && (
                <p className="text-mono-xs" style={{ color: "var(--color-text-3)" }}>
                  cluster{" "}
                  <span className="ow-id">#{entity.cluster_id.slice(0, 8)}</span>
                </p>
              )}
            </div>
          </div>

          <div className="shrink-0">
            <LinkButton href={`/radar?entity=${entity.id}`} variant="amber" size="sm">
                <Radar className="mr-1.5 h-3.5 w-3.5" />
                Ver no Radar
              </LinkButton>
          </div>
        </div>

        {entity.cluster_confidence != null && (
          <div className="ow-card-section">
            <ConfidenceBadge score={entity.cluster_confidence} />
          </div>
        )}

        {/* Risk Metrics Strip */}
        <div
          className="grid grid-cols-2 gap-px sm:grid-cols-4"
          style={{ background: "var(--color-border)" }}
        >
          {SEVERITY_ORDER.map((sev) => (
            <div
              key={sev}
              className="flex flex-col gap-1.5 px-5 py-4"
              style={{ background: "var(--color-surface)" }}
            >
              <span
                className="text-mono-xs uppercase tracking-widest"
                style={{ color: `var(--color-${sev}-text)` }}
              >
                {SEVERITY_LABELS[sev]}
              </span>
              <span
                className="text-display-md tabular-nums leading-none"
                style={{
                  fontFamily: "var(--font-mono)",
                  color: `var(--color-${sev})`,
                }}
              >
                —
              </span>
              <span className="text-mono-xs" style={{ color: "var(--color-text-3)" }}>
                ver Radar
              </span>
            </div>
          ))}
        </div>

        {/* Stats footer strip */}
        <div
          className="ow-card-section flex flex-wrap items-center gap-3 text-mono-xs"
          style={{ color: "var(--color-text-3)", background: "var(--color-surface-2)" }}
        >
          <span>
            <span
              className="tabular-nums font-semibold"
              style={{ color: "var(--color-text-2)" }}
            >
              {eventCount}
            </span>{" "}
            evento{eventCount !== 1 ? "s" : ""}
          </span>
          <span aria-hidden>·</span>
          <span>
            <span
              className="tabular-nums font-semibold"
              style={{ color: "var(--color-text-2)" }}
            >
              {coParticipants.length}
            </span>{" "}
            conexã{coParticipants.length !== 1 ? "ões" : "o"}
          </span>
          {entity.aliases.length > 0 && (
            <>
              <span aria-hidden>·</span>
              <span>
                <span
                  className="tabular-nums font-semibold"
                  style={{ color: "var(--color-text-2)" }}
                >
                  {entity.aliases.length}
                </span>{" "}
                alias
              </span>
            </>
          )}
        </div>
      </div>

      {/* ── Tabs ───────────────────────────────────────────────────── */}
      <div className="ow-card">

        {/* Tab nav */}
        <div
          className="flex overflow-x-auto border-b"
          style={{ borderColor: "var(--color-border)" }}
        >
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  "shrink-0 border-b-2 px-5 py-3.5 text-mono-sm transition-colors -mb-px",
                  isActive
                    ? "border-[var(--color-amber)]"
                    : "border-transparent hover:border-[var(--color-border-strong)]",
                )}
                style={{
                  color: isActive
                    ? "var(--color-amber-text)"
                    : "var(--color-text-3)",
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab panels */}
        <div className="ow-card-section">

          {/* ── Sinais ── */}
          {activeTab === "sinais" && (
            <div className="space-y-4">
              <div className="ow-alert ow-alert-warning flex items-start gap-3">
                <Activity
                  className="mt-0.5 h-4 w-4 shrink-0"
                  style={{ color: "var(--color-amber)" }}
                />
                <div>
                  <p
                    className="text-mono-sm font-semibold"
                    style={{ color: "var(--color-amber-text)" }}
                  >
                    Sinais disponíveis no Radar
                  </p>
                  <p className="mt-0.5 text-mono-xs" style={{ color: "var(--color-text-2)" }}>
                    A contagem detalhada por severidade está disponível na visão Radar
                    desta entidade.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {SEVERITY_ORDER.map((sev) => (
                  <div
                    key={sev}
                    className={`ow-signal-card ow-signal-card-${sev} flex flex-col gap-2 px-4 py-3`}
                  >
                    <span className="text-mono-xs uppercase tracking-widest">
                      {SEVERITY_LABELS[sev]}
                    </span>
                    <span
                      className="text-display-md leading-none"
                      style={{ fontFamily: "var(--font-mono)" }}
                    >
                      —
                    </span>
                  </div>
                ))}
              </div>

              <div>
                <LinkButton href={`/radar?entity=${entity.id}`} variant="ghost" size="sm">
                    <Radar className="mr-1.5 h-3.5 w-3.5" />
                    Acessar Radar desta Entidade
                  </LinkButton>
              </div>
            </div>
          )}

          {/* ── Contratos ── */}
          {activeTab === "contratos" && (
            <EmptyState
              icon={FileText}
              title="Sem contratos vinculados"
              description="Nenhum contrato foi associado diretamente a esta entidade nos dados disponíveis."
            />
          )}

          {/* ── Vínculos ── */}
          {activeTab === "vinculos" && (
            <div className="space-y-6">
              <div>
                <p
                  className="mb-3 text-mono-xs uppercase tracking-widest"
                  style={{ color: "var(--color-text-3)" }}
                >
                  Rede de Relacionamentos
                </p>
                <div
                  className="overflow-hidden"
                  style={{ border: "1px solid var(--color-border)" }}
                >
                  <EntityNetworkGraph entityId={entity.id} className="" />
                </div>
              </div>

              <div>
                <p
                  className="mb-3 text-mono-xs uppercase tracking-widest"
                  style={{ color: "var(--color-text-3)" }}
                >
                  Co-Participantes ({coParticipants.length})
                </p>

                {coParticipants.length === 0 ? (
                  <EmptyState
                    icon={Users}
                    title="Nenhum co-participante encontrado"
                    description="Esta entidade não possui co-participantes identificados nos eventos analisados."
                  />
                ) : (
                  <div className="ow-table-wrapper">
                    <table className="ow-table">
                      <thead>
                        <tr>
                          <th>Nome</th>
                          <th>Tipo</th>
                          <th className="text-right">Eventos em comum</th>
                        </tr>
                      </thead>
                      <tbody>
                        {coParticipants.map((cp) => {
                          const CpIcon =
                            NODE_TYPE_ICONS[cp.node_type as keyof typeof NODE_TYPE_ICONS] ?? User;
                          return (
                            <tr key={cp.entity_id} className="ow-card-hover">
                              <td>
                                <Link
                                  href={`/entity/${cp.entity_id}`}
                                  className="font-medium transition-colors hover:text-[var(--color-amber-text)]"
                                  style={{ color: "var(--color-text)" }}
                                >
                                  {cp.label}
                                </Link>
                              </td>
                              <td>
                                <span
                                  className="flex items-center gap-1.5 text-mono-sm"
                                  style={{ color: "var(--color-text-2)" }}
                                >
                                  <CpIcon className="h-3.5 w-3.5" />
                                  {NODE_TYPE_LABELS[cp.node_type] ??
                                    normalizeUnknownDisplay(cp.node_type)}
                                </span>
                              </td>
                              <td
                                className="text-right tabular-nums"
                                style={{
                                  fontFamily: "var(--font-mono)",
                                  color: "var(--color-text-2)",
                                }}
                              >
                                {cp.shared_events}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {entity.aliases.length > 0 && (
                <div>
                  <p
                    className="mb-3 text-mono-xs uppercase tracking-widest"
                    style={{ color: "var(--color-text-3)" }}
                  >
                    Nomes Alternativos ({entity.aliases.length})
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {entity.aliases.map((alias, i) => (
                      <span key={i} className="ow-badge ow-badge-neutral">
                        {alias.value}
                        <span className="ml-1.5 opacity-50">
                          {normalizeUnknownDisplay(alias.type)}
                        </span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── Sanções ── */}
          {activeTab === "sancoes" && (
            <EmptyState
              icon={Shield}
              title="Sem sanções registradas"
              description="Nenhuma sanção foi identificada para esta entidade nos dados disponíveis."
            />
          )}
        </div>
      </div>
    </div>
  );
}
