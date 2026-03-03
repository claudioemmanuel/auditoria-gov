"use client";

import { Database } from "lucide-react";
import { formatDateTime } from "@/lib/utils";

interface CoverageHeaderProps {
  snapshotAt?: string | null;
}

export function CoverageHeader({ snapshotAt }: CoverageHeaderProps) {
  return (
    <div className="mt-4 flex items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        <div className="rounded-xl border border-border bg-accent-subtle p-2">
          <Database className="h-6 w-6 text-accent" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-primary">Cobertura de Dados</h1>
          <p className="text-sm text-muted">
            Visao investigativa da saude do pipeline e da qualidade operacional por fonte.
          </p>
        </div>
      </div>
      <div className="rounded-lg border border-border bg-surface-card px-3 py-2 text-right">
        <p className="text-xs font-medium uppercase tracking-wide text-muted">Snapshot</p>
        <p className="mt-1 font-mono tabular-nums text-sm font-medium text-primary">
          {snapshotAt ? formatDateTime(snapshotAt) : "Aguardando dados"}
        </p>
      </div>
    </div>
  );
}
