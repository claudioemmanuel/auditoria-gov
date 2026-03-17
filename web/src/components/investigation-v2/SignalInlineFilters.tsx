"use client";

import { useState } from "react";
import { Filter, X, Search } from "lucide-react";
import { cn } from "@/lib/utils";

interface SignalInlineFiltersProps {
  search: string;
  onSearchChange: (v: string) => void;
  typology: string;
  severity: string;
  sort: string;
  periodFrom: string;
  periodTo: string;
  onTypologyChange: (v: string) => void;
  onSeverityChange: (v: string) => void;
  onSortChange: (v: string) => void;
  onPeriodFromChange: (v: string) => void;
  onPeriodToChange: (v: string) => void;
  onClearAll: () => void;
}

const SEVERITIES = [
  { value: "", label: "Todas" },
  { value: "critical", label: "Critico" },
  { value: "high", label: "Alto" },
  { value: "medium", label: "Medio" },
  { value: "low", label: "Baixo" },
];

const SORT_OPTIONS = [
  { value: "", label: "Mais recentes" },
  { value: "analysis_date", label: "Data de analise" },
  { value: "ingestion_date", label: "Data de ingestao" },
];

export function SignalInlineFilters({
  search,
  onSearchChange,
  typology,
  severity,
  sort,
  periodFrom,
  periodTo,
  onTypologyChange,
  onSeverityChange,
  onSortChange,
  onPeriodFromChange,
  onPeriodToChange,
  onClearAll,
}: SignalInlineFiltersProps) {
  const [filtersOpen, setFiltersOpen] = useState(false);
  const hasFilters = !!(typology || severity || sort || periodFrom || periodTo);

  return (
    <div className="flex flex-col gap-2">
      {/* Search + filter toggle */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Buscar sinais..."
            className="w-full rounded-lg border border-border bg-surface-card py-1.5 pl-8 pr-3 text-xs text-primary placeholder:text-placeholder outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/30"
          />
        </div>
        <button
          onClick={() => setFiltersOpen(!filtersOpen)}
          className={cn(
            "flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors",
            filtersOpen || hasFilters
              ? "border-accent/30 bg-accent/5 text-accent"
              : "border-border text-muted hover:text-secondary hover:border-border",
          )}
        >
          <Filter className="h-3.5 w-3.5" />
          Filtros
          {hasFilters && (
            <button
              onClick={(e) => { e.stopPropagation(); onClearAll(); }}
              className="ml-1 rounded-full p-0.5 hover:bg-accent/20"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </button>
      </div>

      {/* Filter row */}
      {filtersOpen && (
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            value={typology}
            onChange={(e) => onTypologyChange(e.target.value)}
            placeholder="Tipologia (ex: T03)"
            className="rounded-lg border border-border bg-surface-card px-2.5 py-1.5 text-xs text-primary placeholder:text-placeholder outline-none focus:border-accent/50 w-32"
          />
          <select
            value={severity}
            onChange={(e) => onSeverityChange(e.target.value)}
            className="rounded-lg border border-border bg-surface-card px-2.5 py-1.5 text-xs text-primary outline-none focus:border-accent/50"
          >
            {SEVERITIES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
          <select
            value={sort}
            onChange={(e) => onSortChange(e.target.value)}
            className="rounded-lg border border-border bg-surface-card px-2.5 py-1.5 text-xs text-primary outline-none focus:border-accent/50"
          >
            {SORT_OPTIONS.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
          <input
            type="date"
            value={periodFrom}
            onChange={(e) => onPeriodFromChange(e.target.value)}
            className="rounded-lg border border-border bg-surface-card px-2.5 py-1.5 text-xs text-primary outline-none focus:border-accent/50"
          />
          <input
            type="date"
            value={periodTo}
            onChange={(e) => onPeriodToChange(e.target.value)}
            className="rounded-lg border border-border bg-surface-card px-2.5 py-1.5 text-xs text-primary outline-none focus:border-accent/50"
          />
        </div>
      )}
    </div>
  );
}
