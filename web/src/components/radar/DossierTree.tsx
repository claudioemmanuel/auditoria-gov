"use client";

import { useMemo, useState } from "react";
import type { RadarV2CaseItem, RadarV2CasePreviewResponse } from "@/lib/types";
import { RadarInlineFilters } from "./RadarInlineFilters";
import { DossierCaseNode } from "./DossierCaseNode";
import { Button } from "@/components/Button";
import { TableSkeleton } from "@/components/Skeleton";
import { ChevronLeft, ChevronRight } from "lucide-react";

const PAGE_SIZE = 20;

interface DossierTreeProps {
  cases: RadarV2CaseItem[];
  total: number;
  loading: boolean;
  error: string | null;
  offset: number;
  onOffsetChange: (offset: number) => void;
  casePreviewCache: Map<string, RadarV2CasePreviewResponse>;
  casePreviewLoading: Set<string>;
  expandedCases: Set<string>;
  onToggleExpand: (caseId: string) => void;
  onSignalClick: (caseId: string, signalId: string) => void;
  activeSignalId: string | null;
  panelOpen: boolean;
  // Filter props
  search: string;
  onSearchChange: (v: string) => void;
  typology: string;
  periodFrom: string;
  periodTo: string;
  corruptionType: string;
  sphere: string;
  onTypologyChange: (v: string) => void;
  onPeriodFromChange: (v: string) => void;
  onPeriodToChange: (v: string) => void;
  onCorruptionTypeChange: (v: string) => void;
  onSphereChange: (v: string) => void;
  onClearAll: () => void;
}

export function DossierTree({
  cases,
  total,
  loading,
  error,
  offset,
  onOffsetChange,
  casePreviewCache,
  casePreviewLoading,
  expandedCases,
  onToggleExpand,
  onSignalClick,
  activeSignalId,
  panelOpen,
  search,
  onSearchChange,
  typology,
  periodFrom,
  periodTo,
  corruptionType,
  sphere,
  onTypologyChange,
  onPeriodFromChange,
  onPeriodToChange,
  onCorruptionTypeChange,
  onSphereChange,
  onClearAll,
}: DossierTreeProps) {
  const filteredCases = useMemo(() => {
    if (!search.trim()) return cases;
    const q = search.toLowerCase();
    return cases.filter((c) => c.title.toLowerCase().includes(q));
  }, [cases, search]);

  const isSearching = search.trim().length > 0;
  const displayTotal = isSearching ? filteredCases.length : total;
  const totalPages = isSearching ? 1 : Math.ceil(total / PAGE_SIZE);
  const currentPage = isSearching ? 1 : Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className={`flex-1 min-w-0 overflow-y-auto px-4 py-6 sm:px-6 transition-all ${panelOpen ? "lg:mr-[480px]" : ""}`}>
      {/* Header + filters */}
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted">Dossie de Investigacao</p>
          <p className="text-sm font-semibold text-primary mt-0.5">
            {loading ? "—" : `${displayTotal.toLocaleString("pt-BR")} casos`}
          </p>
          <p className="text-xs text-secondary mt-0.5">
            Clique em um caso para explorar sinais e entidades
          </p>
        </div>
        <RadarInlineFilters
          search={search}
          onSearchChange={onSearchChange}
          typology={typology}
          periodFrom={periodFrom}
          periodTo={periodTo}
          corruptionType={corruptionType}
          sphere={sphere}
          onTypologyChange={onTypologyChange}

          onPeriodFromChange={onPeriodFromChange}
          onPeriodToChange={onPeriodToChange}
          onCorruptionTypeChange={onCorruptionTypeChange}
          onSphereChange={onSphereChange}
          onClearAll={onClearAll}
        />
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-error/20 bg-error/5 p-6 text-center">
          <p className="text-sm text-error">{error}</p>
          <Button variant="secondary" size="sm" className="mt-3" onClick={() => window.location.reload()}>
            Tentar novamente
          </Button>
        </div>
      )}

      {/* Loading */}
      {loading && !error && <TableSkeleton rows={6} />}

      {/* Empty */}
      {!loading && !error && filteredCases.length === 0 && (
        <div className="rounded-xl border border-border bg-surface-card p-12 text-center">
          <p className="text-sm font-medium text-secondary">Nenhum caso encontrado</p>
          <p className="mt-1 text-xs text-muted">Ajuste os filtros ou aguarde novos dados do pipeline.</p>
        </div>
      )}

      {/* Case nodes */}
      {!loading && !error && filteredCases.length > 0 && (
        <div className="space-y-3">
          {filteredCases.map((c) => (
            <DossierCaseNode
              key={c.id}
              case={c}
              preview={casePreviewCache.get(c.id) ?? null}
              previewLoading={casePreviewLoading.has(c.id)}
              expanded={expandedCases.has(c.id)}
              onToggleExpand={() => onToggleExpand(c.id)}
              onSignalClick={onSignalClick}
              activeSignalId={activeSignalId}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div className="mt-6 flex items-center justify-between border-t border-border pt-4">
          <span className="text-xs text-muted">
            Pagina {currentPage} de {totalPages} · {displayTotal} casos
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={currentPage <= 1}
              onClick={() => onOffsetChange(Math.max(0, offset - PAGE_SIZE))}
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Anterior
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={currentPage >= totalPages}
              onClick={() => onOffsetChange(offset + PAGE_SIZE)}
            >
              Proxima
              <ChevronRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
