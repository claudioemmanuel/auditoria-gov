"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type Node,
  type Edge,
  type NodeProps,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import ELK from "elkjs/lib/elk.bundled.js";
import type { ElkNode } from "elkjs";
import { getGraphNeighborhood } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { NeighborhoodResponse, GraphEdge } from "@/lib/types";

// ─── Constants ───────────────────────────────────────────────────────────────

const NODE_COLORS: Record<string, string> = {
  person:  "#2563eb",
  company: "#059669",
  org:     "#7c3aed",
};

const NODE_TYPE_LABELS: Record<string, string> = {
  person:  "Pessoa",
  company: "Empresa",
  org:     "Órgão",
};

const EDGE_COLORS: Record<string, string> = {
  compra_fornecimento:         "#3b82f6",
  agente_publico_favorecido:   "#ef4444",
  coparticipacao_evento:       "#6b7280",
  coparticipacao_fornecedores: "#9ca3af",
  coparticipacao_orgaos:       "#a78bfa",
  sociedade:                   "#10b981",
  SAME_SOCIO:                  "#f59e0b",
  SAME_ADDRESS:                "#94a3b8",
  SHARES_PHONE:                "#64748b",
  SAME_ACCOUNTANT:             "#94a3b8",
  SUBSIDIARY:                  "#8b5cf6",
  HOLDING:                     "#8b5cf6",
  same_cluster_entity:         "#f43f5e",
};

const EDGE_TYPE_LABELS: Record<string, string> = {
  compra_fornecimento:         "fornecimento",
  agente_publico_favorecido:   "favorecido",
  coparticipacao_evento:       "co-participação",
  coparticipacao_fornecedores: "co-fornecedor",
  coparticipacao_orgaos:       "co-órgão",
  sociedade:                   "sócio",
  SAME_SOCIO:                  "mesmo sócio",
  SAME_ADDRESS:                "mesmo endereço",
  SHARES_PHONE:                "mesmo telefone",
  SAME_ACCOUNTANT:             "mesmo contador",
  SUBSIDIARY:                  "subsidiária",
  HOLDING:                     "holding",
  same_cluster_entity:         "mesma entidade",
};

const DIAGNOSTIC_REASON_LABELS: Record<string, string> = {
  no_events_for_entity:           "A entidade ainda não possui eventos associados",
  no_coparticipants_or_er_not_run:"Não foram encontrados co-participantes nos eventos analisados",
  er_not_materialized:            "O grafo ainda não foi materializado pelo processo de resolução de entidades",
  graph_available:                "Grafo materializado",
};

const NODE_W = 200;
const NODE_H = 68;

// ─── ELK layout ──────────────────────────────────────────────────────────────

const elk = new ELK();

async function computeLayout(nodes: Node[], edges: Edge[]): Promise<Node[]> {
  const graph: ElkNode = {
    id: "root",
    layoutOptions: {
      "elk.algorithm":                               "layered",
      "elk.direction":                               "UNDEFINED",
      "elk.spacing.nodeNode":                        "60",
      "elk.layered.spacing.nodeNodeBetweenLayers":   "90",
      "elk.layered.crossingMinimization.strategy":   "LAYER_SWEEP",
      "elk.layered.nodePlacement.strategy":          "BRANDES_KOEPF",
    },
    children: nodes.map((n) => ({ id: n.id, width: NODE_W, height: NODE_H })),
    edges: edges.map((e) => ({ id: e.id, sources: [e.source], targets: [e.target] })),
  };
  const laid = await elk.layout(graph);
  return nodes.map((n) => {
    const c = laid.children?.find((ch) => ch.id === n.id);
    return { ...n, position: { x: c?.x ?? 0, y: c?.y ?? 0 } };
  });
}

// ─── Custom entity node ───────────────────────────────────────────────────────

type EntityNodeData = {
  label: string;
  node_type: string;
  entity_id: string;
  isCenter: boolean;
};

function EntityNode({ data }: NodeProps) {
  const router = useRouter();
  const d = data as EntityNodeData;
  const color = NODE_COLORS[d.node_type] ?? "#6b7280";

  return (
    <div
      className={cn(
        "bg-surface-card rounded-lg shadow-sm overflow-hidden border transition-all select-none",
        d.isCenter
          ? "border-2 shadow-md"
          : "border-border cursor-pointer hover:shadow-md hover:border-accent/40",
      )}
      style={{
        width: NODE_W,
        ...(d.isCenter ? { borderColor: color, boxShadow: `0 0 0 3px ${color}22` } : {}),
      }}
      onClick={() => {
        if (!d.isCenter && d.entity_id) router.push(`/entity/${d.entity_id}`);
      }}
    >
      {/* Colored top strip */}
      <div className="h-1 w-full" style={{ backgroundColor: color }} />

      <Handle
        type="target"
        position={Position.Left}
        style={{ background: "#4b5563", width: 8, height: 8, border: "none" }}
      />

      <div className="px-3 py-2">
        <div className="flex items-center justify-between gap-1">
          <span className="text-[10px] font-semibold leading-none" style={{ color }}>
            {NODE_TYPE_LABELS[d.node_type] ?? d.node_type}
          </span>
          {d.isCenter && (
            <span
              className="rounded-full px-1.5 py-0.5 text-[8px] font-bold tracking-wide uppercase"
              style={{ backgroundColor: `${color}22`, color }}
            >
              central
            </span>
          )}
        </div>
        <p className="mt-1 text-[12px] font-semibold text-primary leading-snug line-clamp-2">
          {d.label}
        </p>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        style={{ background: "#4b5563", width: 8, height: 8, border: "none" }}
      />
    </div>
  );
}

const nodeTypes = { entity: EntityNode };

// ─── Inner flow (must be inside ReactFlowProvider) ────────────────────────────

interface FlowInnerProps {
  rfNodes: Node[];
  rfEdges: Edge[];
}

function FlowInner({ rfNodes, rfEdges }: FlowInnerProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, , onEdgesChange] = useEdgesState<Edge>([]);
  const { fitView } = useReactFlow();

  useEffect(() => {
    if (!rfNodes.length) return;
    computeLayout(rfNodes, rfEdges).then((laid) => {
      setNodes(laid);
      requestAnimationFrame(() => fitView({ padding: 0.14, duration: 400 }));
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rfNodes, rfEdges]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      proOptions={{ hideAttribution: true }}
      minZoom={0.08}
      maxZoom={3}
      nodesDraggable
      className="bg-surface-base"
    >
      <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#334155" />
      <Controls className="[&>button]:!bg-surface-card [&>button]:!border-border [&>button]:!text-secondary [&>button:hover]:!text-primary [&>button]:!shadow-none" />
      <MiniMap
        nodeColor={(n) => NODE_COLORS[(n.data as EntityNodeData).node_type] ?? "#6b7280"}
        maskColor="rgba(0,0,0,0.35)"
        className="!bg-surface-card !border !border-border !rounded-lg !shadow-sm"
      />
    </ReactFlow>
  );
}

// ─── Public component ─────────────────────────────────────────────────────────

interface GraphViewProps {
  entityId: string;
  height?: number;
  className?: string;
}

export function GraphView({ entityId, height = 480, className }: GraphViewProps) {
  const [data, setData] = useState<NeighborhoodResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    setLoading(true);
    setError(null);
    getGraphNeighborhood(entityId)
      .then(setData)
      .catch(() => setError("Erro ao carregar grafo"))
      .finally(() => setLoading(false));
  }, [entityId]);

  const { rfNodes, rfEdges } = useMemo(() => {
    if (!data?.nodes.length) return { rfNodes: [], rfEdges: [] };

    const uniqueNodes = Array.from(new Map(data.nodes.map((n) => [n.id, n])).values());
    const nodeIds = new Set(uniqueNodes.map((n) => n.id));

    const rfNodes: Node[] = uniqueNodes.map((n) => ({
      id: n.id,
      type: "entity",
      position: { x: 0, y: 0 },
      data: {
        label: n.label,
        node_type: n.node_type,
        entity_id: n.entity_id,
        isCenter: n.id === data.center_node_id,
      },
    }));

    const rfEdges: Edge[] = data.edges
      .filter((e: GraphEdge) => nodeIds.has(e.from_node_id) && nodeIds.has(e.to_node_id))
      .map((e: GraphEdge) => ({
        id: e.id,
        source: e.from_node_id,
        target: e.to_node_id,
        type: "smoothstep",
        style: {
          stroke: EDGE_COLORS[e.type] ?? "#6b7280",
          strokeWidth: e.edge_strength === "strong" ? 2 : 1,
          strokeDasharray: e.edge_strength === "strong" ? undefined : "5 3",
        },
        label: EDGE_TYPE_LABELS[e.type] ?? e.type,
        labelStyle: { fontSize: 9, fill: "#94a3b8", fontFamily: "system-ui, sans-serif" },
        labelBgStyle: { fill: "#0f172a", fillOpacity: 0.85 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 3,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: EDGE_COLORS[e.type] ?? "#6b7280",
          width: 14,
          height: 14,
        },
      }));

    return { rfNodes, rfEdges };
  }, [data]);

  // ── Loading ──
  if (loading) {
    return (
      <div className={cn("flex items-center justify-center bg-surface-card", className)} style={{ height }}>
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <span className="text-sm text-secondary">Carregando grafo...</span>
        </div>
      </div>
    );
  }

  // ── Error ──
  if (error) {
    return (
      <div className={cn("flex items-center justify-center bg-surface-card", className)} style={{ height }}>
        <p className="text-sm text-severity-critical">{error}</p>
      </div>
    );
  }

  // ── Empty / no graph ──
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
            <div className="mt-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-surface-card">
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

  // ── Graph ──
  return (
    <div className={cn("relative overflow-hidden rounded-lg border border-border", className)} style={{ height }}>
      {/* Stats overlay */}
      <div className="absolute right-2 top-2 z-10 rounded-md bg-surface-card/90 px-2.5 py-1.5 text-[11px] text-muted shadow-sm backdrop-blur-sm">
        {data.nodes.length} nós · {data.edges.length} arestas
        {data.truncated && <span className="ml-1 text-severity-medium">(truncado)</span>}
      </div>

      <ReactFlowProvider>
        <FlowInner rfNodes={rfNodes} rfEdges={rfEdges} />
      </ReactFlowProvider>
    </div>
  );
}
