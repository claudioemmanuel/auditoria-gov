"use client";

import { useState } from "react";
import { CORRUPTION_TYPE_LABELS, SEVERITY_LABELS, SPHERE_LABELS, TYPOLOGY_LABELS } from "@/lib/constants";
import type { RadarViewMode } from "@/components/radar/RadarViewTabs";
import { cn } from "@/lib/utils";
import { CalendarRange, Filter, Globe, Scale, SlidersHorizontal, X } from "lucide-react";

interface RadarFilterPanelProps {
  view: RadarViewMode;
  typology: string;
  severity: string;
  periodFrom: string;
  periodTo: string;
  corruptionType: string;
  sphere: string;
  onTypologyChange: (value: string) => void;
  onSeverityChange: (value: string) => void;
  onPeriodFromChange: (value: string) => void;
  onPeriodToChange: (value: string) => void;
  onCorruptionTypeChange: (value: string) => void;
  onSphereChange: (value: string) => void;
  onClearAll: () => void;
}

export function RadarFilterPanel({
  typology,
  severity,
  periodFrom,
  periodTo,
  corruptionType,
  sphere,
  onTypologyChange,
  onSeverityChange,
  onPeriodFromChange,
  onPeriodToChange,
  onCorruptionTypeChange,
  onSphereChange,
  onClearAll,
}: RadarFilterPanelProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const hasFilters = Boolean(typology || severity || periodFrom || periodTo || corruptionType || sphere);

  const severities = ["critical", "high", "medium", "low"] as const;

  const panelContent = (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Filter className="h-3.5 w-3.5 text-gov-blue-700" />
          <span className="text-xs font-semibold uppercase tracking-wider text-gov-gray-600">Filtros</span>
        </div>
        {hasFilters && (
          <button
            type="button"
            onClick={onClearAll}
            className="inline-flex items-center gap-1 text-xs text-gov-blue-700 hover:underline"
          >
            <X className="h-3 w-3" />
            Limpar
          </button>
        )}
      </div>

      {/* Tipologia */}
      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-medium text-gov-gray-600">Tipologia</label>
        <select
          value={typology}
          onChange={(e) => onTypologyChange(e.target.value)}
          className="w-full rounded-md border border-gov-gray-200 bg-white px-2.5 py-2 text-xs text-gov-gray-900 outline-none focus:border-gov-blue-700 focus:ring-1 focus:ring-gov-blue-700"
        >
          <option value="">Todas</option>
          {Object.entries(TYPOLOGY_LABELS).map(([code, label]) => (
            <option key={code} value={code}>
              {code} – {label}
            </option>
          ))}
        </select>
      </div>

      {/* Severidade */}
      <div className="flex flex-col gap-2">
        <label className="text-xs font-medium text-gov-gray-600">Severidade</label>
        <div className="flex flex-col gap-1">
          {severities.map((sev) => {
            const dotMap: Record<string, string> = {
              critical: "bg-severity-critical",
              high: "bg-severity-high",
              medium: "bg-severity-medium",
              low: "bg-severity-low",
            };
            const isSelected = severity === sev;
            return (
              <button
                key={sev}
                type="button"
                onClick={() => onSeverityChange(isSelected ? "" : sev)}
                className={cn(
                  "flex items-center gap-2 rounded-md px-2 py-1.5 text-xs transition",
                  isSelected
                    ? "bg-gov-blue-50 text-gov-blue-700 font-medium"
                    : "text-gov-gray-900 hover:bg-gov-gray-50",
                )}
              >
                <span className={cn("h-2 w-2 rounded-full flex-shrink-0", dotMap[sev])} />
                {SEVERITY_LABELS[sev]}
              </button>
            );
          })}
        </div>
      </div>

      {/* Periodo */}
      <div className="flex flex-col gap-1.5">
        <label className="flex items-center gap-1.5 text-xs font-medium text-gov-gray-600">
          <CalendarRange className="h-3.5 w-3.5" />
          Período
        </label>
        <input
          type="date"
          value={periodFrom}
          onChange={(e) => onPeriodFromChange(e.target.value)}
          placeholder="De"
          className="w-full rounded-md border border-gov-gray-200 bg-white px-2.5 py-1.5 text-xs text-gov-gray-900 outline-none focus:border-gov-blue-700 focus:ring-1 focus:ring-gov-blue-700"
        />
        <input
          type="date"
          value={periodTo}
          onChange={(e) => onPeriodToChange(e.target.value)}
          placeholder="Até"
          className="w-full rounded-md border border-gov-gray-200 bg-white px-2.5 py-1.5 text-xs text-gov-gray-900 outline-none focus:border-gov-blue-700 focus:ring-1 focus:ring-gov-blue-700"
        />
      </div>

      {/* Tipo de Corrupção */}
      <div className="flex flex-col gap-1.5">
        <label className="flex items-center gap-1.5 text-xs font-medium text-gov-gray-600">
          <Scale className="h-3.5 w-3.5" />
          Tipo de Corrupção
        </label>
        <select
          value={corruptionType}
          onChange={(e) => onCorruptionTypeChange(e.target.value)}
          className="w-full rounded-md border border-gov-gray-200 bg-white px-2.5 py-2 text-xs text-gov-gray-900 outline-none focus:border-gov-blue-700 focus:ring-1 focus:ring-gov-blue-700"
        >
          <option value="">Todos</option>
          {Object.entries(CORRUPTION_TYPE_LABELS).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {/* Esfera */}
      <div className="flex flex-col gap-1.5">
        <label className="flex items-center gap-1.5 text-xs font-medium text-gov-gray-600">
          <Globe className="h-3.5 w-3.5" />
          Esfera
        </label>
        <select
          value={sphere}
          onChange={(e) => onSphereChange(e.target.value)}
          className="w-full rounded-md border border-gov-gray-200 bg-white px-2.5 py-2 text-xs text-gov-gray-900 outline-none focus:border-gov-blue-700 focus:ring-1 focus:ring-gov-blue-700"
        >
          <option value="">Todas</option>
          {Object.entries(SPHERE_LABELS).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {hasFilters && (
        <button
          type="button"
          onClick={onClearAll}
          className="mt-1 w-full rounded-md border border-gov-gray-200 bg-gov-gray-50 py-2 text-xs font-medium text-gov-gray-600 transition hover:bg-gov-gray-100"
        >
          Limpar filtros
        </button>
      )}
    </div>
  );

  return (
    <>
      {/* Mobile toggle button */}
      <div className="lg:hidden">
        <button
          type="button"
          onClick={() => setMobileOpen((v) => !v)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gov-gray-200 bg-white px-3 py-2 text-xs font-medium text-gov-gray-600 shadow-sm"
        >
          <SlidersHorizontal className="h-3.5 w-3.5" />
          Filtros
          {hasFilters && (
            <span className="ml-1 flex h-4 w-4 items-center justify-center rounded-full bg-gov-blue-700 text-[10px] font-semibold text-white">
              {[typology, severity, periodFrom || periodTo, corruptionType, sphere].filter(Boolean).length}
            </span>
          )}
        </button>

        {mobileOpen && (
          <div className="mt-2 rounded-xl border border-gov-gray-200 bg-white p-4 shadow-sm">
            {panelContent}
          </div>
        )}
      </div>

      {/* Desktop sidebar panel */}
      <aside className="hidden lg:flex lg:w-56 lg:flex-shrink-0 lg:flex-col">
        <div className="rounded-xl border border-gov-gray-200 bg-white p-4 shadow-sm">
          {panelContent}
        </div>
      </aside>
    </>
  );
}
