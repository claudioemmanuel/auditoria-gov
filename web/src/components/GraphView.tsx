"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getGraphNeighborhood } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { NeighborhoodResponse, GraphNode, GraphEdge } from "@/lib/types";
import ForceGraph2D from "react-force-graph-2d";

interface GraphViewProps {
  entityId: string;
  height?: number;
  className?: string;
}

interface GNode {
  id: string;
  label: string;
  node_type: string;
  entity_id: string;
  isCenter: boolean;
  x?: number;
  y?: number;
}

const NODE_COLORS: Record<string, string> = {
  person: "#2563eb",
  company: "#059669",
  org: "#7c3aed",
};

const NODE_SIZE: Record<string, number> = {
  person: 5,
  company: 6,
  org: 7,
};

const DIAGNOSTIC_REASON_LABELS: Record<string, string> = {
  no_events_for_entity: "A entidade ainda não possui eventos associados",
  no_coparticipants_or_er_not_run: "Não foram encontrados co-participantes nos eventos analisados",
  er_not_materialized: "O grafo ainda não foi materializado pelo processo de resolução de entidades",
  graph_available: "Grafo materializado",
};

export function GraphView({ entityId, height = 400, className }: GraphViewProps) {
  const [data, setData] = useState<NeighborhoodResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GNode | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 600, height });
  const router = useRouter();

  useEffect(() => {
    setLoading(true);
    setError(null);
    getGraphNeighborhood(entityId)
      .then(setData)
      .catch(() => setError("Erro ao carregar grafo"))
      .finally(() => setLoading(false));
  }, [entityId]);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: entry.contentRect.width,
          height: Math.max(entry.contentRect.height, height),
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [height]);

  const graphData = useMemo(() => {
    if (!data) return { nodes: [] as GNode[], links: [] as { source: string; target: string; type: string; weight: number }[] };

    const nodes: GNode[] = data.nodes.map((n: GraphNode) => ({
      id: n.id,
      label: n.label,
      node_type: n.node_type,
      entity_id: n.entity_id,
      isCenter: n.id === data.center_node_id,
    }));

    const nodeIds = new Set(nodes.map((n) => n.id));
    const links = data.edges
      .filter((e: GraphEdge) => nodeIds.has(e.from_node_id) && nodeIds.has(e.to_node_id))
      .map((e: GraphEdge) => ({
        source: e.from_node_id,
        target: e.to_node_id,
        type: e.type,
        weight: e.weight,
      }));

    return { nodes, links };
  }, [data]);

  const paintNode = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const gNode = node as GNode;
      const r = (NODE_SIZE[gNode.node_type] ?? 5) * (gNode.isCenter ? 1.5 : 1);
      const color = NODE_COLORS[gNode.node_type] ?? "#6b7280";
      const isHovered = hoveredNode?.id === gNode.id;

      // Glow for center node
      if (gNode.isCenter) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, r + 3, 0, 2 * Math.PI);
        ctx.fillStyle = `${color}33`;
        ctx.fill();
      }

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = isHovered ? "#f59e0b" : color;
      ctx.fill();

      if (gNode.isCenter || isHovered) {
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Label
      if (globalScale > 1.2 || gNode.isCenter || isHovered) {
        const label = gNode.label.length > 20 ? gNode.label.slice(0, 20) + "..." : gNode.label;
        const fontSize = Math.max(10 / globalScale, 3);
        ctx.font = `${gNode.isCenter ? "bold " : ""}${fontSize}px system-ui, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = "#374151";
        ctx.fillText(label, node.x, node.y + r + 2);
      }
    },
    [hoveredNode]
  );

  if (loading) {
    return (
      <div
        className={cn("flex items-center justify-center bg-surface-card", className)}
        style={{ height }}
      >
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <span className="text-sm text-secondary">Carregando grafo...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={cn("flex items-center justify-center bg-surface-card", className)}
        style={{ height }}
      >
        <p className="text-sm text-severity-critical">{error}</p>
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    const diagnostics = data?.diagnostics;
    const coParticipants = data?.co_participants || [];
    const reasonLabel = diagnostics
      ? (DIAGNOSTIC_REASON_LABELS[diagnostics.reason] || diagnostics.reason)
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
                Motivo: <strong>{reasonLabel}</strong> <span className="text-muted">({diagnostics.reason})</span>
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

  return (
    <div className={cn("relative", className)} ref={containerRef}>
      {/* Legend */}
      <div className="absolute left-2 top-2 z-10 flex flex-col gap-1 rounded-md bg-surface-card/90 px-3 py-2 text-xs shadow-sm backdrop-blur-sm">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-2">
            <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
            <span className="capitalize text-secondary">
              {type === "person" ? "Pessoa" : type === "company" ? "Empresa" : "Órgão"}
            </span>
          </div>
        ))}
      </div>

      {/* Stats */}
      <div className="absolute right-2 top-2 z-10 rounded-md bg-surface-card/90 px-3 py-2 text-xs text-muted shadow-sm backdrop-blur-sm">
        {data.nodes.length} nós, {data.edges.length} arestas
        {data.truncated && (
          <span className="ml-1 text-severity-medium">(truncado)</span>
        )}
      </div>

      {/* Tooltip */}
      {hoveredNode && (
        <div className="absolute bottom-2 left-2 z-10 rounded-md bg-surface-card px-3 py-2 text-xs shadow-md border border-border">
          <p className="font-semibold text-primary">{hoveredNode.label}</p>
          <p className="capitalize text-secondary">
            {hoveredNode.node_type === "person" ? "Pessoa" : hoveredNode.node_type === "company" ? "Empresa" : "Órgão"}
          </p>
        </div>
      )}

      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        width={dimensions.width}
        height={height}
        nodeCanvasObject={paintNode}
        nodePointerAreaPaint={(node: GNode, color: string, ctx: CanvasRenderingContext2D) => {
          const r = (NODE_SIZE[node.node_type] ?? 5) * (node.isCenter ? 1.5 : 1) + 2;
          ctx.beginPath();
          ctx.arc(node.x!, node.y!, r, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
        linkColor={() => "#d1d5db"}
        linkWidth={(link: { weight: number }) => Math.max(1, link.weight * 2)}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        onNodeHover={(node: GNode | null) => setHoveredNode(node)}
        onNodeClick={(node: GNode) => {
          if (node.entity_id) {
            router.push(`/entity/${node.entity_id}`);
          }
        }}
        cooldownTicks={80}
        enableZoomInteraction={true}
        enablePanInteraction={true}
      />
    </div>
  );
}
