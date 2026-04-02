"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getOrg } from "@/lib/api";
import { GraphView } from "@/components/GraphView";
import { DetailSkeleton } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { formatBRL } from "@/lib/utils";
import { SEVERITY_LABELS } from "@/lib/constants";
import type { OrgSummary } from "@/lib/types";
import {
  Landmark,
  AlertTriangle,
  Search,
  FileText,
  BarChart3,
  ShieldCheck,
  Info,
  AlertCircle,
  ShieldAlert,
  ChevronRight,
  Users,
  Layers,
} from "lucide-react";
import { clsx } from "clsx";

type Tab = "sinais" | "contratos" | "fornecedores" | "tipologias";

const TABS: { id: Tab; label: string }[] = [
  { id: "sinais", label: "Sinais" },
  { id: "contratos", label: "Contratos" },
  { id: "fornecedores", label: "Fornecedores" },
  { id: "tipologias", label: "Tipologias" },
];

const SEVERITY_ORDER = ["critical", "high", "medium", "low"] as const;

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
  const [activeTab, setActiveTab] = useState<Tab>("sinais");

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

  const identifierEntries = Object.entries(org.identifiers);
  const uf =
    (org.attrs?.uf as string | undefined) ??
    org.identifiers?.uf ??
    (org.attrs?.state as string | undefined);
  const highRiskCount =
    (org.severity_distribution?.critical ?? 0) +
    (org.severity_distribution?.high ?? 0);

  return (
    <div className="animate-slide-up mx-auto max-w-6xl px-4 py-6 sm:px-6 space-y-5">

      {/* ── Breadcrumb ─────────────────────────────────────────────── */}
      <nav className="flex items-center gap-1.5" style={{ color: "var(--color-text-3)" }}>
        <Link
          href="/radar"
          className="text-mono-xs transition-colors hover:text-[var(--color-amber-text)]"
        >
          Radar
        </Link>
        <ChevronRight className="h-3 w-3 opacity-40" />
        <Link
          href="/orgaos"
          className="text-mono-xs transition-colors hover:text-[var(--color-amber-text)]"
        >
          Órgãos
        </Link>
        <ChevronRight className="h-3 w-3 opacity-40" />
        <span
          className="text-mono-xs max-w-xs truncate"
          style={{ color: "var(--color-text-2)" }}
        >
          {org.name}
        </span>
      </nav>

      {/* ── Org Header Card ────────────────────────────────────────── */}
      <div className="ow-card">

        {/* Identity row */}
        <div className="ow-card-section flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-4">
            <div
              className="shrink-0 flex items-center justify-center h-16 w-16"
              style={{
                background: "var(--color-amber-dim)",
                border: "1px solid var(--color-amber-border)",
              }}
            >
              <Landmark className="h-8 w-8" style={{ color: "var(--color-amber)" }} />
            </div>

            <div className="min-w-0 space-y-2">
              <h1 className="text-display-lg leading-tight" style={{ color: "var(--color-text)" }}>
                {org.name}
              </h1>
              <div className="flex flex-wrap items-center gap-2">
                <span className="ow-badge ow-badge-neutral">
                  {org.type ?? "Órgão"}
                </span>
                {uf && (
                  <span className="ow-badge ow-badge-info">{uf}</span>
                )}
              </div>
              {identifierEntries.length > 0 && (
                <div className="flex flex-wrap gap-x-6 gap-y-1.5 pt-1">
                  {identifierEntries.map(([key, value]) => (
                    <div key={key} className="flex items-baseline gap-1.5">
                      <span
                        className="text-mono-xs uppercase tracking-widest"
                        style={{ color: "var(--color-text-3)" }}
                      >
                        {key}
                      </span>
                      <span className="ow-id">{value}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Risk Metrics Strip */}
        <div
          className="grid grid-cols-2 gap-px sm:grid-cols-4"
          style={{ background: "var(--color-border)" }}
        >
          {/* Total Sinais */}
          <div
            className="flex flex-col gap-1.5 px-5 py-4"
            style={{ background: "var(--color-surface)" }}
          >
            <span
              className="text-mono-xs uppercase tracking-widest"
              style={{ color: "var(--color-text-3)" }}
            >
              Total Sinais
            </span>
            <span
              className="text-display-md tabular-nums leading-none"
              style={{
                fontFamily: "var(--font-mono)",
                color: "var(--color-amber)",
              }}
            >
              {org.total_signals}
            </span>
          </div>

          {/* Total Contratos */}
          <div
            className="flex flex-col gap-1.5 px-5 py-4"
            style={{ background: "var(--color-surface)" }}
          >
            <span
              className="text-mono-xs uppercase tracking-widest"
              style={{ color: "var(--color-text-3)" }}
            >
              Total Contratos
            </span>
            <span
              className="text-display-md tabular-nums leading-none"
              style={{
                fontFamily: "var(--font-mono)",
                color: "var(--color-text)",
              }}
            >
              {org.total_contracts_value > 0
                ? formatBRL(org.total_contracts_value)
                : "—"}
            </span>
          </div>

          {/* Score de Risco */}
          <div
            className="flex flex-col gap-1.5 px-5 py-4"
            style={{ background: "var(--color-surface)" }}
          >
            <span
              className="text-mono-xs uppercase tracking-widest"
              style={{ color: "var(--color-text-3)" }}
            >
              Score de Risco
            </span>
            <span
              className="text-display-md tabular-nums leading-none"
              style={{
                fontFamily: "var(--font-mono)",
                color:
                  org.risk_score != null && org.risk_score > 70
                    ? "var(--color-critical)"
                    : org.risk_score != null && org.risk_score > 40
                    ? "var(--color-high)"
                    : "var(--color-text)",
              }}
            >
              {org.risk_score != null ? org.risk_score.toFixed(0) : "—"}
            </span>
          </div>

          {/* Alto Risco */}
          <div
            className="flex flex-col gap-1.5 px-5 py-4"
            style={{ background: "var(--color-surface)" }}
          >
            <span
              className="text-mono-xs uppercase tracking-widest"
              style={{ color: "var(--color-text-3)" }}
            >
              Alto Risco
            </span>
            <span
              className="text-display-md tabular-nums leading-none"
              style={{
                fontFamily: "var(--font-mono)",
                color: highRiskCount > 0 ? "var(--color-high)" : "var(--color-text)",
              }}
            >
              {highRiskCount}
            </span>
            <span className="text-mono-xs" style={{ color: "var(--color-text-3)" }}>
              crítico + alto
            </span>
          </div>
        </div>

        {/* Stats footer strip */}
        <div
          className="ow-card-section flex flex-wrap items-center gap-3 text-mono-xs"
          style={{ color: "var(--color-text-3)", background: "var(--color-surface-2)" }}
        >
          <span>
            <span
              className="tabular-nums font-semibold"
              style={{ color: "var(--color-text-2)" }}
            >
              {org.total_events}
            </span>{" "}
            evento{org.total_events !== 1 ? "s" : ""}
          </span>
          <span aria-hidden>·</span>
          <span>
            <span
              className="tabular-nums font-semibold"
              style={{ color: "var(--color-text-2)" }}
            >
              {org.total_signals}
            </span>{" "}
            sinal{org.total_signals !== 1 ? "is" : ""}
          </span>
          {org.total_contracts_value > 0 && (
            <>
              <span aria-hidden>·</span>
              <span>
                <span
                  className="tabular-nums font-semibold"
                  style={{ color: "var(--color-amber-text)" }}
                >
                  {formatBRL(org.total_contracts_value)}
                </span>{" "}
                em contratos
              </span>
            </>
          )}
        </div>
      </div>

      {/* ── Tabs ───────────────────────────────────────────────────── */}
      <div className="ow-card">

        {/* Tab nav */}
        <div
          className="flex overflow-x-auto border-b"
          style={{ borderColor: "var(--color-border)" }}
        >
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  "shrink-0 border-b-2 px-5 py-3.5 text-mono-sm transition-colors -mb-px",
                  isActive
                    ? "border-[var(--color-amber)]"
                    : "border-transparent hover:border-[var(--color-border-strong)]",
                )}
                style={{
                  color: isActive
                    ? "var(--color-amber-text)"
                    : "var(--color-text-3)",
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab panels */}
        <div className="ow-card-section">

          {/* ── Sinais ── */}
          {activeTab === "sinais" && (
            <div className="space-y-6">
              {org.total_signals > 0 && org.severity_distribution ? (
                <div className="space-y-3">
                  <p
                    className="text-mono-xs uppercase tracking-widest"
                    style={{ color: "var(--color-text-3)" }}
                  >
                    Distribuição por Severidade
                  </p>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {SEVERITY_ORDER.map((sev) => {
                      const count = org.severity_distribution[sev] ?? 0;
                      const SevIcon = SEVERITY_ICONS[sev];
                      return (
                        <div
                          key={sev}
                          className={`ow-signal-card ow-signal-card-${sev} flex flex-col gap-2 px-4 py-3`}
                        >
                          <div className="flex items-center gap-1.5">
                            <SevIcon className="h-3.5 w-3.5" />
                            <span className="text-mono-xs uppercase tracking-widest">
                              {SEVERITY_LABELS[sev]}
                            </span>
                          </div>
                          <span
                            className="text-display-md tabular-nums leading-none"
                            style={{ fontFamily: "var(--font-mono)" }}
                          >
                            {count}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <EmptyState
                  icon={ShieldCheck}
                  title="Nenhum sinal registrado"
                  description="Esta organização não possui sinais de risco identificados."
                />
              )}

              <div>
                <p
                  className="mb-3 text-mono-xs uppercase tracking-widest"
                  style={{ color: "var(--color-text-3)" }}
                >
                  Grafo de Relacionamentos
                </p>
                <div
                  className="overflow-hidden"
                  style={{ border: "1px solid var(--color-border)" }}
                >
                  <GraphView entityId={org.id} />
                </div>
              </div>
            </div>
          )}

          {/* ── Contratos ── */}
          {activeTab === "contratos" && (
            <div className="space-y-4">
              {org.total_contracts_value > 0 ? (
                <div className="space-y-3">
                  <p
                    className="text-mono-xs uppercase tracking-widest"
                    style={{ color: "var(--color-text-3)" }}
                  >
                    Valor Total de Contratos
                  </p>
                  <p
                    className="text-display-lg tabular-nums"
                    style={{
                      fontFamily: "var(--font-mono)",
                      color: "var(--color-amber)",
                    }}
                  >
                    {formatBRL(org.total_contracts_value)}
                  </p>
                  <p className="text-mono-xs" style={{ color: "var(--color-text-3)" }}>
                    Soma de todos os contratos registrados para este órgão.
                  </p>
                </div>
              ) : (
                <EmptyState
                  icon={FileText}
                  title="Sem contratos registrados"
                  description="Nenhum contrato foi associado a esta organização nos dados disponíveis."
                />
              )}
            </div>
          )}

          {/* ── Fornecedores ── */}
          {activeTab === "fornecedores" && (
            <EmptyState
              icon={Users}
              title="Sem fornecedores cadastrados"
              description="Os dados de fornecedores desta organização não estão disponíveis no momento."
            />
          )}

          {/* ── Tipologias ── */}
          {activeTab === "tipologias" && (
            <EmptyState
              icon={Layers}
              title="Sem tipologias registradas"
              description="Nenhuma tipologia foi identificada para esta organização nos dados disponíveis."
            />
          )}
        </div>
      </div>
    </div>
  );
}
