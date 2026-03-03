"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getOrg } from "@/lib/api";
import { GraphView } from "@/components/GraphView";
import { Breadcrumb } from "@/components/Breadcrumb";
import { DetailSkeleton } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { severityColor, formatBRL } from "@/lib/utils";
import { SEVERITY_LABELS } from "@/lib/constants";
import type { OrgSummary } from "@/lib/types";
import {
  Landmark,
  Fingerprint,
  ShieldCheck,
  GitBranch,
  AlertTriangle,
  Search,
  BarChart3,
  FileText,
  Info,
  AlertCircle,
  ShieldAlert,
} from "lucide-react";

const SEVERITY_ICONS = {
  low: Info,
  medium: AlertCircle,
  high: AlertTriangle,
  critical: ShieldAlert,
} as const;

export default function OrgDetailPage() {
  const params = useParams();
  const [org, setOrg] = useState<OrgSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (params.id) {
      setLoading(true);
      setError(null);
      getOrg(params.id as string)
        .then(setOrg)
        .catch(() => setError("Erro ao carregar organização"))
        .finally(() => setLoading(false));
    }
  }, [params.id]);

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <DetailSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <EmptyState
          icon={AlertTriangle}
          title="Erro ao carregar organização"
          description={error}
        />
      </div>
    );
  }

  if (!org) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <EmptyState
          icon={Search}
          title="Organização não encontrada"
          description="A organização solicitada não existe ou foi removida"
        />
      </div>
    );
  }

  return (
    <div className="page-wrap">
      <div className="mx-auto max-w-5xl">
      <Breadcrumb
        items={[
          { label: "Radar", href: "/radar" },
          { label: org.name },
        ]}
      />

      <div className="mt-4 flex items-start gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gov-blue-100">
          <Landmark className="h-6 w-6 text-gov-blue-700" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gov-gray-900">{org.name}</h1>
          <p className="mt-0.5 text-sm text-gov-gray-500">Organização</p>
        </div>
      </div>

      {/* Summary stats */}
      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-gov-gray-200 bg-white p-4 text-center">
          <FileText className="mx-auto h-5 w-5 text-gov-blue-600" />
          <p className="mt-1 text-lg font-bold text-gov-gray-900">{org.total_events}</p>
          <p className="text-xs text-gov-gray-500">Eventos</p>
        </div>
        <div className="rounded-lg border border-gov-gray-200 bg-white p-4 text-center">
          <AlertTriangle className="mx-auto h-5 w-5 text-orange-500" />
          <p className="mt-1 text-lg font-bold text-gov-gray-900">{org.total_signals}</p>
          <p className="text-xs text-gov-gray-500">Sinais</p>
        </div>
        <div className="rounded-lg border border-gov-gray-200 bg-white p-4 text-center">
          <BarChart3 className="mx-auto h-5 w-5 text-gov-blue-600" />
          <p className="mt-1 text-lg font-bold text-gov-gray-900">
            {org.total_contracts_value > 0 ? formatBRL(org.total_contracts_value) : "—"}
          </p>
          <p className="text-xs text-gov-gray-500">Valor Contratos</p>
        </div>
        <div className="rounded-lg border border-gov-gray-200 bg-white p-4 text-center">
          <ShieldCheck className="mx-auto h-5 w-5 text-gov-blue-600" />
          <p className="mt-1 text-lg font-bold text-gov-gray-900">
            {org.risk_score != null ? org.risk_score.toFixed(0) : "—"}
          </p>
          <p className="text-xs text-gov-gray-500">Score de Risco</p>
        </div>
      </div>

      {Object.keys(org.identifiers).length > 0 && (
        <div className="mt-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
            <Fingerprint className="h-5 w-5 text-gov-blue-600" />
            Identificadores
          </h2>
          <dl className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {Object.entries(org.identifiers).map(([key, value]) => (
              <div key={key} className="rounded-lg bg-gov-gray-100 p-3">
                <dt className="text-xs font-medium uppercase text-gov-gray-500">
                  {key}
                </dt>
                <dd className="mt-0.5 font-mono text-sm text-gov-gray-900">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {/* Severity distribution */}
      {org.total_signals > 0 && org.severity_distribution && (
        <div className="mt-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
            <ShieldCheck className="h-5 w-5 text-gov-blue-600" />
            Distribuição de Sinais por Severidade
          </h2>
          <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {(["critical", "high", "medium", "low"] as const).map((sev) => {
              const count = org.severity_distribution[sev] ?? 0;
              if (count === 0) return null;
              const SevIcon = SEVERITY_ICONS[sev];
              return (
                <div key={sev} className={`flex items-center gap-2 rounded-lg p-3 ${severityColor(sev)}`}>
                  <SevIcon className="h-4 w-4" />
                  <span className="text-sm font-semibold">{count}</span>
                  <span className="text-xs">{SEVERITY_LABELS[sev]}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Graph */}
      <div className="mt-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
          <GitBranch className="h-5 w-5 text-gov-blue-600" />
          Grafo de Relacionamentos
        </h2>
        <div className="mt-2 overflow-hidden rounded-lg border border-gov-gray-200 bg-white">
          <GraphView entityId={org.id} />
        </div>
      </div>
      </div>
    </div>
  );
}
