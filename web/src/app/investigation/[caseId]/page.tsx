"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useCaseGraph } from "@/hooks/useCaseGraph";
import type { GNode } from "@/hooks/useCaseGraph";
import { InvestigationCanvas } from "@/components/investigation/InvestigationCanvas";
import { InvestigationToolbar } from "@/components/investigation/InvestigationToolbar";
import { InvestigationSidebar } from "@/components/investigation/InvestigationSidebar";
import { AlertTriangle, Network, Building2, User, Info, ArrowLeft, X } from "lucide-react";
import { formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";

const ENTITY_TYPE_ICONS: Record<string, typeof Building2> = {
  company: Building2,
  person: User,
  org: Building2,
};

// Legend overlay shown when legendOpen=true
function LegendOverlay({ onClose }: { onClose: () => void }) {
  return (
    <div className="absolute bottom-16 left-4 z-30 w-52 rounded-xl border border-border bg-surface-card p-3 shadow-md">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">Legenda</p>
        <button
          onClick={onClose}
          className="flex h-5 w-5 items-center justify-center rounded text-muted hover:text-secondary"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted">Tipos de node</p>
      <div className="space-y-1 text-[11px]">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-blue-500" />
          <span className="text-secondary">Pessoa</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
          <span className="text-secondary">Empresa</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-violet-500" />
          <span className="text-secondary">Orgao Publico</span>
        </div>
      </div>
      <div className="my-2 h-px bg-border" />
      <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted">Arestas</p>
      <div className="space-y-1 text-[11px]">
        <div className="flex items-center gap-2">
          <span className="h-px w-5 bg-indigo-500" />
          <span className="text-secondary">Contrato</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-px w-5 bg-emerald-600" />
          <span className="text-secondary">Socio / Repr.</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-px w-5 border-t-2 border-dashed border-red-500" style={{ display: "inline-block" }} />
          <span className="text-secondary">Socio Oculto</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-px w-5 bg-violet-600" />
          <span className="text-secondary">Servidor</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-px w-5 bg-pink-500" />
          <span className="text-secondary">Vinculo Familiar</span>
        </div>
      </div>
      <div className="my-2 h-px bg-border" />
      <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted">Atalhos</p>
      <div className="space-y-0.5 text-[10px] text-muted">
        <div className="flex justify-between">
          <kbd className="rounded bg-surface-subtle px-1 font-mono">Espaco</kbd>
          <span>ajustar vista</span>
        </div>
        <div className="flex justify-between">
          <kbd className="rounded bg-surface-subtle px-1 font-mono">E</kbd>
          <span>expandir node</span>
        </div>
        <div className="flex justify-between">
          <kbd className="rounded bg-surface-subtle px-1 font-mono">Esc</kbd>
          <span>limpar selecao</span>
        </div>
      </div>
    </div>
  );
}

export default function InvestigationPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const caseId = params.caseId as string;
  const focusSignalId = searchParams.get("signal_id") ?? undefined;

  const {
    raw,
    graphData,
    degreeMap,
    entitySeverityMap,
    signals,
    seedEntityIds,
    loading,
    error,
    expanding,
    expandNode,
    erPending,
    focusSignalSummary,
  } = useCaseGraph(caseId, focusSignalId);

  const [selectedNode, setSelectedNode] = useState<GNode | null>(null);
  const [legendOpen, setLegendOpen] = useState(false);

  // ref to the ReactFlow fitView — passed up from canvas via callback
  const fitViewRef = useRef<(() => void) | null>(null);

  const handleNodeClick = useCallback(
    (node: GNode) => {
      setSelectedNode(node);
      expandNode(node.entity_id);
    },
    [expandNode],
  );

  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleClearSelected = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleExpandSelected = useCallback(() => {
    if (selectedNode) expandNode(selectedNode.entity_id);
  }, [selectedNode, expandNode]);

  // Build attrs lookup: node.id -> attrs
  const nodeAttrsMap = useMemo(() => {
    if (!raw) return {};
    const map: Record<string, Record<string, unknown>> = {};
    for (const n of raw.nodes) {
      map[n.id] = n.attrs;
    }
    return map;
  }, [raw]);

  // Loading
  if (loading) {
    return (
      <div className="investigation-bg fixed inset-0 z-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <span className="text-sm text-muted">
            Carregando grafo de investigacao...
          </span>
        </div>
      </div>
    );
  }

  // Error
  if (error) {
    return (
      <div className="investigation-bg fixed inset-0 z-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-center">
          <AlertTriangle className="h-8 w-8 text-severity-critical" />
          <p className="text-sm text-muted">{error}</p>
        </div>
      </div>
    );
  }

  // Has nodes but no edges — show fallback with entity cards
  const hasNodesNoEdges = raw && graphData.nodes.length > 0 && graphData.links.length === 0;

  if (!raw || (graphData.nodes.length === 0 && !hasNodesNoEdges)) {
    return (
      <div className="investigation-bg fixed inset-0 z-50 flex items-center justify-center">
        <div className="flex max-w-md flex-col items-center gap-3 text-center">
          <Network className="h-8 w-8 text-muted" />
          <p className="text-sm text-muted">
            Nenhuma entidade com conexoes encontrada neste caso
          </p>
          <Link
            href={`/case/${caseId}`}
            className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-white transition hover:opacity-90"
          >
            <ArrowLeft className="h-4 w-4" />
            Voltar ao caso
          </Link>
        </div>
      </div>
    );
  }

  // Fallback: nodes exist but no edges (ER pending)
  if (hasNodesNoEdges) {
    return (
      <div className="investigation-bg fixed inset-0 z-50 overflow-auto">
        <div className="mx-auto max-w-4xl px-4 py-8">
          {/* Toolbar-like header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Link
                href={`/case/${caseId}`}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-card px-3 py-1.5 text-xs font-medium text-secondary shadow-sm transition hover:bg-surface-subtle"
              >
                <ArrowLeft className="h-4 w-4" />
                Voltar ao caso
              </Link>
              <h1 className="text-lg font-semibold text-primary">
                {raw.case_title}
              </h1>
            </div>
            <span className="text-xs text-muted">
              {graphData.nodes.length} entidades | 0 conexoes
            </span>
          </div>

          {/* ER pending banner */}
          <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
            <div className="flex items-start gap-2">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
              <div>
                <p className="text-sm font-medium text-amber-800">
                  Grafo de relacionamentos pendente
                </p>
                <p className="mt-1 text-xs text-amber-700">
                  As entidades deste caso ainda nao possuem conexoes mapeadas no grafo.
                  Execute a resolucao de entidades para enriquecer o grafo com relacionamentos
                  derivados de contratos, licitacoes e participacoes em eventos compartilhados.
                </p>
              </div>
            </div>
          </div>

          {focusSignalSummary && (
            <div className="mt-4 rounded-lg border border-accent-subtle bg-accent-subtle/30 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-accent">
                Sinal em foco
              </p>
              <p className="mt-1 text-sm font-semibold text-primary">
                {focusSignalSummary.title}
              </p>
              <p className="mt-1 text-xs text-secondary">
                {focusSignalSummary.typology_code} - {focusSignalSummary.typology_name}
                {focusSignalSummary.period_start || focusSignalSummary.period_end ? (
                  <>
                    {" • "}
                    {focusSignalSummary.period_start ? formatDate(focusSignalSummary.period_start) : "---"}
                    {" -> "}
                    {focusSignalSummary.period_end ? formatDate(focusSignalSummary.period_end) : "---"}
                  </>
                ) : null}
              </p>
              {focusSignalSummary.summary && (
                <p className="mt-2 text-xs text-secondary">{focusSignalSummary.summary}</p>
              )}
            </div>
          )}

          {/* Entity cards grid */}
          <h2 className="mt-6 flex items-center gap-2 text-sm font-semibold text-secondary">
            <Building2 className="h-4 w-4 text-accent" />
            Entidades identificadas ({graphData.nodes.length})
          </h2>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {graphData.nodes.map((node) => {
              const EntityIcon = ENTITY_TYPE_ICONS[node.node_type] || Building2;
              const attrs = nodeAttrsMap[node.id] || {};
              const identifiers = (attrs.identifiers || {}) as Record<string, string>;
              const isSeed = seedEntityIds.has(node.entity_id);

              // Find signals referencing this entity
              const relatedSignals = signals.filter((s) =>
                s.entity_ids.includes(node.entity_id),
              );

              return (
                <div
                  key={node.id}
                  className={cn(
                    "rounded-lg border bg-surface-card p-4",
                    isSeed ? "border-accent/30 shadow-sm" : "border-border",
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      "flex h-10 w-10 shrink-0 items-center justify-center rounded-full",
                      isSeed ? "bg-accent-subtle" : "bg-surface-subtle",
                    )}>
                      <EntityIcon className={cn(
                        "h-5 w-5",
                        isSeed ? "text-accent" : "text-muted",
                      )} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-primary">
                        {node.label}
                      </p>
                      <p className="text-xs capitalize text-muted">
                        {node.node_type}
                        {isSeed && (
                          <span className="ml-1 rounded bg-accent-subtle px-1 py-0.5 text-accent">
                            semente
                          </span>
                        )}
                      </p>
                      {Object.keys(identifiers).length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {Object.entries(identifiers).map(([k, v]) => (
                            <span key={k} className="rounded bg-surface-subtle px-1.5 py-0.5 font-mono tabular-nums text-xs text-secondary">
                              {k.toUpperCase()}: {v}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  {relatedSignals.length > 0 && (
                    <div className="mt-3 border-t border-border pt-2">
                      <p className="text-xs font-medium text-muted">
                        {relatedSignals.length} sinal(is) relacionado(s)
                      </p>
                      <div className="mt-1 space-y-1">
                        {relatedSignals.slice(0, 3).map((s) => (
                          <p key={s.id} className="truncate text-xs text-secondary">
                            {s.typology_code} — {s.title}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="mt-3">
                    <Link
                      href={`/entity/${node.entity_id}`}
                      className="text-xs text-accent hover:underline"
                    >
                      Ver detalhes da entidade
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // Full graph view — split canvas + persistent sidebar
  const selectedNodeAttrs: Record<string, unknown> =
    selectedNode ? (nodeAttrsMap[selectedNode.id] ?? {}) : {};

  return (
    <div className="investigation-bg fixed inset-0 z-50 flex flex-col">
      {/* The toolbar renders its own absolute top bar + bottom-left actions */}
      <InvestigationToolbar
        caseId={caseId}
        caseTitle={raw.case_title}
        caseSeverity={raw.case_severity}
        nodeCount={graphData.nodes.length}
        edgeCount={graphData.links.length}
        seedCount={seedEntityIds.size}
        truncated={raw.truncated}
        expanding={expanding}
        onFitView={() => fitViewRef.current?.()}
        onToggleLegend={() => setLegendOpen((v) => !v)}
        legendOpen={legendOpen}
      />

      {/* Main content area below top bar */}
      <div className="flex flex-1 overflow-hidden pt-14">
        {/* Canvas area */}
        <div className="relative flex-1 overflow-hidden">
          {/* ER pending banner overlay */}
          {erPending && (
            <div className="absolute left-1/2 top-3 z-10 -translate-x-1/2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 shadow-md">
              <p className="text-xs text-amber-700">
                O grafo de relacionamentos sera enriquecido apos a resolucao de entidades ser executada.
              </p>
            </div>
          )}

          {focusSignalSummary && (
            <div className="absolute left-1/2 top-14 z-10 w-[min(680px,90%)] -translate-x-1/2 rounded-lg border border-accent-subtle bg-surface-card/95 px-4 py-3 shadow-md backdrop-blur-sm">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-accent">
                Narrativa do sinal em foco
              </p>
              <p className="mt-1 text-sm font-semibold text-primary">
                {focusSignalSummary.title}
              </p>
              <p className="mt-1 text-xs text-secondary">
                {focusSignalSummary.typology_code} - {focusSignalSummary.typology_name}
                {focusSignalSummary.period_start || focusSignalSummary.period_end ? (
                  <>
                    {" • "}
                    {focusSignalSummary.period_start ? formatDate(focusSignalSummary.period_start) : "---"}
                    {" -> "}
                    {focusSignalSummary.period_end ? formatDate(focusSignalSummary.period_end) : "---"}
                  </>
                ) : null}
              </p>
              {focusSignalSummary.summary && (
                <p className="mt-1 text-xs text-secondary">{focusSignalSummary.summary}</p>
              )}
            </div>
          )}

          {/* Legend overlay */}
          {legendOpen && <LegendOverlay onClose={() => setLegendOpen(false)} />}

          <InvestigationCanvas
            graphData={graphData}
            degreeMap={degreeMap}
            entitySeverityMap={entitySeverityMap}
            nodeAttrsMap={nodeAttrsMap}
            selectedNodeId={selectedNode?.id ?? null}
            onNodeClick={handleNodeClick}
            onBackgroundClick={handleBackgroundClick}
            onClearSelected={handleClearSelected}
            onExpandSelected={handleExpandSelected}
            fitViewRef={fitViewRef}
          />
        </div>

        {/* Persistent right sidebar */}
        <InvestigationSidebar
          node={selectedNode}
          nodeAttrs={selectedNodeAttrs}
          signals={signals}
          entitySeverityMap={entitySeverityMap}
          open={selectedNode !== null}
          onClose={handleClearSelected}
        />
      </div>
    </div>
  );
}
