"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getOrg } from "@/lib/api";
import { GraphView } from "@/components/GraphView";
import { DetailPageLayout } from "@/components/DetailPageLayout";
import { DetailHeader } from "@/components/DetailHeader";
import { DetailSkeleton } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { severityColor, formatBRL } from "@/lib/utils";
import { SEVERITY_LABELS } from "@/lib/constants";
import type { OrgSummary } from "@/lib/types";
import {
  Landmark,
  GitBranch,
  AlertTriangle,
  Search,
  FileText,
  BarChart3,
  ShieldCheck,
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
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <DetailSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
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
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
        <EmptyState
          icon={Search}
          title="Organização não encontrada"
          description="A organização solicitada não existe ou foi removida"
        />
      </div>
    );
  }

  // ── Aside ──────────────────────────────────────────────────────
  const aside = (
    <>
      {/* Identity */}
      <div className="rounded-lg border border-border bg-surface-card p-4 space-y-3">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-accent-subtle border border-accent/20">
            <Landmark className="h-6 w-6 text-accent" />
          </div>
          <div className="min-w-0">
            <h2 className="font-display text-sm font-bold text-primary truncate">{org.name}</h2>
            <p className="text-xs text-muted">Organização</p>
          </div>
        </div>

        {/* Identifiers */}
        {Object.keys(org.identifiers).length > 0 && (
          <div className="border-t border-border pt-3 space-y-2">
            {Object.entries(org.identifiers).map(([key, value]) => (
              <div key={key}>
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted">{key}</p>
                <p className="font-mono text-xs text-primary">{value}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Key stats */}
      <div className="rounded-lg border border-border bg-surface-card p-4 space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">Estatísticas</h3>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs text-secondary">
              <FileText className="h-3.5 w-3.5 text-accent" />
              Eventos
            </span>
            <span className="font-mono tabular-nums text-sm font-bold text-primary">
              {org.total_events}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs text-secondary">
              <AlertTriangle className="h-3.5 w-3.5 text-severity-high" />
              Sinais
            </span>
            <span className="font-mono tabular-nums text-sm font-bold text-primary">
              {org.total_signals}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs text-secondary">
              <ShieldCheck className="h-3.5 w-3.5 text-accent" />
              Score de Risco
            </span>
            <span className="font-mono tabular-nums text-sm font-bold text-primary">
              {org.risk_score != null ? org.risk_score.toFixed(0) : "—"}
            </span>
          </div>
          {org.total_contracts_value > 0 && (
            <div className="flex items-center justify-between border-t border-border pt-2">
              <span className="flex items-center gap-1.5 text-xs text-secondary">
                <BarChart3 className="h-3.5 w-3.5 text-accent" />
                Contratos
              </span>
              <span className="font-mono tabular-nums text-xs font-bold text-primary">
                {formatBRL(org.total_contracts_value)}
              </span>
            </div>
          )}
        </div>
      </div>
    </>
  );

  // ── Main ───────────────────────────────────────────────────────
  const main = (
    <>
      {/* Severity distribution */}
      {org.total_signals > 0 && org.severity_distribution && (
        <section>
          <h2 className="font-display flex items-center gap-2 text-sm font-semibold text-primary mb-3">
            <ShieldCheck className="h-4 w-4 text-accent" />
            Distribuição de Sinais por Severidade
          </h2>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
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
        </section>
      )}

      {/* Graph */}
      <section>
        <h2 className="font-display flex items-center gap-2 text-sm font-semibold text-primary mb-3">
          <GitBranch className="h-4 w-4 text-accent" />
          Grafo de Relacionamentos
        </h2>
        <div className="overflow-hidden rounded-lg border border-border bg-surface-card">
          <GraphView entityId={org.id} />
        </div>
      </section>
    </>
  );

  return (
    <DetailPageLayout
      header={
        <DetailHeader
          breadcrumbs={[{ label: "Radar", href: "/radar" }, { label: org.name }]}
          title={org.name}
          badge={
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-subtle">
              <Landmark className="h-4 w-4 text-accent" />
            </div>
          }
        />
      }
      aside={aside}
      main={main}
      maxWidth="6xl"
    />
  );
}
