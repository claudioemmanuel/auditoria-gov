"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getGraphNeighborhood } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { NeighborhoodResponse, GraphNode, GraphEdge } from "@/lib/types";

interface EntityNetworkGraphProps {
  entityId: string;
  className?: string;
}

const NODE_COLORS: Record<string, string> = {
  person: "#3b82f6",
  company: "#10b981",
  org: "#8b5cf6",
};

const NODE_TYPE_LABELS: Record<string, string> = {
  person: "Pessoa",
  company: "Empresa",
  org: "Órgão",
};

const DIAGNOSTIC_REASON_LABELS: Record<string, string> = {
  no_events_for_entity: "A entidade ainda não possui eventos associados",
  no_coparticipants_or_er_not_run: "Não foram encontrados co-participantes nos eventos analisados",
  er_not_materialized: "O grafo ainda não foi materializado pelo processo de resolução de entidades",
  graph_available: "Grafo materializado",
};

const CX = 280;
const CY = 210;
const OUTER_RADIUS = 160;
const INNER_RADIUS = 100;
const CENTER_R = 26;
const PERIPHERAL_R = 15;
const MAX_OUTER = 12;
const LABEL_MAX = 18;
const CENTER_LABEL_MAX = 20;

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + "…" : s;
}

function radialPos(index: number, total: number, radius: number): { x: number; y: number } {
  const angle = (2 * Math.PI * index) / total - Math.PI / 2;
  return {
    x: CX + radius * Math.cos(angle),
    y: CY + radius * Math.sin(angle),
  };
}

interface NodePosition {
  node: GraphNode;
  x: number;
  y: number;
  isCenter: boolean;
}

export function EntityNetworkGraph({ entityId, className }: EntityNetworkGraphProps) {
  const [data, setData] = useState<NeighborhoodResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    setLoading(true);
    setError(null);
    setData(null);
    getGraphNeighborhood(entityId)
      .then(setData)
      .catch(() => setError("Erro ao carregar grafo"))
      .finally(() => setLoading(false));
  }, [entityId]);

  if (loading) {
    return (
      <div className={cn("flex items-center justify-center bg-surface-card", className)} style={{ height: 420 }}>
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <span className="text-sm text-secondary">Carregando grafo...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("flex items-center justify-center bg-surface-card", className)} style={{ height: 420 }}>
        <p className="text-sm text-severity-critical">{error}</p>
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    const diagnostics = data?.diagnostics;
    const coParticipants = data?.co_participants ?? [];
    const reasonLabel = diagnostics
      ? (DIAGNOSTIC_REASON_LABELS[diagnostics.reason] ?? diagnostics.reason)
      : "Sem diagnóstico disponível";

    return (
      <div className={cn("p-4 bg-surface-card", className)}>
        <div className="rounded-lg border border-border bg-surface-subtle p-4">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-10 w-10 items-center justify-center rounded-full bg-surface-card">
              <svg className="h-5 w-5 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m9.86-4.568a4.5 4.5 0 00-6.364-6.364L4.5 8.78" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-primary">
                Nenhuma conexão materializada para esta entidade
              </p>
              <p className="mt-1 text-xs text-secondary">
                Isso pode ocorrer quando o processo de resolução de entidades/arestas ainda não foi executado
                ou quando os eventos não possuem co-participantes suficientes.
              </p>
            </div>
          </div>
          {diagnostics && (
            <div className="mt-3 grid grid-cols-1 gap-2 text-xs sm:grid-cols-3">
              <div className="rounded bg-surface-card px-2 py-1.5 text-secondary">
                Eventos da entidade: <strong>{diagnostics.entity_event_count}</strong>
              </div>
              <div className="rounded bg-surface-card px-2 py-1.5 text-secondary">
                Co-participantes: <strong>{diagnostics.co_participant_count}</strong>
              </div>
              <div className="rounded bg-surface-card px-2 py-1.5 text-secondary">
                Motivo: <strong>{reasonLabel}</strong>{" "}
                <span className="text-muted">({diagnostics.reason})</span>
              </div>
            </div>
          )}
          {data?.virtual_center_node && (
            <p className="mt-2 text-xs text-secondary">
              Entidade central: <strong>{data.virtual_center_node.label}</strong> ({data.virtual_center_node.node_type})
            </p>
          )}
          {coParticipants.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-semibold text-primary">Co-participantes identificados</p>
              <div className="mt-1 overflow-x-auto">
                <table className="min-w-full text-left text-xs">
                  <thead>
                    <tr className="text-muted">
                      <th className="py-1 pr-3">Entidade</th>
                      <th className="py-1 pr-3">Tipo</th>
                      <th className="py-1">Eventos em comum</th>
                    </tr>
                  </thead>
                  <tbody>
                    {coParticipants.map((cp) => (
                      <tr
                        key={cp.entity_id}
                        className="cursor-pointer border-t border-border text-secondary hover:bg-surface-base"
                        onClick={() => router.push(`/entity/${cp.entity_id}`)}
                      >
                        <td className="py-1 pr-3">{cp.label}</td>
                        <td className="py-1 pr-3 capitalize">{cp.node_type}</td>
                        <td className="py-1">{cp.shared_events}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Build positions
  const centerNode = data.nodes.find((n) => n.id === data.center_node_id) ?? data.nodes[0]!;
  const peripheralNodes = data.nodes.filter((n) => n.id !== data.center_node_id);
  const outerNodes = peripheralNodes.slice(0, MAX_OUTER);
  const innerNodes = peripheralNodes.slice(MAX_OUTER);

  const positions: NodePosition[] = [
    { node: centerNode, x: CX, y: CY, isCenter: true },
    ...outerNodes.map((n, i) => ({
      node: n,
      ...radialPos(i, outerNodes.length, OUTER_RADIUS),
      isCenter: false,
    })),
    ...innerNodes.map((n, i) => ({
      node: n,
      ...radialPos(i, innerNodes.length, INNER_RADIUS),
      isCenter: false,
    })),
  ];

  const posMap = new Map(positions.map((p) => [p.node.id, p]));

  // Edges: center-to-peripheral and cross-edges
  const nodeIdSet = new Set(positions.map((p) => p.node.id));
  const validEdges = data.edges.filter(
    (e: GraphEdge) => nodeIdSet.has(e.from_node_id) && nodeIdSet.has(e.to_node_id)
  );

  const centerEdges = validEdges.filter(
    (e) => e.from_node_id === centerNode.id || e.to_node_id === centerNode.id
  );
  const crossEdges = validEdges.filter(
    (e) => e.from_node_id !== centerNode.id && e.to_node_id !== centerNode.id
  );

  const hoveredPos = hoveredId ? posMap.get(hoveredId) : undefined;

  return (
    <div className={cn("relative bg-surface-card", className)}>
      {/* Legend */}
      <div className="absolute left-2 top-2 z-10 flex flex-col gap-1 rounded-md bg-surface-card/90 px-3 py-2 text-xs shadow-sm backdrop-blur-sm">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-2">
            <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-secondary">{NODE_TYPE_LABELS[type] ?? type}</span>
          </div>
        ))}
      </div>

      {/* Stats */}
      <div className="absolute right-2 top-2 z-10 rounded-md bg-surface-card/90 px-3 py-2 text-xs text-muted shadow-sm backdrop-blur-sm">
        {data.nodes.length} nós, {data.edges.length} arestas
        {data.truncated && <span className="ml-1 text-severity-medium">(truncado)</span>}
      </div>

      {/* Tooltip */}
      {hoveredPos && (
        <div className="absolute bottom-2 left-2 z-10 rounded-md bg-surface-card px-3 py-2 text-xs shadow-md border border-border pointer-events-none">
          <p className="font-semibold text-primary">{hoveredPos.node.label}</p>
          <p className="text-secondary capitalize">
            {NODE_TYPE_LABELS[hoveredPos.node.node_type] ?? hoveredPos.node.node_type}
          </p>
          {!hoveredPos.isCenter && (
            <p className="mt-0.5 text-muted">Clique para navegar →</p>
          )}
        </div>
      )}

      <svg
        viewBox="0 0 560 420"
        className="w-full"
        style={{ display: "block" }}
      >
        {/* Cross-edges (dashed) */}
        {crossEdges.map((e: GraphEdge) => {
          const from = posMap.get(e.from_node_id);
          const to = posMap.get(e.to_node_id);
          if (!from || !to) return null;
          return (
            <line
              key={e.id}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke="#6b7280"
              strokeOpacity={0.3}
              strokeWidth={1}
              strokeDasharray="4 3"
            />
          );
        })}

        {/* Center edges */}
        {centerEdges.map((e: GraphEdge) => {
          const fromP = posMap.get(e.from_node_id);
          const toP = posMap.get(e.to_node_id);
          if (!fromP || !toP) return null;
          return (
            <line
              key={e.id}
              x1={fromP.x}
              y1={fromP.y}
              x2={toP.x}
              y2={toP.y}
              stroke="#4b5563"
              strokeOpacity={0.5}
              strokeWidth={1.5}
            />
          );
        })}

        {/* Nodes */}
        {positions.map((p) => {
          const color = NODE_COLORS[p.node.node_type] ?? "#6b7280";
          const r = p.isCenter ? CENTER_R : PERIPHERAL_R;
          const isHovered = hoveredId === p.node.id;
          const fillOpacity = isHovered ? 1 : 0.85;
          const label = truncate(p.node.label, p.isCenter ? CENTER_LABEL_MAX : LABEL_MAX);

          return (
            <g
              key={p.node.id}
              style={{ cursor: p.isCenter ? "default" : "pointer" }}
              onMouseEnter={() => setHoveredId(p.node.id)}
              onMouseLeave={() => setHoveredId(null)}
              onClick={() => {
                if (!p.isCenter) {
                  router.push(`/entity/${p.node.entity_id}`);
                }
              }}
            >
              {/* Glow ring for center node */}
              {p.isCenter && (
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={r + 8}
                  fill={color}
                  fillOpacity={0.15}
                />
              )}

              {/* Node circle */}
              <circle
                cx={p.x}
                cy={p.y}
                r={r}
                fill={color}
                fillOpacity={fillOpacity}
                stroke={p.isCenter ? "#ffffff" : isHovered ? "#ffffff" : "none"}
                strokeWidth={p.isCenter ? 2 : 1.5}
              />

              {/* Label */}
              <text
                x={p.x}
                y={p.y + r + 11}
                textAnchor="middle"
                fontSize={9}
                fill="#94a3b8"
                fontWeight={p.isCenter ? "bold" : "normal"}
              >
                {label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
