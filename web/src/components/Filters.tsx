"use client";

import { TYPOLOGY_LABELS, SEVERITY_LABELS } from "@/lib/constants";
import { Filter, X } from "lucide-react";

interface FiltersProps {
  typology: string;
  severity: string;
  onTypologyChange: (value: string) => void;
  onSeverityChange: (value: string) => void;
}

export function Filters({
  typology,
  severity,
  onTypologyChange,
  onSeverityChange,
}: FiltersProps) {
  const hasFilters = typology || severity;

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-1.5 text-sm text-gov-gray-500">
        <Filter className="h-4 w-4" />
        <span>Filtros</span>
      </div>

      <select
        value={typology}
        onChange={(e) => onTypologyChange(e.target.value)}
        className="rounded-md border border-gov-gray-300 bg-white px-3 py-2 text-sm focus:border-gov-blue-500 focus:outline-none focus:ring-1 focus:ring-gov-blue-500"
      >
        <option value="">Todas as tipologias</option>
        {Object.entries(TYPOLOGY_LABELS).map(([code, label]) => (
          <option key={code} value={code}>
            {code} — {label}
          </option>
        ))}
      </select>

      <select
        value={severity}
        onChange={(e) => onSeverityChange(e.target.value)}
        className="rounded-md border border-gov-gray-300 bg-white px-3 py-2 text-sm focus:border-gov-blue-500 focus:outline-none focus:ring-1 focus:ring-gov-blue-500"
      >
        <option value="">Todas as severidades</option>
        {Object.entries(SEVERITY_LABELS).map(([key, label]) => (
          <option key={key} value={key}>
            {label}
          </option>
        ))}
      </select>

      {hasFilters && (
        <button
          onClick={() => {
            onTypologyChange("");
            onSeverityChange("");
          }}
          className="flex items-center gap-1 rounded-md px-2 py-1.5 text-xs text-gov-gray-500 transition hover:bg-gov-gray-100"
        >
          <X className="h-3 w-3" />
          Limpar
        </button>
      )}
    </div>
  );
}
