"use client";

import { useCallback, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { Network, Building2, User, Landmark, Link2, AlertTriangle } from "lucide-react";
import { useDossieBook } from "@/components/dossie/DossieBookContext";
import { useCaseGraphEnriched } from "@/hooks/useCaseGraphEnriched";
import type { GNode } from "@/hooks/useCaseGraph";
import { cn } from "@/lib/utils";

const InvestigationCanvas = dynamic(
  () =>
    import("@/components/investigation/InvestigationCanvas").then((m) => ({
      default: m.InvestigationCanvas,
    })),
  {
    loading: () => (
      <div className="h-[560px] animate-pulse rounded-xl bg-surface-subtle" />
    ),
    ssr: false,
  },
);

const SEV = {
  critical: {
    label: "Critico",
    bg: "bg-severity-critical-bg",
    text: "text-severity-critical",
    border: "border-severity-critical/30",
    dot: "bg-severity-critical",
  },
  high: {
    label: "Alto",
    bg: "bg-severity-high-bg",
    text: "text-severity-high",
    border: "border-severity-high/30",
    dot: "bg-severity-high",
  },
  medium: {
    label: "Medio",
    bg: "bg-severity-medium-bg",
    text: "text-severity-medium",
    border: "border-severity-medium/30",
    dot: "bg-severity-medium",
  },
  low: {
    label: "Baixo",
    bg: "bg-severity-low-bg",
    text: "text-severity-low",
    border: "border-severity-low/30",
    dot: "bg-severity-low",
  },
} as const;

const ENTITY_COL: Record<string, string> = {
  org:     "#3A90A0",
  company: "#4A82D4",
  person:  "#7C6AE0",
};

const ENTITY_ICON: Record<string, React.ElementType> = {
  org: Landmark,
  company: Building2,
  person: User,
};

const ENTITY_LABEL: Record<string, string> = {
  org: "Orgao Publico",
  company: "Empresa",
  person: "Pessoa Fisica",
};

function initials(name: string): string {
  const p = name.trim().split(/\s+/);
  return (
    (p[0]?.[0] ?? "") +
    (p.length > 1 ? (p[p.length - 1]?.[0] ?? "") : "")
  ).toUpperCase();
}


export default function DossieRedePage() {
  const { caseId } = useParams<{ caseId: string }>();
  const { data, loading, error } = useDossieBook();
  const [focusSignalId, setFocusSignalId] = useState<string | undefined>(
    undefined,
  );
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const fitViewRef = useRef<(() => void) | null>(null);

  const {
    graphData,
    degreeMap,
    entitySeverityMap,
    nodeAttrsMap,
    signals,
    loading: graphLoading,
    error: graphError,
    expandNode,
    erPending,
  } = useCaseGraphEnriched(caseId, focusSignalId);

  const handleNodeClick = useCallback((node: GNode) => {
    setSelectedNodeId((prev) => (prev === node.id ? null : node.id));
  }, []);

  const handleClearSelected = useCallback(() => setSelectedNodeId(null), []);

  const handleExpandSelected = useCallback(() => {
    if (!selectedNodeId) return;
    const node = graphData.nodes.find((n) => n.id === selectedNodeId);
    if (node) expandNode(node.entity_id);
  }, [selectedNodeId, graphData.nodes, expandNode]);

  // ── Loading ─────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-surface-base">
        <div className="h-20 animate-pulse border-b border-border bg-surface-card" />
        <div className="mx-auto max-w-6xl px-6 py-10 space-y-6">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-24 rounded-xl border border-border bg-surface-card animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  // ── Error ───────────────────────────────────────────────────────────────────
  if (error || !data) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <div className="text-center">
          <p className="text-sm text-error">
            {error ?? "Erro ao carregar dados do caso."}
          </p>
          <Link
            href={`/radar/dossie/${caseId}`}
            className="mt-3 inline-block text-sm text-accent hover:underline"
          >
            Voltar ao dossie
          </Link>
        </div>
      </div>
    );
  }

  const sevData =
    SEV[data.case.severity as keyof typeof SEV] ?? SEV.low;
  const entities = data.entities;

  return (
    <div className="ledger-page min-h-screen bg-surface-base">

      {/* ── Hero Banner ──────────────────────────────────────────────────────── */}
      <div className={cn("border-b", sevData.bg, sevData.border)}>
        <div className="mx-auto max-w-6xl px-6 py-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-xs font-bold",
                sevData.border,
                sevData.text,
              )}
            >
              <span
                className={cn("h-2 w-2 rounded-full animate-pulse", sevData.dot)}
              />
              Rede de Conexoes — {data.case.id}
            </div>
            <span
              className={cn(
                "rounded-full border px-2.5 py-0.5 font-mono text-[10px] font-bold uppercase",
                sevData.border,
                sevData.text,
              )}
            >
              {sevData.label}
            </span>
          </div>
          <Network className={cn("h-4 w-4 opacity-60", sevData.text)} />
        </div>
      </div>

      {/* ── Stats Grid ───────────────────────────────────────────────────────── */}
      <div className="border-b border-border bg-surface-card">
        <div className="mx-auto max-w-6xl px-6 py-6">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Entidades", val: graphData.nodes.length, color: "#a78bfa" },
              { label: "Conexoes", val: graphData.links.length, color: "#6366f1" },
              { label: "Sinais", val: signals.length, color: "#f59e0b" },
              { label: "Entidades do Caso", val: entities.length, color: "#34D399" },
            ].map(({ label, val, color }) => (
              <div
                key={label}
                className="rounded-xl border border-border bg-surface-subtle p-4"
              >
                <p className="font-mono text-xs text-muted mb-1">{label}</p>
                <p
                  className="font-mono text-2xl font-black tabular-nums"
                  style={{ color }}
                >
                  {val}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-6 py-10 space-y-10">

        {/* ── Signal Filter + Graph ──────────────────────────────────────────── */}
        <section>
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Network className="h-4 w-4 text-accent" />
              <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
                Grafo de Rede do Caso
              </h2>
            </div>
            {signals.length > 0 && (
              <div className="flex items-center gap-2">
                <label className="font-mono text-[10px] text-muted">
                  Filtrar por sinal:
                </label>
                <select
                  value={focusSignalId ?? ""}
                  onChange={(e) =>
                    setFocusSignalId(e.target.value || undefined)
                  }
                  className="max-w-xs rounded-lg border border-border bg-surface-card px-2.5 py-1.5 font-mono text-[11px] text-primary outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/30"
                >
                  <option value="">Todos os sinais</option>
                  {signals.map((sig) => (
                    <option key={sig.id} value={sig.id}>
                      {sig.typology_code} — {sig.title}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {erPending && (
            <div className="mb-4 flex items-center gap-2 rounded-lg border border-warning/30 bg-warning/5 px-3 py-2">
              <AlertTriangle className="h-3.5 w-3.5 text-warning" />
              <p className="font-mono text-[10px] text-warning">
                Resolucao de entidades em andamento — o grafo pode estar incompleto.
              </p>
            </div>
          )}

          {graphLoading ? (
            <div className="h-[560px] animate-pulse rounded-xl bg-surface-subtle" />
          ) : graphError ? (
            <div className="rounded-xl border border-dashed border-error/30 bg-error/5 p-12 text-center">
              <p className="text-sm text-error">{graphError}</p>
            </div>
          ) : graphData.nodes.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-surface-card p-12 text-center">
              <Network className="h-8 w-8 text-muted mx-auto mb-3 opacity-40" />
              <p className="text-sm font-medium text-secondary">
                Nenhuma conexao encontrada entre as entidades deste caso.
              </p>
            </div>
          ) : (
            <div className="h-[560px] relative rounded-xl border border-border bg-surface-card overflow-hidden">
              <InvestigationCanvas
                graphData={graphData}
                degreeMap={degreeMap}
                entitySeverityMap={entitySeverityMap}
                nodeAttrsMap={nodeAttrsMap}
                selectedNodeId={selectedNodeId}
                onNodeClick={handleNodeClick}
                onBackgroundClick={handleClearSelected}
                onClearSelected={handleClearSelected}
                onExpandSelected={handleExpandSelected}
                fitViewRef={fitViewRef}
              />
            </div>
          )}

          {/* Keyboard hints */}
          {graphData.nodes.length > 0 && (
            <div className="mt-2 flex items-center gap-4 font-mono text-[9px] text-muted">
              <span><kbd className="rounded border border-border bg-surface-subtle px-1">Space</kbd> / <kbd className="rounded border border-border bg-surface-subtle px-1">F</kbd> Ajustar</span>
              <span><kbd className="rounded border border-border bg-surface-subtle px-1">Esc</kbd> Desselecionar</span>
              <span><kbd className="rounded border border-border bg-surface-subtle px-1">E</kbd> Expandir no selecionado</span>
            </div>
          )}
        </section>

        {/* ── Entity Grid ──────────────────────────────────────────────────── */}
        <section>
          <div className="mb-4 flex items-center gap-2">
            <User className="h-4 w-4 text-accent" />
            <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
              Entidades do Caso ({entities.length})
            </h2>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {entities.map((entity) => {
              const col = ENTITY_COL[entity.type] ?? "#a78bfa";
              const EIcon = ENTITY_ICON[entity.type] ?? Building2;
              const cnpj = entity.identifiers["cnpj"];
              const cpf = entity.identifiers["cpf"];
              const party = entity.attrs["party"] as string | undefined;
              const sphere = entity.attrs["sphere"] as string | undefined;
              const mandateStart = entity.attrs["mandate_start"] as
                | string
                | undefined;
              const mandateEnd = entity.attrs["mandate_end"] as
                | string
                | undefined;
              const photoUrl = entity.attrs["photo_url"] as
                | string
                | undefined;

              // Find the graph node for this entity to check if selected
              const graphNode = graphData.nodes.find(
                (n) => n.entity_id === entity.id,
              );
              const isActive = graphNode
                ? selectedNodeId === graphNode.id
                : false;

              return (
                <button
                  key={entity.id}
                  onClick={() => {
                    if (graphNode) {
                      setSelectedNodeId((prev) =>
                        prev === graphNode.id ? null : graphNode.id,
                      );
                    }
                  }}
                  className={cn(
                    "rounded-2xl border bg-surface-card p-5 text-left transition-all hover:border-accent/40",
                    isActive
                      ? "border-accent/50 ring-1 ring-accent/30"
                      : "border-border",
                  )}
                >
                  {/* Avatar + name */}
                  <div className="mb-3 flex items-start gap-3">
                    {photoUrl ? (
                      <img
                        src={photoUrl}
                        alt={entity.name}
                        className="h-10 w-10 shrink-0 rounded-xl object-cover"
                      />
                    ) : (
                      <div
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-sm font-bold text-white"
                        style={{ backgroundColor: col }}
                      >
                        {initials(entity.name)}
                      </div>
                    )}
                    <div className="min-w-0">
                      <p className="font-semibold text-primary leading-tight line-clamp-2">
                        {entity.name}
                      </p>
                      <span
                        className="font-mono text-[9px] font-bold uppercase"
                        style={{ color: col }}
                      >
                        {ENTITY_LABEL[entity.type] ?? entity.type}
                      </span>
                    </div>
                  </div>

                  {/* Identifier */}
                  {(cnpj ?? cpf) && (
                    <p className="mb-2 font-mono text-[10px] text-muted">
                      {cnpj ? `CNPJ ${cnpj}` : `CPF ${cpf}`}
                    </p>
                  )}

                  {/* Badges */}
                  {(party ?? sphere) && (
                    <div className="mb-2 flex flex-wrap gap-1">
                      {party && (
                        <span className="rounded-full border border-border bg-surface-subtle px-2 py-0.5 font-mono text-[9px] text-secondary">
                          {party}
                        </span>
                      )}
                      {sphere && (
                        <span className="rounded-full border border-border bg-surface-subtle px-2 py-0.5 font-mono text-[9px] text-secondary">
                          {sphere}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Mandate */}
                  {mandateStart && (
                    <p className="mb-2 font-mono text-[9px] text-muted">
                      Mandato: {mandateStart}
                      {mandateEnd ? `–${mandateEnd}` : ""}
                    </p>
                  )}

                  {/* Type icon + external link */}
                  <div className="mt-3 flex items-center justify-between border-t border-border pt-3">
                    <EIcon className="h-3 w-3 text-muted opacity-60" />
                    <Link
                      href={`/radar/rede/${entity.id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="font-mono text-[9px] text-accent hover:underline"
                    >
                      Rede completa →
                    </Link>
                  </div>
                </button>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
