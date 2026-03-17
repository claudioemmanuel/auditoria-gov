"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type Node,
  type Edge,
  BackgroundVariant,
  Panel,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { EntityNode, type EntityNodeData } from "./EntityNode";
import { RelationEdge } from "./RelationEdge";
import { useElkLayout } from "./useElkLayout";
import type { GNode, GLink } from "@/hooks/useCaseGraph";
import type { SignalSeverity } from "@/lib/types";
import { tokens } from "@/lib/design-tokens";

const NODE_TYPES = { entity: EntityNode };
const EDGE_TYPES = { relation: RelationEdge };

const MINIMAP_NODE_COLOR: Record<string, string> = {
  person: "#3b82f6",
  company: "#059669",
  org: "#7c3aed",
};

interface InvestigationCanvasProps {
  graphData: { nodes: GNode[]; links: GLink[] };
  degreeMap: Record<string, number>;
  entitySeverityMap: Record<string, SignalSeverity>;
  nodeAttrsMap: Record<string, Record<string, unknown>>;
  selectedNodeId: string | null;
  onNodeClick: (node: GNode) => void;
  onBackgroundClick: () => void;
  onClearSelected: () => void;
  onExpandSelected: () => void;
  /** Optional ref that will be populated with the fitView function once the canvas mounts */
  fitViewRef?: React.MutableRefObject<(() => void) | null>;
  /** Called once ELK layout finishes and nodes are positioned */
  onLayoutDone?: () => void;
}

const DEFAULT_EDGE_OPTIONS = { type: "relation" as const };

function getIdentifier(attrs: Record<string, unknown>): string | undefined {
  if (typeof attrs.cnpj === "string") return attrs.cnpj;
  if (typeof attrs.cpf === "string") return attrs.cpf;
  if (typeof attrs.uasg === "string") return `UASG ${attrs.uasg}`;
  return undefined;
}

function InvestigationCanvasInner({
  graphData,
  degreeMap,
  entitySeverityMap,
  nodeAttrsMap,
  selectedNodeId,
  onNodeClick,
  onBackgroundClick,
  onClearSelected,
  onExpandSelected,
  fitViewRef,
  onLayoutDone,
}: InvestigationCanvasProps) {
  const { computeLayout } = useElkLayout();
  const { fitView } = useReactFlow();

  // Expose fitView to parent via ref
  useEffect(() => {
    if (fitViewRef) {
      fitViewRef.current = () => fitView({ padding: 0.2, maxZoom: 1.2, duration: 400 });
    }
    return () => {
      if (fitViewRef) fitViewRef.current = null;
    };
  }, [fitView, fitViewRef]);
  const [layoutReady, setLayoutReady] = useState(false);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Track which node IDs we already laid out to avoid re-running ELK
  const laidOutIdsRef = useRef<string>("");

  // Build React Flow data from graph data
  const rfNodes: Node[] = useMemo(
    () =>
      graphData.nodes.map((gn) => ({
        id: gn.id,
        type: "entity",
        position: { x: 0, y: 0 },
        data: {
          label: gn.label,
          nodeType: gn.node_type,
          entityId: gn.entity_id,
          isSeed: gn.isSeed,
          isFocused: gn.isFocused,
          isExpanded: gn.isExpanded,
          sourceConnector: gn.sourceConnector,
          severity: entitySeverityMap[gn.entity_id],
          identifier: getIdentifier(nodeAttrsMap[gn.id] ?? {}),
          connectionCount: degreeMap[gn.id] ?? 0,
        } satisfies EntityNodeData,
      })),
    [graphData.nodes, entitySeverityMap, nodeAttrsMap, degreeMap],
  );

  const rfEdges: Edge[] = useMemo(
    () =>
      graphData.links.map((link, i) => ({
        id: link.id || `edge-${i}`,
        source: link.source,
        target: link.target,
        type: "relation",
        data: {
          type: link.type,
          weight: link.weight,
          isFocused: link.isFocused,
          isExpansion: link.isExpansion,
          edge_strength: link.edge_strength,
          verification_method: link.verification_method,
          verification_confidence: link.verification_confidence,
          context: link.context,
        },
        animated: link.type === "socio_oculto",
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 12,
          height: 12,
          color: "#94a3b8",
        },
      })),
    [graphData.links],
  );

  // Run ELK layout ONLY when the set of node IDs changes (initial load or expansion)
  useEffect(() => {
    if (rfNodes.length === 0) return;

    const nodeIdKey = rfNodes.map((n) => n.id).sort().join(",");
    if (nodeIdKey === laidOutIdsRef.current) {
      // Node set didn't change — just update data in place (no layout recompute)
      setNodes((prev) =>
        prev.map((existing) => {
          const updated = rfNodes.find((n) => n.id === existing.id);
          if (!updated) return existing;
          return { ...existing, data: updated.data };
        }),
      );
      setEdges(rfEdges);
      return;
    }

    // New nodes appeared — run layout
    laidOutIdsRef.current = nodeIdKey;
    setLayoutReady(false);
    computeLayout(rfNodes, rfEdges).then(({ nodes: ln, edges: le }) => {
      setNodes(ln);
      setEdges(le);
      setLayoutReady(true);
      onLayoutDone?.();
    });
  }, [rfNodes, rfEdges, computeLayout, setNodes, setEdges, onLayoutDone]);

  // Selection: update selected flag without replacing objects / triggering fitView
  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) =>
        n.selected === (n.id === selectedNodeId)
          ? n
          : { ...n, selected: n.id === selectedNodeId },
      ),
    );
    setEdges((eds) =>
      eds.map((e) => {
        const shouldSelect = selectedNodeId
          ? e.source === selectedNodeId || e.target === selectedNodeId
          : false;
        return e.selected === shouldSelect ? e : { ...e, selected: shouldSelect };
      }),
    );
  }, [selectedNodeId, setNodes, setEdges]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't fire when typing in inputs
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;

      if (e.code === "Space") {
        e.preventDefault();
        fitView({ padding: 0.2, maxZoom: 1.2, duration: 400 });
      } else if (e.key === "f" || e.key === "F") {
        fitView({ padding: 0.2, maxZoom: 1.2, duration: 400 });
      } else if (e.key === "Escape") {
        onClearSelected();
      } else if (e.key === "e" || e.key === "E") {
        if (selectedNodeId) {
          onExpandSelected();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [fitView, onClearSelected, onExpandSelected, selectedNodeId]);

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const gNode = graphData.nodes.find((n) => n.id === node.id);
      if (gNode) onNodeClick(gNode);
    },
    [graphData.nodes, onNodeClick],
  );

  const handlePaneClick = useCallback(() => {
    onBackgroundClick();
  }, [onBackgroundClick]);

  if (!layoutReady && rfNodes.length > 0) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-surface-subtle">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <span className="text-xs text-muted">Calculando layout...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="absolute inset-0">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        nodeTypes={NODE_TYPES}
        edgeTypes={EDGE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.2, maxZoom: 1.2 }}
        minZoom={0.1}
        maxZoom={3}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={true}
        nodesConnectable={false}
        defaultEdgeOptions={DEFAULT_EDGE_OPTIONS}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={0.8}
          color={tokens.border}
        />

        <Controls
          showInteractive={false}
          className="!bg-surface-card !border-border !shadow-md [&>button]:!bg-surface-card [&>button]:!border-border [&>button]:!text-secondary [&>button:hover]:!bg-surface-subtle"
        />

        <MiniMap
          nodeColor={(node) =>
            MINIMAP_NODE_COLOR[(node.data as EntityNodeData).nodeType] ?? tokens.text.muted
          }
          maskColor="rgba(247,248,252,0.75)"
          className="!bg-surface-card !border-border !shadow-md"
          pannable
          zoomable
        />

        {/* Custom SVG arrow markers */}
        <Panel position="top-left" className="!m-0 !p-0">
          <svg width="0" height="0">
            <defs>
              <marker
                id="arrow-default"
                viewBox="0 0 12 12"
                refX="10"
                refY="6"
                markerWidth="12"
                markerHeight="12"
                orient="auto-start-reverse"
              >
                <path d="M 2 2 L 10 6 L 2 10 z" fill="#94a3b8" />
              </marker>
              <marker
                id="arrow-selected"
                viewBox="0 0 12 12"
                refX="10"
                refY="6"
                markerWidth="12"
                markerHeight="12"
                orient="auto-start-reverse"
              >
                <path d="M 2 2 L 10 6 L 2 10 z" fill={tokens.accent} />
              </marker>
            </defs>
          </svg>
        </Panel>
      </ReactFlow>
    </div>
  );
}

export function InvestigationCanvas(props: InvestigationCanvasProps) {
  return (
    <ReactFlowProvider>
      <InvestigationCanvasInner {...props} />
    </ReactFlowProvider>
  );
}
