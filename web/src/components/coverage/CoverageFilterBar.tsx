"use client";

import type { CoverageStatus } from "@/lib/types";

export interface CoverageFilterState {
  q: string;
  status: "" | CoverageStatus;
  domain: string;
  enabledOnly: boolean;
  sort: "status_desc" | "name_asc" | "freshness_desc" | "jobs_desc";
}

interface CoverageFilterBarProps {
  value: CoverageFilterState;
  domains: string[];
  onChange: (next: CoverageFilterState) => void;
}

const STATUS_OPTIONS: Array<{ value: "" | CoverageStatus; label: string }> = [
  { value: "", label: "Todos os status" },
  { value: "ok", label: "OK" },
  { value: "warning", label: "Atencao" },
  { value: "stale", label: "Desatualizado" },
  { value: "error", label: "Erro" },
  { value: "pending", label: "Pendente" },
];

const selectCls =
  "rounded-lg border border-border bg-surface-base px-3 py-2 text-sm text-primary focus:border-accent focus:outline-none";

export function CoverageFilterBar({ value, domains, onChange }: CoverageFilterBarProps) {
  return (
    <div className="rounded-xl border border-border bg-surface-card p-3">
      <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-5">
        <input
          type="text"
          value={value.q}
          onChange={(event) => onChange({ ...value, q: event.target.value })}
          placeholder="Buscar fonte, job ou dominio..."
          className="rounded-lg border border-border bg-surface-base px-3 py-2 text-sm text-primary placeholder:text-muted focus:border-accent focus:outline-none"
        />
        <select
          value={value.status}
          onChange={(event) =>
            onChange({ ...value, status: event.target.value as CoverageFilterState["status"] })
          }
          className={selectCls}
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value || "all"} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select
          value={value.domain}
          onChange={(event) => onChange({ ...value, domain: event.target.value })}
          className={selectCls}
        >
          <option value="">Todos os dominios</option>
          {domains.map((domain) => (
            <option key={domain} value={domain}>
              {domain}
            </option>
          ))}
        </select>
        <select
          value={value.sort}
          onChange={(event) =>
            onChange({ ...value, sort: event.target.value as CoverageFilterState["sort"] })
          }
          className={selectCls}
        >
          <option value="status_desc">Ordenar por status</option>
          <option value="name_asc">Ordenar por nome</option>
          <option value="freshness_desc">Maior defasagem</option>
          <option value="jobs_desc">Mais jobs</option>
        </select>
        <label className="flex items-center gap-2 rounded-lg border border-border bg-surface-base px-3 py-2 text-sm text-secondary">
          <input
            type="checkbox"
            checked={value.enabledOnly}
            onChange={(event) => onChange({ ...value, enabledOnly: event.target.checked })}
            className="h-4 w-4 rounded border-border text-accent focus:ring-accent"
          />
          Apenas jobs habilitados
        </label>
      </div>
    </div>
  );
}
