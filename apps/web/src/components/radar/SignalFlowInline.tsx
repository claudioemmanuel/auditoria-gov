"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, CircleDashed, Loader2, AlertTriangle } from "lucide-react";
import { getSignalGraph } from "@/lib/api";
import type { SignalGraphResponse, SignalSeverity } from "@/lib/types";
import type { GNode, GLink } from "@/hooks/useCaseGraph";
import { InvestigationCanvas } from "@/components/investigation/InvestigationCanvas";

// ── Graph data transform (mirrors graph/page.tsx) ─────────────────────────────
function buildGraphData(data: SignalGraphResponse): { nodes: GNode[]; links: GLink[] } {
  const starterIds = new Set(
    data.pattern_story.started_from_entities.map((e) => e.entity_id),
  );

  const directNodes: GNode[] = data.overview.nodes.map((node) => ({
    id: node.id,
    label: node.label,
    node_type: node.node_type,
    entity_id: node.entity_id,
    isSeed: starterIds.has(node.entity_id),
    isFocused: false,
  }));

  const bfsNodes: GNode[] = (data.overview.expanded_nodes ?? []).map((node) => ({
    id: node.id,
    label: node.label,
    node_type: node.node_type,
    entity_id: node.entity_id,
    isSeed: false,
    isFocused: false,
    isExpanded: true,
    sourceConnector: node.source_connector ?? undefined,
  }));

  const allNodes = [...directNodes, ...bfsNodes];
  const entityToNodeId: Record<string, string> = {};
  for (const node of allNodes) entityToNodeId[node.entity_id] = node.id;

  const directLinks: GLink[] = data.overview.edges.map((edge) => ({
    id: edge.id,
    source: edge.from_node_id,
    target: edge.to_node_id,
    type: edge.type,
    weight: edge.weight,
    isFocused: false,
  }));

  const bfsLinks: GLink[] = (data.overview.expansion_edges ?? [])
    .map((edge) => ({
      id: edge.id,
      source: entityToNodeId[edge.from_entity_id] ?? "",
      target: entityToNodeId[edge.to_entity_id] ?? "",
      type: edge.edge_type,
      weight: edge.weight,
      isFocused: false,
      isExpansion: true,
    }))
    .filter((l) => l.source && l.target);

  return { nodes: allNodes, links: [...directLinks, ...bfsLinks] };
}

// ── Loading step definitions ───────────────────────────────────────────────────
type StepState = "waiting" | "active" | "done";

const STEPS = [
  { label: "Buscando sinal e relações", detail: "Conectando à base de dados" },
  { label: "Identificando entidades", detail: "Mapeando participantes e vínculos" },
  { label: "Calculando layout da teia", detail: "Algoritmo de posicionamento ELK" },
  { label: "Renderizando visualização", detail: "Grafo interativo pronto" },
] as const;

function StepItem({ label, detail, state }: { label: string; detail: string; state: StepState }) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 shrink-0">
        {state === "done" && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
        {state === "active" && <Loader2 className="h-4 w-4 text-accent animate-spin" />}
        {state === "waiting" && <CircleDashed className="h-4 w-4 text-muted/40" />}
      </div>
      <div>
        <p className={`text-sm font-medium ${state === "waiting" ? "text-muted/50" : "text-primary"}`}>
          {label}
        </p>
        {state !== "waiting" && (
          <p className="text-xs text-muted mt-0.5">{detail}</p>
        )}
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
interface SignalFlowInlineProps {
  signalId: string;
}

export function SignalFlowInline({ signalId }: SignalFlowInlineProps) {
  const [stepStates, setStepStates] = useState<StepState[]>(["active", "waiting", "waiting", "waiting"]);
  const [graphData, setGraphData] = useState<{ nodes: GNode[]; links: GLink[] } | null>(null);
  const [entitySeverityMap, setEntitySeverityMap] = useState<Record<string, SignalSeverity>>({});
  const [degreeMap, setDegreeMap] = useState<Record<string, number>>({});
  const [nodeAttrsMap, setNodeAttrsMap] = useState<Record<string, Record<string, unknown>>>({});
  const [canvasVisible, setCanvasVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setStep = useCallback((active: number) => {
    setStepStates((prev) =>
      prev.map((_, i) => {
        if (i < active) return "done";
        if (i === active) return "active";
        return "waiting";
      }),
    );
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        // Step 0: fetch API
        const response = await getSignalGraph(signalId);
        if (cancelled) return;

        // Step 1: process entities (brief visual beat)
        setStep(1);
        await new Promise((r) => setTimeout(r, 350));
        if (cancelled) return;

        const gd = buildGraphData(response);

        // Build derived maps
        const sev: Record<string, SignalSeverity> = {};
        for (const node of response.overview.nodes) sev[node.entity_id] = response.signal.severity;
        const deg: Record<string, number> = {};
        for (const edge of gd.links) {
          deg[edge.source] = (deg[edge.source] ?? 0) + 1;
          deg[edge.target] = (deg[edge.target] ?? 0) + 1;
        }
        const attrs: Record<string, Record<string, unknown>> = {};
        for (const entity of response.involved_entities ?? []) {
          const node = response.overview.nodes.find((n) => n.entity_id === entity.entity_id);
          if (node) attrs[node.id] = entity.identifiers ?? {};
        }

        setEntitySeverityMap(sev);
        setDegreeMap(deg);
        setNodeAttrsMap(attrs);
        setGraphData(gd);

        // Step 2: ELK layout starts (canvas mounts, hidden)
        setStep(2);
      } catch {
        if (!cancelled) setError("Não foi possível carregar a teia de conexões.");
      }
    }

    load();
    return () => { cancelled = true; };
  }, [signalId, setStep]);

  const handleLayoutDone = useCallback(() => {
    // Step 3: layout done → fade in canvas
    setStepStates(["done", "done", "done", "active"]);
    setTimeout(() => {
      setStepStates(["done", "done", "done", "done"]);
      setCanvasVisible(true);
    }, 400);
  }, []);

  const fitViewRef = useRef<(() => void) | null>(null);

  const isLoading = !canvasVisible && !error;

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Progressive loader */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center gap-6 py-8">
          {/* Steps list */}
          <div className="w-full max-w-sm space-y-4">
            {STEPS.map((step, i) => (
              <StepItem
                key={step.label}
                label={step.label}
                detail={step.detail}
                state={stepStates[i] ?? "waiting"}
              />
            ))}
          </div>

          {/* Progress bar */}
          <div className="w-full max-w-sm h-1 rounded-full bg-surface-subtle overflow-hidden">
            <div
              className="h-full rounded-full bg-accent transition-all duration-500"
              style={{
                width: `${(stepStates.filter((s) => s === "done").length / STEPS.length) * 100}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-error/20 bg-error/5 p-4">
          <AlertTriangle className="h-4 w-4 text-error shrink-0" />
          <p className="text-sm text-error">{error}</p>
        </div>
      )}

      {/* Canvas — mounted as soon as graphData is ready (hidden until layout done) */}
      {graphData && (
        <div
          className="rounded-lg overflow-hidden transition-opacity duration-500"
          style={{
            height: 480,
            opacity: canvasVisible ? 1 : 0,
            pointerEvents: canvasVisible ? "auto" : "none",
          }}
        >
          <InvestigationCanvas
            graphData={graphData}
            degreeMap={degreeMap}
            entitySeverityMap={entitySeverityMap}
            nodeAttrsMap={nodeAttrsMap}
            selectedNodeId={null}
            onNodeClick={() => {}}
            onBackgroundClick={() => {}}
            onClearSelected={() => {}}
            onExpandSelected={() => {}}
            fitViewRef={fitViewRef}
            onLayoutDone={handleLayoutDone}
          />
        </div>
      )}
    </div>
  );
}
