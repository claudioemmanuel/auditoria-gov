"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getSignalGraph } from "@/lib/api";
import type { SignalGraphResponse, SignalInvolvedEntityProfile } from "@/lib/types";
import type { GNode, GLink } from "@/hooks/useCaseGraph";
import { CONNECTOR_COLORS, CONNECTOR_LABELS } from "@/lib/constants";
import { InvestigationCanvas } from "@/components/investigation/InvestigationCanvas";
import { PageHeader } from "@/components/PageHeader";
import { DetailSkeleton } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { severityColor, formatDate, formatBRL } from "@/lib/utils";
import { SEVERITY_LABELS } from "@/lib/constants";
import {
  AlertTriangle,
  Network,
  Scale,
  ArrowRight,
  Calendar,
  Users,
  FileText,
  Waypoints,
  MapPin,
  Tag,
  DollarSign,
  Info,
  ExternalLink,
} from "lucide-react";

function entityTypeLabel(nodeType: string): string {
  if (nodeType === "org") return "Órgão";
  if (nodeType === "company") return "Empresa";
  if (nodeType === "person") return "Pessoa";
  return nodeType;
}

function entityDisplayName(name: string, entityId: string, nodeType: string): string {
  if (name && name.trim()) return name;
  return `${entityTypeLabel(nodeType)} (${entityId.slice(0, 8)}...)`;
}

function attrLabel(key: string): string {
  const labels: Record<string, string> = {
    modalidade: "Modalidade",
    modality: "Modalidade",
    situacao: "Situação",
    uf: "UF",
    catmat_group: "CATMAT",
  };
  return labels[key] ?? key;
}

function attrValue(val: unknown): string {
  if (!val || val === "" || val === "nao_informado" || val === "sem classificacao") return "—";
  return String(val);
}

function cleanSourceId(sourceId: string): string {
  // Strip internal pagination cursors like "pncp_contracting_notices:w28p7:99"
  // Show only meaningful identifiers
  const parts = sourceId.split(":");
  if (parts.length >= 2 && /^w\d+p\d+$/.test(parts[1] ?? "")) {
    // Format: connector:w{n}p{m}:{idx} → just show connector
    return parts[0] ?? sourceId;
  }
  return sourceId;
}

const UUID_PATTERN = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;

function cleanUuidsInText(text: string): string {
  // Replace bare UUIDs with shortened form only if surrounded by punctuation/spaces (not in proper nouns)
  return text.replace(UUID_PATTERN, (match) => `[${match.slice(0, 8)}…]`);
}

function cleanDescription(description: string, sourceConnector: string): string {
  // If description is just "Evento {uuid}", show a semantic fallback
  if (/^Evento\s+[0-9a-f-]{36}$/i.test(description.trim())) {
    const labels: Record<string, string> = {
      pncp: "Contratação pública (PNCP)",
      compras_gov: "Licitação (ComprasGov)",
      comprasnet_contratos: "Contrato (Comprasnet)",
      transferegov: "Transferência federal",
      portal_transparencia: "Dado do Portal da Transparência",
      tse: "Dado eleitoral (TSE)",
      camara: "Despesa parlamentar (Câmara)",
    };
    return labels[sourceConnector] ?? "Evento público registrado";
  }
  return description;
}


export default function SignalGraphPage() {
  const params = useParams();
  const signalId = params.id as string;

  const [data, setData] = useState<SignalGraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GNode | null>(null);
  const [roleFilter, setRoleFilter] = useState("all");
  const [showExpanded, setShowExpanded] = useState(true);

  useEffect(() => {
    if (!signalId) return;
    setLoading(true);
    setError(null);
    getSignalGraph(signalId)
      .then((response) => {
        setData(response);
      })
      .catch(() => setError("Erro ao carregar teia investigativa do sinal"))
      .finally(() => setLoading(false));
  }, [signalId]);

  const expandedCount = data?.overview.expanded_nodes?.length ?? 0;
  const expansionEdgeCount = data?.overview.expansion_edges?.length ?? 0;

  const graphData = useMemo(() => {
    if (!data) return { nodes: [] as GNode[], links: [] as GLink[] };

    const starterIds = new Set(data.pattern_story.started_from_entities.map((entity) => entity.entity_id));

    // Direct participant nodes
    const directNodes: GNode[] = data.overview.nodes.map((node) => ({
      id: node.id,
      label: node.label,
      node_type: node.node_type,
      entity_id: node.entity_id,
      isSeed: starterIds.has(node.entity_id),
      isFocused: false,
    }));

    // BFS expanded nodes (only if toggle is on)
    const bfsNodes: GNode[] = showExpanded
      ? (data.overview.expanded_nodes ?? []).map((node) => ({
          id: node.id,
          label: node.label,
          node_type: node.node_type,
          entity_id: node.entity_id,
          isSeed: false,
          isFocused: false,
          isExpanded: true,
          sourceConnector: node.source_connector ?? undefined,
        }))
      : [];

    const allNodes = [...directNodes, ...bfsNodes];

    // Build entity_id → node_id map for resolving expansion edges
    const entityToNodeId: Record<string, string> = {};
    for (const node of allNodes) {
      entityToNodeId[node.entity_id] = node.id;
    }

    // Direct edges
    const directLinks: GLink[] = data.overview.edges.map((edge) => ({
      id: edge.id,
      source: edge.from_node_id,
      target: edge.to_node_id,
      type: edge.type,
      weight: edge.weight,
      isFocused: false,
    }));

    // BFS expansion edges (only if toggle is on)
    const bfsLinks: GLink[] = showExpanded
      ? (data.overview.expansion_edges ?? [])
          .map((edge) => ({
            id: edge.id,
            source: entityToNodeId[edge.from_entity_id] ?? "",
            target: entityToNodeId[edge.to_entity_id] ?? "",
            type: edge.edge_type,
            weight: edge.weight,
            isFocused: false,
            isExpansion: true,
          }))
          .filter((link) => link.source && link.target)
      : [];

    return {
      nodes: allNodes,
      links: [...directLinks, ...bfsLinks],
    };
  }, [data, showExpanded]);

  const degreeMap = useMemo(() => {
    const map: Record<string, number> = {};
    for (const edge of graphData.links) {
      map[edge.source] = (map[edge.source] ?? 0) + 1;
      map[edge.target] = (map[edge.target] ?? 0) + 1;
    }
    return map;
  }, [graphData.links]);

  const nodeAttrsMap = useMemo(() => {
    if (!data) return {};
    const map: Record<string, Record<string, unknown>> = {};
    for (const node of data.overview.nodes) {
      map[node.id] = node.attrs || {};
    }
    for (const node of data.overview.expanded_nodes ?? []) {
      map[node.id] = node.attrs || {};
    }
    return map;
  }, [data]);

  const entitySeverityMap = useMemo(() => {
    if (!data) return {};
    const map: Record<string, "low" | "medium" | "high" | "critical"> = {};
    for (const node of data.overview.nodes) {
      map[node.entity_id] = data.signal.severity;
    }
    return map;
  }, [data]);

  const selectedEntity: SignalInvolvedEntityProfile | null = useMemo(() => {
    if (!data || !selectedNode) return null;
    return data.involved_entities.find((entity) => entity.entity_id === selectedNode.entity_id) ?? null;
  }, [data, selectedNode]);

  const roleOptions = useMemo(() => {
    if (!data) return [];
    return Array.from(
      new Set(
        data.timeline.flatMap((event) =>
          event.participants.map((participant) => participant.role),
        ),
      ),
    ).sort((a, b) => a.localeCompare(b));
  }, [data]);

  const filteredTimeline = useMemo(() => {
    if (!data) return [];
    if (roleFilter === "all") return data.timeline;
    return data.timeline.filter((event) =>
      event.participants.some((participant) => participant.role === roleFilter),
    );
  }, [data, roleFilter]);

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-8">
        <DetailSkeleton />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <EmptyState
          icon={AlertTriangle}
          title="Não foi possível carregar a teia do sinal"
          description={error || "Sinal não encontrado"}
        />
      </div>
    );
  }

  const hasGraph = graphData.nodes.length > 0 && graphData.links.length > 0;

  return (
    <div className="ledger-page mx-auto max-w-6xl px-4 py-8">
      <PageHeader
        eyebrow="Teia investigativa"
        title={data.signal.title}
        description={`${data.signal.typology_code} · ${data.signal.typology_name}`}
        breadcrumbs={[
          { label: "Radar", href: "/radar" },
          { label: "Sinal", href: `/signal/${data.signal.id}` },
          { label: "Teia investigativa" },
        ]}
        variant="hero"
        icon={<Network className="h-5 w-5" />}
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`rounded-full px-3 py-1 text-xs font-medium ${severityColor(data.signal.severity)}`}>
              {SEVERITY_LABELS[data.signal.severity]}
            </span>
            <span className="rounded-full bg-accent-subtle px-3 py-1 text-xs font-semibold text-accent">
              {Math.round(data.signal.confidence * 100)}% confiança
            </span>
            <Link
              href={`/signal/${data.signal.id}`}
              className="rounded-lg border border-border bg-surface-card px-3 py-1.5 text-xs font-medium text-secondary transition hover:bg-surface-subtle"
            >
              Voltar ao sinal
            </Link>
          </div>
        }
      />

      {/* Summary cards */}
      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-accent/20 bg-accent-subtle p-4 sm:col-span-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent">Padrão detectado</p>
          <p className="mt-1 text-sm font-medium text-primary">{data.pattern_story.pattern_label}</p>
          <p className="mt-2 text-xs text-accent-hover leading-relaxed">{cleanUuidsInText(data.pattern_story.why_flagged)}</p>
        </div>

        {/* Value */}
        <div className="rounded-lg border border-border bg-surface-card p-4">
          <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-secondary">
            <DollarSign className="h-3.5 w-3.5" />
            Valor estimado
          </p>
          {data.timeline[0]?.value_brl != null ? (
            <p className="mt-1 text-lg font-bold text-primary tabular-nums">
              {formatBRL(data.timeline[0].value_brl)}
            </p>
          ) : (
            <p className="mt-1 text-sm text-muted">Não informado</p>
          )}
          <p className="mt-1 text-xs text-muted">
            {data.pattern_story.started_at ? formatDate(data.pattern_story.started_at) : "Data desconhecida"}
          </p>
        </div>

        {/* Event attrs */}
        <div className="rounded-lg border border-border bg-surface-card p-4">
          <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-secondary">
            <Info className="h-3.5 w-3.5" />
            Atributos
          </p>
          <div className="mt-2 space-y-1.5">
            {(["modalidade", "uf", "situacao", "catmat_group"] as const).map((key) => {
              const val = attrValue(data.timeline[0]?.attrs?.[key]);
              return (
                <div key={key} className="flex items-center justify-between gap-2">
                  <span className="text-[10px] uppercase tracking-wide text-muted">{attrLabel(key)}</span>
                  <span className="text-xs font-medium text-secondary truncate max-w-[100px]">{val}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Entities involved */}
      <div className="mt-3 rounded-lg border border-border bg-surface-card px-4 py-3">
        <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-secondary">
          <Users className="h-3.5 w-3.5" />
          Entidades envolvidas ({data.overview.nodes.length + (data.overview.expanded_nodes?.length ?? 0)})
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {data.pattern_story.started_from_entities.map((entity) => (
            <Link
              key={entity.entity_id}
              href={`/entity/${entity.entity_id}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent-subtle px-3 py-1 text-xs font-medium text-accent hover:opacity-80 transition"
            >
              {entityDisplayName(entity.name, entity.entity_id, entity.node_type)}
              <ExternalLink className="h-3 w-3 opacity-60" />
            </Link>
          ))}
          {data.overview.nodes
            .filter((n) => !data.pattern_story.started_from_entities.some((e) => e.entity_id === n.entity_id))
            .map((node) => (
              <Link
                key={node.entity_id}
                href={`/entity/${node.entity_id}`}
                className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-subtle px-3 py-1 text-xs text-secondary hover:bg-surface-hover transition"
              >
                {entityDisplayName(node.label, node.entity_id, node.node_type)}
                <ExternalLink className="h-3 w-3 opacity-40" />
              </Link>
            ))}
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-[2fr,1fr]">
        <div className="rounded-lg border border-border bg-surface-card p-3">
          <div className="mb-3 flex items-center justify-between px-1">
            <h2 className="font-display flex items-center gap-2 text-sm font-semibold text-primary">
              <Network className="h-4 w-4 text-accent" />
              Teia de conexões
            </h2>
            <div className="flex items-center gap-3">
              {expandedCount > 0 && (
                <button
                  onClick={() => setShowExpanded(!showExpanded)}
                  className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                    showExpanded
                      ? "bg-accent-subtle text-accent hover:bg-accent-subtle"
                      : "bg-surface-subtle text-muted hover:bg-surface-hover"
                  }`}
                >
                  <Waypoints className="h-3.5 w-3.5" />
                  {showExpanded ? "Ocultar expansão" : "Mostrar expansão"}
                </button>
              )}
              <span className="text-xs text-muted">
                {data.overview.nodes.length} entidades
                {expandedCount > 0 && (
                  <span className={showExpanded ? "text-accent" : "text-muted"}>
                    {" "}+ {expandedCount} descobertas
                  </span>
                )}
                {" - "}
                {data.overview.edges.length} ligações
                {expansionEdgeCount > 0 && showExpanded && (
                  <span className="text-accent"> + {expansionEdgeCount} conexões</span>
                )}
              </span>
            </div>
          </div>
          {hasGraph ? (
            <div className="relative h-[520px] overflow-hidden rounded-lg border border-border">
              <InvestigationCanvas
                graphData={graphData}
                degreeMap={degreeMap}
                entitySeverityMap={entitySeverityMap}
                nodeAttrsMap={nodeAttrsMap}
                selectedNodeId={selectedNode?.id ?? null}
                onNodeClick={(node) => setSelectedNode(node)}
                onBackgroundClick={() => setSelectedNode(null)}
                onClearSelected={() => setSelectedNode(null)}
                onExpandSelected={() => {}}
              />
            </div>
          ) : (
            <div className="space-y-2 rounded-lg border border-amber/20 bg-amber-subtle p-4">
              <p className="text-sm font-medium text-amber">Teia insuficiente para visualização em grafo</p>
              <p className="text-xs text-amber/80">
                {data.diagnostics.fallback_reason === "insufficient_entities"
                  ? `Apenas ${data.diagnostics.unique_entities} entidade(s) identificada(s) neste sinal. São necessárias pelo menos 2 entidades distintas para desenhar a rede.`
                  : `Motivo: ${data.diagnostics.fallback_reason || "sem detalhes"}.`}
              </p>
              <p className="text-xs text-amber/60">
                Eventos: {data.diagnostics.events_loaded}/{data.diagnostics.events_total} carregados · {data.diagnostics.participants_total} participações
              </p>
              {data.overview.nodes.length > 0 && (
                <div className="mt-3 space-y-1.5">
                  <p className="text-xs font-semibold text-secondary">Entidades identificadas:</p>
                  {data.overview.nodes.map((node) => (
                    <Link
                      key={node.entity_id}
                      href={`/entity/${node.entity_id}`}
                      className="flex items-center gap-2 rounded-md bg-surface-card border border-border px-3 py-2 text-xs text-secondary hover:text-accent transition"
                    >
                      <span className="font-medium">{entityDisplayName(node.label, node.entity_id, node.node_type)}</span>
                      <span className="text-muted">· {entityTypeLabel(node.node_type)}</span>
                      <ArrowRight className="ml-auto h-3.5 w-3.5 opacity-40" />
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="rounded-lg border border-border bg-surface-card p-4">
          <h2 className="font-display flex items-center gap-2 text-sm font-semibold text-primary">
            <Users className="h-4 w-4 text-accent" />
            Entidade selecionada
          </h2>
          {selectedEntity ? (
            <div className="mt-3 space-y-3">
              <div className="flex items-start gap-3">
                {selectedEntity.photo_url ? (
                  <img
                    src={selectedEntity.photo_url}
                    alt={`Foto de ${entityDisplayName(selectedEntity.name, selectedEntity.entity_id, selectedEntity.node_type)}`}
                    className="h-14 w-14 rounded-lg object-cover"
                  />
                ) : (
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg bg-surface-subtle text-lg text-muted">
                    {selectedEntity.node_type === "org" ? "🏛" : selectedEntity.node_type === "company" ? "🏢" : "👤"}
                  </div>
                )}
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-primary truncate">
                    {entityDisplayName(selectedEntity.name, selectedEntity.entity_id, selectedEntity.node_type)}
                  </p>
                  <p className="text-xs text-muted">{entityTypeLabel(selectedEntity.node_type)}</p>
                  <p className="mt-1 text-xs text-muted">
                    {selectedEntity.event_count} evento(s) · {selectedEntity.roles_in_signal.length} papel(is)
                  </p>
                </div>
              </div>

              {selectedEntity.is_direct_participant === false && (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-subtle px-2 py-0.5 text-xs text-amber">
                  <Waypoints className="h-3 w-3" />
                  Descoberto via expansão de rede
                </span>
              )}

              {Object.entries(selectedEntity.identifiers).filter(([, v]) => v && String(v).trim()).length > 0 && (
                <div className="space-y-1">
                  {Object.entries(selectedEntity.identifiers)
                    .filter(([, v]) => v && String(v).trim())
                    .map(([key, value]) => (
                      <p key={key} className="rounded bg-surface-base px-2 py-1 text-xs text-secondary">
                        <span className="font-semibold">{key.toUpperCase()}:</span> {String(value)}
                      </p>
                    ))}
                </div>
              )}

              {selectedEntity.roles_in_signal.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {selectedEntity.roles_in_signal.map((role) => (
                    <span key={role.code} className="rounded-full bg-accent-subtle px-2 py-0.5 text-xs text-accent">
                      {role.label} ({role.code}) - {role.count_in_signal}
                    </span>
                  ))}
                </div>
              )}

              {selectedEntity.cluster_entities && selectedEntity.cluster_entities.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-xs font-semibold text-secondary">Outras aparições (mesmo cluster)</p>
                  {selectedEntity.cluster_entities.map((ce) => {
                    const ceColors = CONNECTOR_COLORS[ce.source_connector ?? ""];
                    const ceLabel = CONNECTOR_LABELS[ce.source_connector ?? ""] ?? ce.source_connector;
                    return (
                      <div key={ce.entity_id} className="flex items-center gap-2 rounded bg-surface-base px-2 py-1 text-xs">
                        {ceLabel && (
                          <span className={`inline-flex shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium ${ceColors?.bg ?? "bg-surface-subtle"} ${ceColors?.text ?? "text-secondary"}`}>
                            {ceLabel}
                          </span>
                        )}
                        <span className="text-secondary truncate">{ce.name}</span>
                      </div>
                    );
                  })}
                </div>
              )}

              <Link
                href={`/entity/${selectedEntity.entity_id}`}
                className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
              >
                Ver perfil completo <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          ) : (
            <p className="mt-3 text-xs text-muted">
              Clique em uma entidade na teia para ver detalhes completos.
            </p>
          )}

          <div className="mt-4 rounded-lg border border-border bg-surface-base p-3 text-xs text-secondary">
            Cobertura: {data.diagnostics.events_loaded}/{data.diagnostics.events_total} eventos,
            {" "}
            {data.diagnostics.participants_total} participações, {data.diagnostics.unique_entities} entidades.
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-lg border border-border bg-surface-card p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-display flex items-center gap-2 text-sm font-semibold text-primary">
            <FileText className="h-4 w-4 text-accent" />
            Eventos e evidências ({filteredTimeline.length})
          </h2>
          <label className="text-xs text-secondary">
            Filtrar por papel:
            <select
              className="ml-2 rounded border border-border bg-surface-card px-2 py-1 text-xs"
              value={roleFilter}
              onChange={(event) => setRoleFilter(event.target.value)}
            >
              <option value="all">Todos</option>
              {roleOptions.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="mt-3 space-y-2">
          {filteredTimeline.map((event) => {
            const uf = attrValue(event.attrs?.uf);
            const modalidade = attrValue(event.attrs?.modalidade);
            const situacao = attrValue(event.attrs?.situacao);
            const catmat = attrValue(event.attrs?.catmat_group);
            const displayDescription = cleanDescription(event.description, event.source_connector);
            const cleanSrc = cleanSourceId(event.source_id);

            // Deduplicate participants: group roles by entity
            const participantMap = new Map<string, { name: string; node_type: string; roles: string[] }>();
            for (const p of event.participants) {
              const existing = participantMap.get(p.entity_id);
              if (existing) {
                existing.roles.push(p.role_label);
              } else {
                participantMap.set(p.entity_id, { name: p.name, node_type: p.node_type, roles: [p.role_label] });
              }
            }
            const dedupedParticipants = Array.from(participantMap.entries());

            return (
              <div key={event.event_id} className="rounded-lg border border-border bg-surface-base p-3 space-y-2">
                {/* Header row */}
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
                  <span className="inline-flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" />
                    {event.occurred_at ? formatDate(event.occurred_at) : "Data não informada"}
                  </span>
                  {typeof event.value_brl === "number" && event.value_brl > 0 && (
                    <span className="font-semibold text-primary">{formatBRL(event.value_brl)}</span>
                  )}
                  {uf !== "—" && (
                    <span className="inline-flex items-center gap-1">
                      <MapPin className="h-3 w-3" />{uf}
                    </span>
                  )}
                  {modalidade !== "—" && (
                    <span className="rounded-full bg-surface-card px-2 py-0.5">{modalidade}</span>
                  )}
                  {situacao !== "—" && (
                    <span className="rounded-full bg-surface-card px-2 py-0.5 text-secondary">{situacao}</span>
                  )}
                  {catmat !== "—" && (
                    <span className="inline-flex items-center gap-1 text-muted">
                      <Tag className="h-3 w-3" />CATMAT: {catmat}
                    </span>
                  )}
                </div>

                {/* Description */}
                <p className="text-sm font-medium text-primary leading-snug">{displayDescription}</p>

                {/* Participants (deduped) */}
                {dedupedParticipants.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {dedupedParticipants.map(([entityId, info]) => (
                      <Link
                        key={`${event.event_id}-${entityId}`}
                        href={`/entity/${entityId}`}
                        className="inline-flex items-center gap-1 rounded-full bg-surface-card border border-border px-2 py-0.5 text-xs text-secondary hover:text-accent transition"
                      >
                        <span className="font-medium">{entityDisplayName(info.name, entityId, info.node_type)}</span>
                        <span className="text-muted">· {info.roles.join(", ")}</span>
                      </Link>
                    ))}
                  </div>
                )}

                {/* Source — clean display */}
                <p className="text-[10px] text-muted">
                  Fonte: <span className="font-mono">{event.source_connector}</span>
                  {cleanSrc !== event.source_connector && <> / <span className="font-mono">{cleanSrc}</span></>}
                </p>
              </div>
            );
          })}
          {filteredTimeline.length === 0 && (
            <p className="text-xs text-muted">Nenhum evento para o filtro selecionado.</p>
          )}
        </div>
      </div>

      <div className="mt-6 rounded-lg border border-border bg-surface-base p-3">
        <p className="text-xs text-muted">
          <strong>Aviso legal:</strong> Esta teia representa hipótese investigativa com base em cruzamento automático de dados públicos.
        </p>
      </div>
    </div>
  );
}
