"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import {
  FileText,
  ExternalLink,
  Layers,
  Building2,
  FileSearch,
  ArrowUpDown,
  Download,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { cn, formatBRL, formatDate } from "@/lib/utils";
import type { EvidenceRef, SignalEvidenceItem } from "@/lib/types";

// ---- Ref-based list (provenance chain) ----

interface ProvenanceRef extends EvidenceRef {
  children?: ProvenanceRef[];
}

const REF_TYPE_CONFIG: Record<string, { label: string; icon: typeof FileText }> = {
  event: { label: "Evento", icon: FileText },
  baseline: { label: "Baseline", icon: Layers },
  entity: { label: "Entidade", icon: Building2 },
  external_url: { label: "Fonte externa", icon: ExternalLink },
  raw_source: { label: "Registro bruto", icon: FileSearch },
};

interface ProvenanceNodeProps {
  ref: ProvenanceRef;
  depth: number;
  forceExpand: boolean;
}

function ProvenanceNode({ ref: r, depth, forceExpand }: ProvenanceNodeProps) {
  const [open, setOpen] = useState(depth < 3);
  const isExpanded = forceExpand || open;
  const config = REF_TYPE_CONFIG[r.ref_type] ?? { label: r.ref_type, icon: FileText };
  const RefIcon = config.icon;
  const hasChildren = r.children && r.children.length > 0;

  return (
    <li className="border-l border-border pl-3">
      <div className="flex items-start gap-2 py-1.5">
        {hasChildren ? (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="mt-0.5 shrink-0 text-secondary hover:text-primary"
            aria-label={isExpanded ? "Recolher" : "Expandir"}
          >
            {isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
          </button>
        ) : (
          <span className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        )}
        <RefIcon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" />
        <div className="min-w-0 flex-1">
          <p className="text-sm text-primary">{r.description}</p>
          <div className="mt-0.5 flex flex-wrap items-center gap-2">
            <span className="rounded bg-surface-base px-1 py-0.5 text-xs text-secondary">
              {config.label}
            </span>
            {r.url && (
              <a
                href={r.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-0.5 text-xs text-accent underline hover:opacity-80"
              >
                fonte
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
            {r.ref_id && r.ref_type === "entity" && (
              <Link
                href={`/entity/${r.ref_id}`}
                className="inline-flex items-center gap-0.5 text-xs text-accent underline hover:opacity-80"
              >
                ver entidade
                <ExternalLink className="h-3 w-3" />
              </Link>
            )}
          </div>
        </div>
      </div>
      {hasChildren && isExpanded && (
        <ul className="ml-2 mt-1 space-y-0.5">
          {r.children!.map((child, i) => (
            <ProvenanceNode key={i} ref={child} depth={depth + 1} forceExpand={forceExpand} />
          ))}
        </ul>
      )}
    </li>
  );
}

interface ProvenanceChainProps {
  refs: EvidenceRef[];
}

function ProvenanceChain({ refs }: ProvenanceChainProps) {
  const [expandAll, setExpandAll] = useState(false);

  if (refs.length === 0) return null;

  // Build flat list — the API does not return a nested tree so render as flat
  const nodes = refs as ProvenanceRef[];
  // Determine max depth heuristic: more than 3 items → collapse by default
  const defaultCollapsed = refs.length > 3;

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-primary">
          Cadeia de Proveniência
        </h2>
        {defaultCollapsed && (
          <button
            type="button"
            onClick={() => setExpandAll((v) => !v)}
            className="text-xs text-accent hover:opacity-80"
          >
            {expandAll ? "Recolher tudo" : "Expandir tudo"}
          </button>
        )}
      </div>
      <ul className="mt-3 space-y-0.5">
        {nodes.map((node, i) => (
          <ProvenanceNode
            key={i}
            ref={node}
            depth={0}
            forceExpand={expandAll}
          />
        ))}
      </ul>
    </div>
  );
}

// ---- Main EvidenceList (table of SignalEvidenceItem + pagination + sort + export) ----

type SortKey = "date" | "value";
type SortDir = "asc" | "desc";

interface EvidenceListProps {
  signalId: string;
  items: SignalEvidenceItem[];
  total: number;
  offset: number;
  limit: number;
  onPageChange: (offset: number) => void;
  loading?: boolean;
  refs?: EvidenceRef[];
}

export function EvidenceList({
  signalId,
  items,
  total,
  offset,
  limit,
  onPageChange,
  loading = false,
  refs = [],
}: EvidenceListProps) {
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [exporting, setExporting] = useState(false);

  const toggleSort = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortKey(key);
        setSortDir("desc");
      }
    },
    [sortKey],
  );

  const sorted = [...items].sort((a, b) => {
    const mul = sortDir === "asc" ? 1 : -1;
    if (sortKey === "date") {
      const aT = a.occurred_at ? new Date(a.occurred_at).getTime() : 0;
      const bT = b.occurred_at ? new Date(b.occurred_at).getTime() : 0;
      return (aT - bT) * mul;
    }
    // value
    const aV = a.value_brl ?? 0;
    const bV = b.value_brl ?? 0;
    return (aV - bV) * mul;
  });

  const handleExport = useCallback(async () => {
    setExporting(true);
    try {
      const url = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/public/signals/${signalId}/evidence/export?format=csv`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Export failed: ${res.status}`);
      const blob = await res.blob();
      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = `evidencias-${signalId}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(href);
    } catch {
      // silent — export failure is non-critical
    } finally {
      setExporting(false);
    }
  }, [signalId]);

  const hasPagination = total > limit;
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  function SortButton({ col, label }: { col: SortKey; label: string }) {
    const active = sortKey === col;
    return (
      <button
        type="button"
        onClick={() => toggleSort(col)}
        className={cn(
          "inline-flex items-center gap-1 text-xs font-medium",
          active ? "text-accent" : "text-secondary hover:text-primary",
        )}
      >
        {label}
        <ArrowUpDown className="h-3 w-3" />
        {active && (
          <span className="text-[10px]">{sortDir === "asc" ? "↑" : "↓"}</span>
        )}
      </button>
    );
  }

  return (
    <div className="mt-6">
      {/* Section header */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-primary">
          Evidências ({total})
        </h2>
        <button
          type="button"
          onClick={handleExport}
          disabled={exporting || total === 0}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md border border-border bg-surface-card px-2.5 py-1 text-xs font-medium text-secondary transition hover:text-primary",
            (exporting || total === 0) && "cursor-not-allowed opacity-50",
          )}
        >
          <Download className="h-3.5 w-3.5" />
          {exporting ? "Exportando..." : "Exportar CSV"}
        </button>
      </div>

      {/* Sort controls */}
      {items.length > 1 && (
        <div className="mt-2 flex items-center gap-3 text-xs text-secondary">
          <span>Ordenar:</span>
          <SortButton col="date" label="Data" />
          <SortButton col="value" label="Valor" />
        </div>
      )}

      {/* Table */}
      {loading && items.length === 0 ? (
        <div className="mt-3 rounded-lg border border-border bg-surface-card p-4 text-sm text-secondary">
          Carregando evidências...
        </div>
      ) : sorted.length === 0 ? (
        <div className="mt-3 rounded-lg border border-border bg-surface-card p-4 text-sm text-secondary">
          Nenhuma evidência encontrada.
        </div>
      ) : (
        <div className="mt-3 overflow-x-auto rounded-lg border border-border">
          <table className="min-w-full divide-y divide-border text-sm">
            <thead className="bg-surface-base">
              <tr>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-secondary">
                  Data
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-secondary">
                  Descrição
                </th>
                <th className="px-3 py-2.5 text-right text-xs font-semibold text-secondary">
                  Valor
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-secondary">
                  Fonte
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-secondary">
                  Link
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-surface-card">
              {sorted.map((item) => (
                <tr key={item.event_id} className="hover:bg-surface-subtle/50 transition-colors">
                  <td className="whitespace-nowrap px-3 py-2.5 font-mono tabular-nums text-xs text-secondary">
                    {item.occurred_at ? formatDate(item.occurred_at) : "—"}
                  </td>
                  <td className="px-3 py-2.5 text-xs text-primary">
                    <p className="font-medium">{item.description}</p>
                    {item.evidence_reason && (
                      <p className="mt-0.5 text-muted">{item.evidence_reason}</p>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-right font-mono tabular-nums text-xs text-primary">
                    {typeof item.value_brl === "number" ? formatBRL(item.value_brl) : "—"}
                  </td>
                  <td className="px-3 py-2.5">
                    <span className="rounded bg-surface-base px-1.5 py-0.5 font-mono text-xs text-secondary">
                      {item.source_connector}
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    <a
                      href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/public/event/${item.source_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-0.5 text-xs text-accent hover:opacity-80"
                      title={item.source_id}
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {hasPagination && (
        <div className="mt-3 flex items-center justify-between text-xs text-secondary">
          <button
            type="button"
            disabled={offset === 0 || loading}
            onClick={() => onPageChange(Math.max(0, offset - limit))}
            className="rounded border border-border bg-surface-card px-2.5 py-1 text-secondary disabled:cursor-not-allowed disabled:opacity-50 hover:text-primary"
          >
            Anterior
          </button>
          <span>
            Página {currentPage} de {totalPages} &mdash; {total} registros
          </span>
          <button
            type="button"
            disabled={offset + limit >= total || loading}
            onClick={() => onPageChange(offset + limit)}
            className="rounded border border-border bg-surface-card px-2.5 py-1 text-secondary disabled:cursor-not-allowed disabled:opacity-50 hover:text-primary"
          >
            Próxima
          </button>
        </div>
      )}

      {/* Provenance chain */}
      {refs.length > 0 && <ProvenanceChain refs={refs} />}
    </div>
  );
}
