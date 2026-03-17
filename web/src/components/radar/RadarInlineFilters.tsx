"use client";

import { useEffect, useRef, useState } from "react";
import { Search, SlidersHorizontal, X, ShieldCheck } from "lucide-react";
import {
  CORRUPTION_TYPE_LABELS,
  SPHERE_LABELS,
  TYPOLOGY_LABELS,
} from "@/lib/constants";

interface RadarInlineFiltersProps {
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
  onCoverageClick: () => void;
}

export function RadarInlineFilters({
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
  onCoverageClick,
}: RadarInlineFiltersProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const activeCount = [typology, periodFrom, periodTo, corruptionType, sphere].filter(Boolean).length;

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  const chips: { label: string; onRemove: () => void }[] = [];
  if (typology) chips.push({ label: typology, onRemove: () => onTypologyChange("") });
  if (periodFrom) chips.push({ label: `De ${periodFrom}`, onRemove: () => onPeriodFromChange("") });
  if (periodTo) chips.push({ label: `Até ${periodTo}`, onRemove: () => onPeriodToChange("") });
  if (corruptionType) chips.push({ label: CORRUPTION_TYPE_LABELS[corruptionType] ?? corruptionType, onRemove: () => onCorruptionTypeChange("") });
  if (sphere) chips.push({ label: SPHERE_LABELS[sphere] ?? sphere, onRemove: () => onSphereChange("") });

  return (
    <div ref={ref} className="relative flex flex-wrap items-center gap-2">
      {/* Search */}
      <label className="flex items-center gap-2 rounded-lg border border-border bg-surface-card px-3 py-1.5">
        <Search className="h-3.5 w-3.5 text-muted shrink-0" />
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Buscar casos..."
          className="w-36 bg-transparent text-xs text-primary outline-none placeholder:text-placeholder"
        />
        {search && (
          <button type="button" onClick={() => onSearchChange("")} className="text-muted hover:text-primary">
            <X className="h-3 w-3" />
          </button>
        )}
      </label>

      {/* Active filter chips */}
      {chips.map((chip) => (
        <span
          key={chip.label}
          className="inline-flex items-center gap-1 rounded-full border border-accent/30 bg-accent-subtle px-2 py-0.5 text-[10px] font-semibold text-accent"
        >
          {chip.label}
          <button type="button" onClick={chip.onRemove} className="ml-0.5 rounded-full hover:text-error transition-colors">
            <X className="h-2.5 w-2.5" />
          </button>
        </span>
      ))}

      {/* Clear all */}
      {activeCount > 0 && (
        <button type="button" onClick={onClearAll} className="text-[10px] text-muted hover:text-error transition-colors">
          Limpar tudo
        </button>
      )}

      {/* Filtros dropdown button */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
          open
            ? "border-accent bg-accent-subtle text-accent"
            : "border-border bg-surface-card text-secondary hover:border-accent/40"
        }`}
      >
        <SlidersHorizontal className="h-3.5 w-3.5" />
        Filtros
        {activeCount > 0 && (
          <span className="ml-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-accent text-[9px] font-bold text-white">
            {activeCount}
          </span>
        )}
      </button>

      {/* Coverage button */}
      <button
        type="button"
        onClick={onCoverageClick}
        className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-card px-3 py-1.5 text-xs font-medium text-secondary transition-colors hover:border-accent/40"
      >
        <ShieldCheck className="h-3.5 w-3.5" />
        Cobertura
      </button>

      {/* Dropdown popover — anchored right */}
      {open && (
        <div className="absolute right-0 top-full z-30 mt-2 w-[640px] max-w-[calc(100vw-2rem)] rounded-xl border border-border bg-surface-card shadow-lg">
          <div className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-3">
            {/* Tipologia */}
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-muted">Tipologia</label>
              <select
                value={typology}
                onChange={(e) => onTypologyChange(e.target.value)}
                className="w-full rounded-md border border-border bg-surface-base px-2 py-1.5 text-xs text-primary focus:outline-none focus:ring-1 focus:ring-accent"
              >
                <option value="">Todas</option>
                {Object.entries(TYPOLOGY_LABELS).map(([code, label]) => (
                  <option key={code} value={code}>{code} — {label}</option>
                ))}
              </select>
            </div>

            {/* Tipo de Corrupção */}
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-muted">Tipo de Corrupção</label>
              <select
                value={corruptionType}
                onChange={(e) => onCorruptionTypeChange(e.target.value)}
                className="w-full rounded-md border border-border bg-surface-base px-2 py-1.5 text-xs text-primary focus:outline-none focus:ring-1 focus:ring-accent"
              >
                <option value="">Todos</option>
                {Object.entries(CORRUPTION_TYPE_LABELS).map(([code, label]) => (
                  <option key={code} value={code}>{label}</option>
                ))}
              </select>
            </div>

            {/* Esfera */}
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-muted">Esfera</label>
              <select
                value={sphere}
                onChange={(e) => onSphereChange(e.target.value)}
                className="w-full rounded-md border border-border bg-surface-base px-2 py-1.5 text-xs text-primary focus:outline-none focus:ring-1 focus:ring-accent"
              >
                <option value="">Todas</option>
                {Object.entries(SPHERE_LABELS).map(([code, label]) => (
                  <option key={code} value={code}>{label}</option>
                ))}
              </select>
            </div>

            {/* Período De */}
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-muted">Período — De</label>
              <input
                type="date"
                value={periodFrom}
                onChange={(e) => onPeriodFromChange(e.target.value)}
                className="w-full rounded-md border border-border bg-surface-base px-2 py-1.5 text-xs text-primary focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>

            {/* Período Até */}
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-muted">Período — Até</label>
              <input
                type="date"
                value={periodTo}
                onChange={(e) => onPeriodToChange(e.target.value)}
                className="w-full rounded-md border border-border bg-surface-base px-2 py-1.5 text-xs text-primary focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
