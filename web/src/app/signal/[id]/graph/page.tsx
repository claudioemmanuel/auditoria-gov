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
} from "lucide-react";

function entityTypeLabel(nodeType: string): string {
  if (nodeType === "org") return "Órgão";
  if (nodeType === "company") return "Empresa";
  if (nodeType === "person") return "Pessoa";
  return nodeType;
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
    <div className="mx-auto max-w-6xl px-4 py-8">
      <PageHeader
        title={data.signal.title}
        subtitle={`${data.signal.typology_code} - ${data.signal.typology_name}`}
        breadcrumbs={[
          { label: "Radar", href: "/radar" },
          { label: "Sinal", href: `/signal/${data.signal.id}` },
          { label: "Teia investigativa" },
        ]}
      />

      <div className="mt-4 flex flex-wrap items-end justify-end gap-2">
        <div className="flex items-center gap-2">
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
      </div>

      <div className="mt-6 grid grid-cols-1 gap-3 lg:grid-cols-3">
        <div className="rounded-lg border border-accent/20 bg-accent-subtle p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent">Padrão detectado</p>
          <p className="mt-1 text-sm text-primary">{data.pattern_story.pattern_label}</p>
          <p className="mt-2 text-xs text-accent-hover">{data.pattern_story.why_flagged}</p>
        </div>
        <div className="rounded-lg border border-border bg-surface-card p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-secondary">Começou em</p>
          <p className="mt-1 text-sm font-medium text-primary">
            {data.pattern_story.started_at ? formatDate(data.pattern_story.started_at) : "Data não informada"}
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {data.pattern_story.started_from_entities.map((entity) => (
              <span key={entity.entity_id} className="rounded-full bg-surface-subtle px-2 py-0.5 text-xs text-secondary">
                {entity.name}
              </span>
            ))}
          </div>
        </div>
        <div className="rounded-lg border border-border bg-surface-card p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-secondary">Fluxo observado</p>
          <p className="mt-1 text-sm font-medium text-primary">
            {data.pattern_story.ended_at ? formatDate(data.pattern_story.ended_at) : "Data não informada"}
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {data.pattern_story.flow_targets.map((entity) => (
              <span key={entity.entity_id} className="rounded-full bg-surface-subtle px-2 py-0.5 text-xs text-secondary">
                {entity.name}
              </span>
            ))}
          </div>
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
            <div className="rounded-lg border border-amber/20 bg-amber-subtle p-4">
              <p className="text-sm font-medium text-amber">Teia insuficiente para desenhar conexões</p>
              <p className="mt-1 text-xs text-amber/80">
                Motivo: {data.diagnostics.fallback_reason || "sem detalhes"}.
                Eventos carregados: {data.diagnostics.events_loaded}/{data.diagnostics.events_total}.
              </p>
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
                    alt={`Foto de ${selectedEntity.name}`}
                    className="h-14 w-14 rounded-lg object-cover"
                  />
                ) : (
                  <div className="flex h-14 w-14 items-center justify-center rounded-lg bg-surface-subtle text-xs text-muted">
                    sem foto
                  </div>
                )}
                <div>
                  <p className="text-sm font-semibold text-primary">{selectedEntity.name}</p>
                  <p className="text-xs text-muted">{entityTypeLabel(selectedEntity.node_type)}</p>
                  <p className="mt-1 text-xs text-muted">
                    Participa de {selectedEntity.event_count} evento(s) nesta teia
                  </p>
                </div>
              </div>

              {selectedEntity.is_direct_participant === false && (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-subtle px-2 py-0.5 text-xs text-amber">
                  <Waypoints className="h-3 w-3" />
                  Descoberto via expansão de rede
                </span>
              )}

              {Object.keys(selectedEntity.identifiers).length > 0 && (
                <div className="space-y-1">
                  {Object.entries(selectedEntity.identifiers).map(([key, value]) => (
                    <p key={key} className="rounded bg-surface-base px-2 py-1 text-xs text-secondary">
                      <span className="font-semibold">{key.toUpperCase()}:</span> {value}
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
          {filteredTimeline.map((event) => (
            <div key={event.event_id} className="rounded-lg border border-border bg-surface-base p-3">
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
                <span className="inline-flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5" />
                  {event.occurred_at ? formatDate(event.occurred_at) : "Data não informada"}
                </span>
                {typeof event.value_brl === "number" && (
                  <span>{formatBRL(event.value_brl)}</span>
                )}
                <span>{event.source_connector}/{event.source_id}</span>
              </div>
              <p className="mt-1 text-sm font-medium text-primary">{event.description}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {event.participants.map((participant) => (
                  <span key={`${event.event_id}-${participant.entity_id}-${participant.role}`} className="rounded-full bg-surface-card px-2 py-0.5 text-xs text-secondary">
                    {participant.name} - {participant.role_label} ({participant.role})
                  </span>
                ))}
              </div>
              <p className="mt-2 text-xs text-secondary">
                Porque sustenta a ligação: {event.evidence_reason}
              </p>
            </div>
          ))}
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
