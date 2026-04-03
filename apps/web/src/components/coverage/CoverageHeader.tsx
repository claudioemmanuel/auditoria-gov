"use client";

import { Database, RadioTower } from "lucide-react";
import { formatDateTime } from "@/lib/utils";

interface CoverageHeaderProps {
  snapshotAt?: string | null;
}

export function CoverageHeader({ snapshotAt }: CoverageHeaderProps) {
  return (
    <div className="mt-4 ow-card ow-card-glass ow-card-signal p-4 md:p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl border border-[color:var(--color-brand-border)] bg-[color:var(--color-brand-dim)] p-2 shadow-[var(--shadow-brand)]">
            <Database className="h-6 w-6 text-[var(--color-brand-light)]" />
          </div>
          <div>
            <div className="mb-1 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-brand-light)]">
              <RadioTower className="h-3.5 w-3.5" />
              Pipeline observability
            </div>
            <h1 className="text-2xl font-bold text-[var(--color-text)]">Cobertura de Dados</h1>
            <p className="text-sm text-[var(--color-text-2)]">
              Saúde do pipeline, latência operacional e qualidade por fonte investigada.
            </p>
          </div>
        </div>
        <div className="rounded-lg border border-[color:var(--color-brand-border)] bg-[color:rgba(8,39,43,0.35)] px-3 py-2 text-right">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-3)]">Snapshot</p>
          <p className="mt-1 font-mono tabular-nums text-sm font-medium text-[var(--color-text)]">
            {snapshotAt ? formatDateTime(snapshotAt) : "Aguardando dados"}
          </p>
        </div>
      </div>
    </div>
  );
}
