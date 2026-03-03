"use client";

import { useCallback, useMemo, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useCaseGraph } from "@/hooks/useCaseGraph";
import type { GNode } from "@/hooks/useCaseGraph";
import { InvestigationCanvas } from "@/components/investigation/InvestigationCanvas";
import { InvestigationToolbar } from "@/components/investigation/InvestigationToolbar";
import { InvestigationSidebar } from "@/components/investigation/InvestigationSidebar";
import { AlertTriangle, Network, Building2, User, Info, ArrowLeft } from "lucide-react";
import { formatDate } from "@/lib/utils";

const ENTITY_TYPE_ICONS: Record<string, typeof Building2> = {
  company: Building2,
  person: User,
  org: Building2,
};

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
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleNodeClick = useCallback(
    (node: GNode) => {
      setSelectedNode(node);
      setSidebarOpen(true);
      expandNode(node.entity_id);
    },
    [expandNode],
  );

  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
    setSidebarOpen(false);
  }, []);

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
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-gov-blue-600 border-t-transparent" />
          <span className="text-sm text-gov-gray-500">
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
          <AlertTriangle className="h-8 w-8 text-red-500" />
          <p className="text-sm text-gov-gray-500">{error}</p>
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
          <Network className="h-8 w-8 text-gov-gray-400" />
          <p className="text-sm text-gov-gray-500">
            Nenhuma entidade com conexoes encontrada neste caso
          </p>
          <Link
            href={`/case/${caseId}`}
            className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-gov-blue-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-gov-blue-700"
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
                className="inline-flex items-center gap-1.5 rounded-lg border border-gov-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gov-gray-700 shadow-sm transition hover:bg-gov-gray-50"
              >
                <ArrowLeft className="h-4 w-4" />
                Voltar ao caso
              </Link>
              <h1 className="text-lg font-semibold text-gov-gray-900">
                {raw.case_title}
              </h1>
            </div>
            <span className="text-xs text-gov-gray-500">
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
            <div className="mt-4 rounded-lg border border-gov-blue-200 bg-gov-blue-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gov-blue-700">
                Sinal em foco
              </p>
              <p className="mt-1 text-sm font-semibold text-gov-blue-900">
                {focusSignalSummary.title}
              </p>
              <p className="mt-1 text-xs text-gov-blue-700">
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
                <p className="mt-2 text-xs text-gov-blue-800">{focusSignalSummary.summary}</p>
              )}
            </div>
          )}

          {/* Entity cards grid */}
          <h2 className="mt-6 flex items-center gap-2 text-sm font-semibold text-gov-gray-700">
            <Building2 className="h-4 w-4 text-gov-blue-600" />
            Entidades identificadas ({graphData.nodes.length})
          </h2>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {graphData.nodes.map((node) => {
              const EntityIcon = ENTITY_TYPE_ICONS[node.node_type] || Building2;
              const attrs = nodeAttrsMap[node.id] || {};
              const identifiers = (attrs.identifiers || {}) as Record<string, string>;
              const isSeed = seedEntityIds.has(node.entity_id);
              const severity = entitySeverityMap[node.entity_id];

              // Find signals referencing this entity
              const relatedSignals = signals.filter((s) =>
                s.entity_ids.includes(node.entity_id),
              );

              return (
                <div
                  key={node.id}
                  className={`rounded-lg border bg-white p-4 ${
                    isSeed ? "border-gov-blue-300 shadow-sm" : "border-gov-gray-200"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
                      isSeed ? "bg-gov-blue-100" : "bg-gov-gray-100"
                    }`}>
                      <EntityIcon className={`h-5 w-5 ${
                        isSeed ? "text-gov-blue-700" : "text-gov-gray-500"
                      }`} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-gov-gray-900 truncate">
                        {node.label}
                      </p>
                      <p className="text-xs capitalize text-gov-gray-500">
                        {node.node_type}
                        {isSeed && (
                          <span className="ml-1 rounded bg-gov-blue-100 px-1 py-0.5 text-gov-blue-700">
                            semente
                          </span>
                        )}
                      </p>
                      {Object.keys(identifiers).length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {Object.entries(identifiers).map(([k, v]) => (
                            <span key={k} className="rounded bg-gov-gray-50 px-1.5 py-0.5 font-mono text-xs text-gov-gray-600">
                              {k.toUpperCase()}: {v}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  {relatedSignals.length > 0 && (
                    <div className="mt-3 border-t border-gov-gray-100 pt-2">
                      <p className="text-xs font-medium text-gov-gray-500">
                        {relatedSignals.length} sinal(is) relacionado(s)
                      </p>
                      <div className="mt-1 space-y-1">
                        {relatedSignals.slice(0, 3).map((s) => (
                          <p key={s.id} className="truncate text-xs text-gov-gray-600">
                            {s.typology_code} — {s.title}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="mt-3">
                    <Link
                      href={`/entity/${node.entity_id}`}
                      className="text-xs text-gov-blue-600 hover:underline"
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

  // Full graph view — normal canvas
  const selectedNodeAttrs: Record<string, unknown> =
    selectedNode ? (nodeAttrsMap[selectedNode.id] ?? {}) : {};

  return (
    <div className="investigation-bg fixed inset-0 z-50">
      <InvestigationToolbar
        caseId={caseId}
        caseTitle={raw.case_title}
        caseSeverity={raw.case_severity}
        nodeCount={graphData.nodes.length}
        edgeCount={graphData.links.length}
        seedCount={seedEntityIds.size}
        truncated={raw.truncated}
        expanding={expanding}
      />

      {/* ER pending banner overlay */}
      {erPending && (
        <div className="absolute left-1/2 top-16 z-10 -translate-x-1/2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 shadow-md">
          <p className="text-xs text-amber-700">
            O grafo de relacionamentos sera enriquecido apos a resolucao de entidades ser executada.
          </p>
        </div>
      )}

      {focusSignalSummary && (
        <div className="absolute left-1/2 top-28 z-10 w-[min(760px,92vw)] -translate-x-1/2 rounded-lg border border-gov-blue-200 bg-white/95 px-4 py-3 shadow-md backdrop-blur-sm">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-gov-blue-700">
            Narrativa do sinal em foco
          </p>
          <p className="mt-1 text-sm font-semibold text-gov-gray-900">
            {focusSignalSummary.title}
          </p>
          <p className="mt-1 text-xs text-gov-gray-600">
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
            <p className="mt-1 text-xs text-gov-gray-700">{focusSignalSummary.summary}</p>
          )}
        </div>
      )}

      <InvestigationCanvas
        graphData={graphData}
        degreeMap={degreeMap}
        entitySeverityMap={entitySeverityMap}
        nodeAttrsMap={nodeAttrsMap}
        selectedNodeId={selectedNode?.id ?? null}
        onNodeClick={handleNodeClick}
        onBackgroundClick={handleBackgroundClick}
      />

      <InvestigationSidebar
        node={selectedNode}
        nodeAttrs={selectedNodeAttrs}
        signals={signals}
        entitySeverityMap={entitySeverityMap}
        open={sidebarOpen}
        onClose={() => {
          setSidebarOpen(false);
          setSelectedNode(null);
        }}
      />
    </div>
  );
}
