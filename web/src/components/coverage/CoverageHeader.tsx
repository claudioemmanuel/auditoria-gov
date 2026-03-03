"use client";

import { Database } from "lucide-react";

interface CoverageHeaderProps {
  snapshotAt?: string | null;
}

export function CoverageHeader({ snapshotAt }: CoverageHeaderProps) {
  return (
    <div className="mt-4 flex items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        <div className="rounded-xl border border-gov-blue-200 bg-gov-blue-50 p-2">
          <Database className="h-6 w-6 text-gov-blue-700" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gov-gray-900">Cobertura de Dados v2</h1>
          <p className="text-sm text-gov-gray-500">
            Visao investigativa da saude do pipeline e da qualidade operacional por fonte.
          </p>
        </div>
      </div>
      <div className="rounded-lg border border-gov-gray-200 bg-white px-3 py-2 text-right">
        <p className="text-xs font-medium uppercase tracking-wide text-gov-gray-500">Snapshot</p>
        <p className="mt-1 text-sm font-medium text-gov-gray-800">
          {snapshotAt ? new Date(snapshotAt).toLocaleString("pt-BR") : "Aguardando dados"}
        </p>
      </div>
    </div>
  );
}
