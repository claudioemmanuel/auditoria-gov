"use client";

import { CORRUPTION_TYPE_LABELS, SEVERITY_LABELS, SPHERE_LABELS, TYPOLOGY_LABELS } from "@/lib/constants";
import type { RadarViewMode } from "@/components/radar/RadarViewTabs";
import { ArrowUpDown, CalendarRange, Filter, Globe, Scale, X } from "lucide-react";

interface RadarFilterBarProps {
  view: RadarViewMode;
  typology: string;
  severity: string;
  sort: "analysis_date" | "ingestion_date";
  periodFrom: string;
  periodTo: string;
  corruptionType: string;
  sphere: string;
  onTypologyChange: (value: string) => void;
  onSeverityChange: (value: string) => void;
  onSortChange: (value: "analysis_date" | "ingestion_date") => void;
  onPeriodFromChange: (value: string) => void;
  onPeriodToChange: (value: string) => void;
  onCorruptionTypeChange: (value: string) => void;
  onSphereChange: (value: string) => void;
  onClearAll: () => void;
}

export function RadarFilterBar({
  view,
  typology,
  severity,
  sort,
  periodFrom,
  periodTo,
  corruptionType,
  sphere,
  onTypologyChange,
  onSeverityChange,
  onSortChange,
  onPeriodFromChange,
  onPeriodToChange,
  onCorruptionTypeChange,
  onSphereChange,
  onClearAll,
}: RadarFilterBarProps) {
  const hasFilters = Boolean(
    typology || severity || periodFrom || periodTo || corruptionType || sphere,
  );

  return (
    <div className="surface-card mt-6 p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-sm text-gov-gray-700">
          <Filter className="h-4 w-4 text-gov-blue-600" />
          <span className="font-semibold">Filtros investigativos</span>
        </div>
        {hasFilters && (
          <button
            type="button"
            onClick={onClearAll}
            className="inline-flex items-center gap-1 text-sm text-gov-blue-700 hover:underline"
          >
            <X className="h-3.5 w-3.5" />
            Limpar todos
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2 xl:grid-cols-3">
        <select
          value={typology}
          onChange={(event) => onTypologyChange(event.target.value)}
          className="rounded-lg border border-gov-gray-300/90 bg-white px-3 py-2 text-sm"
        >
          <option value="">Todas as tipologias</option>
          {Object.entries(TYPOLOGY_LABELS).map(([code, label]) => (
            <option key={code} value={code}>
              {code} - {label}
            </option>
          ))}
        </select>

        <select
          value={severity}
          onChange={(event) => onSeverityChange(event.target.value)}
          className="rounded-lg border border-gov-gray-300/90 bg-white px-3 py-2 text-sm"
        >
          <option value="">Todas as severidades</option>
          {Object.entries(SEVERITY_LABELS).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>

        {view === "signals" ? (
          <div className="flex items-center gap-2 rounded-lg border border-gov-gray-300/90 px-3 py-2">
            <ArrowUpDown className="h-4 w-4 text-gov-gray-400" />
            <select
              value={sort}
              onChange={(event) => onSortChange(event.target.value as "analysis_date" | "ingestion_date")}
              className="w-full border-none bg-transparent text-sm text-gov-gray-700 outline-none"
            >
              <option value="analysis_date">Ordenar por data de análise</option>
              <option value="ingestion_date">Ordenar por data de ingestão</option>
            </select>
          </div>
        ) : (
          <div className="rounded-lg border border-gov-gray-200 bg-gov-gray-50/80 px-3 py-2 text-sm text-gov-gray-600">
            A ordenação dos casos usa prioridade temporal do caso consolidado.
          </div>
        )}
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2 xl:grid-cols-4">
        <label className="flex items-center gap-2 rounded-lg border border-gov-gray-300/90 px-3 py-2">
          <CalendarRange className="h-4 w-4 text-gov-gray-400" />
          <input
            type="date"
            value={periodFrom}
            onChange={(event) => onPeriodFromChange(event.target.value)}
            className="w-full border-none bg-transparent text-sm text-gov-gray-700 outline-none"
          />
        </label>
        <label className="flex items-center gap-2 rounded-lg border border-gov-gray-300/90 px-3 py-2">
          <CalendarRange className="h-4 w-4 text-gov-gray-400" />
          <input
            type="date"
            value={periodTo}
            onChange={(event) => onPeriodToChange(event.target.value)}
            className="w-full border-none bg-transparent text-sm text-gov-gray-700 outline-none"
          />
        </label>
        <label className="flex items-center gap-2 rounded-lg border border-gov-gray-300/90 px-3 py-2">
          <Scale className="h-4 w-4 text-gov-gray-400" />
          <select
            value={corruptionType}
            onChange={(event) => onCorruptionTypeChange(event.target.value)}
            className="w-full border-none bg-transparent text-sm text-gov-gray-700 outline-none"
          >
            <option value="">Todos os tipos de corrupção</option>
            {Object.entries(CORRUPTION_TYPE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 rounded-lg border border-gov-gray-300/90 px-3 py-2">
          <Globe className="h-4 w-4 text-gov-gray-400" />
          <select
            value={sphere}
            onChange={(event) => onSphereChange(event.target.value)}
            className="w-full border-none bg-transparent text-sm text-gov-gray-700 outline-none"
          >
            <option value="">Todas as esferas</option>
            {Object.entries(SPHERE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </div>
  );
}
